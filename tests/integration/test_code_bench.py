"""Code benches: labelled review must be perfect per rule; pass@1 measured."""

from __future__ import annotations

from pathlib import Path

from axiome.evaluation.codebench import load_generation, load_review, run_generation, run_review

BENCH = Path(__file__).parents[2] / "evals" / "code"


def test_review_bench_per_rule() -> None:
    cases = load_review(BENCH / "review.jsonl")
    assert len(cases) == 5
    report = run_review(cases)
    assert report.perfect
    assert {"import_inutilise", "exception_avalee", "comparaison_a_none", "appel_inconnu"} <= set(
        report.rules
    )
    assert all(score.recall == 1.0 and score.precision == 1.0 for score in report.rules.values())


def test_generation_bench_has_no_silent_failure() -> None:
    cases = load_generation(BENCH / "generation.jsonl")
    report = run_generation(cases)
    assert report.cases == 14
    assert report.pass_at_1 == 1.0
    assert report.silent_failures == 0
