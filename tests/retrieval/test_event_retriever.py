import pytest

from footballanalyst.ingestion.types import EventSummary
from footballanalyst.retrieval.event_retriever import EventRetriever
from footballanalyst.store.vector_store import ScoredChunk
from tests.fakes import FakeVectorStore


def test_event_retriever_returns_top_k_results() -> None:
    store = FakeVectorStore()
    scored_chunks = [
        ScoredChunk(
            chunk=EventSummary(
                match_id=1,
                window="0-15",
                text=f"Event summary chunk {i}",
                chunk_id=f"1_event_{i}",
                chunk_type="event_summary",
                source="statsbomb",
            ),
            score=1.0 - (i * 0.05),
        )
        for i in range(10)
    ]
    store.query_responses[("event_summaries", 1)] = scored_chunks

    retriever = EventRetriever(vector_store=store)
    results = retriever.retrieve(query_embedding=[0.1] * 384, match_id=1, top_k=5)

    assert len(results) == 5
    assert results[0].chunk.chunk_id == "1_event_0"


def test_event_retriever_filters_by_match_id() -> None:
    store = FakeVectorStore()
    m1_chunk = EventSummary(
        match_id=1,
        window="0-15",
        text="Match 1 summary",
        chunk_id="1_event_1",
        chunk_type="event_summary",
        source="statsbomb",
    )
    m2_chunk = EventSummary(
        match_id=2,
        window="0-15",
        text="Match 2 summary",
        chunk_id="2_event_1",
        chunk_type="event_summary",
        source="statsbomb",
    )
    store.query_responses[("event_summaries", 1)] = [ScoredChunk(chunk=m1_chunk, score=0.9)]
    store.query_responses[("event_summaries", 2)] = [ScoredChunk(chunk=m2_chunk, score=0.85)]

    retriever = EventRetriever(vector_store=store)
    results = retriever.retrieve(query_embedding=[0.1] * 384, match_id=1, top_k=5)

    assert len(results) == 1
    assert results[0].chunk.match_id == 1
    assert results[0].chunk.chunk_id == "1_event_1"


def test_event_retriever_returns_empty_list_for_unknown_match() -> None:
    store = FakeVectorStore()
    retriever = EventRetriever(vector_store=store)
    results = retriever.retrieve(query_embedding=[0.1] * 384, match_id=99, top_k=5)

    assert results == []


def test_event_retriever_returns_chunks_ordered_by_score_descending() -> None:
    store = FakeVectorStore()
    c1 = EventSummary(
        match_id=1,
        window="0-15",
        text="Chunk 1",
        chunk_id="1_event_1",
        chunk_type="event_summary",
        source="statsbomb",
    )
    c2 = EventSummary(
        match_id=1,
        window="15-30",
        text="Chunk 2",
        chunk_id="1_event_2",
        chunk_type="event_summary",
        source="statsbomb",
    )
    c3 = EventSummary(
        match_id=1,
        window="30-45",
        text="Chunk 3",
        chunk_id="1_event_3",
        chunk_type="event_summary",
        source="statsbomb",
    )

    # Provide out of order scores
    store.query_responses[("event_summaries", 1)] = [
        ScoredChunk(chunk=c1, score=0.3),
        ScoredChunk(chunk=c2, score=0.9),
        ScoredChunk(chunk=c3, score=0.6),
    ]

    retriever = EventRetriever(vector_store=store)
    results = retriever.retrieve(query_embedding=[0.1] * 384, match_id=1, top_k=5)

    assert [r.score for r in results] == [0.9, 0.6, 0.3]
    assert [r.chunk.chunk_id for r in results] == ["1_event_2", "1_event_3", "1_event_1"]
