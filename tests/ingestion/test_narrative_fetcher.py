import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from footballanalyst.ingestion.narrative_fetcher import NarrativeFetcher

FIXTURE_DIR = Path("tests/fixtures/narrative")


def test_fetcher_uses_cache_if_raw_file_exists(tmp_path: Path) -> None:
    match_id = 3869685
    raw_dir = tmp_path / "raw"
    match_dir = raw_dir / str(match_id)
    match_dir.mkdir(parents=True, exist_ok=True)

    # Pre-populate raw_dir from actual fixture files
    for source in ["guardian", "wikipedia", "statsbomb_blog"]:
        shutil.copy(
            FIXTURE_DIR / f"{source}_{match_id}.txt",
            match_dir / f"{source}.txt",
        )
        shutil.copy(
            FIXTURE_DIR / f"{source}_{match_id}.json",
            match_dir / f"{source}.json",
        )

    fetcher = NarrativeFetcher(raw_dir=raw_dir)

    # Mock httpx to ensure no HTTP requests are attempted when cached
    with patch.object(
        httpx,
        "get",
        side_effect=AssertionError("HTTP call should not occur on cache hit"),
    ):
        results = fetcher.fetch(match_id=match_id, match_label="Argentina vs France")

    assert "guardian" in results
    assert "theguardian.com" in results["guardian"]["url"]
    assert "Argentina won the 2022 World Cup" in results["guardian"]["text"]

    assert "wikipedia" in results
    assert "wikipedia.org" in results["wikipedia"]["url"]
    assert "The 2022 FIFA World Cup final" in results["wikipedia"]["text"]

    assert "statsbomb_blog" in results
    assert "statsbomb.com" in results["statsbomb_blog"]["url"]
    assert "Tactical Breakdown" in results["statsbomb_blog"]["text"]


def test_fetcher_skips_guardian_when_api_key_not_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GUARDIAN_API_KEY", raising=False)
    raw_dir = tmp_path / "raw"

    fetcher = NarrativeFetcher(raw_dir=raw_dir, guardian_api_key=None)

    with patch.object(httpx, "get") as mock_get:

        def mock_http_get(url: str, **kwargs: object) -> MagicMock:
            resp = MagicMock()
            resp.status_code = 200
            if "wikipedia" in url or "api.php" in url:
                resp.json.return_value = {
                    "query": {"search": [{"title": "2022_FIFA_World_Cup_Final"}]}
                }
                resp.text = (
                    "<html><body><div id='mw-content-text'>"
                    "<p>Wikipedia content paragraph.</p></div></body></html>"
                )

            else:
                resp.text = "<p>StatsBomb blog content paragraph.</p>"
            return resp

        mock_get.side_effect = mock_http_get

        results = fetcher.fetch(
            match_id=3869685,
            match_label="Argentina vs France",
            competition="FIFA World Cup",
            statsbomb_blog_url="https://statsbomb.com/blog1",
        )

    # Guardian should be skipped gracefully, not present or empty
    assert "guardian" not in results or results["guardian"]["text"] == ""


