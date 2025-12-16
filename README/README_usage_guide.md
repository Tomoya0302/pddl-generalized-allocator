# PDDL Multi-Agent Task Decomposition & Allocation - 実行ガイド（Usage Guide）

このドキュメントでは、`pddl-generalized-allocator` の主要機能を「**どの順番で**」「**どの設定を触れば**」動かせるかに焦点を当ててまとめます。

* **単一解生成**（1つの分解・割当）
* **多様解生成**（feature objective を切り替えて複数解生成）
* **階層的クラスタリング分析**（特徴量抽出→クラスタリング→可視化）
* **多様性評価（volume_eval）**（クラスタ特徴量CSVを入力に volume / diversity を算出）

> 詳細アルゴリズムは `README/pddl_multi_agent_algorithm.md`、多様解生成の詳細は `README/README_diverse_solutions.md` を参照してください。

---

## 目次

1. [環境準備](#環境準備)
2. [クイックスタート](#クイックスタート)
3. [1. 単一解の生成](#1-単一解の生成)
4. [2. 多様解の生成](#2-多様解の生成)
5. [3. 階層的クラスタリング分析](#3-階層的クラスタリング分析)
6. [4. 多様性評価（volume_eval）](#4-多様性評価volume_eval)
7. [設定ファイルの要点（どこを触る？）](#設定ファイルの要点どこを触る)
8. [よくあるワークフロー](#よくあるワークフロー)
9. [トラブルシューティング](#トラブルシューティング)

---

## 環境準備

### 依存ライブラリ

最低限、以下が必要です（分析系のため `numpy/pandas/scikit-learn/matplotlib/scipy/pyyaml` が必須）。

```bash
pip install numpy pandas scikit-learn matplotlib scipy pyyaml
```

クラスタリング可視化のスタイル指定に `seaborn` を使う設定がある場合は、追加で入れてください。

```bash
pip install seaborn
```

---

## クイックスタート

### 1) 単一解の生成

```bash
python -m src.cli.main --config configs/default_config.yaml --output solution.json
```

### 2) 多様解の生成（例: 20解）

```bash
python -m src.cli.generate_diverse_solutions \
  --config configs/default_config.yaml \
  --num-solutions 20 \
  --output-dir analysis_dataset
```

### 3) 階層的クラスタリング分析

```bash
python -m src.analyze.cluster_solutions --config configs/clustering_analysis_config.yaml
```

### 4) 多様性評価（volume_eval）

`volume_eval` は **クラスタリング分析で出力される特徴量CSV** を入力に評価します。

```bash
python -m src.analyze.volume_eval --config configs/volume_eval_config.yaml
```

---

## 1. 単一解の生成

単一の PDDL マルチエージェント分解・割当解（1解）を生成します。

### 実行

```bash
# 設定ファイルを指定して実行
python -m src.cli.main --config configs/default_config.yaml

# 結果をファイルに保存
python -m src.cli.main --config configs/default_config.yaml --output solution.json
```

### 主な引数

| 引数         | デフォルト                         | 説明                |
| ---------- | ----------------------------- | ----------------- |
| `--config` | `configs/default_config.yaml` | 設定ファイル            |
| `--output` | なし                            | 出力JSON（未指定なら標準出力） |

### 出力（概略）

* `subtasks`: 分解されたサブタスク群
* `assignment`: サブタスク→エージェントの割当
* `agents/capabilities`: エージェント情報（能力推定含む）

---

## 2. 多様解の生成

同一の Domain/Problem に対して、設定（seed と探索・最適化目的）を変えながら **複数の解** を生成します。

### 実行

```bash
python -m src.cli.generate_diverse_solutions \
  --config configs/default_config.yaml \
  --num-solutions 10 \
  --output-dir diverse_results
```

### 主な引数

| 引数                | デフォルト | 説明     |
| ----------------- | ----: | ------ |
| `--config`        |  （必須） | ベース設定  |
| `--num-solutions` |    10 | 生成する解数 |
| `--output-dir`    |  （必須） | 出力先    |

### 多様化の中身（重要）

現在の実装では、解ごとに `feature_objectives` を切り替えることで、

* `subtask_count` を小さくしたい
* `goal_variance` を大きくしたい
* `role_signature_entropy` を大きくしたい

のように **狙う性質（目的関数）を変えた探索** を行います。

生成時のログに、各解で使われた特徴量目的（`name/direction/weight`）が表示されます。

### 出力構成

```text
output-dir/
├── result_000.json ~ result_XXX.json
├── diverse_config_000.yaml ~ XXX.yaml
├── diversity_analysis.json
└── diversity_summary.txt
```

> `analysis_dataset/` を使う場合は、`configs/clustering_analysis_config.yaml` の `results_directory` と揃えておくと、そのまま後段分析へ進めます。

---

## 3. 階層的クラスタリング分析

多様解（`result_*.json`）から特徴量を抽出し、階層クラスタリング（例: Ward）で解の系統を可視化します。

### 実行

```bash
python -m src.analyze.cluster_solutions --config configs/clustering_analysis_config.yaml
```

### 入力/出力の対応

* 入力: `results_directory`（例: `analysis_dataset`）配下の `result_*.json`
* 出力: `output.output_dir`（例: `clustering_analysis/`）

  * `solution_clustering_features.csv`（重要：後段 volume_eval の入力）

---

## 4. 多様性評価（volume_eval）

`volume_eval` は **特徴量空間での多様性（generalized variance / convex hull volume）** を評価します。

### 実行

```bash
python -m src.analyze.volume_eval --config configs/volume_eval_config.yaml
```

### 入力

* `configs/volume_eval_config.yaml` の `input_csv` を参照

  * 典型: `clustering_analysis/solution_clustering_features.csv`

### 出力

* `output_dir` 配下に `volume_report.txt`
* 設定に応じて、

  * Diversity Growth Curve
  * PCA + Convex Hull（2D/3D）
  * R-Theta ポーラーチャート

などの可視化が生成されます。

---

## 設定ファイルの要点（どこを触る？）

### A) `configs/default_config.yaml`

単一解生成 / 多様解生成の「ベース設定」です。特に触る頻度が高いのは以下です。

* `pddl.domain_file / pddl.problem_file`

  * 例: `pddl/small_weld_domain/domain.pddl`, `pddl/small_weld_domain/problem.pddl`
* `clustering.max_subtasks`（K_max）
* `clustering.max_goals_per_subtask`
* `clustering.use_landmarks`, `clustering.landmark_max_depth`
* 制約

  * `clustering.constraint_binary_predicates`
  * `clustering.constraint_type_predicates`
  * `clustering.constraint_goal_object_index`
* 多様解生成で重要

  * `clustering.optimization_strategy: feature_driven`
  * `clustering.feature_objectives: [...]`

> 新しいドメインに合わせる場合は、まず `pddl.*` と制約述語（constraint_*）を合わせるのが最短です。

### B) `configs/clustering_analysis_config.yaml`

* `results_directory`（多様解の出力ディレクトリ）
* `feature_extraction`（抽出する特徴量のON/OFF）
* `clustering`（Ward/距離/クラスタ数選択）
* `output.output_dir`（出力先）

### C) `configs/volume_eval_config.yaml`

* `input_csv`（クラスタリング分析の `features.csv` を指定）
* `features`（評価に使う列名リスト）
* `normalization`（minmax / standard）
* `metrics`（logdet / convex_hull_volume）
* 可視化フラグ（`plot_*`）

---

## よくあるワークフロー

### 1) ドメインを切り替えたい（small ↔ large）

`configs/default_config.yaml` の `pddl.domain_file/problem_file` を差し替えます。

### 2) サブタスクが多すぎる / 少なすぎる

* 多すぎる → `clustering.max_subtasks` を下げる、`merge_compatible_subtasks` を有効にする
* 少なすぎる → `clustering.max_cluster_size` を下げる、`max_goals_per_subtask` を下げる

### 3) 多様解が「似た解ばかり」になる

* `--num-solutions` を増やす
* `feature_objectives` の種類を増やす／方向を変える
* `clustering.epsilon_start / epsilon_step` や `strategy_randomness` を調整

### 4) volume_eval を先に回したい

現状の `volume_eval` は CSV 入力（`input_csv`）前提です。

* 先に `cluster_solutions` を回して `solution_clustering_features.csv` を作る
* もしくは、自前で同じ列名を持つ特徴量CSVを用意して `input_csv` を差し替える

---

## トラブルシューティング

* **解生成がタイムアウトする**

  * `configs/default_config.yaml` の `clustering.solution_timeout` を増やす

* **`Cannot satisfy max_subtasks=...` が頻発する**

  * `max_subtasks` が厳しすぎる可能性（上げる／分割粒度を調整）

* **新ドメインで制約が合わない**

  * `constraint_binary_predicates / constraint_type_predicates / constraint_goal_object_index` を見直す

* **クラスタリング/volume_eval の入力が見つからない**

  * `results_directory`（クラスタリング）と `input_csv`（volume_eval）のパスを確認

---

## 関連ドキュメント

* `README/README_diverse_solutions.md` : 多様解生成の詳細
* `README/README_clustering_analysis.md` : クラスタリング分析の詳細
* `README/README_volume_eval.md` : 多様性評価の詳細
* `README/pddl_multi_agent_algorithm.md` : アルゴリズム（分解+割当）
* `README/TROUBLESHOOTING.md` : 追加のトラブルシューティング
