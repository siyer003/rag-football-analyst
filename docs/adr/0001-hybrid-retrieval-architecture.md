# ADR-0001: Hybrid Retrieval — Separate Retrievers, Merged Results

**Status:** Accepted  
**Date:** 2026-08-20

## Context

The system needs to answer tactical-reasoning questions ("why did this tactic work") over two
qualitatively different data sources:

1. **Structured event data** (StatsBomb): precise, quantitative, spatiotemporal. Best for
   "what happened" questions — pressing stats, xG by phase, formation changes.
2. **Narrative text** (Guardian, Wikipedia, StatsBomb blog): contextual, interpretive, causal.
   Best for "why it happened" questions — manager intent, pre-match context, tactical framing.

A single unified index (everything embedded together) would let quantitative event chunks crowd out
narrative chunks for tactical questions, or vice versa. A query router (classify-then-route) would
require a reliable intent classifier and would prevent answers that need both signal types.

## Decision

Use **separate retrievers** — an EventRetriever and a NarrativeRetriever — each searching their
own sub-collection in ChromaDB, both filtered by `match_id`. Results are merged by a Re-ranker
inside the HybridRetriever using Reciprocal Rank Fusion (RRF) before being passed to the
LLMProvider.

The HybridRetriever is the single seam exposed to callers. Sub-retrievers are implementation
details hidden behind it.

## Consequences

- **+** Both signal types always contribute to every answer; no routing mistakes.
- **+** Each sub-collection can be tuned (chunk size, top-k) independently.
- **+** Easy to test: mock both sub-retrievers in HybridRetriever tests.
- **-** RRF is a heuristic; a learned re-ranker would be better but is v2.
- **-** Two ChromaDB collections to maintain during ingestion.

## Rejected alternatives

- **Unified index**: simpler but loses signal type separation.
- **Query routing**: brittle without a good classifier; prevents blended answers.
- **Cross-encoder re-ranking**: better quality but needs a hosted model; deferred to v2.
