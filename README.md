# PDDL Multi-Agent Task Decomposition & Allocation System

PDDL 問題（Domain/Problem）を **複数エージェントで実行可能なサブタスク** に分解し、各サブタスクを **エージェントへ割り当て** るためのツール群です。

* **単一解生成**（1つの分解・割当）
* **多様解生成**（複数の分解・割当を戦略・seed を変えて生成）
* **多様解評価（Volume / Diversity Evaluation）**（解集合の多様性・被覆度を評価）
* **階層的クラスタリング分析**（解集合の特徴量抽出・可視化・クラスタリング）

> 本 README は、リポジトリの更新に合わせて「多様解生成・評価」の導線と、添付 drawio に記述されたアルゴリズム概要を統合したアップデート版です。

---

## クイックスタート

### 1) 単一解の生成

```bash
python -m src.cli.main --config configs/default_config.yaml --output solution.json
```

### 2) 多様解の生成

```bash
# 例: 10 個の多様な解（分解・割当）を生成
python -m src.cli.generate_diverse_solutions \
  --config configs/default_config.yaml \
  --num-solutions 10 \
  --output-dir diverse_results
```

### 3) 多様解評価（Volume / Diversity Evaluation）

```bash
python -m src.analyze.volume_eval --config configs/volume_eval_config.yaml
```

* `volume_eval` は、生成済みの多様解セット（例: `diverse_results/`）に対して、**多様性・被覆度（volume）・ペア距離・指標集計** などを計算するための分析エントリポイントです。
* 入力ディレクトリ／評価指標／正規化方法／出力先などは `configs/volume_eval_config.yaml` で指定します。

### 4) 階層的クラスタリング分析

```bash
python -m src.analyze.cluster_solutions --config configs/clustering_analysis_config.yaml
```

---

## 典型的な分析パイプライン

```bash
# Step 1: 多様解生成
python -m src.cli.generate_diverse_solutions \
  --config configs/default_config.yaml \
  --num-solutions 20 \
  --output-dir analysis_dataset

# Step 2: 多様解評価（任意）
python -m src.analyze.volume_eval --config configs/volume_eval_config.yaml

# Step 3: クラスタリング分析
python -m src.analyze.cluster_solutions --config configs/clustering_analysis_config.yaml
```

---

## 出力例

### 多様解生成結果

```text
diverse_results/
├── result_000.json ~ result_019.json    # 生成された解（分解・割当）
├── diverse_config_000.yaml ~ 019.yaml   # 各解の生成に使われた設定（seed/戦略/調整後パラメータ等）
├── diversity_analysis.json              # 多様性の詳細データ（距離・指標など）
└── diversity_summary.txt                # 要約レポート
```

### クラスタリング分析結果

```text
clustering_analysis/
├── solution_clustering_features.csv
├── solution_clustering_cluster_assignments.csv
├── solution_clustering_summary.txt
├── solution_clustering_dendrogram.png
├── solution_clustering_scatter.png
└── solution_clustering_feature_importance.png
```

### 多様解評価（volume_eval）結果（例）

`configs/volume_eval_config.yaml` の `output_dir` 次第ですが、一般に次のような **評価レポート／集計結果／プロット** が出力されます。

```text
volume_eval/
├── volume_eval_summary.txt
├── volume_eval_metrics.json
└── (optional) plots/*.png
```

---

## 主要機能

### 1. 単一解生成

* PDDL Domain/Problem を読み込み
* マルチエージェント対応のサブタスク分解
* エージェントへの割当
* JSON で出力

### 2. 多様解生成

* 複数の最適化戦略を切り替えながら解を生成

  * `minimize_subtasks`, `balanced`, `distribute_goals`, `auto`
* `seed` ベースの探索で「同等品質でも異なる」分解・割当を集める
* 生成の過程でパラメータ（例: 目標クラスタ数・統合閾値・merge 戦略など）を自動調整
* 生成した解集合に対して、多様性指標の集計を自動生成

> 詳細仕様・使い方は `README/README_diverse_solutions.md` を参照してください。

### 3. 多様解評価（Volume / Diversity Evaluation）

* 多様解生成で得られた **解集合** を入力として、

  * 目的関数（例: サブタスク数／負荷バランス／達成目標の分布など）に基づく **解空間の被覆度（volume）**
  * 解同士の距離（割当・サブタスク構造の差分）や多様性指標
  * 指標の正規化・集約
    を計算します。

> 実装は `src/analyze/volume_eval/__main__.py` がエントリで、`python -m src.analyze.volume_eval --config configs/volume_eval_config.yaml` で起動します。

### 4. 階層的クラスタリング分析

* 汎用的特徴量（複数種）を抽出
* Ward 法による階層クラスタリング
* 自動クラスタ数決定（silhouette / elbow / dendrogram gap 等）
* 可視化（デンドログラム、PCA 散布図、特徴量重要度）

### 5. 制約考慮型統合（Constraint-aware Merge）

* ドメイン固有制約を **厳密にチェック** しながらサブタスク統合

  * 例: `reachable` 制約、`weld_type` 制約
* 統合時に制約情報（role signature 等）を保持
* 制約違反を引き起こす統合を禁止して品質を担保

---

## アルゴリズム概要（添付 drawio 反映）

このプロジェクトが扱う問題は、次を満たす **サブタスク集合** と **割当** を求めることです。

