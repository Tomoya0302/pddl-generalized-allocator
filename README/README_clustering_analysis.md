# 階層的クラスタリング分析システム

## 概要
PDDL Multi-Agent Task Decomposition & Allocationシステムで生成された多様な解を階層的クラスタリングで分析するシステム。

## 分析結果サマリー

### 分析対象
- **解の総数**: 5個 (result_000 ~ result_004)  
- **特徴量数**: 20個
- **クラスター数**: 2個 (自動決定、silhouette法)
- **クラスタリング手法**: Ward法 + Euclidean距離

### クラスター構成

#### Cluster 1 (4解)
- **構成**: result_001, result_002, result_003, result_004
- **特徴**:
  - 類似度分散: 低 (-0.49)
  - 役割シグネチャエントロピー: 中 (0.49)
  - サブタスク間平均類似度: 高 (0.48)
- **解釈**: 類似した役割構成を持つ効率的・集約型の解

#### Cluster 2 (1解)
- **構成**: result_000
- **特徴**:
  - 類似度分散: 高 (1.95)
  - 役割シグネチャエントロピー: 低 (-1.94)
  - サブタスク間平均類似度: 低 (-1.94)
- **解釈**: 多様な役割構成を持つ柔軟性重視の分散型解

## 主要特徴量

### 基本統計特徴量
1. **agent_balance_max_min_ratio**: エージェント負荷バランス比
2. **agent_balance_variance**: エージェント負荷分散
3. **goal_variance**: ゴール数分散
4. **subtask_count**: サブタスク総数
5. **num_active_agents**: アクティブエージェント数

### 汎用的な構造特徴量
1. **role_signature_entropy**: 役割シグネチャの多様性（エントロピー）
2. **unique_role_signature_count**: ユニークな役割シグネチャ数
3. **avg_role_attributes_per_subtask**: サブタスクあたり平均役割属性数
4. **avg_role_complexity**: 役割の複合性
5. **avg_subtask_similarity**: サブタスク間類似度
6. **similarity_variance**: サブタスク類似度の分散

## 生成ファイル

### CSVファイル
- [`solution_clustering_features.csv`](../clustering_analysis/solution_clustering_features.csv): 全特徴量データ
- [`solution_clustering_cluster_assignments.csv`](../clustering_analysis/solution_clustering_cluster_assignments.csv): クラスター割り当て結果

### レポート
- [`solution_clustering_summary.txt`](../clustering_analysis/solution_clustering_summary.txt): 分析サマリーレポート

### 可視化
- [`solution_clustering_dendrogram.png`](../clustering_analysis/solution_clustering_dendrogram.png): 階層構造デンドログラム
- [`solution_clustering_scatter.png`](../clustering_analysis/solution_clustering_scatter.png): PCA散布図プロット
- [`solution_clustering_feature_importance.png`](../clustering_analysis/solution_clustering_feature_importance.png): 特徴量重要度

## 実行方法

### 基本実行
```bash
# 基本的なクラスタリング分析
python -m src.analyze.cluster_solutions --config configs/clustering_analysis_config.yaml

# カスタム設定での分析
python -m src.analyze.cluster_solutions --config configs/custom_clustering_config.yaml
```

### 設定ファイル
[`configs/clustering_analysis_config.yaml`](../configs/clustering_analysis_config.yaml)で以下をカスタマイズ可能:

```yaml
# 特徴量抽出設定
feature_extraction:
  normalize_features: true
  normalization_method: "standard"  # standard, minmax, robust
  use_structural_features: true
  role_config_file: "configs/role_configs/example_roles.json"
  structural_feature_types:
    - "role_diversity"
    - "role_complexity"
    - "subtask_similarity"

# クラスタリング設定  
clustering:
  method: "ward"  # ward, complete, average, single
  metric: "euclidean"
  auto_cluster_method: "silhouette"  # silhouette, elbow, dendrogram_gap
  min_clusters: 2
  max_clusters: 8

# 可視化設定
visualization:
  create_dendrogram: true
  create_scatter_plots: true  
  create_feature_importance: true
  style: "seaborn"
  color_palette: "Set1"
```

## システム構成

### コアモジュール
- [`src/analyze/hierarchical_clustering.py`](../src/analyze/hierarchical_clustering.py): メイン分析エンジン
- [`src/analyze/feature_extractor.py`](../src/analyze/feature_extractor.py): 特徴量抽出
- [`src/analyze/cluster_solutions.py`](../src/analyze/cluster_solutions.py): CLIインターフェース

### 設定スキーマ
- [`src/config/clustering_analysis_schema.py`](../src/config/clustering_analysis_schema.py): 設定バリデーション

## 分析結果の解釈

### 重要な発見
1. **result_000は明確に他と異なる特性**: 役割構成の多様性とタスク分散パターン
2. **result_001-004は類似パターン**: 役割の統一性を重視した集約型戦略
3. **特徴量重要度**: 類似度分散、役割シグネチャエントロピー、サブタスク類似度が最重要

### 実用的示唆
- **統一性 vs 多様性のトレードオフ**: Cluster1は統一性、Cluster2は多様性
- **役割配分戦略**: 集約型 vs 分散型の明確な差異
- **最適化方向性**: システム要件に応じてクラスター選択が可能

## 技術仕様

### 依存関係
- scikit-learn: 機械学習・クラスタリング
- scipy: 統計・階層クラスタリング
- matplotlib, seaborn: データ可視化  
- pandas, numpy: データ処理

### パフォーマンス
- **処理時間**: ~30秒 (5解、20特徴量)
- **メモリ使用量**: 軽量 (~10MB)
- **スケーラビリティ**: 数百解まで対応可能