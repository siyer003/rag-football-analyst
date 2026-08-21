# ADR-0003: LLMProvider Abstraction (Groq + Gemini)

**Status:** Accepted  
**Date:** 2026-08-20

## Context

The generation step requires calling an LLM with a RetrievedContext and Query to produce an Answer.
Two free-tier providers are viable:

- **Groq** (Llama 3.1 / Llama 3.3 70B): OpenAI-compatible API, very low latency (~1–3s),
  free tier generous, `groq` Python SDK.
- **Gemini API** (Gemini 1.5 Flash / 2.0 Flash): better long-context handling (useful if
  narrative chunks are large), free tier available, `google-genai` SDK.

Both are useful: Groq for fast demos, Gemini for large-context queries. Hardcoding either one
makes the portfolio less impressive and ties tests to a real API.

## Decision

Define a **`LLMProvider` abstract interface** with a single method:

```python
class LLMProvider(Protocol):
    def complete(self, system: str, user: str) -> str: ...
```

Concrete implementations: `GroqProvider` and `GeminiProvider`.
Selection via `LLM_PROVIDER` env var (`groq` | `gemini`); default `groq`.
API keys via `GROQ_API_KEY` / `GOOGLE_API_KEY` env vars.

Tests use a `FakeLLMProvider` fixture that returns deterministic canned responses without
any network call. The `FakeLLMProvider` is the only LLM implementation in the test suite.

## Consequences

- **+** Tests never hit real APIs; fully offline and free.
- **+** Demo can switch provider by changing one env var.
- **+** Adding a third provider (e.g., local Ollama) is a new concrete class, no interface change.
- **-** One extra abstraction layer; marginal complexity.
- **-** The two concrete providers must be kept in sync with upstream SDK changes.

## Rejected alternatives

- **Hardcode Groq**: simpler but makes tests require a real API key.
- **LiteLLM**: unified interface library, but adds a dependency that abstracts away the
  portfolio-relevant code; better to own the thin abstraction.

## Note on embedding model

The same protocol pattern is applied to the `EmbeddingModel`:

```python
class EmbeddingModel(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...
```

Default: `SentenceTransformerEmbedding` (`all-MiniLM-L6-v2`, runs on CPU, no API key).
Override: `GeminiEmbedding` via `EMBEDDING_MODEL=gemini` env var.
Tests use a `FakeEmbeddingModel` that returns zero-vectors of the correct dimension.
