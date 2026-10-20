"""triagekit — a configurable, deterministic engine for clinical referral triage.

The engine core (:class:`TriageEngine`) is domain-agnostic: it runs an ordered
ruleset against a normalized :class:`Referral` and produces a structured
:class:`TriageResult`. The program-specific behavior lives in a YAML
:class:`TriageConfig` plus a ruleset. The bundled reference implementation is a
specialty-clinic referral triage policy (:func:`build_clinic_engine`).
"""

from __future__ import annotations

from .config import TriageConfig
from .engine import CONTINUE, STOP, Rule, TriageEngine
from .factory import build_clinic_engine
from .models import Decision, Referral, Service, TriageResult

__all__ = [
    "CONTINUE",
    "STOP",
    "Decision",
    "Referral",
    "Rule",
    "Service",
    "TriageConfig",
    "TriageEngine",
    "TriageResult",
    "build_clinic_engine",
]

__version__ = "0.1.0"
