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
    result = kernel.ask("est_un(chat, animal)")
    assert len(result.answers) == 1
    assert result.answers[0].overall.status is Status.PROVED
    ex = kernel.explain("est_un(chat, animal)")
    assert ex.proof is not None and ex.proof.rule is not None
    text = render.render_explanation(ex)
    assert "transitivite_est_un" in text and "PROUVÉ" in text


def test_user_contradiction_is_refuted(kernel: Kernel) -> None:
    assert kernel.tell("est_un(chat, oiseau).").startswith("Noté")
    assert kernel.tell("est_un(chat, oiseau).").startswith("Déjà connu")
    result = kernel.ask("est_un(chat, oiseau)")
    assert not result.answers
    assert result.refuted[0][1].status is Status.REFUTED
    out = render.render_query(result)
    assert out.startswith("Non.") and "classes_disjointes" in out
    ex = kernel.explain("est_un(chat, oiseau)")
    assert ex.proof is None and "RÉFUTÉ" in render.render_explanation(ex)
    assert "résolu" in render.render_conflicts(kernel.state)


def test_unknown_is_not_false(kernel: Kernel) -> None:
    out = render.render_query(kernel.ask("est_un(licorne, animal)"))
    assert "Je ne sais pas" in out
    with pytest.raises(KnowledgeError, match="pas établi"):
        kernel.explain("est_un(licorne, animal)")


def test_user_fact_is_unverified_and_rule_is_hypothesis(kernel: Kernel) -> None:
    kernel.tell("est_un(félix, chat).")
    a = kernel.ask("est_un(félix, vertébré)").answers[0]
    assert a.overall.status is Status.UNVERIFIED
    assert kernel.tell("domestique(X) :- est_un(X, chat).").startswith("Règle ajoutée")
    assert kernel.tell("domestique(X) :- est_un(X, chat).") == "Règle déjà connue."
    assert kernel.ask("domestique(félix)").answers


def test_closed_world_answers_are_capped(kernel: Kernel) -> None:
    result = kernel.ask("est_un(X, algorithme_de_tri), non a_propriete(X, stable)")
    assert result.answers and all(v.closed_world for v in result.answers)
    assert all(v.overall.status is Status.PLAUSIBLE for v in result.answers)
    assert "(monde clos)" in render.render_query(result)


def test_software_engineering_rule(kernel: Kernel) -> None:
    kernel.tell("entree(t).")
    kernel.tell("garantit(t, accès_aléatoire).")
    assert not kernel.ask("applicable(recherche_binaire, t)").answers
    kernel.tell("garantit(t, entrée_triée).")
    assert kernel.ask("applicable(recherche_binaire, t)").answers


def test_contested_conflict_rendering(kernel: Kernel) -> None:
    kernel.tell("est_un(x, mammifère).")
    kernel.tell("est_un(x, oiseau).")
    text = render.render_conflicts(kernel.state)
    assert "non résolu" in text
    assert kernel.ask("est_un(x, oiseau)").answers[0].overall.status is Status.CONTESTED


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
    assert kernel.body_of("p(a), non q(a)")[1].negated


def test_persistence_across_sessions(tmp_path: Path) -> None:
    cfg = Config(str(tmp_path / "a.db"))
    k1 = Kernel.open(cfg, FixedClock())
    k1.tell("est_un(félix, chat).")
    k2 = Kernel.open(cfg, FixedClock())
    assert k2.ask("est_un(félix, animal)").answers


def test_contradicting_evidence(kernel: Kernel) -> None:
    kernel.tell("est_un(pingu, manchot).")
    kernel.tell("est_un(pingu, manchot).", contradicts=True)
    assert kernel.ask("est_un(pingu, manchot)").answers[0].overall.status is Status.CONTESTED
