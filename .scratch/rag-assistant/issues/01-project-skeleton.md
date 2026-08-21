# 01: Project skeleton & tooling

**Status:** ready-for-agent  
**Blocked by:** None (can start immediately)

## What to build

Bootstrap the repo so every subsequent ticket has a working foundation to build on. A developer
cloning this repo should be able to run `uv sync`, `uv run pytest`, `uv run ruff check .`, and
`uv run mypy src/` and get green results — before any feature code exists.

- Configure `pyproject.toml` with all project dependencies and dev-dependencies (pytest, ruff,
  mypy, structlog, chromadb, sentence-transformers, statsbombpy, httpx, beautifulsoup4, streamlit,
  groq, google-genai, tomllib).
- Create the full `src/footballanalyst/` package tree with empty `__init__.py` stubs for:
  `corpus/`, `ingestion/`, `retrieval/`, `generation/`, `embedding/`, `store/`, `app/`, `eval/`.
- Create `tests/` with a `conftest.py` and a `tests/fakes.py` stub (empty classes for now).
- Configure `ruff` (lint + format) and `mypy` (strict mode) in `pyproject.toml`.
- Add a `pytest` config section: `testpaths = ["tests"]`, markers for `integration`.
- Add a GitHub Actions workflow (`.github/workflows/ci.yml`) that runs on push/PR:
  `uv sync → ruff check → mypy → pytest` (unit tests only; integration tests skipped).
- Create `config/corpus.toml` as an empty skeleton (just `[matches]` header, no IDs yet —
  those come in ticket 02).
- Create `data/raw/.gitkeep` and `data/chroma/.gitkeep`; add `data/chroma/` to `.gitignore`.
- Add a top-level `Makefile` or `justfile` with `make test`, `make lint`, `make ingest`, `make eval`.

## Acceptance criteria

- [ ] `uv sync` completes without error on a clean machine (no pre-installed packages assumed).
- [ ] `uv run pytest` exits 0 (zero tests collected is fine at this stage).
- [ ] `uv run ruff check .` exits 0.
- [ ] `uv run mypy src/` exits 0 (no source code yet; stubs only).
- [ ] CI workflow file exists and the workflow definition is valid YAML.
- [ ] `src/footballanalyst/` package tree has all 8 sub-packages with `__init__.py`.
- [ ] `config/corpus.toml` exists.
- [ ] `data/chroma/` is gitignored.
