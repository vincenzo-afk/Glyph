"""Turn raw model JSON into a contract-grade answer.

- value-only normalization (units/degree signs stripped per the contract)
- citation necessity: every citation must be from the retrieved set and
  non-stale unless it is the only support
- support check: the answer token must literally appear in the retrieved
  CHUNK TEXT of >=1 cited file (chunks are already extracted text, so this
  works for pdf/docx/xlsx/images too); if not, repair citations from the
  retrieved set, else refuse
- honest refusal: weak evidence => empty answer AND empty citations
"""
from __future__ import annotations
import json
import re

UNIT_RE = re.compile(r"^([+-]?[\d.,]+)\s*(?:[°°]?\s*[Cc]|\s*degrees?|\s*seconds?|\s*s)$")
WS_RE = re.compile(r"\s+")
REFUSAL = ("", [], 0.0)


def parse_model_json(text: str) -> dict:
    """First `{` that starts a valid JSON object wins; trailing prose is ignored."""
    dec = json.JSONDecoder()
    text = text or ""
    pos = text.find("{")
    while pos != -1:
        try:
            obj, _ = dec.raw_decode(text, pos)
            if isinstance(obj, dict):
                return obj
        except ValueError:
            pass
        pos = text.find("{", pos + 1)
    return {}


def normalize_answer(ans: str) -> str:
    a = WS_RE.sub(" ", (ans or "").strip()).strip('"').strip("'")
    a = re.sub(r"^(?:the|a|an)\s+", "", a, flags=re.I).strip(" .")
    m = UNIT_RE.match(a)
    if m:                       # "94 C", "94°C", "180 seconds" -> bare value
        return m.group(1)
    return a


def _norm_text(s: str) -> str:
    return WS_RE.sub(" ", s.lower())


def _variants(token: str) -> list:
    """'94.0' and '94' should match each other in the evidence."""
    out = [token]
    if re.fullmatch(r"[+-]?\d+\.0+", token):
        out.append(token.split(".")[0])
    elif re.fullmatch(r"[+-]?\d+", token):
        out.append(token + ".0")
    return out


def _pattern(v: str) -> str:
    # Whole token: "94" must not match "1940" or "94.5", "4.3.2" not "4.3.2.1".
    return r"(?<![a-z0-9])(?<!\d\.)" + re.escape(v) + r"(?![a-z0-9]|\.\d)"


def _contains(text: str, variants: list) -> bool:
    return any(v and re.search(_pattern(v), text) for v in variants)


def _bridges(answer_files: list, listed: list, retrieved: list, variants: list,
             stale: set, query: str) -> list:
    """Multi-hop: files that do not hold the value but link the question to it.

    A bridge shares an identifier with the line holding the answer, and that
    identifier is not in the question (else the question reached the answer
    directly). It must also be listed by the model or out-rank the answer file
    for this question, i.e. be the route by which the question got there.
    """
    from retrieve import entities
    asked = {e.upper() for e in entities(query)}
    links, best = set(), {}
    for c in retrieved:
        best[c["file"]] = max(best.get(c["file"], 0.0), c.get("score", 0.0))
        if c["file"] in answer_files:
            for line in c.get("text", "").splitlines():
                if _contains(_norm_text(line), variants):
                    links |= {e for e in entities(line) if e.upper() not in asked}
    top_answer = max((best.get(f, 0.0) for f in answer_files), default=0.0)
    out = []
    for c in retrieved:
        f = c["file"]
        if (f in answer_files or f in out or f in stale
                or not links & entities(c.get("text", ""))):
            continue
        if f in listed or best[f] > top_answer:
            out.append(f)
    return out

