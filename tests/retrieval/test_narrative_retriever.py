import pytest

from footballanalyst.ingestion.types import NarrativeChunk
from footballanalyst.retrieval.narrative_retriever import NarrativeRetriever
from footballanalyst.store.vector_store import ScoredChunk
from tests.fakes import FakeVectorStore


def test_narrative_retriever_returns_top_k_results() -> None:
    store = FakeVectorStore()
    scored_chunks = [
        ScoredChunk(
            chunk=NarrativeChunk(
                match_id=1,
                source="guardian",
                url="https://guardian.com/article",
                text=f"Narrative chunk {i}",
                chunk_id=f"1_narrative_{i}",
                chunk_type="narrative",
            ),
            score=1.0 - (i * 0.05),
        )
        for i in range(10)
    ]
    store.query_responses[("narrative_chunks", 1)] = scored_chunks

    retriever = NarrativeRetriever(vector_store=store)
    results = retriever.retrieve(query_embedding=[0.1] * 384, match_id=1, top_k=5)

    assert len(results) == 5
    assert results[0].chunk.chunk_id == "1_narrative_0"


def test_narrative_retriever_filters_by_match_id() -> None:
    store = FakeVectorStore()
    m1_chunk = NarrativeChunk(
        match_id=1,
        source="guardian",
        url="https://guardian.com/m1",
        text="Match 1 narrative",
        chunk_id="1_narrative_1",
        chunk_type="narrative",
    )
    m2_chunk = NarrativeChunk(
        match_id=2,
        source="guardian",
        url="https://guardian.com/m2",
        text="Match 2 narrative",
        chunk_id="2_narrative_1",
        chunk_type="narrative",
    )
    store.query_responses[("narrative_chunks", 1)] = [ScoredChunk(chunk=m1_chunk, score=0.9)]
    store.query_responses[("narrative_chunks", 2)] = [ScoredChunk(chunk=m2_chunk, score=0.85)]

    retriever = NarrativeRetriever(vector_store=store)
    results = retriever.retrieve(query_embedding=[0.1] * 384, match_id=1, top_k=5)

    assert len(results) == 1
    assert results[0].chunk.match_id == 1
    assert results[0].chunk.chunk_id == "1_narrative_1"


def test_narrative_retriever_returns_empty_list_for_unknown_match() -> None:
    store = FakeVectorStore()
    retriever = NarrativeRetriever(vector_store=store)
    results = retriever.retrieve(query_embedding=[0.1] * 384, match_id=99, top_k=5)

    assert results == []


def test_narrative_retriever_returns_chunks_ordered_by_score_descending() -> None:
    store = FakeVectorStore()
    c1 = NarrativeChunk(
        match_id=1,
        source="guardian",
        url="https://guardian.com/1",
        text="Chunk 1",
        chunk_id="1_narrative_1",
        chunk_type="narrative",
    )
    c2 = NarrativeChunk(
        match_id=1,
        source="wikipedia",
        url="https://wiki.org/1",
        text="Chunk 2",
        chunk_id="1_narrative_2",
        chunk_type="narrative",
    )
    c3 = NarrativeChunk(
        match_id=1,
        source="statsbomb_blog",
        url="https://statsbomb.com/blog/1",
        text="Chunk 3",
        chunk_id="1_narrative_3",
        chunk_type="narrative",
    )

    # Provide out of order scores
    store.query_responses[("narrative_chunks", 1)] = [
        ScoredChunk(chunk=c1, score=0.4),
        ScoredChunk(chunk=c2, score=0.95),
        ScoredChunk(chunk=c3, score=0.7),
    ]

    retriever = NarrativeRetriever(vector_store=store)
    results = retriever.retrieve(query_embedding=[0.1] * 384, match_id=1, top_k=5)

    assert [r.score for r in results] == [0.95, 0.7, 0.4]
    assert [r.chunk.chunk_id for r in results] == ["1_narrative_2", "1_narrative_3", "1_narrative_1"]
