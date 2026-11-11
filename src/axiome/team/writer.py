"""Writer: turns verified facts into sentences adapted to the reader's level.

Checklist: every factual sentence carries its support (facts or sources); a
status below CONFIRMED is announced, either in the sentence itself or by one
reliability note covering the whole answer; the content for a beginner is a
subset of the content for an expert, never a different truth.

An answer is shaped like a good human one: a lead that answers the question
(the summary), details as a list, then a reliability note and numbered sources.

What changes with the level:

========== ==================================================================
beginner   one idea per sentence, everyday words first, technical words are
           defined (gloss) at first use, few examples
intermediate  domain vocabulary, more properties and examples, measures
expert     everything verified: full classification, constraints, status note
========== ==================================================================
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace

from axiome.dialogue.level import Level
from axiome.i18n import t_in
from axiome.kernel import Kernel
from axiome.language.pack import LanguagePack
from axiome.perception.normalize import fold
from axiome.reasoning.terms import Atom
from axiome.research.providers.base import Document
from axiome.team.planner import Aspect
from axiome.team.researcher import WebFindings
from axiome.team.verifier import Fact, Findings, ancestry, disjointness
from axiome.verification.epistemic import Evidence, Source, Stance, Status, assess

LEXICON_SOURCE = "lexicon"

# Roles of a sentence in the answer layout.
LEAD = "lead"  # answers the question; together the leads are the summary
POINT = "point"  # a detail, shown as a list item
NOTE = "note"  # reliability / status note
SEE_ALSO = "see_also"
SOURCE = "source"  # a numbered reference
SOCIAL = "social"  # conversation, not knowledge
NOTE_KEY = {
    Status.CONFIRMED: "note_confirmed",
    Status.PLAUSIBLE: "note_plausible",
    Status.UNVERIFIED: "note_unverified",
    Status.CONTESTED: "note_contested",
}
DETAILS = (2, 4, 6)  # details taken from the main page per level
CORROBORATIONS = (0, 2, 4)  # details taken from other organizations per level

# (beginner, intermediate, expert) caps on how many items of a kind are given.
PROPERTY_CAP = (1, 3, 99)
MEMBER_CAP = (2, 4, 99)
EXPLICIT_MEMBER_CAP = (4, 8, 99)


@dataclass(frozen=True, slots=True)
class Claim:
    text: str
    status: Status | None = None
    support: tuple[str, ...] = ()
    factual: bool = True
    hedged: bool = False  # the sentence itself states its uncertainty / refutation
    role: str = LEAD
    covered: bool = False  # uncertainty stated by the answer's reliability note


def emphasize(text: str, phrase: str) -> str:
    """Bold the first occurrence of ``phrase`` (accent and case insensitive)."""
    if not phrase:
        return text
    i = fold(text).find(fold(phrase))
    if i < 0:
        return text
    return f"{text[:i]}**{text[i : i + len(phrase)]}**{text[i + len(phrase) :]}"


def _weakest(facts: Sequence[Fact]) -> Status:
    return min((f.status for f in facts), default=Status.PROVED)


def _arg(atom: Atom, i: int) -> str:
    return str(atom.args[i])


class Writer:
    def __init__(self, pack: LanguagePack, kernel: Kernel) -> None:
        self.pack = pack
        self.kernel = kernel

    # -- building blocks -------------------------------------------------------
    def label(self, status: Status) -> str:
        return t_in(self.pack.code, f"status.{status.name}")

    def reasons(self, assessment: object) -> str:
        found = getattr(assessment, "reasons", ())
        return "; ".join(r.render(self.pack.code) for r in found)

    def social(self, key: str, **slots: object) -> Claim:
        return Claim(self.pack.say(key, **slots), factual=False, role=SOCIAL)

    def np(self, concept: str) -> object:
        return self.pack.lexicon.phrase(concept)

    def hedge(self, text: str, status: Status, level: Level) -> tuple[str, bool]:
        if status >= Status.CONFIRMED:
            return text, False
        body = text.rstrip(".")
        if status is Status.PLAUSIBLE:
            return self.pack.say("hedge_plausible", claim=body) + ".", True
        if len(body) > 1 and body[1].islower():
            body = body[0].lower() + body[1:]
        key = "hedge_contested" if status is Status.CONTESTED else "hedge_unverified"
        return self.pack.say(key, claim=body) + ".", True

    def fact_claim(
        self, key: str, facts: Sequence[Fact], level: Level, role: str = POINT, **slots: object
    ) -> Claim:
        status = _weakest(facts)
        text, hedged = self.hedge(self.pack.say(key, **slots), status, level)
        return Claim(text, status, tuple(str(f.atom) for f in facts), hedged=hedged, role=role)

    def gloss(self, concept: str) -> Claim | None:
        lexeme = self.pack.lexicon.get(concept)
        if lexeme is None or not lexeme.gloss:
            return None
        text = self.pack.say("is_a_gloss", o=self.np(concept), gloss=lexeme.gloss)
        support = (f"{LEXICON_SOURCE}:{self.pack.code}:{concept}",)
        return Claim(text, Status.PROVED, support)

    def _needs_gloss(self, concept: str, level: Level) -> bool:
        lexeme = self.pack.lexicon.get(concept)
        if lexeme is None:
            return False
        return (level is Level.BEGINNER and lexeme.level >= 1) or (
            level is Level.INTERMEDIATE and lexeme.level >= 2
        )

    # -- sections --------------------------------------------------------------
    def categories(self, subject: str, findings: Findings, level: Level) -> list[Claim]:
        facts = findings.of(Aspect.CATEGORY)
        direct = [f for f in facts if f.base] or list(facts[:1])
        if level is Level.BEGINNER:
            direct = direct[:1]
        out: list[Claim] = []
        for fact in direct:
            parent = _arg(fact.atom, 1)
            out.append(
                self.fact_claim("is_a", [fact], level, LEAD, s=self.np(subject), o=self.np(parent))
            )
            if self._needs_gloss(parent, level) and (g := self.gloss(parent)) is not None:
                out.append(g)
        if level is Level.EXPERT:
            chain = ancestry(self.kernel, subject)
            if len(chain) > 2:
                lemmas = " ⊂ ".join(self.pack.lexicon.lexeme(c).lemma for c in chain)
                out.append(self.fact_claim("taxonomy", list(facts), level, chain=lemmas))
        return out

    def properties(self, subject: str, findings: Findings, level: Level, cap: int) -> list[Claim]:
        facts = sorted(findings.of(Aspect.PROPERTY), key=lambda f: (not f.base, str(f.atom)))
        return [
            self.fact_claim(
                "has_property", [f], level, POINT, s=self.np(subject), p=self.np(_arg(f.atom, 1))
            )
            for f in facts[:cap]
        ]

    def members(self, subject: str, findings: Findings, level: Level, cap: int) -> list[Claim]:
        facts = findings.of(Aspect.MEMBERS)
        chosen = [f for f in facts if f.base] or list(facts)
        chosen = chosen[:cap]
        if not chosen:
            return []
        items = self.pack.join([format(self.np(_arg(f.atom, 0)), "def") for f in chosen])
        return [self.fact_claim("members", chosen, level, c=self.np(subject), items=items)]

    def measures(self, subject: str, findings: Findings, level: Level) -> list[Claim]:
        out = [
            self.fact_claim("si_unit", [f], level, q=self.np(subject), u=self.np(_arg(f.atom, 1)))
            for f in findings.of(Aspect.UNIT)
        ]
        if level >= Level.INTERMEDIATE:
            out += [
                self.fact_claim("dimension", [f], level, q=self.np(subject), v=_arg(f.atom, 1))
                for f in findings.of(Aspect.DIMENSION)
            ]
        return out

    def complexity(self, subject: str, findings: Findings, level: Level) -> list[Claim]:
        out = [
            self.fact_claim(
                "worst_time_complexity", [f], level, s=self.np(subject), v=_arg(f.atom, 1)
            )
            for f in findings.of(Aspect.WORST_TIME)
        ]
        if level >= Level.INTERMEDIATE:
            out += [
                self.fact_claim(
                    "average_time_complexity", [f], level, s=self.np(subject), v=_arg(f.atom, 1)
                )
                for f in findings.of(Aspect.AVERAGE_TIME)
            ]
            out += [
                self.fact_claim(
                    "prerequisite", [f], level, s=self.np(subject), p=self.np(_arg(f.atom, 1))
                )
                for f in findings.of(Aspect.PREREQUISITE)
            ]
        return out

    def constraints(self, subject: str, findings: Findings, level: Level) -> list[Claim]:
        if level is not Level.EXPERT:
            return []
        return [
            self.fact_claim("disjoint", [f], level, a=self.np(subject), b=self.np(_arg(f.atom, 1)))
            for f in findings.of(Aspect.DISJOINT)
        ]

    def learned_definitions(self, findings: Findings, level: Level) -> list[Claim]:
        """Answer from what earlier web research taught (offline replay)."""
        leads = list(findings.of(Aspect.WEB_DEFINITION))
        if not leads:
            return []
        facts = leads[:1] + list(findings.of(Aspect.WEB_DETAIL))[: DETAILS[level]]
        refs: dict[str, tuple[int, Source]] = {}
        out: list[Claim] = []
        for i, fact in enumerate(facts):
            evidence = self.kernel.evidence(fact.atom)
            for e in evidence:
                refs.setdefault(e.source.id, (len(refs) + 1, e.source))
            marks = " ".join(f"[{refs[e.source.id][0]}]" for e in evidence)
            text = f"{_arg(fact.atom, 1)} {marks}".strip()
            role = LEAD if i == 0 else POINT
            support = tuple(sorted({e.source.id for e in evidence}))
            out.append(Claim(text, fact.status, support, role=role, covered=True))
        out += self.reliability(_weakest(facts))
        out += self.references([(src, "") for _, src in sorted(refs.values(), key=lambda r: r[0])])
        return out

    def reliability(self, status: Status) -> list[Claim]:
        key = NOTE_KEY.get(status)
        if key is None:
            return []
        return [Claim(self.pack.say(key), factual=False, role=NOTE)]

    def references(self, sources: Sequence[tuple[Source, str]]) -> list[Claim]:
        out: list[Claim] = []
        if sources:
            out.append(Claim(self.pack.say("sources_header"), factual=False, role=SOURCE))
        for n, (source, title) in enumerate(sources, start=1):
            key = "source_ref" if title else "source_ref_untitled"
            text = self.pack.say(key, n=n, name=source.name, title=title, url=source.url)
            out.append(Claim(text, factual=False, role=SOURCE))
        return out

    def web_answer(self, query: str, found: WebFindings) -> list[Claim]:
        """Lead (summary) + details + see also + reliability + numbered sources."""
        if found.lead is None or found.assessment is None:
            return []
        status = found.assessment.status
        numbers = {d: n for n, d in enumerate(found.cited, start=1)}
        docs: tuple[Document, ...] = found.documents
        out: list[Claim] = []
        for excerpt in (found.lead, *found.points):
            n = numbers[excerpt.doc]
            source = docs[excerpt.doc].source
            text = f"{excerpt.text} [{n}]"
            if excerpt is found.lead:
                text = emphasize(text, query)
                support = tuple(s.id for s in found.agreeing)
                out.append(Claim(text, status, support, role=LEAD, covered=True))
            else:
                alone = assess([Evidence(source, Stance.SUPPORTS, excerpt.text)]).status
                if source.organization in {s.organization for s in found.agreeing}:
                    alone = status  # same organization as the lead's corroborated source
                out.append(Claim(text, alone, (source.id,), role=POINT, covered=True))
        if found.see_also:
            items = self.pack.join(list(found.see_also[:4]))
            out.append(
                Claim(self.pack.say("other_meanings", items=items), factual=False, role=SEE_ALSO)
            )
        out += self.reliability(min(c.status for c in out if c.status is not None))
        out += self.references([(docs[d].source, docs[d].title) for d in found.cited])
        return out

    def expert_note(self, claims: list[Claim]) -> list[Claim]:
        """At expert level, one line giving the status and origin of the facts used."""
        statuses = [c.status for c in claims if c.status is not None and c.factual]
        if not statuses:
            return []
        atoms = sorted({a for c in claims if c.factual for a in c.support if "(" in a})
        names: set[str] = set()
        for text in atoms:
            for e in self.kernel.store.evidence_for_text(text):
                names.add(e.source.name)
        if not names:
            return []
        label = self.label(min(statuses))
        note = self.pack.say("note_status", status=label, sources=self.pack.join(sorted(names)))
        return [Claim(note, factual=False, role=NOTE)]

    # -- whole answers ---------------------------------------------------------
    def definition(self, subject: str, findings: Findings, level: Level) -> list[Claim]:
        own = self.gloss(subject) if self._needs_gloss(subject, level) else None
        claims = [
            *([own] if own is not None else []),
            *self.categories(subject, findings, level),
            *self.properties(subject, findings, level, PROPERTY_CAP[level]),
            *self.members(subject, findings, level, MEMBER_CAP[level]),
            *self.measures(subject, findings, level),
            *self.complexity(subject, findings, level),
            *self.constraints(subject, findings, level),
        ]
        if claims:
            lemma = self.pack.lexicon.lexeme(subject).lemma
            first = claims[0]
            claims[0] = replace(first, text=emphasize(first.text, lemma))
            if level is Level.EXPERT:
                claims += self.expert_note(claims)
        return claims + self.learned_definitions(findings, level)

    def check(self, subject: str, obj: str, findings: Findings, level: Level) -> list[Claim]:
        if findings.refuted:
            atom, assessment = findings.refuted[0]
            text = self.pack.say("no_refuted", reasons=self.reasons(assessment))
            return [Claim(text, Status.REFUTED, (str(atom),), hedged=True)]
        facts = findings.of(Aspect.CHECK)
        if not facts:
            clash = disjointness(self.kernel, subject, obj)
            if clash is None:
                return [Claim(self.pack.say("unknown_check"), None, (), factual=False)]
            a, b, support = clash
            text = self.pack.say("no_disjoint", s=self.np(subject), a=self.np(a), b=self.np(b))
            text, _ = self.hedge(text, _weakest(support), level)
            return [
                Claim(text, _weakest(support), tuple(str(f.atom) for f in support), hedged=True)
            ]
        statement = self.fact_claim("is_a", facts[:1], level, s=self.np(subject), o=self.np(obj))
        if facts[0].status < Status.PLAUSIBLE:  # no plain "yes" on a weak fact
            return [statement]
        yes = Claim(self.pack.say("yes"), facts[0].status, (str(facts[0].atom),), hedged=True)
        return [yes, statement]
