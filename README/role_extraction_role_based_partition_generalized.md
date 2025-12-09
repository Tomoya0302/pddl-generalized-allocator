# Role Extraction & Role-based Finer Partition の一般化説明

## 0. 位置づけ（Step 8・9 の役割）

全体アルゴリズムは大きく

- (A) ゴール間の **論理的依存**：因果グラフ \(CG\)
- (B) ゴールと **物理・機構・リソース制約**：Role Extraction
- (C) (A)+(B) を同時に満たすような **クラスタリング**：SubTask 分解

の 3 層構造になっている。

このうち

- **Step 8 = (B)**：PDDL 初期状態 \(I\) に埋め込まれた制約から、各ゴールに対して role を解読する段階
- **Step 9 = (B) を使った (C)**：role の等価性に基づいて、物理的・機構的に意味のあるサブタスクに細分化する段階

に対応する。

以下では、Step 8・9 を **一般のドメインに対して記述できる数式レベル** まで抽象化する。

---

## 1. 前提：ゴールと初期状態の形式化

### 1.1 ゴール集合

ゴール集合を

$$
G = \{ g_1, g_2, \dots, g_N \}
$$

とする。各ゴールは ground atom：

$$
 g = p(o_1, \dots, o_k)
$$

ここで

- \(p\)：述語名
- \(o_i\)：オブジェクト（PDDL の `:objects` に含まれる）

例（TSSW / 溶接ドメイン）では：

$$
 g = welded(weld\_pos\_i)
$$

が典型的なゴールである。

PDDL の初期状態は ground atom の集合：

$$
I \subseteq \text{GroundAtoms}
$$

Role Extraction は「\(I\) に書かれた静的述語から、各ゴールに紐づく base / tool / agent などを復元する処理」とみなすことができる。

---

## 2. サブタスクフォーマット F（DomainRoleConfig）の一般化

Step 8・9 で使う「config」は、数学的には次の 3 つ組：

$$
F = (\mathcal{R}, \mathcal{E}, \mathcal{K})
$$

### 2.1 役割集合（Roles）

$$
\mathcal{R} = \{ r_1, r_2, \dots, r_m \}
$$

例：溶接ドメインでは

$$
\mathcal{R} = \{ \text{base}, \text{hand\_type}, \text{hand}, \lambda \}
$$

ここで \(\lambda\) は「担当エージェント」を表す役割。

### 2.2 抽出器集合（Extractors）

各役割 \(r \in \mathcal{R}\) に対し、抽出器の集合 \(\mathcal{E}(r)\) を定義する：

$$
\mathcal{E}(r) = \{ E_{r,1}, E_{r,2}, \dots \}
$$

各抽出器 \(E\) は「どの述語から、どの引数を、どう条件付けして取り出すか」を表す。

### 2.3 クラスタキー（Cluster Keys）

クラスタリングに直接使う役割集合：

$$
\mathcal{K} \subseteq \mathcal{R}
$$

例：

$$
\mathcal{K} = \{ \text{base}, \text{hand\_type} \}
$$

これは「サブタスクを識別する際に、base と hand\_type だけを使う」ことを意味する。

---

## 3. 抽出器 E の形式的定義

1 つの抽出器を

$$
E = (pred, bind, val)
$$

の 3 つ組として表す：

- \(pred\)：PDDL 述語名（例：`reachable`, `weld_type` など）
- \(val \in \mathbb{N}\)：`pred` のどの引数を取り出すかを示すインデックス
- \(bind\)：\(pred\) の各引数位置に対する **束縛指定**

束縛関数 \(bind\) は

$$
 bind : \{0,1,\dots,n\} \to (\text{goal:i} \mid \text{role:r}) \cup \{\bot\}
$$

のように定義する：

- `goal:i`：現在のゴール \(g = p(o_0,\dots,o_k)\) の第 \(i\) 引数 \(o_i\) を、この位置に束縛する
- `role:r`：すでに抽出済みの role 値 \(roles(g).r\) を束縛する
- \(\bot\)：束縛なし（任意値）

### 3.1 抽出器の意味論

抽出器 \(E = (pred, bind, val)\) がゴール \(g\) に対して返す値集合を

$$
E(g) \subseteq Obj
$$

と定義する。ここで \(Obj\) はオブジェクト集合。具体的には：

$$
E(g) = \{ x_{val} \mid pred(x_0,\dots,x_n) \in I \land \forall j,\; bind(j) \neq \bot \Rightarrow x_j = B_j(g) \}
$$

ただし \(B_j(g)\) は `goal:i` / `role:r` の参照を実際のオブジェクトに解決する関数：

