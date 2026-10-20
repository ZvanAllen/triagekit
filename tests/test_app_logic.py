"""Headless tests for the desktop app's GUI-free logic.

These never construct a Tk window, so they run in CI without a display.
"""

from triagekit.app import (
    EXPORT_FIELDS,
    export_rows,
    final_decision,
    printable_summary,
    sample_referrals,
    triage_referrals,
    write_csv,
)

WAITLISTS = {
    "waitlist.medication_open": True,
    "waitlist.procedure_open": True,
    "waitlist.counselling_open": True,
    "waitlist.peer_open": True,
}


def test_sample_data_bundled_and_loads():
    rows = sample_referrals()
    assert len(rows) == 12
    assert "full_name" in rows[0]


def test_triage_referrals_shapes_results():
    rows = sample_referrals()
    results = triage_referrals(rows, WAITLISTS)
    assert len(results) == len(rows)
    r = results[0]
    assert r["row"] == 1
    assert r["decision"] in {"ACCEPT", "DECLINE", "CONTACT_REQUIRED", "REFER", "REDIRECT_YOUTH"}
    assert "_referral" in r


def test_waitlist_state_flows_into_engine():
    # A counselling-only request with the counselling waitlist closed -> declined.
    referral = {
        "first_name": "A", "last_name": "B", "age": 30, "postal_fsa": "Z1A",
        "connected_pcp": True, "request.counselling": True,
    }
    closed = dict(WAITLISTS, **{"waitlist.counselling_open": False})
    result = triage_referrals([referral], closed)[0]
    assert result["decision"] == "DECLINE"


def test_final_decision_prefers_override():
    result = {"decision": "ACCEPT", "override_decision": "CONTACT_REQUIRED"}
    assert final_decision(result) == "CONTACT_REQUIRED"
    assert final_decision({"decision": "ACCEPT", "override_decision": ""}) == "ACCEPT"


def test_export_rows_join_lists_and_cover_fields():
    results = triage_referrals(sample_referrals(), WAITLISTS)
    rows = export_rows(results)
    assert set(rows[0].keys()) == set(EXPORT_FIELDS)
    assert isinstance(rows[0]["accepted_services"], str)


def test_write_csv_roundtrip(tmp_path):
    results = triage_referrals(sample_referrals(), WAITLISTS)
    out = tmp_path / "out.csv"
    write_csv(results, out)
    text = out.read_text(encoding="utf-8")
    assert "final_decision" in text.splitlines()[0]
    assert text.count("\n") >= len(results)


def test_printable_summary_has_summary_and_cases():
    results = triage_referrals(sample_referrals(), WAITLISTS)
    text = printable_summary(results, WAITLISTS, source="sample.csv")
    assert "Referral Triage Results" in text
    assert "SUMMARY" in text
    assert "Case #1" in text
