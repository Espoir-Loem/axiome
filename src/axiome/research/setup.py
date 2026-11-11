"""Builds the researcher from the configuration (which providers, which cache)."""

from __future__ import annotations

from axiome.core.config import Config
from axiome.research.fetch import CachedFetcher, Fetcher, HttpFetcher
from axiome.research.providers.base import SearchProvider
from axiome.research.providers.google import GoogleCSE
from axiome.research.providers.searxng import SearXNG
from axiome.research.providers.wikipedia import Wikipedia
from axiome.team.researcher import Researcher


def providers(config: Config, fetcher: Fetcher) -> list[SearchProvider]:
    """Configured engines first, then keyless sources (always available)."""
    found: list[SearchProvider] = []
    if config.google_api_key and config.google_engine_id:
        found.append(GoogleCSE(fetcher, config.google_api_key, config.google_engine_id))
    if config.searxng_url:
        found.append(SearXNG(fetcher, config.searxng_url))
    found.append(Wikipedia(fetcher))
    return found


def build_researcher(config: Config, fetcher: Fetcher | None = None) -> Researcher | None:
    if config.offline:
        return None
    if fetcher is None:
        fetcher = HttpFetcher()
        if config.cache_dir:
            fetcher = CachedFetcher(fetcher, config.cache_dir)
    return Researcher(providers(config, fetcher))
