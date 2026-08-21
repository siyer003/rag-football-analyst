# ADR-0004: Fixed Corpus with Re-runnable Ingestion Script

**Status:** Accepted  
**Date:** 2026-08-20

## Context

The system covers a curated, fixed set of matches ("well-documented matches with rich data and
rich narrative"). Two design poles:

1. **Dynamic ingestion at request time**: fetch data on demand when a user asks about a match.
   More flexible but adds latency, requires runtime network access, complicates error handling.

2. **Pre-ingested static corpus**: all data fetched, chunked, embedded, and stored before the
   application runs. Request-time is pure retrieval + generation, no network calls.

The project is timeboxed to a weekend. Adding new matches later is desirable without a redesign.

## Decision

Use a **pre-ingested static corpus**:

- A `MatchRegistry` config file (`config/corpus.toml`) lists all match IDs to ingest.
- An `ingest` CLI command (or `uv run ingest`) reads the registry, fetches StatsBomb events +
  narrative sources, chunks, embeds, and upserts into ChromaDB.
- The application at request-time performs only retrieval + generation — zero network calls
  to data sources.
- Ingestion is **idempotent**: re-running for already-ingested matches is safe (upsert by
  deterministic chunk ID).

**Adding a new match** = add its `match_id` to `corpus.toml` + re-run `uv run ingest`. No
code changes, no redesign.

**Narrative sources** are fetched during ingestion and stored as raw text in `data/raw/` before
chunking, making ingestion re-runnable without re-hitting APIs (cache-first).

## Consequences

- **+** Request-time has zero external dependencies — fast and reliable for demos.
- **+** Corpus is reproducible; `data/raw/` can be committed or regenerated.
- **+** Adding matches is a config change, not a code change.
- **+** Tests can run entirely against fixture data; no live API calls.
- **-** The application cannot answer questions about matches not in the corpus (by design —
  out-of-corpus queries return a graceful "not covered" message).
- **-** `data/raw/` may be large; may need git-lfs or `.gitignore` with a `make data` target.

## Rejected alternatives

- **Dynamic ingestion**: violates the "no live data sources at request time" constraint and
  makes demo reliability dependent on network availability.
