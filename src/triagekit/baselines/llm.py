"""LLM triage baseline (Claude).

An LLM alternative to the deterministic engine: given a referral, ask Claude to
return a triage decision in the *same* output schema. This is the "before" side
of the project's core story — frontier LLMs could do this with a structured
prompt, but privacy/infra constraints ruled out running one in production, which
is why the deterministic engine exists.

Design notes:
- Optional dependency. ``anthropic`` is only imported when you actually call the
  model, so importing triagekit never requires it. Install with
  ``pip install "triagekit[llm]"``.
- Responses are cached to disk keyed by (model, prompt) so re-runs cost nothing.
- Nothing here is in the decision path of the deterministic product.

Requires ``ANTHROPIC_API_KEY`` (or an ``ant auth login`` profile) at call time.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

DECISION_STATES = [
    "ACCEPT",
    "DECLINE",
    "CONTACT_REQUIRED",
    "REFER",
    "REDIRECT_YOUTH",
]

SYSTEM_PROMPT = """\
You are a triage assistant for a weight-management program's referral intake.
The program starts anti-obesity medication (but does not take on maintenance-only
prescriptions), refers clients for a bariatric procedure once they are
established on medical treatment, and offers wrap-around counselling and peer
support groups. Given a single referral, decide how it should be triaged and return
ONLY a JSON object (no prose, no code fences).

Decision must be exactly one of:
- ACCEPT            client accepted for the requested service(s)
- DECLINE           client not eligible (out-of-region public insurance, or out of catchment)
- CONTACT_REQUIRED  coordinator must contact the client before deciding
                    (missing info, contradictions, or follow-up needed)
- REFER             refer clinical services out (e.g. uncontrolled comorbidity
                    to a complexity clinic)
- REDIRECT_YOUTH    client is a minor; redirect to youth/paediatric services

Guiding policy (apply in order, stop at the first that decides):
1. Missing name/DOB, or no service requested -> CONTACT_REQUIRED.
2. Age <= 17 -> REDIRECT_YOUTH.
3. Covered by another region's public insurance -> DECLINE.
4. Postal code clearly outside the program's catchment -> DECLINE.
5. Uncontrolled comorbidity (e.g. unmanaged diabetes, heart failure, kidney disease)
   -> REFER clinical services; wrap-around (counselling/peer) may still be accepted.
6. Medication maintenance requested without initiation -> decline that service.
7. A procedure with no prior treatment (and not an exempt procedure type)
   -> defer. Requested services whose waitlist is closed -> declined.
8. Contradictions (e.g. maintenance requested but no prior treatment), unclear
   comorbidity control, or access barriers -> follow-up -> CONTACT_REQUIRED.
9. Otherwise, ACCEPT the available services.

Return exactly this shape:
{
  "decision": "<one of the five states>",
  "accepted_services": [],
  "declined_services": [],
  "refer_out_services": [],
  "follow_up_required": true,
  "notes": "one concise sentence"
}
Services use these labels: MEDICATION_INITIATION, MEDICATION_MAINTENANCE,
PROCEDURE, COUNSELLING, PEER_SUPPORT."""

# Fields we surface to the model. Deliberately excludes direct identifiers.
_PROMPT_FIELDS = [
    "age", "postal_fsa", "out_of_region_insurance", "in_catchment", "connected_pcp",
    "waitlist.medication_open", "waitlist.procedure_open",
    "waitlist.counselling_open", "waitlist.peer_open",
    "request.medication_initiation", "request.medication_maintenance", "request.procedure",
    "request.counselling", "request.peer_support",
    "procedure_type_specified", "prior_treatment", "comorbidity_uncontrolled",
    "mental_health_history", "can_attend_partner_site", "virtual_possible",
    "med_history_text", "meds_text",
]


@dataclass
class LLMConfig:
    model: str = "claude-opus-5"
    effort: str = "low"          # triage is a constrained classification task
    max_tokens: int = 1024
    cache_dir: str | None = None  # defaults to ./.llm_cache when None


def build_user_prompt(referral: dict) -> str:
    lines = ["Referral:"]
    for key in _PROMPT_FIELDS:
        value = referral.get(key, "")
        if value not in (None, ""):
            lines.append(f"  {key}: {value}")
    return "\n".join(lines)


def _cache_path(cache_dir: Path, model: str, prompt: str) -> Path:
    digest = hashlib.sha256(f"{model}\n{prompt}".encode()).hexdigest()[:16]
    return cache_dir / f"{digest}.json"


def _extract_json(text: str) -> dict:
    """Parse the model's reply, tolerating stray prose or code fences."""
    text = text.strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object in LLM response: {text[:200]!r}")
    return json.loads(text[start : end + 1])


def triage_with_llm(referral: dict, config: LLMConfig | None = None, client=None) -> dict:
    """Triage one referral with Claude. Returns a decision dict; caches to disk.

    Raises ImportError with an install hint if the ``anthropic`` SDK is missing.
    """
    config = config or LLMConfig()
    cache_dir = Path(config.cache_dir or ".llm_cache")
    cache_dir.mkdir(parents=True, exist_ok=True)

    user_prompt = build_user_prompt(referral)
    cached = _cache_path(cache_dir, config.model, user_prompt)
    if cached.exists():
        return json.loads(cached.read_text(encoding="utf-8"))

    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover - depends on optional extra
        raise ImportError(
            "The LLM baseline needs the Anthropic SDK. Install with: "
            'pip install "triagekit[llm]"'
        ) from exc

    client = client or anthropic.Anthropic()
    response = client.messages.create(
        model=config.model,
        max_tokens=config.max_tokens,
        thinking={"type": "adaptive"},
        output_config={"effort": config.effort},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text = "".join(b.text for b in response.content if b.type == "text")
    decision = _extract_json(text)

    if decision.get("decision") not in DECISION_STATES:
        decision["_warning"] = f"unexpected decision: {decision.get('decision')!r}"

    cached.write_text(json.dumps(decision, indent=2, ensure_ascii=False), encoding="utf-8")
    return decision
