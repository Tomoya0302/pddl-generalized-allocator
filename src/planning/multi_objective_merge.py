"""
多目的最適化サブタスク統合処理
seedベースで異なる最適化戦略を実現するドメイン汎化システム
"""
import random
from typing import List, Dict, Set, Tuple, Optional
from .subtasks import SubTask
from .task import GroundAtom, PlanningTask
from .constraint_aware_merge import (
    extract_binary_constraints, 
    extract_unary_type_constraints,
    find_common_accessible_objects,
    is_compatible_for_merging
)
from ..utils.random_utils import RandomState


class OptimizationStrategy:
    """最適化戦略の基底クラス"""
    
    def __init__(self, rng: RandomState, randomness: float = 0.1):
        self.rng = rng
        self.randomness = randomness
    
    def compute_merge_score(self, subtask1: SubTask, subtask2: SubTask, 
                           task: PlanningTask, constraint_config: Dict,
                           current_subtask_count: int, target_count: int) -> float:
        """統合スコアを計算（戦略ごとに実装）"""
        raise NotImplementedError
    
    def should_continue_merging(self, subtasks: List[SubTask], 
                               target_count: int, iteration: int) -> bool:
        """統合を続けるべきかの判定（戦略ごとに実装）"""
        return len(subtasks) > target_count


class MinimizeSubtasksStrategy(OptimizationStrategy):
    """サブタスク数最小化戦略"""
    
    def compute_merge_score(self, subtask1: SubTask, subtask2: SubTask, 
                           task: PlanningTask, constraint_config: Dict,
                           current_subtask_count: int, target_count: int) -> float:
        base_score = 1000  # 統合自体を強く推奨
        
        # 制約互換性チェック
        compatibility_score = self._compute_compatibility_score(
            subtask1, subtask2, task, constraint_config
        )
        
        # ゴール数が多いペアほど高スコア（大きな統合を優先）
        total_goals = len(subtask1.goals) + len(subtask2.goals)
        size_bonus = total_goals * 50
        
        # ランダムネス
        random_factor = 1.0 + (self.rng.random() - 0.5) * self.randomness
        
        return (base_score + compatibility_score + size_bonus) * random_factor
    
    def _compute_compatibility_score(self, subtask1: SubTask, subtask2: SubTask,
                                   task: PlanningTask, constraint_config: Dict) -> float:
        score = 0
        
        # 共通ランドマークスコア
        common_landmarks = len(subtask1.landmark_predicates.intersection(
            subtask2.landmark_predicates))
        score += common_landmarks * 10
        
        # role_signature互換性
        if subtask1.role_signature == subtask2.role_signature:
            score += 100
        
        return score


