"""Hosted backend for development, selected with GLYPH_BACKEND=groq.

NOT usable for the graded run: evaluation has no outbound network and rejects
runs under 1 GiB of VRAM. It exists to exercise the pipeline with a real model
on machines without the GPU. The key comes from the environment or an untracked
.env, which is excluded from the image.
"""
from __future__ import annotations
import base64
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

URL = "https://api.groq.com/openai/v1/chat/completions"
TEXT_MODEL = os.environ.get("GLYPH_GROQ_MODEL", "openai/gpt-oss-120b")
VISION_MODEL = os.environ.get("GLYPH_GROQ_VISION_MODEL", "qwen/qwen3.8-27b")
ASK_BUDGET = 25.0       # seconds, inside the 30s per-query budget
VISION_BUDGET = 120.0   # index time: free-tier rate limits are worth waiting out


def _key() -> str:
    key = os.environ.get("GROQ_API_KEY")
    if key:
        return key
    env = Path(__file__).resolve().parents[1] / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("GROQ_API_KEY="):
                return line.split("=", 1)[1].strip()
    raise RuntimeError("GROQ_API_KEY is not set")


def _chat(body: dict, budget: float) -> str:
    deadline = time.time() + budget
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), headers={
        "Authorization": f"Bearer {_key()}", "Content-Type": "application/json",
        "User-Agent": "glyph"})
    while True:
        try:
            left = max(1.0, deadline - time.time())
            with urllib.request.urlopen(req, timeout=left) as resp:
                return json.load(resp)["choices"][0]["message"].get("content") or ""
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:300]
            if e.code not in (429, 500, 502, 503):
                raise RuntimeError(f"groq {e.code}: {detail}") from None
            delay = float(e.headers.get("retry-after") or 2.0)
            if time.time() + delay > deadline:
                raise RuntimeError(f"groq {e.code}, out of budget: {detail}") from None
            print(f"[groq] {e.code}, retrying in {delay}s", file=sys.stderr)
            time.sleep(delay)


def generate(query: str, context: str, max_citations: int) -> str:
    from prompts import EXTRACTION_PROMPT, MODEL_SYSTEM
    prompt = EXTRACTION_PROMPT.format(query=query, context=context, max_c=max_citations)
    return _chat({"model": TEXT_MODEL, "temperature": 0, "max_completion_tokens": 2048,
                  "messages": [{"role": "system", "content": MODEL_SYSTEM},
                               {"role": "user", "content": prompt}]}, ASK_BUDGET)


def vision(image_path) -> str:
    from PIL import Image
    from prompts import VISION_PROMPT
    img = Image.open(image_path).convert("RGB")
    img.thumbnail((2000, 2000))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90)
    url = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    return _chat({"model": VISION_MODEL, "temperature": 0, "max_completion_tokens": 2048,
                  "messages": [{"role": "user", "content": [
                      {"type": "text", "text": VISION_PROMPT},
                      {"type": "image_url", "image_url": {"url": url}}]}]},
                 VISION_BUDGET).strip()
