"""
制約考慮型サブタスク統合処理
ドメイン汎化されたreachability制約とtype制約を考慮した統合戦略
"""
from typing import List, Dict, Set, Tuple, Optional
from .subtasks import SubTask
from .task import GroundAtom, PlanningTask


def extract_binary_constraints(task: PlanningTask, 
                              constraint_predicates: List[str]) -> Dict[str, Dict[str, Set[str]]]:
    """
    ドメイン汎化: 指定された述語からバイナリ制約を抽出する。
    
    Args:
        task: PDDL問題
        constraint_predicates: 制約述語のリスト（例：['reachable', 'accessible']）
    
    Returns:
        Dict[predicate_name, Dict[from_object, Set[to_object]]]: 制約関係
    """
    constraints = {}
    
    for predicate_name in constraint_predicates:
        constraints[predicate_name] = {}
        
        for fact in task.init:
            if hasattr(fact, 'predicate') and fact.predicate == predicate_name:
                if hasattr(fact, 'args') and len(fact.args) >= 2:
                    from_obj = fact.args[0]
                    to_obj = fact.args[1]
                    
                    if from_obj not in constraints[predicate_name]:
                        constraints[predicate_name][from_obj] = set()
                    constraints[predicate_name][from_obj].add(to_obj)
    
    return constraints


def extract_unary_type_constraints(task: PlanningTask, 
                                  type_predicates: List[str]) -> Dict[str, Dict[str, str]]:
    """
    ドメイン汎化: 指定された述語からオブジェクトのタイプ制約を抽出する。
    
    Args:
        task: PDDL問題
        type_predicates: タイプ述語のリスト（例：['object_type', 'tool_type']）
    
    Returns:
        Dict[predicate_name, Dict[object, type_value]]: オブジェクトのタイプマップ
    """
    type_constraints = {}
    
    for predicate_name in type_predicates:
        type_constraints[predicate_name] = {}
        
        for fact in task.init:
            if hasattr(fact, 'predicate') and fact.predicate == predicate_name:
                if hasattr(fact, 'args') and len(fact.args) >= 2:
                    obj = fact.args[0]
                    type_value = str(fact.args[1])
                    type_constraints[predicate_name][obj] = type_value
    
    return type_constraints


def find_common_accessible_objects(target_objects: List[str], 
                                  access_constraint: Dict[str, Set[str]],
                                  constraint_name: str) -> Set[str]:
    """
    ドメイン汎化: 複数のターゲットオブジェクトすべてからアクセス可能な共通オブジェクトを見つける。
    
    Args:
        target_objects: ターゲットオブジェクトのリスト
        access_constraint: アクセス制約（from_object -> Set[to_object]）
        constraint_name: 制約の名前（デバッグ用）
    
    Returns:
        すべてのターゲットからアクセス可能な共通オブジェクトの集合
    """
    if not target_objects:
        return set()
    
    # 最初のターゲットからアクセス可能なオブジェクトを基準とする
    common_accessible = set()
    for from_obj, accessible_set in access_constraint.items():
        if target_objects[0] in accessible_set:
            common_accessible.add(from_obj)
    
    # 他のターゲットからもアクセス可能なオブジェクトのみを残す
    for target_obj in target_objects[1:]:
        accessible_to_target = set()
        for from_obj, accessible_set in access_constraint.items():
            if target_obj in accessible_set:
                accessible_to_target.add(from_obj)
        common_accessible &= accessible_to_target
    
    return common_accessible


