from __future__ import annotations

import pytest

from axiome.core.errors import ProgramError
from axiome.reasoning.program import Constraint, Program, Rule
from axiome.reasoning.syntax import parse_program


def program(text: str) -> Program:
    stmts = parse_program(text)
    return Program(
        tuple(s for s in stmts if isinstance(s, Rule)),
        tuple(s for s in stmts if isinstance(s, Constraint)),
    )


def test_stratification_orders_negation() -> None:
    p = program("b(X) :- a(X), non c(X). c(X) :- d(X). e(X) :- b(X), non f(X).")
    # c (strate 0) avant b (strate 1) avant e
    flat = [i for stratum in p.strata for i in stratum]
    assert flat.index(1) < flat.index(0) < flat.index(2)


@pytest.mark.parametrize(
    ("text", "fragment"),
    [
        ("p(X) :- q(Y).", "variable X"),
        ("p(X) :- q(X), non r(Y).", "sous négation"),
        ("p(X) :- non q(X).", "au moins un littéral positif"),
        ("p(X) :- q(X), non r(X). r(X) :- q(X), non p(X).", "non stratifiable"),
        ("p(X) :- q(X), non p(X).", "propre tête"),
        ("! c :- non q(a).", "au moins un littéral positif"),
    ],
)
def test_invalid_programs(text: str, fragment: str) -> None:
    with pytest.raises(ProgramError) as exc:
        program(text)
    assert fragment in str(exc.value)


def test_head_variables_must_be_bound_even_with_underscore() -> None:
    with pytest.raises(ProgramError):
        program("p(_Z) :- q(a).")
