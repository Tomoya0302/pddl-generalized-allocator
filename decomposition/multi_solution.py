from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
import random

from pddl_generalized_allocator.model.ma_types import MultiAgentTask
from pddl_generalized_allocator.decomposition.subtasks import SubTask
from pddl_generalized_allocator.decomposition.goal_clustering import cluster_goals_into_subtasks
from pddl_generalized_allocator.decomposition.allocation import (
    AllocationPlan,
    compute_allocation_plan,
)
from pddl_generalized_allocator.analysis.goal_extractor import extract_goal_atoms
from pddl_generalized_allocator.analysis.causal_graph import build_causal_graph
from pddl_generalized_allocator.analysis.landmark_extractor import compute_landmarks


@dataclass
class DecompositionAllocationSolution:
    """
    1つの「分解＋割当」案。
    """
    subtasks: List[SubTask]
    allocation: AllocationPlan


def generate_multiple_solutions(
    ma_task: MultiAgentTask,
    num_solutions: int,
    random_seed: Optional[int] = None,
    max_num_subtasks: Optional[int] = None,
) -> List[DecompositionAllocationSolution]:
    """
    多様なタスク分解・割当案を生成する。

    多様性のためにランダムに変えるもの:
      - max_cluster_size
      - ランドマーク逆探索 depth_limit
    """
    if random_seed is not None:
        random.seed(random_seed)

    solutions: List[DecompositionAllocationSolution] = []

    planning_task = ma_task.planning_task

    # 因果グラフはタスクに対して固定
    cg = build_causal_graph(planning_task)
    # ゴール命題も固定
    goals = extract_goal_atoms(ma_task)

    for _ in range(num_solutions):
        # パラメータをランダムに変える
        max_cluster_size = random.choice([1, 2, 3, 4])
        depth_limit = random.choice([1, 2, 3])

        landmarks = compute_landmarks(
            planning_task,
            cg,
            goals,
            depth_limit=depth_limit,
        )

        decomp = cluster_goals_into_subtasks(
            planning_task,
            goals,
            landmarks,
            cg,
            max_cluster_size=max_cluster_size,
            max_num_subtasks=max_num_subtasks,
        )

        allocation = compute_allocation_plan(ma_task, decomp)

        solutions.append(
            DecompositionAllocationSolution(
                subtasks=decomp.subtasks,
                allocation=allocation,
            )
        )

    return solutions
