from typing import Dict, List
from .subtasks import SubTask
from .roles import DomainRoleConfig, extract_agent_roles
from .task import PlanningTask
from ..multiagent.capabilities import AgentCapabilities

SubtaskAssignment = Dict[int, str]  # SubTask.id -> agent_name

def can_execute_subtask(subtask: SubTask,
                        agent_name: str,
                        agent_roles: Dict[str, Dict[str, str]]) -> bool:
    """
    エージェントがサブタスクを実行できるかチェック。
    サブタスクのrole_signatureとエージェントのrole値を照合。
    複合的なrole_signature（'value1|value2'形式）もサポート。
    """
    if agent_name not in agent_roles:
        return True  # agent_role_extractorsが未定義の場合は制約なし
    
    agent_role_values = agent_roles[agent_name]
    
    # サブタスクが要求する各役割について、エージェントが対応可能かチェック
    for role_key, required_value in subtask.role_signature.items():
        if role_key not in agent_role_values:
            continue  # エージェントがこの役割を持たない場合はスキップ
            
        agent_value = agent_role_values[role_key]
        
        # 複合的なrequired_value（'value1|value2'形式）をチェック
        if '|' in required_value:
            # 複合値を分解して、エージェントの値がいずれかにマッチするかチェック
            possible_values = required_value.split('|')
            if agent_value not in possible_values:
                return False
        else:
            # 単純値の場合は完全一致
            if agent_value != required_value:
                return False
    
    return True

def compute_cost(subtask: SubTask,
                 agent_name: str,
                 capabilities: AgentCapabilities,
                 agent_roles: Dict[str, Dict[str, str]],
                 mode: str = "inverse_capability_size") -> float:
    """
    cost(T_i, λ) を計算する。
    - 制約違反の場合は無限大を返す
    - inverse_capability_size:
        cost = 1 / (1 + |Capabilities(λ)|)
      （専門性が高いほどcostが小さくなる）
    """
    # 制約チェック
    if not can_execute_subtask(subtask, agent_name, agent_roles):
        return float('inf')
    
    if mode == "inverse_capability_size":
        capability_size = len(capabilities.get(agent_name, set()))
        return 1.0 / (1.0 + capability_size)
    else:
        # 他のコスト関数を追加する余地
        raise NotImplementedError(f"Cost function '{mode}' is not implemented")

def allocate_subtasks(subtasks: List[SubTask],
                      capabilities: AgentCapabilities,
                      task: PlanningTask,
                      role_config: DomainRoleConfig,
                      cost_mode: str) -> SubtaskAssignment:
    """
    各サブタスクT_iに対し:
      Λ_i* = argmin_λ cost(T_i, λ)
      α(T_i) はΛ_i* から一様ランダム選択（決定論にしたければ最小のagent_nameを選ぶ等）

    擬似コード:
      assignment = {}
      for T in subtasks:
          best_cost = +inf; best_agents = []
          for λ in capabilities.keys():
              c = compute_cost(T, λ, capabilities, cost_mode)
              if c < best_cost:
                  best_cost = c
                  best_agents = [λ]
              elif c == best_cost:
                  best_agents.append(λ)
          chosen = deterministic_choice(best_agents)
          assignment[T.id] = chosen
      return assignment
    """
    # 全エージェントの役割値を抽出
    agent_roles = {}
    for agent_name in capabilities.keys():
        agent_roles[agent_name] = extract_agent_roles(task, agent_name, role_config)
    
    assignment = {}
    
    for subtask in subtasks:
        best_cost = float('inf')
        best_agents = []
        
        for agent_name in capabilities.keys():
            cost = compute_cost(subtask, agent_name, capabilities, agent_roles, cost_mode)
            if cost < best_cost:
                best_cost = cost
                best_agents = [agent_name]
            elif cost == best_cost and cost != float('inf'):
                best_agents.append(agent_name)
        
        if best_agents:
            # 決定論的選択（最小の名前を選択）
            chosen = min(best_agents)
            assignment[subtask.id] = chosen
        else:
            raise RuntimeError(f"No agents available for subtask {subtask.id} with role_signature {subtask.role_signature}")
    
    return assignment