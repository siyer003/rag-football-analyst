import json
from pathlib import Path
from typing import Any

import httpx

from footballanalyst.ingestion.types import RawMatchData

OPEN_DATA_EVENTS_URL = (
    "https://raw.githubusercontent.com/statsbomb/open-data/master/data/events/{match_id}.json"
)


class StatsBombFetcher:
    """Fetcher for StatsBomb event data with cache-first disk storage."""

    def __init__(self, raw_dir: str | Path = "data/raw") -> None:
        self.raw_dir = Path(raw_dir)

    def fetch(self, match_id: int) -> RawMatchData:
        """Fetch raw match events and metadata for a given match_id.

        Checks local cache at raw_dir/<match_id>/events.json first.
        If missing, fetches from StatsBomb open data repository and caches locally.
        """
        match_dir = self.raw_dir / str(match_id)
        events_file = match_dir / "events.json"
        metadata_file = match_dir / "metadata.json"

        if events_file.is_file():
            events = json.loads(events_file.read_text(encoding="utf-8"))
            metadata: dict[str, Any] = {}
            if metadata_file.is_file():
                metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
            else:
                metadata = self._extract_metadata(match_id, events)
            return RawMatchData(match_id=match_id, events=events, metadata=metadata)

        # Cache miss — fetch from remote repository
        url = OPEN_DATA_EVENTS_URL.format(match_id=match_id)
        response = httpx.get(url, timeout=30.0)
        response.raise_for_status()

        events_data: list[dict[str, Any]] = response.json()
        match_dir.mkdir(parents=True, exist_ok=True)
        events_file.write_text(json.dumps(events_data, indent=2), encoding="utf-8")

        extracted_metadata = self._extract_metadata(match_id, events_data)
        metadata_file.write_text(
            json.dumps(extracted_metadata, indent=2), encoding="utf-8"
        )
        return RawMatchData(
            match_id=match_id, events=events_data, metadata=extracted_metadata
        )

    def _extract_metadata(
        self, match_id: int, events: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Extract deterministic metadata from raw events."""
        starting_xi_events = [
            e for e in events if e.get("type", {}).get("name") == "Starting XI"
        ]

        home_team = "Home Team"
        away_team = "Away Team"
        lineups: dict[str, list[str]] = {}
        starting_formations: dict[str, str] = {}

        if len(starting_xi_events) >= 1:
            home_team = starting_xi_events[0].get("team", {}).get("name", "Home Team")
        if len(starting_xi_events) >= 2:
            away_team = starting_xi_events[1].get("team", {}).get("name", "Away Team")

        for e in starting_xi_events:
            team_name = e.get("team", {}).get("name", "")
            tactics = e.get("tactics", {})
            formation = str(tactics.get("formation", "Unknown"))
            starting_formations[team_name] = formation

            player_list = [
                p.get("player", {}).get("name", "Unknown Player")
                for p in tactics.get("lineup", [])
            ]
            lineups[team_name] = player_list

        home_goals = 0
        away_goals = 0
        for e in events:
            if (
                e.get("type", {}).get("name") == "Shot"
                and e.get("shot", {}).get("outcome", {}).get("name") == "Goal"
            ):
                team_name = e.get("team", {}).get("name")
                if team_name == home_team:
                    home_goals += 1
                elif team_name == away_team:
                    away_goals += 1

        return {
            "match_id": match_id,
            "home_team": home_team,
            "away_team": away_team,
            "home_score": home_goals,
            "away_score": away_goals,
            "starting_formations": starting_formations,
            "lineups": lineups,
            "managers": {home_team: "N/A", away_team: "N/A"},
        }
