# Project State

## Current Progress
- **01: Project skeleton & tooling** (`01-project-skeleton.md`) - Completed: Repository structure, dependencies, toolchain configs, and CI workflow.
- **02: MatchRegistry + corpus config + out-of-corpus guard** (`02-match-registry.md`) - Completed: MatchRegistry config loader, Answer domain dataclasses, and initial `ask()` entrypoint guard.
- **03: StatsBomb event fetcher + EventSummary chunker** (`03-event-fetcher-chunker.md`) - Completed: Disk-cached StatsBomb fetcher and structured EventSummary analytical window chunker.
- **04: Narrative fetcher + NarrativeChunk chunker** (`04-narrative-fetcher-chunker.md`) - Completed: Disk-cached Guardian/Wikipedia/StatsBomb narrative fetcher and sliding-window paragraph chunker.
- **05: VectorStore + EmbeddingModel abstractions** (`05-vector-store-embedding.md`) - Completed: VectorStore ChromaDB wrapper with cosine similarity scoring, SentenceTransformer/Gemini/Fake embedding models and factory.
- **06: Ingestion pipeline (`uv run ingest`)** (`06-ingestion-pipeline.md`) - Completed: IngestionPipeline orchestrating event and narrative fetching, chunking, embedding, vector store upserting, CLI entry point (`uv run ingest`), and structlog logging.
- **07: EventRetriever + NarrativeRetriever** (`07-retrievers.md`) - Completed: EventRetriever and NarrativeRetriever sub-retrievers bound to ChromaDB collections with score-ordered query retrieval.
- **08: HybridRetriever (RRF merge)** (`08-hybrid-retriever.md`) - Completed: HybridRetriever with RRF rank fusion, RetrievedContext/RankedChunk types, HybridRetrieverProtocol, and FakeHybridRetriever.

### Current/Next Ticket
- **09: LLMProvider abstraction + `ask()` happy path** (`09-llm-provider-ask.md`) - Groq/Gemini LLM integration and end-to-end prompt generation with citations.

### Remaining Tickets
- **10: Streamlit UI** (`10-streamlit-ui.md`) - Interactive tactical analysis web application.
- **11: EvalHarness + golden Q&A pairs** (`11-eval-harness.md`) - Retrieval recall and grounding evaluation framework.
- **12: Structured logging + observability** (`12-structured-logging.md`) - Comprehensive structlog instrumentation.
- **13: Dockerfile** (`13-dockerfile.md`) - Containerization for Streamlit application deployment.

## Current Architecture
The system is structured into five core sub-packages:
- **`corpus`**: Manages match corpus configuration (`config/corpus.toml`) via `MatchRegistry`.
- **`ingestion`**: Fetches raw match data from StatsBomb and narrative sources (cached in `data/raw/`), transforming them into `EventSummary` and `NarrativeChunk` instances. Orchestrated by `IngestionPipeline` and `ingest` CLI.
- **`embedding`**: Provides `EmbeddingModel` protocol implemented by `SentenceTransformerEmbedding`, `GeminiEmbedding`, and `FakeEmbeddingModel`, created via `EmbeddingModelFactory`.
- **`store`**: `VectorStore` persists chunk embeddings in ChromaDB PersistentClient (`data/chroma/`) across `event_summaries` and `narrative_chunks` collections using cosine similarity.
- **`retrieval`**: `HybridRetriever` is the single retrieval seam exposed to `ask()`. It fans out to `EventRetriever` and `NarrativeRetriever`, merges results via RRF (k=60, top-8), and returns a `RetrievedContext` (list of `RankedChunk`). `HybridRetrieverProtocol` is used for type-checking in `ask()`.
- **`app`**: Application entrypoint exposing `ask()`, which currently guards against out-of-corpus query match IDs before invoking retrieval or LLM completion.

## Implemented Capabilities
- Static match registry loading from TOML (`config/corpus.toml`) covering v1 matches.
- Out-of-corpus query guard returning `Answer(out_of_corpus=True)` for unknown match IDs.
- Disk-cached raw StatsBomb event fetching and analytical window chunking into `EventSummary`.
- Disk-cached Guardian, Wikipedia, and StatsBomb blog narrative fetching and paragraph chunking into `NarrativeChunk`.
- Pluggable embedding models (`SentenceTransformerEmbedding`, `GeminiEmbedding`, `FakeEmbeddingModel`) selectable by env var.
- Disk-backed ChromaDB `VectorStore` supporting idempotent `upsert` and `query` filtered by `match_id` with cosine similarity scoring.
- Offline end-to-end ingestion pipeline (`IngestionPipeline`) and CLI executable (`uv run ingest`) with `--match-ids` support, idempotent upserts, fault tolerance per match, and basic `structlog` progress logging.
- `HybridRetriever` merging `EventRetriever` + `NarrativeRetriever` results via RRF rank fusion (k=60, top-8), returning a `RetrievedContext` with scored and ranked `RankedChunk` objects.

## Architectural Decisions
- Use separate EventRetriever and NarrativeRetriever per collection, merged by RRF in HybridRetriever (see `docs/adr/0001-hybrid-retrieval-architecture.md`).
- Use disk-backed ChromaDB PersistentClient with two collections (`event_summaries`, `narrative_chunks`) filtered by `match_id` (see `docs/adr/0002-chromadb-vector-store.md`).
- Define Protocol abstractions for LLMProvider and EmbeddingModel with environment-driven concrete factory selection (see `docs/adr/0003-llm-provider-abstraction.md`).
- Pre-ingest a static corpus specified by MatchRegistry via idempotent offline ingestion with raw disk caching (see `docs/adr/0004-fixed-corpus-ingestion.md`).
- Gracefully decline queries for match IDs not present in MatchRegistry at `ask()` entrypoint before retrieval/LLM (see `docs/adr/0005-out-of-corpus-handling.md`).

### System Area to ADR Mapping
- **Retrieval**: `docs/adr/0001-hybrid-retrieval-architecture.md`
- **Vector Storage**: `docs/adr/0002-chromadb-vector-store.md`
- **LLM & Embedding Models**: `docs/adr/0003-llm-provider-abstraction.md`
- **Data Ingestion & Corpus**: `docs/adr/0004-fixed-corpus-ingestion.md`
- **App Entrypoint & Error Guarding**: `docs/adr/0005-out-of-corpus-handling.md`

## Current State / Important Context
- **No live API dependencies at request-time**: All retrieval operates against local ChromaDB (`data/chroma/`); raw API data is cached in `data/raw/`.
- **Environment variables**: `EMBEDDING_MODEL` (`local` | `gemini` | `fake`), `GOOGLE_API_KEY`, `GUARDIAN_API_KEY`, `GROQ_API_KEY`.
- **Unit vs Integration Testing**: Offline unit tests skip ChromaDB/network using `FakeVectorStore` and `FakeEmbeddingModel`. Real ChromaDB tests are marked `@pytest.mark.integration`.
- **Idempotency**: Chunks use deterministic SHA-256 IDs; vector store upsert is idempotent.
- **RRF tiebreak**: HybridRetriever uses an event-first stable tiebreak (arbitrary, documented in class docstring, not a semantic preference).
- **Deferred Code Smells & Technical Debt**: Tracked in `docs/deferred.md` for dedicated cleanup passes.


## Next Work
- **Ticket 09: LLMProvider abstraction + `ask()` happy path** (`09-llm-provider-ask.md`)
  - **Dependencies**: Ticket 08 (HybridRetriever + RetrievedContext).
  - **Relevant ADRs / Architecture to check**: `docs/adr/0003-llm-provider-abstraction.md`.


