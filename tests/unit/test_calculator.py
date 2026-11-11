"""Calculator: exact results, no code execution, bounded work."""

from __future__ import annotations

from fractions import Fraction

import pytest

from axiome.team.calculator import (
    CalculationError,
    DivisionByZeroError,
    calculate,
    decimal,
    exact,
)


@pytest.mark.parametrize(
    ("expression", "value"),
    [
        ("2 + 2", Fraction(4)),
        ("(3 + 5) * 2 - 1", Fraction(15)),
        ("10 / 4", Fraction(5, 2)),
        ("2^10", Fraction(1024)),
        ("2 ^ -2", Fraction(1, 4)),
        ("15 % 4", Fraction(3)),
        ("-3 + +5", Fraction(2)),
        ("2,5 * 4", Fraction(10)),
        ("0.1 + 0.2", Fraction(3, 10)),  # exact, unlike floating point
    ],
)
def test_exact_values(expression: str, value: Fraction) -> None:
    assert calculate(expression) == value


@pytest.mark.parametrize("expression", ["1 / 0", "5 % 0", "0 ^ -1"])
def test_division_by_zero(expression: str) -> None:
    with pytest.raises(DivisionByZeroError):
        calculate(expression)


@pytest.mark.parametrize(
    "expression",
    [
        "2 +",  # syntax
        "__import__('os')",  # never executed
        "2 ** 0.5",  # non integer exponent
        "9 ^ 9 ^ 9",  # exponent too large
        "(10 ^ 3000) ^ 3000",  # result too large, refused before computing
        "7 // 2",  # operator outside the allowed set
        "'a' * 3",
    ],
)
def test_refused(expression: str) -> None:
    with pytest.raises(CalculationError):
        calculate(expression)


def test_writing() -> None:
    assert exact(Fraction(84)) == "84"
    assert exact(Fraction(5, 2)) == "5/2"
    assert decimal(Fraction(5, 2), comma=True) == "2,5"
    assert decimal(Fraction(1, 3), comma=False) == "0.333333"
    assert decimal(Fraction(-7, 4), comma=False) == "-1.75"
    assert decimal(Fraction(-1, 10**9), comma=False) == "0"
