import json

import indexer
from indexer import BM25, build_index, chunk_text, load_chunks, tokenize


def test_chunk_boundaries():
    chunks = chunk_text("\n\n".join(f"Paragraph number {i} has some words." for i in range(40)), 100, 0)
    assert len(chunks) > 1 and all(len(c) <= 100 for c in chunks)


def test_overlap_never_starts_mid_word():
    words = " ".join(f"word{i}" for i in range(200))
    text = ". ".join(words[i:i + 90] for i in range(0, 900, 90))
    vocab = set(tokenize(text))
    for c in chunk_text(text, 120, 40)[1:]:
        assert c.split()[0].strip(".") in text


def test_overlap_drops_partial_first_word():
    a = "alpha bravo charlie delta echo foxtrot."
    chunks = chunk_text(a + "\n\n" + "golf hotel india juliet kilo lima mike.", 45, 12)
    assert chunks[1].split()[0] in {"echo", "foxtrot."}


def test_bm25_sanity():
    docs = [tokenize("fan assembly part"), tokenize("junction temperature limit"), tokenize("other words")]
    bm = BM25(docs)
    assert bm.score(tokenize("junction"), 1) > bm.score(tokenize("junction"), 0) == 0


def test_manifest_mixed_corpus(corpus, cfg, monkeypatch):
    import daemon_client
    monkeypatch.setattr(daemon_client, "vision_describe", lambda p: "")
    build_index(corpus, cfg)
    m = json.loads(cfg.MANIFEST_PATH.read_text())["files"]
    assert m["notes.txt"]["ok"] and m["specs/sheet_r2.pdf"]["ok"]
    assert not m["blob.dat"]["ok"] and not m["zero.txt"]["ok"]
    assert m["specs/sheet_r1_WITHDRAWN.txt"]["stale"] and m["old_SUPERSEDED.txt"]["stale"]
    assert {c["file"] for c in load_chunks(cfg)} >= {"notes.txt", "bugs.csv", "roadmap.docx", "parts.xlsx"}

