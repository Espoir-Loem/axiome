"""Code index: queries, problems and determinism."""

from __future__ import annotations

from pathlib import Path

import pytest

from axiome.code.index import CodeIndex
from axiome.code.source import SourceFile
from axiome.core.errors import CodeError
from axiome.reasoning.terms import Var

FILES = (
    SourceFile("src/pkg/__init__.py", ""),
    SourceFile(
        "src/pkg/mod.py",
        "import os\n\nclass C:\n    def f(self, x):\n        return x\n\n"
        "def g():\n    return C().f(1)\n",
    ),
    SourceFile("bad.py", "def broken(:\n"),
)


def bindings(solutions: tuple[dict[Var, object], ...]) -> list[dict[str, object]]:
    return [{str(variable): term for variable, term in solution.items()} for solution in solutions]


def test_build_reports_unparsable_files() -> None:
    index = CodeIndex.build(FILES)
    assert [problem.path for problem in index.problems] == ["bad.py"]
    assert index.problems[0].line == 1
    assert "bad.py" in str(index.problems[0].message)


def test_query_binds_variables_in_canonical_order() -> None:
    index = CodeIndex.build(FILES)
    assert bindings(index.ask("?- defines(Pos, Nom).")) == [
        {"Nom": "pkg.mod.C", "Pos": "src/pkg/mod.py:3"},
        {"Nom": "pkg.mod.C.f", "Pos": "src/pkg/mod.py:4"},
        {"Nom": "pkg.mod.g", "Pos": "src/pkg/mod.py:7"},
    ]


def test_ground_queries_and_partial_queries() -> None:
    index = CodeIndex.build(FILES)
    assert index.ask('?- imports("pkg.mod", os).') == ({},)
    assert index.ask('?- imports("pkg.mod", "missing").') == ()
    assert bindings(index.ask("imports(Module, os)")) == [{"Module": "pkg.mod"}]
    assert bindings(index.ask('?- calls("pkg.mod.g", Callee).')) == [
        {"Callee": "C"},
        {"Callee": "f"},
    ]


def test_unsupported_queries_are_refused() -> None:
    index = CodeIndex.build(FILES)
    with pytest.raises(CodeError, match="unknown code predicate"):
        index.ask("?- nope(X).")
    with pytest.raises(CodeError, match="one positive literal"):
        index.ask("?- defines(Pos, Nom), imports(Module, os).")
    with pytest.raises(CodeError, match="one positive literal"):
        index.ask("?- not defines(Pos, Nom).")


def test_of_returns_canonical_facts() -> None:
    index = CodeIndex.build(FILES)
    facts = index.of("defines")
    assert facts == tuple(sorted(facts, key=lambda fact: fact.sort_key()))
    assert index.of("unknown") == ()


def test_build_is_independent_of_file_order_and_duplicates() -> None:
    forward = CodeIndex.build(FILES)
    backward = CodeIndex.build(tuple(reversed(FILES)))
    assert forward.facts == backward.facts
    assert forward.problems == backward.problems
    assert CodeIndex.build((*FILES, *FILES)).facts == forward.facts


def test_from_repository(tmp_path: Path) -> None:
    (tmp_path / "m.py").write_text("x = 1\n", encoding="utf-8")
    index = CodeIndex.from_repository(tmp_path)
    assert index.problems == ()
    assert index.ask("?- defines(Pos, Nom).") == ({Var("Pos"): "m.py:1", Var("Nom"): "m.x"},)
