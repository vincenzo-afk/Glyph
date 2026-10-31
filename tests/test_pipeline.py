"""End-to-end through app.main() with the GPU daemon faked: --index, then --query."""
import json
import sys

import pytest

import app as app_mod
import daemon_client
from conftest import KIT


@pytest.fixture
def daemon_up(monkeypatch):
    calls = []
    monkeypatch.setattr(daemon_client, "ensure_daemon", lambda wait: calls.append("up") or True)
    monkeypatch.setattr(daemon_client, "_request", lambda *a, **k: {"ok": True})
    monkeypatch.setattr(daemon_client, "vision_describe", lambda p: "")
    return calls


def run(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["app.py", *argv])
    return app_mod.main()


def query(monkeypatch, cfg, corpus, q, model_reply=None):
    seen = {}
    def ask(query, context):
        seen["context"] = context
        return model_reply
    monkeypatch.setattr(daemon_client, "ask", ask)
    assert run(monkeypatch, "--corpus", str(corpus), "--query-id", "q1", "--query", q) == 0
    return json.loads((cfg.OUTPUT_DIR / "q1_output.json").read_text(encoding="utf-8")), seen


def test_daemon_is_up_before_the_vision_pass(tmp_path, cfg, monkeypatch):
    # Regression P0-1.
    order = []
    monkeypatch.setattr(daemon_client, "ensure_daemon", lambda w: order.append("daemon") or True)
    monkeypatch.setattr(daemon_client, "_request", lambda *a, **k: {"ok": True})
    monkeypatch.setattr(app_mod, "build_index", lambda c, f: order.append("index"))
    run(monkeypatch, "--index", str(tmp_path))
    assert order == ["daemon", "index"]


def test_answerable(corpus, cfg, daemon_up, monkeypatch):
    run(monkeypatch, "--index", str(corpus))
    reply = '{"answer": "94 C", "files": ["specs/sheet_r2.pdf"], "why": "x"} trailing prose'
    out, seen = query(monkeypatch, cfg, corpus, "What is the maximum junction temperature?", reply)
    assert out["answer"] == "94" and out["citations"] == ["specs/sheet_r2.pdf"]
    assert "[FILE: specs/sheet_r2.pdf]" in seen["context"]
    assert "[WITHDRAWN/SUPERSEDED]" in seen["context"]
    assert not list(cfg.OUTPUT_DIR.glob("*.tmp"))


def test_unanswerable_refusal_shape(corpus, cfg, daemon_up, monkeypatch):
    run(monkeypatch, "--index", str(corpus))
    out, _ = query(monkeypatch, cfg, corpus, "What is the maximum junction temperature?",
                   '{"answer": "", "files": []}')
    assert out == {"answer": "", "citations": [], "confidence": 0.0}


def test_citation_outside_retrieved_is_dropped(corpus, cfg, daemon_up, monkeypatch):
    run(monkeypatch, "--index", str(corpus))
    out, _ = query(monkeypatch, cfg, corpus, "What is the maximum junction temperature?",
                   '{"answer": "94", "files": ["/etc/passwd"]}')
    assert out["citations"] == ["specs/sheet_r2.pdf"]


@pytest.mark.parametrize("q", ["?", "...", ""])
def test_tokenless_query_refuses_without_model(corpus, cfg, daemon_up, monkeypatch, q):
    run(monkeypatch, "--index", str(corpus))
    out, seen = query(monkeypatch, cfg, corpus, q)
    assert out["answer"] == "" and not seen


def test_very_long_query(corpus, cfg, daemon_up, monkeypatch):
    run(monkeypatch, "--index", str(corpus))
    out, seen = query(monkeypatch, cfg, corpus, "junction " * 20000, '{"answer": ""}')
    assert out["citations"] == [] and seen


def test_daemon_failure_still_writes_refusal(corpus, cfg, daemon_up, monkeypatch):
    run(monkeypatch, "--index", str(corpus))
    def boom(q, c):
        raise TimeoutError
    monkeypatch.setattr(daemon_client, "ask", boom)
    run(monkeypatch, "--corpus", str(corpus), "--query-id", "q1", "--query", "junction temperature")
    assert json.loads((cfg.OUTPUT_DIR / "q1_output.json").read_text())["answer"] == ""


