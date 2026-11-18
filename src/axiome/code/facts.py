"""Python source to Axiome facts (M7.0).

The code index is a logic program: every extracted item is a ground atom, so
code questions are ordinary ``?-`` queries and every later diagnostic can carry
a proof. The predicates are:

``defines(Pos, Nom)``
    ``Nom`` is defined at ``Pos``: function, method, class letter or assigned name.
``references(Pos, Nom)``
    ``Nom`` is read at ``Pos`` (syntactic name, not yet resolved).
``imports(Module, Cible)``
    ``Module`` imports the dotted target ``Cible`` (``*`` allowed, relative
    imports keep their leading dots).
``calls(Appelant, Appelé)``
    ``Appelant`` calls ``Appelé``; the callee is the syntactic name or attribute,
    so dynamic dispatch is never asserted (RFC-0002).
``parametre(Fonction, Rang, Nom)``
    positional (positional-only included) and keyword-only parameter.
``retourne(Nom, Pos)``
    ``return`` statement at ``Pos`` inside ``Nom``.
``complexite(Nom, N)``
    cyclomatic complexity of ``Nom``: ``1 + decision points``.
``importe_sous(Module, Nom, Cible, Pos)``
    ``Module`` binds ``Nom`` to the dotted target ``Cible`` at ``Pos``.
``appel_simple(Appelant, Nom, Pos)``
    ``Appelant`` calls the bare name ``Nom`` at ``Pos`` (no attribute).
``except_vide(Pos)``
    ``except: pass`` (or ``...``) at ``Pos``: the error is swallowed.
``compare_a_none(Pos)``
    ``== None`` / ``!= None`` comparison at ``Pos``.
``ligne(Pos, Texte)``
    source text of a line, for citing a position.

Definitions and callers are fully qualified by module and by enclosing
definition (``pkg.mod.Cls.method``); module level is the module itself.
"""

from __future__ import annotations

import ast

from axiome.code.source import Position, SourceFile, module_name
from axiome.core.errors import CodeSyntaxError
from axiome.reasoning.terms import Atom

#: Every predicate produced by :func:`extract`, in canonical order.
PREDICATES = (
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
)

_FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)


def extract(source: SourceFile) -> tuple[Atom, ...]:
    """Extract the facts of one source file, sorted canonically."""
    try:
        tree = ast.parse(source.text, filename=source.path)
    except SyntaxError as exc:
        raise CodeSyntaxError(
            "code.syntax_error", path=source.path, line=exc.lineno or 0, detail=exc.msg
        ) from exc
    atoms: list[Atom] = []
    for number, text in enumerate(source.text.splitlines(), start=1):
        atoms.append(_fact("ligne", str(Position(source.path, number)), text))
    module = module_name(source.path)
    _scan(tree, source.path, module, module, atoms)
    unique = {atom.sort_key(): atom for atom in atoms}
    return tuple(unique[key] for key in sorted(unique))


def _scan(node: ast.AST, path: str, module: str, scope: str, out: list[Atom]) -> None:
    """Walk ``node`` in ``scope`` (module name or qualified definition)."""
    if isinstance(node, _FUNCTIONS):
        _scan_function(node, path, module, scope, out)
        return
    if isinstance(node, ast.ClassDef):
        _scan_class(node, path, module, scope, out)
        return
    _scan_leaf(node, module, scope, path, out)
    for child in ast.iter_child_nodes(node):
        _scan(child, path, module, scope, out)


def _scan_function(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    path: str,
    module: str,
    scope: str,
    out: list[Atom],
) -> None:
    """A function defines its (qualified) name and parameters; its body is a new scope."""
    name = f"{scope}.{node.name}"
    out.append(_fact("defines", _position(path, node.lineno), name))
    out.append(_fact("complexite", name, _cyclomatic(node)))
    for rank, argument in enumerate(_parameters(node.args), start=1):
        out.append(_fact("parametre", name, rank, argument))
    for child in (
        *node.decorator_list,
        *node.args.defaults,
        *node.args.kw_defaults,
        *(argument.annotation for argument in _arguments(node.args)),
        node.returns,
    ):
        if child is not None:
            _scan(child, path, module, scope, out)
    for statement in node.body:
        _scan(statement, path, module, name, out)
    for line in _returns(node, path, name):
        out.append(_fact("retourne", name, line))


def _scan_class(node: ast.ClassDef, path: str, module: str, scope: str, out: list[Atom]) -> None:
    """A class is a scope of its own: methods are qualified through it."""
    name = f"{scope}.{node.name}"
    out.append(_fact("defines", _position(path, node.lineno), name))
    for child in (*node.decorator_list, *node.bases, *node.keywords):
        _scan(child, path, module, scope, out)
    for statement in node.body:
        _scan(statement, path, module, name, out)


def _scan_leaf(node: ast.AST, module: str, scope: str, path: str, out: list[Atom]) -> None:
    """Facts carried by the node itself (not by its children)."""
    if isinstance(node, ast.Import):
        _record_import(node, module, path, out)
    elif isinstance(node, ast.ImportFrom):
        _record_import_from(node, module, path, out)
    elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
        out.append(_fact("references", _position(path, node.lineno), node.id))
    elif isinstance(node, ast.Call):
        _record_call(node, scope, path, out)
    elif isinstance(node, (ast.Compare, ast.ExceptHandler)):
        _record_pattern(node, path, out)
    elif isinstance(node, (ast.Assign, ast.AnnAssign)):
        for assigned in _assigned_names(node):
            out.append(_fact("defines", _position(path, node.lineno), f"{scope}.{assigned}"))


