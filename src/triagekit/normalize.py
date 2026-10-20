"""Value coercion helpers.

Intake data arrives from CSV exports, spreadsheets, and EMR dumps where a
boolean might be ``True``, ``"yes"``, ``"1"``, ``"NA"``, ``""`` or a NaN float.
These helpers collapse that variety into ``bool | None`` / ``int | None`` so the
rules never have to think about representation.
"""

from __future__ import annotations

from typing import Any

_TRUE = {"true", "yes", "1"}
_FALSE = {"false", "no", "0"}
_NULLISH = {"na", "none", "null", "nan", ""}


def to_bool(val: Any) -> bool | None:
    """Convert a loose value to ``True``/``False``/``None`` (unknown).

    ``None`` means "unknown / not asked" and is deliberately distinct from
    ``False`` — several rules branch on that difference.
    """
    if val is None:
        return None
    if isinstance(val, float) and val != val:  # NaN
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        v = val.strip().lower()
        if v in _TRUE:
            return True
        if v in _FALSE:
            return False
        if v in _NULLISH:
            return None
        return None
    if isinstance(val, (int, float)):
        return bool(val)
    return None


def to_int(val: Any) -> int | None:
    """Convert a loose value to an int, or ``None`` if it cannot be parsed."""
    if val is None:
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None
