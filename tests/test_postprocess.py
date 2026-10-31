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


@pytest.mark.parametrize("raw", [
    {"answer": "6412", "files": ["a.txt"]},      # hallucinated
    {"answer": "", "files": ["a.txt"]},          # never citations without an answer
    {},
])
def test_refusal_shape(raw):
    assert finalize(raw, [chunk("a.txt", "limit 94")], config) == REFUSAL


@pytest.mark.parametrize("text", ["year 1940", "ratio 94.5", "x94"])
def test_support_needs_whole_token(text):
    assert finalize({"answer": "94", "files": ["a"]}, [chunk("a", text)], config) == REFUSAL


def test_decimal_variant_supported():
    assert finalize({"answer": "94.0", "files": ["a"]}, [chunk("a", "limit 94 C")], config)[1] == ["a"]


def test_case_insensitive_support():
    assert finalize({"answer": "rev-c2", "files": ["a"]}, [chunk("a", "Board REV-C2")], config)[0] == "rev-c2"


def test_redundant_file_not_cited():
    top = [chunk("a", "limit 94"), chunk("b", "also 94")]
    assert finalize({"answer": "94", "files": ["a", "b"]}, top, config)[1] == ["a"]


def test_uncited_supporter_repaired():
    top = [chunk("a", "nothing"), chunk("b", "limit 94")]
    assert finalize({"answer": "94", "files": ["a"]}, top, config)[1] == ["b"]


LOG = "incident logged against ORR-1847"
ROW = "ticket: ORR-1847 | fixed_in: 4.3.2\nticket: ORR-1904 | note: 4.3.2 list"


def test_multi_hop_keeps_listed_bridge():
    top = [chunk("x.log", LOG, 9), chunk("bugs.csv", ROW, 1)]
    q = "The log shows an incident. Which release fixed it?"
    raw = {"answer": "4.3.2", "files": ["x.log", "bugs.csv"]}
    assert set(finalize(raw, top, config, q)[1]) == {"x.log", "bugs.csv"}


def test_multi_hop_adds_bridge_the_model_missed():
    top = [chunk("x.log", LOG, 9), chunk("bugs.csv", ROW, 1)]
    raw = {"answer": "4.3.2", "files": ["bugs.csv"]}
    assert set(finalize(raw, top, config, "The log shows an incident. Which release?")[1]) == {"x.log", "bugs.csv"}


def test_single_hop_drops_log_when_ticket_is_in_question():
    # The question already names the ticket: the log is not necessary.
    top = [chunk("x.log", LOG, 9), chunk("bugs.csv", ROW, 1)]
    raw = {"answer": "4.3.2", "files": ["x.log", "bugs.csv"]}
    assert finalize(raw, top, config, "Which version fixed ORR-1847?")[1] == ["bugs.csv"]


def test_unrelated_listed_file_dropped():
    top = [chunk("a", "fan cost is 7"), chunk("b", "limit 94")]
    assert finalize({"answer": "94", "files": ["a", "b"]}, top, config)[1] == ["b"]
