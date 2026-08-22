import json
from pathlib import Path

from footballanalyst.ingestion.event_chunker import EventSummaryChunker
from footballanalyst.ingestion.types import EventSummary, RawMatchData

FIXTURE_PATH = Path("tests/fixtures/events_3869685.json")


def load_fixture_raw_data() -> RawMatchData:
    events = json.loads(FIXTURE_PATH.read_text())
    return RawMatchData(
        match_id=3869685,
        events=events,
        metadata={
            "home_team": "Argentina",
            "away_team": "France",
            "competition": "FIFA World Cup",
            "season": "2022",
        },
    )


def test_chunker_produces_at_least_one_summary_per_window_type() -> None:
    raw_data = load_fixture_raw_data()
    chunker = EventSummaryChunker()
    summaries = chunker.chunk(raw_data)

    windows = {s.window for s in summaries}
    expected_windows = {
        "pressing_intensity",
        "xg_by_phase",
        "substitutions",
        "top_ball_carriers",
        "shot_map",
        "key_passes",
    }

    assert expected_windows.issubset(windows)
    assert len(windows) >= 6


def test_pressing_summary_contains_ppda_and_periods() -> None:
    raw_data = load_fixture_raw_data()
    chunker = EventSummaryChunker()
    summaries = chunker.chunk(raw_data)

    pressing = next(s for s in summaries if s.window == "pressing_intensity")
    assert "Per-Period Attacking 60% Pressing Intensity & PPDA Proxy" in pressing.text
    assert "[First Half]" in pressing.text
    assert "PPDA proxy" in pressing.text


def test_substitutions_summary_contains_formation_context() -> None:
    raw_data = load_fixture_raw_data()
    chunker = EventSummaryChunker()
    summaries = chunker.chunk(raw_data)

    sub_summary = next(s for s in summaries if s.window == "substitutions")
    assert "Substitutions and Tactical Adjustments" in sub_summary.text
    assert "Formation" in sub_summary.text


def test_ball_carriers_calculates_progressive_forward_distance() -> None:
    raw_data = load_fixture_raw_data()
    chunker = EventSummaryChunker()
    summaries = chunker.chunk(raw_data)

    carriers = next(s for s in summaries if s.window == "top_ball_carriers")
    assert "Top Ball Carriers by Progressive Distance" in carriers.text
    assert "progressive carries (>=10m forward)" in carriers.text
    assert "meters forward towards goal" in carriers.text


def test_event_summary_has_required_fields() -> None:
    raw_data = load_fixture_raw_data()
    chunker = EventSummaryChunker()
    summaries = chunker.chunk(raw_data)

    assert len(summaries) > 0
    chunk_ids = set()

    for s in summaries:
        assert isinstance(s, EventSummary)
        assert s.match_id == 3869685
        assert s.chunk_type == "event_summary"
        assert s.source == "statsbomb"
        assert len(s.window) > 0
        assert len(s.text) > 0
        assert len(s.chunk_id) > 0
        assert s.chunk_id not in chunk_ids
        chunk_ids.add(s.chunk_id)


def test_chunk_ids_are_deterministic() -> None:
    raw_data = load_fixture_raw_data()
    chunker = EventSummaryChunker()

    res1 = chunker.chunk(raw_data)
    res2 = chunker.chunk(raw_data)

    ids1 = [s.chunk_id for s in res1]
    ids2 = [s.chunk_id for s in res2]

    assert ids1 == ids2
