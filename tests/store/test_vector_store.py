from pathlib import Path

import pytest

from footballanalyst.ingestion.types import EventSummary, NarrativeChunk
from footballanalyst.store.vector_store import ScoredChunk, VectorStore
from tests.fakes import FakeVectorStore


def test_scored_chunk_dataclass() -> None:
    chunk = EventSummary(
        match_id=3869685,
        window="first_15_mins",
        text="High pressing intensity",
        chunk_id="es_1",
    )
    scored = ScoredChunk(chunk=chunk, score=0.95)
    assert scored.chunk == chunk
    assert scored.score == 0.95


def test_fake_vector_store_upsert_and_query() -> None:
    fake_store = FakeVectorStore()
    chunk = EventSummary(
        match_id=3869685,
        window="first_15_mins",
        text="Offline unit test text",
        chunk_id="es_offline_01",
    )
    embedding = [0.1] * 384
    fake_store.upsert(chunks=[chunk], embeddings=[embedding])

    scored = ScoredChunk(chunk=chunk, score=0.98)
    fake_store.query_responses[("event_summaries", 3869685)] = [scored]

    results = fake_store.query(
        embedding=embedding,
        collection="event_summaries",
        match_id=3869685,
        top_k=5,
    )
    assert len(results) == 1
    assert results[0].chunk.chunk_id == "es_offline_01"
    assert results[0].score == 0.98
    assert len(fake_store.upserted_chunks) == 1


def test_fake_vector_store_query_filters_by_match_id() -> None:
    fake_store = FakeVectorStore()
    chunk1 = EventSummary(match_id=101, window="w1", text="Match 101", chunk_id="c1")
    chunk2 = EventSummary(match_id=102, window="w1", text="Match 102", chunk_id="c2")

    fake_store.query_responses[("event_summaries", 101)] = [
        ScoredChunk(chunk=chunk1, score=0.9)
    ]
    fake_store.query_responses[("event_summaries", 102)] = [
        ScoredChunk(chunk=chunk2, score=0.85)
    ]

    res_101 = fake_store.query(
        embedding=[0.0] * 384, collection="event_summaries", match_id=101
    )
    res_102 = fake_store.query(
        embedding=[0.0] * 384, collection="event_summaries", match_id=102
    )

    assert len(res_101) == 1
    assert res_101[0].chunk.match_id == 101
    assert len(res_102) == 1
    assert res_102[0].chunk.match_id == 102


@pytest.mark.integration
def test_vector_store_empty_upsert_does_not_raise(tmp_path: Path) -> None:
    store = VectorStore(persist_directory=tmp_path)
    store.upsert(chunks=[], embeddings=[])


@pytest.mark.integration
def test_upsert_then_query_returns_chunk(tmp_path: Path) -> None:
    store = VectorStore(persist_directory=tmp_path)
    chunk = EventSummary(
        match_id=3869685,
        window="first_15_mins",
        text="High pressing intensity from Argentina",
        chunk_id="es_3869685_01",
        chunk_type="event_summary",
        source="statsbomb",
    )
    embedding = [0.1] * 384

    store.upsert(chunks=[chunk], embeddings=[embedding])

    results: list[ScoredChunk] = store.query(
        embedding=embedding,
        collection="event_summaries",
        match_id=3869685,
        top_k=5,
    )

    assert len(results) == 1
    assert isinstance(results[0].chunk, EventSummary)
    assert results[0].chunk.chunk_id == "es_3869685_01"
    assert results[0].chunk.text == "High pressing intensity from Argentina"
    assert results[0].chunk.match_id == 3869685
    assert results[0].chunk.window == "first_15_mins"
    # Cosine distance for identical vector is 0.0, so similarity score = 1.0
    assert results[0].score > 0.99


@pytest.mark.integration
def test_upsert_is_idempotent(tmp_path: Path) -> None:
    store = VectorStore(persist_directory=tmp_path)
    chunk = EventSummary(
        match_id=3869685,
        window="first_15_mins",
        text="High pressing intensity from Argentina",
        chunk_id="es_3869685_01",
    )
    embedding = [0.1] * 384

    store.upsert(chunks=[chunk], embeddings=[embedding])
    store.upsert(chunks=[chunk], embeddings=[embedding])

    results = store.query(
        embedding=embedding,
        collection="event_summaries",
        match_id=3869685,
        top_k=10,
    )

    assert len(results) == 1


@pytest.mark.integration
def test_query_filters_by_match_id(tmp_path: Path) -> None:
    store = VectorStore(persist_directory=tmp_path)
    chunk_match1 = EventSummary(
        match_id=1001,
        window="p1",
        text="Match 1001 event summary text",
        chunk_id="es_1001_01",
    )
    chunk_match2 = EventSummary(
        match_id=1002,
        window="p1",
        text="Match 1002 event summary text",
        chunk_id="es_1002_01",
    )
    embedding1 = [0.1] * 384
    embedding2 = [0.2] * 384

    store.upsert(
        chunks=[chunk_match1, chunk_match2],
        embeddings=[embedding1, embedding2],
    )

    results_1001 = store.query(
        embedding=embedding1,
        collection="event_summaries",
        match_id=1001,
        top_k=5,
    )

    assert len(results_1001) == 1
    assert results_1001[0].chunk.match_id == 1001
    assert results_1001[0].chunk.chunk_id == "es_1001_01"


@pytest.mark.integration
def test_narrative_chunk_upsert_and_query(tmp_path: Path) -> None:
    store = VectorStore(persist_directory=tmp_path)
    chunk = NarrativeChunk(
        match_id=3869685,
        source="guardian",
        url="https://theguardian.com/football/2022/dec/18/world-cup-final",
        text="Argentina won a thrilling final in Lusail.",
        chunk_id="nc_3869685_01",
        chunk_type="narrative",
    )
    embedding = [0.05] * 384

    store.upsert(chunks=[chunk], embeddings=[embedding])

    results = store.query(
        embedding=embedding,
        collection="narrative_chunks",
        match_id=3869685,
        top_k=5,
    )

    assert len(results) == 1
    assert isinstance(results[0].chunk, NarrativeChunk)
    assert results[0].chunk.chunk_id == "nc_3869685_01"
    assert results[0].chunk.source == "guardian"
    assert (
        results[0].chunk.url
        == "https://theguardian.com/football/2022/dec/18/world-cup-final"
    )
