"""Diagnostics over the code index (M7.1).

Every rule is a query on the ground facts of :mod:`axiome.code.facts`: no
heuristic, no opaque score. A diagnostic always carries a rule name, a
position, the cited source line and the facts that support it, so it can be
verified (``VÉRIFIÉ``, E3) and reviewed like any other claim (RFC-0002).

Rules of the first batch:

``import_inutilise``
    an imported binding is never read in its module.
``nom_non_utilise``
    a module-level assignment is never read anywhere.
``code_mort``
    a module-level function or class is never referenced, called or exported.
``appel_inconnu``
    a bare call names nothing defined, imported or built in.
``exception_avalee``
    ``except: pass``.
``comparaison_a_none``
    ``== None`` / ``!= None``.
``complexite_cyclomatique``
    cyclomatic complexity above the configured threshold.
``cycle_import``
    modules importing each other in a cycle.

Enabled rules and the complexity threshold are declared in
``[tool.axiome.code]`` of ``pyproject.toml``.
"""

from __future__ import annotations

import builtins
import sys
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any, cast

from axiome.code.index import CodeIndex
from axiome.code.source import Position, module_name
from axiome.core.errors import CodeError
from axiome.i18n import Msg, msg
from axiome.reasoning.terms import Atom

BLOCKING = "bloquant"
TO_FIX = "a_corriger"
REMARK = "remarque"


@dataclass(frozen=True, slots=True)
class Rule:
    """One named rule: its severity is fixed, never computed."""

    name: str
    severity: str


RULES: Mapping[str, Rule] = {
    rule.name: rule
    for rule in (
        Rule("import_inutilise", TO_FIX),
        Rule("nom_non_utilise", TO_FIX),
        Rule("code_mort", REMARK),
        Rule("appel_inconnu", TO_FIX),
        Rule("exception_avalee", BLOCKING),
        Rule("comparaison_a_none", TO_FIX),
        Rule("complexite_cyclomatique", TO_FIX),
        Rule("cycle_import", TO_FIX),
    )
}
DEFAULT_COMPLEXITY_THRESHOLD = 10


@dataclass(frozen=True, slots=True)
class AnalysisConfig:
    """Which rules run, and with which threshold."""

    enabled: frozenset[str] = frozenset(RULES)
    complexity_threshold: int = DEFAULT_COMPLEXITY_THRESHOLD


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """A located, supported rule violation."""

    rule: str
    severity: str
    position: str
    line: str
    message: Msg
    support: tuple[Atom, ...]

    @property
    def path(self) -> str:
        return Position.parse(self.position).path


def load_config(path: str | Path = "pyproject.toml") -> AnalysisConfig:
    """Read ``[tool.axiome.code]``; absent file or section means defaults."""
    file = Path(path)
    if file.is_dir():
        file = file / "pyproject.toml"
    if not file.is_file():
        return AnalysisConfig()
    document = _read_toml(file)
    section = document.get("tool", {}).get("axiome", {}).get("code", {})
    if not section:
        return AnalysisConfig()
    enabled = frozenset(str(name) for name in section.get("rules", RULES))
    unknown = sorted(enabled - set(RULES))
    if unknown:
        raise CodeError("code.unknown_rule", rule=", ".join(unknown))
    threshold = section.get("complexity_threshold", DEFAULT_COMPLEXITY_THRESHOLD)
    if not isinstance(threshold, int) or threshold < 1:
        raise CodeError("code.bad_threshold", value=threshold)
    return AnalysisConfig(enabled, threshold)


def _read_toml(path: Path) -> dict[str, Any]:
    if sys.version_info < (3, 11):  # pragma: no cover - the project supports 3.10
        return {}
    toml = cast("Any", import_module("tomllib"))
    with path.open("rb") as handle:
        return cast("dict[str, Any]", toml.load(handle))


def analyze(index: CodeIndex, config: AnalysisConfig | None = None) -> tuple[Diagnostic, ...]:
    """Run the enabled rules and return diagnostics sorted by position."""
    settings = config or AnalysisConfig()
    facts = _Facts(index)
    out: list[Diagnostic] = []
    for name in sorted(settings.enabled):
        rule = RULES.get(name)
        if rule is None:
            continue
        found = _CHECKS[name](facts, rule, settings)
        out.extend(found)
    return tuple(sorted(out, key=_diagnostic_key))


def _diagnostic_key(d: Diagnostic) -> tuple[str, int, str, str]:
    parsed = Position.parse(d.position)
    return (parsed.path, parsed.line, d.rule, str(d.message))


