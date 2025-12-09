# PDDL Multi-Agent Task Decomposition & Allocation - 実行ガイド

このドキュメントでは、システムの3つの主要機能の実行方法を詳しく説明します。

## 目次
1. [単一解の生成](#1-単一解の生成)
2. [多様解の生成](#2-多様解の生成) 
3. [階層的クラスタリング分析](#3-階層的クラスタリング分析)

---

## 1. 単一解の生成

単一のPDDLマルチエージェントタスク分解解を生成します。制約考慮型統合システムにより、制約を厳密に遵守したサブタスクの統合が行われます。

### 基本実行方法

```bash
# デフォルト設定での実行
python -m src.cli.main

# 設定ファイルを指定
python -m src.cli.main --config configs/default_config.yaml

# 結果をファイルに保存
python -m src.cli.main --config configs/default_config.yaml --output result.json
```

### パラメータ

| パラメータ | デフォルト値 | 説明 |
|-----------|-------------|------|
| `--config` | `configs/default_config.yaml` | 設定ファイルパス |
| `--output` | なし（標準出力） | 出力JSONファイルパス |

### 設定ファイル例

```yaml
# configs/default_config.yaml
pddl:
  domain_file: "pddl/small_weld_task/domain.pddl"
  problem_file: "pddl/small_weld_task/problem.pddl"

multiagent:
  agent_types: ["robot"]

clustering:
  random_seed: 42
  max_subtasks: 50
  max_goals_per_subtask: 15
  strategy: "auto"  # minimize_subtasks, balanced, distribute_goals, auto
  strategy_randomness: 0.2
  
  # 制約考慮型統合の設定
  merge_compatible_subtasks: true
  constraint_binary_predicates: ["reachable"]      # バイナリ制約述語
  constraint_type_predicates: ["weld_type"]        # タイプ制約述語
  constraint_goal_object_index: 1                  # ゴールオブジェクトインデックス
  
roles:
  role_config_file: "configs/role_configs/example_roles.json"

allocation:
  cost_function: "balanced"
```

### 出力形式

```json
{
  "domain": "small_weld_task",
  "problem": "small_weld_instance",
  "subtasks": [
    {
      "id": "subtask_001",
      "goals": ["(goal_predicate obj1 obj2)"],
      "landmark_predicates": ["landmark_pred"],
      "role_signature": {"base": "pos1", "hand_type": "0"},
      "assigned_agent": "robot_1"
    }
  ],
  "assignment": {"subtask_001": "robot_1"},
  "agents": {"robot_1": {"name": "robot_1", "type": "robot"}},
  "capabilities": {"robot_1": ["action1", "action2"]}
}
```

### 実行例

```bash
$ python -m src.cli.main --config configs/default_config.yaml --output solution.json
Loading domain: pddl/small_weld_task/domain.pddl
Loading problem: pddl/small_weld_task/problem.pddl
Parsed domain 'small_weld_task' with 15 actions
Parsed problem 'small_weld_instance' with 45 objects and 25 goals
Found 2 agents: ['robot_1', 'robot_2']
Building subtasks with retry...
Debug: After role-based partition: 169 subtasks
Debug: After constraint-aware merging: 35 subtasks (was 169)
Generated 35 subtasks
Allocating subtasks to agents...
Results saved to solution.json
```

### 制約考慮型統合システム

システムは以下の制約を厳密にチェックして、制約を満たさないサブタスクペアの統合を防止します：

#### 1. バイナリ制約チェック
- **`reachable`制約**: `reachable(base, weld_pos)`の形式で定義
- 異なるbaseを持つサブタスク統合時に、すべての組み合わせが到達可能であることを確認
- 例：`base_pos_1`と`base_pos_5`の統合時、両方のbaseから目標位置へ到達可能かチェック

#### 2. タイプ制約チェック
- **`weld_type`制約**: `weld_type(weld_pos, type)`の形式で定義
- 異なるhand_typeを持つサブタスク統合時に、要求されるweld_typeが一致することを確認
- 例：`hand_type: "0"`と`hand_type: "1"`のサブタスクは統合不可

#### 3. role_signature保持機能
- 統合時に元のrole_signature情報を適切に保持・統合
- 制約設定から再計算せず、実際の制約情報を維持
- 結果：`"base": "base_pos_1|base_pos_5"`, `"hand_type": "0"`のような適切な統合

#### 4. ドメイン汎化対応
```yaml
# ドメイン固有の制約述語を設定可能
constraint_binary_predicates: ["reachable", "connected"]    # カスタム設定可能
constraint_type_predicates: ["weld_type", "tool_type"]      # カスタム設定可能
constraint_goal_object_index: 1                             # ドメイン依存インデックス
```

---

## 2. 多様解の生成

複数の多様なサブタスク分解解を自動生成します。seedと戦略を変更することで、同一問題に対して異なる最適化特性を持つ解を生成します。

### 基本実行方法

```bash
# 基本的な多様解生成
python -m src.cli.generate_diverse_solutions \
  --config configs/default_config.yaml \
  --num-solutions 10 \
  --output-dir diverse_results

# 大量の解を生成
python -m src.cli.generate_diverse_solutions \
  --config configs/default_config.yaml \
  --num-solutions 50 \
  --output-dir large_scale_analysis
```

### パラメータ

| パラメータ | デフォルト値 | 説明 |
|-----------|-------------|------|
| `--config` | 必須 | ベース設定ファイルパス |
| `--num-solutions` | 10 | 生成する解の数 |
| `--output-dir` | 必須 | 結果保存ディレクトリ |

### 生成される多様性

システムは以下の要素を自動的に変化させて多様な解を生成します：

#### 1. 最適化戦略
- `minimize_subtasks`: サブタスク数最小化重視
- `balanced`: バランス型戦略
- `distribute_goals`: ゴール分散型
- `auto`: seedに基づく自動選択

#### 2. 自動調整パラメータ
- `random_seed`: `42 + i * 123` （異なる乱数シード）
- `strategy_randomness`: `0.1-0.5` （戦略のランダム性）
- `max_subtasks`: 基準値 ± 5-10 （サブタスク数制約）
- `max_goals_per_subtask`: 基準値 ± 3-5 （ゴール数制約）

#### 3. 探索設定の変化
- `epsilon_start`: `0.0-0.2` （探索の初期ランダム性）
- `epsilon_step`: `0.1-0.3` （探索のランダム性増加）
- `use_landmarks`: `true/false` （ランドマーク使用）
- `landmark_max_depth`: `2-4` （ランドマーク深度）

### 出力ファイル構成

```
output-dir/
├── result_000.json           # 個別解（JSON形式）
├── result_001.json
├── result_002.json
├── ...
├── diverse_config_000.yaml   # 使用された設定ファイル
├── diverse_config_001.yaml
├── diverse_config_002.yaml
├── ...
├── diversity_analysis.json   # 詳細分析データ
└── diversity_summary.txt     # 読みやすい要約レポート
```

### 実行例

```bash
$ python -m src.cli.generate_diverse_solutions --config configs/default_config.yaml --num-solutions 5 --output-dir diverse_results

🚀 Generating 5 diverse subtask decomposition solutions...
📁 Base config: configs/default_config.yaml  
📂 Output directory: diverse_results

📝 Creating diverse configuration files...
⚙️  Running solution 1/5: diverse_config_000.yaml
⚙️  Running solution 2/5: diverse_config_001.yaml
⚙️  Running solution 3/5: diverse_config_002.yaml
⚙️  Running solution 4/5: diverse_config_003.yaml
⚙️  Running solution 5/5: diverse_config_004.yaml

✅ Successfully generated 5/5 solutions
📊 Analyzing solution diversity...

🎯 DIVERSITY METRICS:
   Subtask Count Range: 35-45
   Subtask Count Variance: 16.00
   Unique Subtask Counts: 3
   Average Goal Variance: 10.88
```

### 多様性分析レポート

#### diversity_summary.txt 例
```
================================================================================
DIVERSE SUBTASK DECOMPOSITION ANALYSIS
================================================================================

Total Solutions Generated: 5
Subtask Count Range: 35-45
Subtask Count Variance: 16.00
Unique Subtask Counts: 3
Average Goal Distribution Variance: 10.88

Subtask Count Distribution:
  35 subtasks: 1 solutions
  40 subtasks: 1 solutions  
  45 subtasks: 3 solutions

Strategy Distribution:
  minimize_subtasks: 1 solutions
  balanced: 2 solutions
  distribute_goals: 1 solutions
  auto: 1 solutions
```

#### 指標の意味
- **Subtask Count Range**: サブタスク数の最小-最大値
- **Subtask Count Variance**: サブタスク数の分散（大きいほど多様）
- **Unique Subtask Counts**: 異なるサブタスク数の種類
- **Average Goal Variance**: ゴール分布の平均分散

---

## 3. 階層的クラスタリング分析

生成された多様な解を階層的クラスタリングで分析し、解の特性パターンを可視化します。

### 基本実行方法

```bash
# 基本的なクラスタリング分析
python -m src.analyze.cluster_solutions --config configs/clustering_analysis_config.yaml

# カスタム設定での分析
python -m src.analyze.cluster_solutions --config configs/custom_clustering_config.yaml
```

### パラメータ

| パラメータ | 説明 |
|-----------|------|
| `--config` | クラスタリング分析設定ファイルパス（必須） |

### 設定ファイル例

```yaml
# configs/clustering_analysis_config.yaml

# データソース
results_directory: "diverse_results"
result_file_pattern: "result_*.json"

# 特徴量抽出設定
feature_extraction:
  # 基本統計特徴量
  use_subtask_count: true
  use_goal_variance: true
  use_goal_mean: true
  use_goal_min_max: true
  use_agent_balance: true
  
  # 汎用的な構造特徴量
  use_structural_features: true
  role_config_file: "configs/role_configs/example_roles.json"
  structural_feature_types:
    - "role_diversity"
    - "role_complexity"
    - "subtask_similarity"
  
  # 正規化設定
  normalize_features: true
  normalization_method: "standard"  # standard, minmax, robust

# クラスタリング設定
clustering:
  method: "ward"                    # ward, complete, average, single
  metric: "euclidean"               # euclidean, manhattan, cosine
  num_clusters: null                # null = 自動決定
  auto_cluster_method: "silhouette" # silhouette, elbow, dendrogram_gap
  max_clusters: 8
  min_clusters: 2

# 可視化設定
visualization:
  create_dendrogram: true
  create_scatter_plots: true
  create_feature_importance: true
  create_cluster_summary: true
  
  # 図のサイズとスタイル
  figure_size: [12, 8]
  dpi: 300
  style: "seaborn-v0_8"
  color_palette: "husl"

# 出力設定
output:
  output_dir: "clustering_analysis"
  save_features_csv: true
  save_cluster_assignments: true
  save_plots: true
  save_summary_report: true
  prefix: "solution_clustering"
```

### 抽出される特徴量（16個）

#### 基本統計特徴量（11個）
1. `agent_balance_max_min_ratio`: エージェント負荷バランス比
2. `agent_balance_variance`: エージェント負荷分散
3. `goal_variance`, `goal_mean`, `goal_min`, `goal_max`, `goal_range`: ゴール数統計
4. `subtask_count`: サブタスク総数
5. `num_active_agents`: アクティブエージェント数
6. `complex_role_ratio`: 複合役割の割合

#### 汎用的構造特徴量（5個）
1. `role_signature_entropy`: 役割シグネチャの多様性（エントロピー）
2. `unique_role_signature_count`: ユニークな役割シグネチャ数
3. `avg_role_attributes_per_subtask`: サブタスクあたり平均役割属性数
4. `avg_subtask_similarity`: サブタスク間類似度
5. `similarity_variance`: サブタスク類似度の分散

### 出力ファイル構成

```
clustering_analysis/
├── solution_clustering_features.csv          # 全特徴量データ
├── solution_clustering_cluster_assignments.csv # クラスター割り当て結果
├── solution_clustering_summary.txt           # 詳細分析レポート
├── solution_clustering_dendrogram.png        # 階層構造デンドログラム
├── solution_clustering_scatter.png           # PCA散布図プロット
└── solution_clustering_feature_importance.png # 特徴量重要度
```

### 実行例

```bash
$ python -m src.analyze.cluster_solutions --config configs/clustering_analysis_config.yaml

🚀 Starting hierarchical clustering analysis...
🔍 Extracting features from solutions...
✅ Extracted 16 features from 5 solutions
📊 Features: agent_balance_max_min_ratio, agent_balance_variance, avg_role_attributes_per_subtask...
💾 Features saved to clustering_analysis/solution_clustering_features.csv
📏 Normalizing features...
✅ Features normalized using standard scaling
🔗 Performing hierarchical clustering...
🎯 Determining optimal number of clusters using silhouette...
🎯 Best silhouette score: 0.321 with 2 clusters
📈 Using 2 clusters
📊 Clustering Quality:
   Silhouette Score: 0.321
   Calinski-Harabasz Score: 3.670
✅ Hierarchical clustering completed
📊 Creating visualizations...
✅ Visualizations created
💾 Saving clustering results...
✅ Results saved to clustering_analysis
🎉 Hierarchical clustering analysis completed successfully!

🎉 Analysis completed successfully!
📊 Results summary:
   Solutions analyzed: 5
   Features used: 16
   Clusters found: 2
```

### クラスタリング結果の解釈

#### solution_clustering_summary.txt 例
```
================================================================================
HIERARCHICAL CLUSTERING ANALYSIS REPORT
================================================================================

Total Solutions Analyzed: 5
Number of Features: 16
Number of Clusters: 2
Clustering Method: ward
Distance Metric: euclidean

CLUSTER SUMMARY:
--------------------------------------------------
Cluster 1: 4 solutions
  Solutions: result_001, result_002, result_003, result_004
  Top features: similarity_variance(-0.49) role_signature_entropy(0.49) avg_subtask_similarity(0.48)

Cluster 2: 1 solutions
  Solutions: result_000
  Top features: similarity_variance(1.95) role_signature_entropy(-1.94) avg_subtask_similarity(-1.94)

FEATURE SUMMARY:
--------------------------------------------------
Features used: agent_balance_max_min_ratio, agent_balance_variance, avg_role_attributes_per_subtask, avg_role_complexity, avg_subt
ask_similarity(-1.94)

FEATURE SUMMARY:
--------------------------------------------------
Features used: agent_balance_max_min_ratio, agent_balance_variance, avg_role_attributes_per_subtask, avg_role_complexity, avg_subtask_similarity, complex_role_ratio, goal_max, goal_mean, goal_min, goal_range, goal_variance, num_active_agents, role_signature_entropy, similarity_variance, subtask_count, unique_role_signature_count

CONFIGURATION:
--------------------------------------------------
Results Directory: diverse_results
Normalization: standard
Structural Features: true
```

#### クラスター特性の解釈
- **Cluster 1** (統一性重視): 類似度分散が低く、役割構成が統一された集約型戦略
- **Cluster 2** (多様性重視): 類似度分散が高く、役割構成が多様な分散型戦略

---

## 統合ワークフロー例

### 完全分析パイプライン

```bash
# Step 1: 多様解の生成（20個の解）
python -m src.cli.generate_diverse_solutions \
  --config configs/default_config.yaml \
  --num-solutions 20 \
  --output-dir analysis_dataset

# Step 2: 階層的クラスタリング分析
python -m src.analyze.cluster_solutions \
  --config configs/clustering_analysis_config.yaml

# Step 3: 結果の確認
ls analysis_dataset/          # 生成された解とメタデータ
ls clustering_analysis/       # クラスタリング結果と可視化
```

### 設定ファイルの対応表

| 用途 | 設定ファイル | 主要パラメータ |
|------|-------------|---------------|
| 単一解生成 | `configs/default_config.yaml` | `random_seed`, `strategy`, `max_subtasks` |
| 多様解生成 | `configs/default_config.yaml` (ベース) | `num_solutions`, `output_dir` |
| クラスタリング分析 | `configs/clustering_analysis_config.yaml` | `results_directory`, `clustering.method` |

### パラメータ命名規則

システム全体で統一されたパラメータ命名規則：

#### ファイルパス関連
- `config`: 設定ファイルパス
- `output`: 出力ファイルパス  
- `output_dir`: 出力ディレクトリパス
- `results_directory`: 結果読み込みディレクトリパス

#### 数値パラメータ
- `num_solutions`: 生成する解の数
- `random_seed`: 乱数シード
- `max_subtasks`: 最大サブタスク数
- `max_goals_per_subtask`: サブタスクあたり最大ゴール数

#### 戦略・手法
- `strategy`: 最適化戦略
- `method`: クラスタリング手法  
- `normalization_method`: 正規化手法

#### フラグ
- `use_landmarks`: ランドマーク使用フラグ
- `use_structural_features`: 構造特徴量使用フラグ
- `normalize_features`: 特徴量正規化フラグ

---

## トラブルシューティング

### よくあるエラーと対処法

#### 1. 設定ファイルが見つからない
```bash
❌ Configuration file not found: configs/missing_config.yaml
```
**対処法**: 設定ファイルのパスを確認し、正しいパスを指定してください。

#### 2. 結果ディレクトリが存在しない
```bash
❌ Results directory not found: missing_results/
```
**対処法**: 先に多様解生成を実行してからクラスタリング分析を実行してください。

#### 3. メモリ不足エラー
```bash
❌ MemoryError: Unable to allocate array
```
**対処法**: 生成する解の数を減らすか、特徴量の種類を制限してください。

#### 4. 依存ライブラリ不足
```bash
❌ ModuleNotFoundError: No module named 'sklearn'
```
**対処法**: 必要なライブラリをインストールしてください：
```bash
pip install scikit-learn matplotlib seaborn scipy pandas numpy
```

### パフォーマンス最適化

#### 大規模問題での推奨設定
- `num_solutions`: 50-100
- `clustering.max_clusters`: 10-15
- `normalization_method`: "robust"（外れ値に強い）

#### 小規模問題での推奨設定
- `num_solutions`: 10-20
- `clustering.max_clusters`: 5-8
- `normalization_method`: "standard"（標準的）

---

## 関連ドキュメント

- [`README_diverse_solutions.md`](README_diverse_solutions.md): 多様解生成の詳細
- [`README_clustering_analysis.md`](README_clustering_analysis.md): クラスタリング分析の詳細
- 設定ファイル例: `configs/` ディレクトリ
- 実行例: `examples/` ディレクトリ（もしあれば）