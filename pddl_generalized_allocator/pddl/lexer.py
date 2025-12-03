from __future__ import annotations

from dataclasses import dataclass
from typing import List

from pddl_generalized_allocator.utils.errors import PDDLParseError


@dataclass
class Token:
    type: str   # 'LPAREN' | 'RPAREN' | 'NAME' | 'DASH'
    value: str
    line: int
    column: int

    def __repr__(self) -> str:
        return f"Token({self.type}, {self.value!r}, {self.line}:{self.column})"


class Lexer:
    """
    シンプルな PDDL / MA-PDDL 用 lexer。

    対応:
        - コメント ';'〜改行 まで無視
        - '(' / ')' / '-' を専用トークン
        - それ以外の記号は NAME としてまとめる
    """

    def __init__(self, text: str) -> None:
        self.text = text
        self.pos = 0
        self.line = 1
        self.col = 1

    def _peek(self) -> str | None:
        if self.pos >= len(self.text):
            return None
        return self.text[self.pos]

    def _advance(self, n: int = 1) -> None:
        for _ in range(n):
            if self.pos >= len(self.text):
                return
            ch = self.text[self.pos]
            self.pos += 1
            if ch == "\n":
                self.line += 1
                self.col = 1
            else:
                self.col += 1

    def _emit(self, tokens: List[Token], ttype: str, value: str, line: int, col: int) -> None:
        tokens.append(Token(ttype, value, line, col))

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []

        while True:
            ch = self._peek()
            if ch is None:
                break

            # whitespace
            if ch.isspace():
                self._advance()
                continue

            # コメント ; ... end of line
            if ch == ";":
                # skip until newline or EOF
                while ch is not None and ch != "\n":
                    self._advance()
                    ch = self._peek()
                continue

            line, col = self.line, self.col

            if ch == "(":
                self._emit(tokens, "LPAREN", ch, line, col)
                self._advance()
            elif ch == ")":
                self._emit(tokens, "RPAREN", ch, line, col)
                self._advance()
            elif ch == "-":
                # パラメータの型指定で使う '-'
                self._emit(tokens, "DASH", ch, line, col)
                self._advance()
            else:
                # NAME トークン
                start_line, start_col = line, col
                value_chars: list[str] = []
                while True:
                    ch = self._peek()
                    if ch is None:
                        break
                    if ch.isspace() or ch in "()":
                        break
                    # '-' も NAME に含める（型指定の '-' は別トークンにしたが、
                    # ':' を含むキーワードなどは NAME にしておく）
                    if ch == ";":
                        # コメント開始なら break
                        break
                    value_chars.append(ch)
                    self._advance()
                if not value_chars:
                    raise PDDLParseError(f"Unexpected character {ch!r} at {line}:{col}")
                value = "".join(value_chars)
                self._emit(tokens, "NAME", value, start_line, start_col)

        return tokens
