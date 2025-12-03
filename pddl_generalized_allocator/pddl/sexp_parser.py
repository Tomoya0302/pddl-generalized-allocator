from __future__ import annotations

from typing import List, Union

from pddl_generalized_allocator.utils.errors import PDDLParseError
from pddl_generalized_allocator.pddl.lexer import Token


SExp = Union[str, List["SExp"]]


class SExpParser:
    """
    PDDL を Lisp 風 S 式のネストした list[str|list] に変換する簡単なパーサ。
    """

    def __init__(self, tokens: List[Token]) -> None:
        self.tokens = tokens
        self.pos = 0

    def _peek(self) -> Token | None:
        if self.pos >= len(self.tokens):
            return None
        return self.tokens[self.pos]

    def _advance(self) -> Token:
        tok = self._peek()
        if tok is None:
            raise PDDLParseError("Unexpected EOF in SExpParser")
        self.pos += 1
        return tok

    def parse(self) -> List[SExp]:
        sexps: List[SExp] = []
        while self._peek() is not None:
            tok = self._peek()
            if tok.type != "LPAREN":
                raise PDDLParseError(
                    f"Expected '(' at top-level, got {tok.type} {tok.value!r} at {tok.line}:{tok.column}"
                )
            sexps.append(self._parse_sexp())
        return sexps

    def _parse_sexp(self) -> SExp:
        # assume current token is LPAREN
        lpar = self._advance()
        if lpar.type != "LPAREN":
            raise PDDLParseError(f"Expected '(', got {lpar}")

        elements: List[SExp] = []
        while True:
            tok = self._peek()
            if tok is None:
                raise PDDLParseError("Unclosed '(' in S-expression")
            if tok.type == "RPAREN":
                self._advance()
                break
            if tok.type == "LPAREN":
                elements.append(self._parse_sexp())
            elif tok.type in ("NAME", "DASH"):
                self._advance()
                elements.append(tok.value)
            else:
                raise PDDLParseError(f"Unexpected token in S-expression: {tok}")
        return elements
