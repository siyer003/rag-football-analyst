# 11: EvalHarness + golden Q&A pairs

**Status:** ready-for-agent  
**Blocked by:** 09

## What to build

A developer can run `uv run eval` and get a structured report showing how well the system
retrieves relevant Chunks and how faithfully the LLM grounds its Answer in those Chunks — across
15–20 golden (question, match_id, expected_themes) pairs. This is the primary quality gate for
the portfolio.

This ticket delivers:

1. **`eval/golden.json`** — 15–20 golden pairs, at least one per v1 match, covering:
   - Tactical questions ("why did X tactic work")
   - Player performance questions ("why did player X underperform")
   - Formation/phase questions ("how did team X set up defensively")
   - Expected themes are a list of keywords/phrases that a good answer should mention.

   Example entry:
   ```json
   {
     "id": "wc2022-final-01",
     "match_id": 3869685,
     "question": "Why did Argentina's pressing system break down in the second half?",
     "expected_themes": ["high press", "France counter-attack", "Mbappé", "xG", "space behind"]
   }
   ```

2. **`EvalHarness`** in `src/footballanalyst/eval/harness.py`:
   - Loads `eval/golden.json`.
   - For each golden pair: calls `ask(question, match_id, retriever=<real>, llm=<real>)`.
   - Computes two scores per pair:
     - **Chunk recall**: fraction of `expected_themes` that appear (case-insensitive substring
       match) in any retrieved Chunk's text.
     - **Answer faithfulness**: fraction of `expected_themes` that appear in `answer.text`.
   - Aggregates: mean chunk recall and mean faithfulness across all pairs, and per-match.
   - Outputs a structured report (JSON + human-readable table).

3. **`eval` CLI entry point** in `src/footballanalyst/eval/cli.py`:
   - Registered as `eval = "footballanalyst.eval.cli:main"` in `pyproject.toml`.
   - Accepts `--match-ids` to run eval for specific matches only.
   - Accepts `--output-json path` to write the full report JSON.
   - Exits non-zero if mean faithfulness < 0.5 (configurable threshold).

4. **Tests** in `tests/eval/test_harness.py`:
   - `test_harness_loads_golden_file` — assert at least 15 entries loaded.
   - `test_chunk_recall_score_is_between_0_and_1` — given a mocked `ask()` that returns a known
     Answer, assert score is correctly computed.
   - `test_harness_exits_nonzero_below_threshold` — assert CLI returns exit code 1 when
     faithfulness is below threshold.
   - Tests use `FakeLLMProvider` + `FakeHybridRetriever`; no real LLM call.

## Acceptance criteria

- [ ] `eval/golden.json` contains at least 15 entries, at least one per v1 match.
- [ ] `uv run eval` completes and prints a per-match faithfulness table.
- [ ] `uv run eval --output-json report.json` writes valid JSON.
- [ ] `uv run eval` exits 1 if any match scores below the faithfulness threshold.
- [ ] All unit tests pass offline.
- [ ] `mypy` exits 0.