def is_compatible_for_merging(subtask1: SubTask, 
                             subtask2: SubTask,
                             task: PlanningTask,
                             max_goals_per_subtask: int,
                             constraint_config: Dict) -> bool:
    """
    ドメイン汎化: 2つのサブタスクが制約を満たしつつ統合可能かチェック。
    
    Args:
        constraint_config: 制約設定 {
            'binary_constraints': ['reachable'],
            'type_constraints': ['object_type'],  
            'goal_object_index': 0  # ゴールの引数のどのインデックスがターゲットオブジェクトか
        }
    """
    # ゴール数制約
    total_goals = len(subtask1.goals) + len(subtask2.goals)
    if total_goals > max_goals_per_subtask:
        return False
    
    # 設定から制約情報を取得
    binary_constraints = constraint_config.get('binary_constraints', [])
    type_constraints = constraint_config.get('type_constraints', [])
    goal_object_index = constraint_config.get('goal_object_index', 0)
    
    if not binary_constraints and not type_constraints:
        return True  # 制約が指定されていない場合は常に統合可能
    
    # ターゲットオブジェクト（ゴールの対象）を抽出
    def extract_target_objects(goals):
        targets = []
        for goal in goals:
            if hasattr(goal, 'args') and len(goal.args) > goal_object_index:
                targets.append(goal.args[goal_object_index])
        return targets
    
    target_objects1 = extract_target_objects(subtask1.goals)
    target_objects2 = extract_target_objects(subtask2.goals)
    all_targets = target_objects1 + target_objects2
    
    # バイナリ制約のチェック
    if binary_constraints:
        binary_constraint_map = extract_binary_constraints(task, binary_constraints)
        
        for constraint_name in binary_constraints:
            if constraint_name in binary_constraint_map:
                common_accessible = find_common_accessible_objects(
                    all_targets, binary_constraint_map[constraint_name], constraint_name
                )
                if not common_accessible:
                    return False  # 共通してアクセス可能なオブジェクトが存在しない
    
    # タイプ制約のチェック
    if type_constraints:
        type_constraint_map = extract_unary_type_constraints(task, type_constraints)
        
        for constraint_name in type_constraints:
            if constraint_name in type_constraint_map:
                type_map = type_constraint_map[constraint_name]
                required_types = set()
                for target in all_targets:
                    if target in type_map:
                        required_types.add(type_map[target])
                
                # 2つ以上の異なるタイプが必要な場合は統合不可能
                if len(required_types) > 1:
                    return False
    
    return True


def constraint_aware_merge_subtasks(subtasks: List[SubTask],
                                   task: PlanningTask,
                                   max_goals_per_subtask: int = 10,
                                   target_subtask_count: int = None,
                                   constraint_config: Dict = None) -> List[SubTask]:
    """
    ドメイン汎化された制約考慮型サブタスク統合。
    
    Args:
        subtasks: 統合前のサブタスクリスト
        task: PDDL問題（制約情報を含む）
        max_goals_per_subtask: 1つのサブタスクに含められる最大ゴール数
        target_subtask_count: 目標サブタスク数
        constraint_config: 制約設定辞書
    
    Returns:
        制約を満たしつつ統合されたサブタスクリスト
    """
    if not subtasks:
        return subtasks
    
    # デフォルト制約設定（汎用）
    if constraint_config is None:
        constraint_config = {
            'binary_constraints': ['reachable'],
            'type_constraints': ['object_type'],
            'goal_object_index': 0
        }
    
    # Phase 1: 同一role_signature内での制約考慮統合
    merged = _merge_within_same_role_signature(subtasks, task, max_goals_per_subtask, constraint_config)
    
    # Phase 2: 異なるrole_signature間での互換統合
    merged = _merge_compatible_across_roles(merged, task, max_goals_per_subtask, constraint_config)
    
    # Phase 3: 目標数に達していない場合の積極的統合
    if target_subtask_count and len(merged) > target_subtask_count:
        merged = _aggressive_constraint_aware_merge(merged, task, max_goals_per_subtask, target_subtask_count, constraint_config)
    
    return merged


def _merge_within_same_role_signature(subtasks: List[SubTask], 
                                     task: PlanningTask,
                                     max_goals_per_subtask: int,
                                     constraint_config: Dict) -> List[SubTask]:
    """
    同一role_signature内での制約考慮統合。
    """
    # role_signatureでグループ化
    signature_groups = {}
    for subtask in subtasks:
        signature_key = tuple(sorted(subtask.role_signature.items()))
        if signature_key not in signature_groups:
            signature_groups[signature_key] = []
        signature_groups[signature_key].append(subtask)
    
    merged = []
    next_id = max(s.id for s in subtasks) + 1
    
    for signature_key, group in signature_groups.items():
        if len(group) == 1:
            merged.extend(group)
            continue
        
        # グループ内での制約考慮統合
        group_merged = _merge_group_with_constraints(group, task, max_goals_per_subtask, next_id, constraint_config)
        merged.extend(group_merged)
        next_id += len(group_merged)
    
    return merged


def _merge_compatible_across_roles(subtasks: List[SubTask],
                                  task: PlanningTask,
                                  max_goals_per_subtask: int,
                                  constraint_config: Dict) -> List[SubTask]:
    """
    異なるrole_signature間での互換統合。
    """
    merged = list(subtasks)
    next_id = max(s.id for s in subtasks) + 1
    
    changed = True
    while changed:
        changed = False
        new_merged = []
        used = set()
        
        for i, subtask1 in enumerate(merged):
            if i in used:
                continue
                
            # 統合可能なパートナーを探す
            best_partner = None
            best_partner_idx = None
            
            for j, subtask2 in enumerate(merged[i+1:], i+1):
                if j in used:
                    continue
                
                if is_compatible_for_merging(subtask1, subtask2, task, max_goals_per_subtask, constraint_config):
                    best_partner = subtask2
                    best_partner_idx = j
                    break
            
            if best_partner:
                # 統合を実行
                merged_subtask = _merge_two_constraint_aware(subtask1, best_partner, task, next_id, constraint_config)
                new_merged.append(merged_subtask)
                used.add(i)
                used.add(best_partner_idx)
                next_id += 1
                changed = True
            else:
                new_merged.append(subtask1)
                used.add(i)
        
        merged = new_merged
    
    return merged


