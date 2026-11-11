"""HTTP access, with a disk cache.

Only the standard library is used. Requests carry a generic User-Agent (no user
data). Replaying a question from the cache yields byte-identical responses, so
answers are reproducible.
"""

from __future__ import annotations

import hashlib
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Protocol

from axiome import __version__
from axiome.core.errors import ResearchError

DEFAULT_TIMEOUT_S = 6
RETRIES = 3  # on "too many requests" / "unavailable", after the delay the server asks for
MAX_WAIT_S = 10.0
RETRY_STATUS = frozenset({429, 503})
MAX_BYTES = 2_000_000
USER_AGENT = f"axiome/{__version__} (offline-first research assistant)"


class Fetcher(Protocol):
    def get(self, url: str, headers: Mapping[str, str] | None = None) -> bytes: ...


def build_url(base: str, params: Mapping[str, str | int]) -> str:
    """Append query parameters in a canonical (sorted) order."""
    query = urllib.parse.urlencode(sorted((k, str(v)) for k, v in params.items()))
    return f"{base}?{query}" if query else base


class HttpFetcher:
    def __init__(
        self,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        sleep: Callable[[float], None] = time.sleep,
        contact: str = "",
    ) -> None:
        self.timeout_s = timeout_s
        self.sleep = sleep
        # Wikimedia asks automated clients for a contact; only sent when the user sets one.
        self.user_agent = f"{USER_AGENT[:-1]}; {contact})" if contact else USER_AGENT

    def get(self, url: str, headers: Mapping[str, str] | None = None) -> bytes:
        if not url.startswith(("https://", "http://")):
            raise ResearchError("research.bad_url", url=url)
        sent = {"User-Agent": self.user_agent, "Accept": "application/json, text/html;q=0.9"}
        sent.update(headers or {})
        request = urllib.request.Request(url, headers=sent)
        for attempt in range(RETRIES + 1):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
                    data: bytes = response.read(MAX_BYTES)
                    return data
            except urllib.error.HTTPError as exc:
                if exc.code not in RETRY_STATUS or attempt == RETRIES:
                    raise ResearchError("research.fetch_failed", url=url, detail=exc) from exc
                self.sleep(_retry_after(exc.headers.get("Retry-After"), attempt))
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                raise ResearchError("research.fetch_failed", url=url, detail=exc) from exc
        raise AssertionError("unreachable")  # pragma: no cover


def _retry_after(header: str | None, attempt: int) -> float:
    """Seconds to wait: the server's Retry-After (capped), else a short exponential delay."""
    try:
        wanted = float(header) if header else 0.5 * 2**attempt
    except ValueError:  # an HTTP date: not worth parsing for a capped wait
        wanted = MAX_WAIT_S
    return min(max(wanted, 0.0), MAX_WAIT_S)


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
