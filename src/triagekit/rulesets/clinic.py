"""Reference ruleset: referral triage for a fictional weight-management program.

Each function is one rule. Rules run in list order (``CLINIC_RULES``); a rule
returns ``STOP`` to finalize early or ``CONTINUE`` to fall through. Inputs are
read from the :class:`Referral`; the working set that later rules mutate
(request flags, derived catchment, detector output) lives in ``ctx``.

The reference program starts anti-obesity medication (but does not take on
maintenance-only prescriptions), refers clients for a bariatric procedure once
they are established on medical treatment (with configurable exempt procedure
types), and offers wrap-around counselling and peer support groups. All
program-specific parameters live in the configuration, not here — so this policy
can be retargeted by editing the config rather than the code.

This is a behavior-preserving decomposition of an original monolithic engine
into named, individually-testable rules.
"""

from __future__ import annotations

from ..detectors import detect_comorbidity, detect_maintenance_treatment
from ..engine import CONTINUE, STOP
from ..models import Decision, Referral, Service, TriageResult

_CLINICAL_SERVICES = [
    Service.MEDICATION_INITIATION,
    Service.MEDICATION_MAINTENANCE,
    Service.PROCEDURE,
]


def _decline_all_requested(ref: Referral, result: TriageResult) -> None:
    for svc, requested in ref.requested_services().items():
        if requested:
            result.declined_services.append(svc)


# --- STEP 1: Input validation -------------------------------------------------
def validate_input(ref, result, cfg, ctx):
    missing = []
    if not ref.first_name:
        missing.append("first_name")
    if not ref.last_name:
        missing.append("last_name")
    if ref.age is None:
        missing.append("age/dob")
    if missing:
        result.decision = Decision.CONTACT_REQUIRED
        result.add_note(f"Missing required fields: {', '.join(missing)}")
        result.follow_up_required = True
        return STOP

    if not any(ref.requested_services().values()):
        result.decision = Decision.CONTACT_REQUIRED
        result.add_note("No services requested; verify support request")
        result.follow_up_required = True
        return STOP
    return CONTINUE


# --- STEP 2: Initialize working context + derive catchment --------------------
def init_context(ref, result, cfg, ctx):
    ctx["req"] = ref.requested_services()  # mutable working copy
    in_catchment = ref.in_catchment  # explicit override wins
    if in_catchment is None:
        in_catchment = cfg.fsa_in_catchment(ref.postal_fsa)  # True / False / None
    ctx["in_catchment"] = in_catchment
    return CONTINUE


# --- STEP 3: RULE-01 Age ------------------------------------------------------
def age_gate(ref, result, cfg, ctx):
    if ref.age <= cfg.youth_redirect_max_age:
        result.decision = Decision.REDIRECT_YOUTH
        _decline_all_requested(ref, result)
        if ref.age <= cfg.paediatric_max_age:
            result.add_note("Client under paediatric age threshold; redirect to paediatric services")
            result.referral_destination = cfg.destinations.get("paediatric", "Paediatric Service")
        else:
            result.add_note("Client is a minor; redirect to youth services")
            result.referral_destination = cfg.destinations.get("youth", "Youth Service")
        return STOP
    return CONTINUE


# --- STEP 4: RULE-02 Out-of-region public insurance ---------------------------
def decline_out_of_region_coverage(ref, result, cfg, ctx):
    if ref.out_of_region_insurance is True:
        result.decision = Decision.DECLINE
        _decline_all_requested(ref, result)
        result.add_note(
            "Covered by another jurisdiction's public insurance; outside service scope"
        )
        return STOP
    return CONTINUE


# --- STEP 5: RULE-03 Catchment ------------------------------------------------
def catchment(ref, result, cfg, ctx):
    in_catchment = ctx["in_catchment"]
    if in_catchment is False:
        result.decision = Decision.DECLINE
        _decline_all_requested(ref, result)
        result.add_note("Out-of-catchment postal code")
        result.routing_instruction = (
            "Client may seek similar services through other providers in their region"
        )
        return STOP
    if in_catchment is None:
        result.follow_up_required = True
        result.add_note("Catchment status could not be determined; verify address")
    return CONTINUE


# --- STEP 6: Comorbidity & treatment detection from free text -----------------
def detect_from_text(ref, result, cfg, ctx):
    ctx["comorbidity_detected"] = detect_comorbidity(
        ref.meds_text, ref.med_history_text, cfg
    )
    ctx["treatment_detected"] = detect_maintenance_treatment(ref.meds_text, cfg)
    return CONTINUE


# --- STEP 7: RULE-04 Access capability ----------------------------------------
def access_capability(ref, result, cfg, ctx):
    if ref.virtual_possible is False and ref.can_attend_partner_site is False:
        result.follow_up_required = True
        result.add_note("Limited access options; confirm in-person attendance")
    return CONTINUE


# --- STEP 8: RULE-05 Uncontrolled comorbidity ---------------------------------
def uncontrolled_comorbidity(ref, result, cfg, ctx):
    if ref.comorbidity_uncontrolled is True:
        result.decision = Decision.REFER
        for svc in _CLINICAL_SERVICES:
            if ctx["req"][svc]:
                result.refer_out_services.append(svc)
        if ctx["req"][Service.COUNSELLING]:
            (result.accepted_services if ref.wl_counselling else result.declined_services).append(
                Service.COUNSELLING
            )
        if ctx["req"][Service.PEER_SUPPORT]:
            (result.accepted_services if ref.wl_peer else result.declined_services).append(
                Service.PEER_SUPPORT
            )
        result.add_note(
            "Uncontrolled comorbidity; refer clinical services to complexity clinic"
        )
        result.referral_destination = cfg.destinations.get("complexity", "Complexity Clinic")
        return STOP
    return CONTINUE


