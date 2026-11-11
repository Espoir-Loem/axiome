"""A conversation: orchestrates the team and streams the answer as events.

Flow of a turn: Analyst -> (level update) -> Planner -> Verifier (local
knowledge) -> Researcher (web, when local knowledge is missing) -> Writer ->
Reviewer -> events. Each approved sentence is emitted as soon as it passes
review, so the first words appear before the whole answer is ready.
"""

from __future__ import annotations

from collections.abc import Callable, Generator, Iterator
from dataclasses import replace
from datetime import datetime, tzinfo

from axiome.dialogue.events import Done, Event, Say, Thinking
from axiome.dialogue.layout import render
from axiome.dialogue.level import ANY_DOMAIN, Level, LevelProfile
from axiome.i18n import get_locale
from axiome.kernel import Kernel
from axiome.language.lexicon import GENERAL_DOMAIN
from axiome.language.pack import LanguagePack, load_pack
from axiome.perception.normalize import fold, slug, words
from axiome.reasoning.terms import Atom
from axiome.team.analyst import TOPICAL, Analysis, Analyst, Context, Intent, Mention
from axiome.team.calculator import CalculationError, DivisionByZeroError, calculate, decimal, exact
from axiome.team.planner import make_plan
from axiome.team.researcher import Researcher, WebFindings, digest
from axiome.team.reviewer import Reviewer
from axiome.team.verifier import Findings, is_a_path, verify
from axiome.team.writer import (
    CORROBORATIONS,
    DETAILS,
    EXPLICIT_MEMBER_CAP,
    LEAD,
    LEXICON_SOURCE,
    POINT,
    Claim,
    Writer,
)
from axiome.verification.epistemic import Status

