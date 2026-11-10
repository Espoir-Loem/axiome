"""Saturation engine (stratified, semi-naive forward chaining) with proofs.

Guaranteed properties (tested in ``tests/property``):

* **termination**: Datalog without function symbols yields a finite model;
* **correctness**: the model is the least stratified model of the program;
* **determinism**: neither the model NOR the justifications depend on fact
  insertion order. For each derived fact we keep the minimal justification by
  (round, rule index, canonical premise keys);
* **traceability**: every derived fact has a checkable proof tree.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass

from axiome.core.errors import KnowledgeError, ProgramError
from axiome.i18n import msg
from axiome.reasoning.program import Constraint, Program, Rule, check_body_safety
from axiome.reasoning.terms import (
    Atom,
    AtomKey,
    Literal,
    Substitution,
    Term,
    Var,
    substitute,
    unify,
    walk,
)

Index = Mapping[str, Sequence[Atom]]


@dataclass(frozen=True, slots=True)
class Justification:
    """Why a fact holds. ``rule_index is None`` iff it is a base fact."""

    rule_index: int | None
    premises: tuple[Atom, ...] = ()
    absent: tuple[Atom, ...] = ()  # atoms whose absence was used (negation)


BASE = Justification(rule_index=None)


@dataclass(frozen=True, slots=True)
class Proof:
    fact: Atom
    rule: Rule | None
    children: tuple[Proof, ...]
    absent: tuple[Atom, ...]


@dataclass(frozen=True, slots=True)
class Violation:
    constraint: Constraint
    premises: tuple[Atom, ...]


@dataclass(frozen=True, slots=True)
class Answer:
    bindings: tuple[tuple[Var, Term], ...]
    premises: tuple[Atom, ...]


def _build_index(facts: Iterable[Atom]) -> dict[str, list[Atom]]:
    index: dict[str, list[Atom]] = {}
    for f in facts:
        index.setdefault(f.predicate, []).append(f)
    for bucket in index.values():
        bucket.sort(key=Atom.sort_key)
    return index


def _solve(
    positives: Sequence[Atom],
    sources: Sequence[Index],
    negatives: Sequence[Atom],
    known: Mapping[Atom, object],
    subst: Substitution,
    *,
    acc: tuple[Atom, ...] = (),
) -> Iterator[tuple[Substitution, tuple[Atom, ...], tuple[Atom, ...]]]:
    """Enumerate, in canonical order, the solutions of a rule body."""
    depth = len(acc)
    if depth == len(positives):
        absent = tuple(substitute(n, subst) for n in negatives)
        if not any(a in known for a in absent):
            yield subst, acc, absent
        return
    pattern = positives[depth]
    for fact in sources[depth].get(pattern.predicate, ()):
        extended = unify(pattern, fact, subst)
        if extended is not None:
            yield from _solve(positives, sources, negatives, known, extended, acc=(*acc, fact))


def _split(body: Sequence[Literal]) -> tuple[list[Atom], list[Atom]]:
    return (
        [lit.atom for lit in body if not lit.negated],
        [lit.atom for lit in body if lit.negated],
    )


def _candidate_key(rule_index: int, premises: Sequence[Atom]) -> tuple[int, tuple[AtomKey, ...]]:
    return (rule_index, tuple(p.sort_key() for p in premises))


class Model:
    """Immutable result of a saturation."""

    def __init__(self, program: Program, facts: dict[Atom, Justification]) -> None:
        self.program = program
        self._facts = facts
        self._index = _build_index(facts)
        self.violations = self._check_constraints()

    # -- lookup -----------------------------------------------------------
    def __contains__(self, atom: object) -> bool:
        return atom in self._facts

    def __len__(self) -> int:
        return len(self._facts)

    def facts(self) -> list[Atom]:
        return sorted(self._facts, key=Atom.sort_key)

    def justification(self, atom: Atom) -> Justification:
        try:
            return self._facts[atom]
        except KeyError:
            raise KnowledgeError("knowledge.not_established", atom=atom) from None

    def is_base(self, atom: Atom) -> bool:
        return self.justification(atom).rule_index is None

    def query(self, body: Sequence[Literal]) -> list[Answer]:
        """Answer a conjunction of literals; unique answers in canonical order."""
        variables: dict[Var, None] = {}
        for lit in body:
            if not lit.negated:
                for v in lit.atom.variables():
                    variables.setdefault(v, None)
        check_body_safety(body, (), msg("where.query"))
        positives, negatives = _split(body)
        answers: dict[tuple[tuple[Var, Term], ...], Answer] = {}
        sources = [self._index] * len(positives)
        for subst, premises, _ in _solve(positives, sources, negatives, self._facts, {}):
            binding = tuple((v, walk(v, subst)) for v in variables)
            answers.setdefault(binding, Answer(binding, premises))
        return list(answers.values())

    def proof(self, atom: Atom) -> Proof:
        memo: dict[Atom, Proof] = {}

        def build(a: Atom) -> Proof:
            if a not in memo:
                j = self.justification(a)
                rule = None if j.rule_index is None else self.program.rules[j.rule_index]
                memo[a] = Proof(a, rule, tuple(build(p) for p in j.premises), j.absent)
            return memo[a]

        return build(atom)

    def support(self, atom: Atom) -> frozenset[Atom]:
        """Base facts that ``atom`` depends on (its epistemic roots)."""
        out: set[Atom] = set()
        stack = [atom]
        seen: set[Atom] = set()
        while stack:
            a = stack.pop()
            if a in seen:
                continue
            seen.add(a)
            j = self.justification(a)
            if j.rule_index is None:
                out.add(a)
            stack.extend(j.premises)
        return frozenset(out)

    # -- integrity ---------------------------------------------------------
    def _check_constraints(self) -> tuple[Violation, ...]:
        found: dict[tuple[str, frozenset[Atom]], Violation] = {}
        for c in self.program.constraints:
            positives, negatives = _split(c.body)
            sources = [self._index] * len(positives)
            for _, premises, _ in _solve(positives, sources, negatives, self._facts, {}):
                found.setdefault((c.name, frozenset(premises)), Violation(c, premises))
        return tuple(found.values())


def evaluate(program: Program, base: Iterable[Atom]) -> Model:
    """Compute the stratified model of ``program`` from the ``base`` facts."""
    known: dict[Atom, Justification] = {}
    for atom in sorted(set(base), key=Atom.sort_key):
        if not atom.is_ground():
            raise ProgramError("program.non_ground_fact", atom=atom)
        known[atom] = BASE

    for stratum in program.strata:
        delta: list[Atom] = list(known)
        while delta:
            full = _build_index(known)
            delta_index = _build_index(delta)
            delta_set = set(delta)
            old = _build_index(a for a in known if a not in delta_set)
            best: dict[Atom, tuple[tuple[int, tuple[AtomKey, ...]], Justification]] = {}
            for rule_index in stratum:
                rule = program.rules[rule_index]
                positives, negatives = _split(rule.body)
                # Semi-naive: the i-th premise comes from the delta, earlier ones from
                # the old state and later ones from the full state, so every combination
                # containing at least one new fact is enumerated exactly once.
                for i in range(len(positives)):
                    sources = [old] * i + [delta_index] + [full] * (len(positives) - i - 1)
                    for subst, premises, absent in _solve(positives, sources, negatives, known, {}):
                        head = substitute(rule.head, subst)
                        if head in known:
                            continue
                        key = _candidate_key(rule_index, premises)
                        current = best.get(head)
                        if current is None or key < current[0]:
                            best[head] = (key, Justification(rule_index, premises, absent))
            for head in sorted(best, key=Atom.sort_key):
                known[head] = best[head][1]
            delta = list(best)
    return Model(program, known)
