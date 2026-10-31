"""BM25 retrieval + entity hop.

The hop serves multi-hop questions: a top chunk names an identifier (a ticket
id, say) the question does not, and the chunk that resolves it may share no
terms with the question. Chunks holding that identifier are pulled in.
"""
from __future__ import annotations
import re

from indexer import BM25, tokenize

ENTITY_RE = re.compile(r"\b[A-Z][A-Z0-9]*-\d[A-Za-z0-9-]*\b")
HOP_SEEDS = 5           # top chunks whose identifiers are followed
HOP_MAX_CHUNKS = 3      # extra chunks a hop may add
HOP_MAX_FILES = 3       # an id in more files than this is a product name, not a link


def entities(text: str) -> set:
    return set(ENTITY_RE.findall(text or ""))


def retrieve(chunks: list, query: str, cfg) -> list:
    q = tokenize(query)
    if not chunks or not q:
        return []
    bm = BM25([c.get("tokens") or [] for c in chunks])
    scored = [dict(c, score=bm.score(q, i)) for i, c in enumerate(chunks)]
    ranked = sorted(scored, key=lambda c: -c["score"])
    top = [c for c in ranked[:cfg.TOP_K] if c["score"] > 0]
    if not top:
        return []

    in_query = {e.upper() for e in entities(query)}
    present = {(c["file"], c["idx"]) for c in top}
    added = 0
    for seed in top[:HOP_SEEDS]:
        for ent in sorted(entities(seed["text"])):
            if ent.upper() in in_query:
                continue
            holders = [c for c in ranked if ent in c["text"]]
            if len({c["file"] for c in holders}) > HOP_MAX_FILES:
                continue
            for c in holders:
                key = (c["file"], c["idx"])
                if key not in present and c["file"] != seed["file"] and added < HOP_MAX_CHUNKS:
                    top.append(c)
                    present.add(key)
                    added += 1
    return top
