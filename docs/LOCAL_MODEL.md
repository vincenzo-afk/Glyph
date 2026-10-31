# Local model

The submitted image runs Qwen2.5-VL-7B-Instruct locally, in bf16, on the AMD GPU.
Weights are downloaded once at build time and copied into the image; the
container has no network during grading.

## Get the weights

```
make fetch           # needs the network; writes models/qwen2_5-vl-7b-instruct/
make check-model     # fails and names anything missing
```

`check-model` verifies `config.json`, a tokenizer file, a processor config, and
non-empty `*.safetensors` shards. `make build` runs it first, so an incomplete
download fails before Docker starts.

## Where it is used

| Setting | Default | Meaning |
|---|---|---|
| `GLYPH_MODEL` | `/models/qwen2_5-vl-7b-instruct` | Directory `daemon.py` loads |
| `GLYPH_BACKEND` | `local` | `local` uses the daemon; `groq` is development-only |

The daemon checks for `config.json` at start-up and exits with a message if it is
missing, so a bad path shows up in `daemon.log` rather than as an empty answer.

## Sizing

The mandated base image is about 29.2 GiB. The bf16 weights add about 16 GiB, which
keeps the image under the 60 GiB limit. Peak VRAM must stay between 1 and 48 GiB;
below the floor means the model ran on the CPU.

## Running it

The daemon starts during `--index`, before the graded clock. Each query then
reuses it. To run the daemon by hand:

```
GLYPH_INDEX_DIR=/tmp/glyph-index python3 app/daemon.py
```

A second daemon on the same index directory exits immediately, because it cannot
take the lock in `daemon.lock`.