def _aggressive_constraint_aware_merge(subtasks: List[SubTask],
                                      task: PlanningTask,
                                      max_goals_per_subtask: int,
                                      target_count: int,
                                      constraint_config: Dict) -> List[SubTask]:
    """
    目標数に達するまでの積極的制約考慮統合。
    """
    merged = list(subtasks)
    next_id = max(s.id for s in subtasks) + 1
    
    while len(merged) > target_count:
        best_pair = None
        best_score = float('-inf')
        
        for i in range(len(merged)):
            for j in range(i + 1, len(merged)):
                if is_compatible_for_merging(merged[i], merged[j], task, max_goals_per_subtask, constraint_config):
                    score = _compatibility_score_with_constraints(merged[i], merged[j], task, constraint_config)
                    if score > best_score:
                        best_score = score
                        best_pair = (i, j)
        
        if best_pair is None:
            break  # これ以上統合できない
        
        # 最適ペアを統合
        i, j = best_pair
        merged_subtask = _merge_two_constraint_aware(merged[i], merged[j], task, next_id, constraint_config)
        
        # 古いサブタスクを削除し、新しいものを追加
        merged = [merged[k] for k in range(len(merged)) if k != i and k != j]
        merged.append(merged_subtask)
        next_id += 1
    
    return merged


def _merge_group_with_constraints(group: List[SubTask],
                                 task: PlanningTask,
                                 max_goals_per_subtask: int,
                                 start_id: int,
                                 constraint_config: Dict) -> List[SubTask]:
    """
    同一グループ内での制約考慮統合。
    """
    merged = []
    remaining = list(group)
    next_id = start_id
    
    while remaining:
        current = remaining.pop(0)
        
        # 統合可能なサブタスクを探して統合
        i = 0
        while i < len(remaining):
            candidate = remaining[i]
            if is_compatible_for_merging(current, candidate, task, max_goals_per_subtask, constraint_config):
                current = _merge_two_constraint_aware(current, candidate, task, next_id, constraint_config)
                remaining.pop(i)
                next_id += 1
            else:
                i += 1
        
        merged.append(current)
    
    return merged


def _merge_two_constraint_aware(subtask1: SubTask,
                               subtask2: SubTask,
                               task: PlanningTask,
                               new_id: int,
                               constraint_config: Dict) -> SubTask:
    """
    2つのサブタスクを制約考慮で統合。
    """
    # ゴールを統合
    combined_goals = subtask1.goals + subtask2.goals
    
    # ランドマークを統合
    combined_landmarks = subtask1.landmark_predicates.union(subtask2.landmark_predicates)
    
    # 元のrole_signatureを保持・統合（multi_objective_merge.pyと同じロジック）
    role_signature = _merge_role_signatures_constraint_aware(subtask1.role_signature, subtask2.role_signature)
    
    # roles_per_goalを統合
    combined_roles_per_goal = {}
    combined_roles_per_goal.update(subtask1.roles_per_goal)
    combined_roles_per_goal.update(subtask2.roles_per_goal)
    
    return SubTask(
        id=new_id,
        goals=combined_goals,
        landmark_predicates=combined_landmarks,
        role_signature=role_signature,
        roles_per_goal=combined_roles_per_goal
    )


def _merge_role_signatures_constraint_aware(signature1: Dict[str, str], signature2: Dict[str, str]) -> Dict[str, str]:
    """2つのrole_signatureを統合（制約考慮版）"""
    merged_signature = signature1.copy()
    
    for key, value in signature2.items():
        if key in merged_signature:
            if merged_signature[key] != value:
                # 異なる値の場合は統合（|で区切って結合）
                existing_values = set(merged_signature[key].split("|"))
                new_values = set(value.split("|"))
                all_values = existing_values.union(new_values)
                merged_signature[key] = "|".join(sorted(all_values))
        else:
            merged_signature[key] = value
    
    return merged_signature


