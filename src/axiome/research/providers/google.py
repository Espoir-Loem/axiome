"""Google Programmable Search (Custom Search JSON API): needs an API key and an engine id.

Scraping Google's result pages is forbidden by its terms of service; this official
API is the supported way to query Google.
"""

from __future__ import annotations

from axiome.research.fetch import Fetcher, build_url
from axiome.research.providers.base import Document, load_json, page_document, web_source

ENDPOINT = "https://www.googleapis.com/customsearch/v1"


class GoogleCSE:
    name = "Google"

    def __init__(
        self, fetcher: Fetcher, api_key: str, engine_id: str, read_pages: bool = True
    ) -> None:
        self.fetcher = fetcher
        self.api_key = api_key
        self.engine_id = engine_id
        self.read_pages = read_pages

    def search(self, query: str, language: str, limit: int) -> list[Document]:
        params: dict[str, str | int] = {
            "key": self.api_key,
            "cx": self.engine_id,
            "q": query,
            "num": limit,
            "hl": language,
        }
        found = load_json(self.fetcher, build_url(ENDPOINT, params))
        docs = []
        for item in found.get("items", [])[:limit]:
            url, title, snippet = (
                str(item["link"]),
                str(item.get("title", "")),
                str(item.get("snippet", "")),
            )
            if self.read_pages:
                docs.append(page_document(self.fetcher, url, title, snippet))
            else:
                docs.append(Document(web_source(url, ""), title, snippet))
        return docs
