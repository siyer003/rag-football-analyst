# 13: Dockerfile

**Status:** ready-for-agent  
**Blocked by:** 01

## What to build

A single multi-stage Dockerfile that builds a production image for the Streamlit app. A
developer can run `docker build -t football-analyst .` and `docker run -p 8501:8501 football-analyst`
to start the app — assuming the ChromaDB data volume is mounted.

This ticket delivers:

1. **`Dockerfile`** at the repo root — multi-stage build:
   - **Stage 1 (builder)**: `python:3.12-slim` base; install `uv`; copy `pyproject.toml` +
     `uv.lock`; run `uv sync --no-dev` to install production deps into a virtual env.
   - **Stage 2 (runtime)**: `python:3.12-slim` base; copy venv from builder; copy `src/`,
     `config/`, and `eval/` (not `data/` — that's mounted at runtime).
   - `EXPOSE 8501`.
   - `CMD ["python", "-m", "streamlit", "run", "src/footballanalyst/app/ui.py", "--server.port=8501", "--server.address=0.0.0.0"]`.

2. **`.dockerignore`** — exclude `.venv/`, `data/chroma/`, `.git/`, `tests/`, `*.pyc`,
   `data/raw/` (raw data is large; only the embedded ChromaDB matters at runtime).

3. **`docker-compose.yml`** (optional, nice-to-have):
   - `app` service: the Dockerfile image.
   - Volume mount: `./data/chroma:/app/data/chroma` (pre-ingested ChromaDB from host).
   - Env file: `.env` with `GROQ_API_KEY` etc.

4. **`README.md` Docker section** (add):
   - Build command, run command, env var list, volume mount instruction.
   - Note: `uv run ingest` must be run on the host before starting the container (data is
     pre-ingested; the container is runtime-only).

5. **No new Python tests** for the Dockerfile — Docker build validity is verified by running
   `docker build` in a manual check or a separate CI job (not the main pytest suite).
   Optionally: add a `docker-build` job to the GitHub Actions workflow that runs `docker build`
   without pushing.

## Acceptance criteria

- [ ] `docker build -t football-analyst .` completes without error.
- [ ] `docker run -p 8501:8501 -v $(pwd)/data/chroma:/app/data/chroma -e GROQ_API_KEY=<key> football-analyst`
      starts the Streamlit server and the app is reachable at `http://localhost:8501`.
- [ ] The image does not contain `data/raw/` or `.venv/` (verify with `docker image inspect`).
- [ ] `docker build` is reproducible (second build uses layer cache; finishes in < 30s on warm
      cache).
