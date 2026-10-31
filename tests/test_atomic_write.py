import json

import indexer


def test_atomic_write_replaces_content_and_leaves_no_tmp(tmp_path):
    target = tmp_path / "manifest.json"
    target.write_text("old")
    indexer._atomic_write(target, json.dumps({"ok": True}))
    assert json.loads(target.read_text()) == {"ok": True}
    assert not (tmp_path / "manifest.json.tmp").exists()


def test_atomic_write_creates_new_file(tmp_path):
    target = tmp_path / "chunks.jsonl"
    indexer._atomic_write(target, "line\n")
    assert target.read_text() == "line\n"
