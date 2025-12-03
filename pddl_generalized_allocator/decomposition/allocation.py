from __future__ import annotations

from dataclasses import dataclass
from typing import List
import random

from pddl_generalized_allocator.model.types import PlanningTask, ActionSchema
from pddl_generalized_allocator.model.ma_types import MultiAgentTask, Agent
from pddl_generalized_allocator.decomposition.subtasks import SubTask, DecompositionResult
from pddl_generalized_allocator.analysis.causal_graph import (
    _predicates_in_formula,
    _predicates_in_effect,
)


@dataclass
class Assignment:
    """
    1つのサブタスクに対する 1 エージェントの割当と、そのコスト。
    """
    subtask: SubTask
    agent: Agent
    cost: float


@dataclass
class AllocationPlan:
    """
    サブタスク→エージェント割当の 1 パターン。
    """
    assignments: List[Assignment]


def compute_allocation_plan(
    ma_task: MultiAgentTask,
    decomp: DecompositionResult,
) -> AllocationPlan:
    """
    サブタスク→エージェント割当を 1 パターン決める。

    アルゴリズム:
      - 各 SubTask について：
          * 全エージェントに対して estimate_cost を計算
          * 最小コストのエージェント候補リストを集める
          * その中からランダムに1人選択（ランダムシードは上位で設定済み）
    """
    planning_task: PlanningTask = ma_task.planning_task
    assignments: List[Assignment] = []

    for subtask in decomp.subtasks:
        best_cost = float("inf")
        best_agents: List[Agent] = []

        for agent in ma_task.agents:
            c = _estimate_cost(
                subtask=subtask,
                agent=agent,
                planning_task=planning_task,
                ma_task=ma_task,
            )
            if c < best_cost:
                best_cost = c
                best_agents = [agent]
            elif c == best_cost:
                best_agents.append(agent)

        # 候補があればその中からランダムに選ぶ
        if best_agents:
            chosen_agent = random.choice(best_agents)
        else:
            # すべて同じ超ペナルティ等で best_agents が空…は基本ないが、一応 fallback
            if ma_task.agents:
                chosen_agent = random.choice(ma_task.agents)
                best_cost = float("inf")
            else:
                chosen_agent = None
                best_cost = float("inf")

        assignments.append(
            Assignment(
                subtask=subtask,
                agent=chosen_agent,
                cost=best_cost,
            )
        )

    return AllocationPlan(assignments=assignments)


def _estimate_cost(
    subtask: SubTask,
    agent: Agent,
    planning_task: PlanningTask,
    ma_task: MultiAgentTask,
) -> float:
    """
    単純なコスト関数:

      - agent が実行可能なアクション集合のうち、
        subtask.involved_predicates と関連する述語を含むアクション数を数える。
      - relevant_actions > 0 なら cost = 1.0 / relevant_actions
      - そうでなければ大きなペナルティ値を返す。
    """
    caps = ma_task.capabilities.get(agent.name)
    if caps is None or not caps.actions:
        return 1e9  # 実行可能アクションなし

    relevant_actions = 0
    for action_name in caps.actions:
        action: ActionSchema = planning_task.actions[action_name]
        preds = set()
        preds |= _predicates_in_formula(action.precondition)
        preds |= _predicates_in_effect(action.effect)
        if preds & subtask.involved_predicates:
            relevant_actions += 1

    if relevant_actions == 0:
        return 1e8

    return 1.0 / float(relevant_actions)
