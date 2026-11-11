"""The evaluation harness: every suite passes, grading and reports behave."""

from __future__ import annotations

import shutil
from pathlib import Path

from axiome.evaluation.__main__ import main
from axiome.evaluation.runner import Case, FixtureProvider, grade, load_cases, run

EVALS = Path(__file__).resolve().parents[2] / "evals"


def test_main_suite_and_heldout_pass() -> None:
    for suite in ("suites", "heldout"):
        report = run(EVALS / suite, EVALS / "fixtures" / "web.json")
        failed = [(o.case.id, o.failures) for o in report.outcomes if not o.passed]
        assert not failed, failed


def test_grade_reports_every_problem() -> None:
    case = Case(
        "x-fr-001",
        "x",
        "fr",
        "q",
        {
            "contains": ["chat"],
            "not_contains": ["chien"],
            "any_of": ["a", "b"],
            "starts_with": "Oui",
            "equals": "Oui",
            "no_search": True,
            "max_chars": 3,
        },
    )
    problems = grade(case, "Non, chien", searched=True, tells=["S1"])
    assert len(problems) == 8
    searches = Case("y-fr-001", "x", "fr", "q", {"searches": True})
    assert grade(searches, "", searched=False, tells=[]) == ["n'a pas cherché"]


def test_fixture_language_key_wins() -> None:
    rec = {"url": "https://x.org/a", "title": "A", "text": "t"}
    provider = FixtureProvider({"photon": [rec], "en:photon": [{**rec, "title": "B"}]})
    assert provider.search("Photon ?", "en", 3)[0].title == "B"
    assert provider.search("photon", "fr", 3)[0].title == "A"


def test_report_and_entry_point(tmp_path: Path) -> None:
    root = tmp_path / "evals"
    shutil.copytree(EVALS / "fixtures", root / "fixtures")
    (root / "suites").mkdir()
    good = '{"id": "a-fr-001", "category": "a", "lang": "fr", "turn": "merci", "expect": {}}'
    bad = (
        '{"id": "a-fr-002", "category": "a", "lang": "fr", "turn": "merci",'
        ' "expect": {"contains": ["absent"]}, "online": false}'
    )
    (root / "suites" / "a.jsonl").write_text(f"// comment\n{good}\n\n{bad}\n", "utf-8")
    assert main([str(root)]) == 1
    text = (root / "reports" / "latest.md").read_text("utf-8")
    assert "**1/2**" in text and "a-fr-002" in text and "manque « absent »" in text
    (root / "suites" / "a.jsonl").write_text(good + "\n", "utf-8")
    assert main([str(root)]) == 0


def test_duplicate_ids_are_refused(tmp_path: Path) -> None:
    line = '{"id": "d-fr-001", "category": "d", "lang": "fr", "turn": "t", "expect": {}}'
    path = tmp_path / "d.jsonl"
    path.write_text(f"{line}\n{line}\n", "utf-8")
    try:
        load_cases([path])
    except ValueError as exc:
        assert "d-fr-001" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("duplicates accepted")
