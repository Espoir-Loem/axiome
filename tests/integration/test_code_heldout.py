"""Held-out generation bench: replay real commits, never read their patch."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from axiome.evaluation.heldout import load_heldout, run_heldout

REPOSITORY = Path(__file__).parents[2]
BENCH = REPOSITORY / "evals" / "code" / "heldout.jsonl"


def _history_available() -> bool:
    """The bench reads parent trees with git; a shallow clone cannot provide them."""
    return all(
        subprocess.run(
            ["git", "-C", str(REPOSITORY), "cat-file", "-e", f"{case.parent}^{{commit}}"],
            capture_output=True,
            check=False,
        ).returncode
        == 0
        for case in load_heldout(BENCH)
    )


pytestmark = pytest.mark.skipif(not _history_available(), reason="full git history required")


def test_heldout_bench_replays_real_patches() -> None:
    cases = load_heldout(BENCH)
    report = run_heldout(cases, REPOSITORY)
    assert report.cases >= 1
    # Measured 2026-11-18: the search finds nothing on a real patch. The number is
    # recorded on purpose, so an improvement (or a regression) has to be deliberate.
    assert report.pass_at_1 == 0.0
