from typing import Dict, Set, List
from .agents import Agent
from ..planning.task import PlanningTask

AgentCapabilities = Dict[str, Set[str]]  # agent_name -> {action_name}

def compute_capabilities(task: PlanningTask,
                         agents: Dict[str, Agent],
                         agent_types: List[str]) -> AgentCapabilities:
    """
    Capabilities(λ) = { A | A のパラメータにagent_typesの型があり、
                          その型 == type(λ) } を満たすアクション名集合。

    擬似コード:
      caps = {agent_name: set() for ...}
      for each action in task.actions:
        for each parameter in action.parameters:
          if parameter.type in agent_types:
            for each agent a with a.type_name == parameter.type:
              caps[a.name].add(action.name)
      return caps
    """
    caps = {agent_name: set() for agent_name in agents.keys()}
    
    for action_name, action in task.actions.items():
        for param in action.parameters:
            if param.type in agent_types:
                # この型のエージェントすべてにこのアクションを追加
                for agent_name, agent in agents.items():
                    if agent.type_name == param.type:
                        caps[agent_name].add(action_name)
    
    return caps