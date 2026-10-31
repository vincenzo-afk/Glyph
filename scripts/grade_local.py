#!/usr/bin/env python3
"""Score the sample questions against any corpus, no Docker needed:
   python3 scripts/grade_local.py /path/to/mc3-corpus [questions.json]
"""
from __future__ import annotations
import json
import os
import sys
import tempfile
from pathlib import Path

# A private index dir, set BEFORE importing config: the daemon is a subprocess
# and only sees the environment, so patching cfg in-process would split the
# client and the daemon onto different sockets.
_td = tempfile.TemporaryDirectory()
os.environ["GLYPH_INDEX_DIR"] = _td.name
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
import config as cfg  # noqa: E402
import app as app_mod  # noqa: E402


def norm(s: str) -> str:
    s = (s or "").strip().lower().replace("\u00b0", "")
    for u in (" c", " degrees", " seconds", "s"):
        if s.endswith(u):
            s = s[: -len(u)]
    return " ".join(s.split())


def main() -> int:
    corpus = Path(sys.argv[1])
    qfile = Path(sys.argv[2]) if len(sys.argv) > 2 else \
        Path(__file__).resolve().parents[1].parent / "mc3-starter-kit" / "sample-questions.json"
    qs = json.loads(qfile.read_text(encoding="utf-8"))["queries"]

    try:
        app_mod.index(corpus)

        score = 0
        for q in qs:
            a, cites, conf = app_mod.answer(corpus, q["query"])
            if q.get("unanswerable"):
                ok_a = (a == "")
            else:
                ok_a = norm(a) == norm(q["expected_answer"]) or \
                       norm(a) in {norm(x) for x in q.get("answer_aliases", [])}
            ok_c = set(cites) == set(q["expected_citations"])
            good = ok_a and ok_c
            score += 20 if good else 0
            print(f"Q{q['n']:>2} {'PASS' if good else 'FAIL'}  ans={a!r:>16} "
                  f"cites={cites} conf={conf}  ({q['category']})")
        print(f"\nSCORE: {score}/200")
    finally:
        import daemon_client
        try:                        # leave no daemon behind on the GPU
            daemon_client._request({"op": "shutdown"}, wait=0.0)
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
