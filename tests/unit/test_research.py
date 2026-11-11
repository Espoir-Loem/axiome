"""Web research building blocks, with recorded responses."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from axiome.core.config import Config
from axiome.core.errors import ResearchError
from axiome.dialogue.events import Searching, SourceFound
from axiome.research.extract import main_text, sentences
from axiome.research.fetch import CachedFetcher, HttpFetcher, build_url
from axiome.research.providers.base import Document, load_json, organization, web_source
from axiome.research.providers.google import GoogleCSE
from axiome.research.providers.searxng import SearXNG
from axiome.research.providers.wikipedia import Wikipedia
from axiome.research.rank import bm25, overlap, terms
from axiome.research.setup import build_researcher, providers
from axiome.team.researcher import Researcher, digest
from axiome.verification.epistemic import Status
from tests.fakes import PAGE, PHOTON_FR, FakeFetcher, wikipedia_routes


def test_extract_and_sentences() -> None:
    text = main_text(PAGE)
    assert "Menu" not in text and "var x" not in text and "Mentions" not in text
    assert "Einstein" in text
    parts = sentences(
        "M. Dupont a vu le chat dormir longtemps. Le chien, lui, a couru [3] très vite.\ncourt"
    )
    assert parts == [
        "M. Dupont a vu le chat dormir longtemps.",
        "Le chien, lui, a couru très vite.",
    ]


def test_ranking() -> None:
    passages = ["Le chat dort sur le canapé.", "Le photon est une particule de lumière.", "Rien."]
    ranked = bm25("photon lumière", passages, ["le", "est", "une", "de"])
    assert [r.index for r in ranked] == [1]
    assert bm25("", passages) == [] and bm25("x", []) == []
    assert terms("Le Photon, a", ["le"]) == ["photon"]
    assert overlap("le photon est rapide", "photon rapide", ["le", "est"]) == 100
    assert overlap("", "x") == 0


def test_fetch_helpers(tmp_path: Path) -> None:
    assert build_url("https://x/a", {"b": 2, "a": "é"}) == "https://x/a?a=%C3%A9&b=2"
    assert build_url("https://x", {}) == "https://x"
    with pytest.raises(ResearchError):
        HttpFetcher().get("file:///etc/passwd")
    with pytest.raises(ResearchError):
        HttpFetcher(timeout_s=0.5).get("http://127.0.0.1:9/nothing")
    inner = FakeFetcher({"x": b"payload"})
    cached = CachedFetcher(inner, tmp_path / "cache")
    assert cached.get("https://x") == b"payload" == cached.get("https://x")
    assert len(inner.calls) == 1  # second answer came from disk


def test_provider_helpers() -> None:
    assert organization("https://www.fr.example.org/page") == "example.org"
    assert organization("http://localhost/x") == "localhost"
    assert web_source("https://a.b.com/x", "").name == "b.com"
    with pytest.raises(ResearchError):
        load_json(FakeFetcher({"x": b"not json"}), "https://x")


def test_wikipedia_provider() -> None:
    docs = Wikipedia(FakeFetcher(wikipedia_routes())).search("photon", "fr", 3)
    assert len(docs) == 1  # the empty summary is skipped
    assert docs[0].source.organization == "wikimedia" and docs[0].text == PHOTON_FR
    assert docs[0].source.url == "https://fr.wikipedia.org/wiki/Photon"


def test_google_and_searxng_providers() -> None:
    google_json = {
        "items": [{"link": "https://phys.example.org/photon", "title": "P", "snippet": "S."}]
    }
    sx_json = {
        "results": [{"url": "https://cours.example.net/p", "title": "C", "content": "Snip."}]
    }
    fetcher = FakeFetcher(
        {
            "googleapis.com": json.dumps(google_json).encode(),
            "phys.example.org": PAGE.encode(),
            "searx.local": json.dumps(sx_json).encode(),
        }
    )
    g = GoogleCSE(fetcher, "key", "cx").search("photon", "fr", 3)
    assert g[0].source.organization == "example.org" and "Einstein" in g[0].text
    assert (
        GoogleCSE(fetcher, "key", "cx", read_pages=False).search("photon", "fr", 3)[0].text == "S."
    )
    s = SearXNG(fetcher, "http://searx.local/").search("photon", "fr", 3)
    assert s[0].text == "Snip."  # unreadable page: the snippet is kept
    assert (
        SearXNG(fetcher, "http://searx.local", read_pages=False).search("p", "fr", 1)[0].title
        == "C"
    )


class Boom:
    name = "Boom"

    def search(self, query: str, language: str, limit: int) -> list[Document]:
        raise ResearchError("research.fetch_failed", url="x", detail="down")


def test_researcher_streams_in_provider_order_and_survives_failures() -> None:
    wiki = Wikipedia(FakeFetcher(wikipedia_routes()))
    researcher = Researcher([Boom(), wiki])
    events = []
    gen = researcher.search("photon", "fr")
    try:
        while True:
            events.append(next(gen))
    except StopIteration as stop:
        docs = stop.value
    assert [type(e) for e in events] == [Searching, Searching, SourceFound]
    assert len(docs) == 1 and researcher.names == ["Boom", "Wikipedia"]
    assert list(Researcher([]).search("x", "fr")) == []


def test_digest_agreement_and_status() -> None:
    a = Document(
        web_source("https://a.org/1", "A"),
        "t",
        "Le photon est une particule de lumière sans masse.",
    )
    b = Document(
        web_source("https://b.org/1", "B"),
        "t",
        "Le photon est une particule de lumière, sans masse.",
    )
    c = Document(
        web_source("https://c.org/1", "C"),
        "t",
        "Einstein a reçu le prix Nobel pour le photon en 1921.",
    )
    found = digest("photon", [a, b, c], ["le", "est", "une", "de"])
    assert found.summary is not None and found.assessment is not None
    assert {s.organization for s in found.agreeing} == {"a.org", "b.org"}
    assert [e.source.organization for e in found.others] == ["c.org"]
    assert found.assessment.status is Status.PLAUSIBLE  # two medium sources (E7)
    assert digest("photon", []).summary is None


def test_setup(tmp_path: Path) -> None:
    fetcher = FakeFetcher({})
    full = Config("x", google_api_key="k", google_engine_id="c", searxng_url="http://s")
    assert [p.name for p in providers(full, fetcher)] == ["Google", "SearXNG", "Wikipedia"]
    assert build_researcher(Config("x", offline=True)) is None
    built = build_researcher(Config("x", cache_dir=str(tmp_path)))
    assert built is not None and built.names == ["Wikipedia"]
    assert build_researcher(Config("x"), fetcher) is not None