class _Facts:
    """Index views shared by the rules (each one is a plain lookup)."""

    def __init__(self, index: CodeIndex) -> None:
        self.index = index
        self.lines: dict[str, str] = {
            str(fact.args[0]): str(fact.args[1]) for fact in index.of("ligne")
        }
        self.defines: dict[str, Atom] = {str(fact.args[1]): fact for fact in index.of("defines")}
        self.module_paths: dict[str, str] = {}
        for position in self.lines:
            path = Position.parse(position).path
            try:
                self.module_paths.setdefault(module_name(path), path)
            except ValueError:
                continue
        self.modules = frozenset(self.module_paths)
        self.imported = {fact.args[0] for fact in index.of("importe_sous")}
        self.import_targets = {str(fact.args[1]) for fact in index.of("imports")}
        self.referenced = {str(fact.args[1]) for fact in index.of("references")}
        self.called = {str(fact.args[1]) for fact in index.of("calls")}
        self.refs_by_module: dict[str, set[str]] = {}
        for fact in index.of("references"):
            path = Position.parse(str(fact.args[0])).path
            try:
                scope = module_name(path)
            except ValueError:  # pragma: no cover - index only holds source paths
                continue
            self.refs_by_module.setdefault(scope, set()).add(str(fact.args[1]))

    def line(self, position: str) -> str:
        return self.lines.get(position, "")

    def module_of_position(self, position: str) -> str:
        return module_name(Position.parse(position).path)

    def module_of_name(self, qualified: str) -> str:
        """Longest known module prefix of a qualified name."""
        parts = qualified.split(".")
        for size in range(len(parts), 0, -1):
            candidate = ".".join(parts[:size])
            if candidate in self.modules:
                return candidate
        return parts[0]

    def imported_names(self, module: str) -> set[str]:
        return {
            str(fact.args[1]) for fact in self.index.of("importe_sous") if fact.args[0] == module
        }

    def exported(self, name: str) -> bool:
        return any(target == name or target.endswith(f".{name}") for target in self.import_targets)


def _diagnostic(
    rule: Rule, position: str, line: str, message: Msg, support: Iterable[Atom]
) -> Diagnostic:
    return Diagnostic(rule.name, rule.severity, position, line, message, tuple(support))


def _import_inutilise(facts: _Facts, rule: Rule, _config: AnalysisConfig) -> list[Diagnostic]:
    out: list[Diagnostic] = []
    for fact in facts.index.of("importe_sous"):
        module, name, target, position = (str(arg) for arg in fact.args)
        if name == "*" or name in facts.refs_by_module.get(module, set()):
            continue
        if Position.parse(position).path.endswith("__init__.py"):  # public re-export
            continue
        if name in _simple_calls(facts, module):
            continue
        if name in {"annotations"}:
            continue
        support = (Atom("imports", (module, target)), fact)
        out.append(
            _diagnostic(
                rule,
                position,
                facts.line(position),
                msg("code.diag.import_inutilise", name=name),
                support,
            )
        )
    return out


def _simple_calls(facts: _Facts, module: str) -> set[str]:
    names: set[str] = set()
    for fact in facts.index.of("appel_simple"):
        if facts.module_of_name(str(fact.args[0])) == module:
            names.add(str(fact.args[1]))
    return names


def _nom_non_utilise(facts: _Facts, rule: Rule, _config: AnalysisConfig) -> list[Diagnostic]:
    out: list[Diagnostic] = []
    for qualified, fact in facts.defines.items():
        position = str(fact.args[0])
        name = qualified.rsplit(".", 1)[-1]
        module = facts.module_of_name(qualified)
        if qualified != f"{module}.{name}" or name.startswith("_") or name == "__all__":
            continue
        if not _is_assignment(facts.line(position)):
            continue
        if name in facts.referenced or name in facts.called or facts.exported(name):
            continue
        out.append(
            _diagnostic(
                rule,
                position,
                facts.line(position),
                msg("code.diag.nom_non_utilise", name=name),
                (fact,),
            )
        )
    return out


def _is_assignment(line: str) -> bool:
    stripped = line.lstrip()
    return "=" in stripped and not stripped.startswith(("def ", "async def ", "class ", "@"))


def _code_mort(facts: _Facts, rule: Rule, _config: AnalysisConfig) -> list[Diagnostic]:
    out: list[Diagnostic] = []
    for qualified, fact in facts.defines.items():
        position = str(fact.args[0])
        line = facts.line(position).lstrip()
        name = qualified.rsplit(".", 1)[-1]
        module = facts.module_of_name(qualified)
        if not line.startswith(("def ", "async def ", "class ")):
            continue
        if qualified != f"{module}.{name}" or name.startswith("_"):
            continue
        if name.startswith("test_"):  # test entry points are called by the runner
            continue
        if name in facts.referenced or name in facts.called or facts.exported(name):
            continue
        out.append(
            _diagnostic(
                rule,
                position,
                facts.line(position),
                msg("code.diag.code_mort", name=name),
                (fact,),
            )
        )
    return out


