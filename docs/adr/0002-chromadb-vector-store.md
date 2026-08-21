# ADR-0002: ChromaDB as Vector Store

**Status:** Accepted  
**Date:** 2026-08-20

## Context

The system needs a vector store for Chunks (EventSummaries and NarrativeChunks). Requirements:

- No Docker dependency (breaks CI on GitHub Actions without extra setup).
- Zero-config: no server process to start or manage.
- Persistent to local disk (survive restarts; don't re-embed on every run).
- Pure Python install via pip/uv.
- Supports metadata filtering (filter by `match_id`, `chunk_type` without loading all vectors).
- Compatible with `sentence-transformers` embeddings and custom embedding functions.

## Decision

Use **ChromaDB** (`chromadb` package) with the local PersistentClient (disk-backed).

- Two named collections: `event_summaries` and `narrative_chunks`.
- Metadata stored per document: `match_id`, `chunk_type`, `source`, `window` (events only).
- Upsert semantics (idempotent ingestion): documents keyed by a deterministic `chunk_id`
  derived from `match_id + source + content_hash`.
- ChromaDB's `where` filter used for `match_id` scoping in both sub-retrievers.

The `VectorStore` abstraction in code wraps ChromaDB; the concrete type is never leaked to
callers above the retriever layer.

## Consequences

- **+** No Docker, no server, no CI special-casing.
- **+** pip-installable; `uv add chromadb` is the entire setup.
- **+** Metadata filters work out of the box.
- **+** Deterministic chunk IDs make ingestion idempotent.
- **-** Not suitable for production-scale (millions of vectors), but corpus is ≤ 15 matches.
- **-** ChromaDB's DuckDB backend has occasional API changes between minor versions; pin version.

## Rejected alternatives

- **FAISS**: no built-in persistence or metadata filtering without wrappers; harder to make
  idempotent.
- **LanceDB**: strong Arrow integration, potentially better for event data, but less mature
  Python API for metadata filtering at the time of decision.
- **Qdrant / Weaviate**: require Docker or a cloud account; violates CI constraint.
- **pgvector**: requires PostgreSQL; Docker dependency.
