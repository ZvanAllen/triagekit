import math

import pytest

from triagekit.normalize import to_bool, to_int


@pytest.mark.parametrize(
    "value,expected",
    [
        (True, True),
        (False, False),
        ("yes", True),
        ("No", False),
        ("TRUE", True),
        ("0", False),
        ("1", True),
        (1, True),
        (0, False),
        ("NA", None),
        ("", None),
        (None, None),
        ("null", None),
        (float("nan"), None),
        ("maybe", None),  # unrecognized string -> unknown, not False
    ],
)
def test_to_bool(value, expected):
    assert to_bool(value) is expected


@pytest.mark.parametrize(
    "value,expected",
    [(30, 30), ("30", 30), ("30.0", 30), (30.9, 30), (None, None), ("abc", None), ("", None)],
)
def test_to_int(value, expected):
    assert to_int(value) == expected or (to_int(value) is None and expected is None)


def test_nan_is_none_not_false():
    assert to_bool(math.nan) is None
