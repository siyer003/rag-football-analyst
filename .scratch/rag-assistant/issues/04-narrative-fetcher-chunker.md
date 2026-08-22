# 04: Narrative fetcher + NarrativeChunk chunker

**Status:** closed  
**Blocked by:** 01, 02

## What to build

A developer can call the narrative fetcher with a `match_id` and receive a list of `NarrativeChunk`
objects from up to three sources (Guardian API, Wikipedia, StatsBomb blog) — without any vector
store involved. Sources are fetched once and cached to disk; the chunker is re-runnable from cache.

This ticket delivers:

1. **`NarrativeFetcher`** in `src/footballanalyst/ingestion/narrative_fetcher.py`:
   - Three source sub-fetchers:
     - **Guardian**: searches the Guardian API (`GUARDIAN_API_KEY` env var) for articles matching
       the match label + competition. Fetches article body text. Gracefully skips if key not set.
     - **Wikipedia**: fetches the Wikipedia article for the match (URL pattern: match label →
       search Wikipedia API). Uses `httpx` + `beautifulsoup4` to extract article body.
     - **StatsBomb blog**: fetches known StatsBomb blog post URLs for the match (a small
       hard-coded or config-driven URL map per match in `corpus.toml`).
   - Each fetcher writes raw text to `data/raw/<match_id>/<source>.txt`.
   - On re-run: if the file already exists, loads from disk (no HTTP request). Cache-first.
   - HTTP calls use `httpx` with a timeout; failures are logged and skipped (best-effort —
     the match still ingests with partial narrative).

2. **`NarrativeChunker`** in `src/footballanalyst/ingestion/narrative_chunker.py`:
   - Takes raw text per source and produces `list[NarrativeChunk]` via sliding-window paragraph
     splitting (target: 150–250 tokens per chunk, 20% overlap between consecutive chunks).
   - Each `NarrativeChunk` has: `match_id`, `chunk_type="narrative"`, `source`
     (guardian|wikipedia|statsbomb_blog), `url`, `text`, deterministic `chunk_id`.
   - `chunk_id` = `sha256(match_id + source + text[:100])` truncated to 16 hex chars.

3. **Mock HTTP fixtures** in `tests/fixtures/narrative/`:
   - Pre-saved `.txt` files for one match per source, used as cache files in tests.
   - Tests pre-populate `data/raw/<match_id>/` from fixtures; fetcher reads from disk.

4. **Tests** in `tests/ingestion/test_narrative_chunker.py`:
   - `test_chunker_produces_chunks_from_fixture_text` — given fixture text, asserts at least
     3 NarrativeChunks are produced.
   - `test_chunk_has_required_fields` — asserts `chunk_id`, `match_id`, `source`, `text` present.
   - `test_chunk_ids_are_deterministic` — same input yields same IDs.
   - `test_fetcher_uses_cache_if_raw_file_exists` — pre-creates cache file; asserts no HTTP
     call is made (mock `httpx` with `pytest-httpx` or similar).
   - No test makes real HTTP calls.

## Acceptance criteria

- [x] `NarrativeFetcher` skips Guardian gracefully when `GUARDIAN_API_KEY` is not set, without
      raising an exception.
- [x] On second run, fetcher reads from `data/raw/<match_id>/<source>.txt` without making HTTP
      requests.
- [x] `NarrativeChunker` produces chunks of ≤ 300 tokens each.
- [x] All `NarrativeChunk.chunk_id` values are unique within a match.
- [x] All tests pass offline (no real HTTP calls in test suite).
- [x] `mypy` exits 0.

