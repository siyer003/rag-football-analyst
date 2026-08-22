from dataclasses import dataclass

from footballanalyst.ingestion.types import Chunk


@dataclass
class RankedChunk:
    """A Chunk with its position in the final merged result and its RRF score."""

    chunk: Chunk
    rrf_score: float
    rank: int


@dataclass
class RetrievedContext:
    """The ordered set of Chunks returned by HybridRetriever for a given Query."""

    chunks: list[RankedChunk]
