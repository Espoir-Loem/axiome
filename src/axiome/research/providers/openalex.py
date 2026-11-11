"""OpenAlex (no key): scholarly works with their abstracts. Used in deep research."""

from __future__ import annotations

from typing import Any

from axiome.research.fetch import Fetcher, build_url
from axiome.research.providers.base import Document, load_json
from axiome.verification.epistemic import Reliability, Source, SourceKind

ENDPOINT = "https://api.openalex.org/works"


def abstract(inverted: dict[str, list[int]] | None) -> str:
    """Rebuild an abstract from OpenAlex's inverted index (word -> positions)."""
    if not inverted:
        return ""
    slots: dict[int, str] = {}
    for word, positions in inverted.items():
        for pos in positions:
            slots[pos] = word
    return " ".join(slots[i] for i in sorted(slots))


def _venue(work: dict[str, Any]) -> str:
    location = work.get("primary_location") or {}
    source = location.get("source") or {}
    return str(source.get("display_name") or "")


class OpenAlex:
    name = "OpenAlex"
    deep = True  # scholarly literature: only for deep research or expert level

    def __init__(self, fetcher: Fetcher) -> None:
        self.fetcher = fetcher

    def search(self, query: str, language: str, limit: int) -> list[Document]:
        params: dict[str, str | int] = {
            "search": query,
            "per-page": limit,
            "filter": "has_abstract:true",
        }
        found = load_json(self.fetcher, build_url(ENDPOINT, params))
        docs: list[Document] = []
        for work in found.get("results", [])[:limit]:
            text = abstract(work.get("abstract_inverted_index"))
            if not text:
                continue
            url = str(work.get("doi") or work.get("id") or "")
            venue = _venue(work)
            source = Source(
                id=f"openalex:{work.get('id', url)}",
                name=venue or "OpenAlex",
                kind=SourceKind.PUBLICATION,
                reliability=Reliability.HIGH,
                organization=venue or url,
                url=url,
            )
            docs.append(Document(source, str(work.get("display_name", "")), text))
        return docs
