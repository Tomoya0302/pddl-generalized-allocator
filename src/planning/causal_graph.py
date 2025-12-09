from typing import Dict, Set
from .task import PlanningTask
from ..pddl.ast import ActionSchema, Literal

CausalGraph = Dict[str, Set[str]]  # predicate_name -> successors

def build_causal_graph(task: PlanningTask) -> CausalGraph:
    """
    ノード: 述語名
    エッジ: preに現れる述語pからaddに現れる述語qへの有向辺

    擬似コード:
      cg = {p: set() for p in task.predicates.keys()}
      for action in task.actions.values():
        pre_preds = {lit.predicate for lit in flatten_precondition(action.precondition)}
        add_preds = {lit.predicate for lit in flatten_effect_adds(action.effect)}
        for p in pre_preds:
          for q in add_preds:
            cg[p].add(q)
      return cg
    """
    cg = {p: set() for p in task.predicates.keys()}
    
    for action in task.actions.values():
        pre_preds = _flatten_precondition(action.precondition)
        add_preds = _flatten_effect_adds(action.effect)
        
        for p in pre_preds:
            for q in add_preds:
                if p in cg:
                    cg[p].add(q)
    
    return cg

def _flatten_precondition(precondition) -> Set[str]:
    """前提条件から述語名を抽出（簡易版）"""
    predicates = set()
    
    if isinstance(precondition, list):
        if len(precondition) == 0:
            return predicates
        
        # (and ...) の形式
        if precondition[0] == "and":
            for sub_expr in precondition[1:]:
                predicates.update(_flatten_precondition(sub_expr))
        
        # (not ...) の形式（否定前提）
        elif precondition[0] == "not":
            if len(precondition) > 1 and isinstance(precondition[1], list):
                if len(precondition[1]) > 0:
                    predicates.add(precondition[1][0])
        
        # 単純な肯定前提
        else:
            if len(precondition) > 0:
                predicates.add(precondition[0])
    
    return predicates

def _flatten_effect_adds(effect_expr) -> Set[str]:
    """エフェクト式から追加される述語名を抽出（簡易版）"""
    predicates = set()
    
    if isinstance(effect_expr, list):
        if len(effect_expr) == 0:
            return predicates
        
        # (and ...) の形式
        if effect_expr[0] == "and":
            for sub_expr in effect_expr[1:]:
                predicates.update(_flatten_effect_adds(sub_expr))
        
        # (not ...) の形式は削除効果なのでaddには含めない
        elif effect_expr[0] == "not":
            pass
        
        # 単純な追加効果
        else:
            if len(effect_expr) > 0:
                predicates.add(effect_expr[0])
    
    return predicates