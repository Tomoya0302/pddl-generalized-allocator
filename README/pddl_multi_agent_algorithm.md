# PDDL Multi-Agent Task Decomposition & Allocation Algorithm

## 0. 問題設定の定式化

**入力**

- PDDL ドメイン \(\mathcal{D}\)
- PDDL 問題 \(\mathcal{P}\)
- ゴール集合 \(G = \{ g_1, g_2, \dots, g_N \}\)
- エージェント集合 \(\Lambda = \{ \lambda_1, \lambda_2, \dots, \lambda_M \}\)

**出力**

- サブタスク集合 \(T = \{ T_1, T_2, \dots, T_K \}\)
- 割当関数 \(\alpha : T \rightarrow \Lambda\)

**制約**

1. 各サブタスクはゴールの部分集合：
   $$
   T_i \subseteq G,\quad \bigcup_i T_i = G,\quad T_i \cap T_j = \emptyset
   $$
2. 各 \(T_i\) は PDDL 的に実行可能な構造制約を満たす
3. 各 \(\alpha(T_i)\) は \(T_i\) を実行可能な能力を持つ（下記の Capabilities で定義）
4. 可能なら \(|T| \le K_{\max}\)

---

## 1. PDDL から構文木 → PlanningTask への写像

PDDL パーサは以下を生成：

- Objects: \(\text{Obj}: \text{name} \mapsto \text{type}\)
- Predicates: \(\text{Pred}: p \mapsto (t_1, \dots, t_k)\)
- Actions: \(\text{Act}: A \mapsto (\text{params}, \text{pre}, \text{add}, \text{del})\)
- Init State: \(I \subseteq \text{GroundAtoms}\)
- Goals: \(G \subseteq \text{GroundAtoms}\)

これを `PlanningTask` が保持：

```python
PlanningTask = {
  objects: Dict[type, Set[obj]],
  predicates: Dict[name, PredicateSchema],
  actions: Dict[name, ActionSchema],
  init: Set[GroundAtom],
  goals: Set[GroundAtom]
}
```

---

## 2. MultiAgentTask + Capabilities の構築

PDDL の型 `agent_type` を「エージェント型」とする。\(\lambda \in \Lambda\) の PDDL 型を \(\text{type}(\lambda)\) と書く。

各アクション \(A \in \text{Act}\) のパラメータ列を

$$
\text{params}(A) = (x_1{:}\tau_1, \dots, x_k{:}\tau_k)
$$

とするとき、各エージェント \(\lambda \in \Lambda\) の能力集合を次のように定義する：

$$
\text{Capabilities}(\lambda)
  = \{ A \in \text{Act} \mid \exists x_j{:}\tau_j \in \text{params}(A): \tau_j = \text{type}(\lambda) = agent\_type \}.
$$

すなわち「エージェント型のパラメータを含むすべてのアクション」が、その型を持つエージェントにとって実行可能であるとみなす。

実装イメージ：

```python
AgentCapabilities = {  # 対応するのは理論上の Capabilities(λ)
  agent_name: Set[action_names]
}

for each action A in actions:
  for each parameter p in A.parameters:
    if type(p) == agent_type:
      for each agent λ with type(λ) == agent_type:
        AgentCapabilities[λ].add(A.name)
```

---

## 3. 因果グラフ CausalGraph の構築

ノード：

$$
V = \{ p \mid p \in \text{Predicates} \}
$$

辺の生成則：

$$
(p \rightarrow q) \in E \iff \exists A \in \text{Act}: p \in \text{Pre}(A) \land q \in \text{Add}(A)
$$

実装：

```python
for action in actions:
  for p in action.preconditions:
    for q in action.add_effects:
      CG[p.predicate].add(q.predicate)
```

この因果グラフは、ゴール同士が「同じ計画フローに乗りやすいかどうか」を測るための構造的近さの指標として用いる。

---

## 4. ランドマーク抽出（近似版）

各ゴール \(g \in G\) の述語を \(pred(g)\) とし、因果グラフ上で逆方向探索を行う：

$$
LM(g) = \text{BFS}^{-d}(pred(g))
$$

ここで \(d\) は 1〜3 のランダムな深さ（あるいはハイパーパラメータ）とする。これは

- ゴールに至るまでに「通りがちな中間述語」の近似集合
- 異なるゴール間の「共有部分構造」の近さ

を表すヒューリスティック情報である。

```python
for g in goals:
  L[g] = backward_bfs(CausalGraph, predicate(g), depth=random(1,3))
```

