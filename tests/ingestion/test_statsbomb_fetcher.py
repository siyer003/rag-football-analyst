import json
from pathlib import Path

from footballanalyst.ingestion.statsbomb_fetcher import StatsBombFetcher
from footballanalyst.ingestion.types import RawMatchData


def test_fetcher_reads_from_cache_and_extracts_deterministic_metadata(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data" / "raw"
    match_dir = data_dir / "3869685"
    match_dir.mkdir(parents=True, exist_ok=True)

    fake_events = [
        {
            "id": "event-1",
            "type": {"name": "Starting XI"},
            "team": {"name": "Argentina"},
            "tactics": {
                "formation": 433,
                "lineup": [{"player": {"name": "Emiliano Martínez"}}],
            },
        },
        {
            "id": "event-2",
            "type": {"name": "Starting XI"},
            "team": {"name": "France"},
            "tactics": {
                "formation": 4231,
                "lineup": [{"player": {"name": "Hugo Lloris"}}],
            },
        },
        {
            "id": "event-3",
            "type": {"name": "Shot"},
            "team": {"name": "Argentina"},
            "shot": {"outcome": {"name": "Goal"}, "statsbomb_xg": 0.78},
        },
    ]

    (match_dir / "events.json").write_text(json.dumps(fake_events))

    fetcher = StatsBombFetcher(raw_dir=data_dir)
    res: RawMatchData = fetcher.fetch(3869685)

    assert res.match_id == 3869685
    assert len(res.events) == 3
    assert res.metadata["home_team"] == "Argentina"
    assert res.metadata["away_team"] == "France"
    assert res.metadata["home_score"] == 1
    assert res.metadata["away_score"] == 0
    assert res.metadata["starting_formations"]["Argentina"] == "433"
    assert res.metadata["starting_formations"]["France"] == "4231"
    assert "Emiliano Martínez" in res.metadata["lineups"]["Argentina"]
