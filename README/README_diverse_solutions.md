# Diverse Subtask Decomposition Generator

多様なサブタスク分解解を自動生成するCLIツールです。seedを変更することで、同一問題に対して異なる最適化戦略を持つ多様な解を生成します。

## 使用方法

```bash
# 基本的な使用方法
python -m src.cli.generate_diverse_solutions --config configs/default_config.yaml --num-solutions 10 --output-dir results_diverse

# パラメータ説明
# --config: ベースとなる設定ファイルパス
# --num-solutions: 生成する解の数（デフォルト: 10）
# --output-dir: 結果を保存するディレクトリパス
```

## 生成される多様性

このツールは以下の要素を自動的に変化させて多様な解を生成します：

### 1. 最適化戦略
- `minimize_subtasks`: サブタスク数最小化
- `balanced`: バランス型
- `distribute_goals`: ゴール分散型
- `auto`: seed基づく自動選択

### 2. パラメータ調整
- `random_seed`: 42 + i * 123 (異なる乱数シード)
- `strategy_randomness`: 0.1-0.5 (戦略のランダム性)
- `max_subtasks`: 基準値±5-10 (サブタスク数制約)
- `max_goals_per_subtask`: 基準値±3-5 (ゴール数制約)

### 3. 探索設定
- `epsilon_start`: 0.0-0.2 (探索の初期ランダム性)
- `epsilon_step`: 0.1-0.3 (探索のランダム性増加)
- `use_landmarks`: true/false (ランドマーク使用)
- `landmark_max_depth`: 2-4 (ランドマーク深度)

## 出力ファイル

生成されるファイル：

```
output-dir/
├── result_000.json           # 個別解（JSON形式）
├── result_001.json
├── ...
├── diverse_config_000.yaml   # 使用された設定ファイル
├── diverse_config_001.yaml
├── ...
├── diversity_analysis.json   # 詳細分析データ
└── diversity_summary.txt     # 読みやすい要約レポート
```

## 例：実行結果

```bash
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

## 分析レポートの見方

### diversity_summary.txt
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
```

### 指標の意味
- **Subtask Count Range**: サブタスク数の最小-最大値
- **Subtask Count Variance**: サブタスク数の分散（大きいほど多様）
- **Unique Subtask Counts**: 異なるサブタスク数の種類
- **Average Goal Variance**: ゴール分布の平均分散

## 応用例

### 1. 小規模問題での多様解探索
```bash
python -m src.cli.generate_diverse_solutions \
  --config configs/minimize_subtasks_config.yaml \
  --num-solutions 20 \
  --output-dir small_problem_diverse
```

### 2. 大規模問題での効率性重視
```bash
python -m src.cli.generate_diverse_solutions \
  --config configs/high_diversity_config.yaml \
  --num-solutions 50 \
  --output-dir large_problem_analysis
```

### 3. 特定戦略の比較分析
```bash
# 最小化戦略ベース
python -m src.cli.generate_diverse_solutions \
  --config configs/minimize_subtasks_config.yaml \
  --num-solutions 10 \
  --output-dir minimize_variants

# 分散戦略ベース
python -m src.cli.generate_diverse_solutions \
  --config configs/distribute_goals_config.yaml \
  --num-solutions 10 \
  --output-dir distribute_variants
```

## 技術的詳細

このツールは`src.cli.main`を内部的に呼び出し、各設定で独立してPDDL問題を解決します。生成される多様性は以下の要素により実現されます：

1. **Seedベース多様性**: 異なる乱数シードにより探索パスが変化
2. **戦略多様性**: 4つの最適化戦略を循環的に適用
3. **パラメータ多様性**: 制約パラメータを系統的に変化
4. **設定多様性**: 探索・ランドマーク設定の組み合わせ

生成される解は全て制約を満たしつつ、異なる最適化目標に基づいた多様なサブタスク分解を実現します。