"""
解の特徴量抽出モジュール
階層的クラスタリングのための特徴量を抽出
"""
import json
import numpy as np
from typing import List, Dict, Any, Tuple
from collections import Counter
import statistics
from pathlib import Path


class SolutionFeatureExtractor:
    """解の特徴量抽出クラス"""
    
    def __init__(self, config, role_config_path: str = None):
        self.config = config
        self.role_config = None
        
        if role_config_path and Path(role_config_path).exists():
            with open(role_config_path, 'r') as f:
                self.role_config = json.load(f)
    
    def extract_features(self, solution_data: Dict[str, Any]) -> Dict[str, float]:
        """1つの解から特徴量を抽出"""
        features = {}
        
        subtasks = solution_data.get('subtasks', [])
        assignment = solution_data.get('assignment', {})
        
        # 基本統計特徴量
        if self.config.feature_extraction.use_subtask_count:
            features['subtask_count'] = len(subtasks)
        
        if self.config.feature_extraction.use_goal_variance:
            goal_counts = [len(subtask['goals']) for subtask in subtasks]
            features['goal_variance'] = np.var(goal_counts) if goal_counts else 0.0
        
        if self.config.feature_extraction.use_goal_mean:
            goal_counts = [len(subtask['goals']) for subtask in subtasks]
            features['goal_mean'] = np.mean(goal_counts) if goal_counts else 0.0
        
        if self.config.feature_extraction.use_goal_min_max:
            goal_counts = [len(subtask['goals']) for subtask in subtasks]
            if goal_counts:
                features['goal_min'] = min(goal_counts)
                features['goal_max'] = max(goal_counts)
                features['goal_range'] = max(goal_counts) - min(goal_counts)
            else:
                features.update({'goal_min': 0, 'goal_max': 0, 'goal_range': 0})
        
        if self.config.feature_extraction.use_agent_balance:
            agent_counts = Counter(assignment.values())
            if agent_counts:
                workloads = list(agent_counts.values())
                features['agent_balance_variance'] = np.var(workloads)
                features['agent_balance_max_min_ratio'] = max(workloads) / max(min(workloads), 1)
                features['num_active_agents'] = len(agent_counts)
            else:
                features.update({
                    'agent_balance_variance': 0,
                    'agent_balance_max_min_ratio': 1,
                    'num_active_agents': 0
                })
        
        # 汎用的な構造特徴量
        if self.config.feature_extraction.use_structural_features:
            structural_features = self._extract_structural_features(subtasks)
            features.update(structural_features)
        
        return features
    
    def _extract_structural_features(self, subtasks: List[Dict[str, Any]]) -> Dict[str, float]:
        """汎用的な構造特徴量を抽出"""
        features = {}
        
        if not subtasks:
            return features
        
        # role_signatureの分析
        role_signatures = [subtask.get('role_signature', {}) for subtask in subtasks]
        
        # 役割の多様性（汎用的）
        if 'role_diversity' in self.config.feature_extraction.structural_feature_types:
            role_diversity = self._compute_role_diversity(role_signatures)
            features.update(role_diversity)
        
        # role_signatureの複合性（複数値を含む割合）
        if 'role_complexity' in self.config.feature_extraction.structural_feature_types:
            complexity_features = self._compute_role_complexity(role_signatures)
            features.update(complexity_features)
        
        # サブタスク間の類似性
        if 'subtask_similarity' in self.config.feature_extraction.structural_feature_types:
            similarity_features = self._compute_subtask_similarity(subtasks)
            features.update(similarity_features)
        
        return features
    
    def _compute_role_diversity(self, role_signatures: List[Dict[str, str]]) -> Dict[str, float]:
        """役割の多様性を汎用的に計算"""
        features = {}
        
        if not role_signatures:
            return {
                'unique_role_signature_count': 0,
                'role_signature_entropy': 0,
                'avg_role_attributes_per_subtask': 0
            }
        
        # role_signatureを文字列に変換して多様性を計算
        signature_strings = []
        total_attributes = 0
        
        for signature in role_signatures:
            if signature:
                # role_signatureを一意な文字列に変換
                signature_items = []
                for key, value in sorted(signature.items()):
                    if value:  # 空でない値のみ
                        if '|' in str(value):
                            # 複合値の場合は分割してカウント
                            signature_items.extend([f"{key}:{v}" for v in str(value).split('|')])
                            total_attributes += len(str(value).split('|'))
                        else:
                            signature_items.append(f"{key}:{value}")
                            total_attributes += 1
                
                signature_string = "|".join(signature_items) if signature_items else "empty"
                signature_strings.append(signature_string)
            else:
                signature_strings.append("empty")
        
        # 多様性の計算
        unique_signatures = set(signature_strings)
        features['unique_role_signature_count'] = len(unique_signatures)
        features['role_signature_entropy'] = self._compute_entropy(Counter(signature_strings))
        features['avg_role_attributes_per_subtask'] = total_attributes / len(role_signatures) if role_signatures else 0
        
        return features
    
    def _compute_role_complexity(self, role_signatures: List[Dict[str, str]]) -> Dict[str, float]:
        """role_signatureの複合性を計算"""
        features = {}
        
        if not role_signatures:
            return {'complex_role_ratio': 0, 'avg_role_complexity': 0}
        
        complex_count = 0
        total_complexity = 0
        
        for signature in role_signatures:
            is_complex = False
            signature_complexity = 0
            
            for key, value in signature.items():
                if '|' in str(value):  # 複合値
                    is_complex = True
                    signature_complexity += len(str(value).split('|'))
                else:
                    signature_complexity += 1
            
            if is_complex:
                complex_count += 1
            total_complexity += signature_complexity
        
        features['complex_role_ratio'] = complex_count / len(role_signatures)
        features['avg_role_complexity'] = total_complexity / len(role_signatures)
        
        return features
    
    def _compute_subtask_similarity(self, subtasks: List[Dict[str, Any]]) -> Dict[str, float]:
        """サブタスク間の類似性を計算"""
        features = {}
        
        if len(subtasks) < 2:
            return {'avg_subtask_similarity': 0, 'similarity_variance': 0}
        
        similarities = []
        
        for i in range(len(subtasks)):
            for j in range(i + 1, len(subtasks)):
                sim = self._compute_pairwise_similarity(subtasks[i], subtasks[j])
                similarities.append(sim)
        
        if similarities:
            features['avg_subtask_similarity'] = np.mean(similarities)
            features['similarity_variance'] = np.var(similarities)
        else:
            features.update({'avg_subtask_similarity': 0, 'similarity_variance': 0})
        
        return features
    
    def _compute_pairwise_similarity(self, subtask1: Dict[str, Any], subtask2: Dict[str, Any]) -> float:
        """2つのサブタスク間の類似性を計算"""
        # ランドマークの共通度
        landmarks1 = set(subtask1.get('landmark_predicates', []))
        landmarks2 = set(subtask2.get('landmark_predicates', []))
        
        if landmarks1 or landmarks2:
            landmark_similarity = len(landmarks1 & landmarks2) / len(landmarks1 | landmarks2)
        else:
            landmark_similarity = 1.0
        
        # role_signatureの類似度
        role1 = subtask1.get('role_signature', {})
        role2 = subtask2.get('role_signature', {})
        
        role_similarity = self._compute_role_similarity(role1, role2)
        
        # ゴール数の類似度（正規化済み）
        goals1 = len(subtask1.get('goals', []))
        goals2 = len(subtask2.get('goals', []))
        max_goals = max(goals1, goals2, 1)
        goal_similarity = 1 - abs(goals1 - goals2) / max_goals
        
        # 重み付き平均
        return 0.4 * landmark_similarity + 0.4 * role_similarity + 0.2 * goal_similarity
    
    def _compute_role_similarity(self, role1: Dict[str, str], role2: Dict[str, str]) -> float:
        """role_signature間の類似度を計算"""
        if not role1 and not role2:
            return 1.0
        
        all_keys = set(role1.keys()) | set(role2.keys())
        if not all_keys:
            return 1.0
        
        matches = 0
        for key in all_keys:
            val1 = set(str(role1.get(key, '')).split('|'))
            val2 = set(str(role2.get(key, '')).split('|'))
            
            if val1 and val2:
                similarity = len(val1 & val2) / len(val1 | val2)
                matches += similarity
        
        return matches / len(all_keys)
    
    def _compute_entropy(self, counter: Counter) -> float:
        """エントロピーを計算"""
        total = sum(counter.values())
        if total == 0:
            return 0.0
        
        entropy = 0.0
        for count in counter.values():
            if count > 0:
                p = count / total
                entropy -= p * np.log2(p)
        
        return entropy


