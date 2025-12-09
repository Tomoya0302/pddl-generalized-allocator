from typing import Dict, Set, List
from .task import GroundAtom
from .causal_graph import CausalGraph

GoalGraph = Dict[GroundAtom, Set[GroundAtom]]

def build_goal_graph(goals: Set[GroundAtom],
                     cg: CausalGraph,
                     landmarks: Dict[GroundAtom, Set[str]] | None) -> GoalGraph:
    """
    無向グラフΓ = (G, E)
    - 同じ述語
    - 因果グラフ上で直接依存 (pred_i -> pred_j or pred_j -> pred_i)
    - ランドマーク集合が重なる (オプション)

    擬似コード:
      goal_list = list(goals)
      γ = {g: set() for g in goal_list}
      for i in range(len(goal_list)):
        for j in range(i+1, len(goal_list)):
          gi, gj = goal_list[i], goal_list[j]
          pi, pj = gi.predicate, gj.predicate
          cond1 = (pi == pj)
          cond2 = (pj in cg.get(pi, set()) or pi in cg.get(pj, set()))
          cond3 = False
          if landmarks is not None:
            cond3 = bool(landmarks[gi] & landmarks[gj])
          if cond1 or cond2 or cond3:
            γ[gi].add(gj)
            γ[gj].add(gi)
      return γ
    """
    goal_list = list(goals)
    γ = {g: set() for g in goal_list}
    
    for i in range(len(goal_list)):
        for j in range(i + 1, len(goal_list)):
            gi, gj = goal_list[i], goal_list[j]
            pi, pj = gi.predicate, gj.predicate
            
            # 条件1: 同じ述語
            cond1 = (pi == pj)
            
            # 条件2: 因果的に直接依存
            cond2 = (pj in cg.get(pi, set()) or pi in cg.get(pj, set()))
            
            # 条件3: ランドマーク集合が重なる
            cond3 = False
            if landmarks is not None:
                landmarks_i = landmarks.get(gi, set())
                landmarks_j = landmarks.get(gj, set())
                cond3 = bool(landmarks_i & landmarks_j)
            
            if cond1 or cond2 or cond3:
                γ[gi].add(gj)
                γ[gj].add(gi)
    
    return γ