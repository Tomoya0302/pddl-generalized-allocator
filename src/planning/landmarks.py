from typing import Dict, Set, List
from .task import PlanningTask, GroundAtom
from .causal_graph import CausalGraph

Landmarks = Dict[GroundAtom, Set[str]]  # goal -> set(predicate_names)

def compute_landmarks(task: PlanningTask,
                      cg: CausalGraph,
                      max_depth: int) -> Landmarks:
    """
    各ゴールgについて、そのpredicateから逆向きに深さmax_depthまでBFS。
    - ただしここでは「述語名」をランドマークとし、GroundAtomにはしない。
    """
    # 逆向きグラフを構築
    cg_rev = _build_reverse_graph(cg)
    
    lm = {}
    for g in task.goals:
        root = g.predicate
        visited = set([root])
        frontier = [root]
        depth = 0
        
        while depth < max_depth and frontier:
            new_frontier = []
            for q in frontier:
                parents = cg_rev.get(q, set())
                for p in parents:
                    if p not in visited:
                        visited.add(p)
                        new_frontier.append(p)
            frontier = new_frontier
            depth += 1
        
        # ルート自体は除外
        visited.discard(root)
        lm[g] = visited
    
    return lm

def _build_reverse_graph(cg: CausalGraph) -> CausalGraph:
    """因果グラフの逆向きグラフを構築"""
    cg_rev = {}
    
    # 全ノードを初期化
    for node in cg.keys():
        cg_rev[node] = set()
    
    # 逆向きエッジを追加
    for from_node, to_nodes in cg.items():
        for to_node in to_nodes:
            if to_node not in cg_rev:
                cg_rev[to_node] = set()
            cg_rev[to_node].add(from_node)
    
    return cg_rev