# Reference triage decision logic

This documents the reference ruleset in
[`src/triagekit/rulesets/clinic.py`](../src/triagekit/rulesets/clinic.py). Rules
run top to bottom; the first rule that reaches a terminal decision stops
evaluation. Everything program-specific (postal patterns, keyword lexicons, age
thresholds, exempt procedure types, referral destinations) lives in
[`configs/clinic.yaml`](../src/triagekit/configs/clinic.yaml).

The reference program is a fictional weight-management service. It starts
anti-obesity medication (but does not take on maintenance-only prescriptions),
refers clients for a bariatric procedure once they are established on medical
treatment, and offers wrap-around counselling and peer support groups.

## Decision states

| State | Meaning |
|-------|---------|
| `ACCEPT` | Accepted for the requested service(s). |
| `DECLINE` | Not eligible (out-of-region public insurance, out of catchment, or all services unavailable). |
| `CONTACT_REQUIRED` | Coordinator must contact the client before deciding (missing data, contradictions, or follow-up needed). |
| `REFER` | Clinical services referred out (e.g. uncontrolled comorbidity → complexity clinic). |
| `REDIRECT_YOUTH` | Minor; redirect to paediatric or youth services. |

## Rule order

| # | Rule | Effect |
|---|------|--------|
| 1 | **Input validation** | Missing name/DOB, or no service requested → `CONTACT_REQUIRED` (stop). |
| 2 | **Init + derive catchment** | Build working state; if `in_catchment` is unset, derive it from `postal_fsa`. An explicit `in_catchment` override always wins. |
| 3 | **Age** | Age ≤ paediatric threshold → `REDIRECT_YOUTH` (paediatric services); one year above → `REDIRECT_YOUTH` (youth services); older → continue. |
| 4 | **Out-of-region coverage** | Covered by another region's public insurance → `DECLINE` (stop). |
| 5 | **Catchment** | Out of catchment → `DECLINE` with alternatives (stop). Undeterminable → follow-up. |
| 6 | **Detection** | Keyword-scan meds/history for comorbidities and existing treatment (transparent substring match; mental-health meds excluded from comorbidity detection). |
| 7 | **Access** | No virtual option *and* cannot attend a partner site → follow-up. |
| 8 | **Uncontrolled comorbidity** | Refer clinical services to the complexity clinic; still accept open wrap-around services → `REFER` (stop). |
| 9 | **Comorbidity, control unknown** | Detected comorbidity with unknown control status → follow-up. Detected but reported controlled → informational note only. |
| 10 | **Contradictions** | e.g. medication initiation *and* maintenance requested; maintenance requested but no prior treatment. |
| 11 | **Maintenance without initiation** | Decline the maintenance service (program does not provide maintenance-only). |
| 12–15 | **Per-service waitlists** | For each requested service, accept if its waitlist is open, decline if closed. A procedure additionally defers when there is no prior treatment (exempt procedure types excepted) and flags an unspecified procedure type. |
| 16 | **PCP follow-up** | Unknown PCP status → follow-up. |
| 17 | **Finalize** | Normalize accumulated state into one decision (see below). |

## Finalization

Applied in order:

1. Any contradiction → `CONTACT_REQUIRED`.
2. Any follow-up flag → `CONTACT_REQUIRED`.
3. Any referred-out service → `REFER`.
4. All accepted, none declined → `ACCEPT`.
5. All declined, none accepted → `DECLINE`.
6. Mixed accepted + declined (e.g. one waitlist closed) → `ACCEPT` for what's available, with a note.

## Design notes

- **`None` ≠ `False`.** "Unknown / not asked" is distinct from "no" throughout;
  several rules branch specifically on unknown values to trigger follow-up rather
  than a hard decision.
- **Detectors are advisory.** Keyword detection never *overrides* a structured
  intake answer — a detected comorbidity med with `comorbidity_uncontrolled =
  False` is a note, not an escalation.
- **Auditability.** Every decision carries the notes that produced it, and every
  positive detector match is traceable to a specific keyword.

> The rule structure comes from a clinician-reviewed specification; the clinical
> content is fictional. It is a research artifact, not clinical guidance.
