"""Analysis rules: one positive and one negative case per rule, all located."""

from __future__ import annotations

from pathlib import Path

import pytest

from axiome.code.analyze import (
    AnalysisConfig,
    Diagnostic,
    analyze,
    load_config,
)
from axiome.code.index import CodeIndex
from axiome.code.source import Position, SourceFile
from axiome.core.errors import CodeError


def run(rule: str, source: str, threshold: int = 10) -> tuple[Diagnostic, ...]:
    index = CodeIndex.build((SourceFile("m.py", source),))
    return analyze(index, AnalysisConfig(frozenset({rule}), threshold))


def test_import_inutilise() -> None:
    found = run("import_inutilise", "import os\n\nx = 1\n")
    assert [(d.rule, d.position, d.line) for d in found] == [
        ("import_inutilise", "m.py:1", "import os")
    ]
    assert found[0].support
    assert run("import_inutilise", "import os\n\nos.getcwd()\n") == ()


def test_nom_non_utilise() -> None:
    found = run("nom_non_utilise", "x = 1\n")
    assert [(d.position, d.line) for d in found] == [("m.py:1", "x = 1")]
    assert run("nom_non_utilise", "x = 1\nprint(x)\n") == ()


def test_code_mort() -> None:
    found = run("code_mort", "def helper():\n    return 1\n")
    assert [(d.position, d.line) for d in found] == [("m.py:1", "def helper():")]
    assert run("code_mort", "def helper():\n    return 1\n\nhelper()\n") == ()


def test_appel_inconnu() -> None:
    found = run("appel_inconnu", "def f():\n    missing()\n")
    assert [(d.position, d.line) for d in found] == [("m.py:2", "    missing()")]
    assert run("appel_inconnu", "def f():\n    print(1)\n") == ()


def test_exception_avalee() -> None:
    source = "try:\n    pass\nexcept:\n    pass\n"
    found = run("exception_avalee", source)
    assert [(d.severity, d.position) for d in found] == [("bloquant", "m.py:3")]
    assert run("exception_avalee", "try:\n    pass\nexcept ValueError:\n    raise\n") == ()


def test_comparaison_a_none() -> None:
    found = run("comparaison_a_none", "x = 1\nif x == None:\n    pass\n")
    assert [d.position for d in found] == ["m.py:2"]
    assert run("comparaison_a_none", "x = 1\nif x is None:\n    pass\n") == ()


def test_complexite_avec_formule_et_seuil() -> None:
    source = (
        "def f(x):\n"
        "    if x:\n"
        "        return 1\n"
        "    if x > 1:\n"
        "        return 2\n"
        "    return 3\n"
    )
    found = run("complexite_cyclomatique", source, threshold=2)
    assert len(found) == 1
    assert found[0].position == "m.py:1"
    assert "3 > 2" in str(found[0].message)
    assert "1 + decision points" in str(found[0].message)
    assert run("complexite_cyclomatique", source, threshold=3) == ()


def test_cycle_import() -> None:
    files = (
        SourceFile("a.py", "import b\n\nx = 1\n"),
        SourceFile("b.py", "import a\n\ny = 1\n"),
    )
    found = analyze(
        CodeIndex.build(files), AnalysisConfig(frozenset({"cycle_import"}))
    )
    assert [(d.rule, d.path) for d in found] == [
        ("cycle_import", "a.py"),
        ("cycle_import", "b.py"),
    ]
    assert all(d.support for d in found)
    one_way = (SourceFile("a.py", "import b\n\nx = 1\n"), SourceFile("b.py", "y = 1\n"))
    assert analyze(CodeIndex.build(one_way), AnalysisConfig(frozenset({"cycle_import"}))) == ()


def test_every_diagnostic_has_a_position_and_support() -> None:
    source = (
        "import os\n"
        "unused = 1\n"
        "def dead():\n"
        "    missing()\n"
        "try:\n"
        "    pass\n"
        "except:\n"
        "    pass\n"
        "if 1 == None:\n"
        "    pass\n"
    )
    index = CodeIndex.build((SourceFile("m.py", source),))
    findings = analyze(index)
    assert findings
    for diagnostic in findings:
        assert Position.parse(diagnostic.position)
        assert diagnostic.line
        assert diagnostic.support
        assert diagnostic.severity in {"bloquant", "a_corriger", "remarque"}


def test_rules_are_deterministic_and_sorted() -> None:
    index = CodeIndex.build((SourceFile("m.py", "x = 1\nimport os\n"),))
    first = analyze(index)
    assert first == analyze(index)
    positions = [Position.parse(d.position) for d in first]
    assert positions == sorted(positions, key=lambda p: (p.path, p.line))


def test_load_config(tmp_path: Path) -> None:
    assert load_config(tmp_path / "absent.toml") == AnalysisConfig()
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[tool.axiome.code]\nrules = ["code_mort"]\ncomplexity_threshold = 4\n',
        encoding="utf-8",
    )
    config = load_config(pyproject)
    assert config.enabled == frozenset({"code_mort"})
    assert config.complexity_threshold == 4
    pyproject.write_text('[tool.axiome.code]\nrules = ["nope"]\n', encoding="utf-8")
    with pytest.raises(CodeError, match="unknown analysis rule"):
        load_config(pyproject)
    pyproject.write_text("[tool.axiome.code]\ncomplexity_threshold = 0\n", encoding="utf-8")
    with pytest.raises(CodeError, match="invalid complexity threshold"):
        load_config(pyproject)