class BalancedStrategy(OptimizationStrategy):
    """バランス戦略：サブタスク数とゴール分散のバランス"""
    
    def compute_merge_score(self, subtask1: SubTask, subtask2: SubTask, 
                           task: PlanningTask, constraint_config: Dict,
                           current_subtask_count: int, target_count: int) -> float:
        base_score = 500
        
        # 制約互換性
        compatibility_score = self._compute_compatibility_score(
            subtask1, subtask2, task, constraint_config
        )
        
        # 適度なサイズの統合を優先
        total_goals = len(subtask1.goals) + len(subtask2.goals)
        optimal_size = 5  # 目標ゴール数
        size_score = 100 - abs(total_goals - optimal_size) * 10
        
        # 現在の進捗に応じた調整
        progress = (target_count - current_subtask_count) / max(target_count * 0.1, 1)
        progress_factor = 1.0 + progress * 0.5
        
        # ランダムネス
        random_factor = 1.0 + (self.rng.random() - 0.5) * self.randomness
        
        return (base_score + compatibility_score + size_score) * progress_factor * random_factor
    
    def _compute_compatibility_score(self, subtask1: SubTask, subtask2: SubTask,
                                   task: PlanningTask, constraint_config: Dict) -> float:
        score = 0
        
        # 制約ベースの互換性
        binary_constraints = constraint_config.get('binary_constraints', [])
        if binary_constraints:
            # 共通リソースの存在をチェック
            score += self._compute_resource_compatibility(
                subtask1, subtask2, task, constraint_config
            ) * 20
        
        # 類似性スコア
        common_landmarks = len(subtask1.landmark_predicates.intersection(
            subtask2.landmark_predicates))
        score += common_landmarks * 5
        
        return score
    
    def _compute_resource_compatibility(self, subtask1: SubTask, subtask2: SubTask,
                                      task: PlanningTask, constraint_config: Dict) -> float:
        # リソース共有度を計算
        goal_object_index = constraint_config.get('goal_object_index', 0)
        
        def extract_targets(goals):
            return [goal.args[goal_object_index] for goal in goals 
                    if hasattr(goal, 'args') and len(goal.args) > goal_object_index]
        
        targets1 = extract_targets(subtask1.goals)
        targets2 = extract_targets(subtask2.goals)
        all_targets = targets1 + targets2
        
        binary_constraints = constraint_config.get('binary_constraints', [])
        if not binary_constraints:
            return 0.5
        
        binary_constraint_map = extract_binary_constraints(task, binary_constraints)
        total_resources = 0
        
        for constraint_name in binary_constraints:
            if constraint_name in binary_constraint_map:
                common_resources = find_common_accessible_objects(
                    all_targets, binary_constraint_map[constraint_name], constraint_name
                )
                total_resources += len(common_resources)
        
        return min(total_resources / max(len(all_targets), 1), 1.0)


class DistributeGoalsStrategy(OptimizationStrategy):
    """ゴール分散戦略：各サブタスクのゴール数を均等化"""
    
    def compute_merge_score(self, subtask1: SubTask, subtask2: SubTask, 
                           task: PlanningTask, constraint_config: Dict,
                           current_subtask_count: int, target_count: int) -> float:
        
        # 小さなサブタスクの統合を優先
        size1, size2 = len(subtask1.goals), len(subtask2.goals)
        total_size = size1 + size2
        
        # 小さなサブタスク同士の統合を高スコア
        small_subtask_bonus = 0
        if size1 <= 2 or size2 <= 2:  # 小さなサブタスクがある場合
            small_subtask_bonus = 300
        
        # 統合後サイズが適度な場合にボーナス
        optimal_range_bonus = 0
        if 3 <= total_size <= 6:  # 適度なサイズ
            optimal_range_bonus = 200
        elif total_size > 8:  # 大きすぎる場合はペナルティ
            optimal_range_bonus = -100
        
        # 制約互換性
        compatibility_score = self._compute_compatibility_score(
            subtask1, subtask2, task, constraint_config
        )
        
        # ランダムネス
        random_factor = 1.0 + (self.rng.random() - 0.5) * self.randomness
        
        base_score = 400 + small_subtask_bonus + optimal_range_bonus + compatibility_score
        return base_score * random_factor
    
    def should_continue_merging(self, subtasks: List[SubTask], 
                               target_count: int, iteration: int) -> bool:
        if len(subtasks) <= target_count:
            return False
        
        # 小さなサブタスクがあるかチェック
        small_subtasks = [s for s in subtasks if len(s.goals) <= 2]
        if small_subtasks:
            return True  # 小さなサブタスクがある間は統合を続ける
        
        # 分散が大きい場合も統合を続ける
        sizes = [len(s.goals) for s in subtasks]
        if sizes:
            variance = sum((size - sum(sizes)/len(sizes))**2 for size in sizes) / len(sizes)
            return variance > 4.0  # 分散が大きい場合
        
        return False
    
    def _compute_compatibility_score(self, subtask1: SubTask, subtask2: SubTask,
                                   task: PlanningTask, constraint_config: Dict) -> float:
        # 基本的な互換性スコア
        common_landmarks = len(subtask1.landmark_predicates.intersection(
            subtask2.landmark_predicates))
        return common_landmarks * 8


