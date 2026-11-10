"""Utilitaires de test partagés."""

from __future__ import annotations

from axiome.reasoning.engine import Model, evaluate
from axiome.reasoning.program import Constraint, Program, Rule
from axiome.reasoning.syntax import parse_program
from axiome.reasoning.terms import Atom


def model(text: str) -> Model:
    stmts = parse_program(text)
    prog = Program(
        tuple(s for s in stmts if isinstance(s, Rule)),
        tuple(s for s in stmts if isinstance(s, Constraint)),
    )
    return evaluate(prog, [s for s in stmts if isinstance(s, Atom)])


def program_of(text: str) -> Program:
    stmts = parse_program(text)
    return Program(
        tuple(s for s in stmts if isinstance(s, Rule)),
        tuple(s for s in stmts if isinstance(s, Constraint)),
    )
