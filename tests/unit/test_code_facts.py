"""Extracted facts: exact atoms, qualified names, located failures."""

from __future__ import annotations

import pytest

from axiome.code.facts import PREDICATES, extract
from axiome.code.source import SourceFile
from axiome.core.errors import CodeSyntaxError
from axiome.reasoning.terms import Atom

SOURCE = SourceFile(
    "src/pkg/m.py",
    """\
import os
import a.b as ab
from c.d import e
from . import f
from .mod import g

VALUE = 1
a, b = (2, 3)

class Cls:
    attr = 0

    def method(self, x, *, y=1):
        helper(x)
        self.attr = y
        return [n for n in range(x)]

    async def run(self):
        return await Cls.method(self, 1)

def _helper(first, second=2, *args, **kwargs):
    def inner():
        return os.path.join(str(first), str(second))
    return inner

result = Cls().method(1, y=2)
""",
)


def atoms(predicate: str, source: SourceFile = SOURCE) -> set[str]:
    return {str(atom) for atom in extract(source) if atom.predicate == predicate}


def test_predicates_are_the_documented_ones() -> None:
    assert set(PREDICATES) == {
        "appel_simple",
        "calls",
        "compare_a_none",
        "complexite",
        "defines",
        "except_vide",
        "importe_sous",
        "imports",
        "ligne",
        "parametre",
        "references",
        "retourne",
    }
    assert {atom.predicate for atom in extract(SOURCE)} <= set(PREDICATES)


def test_imports() -> None:
    assert atoms("imports") == {
        'imports("pkg.m", os)',
        'imports("pkg.m", "a.b")',
        'imports("pkg.m", "c.d.e")',
        'imports("pkg.m", ".f")',
        'imports("pkg.m", ".mod.g")',
    }


def test_definitions_are_qualified_and_located() -> None:
    assert atoms("defines") == {
        'defines("src/pkg/m.py:7", "pkg.m.VALUE")',
        'defines("src/pkg/m.py:8", "pkg.m.a")',
        'defines("src/pkg/m.py:8", "pkg.m.b")',
        'defines("src/pkg/m.py:10", "pkg.m.Cls")',
        'defines("src/pkg/m.py:11", "pkg.m.Cls.attr")',
        'defines("src/pkg/m.py:13", "pkg.m.Cls.method")',
        'defines("src/pkg/m.py:18", "pkg.m.Cls.run")',
        'defines("src/pkg/m.py:21", "pkg.m._helper")',
        'defines("src/pkg/m.py:22", "pkg.m._helper.inner")',
        'defines("src/pkg/m.py:26", "pkg.m.result")',
    }


def test_calls_keep_the_syntactic_callee() -> None:
    assert atoms("calls") == {
        'calls("pkg.m.Cls.method", helper)',
        'calls("pkg.m.Cls.method", range)',
        'calls("pkg.m.Cls.run", method)',
        'calls("pkg.m._helper.inner", join)',
        'calls("pkg.m._helper.inner", str)',
        'calls("pkg.m", "Cls")',
        'calls("pkg.m", method)',
    }


def test_parameters_exclude_varargs() -> None:
    assert atoms("parametre") == {
        'parametre("pkg.m.Cls.method", 1, self)',
        'parametre("pkg.m.Cls.method", 2, x)',
        'parametre("pkg.m.Cls.method", 3, y)',
        'parametre("pkg.m.Cls.run", 1, self)',
        'parametre("pkg.m._helper", 1, first)',
        'parametre("pkg.m._helper", 2, second)',
    }


def test_parameters_include_positional_only() -> None:
    source = SourceFile("m.py", "def f(a, /, b, *args, c, **kwargs):\n    pass\n")
    assert atoms("parametre", source) == {
        'parametre("m.f", 1, a)',
        'parametre("m.f", 2, b)',
        'parametre("m.f", 3, c)',
    }


def test_references_are_deduplicated_per_position() -> None:
    references = atoms("references")
    assert len(references) == 15
    assert 'references("src/pkg/m.py:14", helper)' in references
    assert 'references("src/pkg/m.py:16", range)' in references
    assert 'references("src/pkg/m.py:24", inner)' in references
    assert 'references("src/pkg/m.py:26", "Cls")' in references
    assert 'references("src/pkg/m.py:23", str)' in references  # read twice on that line


def test_lines_are_citable() -> None:
    facts = extract(SourceFile("m.py", "x = 1\n\n"))
    assert [str(atom) for atom in facts if atom.predicate == "ligne"] == [
        'ligne("m.py:1", "x = 1")',
        'ligne("m.py:2", "")',
    ]


def test_bases_starred_targets_and_indirect_calls() -> None:
    source = SourceFile(
        "m.py", "class Sub(Base):\n    pass\n\nfirst, *rest = values\nfactory()(1)\n"
    )
    assert atoms("defines", source) == {
        'defines("m.py:1", "m.Sub")',
        'defines("m.py:4", "m.first")',
        'defines("m.py:4", "m.rest")',
    }
    assert atoms("calls", source) == {"calls(m, factory)"}
    assert atoms("references", source) == {
        'references("m.py:1", "Base")',
        'references("m.py:4", values)',
        'references("m.py:5", factory)',
    }


def test_import_bindings_retours_complexite_et_motifs() -> None:
    source = SourceFile(
        "m.py",
        """\
import os
import a.b as ab
from . import f

def work(x):
    if x and x > 1:
        return 1
    return None

try:
    g()
except:
    pass

if x == None:
    pass
""",
    )
    assert atoms("importe_sous", source) == {
        'importe_sous(m, os, os, "m.py:1")',
        'importe_sous(m, ab, "a.b", "m.py:2")',
        'importe_sous(m, f, ".f", "m.py:3")',
    }
    assert atoms("complexite", source) == {'complexite("m.work", 3)'}
    assert atoms("retourne", source) == {
        'retourne("m.work", "m.py:7")',
        'retourne("m.work", "m.py:8")',
    }
    assert atoms("except_vide", source) == {'except_vide("m.py:12")'}
    assert atoms("compare_a_none", source) == {'compare_a_none("m.py:15")'}
    assert atoms("appel_simple", source) == {'appel_simple(m, g, "m.py:11")'}


def test_syntax_error_is_located() -> None:
    with pytest.raises(CodeSyntaxError) as error:
        extract(SourceFile("bad.py", "x = 1\ndef broken(:\n"))
    assert (error.value.path, error.value.line) == ("bad.py", 2)
    assert "bad.py, line 2" in str(error.value)


def test_empty_file_has_no_facts() -> None:
    assert extract(SourceFile("empty.py", "")) == ()


def test_facts_are_sorted_canonically() -> None:
    facts = extract(SOURCE)
    assert all(isinstance(atom, Atom) for atom in facts)
    assert list(facts) == sorted(set(facts), key=Atom.sort_key)
