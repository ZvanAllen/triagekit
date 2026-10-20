"""Make `triagekit` importable from src without installing (convenience for
local `pytest`; CI installs the package with `pip install -e .`)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
