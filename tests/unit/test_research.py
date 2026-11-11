"""Web research building blocks, with recorded responses."""

from __future__ import annotations

import json
import re
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
from axiome.verification.epistemic import Reliability, Source, SourceKind, Status
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
    assert [d.title for d in docs] == ["Photon", "Photonique"]  # the empty page is skipped
    assert docs[0].source.organization == "wikipedia.org" and docs[0].text.startswith(PHOTON_FR)
    assert docs[0].source.url == "https://fr.wikipedia.org/wiki/Photon"
    assert (
        Wikipedia(FakeFetcher({"list=search": b'{"query": {"search": []}}'})).search("x", "fr", 3)
        == []
    )


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
    assert [type(e) for e in events] == [Searching, Searching, SourceFound, SourceFound]
    assert len(docs) == 2 and researcher.names == ["Boom", "Wikipedia"]
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
    assert found.lead is not None and found.assessment is not None
    assert {s.organization for s in found.agreeing} == {"a.org", "b.org"}
    assert [found.documents[e.doc].source.organization for e in found.points] == ["c.org"]
    assert found.assessment.status is Status.PLAUSIBLE  # two medium sources (E7)
    assert found.cited == (0, 2)
    assert digest("photon", []).lead is None


def test_setup(tmp_path: Path) -> None:
    fetcher = FakeFetcher({})
    full = Config(
        "x", google_api_key="k", google_engine_id="c", searxng_url="http://s", brave_api_key="b"
    )
    names = [p.name for p in providers(full, fetcher)]
    assert names == ["Brave", "Google", "SearXNG", "Wikipedia", "DuckDuckGo", "OpenAlex"]
    assert build_researcher(Config("x", offline=True)) is None
    built = build_researcher(Config("x", cache_dir=str(tmp_path)))
    assert built is not None and [p.name for p in built.active(False)] == [
        "Wikipedia",
        "DuckDuckGo",
    ]
    assert [p.name for p in built.active(True)][-1] == "OpenAlex"
    assert build_researcher(Config("x"), fetcher) is not None


def test_digest_uses_the_page_named_like_the_question() -> None:
    side = Document(
        web_source("https://a.org/x", "A"),
        "Interaction photon-photon",
        "L'interaction photon-photon est la diffusion d'un photon par un autre photon.",
    )
    main = Document(
        web_source("https://a.org/p", "B"),
        "Photon",
        "Il a été nommé en 1926. Le photon est une particule élémentaire de lumière. "
        "Il n'a pas de masse et va à la vitesse de la lumière.",
    )
    found = digest("photon", [side, main], ["le", "est", "une", "d", "l", "par", "un", "de"])
    assert found.lead is not None and found.lead.doc == 1
    assert found.lead.text.startswith("Le photon est")  # the definition, not the first line
    assert found.see_also == ("Interaction photon-photon",)
    assert [p.text[:6] for p in found.points] == ["Il n'a"]  # too-short sentences are dropped


def test_more_providers() -> None:
    from axiome.research.providers.brave import BraveSearch  # noqa: PLC0415
    from axiome.research.providers.duckduckgo import DuckDuckGo  # noqa: PLC0415
    from axiome.research.providers.openalex import OpenAlex, abstract  # noqa: PLC0415

    ddg = {
        "AbstractText": "Le photon est une particule.",
        "AbstractURL": "https://fr.wikipedia.org/wiki/Photon",
        "AbstractSource": "Wikipédia",
        "Heading": "Photon",
    }
    alex = {
        "results": [
            {
                "id": "https://openalex.org/W1",
                "doi": "https://doi.org/10.1/x",
                "display_name": "On photons",
                "abstract_inverted_index": {"Photons": [0], "are": [1], "quanta.": [2]},
                "primary_location": {"source": {"display_name": "Nature"}},
            },
            {"id": "https://openalex.org/W2", "abstract_inverted_index": None},
        ]
    }
    brave = {
        "web": {
            "results": [{"url": "https://phys.example.org/p", "title": "P", "description": "D."}]
        }
    }
    fetcher = FakeFetcher(
        {
            "duckduckgo.com": json.dumps(ddg).encode(),
            "openalex.org/works": json.dumps(alex).encode(),
            "search.brave.com": json.dumps(brave).encode(),
        }
    )
    d = DuckDuckGo(fetcher).search("photon", "fr", 3)
    assert d[0].source.organization == "wikipedia.org" and d[0].source.name == "Wikipédia"
    assert DuckDuckGo(FakeFetcher({"duckduckgo.com": b"{}"})).search("x", "fr", 1) == []
    o = OpenAlex(fetcher).search("photon", "en", 3)
    assert len(o) == 1 and o[0].text == "Photons are quanta." and o[0].source.name == "Nature"
    assert abstract(None) == ""
    b = BraveSearch(fetcher, "secret", read_pages=False).search("photon", "fr", 3)
    assert b[0].text == "D." and {"X-Subscription-Token": "secret"} in fetcher.headers


def test_disambiguation_page_makes_the_question_ambiguous() -> None:
    def doc(title: str, text: str) -> Document:
        src = Source(f"w:{title}", "W", SourceKind.REFERENCE, Reliability.HIGH, "w.org", "u")
        return Document(src, title, text)

    pattern = re.compile(r"peut designer")
    docs = [
        doc("Espoir", "Le mot espoir peut désigner plusieurs choses très différentes."),
        doc(
            "Nouvel Espoir", "Nouvel Espoir est un ancien parti politique israélien fondé en 2020."
        ),
    ]
    found = digest("espoir", docs, ambiguous=pattern)
    assert found.lead is None and found.see_also == ("Nouvel Espoir",)
    other = [
        docs[0],
        doc("Mercure", "Mercure est la planète la plus proche du Soleil, très chaude."),
    ]
    found = digest("mercure", other, ambiguous=pattern)
    assert found.lead is not None and found.lead.doc == 1  # the listing page is skipped
