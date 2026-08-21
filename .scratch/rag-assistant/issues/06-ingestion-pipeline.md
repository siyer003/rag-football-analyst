# 06: Ingestion pipeline (`uv run ingest`)

**Status:** ready-for-agent  
**Blocked by:** 03, 04, 05

## What to build

Running `uv run ingest` reads the MatchRegistry, fetches and chunks all data for every listed
match, embeds all chunks, and upserts them to ChromaDB — with structured logging and idempotency.
A developer can add a new match ID to `corpus.toml` and re-run `ingest` to extend the corpus
without touching any other code.

This ticket delivers:

1. **`IngestionPipeline`** in `src/footballanalyst/ingestion/pipeline.py`:
   - Accepts: `MatchRegistry`, `StatsBombFetcher`, `EventSummaryChunker`, `NarrativeFetcher`,
     `NarrativeChunker`, `EmbeddingModel`, `VectorStore`.
   - `run(match_ids: list[int] | None = None)`:
     - If `match_ids` is None, ingests all matches in the registry.
     - For each match: fetch events → chunk → fetch narratives → chunk → embed all chunks →
       upsert to VectorStore.
     - Logs per-match progress: chunks produced, embedding time, upsert count.
     - Skips a match and logs a warning if any fetch step fails; does not abort the whole run.

2. **`ingest` CLI entry point** in `src/footballanalyst/ingestion/cli.py`:
   - Registered as a `[project.scripts]` entry in `pyproject.toml`: `ingest = "footballanalyst.ingestion.cli:main"`.
   - Accepts optional `--match-ids` flag for selective re-ingestion.
   - Wires up all dependencies (real fetchers, real ChromaDB, real embedding model) and calls
     `IngestionPipeline.run()`.
   - Prints a summary: total matches ingested, total chunks stored, total time.

3. **Structured logging** (basic, expanded in ticket 12):
   - `structlog.get_logger()` in pipeline; logs `match_id`, `chunk_count`, `step` at INFO level.
   - Errors logged at ERROR level with the exception, not raised (pipeline continues).

4. **Tests** in `tests/ingestion/test_pipeline.py`:
   - All tests use `FakeEmbeddingModel`, a `FakeVectorStore` (in-memory dict, not ChromaDB),
     and fixture-based fetchers (pre-populated `data/raw/` cache in a `tmp_path`).
   - `test_pipeline_upserts_both_event_and_narrative_chunks` — asserts both chunk types appear
     in the fake store after a run.
   - `test_pipeline_is_idempotent` — running twice on the same match produces the same chunk
     count in the store (no duplicates).
   - `test_pipeline_skips_failed_match_and_continues` — if the fetcher raises for one match_id,
     the pipeline logs and continues to the next match.

## Acceptance criteria

- [ ] `uv run ingest` completes without error for the full 8-match corpus (requires real
      StatsBomb API, so tested manually; CI runs only unit tests).
- [ ] Running `uv run ingest` twice results in the same ChromaDB state (idempotent).
- [ ] `uv run ingest --match-ids 3869685` ingests only the 2022 WC final.
- [ ] All unit tests pass with fake dependencies (no network, no real ChromaDB in CI).
- [ ] `mypy` exits 0.
