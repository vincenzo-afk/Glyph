# Troubleshooting

Start with the two logs the container writes:

- `/app/index/daemon.log`: daemon start-up, model load errors, accept failures
- `/app/index/manifest.json`: per-file extraction results and vision notes

## Every answer is a refusal

1. Check `manifest.json`: are the files you expect listed with `"ok": true`?
2. Check `daemon.log`: did the model load? A missing `config.json` stops start-up
   with a message here.
3. Run one query by hand and read stderr. The `top=[...]` line shows the retrieval
   scores; all zeros means the query shares no terms with the corpus.

## An image answer is missing

Images go through OCR and then the vision pass. A blank OCR result is fine; the
vision pass still runs. If `manifest.json` has a `vision_notes` entry for the
image, the model saw it. If not, look for a `vision:` error under `errors`, and
for `[daemon_client] vision failed` in stderr.

## A query is slow or times out

- The first query after `--index` can be slow while the KV cache warms up. Budget
  is 27 s on the client; the harness limit is 30 s.
- Timeouts never respawn the daemon. If you see two daemons, check `pgrep -af daemon.py`
  and that the index directory is the same for both.

## Output is missing or malformed

The output is written through a temporary file and a rename, so a reader never
sees a partial file. If it is missing, the process failed before `write_output`;
check stderr. A failed query still writes a refusal.

## The model directory is incomplete

Run `make check-model`. It names what is missing. Re-run `make fetch` with the
network open.

## Local runs without a GPU

`GLYPH_BACKEND=groq` routes model calls to Groq. Use it for development only: the
evaluation container has no network and must use the local model.