def _compute_merged_role_signature(goals: List[GroundAtom],
                                  task: PlanningTask,
                                  constraint_config: Dict) -> Dict[str, str]:
    """
    ドメイン汎化: 統合されたゴールに基づいてrole_signatureを計算（レガシー用：現在は使用しない）
    """
    # 設定から制約情報を取得
    binary_constraints = constraint_config.get('binary_constraints', [])
    type_constraints = constraint_config.get('type_constraints', [])
    goal_object_index = constraint_config.get('goal_object_index', 0)
    
    role_signature = {}
    
    # ターゲットオブジェクトを抽出
    target_objects = []
    for goal in goals:
        if hasattr(goal, 'args') and len(goal.args) > goal_object_index:
            target_objects.append(goal.args[goal_object_index])
    
    # バイナリ制約から役割値を計算
    if binary_constraints:
        binary_constraint_map = extract_binary_constraints(task, binary_constraints)
        
        for constraint_name in binary_constraints:
            if constraint_name in binary_constraint_map:
                common_accessible = find_common_accessible_objects(
                    target_objects, binary_constraint_map[constraint_name], constraint_name
                )
                # role_signatureのキー名を推定（制約名から）
                role_key = _infer_role_key_from_constraint(constraint_name)
                role_signature[role_key] = "|".join(sorted(common_accessible)) if common_accessible else "no_common"
    
    # タイプ制約から役割値を計算
    if type_constraints:
        type_constraint_map = extract_unary_type_constraints(task, type_constraints)
        
        for constraint_name in type_constraints:
            if constraint_name in type_constraint_map:
                type_map = type_constraint_map[constraint_name]
                required_types = set()
                for target in target_objects:
                    if target in type_map:
                        required_types.add(type_map[target])
                
                # role_signatureのキー名を推定
                role_key = _infer_role_key_from_type_constraint(constraint_name)
                role_signature[role_key] = "|".join(sorted(required_types)) if required_types else "any"
    
    return role_signature


def _infer_role_key_from_constraint(constraint_name: str) -> str:
    """
    制約名からrole_signatureのキー名を推定。
    """
    # 簡単なヒューリスティック: 制約名から役割名を推定
    if 'reachable' in constraint_name.lower():
        return 'location'  # reachable制約は通常、位置を表す
    elif 'accessible' in constraint_name.lower():
        return 'location'
    else:
        return constraint_name.lower() + '_resource'


def _infer_role_key_from_type_constraint(constraint_name: str) -> str:
    """
    タイプ制約名からrole_signatureのキー名を推定。
    """
    # 簡単なヒューリスティック: _typeサフィックスを除去
    if constraint_name.endswith('_type'):
        return constraint_name[:-5]  # '_type'を除去
    else:
        return constraint_name.lower()


def _compatibility_score_with_constraints(subtask1: SubTask,
                                         subtask2: SubTask,
                                         task: PlanningTask,
                                         constraint_config: Dict) -> float:
    """
    制約を考慮した互換性スコアを計算。
    """
    score = 0
    
    # 設定から制約情報を取得
    binary_constraints = constraint_config.get('binary_constraints', [])
    type_constraints = constraint_config.get('type_constraints', [])
    goal_object_index = constraint_config.get('goal_object_index', 0)
    
    # ターゲットオブジェクトを抽出
    def extract_targets(goals):
        return [goal.args[goal_object_index] for goal in goals
                if hasattr(goal, 'args') and len(goal.args) > goal_object_index]
    
    targets1 = extract_targets(subtask1.goals)
    targets2 = extract_targets(subtask2.goals)
    all_targets = targets1 + targets2
    
    # 共通アクセス可能オブジェクト数をスコアに加算
    if binary_constraints:
        binary_constraint_map = extract_binary_constraints(task, binary_constraints)
        
        for constraint_name in binary_constraints:
            if constraint_name in binary_constraint_map:
                common_accessible = find_common_accessible_objects(
                    all_targets, binary_constraint_map[constraint_name], constraint_name
                )
                score += len(common_accessible) * 10
    
    # タイプ互換性をチェック
    if type_constraints:
        type_constraint_map = extract_unary_type_constraints(task, type_constraints)
        
        for constraint_name in type_constraints:
            if constraint_name in type_constraint_map:
                type_map = type_constraint_map[constraint_name]
                required_types = set()
                for target in all_targets:
                    if target in type_map:
                        required_types.add(type_map[target])
                
                # 同じタイプなら高スコア
                if len(required_types) <= 1:
                    score += 20
    
    # 共通ランドマークスコア
    common_landmarks = len(subtask1.landmark_predicates.intersection(subtask2.landmark_predicates))
    score += common_landmarks * 2
    
    # ゴール数が少ないほど統合しやすい
    total_goals = len(subtask1.goals) + len(subtask2.goals)
    score += (10 - total_goals) * 1  # max 10 goalsと仮定
    
    return score