# --- STEP 9: Comorbidity detected, control status unknown ---------------------
def comorbidity_unknown(ref, result, cfg, ctx):
    if ctx["comorbidity_detected"] and ref.comorbidity_uncontrolled is None:
        result.follow_up_required = True
        result.add_note(
            "Comorbidity detected from medications/history; control status "
            "unknown — requires assessment"
        )
    elif ctx["comorbidity_detected"] and ref.comorbidity_uncontrolled is False:
        result.add_note(
            "Note: comorbidity-related medication detected; intake reports controlled"
        )
    return CONTINUE


# --- STEP 10: Contradiction detection -----------------------------------------
def contradictions(ref, result, cfg, ctx):
    req = ctx["req"]
    if req[Service.MEDICATION_INITIATION] and req[Service.MEDICATION_MAINTENANCE]:
        result.add_contradiction(
            "Cannot request both medication initiation and maintenance"
        )
    if req[Service.MEDICATION_MAINTENANCE] and ref.prior_treatment is True and not ctx["treatment_detected"]:
        result.add_contradiction(
            "Maintenance requested with prior_treatment=True but no matching medication listed"
        )
    if req[Service.MEDICATION_MAINTENANCE] and ref.prior_treatment is False:
        result.add_contradiction("Maintenance requested but prior_treatment=False")
    return CONTINUE


# --- STEP 11: RULE-06 Maintenance without initiation --------------------------
def medication_maintenance(ref, result, cfg, ctx):
    req = ctx["req"]
    if req[Service.MEDICATION_MAINTENANCE] and not req[Service.MEDICATION_INITIATION]:
        result.declined_services.append(Service.MEDICATION_MAINTENANCE)
        result.add_note(
            "Maintenance declined; program does not provide maintenance without initiation"
        )
        req[Service.MEDICATION_MAINTENANCE] = False
    return CONTINUE


# --- Per-service waitlist evaluation (RULE-07/08/09) --------------------------
def service_medication_initiation(ref, result, cfg, ctx):
    if ctx["req"][Service.MEDICATION_INITIATION]:
        if ref.wl_medication is False:
            result.declined_services.append(Service.MEDICATION_INITIATION)
            result.add_note("Medication initiation waitlist closed")
        else:
            result.accepted_services.append(Service.MEDICATION_INITIATION)
    return CONTINUE


def service_procedure(ref, result, cfg, ctx):
    if not ctx["req"][Service.PROCEDURE]:
        return CONTINUE
    procedure_type = (ref.procedure_type or "").strip()
    if ref.wl_procedure is False:
        result.declined_services.append(Service.PROCEDURE)
        result.add_note("Procedure waitlist closed")
    elif ref.prior_treatment is False:
        if cfg.procedure_is_exempt(procedure_type):
            result.accepted_services.append(Service.PROCEDURE)
        else:
            result.declined_services.append(Service.PROCEDURE)
            result.add_note("Procedure deferred until treatment started (exempt types excepted)")
    elif not procedure_type or procedure_type.lower() in ("", "unsure", "uncertain", "unspecified"):
        result.accepted_services.append(Service.PROCEDURE)
        result.add_note("Procedure type unspecified; clarification needed")
    else:
        result.accepted_services.append(Service.PROCEDURE)
    return CONTINUE


def service_counselling(ref, result, cfg, ctx):
    if ctx["req"][Service.COUNSELLING]:
        if ref.wl_counselling is False:
            result.declined_services.append(Service.COUNSELLING)
            result.add_note("Counselling waitlist closed")
        else:
            result.accepted_services.append(Service.COUNSELLING)
    return CONTINUE


def service_peer_support(ref, result, cfg, ctx):
    if ctx["req"][Service.PEER_SUPPORT]:
        if ref.wl_peer is False:
            result.declined_services.append(Service.PEER_SUPPORT)
            result.add_note("Peer support waitlist closed")
        else:
            result.accepted_services.append(Service.PEER_SUPPORT)
    return CONTINUE


# --- STEP 12: PCP follow-up trigger -------------------------------------------
def pcp_followup(ref, result, cfg, ctx):
    if ref.connected_pcp is None:
        result.follow_up_required = True
        result.add_note("PCP status unknown; follow up needed")
    return CONTINUE


# --- STEP 13: RULE-10 Final decision normalization ----------------------------
def finalize(ref, result, cfg, ctx):
    if result.contradictions:
        result.decision = Decision.CONTACT_REQUIRED
        result.follow_up_required = True
    elif result.follow_up_required:
        result.decision = Decision.CONTACT_REQUIRED
    elif result.refer_out_services:
        result.decision = Decision.REFER
    elif result.accepted_services and not result.declined_services:
        result.decision = Decision.ACCEPT
    elif result.declined_services and not result.accepted_services:
        result.decision = Decision.DECLINE
    elif result.accepted_services and result.declined_services:
        result.decision = Decision.ACCEPT
        result.add_note("Some requested services unavailable due to waitlist status")
    else:
        result.decision = Decision.CONTACT_REQUIRED
        result.follow_up_required = True
        result.add_note("Unable to determine decision; manual review needed")
    return STOP


# Ordered ruleset consumed by TriageEngine.
CLINIC_RULES = [
    validate_input,
    init_context,
    age_gate,
    decline_out_of_region_coverage,
    catchment,
    detect_from_text,
    access_capability,
    uncontrolled_comorbidity,
    comorbidity_unknown,
    contradictions,
    medication_maintenance,
    service_medication_initiation,
    service_procedure,
    service_counselling,
    service_peer_support,
    pcp_followup,
    finalize,
]
