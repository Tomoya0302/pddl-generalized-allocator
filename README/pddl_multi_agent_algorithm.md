# PDDL Multi-Agent Task Decomposition & Allocation Algorithm

本ドキュメントは、`pddl-generalized-allocator` が実装している **マルチエージェント向けタスク分解 + 割当アルゴリズム**を、数式・データ構造・処理フローとして整理したものです。

* 対象: PDDL Domain/Problem（古典計画）
* 目的: ゴール集合を **サブタスク** に分割し、各サブタスクを **実行可能なエージェントへ割り当て**る
* 追加: role による意味的分割（ドメイン知識の抽出器による一般化）と、上限サブタスク数 (K_{max}) の制約下での統合

> 多様解生成（diverse solutions）・多様解評価（volume evaluation）は、別資料 `README/README_diverse_solutions.md` および `src/analyze/volume_eval` を参照してください。

---

## 1. 問題定義

### 入力

* PDDL Domain: $$\mathcal{D}$$
* PDDL Problem: $$\mathcal{P}$$
* ゴール集合: $$G={g_1, \cdots , g_N}$$
* エージェント集合: $$\Lambda={\lambda_1, \cdots , \lambda_M}$$

### 出力

* サブタスク集合: $$T={T_1, \cdots , T_K}$$
* 割当関数: $$\alpha : T \rightarrow \Lambda$$

### 制約

* 各サブタスクはゴールの部分集合:
  $$T_i \subseteq G, ; \cup_i T_i = G, ; T_i \cap T_j = \emptyset$$
* 各サブタスクに割り当てられたエージェントはサブタスクを実行可能
* サブタスク数制約:
  $$|T|\leq K_{max}$$

---

## 2. データ構造

### PlanningTask

PDDL をプログラムが扱える構造に落としたもの。

```python
PlanningTask = {
  objects: Dict[type, Set[obj]],
  predicates: List[PredicateSchema],
  actions: List[ActionSchema],
  init: Set[GroundAtom],
  goals: Set[GroundAtom]
}
```

### MultiAgentTask / Capabilities

エージェントごとの実行可能アクション集合（能力）を定義します。

* $$\mathrm{Capabilities}(\lambda_i) = { A ; | ; a ;\mathrm{がパラメータ型的に実行可能} }$$

```python
AgentCapabilities = {
  agent_name: Set[action_names]
}
```

---

## 3. アルゴリズム全体フロー（1〜12）

### 1. PDDL から PlanningTask を生成

* Domain/Problem をパースし、オブジェクト・述語・アクション・初期状態・ゴールを構造化

### 2. MultiAgentTask + Capabilities の構築

* エージェント型パラメータを持つアクションから、各エージェントの能力（実行可能アクション集合）を推定

### 3. 因果グラフ CausalGraph: CG の構築

「前提に現れる述語」と「add 効果に現れる述語」の依存関係で、述語レベルの因果グラフを作ります。

```python
for action in actions:
  for p in action.preconditions:
    for q in action.add_effects:
      CG[p.predicate].add(q.predicate)
```

> del 効果は扱わない（add の因果を追う）前提。

### 4. ランドマーク LM 抽出

各ゴール述語に対して、因果グラフを **逆探索**し、重要な中間述語をランドマークとして付与します。

* $$LM(g) = \mathrm{BFS}^{-d}(g)$$

```python
Landmark = {
  goal_predicate: Set[important_predicates]
}
```

### 5. ゴール間のグラフ構築（構造的依存）

ゴール同士の関連性を、述語の一致・因果依存で定義します。

