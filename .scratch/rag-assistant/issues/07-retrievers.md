# 07: EventRetriever + NarrativeRetriever

**Status:** ready-for-agent  
**Blocked by:** 05

## What to build

Given a query embedding and a `match_id`, the EventRetriever returns the top-k most relevant
`EventSummary` chunks for that match, and the NarrativeRetriever returns the top-k most relevant
`NarrativeChunk` chunks. Both retrievers are the implementation detail behind the HybridRetriever
(ticket 08); they are never called directly by application code.

This ticket delivers:

1. **`EventRetriever`** in `src/footballanalyst/retrieval/event_retriever.py`:
   ```python
   class EventRetriever:
       def retrieve(
           self,
           query_embedding: list[float],
           match_id: int,
           top_k: int = 5,
       ) -> list[ScoredChunk]: ...
   ```
   - Queries the `event_summaries` ChromaDB collection with `match_id` filter.
   - Returns `ScoredChunk` list ordered by cosine similarity descending.

2. **`NarrativeRetriever`** in `src/footballanalyst/retrieval/narrative_retriever.py`:
   - Same interface, same logic, queries `narrative_chunks` collection.

3. **`FakeVectorStore`** added to `tests/fakes.py`:
   - In-memory `dict[str, list[ScoredChunk]]` keyed by `(collection, match_id)`.
   - Supports `upsert` (stores) and `query` (returns pre-configured results).
   - Used in all retriever unit tests; no ChromaDB process needed.

4. **Tests** in `tests/retrieval/test_event_retriever.py` and `test_narrative_retriever.py`:
   - `test_retriever_returns_top_k_results` — pre-configure `FakeVectorStore` with 10 chunks;
     assert retriever returns exactly `top_k=5`.
   - `test_retriever_filters_by_match_id` — store has chunks for match 1 and match 2; querying
     for match 1 returns only match 1 chunks.
   - `test_retriever_returns_empty_list_for_unknown_match` — querying a match_id with no stored
     chunks returns `[]`, not an exception.

## Acceptance criteria

- [ ] `EventRetriever.retrieve(embedding, match_id=99)` returns `[]` when no chunks exist for
      that `match_id`, without raising.
- [ ] Both retrievers honour the `top_k` parameter exactly when enough results exist.
- [ ] All tests use `FakeVectorStore`; no ChromaDB process is started in unit tests.
- [ ] `mypy` exits 0.
