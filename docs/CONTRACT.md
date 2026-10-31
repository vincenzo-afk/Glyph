# Contract map

Each rule from the Mini-Challenge 3 submission contract, and where the code enforces it.

| Rule | Enforced in | Test |
|---|---|---|
| `--index` then `--query` invocations with the given query id | `app/app.py:main` | `tests/test_pipeline.py::test_answerable` |
| Output at `/app/output/<query-id>_output.json` | `app/app.py:write_output` | `tests/test_pipeline.py::test_same_query_id_twice_overwrites` |
| Output written atomically (temp file, fsync, rename) | `app/app.py:write_output` | `tests/test_pipeline.py::test_failed_write_leaves_previous_output_intact` |
| Object with string `answer`, list `citations`, number `confidence` | `app/app.py:write_output` | `tests/test_pipeline.py::test_answerable` |
| Refusal is `("", [], 0.0)`, never prose | `app/postprocess.py:REFUSAL`, `finalize` | `tests/test_postprocess.py::test_refusal_shape` |
| Citations are corpus-relative paths | `app/indexer.py` (paths from `relative_to`) | `tests/test_pipeline.py::test_citation_outside_retrieved_is_dropped` |
| Citations are necessary, not relevant | `app/postprocess.py:finalize`, `_bridges` | `tests/test_postprocess.py::test_redundant_file_not_cited` |
| Withdrawn and superseded files are not cited unless they are the only support | `app/extractors.py:_mark_stale`, `finalize` | `tests/test_postprocess.py::test_stale_demoted` |
| Per-file failures are data, never an abort | `app/extractors.py:extract_file` | `tests/test_extractors.py::test_empty_and_binary` |
| Model is resident before the graded clock starts | `app/app.py:index`, `app/daemon_client.py:ensure_daemon` | `tests/test_pipeline.py::test_daemon_is_up_before_the_vision_pass` |
| Query processes never load the model | `app/daemon_client.py:ask` | `tests/test_daemon_client.py::test_no_respawn_on_timeout` |
| No network at query time | Local model only; Groq is opt-in | `docs/LOCAL_MODEL.md` |
| Model weights ship in the image | `Dockerfile` (`COPY models/`), `make check-model` | `tests/test_check_model.py` |

Not verifiable on this machine: GPU use, the 30 s budget on real hardware, the
image size, and running without `DAC_OVERRIDE`. See `docs/TROUBLESHOOTING.md`.
