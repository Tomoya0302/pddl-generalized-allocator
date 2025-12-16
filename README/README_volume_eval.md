# 多様性評価（Volume / Diversity Evaluation）

このドキュメントは、`pddl-generalized-allocator` が生成した **多様解（分解・割当の解集合）** を対象に、

* 解集合の **多様性（diversity）**
* 解空間の **被覆度（volume / coverage）**
* 解同士の **距離（pairwise distance）**

などを計算・可視化・集計するための手順をまとめたものです。

> 実行エントリは `src/analyze/volume_eval/__main__.py` で、
> `python -m src.analyze.volume_eval --config configs/volume_eval_config.yaml` で起動します（トップ README にも記載）。

---

## 1. 前提

* 先に **多様解生成** を実行し、解ファイル（例: `result_000.json` など）が出力されていること
* 評価設定 `configs/volume_eval_config.yaml` が用意されていること

典型的なパイプライン（トップ README の流れ）:

```bash
# Step 1: 多様解生成
python -m src.cli.generate_diverse_solutions \
  --config configs/default_config.yaml \
  --num-solutions 20 \
  --output-dir analysis_dataset

# Step 2: 多様解評価
python -m src.analyze.volume_eval --config configs/volume_eval_config.yaml
```

---

## 2. 実行方法

```bash
python -m src.analyze.volume_eval --config configs/volume_eval_config.yaml
```

* `--config` で指定した YAML に従い、

  * どの解集合を評価するか（入力ディレクトリ）
  * どの指標を計算するか（指標セット）
  * 正規化・集約の方法
  * 出力先
    を切り替えます。

---

## 3. 入力（評価対象）

### 3.1 想定ディレクトリ構成

多様解生成の出力例（トップ README の例）:

```text
diverse_results/
├── result_000.json ~ result_019.json
├── diverse_config_000.yaml ~ 019.yaml
├── diversity_analysis.json
└── diversity_summary.txt
```

`volume_eval` は、このような **解ファイル群** を入力として読み込みます。

### 3.2 解ファイルに含まれるべき情報（概念）

実装の前提として、各解（1ファイル）は概ね次の情報を持ちます。

* サブタスク分解（例: サブタスク数、各サブタスクに含まれるゴール）
* エージェント割当（どのサブタスクがどのエージェントに割り当てられたか）
* 追加メタ情報（スコア、戦略、seed 等）

> ファイルフォーマットが変更された場合は、`volume_eval` 側のローダが解釈するキーに合わせてください。

---

## 4. 出力

トップ README の説明では、`output_dir` 次第で、概ね次が出力されます。

```text
volume_eval/
├── volume_eval_summary.txt
├── volume_eval_metrics.json
└── (optional) plots/*.png
```

* `volume_eval_summary.txt`

  * 実行条件、対象解数、主要指標の要約（平均、中央値、分散、上位/下位など）
* `volume_eval_metrics.json`

  * 各解・各解ペアに紐づく詳細なメトリクス（距離行列、正規化値、volume 集計など）
* `plots/*.png`（設定で有効な場合）

  * 距離分布、指標分布、2D 埋め込み（PCA 等）など

---

## 5. 評価指標（設計の考え方）

`volume_eval` は、「解集合の良さ」を **1つのスコア** に潰すのではなく、以下の観点を分けて扱うことを想定しています。

### 5.1 Diversity（多様性）

* **解同士がどれだけ異なるか**
* 例:

  * サブタスク構造の差（ゴールのグルーピングの違い）
  * 割当の差（同じ分解でも割当が異なる）
  * サブタスク数・負荷分散の違い

### 5.2 Distance（距離）

* 解 (s_i) と (s_j) の距離 (d(s_i, s_j)) を定義し、

  * 距離行列
  * 距離分布
  * 近傍数（一定距離以下の解が何個あるか）
    などを計算します。

### 5.3 Volume / Coverage（被覆度）

* 目的関数空間（例: サブタスク数、負荷バランス、達成目標分布など）上で、
  **解集合がどれだけ広い範囲をカバーしているか** を評価します。

> トップ README では、volume は「目的関数に基づく解空間の被覆度（volume）」として説明されています。

---

## 6. 設定ファイル（configs/volume_eval_config.yaml）

実際のキーは `configs/volume_eval_config.yaml` を正としてください。
ここでは「どんな項目があると運用しやすいか」の観点で、README 用のテンプレ例を示します。

> **注意**: 以下は説明用のテンプレです。実装に合わせてキー名・構造を調整してください。

```yaml
# === 入出力 ===
input_dir: "diverse_results"          # 多様解ファイル群のあるディレクトリ
output_dir: "volume_eval"            # 評価結果の出力先

# === 対象ファイル ===
solution_glob: "result_*.json"       # 読み込む解ファイルのパターン

# === 指標 ===
metrics:
  - name: "pairwise_distance"
  - name: "diversity_summary"
  - name: "volume_coverage"

# === 距離定義（例） ===
distance:
  mode: "assignment+structure"       # 割当差 + 構造差
  weights:
    assignment: 1.0
    structure: 1.0

# === 正規化・集約（例） ===
normalize:
  enabled: true
  method: "minmax"                   # minmax / zscore など

plots:
  enabled: true
  embedding: "pca"                   # pca / tsne など
```

---

## 7. よくある使い分け

### 7.1 「多様解生成の結果が本当に多様か？」を確認したい

* pairwise distance 分布を見て、

  * 近い解ばかりになっていないか
  * 特定のクラスに偏っていないか
    を確認します。

### 7.2 「解集合として、探索範囲を広くカバーしたい」

* volume / coverage を優先
* 目的関数（何を軸に解空間を定義するか）を明確にしてから評価します

### 7.3 「クラスタリング分析と繋げたい」

* `volume_eval_metrics.json` で得た距離や指標を、
  `README_clustering_analysis.md` の特徴量抽出・クラスタリングにフィードすると、
  "多様性はあるが、実は同じ系統" のような偏りを見つけやすくなります。

---

## 8. トラブルシューティング

* **入力ディレクトリが空／解が見つからない**

  * `input_dir` と `solution_glob` を確認
  * 先に多様解生成を実行しているか確認

* **解ファイルのキーが合わずに落ちる**

  * 解フォーマット変更に伴い、ローダの期待するキーがズレている可能性

* **評価が重い／遅い**

  * 解数 (N) に対しペア距離は (O(N^2)) になりやすい
  * サンプリング評価や、距離計算の簡略化（割当のみ等）を検討

---

## 9. 関連ドキュメント

* `README/README_diverse_solutions.md` : 多様解の生成方法
* `README/README_clustering_analysis.md` : 解集合の特徴量抽出・クラスタリング・可視化
* `README/pddl_multi_agent_algorithm.md` : 分解 + 割当の基本アルゴリズム
