from dataclasses import dataclass
from typing import Dict, Set, List
from ..pddl.ast import DomainAST, ProblemAST, Literal, ActionSchema
from ..pddl.types import TypeEnv
from ..pddl.static_analysis import compute_static_predicates

@dataclass(frozen=True)
class GroundAtom:
    predicate: str
    args: tuple[str, ...]

    def __str__(self):
        return f"{self.predicate}({', '.join(self.args)})"

@dataclass
class PlanningTask:
    objects: TypeEnv
    predicates: Dict[str, ...]      # PredicateSchema or簡易情報
    actions: Dict[str, ActionSchema]
    init: Set[GroundAtom]
    goals: Set[GroundAtom]
    static_predicates: Set[str]

    @staticmethod
    def from_ast(domain: DomainAST, problem: ProblemAST) -> "PlanningTask":
        """
        - TypeEnvを構築
        - init / goalsのLiteralからGroundAtomへ変換
        - static_predicatesをcompute_static_predicatesで計算
        """
        # TypeEnvを構築
        objects = TypeEnv()
        for obj_name, obj_type in problem.objects.items():
            objects.add_object(obj_name, obj_type)
        
        # init状態をGroundAtomに変換
        init_atoms = set()
        for literal in problem.init:
            if not literal.negated:  # 肯定リテラルのみ
                atom = GroundAtom(
                    predicate=literal.predicate,
                    args=tuple(literal.args)
                )
                init_atoms.add(atom)
        
        # ゴールをGroundAtomに変換
        goal_atoms = set()
        for literal in problem.goals:
            if not literal.negated:  # 肯定リテラルのみ
                atom = GroundAtom(
                    predicate=literal.predicate,
                    args=tuple(literal.args)
                )
                goal_atoms.add(atom)
        
        # 静的述語を計算
        static_predicates = compute_static_predicates(domain)
        
        return PlanningTask(
            objects=objects,
            predicates=domain.predicates,
            actions=domain.actions,
            init=init_atoms,
            goals=goal_atoms,
            static_predicates=static_predicates
        )