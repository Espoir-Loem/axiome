"""Axiome facade: wires storage, reasoning and verification together.

This is the only entry point interfaces (CLI, later others) should use. The
belief state is recomputed lazily after every write.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from axiome.core.clock import Clock, SystemClock
from axiome.core.config import IN_MEMORY, Config
from axiome.core.errors import KnowledgeError, ProgramError
from axiome.i18n import Msg, msg
from axiome.knowledge.seed import load_seed
from axiome.knowledge.store import KnowledgeStore
from axiome.reasoning.engine import Answer, Proof
from axiome.reasoning.program import Constraint, Program, Rule
from axiome.reasoning.syntax import Query, parse_program, parse_statement
from axiome.reasoning.terms import Atom
from axiome.verification.epistemic import Assessment, Evidence, Source, Stance, Status, assess
from axiome.verification.revision import CLOSED_WORLD_CAP, BeliefState, revise

USER_SOURCE = "user"


@dataclass(frozen=True, slots=True)
class AnswerView:
    answer: Answer
    facts: tuple[tuple[Atom, Assessment], ...]  # every premise with its status
    overall: Assessment  # weakest link, capped when the query uses negation
    closed_world: bool  # the answer depends on an absence of information


@dataclass(frozen=True, slots=True)
class QueryResult:
    query: Query
    answers: tuple[AnswerView, ...]
    refuted: tuple[tuple[Atom, Assessment], ...]  # ground query atoms that were refuted


@dataclass(frozen=True, slots=True)
class Explanation:
    fact: Atom
    assessment: Assessment
    proof: Proof | None  # None when the fact was discarded (refuted)
    statuses: dict[Atom, Assessment]


class Kernel:
    def __init__(self, store: KnowledgeStore, clock: Clock | None = None) -> None:
        self.store = store
        self.clock = clock or SystemClock()
        load_seed(store, self.clock)
        self._state: BeliefState | None = None

    @classmethod
    def open(cls, config: Config | None = None, clock: Clock | None = None) -> Kernel:
        config = config or Config.from_env()
        return cls(KnowledgeStore(config.db_path), clock)

    @classmethod
    def in_memory(cls, clock: Clock | None = None) -> Kernel:
        return cls(KnowledgeStore(IN_MEMORY), clock)

    # -- program -------------------------------------------------------------
    def program(self, extra: Sequence[Rule] = ()) -> Program:
        rules: list[Rule] = []
        constraints: list[Constraint] = []
        for stored in self.store.rules():
            for stmt in parse_program(stored.text, axiomatic=stored.axiomatic):
                if isinstance(stmt, Rule):
                    rules.append(stmt)
                elif isinstance(stmt, Constraint):
                    constraints.append(stmt)
        return Program((*rules, *extra), tuple(constraints))

    @property
    def state(self) -> BeliefState:
        if self._state is None:
            base = {atom: assess(ev) for atom, ev in self.store.evidence().items()}
            self._state = revise(self.program(), base)
        return self._state

    # -- writes --------------------------------------------------------------
    def tell(self, text: str, source_id: str = USER_SOURCE, *, contradicts: bool = False) -> Msg:
        """Add a fact or a (hypothetical) rule. Return a translatable acknowledgement."""
        stmt = parse_statement(text, axiomatic=False)
        if isinstance(stmt, Atom):
            stance = Stance.CONTRADICTS if contradicts else Stance.SUPPORTS
            added = self.store.add_evidence(stmt, source_id, stance, self.clock.now())
            self._state = None
            return msg("tell.noted" if added else "tell.known", atom=stmt)
        if isinstance(stmt, Rule):
            self.program(extra=(stmt,))  # validate BEFORE writing (safety, stratification)
            added = self.store.add_rule(str(stmt), axiomatic=False)
            self._state = None
            return msg("tell.rule_added", rule=stmt) if added else msg("tell.rule_known")
        if isinstance(stmt, Constraint):
            raise ProgramError("knowledge.constraint_seed_only")
        raise KnowledgeError("knowledge.use_ask")

    def record(self, atom: Atom, source: Source, excerpt: str = "") -> bool:
        """Store evidence coming from an external source (web page, reference)."""
        self.store.add_source(source)
        added = self.store.add_evidence(atom, source.id, Stance.SUPPORTS, self.clock.now(), excerpt)
        if added:
            self._state = None
        return added

    # -- reads ---------------------------------------------------------------
    def ask(self, text: str) -> QueryResult:
        stmt = parse_statement(text if text.lstrip().startswith("?-") else f"?- {text}")
        if not isinstance(stmt, Query):  # pragma: no cover - guaranteed by the prefix
            raise KnowledgeError("knowledge.use_ask")
        state = self.state
        uses_absence = any(lit.negated for lit in stmt.body)
        views = tuple(_view(a, state, uses_absence) for a in state.model.query(stmt.body))
        refuted = tuple(
            (lit.atom, state.refuted[lit.atom])
            for lit in stmt.body
            if not lit.negated and lit.atom in state.refuted
        )
        return QueryResult(stmt, views, refuted)

    def evidence(self, atom: Atom) -> list[Evidence]:
        return self.store.evidence_for(atom)

    def explain(self, text: str) -> Explanation:
        stmt = parse_statement(text)
        if not isinstance(stmt, Atom):
            raise KnowledgeError("knowledge.ground_fact_expected")
        state = self.state
        if stmt in state.refuted:
            return Explanation(stmt, state.refuted[stmt], None, {})
        if stmt not in state.model:
            raise KnowledgeError("knowledge.not_established", atom=stmt)
        proof = state.model.proof(stmt)
        statuses: dict[Atom, Assessment] = {}
        stack = [proof]
        while stack:
            node = stack.pop()
            statuses[node.fact] = state.assessments[node.fact]
            stack.extend(node.children)
        return Explanation(stmt, state.assessments[stmt], proof, statuses)


def _view(answer: Answer, state: BeliefState, uses_absence: bool) -> AnswerView:
    facts = tuple((p, state.assessments[p]) for p in answer.premises)
    weakest = min((a.status for _, a in facts), default=Status.PROVED)
    reasons: tuple[Msg, ...] = (msg("reason.weakest_premise"),)
    if uses_absence:
        reasons += (msg("reason.closed_world_answer"),)
        weakest = min(weakest, CLOSED_WORLD_CAP)
    return AnswerView(answer, facts, Assessment(weakest, reasons), uses_absence)
