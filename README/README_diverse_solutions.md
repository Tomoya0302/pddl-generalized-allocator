# Diverse Solutions Generator with Domain-Free Features

このドキュメントでは、`pddl-generalized-allocator` における「16種類の domain-free features を用いた多様解算出アルゴリズム」について説明します。

対象ファイル:

* `src/features/domain_free_features.py`
* `src/planning/multi_objective_merge.py`
* `src/planning/clustering.py`
* `src/cli/generate_diverse_solutions.py`
* `src/config/schema.py`
* `configs/*.yaml`

## 1. 目的

従来の多様解生成は、

* 乱数シード
* クラスタリング戦略（`minimize_subtasks` / `balanced` / `distribute_goals` / `auto`）
* クラスタサイズやサブタスク数などのパラメータ

を変えることで、多様なサブタスク分解解を得ていた。

本アルゴリズムではさらに一歩進めて、

> **「解の形」を 16 個の domain-free features で定量化し、それぞれを“目的関数”として使い分けながら多様解を生成する**

ことを目指す。

---

## 2. 16種類の domain-free features

特徴量そのものの計算は `src/features/domain_free_features.py` に集約される。特徴量は以下の通り。

### 2.1 サブタスク & ゴール分布

* `subtask_count`
  サブタスク数。
* `goal_mean`
  サブタスク1つあたりの平均ゴール数。
* `goal_variance`
  サブタスク間のゴール数分散。
* `goal_min`
  1サブタスクあたりゴール数の最小値。
* `goal_max`
  1サブタスクあたりゴール数の最大値。
* `goal_range`
  `goal_max - goal_min`。

### 2.2 エージェント負荷バランス

* `num_active_agents`
  1つ以上のサブタスクを持つエージェント数。
* `agent_balance_variance`
  エージェントごとの担当サブタスク数の分散。
* `agent_balance_max_min_ratio`
  最大担当数と最小担当数の比。

### 2.3 role_signature に関する多様性・複雑さ

* `unique_role_signature_count`
  異なる `role_signature` パターン数。
* `role_signature_entropy`
  `role_signature` 出現分布のエントロピー。
* `avg_role_attributes_per_subtask`
  1サブタスクあたりの role 属性数（複数値を展開後）。
* `complex_role_ratio`
  複合値（`|` を含む）を持つサブタスク比率。
* `avg_role_complexity`
  role 属性数の平均。

### 2.4 サブタスク間類似度

サブタスク間の pairwise 類似度を、ランドマーク + role + ゴール数から計算し、

* `avg_subtask_similarity`
  類似度平均。
* `similarity_variance`
  類似度分散。

として集約する。

これら 16 個はすべてドメインに依存しない形で定義されているため、`domain-free features` と呼ぶ。

---

## 3. FeatureDrivenStrategy によるタスク分解制御

タスク分解の最終段階で、`multi_objective_merge.py` の `FeatureDrivenStrategy` を用いてサブタスク統合を行う。

### 3.1 FeatureObjective

`src/config/schema.py` にて、複数特徴量を扱うための構造体 `FeatureObjective` を定義する。

```python
@dataclass
class FeatureObjective:
    name: str          # 例: "subtask_count", "avg_subtask_similarity" など
    direction: str     # "min" または "max"
    weight: float = 1.0
```

`ClusteringConfig` はこれをフィールドとして持つ。

```python
@dataclass
class ClusteringConfig:
    ...
    optimization_strategy: Optional[str] = None
    strategy_randomness: float = 0.1
    feature_objectives: List[FeatureObjective] = field(default_factory=list)
```

### 3.2 FeatureDrivenStrategy

`FeatureDrivenStrategy` は、`feature_objectives` に含まれる複数の特徴量を重み付き和として扱い、

```python
score = sum( weight_k * proxy(feature_k, direction_k, subtask1, subtask2) )
```

という形でマージ候補のスコアを評価する。

* `proxy(...)` は、16特徴量を完全に再計算する代わりに、局所的なヒューリスティックで近似する。
* 例:

  * `subtask_count` → マージすると必ず -1 なので、`min` なら常に高スコア
  * `goal_variance` → サブタスクサイズ差が大きいマージを好む/嫌う
  * `avg_subtask_similarity` → ランドマーク・role の似ていないペアを好む/嫌う

最後に `randomness` パラメータに応じてスコアに乱数を掛けることで、局所最適に陥りにくくしている。

### 3.3 clustering からの呼び出し

`src/planning/clustering.py` の `build_subtasks_with_retry` 内で、

1. role 制約に基づく `constraint_aware_merge_subtasks` を実行
2. `cfg_cluster.optimization_strategy == "feature_driven"` の場合、
   `multi_objective_merge_subtasks(..., feature_objectives=cfg_cluster.feature_objectives)` を呼び、
   FeatureDrivenStrategy による統合を行う

ことで、クラスタリングの最終形を feature-driven に制御する。

---

## 4. 16特徴量を使った多様解生成スケジューラ

多様解生成の CLI (`src/cli/generate_diverse_solutions.py`) は、

* 複数の config ファイルを自動生成
* 各 config に異なる `feature_objectives` を設定
* それぞれを `src/cli/main.py` に渡して解を生成

する仕組みになっている。

