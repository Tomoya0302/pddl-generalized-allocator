from .ast import ProblemAST, Literal
from .sexpr_parser import SExpr
from typing import List, Dict

class ProblemParser:
    def __init__(self, sexprs: List[SExpr]):
        self.sexprs = sexprs

    def parse(self) -> ProblemAST:
        """
        (define (problem ...) ...) を解析。
        - :objects, :init, :goal を抽出。
        - multiagent 拡張でagentの宣言があっても、単に型付きobjectsとして読む。
        """
        problem_expr = None
        for expr in self.sexprs:
            if isinstance(expr, list) and len(expr) >= 3:
                if expr[0] == "define" and isinstance(expr[1], list) and expr[1][0] == "problem":
                    problem_expr = expr
                    break
        
        if problem_expr is None:
            raise ValueError("Problem definition not found")
        
        problem_name = problem_expr[1][1] if len(problem_expr[1]) > 1 else "unknown"
        domain_name = "unknown"
        objects = {}
        init = []
        goals = []
        
        # 問題定義の各部分をパース
        for item in problem_expr[2:]:
            if isinstance(item, list) and len(item) > 0:
                if item[0] == ":domain":
                    domain_name = item[1] if len(item) > 1 else "unknown"
                elif item[0] == ":objects":
                    objects = self._parse_objects(item[1:])
                elif item[0] == ":init":
                    init = self._parse_literals(item[1:])
                elif item[0] == ":goal":
                    goals = self._parse_goal(item[1:])
        
        return ProblemAST(
            name=problem_name,
            domain_name=domain_name,
            objects=objects,
            init=init,
            goals=goals
        )
    
    def _parse_objects(self, obj_list: List[SExpr]) -> Dict[str, str]:
        """オブジェクト定義をパース"""
        objects = {}
        i = 0
        current_objects = []
        
        while i < len(obj_list):
            if isinstance(obj_list[i], str):
                if obj_list[i] == "-":
                    # 型指定の区切り文字
                    if i + 1 < len(obj_list) and current_objects:
                        obj_type = obj_list[i + 1]
                        for obj_name in current_objects:
                            objects[obj_name] = obj_type
                        current_objects = []
                        i += 2
                    else:
                        i += 1
                else:
                    # オブジェクト名
                    current_objects.append(obj_list[i])
                    i += 1
            else:
                i += 1
        
        # 型指定がないオブジェクトはデフォルト型
        for obj_name in current_objects:
            objects[obj_name] = "object"
        
        return objects
    
    def _parse_literals(self, literal_list: List[SExpr]) -> List[Literal]:
        """リテラルリストをパース（初期状態用）"""
        literals = []
        for item in literal_list:
            if isinstance(item, list) and len(item) > 0:
                literal = self._parse_single_literal(item)
                if literal:
                    literals.append(literal)
        return literals
    
    def _parse_single_literal(self, expr: List[SExpr]) -> Literal | None:
        """単一のリテラルをパース"""
        if len(expr) == 0:
            return None
        
        negated = False
        start_idx = 0
        
        # 否定チェック
        if expr[0] == "not":
            negated = True
            start_idx = 1
            if len(expr) <= 1 or not isinstance(expr[1], list):
                return None
            expr = expr[1]
        
        predicate = expr[0] if len(expr) > 0 else ""
        args = [str(arg) for arg in expr[1:] if isinstance(arg, str)]
        
        return Literal(predicate=predicate, args=args, negated=negated)
    
    def _parse_goal(self, goal_expr: List[SExpr]) -> List[Literal]:
        """ゴール式をパース"""
        if len(goal_expr) == 0:
            return []
        
        # 単一の式の場合
        expr = goal_expr[0]
        
        if isinstance(expr, list) and len(expr) > 0:
            # (and ...) の形式かチェック
            if expr[0] == "and":
                return self._parse_literals(expr[1:])
            else:
                # 単一のゴール
                literal = self._parse_single_literal(expr)
                return [literal] if literal else []
        
        return []