"""In-memory code index and its ``?-`` query surface (M7.0).

The index only stores facts produced by :mod:`axiome.code.facts`; it adds
nothing and guesses nothing. A file that does not parse is reported as a
:class:`Problem` and excluded, never silently dropped (RFC-0002).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from axiome.code.facts import PREDICATES, extract
from axiome.code.source import SourceFile, read_repository
from axiome.core.errors import CodeError, CodeSyntaxError
from axiome.i18n import Msg
from axiome.reasoning.syntax import Query, parse_statement
from axiome.reasoning.terms import Atom, Term, TermKey, Var, term_key, unify


@dataclass(frozen=True, slots=True)
class Problem:
    """A file the index could not read: reported with its location."""

    path: str
    line: int
    message: Msg


class CodeIndex:
    """Ground code facts, queryable with single positive literals.

    ``ask("?- defines(Pos, Nom).")`` returns bindings sorted canonically; a
    ground query returns ``({},)`` when the fact holds and ``()`` otherwise.
    """

    def __init__(self, facts: Iterable[Atom], problems: Iterable[Problem] = ()) -> None:
        unique = {fact.sort_key(): fact for fact in facts}
        self.facts: tuple[Atom, ...] = tuple(unique[key] for key in sorted(unique))
        self.problems: tuple[Problem, ...] = tuple(
            sorted(problems, key=lambda problem: (problem.path, problem.line, problem.message.key))
        )
        by_predicate: dict[str, list[Atom]] = {}
        for fact in self.facts:
            by_predicate.setdefault(fact.predicate, []).append(fact)
        self._by_predicate: dict[str, tuple[Atom, ...]] = {
            predicate: tuple(items) for predicate, items in by_predicate.items()
        }

    @classmethod
    def build(cls, files: Iterable[SourceFile]) -> CodeIndex:
        """Index source files; unparsable files become problems, not failures."""
        facts: list[Atom] = []
        problems: list[Problem] = []
        for source in sorted(files, key=lambda item: item.path):
            try:
                facts.extend(extract(source))
            except CodeSyntaxError as exc:
                problems.append(Problem(exc.path, exc.line, exc.message))
        return cls(facts, problems)

    @classmethod
    def from_repository(cls, root: str | Path) -> CodeIndex:
        return cls.build(read_repository(root))

    def of(self, predicate: str) -> tuple[Atom, ...]:
        """All facts of one predicate, in canonical order."""
        return self._by_predicate.get(predicate, ())

    def ask(self, text: str) -> tuple[dict[Var, Term], ...]:
        """Answer one positive literal against the index."""
        statement = parse_statement(text if text.lstrip().startswith("?-") else f"?- {text}")
        if not isinstance(statement, Query):  # pragma: no cover - parse always yields a query
            raise CodeError("code.query_expected")
        if len(statement.body) != 1 or statement.body[0].negated:
            raise CodeError("code.query_shape")
        pattern = statement.body[0].atom
        if pattern.predicate not in PREDICATES:
            raise CodeError("code.unknown_predicate", predicate=pattern.predicate)
        solutions: list[dict[Var, Term]] = []
        for fact in self.of(pattern.predicate):
            substitution = unify(pattern, fact, {})
            if substitution is not None:
                solutions.append(substitution)
        return tuple(sorted(solutions, key=_solution_key))


def _solution_key(substitution: Mapping[Var, Term]) -> tuple[tuple[str, TermKey], ...]:
    return tuple(sorted((variable.name, term_key(term)) for variable, term in substitution.items()))
