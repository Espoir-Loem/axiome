"""Sandbox: temporary copy, limits, clean environment, explicit degradation."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from axiome.code.sandbox import SandboxLimits, run, run_tests
from axiome.core.errors import CodeError


def test_runs_in_a_copy_and_leaves_the_tree_untouched(tmp_path: Path) -> None:
    (tmp_path / "keep.txt").write_text("original", encoding="utf-8")
    result = run(
        tmp_path,
        [
            sys.executable,
            "-c",
            "from pathlib import Path; Path('keep.txt').write_text('changed'); "
            "Path('new.txt').write_text('x'); print(Path('keep.txt').read_text())",
        ],
        isolate_network=False,
    )
    assert result.passed
    assert result.stdout.strip() == "changed"
    assert not result.timed_out
    assert (tmp_path / "keep.txt").read_text(encoding="utf-8") == "original"
    assert not (tmp_path / "new.txt").exists()


def test_environment_is_scrubbed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AXIOME_SECRET", "do-not-leak")
    result = run(
        tmp_path,
        [sys.executable, "-c", "import os; print(os.environ.get('AXIOME_SECRET', 'absent'))"],
        isolate_network=False,
    )
    assert result.stdout.strip() == "absent"
    assert "do-not-leak" not in result.stdout + result.stderr


def test_timeout_is_reported(tmp_path: Path) -> None:
    result = run(
        tmp_path,
        [sys.executable, "-c", "import time; time.sleep(5)"],
        SandboxLimits(timeout_seconds=0.3),
        isolate_network=False,
    )
    assert result.timed_out
    assert not result.passed
    assert "timeout" in result.report()


def test_output_is_capped(tmp_path: Path) -> None:
    result = run(
        tmp_path,
        [sys.executable, "-c", "print('x' * 5000)"],
        SandboxLimits(output_bytes=20),
        isolate_network=False,
    )
    assert result.truncated
    assert len(result.stdout) == 20


def test_network_state_is_never_claimed_without_check(tmp_path: Path) -> None:
    result = run(
        tmp_path, [sys.executable, "-c", "print(1)"], isolate_network=False
    )
    assert not result.network_isolated
    assert not result.degraded_network
    requested = run(tmp_path, [sys.executable, "-c", "print(1)"], isolate_network=True)
    assert requested.degraded_network != requested.network_isolated


def test_run_tests_on_a_tiny_project(tmp_path: Path) -> None:
    (tmp_path / "test_ok.py").write_text(
        "def test_ok():\n    assert 1 + 1 == 2\n", encoding="utf-8"
    )
    assert run_tests(tmp_path, isolate_network=False).passed


def test_missing_directory_is_an_expected_error(tmp_path: Path) -> None:
    with pytest.raises(CodeError, match="not a directory"):
        run(tmp_path / "absent", [sys.executable, "-c", "print(1)"])
