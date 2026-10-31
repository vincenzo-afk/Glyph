from indexer import chunk_text


def test_empty_and_whitespace_input_gives_no_chunks():
    assert chunk_text("", 100, 10) == []
    assert chunk_text("   \n\n  ", 100, 10) == []


def test_short_text_is_one_chunk():
    text = "The default timeout is 180 seconds for every batch."
    assert chunk_text(text, 450, 80) == [text]


def test_no_chunk_drops_all_content():
    text = " ".join(f"token{i}." for i in range(300))
    joined = " ".join(chunk_text(text, 120, 0))
    for i in range(300):
        assert f"token{i}." in joined
