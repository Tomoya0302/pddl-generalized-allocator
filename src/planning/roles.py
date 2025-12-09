from dataclasses import dataclass
from typing import Dict, List, Set, Tuple, Optional
from .task import GroundAtom, PlanningTask
import json

@dataclass
class BindingRef:
    kind: str            # "goal" or "role"
    index_or_name: str   # goal-index (str 化した整数) or role-name

@dataclass
class ExtractorConfig:
    predicate: str
    bindings: Dict[int, BindingRef]   # arg_index -> BindingRef
    value_arg: int                    # 取り出したい引数位置

@dataclass
class RoleConfig:
    extractors: List[ExtractorConfig]

@dataclass
class DomainRoleConfig:
    domain: str
    goal_predicates: List[str]
    roles: Dict[str, RoleConfig]
    cluster_keys: List[str]
    output_role_fields: List[str]
    agent_role_extractors: Optional[Dict[str, ExtractorConfig]] = None

def load_domain_role_config(path: str) -> DomainRoleConfig:
    """JSONファイルからDomainRoleConfigを読み込む"""
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    def parse_binding(raw_value: str) -> BindingRef:
        # "goal:0" or "role:some_role"
        kind, arg = raw_value.split(":", 1)
        return BindingRef(kind=kind, index_or_name=arg)

    roles = {}
    for role_name, role_def in raw["roles"].items():
        ex_list = []
        for e in role_def["extractors"]:
            bindings = {int(k): parse_binding(v)
                        for k, v in e["bindings"].items()}
            ex_list.append(ExtractorConfig(
                predicate=e["predicate"],
                bindings=bindings,
                value_arg=e["value_arg"],
            ))
        roles[role_name] = RoleConfig(extractors=ex_list)

    # エージェント役割抽出器の解析
    agent_role_extractors = None
    if "agent_role_extractors" in raw:
        agent_role_extractors = {}
        for role_name, extractor_def in raw["agent_role_extractors"].items():
            bindings = {int(k): parse_binding(v)
                        for k, v in extractor_def["bindings"].items()}
            agent_role_extractors[role_name] = ExtractorConfig(
                predicate=extractor_def["predicate"],
                bindings=bindings,
                value_arg=extractor_def["value_arg"]
            )

    return DomainRoleConfig(
        domain=raw["domain"],
        goal_predicates=raw["goal_predicates"],
        roles=roles,
        cluster_keys=raw.get("cluster_keys", []),
        output_role_fields=raw.get("output_role_fields", list(roles.keys())),
        agent_role_extractors=agent_role_extractors
    )

def evaluate_extractor_for_goal(task: PlanningTask,
                                goal: GroundAtom,
                                roles_so_far: Dict[str, str],
                                extractor: ExtractorConfig) -> Set[str]:
    """
    E(g, roles_so_far) を計算してvalue候補集合を返す。
    - I = task.init の中から、predicate一致するGroundAtomを列挙。
    - それぞれの引数 (x_0,...,x_n) についてbindingsをチェック。
    """
    results = set()
    matching_atoms = []
    
    for atom in task.init:
        if atom.predicate != extractor.predicate:
            continue
        matching_atoms.append(atom)
        
        # atom.args は tuple[str,...]
        ok = True
        for idx, bind in extractor.bindings.items():
            if idx >= len(atom.args):
                ok = False
                break
            
            if bind.kind == "goal":
                goal_arg_index = int(bind.index_or_name)
                if goal_arg_index >= len(goal.args):
                    ok = False
                    break
                expected = goal.args[goal_arg_index]
            else:  # "role"
                role_name = bind.index_or_name
                if role_name not in roles_so_far:
                    ok = False
                    break
                expected = roles_so_far[role_name]
            
            if atom.args[idx] != expected:
                ok = False
                break
        
        if ok:
            if extractor.value_arg < len(atom.args):
                results.add(atom.args[extractor.value_arg])
    
    # デバッグ情報は簡潔に
    
    return results

