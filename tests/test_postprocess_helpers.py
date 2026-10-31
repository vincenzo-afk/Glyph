import pytest

from postprocess import _contains, _variants


@pytest.mark.parametrize("token,want", [
    ("94", ["94", "94.0"]),
    ("94.0", ["94.0", "94"]),
    ("4.3.2", ["4.3.2"]),
    ("orr-1847", ["orr-1847"]),
])
def test_variants(token, want):
    assert _variants(token) == want


@pytest.mark.parametrize("text,token,hit", [
    ("limit 94 c", "94", True),
    ("limit 94.0 c", "94", True),         # "94" and "94.0" are the same value
    ("limit 94.0 c", "94.0", True),
    ("year 1940", "94", False),
    ("ratio 94.5", "94", False),
    ("fixed in 4.3.2.", "4.3.2", True),   # sentence full stop is fine
    ("fixed in 4.3.2.1", "4.3.2", False),
])
def test_whole_token_matching(text, token, hit):
    assert _contains(text, _variants(token)) is hit


def test_pattern_escapes_regex_metacharacters():
    assert _contains("part orr-fan+2214", _variants("orr-fan+2214"))
    assert not _contains("part orr-fanx2214", _variants("orr-fan+2214"))
