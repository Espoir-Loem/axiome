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
from axiome.core.errors import CodeError, CodeSyntaxError

MOD = "def double(n):\n    return n + 3\n"
TEST = "from mod import double\n\n\ndef test_double():\n    assert double(2) == 4\n"

PAIR_SOURCE = "def bounds():\n    first = 1\n    second = 1\n    return first, second\n"
PAIR_TEST = "from mod import bounds\n\n\ndef test_bounds():\n    assert bounds() == (2, 2)\n"

HELPER_SOURCE = "def double(n):\n    return n + 1\n"
MAIN_SOURCE = "from helper import double\n\n\ndef run(n):\n    return double(n) + 1\n"
MAIN_TEST = "from main import run\n\n\ndef test_run():\n    assert run(1) == 5\n"


def project(tmp_path: Path) -> Path:
    (tmp_path / "mod.py").write_text(MOD, encoding="utf-8")
    (tmp_path / "test_mod.py").write_text(TEST, encoding="utf-8")
    return tmp_path


def two_files(tmp_path: Path) -> Path:
    (tmp_path / "helper.py").write_text(HELPER_SOURCE, encoding="utf-8")
    (tmp_path / "main.py").write_text(MAIN_SOURCE, encoding="utf-8")
    (tmp_path / "test_main.py").write_text(MAIN_TEST, encoding="utf-8")
    return tmp_path


def test_accepts_only_a_patch_that_passes_the_tests(tmp_path: Path) -> None:
    result = generate(project(tmp_path), "mod.py", budget=10, isolate_network=False)
    assert result.status == ACCEPTED
    assert result.accepted
    assert "+    return n + 2" in result.patch
    assert result.attempts[-1].passed
    assert all(not attempt.passed for attempt in result.attempts[:-1])


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


def test_unknown_extra_target_is_reported(tmp_path: Path) -> None:
    with pytest.raises(CodeError, match=r"absent\.py"):
        generate(project(tmp_path), "mod.py", extra_targets=("absent.py",), isolate_network=False)


def test_unparsable_target_is_reported(tmp_path: Path) -> None:
    (tmp_path / "bad.py").write_text("def broken(:\n", encoding="utf-8")
    with pytest.raises(CodeError, match=r"bad\.py"):
        generate(tmp_path, "bad.py", isolate_network=False)


def test_syntax_error_has_a_position(tmp_path: Path) -> None:
    (tmp_path / "broken.py").write_text("def f(\n", encoding="utf-8")
    with pytest.raises(CodeError) as match:
        generate(project(tmp_path), "broken.py", budget=10, isolate_network=False)
    assert match.value.args[0] == "code.syntax_error"
    assert isinstance(match.value, CodeSyntaxError)
    assert (match.value.path, match.value.line) == ("broken.py", 1)


def test_bad_budget_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(CodeError) as match:
        generate(project(tmp_path), "mod.py", budget=0, isolate_network=False)
    assert match.value.args[0] == "code.bad_budget"
    assert "invalid generation budget: 0" in str(match.value)


def test_bad_depth_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(CodeError) as match:
        generate(project(tmp_path), "mod.py", depth=0, budget=10, isolate_network=False)
    assert match.value.args[0] == "code.bad_depth"
    assert "invalid search depth: 0" in str(match.value)


@pytest.mark.parametrize(
    "case",
    [
        (
            "binary",
            "counter.py",
            "def add_one(n):\n    return n - 1\n",
            "from counter import add_one\n\n\ndef test_add_one():\n    assert add_one(2) == 3\n",
            "+    return n + 1",
        ),
        (
            "boolean",
            "logic.py",
            "def either(a, b):\n    return a and b\n",
            "from logic import either\n\n\ndef test_either():\n"
            "    assert either(True, False) is True\n",
            "+    return a or b",
        ),
        (
            "condition",
            "label.py",
            'def label(flag):\n    if flag:\n        return "on"\n    return "off"\n',
            'from label import label\n\n\ndef test_label():\n    assert label(False) == "on"\n',
            "+    if not flag:",
        ),
        (
            "ifexp",
            "ternary.py",
            'def label(flag):\n    return "on" if flag else "off"\n',
            'from ternary import label\n\n\ndef test_label():\n    assert label(True) == "off"\n',
            '+    return "on" if not flag else "off"',
        ),
    ],
    ids=["binary", "boolean", "condition", "ifexp"],
)
def test_new_mutation_families_are_searched(
    tmp_path: Path, case: tuple[str, str, str, str, str]
) -> None:
    name, target, source, test, expected = case
    root = tmp_path / name
    root.mkdir()
    (root / target).write_text(source, encoding="utf-8")
    (root / f"test_{target}").write_text(test, encoding="utf-8")
    result = generate(root, target, budget=8, isolate_network=False)
    assert result.accepted, result.attempts
    assert expected in result.patch


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


