"""Terms and atoms of the Axiome logic language (a Datalog subset).

Design choices (see RFC-0001):

* no function symbols, so the Herbrand universe is finite and every saturation
  terminates;
* constants are strings or integers (no floats: their arithmetic is
  platform-dependent and would break determinism);
* a canonical total order (:func:`term_key`, :meth:`Atom.sort_key`) is defined
  on every object: each traversal in the engine is sorted, never dependent on
  insertion or hashing order.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

_IDENT = re.compile(r"[^\W\d_]\w*", re.UNICODE)
NEGATION = "not"  # reserved keyword of the language


@dataclass(frozen=True, slots=True)
class Var:
    """Logic variable (starts with an uppercase letter or ``_`` in the syntax)."""

    name: str

    def __str__(self) -> str:
        return self.name


Constant = str | int
Term = Var | str | int
Substitution = Mapping[Var, Term]
TermKey = tuple[int, int | str]
AtomKey = tuple[str, tuple[TermKey, ...]]


def is_bare_identifier(value: str) -> bool:
    """True if the constant can be written without quotes."""
    return bool(_IDENT.fullmatch(value)) and value[0].islower() and value != NEGATION


def format_term(term: Term) -> str:
    if isinstance(term, Var):
        return term.name
    if isinstance(term, bool):  # bool is an int in Python: reject it explicitly
        raise TypeError("booleans are not Axiome constants")
    if isinstance(term, int):
        return str(term)
    if is_bare_identifier(term):
        return term
    escaped = term.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'


def term_key(term: Term) -> TermKey:
    """Total sort key: integers < strings < variables."""
    if isinstance(term, Var):
        return (2, term.name)
    if isinstance(term, int):
        return (0, term)
    return (1, term)


@dataclass(frozen=True, slots=True)
class Atom:
    """A predicate applied to terms, e.g. ``is_a(cat, mammal)``."""

    predicate: str
    args: tuple[Term, ...] = ()

    @property
    def signature(self) -> tuple[str, int]:
        return (self.predicate, len(self.args))

    def is_ground(self) -> bool:
        return not any(isinstance(a, Var) for a in self.args)

    def variables(self) -> tuple[Var, ...]:
        """Variables in order of first occurrence (without duplicates)."""
        seen: dict[Var, None] = {}
        for a in self.args:
            if isinstance(a, Var):
                seen.setdefault(a, None)
        return tuple(seen)

    def sort_key(self) -> AtomKey:
        return (self.predicate, tuple(term_key(a) for a in self.args))

    def __str__(self) -> str:
        if not self.args:
            return self.predicate
        return f"{self.predicate}({', '.join(format_term(a) for a in self.args)})"


@dataclass(frozen=True, slots=True)
class Literal:
    """A possibly negated atom (stratified negation as failure)."""

    atom: Atom
    negated: bool = False

    def __str__(self) -> str:
        return f"{NEGATION} {self.atom}" if self.negated else str(self.atom)


def walk(term: Term, subst: Substitution) -> Term:
    while isinstance(term, Var) and term in subst:
        term = subst[term]
    return term


def unify(pattern: Atom, fact: Atom, subst: Substitution) -> dict[Var, Term] | None:
    """Unify two atoms under a substitution; return the extended substitution or None."""
    if pattern.signature != fact.signature:
        return None
    out = dict(subst)
    for left, right in zip(pattern.args, fact.args, strict=True):
        a, b = walk(left, out), walk(right, out)
        if type(a) is type(b) and a == b:
            continue
        if isinstance(a, Var):
            out[a] = b
        elif isinstance(b, Var):
            out[b] = a
        else:
            return None
    return out


def substitute(atom: Atom, subst: Substitution) -> Atom:
    return Atom(atom.predicate, tuple(walk(a, subst) for a in atom.args))
