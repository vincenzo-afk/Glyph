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

