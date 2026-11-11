"""Wikipedia (no key): search, then the full introduction of each article.

The introduction (several paragraphs) is read rather than the one-paragraph
summary, so the answer can give details and not only a definition.
"""

from __future__ import annotations

import urllib.parse

from axiome.research.fetch import Fetcher, build_url
from axiome.research.providers.base import Document, load_json, organization
from axiome.verification.epistemic import Reliability, Source, SourceKind


class Wikipedia:
    name = "Wikipedia"
    deep = False

    def __init__(self, fetcher: Fetcher) -> None:
        self.fetcher = fetcher

    def search(self, query: str, language: str, limit: int) -> list[Document]:
        api = f"https://{language}.wikipedia.org/w/api.php"
        params: dict[str, str | int] = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": limit,
            "format": "json",
            "utf8": 1,
        }
        found = load_json(self.fetcher, build_url(api, params))
        titles = [str(h["title"]) for h in found.get("query", {}).get("search", [])[:limit]]
        if not titles:
            return []
        intro: dict[str, str | int] = {
            "action": "query",
            "prop": "extracts",
            "exintro": 1,
            "explaintext": 1,
            "redirects": 1,
            "titles": "|".join(titles),
            "format": "json",
            "utf8": 1,
        }
        pages = load_json(self.fetcher, build_url(api, intro)).get("query", {}).get("pages", {})
        texts = {str(p.get("title")): str(p.get("extract", "")).strip() for p in pages.values()}
        docs: list[Document] = []
        for title in titles:
            text = texts.get(title, "")
            if not text:
                continue
            page = urllib.parse.quote(title.replace(" ", "_"))
            url = f"https://{language}.wikipedia.org/wiki/{page}"
            source = Source(
                id=f"wikipedia:{language}:{title}",
                name=f"Wikipedia ({language})",
                kind=SourceKind.REFERENCE,
                reliability=Reliability.HIGH,
                organization=organization(url),
                url=url,
            )
            docs.append(Document(source, title, text))
        return docs
