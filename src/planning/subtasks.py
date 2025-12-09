from dataclasses import dataclass
from typing import List, Dict, Set, Tuple
from .task import GroundAtom
from .roles import DomainRoleConfig

@dataclass
class SubTask:
    id: int
    goals: List[GroundAtom]
    landmark_predicates: Set[str]
    role_signature: Dict[str, str]  # cluster_keysに対応する役割値
    roles_per_goal: Dict[GroundAtom, Dict[str, str]]

def finer_partition_by_roles(clusters: List[List[GroundAtom]],
                             role_assignments: Dict[GroundAtom, Dict[str, str]],
                             cfg: DomainRoleConfig,
                             landmarks: Dict[GroundAtom, Set[str]]) -> List[SubTask]:
    """
    Step 9:
    - 第一次クラスタ (構造クラスタ) ごとに、cluster_keysに基づいて細分化。
    """
    subtasks: List[SubTask] = []
    next_id = 0

    for cluster in clusters:
        # 同値類のキー: Tuple[role_value_for_each_cluster_key]
        groups: Dict[Tuple[str, ...], List[GroundAtom]] = {}
        for g in cluster:
            roles = role_assignments.get(g)
            if roles is None:
                continue
            key_tuple = tuple(roles.get(r, None) for r in cfg.cluster_keys)
            groups.setdefault(key_tuple, []).append(g)

        for key_tuple, group_goals in groups.items():
            role_sig = {r: v for r, v in zip(cfg.cluster_keys, key_tuple)}
            lm_union: Set[str] = set()
            for g in group_goals:
                lm_union |= landmarks.get(g, set())
            subtasks.append(SubTask(
                id=next_id,
                goals=group_goals,
                landmark_predicates=lm_union,
                role_signature=role_sig,
                roles_per_goal={g: role_assignments[g] for g in group_goals if g in role_assignments},
            ))
            next_id += 1

    return subtasks

def merge_compatible_subtasks(subtasks: List[SubTask],
                              max_goals_per_subtask: int = 10) -> List[SubTask]:
    """
    同じrole_signatureを持つサブタスクを統合する。
    ドメイン汎化された後処理ステップ。
    
    Args:
        subtasks: 統合前のサブタスクリスト
        max_goals_per_subtask: 1つのサブタスクに含められる最大ゴール数
    
    Returns:
        統合後のサブタスクリスト
    """
    # role_signatureでグループ化
    signature_groups = {}
    for subtask in subtasks:
        # role_signatureを文字列キーに変換（辞書のハッシュ化）
        signature_key = tuple(sorted(subtask.role_signature.items()))
        if signature_key not in signature_groups:
            signature_groups[signature_key] = []
        signature_groups[signature_key].append(subtask)
    
    merged_subtasks = []
    next_id = 0
    
    for signature_key, group in signature_groups.items():
        # 各グループ内でサブタスクを統合
        role_signature = dict(signature_key)
        
        # 全ゴールとランドマークを集約
        all_goals = []
        all_landmarks = set()
        combined_roles_per_goal = {}
        
        for subtask in group:
            all_goals.extend(subtask.goals)
            all_landmarks.update(subtask.landmark_predicates)
            combined_roles_per_goal.update(subtask.roles_per_goal)
        
        # max_goals_per_subtaskでサブタスクを分割
        for i in range(0, len(all_goals), max_goals_per_subtask):
            chunk_goals = all_goals[i:i + max_goals_per_subtask]
            chunk_roles_per_goal = {g: combined_roles_per_goal[g] for g in chunk_goals if g in combined_roles_per_goal}
            
            merged_subtask = SubTask(
                id=next_id,
                goals=chunk_goals,
                landmark_predicates=all_landmarks,
                role_signature=role_signature,
                roles_per_goal=chunk_roles_per_goal
            )
            merged_subtasks.append(merged_subtask)
            next_id += 1
    
    return merged_subtasks

def advanced_merge_subtasks(subtasks: List[SubTask],
                           max_goals_per_subtask: int = 10,
                           target_subtask_count: int = None) -> List[SubTask]:
    """
    高度なサブタスク統合：複数の戦略を組み合わせてサブタスク数を大幅に削減。
    
    Args:
        subtasks: 統合前のサブタスクリスト
        max_goals_per_subtask: 1つのサブタスクに含められる最大ゴール数
        target_subtask_count: 目標サブタスク数（指定時はより積極的に統合）
    
    Returns:
        統合後のサブタスクリスト
    """
    if not subtasks:
        return subtasks
    
    # Strategy 1: 同一role_signature統合
    merged = merge_compatible_subtasks(subtasks, max_goals_per_subtask)
    
    # Strategy 2: 共通オブジェクト統合（ドメイン汎化的アプローチ）
    merged = _merge_by_shared_objects(merged, max_goals_per_subtask)
    
    # Strategy 3: 目標数に達していない場合、より積極的な統合
    if target_subtask_count and len(merged) > target_subtask_count:
        merged = _aggressive_merge(merged, max_goals_per_subtask, target_subtask_count)
    
    return merged

