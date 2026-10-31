# Architecture

Glyph answers value-only questions over a mixed-document corpus and reports the
corpus-relative files each answer came from. The work is split into two phases,
because the harness starts a new process for every question.

## Two phases

| Phase | Command | Budget | What happens |
|---|---|---|---|
| Index | `python3 /app/app.py --index /app/corpus` | 10 min, startup | Start the GPU daemon, wait for it, then walk the corpus, extract text, OCR and describe images, chunk, and write the index |
| Query | `python3 /app/app.py --corpus ... --query-id ... --query ...` | 30 s each | Load the index, retrieve chunks, ask the daemon, check the answer, write the output file |

The daemon (`app/daemon.py`) keeps Qwen2.5-VL-7B resident on the GPU behind a unix
socket. A query process is a thin socket client (`app/daemon_client.py`) and never
loads the model.

## Modules

| Module | Role |
|---|---|
| `app/app.py` | CLI entrypoint; `index()`, `answer()`, atomic output writer |
| `app/config.py` | Central settings; paths and limits overridable by `GLYPH_*` environment variables |
| `app/extractors.py` | Per-file text extraction for pdf, docx, xlsx, csv, text and binaries; every failure is recorded, never raised |
| `app/ocr.py` | Tesseract OCR for images |
| `app/indexer.py` | Corpus walk, chunking, BM25 tokens, vision pass, persisted index |
| `app/retrieve.py` | BM25 retrieval plus the identifier hop for multi-hop questions |
| `app/postprocess.py` | Turns model JSON into a contract-grade answer: value check, citation necessity, refusal |
| `app/daemon.py` | GPU model behind a unix socket; single instance per index directory |
| `app/daemon_client.py` | Socket client, respawn policy, cross-process lock |
| `app/groq_backend.py` | Hosted backend for development only (`GLYPH_BACKEND=groq`) |
| `app/prompts.py` | Extraction and vision prompts |

## Answer path

1. Retrieve the top chunks with BM25, then follow identifiers such as `ORR-1847`
   from the top chunks into other files.
2. Send the excerpts, tagged with their file paths, to the model.
3. Parse the first JSON object in the reply (`parse_model_json`).
4. Normalise the value: strip units and degree signs, drop leading articles.
5. Check that the value appears as a whole token in the retrieved text of at least
   one cited file. If not, repair the citation from the retrieved set; if nothing
   supports the value, refuse.
6. Keep only necessary citations: demote withdrawn or superseded files, add bridge
   files that link the question to the answer, and cite one file when several
   each prove the value.
7. Write `<query-id>_output.json` through a temporary file and a rename.

## Failure policy

- A bad file is a manifest entry, not an exception: the walk continues.
- A failed query still writes a refusal, `("", [], 0.0)`, so the output is always well-formed.
- A daemon timeout is never a reason to respawn it; respawning only happens when
  the socket is gone.
