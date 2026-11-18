"""Properties of code extraction: positions round-trip, order never matters."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from axiome.code.index import CodeIndex
from axiome.code.source import Position, SourceFile

PATH = st.text(
    alphabet=st.characters(blacklist_categories=("Cs", "Cc")), min_size=1, max_size=20
).map(lambda path: path + ".py")

FILES = (
    SourceFile("a.py", "import os\nx = f(1)\n"),
    SourceFile("b.py", "def f(y):\n    return y\n"),
)


@settings(max_examples=150, deadline=None)
@given(PATH, st.integers(min_value=1, max_value=10**6))
def test_position_round_trip(path: str, line: int) -> None:
    position = Position(path, line)
    assert Position.parse(str(position)) == position


@settings(max_examples=50, deadline=None)
@given(st.randoms(use_true_random=False))
def test_index_is_invariant_under_file_order(rnd) -> None:  # type: ignore[no-untyped-def]
    shuffled = list(FILES)
    rnd.shuffle(shuffled)
    assert CodeIndex.build(shuffled).facts == CodeIndex.build(FILES).facts
