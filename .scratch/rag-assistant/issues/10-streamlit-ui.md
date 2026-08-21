# 10: Streamlit UI

**Status:** ready-for-agent  
**Blocked by:** 09

## What to build

A user can open the Streamlit app in a browser, select a match from a dropdown, type a
tactical question, and see a formatted Answer with citations — without touching a terminal.
The UI is minimal and functional; polish is secondary.

This ticket delivers:

1. **`src/footballanalyst/app/ui.py`** — the Streamlit app:
   - Page title and a brief one-line description of what the assistant does.
   - **Match selector**: `st.selectbox` populated from `MatchRegistry.matches()` (labels as
     display text, `match_id` as the underlying value).
   - **Question input**: `st.text_area` with placeholder text ("e.g. Why did Croatia's
     midfield dominate England in the first half?").
   - **Ask button**: `st.button("Ask")`.
   - **Answer display** (after submission):
     - `st.markdown(answer.text)` for the generated answer.
     - A collapsible `st.expander("Sources")` listing each `ChunkRef` — source name, chunk
       type, and a snippet of the chunk text.
     - If `answer.out_of_corpus`, display a friendly info box instead of the expander.
   - **Spinner** while the `ask()` call is in progress: `st.spinner("Thinking...")`.
   - Session state: previous answer persists in `st.session_state` until a new question is asked.

2. **`streamlit` entry point** in `pyproject.toml` scripts:
   - `app = "footballanalyst.app.ui:main"` — or a shell script wrapper; ensure `uv run app`
     starts the Streamlit server.
   - Alternatively, document `uv run streamlit run src/footballanalyst/app/ui.py` in the README.

3. **`README.md` quickstart section** (add or update):
   - `uv sync` → `uv run ingest` → `uv run streamlit run src/footballanalyst/app/ui.py`
   - Required env vars listed: `GROQ_API_KEY` (or `GOOGLE_API_KEY`), optional `GUARDIAN_API_KEY`.

4. **Smoke test** in `tests/app/test_ui.py` (unit, not integration):
   - Uses `streamlit.testing.v1.AppTest` (Streamlit's built-in test runner).
   - `test_ui_renders_match_selector` — assert a selectbox with at least 8 options is present.
   - `test_ui_shows_spinner_placeholder_before_question` — app renders without error on cold load.
   - These tests do NOT exercise the `ask()` call (that's tested in `test_ask.py`).

## Acceptance criteria

- [ ] `uv run streamlit run src/footballanalyst/app/ui.py` starts the server without error
      (requires ChromaDB populated from `uv run ingest`).
- [ ] The match dropdown shows all 8 v1 match labels.
- [ ] Submitting a question shows a spinner, then the answer with citations in an expander.
- [ ] Asking about a match that is somehow not in the registry shows a friendly message (not a
      Python traceback).
- [ ] Smoke tests pass in CI (no real `ask()` call; LLM and retriever not needed).
- [ ] `mypy` exits 0.
