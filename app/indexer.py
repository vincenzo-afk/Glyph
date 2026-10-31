"""Resilient corpus walk + chunking + BM25 index, persisted to INDEX_DIR.

Heavy work (parsing, OCR, vision descriptions) happens HERE, inside the
startup budget -- not inside the 30s per-question clock.
"""
from __future__ import annotations
import json
import math
import re
from collections import Counter
from pathlib import Path

TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(s: str) -> list:
    return TOKEN_RE.findall(s.lower())


def chunk_text(text: str, target: int, overlap: int) -> list:
    """Split on paragraph/line boundaries where possible."""
    blocks = re.split(r"(?:\n\s*\n|(?<=[.;:])\s+\n?)", text)
    chunks, cur = [], ""
    for b in blocks:
        b = b.strip()
        if not b:
            continue
        if len(cur) + len(b) + 1 > target and cur:
            chunks.append(cur)
            tail = cur[-overlap:] if overlap else ""
            sp = tail.find(" ")
            tail = tail[sp + 1:] if sp > 0 else tail      # never start mid-word
            cur = (tail + " " + b).strip() if tail else b
        else:
            cur = (cur + " " + b).strip()
    if cur.strip():
        chunks.append(cur)
    return [c for c in chunks if len(c.strip()) > 20] or ([text[:target]] if text.strip() else [])


class BM25:
    def __init__(self, docs: list):
        self.docs = docs
        self.df = Counter()
        for d in docs:
            for t in set(d):
                self.df[t] += 1
        self.n = len(docs)
        self.avgdl = sum(len(d) for d in docs) / max(1, self.n)
        self.k1, self.b = 1.5, 0.75

    def idf(self, t: str) -> float:
        return math.log(1 + (self.n - self.df[t] + 0.5) / (self.df[t] + 0.5))

    def score(self, q: list, i: int) -> float:
        d = self.docs[i]
        if not d:
            return 0.0
        tf = Counter(d)
        dl = len(d)
        s = 0.0
        for t in q:
            f = tf.get(t, 0)
            if f:
                s += self.idf(t) * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
        return s


def build_index(corpus: Path, cfg) -> None:
    import extractors
    cfg.INDEX_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {"files": {}, "errors": [], "vision_notes": {}}

    chunks_meta = []
    for p in sorted(corpus.rglob("*")):
        if not p.is_file():
            continue
        res = extractors.extract_file(p, corpus, cfg)
        manifest["files"][res.path] = {"ok": res.ok, "stale": res.stale,
                                       "error": res.error}
        if not res.ok:
            manifest["errors"].append({"path": res.path, "error": res.error})
            continue
        for i, c in enumerate(chunk_text(res.text, cfg.CHUNK_TARGET, cfg.CHUNK_OVERLAP)):
            chunks_meta.append({"file": res.path, "stale": res.stale,
                                "idx": i, "text": c, "tokens": tokenize(c)})

    # Vision pass over EVERY image, including those whose OCR failed (blurry
    # scans, text-free diagrams): the VL model is the fallback for exactly them.
    imgs = [f for f in manifest["files"]
            if Path(f).suffix.lower() in cfg.IMAGE_SUFFIXES]
    if imgs:
        from daemon_client import vision_describe
        for rel in imgs:
            try:
                note = vision_describe(corpus / rel)
            except Exception as e:
                manifest["errors"].append({"path": rel, "error": f"vision: {e}"})
                continue
            if note:
                manifest["vision_notes"][rel] = note
                for i, c in enumerate(chunk_text("Image content: " + note,
                                                 cfg.CHUNK_TARGET, cfg.CHUNK_OVERLAP)):
                    stale = extractors._mark_stale(rel, note, cfg.STALE_MARKERS)
                    chunks_meta.append({"file": rel, "stale": stale, "idx": 1000 + i,
                                        "text": c, "tokens": tokenize(c)})

    # Write via tmp + rename so re-running --index never leaves half a file.
    _atomic_write(cfg.CHUNKS_PATH, "".join(
        json.dumps(c, ensure_ascii=False) + "\n" for c in chunks_meta))
    _atomic_write(cfg.MANIFEST_PATH, json.dumps(manifest, ensure_ascii=False, indent=1))


def _atomic_write(path: Path, data: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(data, encoding="utf-8")
    tmp.replace(path)


def load_chunks(cfg) -> list:
    out = []
    with open(cfg.CHUNKS_PATH, encoding="utf-8") as fh:
        for line in fh:
            out.append(json.loads(line))
    return out