### 4.1 ベースとなる16特徴量テーブル

```python
BASE_FEATURE_OBJECTIVES = [
    {"name": "subtask_count",               "direction": "min"},
    {"name": "goal_mean",                   "direction": "min"},
    {"name": "goal_variance",               "direction": "max"},
    {"name": "goal_min",                    "direction": "max"},
    {"name": "goal_max",                    "direction": "min"},
    {"name": "goal_range",                  "direction": "max"},

    {"name": "num_active_agents",           "direction": "max"},
    {"name": "agent_balance_variance",      "direction": "min"},
    {"name": "agent_balance_max_min_ratio", "direction": "min"},

    {"name": "unique_role_signature_count", "direction": "max"},
    {"name": "role_signature_entropy",      "direction": "max"},
    {"name": "avg_role_attributes_per_subtask", "direction": "max"},
    {"name": "complex_role_ratio",          "direction": "max"},
    {"name": "avg_role_complexity",         "direction": "max"},

    {"name": "avg_subtask_similarity",      "direction": "min"},
    {"name": "similarity_variance",         "direction": "max"},
]
```

### 4.2 ラウンドごとの特徴量選択ルール

解インデックス `i` (0-based) に対して、以下のルールで `feature_objectives` を決定する。

* 1週目 (round=1): 単一特徴量（順方向）
* 2週目 (round=2): 単一特徴量（方向反転）
* 3週目 (round=3): 2特徴量の融合（順方向）
* 4週目 (round=4): 2特徴量の融合（方向反転）
* 5週目 (round=5): 3特徴量の融合（順方向）
* 6週目 (round=6): 3特徴量の融合（方向反転）
* ...

ここで 1週 = 16解（BASE_FEATURE_OBJECTIVES の長さ）とする。

擬似コード:

```python
def build_feature_objectives_for_solution(i: int) -> List[dict]:
    n = len(BASE_FEATURE_OBJECTIVES)
    round_index = i // n       # 0,1,2,...
    round_num = round_index + 1
    base_idx = i % n

    # 使う特徴量の個数: 1,1,2,2,3,3,...
    combo_size = (round_num + 1) // 2

    # 偶数ラウンドは方向反転
    flip_direction = (round_num % 2 == 0)

    indices = [(base_idx + k) % n for k in range(combo_size)]
    weight = 1.0 / combo_size

    objectives = []
    for idx in indices:
        base = BASE_FEATURE_OBJECTIVES[idx]
        base_dir = base["direction"]
        direction = ("max" if base_dir == "min" else "min") if flip_direction else base_dir
        objectives.append({
            "name": base["name"],
            "direction": direction,
            "weight": weight,
        })
    return objectives
```

この関数で得た `objectives` を、そのまま YAML の `clustering.feature_objectives` に書き込む。

### 4.3 config 生成と実行ログ

`create_diverse_configs` は、

1. ベース config を読み込み
2. 各解インデックス `i` ごとに

   * `build_feature_objectives_for_solution(i)` で特徴量セットを生成
   * `clustering.optimization_strategy = "feature_driven"`
   * `clustering.feature_objectives = objectives`
     として新しい config を書き出す

という動作を行う。

CLI 実行時には、

```text
⚙️  Running solution 154/160: diverse_config_153.yaml (timeout: 120s)
   ↳ 使用特徴量: subtask_count(min, w=0.50), avg_subtask_similarity(min, w=0.50)
✅ Solution 154 completed successfully
```

のように、各解で使われた特徴量セットがログに出力される。

---

## 5. 使い方

### 5.1 事前準備

* `FeatureObjective` / `ClusteringConfig.feature_objectives` / `FeatureDrivenStrategy` / `domain_free_features` などの変更を反映済みであること。
* `configs/default_config.yaml` に `clustering.feature_objectives: []` が定義されていること。

### 5.2 多様解生成

```bash
python -m src.cli.generate_diverse_solutions \
  --config configs/default_config.yaml \
  --num-solutions 160 \
  --output-dir diverse_feature_solutions
```

* 1〜16解: 16特徴量それぞれを単独・元方向で最適化
* 17〜32解: 同じ16特徴量を単独・方向反転で最適化
* 33〜48解: 2特徴量の組み合わせを元方向で最適化
* 49〜64解: 2特徴量の組み合わせを方向反転で最適化
* 65〜...: 3特徴量、4特徴量... と順に増やしていく

### 5.3 解の分析

生成された `result_*.json` を `SolutionFeatureExtractor` で解析すれば、

* 各解の 16 次元 feature ベクトル
* 解どうしの距離 / クラスタリング

などを通じて、「どの特徴量を目的にした解が、どのようなタスク分解構造を持ったか」を詳細に分析できる。

---

## 6. 拡張の方向性

* FeatureDrivenStrategy 内の `proxy` 設計を改善し、「真の feature 変化」に近づける
* エージェント負荷関連の特徴量を、allocation フェーズにも組み込む
* 複数特徴量の重みを自動調整する（例: 既存解との距離最大化など）

現状の実装でも、

* 「何を最適化した解か」が明示され
* 16種類の domain-free features を軸に多様解を組織的に生成できる

という点で、従来の seed ベース多様化よりも制御性と解釈性が高いフレームワークになっている。
