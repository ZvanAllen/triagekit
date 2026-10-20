"""Command-line interface: run the reference clinic engine over a CSV of referrals.

    triagekit run referrals.csv -o results.json
    triagekit run referrals.csv --config my_program.yaml
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from .factory import build_clinic_engine


def _load_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def run_command(args: argparse.Namespace) -> int:
    engine = build_clinic_engine(args.config)
    referrals = _load_csv(Path(args.input))
    results = engine.run_batch(referrals)

    payload = json.dumps(results, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
        print(f"Wrote {len(results)} results to {args.output}")
    else:
        print(payload)

    # Small human-readable summary to stderr so stdout stays machine-readable.
    from collections import Counter

    dist = Counter(r["decision"] for r in results)
    print("\nDecision distribution:", file=sys.stderr)
    for decision, n in sorted(dist.items()):
        print(f"  {decision:<18} {n}", file=sys.stderr)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="triagekit", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Triage a CSV of referrals")
    run.add_argument("input", help="Path to referrals CSV")
    run.add_argument("-o", "--output", help="Write results JSON here (default: stdout)")
    run.add_argument(
        "-c", "--config", default=None, help="Path to a config YAML (default: bundled clinic)"
    )
    run.set_defaults(func=run_command)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
