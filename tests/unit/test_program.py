from __future__ import annotations

import pytest

from axiome.core.errors import ProgramError
from tests.helpers import program_of


def test_stratification_orders_negation() -> None:
    p = program_of("b(X) :- a(X), not c(X). c(X) :- d(X). e(X) :- b(X), not f(X).")
    # c (stratum 0) before b (stratum 1) before e
    flat = [i for stratum in p.strata for i in stratum]
    assert flat.index(1) < flat.index(0) < flat.index(2)


@pytest.mark.parametrize(
    ("text", "key"),
    [
        ("p(X) :- q(Y).", "program.unbound_variable"),
        ("p(X) :- q(X), not r(Y).", "program.negated_only"),
        ("p(X) :- not q(X).", "program.no_positive_literal"),
        ("p(X) :- q(X), not r(X). r(X) :- q(X), not p(X).", "program.not_stratifiable"),
        ("p(X) :- q(X), not p(X).", "program.negates_own_head"),
        ("! c :- not q(a).", "program.no_positive_literal"),
        ("p(_Z) :- q(a).", "program.unbound_variable"),
    ],
)
def test_invalid_programs(text: str, key: str) -> None:
    with pytest.raises(ProgramError) as exc:
        program_of(text)
    assert exc.value.message.key == key
    assert str(exc.value)  # renders without missing parameters
