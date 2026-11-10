"""Termes et atomes du langage logique d'Axiome (sous-ensemble de Datalog).

Choix de conception (voir RFC-0001) :

* pas de symboles de fonction → l'univers de Herbrand est fini, donc toute
  saturation termine ;
* constantes = chaînes ou entiers (pas de flottants : leur arithmétique dépend de
  la plateforme et casserait le déterminisme) ;
* un ordre total canonique (:func:`term_key`, :meth:`Atom.sort_key`) est défini
  sur tous les objets : chaque parcours du moteur est trié, jamais dépendant de
  l'ordre d'insertion ou du hachage.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

_IDENT = re.compile(r"[^\W\d_]\w*", re.UNICODE)


@dataclass(frozen=True, slots=True)
class Var:
    """Variable logique (commence par une majuscule ou ``_`` dans la syntaxe)."""

    name: str

    def __str__(self) -> str:
        return self.name


Constant = str | int
Term = Var | str | int
Substitution = Mapping[Var, Term]
TermKey = tuple[int, int | str]
AtomKey = tuple[str, tuple[TermKey, ...]]


def is_bare_identifier(value: str) -> bool:
    """Vrai si la constante peut s'écrire sans guillemets."""
    return bool(_IDENT.fullmatch(value)) and value[0].islower() and value != "non"


def format_term(term: Term) -> str:
    if isinstance(term, Var):
        return term.name
    if isinstance(term, bool):  # bool est un int en Python : on le refuse explicitement
        raise TypeError("les booléens ne sont pas des constantes Axiome")
    if isinstance(term, int):
        return str(term)
    if is_bare_identifier(term):
        return term
    escaped = term.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'


def term_key(term: Term) -> TermKey:
    """Clé de tri totale : entiers < chaînes < variables."""
    if isinstance(term, Var):
        return (2, term.name)
    if isinstance(term, int):
        return (0, term)
    return (1, term)


@dataclass(frozen=True, slots=True)
class Atom:
    """Prédicat appliqué à des termes, ex. ``est_un(chat, mammifère)``."""

    predicate: str
    args: tuple[Term, ...] = ()

    @property
    def signature(self) -> tuple[str, int]:
        return (self.predicate, len(self.args))

    def is_ground(self) -> bool:
        return not any(isinstance(a, Var) for a in self.args)

    def variables(self) -> tuple[Var, ...]:
        """Variables dans l'ordre de première apparition (sans doublon)."""
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
    """Atome éventuellement nié (négation par l'échec, stratifiée)."""

    atom: Atom
    negated: bool = False

    def __str__(self) -> str:
        return f"non {self.atom}" if self.negated else str(self.atom)


def walk(term: Term, subst: Substitution) -> Term:
    while isinstance(term, Var) and term in subst:
        term = subst[term]
    return term


def unify(pattern: Atom, fact: Atom, subst: Substitution) -> dict[Var, Term] | None:
    """Unifie deux atomes sous une substitution ; renvoie la nouvelle substitution ou None."""
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
