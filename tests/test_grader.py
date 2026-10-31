import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "grade_local.py"


@pytest.fixture(scope="module")
def grader():
    spec = importlib.util.spec_from_file_location("grade_local", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("raw,want", [
    ("94 C", "94"),
    ("94°C", "94"),
    ("180 seconds", "180"),
    ("  Q3 FY27 ", "q3 fy27"),
    ("", ""),
])
def test_norm_matches_contract_units(grader, raw, want):
    assert grader.norm(raw) == want
