"""Shared test utilities."""

from __future__ import annotations

from axiome.reasoning.engine import Model, evaluate
from axiome.reasoning.program import Constraint, Program, Rule
from axiome.reasoning.syntax import Query, parse_program, parse_statement
from axiome.reasoning.terms import Atom, Literal


def program_of(text: str) -> Program:
    stmts = parse_program(text)
    return Program(
        tuple(s for s in stmts if isinstance(s, Rule)),
        tuple(s for s in stmts if isinstance(s, Constraint)),
    )


def model(text: str) -> Model:
    stmts = parse_program(text)
    return evaluate(program_of(text), [s for s in stmts if isinstance(s, Atom)])


def body(text: str) -> tuple[Literal, ...]:
    stmt = parse_statement(f"?- {text}")
    assert isinstance(stmt, Query)
    return stmt.body
