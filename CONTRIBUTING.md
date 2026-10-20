# Contributing

Thanks for your interest in `triagekit`.

## Development setup

```bash
git clone https://github.com/ZvanAllen/triagekit.git
cd triagekit
pip install -e ".[dev,app,llm]"
```

## Before opening a PR

```bash
ruff check .      # lint
pytest -q         # tests (must stay green)
```

CI runs both on Python 3.10–3.12.

## Design principles (please preserve these)

- **The decision path stays deterministic.** No model output may influence a
  triage decision. The LLM baseline in `baselines/` is for comparison only and
  must never be imported by the engine or a ruleset.
- **The engine stays domain-agnostic.** Clinic-specific values belong in a
  config (`configs/*.yaml`) or a ruleset, never in `engine.py`, `models.py`,
  `config.py`, or `normalize.py`.
- **Rules stay small and named.** Each rule is one function with a single,
  testable responsibility; add a test in `tests/` alongside any new rule.
- **Auditability first.** Every decision must remain traceable to the rules and
  keywords that produced it.

## Data

Never commit real patient data. All fixtures are synthetic — regenerate with
`python data/synthetic/generate.py`.
