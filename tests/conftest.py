from __future__ import annotations

import pytest

from axiome.core.clock import FixedClock
from axiome.kernel import Kernel


@pytest.fixture
def kernel() -> Kernel:
    return Kernel.in_memory(FixedClock())
