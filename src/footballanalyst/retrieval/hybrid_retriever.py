from typing import Protocol

from footballanalyst.embedding.base import EmbeddingModel
from footballanalyst.retrieval.types import RankedChunk, RetrievedContext
from footballanalyst.store.vector_store import ScoredChunk


class _SubRetrieverProtocol(Protocol):
    """Structural protocol for EventRetriever and NarrativeRetriever."""

    def retrieve(
        self,
        query_embedding: list[float],
        match_id: int,
        top_k: int = 5,
    ) -> list[ScoredChunk]: ...


def _rrf_score(rank: int, k: int = 60) -> float:
    """Return the Reciprocal Rank Fusion score for a 1-based rank position."""
    return 1.0 / (k + rank)


class HybridRetriever:
    """Merges EventRetriever and NarrativeRetriever results via RRF (ADR-0001).

    RRF produces a rank-position-weighted interleaving of the two sub-lists.
    Because event and narrative chunks live in disjoint collections, no chunk_id
    can appear in both lists, so the cross-list score accumulation in the
    canonical RRF formula never fires; each chunk receives a score from exactly
    one list.

    Tiebreak: event chunks are placed before narrative chunks in the input list
    passed to the stable sort, so equal-scored chunks preserve that insertion
    order. This is an arbitrary-but-stable tiebreak chosen for determinism and
    testability, not because event chunks carry higher semantic weight.
    """

    _TOP_K_PER_RETRIEVER: int = 5
    _TOP_N_RESULT: int = 8

    def __init__(
        self,
        event_retriever: _SubRetrieverProtocol,
        narrative_retriever: _SubRetrieverProtocol,
        embedding_model: EmbeddingModel,
    ) -> None:
        self._event_retriever = event_retriever
        self._narrative_retriever = narrative_retriever
        self._embedding_model = embedding_model

    def retrieve(self, query: str, match_id: int) -> RetrievedContext:
        """Retrieve and RRF-merge event + narrative chunks for a query."""
        embedding = self._embedding_model.embed([query])[0]

        event_scored = self._event_retriever.retrieve(
            embedding, match_id, top_k=self._TOP_K_PER_RETRIEVER
        )
        narrative_scored = self._narrative_retriever.retrieve(
            embedding, match_id, top_k=self._TOP_K_PER_RETRIEVER
        )

        # Assign RRF scores using 1-based rank within each sub-list.
        # Event sub-list is first so the stable sort produces event-first
        # ordering on score ties (see class docstring).
        ranked: list[tuple[float, ScoredChunk]] = []
        for sub_list in [event_scored, narrative_scored]:
            for rank, sc in enumerate(sub_list, start=1):
                ranked.append((_rrf_score(rank), sc))

        ranked.sort(key=lambda t: t[0], reverse=True)

        result_chunks = [
            RankedChunk(chunk=sc.chunk, rrf_score=score, rank=position)
            for position, (score, sc) in enumerate(
                ranked[: self._TOP_N_RESULT], start=1
            )
        ]

        return RetrievedContext(chunks=result_chunks)
