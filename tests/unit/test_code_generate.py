"""Verified generation: bounded, deterministic, accepted only when tests pass."""

from __future__ import annotations

from pathlib import Path

import pytest

from axiome.code.generate import (
    ACCEPTED,
    BUDGET_EXHAUSTED,
    NO_CANDIDATES,
    generate,
)
from axiome.core.errors import CodeError

MOD = "def double(n):\n    return n + 3\n"
TEST = "from mod import double\n\n\ndef test_double():\n    assert double(2) == 4\n"


def project(tmp_path: Path) -> Path:
    (tmp_path / "mod.py").write_text(MOD, encoding="utf-8")
    (tmp_path / "test_mod.py").write_text(TEST, encoding="utf-8")
    return tmp_path


def test_accepts_only_a_patch_that_passes_the_tests(tmp_path: Path) -> None:
    root = project(tmp_path)
    result = generate(root, "mod.py", budget=10, isolate_network=False)
    assert result.status == ACCEPTED
    assert result.accepted
    assert "+    return n + 2" in result.patch
    assert result.attempts[-1].passed
    assert all(not attempt.passed for attempt in result.attempts[:-1])
    assert (root / "mod.py").read_text(encoding="utf-8") == MOD


def test_budget_exhaustion_is_honest(tmp_path: Path) -> None:
    result = generate(project(tmp_path), "mod.py", budget=2, isolate_network=False)
    assert result.status == BUDGET_EXHAUSTED
    assert not result.accepted
    assert len(result.attempts) == 2
    assert all(not attempt.passed for attempt in result.attempts)


def test_search_is_deterministic(tmp_path: Path) -> None:
    first = generate(project(tmp_path), "mod.py", budget=10, seed=3, isolate_network=False)
    second = generate(project(tmp_path), "mod.py", budget=10, seed=3, isolate_network=False)
    assert first.patch == second.patch
    assert [a.index for a in first.attempts] == [a.index for a in second.attempts]


def test_no_mutation_means_no_candidate(tmp_path: Path) -> None:
    (tmp_path / "mod.py").write_text('NAME = "value"\n', encoding="utf-8")
    (tmp_path / "test_mod.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    result = generate(tmp_path, "mod.py", isolate_network=False)
    assert result.status == NO_CANDIDATES
    assert result.attempts == ()


def test_unknown_target_is_reported(tmp_path: Path) -> None:
    with pytest.raises(CodeError, match="unknown file"):
        generate(tmp_path, "absent.py", isolate_network=False)


def test_unparsable_target_is_reported(tmp_path: Path) -> None:
    (tmp_path / "bad.py").write_text("def broken(:\n", encoding="utf-8")
    with pytest.raises(CodeError, match=r"bad\.py"):
        generate(tmp_path, "bad.py", isolate_network=False)


def test_comparison_and_not_mutations_are_searched(tmp_path: Path) -> None:
    compared_root = tmp_path / "compared"
    compared_root.mkdir()
    (compared_root / "mod.py").write_text("def below(n):\n    return n < 10\n", encoding="utf-8")
    (compared_root / "test_mod.py").write_text(
        "from mod import below\n\n\ndef test_below():\n"
        "    assert below(5) is False\n    assert below(15) is True\n",
        encoding="utf-8",
    )
    compared = generate(compared_root, "mod.py", budget=12, isolate_network=False)
    assert compared.accepted
    assert "+    return n >= 10" in compared.patch

    negated_root = tmp_path / "negated"
    negated_root.mkdir()
    (negated_root / "flag.py").write_text("def ok(flag):\n    return not flag\n", encoding="utf-8")
    (negated_root / "test_flag.py").write_text(
        "from flag import ok\n\n\ndef test_ok():\n    assert ok(False) is False\n",
        encoding="utf-8",
    )
    negated = generate(negated_root, "flag.py", budget=1, isolate_network=False)
    assert negated.accepted
    assert "+    return flag" in negated.patch
