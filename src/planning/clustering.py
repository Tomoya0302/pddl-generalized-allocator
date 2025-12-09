from typing import List, Set, Dict
from .task import GroundAtom, PlanningTask
from .goal_graph import GoalGraph, build_goal_graph
from .causal_graph import build_causal_graph
from .landmarks import compute_landmarks
from .roles import load_domain_role_config, extract_roles_for_goals
from .subtasks import finer_partition_by_roles, merge_compatible_subtasks, advanced_merge_subtasks, SubTask
from .constraint_aware_merge import constraint_aware_merge_subtasks
from .multi_objective_merge import multi_objective_merge_subtasks
from ..config.schema import ClusteringConfig, RolesConfigRef
from ..utils.random_utils import RandomState

def connected_components(goal_graph: GoalGraph) -> List[Set[GroundAtom]]:
    """
    通常のDFS/BFSで連結成分を列挙。
    """
    visited = set()
    components = []
    
    for goal in goal_graph.keys():
        if goal not in visited:
            component = set()
            _dfs_component(goal_graph, goal, visited, component)
            if component:
                components.append(component)
    
    return components

def _dfs_component(goal_graph: GoalGraph, start: GroundAtom, visited: Set[GroundAtom], component: Set[GroundAtom]):
    """DFSで連結成分を探索"""
    if start in visited:
        return
    
    visited.add(start)
    component.add(start)
    
    for neighbor in goal_graph.get(start, set()):
        _dfs_component(goal_graph, neighbor, visited, component)

def split_large_cluster(cluster: List[GroundAtom],
                        max_size: int,
                        rng: RandomState,
                        epsilon: float,
                        use_structure_order: bool) -> List[List[GroundAtom]]:
    """
    Step 7:
    - cluster は「構造順」に並んだゴールのリスト（例: BFS で順序をつける）
    - ε-greedy:
      - with prob 1 - ε: 構造順のままスライス (size <= max_size)
      - with prob ε: cluster を rng.shuffle してからスライス
    """
    if len(cluster) <= max_size:
        return [cluster]
    
    # ε-greedy: ランダム性の制御
    cluster_copy = cluster.copy()
    if rng.random() < epsilon:
        # ランダムシャッフル
        rng.shuffle(cluster_copy)
    # else: 構造順を維持
    
    # max_sizeずつに分割
    result = []
    for i in range(0, len(cluster_copy), max_size):
        chunk = cluster_copy[i:i + max_size]
        result.append(chunk)
    
    return result

def build_subtasks_with_retry(task: PlanningTask,
                              cfg_cluster: ClusteringConfig,
                              roles_ref: RolesConfigRef,
                              rng: RandomState) -> List[SubTask]:
    """
    e-greedy でStep 7〜9 を再試行しながらmax_subtasks制約を満たすSubTaskの集合を作る。
    """
    role_cfg = load_domain_role_config(roles_ref.role_config_file)
    cg = build_causal_graph(task)
    landmarks = compute_landmarks(task, cg, cfg_cluster.landmark_max_depth) \
                if cfg_cluster.use_landmarks else {g: set() for g in task.goals}

    epsilon = cfg_cluster.epsilon_start
    for retry in range(cfg_cluster.max_retries + 1):
        # Step 5: goal graph
        goal_graph = build_goal_graph(task.goals, cg, landmarks if cfg_cluster.use_landmarks else None)

        # Step 6-7: first level clustering + size limit
        struct_clusters = connected_components(goal_graph)
        clusters = []
        for comp in struct_clusters:
            goals_list = list(comp)
            clusters.extend(
                split_large_cluster(goals_list,
                                    cfg_cluster.max_cluster_size,
                                    rng, epsilon,
                                    use_structure_order=True)
            )

        # Step 8: role extraction
        role_assignments = extract_roles_for_goals(
            task, role_cfg, task.goals, roles_ref.on_missing_role
        )

        # Step 9: role-based finer partition
        subtasks = finer_partition_by_roles(
            clusters, role_assignments, role_cfg, landmarks
        )
        print(f"Debug: After role-based partition: {len(subtasks)} subtasks")

        # Step 9.5: 制約考慮型サブタスク統合（オプション）
        if cfg_cluster.merge_compatible_subtasks:
            original_count = len(subtasks)
            
            # ドメイン汎化された制約設定を作成
            constraint_config = {
                'binary_constraints': cfg_cluster.constraint_binary_predicates or ['reachable'],
                'type_constraints': cfg_cluster.constraint_type_predicates or ['weld_type'],
                'goal_object_index': cfg_cluster.constraint_goal_object_index
            }
            
            # 制約考慮型統合を使用
            subtasks = constraint_aware_merge_subtasks(
                subtasks,
                task,  # 制約情報を含むタスクを渡す
                cfg_cluster.max_goals_per_subtask,
                cfg_cluster.max_subtasks,  # 目標サブタスク数
                constraint_config
            )
            print(f"Debug: After constraint-aware merging: {len(subtasks)} subtasks (was {original_count})")

        if len(subtasks) <= cfg_cluster.max_subtasks:
            return subtasks

        # e-greedy: ε を増やし、よりランダムな分割を許す
        epsilon = min(1.0, epsilon + cfg_cluster.epsilon_step)

    # ここまで来たら UNSAT
    raise RuntimeError(
        f"Cannot satisfy max_subtasks={cfg_cluster.max_subtasks} "
        f"even after {cfg_cluster.max_retries} retries."
    )

def first_level_clustering(goals: Set[GroundAtom],
                           goal_graph: GoalGraph,
                           cfg: ClusteringConfig,
                           rng: RandomState,
                           epsilon: float) -> List[List[GroundAtom]]:
    """
    1. connected_componentsでクラスタC1, C2, ...
    2. 各CをMax_cluster_sizeに従ってsplit_large_cluster
    3. 返り値: List[ List[GroundAtom] ]
    """
    # 1. 連結成分を取得
    components = connected_components(goal_graph)
    
    # 2. 各連結成分を最大サイズで分割
    result = []
    for component in components:
        goals_list = list(component)
        split_clusters = split_large_cluster(
            goals_list,
            cfg.max_cluster_size,
            rng,
            epsilon,
            use_structure_order=True
        )
        result.extend(split_clusters)
    
    return result