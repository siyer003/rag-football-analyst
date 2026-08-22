import json
from pathlib import Path
from typing import cast
from unittest.mock import MagicMock

import pytest

from footballanalyst.corpus.registry import MatchRegistry
from footballanalyst.ingestion.event_chunker import EventSummaryChunker
from footballanalyst.ingestion.narrative_chunker import NarrativeChunker
from footballanalyst.ingestion.narrative_fetcher import NarrativeFetcher
from footballanalyst.ingestion.pipeline import IngestionPipeline, IngestionResult
from footballanalyst.ingestion.statsbomb_fetcher import StatsBombFetcher
from footballanalyst.ingestion.types import (
    EventSummary,
    NarrativeChunk,
    RawMatchData,
    SourcePayload,
)
from tests.fakes import FakeEmbeddingModel, FakeVectorStore


@pytest.fixture
def dummy_registry() -> MatchRegistry:
    matches = [
        {
            "match_id": 3869685,
            "label": "Argentina vs France 2022",
            "competition": "World Cup",
            "season": "2022",
            "statsbomb_blog_url": "https://example.com/blog",
        },
        {
            "match_id": 3754058,
            "label": "Barcelona vs Real Madrid 2011",
            "competition": "La Liga",
            "season": "2010/2011",
            "statsbomb_blog_url": "",
        },
    ]
    return MatchRegistry(matches)


def test_pipeline_upserts_both_event_and_narrative_chunks(
    dummy_registry: MatchRegistry,
) -> None:
    statsbomb_fetcher = MagicMock()
    statsbomb_fetcher.fetch.return_value = RawMatchData(match_id=3869685, events=[])

    event_chunker = MagicMock()
    event_chunker.chunk.return_value = [
        EventSummary(
            match_id=3869685,
            window="pressing_intensity",
            text="Pressing summary text",
            chunk_id="es_3869685_1",
        )
    ]

    narrative_fetcher = MagicMock()
    narrative_fetcher.fetch.return_value = {
        "guardian": cast(
            SourcePayload,
            {"url": "https://guardian.com", "text": "Guardian story text"},
        )
    }

    narrative_chunker = MagicMock()
    narrative_chunker.chunk.return_value = [
        NarrativeChunk(
            match_id=3869685,
            source="guardian",
            url="https://guardian.com",
            text="Guardian story text",
            chunk_id="nc_3869685_1",
        )
    ]

    embedding_model = FakeEmbeddingModel()
    vector_store = FakeVectorStore()

    pipeline = IngestionPipeline(
        registry=dummy_registry,
        statsbomb_fetcher=statsbomb_fetcher,
        event_chunker=event_chunker,
        narrative_fetcher=narrative_fetcher,
        narrative_chunker=narrative_chunker,
        embedding_model=embedding_model,
        vector_store=vector_store,
    )

    result = pipeline.run(match_ids=[3869685])

    assert result.matches_processed == 1
    assert result.matches_failed == 0
    assert result.systemic_failures == 0
    assert result.total_chunks_stored == 2
    assert len(vector_store.chunks_by_id) == 2
    assert "es_3869685_1" in vector_store.chunks_by_id
    assert "nc_3869685_1" in vector_store.chunks_by_id


def test_pipeline_is_idempotent(dummy_registry: MatchRegistry) -> None:
    statsbomb_fetcher = MagicMock()
    statsbomb_fetcher.fetch.return_value = RawMatchData(match_id=3869685, events=[])

    event_chunker = MagicMock()
    event_chunker.chunk.return_value = [
        EventSummary(
            match_id=3869685,
            window="pressing_intensity",
            text="Pressing summary text",
            chunk_id="es_3869685_1",
        )
    ]

    narrative_fetcher = MagicMock()
    narrative_fetcher.fetch.return_value = {
        "guardian": cast(
            SourcePayload,
            {"url": "https://guardian.com", "text": "Guardian story text"},
        )
    }

    narrative_chunker = MagicMock()
    narrative_chunker.chunk.return_value = [
        NarrativeChunk(
            match_id=3869685,
            source="guardian",
            url="https://guardian.com",
            text="Guardian story text",
            chunk_id="nc_3869685_1",
        )
    ]

    embedding_model = FakeEmbeddingModel()
    vector_store = FakeVectorStore()

    pipeline = IngestionPipeline(
        registry=dummy_registry,
        statsbomb_fetcher=statsbomb_fetcher,
        event_chunker=event_chunker,
        narrative_fetcher=narrative_fetcher,
        narrative_chunker=narrative_chunker,
        embedding_model=embedding_model,
        vector_store=vector_store,
    )

    result1 = pipeline.run(match_ids=[3869685])
    result2 = pipeline.run(match_ids=[3869685])

    assert result1.total_chunks_stored == 2
    assert result2.total_chunks_stored == 2
    assert len(vector_store.chunks_by_id) == 2


