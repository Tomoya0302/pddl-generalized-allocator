from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Union

from pddl_generalized_allocator.utils.errors import PDDLParseError
from pddl_generalized_allocator.pddl.sexp_parser import SExp


# --- 基本的なシンボル／述語／アクション宣言 AST ------------------------------------


@dataclass
class TypedSymbol:
    name: str
    type: Optional[str]  # None の場合は型なし


@dataclass
class PredicateDecl:
    name: str
    parameters: List[TypedSymbol]


@dataclass
class Atom:
    """
    変数 or オブジェクトを引数に取る一階の原子述語。
    """
    name: str
    args: List[str]  # парамет名 or オブジェクト名


@dataclass
class Not:
    child: "Formula"


@dataclass
class And:
    children: List["Formula"]


Formula = Union[Atom, Not, And]


@dataclass
class Effect:
    """
    delete-add リスト表現の簡易エフェクト。
    """
    add: List[Atom]
    delete: List[Atom]


@dataclass
class ActionDecl:
    name: str
    parameters: List[TypedSymbol]
    precondition: Optional[Formula]
    effect: Effect


@dataclass
class DomainAST:
    name: str
    requirements: List[str]
    types: List[str]
    predicates: List[PredicateDecl]
    actions: List[ActionDecl]


@dataclass
class ProblemAST:
    name: str
    domain_name: str
    objects: List[TypedSymbol]
    init: List[Atom]
    goal: Optional[Formula]
    agents: List[str]  # MA-PDDL の :agents、なければ推論した agent 名


# --- S 式 → 式 AST 変換ユーティリティ -------------------------------------------


def sexp_to_atom(sexp: SExp) -> Atom:
    """
    S 式 [pred arg1 arg2 ...] を Atom に変換する。
    """
    if not isinstance(sexp, list) or len(sexp) == 0:
        raise PDDLParseError(f"Expected list for atom, got: {sexp!r}")
    head = sexp[0]
    if not isinstance(head, str):
        raise PDDLParseError(f"Expected predicate symbol, got: {head!r}")
    args = []
    for a in sexp[1:]:
        if not isinstance(a, str):
            raise PDDLParseError(f"Atom argument must be symbol string, got: {a!r}")
        args.append(a)
    return Atom(name=head, args=args)


def sexp_to_formula(sexp: SExp) -> Formula:
    """
    :precondition や :goal などに使う論理式の S 式から Formula への変換。
    対応:
        - (and φ1 φ2 ...)
        - (not φ)
        - 原子 (p x y)
    それ以外（or, implies, forall, exists 等）は PDDLParseError にする。
    """
    if isinstance(sexp, str):
        # 単独シンボルは扱わない（PDDL 的にはほとんど出てこないはず）
        raise PDDLParseError(f"Unexpected bare symbol in formula: {sexp!r}")

    if len(sexp) == 0:
        # 空 and は true とみなせるが、ここでは空の And として表現
        return And(children=[])

    head, *rest = sexp
    if not isinstance(head, str):
        raise PDDLParseError(f"Invalid formula head: {head!r}")

    head_lower = head.lower()

    if head_lower == "and":
        children = [sexp_to_formula(s) for s in rest]
        return And(children=children)

    if head_lower == "not":
        if len(rest) != 1:
            raise PDDLParseError(f"(not φ) must have exactly 1 child, got: {len(rest)}")
        return Not(child=sexp_to_formula(rest[0]))

    # それ以外は原子として扱う
    return sexp_to_atom(sexp)


def sexp_to_effect(sexp: SExp) -> Effect:
    """
    :effect の S 式を Effect(add/delete) に変換する。
    対応:
        - 単独の (p x y)
        - 単独の (not (p x y))
        - (and e1 e2 ...) で e_i が上記の組み合わせ
    """
    add: List[Atom] = []
    delete: List[Atom] = []

    def handle(expr: SExp) -> None:
        if isinstance(expr, list) and expr:
            head = expr[0]
            if isinstance(head, str) and head.lower() == "and":
                for sub in expr[1:]:
                    handle(sub)
            elif isinstance(head, str) and head.lower() == "not":
                if len(expr) != 2:
                    raise PDDLParseError(f"Unsupported (not ...) in effect: {expr!r}")
                delete.append(sexp_to_atom(expr[1]))
            else:
                # 原子として扱う
                add.append(sexp_to_atom(expr))
        else:
            raise PDDLParseError(f"Unsupported effect expression: {expr!r}")

    handle(sexp)
    return Effect(add=add, delete=delete)
