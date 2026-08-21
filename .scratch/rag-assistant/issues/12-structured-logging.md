# 12: Structured logging + observability

**Status:** ready-for-agent  
**Blocked by:** 09

## What to build

Every significant pipeline step — ingestion, retrieval, LLM call — emits structured log events
via `structlog`. A developer running the system locally can see exactly what happened (which
chunks were retrieved, how long the LLM took, how many tokens were used). In CI, logs are
machine-parseable JSON.

This ticket delivers:

1. **`structlog` configuration** in `src/footballanalyst/logging.py`:
   - `configure_logging(json: bool = False)` sets up `structlog` with:
     - JSON renderer when `json=True` (CI / production) or `LOG_FORMAT=json` env var.
     - Human-readable coloured renderer otherwise (dev mode).
   - Called once at CLI startup (ingestion CLI, eval CLI, Streamlit app startup).

2. **Ingestion pipeline log events** (augment ticket 06):
   - `match.ingest.start`: `{match_id, label}`
   - `match.ingest.events_fetched`: `{match_id, event_count, source_cache_hit: bool}`
   - `match.ingest.chunks_produced`: `{match_id, event_summary_count, narrative_count}`
   - `match.ingest.embed_complete`: `{match_id, chunk_count, elapsed_ms}`
   - `match.ingest.upsert_complete`: `{match_id, upserted_count, elapsed_ms}`
   - `match.ingest.error`: `{match_id, error, step}` on failure.

3. **Retrieval log events** (augment HybridRetriever in ticket 08):
   - `retrieval.start`: `{match_id, query_len}`
   - `retrieval.event_results`: `{match_id, count, top_score}`
   - `retrieval.narrative_results`: `{match_id, count, top_score}`
   - `retrieval.merged`: `{match_id, final_count, elapsed_ms}`

4. **LLM call log events** (augment LLMProvider in ticket 09):
   - `llm.call.start`: `{provider, model, prompt_tokens_estimate}`
   - `llm.call.complete`: `{provider, model, elapsed_ms, response_len}`
   - `llm.call.error`: `{provider, error}` on failure.

5. **No new tests required** for logging itself — logging is a side effect, not observable
   behaviour. However, existing tests must not break due to log output (ensure loggers are
   silenced or captured in `conftest.py` with `caplog` or `structlog.testing`).

6. **`conftest.py` update**:
   - Add `structlog.testing.capture_logs()` as a pytest fixture to suppress log output in
     unit tests while keeping them available for assertion if needed.

## Acceptance criteria

- [ ] `uv run ingest` emits one `match.ingest.start` event per match.
- [ ] Each LLM call emits `llm.call.start` and `llm.call.complete` with `elapsed_ms` field.
- [ ] Setting `LOG_FORMAT=json uv run ingest` produces newline-delimited JSON log lines.
- [ ] All existing unit tests still pass (log output does not bleed into test output).
- [ ] `mypy` exits 0.
