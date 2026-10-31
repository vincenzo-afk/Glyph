import pytest

from extractors import _looks_textual


@pytest.mark.parametrize("raw,want", [
    (b"plain ascii text with numbers 94 and 180\n", True),
    ("café au lait".encode("utf-8"), True),
    (b"\xff\xfeH\x00i\x00", True),                 # UTF-16 LE BOM
    (b"\xef\xbb\xbfhello", True),                  # UTF-8 BOM
    (bytes(range(256)), False),                    # binary soup
    (b"abc\x00def", False),                        # NUL means binary
    (b"", False),
])
def test_looks_textual(raw, want):
    assert _looks_textual(raw) is want
