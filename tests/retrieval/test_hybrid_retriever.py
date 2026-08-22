"""Tests for HybridRetriever — the single retrieval seam exposed to ask()."""

import pytest

from footballanalyst.ingestion.types import EventSummary, NarrativeChunk
from footballanalyst.retrieval.hybrid_retriever import HybridRetriever
from footballanalyst.retrieval.types import RetrievedContext
from footballanalyst.store.vector_store import ScoredChunk
from tests.fakes import FakeEmbeddingModel

# ---------------------------------------------------------------------------
# Fake sub-retrievers — injected via constructor; test the HybridRetriever
# public interface only.
# ---------------------------------------------------------------------------


class FakeSubRetriever:
    """Fake sub-retriever that returns a pre-configured list of ScoredChunks."""

    def __init__(self, scored_chunks: list[ScoredChunk]) -> None:
        self._scored_chunks = scored_chunks

    def retrieve(
        self,
        query_embedding: list[float],
        match_id: int,
        top_k: int = 5,
    ) -> list[ScoredChunk]:
        # Intentionally ignores top_k: returns all pre-configured chunks so
        # tests can exercise the HybridRetriever's own cap logic directly.
        return self._scored_chunks


def _make_event_chunk(i: int, match_id: int = 8658) -> ScoredChunk:
    return ScoredChunk(
        chunk=EventSummary(
            match_id=match_id,
            window=f"{i * 15}-{(i + 1) * 15}",
            text=f"Event summary {i}",
            chunk_id=f"evt_{match_id}_{i}",
            chunk_type="event_summary",
            source="statsbomb",
        ),
        score=1.0 - i * 0.05,
    )


def _make_narrative_chunk(i: int, match_id: int = 8658) -> ScoredChunk:
    return ScoredChunk(
        chunk=NarrativeChunk(
            match_id=match_id,
            source="guardian",
            url=f"https://example.com/{i}",
            text=f"Narrative chunk {i}",
            chunk_id=f"nar_{match_id}_{i}",
            chunk_type="narrative",
        ),
        score=1.0 - i * 0.05,
    )


# ---------------------------------------------------------------------------
# Test 1: chunks from both sources are present in context
# ---------------------------------------------------------------------------


def test_hybrid_retriever_returns_chunks_from_both_sources() -> None:
    event_chunks = [_make_event_chunk(i) for i in range(2)]
    narrative_chunks = [_make_narrative_chunk(i) for i in range(3)]

    retriever = HybridRetriever(
        event_retriever=FakeSubRetriever(event_chunks),
        narrative_retriever=FakeSubRetriever(narrative_chunks),
        embedding_model=FakeEmbeddingModel(),
    )

    context = retriever.retrieve("why did the high press work?", match_id=8658)

    assert isinstance(context, RetrievedContext)
    chunk_types = {rc.chunk.chunk_type for rc in context.chunks}
    assert "event_summary" in chunk_types
    assert "narrative" in chunk_types


# ---------------------------------------------------------------------------
# Test 2: result is capped at top 8
# ---------------------------------------------------------------------------


def test_hybrid_retriever_limits_to_top_8() -> None:
    event_chunks = [_make_event_chunk(i) for i in range(10)]
    narrative_chunks = [_make_narrative_chunk(i) for i in range(10)]

    retriever = HybridRetriever(
        event_retriever=FakeSubRetriever(event_chunks),
        narrative_retriever=FakeSubRetriever(narrative_chunks),
        embedding_model=FakeEmbeddingModel(),
    )

    context = retriever.retrieve("how did City press?", match_id=8658)

    assert len(context.chunks) == 8


# ---------------------------------------------------------------------------
# Test 3: RRF output is ordered by score descending; higher rank → higher score
# ---------------------------------------------------------------------------


def test_rrf_scores_higher_ranked_results_more() -> None:
    # 5 event chunks ranked 1..5, 5 narrative chunks ranked 1..5.
    # RRF score for rank r: 1 / (60 + r).
    # rank-1 score = 1/61 ≈ 0.016393
    # rank-5 score = 1/65 ≈ 0.015385
    # So rank-1 chunks (score 1/61) must appear before rank-5 chunks (score 1/65).
    event_chunks = [_make_event_chunk(i) for i in range(5)]
    narrative_chunks = [_make_narrative_chunk(i) for i in range(5)]

    retriever = HybridRetriever(
        event_retriever=FakeSubRetriever(event_chunks),
        narrative_retriever=FakeSubRetriever(narrative_chunks),
        embedding_model=FakeEmbeddingModel(),
    )

    context = retriever.retrieve("formation shifts at 60 min?", match_id=8658)

    scores = [rc.rrf_score for rc in context.chunks]
    # Scores must be non-increasing (sorted descending).
    assert scores == sorted(scores, reverse=True), "RRF scores must be descending"

    # Rank-1 from either list gets 1/61; top-8 from a 5+5 pool ends at
    # rank-4 score = 1/(60+4) = 1/64.
    assert pytest.approx(context.chunks[0].rrf_score, rel=1e-6) == 1 / 61
    assert pytest.approx(context.chunks[-1].rrf_score, rel=1e-6) == 1 / 64


# ---------------------------------------------------------------------------
# Test 4: empty sub-retriever results produce an empty context
# ---------------------------------------------------------------------------


def test_hybrid_retriever_returns_empty_context_for_empty_sub_results() -> None:
    retriever = HybridRetriever(
        event_retriever=FakeSubRetriever([]),
        narrative_retriever=FakeSubRetriever([]),
        embedding_model=FakeEmbeddingModel(),
    )

    context = retriever.retrieve("xG breakdown?", match_id=8658)

    assert isinstance(context, RetrievedContext)
    assert len(context.chunks) == 0
