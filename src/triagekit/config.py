"""Configuration for a triage deployment.

Everything program-specific that a rule needs — catchment postal patterns,
keyword lexicons for comorbidity/treatment detection, age thresholds, exempt
procedure types, referral destinations — lives here and is loaded from a YAML
file. The engine and rules stay generic; swapping the config (and ruleset)
retargets the tool.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class TriageConfig:
    catchment_patterns: list = field(default_factory=list)  # compiled regexes
    comorbidity_med_keywords: list = field(default_factory=list)
    comorbidity_history_keywords: list = field(default_factory=list)
    mental_health_med_keywords: list = field(default_factory=list)
    treatment_med_keywords: list = field(default_factory=list)

    # Procedure types that do NOT require prior treatment (matched as substrings).
    procedure_exempt_types: list = field(default_factory=list)

    # Age thresholds (years).
    paediatric_max_age: int = 16          # age <= this -> redirect to paediatric services
    youth_redirect_max_age: int = 17      # age <= this (and > paediatric_max) -> youth services

    destinations: dict = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, path: str | Path) -> TriageConfig:
        with open(path, encoding="utf-8") as f:
            spec = yaml.safe_load(f) or {}
        patterns = spec.get("catchment_fsa_patterns", [])
        kw = spec.get("keywords", {})
        ages = spec.get("age_thresholds", {})
        return cls(
            catchment_patterns=[re.compile(p) for p in patterns],
            comorbidity_med_keywords=[k.lower() for k in kw.get("comorbidity_meds", [])],
            comorbidity_history_keywords=[k.lower() for k in kw.get("comorbidity_history", [])],
            mental_health_med_keywords=[k.lower() for k in kw.get("mental_health_meds", [])],
            treatment_med_keywords=[k.lower() for k in kw.get("treatment_meds", [])],
            procedure_exempt_types=[k.lower() for k in spec.get("procedure_exempt_types", [])],
            paediatric_max_age=int(ages.get("paediatric_max_age", 16)),
            youth_redirect_max_age=int(ages.get("youth_redirect_max_age", 17)),
            destinations=spec.get("destinations", {}),
        )

    def fsa_in_catchment(self, fsa: str) -> bool | None:
        """Return whether an FSA is in catchment, or ``None`` if undeterminable."""
        if not fsa:
            return None
        return any(p.match(fsa) for p in self.catchment_patterns)

    def procedure_is_exempt(self, procedure_type: str) -> bool:
        """True if the procedure type is exempt from the prior-treatment rule."""
        lower = (procedure_type or "").lower()
        return bool(lower) and any(t in lower for t in self.procedure_exempt_types)
