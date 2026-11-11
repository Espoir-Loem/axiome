"""Calculator: exact arithmetic on rational numbers.

The expression is parsed with :mod:`ast` and only numbers, the four operations,
``%``, ``^`` (power) and parentheses are accepted: nothing is ever executed.
Results are exact fractions, so ``10 / 4`` is ``5/2`` and never ``2.4999…``.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Callable
from fractions import Fraction

MAX_EXPONENT = 10_000  # bigger powers are refused rather than computed for minutes
MAX_DIGITS = 4_000  # bigger results are refused
APPROX_DIGITS = 6
_DECIMAL_COMMA = re.compile(r"(\d),(\d)")

_BINARY: dict[type[ast.operator], Callable[[Fraction, Fraction], Fraction]] = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.Mod: lambda a, b: a % b,
}


class CalculationError(ValueError):
    """The expression cannot be read or its value is undefined."""


class DivisionByZeroError(CalculationError):
    pass


def _power(base: Fraction, exponent: Fraction) -> Fraction:
    if exponent.denominator != 1 or abs(exponent) > MAX_EXPONENT:
        raise CalculationError("unsupported exponent")
    if base == 0 and exponent < 0:
        raise DivisionByZeroError("zero to a negative power")
    size = max(len(str(base.numerator)), len(str(base.denominator)))
    if size * abs(int(exponent)) > MAX_DIGITS * 2:  # refuse before computing, not after
        raise CalculationError("result too large")
    return base ** int(exponent)


def _evaluate(node: ast.AST) -> Fraction:
    if isinstance(node, ast.Expression):
        return _evaluate(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
        return Fraction(str(node.value))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub | ast.UAdd):
        value = _evaluate(node.operand)
        return -value if isinstance(node.op, ast.USub) else value
    if isinstance(node, ast.BinOp):
        left, right = _evaluate(node.left), _evaluate(node.right)
        if isinstance(node.op, ast.Pow):
            result = _power(left, right)
        elif type(node.op) in _BINARY:
            if isinstance(node.op, ast.Div | ast.Mod) and right == 0:
                raise DivisionByZeroError("division by zero")
            result = _BINARY[type(node.op)](left, right)
        else:
            raise CalculationError("unsupported operator")
        if len(str(result.numerator)) + len(str(result.denominator)) > MAX_DIGITS:
            raise CalculationError("result too large")
        return result
    raise CalculationError("unsupported expression")


def calculate(expression: str) -> Fraction:
    """Exact value of ``expression`` ("2^10", "(3 + 5) * 2", "2,5 * 4")."""
    source = _DECIMAL_COMMA.sub(r"\1.\2", expression).replace("^", "**")
    try:
        tree = ast.parse(source, mode="eval")
    except SyntaxError as exc:
        raise CalculationError("syntax") from exc
    return _evaluate(tree)


def decimal(value: Fraction, comma: bool, digits: int = APPROX_DIGITS) -> str:
    """Rounded decimal writing, with the language's decimal separator."""
    scaled = round(abs(value) * 10**digits)  # integer arithmetic: no float overflow
    whole, frac = divmod(scaled, 10**digits)
    text = f"{whole}.{frac:0{digits}d}".rstrip("0").rstrip(".")
    if value < 0 and text != "0":
        text = "-" + text
    return text.replace(".", ",") if comma else text


def exact(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value}"
