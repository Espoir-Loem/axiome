"""Wikidata: learning concepts, their classes and their names from an open knowledge graph.

Wikidata is data (CC0), not a model: using it is compatible with ADR-0006. Only
the official API is called (``wbsearchentities``, ``wbgetentities``), through the
cached fetcher, so a replayed import is byte-identical.

What is learned for a concept, and for its classes up to ``depth`` levels:

* ``is_a(child, parent)`` from "instance of" (P31) and "subclass of" (P279);
* its names in each language, with the grammatical gender of French nouns taken
  from Wikidata Lexemes (P5185), so that "une étoile" is never "un étoile";
* the short description, as a definition, when nothing defines the concept yet.

Every fact keeps Wikidata as its source; one reference alone makes a fact
PLAUSIBLE, not CONFIRMED, and the answers say so.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from itertools import pairwise
from typing import Any

from axiome.kernel import Kernel
from axiome.perception.normalize import fold, slug
from axiome.reasoning.terms import Atom, Literal, Var
from axiome.research.fetch import Fetcher, build_url
from axiome.research.providers.base import load_json
from axiome.verification.epistemic import Reliability, Source, SourceKind

API = "https://www.wikidata.org/w/api.php"
PAGE = "https://www.wikidata.org/wiki/"
INSTANCE_OF, SUBCLASS_OF, GRAMMATICAL_GENDER = "P31", "P279", "P5185"
GENDERS = {"Q1775415": "f", "Q499327": "m"}
HUMAN = "Q5"  # people are named without article ("Marie Curie", not "la Marie Curie")
TAXON = "Q16521"  # living things are placed by "parent taxon" (P171), not "subclass of"
PARENT_TAXON = "P171"
FEMININE_ENDINGS = (  # used only when Wikidata Lexemes has no gender for the noun
    "tion",
    "sion",
    "té",
    "ure",
    "ette",
    "ence",
    "ance",
    "ine",
    "elle",
    "esse",
    "ade",
    "ie",
    "ée",
    "ière",
    "euse",
    "ise",
    "ode",
    "ude",
)
DISAMBIGUATION = "Q4167410"  # "Wikimedia disambiguation page": never a concept
BATCH = 50  # API limit for wbgetentities
MAX_PARENTS = 3  # classes kept per entity (Wikidata lists many, the first are the main ones)
SEARCH_LIMIT = 7
MAX_LINEAGE = 20  # class levels climbed to link two concepts
MAX_FRONTIER = 6  # branches followed per level while climbing
POLITE_INTERVAL_S = 0.5  # one request at a time, spaced: Wikimedia's API etiquette
META_QID = "wikidata:"  # meta key: wikidata:Q123 -> concept
META_CONCEPT = "wikidata_concept:"  # meta key: wikidata_concept:<concept> -> Q123
META_GENDER = "gender:fr:"  # meta key: gender:fr:<noun> -> m | f | ?
UNKNOWN_GENDER = "?"


@dataclass(frozen=True, slots=True)
class Entity:
    qid: str
    labels: Mapping[str, str]
    descriptions: Mapping[str, str]
    parents: tuple[str, ...]  # classes (P31 then P279), main ones first
    instance_of: tuple[str, ...] = ()

    def label(self, languages: Sequence[str]) -> str:
        return next((self.labels[lang] for lang in languages if lang in self.labels), "")


def _claim_ids(claims: Mapping[str, Any], prop: str) -> list[str]:
    """Item ids of a property, preferred rank first, deprecated statements dropped."""
    statements = [s for s in claims.get(prop, []) if s.get("rank") != "deprecated"]
    statements.sort(key=lambda s: s.get("rank") != "preferred")
    out: list[str] = []
    for s in statements:
        value = s.get("mainsnak", {}).get("datavalue", {}).get("value", {})
        if isinstance(value, dict) and isinstance(value.get("id"), str):
            out.append(value["id"])
    return out


class Wikidata:
    def __init__(
        self,
        fetcher: Fetcher,
        languages: Sequence[str] = ("fr", "en"),
        *,
        interval_s: float = POLITE_INTERVAL_S,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.fetcher = fetcher
        self.languages = tuple(languages)
        self.interval_s = interval_s
        self._clock, self._sleep = clock, sleep
        self._last = float("-inf")

    def _get(self, params: Mapping[str, str | int]) -> Any:
        wait = self._last + self.interval_s - self._clock()
        if wait > 0:
            self._sleep(wait)
        self._last = self._clock()
        return load_json(self.fetcher, build_url(API, {**params, "format": "json"}))

    def find(self, text: str, language: str) -> str | None:
        """The item whose name is exactly ``text`` (first by Wikidata's own ranking)."""
        data = self._get(
            {
                "action": "wbsearchentities",
                "search": text,
                "language": language,
                "uselang": language,
                "type": "item",
                "limit": SEARCH_LIMIT,
            }
        )
        wanted = fold(text).strip()
        hits = [
            (str(hit["id"]), str(hit.get("match", {}).get("text", "")))
            for hit in data.get("search", [])
        ]
        # Same letters first; same case first among them ("baleine" the animal, not the
        # constellation "Baleine"), Wikidata's own ranking otherwise.
        exact = [
            qid
            for qid, name in sorted(hits, key=lambda h: h[1].strip() != text.strip())
            if fold(name).strip() == wanted
        ]
        if not exact:
            return None
        found = self.entities(exact)
        return next(
            (q for q in exact if q in found and DISAMBIGUATION not in found[q].instance_of), None
        )

    def entities(self, qids: Iterable[str]) -> dict[str, Entity]:
        ids = sorted(set(qids))
        out: dict[str, Entity] = {}
        for start in range(0, len(ids), BATCH):
            data = self._get(
                {
                    "action": "wbgetentities",
                    "ids": "|".join(ids[start : start + BATCH]),
                    "props": "labels|descriptions|claims",
                    "languages": "|".join(self.languages),
                }
            )
            for qid, raw in data.get("entities", {}).items():
                if "missing" in raw:
                    continue
                claims = raw.get("claims", {})
                instance_of = _claim_ids(claims, INSTANCE_OF)
                # A class is placed by "subclass of"; its "instance of" values are
                # metaclasses ("type of astronomical object") and say nothing of its members.
                parents = _claim_ids(claims, SUBCLASS_OF) or instance_of
                if TAXON in instance_of:
                    parents = _claim_ids(claims, PARENT_TAXON) or parents
                out[qid] = Entity(
                    qid,
                    {k: v["value"] for k, v in raw.get("labels", {}).items()},
                    {k: v["value"] for k, v in raw.get("descriptions", {}).items()},
                    tuple(p for p in parents if p != qid),
                    tuple(instance_of),
                )
        return out

    def genders(self, nouns: Iterable[str], language: str) -> dict[str, str | None]:
        """Grammatical gender of nouns from Wikidata Lexemes ("étoile" -> "f").

        One search per noun, then a single batched fetch of all candidate lexemes.
        """
        wanted = sorted(set(nouns))
        candidates: dict[str, list[str]] = {}
        for noun in wanted:
            hits = self._get(
                {
                    "action": "wbsearchentities",
                    "search": noun,
                    "language": language,
                    "uselang": "en",  # descriptions read "French, noun"
                    "type": "lexeme",
                    "limit": SEARCH_LIMIT,
                }
            ).get("search", [])
            candidates[noun] = [  # this language, this spelling, a noun: usually one lexeme
                str(h["id"])
                for h in hits
                if h.get("match", {}).get("language") == language
                and fold(str(h.get("match", {}).get("text", ""))) == fold(noun)
                and "noun" in str(h.get("description", "")).lower()
            ][:1]
        ids = sorted({lid for found in candidates.values() for lid in found})
        lexemes: dict[str, Any] = {}
        for start in range(0, len(ids), BATCH):
            chunk = "|".join(ids[start : start + BATCH])
            data = self._get({"action": "wbgetentities", "ids": chunk, "props": "claims"})
            lexemes.update(data.get("entities", {}))
        return {noun: _gender(candidates[noun], lexemes) for noun in wanted}


def _gender(ids: Sequence[str], lexemes: Mapping[str, Any]) -> str | None:
    for lid in ids:
        lexeme = lexemes.get(lid, {})
        claims = lexeme.get("claims", {})
        found = [GENDERS[g] for g in _claim_ids(claims, GRAMMATICAL_GENDER) if g in GENDERS]
        if found:
            return found[0]
    return None


def _guess_gender(noun: str) -> str:
    """Last resort for French nouns missing from Wikidata Lexemes: common endings."""
    return "f" if fold(noun).endswith(tuple(fold(e) for e in FEMININE_ENDINGS)) else "m"


def _translated(entity: Entity, languages: Sequence[str]) -> bool:
    """Named in every language, and not with a copied untranslated phrase."""
    labels = [entity.labels.get(lang, "") for lang in languages]
    if not all(labels):
        return False
    copied = len({fold(x) for x in labels}) == 1 and " " in labels[0]
    return not copied


@dataclass
class Imported:
    """What one import added (counts are of new rows only)."""

    concept: str | None = None
    concepts: list[str] = field(default_factory=list)
    facts: int = 0
    words: int = 0


def source_for(qid: str) -> Source:
    return Source(
        id=f"wikidata:{qid}",
        name="Wikidata",
        kind=SourceKind.REFERENCE,
        reliability=Reliability.HIGH,
        organization="wikidata.org",
        url=f"{PAGE}{qid}",
    )


class Librarian:
    """Turns Wikidata entities into facts of the knowledge base and words of the lexicons."""

    def __init__(self, kernel: Kernel, wikidata: Wikidata, depth: int = 2) -> None:
        self.kernel = kernel
        self.wikidata = wikidata
        self.depth = depth

    # -- naming ------------------------------------------------------------------
    def concept_for(self, entity: Entity) -> str | None:
        """Stable concept name: the one already used for this item, else the English slug."""
        store = self.kernel.store
        known = store.get_meta(META_QID + entity.qid)
        if known:
            return known
        base = slug(entity.label(("en", *self.wikidata.languages)))
        if not base:
            return None
        owner = store.get_meta(META_CONCEPT + base)
        name = base if owner in (None, "", entity.qid) else f"{base}_{entity.qid.lower()}"
        store.set_meta(META_QID + entity.qid, name)
        store.set_meta(META_CONCEPT + name, entity.qid)
        return name

    # -- import ------------------------------------------------------------------
    def learn(self, text: str, language: str, depth: int | None = None) -> Imported:
        """Find ``text`` on Wikidata and learn it with its classes. Empty result if unknown."""
        qid = self.wikidata.find(text, language)
        if qid is None:
            return Imported()
        return self.learn_item(qid, language, depth)

    def learn_item(self, root: str, language: str, depth: int | None = None) -> Imported:
        result = Imported()
        entities: dict[str, Entity] = {}
        level = [root]
        for _ in range((self.depth if depth is None else depth) + 1):
            fresh = self.wikidata.entities(q for q in level if q not in entities)
            entities.update(fresh)
            level = [p for q in level if q in entities for p in entities[q].parents[:MAX_PARENTS]]
            level = [p for p in dict.fromkeys(level) if p not in entities]
            if not level:
                break
        languages = self.wikidata.languages
        names = {
            q: c
            for q, e in entities.items()
            if (q == root or _translated(e, languages))  # no mixed languages
            and (c := self.concept_for(e)) is not None
        }
        genders = self._genders([entities[q] for q in names])
        result.concept = names.get(root)
        for qid in sorted(names, key=lambda q: (q != root, q)):
            result.concepts.append(names[qid])
            result.words += self._words(entities[qid], names[qid], genders)
        result.facts += self._classes(root, entities, names)
        result.facts += self._definition(entities.get(root), names.get(root), language)
        return result

    def qid(self, concept: str, text: str, language: str) -> str | None:
        """The Wikidata item of a concept: recorded at import, else searched by name."""
        known = self.kernel.store.get_meta(META_CONCEPT + concept)
        if known:
            return known
        found = self.wikidata.find(text, language)
        if found is not None:
            entity = self.wikidata.entities([found]).get(found)
            if entity is not None and self.concept_for(entity) == concept:
                return found
        return None

    def connect(
        self, child: str, goal: str, language: str, max_depth: int = MAX_LINEAGE
    ) -> Imported:
        """Climb the classes of ``child`` until ``goal`` (both Wikidata ids); learn that path.

        Used for yes/no questions across long lineages ("is a lion a mammal?" is about
        ten ranks of the classification of living things). Wikidata often has two items
        for one idea (the taxon "Mammalia" and the class of organisms "mammal"): an item
        with the same English name as the goal counts as the goal.
        """
        target = self.wikidata.entities([goal]).get(goal)
        if target is None:
            return Imported()
        found = self._climb(child, target, max_depth)
        result = Imported()
        if found is None:
            return result
        path, entities = found
        goal_concept = self.concept_for(target)
        if goal_concept is None:
            return result
        if path[-1] != goal:  # the same idea under another item: file it under the goal
            self.kernel.store.set_meta(META_QID + path[-1], goal_concept)
        names = {q: c for q in path if (c := self.concept_for(entities[q])) is not None}
        if len(names) != len(path):
            return result
        genders = self._genders([entities[q] for q in path])
        for qid in path:
            result.concepts.append(names[qid])
            result.words += self._words(entities[qid], names[qid], genders)
        for a, b in pairwise(path):
            result.facts += self.kernel.record(Atom("is_a", (names[a], names[b])), source_for(a))
        result.concept = names[child]
        return result

    def _climb(
        self, child: str, target: Entity, max_depth: int
    ) -> tuple[list[str], dict[str, Entity]] | None:
        """Breadth-first walk up the classes; the path to the target, with the entities met."""
        same_name = fold(target.labels.get("en", target.qid))
        paths: dict[str, list[str]] = {child: [child]}
        entities: dict[str, Entity] = {target.qid: target}
        frontier = [child]
        for _ in range(max_depth + 1):
            entities.update(self.wikidata.entities(q for q in frontier if q not in entities))
            for qid in frontier:
                entity = entities.get(qid)
                if (
                    qid != child
                    and entity is not None
                    and (qid == target.qid or fold(entity.labels.get("en", "")) == same_name)
                ):
                    return paths[qid], entities
            nxt: list[str] = []
            for qid in frontier:
                for parent in entities[qid].parents[:MAX_PARENTS] if qid in entities else ():
                    if parent not in paths:
                        paths[parent] = [*paths[qid], parent]
                        nxt.append(parent)
            if not nxt:
                return None
            frontier = nxt[:MAX_FRONTIER]
        return None

    def _classes(self, root: str, entities: Mapping[str, Entity], names: Mapping[str, str]) -> int:
        """is_a edges, breadth first from the root, skipping any edge that would close a cycle."""
        added = 0
        up: dict[str, set[str]] = {}

        def reaches(start: str, goal: str) -> bool:
            seen, todo = set(), [start]
            while todo:
                node = todo.pop()
                if node == goal:
                    return True
                if node not in seen:
                    seen.add(node)
                    todo.extend(up.get(node, ()))
            return False

        order, seen = [root], {root}
        for qid in order:
            entity = entities.get(qid)
            if entity is None or qid not in names:
                continue
            for parent in entity.parents[:MAX_PARENTS]:
                if parent not in names or reaches(parent, qid):
                    continue
                up.setdefault(qid, set()).add(parent)
                atom = Atom("is_a", (names[qid], names[parent]))
                added += self.kernel.record(atom, source_for(qid))
                if parent not in seen:
                    seen.add(parent)
                    order.append(parent)
        return added

    def _definition(self, entity: Entity | None, concept: str | None, language: str) -> int:
        if entity is None or concept is None or language not in entity.descriptions:
            return 0
        known = Literal(Atom("defined_as", (concept, Var("X"))))
        if self.kernel.state.model.query((known,)):
            return 0  # a fuller definition (from a page) is already known
        label = entity.labels.get(language, concept.replace("_", " "))
        text = f"{label[:1].upper()}{label[1:]} : {entity.descriptions[language]}."
        if language != "fr":
            text = text.replace(" : ", ": ")
        return int(self.kernel.record(Atom("defined_as", (concept, text)), source_for(entity.qid)))

    def _genders(self, entities: Sequence[Entity]) -> dict[str, str]:
        """Gender of the head noun of every French common-noun label, cached in the base."""
        store = self.kernel.store
        heads = {
            fold(e.labels["fr"].split(" ")[0])
            for e in entities
            if "fr" in e.labels and HUMAN not in e.instance_of
        }
        out = {h: store.get_meta(META_GENDER + fold(h)) or "" for h in heads}
        missing = sorted(h for h, g in out.items() if not g)
        if missing:
            for head, gender in self.wikidata.genders(missing, "fr").items():
                out[head] = gender or _guess_gender(head)
                store.set_meta(META_GENDER + fold(head), out[head])
        return out

    def _words(self, entity: Entity, concept: str, genders: Mapping[str, str]) -> int:
        added = 0
        source = source_for(entity.qid)
        self.kernel.store.add_source(source)
        for language, label in sorted(entity.labels.items()):
            if language not in self.wikidata.languages:
                continue
            proper = HUMAN in entity.instance_of
            gender = "m"
            if language == "fr" and not proper:
                found = genders.get(fold(label.split(" ")[0]), UNKNOWN_GENDER)
                gender = "m" if found == UNKNOWN_GENDER else found
            added += self.kernel.store.add_word(
                language,
                label,
                concept,
                source.id,
                self.kernel.clock.now(),
                gender=gender,
                proper=proper,
            )
        return added
