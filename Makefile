.PHONY: test lint ingest eval sync

sync:
	uv sync

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run mypy src/

ingest:
	uv run python -m footballanalyst.ingestion

eval:
	uv run python -m footballanalyst.eval
