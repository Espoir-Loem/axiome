"""Replay bench: real commits reverted, their patch never read."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from axiome.evaluation.replay import load_replay, run_replay

REPOSITORY = Path(__file__).parents[2]
BENCH = REPOSITORY / "evals" / "code" / "replay"


def _history_available() -> bool:
    """The bench extracts commit trees with git; a shallow clone cannot provide them."""
    return all(
        subprocess.run(
            ["git", "-C", str(REPOSITORY), "cat-file", "-e", f"{case.commit}^{{commit}}"],
            capture_output=True,
            check=False,
        ).returncode
        == 0
        for case in load_replay(BENCH)
    )


pytestmark = pytest.mark.skipif(not _history_available(), reason="full git history required")


def test_replay_bench_measures_real_patches() -> None:
    cases = load_replay(BENCH)
    report = run_replay(cases, REPOSITORY)
    assert report.cases >= 3
    assert report.multi_file >= 1
    # Measured 2026-11-18: the search finds nothing on a real patch. The number is
    # recorded on purpose, so an improvement (or a regression) has to be deliberate.
    assert report.pass_at_1 == 0.0
