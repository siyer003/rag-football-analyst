# Football Analyst — Domain Context

Single-context repo. One bounded context: a football tactical-analysis RAG assistant that answers
"why did this tactic work / why did this player underperform" questions over a curated corpus of
~10 well-documented matches, using hybrid retrieval over structured event data and tactical narratives.

---

## Glossary

Terms used across code, tests, issues, and ADRs. Use these exactly; don't drift to synonyms.

### Core Domain

**Match**
A single football game in the corpus, uniquely identified by a StatsBomb `match_id` (integer).
A Match exists in the system only if it is listed in the `MatchRegistry`.

**MatchRegistry**
The static manifest of Match IDs that form the corpus. Lives as a config file (TOML/YAML).
The ingestion script reads this to decide what to fetch and embed. Adding a new match = adding its
ID to this file and re-running ingestion. Not a database — never queried at request-time.

**MatchCorpus**
The combined data package for a single Match after ingestion: all EventSummaries + all
NarrativeChunks. The unit that the HybridRetriever searches over.

**Event**
A single atomic StatsBomb match event (pass, shot, dribble, pressure, substitution, etc.) with
x/y coordinates, timestamp, player, and team metadata. Never embedded directly — too granular.

**EventSummary**
A human-readable text chunk derived from a window of raw Events, covering a specific analytical
lens (e.g. "pressing intensity first 15 minutes", "xG by phase of play", "formation shape changes
after substitution"). The unit embedded into the vector store from the structured side.
Has: `match_id`, `chunk_type="event_summary"`, `source="statsbomb"`, `window`, `text`.

**NarrativeChunk**
A paragraph-sized text passage from a tactical article (Guardian), a StatsBomb blog post, or a
Wikipedia match article. The unit embedded from the narrative side.
Has: `match_id`, `chunk_type="narrative"`, `source` (guardian|statsbomb_blog|wikipedia), `url`, `text`.

**Chunk**
The union type: either an EventSummary or a NarrativeChunk. Every Chunk carries
`match_id`, `chunk_type`, `source`, and `text`. The vector store stores Chunks.
Never refer to these as "documents" or "passages" in code or tests.

**Query**
A natural-language question submitted by a user through the Streamlit UI or CLI. Always associated
with a `match_id` (the user selects the match before asking).

**RetrievedContext**
The ordered set of Chunks returned by the HybridRetriever for a given Query. Passed verbatim
to the LLM prompt as grounding material.

**Answer**
The LLM-generated response to a Query, grounded in a RetrievedContext. Always includes
source citations (chunk references) so the user can trace claims. Never an answer without citations.

### Retrieval

**HybridRetriever**
The top-level retrieval component. Runs the EventRetriever and NarrativeRetriever in parallel
(or sequence), then merges and re-ranks the combined results before returning a RetrievedContext.
The seam at which retrieval is tested.

**EventRetriever**
Retrieves EventSummary Chunks from the vector store, filtered by `match_id` and `chunk_type`.
Uses dense vector search. May use structured metadata filters for phase/window when determinable
from the Query.

**NarrativeRetriever**
Retrieves NarrativeChunk Chunks from the vector store, filtered by `match_id` and `chunk_type`.
Uses dense vector search only.

**Re-ranker**
A lightweight scoring step inside the HybridRetriever that merges and orders results from both
sub-retrievers. In v1: reciprocal rank fusion (RRF). No cross-encoder in v1.

### Infrastructure

**VectorStore**
The ChromaDB-backed persistence layer for Chunks. One collection per `chunk_type` (event_summary,
narrative). Supports upsert (idempotent ingestion). Never accessed directly outside the
EventRetriever or NarrativeRetriever.

**LLMProvider**
An abstraction over LLM backends. Concrete implementations: `GroqProvider` (default, Llama 3)
and `GeminiProvider`. Selected via `LLM_PROVIDER` env var. All callers depend on the abstract
interface, never on a concrete SDK.

**EmbeddingModel**
An abstraction over embedding backends. Default: `sentence-transformers/all-MiniLM-L6-v2`
(local, no API key, CI-safe). Swappable via `EMBEDDING_MODEL` env var to Gemini embeddings
for demo quality. All callers depend on the abstract interface.

**Ingestion**
The process of fetching raw data (StatsBomb events + narrative sources), chunking it into
EventSummaries and NarrativeChunks, embedding each Chunk, and upserting into the VectorStore.
Defined by an ingestion script that reads the MatchRegistry. Idempotent per match_id:
re-running for an already-ingested match updates its Chunks without duplication.

### Quality

**EvalHarness**
A set of golden `(question, match_id, expected_themes)` triples used to measure retrieval
quality (chunk recall) and answer faithfulness (LLM grounding). Lives in `eval/golden.json`.
Run via `uv run eval`. Priority over containerisation in v1.

---

## Out of scope (v1)

- Live match data or team news (web search).
- Any match not in the MatchRegistry.
- Cross-match queries ("compare how Klopp pressed in 2019 vs 2024").
- User accounts, history, or persistence of Answers.

---

## Avoided synonyms

| Use | Not |
|-----|-----|
| Chunk | document, passage, record |
| MatchRegistry | corpus config, match list, dataset |
| EventSummary | event document, event chunk |
| NarrativeChunk | article chunk, text document |
| HybridRetriever | retriever, search engine |
| Answer | response, result |
| Ingestion | indexing, loading |