def extract_features_from_directory(results_dir: str, config, role_config_path: str = None) -> Tuple[np.ndarray, List[str], List[str]]:
    """ディレクトリ内の全ての解から特徴量を抽出
    
    Returns:
        features: 特徴量行列 (n_samples, n_features)
        feature_names: 特徴量名のリスト
        solution_names: 解のファイル名リスト
    """
    extractor = SolutionFeatureExtractor(config, role_config_path)
    
    results_path = Path(results_dir)
    result_files = sorted(results_path.glob(config.result_file_pattern))
    
    all_features = []
    solution_names = []
    
    for result_file in result_files:
        try:
            with open(result_file, 'r') as f:
                solution_data = json.load(f)
            
            features = extractor.extract_features(solution_data)
            all_features.append(features)
            solution_names.append(result_file.stem)
            
        except Exception as e:
            print(f"Warning: Failed to extract features from {result_file}: {e}")
            continue
    
    if not all_features:
        return np.array([]), [], []
    
    # 全特徴量名を収集
    all_feature_names = set()
    for features in all_features:
        all_feature_names.update(features.keys())
    
    feature_names = sorted(list(all_feature_names))
    
    # 特徴量行列を作成
    feature_matrix = []
    for features in all_features:
        feature_vector = [features.get(name, 0.0) for name in feature_names]
        feature_matrix.append(feature_vector)
    
    return np.array(feature_matrix), feature_names, solution_names