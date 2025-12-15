# src/features/domain_free_features.py

"""
Domain-free feature computation for solution analysis.

- subtasks:   List[Dict]  （JSON から読み込んだそのままの形式）
- assignment: Dict[subtask_id, agent_name] など（values がエージェントID）

16個の特徴量を一括で計算して返す：
- subtask_count
- goal_variance, goal_mean, goal_min, goal_max, goal_range
- agent_balance_variance, agent_balance_max_min_ratio, num_active_agents
- unique_role_signature_count, role_signature_entropy, avg_role_attributes_per_subtask
- complex_role_ratio, avg_role_complexity
- avg_subtask_similarity, similarity_variance
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional
from collections import Counter
import numpy as np


def compute_domain_free_features(
    subtasks: List[Dict[str, Any]],
    assignment: Optional[Dict[Any, Any]] = None,
) -> Dict[str, float]:
    """
    サブタスク集合 + 割当結果から 16 個の domain-free features を計算する。
    subtasks / assignment は JSON の dict をそのまま渡してよい。
    """
    features: Dict[str, float] = {}

    # ------------------------
    # 1. 基本統計特徴量
    # ------------------------
    # subtask_count
    features["subtask_count"] = float(len(subtasks))

    # goal_* 系
    goal_counts = [len(st.get("goals", [])) for st in subtasks]
    if goal_counts:
        arr = np.array(goal_counts, dtype=float)
        features["goal_variance"] = float(np.var(arr))
        features["goal_mean"] = float(np.mean(arr))
        features["goal_min"] = float(np.min(arr))
        features["goal_max"] = float(np.max(arr))
        features["goal_range"] = float(np.max(arr) - np.min(arr))
    else:
        features["goal_variance"] = 0.0
        features["goal_mean"] = 0.0
        features["goal_min"] = 0.0
        features["goal_max"] = 0.0
        features["goal_range"] = 0.0

    # agent_balance 系
    if assignment:
        agent_counts = Counter(assignment.values())
        if agent_counts:
            workloads = np.array(list(agent_counts.values()), dtype=float)
            features["agent_balance_variance"] = float(np.var(workloads))
            features["agent_balance_max_min_ratio"] = float(
                workloads.max() / max(workloads.min(), 1.0)
            )
            features["num_active_agents"] = float(len(agent_counts))
        else:
            features["agent_balance_variance"] = 0.0
            features["agent_balance_max_min_ratio"] = 1.0
            features["num_active_agents"] = 0.0
    else:
        # 割当がまだ無い場合
        features["agent_balance_variance"] = 0.0
        features["agent_balance_max_min_ratio"] = 1.0
        features["num_active_agents"] = 0.0

    # ------------------------
    # 2. 構造系特徴量（role / similarity）
    # ------------------------
    structural = _compute_structural_features(subtasks)
    features.update(structural)

    return features


# ============================================================
# 構造系特徴量
# ============================================================

def _compute_structural_features(subtasks: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    汎用的な構造特徴量をまとめて計算する。

    - unique_role_signature_count
    - role_signature_entropy
    - avg_role_attributes_per_subtask
    - complex_role_ratio
    - avg_role_complexity
    - avg_subtask_similarity
    - similarity_variance
    """
    features: Dict[str, float] = {}

    if not subtasks:
        features["unique_role_signature_count"] = 0.0
        features["role_signature_entropy"] = 0.0
        features["avg_role_attributes_per_subtask"] = 0.0
        features["complex_role_ratio"] = 0.0
        features["avg_role_complexity"] = 0.0
        features["avg_subtask_similarity"] = 0.0
        features["similarity_variance"] = 0.0
        return features

    role_signatures = [st.get("role_signature", {}) for st in subtasks]

    role_div = _compute_role_diversity(role_signatures)
    role_complex = _compute_role_complexity(role_signatures)
    sim_feats = _compute_subtask_similarity(subtasks)

    features.update(role_div)
    features.update(role_complex)
    features.update(sim_feats)

    return features


# ============================================================
# role_signature の多様性
# ============================================================

def _compute_role_diversity(
    role_signatures: List[Dict[str, str]]
) -> Dict[str, float]:
    """
    役割の多様性を汎用的に計算（元の feature_extractor と同じロジック）。
    - unique_role_signature_count
    - role_signature_entropy
    - avg_role_attributes_per_subtask
    """
    if not role_signatures:
        return {
            "unique_role_signature_count": 0.0,
            "role_signature_entropy": 0.0,
            "avg_role_attributes_per_subtask": 0.0,
        }

    signature_strings: List[str] = []
    total_attributes = 0

    for signature in role_signatures:
        if signature:
            signature_items: List[str] = []
            for key, value in sorted(signature.items()):
                if value is None:
                    continue
                value_str = str(value)
                if "|" in value_str:
                    parts = [v for v in value_str.split("|") if v]
                    signature_items.extend(f"{key}:{v}" for v in parts)
                    total_attributes += len(parts)
                else:
                    signature_items.append(f"{key}:{value_str}")
                    total_attributes += 1

            signature_string = "|".join(signature_items) if signature_items else "empty"
            signature_strings.append(signature_string)
        else:
            signature_strings.append("empty")

    counter = Counter(signature_strings)
    unique_signatures = set(signature_strings)

    unique_count = float(len(unique_signatures))
    entropy = _compute_entropy(counter)
    avg_attr = (
        float(total_attributes) / float(len(role_signatures))
        if role_signatures
        else 0.0
    )

    return {
        "unique_role_signature_count": unique_count,
        "role_signature_entropy": entropy,
        "avg_role_attributes_per_subtask": avg_attr,
    }


