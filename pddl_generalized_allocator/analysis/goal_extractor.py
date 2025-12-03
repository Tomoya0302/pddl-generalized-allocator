from __future__ import annotations

from typing import List

from pddl_generalized_allocator.model.types import PlanningTask, GroundAtom, _ground_atom_from_ast
from pddl_generalized_allocator.model.ma_types import MultiAgentTask
from pddl_generalized_allocator.pddl.ast import Formula, Atom, And, Not


def extract_goal_atoms(ma_task: MultiAgentTask) -> List[GroundAtom]:
    """
    MultiAgentTask から「正のゴール命題」の GroundAtom リストを抽出する。

    - goal が None の場合は空リスト。
    - (and ...) の中に現れる Atom を集める。
    - (not (p ...)) の下にある Atom は無視（制約扱い）する。
    """
    task: PlanningTask = ma_task.planning_task
    if task.goal is None:
        return []

    atoms: list[Atom] = []
    _collect_positive_atoms(task.goal, atoms, negated=False)

    ground_atoms: list[GroundAtom] = []
    for a in atoms:
        ga = _ground_atom_from_ast(a, task.objects, task.predicates)
        ground_atoms.append(ga)
    return ground_atoms


def _collect_positive_atoms(formula: Formula, out: list[Atom], negated: bool) -> None:
    """
    再帰的に Formula をたどり、negated=False の位置にある Atom を out に追加する。

    - And(children): 各 child を同じ negated フラグで再帰。
    - Not(child): negated フラグを反転させて再帰。
    - Atom: negated=False のときのみ out に追加。
    """
    if isinstance(formula, Atom):
        if not negated:
            out.append(formula)
        return

    if isinstance(formula, And):
        for ch in formula.children:
            _collect_positive_atoms(ch, out, negated=negated)
        return

    if isinstance(formula, Not):
        _collect_positive_atoms(formula.child, out, negated=not negated)
        return

    # 未知の式種別は無視（本実装では Atom/And/Not しか出てこない想定）
    return
