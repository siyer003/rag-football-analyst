# 05: VectorStore + EmbeddingModel abstractions

**Status:** ready-for-agent  
**Blocked by:** 01

## What to build

A developer can embed a list of text strings and upsert/query Chunks in ChromaDB — all through
clean abstract interfaces that can be swapped for fakes in tests. No retriever or ingestion logic
lives here; this is pure infrastructure.

This ticket delivers:

1. **`EmbeddingModel` protocol** in `src/footballanalyst/embedding/base.py`:
   ```python
   class EmbeddingModel(Protocol):
       def embed(self, texts: list[str]) -> list[list[float]]: ...
       @property
       def dimension(self) -> int: ...
   ```

2. **`SentenceTransformerEmbedding`** in `src/footballanalyst/embedding/sentence_transformer.py`:
   - Wraps `sentence-transformers` with `all-MiniLM-L6-v2` (384 dims).
   - Selected when `EMBEDDING_MODEL` env var is unset or `local`.
   - Lazy loads the model on first call.

3. **`GeminiEmbedding`** in `src/footballanalyst/embedding/gemini.py`:
   - Wraps `google-genai` `text-embedding-004` (768 dims).
   - Selected when `EMBEDDING_MODEL=gemini`.
   - Requires `GOOGLE_API_KEY` env var.

4. **`FakeEmbeddingModel`** in `tests/fakes.py`:
   - Returns zero-vectors of dimension 384.
   - Used in all unit tests; no model download required.

5. **`VectorStore`** in `src/footballanalyst/store/vector_store.py`:
   - Wraps ChromaDB `PersistentClient` at path `data/chroma/`.
   - Manages two named collections: `event_summaries`, `narrative_chunks`.
   - Public interface:
     ```python
     def upsert(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None: ...
     def query(
         self,
         embedding: list[float],
         collection: str,
         match_id: int,
         top_k: int = 5,
     ) -> list[ScoredChunk]: ...
     ```
   - `upsert` uses ChromaDB's `upsert` (not `add`) to ensure idempotency.
   - `query` applies `where={"match_id": match_id}` filter before vector search.
   - `ScoredChunk`: `chunk: Chunk`, `score: float`.

6. **`EmbeddingModelFactory`** in `src/footballanalyst/embedding/factory.py`:
   - Reads `EMBEDDING_MODEL` env var; returns correct concrete implementation.

7. **Tests** in `tests/store/test_vector_store.py`:
   - Use a `tmp_path`-based ChromaDB (real ChromaDB, but ephemeral) — integration-tagged.
   - `test_upsert_then_query_returns_chunk` — upserts one chunk, queries, asserts it comes back.
   - `test_upsert_is_idempotent` — upserts same chunk twice; collection still has exactly one doc.
   - `test_query_filters_by_match_id` — upserts chunks from two different match_ids; query for
     one match_id returns only that match's chunks.

## Acceptance criteria

- [ ] `FakeEmbeddingModel.embed(["test"])` returns `[[0.0] * 384]` without loading any model.
- [ ] `SentenceTransformerEmbedding.embed(["hello"])` returns a list of 384 floats.
- [ ] `VectorStore.upsert` called twice with the same chunk IDs does not create duplicates.
- [ ] `VectorStore.query` with a `match_id` filter only returns chunks for that match.
- [ ] Integration tests pass (`uv run pytest -m integration`).
- [ ] Unit tests in `tests/store/` that don't touch real ChromaDB pass without `INTEGRATION=1`.
- [ ] `mypy` exits 0.