def _record_pattern(node: ast.Compare | ast.ExceptHandler, path: str, out: list[Atom]) -> None:
    if isinstance(node, ast.Compare) and _compares_none(node):
        out.append(_fact("compare_a_none", _position(path, node.lineno)))
    if isinstance(node, ast.ExceptHandler) and _swallowed(node):
        out.append(_fact("except_vide", _position(path, node.lineno)))


def _record_import(node: ast.Import, module: str, path: str, out: list[Atom]) -> None:
    position = _position(path, node.lineno)
    for alias in node.names:
        bound = alias.asname or alias.name.split(".")[0]
        out.append(_fact("imports", module, alias.name))
        out.append(_fact("importe_sous", module, bound, alias.name, position))


def _record_import_from(node: ast.ImportFrom, module: str, path: str, out: list[Atom]) -> None:
    prefix = "." * node.level + (node.module or "")
    separator = "." if node.module else ""
    position = _position(path, node.lineno)
    for alias in node.names:
        target = f"{prefix}{separator}{alias.name}"
        out.append(_fact("imports", module, target))
        out.append(_fact("importe_sous", module, alias.asname or alias.name, target, position))


def _record_call(node: ast.Call, scope: str, path: str, out: list[Atom]) -> None:
    position = _position(path, node.lineno)
    callee = _callee(node.func)
    if callee is not None:
        out.append(_fact("calls", scope, callee))
    if isinstance(node.func, ast.Name):
        out.append(_fact("appel_simple", scope, node.func.id, position))


def _compares_none(node: ast.Compare) -> bool:
    exchanged = any(isinstance(op, (ast.Eq, ast.NotEq)) for op in node.ops)
    return exchanged and any(
        isinstance(value, ast.Constant) and value.value is None for value in node.comparators
    )


def _cyclomatic(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """``1 + decision points`` in a function, nested definitions excluded."""
    score = 1
    pending: list[ast.AST] = list(node.body)
    while pending:
        child = pending.pop()
        if isinstance(child, (*_FUNCTIONS, ast.ClassDef, ast.Lambda)):
            continue
        if isinstance(
            child,
            (
                ast.If,
                ast.For,
                ast.AsyncFor,
                ast.While,
                ast.IfExp,
                ast.ExceptHandler,
                ast.With,
                ast.AsyncWith,
                ast.Assert,
            ),
        ):
            score += 1
        elif isinstance(child, ast.BoolOp):
            score += len(child.values) - 1
        elif isinstance(child, ast.comprehension):
            score += len(child.ifs)
        pending.extend(ast.iter_child_nodes(child))
    return score


def _returns(node: ast.FunctionDef | ast.AsyncFunctionDef, path: str, name: str) -> tuple[str, ...]:
    """Positions of the ``return`` statements of one function, nested scopes excluded."""
    found: list[str] = []
    pending: list[ast.AST] = list(node.body)
    while pending:
        child = pending.pop()
        if isinstance(child, (*_FUNCTIONS, ast.ClassDef, ast.Lambda)):
            continue
        if isinstance(child, ast.Return):
            found.append(_position(path, child.lineno))
        pending.extend(ast.iter_child_nodes(child))
    return tuple(found)


def _swallowed(node: ast.ExceptHandler) -> bool:
    """Bare ``except: pass`` or ``except: ...``: nothing is done with the error.

    A typed handler with a deliberate fallback is not a swallowed exception.
    """
    if node.type is not None:
        return False
    for statement in node.body:
        if isinstance(statement, ast.Pass):
            continue
        if (
            isinstance(statement, ast.Expr)
            and isinstance(statement.value, ast.Constant)
            and statement.value.value is Ellipsis
        ):
            continue
        return False
    return bool(node.body)


def _arguments(args: ast.arguments) -> tuple[ast.arg, ...]:
    """Every declared argument, ``*args``/``**kwargs`` included."""
    extras = tuple(extra for extra in (args.vararg, args.kwarg) if extra is not None)
    return (*args.posonlyargs, *args.args, *args.kwonlyargs, *extras)


def _parameters(args: ast.arguments) -> tuple[str, ...]:
    """Parameter names in source order, ``*args``/``**kwargs`` excluded."""
    return tuple(argument.arg for argument in (*args.posonlyargs, *args.args, *args.kwonlyargs))


def _callee(func: ast.expr) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _assigned_names(node: ast.Assign | ast.AnnAssign) -> tuple[str, ...]:
    targets: tuple[ast.expr, ...] = (
        tuple(node.targets) if isinstance(node, ast.Assign) else (node.target,)
    )
    names: list[str] = []
    for target in targets:
        names.extend(_names_in(target))
    return tuple(names)


def _names_in(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, (ast.Tuple, ast.List)):
        names: list[str] = []
        for element in node.elts:
            names.extend(_names_in(element))
        return names
    if isinstance(node, ast.Starred):
        return _names_in(node.value)
    return []


def _position(path: str, line: int) -> str:
    return str(Position(path, line))


def _fact(predicate: str, *arguments: str | int) -> Atom:
    return Atom(predicate, tuple(arguments))
