from .ast import DomainAST, PredicateSchema, ActionSchema, TypedVar, Literal
from .sexpr_parser import SExpr
from typing import List, Dict

class DomainParser:
    def __init__(self, sexprs: List[SExpr]):
        self.sexprs = sexprs

    def parse(self) -> DomainAST:
        """
        (define (domain ...) ...) を探してDomainASTを構築
        - :requirements, :types, :predicates, :action を読む
        - MA-PDDL のagentドメイン拡張はrequirementsとpredicates/typesだけで扱う
        """
        domain_expr = None
        for expr in self.sexprs:
            if isinstance(expr, list) and len(expr) >= 3:
                if expr[0] == "define" and isinstance(expr[1], list) and expr[1][0] == "domain":
                    domain_expr = expr
                    break
        
        if domain_expr is None:
            raise ValueError("Domain definition not found")
        
        domain_name = domain_expr[1][1] if len(domain_expr[1]) > 1 else "unknown"
        
        requirements = []
        types = []
        predicates = {}
        actions = {}
        
        # ドメイン定義の各部分をパース
        for item in domain_expr[2:]:
            if isinstance(item, list) and len(item) > 0:
                if item[0] == ":requirements":
                    requirements = item[1:]
                elif item[0] == ":types":
                    types = self._parse_types(item[1:])
                elif item[0] == ":predicates":
                    predicates = self._parse_predicates(item[1:])
                elif item[0] == ":action":
                    action = self._parse_action(item[1:])
                    actions[action.name] = action
        
        return DomainAST(
            name=domain_name,
            requirements=requirements,
            types=types,
            predicates=predicates,
            actions=actions
        )
    
    def _parse_types(self, type_list: List[SExpr]) -> List[str]:
        """型定義をパース（簡易版）"""
        types = []
        for item in type_list:
            if isinstance(item, str) and item != "-":
                types.append(item)
        return types
    
    def _parse_predicates(self, pred_list: List[SExpr]) -> Dict[str, PredicateSchema]:
        """述語定義をパース"""
        predicates = {}
        for pred_def in pred_list:
            if isinstance(pred_def, list) and len(pred_def) > 0:
                pred_name = pred_def[0]
                params = self._parse_parameters(pred_def[1:])
                predicates[pred_name] = PredicateSchema(name=pred_name, parameters=params)
        return predicates
    
    def _parse_parameters(self, param_list: List[SExpr]) -> List[TypedVar]:
        """パラメータリストをパース"""
        params = []
        i = 0
        while i < len(param_list):
            if isinstance(param_list[i], str):
                var_name = param_list[i]
                var_type = None
                
                # 型指定があるかチェック
                if i + 2 < len(param_list) and param_list[i + 1] == "-":
                    var_type = param_list[i + 2]
                    i += 3
                else:
                    i += 1
                
                params.append(TypedVar(name=var_name, type=var_type))
        return params
    
    def _parse_action(self, action_def: List[SExpr]) -> ActionSchema:
        """アクション定義をパース"""
        if len(action_def) == 0:
            raise ValueError("Empty action definition")
        
        action_name = action_def[0]
        parameters = []
        precondition = None
        effect = None
        
        i = 1
        while i < len(action_def):
            if action_def[i] == ":parameters":
                if i + 1 < len(action_def) and isinstance(action_def[i + 1], list):
                    parameters = self._parse_parameters(action_def[i + 1])
                i += 2
            elif action_def[i] == ":precondition":
                if i + 1 < len(action_def):
                    precondition = action_def[i + 1]
                i += 2
            elif action_def[i] == ":effect":
                if i + 1 < len(action_def):
                    effect = action_def[i + 1]
                i += 2
            else:
                i += 1
        
        return ActionSchema(
            name=action_name,
            parameters=parameters,
            precondition=precondition,
            effect=effect
        )