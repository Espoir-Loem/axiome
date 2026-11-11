"""SQLite persistence for knowledge: facts, evidence, sources, rules.

Storage is deliberately "dumb": it never reasons. Every read is explicitly
sorted (never relying on SQLite's implicit order) to stay deterministic.
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

SCHEMA_VERSION = 3  # v2: learned lexicon; v3: gender and proper-name flag of learned words

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
CREATE TABLE IF NOT EXISTS lexicon (
    language TEXT NOT NULL,
    form TEXT NOT NULL,
    concept TEXT NOT NULL,
    source_id TEXT NOT NULL REFERENCES sources(id),
    recorded_at TEXT NOT NULL,
    gender TEXT NOT NULL DEFAULT 'm',
    proper INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (language, form, concept)
);
"""
_MIGRATE_V2 = (
    "ALTER TABLE lexicon ADD COLUMN gender TEXT NOT NULL DEFAULT 'm'",
    "ALTER TABLE lexicon ADD COLUMN proper INTEGER NOT NULL DEFAULT 0",
)


@dataclass(frozen=True, slots=True)
class LearnedWord:
    form: str
    concept: str
    gender: str = "m"
    proper: bool = False


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
        except sqlite3.Error as exc:  # pragma: no cover - OS dependent
            raise StorageError("storage.open_failed", path=path, detail=exc) from exc
        self._db.execute("PRAGMA foreign_keys = ON")
        version = self._db.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0, 1, 2, SCHEMA_VERSION):
            raise StorageError("storage.unsupported_schema", found=version, expected=SCHEMA_VERSION)
        with self._tx() as db:
            if version == 2:
                for statement in _MIGRATE_V2:
                    db.execute(statement)
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
            raise StorageError("storage.sqlite", detail=exc) from exc

    # -- meta ----------------------------------------------------------------
    def get_meta(self, key: str) -> str | None:
        row = self._db.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return None if row is None else str(row[0])

    def set_meta(self, key: str, value: str) -> None:
        with self._tx() as db:
            db.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (key, value))

    def meta_items(self, prefix: str) -> list[tuple[str, str]]:
        rows = self._db.execute(
            "SELECT key, value FROM meta WHERE substr(key, 1, ?) = ? ORDER BY key",
            (len(prefix), prefix),
        ).fetchall()
        return [(str(k), str(v)) for k, v in rows]

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
            raise KnowledgeError("knowledge.unknown_source", source=source_id)
        return _row_to_source(row)

    def sources(self) -> list[Source]:
        rows = self._db.execute(
            "SELECT id, name, kind, reliability, organization, url FROM sources ORDER BY id"
        ).fetchall()
        return [_row_to_source(r) for r in rows]

    # -- facts and evidence ----------------------------------------------------
    def add_evidence(
        self, atom: Atom, source_id: str, stance: Stance, recorded_at: str, excerpt: str = ""
    ) -> bool:
        """Record evidence. Return False if it already existed (idempotent)."""
        if not atom.is_ground():
            raise KnowledgeError("knowledge.non_ground_fact", atom=atom)
        self.source(source_id)  # validates existence
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

    def evidence_for(self, atom: Atom) -> list[Evidence]:
        return self.evidence_for_text(str(atom))

    def evidence_for_text(self, text: str) -> list[Evidence]:
        sources = {s.id: s for s in self.sources()}
        rows = self._db.execute(
            "SELECT e.source_id, e.stance, e.excerpt FROM evidence e "
            "JOIN facts f ON f.id = e.fact_id WHERE f.text = ? ORDER BY e.source_id, e.stance",
            (text,),
        ).fetchall()
        return [Evidence(sources[sid], Stance(st), ex) for sid, st, ex in rows]

    # -- learned lexicon -------------------------------------------------------
    def add_word(
        self,
        language: str,
        form: str,
        concept: str,
        source_id: str,
        recorded_at: str,
        *,
        gender: str = "m",
        proper: bool = False,
    ) -> bool:
        self.source(source_id)
        with self._tx() as db:
            cur = db.execute(
                "INSERT OR IGNORE INTO lexicon VALUES (?, ?, ?, ?, ?, ?, ?)",
                (language, form, concept, source_id, recorded_at, gender, int(proper)),
            )
            return cur.rowcount == 1

    def words(self, language: str) -> list[LearnedWord]:
        """Learned words of a language, sorted by form."""
        rows = self._db.execute(
            "SELECT form, concept, gender, proper FROM lexicon WHERE language = ?"
            " ORDER BY form, concept",
            (language,),
        ).fetchall()
        return [LearnedWord(str(f), str(c), str(g), bool(p)) for f, c, g, p in rows]

    # -- rules ---------------------------------------------------------------
    def add_rule(self, text: str, axiomatic: bool) -> bool:
        with self._tx() as db:
            cur = db.execute(
                "INSERT OR IGNORE INTO rules (text, axiomatic) VALUES (?, ?)",
                (text, int(axiomatic)),
            )
            return cur.rowcount == 1

    def replace_axiomatic_rules(self, text: str) -> None:
        """Replace the reference program (hypothetical rules are kept)."""
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