結果：

```python
Landmark = {
  goal_predicate: Set[important_predicates]
}
```

---

## 5. ゴール間グラフ（構造的依存グラフ）の構築

ゴール \(g_i, g_j\) の述語をそれぞれ \(p_i = pred(g_i), p_j = pred(g_j)\) とする。

基本的な隣接条件：

$$
adj(i,j) = 1 \;\text{if}\;
\begin{cases}
 p_i = p_j, & \text{(同じ述語ゴール)}\\
 p_i \in CG(p_j), & \text{(因果的に直接依存)}\\
 p_j \in CG(p_i) & \text{(因果的に直接依存)}
\end{cases}
$$

さらに、ランドマークに基づく「同じ計画フローに乗りそうか」の近さを、オプションで隣接に反映できる：

$$
adj(i,j) = 1 \;\text{if 上記のいずれか または } LM(g_i) \cap LM(g_j) \neq \emptyset.
$$

実装では、

- CG ベースの条件を **必須の構造的依存** として用い
- ランドマーク重なりを **ヒューリスティックな追加エッジ** としてオン/オフ切り替え可能

とするのが自然である。

こうしてゴール間無向グラフ \(\Gamma = (G, E)\) を構築する。

---

## 6. グラフ連結成分分解（第一次タスク分解）

$$
\mathcal{C} = \text{ConnectedComponents}(\Gamma)
$$

- 因果的に関係がある（同じ計画フローに乗りやすい）ゴールは同じクラスター
- 構造的に独立なゴールは別クラスター

ここまでで得られるクラスターは、「構造保存」という意味で最も素直なタスク候補である。

---

## 7. クラスターサイズ制限（`max_cluster_size`）

各 \(C \in \mathcal{C}\) を

$$
C = \{g_1,\dots,g_k\}
$$

とし、もし \(k > \text{max\_cluster\_size}\) ならば、\(C\) を内部順序（例：BFS 順やインデックス順）に沿って連続な部分列に分割する：

$$
C \approx \{ \{g_1,\dots,g_m\}, \{g_{m+1},\dots,g_{2m}\}, \dots \}.
$$

この分割は、元の \(\Gamma\) における「完全な因果独立性」を保証するものではなく、

- **クラスターが巨大になりすぎるのを避けるための実用的なヒューリスティック**
- 同一連結成分内での局所的な近さ（BFS 順）をできるだけ保つ

ことを目的としている。

このステップは、後述の e-greedy 再試行で「シャッフル度合い」を変化させる対象にもなる。

---

## 8. Role Extraction（PDDL 制約を構造に埋め込む）

ドメイン依存の設定として、例えば次のような対応を考える：

```text
base      ← reachable(base, weld)
hand_type ← weld_type(weld, ht)
hand      ← hand_type(hand, ht)
agent     ← hand_rel(agent, hand)
```

これは論理式では：

$$
\exists b:\; reachable(b, w)
$$

$$
\exists ht:\; weld\_type(w, ht)
$$

$$
\exists h:\; hand\_type(h, ht)
$$

$$
\exists \lambda:\; hand\_rel(\lambda, h)
$$

に対応する。

ここで前提として：

- これらの関係は「初期状態 \(I\) のみから一意に決まる」
- プラン中に変化しない（静的述語）

ことが保証されているとする。このとき、各ゴール \(g = welded(w)\) について：

$$
roles(g) = (b, ht, h, \lambda)
$$

を一意に求めることができる。

---

## 9. Role-based Finer Partition（意味的タスク分解）

クラスターキーの例として：

$$
\text{cluster\_keys} = (base, hand\_type)
$$

とり、次の同値関係でゴールを分類する：

$$
g_i \sim g_j \iff
roles(g_i).base = roles(g_j).base
\land
roles(g_i).hand\_type = roles(g_j).hand\_type.
$$

第一次クラスタリングで得た各クラスター \(C \in \mathcal{C}\) を、この同値関係によりさらに細分化する：

$$
T = \text{Quotient}(\mathcal{C}, \sim).
$$

これにより：

- 同じ基地・同じ工具でできるゴールは同一サブタスクにまとまり
- 物理的に無理な組合せは（前提より）同一クラスに入り得ない

という意味で、PDDL の静的制約をサブタスク構造に反映させる。

---

## 10. `max_subtasks` 制約 + e-greedy 再試行

ここまでで得られたサブタスク集合を \(T = \{T_1, \dots, T_K\}\) とする。

