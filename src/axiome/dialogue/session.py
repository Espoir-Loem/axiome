"""A conversation: orchestrates the team and streams the answer as events.

Flow of a turn: Analyst -> (level update) -> Planner -> Verifier (local
knowledge) -> Researcher (web, when local knowledge is missing) -> Writer ->
Reviewer -> events. Each approved sentence is emitted as soon as it passes
review, so the first words appear before the whole answer is ready.
"""

from __future__ import annotations

from collections.abc import Generator, Iterator
from dataclasses import replace

from axiome.dialogue.events import Done, Event, Say, Thinking
from axiome.dialogue.layout import render
from axiome.dialogue.level import ANY_DOMAIN, Level, LevelProfile
from axiome.i18n import get_locale
from axiome.kernel import Kernel
from axiome.language.lexicon import GENERAL_DOMAIN
from axiome.language.pack import LanguagePack, load_pack
from axiome.perception.normalize import slug
from axiome.reasoning.terms import Atom
from axiome.team.analyst import TOPICAL, Analysis, Analyst, Context, Intent, Mention
from axiome.team.planner import make_plan
from axiome.team.researcher import Researcher, WebFindings, digest
from axiome.team.reviewer import Reviewer
from axiome.team.verifier import Findings, verify
from axiome.team.writer import (
    CORROBORATIONS,
    DETAILS,
    EXPLICIT_MEMBER_CAP,
    LEAD,
    POINT,
    Claim,
    Writer,
)
from axiome.verification.epistemic import Status

Step = Generator[Event | Claim, None, None]
SOCIAL = {
    Intent.GREETING: "greeting",
    Intent.THANKS: "thanks",
    Intent.FAREWELL: "farewell",
    Intent.IDENTITY: "identity",
    Intent.CAPABILITIES: "capabilities",
    Intent.HOW_ARE_YOU: "how_are_you",
    Intent.USER_FINE: "user_fine",
    Intent.NAME: "name",
    Intent.ACK: "ack",
    Intent.CHAT: "chat_fallback",
}
USER_NAME_KEY = "user:name"
FEMININE_ARTICLES = frozenset({"une", "la", "cette"})
LEVEL_ACK = {
    Level.BEGINNER: "level_beginner",
    Level.INTERMEDIATE: "level_intermediate",
    Level.EXPERT: "level_expert",
}


