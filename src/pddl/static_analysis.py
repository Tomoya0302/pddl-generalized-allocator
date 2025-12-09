from .ast import DomainAST
from typing import Set

def compute_static_predicates(domain: DomainAST) -> Set[str]:
    """
    任意のActionSchemaでadd / deleteに一度も出ない述語をSTATICとみなす。
    Role抽出は基本的にstatic predicateのみを参照する前提。
    """
    all_predicates = set(domain.predicates.keys())
    dynamic_predicates = set()
    
    for action in domain.actions.values():
        # エフェクト部分から動的述語を抽出
        if action.effect is not None:
            dynamic_predicates.update(_extract_effect_predicates(action.effect))
    
    static_predicates = all_predicates - dynamic_predicates
    return static_predicates

def _extract_effect_predicates(effect_expr) -> Set[str]:
    """エフェクト式から述語名を抽出（簡易版）"""
    predicates = set()
    
    if isinstance(effect_expr, list):
        if len(effect_expr) == 0:
            return predicates
        
        # (and ...) の形式
        if effect_expr[0] == "and":
            for sub_expr in effect_expr[1:]:
                predicates.update(_extract_effect_predicates(sub_expr))
        
        # (not ...) の形式（削除効果）
        elif effect_expr[0] == "not":
            if len(effect_expr) > 1 and isinstance(effect_expr[1], list):
                if len(effect_expr[1]) > 0:
                    predicates.add(effect_expr[1][0])
        
        # 単純な追加効果
        else:
            if len(effect_expr) > 0:
                predicates.add(effect_expr[0])
    
    return predicates