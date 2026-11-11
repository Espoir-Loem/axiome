"""SearXNG meta-search engine (self-hosted, no key): aggregates many engines."""

from __future__ import annotations

from axiome.research.fetch import Fetcher, build_url
from axiome.research.providers.base import Document, load_json, page_document


class SearXNG:
    name = "SearXNG"
    deep = False

    def __init__(self, fetcher: Fetcher, base_url: str, read_pages: bool = True) -> None:
        self.fetcher = fetcher
        self.base_url = base_url.rstrip("/")
        self.read_pages = read_pages

    def search(self, query: str, language: str, limit: int) -> list[Document]:
        params = {"q": query, "format": "json", "language": language}
        found = load_json(self.fetcher, build_url(f"{self.base_url}/search", params))
        docs = []
        for item in found.get("results", [])[:limit]:
            url, title, snippet = (
                str(item["url"]),
                str(item.get("title", "")),
                str(item.get("content", "")),
            )
            docs.append(page_document(self.fetcher, url, title, snippet, read=self.read_pages))
        return docs
