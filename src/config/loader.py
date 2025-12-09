import yaml
from .schema import (
    PlannerConfig, PDDLConfig, RolesConfigRef, ClusteringConfig,
    MultiAgentConfig, AllocationConfig
)

def load_config(path: str) -> PlannerConfig:
    """YAML設定ファイルを読み込んでPlannerConfigを返す"""
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    
    # 必須項目のチェック＆デフォルト埋め
    pddl_data = raw.get("pddl", {})
    roles_data = raw.get("roles", {})
    clustering_data = raw.get("clustering", {})
    multiagent_data = raw.get("multiagent", {})
    allocation_data = raw.get("allocation", {})
    
    return PlannerConfig(
        pddl=PDDLConfig(
            domain_file=pddl_data.get("domain_file", "data/domain.pddl"),
            problem_file=pddl_data.get("problem_file", "data/problem.pddl"),
            multiagent_extension=pddl_data.get("multiagent_extension")
        ),
        roles=RolesConfigRef(
            role_config_file=roles_data.get("role_config_file", "configs/role_configs/example_roles.json"),
            on_missing_role=roles_data.get("on_missing_role", "error")
        ),
        clustering=ClusteringConfig(
            use_landmarks=clustering_data.get("use_landmarks", True),
            landmark_max_depth=clustering_data.get("landmark_max_depth", 3),
            max_cluster_size=clustering_data.get("max_cluster_size", 10),
            max_subtasks=clustering_data.get("max_subtasks", 30),
            epsilon_start=clustering_data.get("epsilon_start", 0.0),
            epsilon_step=clustering_data.get("epsilon_step", 0.2),
            max_retries=clustering_data.get("max_retries", 5),
            random_seed=clustering_data.get("random_seed", 42),
            merge_compatible_subtasks=clustering_data.get("merge_compatible_subtasks", True),
            max_goals_per_subtask=clustering_data.get("max_goals_per_subtask", 10)
        ),
        multiagent=MultiAgentConfig(
            agent_types=multiagent_data.get("agent_types", ["agent"]),
            capability_mode=multiagent_data.get("capability_mode", "parameter-type")
        ),
        allocation=AllocationConfig(
            cost_function=allocation_data.get("cost_function", "inverse_capability_size")
        )
    )