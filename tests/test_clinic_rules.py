"""Rule-level tests for the reference specialty-clinic ruleset.

Each test crafts a minimal referral that isolates one rule. The base referral is
an eligible adult in catchment with a PCP and all waitlists open, so any decision
other than a clean ACCEPT is attributable to the field the test changes.
"""

import pytest

from triagekit import Decision, Service
from triagekit.factory import build_clinic_engine


@pytest.fixture(scope="module")
def engine():
    return build_clinic_engine()


def base(**overrides):
    ref = {
        "first_name": "Test",
        "last_name": "Client",
        "age": 30,
        "postal_fsa": "Z1A",
        "out_of_region_insurance": False,
        "connected_pcp": True,
        "waitlist.medication_open": True,
        "waitlist.procedure_open": True,
        "waitlist.counselling_open": True,
        "waitlist.peer_open": True,
        "comorbidity_uncontrolled": False,
    }
    ref.update(overrides)
    return ref


def test_happy_path_accept(engine):
    r = engine.run(base(**{"request.counselling": True}))
    assert r.decision == Decision.ACCEPT
    assert Service.COUNSELLING in r.accepted_services


def test_missing_required_field(engine):
    r = engine.run(base(first_name=None, **{"request.counselling": True}))
    assert r.decision == Decision.CONTACT_REQUIRED
    assert r.follow_up_required


def test_no_service_requested(engine):
    assert engine.run(base()).decision == Decision.CONTACT_REQUIRED


def test_under_paediatric_age_redirects(engine):
    r = engine.run(base(age=14, **{"request.counselling": True}))
    assert r.decision == Decision.REDIRECT_YOUTH
    assert r.referral_destination == "Paediatric Service"


def test_minor_redirects_to_youth_services(engine):
    r = engine.run(base(age=17, **{"request.counselling": True}))
    assert r.decision == Decision.REDIRECT_YOUTH
    assert r.referral_destination == "Youth Service"


def test_out_of_region_insurance_declines(engine):
    r = engine.run(base(out_of_region_insurance=True, **{"request.medication_initiation": True}))
    assert r.decision == Decision.DECLINE


def test_out_of_catchment_declines(engine):
    r = engine.run(base(postal_fsa="Q1A", **{"request.counselling": True}))
    assert r.decision == Decision.DECLINE
    assert "their region" in r.routing_instruction


def test_manual_in_catchment_override_wins(engine):
    # Out-of-pattern FSA but explicit override True -> not declined for catchment.
    r = engine.run(base(postal_fsa="Q1A", in_catchment=True, **{"request.counselling": True}))
    assert r.decision == Decision.ACCEPT


def test_uncontrolled_comorbidity_refers_clinical(engine):
    r = engine.run(
        base(
            comorbidity_uncontrolled=True,
            **{"request.medication_initiation": True, "request.counselling": True},
        )
    )
    assert r.decision == Decision.REFER
    assert Service.MEDICATION_INITIATION in r.refer_out_services
    assert Service.COUNSELLING in r.accepted_services  # wrap-around still accepted


def test_maintenance_only_declines(engine):
    r = engine.run(
        base(
            prior_treatment=True,
            meds_text="Semaglutide 1mg weekly",
            **{"request.medication_maintenance": True},
        )
    )
    assert r.decision == Decision.DECLINE
    assert Service.MEDICATION_MAINTENANCE in r.declined_services


def test_initiation_and_maintenance_is_contradiction(engine):
    r = engine.run(
        base(**{"request.medication_initiation": True, "request.medication_maintenance": True})
    )
    assert r.decision == Decision.CONTACT_REQUIRED
    assert r.contradictions


def test_closed_waitlist_declines_service(engine):
    r = engine.run(
        base(**{"request.counselling": True, "waitlist.counselling_open": False})
    )
    assert r.decision == Decision.DECLINE
    assert Service.COUNSELLING in r.declined_services


def test_unknown_pcp_triggers_contact(engine):
    r = engine.run(base(connected_pcp=None, **{"request.counselling": True}))
    assert r.decision == Decision.CONTACT_REQUIRED
    assert r.follow_up_required


def test_exempt_procedure_skips_prior_treatment(engine):
    # "consultation" is an exempt procedure type in the bundled config.
    r = engine.run(
        base(
            prior_treatment=False,
            procedure_type_specified="consultation",
            **{"request.procedure": True},
        )
    )
    assert Service.PROCEDURE in r.accepted_services


def test_non_exempt_procedure_defers_without_prior_treatment(engine):
    r = engine.run(
        base(
            prior_treatment=False,
            procedure_type_specified="standard procedure",
            **{"request.procedure": True},
        )
    )
    assert Service.PROCEDURE in r.declined_services
