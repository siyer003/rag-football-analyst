# 09: LLMProvider abstraction + `ask()` happy path

**Status:** ready-for-agent  
**Blocked by:** 02, 08

## What to build

The `ask()` function is fully wired: for an in-corpus `match_id`, it calls the HybridRetriever,
assembles a prompt with the RetrievedContext, calls the LLM, and returns an `Answer` with the
generated text and source citations. This is the primary end-to-end behaviour of the system.

This ticket delivers:

1. **`LLMProvider` protocol** in `src/footballanalyst/generation/base.py`:
   ```python
   class LLMProvider(Protocol):
       def complete(self, system: str, user: str) -> str: ...
   ```

2. **`GroqProvider`** in `src/footballanalyst/generation/groq_provider.py`:
   - Uses `groq` SDK with `llama-3.3-70b-versatile` model.
   - Requires `GROQ_API_KEY` env var.
   - Raises `LLMConfigError` if key is missing.

3. **`GeminiProvider`** in `src/footballanalyst/generation/gemini_provider.py`:
   - Uses `google-genai` SDK with `gemini-2.0-flash` model.
   - Requires `GOOGLE_API_KEY` env var.

4. **`LLMProviderFactory`** in `src/footballanalyst/generation/factory.py`:
   - Reads `LLM_PROVIDER` env var (`groq` | `gemini`); defaults to `groq`.
   - Returns the correct concrete implementation.

5. **`FakeLLMProvider`** in `tests/fakes.py`:
   - `complete(system, user) -> str` returns a deterministic canned string that includes the
     phrase `[1]` (simulating a citation reference) — so citation-parsing tests work.

6. **Prompt assembly** in `src/footballanalyst/generation/prompt.py`:
   - `build_prompt(query: str, context: RetrievedContext) -> tuple[str, str]`
     returns `(system_prompt, user_prompt)`.
   - System prompt: instructs the LLM to answer only from the provided context, to cite every
     claim with `[N]` where N is the chunk number, and to say "not enough information" if
     context is insufficient.
   - User prompt: lists each chunk as `[N] (source: X)\n<text>`, then appends the query.

7. **Citation parser** in `src/footballanalyst/generation/citations.py`:
   - `parse_citations(answer_text: str, context: RetrievedContext) -> list[ChunkRef]`
   - Extracts `[N]` references from `answer_text` and maps them to `ChunkRef` objects from the
     context.

8. **`ask()` happy path** in `src/footballanalyst/app/ask.py` (extends ticket 02's stub):
   - Full flow: out-of-corpus guard → retrieve → build prompt → LLM complete → parse citations
     → return `Answer`.

9. **Tests** in `tests/test_ask.py` (extends ticket 02):
   - `test_ask_calls_retriever_with_correct_match_id` — assert `FakeHybridRetriever` was called
     with the right `match_id`.
   - `test_ask_returns_answer_with_text_and_citations` — assert `answer.text` is non-empty and
     `answer.citations` is non-empty (canned LLM response contains `[1]`).
   - `test_ask_answer_text_comes_from_llm` — assert `answer.text` matches the `FakeLLMProvider`
     canned response.
   - `test_ask_does_not_call_llm_for_out_of_corpus_match` — assert `FakeLLMProvider.complete`
     was never called when `out_of_corpus=True`.
   - All tests use `FakeHybridRetriever` and `FakeLLMProvider`; no network calls.

## Acceptance criteria

- [ ] `ask("why did Klopp's press work?", match_id=22912, retriever=FakeRetriever(), llm=FakeLLM())`
      returns `Answer(out_of_corpus=False, text=<non-empty>, citations=<non-empty list>)`.
- [ ] `ask(..., match_id=99999, ...)` returns `Answer(out_of_corpus=True)` without calling LLM.
- [ ] `GroqProvider` raises a clear error when `GROQ_API_KEY` is not set (not a raw SDK error).
- [ ] `LLMProviderFactory` returns `GroqProvider` when `LLM_PROVIDER` is unset.
- [ ] All unit tests pass offline; no real LLM calls in test suite.
- [ ] `mypy` exits 0.
