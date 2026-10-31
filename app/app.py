#!/usr/bin/env python3
"""Glyph entrypoint. Contract plumbing unchanged:

    python3 /app/app.py --index /app/corpus
    python3 /app/app.py --corpus /app/corpus --query-id query_01 --query "..."

writes /app/output/<query-id>_output.json atomically.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as cfg  # noqa: E402
from indexer import build_index, load_chunks, tokenize  # noqa: E402
from retrieve import retrieve  # noqa: E402
from postprocess import parse_model_json, finalize  # noqa: E402

REFUSAL = ("", [], 0.0)


def index(corpus: Path) -> None:
    import daemon_client
    # The daemon must be up BEFORE build_index(): the vision pass talks to it,
    # and the model has to be resident before the graded clock starts.
    if not daemon_client.ensure_daemon(cfg.DAEMON_WAIT):
        print("[index] WARNING: GPU daemon did not come up; images get OCR only. "
              f"See {cfg.DAEMON_LOG}", file=sys.stderr)
    build_index(corpus, cfg)
    if daemon_client.use_groq():
        return
    try:
        daemon_client._request({"op": "ping"}, wait=5.0)
    except Exception as e:
        print(f"[index] WARNING: daemon ping failed after indexing: {e}", file=sys.stderr)


def answer(corpus: Path, query: str):
    query = (query or "")[:cfg.MAX_QUERY_CHARS]
    if not tokenize(query):                      # "?", "...": nothing to retrieve on
        return REFUSAL
    chunks = load_chunks(cfg)
    if not chunks:
        return REFUSAL
    top = retrieve(chunks, query, cfg)
    if not top:
        return REFUSAL
    print(f"[{query[:60]}] top={[round(c['score'], 2) for c in top[:3]]}", file=sys.stderr)
    # No absolute BM25 gate: score magnitude depends on corpus size and query
    # length. The prompt tells the model to return an empty answer on
    # insufficient evidence, and finalize() refuses unsupported answers.
    context = "\n\n".join(
        f"[FILE: {c['file']}]{' [WITHDRAWN/SUPERSEDED]' if c.get('stale') else ''}\n{c['text']}"
        for c in top)
    import daemon_client
    raw_text = daemon_client.ask(query, context)
    raw = parse_model_json(raw_text)
    return finalize(raw, top, cfg, query)


def write_output(query_id: str, text: str, citations, confidence) -> Path:
    cfg.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = cfg.OUTPUT_DIR / (query_id + "_output.json")
    tmp = out.with_name(f"{out.name}.{os.getpid()}.tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"answer": text, "citations": list(citations),
                       "confidence": confidence}, fh, ensure_ascii=False)
            fh.flush()
            os.fsync(fh.fileno())
        tmp.replace(out)   # atomic: harness never reads a partial file
    finally:
        if tmp.exists():
            tmp.unlink()
    return out

