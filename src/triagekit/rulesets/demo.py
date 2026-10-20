"""A tiny, non-clinical ruleset.

Its only purpose is to demonstrate that the engine core (record → ordered rules
→ structured result) is not tied to the clinical domain. This is a generic
"support ticket" triage: route by urgency, contactability, and completeness.

    from triagekit import TriageConfig, TriageEngine
    from triagekit.rulesets.demo import DEMO_RULES, TicketRecord

    engine = TriageEngine(TriageConfig(), DEMO_RULES, record_factory=TicketRecord.from_raw)
    engine.run({"subject": "server down", "urgent": True, "has_contact": True}).decision
    # -> "ACCEPT"
"""

from __future__ import annotations

from dataclasses import dataclass

from ..engine import CONTINUE, STOP
from ..models import Decision
from ..normalize import to_bool


@dataclass
class TicketRecord:
    subject: str = ""
    urgent: bool | None = None
    has_contact: bool | None = None
    full_name: str = ""
    referral_id: str = ""

    @classmethod
    def from_raw(cls, raw: dict) -> TicketRecord:
        g = raw.get
        return cls(
            subject=str(g("subject") or ""),
            urgent=to_bool(g("urgent")),
            has_contact=to_bool(g("has_contact")),
            full_name=str(g("full_name") or g("subject") or ""),
            referral_id=str(g("referral_id") or ""),
        )


def validate(rec, result, cfg, ctx):
    if not rec.subject:
        result.decision = Decision.CONTACT_REQUIRED
        result.add_note("Missing subject")
        result.follow_up_required = True
        return STOP
    return CONTINUE


def route_urgent(rec, result, cfg, ctx):
    if rec.urgent is True:
        result.accepted_services.append("URGENT_QUEUE")
        result.add_note("Routed to urgent queue")
        return CONTINUE
    return CONTINUE


def require_contact(rec, result, cfg, ctx):
    if rec.has_contact is not True:
        result.follow_up_required = True
        result.add_note("No reliable contact method; follow up needed")
    return CONTINUE


def finalize(rec, result, cfg, ctx):
    if result.follow_up_required:
        result.decision = Decision.CONTACT_REQUIRED
    elif result.accepted_services:
        result.decision = Decision.ACCEPT
    else:
        result.accepted_services.append("STANDARD_QUEUE")
        result.decision = Decision.ACCEPT
    return STOP


DEMO_RULES = [validate, route_urgent, require_contact, finalize]
