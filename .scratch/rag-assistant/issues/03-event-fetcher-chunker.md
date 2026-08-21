# 03: StatsBomb event fetcher + EventSummary chunker

**Status:** ready-for-agent  
**Blocked by:** 01

## What to build

A developer can call the event fetcher with a `match_id` and receive a list of `EventSummary`
objects — text chunks representing analytical windows of the match (pressing phases, xG by period,
formation changes) — without any vector store or LLM involved.

This ticket delivers:

1. **`StatsBombFetcher`** in `src/footballanalyst/ingestion/statsbomb_fetcher.py`:
   - Uses `statsbombpy` to fetch raw events for a given `match_id`.
   - Fetches match metadata (home/away team, score, competition, managers, lineups).
   - Returns a structured `RawMatchData` dataclass with events DataFrame + metadata.
   - Cacheable: if `data/raw/<match_id>/events.json` already exists, loads from disk instead of
     hitting the API. Writes to disk on first fetch.

2. **`EventSummaryChunker`** in `src/footballanalyst/ingestion/event_chunker.py`:
   - Takes a `RawMatchData` and produces `list[EventSummary]`.
   - Analytical windows to produce (at minimum):
     - Per-period pressing intensity (PPDA proxy from pass/pressure events).
     - xG by phase of play (open play, set piece, counter-attack — inferred from event sequences).
     - Substitution events with before/after formation context.
     - Top ball-carriers by progressive distance.
     - Shot map summary (locations, outcomes, xG values).
     - Key passing sequences (high-value passes leading to shots).
   - Each `EventSummary` has: `match_id`, `chunk_type="event_summary"`, `source="statsbomb"`,
     `window` (str label), `text` (human-readable prose), deterministic `chunk_id`.

3. **Fixture data** in `tests/fixtures/events_<match_id>.json`:
   - A real StatsBomb events JSON file for one match (e.g. a short match or first 200 events)
     committed to the repo for fast offline tests.

4. **Tests** in `tests/ingestion/test_event_chunker.py`:
   - `test_chunker_produces_at_least_one_summary_per_window_type` — given fixture events,
     asserts at least one EventSummary exists for each window type.
   - `test_event_summary_has_required_fields` — asserts `chunk_id`, `match_id`, `text`, `window`
     are present and non-empty.
   - `test_chunk_ids_are_deterministic` — running chunker twice on same input yields same IDs.
   - No tests call statsbombpy network; all tests use fixture JSON loaded from disk.

## Acceptance criteria

- [ ] `StatsBombFetcher` writes to `data/raw/<match_id>/events.json` on first call; reads from it
      on subsequent calls (no network on cache hit).
- [ ] `EventSummaryChunker` produces at least 6 distinct `window` values for a real match.
- [ ] All `EventSummary.chunk_id` values are unique within a match.
- [ ] All tests pass offline using fixture data (no `statsbombpy` network calls in test suite).
- [ ] `mypy` exits 0.