def extract_roles_for_goal(task: PlanningTask,
                           goal: GroundAtom,
                           cfg: DomainRoleConfig,
                           on_missing_role: str) -> Optional[Dict[str, str]]:
    """
    1ゴールgに対してroles(g): role_name -> object_nameを求める。
    - 反復的にextractorを評価し、1候補に絞れたら確定。
    - すべてのroleが決まるまで繰り返す。
    - どのroleも進展しなくなった場合:
        - on_missing_role == "error": Exception
        - "skip_goal": Noneを返す
    """
    roles = {}
    remaining_roles = set(cfg.roles.keys())

    iteration = 0
    changed = True
    while remaining_roles and changed and iteration < 10:  # 無限ループ防止
        changed = False
        iteration += 1
        
        for r in list(remaining_roles):
            role_cfg = cfg.roles[r]
            candidates: Set[str] = set()
            for extractor in role_cfg.extractors:
                vals = evaluate_extractor_for_goal(
                    task, goal, roles, extractor
                )
                candidates |= vals
            
            if len(candidates) == 1:
                value = next(iter(candidates))
                roles[r] = value
                remaining_roles.remove(r)
                changed = True
            elif len(candidates) > 1:
                # 複数候補がある場合は、辞書順で最小のものを選択
                value = min(candidates)
                roles[r] = value
                remaining_roles.remove(r)
                changed = True
            # len == 0: 情報不足（別のroleが決まれば増えるかもしれないので保留）

    if remaining_roles:
        if on_missing_role == "error":
            raise RuntimeError(f"Cannot extract roles for goal {goal}: missing {remaining_roles}")
        else:
            return None
    return roles

def extract_roles_for_goals(task: PlanningTask,
                            cfg: DomainRoleConfig,
                            goals: Set[GroundAtom],
                            on_missing_role: str) -> Dict[GroundAtom, Dict[str, str]]:
    """
    対象ゴールはcfg.goal_predicatesに含まれるpredicateのみ。
    """
    result = {}
    for g in goals:
        if g.predicate not in cfg.goal_predicates:
            continue
        roles = extract_roles_for_goal(task, g, cfg, on_missing_role)
        if roles is not None:
            result[g] = roles
    return result

def extract_agent_roles(task: PlanningTask,
                        agent_name: str,
                        cfg: DomainRoleConfig) -> Dict[str, str]:
    """
    エージェントの実際の役割値を抽出する。
    agent_role_extractorsを使用してエージェントのrole signatureを決定。
    """
    if cfg.agent_role_extractors is None:
        return {}
    
    agent_roles = {}
    remaining_roles = set(cfg.agent_role_extractors.keys())
    
    # 反復的に解決（依存関係がある場合）
    iteration = 0
    changed = True
    while remaining_roles and changed and iteration < 10:
        changed = False
        iteration += 1
        
        for role_name in list(remaining_roles):
            extractor = cfg.agent_role_extractors[role_name]
            candidates = set()
            
            for atom in task.init:
                if atom.predicate != extractor.predicate:
                    continue
                
                ok = True
                for idx, bind in extractor.bindings.items():
                    if idx >= len(atom.args):
                        ok = False
                        break
                    
                    if bind.kind == "agent":
                        # "agent:self" の場合、現在のエージェント名を期待
                        if bind.index_or_name == "self":
                            expected = agent_name
                        else:
                            expected = bind.index_or_name
                    elif bind.kind == "role":
                        # 他の役割値を参照（依存関係がある場合）
                        role_ref = bind.index_or_name
                        if role_ref not in agent_roles:
                            ok = False
                            break
                        expected = agent_roles[role_ref]
                    else:
                        # その他のbinding typeはエラー
                        ok = False
                        break
                    
                    if atom.args[idx] != expected:
                        ok = False
                        break
                
                if ok and extractor.value_arg < len(atom.args):
                    candidates.add(atom.args[extractor.value_arg])
            
            # 複数候補がある場合は最小値を選択（決定論的）
            if len(candidates) == 1:
                agent_roles[role_name] = next(iter(candidates))
                remaining_roles.remove(role_name)
                changed = True
            elif len(candidates) > 1:
                agent_roles[role_name] = min(candidates)
                remaining_roles.remove(role_name)
                changed = True
            # len == 0 の場合は、その役割値は決定できない（次の反復で再試行）
    
    return agent_roles