Step = Generator[Event | Claim, None, None]
Handler = Callable[[Analysis, Level], Step]
CALCULATOR_SOURCE = "calculator"
MIN_PURPOSE_OVERLAP = 2  # shared word stems between a need and a pattern's use
STEM = 5
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
    Intent.INCOMPLETE: "incomplete",
    Intent.IDENTITY_AI: "identity_ai",
    Intent.HELP: "help",
    Intent.FORECAST: "forecast_unknown",
    Intent.CODE_REQUEST: "code_not_yet",
    Intent.LAUGHTER: "laughter",
    Intent.FILLER: "filler",
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
        timezone: tzinfo | None = None,
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
        self.timezone = timezone  # None: the machine's local time zone
        self._handlers: dict[Intent, Handler] = {
            Intent.USER_NAME: self._user_name,
            Intent.ASK_USER_NAME: self._ask_user_name,
            Intent.SINGLE_LETTER: self._single_letter,
            Intent.LEVEL: self._level,
            Intent.CONFUSION: self._level,
            Intent.TEACH_IS_A: self._teach,
            Intent.CHECK_IS_A: self._check,
            Intent.CHECK_PROPERTY: self._check_property,
            Intent.REQUIREMENTS: self._requirements,
            Intent.WHY_IS_A: self._why_is_a,
            Intent.COMPARE: self._compare,
            Intent.PURPOSE: self._purpose,
            Intent.ARITHMETIC: self._arithmetic,
            Intent.DATE: self._date,
            Intent.CLOCK: self._clock,
            Intent.GIBBERISH: self._gibberish,
        }

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
        handler = self._handlers.get(intent)
        if handler is not None:
            yield from handler(analysis, level)
        elif intent is Intent.GREETING and name:
            yield self.writer.social("greeting_named", name=name)
        elif intent in SOCIAL:
            yield self.writer.social(SOCIAL[intent])
        elif intent in TOPICAL:
            yield from self._topical(analysis, level)
        else:
            yield self.writer.social("not_understood")

    # -- conversation ------------------------------------------------------------
    def _user_name(self, analysis: Analysis, level: Level) -> Step:
        given = analysis.subject.text.strip() if analysis.subject else ""
        if not given:
            yield self.writer.social("not_understood")
            return
        given = given[:1].upper() + given[1:]
        self.kernel.store.set_meta(USER_NAME_KEY, given)
        yield self.writer.social("nice_to_meet", name=given)

    def _ask_user_name(self, analysis: Analysis, level: Level) -> Step:
        name = self.kernel.store.get_meta(USER_NAME_KEY)
        if name:
            yield self.writer.social("user_name_known", name=name)
        else:
            yield self.writer.social("user_name_unknown")

    def _single_letter(self, analysis: Analysis, level: Level) -> Step:
        letter = analysis.subject.text.strip(" ?.!").upper() if analysis.subject else ""
        yield self.writer.social("single_letter", x=letter)

    def _gibberish(self, analysis: Analysis, level: Level) -> Step:
        yield self.writer.social("not_a_word", x=analysis.subject.text if analysis.subject else "")

    def _level(self, analysis: Analysis, level: Level) -> Step:
        yield self.writer.social(LEVEL_ACK[level])
        if self.context.topic is not None and self.context.intent in TOPICAL:
            repeat = Analysis(self.context.intent, self.context.topic, domain=analysis.domain)
            yield from self._topical(repeat, level)

    def _now(self) -> datetime:
        moment = datetime.fromisoformat(self.kernel.clock.now())
        return moment.astimezone(self.timezone)

    def _date(self, analysis: Analysis, level: Level) -> Step:
        now = self._now()
        day = self.pack.say("day_first") if now.day == 1 else str(now.day)
        yield self.writer.social(
            "date_today",
            weekday=self.pack.weekdays[now.weekday()],
            day=day,
            month=self.pack.months[now.month - 1],
            year=now.year,
        )

    def _clock(self, analysis: Analysis, level: Level) -> Step:
        now = self._now()
        yield self.writer.social("clock_now", hour=now.hour, minute=now.minute)

    def _arithmetic(self, analysis: Analysis, level: Level) -> Step:
        shown = analysis.detail.replace("*", "×")
        try:
            value = calculate(analysis.detail)
        except DivisionByZeroError:
            yield self.writer.social("arith_div_zero", expr=shown)
            return
        except CalculationError:
            yield self.writer.social("arith_invalid")
            return
        if value.denominator == 1:
            text = self.pack.say("arith_result", expr=shown, value=exact(value))
        else:
            approx = decimal(value, comma=self.pack.code == "fr")
            text = self.pack.say("arith_approx", expr=shown, value=exact(value), approx=approx)
        yield Claim(text, Status.PROVED, (CALCULATOR_SOURCE,), role=LEAD)

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
        if concept is not None and mention.corrected:
            yield self.writer.social("assume_meant", x=self.pack.lexicon.lexeme(concept).lemma)
        if concept is not None and analysis.intent is not Intent.RESEARCH:
            plan = make_plan(analysis)
            if plan is not None:
                claims = self.writer_for(analysis, concept, verify(self.kernel, plan), level)
                if claims:
                    yield from claims
                    return
        deep = analysis.intent is Intent.RESEARCH or level is Level.EXPERT
        learn = analysis.intent is not Intent.WHY  # a whole question is not a word
        yield from self._research(mention, concept, level, deep, learn=learn)

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

    def _research(
        self, mention: Mention, concept: str | None, level: Level, deep: bool, *, learn: bool = True
    ) -> Step:
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
        if learn:
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

    def _check_property(self, analysis: Analysis, level: Level) -> Step:
        problem = self._unresolved(analysis.subject)
        if problem is not None:
            yield problem
            return
        subject = analysis.subject.concept if analysis.subject else None
        prop = self.pack.lexicon.adjective(analysis.detail)
        if subject is None or prop is None:
            yield self.writer.social("unknown_property")
            return
        yield from self.writer.check_property(subject, prop, level)

    def _requirements(self, analysis: Analysis, level: Level) -> Step:
        problem = self._unresolved(analysis.subject)
        subject = analysis.subject.concept if analysis.subject else None
        if problem is not None or subject is None:
            yield problem or self.writer.social("unknown_check")
            return
        tokens = words(fold(analysis.obj.text if analysis.obj else ""))
        negated = bool(self.pack.negations.intersection(tokens))
        bare: list[str] = []
        for token in tokens:  # "unsorted": negated "sorted"
            prefix = next((p for p in self.pack.negative_prefixes if token.startswith(p)), "")
            if prefix and len(token) - len(prefix) > 3 and not self.pack.lexicon.lookup(token):
                negated = True
                bare.append(token[len(prefix) :])
            else:
                bare.append(token)
        yield from self.writer.requirements(subject, _stems(" ".join(bare)), negated, level)

    def _why_is_a(self, analysis: Analysis, level: Level) -> Step:
        subject = analysis.subject.concept if analysis.subject else None
        obj = analysis.obj.concept if analysis.obj else None
        path = is_a_path(self.kernel, subject, obj) if subject and obj else None
        if not path:  # not deducible: answer the underlying yes/no question instead
            yield from self._check(replace(analysis, intent=Intent.CHECK_IS_A), level)
            return
        yield from self.writer.because(path, level)

    def _compare(self, analysis: Analysis, level: Level) -> Step:
        for mention in (analysis.subject, analysis.obj):
            problem = self._unresolved(mention)
            if problem is not None:
                yield problem
                return
            if mention is not None and mention.concept is None:
                yield from self._research(mention, None, level, deep=False)
                return
        a = analysis.subject.concept if analysis.subject else None
        b = analysis.obj.concept if analysis.obj else None
        if a is None or b is None:
            yield self.writer.social("not_understood")
            return
        yield from self.writer.compare(a, b, level)

    def _purpose(self, analysis: Analysis, level: Level) -> Step:
        need = _stems(analysis.detail, self.pack.stopwords)
        best: tuple[int, str] = (0, "")
        for lexeme in self.pack.lexicon.uses():
            score = len(need & _stems(lexeme.use, self.pack.stopwords))
            if score > best[0]:
                best = (score, lexeme.concept)
        if best[0] < MIN_PURPOSE_OVERLAP:
            yield self.writer.social("pattern_none")
            return
        concept = best[1]
        use = self.pack.lexicon.lexeme(concept).use
        text = self.pack.say("pattern_for", p=self.writer.np(concept), use=use)
        support = (f"{LEXICON_SOURCE}:{self.pack.code}:{concept}",)
        yield Claim(text, Status.PROVED, support, role=LEAD)

    def _teach(self, analysis: Analysis, level: Level) -> Step:
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
                proper = not mention.article and mention.text[:1].isupper()
                self.pack.lexicon.learn(mention.text, concept, gender, proper=proper)
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


def _stems(text: str, stopwords: frozenset[str] = frozenset()) -> set[str]:
    """Crude stems (first letters) of the content words: "notifier" ~ "notifie"."""
    return {w[:STEM] for w in words(fold(text)) if len(w) > 2 and w not in stopwords}


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
