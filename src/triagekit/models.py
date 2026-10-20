"""Core data models for the triage engine.

`Referral` is a normalized, engine-ready view of a raw intake record (dict).
`TriageResult` is the structured decision the engine produces. Neither model
knows anything program-specific — the domain lives in the config and ruleset.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .normalize import to_bool, to_int


class Decision:
    """Terminal decision states. String constants keep serialization trivial."""

    ACCEPT = "ACCEPT"
    DECLINE = "DECLINE"
    CONTACT_REQUIRED = "CONTACT_REQUIRED"
    REFER = "REFER"
    REDIRECT_YOUTH = "REDIRECT_YOUTH"
    PENDING = ""  # engine default before finalization


class Service:
    """Requestable services. Kept as constants for stable output labels.

    The reference program models a clinic that *initiates* a medication therapy
    (but does not provide maintenance-only refills), performs a clinical
    procedure, and offers wrap-around counselling and peer support.
    """

    MEDICATION_INITIATION = "MEDICATION_INITIATION"
    MEDICATION_MAINTENANCE = "MEDICATION_MAINTENANCE"
    PROCEDURE = "PROCEDURE"
    COUNSELLING = "COUNSELLING"
    PEER_SUPPORT = "PEER_SUPPORT"


@dataclass
class Referral:
    """A single referral, normalized to typed fields the engine can reason over.

    Build one with :meth:`from_raw`, which coerces the loose CSV/EMR value
    representations (``"NA"``, ``"yes"``, ``1``, ``""`` ...) into ``bool | None``
    and ``int | None``. Free-text fields are preserved verbatim for keyword
    detection.
    """

    # Identity / required
    first_name: str | None = None
    last_name: str | None = None
    age: int | None = None

    # Geography / coverage
    postal_fsa: str = ""
    out_of_region_insurance: bool | None = None  # covered by another region's public plan
    in_catchment: bool | None = None
    connected_pcp: bool | None = None

    # Waitlist state (batch-level system state)
    wl_medication: bool | None = None
    wl_procedure: bool | None = None
    wl_counselling: bool | None = None
    wl_peer: bool | None = None

    # Requested services
    req_medication_initiation: bool | None = None
    req_medication_maintenance: bool | None = None
    req_procedure: bool | None = None
    req_counselling: bool | None = None
    req_peer_support: bool | None = None

    # Clinical context
    procedure_type: str = ""  # free string; "" / "uncertain" / e.g. "consultation"
    prior_treatment: bool | None = None  # already established on the therapy?
    comorbidity_uncontrolled: bool | None = None
    mental_health_history: bool | None = None
    can_attend_partner_site: bool | None = None
    virtual_possible: bool | None = None

    # Free text (comorbidity / treatment detection)
    meds_text: str = ""
    med_history_text: str = ""

    # Passthrough identifiers (not used in logic, echoed to output)
    full_name: str = ""
    referral_id: str = ""

    @staticmethod
    def _procedure_type(raw: Any) -> str:
        """`procedure_type_specified` is a string in the current data model, but
        legacy rows encode it as a bool. Normalize both to a string."""
        if isinstance(raw, bool):
            return "specified" if raw else ""
        if isinstance(raw, str):
            return raw.strip()
        return ""

    @classmethod
    def from_raw(cls, raw: dict) -> Referral:
        g = raw.get
        return cls(
            first_name=g("first_name"),
            last_name=g("last_name"),
            age=to_int(g("age")),
            postal_fsa=(g("postal_fsa") or "").strip().upper(),
            out_of_region_insurance=to_bool(g("out_of_region_insurance")),
            in_catchment=to_bool(g("in_catchment")),
            connected_pcp=to_bool(g("connected_pcp")),
            wl_medication=to_bool(g("waitlist.medication_open")),
            wl_procedure=to_bool(g("waitlist.procedure_open")),
            wl_counselling=to_bool(g("waitlist.counselling_open")),
            wl_peer=to_bool(g("waitlist.peer_open")),
            req_medication_initiation=to_bool(g("request.medication_initiation")),
            req_medication_maintenance=to_bool(g("request.medication_maintenance")),
            req_procedure=to_bool(g("request.procedure")),
            req_counselling=to_bool(g("request.counselling")),
            req_peer_support=to_bool(g("request.peer_support")),
            procedure_type=cls._procedure_type(g("procedure_type_specified")),
            prior_treatment=to_bool(g("prior_treatment")),
            comorbidity_uncontrolled=to_bool(g("comorbidity_uncontrolled")),
            mental_health_history=to_bool(g("mental_health_history")),
            can_attend_partner_site=to_bool(g("can_attend_partner_site")),
            virtual_possible=to_bool(g("virtual_possible")),
            meds_text=str(g("meds_text") or ""),
            med_history_text=str(g("med_history_text") or ""),
            full_name=str(g("full_name") or ""),
            referral_id=str(g("referral_id") or ""),
        )

    def requested_services(self) -> dict:
        """Mutable working copy of request flags, keyed by Service constant."""
        return {
            Service.MEDICATION_INITIATION: bool(self.req_medication_initiation),
            Service.MEDICATION_MAINTENANCE: bool(self.req_medication_maintenance),
            Service.PROCEDURE: bool(self.req_procedure),
            Service.COUNSELLING: bool(self.req_counselling),
            Service.PEER_SUPPORT: bool(self.req_peer_support),
        }


@dataclass
class TriageResult:
    """Structured triage decision. Mirrors the documented output schema."""

    decision: str = Decision.PENDING
    accepted_services: list = field(default_factory=list)
    declined_services: list = field(default_factory=list)
    refer_out_services: list = field(default_factory=list)
    follow_up_required: bool = False
    contradictions: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    referral_destination: str = ""
    routing_instruction: str = ""

    def add_note(self, note: str) -> None:
        if note and note not in self.notes:
            self.notes.append(note)

    def add_contradiction(self, desc: str) -> None:
        if desc and desc not in self.contradictions:
            self.contradictions.append(desc)

    def to_dict(self) -> dict:
        return {
            "decision": self.decision,
            "accepted_services": self.accepted_services,
            "declined_services": self.declined_services,
            "refer_out_services": self.refer_out_services,
            "follow_up_required": self.follow_up_required,
            "contradictions": self.contradictions,
            "notes": "; ".join(self.notes),
            "referral_destination": self.referral_destination,
            "routing_instruction": self.routing_instruction,
        }
