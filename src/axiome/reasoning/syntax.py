"""Parser for the Axiome logic language ("AXL").

Grammar (EBNF)::

    program     = { statement } ;
    statement   = ( rule | constraint | query | fact ) "." ;
    fact        = atom ;
    rule        = [ "[" NAME "]" ] atom ":-" body ;
    constraint  = "!" NAME ":-" body ;
    query       = "?-" body ;
    body        = literal { "," literal } ;
    literal     = [ "not" ] atom ;
    atom        = NAME [ "(" term { "," term } ")" ] ;
    term        = VARIABLE | NAME | STRING | INTEGER ;

NAME starts with a lowercase letter (Unicode letters allowed), VARIABLE with an
uppercase letter or ``_``. Comments start with ``%`` or ``#``.
"""

from __future__ import annotations

from dataclasses import dataclass

from axiome.core.errors import ParseError
from axiome.reasoning.program import Constraint, Rule
from axiome.reasoning.terms import NEGATION, Atom, Literal, Term, Var

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


def _read_string(text: str, start: int, line: int, col: int) -> tuple[str, int]:
    """Read a quoted string starting at ``start`` (the opening quote); return (value, end)."""
    j = start + 1
    buf: list[str] = []
    while True:
        if j >= len(text) or text[j] == "\n":
            raise ParseError("parse.unterminated_string", line, col)
        c = text[j]
        if c == '"':
            return "".join(buf), j + 1
        if c == "\\":
            if j + 1 >= len(text) or text[j + 1] not in _ESCAPES:
                raise ParseError("parse.invalid_escape", line, col)
            buf.append(_ESCAPES[text[j + 1]])
            j += 2
            continue
        buf.append(c)
        j += 1


def _scan_while(text: str, i: int, accept: str) -> int:
    j = i + 1
    while j < len(text) and (
        text[j].isdigit() if accept == "digit" else (text[j].isalnum() or text[j] == "_")
    ):
        j += 1
    return j


def tokenize(text: str) -> list[Token]:
    """Linear lexer; positions are 1-based lines and columns."""
    tokens: list[Token] = []
    i, line, col, n = 0, 1, 1, len(text)
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
        punct = next((p for p in _PUNCT if text.startswith(p, i)), None)
        if punct is not None:
            kind, value, end = "PUNCT", punct, i + len(punct)
        elif ch == '"':
            value, end = _read_string(text, i, line, col)
            kind = "STRING"
        elif ch.isdigit() or (ch == "-" and i + 1 < n and text[i + 1].isdigit()):
            end = _scan_while(text, i, "digit")
            kind, value = "INT", text[i:end]
        elif ch.isalpha() or ch == "_":
            end = _scan_while(text, i, "word")
            value = text[i:end]
            kind = "VAR" if (ch == "_" or ch.isupper()) else "NAME"
        else:
            raise ParseError("parse.unexpected_char", line, col, char=repr(ch))
        tokens.append(Token(kind, value, line, col))
        col += end - i
        i = end
    tokens.append(Token("EOF", "", line, col))
    return tokens


class _Parser:
    def __init__(self, text: str) -> None:
        self.tokens = tokenize(text)
        self.pos = 0
        self._anon = 0

    # -- helpers -------------------------------------------------------------
    @property
    def tok(self) -> Token:
        return self.tokens[self.pos]

    def error(self, key: str, **params: object) -> ParseError:
        found = repr(self.tok.value) if self.tok.value else "EOF"
        return ParseError(key, self.tok.line, self.tok.column, found=found, **params)

    def accept(self, value: str) -> bool:
        if self.tok.kind == "PUNCT" and self.tok.value == value:
            self.pos += 1
            return True
        return False

    def expect(self, value: str) -> None:
        if not self.accept(value):
            raise self.error("parse.expected_token", token=value)

    def name(self) -> str:
        if self.tok.kind != "NAME":
            raise self.error("parse.expected_name")
        value = self.tok.value
        self.pos += 1
        return value

    # -- grammar -------------------------------------------------------------
    def term(self) -> Term:
        t = self.tok
        if t.kind == "VAR":
            self.pos += 1
            if t.value == "_":  # anonymous variable: every occurrence is distinct
                self._anon += 1
                return Var(f"_G{self._anon}")
            return Var(t.value)
        if t.kind in ("NAME", "STRING"):
            self.pos += 1
            return t.value
        if t.kind == "INT":
            self.pos += 1
            return int(t.value)
        raise self.error("parse.expected_term")

    def atom(self) -> Atom:
        pred = self.name()
        if pred == NEGATION:
            raise self.error("parse.reserved_negation", keyword=NEGATION)
        args: list[Term] = []
        if self.accept("("):
            args.append(self.term())
            while self.accept(","):
                args.append(self.term())
            self.expect(")")
        return Atom(pred, tuple(args))

    def literal(self) -> Literal:
        if self.tok.kind == "NAME" and self.tok.value == NEGATION:
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
                raise self.error("parse.label_only_on_rule")
            elif not head.is_ground():
                raise self.error("parse.fact_not_ground", atom=head)
            else:
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
    """Parse a single statement; the final period is optional."""
    stripped = text.strip()
    if not stripped.endswith("."):
        stripped += "."
    stmts = parse_program(stripped, axiomatic=axiomatic)
    if len(stmts) != 1:
        raise ParseError("parse.single_statement", 1, 1)
    return stmts[0]


def parse_atom(text: str) -> Atom:
    stmt = parse_statement(text)
    if not isinstance(stmt, Atom):
        raise ParseError("parse.ground_fact_expected", 1, 1)
    return stmt
