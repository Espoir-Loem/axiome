"""DuckDuckGo Instant Answer API (official, no key): a short abstract with its origin."""

from __future__ import annotations

from axiome.research.fetch import Fetcher, build_url
from axiome.research.providers.base import Document, load_json, organization
from axiome.verification.epistemic import Reliability, Source, SourceKind

ENDPOINT = "https://api.duckduckgo.com/"


class DuckDuckGo:
    name = "DuckDuckGo"
    deep = False

    def __init__(self, fetcher: Fetcher) -> None:
        self.fetcher = fetcher

    def search(self, query: str, language: str, limit: int) -> list[Document]:
        params: dict[str, str | int] = {
            "q": query,
            "format": "json",
            "no_html": 1,
            "skip_disambig": 1,
            "kl": f"{language}-{language}",
        }
        found = load_json(self.fetcher, build_url(ENDPOINT, params))
        text, url = str(found.get("AbstractText", "")), str(found.get("AbstractURL", ""))
        if not text or not url:
            return []
        name = str(found.get("AbstractSource", "")) or organization(url)
        source = Source(
            id=f"web:{url}",
            name=name,
            kind=SourceKind.REFERENCE,
            reliability=Reliability.MEDIUM,
            organization=organization(url),
            url=url,
        )
        return [Document(source, str(found.get("Heading", "")), text)][:limit]
