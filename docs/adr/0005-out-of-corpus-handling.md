# ADR-0005: Out-of-Corpus Query Handling

**Status:** Accepted  
**Date:** 2026-08-20

## Context

Users ask about specific matches. The corpus covers a fixed set (MatchRegistry). A user might:

1. Ask about a match that is in the corpus — normal path.
2. Ask about a match that is NOT in the corpus — needs a clear, honest response.
3. Ask a question without specifying a match — UI forces match selection, so this can't happen.

Options for case 2:
- **(a) Graceful decline**: return a message like "I don't have data for that match" without
  attempting an answer. Honest, prevents hallucination.
- **(b) Best-effort answer with caveat**: attempt retrieval from whatever is closest, caveat the
  answer. Risks hallucination on thin context.
- **(c) Raise an exception**: treat as a caller error. Appropriate for a bounded library API but
  not for a UI-facing product.

## Decision

Use **(a) graceful decline**.

If the `match_id` supplied with a Query is not in the MatchRegistry, the system returns an
Answer with:
- `text`: a fixed, friendly "not in corpus" message listing the available matches.
- `citations`: empty list.
- `out_of_corpus`: `True` flag.

This check happens at the `ask()` entrypoint before any retrieval is attempted — no LLM call,
no vector search.

The Streamlit UI surfaces available matches as a dropdown populated from the MatchRegistry, so
users can only select in-corpus matches. The `out_of_corpus` path exists for programmatic callers
(API, eval harness) that may supply arbitrary match IDs.

## Consequences

- **+** Eliminates hallucination risk for out-of-corpus queries.
- **+** Simple: one guard at the entrypoint, no retrieval fallback logic.
- **+** The UI's dropdown makes this path unreachable in normal use.
- **-** Users can't get partial answers from related matches (cross-match is out of scope anyway).