もし \(|T| \le K_{\max}\) なら、このステップは成功とみなし次へ進む。

もし \(|T| > K_{\max}\) なら、以下の **e-greedy 型再試行ループ** を実行する：

1. まず、完全に同じ role パターン（base, hand\_type, hand, \(\lambda\) など）を持つ \(T_i, T_j\) に限ってマージを試みる。
2. マージ後もなお \(|T| > K_{\max}\) であれば、現在の試行を **失敗** とみなし、Step 7 へロールバックする。
3. 再試行回数を \(r = 0, 1, 2, \dots\) とし、各試行ごとに e-greedy パラメータ \(\varepsilon_r\) を増加させる：
   - 例：\(\varepsilon_r = \min(1, \varepsilon_0 + r \cdot \Delta)\)
4. Step 7（クラスターサイズ制限）の際に、
   - 確率 \(1 - \varepsilon_r\) で「ランドマーク・因果構造に基づく順序」（BFS 順や LM 類似度順）を優先
   - 確率 \(\varepsilon_r\) で「ゴール集合のランダムシャッフル」に基づいて分割 を行う（e-greedy）
5. その後、Step 8〜9 を再実行して新しい \(T\) を構成し、再び \(|T| \le K_{\max}|\) かどうかを判定する。

最大再試行回数 \(R_{\max}\) を越えてもなお \(|T| > K_{\max}|\) の場合のみ、

$$
\textbf{UNSAT（解なし）}
$$

と最終的に判定する。

直感的には：

- 初期試行では **ランドマーク・因果構造を強く信頼** して分割
- 失敗が続くと徐々に **ランダムシャッフルの比率を増やし**, 構造ヒューリスティックから探索的挙動へと移行

することで、局所解にハマるのを避けつつ、構造保存性と探索性のトレードオフを制御する。

---

## 11. サブタスク定義

各サブタスク \(T_i\) は：

```python
SubTask {
  goals: List[GroundAtom],
  landmarks: Set[Predicate],
  roles: {base, hand_type, hand, λ}
}
```

すなわち

$$
T_i = (G_i, LM_i, roles_i)
$$

という意味付きゴール集合として表現される。

ランドマーク \(LM_i\) は、

- そのサブタスクを解く際に現れやすい中間述語集合
- プランナーへのヒントや、さらなるサブタスク細分化の根拠

として利用可能である（利用するかどうかは設計に依存）。

---

## 12. エージェント割当（Allocation）

各サブタスク \(T_i\) と各エージェント \(\lambda \in \Lambda\) についてコスト関数

$$
cost(T_i, \lambda)
$$

を定義する。

単純な例：

$$
cost(T_i, \lambda) = \frac{1}{1 + |\text{Capabilities}(\lambda)|}.
$$

これにより「専門性が高い（できることが少ない）エージェントを優先する」ような割当になる。

最小コスト集合：

$$
\Lambda_i^* = \arg\min_{\lambda \in \Lambda} cost(T_i, \lambda)
$$

そこからランダム選択して割り当て：

$$
\alpha(T_i) \sim \text{Uniform}(\Lambda_i^*).
$$



---

## 13. アルゴリズムの要約

1. PDDL から `PlanningTask` を構築
2. エージェント型 `agent_type` と \(\Lambda\) から \(\text{Capabilities}(\lambda)\) を数式どおりに導出
3. 述語レベル因果グラフ `CausalGraph` を構築
4. 各ゴールに対しランドマーク集合 \(LM(g)\) を近似的に抽出
5. 因果グラフとランドマークに基づきゴール間依存グラフ \(\Gamma\) を構築
6. \(\Gamma\) の連結成分で第一次クラスタリング \(\mathcal{C}\) を得る
7. `max_cluster_size` に従ってクラスターを分割（e-greedy 再試行では分割戦略を変化させる）
8. Role Extraction により各ゴールに (base, hand\_type, hand, \(\lambda\)) を付与
9. role ベースの同値関係でクラスタを細分化してサブタスク集合 \(T\) を得る
10. `max_subtasks` 制約をチェックし、
    - OK なら次へ
    - NG なら e-greedy で Step 7 へロールバックし再試行（\(r\) に応じてランダム性を増加）
11. 再試行がすべて失敗した場合のみ最終的に UNSAT
12. 各サブタスク \(T_i\) を (goals, landmarks, roles) で定義
13. `Capabilities(\lambda)` とコスト関数に基づいてエージェント割当 \(\alpha\) を決定

