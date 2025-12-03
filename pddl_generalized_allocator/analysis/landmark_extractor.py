from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Set

from pddl_generalized_allocator.model.types import PlanningTask, Predicate
from pddl_generalized_allocator.model.ma_types import MultiAgentTask
from pddl_generalized_allocator.analysis.causal_graph import CausalGraph


@dataclass
class Landmark:
    """
    シンプルな fact landmark 表現。
    ここでは「述語シンボル」レベルでのみ扱う。
    """
    predicate: Predicate


def compute_landmarks(
    task: PlanningTask,
    cg: CausalGraph,
    goals: List["pddl_generalized_allocator.model.types.GroundAtom"],
    depth_limit: int = 2,
) -> List[Landmark]:
    """
    ゴール命題と因果グラフから近似ランドマーク集合を計算する。

    戦略:
      1. まずゴール命題に現れる述語名を landmark 候補とする。
      2. 因果グラフを逆向き（edges_in）に BFS し、
         最大 depth_limit ステップだけ predecessor 述語を追加する。

    注意:
      - ここでは「述語レベルのランドマーク」しか扱っていない。
      - 実際の fact landmark（ground 命題）ではないが、タスク分解用の粗い手がかりとしては十分。
    """
    # 1. ゴール述語名
    lm_pred_names: Set[str] = set()
    for g in goals:
        lm_pred_names.add(g.predicate.name)

    # 2. 逆向き BFS
    visited: Set[str] = set(lm_pred_names)
    frontier: Set[str] = set(lm_pred_names)

    for _depth in range(depth_limit):
        if not frontier:
            break
        next_frontier: Set[str] = set()
        for pred_name in frontier:
            parents = cg.edges_in.get(pred_name, set())
            for p in parents:
                if p not in visited:
                    visited.add(p)
                    lm_pred_names.add(p)
                    next_frontier.add(p)
        frontier = next_frontier

    # 3. Predicate オブジェクトに変換
    landmarks: List[Landmark] = []
    for name in lm_pred_names:
        if name in task.predicates:
            landmarks.append(Landmark(predicate=task.predicates[name]))
        else:
            # 因果グラフの構築上、基本ここには来ない想定だが、念のためスキップ。
            continue

    return landmarks
