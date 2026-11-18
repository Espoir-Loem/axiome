"""Diff review: apply in memory, keep only new diagnostics, pass the Reviewer."""

from __future__ import annotations

from pathlib import Path

import pytest

from axiome.code.review import apply_diff, parse_diff, review_diff
from axiome.core.errors import CodeError
from axiome.language.pack import load_pack
from axiome.team.code_review import claims_for, review_findings

BEFORE = "m.py", "import os\n\nprint(os.getcwd())\n"
ADD_UNUSED = (
    "--- a/m.py\n+++ b/m.py\n@@ -1,3 +1,4 @@\n import os\n+import math\n \n print(os.getcwd())\n"
)
ADD_USED = (
    "--- a/m.py\n"
    "+++ b/m.py\n"
    "@@ -1,3 +1,4 @@\n"
    " import os\n"
    "+import math\n"
    " \n"
    "-print(os.getcwd())\n"
    "+print(os.getcwd(), math.pi)\n"
)


def repository(tmp_path: Path, text: str = BEFORE[1]) -> Path:
    (tmp_path / BEFORE[0]).write_text(text, encoding="utf-8")
    return tmp_path


def test_review_reports_only_new_diagnostics(tmp_path: Path) -> None:
    root = repository(tmp_path)
    findings = review_diff(root, ADD_UNUSED)
    assert [(d.rule, d.position, d.line) for d in findings] == [
        ("import_inutilise", "m.py:2", "import math")
    ]
    assert findings[0].support
    assert review_diff(root, ADD_USED) == ()


def test_review_never_touches_the_working_tree(tmp_path: Path) -> None:
    root = repository(tmp_path)
    review_diff(root, ADD_UNUSED)
    assert (root / "m.py").read_text(encoding="utf-8") == BEFORE[1]


def test_apply_diff_adds_modifies_and_deletes(tmp_path: Path) -> None:
    del tmp_path
    diff = """\
--- /dev/null
+++ b/new.py
@@ -0,0 +1,2 @@
+x = 1
+y = 2
--- a/old.py
+++ /dev/null
@@ -1,1 +0,0 @@
-z = 3
"""
    tree = apply_diff({"old.py": "z = 3"}, diff)
    assert tree == {"new.py": "x = 1\ny = 2"}


def test_malformed_diffs_are_refused() -> None:
    with pytest.raises(CodeError, match="unreadable diff"):
        parse_diff("not a diff")
    with pytest.raises(CodeError, match="missing"):
        parse_diff("--- a/m.py\n")
    with pytest.raises(CodeError, match="out of range"):
        apply_diff({"m.py": "x = 1\n"}, "--- a/m.py\n+++ b/m.py\n@@ -9,1 +9,1 @@\n-x = 1\n+x = 2\n")
    with pytest.raises(CodeError, match="missing from the repository"):
        apply_diff({}, "--- a/missing.py\n+++ b/missing.py\n@@ -1,1 +1,1 @@\n-a\n+b\n")


def test_findings_pass_the_existing_reviewer(tmp_path: Path) -> None:
    findings = review_diff(repository(tmp_path), ADD_UNUSED)
    claims = claims_for(findings)
    assert len(claims) == 1
    assert claims[0].support
    assert "m.py:2" in claims[0].text
    review = review_findings(findings, load_pack("fr"))
    assert not review.blocked
    assert len(review.approved) == 1
