""" 解の特徴量抽出モジュール
階層的クラスタリングのための特徴量を抽出
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

import numpy as np

from src.features.domain_free_features import compute_domain_free_features


class SolutionFeatureExtractor:
    """解の特徴量抽出クラス"""

    def __init__(self, config, role_config_path: Optional[str] = None):
        self.config = config
        self.role_config: Optional[Dict[str, Any]] = None

        # role_config は現状では直接は使っていないが、
        # 互換性のために読み込んで保持しておく
        if role_config_path and Path(role_config_path).exists():
            with open(role_config_path, "r") as f:
                self.role_config = json.load(f)

    def extract_features(self, solution_data: Dict[str, Any]) -> Dict[str, float]:
        """
        1つの解から特徴量を抽出する。

        - JSON の dict から subtasks / assignment を取得
        - domain-free-feature モジュールで 16特徴量を一括計算
        - clustering_analysis_config.yaml の feature_extraction 設定に従って
          利用する特徴量だけを選択して返す
        """
        subtasks_data = solution_data.get("subtasks", [])
        assignment_data = solution_data.get("assignment", {})

        # domain-free features を全て計算
        all_features = compute_domain_free_features(
            subtasks=subtasks_data,
            assignment=assignment_data,
        )

        features: Dict[str, float] = {}
        fe_cfg = self.config.feature_extraction

        # --------------------------------------------------
        # 基本統計特徴量
        # --------------------------------------------------
        if getattr(fe_cfg, "use_subtask_count", False):
            if "subtask_count" in all_features:
                features["subtask_count"] = float(all_features["subtask_count"])

        if getattr(fe_cfg, "use_goal_variance", False):
            if "goal_variance" in all_features:
                features["goal_variance"] = float(all_features["goal_variance"])

        if getattr(fe_cfg, "use_goal_mean", False):
            if "goal_mean" in all_features:
                features["goal_mean"] = float(all_features["goal_mean"])

        if getattr(fe_cfg, "use_goal_min_max", False):
            for k in ("goal_min", "goal_max", "goal_range"):
                if k in all_features:
                    features[k] = float(all_features[k])

        if getattr(fe_cfg, "use_agent_balance", False):
            for k in (
                "agent_balance_variance",
                "agent_balance_max_min_ratio",
                "num_active_agents",
            ):
                if k in all_features:
                    features[k] = float(all_features[k])

        # --------------------------------------------------
        # 構造特徴量（role / similarity 周り）
        # --------------------------------------------------
        if getattr(fe_cfg, "use_structural_features", False):
            # 互換性のため、structural_feature_types をグループ指定として扱う
            #
            # - "role_diversity"
            #     -> unique_role_signature_count
            #        role_signature_entropy
            #        avg_role_attributes_per_subtask
            # - "role_complexity"
            #     -> complex_role_ratio
            #        avg_role_complexity
            # - "subtask_similarity"
            #     -> avg_subtask_similarity
            #        similarity_variance
            structural_types = getattr(
                fe_cfg,
                "structural_feature_types",
                ["role_diversity", "role_complexity", "subtask_similarity"],
            )

            type_to_keys: Dict[str, List[str]] = {
                "role_diversity": [
                    "unique_role_signature_count",
                    "role_signature_entropy",
                    "avg_role_attributes_per_subtask",
                ],
                "role_complexity": [
                    "complex_role_ratio",
                    "avg_role_complexity",
                ],
                "subtask_similarity": [
                    "avg_subtask_similarity",
                    "similarity_variance",
                ],
            }

            for t in structural_types:
                for k in type_to_keys.get(t, []):
                    if k in all_features:
                        features[k] = float(all_features[k])

        return features


def extract_features_from_directory(
    results_dir: str,
    config,
    role_config_path: Optional[str] = None,
) -> Tuple[np.ndarray, List[str], List[str]]:
    """
    ディレクトリ内の全ての解から特徴量を抽出する。

    Parameters
    ----------
    results_dir : str
        result_*.json が格納されているディレクトリ
    config :
        ClusteringAnalysisConfig インスタンス
    role_config_path : Optional[str]
        role_config の JSON パス（オプション）

    Returns
    -------
    features : np.ndarray
        特徴量行列 (n_samples, n_features)
    feature_names : List[str]
        特徴量名のリスト
    solution_names : List[str]
        解のファイル名（拡張子なし）のリスト
    """
    extractor = SolutionFeatureExtractor(config, role_config_path)

    results_path = Path(results_dir)
    result_files = sorted(results_path.glob(config.result_file_pattern))

    all_features: List[Dict[str, float]] = []
    solution_names: List[str] = []

    for result_file in result_files:
        try:
            with open(result_file, "r") as f:
                solution_data = json.load(f)
            feats = extractor.extract_features(solution_data)
            all_features.append(feats)
            solution_names.append(result_file.stem)
        except Exception as e:
            print(f"Warning: Failed to extract features from {result_file}: {e}")
            continue

    if not all_features:
        return np.array([]), [], []

    # 全特徴量名を収集
    all_feature_names: set = set()
    for feats in all_features:
        all_feature_names.update(feats.keys())
    feature_names = sorted(list(all_feature_names))

    # 特徴量行列を作成（足りないものは 0.0 で埋める）
    feature_matrix: List[List[float]] = []
    for feats in all_features:
        vec = [float(feats.get(name, 0.0)) for name in feature_names]
        feature_matrix.append(vec)

    return np.array(feature_matrix, dtype=float), feature_names, solution_names
