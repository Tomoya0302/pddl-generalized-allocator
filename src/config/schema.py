from dataclasses import dataclass
from typing import List, Optional

@dataclass
class PDDLConfig:
    domain_file: str
    problem_file: str
    multiagent_extension: Optional[str]

@dataclass
class RolesConfigRef:
    role_config_file: str
    on_missing_role: str  # "error" or "skip_goal"

@dataclass
class ClusteringConfig:
    use_landmarks: bool
    landmark_max_depth: int
    max_cluster_size: int
    max_subtasks: int
    epsilon_start: float
    epsilon_step: float
    max_retries: int
    random_seed: int
    solution_timeout: int = 120  # 各解の生成タイムアウト（秒）
    # サブタスク統合の設定
    merge_compatible_subtasks: bool = True
    max_goals_per_subtask: int = 10
    # 制約考慮型統合の設定
    constraint_binary_predicates: Optional[List[str]] = None    # バイナリ制約述語
    constraint_type_predicates: Optional[List[str]] = None      # タイプ制約述語
    constraint_goal_object_index: int = 0                       # ゴール引数のターゲットオブジェクトインデックス
    # 多目的最適化戦略
    optimization_strategy: Optional[str] = None                 # "minimize_subtasks" | "balanced" | "distribute_goals" | "auto"
    strategy_randomness: float = 0.1                           # 戦略のランダム性 [0.0-1.0]

@dataclass
class MultiAgentConfig:
    agent_types: List[str]
    capability_mode: str

@dataclass
class AllocationConfig:
    cost_function: str

@dataclass
class PlannerConfig:
    pddl: PDDLConfig
    roles: RolesConfigRef
    clustering: ClusteringConfig
    multiagent: MultiAgentConfig
    allocation: AllocationConfig