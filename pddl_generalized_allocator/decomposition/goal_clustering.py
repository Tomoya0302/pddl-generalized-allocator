from __future__ import annotations

from typing import Dict, List, Set

from pddl_generalized_allocator.model.types import PlanningTask, GroundAtom
from pddl_generalized_allocator.analysis.causal_graph import CausalGraph
from pddl_generalized_allocator.analysis.landmark_extractor import Landmark
from pddl_generalized_allocator.decomposition.subtasks import SubTask, DecompositionResult
from pddl_generalized_allocator.utils.graph import bfs_component


def cluster_goals_into_subtasks(
    task: PlanningTask,
    goals: List[GroundAtom],
    landmarks: List[Landmark],
    cg: CausalGraph,
    max_cluster_size: int = 3,
) -> DecompositionResult:
    """
    ゴール命題をグラフベースでクラスタリングし、SubTask の集合を作る。

    アルゴリズム（素朴版）:
      1. 各ゴール命題をノードとしてグラフを構築。
      2. 以下の条件を満たすペアにエッジを張る:
         - 同じ述語名を持つ
         - 因果グラフ上で 1-hop でつながる（pre→eff / eff→pre）
      3. グラフの連結成分をクラスターとみなす。
      4. クラスターが大きすぎる場合は max_cluster_size ごとにスライス分割。
    """
    n = len(goals)
    if n == 0:
        return DecompositionResult(subtasks=[])

    # 1. 隣接リストを構築
    adjacency: Dict[int, Set[int]] = {i: set() for i in range(n)}

    # 述語間の「近さ」を定義
    def predicates_adjacent(p1: str, p2: str) -> bool:
        if p1 == p2:
            return True
        # 因果グラフの 1-hop でつながっているか
        if p2 in cg.edges_out.get(p1, set()):
            return True
        if p1 in cg.edges_out.get(p2, set()):
            return True
        return False

    for i in range(n):
        for j in range(i + 1, n):
            p1 = goals[i].predicate.name
            p2 = goals[j].predicate.name
            if predicates_adjacent(p1, p2):
                adjacency[i].add(j)
                adjacency[j].add(i)

    # 2. 連結成分ごとにクラスターを構築
    visited: Set[int] = set()
    clusters: List[Set[int]] = []
    for i in range(n):
        if i in visited:
            continue
        comp = bfs_component(i, adjacency)
        visited |= comp
        clusters.append(comp)

    # 3. クラスターが大きすぎる場合は分割
    final_clusters: List[List[int]] = []
    for comp in clusters:
        idx_list = list(comp)
        if len(idx_list) <= max_cluster_size:
            final_clusters.append(idx_list)
        else:
            # 単純に max_cluster_size ごとにスライス
            for k in range(0, len(idx_list), max_cluster_size):
                final_clusters.append(idx_list[k : k + max_cluster_size])

    # 4. SubTask を構築
    subtasks: List[SubTask] = []
    for sid, indices in enumerate(final_clusters):
        g_atoms = [goals[k] for k in indices]
        involved_pred_names = _collect_predicates_for_cluster(g_atoms, landmarks)
        lm_for_cluster = [
            lm for lm in landmarks if lm.predicate.name in involved_pred_names
        ]
        subtasks.append(
            SubTask(
                id=sid,
                goal_atoms=g_atoms,
                related_landmarks=lm_for_cluster,
                involved_predicates=involved_pred_names,
            )
        )

    return DecompositionResult(subtasks=subtasks)


def _collect_predicates_for_cluster(
    goals: List[GroundAtom],
    landmarks: List[Landmark],
) -> Set[str]:
    """
    このクラスターに関連する述語名集合を収集する。

    - ゴールに直接現れる述語
    - ゴールと同じ述語名を持つランドマーク
    """
    names: Set[str] = {g.predicate.name for g in goals}
    for lm in landmarks:
        if lm.predicate.name in names:
            names.add(lm.predicate.name)
    return names
