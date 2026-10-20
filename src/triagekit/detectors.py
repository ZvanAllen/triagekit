"""Keyword-based detectors over free-text medication / history fields.

Deliberately simple and transparent: a substring match against configurable
lexicons. No model, no embeddings — every positive is auditable to the exact
keyword that fired. Mental-health medications are excluded from comorbidity
detection by construction (they simply are not in the comorbidity lexicon).
"""

from __future__ import annotations

from .config import TriageConfig


def detect_comorbidity(meds_text: str, history_text: str, cfg: TriageConfig) -> bool:
    """True if meds or history text mentions a (non-mental-health) comorbidity."""
    combined = f"{meds_text or ''} {history_text or ''}".lower()
    keywords = cfg.comorbidity_med_keywords + cfg.comorbidity_history_keywords
    return any(kw in combined for kw in keywords)


def detect_maintenance_treatment(meds_text: str, cfg: TriageConfig) -> bool:
    """True if medication text indicates the client is already on the therapy.

    Used to sanity-check the ``prior_treatment`` intake field — e.g. a
    maintenance request with ``prior_treatment=True`` but no matching medication
    listed is flagged as a contradiction.
    """
    if not meds_text:
        return False
    lower = meds_text.lower()
    return any(kw in lower for kw in cfg.treatment_med_keywords)
