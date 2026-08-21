# 02: MatchRegistry + corpus config + out-of-corpus guard

**Status:** ready-for-agent  
**Blocked by:** 01

## What to build

A developer can populate `config/corpus.toml` with match IDs and human-readable labels, load it
at runtime as a `MatchRegistry`, and call `ask()` — receiving a well-typed `Answer` with
`out_of_corpus=True` when the match is not in the registry, rather than any hallucinated content.

This ticket delivers:

1. **`corpus.toml`** populated with all 8 v1 match IDs and labels:

   ```toml
   [[matches]]
   match_id = 3869685
   label = "FIFA World Cup 2022 Final — Argentina vs France"
   competition = "FIFA World Cup"
   season = "2022"

   [[matches]]
   match_id = 8658
   label = "FIFA World Cup 2018 Final — France vs Croatia"
   competition = "FIFA World Cup"
   season = "2018"

   # … remaining 6 matches
   ```

2. **`MatchRegistry`** class in `src/footballanalyst/corpus/registry.py`:
   - Loads from `corpus.toml` using `tomllib`.
   - Exposes `match_ids() -> list[int]`, `label(match_id: int) -> str`,
     `contains(match_id: int) -> bool`.

3. **`Answer` dataclass** in `src/footballanalyst/app/types.py`:
   - Fields: `text: str`, `citations: list[ChunkRef]`, `out_of_corpus: bool`.
   - `ChunkRef`: `chunk_id: str`, `source: str`, `chunk_type: str`, `snippet: str`.

4. **`ask()` stub** in `src/footballanalyst/app/ask.py`:
   - Signature: `ask(query: str, match_id: int, retriever: HybridRetriever, llm: LLMProvider) -> Answer`.
   - For now: only implements the out-of-corpus guard (returns `Answer` with `out_of_corpus=True`
     and a friendly message listing available matches). The happy path is wired in ticket 09.

5. **Tests** in `tests/test_ask.py`:
   - `test_ask_returns_out_of_corpus_for_unknown_match_id` — asserts `answer.out_of_corpus is True`
     and `answer.text` contains "not in corpus" (or similar).
   - `test_registry_contains_all_v1_matches` — loads the real `corpus.toml` and asserts all 8
     match IDs are present.

## Acceptance criteria

- [ ] `corpus.toml` contains all 8 v1 match IDs with labels.
- [ ] `MatchRegistry.contains(99999)` returns `False`.
- [ ] `MatchRegistry.contains(3869685)` returns `True`.
- [ ] `ask(query="test", match_id=99999, ...)` returns `Answer(out_of_corpus=True)` without
      calling the retriever or LLM.
- [ ] Both tests pass under `uv run pytest tests/test_ask.py`.
- [ ] `mypy` still exits 0 on `src/`.
