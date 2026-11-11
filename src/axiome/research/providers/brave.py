"""Brave Search API: an independent index of the whole web (free tier with a key)."""

from __future__ import annotations

from axiome.research.fetch import Fetcher, build_url
from axiome.research.providers.base import Document, load_json_with, page_document

ENDPOINT = "https://api.search.brave.com/res/v1/web/search"


class BraveSearch:
    name = "Brave"
    deep = False

    def __init__(self, fetcher: Fetcher, api_key: str, read_pages: bool = True) -> None:
        self.fetcher = fetcher
        self.api_key = api_key
        self.read_pages = read_pages

    def search(self, query: str, language: str, limit: int) -> list[Document]:
        params: dict[str, str | int] = {"q": query, "count": limit, "search_lang": language}
        headers = {"X-Subscription-Token": self.api_key}
        found = load_json_with(self.fetcher, build_url(ENDPOINT, params), headers)
        results = found.get("web", {}).get("results", [])[:limit]
        return [
            page_document(
                self.fetcher,
                str(r["url"]),
                str(r.get("title", "")),
                str(r.get("description", "")),
                read=self.read_pages,
            )
            for r in results
        ]