class Session:
    def __init__(
        self,
        kernel: Kernel,
        language: str | None = None,
        researcher: Researcher | None = None,
        profile: LevelProfile | None = None,
    ) -> None:
        self.kernel = kernel
        self.pack: LanguagePack = load_pack(language or get_locale())
        for form, concept in kernel.store.words(self.pack.code):
            self.pack.lexicon.learn(form, concept)
        self.researcher = researcher
        self.profile = profile or LevelProfile(kernel.store)
        self.analyst = Analyst(self.pack)
        self.writer = Writer(self.pack, kernel)
        self.reviewer = Reviewer(self.pack)
        self.context = Context()

    # -- public ----------------------------------------------------------------
    def respond(self, text: str) -> Iterator[Event]:
        analysis = self.analyst.analyze(text, self.context)
        level = self._update_level(analysis)
        counts = [0, 0, 0]  # approved, blocked, corrected
        pending: list[Claim] = []
        for item in self._answer(analysis, level):
            if isinstance(item, Claim):
                pending.append(item)
                continue
            yield from self._flush(pending, analysis, counts)
            yield item
        yield from self._flush(pending, analysis, counts)
        self._remember(analysis)
        yield Done(*counts)

    def _flush(self, pending: list[Claim], analysis: Analysis, counts: list[int]) -> Iterator[Say]:
        """Review a whole answer at once (the reliability note covers its sentences)."""
        if not pending:
            return
        review = self.reviewer.review(_with_lead(pending), analysis.waivers)
        pending.clear()
        counts[1] += len(review.blocked)
        counts[2] += review.corrected
        for claim in review.approved:
            counts[0] += 1
            yield Say(claim.text, claim.status, claim.support, claim.role)

    def answer_text(self, text: str) -> str:
        """The whole formatted answer, without the progress lines (non-streaming)."""
        return render(e for e in self.respond(text) if not isinstance(e, Thinking))

    # -- state -----------------------------------------------------------------
    def _domain(self, analysis: Analysis) -> str:
        if analysis.domain != GENERAL_DOMAIN:
            return analysis.domain
        return ANY_DOMAIN

    def _update_level(self, analysis: Analysis) -> Level:
        domain = self._domain(analysis)
        if analysis.level is not None:
            self.profile.set(domain, analysis.level)
        elif analysis.intent is Intent.CONFUSION:
            self.profile.lower(domain)
        else:
            self.profile.observe(domain, analysis.technical_terms)
        return self.profile.level(domain)

    def _remember(self, analysis: Analysis) -> None:
        if (analysis.subject is not None and analysis.subject.concepts) or (
            analysis.subject is not None and analysis.subject.text and not analysis.subject.pronoun
        ):
            self.context.topic = analysis.subject
        if analysis.intent in TOPICAL or analysis.intent is Intent.CHECK_IS_A:
            self.context.intent = analysis.intent

    # -- answering ---------------------------------------------------------------
    def _answer(self, analysis: Analysis, level: Level) -> Step:
        intent = analysis.intent
        name = self.kernel.store.get_meta(USER_NAME_KEY)
        if intent is Intent.GREETING and name:
            yield self.writer.social("greeting_named", name=name)
        elif intent is Intent.USER_NAME and analysis.subject is not None:
            given = analysis.subject.text.strip()
            given = given[:1].upper() + given[1:]
            self.kernel.store.set_meta(USER_NAME_KEY, given)
            yield self.writer.social("nice_to_meet", name=given)
        elif intent in SOCIAL:
            yield self.writer.social(SOCIAL[intent])
        elif intent in (Intent.LEVEL, Intent.CONFUSION):
            yield self.writer.social(LEVEL_ACK[level])
            if self.context.topic is not None and self.context.intent in TOPICAL:
                repeat = Analysis(self.context.intent, self.context.topic, domain=analysis.domain)
                yield from self._topical(repeat, level)
        elif intent is Intent.TEACH_IS_A:
            yield from self._teach(analysis)
        elif intent is Intent.CHECK_IS_A:
            yield from self._check(analysis, level)
        elif intent in TOPICAL:
            yield from self._topical(analysis, level)
        else:
            yield self.writer.social("not_understood")

    def _unresolved(self, mention: Mention | None) -> Claim | None:
        if mention is None:
            return self.writer.social("not_understood")
        if mention.pronoun:
            return self.writer.social("no_topic")
        if mention.ambiguous:
            options = [self.pack.lexicon.lexeme(c).lemma for c in mention.concepts]
            return self.writer.social("clarify", options=self.pack.join(options))
        return None

    def _topical(self, analysis: Analysis, level: Level) -> Step:
        mention = analysis.subject
        problem = self._unresolved(mention)
        if problem is not None or mention is None:
            yield problem or self.writer.social("not_understood")
            return
        concept = mention.concept
        if concept is not None and analysis.intent is not Intent.RESEARCH:
            plan = make_plan(analysis)
            if plan is not None:
                claims = self.writer_for(analysis, concept, verify(self.kernel, plan), level)
                if claims:
                    yield from claims
                    return
        deep = analysis.intent is Intent.RESEARCH or level is Level.EXPERT
        yield from self._research(mention, concept, level, deep)

    def writer_for(
        self, analysis: Analysis, concept: str, findings: Findings, level: Level
    ) -> list[Claim]:
        w = self.writer
        if findings.empty():
            return []
        if analysis.intent is Intent.PROPERTIES:
            return w.properties(concept, findings, level, 99)
        if analysis.intent is Intent.MEMBERS:
            return w.members(concept, findings, level, EXPLICIT_MEMBER_CAP[level])
        if analysis.intent is Intent.UNIT:
            return w.measures(concept, findings, level)
        if analysis.intent is Intent.COMPLEXITY:
            return w.complexity(concept, findings, level)
        return w.definition(concept, findings, level)

    def _research(self, mention: Mention, concept: str | None, level: Level, deep: bool) -> Step:
        researcher = self.researcher
        if researcher is None or not researcher.active(deep):
            yield self.writer.social("unknown_topic", x=mention.text)
            yield self.writer.social("offline")
            return
        names = [p.name for p in researcher.active(deep)]
        yield Thinking(self.pack.say("think_search", providers=self.pack.join(names)))
        docs = yield from researcher.search(mention.text, self.pack.code, deep)
        found = digest(
            mention.text,
            docs,
            self.pack.stopwords,
            details=DETAILS[level],
            corroborations=CORROBORATIONS[level],
        )
        claims = self.writer.web_answer(mention.text, found)
        if not claims:
            yield self.writer.social("search_failed", x=mention.text)
            return
        yield from claims
        self._learn(mention, concept, found)

    def _learn(self, mention: Mention, concept: str | None, found: WebFindings) -> None:
        """Keep what was found (with provenance) so the next answer works offline."""
        concept = concept or slug(mention.text)
        if not concept or found.lead is None:
            return
        for excerpt in (found.lead, *found.points):
            predicate = "defined_as" if excerpt is found.lead else "described_as"
            atom = Atom(predicate, (concept, excerpt.text))
            sources = (
                found.agreeing if excerpt is found.lead else (found.documents[excerpt.doc].source,)
            )
            for source in sources:
                self.kernel.record(atom, source, excerpt.text)
        self.pack.lexicon.learn(mention.text, concept)
        self.kernel.store.add_word(
            self.pack.code, mention.text, concept, found.agreeing[0].id, self.kernel.clock.now()
        )

    def _check(self, analysis: Analysis, level: Level) -> Step:
        for mention in (analysis.subject, analysis.obj):
            problem = self._unresolved(mention)
            if problem is not None:
                yield problem
                return
        subject = analysis.subject.concept if analysis.subject else None
        obj = analysis.obj.concept if analysis.obj else None
        plan = make_plan(analysis)
        if subject is None or obj is None or plan is None:
            yield Claim(self.pack.say("unknown_check"), factual=False)
            return
        yield from self.writer.check(subject, obj, verify(self.kernel, plan), level)

    def _teach(self, analysis: Analysis) -> Step:
        names: list[str] = []
        for mention in (analysis.subject, analysis.obj):
            problem = self._unresolved(mention)
            if problem is not None or mention is None:
                yield problem or self.writer.social("not_understood")
                return
            concept = mention.concept or slug(mention.text)
            if not concept:
                yield self.writer.social("not_understood")
                return
            names.append(concept)
            if mention.concept is None:
                gender = "f" if mention.article in FEMININE_ARTICLES else "m"
                self.pack.lexicon.learn(mention.text, concept, gender)
                self.kernel.store.add_word(
                    self.pack.code, mention.text, concept, "user", self.kernel.clock.now()
                )
        atom = Atom("is_a", (names[0], names[1]))
        ack = self.kernel.tell(str(atom))
        state = self.kernel.state
        if atom in state.refuted:
            reasons = self.writer.reasons(state.refuted[atom])
            yield self.writer.social("teach_refuted", reasons=reasons)
        elif ack.key == "tell.known" or _established(state.assessments.get(atom)):
            yield self.writer.social("teach_known")
        else:
            yield self.writer.social("teach_noted")


def _established(assessment: object) -> bool:
    return getattr(assessment, "status", Status.UNVERIFIED) > Status.UNVERIFIED


def _with_lead(claims: list[Claim]) -> list[Claim]:
    """Make sure an answer opens with a lead sentence (the summary)."""
    if any(c.role == LEAD for c in claims):
        return claims
    out = list(claims)
    for i, claim in enumerate(out):
        if claim.role == POINT:
            out[i] = replace(claim, role=LEAD)
            break
    return out
