"""Recorded web responses: research tests never touch the network."""

from __future__ import annotations

import json
from collections.abc import Callable

from axiome.core.errors import ResearchError

PHOTON_FR = (
    "Le photon est la particule élémentaire associée à la lumière et au rayonnement "
    "électromagnétique. Il n'a pas de masse et se déplace à la vitesse de la lumière dans le vide."
)
PHOTON_EN = (
    "A photon is an elementary particle that is a quantum of the electromagnetic field, "
    "including light. Photons are massless and always move at the speed of light in vacuum."
)
PAGE = (
    "<html><head><script>var x = 1;</script><title>t</title></head>"
    "<body><nav>Menu Accueil Contact</nav>"
    "<p>Le photon est la particule élémentaire associée à la lumière et au rayonnement.</p>"
    "<p>Albert Einstein a proposé le concept de quantum de lumière en 1905 "
    "pour expliquer l'effet photoélectrique.</p>"
    "<footer>Mentions légales du site</footer></body></html>"
)


class FakeFetcher:
    """Answers by URL fragment; unknown URLs fail like a network error."""

    def __init__(self, routes: dict[str, bytes | Callable[[], bytes]]) -> None:
        self.routes = routes
        self.calls: list[str] = []

    def get(self, url: str) -> bytes:
        self.calls.append(url)
        for fragment, body in self.routes.items():
            if fragment in url:
                return body() if callable(body) else body
        raise ResearchError("research.fetch_failed", url=url, detail="offline test")


def wikipedia_routes(lang: str = "fr") -> dict[str, bytes | Callable[[], bytes]]:
    extract = PHOTON_FR if lang == "fr" else PHOTON_EN
    search = {"query": {"search": [{"title": "Photon"}, {"title": "Vide"}]}}
    summary = {
        "extract": extract,
        "content_urls": {"desktop": {"page": f"https://{lang}.wikipedia.org/wiki/Photon"}},
    }
    return {
        "/w/api.php": json.dumps(search).encode(),
        "/page/summary/Photon": json.dumps(summary).encode(),
        "/page/summary/Vide": json.dumps({"extract": ""}).encode(),
    }
