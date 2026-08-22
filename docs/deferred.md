# Deferred Smells & Technical Debt

A persistent log of code smells, architectural debt, and follow-up items flagged during ticket reviews that have been deliberately deferred for future refactoring passes.

---

## `src/footballanalyst/embedding/factory.py`

- **Middle Man / Speculative Generality**: `get_embedding_model()` is a pure delegator function to `EmbeddingModelFactory.create()`, introducing redundant API surface. *(Flagged during Ticket 05 review)*

---

## `src/footballanalyst/embedding/sentence_transformer.py`

- **Dimension Mismatch / Unlisted Model Fallback**: `SentenceTransformerEmbedding` falls back to default 384 dimensions for unlisted custom model names if `.dimension` is accessed before `.embed()` lazy loads the model weights. *(Flagged during Ticket 05 review)*

---

## `src/footballanalyst/ingestion/event_chunker.py`

- **Duplicated Dictionary Traversal**: Deep nested dictionary access (`e.get("type", {}).get("name")`) is repeated across all 6 analytical window builder methods. *(Flagged during Ticket 03 review)*
- **Divergent Change**: `EventSummaryChunker` combines event parsing, metric calculations, and prose formatting across 6 distinct lenses in a single class. *(Flagged during Ticket 03 review)*

---

## `src/footballanalyst/ingestion/statsbomb_fetcher.py`

- **Feature Envy**: `StatsBombFetcher._extract_metadata()` performs domain-level event analysis inside the network/disk fetcher class. *(Flagged during Ticket 03 review)*

---

## `src/footballanalyst/store/vector_store.py`

- **Repeated Switches / Type Checking**: Repeated `chunk_type == "event_summary"` and `isinstance()` branching across collection selection, metadata serialization, and chunk deserialization. *(Flagged during Ticket 05 review)*
- **Primitive Obsession / Data Clumps**: `VectorStore.upsert` accepts parallel lists `chunks: list[Chunk]` and `embeddings: list[list[float]]`, requiring explicit length matching checks. *(Flagged during Ticket 05 review)*
- **Duplicated Code**: Literal repetition of collection dictionary structures (`ids`, `documents`, `metadatas`, `embeddings`) for both `event_summaries` and `narrative_chunks`. *(Flagged during Ticket 05 review)*
- **Divergent Change**: `VectorStore` is modified both when ChromaDB storage configuration changes and when `Chunk` schema metadata fields change. *(Flagged during Ticket 05 review)*

---

## `tests/fakes.py`

- **Refused Bequest**: `FakeVectorStore` inherits from concrete `VectorStore` to satisfy mypy type checking without invoking `super().__init__()` to avoid ChromaDB client initialization. Protocol abstraction for `VectorStore` deferred to future store refactoring pass. *(Flagged during Ticket 06 review)*

---

## `src/footballanalyst/ingestion/__init__.py` *(resolved)*

- **Circular Import — Fixed in Ticket 09**: `ingestion/__init__.py` previously eagerly re-exported `IngestionPipeline` and `IngestionResult`, causing a `store → ingestion/__init__ → pipeline → store` circular import that was latent (masked by pytest's module-load ordering). Removed from `__init__.py` since no caller imported them via the package; all consumers already used `from footballanalyst.ingestion.pipeline import ...` directly. *(Flagged and resolved during Ticket 09)*

---

## `src/footballanalyst/app/ask.py`

- **LLM Error Handling Deferred**: `ask()` does not catch or wrap LLM call failures (timeouts, rate limits, API errors). Exceptions propagate to the caller as-is. A proper `Answer(error=...)` state or retry/circuit-breaker logic is deferred. Structured error logging can be added in Ticket 12; retry/recovery in a future ticket. *(Flagged during Ticket 09)*

---

## `src/footballanalyst/generation/prompt.py`

- **No Prompt Truncation**: `build_prompt()` has no truncation strategy. At v1 corpus scale (top-8 chunks, paragraph-sized texts ≈ 4,000 tokens total), this is safely within all supported providers' context windows. If the corpus grows or top-k increases, a truncation strategy should be added. *(Flagged during Ticket 09)*
