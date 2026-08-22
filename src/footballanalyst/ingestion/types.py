from dataclasses import dataclass, field
from typing import Any


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
