"""Axiome error hierarchy.

Every expected error derives from :class:`AxiomeError` so that interfaces can
display it cleanly without hiding genuine bugs (which are not ``AxiomeError``).
Errors carry a translation key and parameters; the text is rendered lazily in
the active locale (see :mod:`axiome.i18n`).
"""

from __future__ import annotations

from axiome.i18n import Msg, msg, t


class AxiomeError(Exception):
    """Root of all expected errors."""

    def __init__(self, key: str, **params: object) -> None:
        super().__init__(key)
        self.message: Msg = msg(key, **params)

    def __str__(self) -> str:
        return str(self.message)


class ParseError(AxiomeError):
    """Malformed logic text, with its location."""

    def __init__(self, key: str, line: int, column: int, **params: object) -> None:
        super().__init__(key, **params)
        self.line = line
        self.column = column

    def __str__(self) -> str:
        return t("error.location", line=self.line, column=self.column, message=self.message)


class ProgramError(AxiomeError):
    """Invalid logic program (unsafe rule, non-stratifiable negation, ...)."""


class StorageError(AxiomeError):
    """Knowledge base persistence failure."""


class KnowledgeError(AxiomeError):
    """Inconsistent knowledge operation (unknown source, non-ground fact, ...)."""
