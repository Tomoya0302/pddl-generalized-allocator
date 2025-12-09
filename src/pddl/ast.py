from dataclasses import dataclass
from typing import List, Dict, Optional, Any

@dataclass
class TypedVar:
    name: str
    type: Optional[str]  # None = untyped

@dataclass
class PredicateSchema:
    name: str
    parameters: List[TypedVar]

@dataclass
class Literal:
    predicate: str
    args: List[str]
    negated: bool = False

@dataclass
class ActionSchema:
    name: str
    parameters: List[TypedVar]
    precondition: Any  # 後でNormalizedFormulaなどにしてもよい
    effect: Any        # 同上

@dataclass
class DomainAST:
    name: str
    requirements: List[str]
    types: List[str]
    predicates: Dict[str, PredicateSchema]
    actions: Dict[str, ActionSchema]

@dataclass
class ProblemAST:
    name: str
    domain_name: str
    objects: Dict[str, str]     # obj_name -> type_name
    init: List[Literal]
    goals: List[Literal]