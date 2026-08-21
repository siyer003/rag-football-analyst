# Football Tactical-Analysis RAG Assistant — Spec

**Feature slug:** `rag-assistant`  
**Status:** ready-for-agent

---

## Problem Statement

Tactical football analysis is currently split between two worlds: structured statistics (xG,
passes, formations) that are precise but context-free, and narrative write-ups that are rich but
unsearchable. A fan or analyst asking "why did Croatia's midfield dominate England in the 2018
semi-final?" has to manually cross-reference StatsBomb event exports with Guardian long-reads —
there's no tool that reasons across both simultaneously.

---

## Solution

A RAG assistant that answers tactical-reasoning questions ("why did this tactic work / why did
this player underperform") about a curated set of 8 historically significant matches. The system
combines:

- **Hybrid retrieval**: structured StatsBomb event data (passes, xG, formations, substitutions)
  summarised as EventSummaries, plus NarrativeChunks from Guardian articles, StatsBomb blog posts,
  and Wikipedia match articles — retrieved by separate retrievers and merged.
- **Grounded generation**: every Answer cites the specific Chunks that grounded it, preventing
  hallucination and letting users trace claims.
- **Fixed corpus**: 8 confirmed matches (see `config/corpus.toml`), ingested once and re-runnable
  as the corpus grows.

---

## User Stories

1. As a football analyst, I want to ask "why did Klopp's press work in the 2019 UCL final?" and get
   an answer that cites both pressing stats and tactical write-ups, so I can understand the causal
   chain, not just the numbers.
2. As a football analyst, I want to select a specific match from a dropdown before asking my
   question, so I don't have to specify it in natural language.
3. As a football analyst, I want every answer to include source citations (which Chunks it used),
   so I can judge how well-grounded the claim is.
4. As a football analyst, I want to ask about a player's underperformance ("why did Salah struggle
   after his injury in the 2018 UCL final?") and get both statistical evidence and narrative context.
5. As a football analyst, I want to ask formation and phase-of-play questions ("how did Mancini
   set up Italy to dominate the Euro 2020 final midfield?") and get answers that reference both
   the event data phases and tactical write-ups.
6. As a developer, I want to add a new match to the corpus by updating a config file and re-running
   an ingestion script, without changing any application code.
7. As a developer, I want the ingestion script to be idempotent, so I can safely re-run it without
   creating duplicate Chunks.
8. As a developer, I want to supply the LLM provider (Groq or Gemini) via an environment variable,
   so I can switch backends without code changes.
9. As a developer, I want to run an eval harness against golden Q&A pairs to measure retrieval
   quality and answer faithfulness before deploying.
10. As a developer, I want the full test suite to run offline without any real API keys, so CI
    passes on a clean machine.
11. As a user, I want the system to tell me clearly when I ask about a match that isn't in the
    corpus, rather than hallucinating an answer.
12. As a user, I want to use a minimal Streamlit web UI to interact with the assistant, so I don't
    need to run CLI commands.

---

## Implementation Decisions

### Architecture

- **Single bounded context**: no microservices. All code under `src/footballanalyst/`.
- **Module layout**:
  - `corpus/` — MatchRegistry, corpus.toml loading
  - `ingestion/` — ingestion pipeline: StatsBomb fetcher, narrative fetcher, chunkers
  - `retrieval/` — HybridRetriever, EventRetriever, NarrativeRetriever, re-ranker (RRF)
  - `generation/` — LLMProvider protocol + GroqProvider + GeminiProvider, prompt assembly
  - `embedding/` — EmbeddingModel protocol + SentenceTransformerEmbedding + GeminiEmbedding
  - `store/` — VectorStore abstraction wrapping ChromaDB
  - `app/` — Streamlit UI + `ask()` entrypoint
  - `eval/` — EvalHarness runner
- **Seam for testing**: `ask(query: str, match_id: int, retriever: HybridRetriever, llm: LLMProvider) -> Answer`.
  Tests inject fake retriever and LLM; all behaviour testable without network.

### Data

- **MatchRegistry**: `config/corpus.toml` — list of match IDs with human-readable labels.
- **V1 corpus**: 8 confirmed StatsBomb matches (WC 2018 final, WC 2022 final, WC 2018 semi,
  UCL 2009/19/18 finals, Euro 2020/2024 finals).
- **Raw narrative cache**: `data/raw/<match_id>/<source>.txt` — fetched once at ingest time,
  reused on re-ingest without hitting APIs again.
- **ChromaDB path**: `data/chroma/` — gitignored; reproducible via `uv run ingest`.

### Retrieval

- **Two ChromaDB collections**: `event_summaries`, `narrative_chunks`.
- **Chunk sizing**: EventSummary = one analytical window (≈ 300–500 tokens). NarrativeChunk =
  one paragraph (≈ 150–250 tokens), overlapping sliding window.
- **top-k**: EventRetriever retrieves top-5, NarrativeRetriever top-5; RRF merges to top-8
  passed to LLM context.
- **Metadata filter**: both retrievers filter by `match_id` first, limiting search space.

### Generation

- **LLM**: Groq Llama 3.3 70B by default (fast, free tier). Gemini 2.0 Flash as alternative.
- **Prompt structure**: system prompt with role + citation instructions; user prompt with
  RetrievedContext chunks labelled [1], [2], … and the Query.
- **Answer format**: structured response with `text` (markdown) + `citations` (list of chunk refs).

### Embedding

- **Default**: `sentence-transformers/all-MiniLM-L6-v2` (384 dims, local CPU, no API key).
- **Override**: Gemini `text-embedding-004` via `EMBEDDING_MODEL=gemini` env var.

### Quality

- **EvalHarness**: `eval/golden.json` — 15–20 golden `(question, match_id, expected_themes)` pairs.
  Scoring: chunk recall (were relevant chunks retrieved?) + LLM faithfulness (did the answer
  use the retrieved context?).
- **Structured logging**: `structlog` for all pipeline steps. LLM call tracing includes
  token counts, latency, provider name.
- **Containerisation**: Dockerfile in scope but lowest priority; `uv run` is the primary dev
  interface.

---

## Testing Decisions

- **Good tests**: test external behaviour through the public `ask()` interface. Never test
  internal chunking algorithms directly — test them via the ingestion pipeline's output shape.
- **Seam**: `ask(query, match_id, retriever=FakeRetriever(), llm=FakeLLM())`. All unit tests
  operate at this seam.
- **Integration tests** (tagged `@pytest.mark.integration`): run actual ChromaDB + SentenceTransformer
  against a single fixture match; skipped in CI unless `INTEGRATION=1` env var set.
- **No prior art** in codebase (greenfield). Test file layout mirrors `src/`: `tests/test_ask.py`,
  `tests/retrieval/test_hybrid_retriever.py`, `tests/ingestion/test_event_chunker.py`, etc.
- **Fake implementations**: `FakeLLMProvider`, `FakeEmbeddingModel`, `FakeHybridRetriever` live
  in `tests/fakes.py`.

---

## Out of Scope

- Live web search or team news (v2).
- Cross-match queries ("compare Klopp in 2019 vs 2024").
- User accounts or answer history.
- UCL 2021/22 final (not in StatsBomb open data).
- Any match not in the MatchRegistry.
- A production deployment (no cloud hosting, no auth).

---

## Further Notes

- The StatsBomb open data is confirmed available for all 8 v1 matches (verified via live API call).
- Guardian API requires a free developer key (`GUARDIAN_API_KEY` env var); tests use mock HTTP.
- Wikipedia and StatsBomb blog are scraped (no key needed) using `httpx` + `beautifulsoup4`.
- `uv` is the package manager throughout; `pyproject.toml` is the single source of truth.
- Python 3.12+ required (already pinned in `.python-version`).
