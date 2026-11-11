"""``python -m axiome.evaluation [evals_dir [suite]]``: run a suite, print and save the report.

``suite`` is a sub-directory of ``evals_dir`` (default ``suites``). The held-out
suite (``heldout``) is never used while fixing failures: it measures whether a
fix generalizes instead of fitting the cases it was written for.
"""

from __future__ import annotations

import sys
from pathlib import Path

from axiome.evaluation.runner import run
from axiome.i18n import set_locale


def main(argv: list[str]) -> int:
    root = Path(argv[0]) if argv else Path("evals")
    suite = argv[1] if len(argv) > 1 else "suites"
    set_locale("fr")
    report = run(root / suite, root / "fixtures" / "web.json")
    text = report.markdown()
    (root / "reports").mkdir(exist_ok=True)
    name = "latest" if suite == "suites" else suite
    (root / "reports" / f"{name}.md").write_text(text, "utf-8")
    passed, total = report.score
    for cat, (ok, n) in report.by_category().items():
        print(f"{cat:<14} {ok:>3}/{n:<3}")
    print(f"{'TOTAL':<14} {passed:>3}/{total:<3}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
