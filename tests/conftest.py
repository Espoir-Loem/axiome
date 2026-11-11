from __future__ import annotations

from collections.abc import Iterator

import pytest

from axiome.core.clock import FixedClock
from axiome.i18n import get_locale, set_locale
from axiome.kernel import Kernel


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests never touch the network: web research uses recorded responses."""
    monkeypatch.setenv("AXIOME_OFFLINE", "1")


@pytest.fixture(autouse=True)
def english_locale() -> Iterator[None]:
    """Assertions are written against the English catalog."""
    previous = get_locale()
    set_locale("en")
    yield
    set_locale(previous)


@pytest.fixture
def kernel() -> Kernel:
    return Kernel.in_memory(FixedClock())
