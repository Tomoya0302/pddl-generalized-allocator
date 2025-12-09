from dataclasses import dataclass
from typing import Dict, List
from ..planning.task import PlanningTask

@dataclass
class Agent:
    name: str
    type_name: str

@dataclass
class MultiAgentTask:
    planning_task: PlanningTask
    agents: Dict[str, Agent]  # name -> Agent

def extract_agents(task: PlanningTask, agent_types: List[str]) -> Dict[str, Agent]:
    """
    - PDDLのobjectsから、typeがagent_typesのものをAgentとみなす。
    - agent.name = object name, agent.type_name = object type
    """
    agents = {}
    
    for agent_type in agent_types:
        objects_of_type = task.objects.get_objects(agent_type)
        for obj_name in objects_of_type:
            agent = Agent(name=obj_name, type_name=agent_type)
            agents[obj_name] = agent
    
    return agents