* 入力:

  * PDDL Domain: (\mathcal{D})
  * PDDL Problem: (\mathcal{P})
  * ゴール集合: (G={g_1,\dots,g_N})
  * エージェント集合: (\Lambda={\lambda_1,\dots,\lambda_M})
* 出力:

  * サブタスク集合: (T={T_1,\dots,T_K})
  * 割当関数: (\alpha: T\to \Lambda)
* 制約:

  * (T_i \subseteq G), (\cup_i T_i = G), (T_i \cap T_j = \emptyset)
  * 各サブタスクは、割り当てられたエージェントで実行可能
  * サブタスク数上限: (|T|\le K_{max})

### 手順（drawio のステップ対応）

1. **PDDL から PlanningTask を生成**

   * `Domain/Problem` をパースし、オブジェクト・述語・アクション・初期状態・ゴールを構造化

2. **MultiAgentTask + Capabilities の構築**

   * エージェント型パラメータを持つアクションから、各エージェントの実行可能アクション集合を推定

3. **因果グラフ (Causal Graph) 構築**

   * あるアクションで、述語 (p) が前提に出現し、述語 (q) が add 効果に出現するなら、(p\to q) を張る（del 効果は使わない）

4. **ランドマーク (LM) 抽出**

   * ゴール達成に重要な述語（中間条件）を抽出してサブタスクへ付与

5. **ゴール間グラフ構築（構造的依存）**

   * 因果グラフを利用して、ゴール同士の依存関係をグラフ化

6. **連結成分分解（構造的タスク分解）**

   * ゴール依存グラフを連結成分に分け、独立に解ける塊へ分割

7. **クラスタ分解**

   * 連結成分内をさらにクラスタリングして、分解粒度を調整

8. **サブタスクフォーマット導入**

   * ゴール集合とランドマーク、そして後述の role 情報をまとめて `SubTask` として表現

9. **Role-based Finer Partition（意味的タスク分解）**

   * 初期状態 (I) とゴール (g) から role を抽出し、role キー（例: `base`, `hand_type`）でゴールを再分割

10. **最大サブタスク数制約 (K_{max})**

* サブタスク数が上限を超える場合は、制約を壊さない範囲で merge して調整

11. **最終サブタスク定義**

12. **エージェント割当**

* 各サブタスク (T_i) に対して、能力に基づくコストを定義し、(\Lambda_i^* = \arg\min_\lambda cost(T_i,\lambda)) で割当

> 図の詳細（定義式・抽出器 (\mathcal{E}(r))・role 設計など）は、添付の drawio ファイルを参照してください。

---

## プロジェクト構成

```text
pddl-generalized-allocator/
├── README/
│   ├── README_clustering_analysis.md
│   ├── README_diverse_solutions.md
│   ├── README_usage_guide.md
│   ├── TROUBLESHOOTING.md
│   ├── pddl_multi_agent_algorithm.md
│   └── role_extraction_role_based_partition_generalized.md
├── README.md
├── configs/
│   ├── clustering_analysis_config.yaml
│   ├── default_config.yaml
│   ├── volume_eval_config.yaml
│   └── role_configs/
│       └── example_roles.json
├── pddl/
│   ├── large_weld_domain/
│   │   ├── domain.pddl
│   │   └── problem.pddl
│   └── small_weld_domain/
│       ├── domain.pddl
│       └── problem.pddl
└── src/
    ├── analyze/
    │   ├── analyze_results.py
    │   ├── cluster_solutions.py
    │   ├── feature_extractor.py
    │   ├── hierarchical_clustering.py
    │   └── volume_eval/
    │       ├── __main__.py
    │       ├── metrics.py
    │       ├── runner.py
    │       └── utils.py
    ├── cli/
    │   ├── generate_diverse_solutions.py
    │   └── main.py
    ├── config/
    │   ├── clustering_analysis_schema.py
    │   ├── loader.py
    │   └── schema.py
    ├── multiagent/
    │   ├── agents.py
    │   └── capabilities.py
    ├── pddl/
    │   ├── ast.py
    │   ├── domain_parser.py
    │   ├── problem_parser.py
    │   ├── sexpr_parser.py
    │   ├── static_analysis.py
    │   ├── tokenizer.py
    │   └── types.py
    ├── planning/
    │   ├── allocation.py
    │   ├── causal_graph.py
    │   ├── clustering.py
    │   ├── constraint_aware_merge.py
    │   ├── goal_graph.py
    │   ├── landmarks.py
    │   ├── multi_objective_merge.py
    │   ├── roles.py
    │   ├── subtasks.py
    │   └── task.py
    └── utils/
        └── random_utils.py
```

---

## 設定ファイル（Configs）

* `configs/default_config.yaml`

  * 単一解生成・多様解生成に関する主要設定
* `configs/clustering_analysis_config.yaml`

  * 特徴量抽出・クラスタリング・可視化の設定
* `configs/volume_eval_config.yaml`

  * 多様解評価（入力ディレクトリ、指標、正規化、出力先など）の設定
* `configs/role_configs/example_roles.json`

  * role 抽出で使うキー（例: `base`, `hand_type`, …）の定義例

---

## システム要件

### 依存ライブラリ

```bash
pip install numpy pandas scikit-learn matplotlib seaborn scipy pyyaml
```