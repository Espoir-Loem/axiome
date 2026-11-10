"""Persistance SQLite de la connaissance : faits, preuves, sources, règles.

Le stockage est volontairement « bête » : il ne raisonne pas. Toute lecture est
triée explicitement (jamais d'ordre implicite SQLite) pour rester déterministe.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from axiome.core.config import IN_MEMORY
from axiome.core.errors import KnowledgeError, StorageError
from axiome.reasoning.syntax import parse_atom
from axiome.reasoning.terms import Atom
from axiome.verification.epistemic import Evidence, Reliability, Source, SourceKind, Stance

SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    reliability TEXT NOT NULL,
    organization TEXT NOT NULL,
    url TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS facts (id INTEGER PRIMARY KEY, text TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS evidence (
    fact_id INTEGER NOT NULL REFERENCES facts(id),
    source_id TEXT NOT NULL REFERENCES sources(id),
    stance TEXT NOT NULL,
    excerpt TEXT NOT NULL DEFAULT '',
    recorded_at TEXT NOT NULL,
    PRIMARY KEY (fact_id, source_id, stance)
);
CREATE TABLE IF NOT EXISTS rules (
    id INTEGER PRIMARY KEY,
    text TEXT NOT NULL UNIQUE,
    axiomatic INTEGER NOT NULL
);
"""


@dataclass(frozen=True, slots=True)
class StoredRule:
    text: str
    axiomatic: bool


class KnowledgeStore:
    def __init__(self, path: str = IN_MEMORY) -> None:
        if path != IN_MEMORY:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        try:
            self._db = sqlite3.connect(path)
        except sqlite3.Error as exc:  # pragma: no cover - dépend de l'OS
            raise StorageError(f"impossible d'ouvrir la base {path} : {exc}") from exc
        self._db.execute("PRAGMA foreign_keys = ON")
        version = self._db.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0, SCHEMA_VERSION):
            raise StorageError(f"schéma v{version} non pris en charge (attendu v{SCHEMA_VERSION})")
        with self._tx() as db:
            db.executescript(_SCHEMA)
            db.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    def close(self) -> None:
        self._db.close()

    @contextmanager
    def _tx(self) -> Iterator[sqlite3.Connection]:
        try:
            with self._db:
                yield self._db
        except sqlite3.Error as exc:
            raise StorageError(str(exc)) from exc

    # -- méta ----------------------------------------------------------------
    def get_meta(self, key: str) -> str | None:
        row = self._db.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return None if row is None else str(row[0])

    def set_meta(self, key: str, value: str) -> None:
        with self._tx() as db:
            db.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (key, value))

    # -- sources -------------------------------------------------------------
    def add_source(self, s: Source) -> None:
        with self._tx() as db:
            db.execute(
                "INSERT OR REPLACE INTO sources VALUES (?, ?, ?, ?, ?, ?)",
                (s.id, s.name, s.kind.value, s.reliability.name, s.organization, s.url),
            )

    def source(self, source_id: str) -> Source:
        row = self._db.execute(
            "SELECT id, name, kind, reliability, organization, url FROM sources WHERE id = ?",
            (source_id,),
        ).fetchone()
        if row is None:
            raise KnowledgeError(f"source inconnue : {source_id}")
        return _row_to_source(row)

    def sources(self) -> list[Source]:
        rows = self._db.execute(
            "SELECT id, name, kind, reliability, organization, url FROM sources ORDER BY id"
        ).fetchall()
        return [_row_to_source(r) for r in rows]

    # -- faits et preuves ----------------------------------------------------
    def add_evidence(
        self, atom: Atom, source_id: str, stance: Stance, recorded_at: str, excerpt: str = ""
    ) -> bool:
        """Enregistre une preuve. Renvoie False si elle existait déjà (idempotent)."""
        if not atom.is_ground():
            raise KnowledgeError(f"un fait doit être clos : {atom}")
        self.source(source_id)  # valide l'existence
        text = str(atom)
        with self._tx() as db:
            db.execute("INSERT OR IGNORE INTO facts (text) VALUES (?)", (text,))
            fact_id = db.execute("SELECT id FROM facts WHERE text = ?", (text,)).fetchone()[0]
            cur = db.execute(
                "INSERT OR IGNORE INTO evidence VALUES (?, ?, ?, ?, ?)",
                (fact_id, source_id, stance.value, excerpt, recorded_at),
            )
            return cur.rowcount == 1

    def evidence(self) -> dict[Atom, list[Evidence]]:
        sources = {s.id: s for s in self.sources()}
        rows = self._db.execute(
            "SELECT f.text, e.source_id, e.stance, e.excerpt FROM evidence e "
            "JOIN facts f ON f.id = e.fact_id ORDER BY f.text, e.source_id, e.stance"
        ).fetchall()
        out: dict[Atom, list[Evidence]] = {}
        for text, source_id, stance, excerpt in rows:
            out.setdefault(parse_atom(text), []).append(
                Evidence(sources[source_id], Stance(stance), excerpt)
            )
        return out

    # -- règles --------------------------------------------------------------
    def add_rule(self, text: str, axiomatic: bool) -> bool:
        with self._tx() as db:
            cur = db.execute(
                "INSERT OR IGNORE INTO rules (text, axiomatic) VALUES (?, ?)",
                (text, int(axiomatic)),
            )
            return cur.rowcount == 1

    def replace_axiomatic_rules(self, text: str) -> None:
        """Remplace le programme de référence (les règles hypothétiques sont conservées)."""
        with self._tx() as db:
            db.execute("DELETE FROM rules WHERE axiomatic = 1")
            db.execute("INSERT INTO rules (text, axiomatic) VALUES (?, 1)", (text,))

    def rules(self) -> list[StoredRule]:
        rows = self._db.execute(
            "SELECT text, axiomatic FROM rules ORDER BY axiomatic DESC, id"
        ).fetchall()
        return [StoredRule(str(t), bool(a)) for t, a in rows]


def _row_to_source(row: tuple[str, str, str, str, str, str]) -> Source:
    sid, name, kind, rel, org, url = row
    return Source(sid, name, SourceKind(kind), Reliability[rel], org, url)
