from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Set

from pddl_generalized_allocator.model.types import PlanningTask


@dataclass
class Agent:
    """
    マルチエージェント計画におけるエージェント。

    name は問題ファイルの :agents セクション、または
    :objects 中の agent 型オブジェクト名と一致する想定。
    """
    name: str


@dataclass
class AgentCapabilities:
    """
    エージェントが実行可能なアクション名の集合。
    """
    agent: Agent
    actions: Set[str]


@dataclass
class MultiAgentTask:
    """
    マルチエージェント版の計画タスク。

    - planning_task: 単一エージェント視点の PlanningTask
    - agents: 参加エージェント
    - capabilities: agent_name -> そのエージェントが実行可能なアクション集合
    """
    planning_task: PlanningTask
    agents: List[Agent]
    capabilities: Dict[str, AgentCapabilities]
