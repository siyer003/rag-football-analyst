"""Data ingestion package."""

from footballanalyst.ingestion.event_chunker import EventSummaryChunker
from footballanalyst.ingestion.statsbomb_fetcher import StatsBombFetcher
from footballanalyst.ingestion.types import (
    Chunk,
    EventSummary,
    NarrativeChunk,
    RawMatchData,
)

__all__ = [
    "Chunk",
    "EventSummary",
    "EventSummaryChunker",
    "NarrativeChunk",
    "RawMatchData",
    "StatsBombFetcher",
]

