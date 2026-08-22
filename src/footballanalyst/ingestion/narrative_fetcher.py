import json
import logging
import os
from collections.abc import Callable
from pathlib import Path

import httpx
from bs4 import BeautifulSoup, Tag

from footballanalyst.ingestion.types import SourcePayload

logger = logging.getLogger(__name__)

GUARDIAN_SEARCH_URL = "https://content.guardianapis.com/search"
WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"
WIKIPEDIA_BASE_URL = "https://en.wikipedia.org/wiki/"


class NarrativeFetcher:
    """Fetcher for narrative sources with disk caching."""

    def __init__(
        self,
        raw_dir: str | Path = "data/raw",
        guardian_api_key: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.raw_dir = Path(raw_dir)
        self.guardian_api_key = guardian_api_key or os.environ.get(
            "GUARDIAN_API_KEY", ""
        )
        self.timeout = timeout

    def fetch(
        self,
        match_id: int,
        match_label: str = "",
        competition: str = "",
        statsbomb_blog_url: str = "",
    ) -> dict[str, SourcePayload]:
        """Fetch raw narrative text and URLs for a match across available sources."""
        match_dir = self.raw_dir / str(match_id)
        match_dir.mkdir(parents=True, exist_ok=True)

        results: dict[str, SourcePayload] = {}

        strategy_map: dict[str, Callable[[], SourcePayload | None]] = {
            "guardian": lambda: self._fetch_guardian(match_label, competition),
            "wikipedia": lambda: self._fetch_wikipedia(match_label, competition),
            "statsbomb_blog": lambda: self._fetch_statsbomb_blog(statsbomb_blog_url),
        }

        for source, fetch_fn in strategy_map.items():
            txt_file = match_dir / f"{source}.txt"
            json_file = match_dir / f"{source}.json"

            if txt_file.is_file():
                cached_payload = self._load_cache_files(txt_file, json_file)
                if cached_payload["text"]:
                    results[source] = cached_payload
                    continue

            # Fetch fresh from remote source
            payload = fetch_fn()
            if payload and payload["text"]:
                self._save_cache_files(txt_file, json_file, payload)
                results[source] = payload

        return results

    def _load_cache_files(self, txt_file: Path, json_file: Path) -> SourcePayload:
        text = txt_file.read_text(encoding="utf-8").strip()
        url = ""
        if json_file.is_file():
            try:
                meta = json.loads(json_file.read_text(encoding="utf-8"))
                url = str(meta.get("url", ""))
            except (json.JSONDecodeError, AttributeError):
                url = ""

        return {"url": url, "text": text}

    def _save_cache_files(
        self, txt_file: Path, json_file: Path, payload: SourcePayload
    ) -> None:
        txt_file.write_text(payload["text"], encoding="utf-8")
        meta = {"url": payload["url"]}
        json_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    def _extract_paragraph_texts(
        self, container: Tag | BeautifulSoup | None
    ) -> list[str]:
        if container is None:
            return []
        return [
            p.get_text().strip()
            for p in container.find_all("p")
            if p.get_text().strip()
        ]

    def _fetch_guardian(
        self, match_label: str, competition: str
    ) -> SourcePayload | None:
        if not self.guardian_api_key:
            logger.info("GUARDIAN_API_KEY not set; skipping Guardian fetch.")
            return None

        query = f"{match_label} {competition}".strip()
        params = {
            "q": query,
            "show-fields": "bodyText,webUrl",
            "api-key": self.guardian_api_key,
        }

        try:
            response = httpx.get(
                GUARDIAN_SEARCH_URL, params=params, timeout=self.timeout
            )
            if response.status_code != 200:
                logger.warning(
                    "Guardian API returned status code %d for query '%s'",
                    response.status_code,
                    query,
                )
                return None
            data = response.json()
            results = data.get("response", {}).get("results", [])
            if not results:
                return None
            first = results[0]
            url = str(first.get("webUrl", ""))
            text = str(first.get("fields", {}).get("bodyText", "")).strip()
            if text:
                return {"url": url, "text": text}
        except (httpx.RequestError, ValueError, KeyError) as err:
            logger.warning("Guardian fetch failed: %s", err)
            return None

        return None

    def _fetch_wikipedia(
        self, match_label: str, competition: str
    ) -> SourcePayload | None:
        query = match_label or competition
        if not query:
            return None

        try:
            # Search Wikipedia API for matching article title
            search_params = {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json",
            }
            resp = httpx.get(
                WIKIPEDIA_API_URL, params=search_params, timeout=self.timeout
            )
            if resp.status_code != 200:
                return None

            search_results = resp.json().get("query", {}).get("search", [])
            if not search_results:
                return None

            page_title = search_results[0].get("title", "")
            if not page_title:
                return None

            url = f"{WIKIPEDIA_BASE_URL}{page_title.replace(' ', '_')}"
            page_resp = httpx.get(url, timeout=self.timeout)
            if page_resp.status_code != 200:
                return None

            soup = BeautifulSoup(page_resp.text, "html.parser")
            # Scope extraction to Wikipedia's main content container (#mw-content-text)
            content_container = soup.find(id="mw-content-text")
            paragraphs = self._extract_paragraph_texts(content_container)
            text = "\n\n".join(paragraphs)

            if text:
                return {"url": url, "text": text}
        except (httpx.RequestError, ValueError, KeyError) as err:
            logger.warning("Wikipedia fetch failed: %s", err)
            return None

        return None

    def _fetch_statsbomb_blog(self, blog_url: str) -> SourcePayload | None:
        if not blog_url:
            return None

        try:
            resp = httpx.get(blog_url, timeout=self.timeout)
            if resp.status_code != 200:
                return None

            soup = BeautifulSoup(resp.text, "html.parser")
            article = soup.find("article")
            container = article if article else soup
            paragraphs = self._extract_paragraph_texts(container)

            text = "\n\n".join(paragraphs)
            if text:
                return {"url": blog_url, "text": text}
        except (httpx.RequestError, ValueError, KeyError) as err:
            logger.warning("StatsBomb blog fetch failed: %s", err)
            return None

        return None