def test_query_before_index_refuses(tmp_path, cfg, monkeypatch):
    run(monkeypatch, "--corpus", str(tmp_path), "--query-id", "q1", "--query", "anything")
    assert json.loads((cfg.OUTPUT_DIR / "q1_output.json").read_text())["answer"] == ""


def test_same_query_id_twice_overwrites(cfg):
    app_mod.write_output("q", "1", [], 0.5)
    app_mod.write_output("q", "2", [], 0.5)
    assert json.loads((cfg.OUTPUT_DIR / "q_output.json").read_text())["answer"] == "2"


def test_failed_write_leaves_previous_output_intact(cfg, monkeypatch):
    app_mod.write_output("q", "good", [], 0.5)
    def die(*a):
        raise OSError("disk")
    monkeypatch.setattr(app_mod.os, "fsync", die)
    with pytest.raises(OSError):
        app_mod.write_output("q", "bad", [], 0.5)
    assert json.loads((cfg.OUTPUT_DIR / "q_output.json").read_text())["answer"] == "good"
    assert not list(cfg.OUTPUT_DIR.glob("*.tmp"))


def test_readonly_output_returns_error_not_traceback(corpus, cfg, daemon_up, monkeypatch):
    run(monkeypatch, "--index", str(corpus))
    monkeypatch.setattr(daemon_client, "ask", lambda q, c: "{}")
    def deny(*a, **k):
        raise PermissionError
    monkeypatch.setattr(app_mod, "write_output", deny)
    assert run(monkeypatch, "--corpus", str(corpus), "--query-id", "q", "--query", "junction") == 1


# --- The kit's real corpus and questions, with the model replaced by an oracle.
# This scores everything EXCEPT model quality: parsing, retrieval, hop, citations.
# Vision text is stubbed with the values the model must read off the two images.
VISION = {"backplane_pinout.png": "Backplane pinout TQ-40: pin B14 THERM_ALERT#",
          "asset_label.jpg": "Asset label: board revision REV-C2"}
SAMPLE = None
if (KIT / "sample-questions.json").exists():
    SAMPLE = json.loads((KIT / "sample-questions.json").read_text(encoding="utf-8"))["queries"]


@pytest.fixture
def kit_chunks(cfg, monkeypatch, fake_tesseract):
    if SAMPLE is None:
        pytest.skip("starter kit not present")
    monkeypatch.setattr(daemon_client, "vision_describe",
                        lambda p: VISION.get(p.name, ""))
    app_mod.build_index(KIT / "mc3-corpus", cfg)
    return cfg


@pytest.mark.parametrize("n", range(1, 11))
@pytest.mark.parametrize("cite_all", [False, True], ids=["model-exact", "model-overcites"])
def test_kit_questions_with_oracle_model(kit_chunks, monkeypatch, n, cite_all):
    q = next(x for x in SAMPLE if x["n"] == n)
    seen = {}
    def oracle(query, context):
        seen["context"] = context
        files = q["expected_citations"]
        if cite_all:
            import re
            files = re.findall(r"\[FILE: ([^\]]+)\]", context)
        return json.dumps({"answer": q["expected_answer"], "files": files})
    monkeypatch.setattr(daemon_client, "ask", oracle)
    a, cites, _ = app_mod.answer(KIT / "mc3-corpus", q["query"])
    assert a == q["expected_answer"]
    assert set(cites) == set(q["expected_citations"])


@pytest.mark.parametrize("n", [1, 2, 3, 4, 5, 6, 7, 8, 9])
def test_kit_evidence_reaches_the_model(kit_chunks, monkeypatch, n):
    q = next(x for x in SAMPLE if x["n"] == n)
    seen = {}
    monkeypatch.setattr(daemon_client, "ask", lambda query, c: seen.update(c=c) or "{}")
    app_mod.answer(KIT / "mc3-corpus", q["query"])
    for f in q["expected_citations"]:
        assert f"[FILE: {f}]" in seen["c"]
    assert q["expected_answer"] in seen["c"]
