"""Configuration, resolved once at startup."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

IN_MEMORY = ":memory:"


@dataclass(frozen=True, slots=True)
class Config:
    db_path: str

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Config:
        env = os.environ if env is None else env
        explicit = env.get("AXIOME_DB")
        if explicit:
            return cls(db_path=explicit)
        base = env.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
        return cls(db_path=str(Path(base) / "axiome" / "axiome.db"))
