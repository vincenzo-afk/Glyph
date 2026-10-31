import pytest

import config
from postprocess import finalize, normalize_answer

REFUSAL = ("", [], 0.0)


def chunk(file, text, score=5.0, stale=False):
    return {"file": file, "text": text, "score": score, "stale": stale}


@pytest.mark.parametrize("raw,want", [
    ("94 C", "94"), ("94°C", "94"), ("94 degrees", "94"), (" 94 ", "94"),
    ("The 94", "94"), ("94.0", "94.0"), ("180 seconds", "180"), ("180s", "180"),
    ("94 C", "94"), ("Q3 FY27", "Q3 FY27"), ("4.3.2", "4.3.2"),
    ("ORR-FAN-2214-B", "ORR-FAN-2214-B"),
])
def test_normalize(raw, want):
    assert normalize_answer(raw) == want


def test_pdf_sourced_answer_passes():
    # Regression P0-2: evidence is chunk text, never the raw binary.
    top = [chunk("specs/r2.pdf", "Maximum junction temperature .... 94 C")]
    a, c, conf = finalize({"answer": "94 C", "files": ["specs/r2.pdf"]}, top, config)
    assert (a, c) == ("94", ["specs/r2.pdf"]) and conf > 0


def test_stale_demoted():
    top = [chunk("r1_WITHDRAWN.pdf", "limit 94", stale=True), chunk("r2.pdf", "limit 94")]
    assert finalize({"answer": "94", "files": ["r1_WITHDRAWN.pdf", "r2.pdf"]}, top, config)[1] == ["r2.pdf"]


def test_stale_kept_when_only_support():
    top = [chunk("r1_WITHDRAWN.pdf", "limit 94", stale=True)]
    assert finalize({"answer": "94", "files": ["r1_WITHDRAWN.pdf"]}, top, config)[1] == ["r1_WITHDRAWN.pdf"]