# ============================================================
# role_signature の複雑さ
# ============================================================

def _compute_role_complexity(
    role_signatures: List[Dict[str, str]]
) -> Dict[str, float]:
    """
    role_signature の「複合性」を計算。
    - complex_role_ratio
    - avg_role_complexity
    """
    if not role_signatures:
        return {"complex_role_ratio": 0.0, "avg_role_complexity": 0.0}

    complex_count = 0
    total_complexity = 0

    for signature in role_signatures:
        is_complex = False
        signature_complexity = 0

        for _, value in signature.items():
            value_str = str(value)
            if "|" in value_str:
                is_complex = True
                signature_complexity += len([v for v in value_str.split("|") if v])
            else:
                signature_complexity += 1

        if is_complex:
            complex_count += 1
        total_complexity += signature_complexity

    n = len(role_signatures)
    complex_ratio = complex_count / n if n > 0 else 0.0
    avg_complexity = total_complexity / n if n > 0 else 0.0

    return {
        "complex_role_ratio": float(complex_ratio),
        "avg_role_complexity": float(avg_complexity),
    }


# ============================================================
# サブタスク間の類似度
# ============================================================

def _compute_subtask_similarity(
    subtasks: List[Dict[str, Any]]
) -> Dict[str, float]:
    """
    サブタスク間の類似性を計算。
    - avg_subtask_similarity
    - similarity_variance
    """
    if len(subtasks) < 2:
        return {"avg_subtask_similarity": 0.0, "similarity_variance": 0.0}

    similarities = _compute_pairwise_similarity(subtasks)
    if not similarities:
        return {"avg_subtask_similarity": 0.0, "similarity_variance": 0.0}

    arr = np.array(similarities, dtype=float)
    return {
        "avg_subtask_similarity": float(arr.mean()),
        "similarity_variance": float(arr.var()),
    }


def _compute_pairwise_similarity(
    subtasks: List[Dict[str, Any]]
) -> List[float]:
    """
    すべてのサブタスクペア (i, j), i < j の類似度を計算。
    元の実装と同様に、
      0.4 * landmark_similarity
    + 0.4 * role_similarity
    + 0.2 * goal_similarity
    を使う。
    """
    sims: List[float] = []
    n = len(subtasks)

    for i in range(n):
        st1 = subtasks[i]
        for j in range(i + 1, n):
            st2 = subtasks[j]

            # ランドマークの共通度 (Jaccard)
            landmarks1 = set(st1.get("landmark_predicates", []))
            landmarks2 = set(st2.get("landmark_predicates", []))
            if landmarks1 or landmarks2:
                inter = len(landmarks1 & landmarks2)
                union = len(landmarks1 | landmarks2)
                landmark_similarity = inter / union if union > 0 else 0.0
            else:
                landmark_similarity = 1.0

            # role_signature の類似度
            role1 = st1.get("role_signature", {}) or {}
            role2 = st2.get("role_signature", {}) or {}
            role_similarity = _compute_role_similarity(role1, role2)

            # ゴール数の類似度
            goals1 = len(st1.get("goals", []))
            goals2 = len(st2.get("goals", []))
            max_goals = max(goals1, goals2, 1)
            goal_similarity = 1.0 - abs(goals1 - goals2) / max_goals

            sim = 0.4 * landmark_similarity + 0.4 * role_similarity + 0.2 * goal_similarity
            sims.append(sim)

    return sims


def _compute_role_similarity(
    role1: Dict[str, str], role2: Dict[str, str]
) -> float:
    """
    role_signature 間の類似度を計算。
    元の実装と同様：
    - key ごとに値を '|' で分割して集合にし、
    - Jaccard 類似度を key 平均する。
    """
    if not role1 and not role2:
        return 1.0

    all_keys = set(role1.keys()) | set(role2.keys())
    if not all_keys:
        return 1.0

    matches = 0.0
    for key in all_keys:
        val1 = set(str(role1.get(key, "")).split("|")) if role1.get(key) is not None else set()
        val2 = set(str(role2.get(key, "")).split("|")) if role2.get(key) is not None else set()
        # 空集合は「情報なし」とみなしてスキップ
        if val1 and val2:
            inter = len(val1 & val2)
            union = len(val1 | val2)
            if union > 0:
                similarity = inter / union
                matches += similarity

    return matches / len(all_keys) if all_keys else 1.0


# ============================================================
# 汎用ユーティリティ
# ============================================================

def _compute_entropy(counter: Counter) -> float:
    """
    Counter からエントロピー（log2）を計算。
    """
    total = sum(counter.values())
    if total == 0:
        return 0.0

    entropy = 0.0
    for count in counter.values():
        if count <= 0:
            continue
        p = count / total
        entropy -= p * np.log2(p)
    return float(entropy)
