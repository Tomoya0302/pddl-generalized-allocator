from __future__ import annotations

from typing import List, Dict, Any

from pddl_generalized_allocator.utils.errors import PDDLParseError
from pddl_generalized_allocator.pddl.sexp_parser import SExp
from pddl_generalized_allocator.pddl.ast import (
    TypedSymbol,
    PredicateDecl,
    ActionDecl,
    DomainAST,
    sexp_to_formula,
    sexp_to_effect,
)


class DomainLoader:
    """
    S 式 (SExp) から DomainAST を構築する。

    期待されるトップレベルの形:
      (define (domain NAME)
        (:requirements ...)
        (:types ...)
        (:predicates ...)
        (:action ...)*)
    """

    def __init__(self, sexps: List[SExp]) -> None:
        self.sexps = sexps

    def load(self) -> DomainAST:
        define = self._find_define()
        if not isinstance(define, list) or len(define) < 3:
            raise PDDLParseError(f"Invalid (define ...) structure: {define!r}")

        _, header, *sections = define

        # (domain NAME)
        if not (isinstance(header, list) and len(header) >= 2 and header[0] == "domain"):
            raise PDDLParseError(f"Expected (domain <name>) header, got: {header!r}")
        domain_name = header[1]

        requirements: List[str] = []
        types: List[str] = []
        predicates: List[PredicateDecl] = []
        actions: List[ActionDecl] = []

        for sec in sections:
            if not isinstance(sec, list) or not sec:
                continue
            head = sec[0]
            if not isinstance(head, str):
                continue
            head_lower = head.lower()

            if head_lower == ":requirements":
                # (:requirements :typing :strips ...)
                for r in sec[1:]:
                    if isinstance(r, str):
                        requirements.append(r)
            elif head_lower == ":types":
                types.extend(self._parse_types(sec[1:]))
            elif head_lower == ":predicates":
                predicates.extend(self._parse_predicates(sec[1:]))
            elif head_lower == ":action":
                actions.append(self._parse_action(sec))
            else:
                # MA-PDDL の :shared-data など、現時点では無視
                continue

        return DomainAST(
            name=domain_name,
            requirements=requirements,
            types=types,
            predicates=predicates,
            actions=actions,
        )

    # ------------------------------------------------------------------ #
    # internal helpers
    # ------------------------------------------------------------------ #

    def _find_define(self) -> SExp:
        for sexp in self.sexps:
            if isinstance(sexp, list) and sexp and sexp[0] == "define":
                return sexp
        raise PDDLParseError("No (define ...) found in domain file.")

    def _parse_types(self, sexps: List[SExp]) -> List[str]:
        """
        (:types t1 t2 - base ...) の部分を処理する。
        今は単純にシンボル列をフラットに集めるだけにする。
        """
        types: List[str] = []
        for s in sexps:
            if isinstance(s, str):
                if s == "-":
                    # 階層構造は無視してもいい（必要になったら拡張）
                    continue
                types.append(s)
            elif isinstance(s, list):
                # 想定外だが、取りあえず無視
                continue
        return types

    def _parse_predicates(self, sexps: List[SExp]) -> List[PredicateDecl]:
        """
        (:predicates
           (p ?x - t1 ?y - t2)
           (q ?z - t3)
        )
        """
        preds: List[PredicateDecl] = []
        for s in sexps:
            if not isinstance(s, list) or not s:
                continue
            name = s[0]
            if not isinstance(name, str):
                raise PDDLParseError(f"Invalid predicate name in {s!r}")
            params = self._parse_typed_list(s[1:])
            preds.append(PredicateDecl(name=name, parameters=params))
        return preds

    def _parse_typed_list(self, items: List[SExp]) -> List[TypedSymbol]:
        """
        [?x - t1 ?y - t2 ...] 形式のリストを TypedSymbol の列に変換する。
        """
        result: List[TypedSymbol] = []
        i = 0
        while i < len(items):
            token = items[i]
            if not isinstance(token, str):
                raise PDDLParseError(f"Expected parameter name, got {token!r}")
            if token == "-":
                # 想定外: 名称の前に '-' が来るのはおかしい
                raise PDDLParseError("Unexpected '-' in typed list head position")

            name = token
            ttype: str | None = None

            # 次が '-' なら型が付いている
            if i + 2 <= len(items) - 1 and isinstance(items[i + 1], str) and items[i + 1] == "-":
                type_name = items[i + 2]
                if not isinstance(type_name, str):
                    raise PDDLParseError(f"Expected type name after '-', got {type_name!r}")
                ttype = type_name
                i += 3
            else:
                i += 1

            result.append(TypedSymbol(name=name, type=ttype))

        return result

    def _parse_action(self, sexp: List[SExp]) -> ActionDecl:
        """
        (:action move
           :parameters (?r - robot ?from - loc ?to - loc)
           :precondition (and ...)
           :effect (and ...))
        """
        if len(sexp) < 2 or sexp[0] != ":action":
            raise PDDLParseError(f"Invalid :action form: {sexp!r}")

        if not isinstance(sexp[1], str):
            raise PDDLParseError(f"Action name must be symbol, got {sexp[1]!r}")
        name = sexp[1]

        params: List[TypedSymbol] = []
        precond = None
        effect = None

        # 残りをキー:値ペアで読む
        i = 2
        while i < len(sexp):
            elem = sexp[i]
            if not isinstance(elem, str):
                raise PDDLParseError(f"Expected keyword in action, got {elem!r}")
            key = elem.lower()
            if key == ":parameters":
                if i + 1 >= len(sexp):
                    raise PDDLParseError("Missing parameter list after :parameters")
                param_list = sexp[i + 1]
                if not isinstance(param_list, list):
                    raise PDDLParseError(f"Expected parameter list, got {param_list!r}")
                params = self._parse_typed_list(param_list)
                i += 2
            elif key == ":precondition":
                if i + 1 >= len(sexp):
                    raise PDDLParseError("Missing precondition after :precondition")
                precond_sexp = sexp[i + 1]
                precond = sexp_to_formula(precond_sexp)
                i += 2
            elif key == ":effect":
                if i + 1 >= len(sexp):
                    raise PDDLParseError("Missing effect after :effect")
                effect_sexp = sexp[i + 1]
                effect = sexp_to_effect(effect_sexp)
                i += 2
            else:
                # 未使用のキーワードはスキップ (e.g., :duration など。ただし今回の subset では登場しない想定)
                i += 1

        if effect is None:
            # 空効果として扱う
            effect = sexp_to_effect(["and"])

        return ActionDecl(
            name=name,
            parameters=params,
            precondition=precond,
            effect=effect,
        )