* $$adj(i, j) = \left{
  \begin{array}{ll}
  1 & \mathrm{if} ; pred(g_i) = pred(g_j) \
  1 & \mathrm{if} ; pred(g_i) \in CG(pred(g_j))\
  1 & \mathrm{if} ; pred(g_j) \in CG(pred(g_i)) \
  0 & \mathrm{otherwise} \ \end{array} \right .$$

### 6. グラフ連結成分分解（構造的タスク分解）

* ゴール依存グラフを連結成分に分け、独立に扱える塊へ分割

### 7. クラスタ分解

* 連結成分内をさらにクラスタリングし、分解粒度を調整
* 直観: 因果的に関係があるゴールが同じクラスタ、独立なら別クラスタ

### 8. サブタスクフォーマット導入

#### 8.1 ゴール集合の定義

* 連結成分 + クラスタで得られたゴール集合を (G_i) とする

#### 8.2 サブタスクフォーマット (F)

サブタスクが満たすべき「構造」を、role を含むタプルとして定義します。

* $$F=(\mathcal{R}, \mathcal{E}, \mathcal{K})$$
* $$\mathcal{R}={ r_1, \cdots , r_m }$$
* $$\mathcal{E}(r)={ E_{r,1}, E_{r,2}, \cdots }$$
* $$\mathcal{K}\subseteq \mathcal{R}$$

例（溶接ドメイン）:

* $$\mathcal{R}={ \mathrm{base}, \mathrm{hand_type}, \mathrm{hand}, \mathrm{agent} }$$
* $$\mathcal{K}={ \mathrm{base}, \mathrm{hand_type} }$$

サブタスクの実体:

* $$T_i = (G_i, LM_i, {roles}_i)$$

```python
SubTask {
  goals: List[GroundAtom],
  landmarks: Set[Predicate],
  roles: {r_1, ... , r_m}
}
```

#### 8.3 抽出器 (\mathcal{E}) の一般化定義

抽出器は、初期状態 (I) とゴール (g) から role の値候補を抽出するルールです。

* $$\mathcal{E}={ pred, bind, val }$$

抽出器 (E) は、述語 `pred` と引数束縛 `bind` を使って、初期状態の ground atom と join して `val` 位置の値を取り出します。

* $$E(g)= { x_{val}; | ; pred(x_0,\cdots ,x_n)\in I\wedge \forall j, x_{bind(j)}=y_j }$$

（ここで (y_j) は、ゴール (g) 側の引数や、すでに既知の変数束縛を表す）

#### 8.4 Role Extraction 全体は SAT/Join 問題

* 実装的には「ゴールの引数」↔「初期状態の事実」の結合（join）で候補集合を作り、矛盾がない組（SAT）を採用する形になります。

### 9. Role-based Finer Partition（意味的タスク分解）

各ゴール (g) について role 値を抽出し、キー集合 (\mathcal{K}) によるタプルで再分割します。

* 各ゴール g に対して roles(g) とは:

  $$roles(g) = { r\mapsto v_r ; | ; \exists E_{r,j} \in \mathcal{E}(r), v_r \in E_{r,j}(g) }$$

* キー (\mathcal{K})（例: base, hand_type）でグループ化:

  $$T_k = { g\in G ; | ; (roles(g).base, roles(g).hand_type) = c_k }$$

#### 溶接ドメイン例（role 抽出）

* ゴール例:
  $$g = \mathrm{welded}(\mathrm{weld_pos}_i)$$

* base 抽出（初期状態 (I) の `reachable` から）:
  $$base(w)= { b ; | ; reachable(b, w)\in I }$$

* hand_type 抽出（初期状態 (I) の `weld_type` から）:
  $$hand_type(w)= { ht ; | ; weld_type(w, ht)\in I }$$

> どの述語・束縛を使って role を抽出するかは、ドメインごとに `\mathcal{E}(r)` を設計します。

### 10. 最大サブタスク数制約

* もし (|T| > K_{max}) なら、サブタスクを統合して (K_{max}) 以下にする
* 統合は **制約違反を起こさない**（constraint-aware）ことが必須

  * 例: `reachable` / `weld_type` の矛盾を起こす統合は禁止

### 11. サブタスク定義

* (G_i)（ゴール群） + (LM_i)（ランドマーク） + role 情報（signature）を保持した最終サブタスク (T_i) を確定

### 12. エージェント割当

各サブタスク (T_i) に対して、エージェント (\lambda) のコストを定義し、最小コストのエージェントに割り当てます。

* 例（単純な能力サイズベース）:

  $$cost(T_i, \lambda) = \frac{1}{1+|\mathrm{Capabilities}(\lambda)|}$$

* 割当:

  $$\Lambda_i^* = \arg \min_\lambda cost(T_i, \lambda)$$

> 実運用では、`Capabilities(\lambda)` に加えて「タスクに必要な能力」「移動コスト」「干渉（同時実行制約）」「負荷分散」などの項を加えた目的関数に拡張します。

---

## 4. 実装メモ（読み進める順番）

アルゴリズム実装を追うときは、概ね次の順が読みやすいです。

1. PDDL パーサ → PlanningTask
2. Causal Graph / Landmark / Goal Graph
3. Connected Components / Clustering
4. Role extraction（(\mathcal{R},\mathcal{E},\mathcal{K}) 設計）
5. Constraint-aware merge（(K_{max}) 調整）
6. Allocation（cost 設計・割当）

---

## 5. 付記: 多様解（Diverse Solutions）との関係

* 上記 1〜12 は「1つの分解・割当」を作る基本フロー
* 多様解生成は、クラスタ粒度・merge の順序・seed・目的関数（minimize / balanced / distribute）などを変えて、**複数の (T, \alpha)** を収集する拡張
* 多様解評価は、生成された解集合に対して距離や被覆度（volume）を計算し、良い解集合を比較するための分析