def _appel_inconnu(facts: _Facts, rule: Rule, _config: AnalysisConfig) -> list[Diagnostic]:
    out: list[Diagnostic] = []
    implicit = {"__import__", "cls", "print", "self", "super"}
    known = set(dir(builtins)) | implicit | set(facts.defines)
    known |= {qualified.rsplit(".", 1)[-1] for qualified in facts.defines}
    for fact in facts.index.of("appel_simple"):
        caller, name, position = (str(arg) for arg in fact.args)
        module = facts.module_of_name(caller)
        if name in known or name in facts.imported_names(module):
            continue
        out.append(
            _diagnostic(
                rule,
                position,
                facts.line(position),
                msg("code.diag.appel_inconnu", name=name),
                (fact,),
            )
        )
    return out


def _exception_avalee(facts: _Facts, rule: Rule, _config: AnalysisConfig) -> list[Diagnostic]:
    return [
        _diagnostic(
            rule,
            position,
            facts.line(position),
            msg("code.diag.exception_avalee"),
            (fact,),
        )
        for fact in facts.index.of("except_vide")
        for position in (str(fact.args[0]),)
    ]


def _comparaison_a_none(facts: _Facts, rule: Rule, _config: AnalysisConfig) -> list[Diagnostic]:
    return [
        _diagnostic(
            rule,
            position,
            facts.line(position),
            msg("code.diag.comparaison_a_none"),
            (fact,),
        )
        for fact in facts.index.of("compare_a_none")
        for position in (str(fact.args[0]),)
    ]


def _complexite_cyclomatique(facts: _Facts, rule: Rule, config: AnalysisConfig) -> list[Diagnostic]:
    out: list[Diagnostic] = []
    for fact in facts.index.of("complexite"):
        name, raw = str(fact.args[0]), fact.args[1]
        define = facts.defines.get(name)
        if not isinstance(raw, int) or define is None or raw <= config.complexity_threshold:
            continue
        value = raw
        position = str(define.args[0])
        out.append(
            _diagnostic(
                rule,
                position,
                facts.line(position),
                msg(
                    "code.diag.complexite_cyclomatique",
                    name=name,
                    value=value,
                    threshold=config.complexity_threshold,
                ),
                (fact, define),
            )
        )
    return out


def _cycle_import(facts: _Facts, rule: Rule, _config: AnalysisConfig) -> list[Diagnostic]:
    edges = _import_edges(facts)
    out: list[Diagnostic] = []
    for cycle in _cycles(edges):
        members = ", ".join(sorted(cycle))
        for module in sorted(cycle):
            path = facts.module_paths.get(module)
            if path is None:  # pragma: no cover - an import implies a source line
                continue
            position = str(Position(path, 1))
            support = tuple(
                fact
                for fact in facts.index.of("imports")
                if str(fact.args[0]) == module and _target_module(facts, str(fact.args[1])) in cycle
            )
            out.append(
                _diagnostic(
                    rule,
                    position,
                    facts.line(position),
                    msg("code.diag.cycle_import", modules=members),
                    support,
                )
            )
    return out


def _target_module(facts: _Facts, target: str) -> str | None:
    """Longest known module prefix of an import target (``None`` if external)."""
    candidate = target.lstrip(".")
    parts = candidate.split(".")
    for size in range(len(parts), 0, -1):
        module = ".".join(parts[:size])
        if module in facts.modules:
            return module
    return None


def _import_edges(facts: _Facts) -> dict[str, set[str]]:
    edges: dict[str, set[str]] = {module: set() for module in facts.modules}
    for fact in facts.index.of("imports"):
        module = str(fact.args[0])
        target = _target_module(facts, str(fact.args[1]))
        if target is not None and target != module:
            edges[module].add(target)
    return edges


def _cycles(edges: Mapping[str, set[str]]) -> list[tuple[str, ...]]:
    """Strongly connected components that contain a cycle, deterministically."""
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    components: list[tuple[str, ...]] = []
    counter = 0

    def visit(node: str) -> None:
        nonlocal counter
        index[node] = low[node] = counter
        counter += 1
        stack.append(node)
        on_stack.add(node)
        for neighbour in sorted(edges.get(node, ())):
            if neighbour not in index:
                visit(neighbour)
                low[node] = min(low[node], low[neighbour])
            elif neighbour in on_stack:
                low[node] = min(low[node], index[neighbour])
        if low[node] == index[node]:
            component: list[str] = []
            while True:
                member = stack.pop()
                on_stack.discard(member)
                component.append(member)
                if member == node:
                    break
            if len(component) > 1 or node in edges.get(node, ()):
                components.append(tuple(sorted(component)))

    for node in sorted(edges):
        if node not in index:
            visit(node)
    return sorted(components)


_CHECKS = {
    "import_inutilise": _import_inutilise,
    "nom_non_utilise": _nom_non_utilise,
    "code_mort": _code_mort,
    "appel_inconnu": _appel_inconnu,
    "exception_avalee": _exception_avalee,
    "comparaison_a_none": _comparaison_a_none,
    "complexite_cyclomatique": _complexite_cyclomatique,
    "cycle_import": _cycle_import,
}
