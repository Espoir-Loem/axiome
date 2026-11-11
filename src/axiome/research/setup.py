"""Builds the researcher from the configuration (which providers, which cache)."""

from __future__ import annotations

from axiome.core.config import Config
from axiome.kernel import Kernel
from axiome.knowledge.wikidata import Librarian, Wikidata
from axiome.research.fetch import CachedFetcher, Fetcher, HttpFetcher
from axiome.research.providers.base import SearchProvider
from axiome.research.providers.brave import BraveSearch
from axiome.research.providers.duckduckgo import DuckDuckGo
from axiome.research.providers.google import GoogleCSE
from axiome.research.providers.openalex import OpenAlex
from axiome.research.providers.searxng import SearXNG
from axiome.research.providers.wikipedia import Wikipedia
from axiome.team.researcher import Researcher


def providers(config: Config, fetcher: Fetcher) -> list[SearchProvider]:
    """Whole-web engines first (when configured), then keyless sources (always available)."""
    found: list[SearchProvider] = []
    if config.brave_api_key:
        found.append(BraveSearch(fetcher, config.brave_api_key))
    if config.google_api_key and config.google_engine_id:
        found.append(GoogleCSE(fetcher, config.google_api_key, config.google_engine_id))
    if config.searxng_url:
        found.append(SearXNG(fetcher, config.searxng_url))
    found += [Wikipedia(fetcher), DuckDuckGo(fetcher), OpenAlex(fetcher)]
    return found


def default_fetcher(config: Config) -> Fetcher:
    fetcher: Fetcher = HttpFetcher(contact=config.contact)
    if config.cache_dir:
        fetcher = CachedFetcher(fetcher, config.cache_dir)
    return fetcher


def build_researcher(config: Config, fetcher: Fetcher | None = None) -> Researcher | None:
    if config.offline:
        return None
    return Researcher(providers(config, fetcher or default_fetcher(config)))


def build_librarian(
    config: Config, kernel: Kernel, fetcher: Fetcher | None = None
) -> Librarian | None:
    """Wikidata learning (concepts, classes, names), unless offline."""
    if config.offline:
        return None
    return Librarian(kernel, Wikidata(fetcher or default_fetcher(config)))
