import tomllib
from pathlib import Path
from typing import Any, Self

from footballanalyst.ingestion.types import MatchConfig


class MatchRegistry:
    """Registry of matches in the Football Analyst corpus."""

    def __init__(self, matches: list[dict[str, Any]]) -> None:
        self._matches: dict[int, str] = {}
        self._details: dict[int, MatchConfig] = {}
        for idx, m in enumerate(matches):
            raw_id = m.get("match_id")
            raw_label = m.get("label")
            if raw_id is None or raw_label is None:
                msg = f"Corpus entry at index {idx} missing 'match_id' or 'label': {m}"
                raise ValueError(msg)
            try:
                match_id = int(str(raw_id))
            except ValueError as err:
                msg = f"Corpus entry at index {idx} has invalid match_id '{raw_id}'"
                raise ValueError(msg) from err

            self._matches[match_id] = str(raw_label)
            self._details[match_id] = MatchConfig(
                match_id=match_id,
                label=str(raw_label),
                competition=str(m.get("competition", "")),
                season=str(m.get("season", "")),
                match_date=str(m.get("match_date", "")),
                statsbomb_blog_url=str(m.get("statsbomb_blog_url", "")),
            )

    def get_match(self, match_id: int) -> MatchConfig:
        """Return match configuration for a given match_id."""
        if match_id not in self:
            raise KeyError(f"Match ID {match_id} not found in registry")
        return self._details[match_id]

    @classmethod
    def load(cls, path: str | Path = "config/corpus.toml") -> Self:
        """Load MatchRegistry from a TOML configuration file."""
        config_path = Path(path)
        if not config_path.is_file():
            raise FileNotFoundError(f"Corpus configuration file not found at {path}")

        with config_path.open("rb") as f:
            data = tomllib.load(f)

        matches_data: list[dict[str, Any]] = data.get("matches", [])
        return cls(matches_data)

    def match_ids(self) -> list[int]:
        """Return list of all match IDs registered in the corpus."""
        return list(self._matches.keys())

    def matches(self) -> list[tuple[int, str]]:
        """Return list of (match_id, label) tuples registered in the corpus."""
        return [(mid, self.label(mid)) for mid in self.match_ids()]

    def label(self, match_id: int) -> str:
        """Return human-readable label for a given match_id."""
        if match_id not in self:
            raise KeyError(f"Match ID {match_id} not found in registry")
        return self._matches[match_id]

    def contains(self, match_id: int) -> bool:
        """Check if a match_id is registered in the corpus."""
        return match_id in self._matches

    def __contains__(self, match_id: object) -> bool:
        """Enable native 'in' operator checks for match_id in registry."""
        return match_id in self._matches
