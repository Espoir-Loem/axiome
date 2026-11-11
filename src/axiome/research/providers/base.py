"""Common interface of search providers."""

from __future__ import annotations

import json
import urllib.parse
from dataclasses import dataclass
from typing import Any, Protocol

from axiome.core.errors import ResearchError
from axiome.research.extract import main_text
from axiome.research.fetch import Fetcher
from axiome.verification.epistemic import Reliability, Source, SourceKind


@dataclass(frozen=True, slots=True)
class Document:
    source: Source
    title: str
    text: str  # plain text (summary, snippet or extracted page)


class SearchProvider(Protocol):
    name: str

    def search(self, query: str, language: str, limit: int) -> list[Document]: ...


def load_json(fetcher: Fetcher, url: str) -> Any:
    raw = fetcher.get(url)
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ResearchError("research.bad_response", url=url, detail=exc) from exc


def organization(url: str) -> str:
    """Approximate registrable domain: two independent pages of one site count once."""
    host = (urllib.parse.urlsplit(url).hostname or "").lower().removeprefix("www.")
    labels = host.split(".")
    return ".".join(labels[-2:]) if len(labels) >= 2 else host


def web_source(url: str, name: str) -> Source:
    return Source(
        id=f"web:{url}",
        name=name or organization(url),
        kind=SourceKind.OTHER,
        reliability=Reliability.MEDIUM,
        organization=organization(url),
        url=url,
    )


def page_document(fetcher: Fetcher, url: str, title: str, snippet: str) -> Document:
    """Snippet plus the page's main text when it can be read (failures keep the snippet)."""
    text = snippet
    try:
        html = fetcher.get(url).decode("utf-8", errors="replace")
        body = main_text(html)
        text = f"{snippet}\n{body}" if body else snippet
    except ResearchError:
        pass
    return Document(web_source(url, organization(url)), title, text)
