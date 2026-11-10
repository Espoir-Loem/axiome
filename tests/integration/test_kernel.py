from __future__ import annotations

from pathlib import Path

import pytest

from axiome.core.clock import FixedClock
from axiome.core.config import Config
from axiome.core.errors import KnowledgeError, ParseError, ProgramError
from axiome.kernel import Kernel
from axiome.response import render
from axiome.verification.epistemic import Status


def test_deduction_from_seed(kernel: Kernel) -> None:
    result = kernel.ask("is_a(cat, animal)")
    assert len(result.answers) == 1
    assert result.answers[0].overall.status is Status.PROVED
    ex = kernel.explain("is_a(cat, animal)")
    assert ex.proof is not None and ex.proof.rule is not None
    text = render.render_explanation(ex)
    assert "is_a_transitivity" in text and "PROVED" in text


def test_user_contradiction_is_refuted(kernel: Kernel) -> None:
    assert str(kernel.tell("is_a(cat, bird).")).startswith("Noted")
    assert str(kernel.tell("is_a(cat, bird).")).startswith("Already known")
    result = kernel.ask("is_a(cat, bird)")
    assert not result.answers
    assert result.refuted[0][1].status is Status.REFUTED
    out = render.render_query(result)
    assert out.startswith("No.") and "disjoint_classes" in out
    ex = kernel.explain("is_a(cat, bird)")
    assert ex.proof is None and "REFUTED" in render.render_explanation(ex)
    assert "resolved" in render.render_conflicts(kernel.state)


def test_unknown_is_not_false(kernel: Kernel) -> None:
    assert "I don't know" in render.render_query(kernel.ask("is_a(unicorn, animal)"))
    with pytest.raises(KnowledgeError, match="not established"):
        kernel.explain("is_a(unicorn, animal)")


def test_user_fact_is_unverified_and_rule_is_hypothesis(kernel: Kernel) -> None:
    kernel.tell("is_a(felix, cat).")
    assert kernel.ask("is_a(felix, vertebrate)").answers[0].overall.status is Status.UNVERIFIED
    assert str(kernel.tell("pet(X) :- is_a(X, cat).")).startswith("Rule added")
    assert str(kernel.tell("pet(X) :- is_a(X, cat).")) == "Rule already known."
    assert kernel.ask("pet(felix)").answers


def test_closed_world_answers_are_capped(kernel: Kernel) -> None:
    result = kernel.ask("is_a(X, sorting_algorithm), not has_property(X, stable)")
    assert result.answers and all(v.closed_world for v in result.answers)
    assert all(v.overall.status is Status.PLAUSIBLE for v in result.answers)
    assert "(closed world)" in render.render_query(result)


def test_software_engineering_rule(kernel: Kernel) -> None:
    kernel.tell("input(t).")
    kernel.tell("guarantees(t, random_access).")
    assert not kernel.ask("applicable(binary_search, t)").answers
    kernel.tell("guarantees(t, sorted_input).")
    assert kernel.ask("applicable(binary_search, t)").answers


def test_contested_conflict_rendering(kernel: Kernel) -> None:
    kernel.tell("is_a(x, mammal).")
    kernel.tell("is_a(x, bird).")
    assert "unresolved" in render.render_conflicts(kernel.state)
    assert kernel.ask("is_a(x, bird)").answers[0].overall.status is Status.CONTESTED


def test_invalid_inputs(kernel: Kernel) -> None:
    with pytest.raises(ProgramError):
        kernel.tell("p(X) :- q(Y).")
    with pytest.raises(ProgramError):
        kernel.tell("! c :- p(a).")
    with pytest.raises(KnowledgeError):
        kernel.tell("?- p(a).")
    with pytest.raises(ParseError):
        kernel.ask("p(")
    with pytest.raises(KnowledgeError):
        kernel.explain("p(X) :- q(X)")


def test_persistence_across_sessions(tmp_path: Path) -> None:
    cfg = Config(str(tmp_path / "a.db"))
    Kernel.open(cfg, FixedClock()).tell("is_a(felix, cat).")
    assert Kernel.open(cfg, FixedClock()).ask("is_a(felix, animal)").answers


def test_contradicting_evidence(kernel: Kernel) -> None:
    kernel.tell("is_a(pingu, penguin).")
    kernel.tell("is_a(pingu, penguin).", contradicts=True)
    assert kernel.ask("is_a(pingu, penguin)").answers[0].overall.status is Status.CONTESTED