class AutoStrategy(OptimizationStrategy):
    """自動戦略：seedに基づいて他の戦略を選択"""
    
    def __init__(self, rng: RandomState, randomness: float = 0.1):
        super().__init__(rng, randomness)
        
        # seedに基づいて戦略を選択
        strategies = [
            MinimizeSubtasksStrategy(rng, randomness),
            BalancedStrategy(rng, randomness),
            DistributeGoalsStrategy(rng, randomness)
        ]
        
        self.selected_strategy = self.rng.choice(strategies)
        self.strategy_name = self.selected_strategy.__class__.__name__
    
    def compute_merge_score(self, subtask1: SubTask, subtask2: SubTask, 
                           task: PlanningTask, constraint_config: Dict,
                           current_subtask_count: int, target_count: int) -> float:
        return self.selected_strategy.compute_merge_score(
            subtask1, subtask2, task, constraint_config, current_subtask_count, target_count
        )
    
    def should_continue_merging(self, subtasks: List[SubTask], 
                               target_count: int, iteration: int) -> bool:
        return self.selected_strategy.should_continue_merging(subtasks, target_count, iteration)


def get_optimization_strategy(strategy_name: str, rng: RandomState, 
                             randomness: float = 0.1) -> OptimizationStrategy:
    """最適化戦略を取得"""
    strategies = {
        "minimize_subtasks": MinimizeSubtasksStrategy,
        "balanced": BalancedStrategy,
        "distribute_goals": DistributeGoalsStrategy,
        "auto": AutoStrategy
    }
    
    if strategy_name not in strategies:
        strategy_name = "balanced"  # デフォルト
    
    return strategies[strategy_name](rng, randomness)


def multi_objective_merge_subtasks(subtasks: List[SubTask],
                                  task: PlanningTask,
                                  max_goals_per_subtask: int = 10,
                                  target_subtask_count: int = None,
                                  constraint_config: Dict = None,
                                  strategy_name: str = "balanced",
                                  rng: RandomState = None,
                                  randomness: float = 0.1) -> Tuple[List[SubTask], str]:
    """
    多目的最適化サブタスク統合のメイン関数
    
    Returns:
        Tuple[統合後のサブタスクリスト, 使用された戦略名]
    """
    if not subtasks:
        return subtasks, strategy_name
    
    if rng is None:
        rng = RandomState(42)
    
    # 制約設定のデフォルト値
    if constraint_config is None:
        constraint_config = {
            'binary_constraints': ['reachable'],
            'type_constraints': ['object_type'],
            'goal_object_index': 0
        }
    
    # 戦略を取得
    strategy = get_optimization_strategy(strategy_name, rng, randomness)
    actual_strategy_name = getattr(strategy, 'strategy_name', strategy.__class__.__name__)
    
    print(f"Debug: Using optimization strategy: {actual_strategy_name}")
    
    # Phase 1: 同一role_signature内での統合
    merged = _merge_within_same_role_signature_multi_objective(
        subtasks, task, max_goals_per_subtask, constraint_config, strategy
    )
    
    # Phase 2: 異なるrole_signature間での戦略的統合
    merged = _strategic_cross_role_merge(
        merged, task, max_goals_per_subtask, constraint_config, strategy, target_subtask_count
    )
    
    return merged, actual_strategy_name


def _merge_within_same_role_signature_multi_objective(subtasks: List[SubTask], 
                                                     task: PlanningTask,
                                                     max_goals_per_subtask: int,
                                                     constraint_config: Dict,
                                                     strategy: OptimizationStrategy) -> List[SubTask]:
    """同一role_signature内での戦略的統合"""
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
        
        # グループ内で戦略的統合
        group_merged = _strategic_merge_group(
            group, task, max_goals_per_subtask, constraint_config, strategy, next_id
        )
        merged.extend(group_merged)
        next_id += len(group_merged)
    
    return merged


