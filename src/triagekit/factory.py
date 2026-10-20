"""Convenience constructors for pre-wired engines."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

from .config import TriageConfig
from .engine import TriageEngine
from .models import Referral
from .rulesets.clinic import CLINIC_RULES


def _bundled_config_path(name: str) -> Path:
    return Path(resources.files("triagekit") / "configs" / name)


def build_clinic_engine(config_path: str | Path | None = None) -> TriageEngine:
    """Build the reference specialty-clinic engine.

    Args:
        config_path: path to a clinic-shaped YAML config. Defaults to the bundled
            ``configs/clinic.yaml``.
    """
    path = Path(config_path) if config_path else _bundled_config_path("clinic.yaml")
    config = TriageConfig.from_yaml(path)
    return TriageEngine(config, CLINIC_RULES, record_factory=Referral.from_raw)