def test_pipeline_partial_ingestion_events_only(
    dummy_registry: MatchRegistry,
) -> None:
    statsbomb_fetcher = MagicMock()
    statsbomb_fetcher.fetch.return_value = RawMatchData(match_id=3869685, events=[])

    event_chunker = MagicMock()
    event_chunker.chunk.return_value = [
        EventSummary(
            match_id=3869685,
            window="pressing_intensity",
            text="Pressing summary text",
            chunk_id="es_3869685_1",
        )
    ]

    narrative_fetcher = MagicMock()
    narrative_fetcher.fetch.return_value = {}

    narrative_chunker = MagicMock()
    narrative_chunker.chunk.return_value = []

    embedding_model = FakeEmbeddingModel()
    vector_store = FakeVectorStore()

    pipeline = IngestionPipeline(
        registry=dummy_registry,
        statsbomb_fetcher=statsbomb_fetcher,
        event_chunker=event_chunker,
        narrative_fetcher=narrative_fetcher,
        narrative_chunker=narrative_chunker,
        embedding_model=embedding_model,
        vector_store=vector_store,
    )

    result = pipeline.run(match_ids=[3869685])

    assert result.matches_processed == 1
    assert result.matches_failed == 0
    assert result.systemic_failures == 0
    assert result.total_chunks_stored == 1
    assert "es_3869685_1" in vector_store.chunks_by_id


def test_pipeline_skips_failed_match_and_continues(
    dummy_registry: MatchRegistry,
) -> None:
    def mock_fetch(match_id: int) -> RawMatchData:
        if match_id == 3869685:
            raise RuntimeError("StatsBomb API network error")
        return RawMatchData(match_id=match_id, events=[])

    statsbomb_fetcher = MagicMock()
    statsbomb_fetcher.fetch.side_effect = mock_fetch

    event_chunker = MagicMock()
    event_chunker.chunk.return_value = [
        EventSummary(
            match_id=3754058,
            window="pressing_intensity",
            text="Pressing summary text",
            chunk_id="es_3754058_1",
        )
    ]

    narrative_fetcher = MagicMock()
    narrative_fetcher.fetch.return_value = {}

    narrative_chunker = MagicMock()
    narrative_chunker.chunk.return_value = []

    embedding_model = FakeEmbeddingModel()
    vector_store = FakeVectorStore()

    pipeline = IngestionPipeline(
        registry=dummy_registry,
        statsbomb_fetcher=statsbomb_fetcher,
        event_chunker=event_chunker,
        narrative_fetcher=narrative_fetcher,
        narrative_chunker=narrative_chunker,
        embedding_model=embedding_model,
        vector_store=vector_store,
    )

    result = pipeline.run()

    assert result.matches_processed == 1
    assert result.matches_failed == 1
    assert result.systemic_failures == 0
    assert result.total_chunks_stored == 1
    assert "es_3754058_1" in vector_store.chunks_by_id


