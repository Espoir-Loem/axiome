"""Analyseur du langage logique d'Axiome (« AXL »).

Grammaire (EBNF) ::

    programme   = { énoncé } ;
    énoncé      = ( règle | contrainte | requête | fait ) "." ;
    fait        = atome ;
    règle       = [ "[" NOM "]" ] atome ":-" corps ;
    contrainte  = "!" NOM ":-" corps ;
    requête     = "?-" corps ;
    corps       = littéral { "," littéral } ;
    littéral    = [ "non" ] atome ;
    atome       = NOM [ "(" terme { "," terme } ")" ] ;
    terme       = VARIABLE | NOM | CHAÎNE | ENTIER ;

NOM commence par une minuscule (accents autorisés), VARIABLE par une majuscule
ou ``_``. Les commentaires commencent par ``%`` ou ``#``.
"""

from __future__ import annotations

from dataclasses import dataclass

from axiome.core.errors import ParseError
from axiome.reasoning.program import Constraint, Rule
from axiome.reasoning.terms import Atom, Literal, Term, Var

_PUNCT = ("?-", ":-", "(", ")", ",", ".", "!", "[", "]")
_ESCAPES = {"n": "\n", '"': '"', "\\": "\\"}


@dataclass(frozen=True, slots=True)
class Token:
    kind: str  # NAME VAR STRING INT PUNCT EOF
    value: str
    line: int
    column: int


@dataclass(frozen=True, slots=True)
class Query:
    body: tuple[Literal, ...]

    def __str__(self) -> str:
        return f"?- {', '.join(map(str, self.body))}."


Statement = Atom | Rule | Constraint | Query


def tokenize(text: str) -> list[Token]:  # noqa: C901, PLR0915 - automate lexical linéaire
    tokens: list[Token] = []
    i, line, col = 0, 1, 1
    n = len(text)

    def err(msg: str) -> ParseError:
        return ParseError(msg, line, col)

    while i < n:
        ch = text[i]
        if ch == "\n":
            i, line, col = i + 1, line + 1, 1
            continue
        if ch.isspace():
            i, col = i + 1, col + 1
            continue
        if ch in "%#":
            while i < n and text[i] != "\n":
                i += 1
            continue
        start_col = col
        punct = next((p for p in _PUNCT if text.startswith(p, i)), None)
        if punct is not None:
            tokens.append(Token("PUNCT", punct, line, start_col))
            i, col = i + len(punct), col + len(punct)
            continue
        if ch == '"':
            j, buf = i + 1, []
            while True:
                if j >= n or text[j] == "\n":
                    raise err("chaîne non terminée")
                c = text[j]
                if c == '"':
                    break
                if c == "\\":
                    if j + 1 >= n or text[j + 1] not in _ESCAPES:
                        raise err("séquence d'échappement invalide")
                    buf.append(_ESCAPES[text[j + 1]])
                    j += 2
                    continue
                buf.append(c)
                j += 1
            tokens.append(Token("STRING", "".join(buf), line, start_col))
            col += j + 1 - i
            i = j + 1
            continue
        if ch.isdigit() or (ch == "-" and i + 1 < n and text[i + 1].isdigit()):
            j = i + 1
            while j < n and text[j].isdigit():
                j += 1
            tokens.append(Token("INT", text[i:j], line, start_col))
            col += j - i
            i = j
            continue
        if ch.isalpha() or ch == "_":
            j = i + 1
            while j < n and (text[j].isalnum() or text[j] == "_"):
                j += 1
            word = text[i:j]
            kind = "VAR" if (ch == "_" or ch.isupper()) else "NAME"
            tokens.append(Token(kind, word, line, start_col))
            col += j - i
            i = j
            continue
        raise err(f"caractère inattendu {ch!r}")
    tokens.append(Token("EOF", "", line, col))
    return tokens


class _Parser:
    def __init__(self, text: str) -> None:
        self.tokens = tokenize(text)
        self.pos = 0
        self._anon = 0

    # -- utilitaires -------------------------------------------------------
    @property
    def tok(self) -> Token:
        return self.tokens[self.pos]

    def error(self, msg: str) -> ParseError:
        found = self.tok.value or "fin du texte"
        return ParseError(f"{msg} (trouvé : {found!r})", self.tok.line, self.tok.column)

    def accept(self, value: str) -> bool:
        if self.tok.kind == "PUNCT" and self.tok.value == value:
            self.pos += 1
            return True
        return False

    def expect(self, value: str) -> None:
        if not self.accept(value):
            raise self.error(f"« {value} » attendu")

    def name(self) -> str:
        if self.tok.kind != "NAME":
            raise self.error("nom (commençant par une minuscule) attendu")
        value = self.tok.value
        self.pos += 1
        return value

    # -- grammaire ---------------------------------------------------------
    def term(self) -> Term:
        t = self.tok
        self.pos += 1
        if t.kind == "VAR":
            if t.value == "_":  # variable anonyme : chaque occurrence est distincte
                self._anon += 1
                return Var(f"_G{self._anon}")
            return Var(t.value)
        if t.kind in ("NAME", "STRING"):
            return t.value
        if t.kind == "INT":
            return int(t.value)
        self.pos -= 1
        raise self.error("terme attendu")

    def atom(self) -> Atom:
        pred = self.name()
        if pred == "non":
            raise self.error("« non » est réservé à la négation")
        args: list[Term] = []
        if self.accept("("):
            args.append(self.term())
            while self.accept(","):
                args.append(self.term())
            self.expect(")")
        return Atom(pred, tuple(args))

    def literal(self) -> Literal:
        if self.tok.kind == "NAME" and self.tok.value == "non":
            self.pos += 1
            return Literal(self.atom(), negated=True)
        return Literal(self.atom())

    def body(self) -> tuple[Literal, ...]:
        lits = [self.literal()]
        while self.accept(","):
            lits.append(self.literal())
        return tuple(lits)

    def statement(self, axiomatic: bool) -> Statement:
        if self.accept("?-"):
            stmt: Statement = Query(self.body())
        elif self.accept("!"):
            cname = self.name()
            self.expect(":-")
            stmt = Constraint(cname, self.body())
        else:
            label = ""
            if self.accept("["):
                label = self.name()
                self.expect("]")
            head = self.atom()
            if self.accept(":-"):
                stmt = Rule(head, self.body(), label, axiomatic)
            elif label:
                raise self.error("une étiquette [nom] n'est permise que sur une règle")
            else:
                if not head.is_ground():
                    raise self.error(f"un fait doit être clos : {head}")
                stmt = head
        self.expect(".")
        return stmt

    def program(self, axiomatic: bool) -> list[Statement]:
        out: list[Statement] = []
        while self.tok.kind != "EOF":
            out.append(self.statement(axiomatic))
        return out


def parse_program(text: str, *, axiomatic: bool = True) -> list[Statement]:
    return _Parser(text).program(axiomatic)


def parse_statement(text: str, *, axiomatic: bool = True) -> Statement:
    """Analyse un énoncé unique ; le point final est optionnel."""
    stripped = text.strip()
    if not stripped.endswith("."):
        stripped += "."
    stmts = parse_program(stripped, axiomatic=axiomatic)
    if len(stmts) != 1:
        raise ParseError("un seul énoncé attendu", 1, 1)
    return stmts[0]


def parse_atom(text: str) -> Atom:
    stmt = parse_statement(text)
    if not isinstance(stmt, Atom):
        raise ParseError("un fait clos était attendu", 1, 1)
    return stmt
