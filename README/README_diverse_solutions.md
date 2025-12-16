# 多様解生成（Diverse Solutions Generation）

このドキュメントでは、同一の PDDL Domain/Problem に対して、
**サブタスク分解（decomposition）＋エージェント割当（allocation）** の解を複数生成し、
「品質が同程度でも**性質が異なる**」解集合（diverse solution set）を得る方法をまとめます。

* 実行エントリ: `src/cli/generate_diverse_solutions.py`
* 典型コマンド:

```bash
python -m src.cli.generate_diverse_solutions \
  --config configs/default_config.yaml \
  --num-solutions 20 \
  --output-dir diverse_results
```

> 生成した解集合の分析は、
>
> * クラスタリング: `README/README_clustering_analysis.md`
> * 多様性評価: `README/README_volume_eval.md`
>   を参照してください。

---

## 1. 何を「多様解」と呼ぶか

本リポジトリにおける「解」は概ね次で構成されます。

* サブタスク集合: (T={T_1,\dots,T_K})
* 割当: (\alpha: T\to \Lambda)

多様解生成は、同じ (\mathcal{D},\mathcal{P}) に対して、
((T,\alpha)) を複数作り、その集合 (\mathcal{S}={(T,\alpha)}_1^n) を出力します。

「多様」とは、たとえば以下が異なることを意味します。

* **分解の違い**: ゴールのグルーピング、サブタスク数、サブタスク粒度
* **割当の違い**: 同じ分解でも、担当エージェントの割当が異なる
* **性質の違い**: ある目的では負荷分散が良いが、別の目的ではサブタスク数が少ない等

---

## 2. 基本の使い方

### 2.1 最短実行

```bash
python -m src.cli.generate_diverse_solutions \
  --config configs/default_config.yaml \
  --num-solutions 20 \
  --output-dir diverse_results
```

### 2.2 生成結果（出力ディレクトリ）

```text
diverse_results/
├── result_000.json ~ result_019.json     # 生成された解
├── diverse_config_000.yaml ~ 019.yaml    # 各解の生成に使われた設定（seed/目的/微調整パラメータ等）
├── diversity_analysis.json               # 解集合の基本統計（距離/多様性の簡易集計など）
└── diversity_summary.txt                 # 人が読む用の要約
```

> 後段分析（クラスタリング/volume_eval）では `result_*.json` 群を入力にするか、
> あるいはクラスタリングで出力された特徴量CSVを入力にします（分析モジュールにより異なります）。

---

## 3. 多様化の仕組み（Feature-driven / Objective-driven）

### 3.1 ねらい

多様解生成では、単に seed を変えて「偶然の違い」を集めるだけでなく、
**狙う性質（目的関数）を解ごとに切り替える**ことで、
系統の異なる解が出やすいようにします。

例:

* サブタスク数を小さくしたい（粗い分解）
* エージェント負荷の分散を小さくしたい（バランス重視）
* role signature の種類を増やしたい（意味的に分かれた分解）

### 3.2 `feature_objectives` の概念

`configs/default_config.yaml` 側（または多様解生成側で上書きされる設定）で、
以下のような「特徴量ベースの目的」を持ちます。

* `name`: 目的名（特徴量のキー）
* `direction`: `minimize` / `maximize`
* `weight`: 重み

例（概念）:

```yaml
clustering:
  optimization_strategy: feature_driven
  feature_objectives:
    - name: subtask_count
      direction: minimize
      weight: 1.0
    - name: workload_variance
      direction: minimize
      weight: 1.0
```

多様解生成では、各解ごとに

* 目的の組み合わせ
* 重み
* seed
  -（必要なら）分解パラメータ（クラスタ粒度や merge 閾値など）

を変えて解を生成します。

> 実際に使える `feature_objectives` の種類は、
> 特徴量抽出実装（クラスタリング分析側の feature extractor 等）に依存します。

---

## 4. 「似た解ばかり」になったときの調整ポイント

### 4.1 まず増やす

* `--num-solutions` を増やす
* seed のレンジを広げる（多様解生成側が seed を内部生成している場合は、その規則を調整）

### 4.2 目的関数を増やす / 変える

* `feature_objectives` の種類を増やす
* 同じ特徴でも `direction` を反転する（min ↔ max）
* 重みの比率を変える（例: workload を強く、subtask_count を弱く）

### 4.3 分解粒度に効くパラメータを動かす

ドメイン・実装に依存しますが、一般に次が多様性に効きます。

* サブタスク数上限（(K_{max})）
* ゴールのクラスタ分割の粒度（クラスタサイズ上限など）
* merge の閾値（互換サブタスク統合の厳しさ）
* role-based partition のキー（どの role をキーにするか）

---

## 5. 多様解生成 → 分析のおすすめワークフロー

### 5.1 まず系統を可視化（クラスタリング）

```bash
python -m src.analyze.cluster_solutions --config configs/clustering_analysis_config.yaml
```

* どんなタイプの解が出ているか
* どの目的がどの系統に効いているか

をデンドログラム/散布図/summary で確認します。

### 5.2 解集合としての広がりを数値化（volume_eval）

```bash
python -m src.analyze.volume_eval --config configs/volume_eval_config.yaml
```

* 解集合の多様性・被覆度（volume/coverage）
* 距離分布

を評価し、「どの生成設定（目的セット）が良い解集合を作るか」を比較できます。

---

## 6. 新しい目的（feature objective）を追加したい場合

1. **特徴量を定義する**

   * 例: サブタスクサイズ分布、担当エージェントの偏り、role signature entropy など
2. **特徴量抽出に実装する**

   * クラスタリング分析側の feature extractor（解→feature vector）に列を追加
3. **`feature_objectives` に追加して試す**

   * まずは単独（その目的だけ）で解が変わるか確認
   * 次に複数目的の重みを調整

---

## 7. よくある Q&A

### Q1. 多様解生成の結果を、同じ条件で再現したい

* `diverse_config_XXX.yaml` を保存しておき、その設定で同じコマンドを再実行してください。
* seed が明示されていれば基本的に再現できます（ただし内部で並列実行や非決定性がある場合は差が出ます）。

### Q2. 生成に時間がかかる

* 解数（`--num-solutions`）を下げる
* 目的の数を減らす（多目的最適化が重い場合）
* PDDL の規模（large → small）で先に試す

### Q3. 生成した解が制約を破る

* constraint-aware merge や、制約述語の指定がズレている可能性があります。
* ドメインを切り替えた場合は、制約述語（例: reachable / weld_type など）を見直してください。

---

## 8. 関連ドキュメント

* `README/pddl_multi_agent_algorithm.md` : 分解＋割当の基本アルゴリズム
* `README/README_usage_guide.md` : 実行の全体導線
* `README/README_clustering_analysis.md` : 特徴量抽出・クラスタリング・可視化
* `README/README_volume_eval.md` : 多様性評価（volume/distance/coverage）
