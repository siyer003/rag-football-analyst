"""Data ingestion package."""

from footballanalyst.ingestion.event_chunker import EventSummaryChunker
from footballanalyst.ingestion.statsbomb_fetcher import StatsBombFetcher
from footballanalyst.ingestion.types import EventSummary, RawMatchData

__all__ = [
    "EventSummary",
    "EventSummaryChunker",
    "RawMatchData",
    "StatsBombFetcher",
]