def test_pipeline_reports_systemic_store_failure(
    dummy_registry: MatchRegistry,
) -> None:
    statsbomb_fetcher = MagicMock()
    statsbomb_fetcher.fetch.return_value = RawMatchData(match_id=3869685, events=[])

    event_chunker = MagicMock()
    event_chunker.chunk.return_value = [
        EventSummary(
            match_id=3869685,
            window="pressing",
            text="Pressing text",
            chunk_id="es_sys_1",
        )
    ]

    narrative_fetcher = MagicMock()
    narrative_fetcher.fetch.return_value = {}
    narrative_chunker = MagicMock()
    narrative_chunker.chunk.return_value = []

    embedding_model = FakeEmbeddingModel()
    failing_vector_store = FakeVectorStore()
    failing_vector_store.upsert = MagicMock(  # type: ignore[method-assign]
        side_effect=RuntimeError("ChromaDB disk error")
    )

    pipeline = IngestionPipeline(
        registry=dummy_registry,
        statsbomb_fetcher=statsbomb_fetcher,
        event_chunker=event_chunker,
        narrative_fetcher=narrative_fetcher,
        narrative_chunker=narrative_chunker,
        embedding_model=embedding_model,
        vector_store=failing_vector_store,
    )

    result = pipeline.run(match_ids=[3869685])

    assert result.matches_processed == 0
    assert result.matches_failed == 0
    assert result.systemic_failures == 1


def test_pipeline_with_real_fixture_based_fetchers(
    tmp_path: Path, dummy_registry: MatchRegistry
) -> None:
    match_dir = tmp_path / "3869685"
    match_dir.mkdir(parents=True)
    events_file = match_dir / "events.json"
    dummy_events = [
        {
            "id": "e1",
            "type": {"name": "Starting XI"},
            "team": {"name": "Argentina"},
            "tactics": {"formation": "433", "lineup": []},
        }
    ]
    events_file.write_text(json.dumps(dummy_events), encoding="utf-8")

    statsbomb_fetcher = StatsBombFetcher(raw_dir=tmp_path)
    narrative_fetcher = NarrativeFetcher(raw_dir=tmp_path)

    event_chunker = EventSummaryChunker()
    narrative_chunker = NarrativeChunker()
    embedding_model = FakeEmbeddingModel()
    vector_store = FakeVectorStore()

    pipeline = IngestionPipeline(
        registry=dummy_registry,
        statsbomb_fetcher=statsbomb_fetcher,
        event_chunker=event_chunker,
        narrative_fetcher=narrative_fetcher,
        narrative_chunker=narrative_chunker,
        embedding_model=embedding_model,
        vector_store=vector_store,
    )

    result = pipeline.run(match_ids=[3869685])

    assert result.matches_processed == 1
    assert result.total_chunks_stored == 6  # 6 analytical window EventSummaries
    assert len(vector_store.chunks_by_id) == 6


def test_cli_main_exit_codes(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from footballanalyst.ingestion.cli import main

    mock_pipeline = MagicMock()
    monkeypatch.setattr(
        "footballanalyst.ingestion.cli.build_pipeline", lambda: mock_pipeline
    )

    # Success case -> exit code 0
    mock_pipeline.run.return_value = IngestionResult(
        matches_processed=1,
        matches_failed=0,
        systemic_failures=0,
        total_chunks_stored=2,
        elapsed_seconds=0.5,
    )
    assert main(["--match-ids", "3869685"]) == 0

    # Match fetch failure case -> exit code 1 with warning banner
    mock_pipeline.run.return_value = IngestionResult(
        matches_processed=1,
        matches_failed=1,
        systemic_failures=0,
        total_chunks_stored=2,
        elapsed_seconds=0.5,
    )
    assert main(["--match-ids", "3869685"]) == 1
    captured = capsys.readouterr()
    assert "[WARNING] Data fetch/chunking failed on 1 match(es)" in captured.out

    # Systemic store failure case -> exit code 2 with critical error banner
    mock_pipeline.run.return_value = IngestionResult(
        matches_processed=0,
        matches_failed=0,
        systemic_failures=1,
        total_chunks_stored=0,
        elapsed_seconds=0.5,
    )
    assert main(["--match-ids", "3869685"]) == 2
    captured_sys = capsys.readouterr()
    assert (
        "[CRITICAL ERROR] Systemic vector store / embedding failures "
        "occurred on 1 match(es)!" in captured_sys.out
    )
