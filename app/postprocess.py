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

