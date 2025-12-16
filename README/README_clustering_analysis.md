# クラスタリング分析（Hierarchical Clustering Analysis）

このドキュメントは、`pddl-generalized-allocator` が生成した **解（分解・割当）集合** を対象に、

* 解ごとの特徴量を抽出して **ベクトル化** し
* 距離（類似度）を定義して **階層クラスタリング**（例: Ward 法）を行い
* その結果を **可視化 / 要約 / CSV 出力**

するための手順をまとめたものです。

> 実行はトップ README にある通り `python -m src.analyze.cluster_solutions --config configs/clustering_analysis_config.yaml` を想定します。([github.com](https://github.com/Tomoya0302/pddl-generalized-allocator))

---

## 1. 前提

* 先に **多様解生成**（`diverse_results/` などに `result_*.json` がある状態）を実行済みであること([github.com](https://github.com/Tomoya0302/pddl-generalized-allocator))
* 設定 `configs/clustering_analysis_config.yaml` が用意されていること([github.com](https://github.com/Tomoya0302/pddl-generalized-allocator))

典型的なパイプライン（トップ README の流れ）:

```bash
# Step 1: 多様解生成
python -m src.cli.generate_diverse_solutions \
  --config configs/default_config.yaml \
  --num-solutions 20 \
  --output-dir diverse_results

# Step 2: （任意）多様性評価
python -m src.analyze.volume_eval --config configs/volume_eval_config.yaml

# Step 3: クラスタリング分析
python -m src.analyze.cluster_solutions --config configs/clustering_analysis_config.yaml
```

---

## 2. 実行方法

```bash
python -m src.analyze.cluster_solutions --config configs/clustering_analysis_config.yaml
```

`--config` で指定した YAML に従い、

* 入力ディレクトリ（解ファイル群）
* 抽出する特徴量セット
* 特徴量の正規化
* 距離・クラスタリング手法
* クラスタ数の決め方
* 出力先（CSV / PNG / TXT）

を切り替えます。

---

## 3. 入力（クラスタリング対象）

### 3.1 想定ディレクトリ構成

多様解生成の出力例（トップ README の例）:([github.com](https://github.com/Tomoya0302/pddl-generalized-allocator))

```text
diverse_results/
├── result_000.json ~ result_019.json
├── diverse_config_000.yaml ~ 019.yaml
├── diversity_analysis.json
└── diversity_summary.txt
```

クラスタリング分析では、通常 `result_*.json` を読み込み、
「解ごとの特徴量（feature）→距離→クラスタ」へ進みます。

### 3.2 何を「解」として扱うか

実装の前提として、各解（1ファイル）は概ね次の情報を持つことを想定します。

* サブタスク分解（サブタスク数、各サブタスクに含まれるゴール群など）
* エージェント割当（サブタスク→エージェントの対応）
* 追加メタ情報（スコア / seed / 戦略など）

> 解フォーマットが変わった場合は、特徴量抽出部が参照しているキーに合わせてください。

---

## 4. 出力（生成物）

トップ README の出力例に合わせると、概ね次を出します。([github.com](https://github.com/Tomoya0302/pddl-generalized-allocator))

```text
clustering_analysis/
├── solution_clustering_features.csv
├── solution_clustering_cluster_assignments.csv
├── solution_clustering_summary.txt
├── solution_clustering_dendrogram.png
├── solution_clustering_scatter.png
└── solution_clustering_feature_importance.png
```

* `solution_clustering_features.csv`

  * 解ごとの特徴量（行=解、列=特徴量）
* `solution_clustering_cluster_assignments.csv`

  * 解ID→クラスタID（およびクラスタ数決定に関する付帯情報があればそれも）
* `solution_clustering_summary.txt`

  * 実行条件、採用したクラスタ数、クラスタごとの代表値・特徴などの要約
* `solution_clustering_dendrogram.png`

  * 階層クラスタリングのデンドログラム
* `solution_clustering_scatter.png`

  * 次元圧縮（例: PCA）後の散布図（色=クラスタ）
* `solution_clustering_feature_importance.png`

  * クラスタ分離に寄与した特徴量の可視化（重要度指標は実装依存）

---

## 5. 特徴量設計（何をベクトルにするか）

クラスタリングが「意味のある分類」になるかは、ほぼ特徴量で決まります。
本プロジェクトでは、少なくとも次のような観点を分けて入れるのが実務的です。

### 5.1 分解構造（Task Decomposition）

* サブタスク数
* サブタスクサイズ分布（平均・分散、最大/最小）
* ゴールのグルーピング傾向（特定のゴールが同じ塊に入りやすい等）

### 5.2 割当（Allocation）

* エージェントごとの担当サブタスク数
* エージェント負荷（担当ゴール数など）の分散
* 割当の偏り指標（均等か、特定エージェントに集中するか）

### 5.3 制約・実行可能性（可能なら）

* 「制約に余裕がある」解か「ギリギリ」な解かを表すスカラー
* 実行可能性チェックの結果（True/False）だけでなく、違反種別の集計など

---

## 6. 距離・クラスタリング手法

### 6.1 距離（例）

* 特徴量ベクトル同士の距離（ユークリッド / cosine 等）
* 正規化（min-max / z-score など）を適用して、スケール差で潰れないようにする

### 6.2 階層クラスタリング（例: Ward）

トップ README には Ward 法による階層クラスタリングが示唆されています。([github.com](https://github.com/Tomoya0302/pddl-generalized-allocator))

Ward 法は「クラスタ内分散」を増やさない方向に結合していくため、
“似た解のまとまり” を作りやすい一方、特徴量スケールの影響を受けやすいです。

### 6.3 クラスタ数の自動決定

トップ README には silhouette / elbow / dendrogram gap 等が挙げられています。([github.com](https://github.com/Tomoya0302/pddl-generalized-allocator))

実運用では、

* silhouette がピーク付近の候補
* elbow の曲がり角
* dendrogram の大きなギャップ

が一致するクラスタ数を「まず採用」し、
目的（分類したい意味）に合うかを散布図と summary で確認、がやりやすいです。

---

## 7. 設定ファイル例（configs/clustering_analysis_config.yaml）

> **注意**: 実際のキー名は `configs/clustering_analysis_config.yaml` を正として合わせてください。

README 用のテンプレ（運用の観点）:

```yaml
# === 入出力 ===
input_dir: "diverse_results"
output_dir: "clustering_analysis"
solution_glob: "result_*.json"

# === 特徴量 ===
features:
  # 例: 分解
  decomposition:
    enabled: true
  # 例: 割当
  allocation:
    enabled: true

# === 前処理 ===
normalize:
  enabled: true
  method: "zscore"   # zscore / minmax

# === 距離・クラスタリング ===
distance:
  metric: "euclidean" # euclidean / cosine

clustering:
  method: "ward"      # ward / average / complete ...

# === クラスタ数の決定 ===
cluster_selection:
  enabled: true
  methods: ["silhouette", "elbow", "dendrogram_gap"]
  k_min: 2
  k_max: 10

# === 可視化 ===
plots:
  enabled: true
  embedding: "pca"     # pca / tsne など
```

---

## 8. `volume_eval` と併用するコツ

* `volume_eval` は「解集合としての多様性/被覆度」を数値で押さえる（集合の評価）
* `clustering_analysis` は「多様性が“どの系統”に分かれているか」を可視化する（構造の理解）

たとえば、

* volume は高いのに、クラスタが 1 つに集中 → 実は “同じタイプの多様性” しかない
* volume は低いが、クラスタは明確に分かれる → 方向性は複数あるが探索が浅い

のような診断がしやすくなります。

---

## 9. トラブルシューティング

* **入力が見つからない / 0 件になる**

  * `input_dir` と `solution_glob` を確認
  * 多様解生成の出力ディレクトリ名（`diverse_results` 等）が合っているか確認

* **クラスタリング結果が不安定**

  * 特徴量スケールが合っていない（正規化を有効化）
  * `k_max` が小さすぎる / 大きすぎる
  * 解数が少ない（`--num-solutions` を増やす）

* **散布図が「団子」になる**

  * そもそも特徴量が弱い（分解構造・割当・制約の観点を増やす）
  * PCA 以外（t-SNE 等）が有効な場合もある（ただし解釈性は注意）

---

## 10. 関連ドキュメント

* `README/README_diverse_solutions.md` : 多様解の生成方法
* `README/README_volume_eval.md` : 多様性評価（Volume / Diversity Evaluation）
* `README/pddl_multi_agent_algorithm.md` : 分解 + 割当の基本アルゴリズム