- もし \(bind(j) = \text{goal:i}\) なら \(B_j(g) = g\) の第 \(i\) 引数
- もし \(bind(j) = \text{role:r}\) なら \(B_j(g) = roles(g).r\)

**重要なポイント**：

- これは関係代数でいう **selection + projection** に相当する
- 初期状態 \(I\) 上の「条件付き射影」になっている

---

## 4. Role Extraction 全体：CSP / 関係結合としての捉え方

各ゴール \(g\) に対し、roles(g) は役割からオブジェクトへの写像：

$$
roles(g) : \mathcal{R} \to Obj
$$

を求める問題である。これは以下のような制約充足（CSP）として書ける：

### 4.1 制約系

各役割 \(r \in \mathcal{R}\) について、少なくとも 1 つの抽出器 \(E \in \mathcal{E}(r)\) を選び、その出力と \(roles(g).r\) が一致する：

$$
\forall r \in \mathcal{R},\; \exists E \in \mathcal{E}(r):\; roles(g).r \in E(g, roles(g))
$$

ここで \(E(g, roles(g))\) は、`role:*` 参照を含む bind を roles(g) で解決した上での評価。

### 4.2 一意性の仮定

実装上は、各 \(r\) について \(E(g)\) が 1 要素集合になること（あるいは選択規則で一意に決まること）を仮定している：

$$
|E(g)| = 1 \Rightarrow roles(g).r = \text{唯一の要素}
$$

このとき Role Extraction は

> 初期状態 \(I\) 上で定義された **リレーショナル結合と射影からなる SAT/Join 問題の解を求めている**

と解釈できる。

---

## 5. TSSW/Welding ドメインにおける完全具体例

あなたが使っている welding 用 config を、上の形式で読み直す。

### 5.1 base の抽出

```json
"base": {
  "extractors": [
    {
      "predicate": "reachable",
      "bindings": { "1": "goal:0" },
      "value_arg": 0
    }
  ]
}
```

これは数学的には：

$$
base(w) = \{ b \mid reachable(b, w) \in I \}
$$

を意味し、Role Extraction では

$$
roles(g).base = b \quad \text{s.t. } g = welded(w),\ reachable(b,w) \in I
$$

と解釈される。

### 5.2 hand\_type の抽出

```json
"hand_type": {
  "extractors": [
    {
      "predicate": "weld_type",
      "bindings": { "0": "goal:0" },
      "value_arg": 1
    }
  ]
}
```

$$
hand\_type(w) = \{ ht \mid weld\_type(w, ht) \in I \}
$$

### 5.3 hand の抽出

```json
"hand": {
  "extractors": [
    {
      "predicate": "hand_type",
      "bindings": { "1": "role:hand_type" },
      "value_arg": 0
    }
  ]
}
```

$$
hand(ht) = \{ h \mid hand\_type(h, ht) \in I \}
$$

ここで `bindings[1] = "role:hand_type"` は、すでに求めた \(roles(g).hand\_type\) を使って join していることを意味する。

### 5.4 agent の抽出

```json
"agent": {
  "extractors": [
    {
      "predicate": "hand_rel",
      "bindings": { "1": "role:hand" },
      "value_arg": 0
    }
  ]
}
```

$$
agent(h) = \{ a \mid hand\_rel(a, h) \in I \}
$$

---

### 5.5 まとめ：4 段の関係結合

全体として

$$
w \xrightarrow{reachable} b
$$

$$
w \xrightarrow{weld\_type} ht
$$

$$
ht \xrightarrow{hand\_type} h
$$

$$
h \xrightarrow{hand\_rel} \lambda
$$

という **4 段の join** を初期状態 \(I\) 上で実行している。これはまさに PDDL に埋め込まれた機構・配置制約を、そのまま Role 空間上に持ち上げたものである。

---

## 6. なぜ「config を与えるだけ」で制約が守られるのか？

Role Extraction は、初期状態 \(I\) 上で定義された join + selection によって roles(g) を決めている。

つまり、任意のゴール \(g\) について

$$
roles(g) = (base_g, hand\_type_g, hand_g, \lambda_g)
$$

が得られたとき、これは必ず

$$
I \models reachable(base_g, g)\\
I \models weld\_type(g, hand\_type_g)\\
I \models hand\_type(hand_g, hand\_type_g)\\
I \models hand\_rel(\lambda_g, hand_g)
$$

を満たす。

> 言い換えれば：Role Extraction の出力は、常に PDDL 初期状態のモデルに対して **充足可能な割り当て** になっている。

したがって：

- reachable でない組み合わせ（物理的に届かない base と weld）は **roles(g)** として生成されない
- hand\_type 不一致（工具種が合わない）な組合せも生成不能
- agent 不一致（その hand を持たないエージェント）も生成不能

