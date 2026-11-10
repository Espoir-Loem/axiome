"""Injectable clock.

Time is the main source of non-determinism, so business code never reads it
directly, only through a :class:`Clock`. Timestamps are stored as metadata and
never influence reasoning.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol


class Clock(Protocol):
    def now(self) -> str:
        """ISO 8601 timestamp in UTC."""
        ...


class SystemClock:
    def now(self) -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class FixedClock:
    def __init__(self, value: str = "2000-01-01T00:00:00+00:00") -> None:
        self._value = value

    def now(self) -> str:
        return self._value
