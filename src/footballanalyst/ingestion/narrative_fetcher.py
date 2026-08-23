import json
import logging
import os
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
from bs4 import BeautifulSoup, Tag

from footballanalyst.ingestion.types import SourcePayload

logger = logging.getLogger(__name__)

GUARDIAN_SEARCH_URL = "https://content.guardianapis.com/search"
WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"
WIKIPEDIA_BASE_URL = "https://en.wikipedia.org/wiki/"

TEAM_ALIASES: dict[str, list[str]] = {
    "Tottenham Hotspur": ["Tottenham", "Tottenham Hotspur", "Spurs"],
    "Liverpool": ["Liverpool", "Reds"],
    "Manchester City": ["Manchester City", "Man City", "City"],
    "Manchester United": ["Manchester United", "Man United", "Man Utd", "United"],
    "Real Madrid": ["Real Madrid", "Madrid"],
    "Barcelona": ["Barcelona", "Barca"],
    "Argentina": ["Argentina"],
    "France": ["France"],
    "Croatia": ["Croatia"],
    "England": ["England"],
    "Italy": ["Italy"],
    "Spain": ["Spain"],
}

HARD_EXCLUSIONS = [
    "player-ratings",
    "ratings",
    "live",
    "matchday-live",
    "as-it-happened",
    "blog",
    "preview",
    "previews",
    "team-news",
    "build-up",
    "buildup",
    "predicted-lineups",
    "how-they-line-up",
    "head-to-head",
    "gallery",
    "quiz",
    "podcast",
    "transfer",
    "rumours",
]

MEDIUM_SIGNAL_PATTERNS = [
    "claim champions league",
    "fold without a fight",
    "champions league final",
    "world cup final",
    "euro 2020 final",
    "euro 2024 final",
    "world cup semi-final",
    "match report",
]

WEAK_SIGNAL_PATTERNS = [
    "sink",
    "sinks",
    "crowned",
    "triumph",
    "win",
    "wins",
    "winner",
    "beat",
    "beats",
    "defeat",
    "victory",
    "crush",
    "crushes",
]


class GuardianArticleNotFoundError(Exception):
    """Exception raised when automated Guardian search fails to select
    an unambiguous match report.
    """

    def __init__(
        self,
        match_id: int,
        match_label: str,
        reason: str,
        scored_candidates: list[Any],
    ) -> None:
        msg = f"Match {match_id} ({match_label}) Guardian fetch failed: {reason}"
        super().__init__(msg)
        self.match_id = match_id
        self.match_label = match_label
        self.reason = reason
        self.scored_candidates = scored_candidates


