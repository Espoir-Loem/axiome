"""Configuration, resolved once at startup (environment variables, then defaults)."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

IN_MEMORY = ":memory:"
TRUE = frozenset({"1", "true", "yes", "on"})


@dataclass(frozen=True, slots=True)
class Config:
    db_path: str
    offline: bool = False
    cache_dir: str = ""  # empty: no web cache
    google_api_key: str = ""  # Google Programmable Search (both values required)
    google_engine_id: str = ""
    searxng_url: str = ""  # e.g. http://localhost:8888
    brave_api_key: str = ""  # Brave Search API (independent whole-web index)
    contact: str = ""  # URL or e-mail added to the User-Agent (Wikimedia etiquette), opt-in

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Config:
        env = os.environ if env is None else env
        home = Path.home()
        data = env.get("XDG_DATA_HOME") or str(home / ".local" / "share")
        cache = env.get("XDG_CACHE_HOME") or str(home / ".cache")
        return cls(
            db_path=env.get("AXIOME_DB") or str(Path(data) / "axiome" / "axiome.db"),
            offline=env.get("AXIOME_OFFLINE", "").lower() in TRUE,
            cache_dir=env.get("AXIOME_CACHE_DIR") or str(Path(cache) / "axiome" / "web"),
            google_api_key=env.get("AXIOME_GOOGLE_API_KEY", ""),
            google_engine_id=env.get("AXIOME_GOOGLE_CX", ""),
            searxng_url=env.get("AXIOME_SEARXNG_URL", ""),
            brave_api_key=env.get("AXIOME_BRAVE_API_KEY", ""),
            contact=env.get("AXIOME_CONTACT", ""),
        )