def test_depth_composes_edits_on_distinct_lines(tmp_path: Path) -> None:
    (tmp_path / "mod.py").write_text(PAIR_SOURCE, encoding="utf-8")
    (tmp_path / "test_mod.py").write_text(PAIR_TEST, encoding="utf-8")
    root = tmp_path

    shallow = generate(root, "mod.py", ("test_mod.py",), budget=6, isolate_network=False)
    assert shallow.status == BUDGET_EXHAUSTED

    deep = generate(root, "mod.py", ("test_mod.py",), budget=32, depth=2, isolate_network=False)
    assert deep.status == ACCEPTED
    assert "+    first = 2" in deep.patch
    assert "+    second = 2" in deep.patch


def test_extra_targets_are_required_for_a_multi_file_fix(tmp_path: Path) -> None:
    root = two_files(tmp_path)
    single = generate(root, "main.py", ("test_main.py",), budget=64, depth=2, isolate_network=False)
    assert single.status == BUDGET_EXHAUSTED

    with_extra = generate(
        root,
        "main.py",
        ("test_main.py",),
        budget=64,
        depth=2,
        extra_targets=("helper.py",),
        isolate_network=False,
    )
    assert with_extra.status == ACCEPTED


def test_composed_patch_is_a_single_multi_file_unified_diff(tmp_path: Path) -> None:
    root = two_files(tmp_path)
    result = generate(
        root,
        "main.py",
        ("test_main.py",),
        budget=64,
        depth=2,
        extra_targets=("helper.py",),
        isolate_network=False,
    )
    assert result.status == ACCEPTED
    assert "--- a/helper.py" in result.patch
    assert "--- a/main.py" in result.patch
    assert "+++ b/helper.py" in result.patch
    assert "+++ b/main.py" in result.patch


def test_compositions_are_deduplicated_and_never_announced_false(tmp_path: Path) -> None:
    (tmp_path / "mod.py").write_text(PAIR_SOURCE, encoding="utf-8")
    (tmp_path / "test_mod.py").write_text(
        "from mod import bounds\n\n\ndef test_bounds():\n    assert bounds() == (99, 99)\n",
        encoding="utf-8",
    )
    result = generate(
        tmp_path, "mod.py", ("test_mod.py",), budget=64, depth=2, isolate_network=False
    )
    assert result.status == BUDGET_EXHAUSTED
    assert result.patch == ""
    assert result.attempts
    assert all(not attempt.passed for attempt in result.attempts)


def test_budget_is_shared_across_depths(tmp_path: Path) -> None:
    (tmp_path / "mod.py").write_text(PAIR_SOURCE, encoding="utf-8")
    (tmp_path / "test_mod.py").write_text(PAIR_TEST, encoding="utf-8")
    result = generate(
        tmp_path, "mod.py", ("test_mod.py",), budget=5, depth=3, isolate_network=False
    )
    assert result.status == BUDGET_EXHAUSTED
    assert len(result.attempts) == 5
    assert [attempt.index for attempt in result.attempts] == list(range(5))


def test_failure_diagnostics_reorder_candidates_without_changing_mutations(
    tmp_path: Path,
) -> None:
    (tmp_path / "mod.py").write_text(
        "def decoy():\n    return 0\n\n\ndef wanted():\n    return 0\n", encoding="utf-8"
    )
    (tmp_path / "test_mod.py").write_text(
        "from mod import wanted\n\n\ndef test_wanted():\n    assert wanted() == 1\n",
        encoding="utf-8",
    )
    plain = generate(tmp_path, "mod.py", budget=2, isolate_network=False)
    assert plain.status == BUDGET_EXHAUSTED

    guided = generate(
        tmp_path,
        "mod.py",
        budget=2,
        diagnostics="FAILED test_mod.py::test_wanted - assert wanted() == 1",
        isolate_network=False,
    )
    assert guided.status == ACCEPTED
    assert "+    return 1" in guided.patch
    assert "def wanted" in guided.patch
