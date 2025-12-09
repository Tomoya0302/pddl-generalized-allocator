from typing import List, Union, Any

SExpr = Union[str, List["SExpr"]]

def parse_sexpr(tokens: List[str]) -> List[SExpr]:
    """
    トークン列からネストしたS式のリストを生成。
    例: ['(', 'define', ... , ')'] -> [['define', ...]]
    """
    result = []
    i = 0
    
    while i < len(tokens):
        expr, i = _parse_single_expr(tokens, i)
        if expr is not None:
            result.append(expr)
    
    return result

def _parse_single_expr(tokens: List[str], start: int) -> tuple[SExpr | None, int]:
    """単一のS式をパースして、次のインデックスと共に返す"""
    if start >= len(tokens):
        return None, start
    
    token = tokens[start]
    
    if token == '(':
        # ネストした式の開始
        expr_list = []
        i = start + 1
        
        while i < len(tokens) and tokens[i] != ')':
            sub_expr, i = _parse_single_expr(tokens, i)
            if sub_expr is not None:
                expr_list.append(sub_expr)
        
        if i >= len(tokens):
            raise ValueError("Unmatched opening parenthesis")
        
        return expr_list, i + 1  # ')' をスキップ
    
    elif token == ')':
        raise ValueError("Unexpected closing parenthesis")
    
    else:
        # アトム（文字列）
        return token, start + 1