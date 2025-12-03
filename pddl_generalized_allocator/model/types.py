from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

from pddl_generalized_allocator.utils.errors import ModelBuildError
from pddl_generalized_allocator.pddl.ast import (
    TypedSymbol as AstTypedSymbol,
    PredicateDecl as AstPredicateDecl,
    ActionDecl as AstActionDecl,
    DomainAST,
    ProblemAST,
    Atom as AstAtom,
    Formula,
    Effect,
)


# ---------------------------------------------------------------------------
# 内部表現クラス
# ---------------------------------------------------------------------------


@dataclass
class Object:
    """
    問題インスタンス中のオブジェクト。
    """
    name: str
    type: Optional[str]  # 型なしの場合は None


@dataclass
class Predicate:
    """
    述語シンボル。引数の型情報を保持する。
    """
    name: str
    arg_types: List[Optional[str]]  # 各引数の型名（型なしは None）


@dataclass(frozen=True)
class GroundAtom:
    """
    ground な命題。構造解析で主に使う。
    """
    predicate: Predicate
    args: Tuple[Object, ...]

    def __str__(self) -> str:
        arg_str = " ".join(o.name for o in self.args)
        return f"({self.predicate.name} {arg_str})"


@dataclass
class Parameter:
    """
    アクションスキーマのパラメータ。
    """
    name: str
    type: Optional[str]


@dataclass
class ActionSchema:
    """
    PDDL の :action 宣言に対応する内部表現。
    precondition / effect は pddl.ast の Formula / Effect をそのまま保持する。
    """
    name: str
    parameters: List[Parameter]
    precondition: Optional[Formula]
    effect: Effect


@dataclass
class PlanningTask:
    """
    単一エージェント視点の「計画タスク」内部表現。
    （MultiAgentTask は別ファイルで定義予定）
    """
    domain_name: str
    objects: Dict[str, Object]              # オブジェクト名 -> Object
    predicates: Dict[str, Predicate]        # 述語名 -> Predicate
    actions: Dict[str, ActionSchema]        # アクション名 -> ActionSchema
    init: List[GroundAtom]                  # 初期状態の ground 命題
    goal: Optional[Formula]                 # ゴール式（Formula）


# ---------------------------------------------------------------------------
# DomainAST / ProblemAST -> PlanningTask 変換
# ---------------------------------------------------------------------------


def build_planning_task(domain_ast: DomainAST, problem_ast: ProblemAST) -> PlanningTask:
    """
    DomainAST / ProblemAST から PlanningTask を構築する。

    対応するのは STRIPS ベースの構文のみ（numeric / ADL はあらかじめ ProblemLoader 側で
    フィルタされている前提）。
    """
    if domain_ast.name != problem_ast.domain_name:
        raise ModelBuildError(
            f"Domain name mismatch: domain file '{domain_ast.name}' "
            f"vs problem file '{problem_ast.domain_name}'"
        )

    # 1. オブジェクト表
    objects_by_name: Dict[str, Object] = {}
    for obj in problem_ast.objects:
        if obj.name in objects_by_name:
            raise ModelBuildError(f"Duplicate object name: {obj.name}")
        objects_by_name[obj.name] = Object(name=obj.name, type=obj.type)

    # 2. 述語シンボル表
    predicates_by_name: Dict[str, Predicate] = {}
    for pdecl in domain_ast.predicates:
        if pdecl.name in predicates_by_name:
            raise ModelBuildError(f"Duplicate predicate name: {pdecl.name}")
        arg_types: List[Optional[str]] = []
        for param in pdecl.parameters:
            arg_types.append(param.type)
        predicates_by_name[pdecl.name] = Predicate(
            name=pdecl.name,
            arg_types=arg_types,
        )

    # 3. アクションスキーマ表
    actions_by_name: Dict[str, ActionSchema] = {}
    for adecl in domain_ast.actions:
        if adecl.name in actions_by_name:
            raise ModelBuildError(f"Duplicate action name: {adecl.name}")
        params: List[Parameter] = [
            Parameter(name=p.name, type=p.type) for p in adecl.parameters
        ]
        actions_by_name[adecl.name] = ActionSchema(
            name=adecl.name,
            parameters=params,
            precondition=adecl.precondition,
            effect=adecl.effect,
        )

    # 4. 初期状態 init（Atom AST -> GroundAtom）
    init_atoms: List[GroundAtom] = []
    for atom_ast in problem_ast.init:
        ga = _ground_atom_from_ast(atom_ast, objects_by_name, predicates_by_name)
        init_atoms.append(ga)

    # 5. ゴール式（Formula）は、構造解析で直接扱えるよう AST の Formula をそのまま保持
    goal_formula = problem_ast.goal

    return PlanningTask(
        domain_name=domain_ast.name,
        objects=objects_by_name,
        predicates=predicates_by_name,
        actions=actions_by_name,
        init=init_atoms,
        goal=goal_formula,
    )


# ---------------------------------------------------------------------------
# 補助関数
# ---------------------------------------------------------------------------

from pddl_generalized_allocator.utils.log import get_logger
logger = get_logger(__name__)

def _ground_atom_from_ast(
    atom_ast: AstAtom,
    objects_by_name: Dict[str, Object],
    predicates_by_name: Dict[str, Predicate],
) -> GroundAtom:
    """
    AST レベルの Atom を、内部表現 GroundAtom に変換する。

    以前は「述語引数の型とオブジェクトの型が一致しないと ModelBuildError」を
    投げていたが、Depot などの PDDL では type hierarchy
    （例: locatable のサブタイプ pallet）が存在するため、
    ここでは **厳密な一致チェックは行わない** 方針に変更する。

    - 述語名が未定義なら ModelBuildError
    - 引数数が一致しないなら ModelBuildError
    - オブジェクト名が未定義なら ModelBuildError
    - 型は「参考情報として保持するだけ」で、ミスマッチがあってもエラーにしない
      （必要なら logger で warning を出す）
    """
    pred_name = atom_ast.name
    if pred_name not in predicates_by_name:
        raise ModelBuildError(f"Predicate '{pred_name}' not declared in domain")

    predicate = predicates_by_name[pred_name]
    if len(atom_ast.args) != len(predicate.arg_types):
        raise ModelBuildError(
            f"Arity mismatch for predicate '{pred_name}': "
            f"expected {len(predicate.arg_types)}, got {len(atom_ast.args)}"
        )

    args: List[Object] = []
    for i, arg_name in enumerate(atom_ast.args):
        if arg_name not in objects_by_name:
            raise ModelBuildError(
                f"Object '{arg_name}' used in init/goal but not declared in :objects"
            )
        obj = objects_by_name[arg_name]
        expected_type = predicate.arg_types[i]

        # ★ 型チェックを緩める ★
        # - 本来は「obj.type が expected_type のサブタイプか」を見たいが、
        #   type hierarchy 情報を持っていないので、ここではエラーにしない。
        # - どうしても気になる場合だけ warning をログに出す。
        if expected_type is not None and obj.type is not None:
            if obj.type != expected_type:
                logger.debug(
                    "Type mismatch in predicate '%s' arg %d: expected %s, got %s "
                    "(ignored for now)",
                    pred_name,
                    i,
                    expected_type,
                    obj.type,
                )

        args.append(obj)

    return GroundAtom(predicate=predicate, args=tuple(args))
