"""Generate synthetic (fake) referrals matching the triage input schema.

No real patient data is used anywhere in this project. This produces randomized,
non-identifying rows for demos, load-testing, and CLI examples. It does NOT
produce gold triage labels — labelling is a clinical task.

    python data/synthetic/generate.py --n 50 --seed 7 -o data/synthetic/generated.csv
"""

from __future__ import annotations

import argparse
import csv
import random

FIRST = ["Skyler", "Rowan", "Alex", "Morgan", "Taylor", "Avery", "Sam", "Casey",
         "Quinn", "Emerson", "Drew", "Jordan", "Cameron", "Riley", "Shawn", "Elliot"]
LAST = ["Young", "Khan", "Patel", "Brown", "Novak", "Martin", "Baker", "Nguyen",
        "Smith", "Roy", "Lee", "Ali", "Chen", "Garcia"]
# Fictional placeholder FSAs. In-catchment codes match the placeholder patterns
# in configs/clinic.yaml; out-of-catchment codes deliberately do not.
IN_CATCHMENT_FSA = ["Z1A", "Z3B", "Z1C", "Z3E", "Z5L", "Z1H", "Z8R"]
OUT_FSA = ["Q1A", "U2B", "Q9Z", "U5B", "Q3X"]
COMORBIDITY_MEDS = ["Metformin 500mg", "Furosemide 40mg", "Lisinopril 10mg", "Insulin glargine 20 units"]
TREATMENT_MEDS = ["Semaglutide 1mg weekly", "Liraglutide 3mg daily", "Orlistat 120mg"]
MH_MEDS = ["Sertraline 50mg", "Escitalopram 10mg", "Bupropion 150mg"]
PROCEDURE_TYPES = ["", "consultation", "assessment", "uncertain", "standard procedure"]


def _b(rng, p_true=0.5):
    return rng.random() < p_true


def make_row(rng: random.Random, idx: int) -> dict:
    in_catch = _b(rng, 0.8)
    fsa = rng.choice(IN_CATCHMENT_FSA if in_catch else OUT_FSA)
    first, last = rng.choice(FIRST), rng.choice(LAST)

    meds = []
    if _b(rng, 0.4):
        meds.append(rng.choice(TREATMENT_MEDS))
    if _b(rng, 0.3):
        meds.append(rng.choice(COMORBIDITY_MEDS))
    if _b(rng, 0.3):
        meds.append(rng.choice(MH_MEDS))

    want_init = _b(rng, 0.4)
    return {
        "referral_id": f"SYN-{idx:04d}",
        "full_name": f"{first} {last}",
        "first_name": first,
        "last_name": last,
        "age": rng.choice([14, 16, 17] + list(range(18, 65))),
        "postal_fsa": fsa,
        "out_of_region_insurance": _b(rng, 0.1),
        "in_catchment": "",  # let the engine derive it from the FSA
        "connected_pcp": rng.choice([True, False, ""]),
        "waitlist.medication_open": True,
        "waitlist.procedure_open": _b(rng, 0.7),
        "waitlist.counselling_open": True,
        "waitlist.peer_open": True,
        "request.medication_initiation": want_init,
        "request.medication_maintenance": _b(rng, 0.15) and not want_init,
        "request.procedure": _b(rng, 0.3),
        "request.counselling": _b(rng, 0.5),
        "request.peer_support": _b(rng, 0.4),
        "procedure_type_specified": rng.choice(PROCEDURE_TYPES),
        "prior_treatment": _b(rng, 0.4),
        "comorbidity_uncontrolled": rng.choice([True, False, ""]),
        "mental_health_history": _b(rng, 0.4),
        "can_attend_partner_site": rng.choice([True, False, ""]),
        "virtual_possible": rng.choice([True, False, ""]),
        "med_history_text": "None reported",
        "meds_text": "; ".join(meds) if meds else "None",
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=40, help="number of rows")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("-o", "--output", default="data/synthetic/generated.csv")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    rows = [make_row(rng, i + 1) for i in range(args.n)]
    with open(args.output, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} synthetic referrals to {args.output}")


if __name__ == "__main__":
    main()
