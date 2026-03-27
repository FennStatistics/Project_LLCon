from __future__ import annotations

from dataclasses import dataclass
import re

from search.ast import AndNode
from search.ast import Node
from search.ast import NotNode
from search.ast import OrNode
from search.ast import ProxNode
from search.ast import TermNode


class QueryParseError(ValueError):
    pass


@dataclass(frozen=True)
class Token:
    kind: str
    value: str | int


TOKEN_PATTERN = re.compile(
    r"\s+|<\d+>|\(|\)|\bAND\b|\bOR\b|\bNOT\b|[^\s()]+",
    re.IGNORECASE,
)


class QueryParser:
    def __init__(self, query: str) -> None:
        self.query = query
        self.tokens = self._tokenize(query)
        self.index = 0

    def parse(self) -> Node:
        if not self.tokens:
            raise QueryParseError("Empty query")
        node = self._parse_or()
        if self._current() is not None:
            raise QueryParseError("Unexpected token after end of query")
        return node

    def _tokenize(self, query: str) -> list[Token]:
        raw_tokens: list[Token] = []
        for match in TOKEN_PATTERN.finditer(query):
            token = match.group(0)
            if token.isspace():
                continue
            upper = token.upper()
            if upper == "AND":
                raw_tokens.append(Token("AND", "AND"))
            elif upper == "OR":
                raw_tokens.append(Token("OR", "OR"))
            elif upper == "NOT":
                raw_tokens.append(Token("NOT", "NOT"))
            elif token == "(":
                raw_tokens.append(Token("LPAREN", token))
            elif token == ")":
                raw_tokens.append(Token("RPAREN", token))
            elif token.startswith("<") and token.endswith(">"):
                distance = int(token[1:-1])
                if distance <= 0:
                    raise QueryParseError("Proximity distance must be > 0")
                raw_tokens.append(Token("PROX", distance))
            else:
                raw_tokens.append(Token("TERM", self._normalize_term(token)))

        return self._insert_implicit_and(raw_tokens)

    def _insert_implicit_and(self, tokens: list[Token]) -> list[Token]:
        if not tokens:
            return tokens

        result: list[Token] = []
        prev_kind: str | None = None
        for token in tokens:
            if (
                prev_kind in {"TERM", "RPAREN"}
                and token.kind in {"TERM", "LPAREN", "NOT"}
            ):
                result.append(Token("AND", "AND"))
            result.append(token)
            prev_kind = token.kind
        return result

    def _normalize_term(self, term: str) -> str:
        stripped = term.strip()
        if stripped.startswith('"') and stripped.endswith('"') and len(stripped) > 1:
            stripped = stripped[1:-1]
        return stripped.lower()

    def _current(self) -> Token | None:
        if self.index >= len(self.tokens):
            return None
        return self.tokens[self.index]

    def _consume(self, kind: str) -> Token:
        token = self._current()
        if token is None or token.kind != kind:
            raise QueryParseError(f"Expected {kind}")
        self.index += 1
        return token

    def _match(self, kind: str) -> bool:
        token = self._current()
        if token is None or token.kind != kind:
            return False
        self.index += 1
        return True

    def _parse_or(self) -> Node:
        node = self._parse_and()
        while self._match("OR"):
            right = self._parse_and()
            node = OrNode(node, right)
        return node

    def _parse_and(self) -> Node:
        node = self._parse_not()
        while self._match("AND"):
            right = self._parse_not()
            node = AndNode(node, right)
        return node

    def _parse_not(self) -> Node:
        if self._match("NOT"):
            operand = self._parse_not()
            return NotNode(operand)
        return self._parse_prox()

    def _parse_prox(self) -> Node:
        node = self._parse_primary()
        while True:
            token = self._current()
            if token is None or token.kind != "PROX":
                break
            self.index += 1
            right = self._parse_primary()
            node = ProxNode(node, right, int(token.value))
        return node

    def _parse_primary(self) -> Node:
        token = self._current()
        if token is None:
            raise QueryParseError("Unexpected end of query")
        if token.kind == "TERM":
            self.index += 1
            if not token.value:
                raise QueryParseError("Empty term")
            return TermNode(str(token.value))
        if token.kind == "LPAREN":
            self.index += 1
            node = self._parse_or()
            self._consume("RPAREN")
            return node
        raise QueryParseError(f"Unexpected token: {token.kind}")
