"""Downloading Wikivoyage articles through the MediaWiki API, with a 30-day cache (TP-SRS-104)."""

import json
import re
from dataclasses import asdict, dataclass
from datetime import date

import httpx

API_URL = "https://en.wikivoyage.org/w/api.php"
LICENSE = "CC BY-SA 4.0"
LANGUAGE = "en"
CACHE_DAYS = 30
# Wikimedia's API policy asks clients to identify themselves with a way to contact them (TP-SRS-171).
DEFAULT_CONTACT_URL = "https://github.com/4-Shades/travel_planner"


@dataclass(frozen=True)
class Article:
    title: str
    revision_id: int
    url: str
    extract: str
    downloaded: date


class ArticleNotFound(Exception):
    pass


def _cache_name(title):
    return re.sub(r"[^A-Za-z0-9_-]", "_", title) + ".json"


class MediaWiki:
    def __init__(self, cache_dir, contact_url=DEFAULT_CONTACT_URL, refresh=False, timeout=30):
        self.cache_dir = cache_dir
        self.refresh = refresh
        self.timeout = timeout
        self.headers = {"User-Agent": f"TravelPlannerIngest/1.0 ({contact_url})"}

    async def article(self, title):
        """Return the article from the cache if it is under 30 days old, else download it."""
        cached = self._cached(title)
        if cached and not self.refresh and (date.today() - cached.downloaded).days < CACHE_DAYS:
            return cached
        article = await self._download(title)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        values = {**asdict(article), "downloaded": article.downloaded.isoformat()}
        (self.cache_dir / _cache_name(title)).write_text(json.dumps(values, ensure_ascii=False), encoding="utf-8")
        return article

    def _cached(self, title):
        path = self.cache_dir / _cache_name(title)
        if not path.exists():
            return None
        values = json.loads(path.read_text(encoding="utf-8"))
        return Article(**{**values, "downloaded": date.fromisoformat(values["downloaded"])})

    async def _download(self, title):
        params = {
            "action": "query",
            "format": "json",
            "formatversion": "2",
            "prop": "extracts|revisions|info",
            "explaintext": "1",
            "exsectionformat": "wiki",
            "rvprop": "ids",
            "inprop": "url",
            "redirects": "1",
            "titles": title,
        }
        async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout) as client:
            response = await client.get(API_URL, params=params)
        response.raise_for_status()
        pages = response.json().get("query", {}).get("pages", [])
        if not pages or pages[0].get("missing") or "extract" not in pages[0]:
            raise ArticleNotFound(f"Wikivoyage has no article named {title!r}")
        page = pages[0]
        return Article(
            title=page["title"],
            revision_id=page["revisions"][0]["revid"],
            url=page["canonicalurl"],
            extract=page["extract"],
            downloaded=date.today(),
        )
