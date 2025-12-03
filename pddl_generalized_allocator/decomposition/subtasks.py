from __future__ import annotations

from dataclasses import dataclass
from typing import List, Set

from pddl_generalized_allocator.model.types import GroundAtom
from pddl_generalized_allocator.analysis.landmark_extractor import Landmark


@dataclass
class SubTask:
    """
    サブタスク:
      - 一部のゴール命題をまとめたもの
      - 関連ランドマークと述語集合を持つ
    """
    id: int
    goal_atoms: List[GroundAtom]
    related_landmarks: List[Landmark]
    involved_predicates: Set[str]


@dataclass
class DecompositionResult:
    """
    サブタスク分解の結果。
    """
    subtasks: List[SubTask]
