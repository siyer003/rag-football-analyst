# Football Analyst — Tactical Analysis RAG Assistant

A tactical-analysis assistant answering match strategy questions ("Why did this tactic work? Why did this player underperform?") grounded in match events (StatsBomb) and tactical narrative sources (Guardian, Wikipedia, StatsBomb blog).

## Quickstart

### 1. Installation

Ensure you have [`uv`](https://github.com/astral-sh/uv) installed:

```bash
uv sync
```

### 2. Environment Setup

Configure your API keys in `.env` or your shell environment:

```bash
# Required: LLM provider key (Groq is default)
export GROQ_API_KEY="your-groq-api-key"

# Alternative LLM provider (set LLM_PROVIDER=gemini)
export GOOGLE_API_KEY="your-google-api-key"

# Optional: Guardian API key for narrative fetching during ingestion
export GUARDIAN_API_KEY="your-guardian-api-key"
```

### 3. Ingest Match Corpus

Run offline ingestion to process events and narratives into ChromaDB vector store:

```bash
uv run ingest
```

> **Note on adding/modifying matches:** `MatchRegistry` configuration lives in `config/corpus.toml`. Streamlit's resource cache (`@st.cache_resource`) caches the registry in memory and does not watch `.toml` files for changes. If you add or edit matches in `config/corpus.toml`, you must re-run `uv run ingest` and restart the Streamlit server (`uv run app`) to load the updated registry.

### 4. Run Interactive Web UI

Launch the Streamlit web application:

```bash
uv run app
# or
uv run streamlit run src/footballanalyst/app/ui.py
```

Open `http://localhost:8501` in your web browser, select a match, enter a tactical question, and view grounded answers with citations.

---

## Executable Commands

- `uv run app`: Launches the Streamlit web interface (`src/footballanalyst/app/ui.py`).
- `uv run ingest`: Runs the offline ingestion pipeline (`src/footballanalyst/ingestion/cli.py`).
- `uv run footballanalyst`: Legacy skeleton package entrypoint (placeholder from project skeleton).