def _merge_by_shared_objects(subtasks: List[SubTask], max_goals_per_subtask: int) -> List[SubTask]:
    """
    共通オブジェクトを使用するサブタスクを統合（ドメイン汎化的）。
    """
    if len(subtasks) <= 1:
        return subtasks
    
    # 各サブタスクで使用されるオブジェクトを抽出
    def extract_objects_from_subtask(subtask: SubTask) -> Set[str]:
        objects = set()
        for goal in subtask.goals:
            if hasattr(goal, 'args') and goal.args:
                objects.update(goal.args)
        return objects
    
    # オブジェクト使用パターンでグループ化
    object_groups = {}
    for subtask in subtasks:
        objects = extract_objects_from_subtask(subtask)
        # 主要オブジェクト（最初の2-3個）をキーとして使用
        key_objects = tuple(sorted(list(objects))[:3])
        if key_objects:
            if key_objects not in object_groups:
                object_groups[key_objects] = []
            object_groups[key_objects].append(subtask)
        else:
            # オブジェクトがない場合は単独グループ
            singleton_key = (f"no_objects_{subtask.id}",)
            object_groups[singleton_key] = [subtask]
    
    merged_subtasks = []
    next_id = 0
    
    for key_objects, group in object_groups.items():
        if len(group) == 1:
            merged_subtasks.extend(group)
            continue
            
        # グループ内で統合可能なサブタスクを特定
        merged_group = _merge_compatible_group(group, max_goals_per_subtask, next_id)
        merged_subtasks.extend(merged_group)
        next_id += len(merged_group)
    
    return merged_subtasks

def _aggressive_merge(subtasks: List[SubTask],
                     max_goals_per_subtask: int,
                     target_count: int) -> List[SubTask]:
    """
    目標数に達するまで積極的に統合を行う。
    """
    if len(subtasks) <= target_count:
        return subtasks
    
    merged = list(subtasks)
    next_id = max(s.id for s in subtasks) + 1
    
    while len(merged) > target_count:
        # 最も統合しやすいペアを見つけて統合
        best_pair = None
        best_score = float('-inf')
        
        for i in range(len(merged)):
            for j in range(i + 1, len(merged)):
                score = _compatibility_score(merged[i], merged[j], max_goals_per_subtask)
                if score > best_score:
                    best_score = score
                    best_pair = (i, j)
        
        if best_pair is None or best_score <= 0:
            break  # これ以上統合できない
            
        # ペアを統合
        i, j = best_pair
        subtask1, subtask2 = merged[i], merged[j]
        
        merged_subtask = _merge_two_subtasks(subtask1, subtask2, next_id)
        
        # 古いサブタスクを削除し、新しいものを追加
        merged = [merged[k] for k in range(len(merged)) if k != i and k != j]
        merged.append(merged_subtask)
        next_id += 1
    
    return merged

def _compatibility_score(subtask1: SubTask, subtask2: SubTask, max_goals_per_subtask: int) -> float:
    """
    2つのサブタスクの統合可能性をスコア化。
    """
    total_goals = len(subtask1.goals) + len(subtask2.goals)
    if total_goals > max_goals_per_subtask:
        return -1  # 統合不可能
    
    score = 0
    
    # 同じrole_signatureなら高スコア
    if subtask1.role_signature == subtask2.role_signature:
        score += 100
    
    # 共通オブジェクトがあれば追加スコア
    objects1 = set()
    objects2 = set()
    for goal in subtask1.goals:
        if hasattr(goal, 'args'):
            objects1.update(goal.args or [])
    for goal in subtask2.goals:
        if hasattr(goal, 'args'):
            objects2.update(goal.args or [])
    
    common_objects = len(objects1.intersection(objects2))
    score += common_objects * 10
    
    # 共通ランドマークがあれば追加スコア
    common_landmarks = len(subtask1.landmark_predicates.intersection(subtask2.landmark_predicates))
    score += common_landmarks * 5
    
    # ゴール数が少ないほど統合しやすい
    score += (max_goals_per_subtask - total_goals) * 2
    
    return score

def _merge_compatible_group(group: List[SubTask],
                           max_goals_per_subtask: int,
                           start_id: int) -> List[SubTask]:
    """
    グループ内で統合可能なサブタスクを統合。
    """
    if len(group) <= 1:
        return group
    
    merged = []
    remaining = list(group)
    next_id = start_id
    
    while remaining:
        current = remaining.pop(0)
        
        # 統合可能なサブタスクを探す
        to_merge = [current]
        i = 0
        while i < len(remaining):
            candidate = remaining[i]
            total_goals = len(current.goals) + len(candidate.goals)
            
            if total_goals <= max_goals_per_subtask:
                to_merge.append(remaining.pop(i))
                current = _merge_two_subtasks(current, candidate, next_id)
                next_id += 1
            else:
                i += 1
        
        merged.append(current)
    
    return merged

def _merge_two_subtasks(subtask1: SubTask, subtask2: SubTask, new_id: int) -> SubTask:
    """
    2つのサブタスクを統合して新しいサブタスクを作成。
    """
    # ゴールを統合
    combined_goals = subtask1.goals + subtask2.goals
    
    # ランドマークを統合
    combined_landmarks = subtask1.landmark_predicates.union(subtask2.landmark_predicates)
    
    # role_signatureは最初のものを使用（または共通部分）
    role_signature = subtask1.role_signature.copy()
    for key, value in subtask2.role_signature.items():
        if key in role_signature and role_signature[key] != value:
            # 異なる値の場合は汎用的な値に変更
            role_signature[key] = f"{role_signature[key]}|{value}"
    
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