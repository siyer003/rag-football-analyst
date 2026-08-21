# 08: HybridRetriever (RRF merge)

**Status:** ready-for-agent  
**Blocked by:** 07

## What to build

The `HybridRetriever` is the single retrieval seam exposed to the `ask()` entrypoint. It runs
the EventRetriever and NarrativeRetriever, merges their result lists using Reciprocal Rank Fusion
(RRF), and returns a unified `RetrievedContext` — a ranked list of Chunks ready to be passed to
the LLM prompt.

This ticket delivers:

1. **`HybridRetriever`** in `src/footballanalyst/retrieval/hybrid_retriever.py`:
   ```python
   class HybridRetriever:
       def retrieve(self, query: str, match_id: int) -> RetrievedContext: ...
   ```
   - Internally:
     1. Embeds the `query` string using the `EmbeddingModel`.
     2. Calls `EventRetriever.retrieve(embedding, match_id, top_k=5)`.
     3. Calls `NarrativeRetriever.retrieve(embedding, match_id, top_k=5)`.
     4. Merges using RRF: `score(chunk) = sum(1 / (k + rank_i))` for each list where `k=60`
        (standard RRF constant).
     5. Returns top-8 chunks by RRF score as a `RetrievedContext`.

2. **`RetrievedContext`** dataclass in `src/footballanalyst/retrieval/types.py`:
   - `chunks: list[RankedChunk]`
   - `RankedChunk`: `chunk: Chunk`, `rrf_score: float`, `rank: int`.

3. **`HybridRetriever` protocol** (for type-checking in `ask()`):
   ```python
   class HybridRetrieverProtocol(Protocol):
       def retrieve(self, query: str, match_id: int) -> RetrievedContext: ...
   ```

4. **`FakeHybridRetriever`** in `tests/fakes.py`:
   - Returns a pre-configured `RetrievedContext` regardless of input.
   - Used in `ask()` unit tests (ticket 09).

5. **Tests** in `tests/retrieval/test_hybrid_retriever.py`:
   - All tests use `FakeEmbeddingModel` + fake sub-retrievers (inject via constructor).
   - `test_hybrid_retriever_returns_chunks_from_both_sources` — fake event retriever returns
     2 chunks, fake narrative retriever returns 3; assert final context has chunks of both
     `chunk_type` values.
   - `test_hybrid_retriever_limits_to_top_8` — fake sub-retrievers return 10 chunks each;
     assert `len(context.chunks) == 8`.
   - `test_rrf_scores_higher_ranked_results_more` — first-ranked chunk from each sub-retriever
     has higher RRF score than last-ranked; assert ordering is correct.
   - `test_hybrid_retriever_returns_empty_context_for_empty_sub_results` — both sub-retrievers
     return `[]`; context has 0 chunks.

## Acceptance criteria

- [ ] `HybridRetriever.retrieve("test", match_id=8658)` with fake sub-retrievers returning 5
      chunks each produces a `RetrievedContext` with ≤ 8 chunks.
- [ ] RRF output is ordered by score descending.
- [ ] Result contains chunks of both `chunk_type="event_summary"` and `chunk_type="narrative"`.
- [ ] All tests use fake dependencies; no network calls, no ChromaDB.
- [ ] `mypy` exits 0.
