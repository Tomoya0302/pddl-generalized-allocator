from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Set

from pddl_generalized_allocator.model.types import PlanningTask
from pddl_generalized_allocator.pddl.ast import Formula, Atom, And, Not, Effect


@dataclass
class CausalGraph:
    """
    述語レベルの簡易因果グラフ。

    - edges_out[p] = { q1, q2, ... }  : 「述語 p は q に影響を与える」
    - edges_in[q]  = { p1, p2, ... }  : 逆向きの辺
    """
    edges_out: Dict[str, Set[str]]
    edges_in: Dict[str, Set[str]]


def build_causal_graph(task: PlanningTask) -> CausalGraph:
    """
    PlanningTask から簡易因果グラフを構築する。

    アルゴリズム:
      - 各アクション a について：
        * precond に現れる全ての述語名の集合 P
        * effect.add に現れる全ての述語名の集合 E
      - P の各 p と E の各 e について、エッジ p -> e を張る。
    """
    edges_out: Dict[str, Set[str]] = {}
    edges_in: Dict[str, Set[str]] = {}

    def ensure_node(pred_name: str) -> None:
        if pred_name not in edges_out:
            edges_out[pred_name] = set()
        if pred_name not in edges_in:
            edges_in[pred_name] = set()

    for action in task.actions.values():
        pre_preds = _predicates_in_formula(action.precondition)
        eff_preds = _predicates_in_effect(action.effect)

        for p in pre_preds:
            ensure_node(p)
        for e in eff_preds:
            ensure_node(e)

        for p in pre_preds:
            for e in eff_preds:
                edges_out[p].add(e)
                edges_in[e].add(p)

    return CausalGraph(edges_out=edges_out, edges_in=edges_in)


# ---------------------------------------------------------------------------
# 補助: Formula / Effect 内の述語名収集
# ---------------------------------------------------------------------------


def _predicates_in_formula(formula: Formula | None) -> Set[str]:
    names: Set[str] = set()
    if formula is None:
        return names

    def visit(f: Formula) -> None:
        if isinstance(f, Atom):
            names.add(f.name)
        elif isinstance(f, And):
            for ch in f.children:
                visit(ch)
        elif isinstance(f, Not):
            visit(f.child)
        else:
            # 想定外の式種別は無視
            return

    visit(formula)
    return names


def _predicates_in_effect(effect: Effect) -> Set[str]:
    names: Set[str] = set()
    # add / delete 両方を見るが、因果グラフとしては add 中心と考えてもよい。
    for atom in effect.add:
        names.add(atom.name)
    for atom in effect.delete:
        names.add(atom.name)
    return names
