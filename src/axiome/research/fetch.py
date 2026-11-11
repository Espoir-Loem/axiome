"""HTTP access, with a disk cache.

Only the standard library is used. Requests carry a generic User-Agent (no user
data). Replaying a question from the cache yields byte-identical responses, so
answers are reproducible.
"""

from __future__ import annotations

import hashlib
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from pathlib import Path
from typing import Protocol

from axiome import __version__
from axiome.core.errors import ResearchError

DEFAULT_TIMEOUT_S = 6
MAX_BYTES = 2_000_000
USER_AGENT = f"axiome/{__version__} (offline-first research assistant)"


class Fetcher(Protocol):
    def get(self, url: str, headers: Mapping[str, str] | None = None) -> bytes: ...


def build_url(base: str, params: Mapping[str, str | int]) -> str:
    """Append query parameters in a canonical (sorted) order."""
    query = urllib.parse.urlencode(sorted((k, str(v)) for k, v in params.items()))
    return f"{base}?{query}" if query else base


class HttpFetcher:
    def __init__(self, timeout_s: float = DEFAULT_TIMEOUT_S) -> None:
        self.timeout_s = timeout_s

    def get(self, url: str, headers: Mapping[str, str] | None = None) -> bytes:
        if not url.startswith(("https://", "http://")):
            raise ResearchError("research.bad_url", url=url)
        sent = {"User-Agent": USER_AGENT, "Accept": "application/json, text/html;q=0.9"}
        sent.update(headers or {})
        request = urllib.request.Request(url, headers=sent)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
                data: bytes = response.read(MAX_BYTES)
                return data
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ResearchError("research.fetch_failed", url=url, detail=exc) from exc


class CachedFetcher:
    """Serve from ``directory`` when possible; store every successful response."""

    def __init__(self, inner: Fetcher, directory: str | Path) -> None:
        self.inner = inner
        self.directory = Path(directory)

    def _path(self, url: str) -> Path:
        return self.directory / (hashlib.sha256(url.encode()).hexdigest() + ".bin")

    def get(self, url: str, headers: Mapping[str, str] | None = None) -> bytes:
        """Headers (API keys) are not part of the cache key and are never stored."""
        path = self._path(url)
        if path.exists():
            return path.read_bytes()
        data = self.inner.get(url, headers)
        self.directory.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(data)
        tmp.replace(path)
        return data