def _strategic_cross_role_merge(subtasks: List[SubTask],
                               task: PlanningTask,
                               max_goals_per_subtask: int,
                               constraint_config: Dict,
                               strategy: OptimizationStrategy,
                               target_count: int) -> List[SubTask]:
    """戦略的な異role統合"""
    merged = list(subtasks)
    next_id = max(s.id for s in subtasks) + 1
    iteration = 0
    
    while strategy.should_continue_merging(merged, target_count or len(merged), iteration):
        if len(merged) <= 1:
            break
            
        best_pair = None
        best_score = float('-inf')
        
        # 戦略的な最適ペアを探索
        for i in range(len(merged)):
            for j in range(i + 1, len(merged)):
                if is_compatible_for_merging(
                    merged[i], merged[j], task, max_goals_per_subtask, constraint_config
                ):
                    score = strategy.compute_merge_score(
                        merged[i], merged[j], task, constraint_config,
                        len(merged), target_count or len(merged)
                    )
                    if score > best_score:
                        best_score = score
                        best_pair = (i, j)
        
        if best_pair is None:
            break  # これ以上統合できない
        
        # ペアを統合
        i, j = best_pair
        merged_subtask = _merge_two_strategic(merged[i], merged[j], task, next_id, constraint_config)
        
        # 古いサブタスクを削除し、新しいものを追加
        merged = [merged[k] for k in range(len(merged)) if k != i and k != j]
        merged.append(merged_subtask)
        next_id += 1
        iteration += 1
        
        # 無限ループ防止
        if iteration > len(subtasks) * 2:
            break
    
    return merged


def _strategic_merge_group(group: List[SubTask],
                          task: PlanningTask,
                          max_goals_per_subtask: int,
                          constraint_config: Dict,
                          strategy: OptimizationStrategy,
                          start_id: int) -> List[SubTask]:
    """戦略的グループ内統合"""
    merged = []
    remaining = list(group)
    next_id = start_id
    
    while remaining:
        current = remaining.pop(0)
        
        # 戦略に基づいて最適な統合相手を探す
        best_candidate = None
        best_score = float('-inf')
        best_idx = -1
        
        for i, candidate in enumerate(remaining):
            if is_compatible_for_merging(current, candidate, task, max_goals_per_subtask, constraint_config):
                score = strategy.compute_merge_score(
                    current, candidate, task, constraint_config, len(remaining), len(group)
                )
                if score > best_score:
                    best_score = score
                    best_candidate = candidate
                    best_idx = i
        
        if best_candidate and best_score > 0:
            current = _merge_two_strategic(current, best_candidate, task, next_id, constraint_config)
            remaining.pop(best_idx)
            next_id += 1
        
        merged.append(current)
    
    return merged


def _merge_two_strategic(subtask1: SubTask,
                        subtask2: SubTask,
                        task: PlanningTask,
                        new_id: int,
                        constraint_config: Dict) -> SubTask:
    """戦略的な2サブタスク統合"""
    # ゴールを統合
    combined_goals = subtask1.goals + subtask2.goals
    
    # ランドマークを統合
    combined_landmarks = subtask1.landmark_predicates.union(subtask2.landmark_predicates)
    
    # 元のrole_signatureを保持・統合
    role_signature = _merge_role_signatures(subtask1.role_signature, subtask2.role_signature)
    
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


def _merge_role_signatures(signature1: Dict[str, str], signature2: Dict[str, str]) -> Dict[str, str]:
    """2つのrole_signatureを統合"""
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


def _compute_strategic_role_signature(goals: List[GroundAtom],
                                     task: PlanningTask,
                                     constraint_config: Dict) -> Dict[str, str]:
    """戦略的role_signature計算（レガシー用：現在は使用しない）"""
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
    """制約名からrole_signatureのキー名を推定"""
    if 'reachable' in constraint_name.lower():
        return 'location'
    elif 'accessible' in constraint_name.lower():
        return 'location'
    else:
        return constraint_name.lower() + '_resource'


def _infer_role_key_from_type_constraint(constraint_name: str) -> str:
    """タイプ制約名からrole_signatureのキー名を推定"""
    if constraint_name.endswith('_type'):
        return constraint_name[:-5]  # '_type'を除去
    else:
        return constraint_name.lower()