def test_fetcher_handles_http_failures_gracefully(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    fetcher = NarrativeFetcher(raw_dir=raw_dir, guardian_api_key="test_key")

    with patch.object(httpx, "get") as mock_get:
        # Simulate network failures / timeouts for all HTTP requests
        mock_get.side_effect = httpx.RequestError("Network error", request=MagicMock())

        # Should complete without raising uncaught exception
        results = fetcher.fetch(
            match_id=3869685,
            match_label="Argentina vs France",
            competition="FIFA World Cup",
            statsbomb_blog_url="https://statsbomb.com/blog1",
        )

    assert isinstance(results, dict)
    # All failed HTTP calls result in skipped/empty results, not crashes
    for source_data in results.values():
        assert isinstance(source_data, dict)


def test_fetcher_scopes_wikipedia_extraction_to_mw_content_text(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    fetcher = NarrativeFetcher(raw_dir=raw_dir)

    html_content = (
        "<html><body>"
        "<nav><p>Header Nav Bar Paragraph (Should be ignored)</p></nav>"
        "<div id='mw-content-text'>"
        "<p>Main Article Body Paragraph (Should be extracted)</p></div>"
        "<footer><p>Footer Copyright Paragraph (Should be ignored)</p></footer>"
        "</body></html>"
    )

    with patch.object(httpx, "get") as mock_get:

        def mock_http_get(url: str, **kwargs: object) -> MagicMock:
            resp = MagicMock()
            resp.status_code = 200
            if "w/api.php" in url:
                resp.json.return_value = {
                    "query": {"search": [{"title": "2022_FIFA_World_Cup_Final"}]}
                }
            else:
                resp.text = html_content
            return resp

        mock_get.side_effect = mock_http_get

        results = fetcher.fetch(match_id=3869685, match_label="Argentina vs France")

    assert "wikipedia" in results
    extracted_text = results["wikipedia"]["text"]
    assert "Main Article Body Paragraph" in extracted_text
    assert "Header Nav Bar Paragraph" not in extracted_text
    assert "Footer Copyright Paragraph" not in extracted_text


def test_fetcher_fetches_and_caches_from_http(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    fetcher = NarrativeFetcher(raw_dir=raw_dir, guardian_api_key="fake_guardian_key")

    with patch.object(httpx, "get") as mock_get:

        def mock_http_get(url: str, **kwargs: object) -> MagicMock:
            resp = MagicMock()
            resp.status_code = 200
            if "guardianapis.com" in url:
                resp.json.return_value = {
                    "response": {
                        "results": [
                            {
                                "id": (
                                    "football/2022/dec/18/"
                                    "world-cup-final-argentina-france-match-report"
                                ),
                                "webTitle": (
                                    "Argentina beat France on penalties to win "
                                    "World Cup after stunning final"
                                ),
                                "webUrl": "https://theguardian.com/article_test",
                                "sectionId": "football",
                                "webPublicationDate": "2022-12-18T21:00:00Z",
                                "tags": [{"id": "tone/matchreports", "type": "tone"}],
                                "fields": {"bodyText": "Guardian body article text."},
                            }
                        ]
                    }
                }
            elif "w/api.php" in url:
                resp.json.return_value = {
                    "query": {"search": [{"title": "2022_FIFA_World_Cup_Final"}]}
                }
            elif "wikipedia.org/wiki/" in url:
                resp.text = (
                    "<html><body><div id='mw-content-text'>"
                    "<p>Wikipedia article content.</p></div></body></html>"
                )

            elif "statsbomb.com" in url:
                resp.text = (
                    "<html><body><article><p>StatsBomb article content.</p>"
                    "</article></body></html>"
                )
            return resp

        mock_get.side_effect = mock_http_get

        results = fetcher.fetch(
            match_id=3869685,
            match_label="FIFA World Cup 2022 Final — Argentina vs France",
            competition="FIFA World Cup",
            statsbomb_blog_url="https://statsbomb.com/blog_test",
        )

    match_dir = raw_dir / "3869685"
    assert (match_dir / "guardian.txt").is_file()
    assert (match_dir / "guardian.json").is_file()
    assert (match_dir / "wikipedia.txt").is_file()
    assert (match_dir / "wikipedia.json").is_file()
    assert (match_dir / "statsbomb_blog.txt").is_file()
    assert (match_dir / "statsbomb_blog.json").is_file()

    raw_txt_content = (match_dir / "guardian.txt").read_text(encoding="utf-8")
    assert not raw_txt_content.startswith("URL:")
    assert raw_txt_content == "Guardian body article text."

    sidecar_json = json.loads((match_dir / "guardian.json").read_text(encoding="utf-8"))
    assert sidecar_json["url"] == "https://theguardian.com/article_test"

    assert results["guardian"]["url"] == "https://theguardian.com/article_test"
    assert "Guardian body article text." in results["guardian"]["text"]
    assert "Wikipedia article content." in results["wikipedia"]["text"]
    assert "StatsBomb article content." in results["statsbomb_blog"]["text"]


def test_guardian_fetcher_disqualifies_previews(tmp_path: Path) -> None:
    from footballanalyst.ingestion.narrative_fetcher import (
        GuardianArticleNotFoundError,
    )

    fetcher = NarrativeFetcher(raw_dir=tmp_path / "raw", guardian_api_key="test_key")

    mock_results = [
        {
            "id": (
                "football/2019/jun/01/"
                "tottenham-liverpool-champions-league-final-player-ratings"
            ),
            "webTitle": (
                "Tottenham 0-2 Liverpool: Champions League final player ratings"
            ),
            "webUrl": "https://theguardian.com/player-ratings",
            "sectionId": "football",
            "webPublicationDate": "2019-06-01T22:00:00Z",
            "fields": {"bodyText": "Player ratings content"},
        },
        {
            "id": "football/2019/may/31/pochettino-tottenham-liverpool-preview",
            "webTitle": "Tottenham v Liverpool Champions League preview",
            "webUrl": "https://theguardian.com/preview",
            "sectionId": "football",
            "webPublicationDate": "2019-05-31T12:00:00Z",
            "fields": {"bodyText": "Preview content"},
        },
    ]

    label = "Champions League 2018/2019 Final — Tottenham Hotspur vs Liverpool"
    teams = fetcher._resolve_team_names(["Tottenham Hotspur", "Liverpool"], label)
    patterns = fetcher._build_team_patterns(teams)
    with pytest.raises(GuardianArticleNotFoundError) as exc_info:
        fetcher._score_and_select_guardian_article(
            match_id=22912,
            match_label=label,
            results=mock_results,
            team_patterns=patterns,
            target_date_str="2019-06-01",
        )

    assert "No candidate reached minimum confidence threshold" in str(exc_info.value)


def test_guardian_fetcher_converges_on_golden_urls(tmp_path: Path) -> None:
    golden_path = Path("tests/fixtures/narrative/golden_guardian_urls.json")
    golden_data: dict[str, str] = json.loads(golden_path.read_text(encoding="utf-8"))

    fetcher = NarrativeFetcher(raw_dir=tmp_path / "raw", guardian_api_key="fake_key")

    tottenham_candidates = [
        {
            "id": (
                "football/2019/jun/01/"
                "tottenham-liverpool-champions-league-final-player-ratings"
            ),
            "webTitle": (
                "Tottenham 0-2 Liverpool: Champions League final player ratings"
            ),
            "webUrl": (
                "https://www.theguardian.com/football/2019/jun/01/"
                "tottenham-liverpool-champions-league-final-player-ratings"
            ),
            "sectionId": "football",
            "webPublicationDate": "2019-06-01T22:00:22Z",
            "tags": [{"id": "tone/features", "type": "tone"}],
            "fields": {"bodyText": "Player ratings content"},
        },
        {
            "id": (
                "football/2019/jun/01/"
                "tottenham-liverpool-champions-league-final-match-report"
            ),
            "webTitle": (
                "Liverpool win Champions League final after "
                "Salah and Origi sink Tottenham"
            ),
            "webUrl": golden_data["22912"],
            "sectionId": "football",
            "webPublicationDate": "2019-06-01T20:57:05Z",
            "tags": [{"id": "tone/matchreports", "type": "tone"}],
            "fields": {"bodyText": "Liverpool win match report content"},
        },
    ]

    label = "Champions League 2018/2019 Final — Tottenham Hotspur vs Liverpool"
    teams = fetcher._resolve_team_names(["Tottenham Hotspur", "Liverpool"], label)
    patterns = fetcher._build_team_patterns(teams)
    payload = fetcher._score_and_select_guardian_article(
        match_id=22912,
        match_label=label,
        results=tottenham_candidates,
        team_patterns=patterns,
        target_date_str="2019-06-01",
    )

    assert payload["url"] == golden_data["22912"]
