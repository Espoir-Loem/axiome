"""Hiérarchie d'erreurs d'Axiome.

Toutes les erreurs prévues héritent de :class:`AxiomeError` afin que l'interface
puisse les afficher proprement sans masquer les vrais bogues (qui, eux, ne sont
pas des ``AxiomeError``).
"""

from __future__ import annotations


class AxiomeError(Exception):
    """Racine de toutes les erreurs attendues."""


class ParseError(AxiomeError):
    """Texte logique mal formé."""

    def __init__(self, message: str, line: int, column: int) -> None:
        super().__init__(f"ligne {line}, colonne {column} : {message}")
        self.line = line
        self.column = column


class ProgramError(AxiomeError):
    """Programme logique invalide (règle non sûre, négation non stratifiable…)."""


class StorageError(AxiomeError):
    """Problème de persistance de la base de connaissances."""


class KnowledgeError(AxiomeError):
    """Opération incohérente sur la connaissance (source inconnue, fait non clos…)."""