となり、「config を一貫した形で与えさえすれば、サブタスク構造が自動的にドメイン制約を尊重する」ことになる。

これは Step 8 の理論的な意味である。

---

## 7. Role-based Finer Partition の完全形式化（Step 9）

Step 9 では、Role Extraction で得られた \(roles(g)\) を使ってゴールを同値類に分ける。

### 7.1 同値関係の定義

クラスタキー集合 \(\mathcal{K} \subseteq \mathcal{R}\) に対して、ゴール間の同値関係 \(\sim\) を

$$
g_i \sim g_j
\iff
\forall r \in \mathcal{K}: roles(g_i).r = roles(g_j).r
$$

と定義する。

- 溶接ドメインの例では \(\mathcal{K} = \{ base, hand\_type \}\) なので：

$$
g_i \sim g_j
\iff
roles(g_i).base = roles(g_j).base
\land
roles(g_i).hand\_type = roles(g_j).hand\_type
$$

これは明らかに\*\*同値関係（反射的・対称的・推移的）\*\*である。

### 7.2 商集合としてのサブタスク集合

第一次クラスタリングで得られた構造クラスター \(\mathcal{C}\)（因果グラフ由来）を固定し、その中で \(\sim\) による同値類をとる：

$$
T = \text{Quotient}(\mathcal{C}, \sim)
$$

実際には

$$
T = \{ [g]_\sim \mid g \in G \}
$$

であり、各サブタスク \(T_k\) は

$$
T_k = \{ g \in G \mid \forall r \in \mathcal{K},\ roles(g).r = c_k(r) \}
$$

という形をしている（\(c_k\) はそのクラスの共通 role 値ベクトル）。

---

## 8. 意味論：何が保証されるのか？

同一サブタスク \(T_k\) に含まれる任意の 2 ゴール \(g_i, g_j\) について：

- \(roles(g_i).base = roles(g_j).base = base_k\)
- \(roles(g_i).hand\_type = roles(g_j).hand\_type = ht_k\)

である。Role Extraction の性質から、各ゴールごとに

$$
I \models reachable(base_k, g_i),\qquad I \models reachable(base_k, g_j)
$$

$$
I \models weld\_type(g_i, ht_k),\qquad I \models weld\_type(g_j, ht_k)
$$

が成り立つ。

したがって、\(T_k\) は

> 「同じ基地 base\_k と同じ工具種 ht\_k を共有するゴールの最大集合」

になっている。

これは直観的に

- 1 つの基地・1 つの工具構成で **まとめて実行しうるゴールの束**
- 物理的・機構的制約に関して **同種の設定を共有するゴール群**

を意味している。

---

## 9. SAT / 制約充足としての全体像

Role Extraction + Role-based Partition を SAT / CSP 的に見ると：

1. \(I\) を解釈としてもつ 1 階述語論理の世界で、
2. 各ゴール \(g\) について
   - Role 変数 \(\{r \mid r \in \mathcal{R}\}\) を導入
   - 抽出器により \(pred\) ベースの制約を課す
3. その制約の解が \(roles(g)\) であり、
4. その解ベクトルに対して同値関係 \(\sim\) を取り、商集合としてサブタスクを得ている

という構造になっている。

つまり：

- Step 8： **PDDL 初期状態からの制約 SAT 解読 (roles(g) の決定)**
- Step 9： **SAT 解ベクトルに対する等価類分解 (サブタスク T の構成)**

という 2 段構成になっており、config \(F = (\mathcal{R},\mathcal{E},\mathcal{K})\) を設計することで、 PDDL ドメインの物理・機構制約をタスク分解レベルに埋め込んでいると解釈できる。

---

## 10. まとめ（8・9 の本質）

| 項目                       | 本質的な意味                                       |
| ------------------------ | -------------------------------------------- |
| Role Extraction (Step 8) | PDDL 初期状態 \(I\) 上の **関係結合 + 射影 = SAT 解読**    |
| config \(F\)             | 「どの述語をどう結合するか」を宣言する **DomainRoleConfig**     |
| Role-based Partition (9) | Role ベクトルに対する **同値類分解（商集合）**                 |
| 制約を守る理由                  | 抽出器が **常に ****\(I\)**** を満たすタプルのみ** から値を取るため |
| 汎用性                      | 述語名とバインディング規則を変えるだけで、他ドメインにも移植可能             |

この一般化された枠組みの上に、溶接ドメイン（TSSW）では

- \(\mathcal{R} = \{base, hand\_type, hand, \lambda\}\)
- \(\mathcal{K} = \{base, hand\_type\}\)
- 抽出器 \(\mathcal{E}\) を `reachable`, `weld_type`, `hand_type`, `hand_rel` に対して定義

という具体インスタンスを載せている、という位置づけになる。

