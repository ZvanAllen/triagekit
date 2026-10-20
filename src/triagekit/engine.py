"""The generic rule-runner.

A :class:`TriageEngine` pairs a :class:`~triagekit.config.TriageConfig` with a
*ruleset* — an ordered list of rule callables. Each rule inspects the record and
mutates the shared :class:`~triagekit.models.TriageResult`; a rule may end
evaluation early by returning ``STOP``. The engine holds no clinical knowledge:
a different ruleset + config (+ record type) retargets it to another domain.

The engine does not assume a record type. A ``record_factory`` turns raw dicts
into whatever object the ruleset expects (the clinic engine uses
``Referral.from_raw``); records that are already objects pass through untouched.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from .config import TriageConfig
from .models import TriageResult

# A rule receives (record, result, config, context) and returns True (STOP)
# to end evaluation, or a falsy value to continue to the next rule.
Rule = Callable[[Any, TriageResult, TriageConfig, dict], bool]

STOP = True
CONTINUE = False


def _identity(record: Any) -> Any:
    return record


class TriageEngine:
    def __init__(
        self,
        config: TriageConfig,
        ruleset: Iterable[Rule],
        record_factory: Callable[[dict], Any] = _identity,
    ):
        self.config = config
        self.ruleset = list(ruleset)
        self.record_factory = record_factory

    def _coerce(self, record: Any) -> Any:
        return self.record_factory(record) if isinstance(record, dict) else record

    def run(self, record: Any) -> TriageResult:
        rec = self._coerce(record)
        result = TriageResult()
        context: dict = {}
        for rule in self.ruleset:
            if rule(rec, result, self.config, context):
                break
        return result

    def run_batch(self, records: Iterable) -> list[dict]:
        out = []
        for raw in records:
            rec = self._coerce(raw)
            res = self.run(rec).to_dict()
            res["full_name"] = getattr(rec, "full_name", "")
            res["referral_id"] = getattr(rec, "referral_id", "")
            out.append(res)
        return out
