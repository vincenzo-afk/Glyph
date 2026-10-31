#!/usr/bin/env python3
"""Check that the local VL model directory is complete before building the image.

    python3 scripts/check_model.py [models/qwen2_5-vl-7b-instruct]

Exits 1 and names what is missing. The daemon refuses to start on a missing
config.json; this catches the rest (weights, tokenizer, processor) at build time.
"""
from __future__ import annotations

import sys
from pathlib import Path

REQUIRED = ["config.json"]
TOKENIZER_ANY = [["tokenizer.json", "vocab.json"]]
PROCESSOR_ANY = [["preprocessor_config.json", "processor_config.json"]]
WEIGHTS_GLOB = "*.safetensors"


def missing(model_dir: Path) -> list:
    problems = []
    if not model_dir.is_dir():
        return [f"directory {model_dir} does not exist"]
    for name in REQUIRED:
        if not (model_dir / name).is_file():
            problems.append(name)
    for group in TOKENIZER_ANY + PROCESSOR_ANY:
        if not any((model_dir / n).is_file() for n in group):
            problems.append(" or ".join(group))
    shards = sorted(model_dir.glob(WEIGHTS_GLOB))
    if not shards:
        problems.append(WEIGHTS_GLOB)
    else:
        empty = [s.name for s in shards if s.stat().st_size == 0]
        if empty:
            problems.append(f"empty weight shard(s): {', '.join(empty)}")
    return problems


def main(argv: list) -> int:
    here = Path(__file__).resolve().parents[1]
    target = Path(argv[1]) if len(argv) > 1 else here / "models" / "qwen2_5-vl-7b-instruct"
    problems = missing(target)
    if problems:
        print(f"model incomplete at {target}:", file=sys.stderr)
        for p in problems:
            print(f"  - missing {p}", file=sys.stderr)
        print("run scripts/fetch_model.sh with the network open", file=sys.stderr)
        return 1
    size = sum(p.stat().st_size for p in target.rglob("*") if p.is_file())
    print(f"model complete at {target} ({size / 2**30:.1f} GiB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
