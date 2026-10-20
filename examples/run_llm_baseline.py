"""Run the LLM triage baseline over the synthetic referrals and print decisions.

This calls the Claude API and therefore needs ``ANTHROPIC_API_KEY`` (or an
`ant auth login` profile) and ``pip install "triagekit[llm]"``. Responses are
cached under ``.llm_cache/`` so re-runs are free.

    python examples/run_llm_baseline.py --n 5

Note: this prints the LLM's decisions only. Formal comparison against the
deterministic engine and human labels is deliberately out of scope until the
clinical gold labels are finalized.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from triagekit import build_clinic_engine
from triagekit.baselines import LLMConfig, triage_with_llm


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", default="data/synthetic/referrals.csv")
    ap.add_argument("--n", type=int, default=5, help="how many rows to triage")
    ap.add_argument("--model", default="claude-opus-5")
    args = ap.parse_args()

    with open(args.csv, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))[: args.n]

    engine = build_clinic_engine()  # shown side by side for context, not scored
    config = LLMConfig(model=args.model)

    print(f"{'name':<20}{'engine':<18}{'llm':<18}")
    print("-" * 56)
    for row in rows:
        engine_decision = engine.run(row).decision
        try:
            llm_decision = triage_with_llm(row, config).get("decision", "?")
        except ImportError as exc:
            print(exc)
            return
        print(f"{row.get('full_name', ''):<20}{engine_decision:<18}{llm_decision:<18}")


if __name__ == "__main__":
    main()
