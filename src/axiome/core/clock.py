"""Horloge injectable.

Le temps est la principale source de non-déterminisme : il n'est donc jamais lu
directement par le code métier, toujours via une :class:`Clock`. Les horodatages
sont stockés comme métadonnées et n'influencent jamais un raisonnement.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol


class Clock(Protocol):
    def now(self) -> str:
        """Horodatage ISO 8601 en UTC."""
        ...


class SystemClock:
    def now(self) -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class FixedClock:
    def __init__(self, value: str = "2000-01-01T00:00:00+00:00") -> None:
        self._value = value

    def now(self) -> str:
        return self._value
