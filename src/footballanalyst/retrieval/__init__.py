"""Retrieval package."""

from footballanalyst.retrieval.event_retriever import EventRetriever
from footballanalyst.retrieval.hybrid_retriever import HybridRetriever
from footballanalyst.retrieval.narrative_retriever import NarrativeRetriever
from footballanalyst.retrieval.retriever import HybridRetrieverProtocol
from footballanalyst.retrieval.types import RankedChunk, RetrievedContext

__all__ = [
    "EventRetriever",
    "NarrativeRetriever",
    "HybridRetriever",
    "HybridRetrieverProtocol",
    "RankedChunk",
    "RetrievedContext",
]
