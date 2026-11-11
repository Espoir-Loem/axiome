"""Wikipedia (no key): search API + REST page summaries."""

from __future__ import annotations

import urllib.parse

from axiome.research.fetch import Fetcher, build_url
from axiome.research.providers.base import Document, load_json
from axiome.verification.epistemic import Reliability, Source, SourceKind


class Wikipedia:
    name = "Wikipedia"

    def __init__(self, fetcher: Fetcher) -> None:
        self.fetcher = fetcher

    def search(self, query: str, language: str, limit: int) -> list[Document]:
        host = f"https://{language}.wikipedia.org"
        params: dict[str, str | int] = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": limit,
            "format": "json",
            "utf8": 1,
        }
        found = load_json(self.fetcher, build_url(f"{host}/w/api.php", params))
        docs: list[Document] = []
        for hit in found.get("query", {}).get("search", [])[:limit]:
            title = str(hit["title"])
            page = urllib.parse.quote(title.replace(" ", "_"), safe="")
            summary = load_json(self.fetcher, f"{host}/api/rest_v1/page/summary/{page}")
            extract = str(summary.get("extract", "")).strip()
            if not extract:
                continue
            url = (
                summary.get("content_urls", {})
                .get("desktop", {})
                .get("page", f"{host}/wiki/{page}")
            )
            source = Source(
                id=f"wikipedia:{language}:{title}",
                name=f"Wikipedia ({language})",
                kind=SourceKind.REFERENCE,
                reliability=Reliability.HIGH,
                organization="wikimedia",
                url=str(url),
            )
            docs.append(Document(source, title, extract))
        return docs