@dataclass
class ScoredCandidate:
    """Scored candidate item from Guardian Content API."""

    item: dict[str, Any]
    title: str
    url: str
    score: float
    text: str
    slug: str


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
        match_date: str | None = None,
        teams: list[str] | None = None,
    ) -> dict[str, SourcePayload]:
        """Fetch raw narrative text and URLs for a match across available sources."""
        match_dir = self.raw_dir / str(match_id)
        match_dir.mkdir(parents=True, exist_ok=True)

        results: dict[str, SourcePayload] = {}

        strategy_map: dict[str, Callable[[], SourcePayload | None]] = {
            "guardian": lambda: self._fetch_guardian(
                match_id, match_label, competition, match_date, teams
            ),
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

    def _resolve_team_names(
        self, teams: list[str] | None, match_label: str
    ) -> list[str]:
        """Resolve plain team name strings from upstream metadata or match label."""
        if teams:
            cleaned = [t.strip() for t in teams if t and t.strip()]
            if cleaned:
                return cleaned

        teams_part = match_label.split("—")[-1] if "—" in match_label else match_label
        teams_part = (
            teams_part.split("-")[-1]
            if "-" in teams_part and "—" not in match_label
            else teams_part
        )
        raw_parts = re.split(r"\b(?:vs\.?|v)\b", teams_part, flags=re.IGNORECASE)
        return [re.sub(r"[^\w\s]", "", p).strip() for p in raw_parts if p.strip()]

    def _build_team_patterns(self, resolved_teams: list[str]) -> list[re.Pattern[str]]:
        """Build word-boundary regex search patterns for teams without dropping
        unknown teams.

        Note: The generic-word fallback for unrecognized team names (stripping
        fc/cf/afc/club/de/la) can occasionally produce an overly broad single-word
        pattern for teams with common-word names (e.g. 'Arsenal FC' -> 'Arsenal').
        This is a known limitation for future matches outside the curated corpus.
        """
        patterns: list[re.Pattern[str]] = []
        for team in resolved_teams:
            aliases = TEAM_ALIASES.get(team, [])
            if not aliases:
                variants = [team]
                core_words = [
                    w
                    for w in team.split()
                    if w.lower() not in {"fc", "cf", "afc", "club", "de", "la"}
                ]
                if core_words and core_words[0] not in variants:
                    variants.append(core_words[0])
                aliases = variants

            pattern_str = r"\b(" + "|".join(re.escape(a) for a in aliases) + r")\b"
            patterns.append(re.compile(pattern_str, re.IGNORECASE))

        return patterns

    def _resolve_match_date(
        self, match_id: int, match_date: str | None, match_label: str
    ) -> str | None:
        """Resolve match date from structured metadata or fallback regex."""
        if match_date and match_date.strip():
            return match_date.strip()

        date_match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", match_label)
        if date_match:
            fallback_date = date_match.group(1)
            logger.warning(
                "No structured match_date provided for match %d; "
                "using label regex fallback date '%s'",
                match_id,
                fallback_date,
            )
            return fallback_date

        logger.warning(
            "No match date available for match %d; date proximity scoring disabled",
            match_id,
        )
        return None

    def _build_guardian_query_string(
        self, resolved_teams: list[str], match_label: str
    ) -> str:
        """Build a broad boolean search query (using alias OR clauses)
        to maximize retrieval recall.
        """
        if len(resolved_teams) >= 2:
            clauses: list[str] = []
            for team in resolved_teams:
                aliases = TEAM_ALIASES.get(team, [team])
                variant_strs = [f'"{a}"' if " " in a else a for a in aliases]
                if len(variant_strs) == 1:
                    clauses.append(variant_strs[0])
                else:
                    clauses.append("(" + " OR ".join(variant_strs) + ")")
            return " AND ".join(clauses)

        cleaned_label = re.sub(r"[^\w\s]", " ", match_label).strip()
        return cleaned_label

    def _are_near_duplicates(
        self, cand1: ScoredCandidate, cand2: ScoredCandidate
    ) -> bool:
        """Determine if two candidate items represent near-duplicate stories."""
        slug1 = cand1.slug
        slug2 = cand2.slug

        p1 = slug1.split("/")[-1].split("-match-report")[0].split("-player-ratings")[0]
        p2 = slug2.split("/")[-1].split("-match-report")[0].split("-player-ratings")[0]
        if p1 and p1 == p2:
            return True

        t1_words = set(re.findall(r"\w+", cand1.title.lower()))
        t2_words = set(re.findall(r"\w+", cand2.title.lower()))
        if not t1_words or not t2_words:
            return False
        jaccard = len(t1_words & t2_words) / len(t1_words | t2_words)
        return jaccard >= 0.70

    def _score_and_select_guardian_article(
        self,
        match_id: int,
        match_label: str,
        results: list[dict[str, Any]],
        team_patterns: list[re.Pattern[str]],
        target_date_str: str | None,
    ) -> SourcePayload:
        """Score candidate items and select unambiguous top match report."""
        scored_candidates: list[ScoredCandidate] = []

        for item in results:
            title = str(item.get("webTitle", ""))
            slug = str(item.get("id", ""))
            url = str(item.get("webUrl", ""))
            comb_text = f"{title} {slug}".lower()

            hard_excluded = False
            for bad in HARD_EXCLUSIONS:
                pattern = r"\b" + re.escape(bad) + r"\b"
                if re.search(pattern, comb_text):
                    hard_excluded = True
                    break
            if hard_excluded:
                continue

            if len(team_patterns) >= 2 and not (
                team_patterns[0].search(comb_text)
                and team_patterns[1].search(comb_text)
            ):
                continue

            score = 50.0
            if item.get("sectionId") == "football":
                score += 20.0

            pub_date_str = str(item.get("webPublicationDate", ""))[:10]
            if target_date_str and pub_date_str:
                try:
                    dt_pub = datetime.strptime(pub_date_str, "%Y-%m-%d")
                    dt_target = datetime.strptime(target_date_str, "%Y-%m-%d")
                    days_diff = (dt_pub - dt_target).days

                    if days_diff in (0, 1):
                        score += 30.0
                    elif days_diff == 2:
                        score += 15.0
                    elif days_diff == 3:
                        score += 5.0
                    elif days_diff == -1:
                        score -= 10.0
                except ValueError:
                    pass
            else:
                score += 0.0

            raw_tags = item.get("tags", [])
            tags = [
                str(t.get("id", ""))
                for t in raw_tags
                if isinstance(t, dict) and t.get("type") == "tone"
            ]
            if "tone/matchreports" in tags:
                score += 50.0

            strong_signal = (
                "-match-report" in slug
                or "/match-report" in slug
                or bool(re.search(r"\b\d+-\d+\b", title))
            )
            medium_signal = any(
                p in title.lower() or p in slug.lower() for p in MEDIUM_SIGNAL_PATTERNS
            )
            weak_signal = any(p in title.lower() for p in WEAK_SIGNAL_PATTERNS)

            if strong_signal:
                score += 50.0
            elif medium_signal:
                score += 30.0
            elif weak_signal:
                score += 20.0

            fields = item.get("fields", {})
            body_text = fields.get("bodyText", "") if isinstance(fields, dict) else ""
            text = str(body_text).strip()
            scored_candidates.append(
                ScoredCandidate(
                    item=item,
                    title=title,
                    url=url,
                    score=score,
                    text=text,
                    slug=slug,
                )
            )

        qualified = [c for c in scored_candidates if c.score >= 120.0]
        if not qualified:
            raise GuardianArticleNotFoundError(
                match_id=match_id,
                match_label=match_label,
                reason="No candidate reached minimum confidence threshold S_min=120.0",
                scored_candidates=scored_candidates,
            )

        story_clusters: list[list[ScoredCandidate]] = []
        for cand in sorted(qualified, key=lambda x: x.score, reverse=True):
            placed = False
            for cluster in story_clusters:
                rep = cluster[0]
                if self._are_near_duplicates(cand, rep):
                    cluster.append(cand)
                    placed = True
                    break
            if not placed:
                story_clusters.append([cand])

        top_cluster = story_clusters[0]
        c1 = max(top_cluster, key=lambda x: x.score)
        s1 = c1.score

        s2 = 0.0
        if len(story_clusters) > 1:
            c2_rep = max(story_clusters[1], key=lambda x: x.score)
            s2 = c2_rep.score

        if s2 > 0:
            margin = (s1 - s2) / s1
            if margin < 0.15:
                msg = (
                    f"Ambiguous candidate margin: top={s1:.1f}, "
                    f"second={s2:.1f}, margin={margin:.2f} < 0.15"
                )
                raise GuardianArticleNotFoundError(
                    match_id=match_id,
                    match_label=match_label,
                    reason=msg,
                    scored_candidates=scored_candidates,
                )

        logger.info(
            "Guardian article selected: match_id=%d, url=%s, "
            "score=%.1f, runner_up_score=%.1f, margin=%.2f",
            match_id,
            c1.url,
            s1,
            s2,
            (s1 - s2) / s1 if s1 > 0 else 0.0,
        )

        return {"url": c1.url, "text": c1.text}

    def _fetch_guardian(
        self,
        match_id: int,
        match_label: str,
        competition: str,
        match_date: str | None = None,
        teams: list[str] | None = None,
    ) -> SourcePayload | None:
        if not self.guardian_api_key:
            logger.info("GUARDIAN_API_KEY not set; skipping Guardian fetch.")
            return None

        resolved_teams = self._resolve_team_names(teams, match_label)
        target_date_str = self._resolve_match_date(match_id, match_date, match_label)
        team_patterns = self._build_team_patterns(resolved_teams)
        query_str = self._build_guardian_query_string(resolved_teams, match_label)

        params: dict[str, str] = {
            "q": query_str,
            "section": "football",
            "show-fields": "bodyText,webUrl,headline",
            "show-tags": "all",
            "page-size": "50",
            "api-key": self.guardian_api_key,
        }

        if target_date_str:
            try:
                dt = datetime.strptime(target_date_str, "%Y-%m-%d")
                params["from-date"] = (dt - timedelta(days=1)).strftime("%Y-%m-%d")
                params["to-date"] = (dt + timedelta(days=3)).strftime("%Y-%m-%d")
            except ValueError:
                pass

        try:
            response = httpx.get(
                GUARDIAN_SEARCH_URL, params=params, timeout=self.timeout
            )
            if response.status_code != 200:
                logger.warning(
                    "Guardian API returned status code %d for query '%s'",
                    response.status_code,
                    params.get("q", ""),
                )
                return None

            data = response.json()
            results = data.get("response", {}).get("results", [])
            if not results:
                return None

            return self._score_and_select_guardian_article(
                match_id=match_id,
                match_label=match_label,
                results=results,
                team_patterns=team_patterns,
                target_date_str=target_date_str,
            )
        except GuardianArticleNotFoundError as err:
            logger.warning("Guardian article not found: %s", err)
            return None
        except (httpx.RequestError, ValueError, KeyError) as err:
            logger.warning("Guardian fetch failed: %s", err)
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
