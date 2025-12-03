from __future__ import annotations

from typing import List, Optional, Set

from pddl_generalized_allocator.utils.errors import PDDLParseError
from pddl_generalized_allocator.pddl.sexp_parser import SExp
from pddl_generalized_allocator.pddl.ast import (
    TypedSymbol,
    Atom,
    ProblemAST,
    sexp_to_atom,
    sexp_to_formula,
)


class ProblemLoader:
    """
    S 式 (SExp) から ProblemAST を構築する。

    期待されるトップレベルの形:
      (define (problem NAME)
        (:domain DOMAIN-NAME)
        (:objects ...)
        (:init ...)
        (:goal ...)
        (:agents ...)?)  # MA-PDDL
    """

    def __init__(self, sexps: List[SExp]) -> None:
        self.sexps = sexps

    def load(self) -> ProblemAST:
        define = self._find_define()
        if not isinstance(define, list) or len(define) < 3:
            raise PDDLParseError(f"Invalid (define ...) structure in problem: {define!r}")

        _, header, *sections = define
        if not (isinstance(header, list) and len(header) >= 2 and header[0] == "problem"):
            raise PDDLParseError(f"Expected (problem <name>) header, got: {header!r}")
        problem_name = header[1]

        domain_name: Optional[str] = None
        objects: List[TypedSymbol] = []
        init: List[Atom] = []
        goal = None
        agents: List[str] = []

        for sec in sections:
            if not isinstance(sec, list) or not sec:
                continue
            head = sec[0]
            if not isinstance(head, str):
                continue
            head_lower = head.lower()

            if head_lower == ":domain":
                if len(sec) < 2 or not isinstance(sec[1], str):
                    raise PDDLParseError(f"Invalid :domain section: {sec!r}")
                domain_name = sec[1]
            elif head_lower == ":objects":
                objects.extend(self._parse_objects(sec[1:]))
            elif head_lower == ":init":
                init.extend(self._parse_init(sec[1:]))
            elif head_lower == ":goal":
                if len(sec) != 2:
                    # (:goal (and ...)) を想定
                    if len(sec) < 2:
                        raise PDDLParseError(f"Invalid :goal section: {sec!r}")
                    goal_sexp = ["and"] + sec[1:]
                else:
                    goal_sexp = sec[1]
                goal = sexp_to_formula(goal_sexp)
            elif head_lower == ":agents":
                agents = self._parse_agents(sec[1:])
            else:
                # MA-PDDL の :shared-data など、当面は無視
                continue

        if domain_name is None:
            raise PDDLParseError("Problem file missing :domain section")

        # :agents が無ければ objects から推論
        if not agents:
            agents = self._infer_agents_from_objects(objects)

        return ProblemAST(
            name=problem_name,
            domain_name=domain_name,
            objects=objects,
            init=init,
            goal=goal,
            agents=agents,
        )

    # ------------------------------------------------------------------ #
    # internal helpers
    # ------------------------------------------------------------------ #

    def _find_define(self) -> SExp:
        for sexp in self.sexps:
            if isinstance(sexp, list) and sexp and sexp[0] == "define":
                return sexp
        raise PDDLParseError("No (define ...) found in problem file.")

    def _parse_objects(self, items: List[SExp]) -> List[TypedSymbol]:
        """
        (:objects o1 o2 - t1 o3 - t2 ...) の部分を処理。
        """
        result: List[TypedSymbol] = []
        i = 0
        while i < len(items):
            token = items[i]
            if not isinstance(token, str):
                raise PDDLParseError(f"Expected object name, got {token!r}")
            if token == "-":
                raise PDDLParseError("Unexpected '-' in objects list")

            name = token
            ttype: str | None = None

            if i + 2 <= len(items) - 1 and isinstance(items[i + 1], str) and items[i + 1] == "-":
                type_name = items[i + 2]
                if not isinstance(type_name, str):
                    raise PDDLParseError(f"Expected type name in objects list, got {type_name!r}")
                ttype = type_name
                i += 3
            else:
                i += 1

            result.append(TypedSymbol(name=name, type=ttype))
        return result

    def _parse_init(self, items: List[SExp]) -> List[Atom]:
        """
        (:init f1 f2 ...) の fi を Atom としてパース。
        numeric (= (fuel r1) 0) や increase/decrease 等は無視する。
        """
        atoms: List[Atom] = []
        for s in items:
            if isinstance(s, list) and s:
                head = s[0]
                if isinstance(head, str) and head in ("=", "increase", "decrease", "assign"):
                    # numeric 系はスキップ
                    continue
                if isinstance(head, str) and head.lower() == "and":
                    for sub in s[1:]:
                        atoms.append(sexp_to_atom(sub))
                else:
                    atoms.append(sexp_to_atom(s))
            else:
                # シンボル単体は基本出てこないが、出たら無視かエラーでもよい
                continue
        return atoms

    def _parse_agents(self, items: List[SExp]) -> List[str]:
        """
        (:agents a1 a2 ...) から agent 名のリストを抽出。
        """
        result: List[str] = []
        for s in items:
            if isinstance(s, str):
                result.append(s)
        return result

    def _infer_agents_from_objects(self, objects: List[TypedSymbol]) -> List[str]:
        """
        :agents が無い場合、objects の中から type == 'agent' のものを agent とみなす。
        """
        agents: List[str] = []
        for obj in objects:
            if obj.type and obj.type.lower() == "agent":
                agents.append(obj.name)
        return agents
