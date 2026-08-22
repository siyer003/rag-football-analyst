from dataclasses import dataclass, field
from typing import Any, TypedDict


@dataclass
class RawMatchData:
    """Raw match data containing StatsBomb events list and match metadata."""

    match_id: int
    events: list[dict[str, Any]]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EventSummary:
    """Analytical text chunk derived from structured StatsBomb event data."""

    match_id: int
    window: str
    text: str
    chunk_id: str
    chunk_type: str = "event_summary"
    source: str = "statsbomb"


class SourcePayload(TypedDict):
    """Payload representing fetched raw narrative content and source URL."""

    url: str
    text: str


class MatchConfig(TypedDict, total=False):
    """Typed dictionary representing match metadata configuration."""

    match_id: int
    label: str
    competition: str
    season: str
    statsbomb_blog_url: str


@dataclass
class NarrativeChunk:
    """Paragraph-sized text chunk derived from a tactical article or match report."""

    match_id: int
    source: str
    url: str
    text: str
    chunk_id: str
    chunk_type: str = "narrative"


Chunk = EventSummary | NarrativeChunk
