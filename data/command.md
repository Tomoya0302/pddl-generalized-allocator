python fast-downward.py ../domains/codmap15-fd/blocksworld/domain/domain.pddl ../domains/codmap15-fd/blocksworld/problems/probBLOCKS-9-0.pddl --search "lazy_greedy([ff()], preferred=[ff()])"
python fast-downward.py ../domains/codmap15-fd/depot/domain/domain.pddl ../domains/codmap15-fd/depot/problems/pfile1.pddl --search "lazy_greedy([ff()], preferred=[ff()])"
python fast-downward.py ../domains/codmap15-fd/driverlog/domain/domain.pddl ../domains/codmap15-fd/driverlog/problems/pfile1.pddl --search "lazy_greedy([ff()], preferred=[ff()])"
python fast-downward.py ../domains/codmap15-fd/elevators08/domain/domain.pddl ../domains/codmap15-fd/elevators08/problems/p01.pddl --search "lazy_greedy([ff()], preferred=[ff()])"
python fast-downward.py ../domains/codmap15-fd/logistics00/domain/domain.pddl ../domains/codmap15-fd/logistics00/problems/probLOGISTICS-4-0.pddl --search "lazy_greedy([ff()], preferred=[ff()])"
python fast-downward.py ../domains/codmap15-fd/rovers/domain/domain.pddl ../domains/codmap15-fd/rovers/problems/p10.pddl --search "lazy_greedy([ff()], preferred=[ff()])"
python fast-downward.py ../domains/codmap15-fd/satellites/domain/domain.pddl ../domains/codmap15-fd/satellites/problems/p05-pfile5.pddl --search "lazy_greedy([ff()], preferred=[ff()])"
python fast-downward.py ../domains/codmap15-fd/sokoban/domain/domain.pddl ../domains/codmap15-fd/sokoban/problems/p01.pddl --search "lazy_greedy([ff()], preferred=[ff()])"
python fast-downward.py ../domains/codmap15-fd/taxi/domain/domain.pddl ../domains/codmap15-fd/taxi/problems/p01.pddl --search "lazy_greedy([ff()], preferred=[ff()])"
python fast-downward.py ../domains/codmap15-fd/wireless/domain/domain.pddl ../domains/codmap15-fd/wireless/problems/p01.pddl --search "lazy_greedy([ff()], preferred=[ff()])"
python fast-downward.py ../domains/codmap15-fd/woodworking08/domain/domain.pddl ../domains/codmap15-fd/woodworking08/problems/p01.pddl --search "lazy_greedy([ff()], preferred=[ff()])"
python fast-downward.py ../domains/codmap15-fd/zenotravel/domain/domain.pddl ../domains/codmap15-fd/zenotravel/problems/pfile3.pddl --search "lazy_greedy([ff()], preferred=[ff()])"


python -m pddl_generalized_allocator.cli.main --domain domains/codmap15-fd/blocksworld/domain/domain.pddl --problem domains/codmap15-fd/blocksworld/problems/probBLOCKS-9-0.pddl --num-solutions 5 --seed 123 --output data/assignments.json
python -m pddl_generalized_allocator.cli.main --domain domains/codmap15-fd/depot/domain/domain.pddl --problem domains/codmap15-fd/depot/problems/pfile1.pddl --num-solutions 5 --seed 123 --output data/assignments.json
python -m pddl_generalized_allocator.cli.main --domain domains/codmap15-fd/driverlog/domain/domain.pddl --problem domains/codmap15-fd/driverlog/problems/pfile1.pddl --num-solutions 5 --seed 123 --output data/assignments.json
python -m pddl_generalized_allocator.cli.main --domain domains/codmap15-fd/elevators08/domain/domain.pddl --problem domains/codmap15-fd/elevators08/problems/p01.pddl --num-solutions 5 --seed 123 --output data/assignments.json
python -m pddl_generalized_allocator.cli.main --domain domains/codmap15-fd/logistics00/domain/domain.pddl --problem domains/codmap15-fd/logistics00/problems/probLOGISTICS-4-0.pddl --num-solutions 5 --seed 123 --output data/assignments.json
python -m pddl_generalized_allocator.cli.main --domain domains/codmap15-fd/rovers/domain/domain.pddl --problem domains/codmap15-fd/rovers/problems/p10.pddl --num-solutions 5 --seed 123 --output data/assignments.json
python -m pddl_generalized_allocator.cli.main --domain domains/codmap15-fd/taxi/domain/domain.pddl --problem domains/codmap15-fd/taxi/problems/p01.pddl --num-solutions 5 --seed 123 --output data/assignments.json
python -m pddl_generalized_allocator.cli.main --domain domains/codmap15-fd/wireless/domain/domain.pddl --problem domains/codmap15-fd/wireless/problems/p01.pddl --num-solutions 5 --seed 123 --output data/assignments.json
python -m pddl_generalized_allocator.cli.main --domain domains/codmap15-fd/woodworking08/domain/domain.pddl --problem domains/codmap15-fd/woodworking08/problems/p01.pddl --num-solutions 5 --seed 123 --output data/assignments.json
python -m pddl_generalized_allocator.cli.main --domain domains/codmap15-fd/zenotravel/domain/domain.pddl --problem domains/codmap15-fd/zenotravel/problems/pfile3.pddl --num-solutions 5 --seed 123 --output data/assignments.json


---

# 🗂️ **CoDMAP15 各ドメインの内容説明（要点まとめ）**

---

## **1. blocksworld（積み木ワールド）**

積み木を積み上げたりテーブルに置いたりするドメイン。

### 特色

* ブロックを持ち上げ・積む・下ろす
* 手が空いているか（handempty）、ブロックがクリアか（clear）で操作制約
* 単純だが、再帰的依存（上のブロックをどけないと下に触れない）

### マルチエージェント版の特徴

* 複数のロボットアームが同じ作業場で衝突なく作業する必要がある（元の CoDMAP）。

---

## **2. depot（倉庫＋配送）**

倉庫で物資を積み込み、ポストオフィスに配送するドメイン。

### 特色

* クレーンで荷物をトラックに載せる
* トラックで移動し、荷物を降ろす
* 地点間移動（道路ネットワーク）
* クレーンは倉庫に固定（移動できない）

### マルチエージェントの意味

* 複数のトラック・クレーンが協調して配送を行う。

---

## **3. driverlog（物流＋ドライバー移動）**

運転手（driver）が車輌を運転し、荷物を配送する。

### 特色

* ドライバーとトラックが別の存在
* ドライバーは徒歩でも移動できる
* 車はドライバーが乗らないと動けない
* 荷物の積み降ろし、ネットワーク移動

### マルチエージェントの意味

* 複数ドライバーが動くことで協調的に配送。

---

## **4. elevators08（ビルのエレベータ制御）**

エレベーターで乗客を目的階へ運ぶ。

### 特色

* 複数のエレベータと乗客
* 各階を上下方向に移動
* エレベータの積載制限（IPC2008 版）

### マルチエージェントの意味

* 各エレベータがエージェント、乗客を協調して搬送。

---

## **5. logistics00（航空＋車両を使った配送）**

都市間は飛行機、都市内はトラックで荷物配送。

### 特色

* 飛行機は空港間
* トラックは都市内道路上
* 荷物の積み降ろし、移動

### マルチエージェント版

* 複数トラック・複数飛行機が協調。

---

## **6. rovers（火星探査ローバー）**

探査ローバーが指定地点で観測（撮影・サンプリング）を行う。

### 特色

* ローバーの移動（地形の連結）
* カメラでの撮影、サンプル採集
* サンプルを基地に持ち帰る
* エネルギーや機器の条件もある（簡略版では除外）

### マルチエージェント版

* 複数ローバーが協力して観測とサンプル収集を行う。

---

## **7. satellites（人工衛星による観測）**

人工衛星がセンサーを向けて観測画像を撮る。

### 特色

* 向きの変更（方向転換）
* センサーの切替
* 各観測ポイントで写真撮影
* メモリの容量制約 → ダウンリンクして解放

### マルチエージェント版

* 複数衛星が軌道上で効率よく観測分担。

---

## **8. sokoban（倉庫番）**

作業者が箱を押してゴールに運ぶドメイン。

### 特色

* 押すだけ（引けない） → デッドロックが発生しやすい
* グリッド上移動、壁による拘束
* 1箱でも詰むことがある NP-hard 問題

### マルチエージェント版

* 複数作業員が箱を押して協力する…が衝突回避が難しい。

---

## **9. taxi（タクシー乗客輸送）**

タクシーが乗客を拾い目的地へ運ぶ。

### 特色

* グリッド地図上での位置移動
* pick-up / drop-off
* 複数客、複数タクシー

### マルチエージェント版

* 複数タクシーの協調 → 競合・重複を避ける計画が必要。

---

## **10. wireless（無線ネットワークのリレー）**

無線ノードがパケットを送信して目的のノードへ届ける。

### 特色

* 中継ノード（ルーター）を使ったパケット伝送
* 干渉（interference）を避けて送信
* 一度に複数送信できない制約

### マルチエージェント版

* 各ノードがエージェントとして影響しあう。

---

## **11. woodworking08（木工加工）**

木材ワークピースを複数工程で加工する。

### 特色

* 切断、穴あけ、研磨などの工程
* 各機械は特定工程のみ可能
* 工程依存（順序制約）

### マルチエージェント版

* 複数の機械（加工ステーション）が協調して製品を作る。

---

## **12. zenotravel（燃料制約付き航空移動）**

飛行機で人々を目的地へ運ぶ。燃料消費があるのが特徴。

### 特色

* 都市間飛行
* 燃料を消費、補給する
* 人員搭乗・降ろし
* 最適燃費ルート探索が必要

### マルチエージェント版

* 複数航空機が協調して輸送。

---

# 🧩 まとめ：CoDMAP15 の本質

CoDMAP15 は **「IPC 古典ドメインをマルチエージェント化した標準ベンチマークセット」**。

* エージェント間の **干渉／競合**
* それぞれの **プライバシー（本来）**
* 協調による **計画の非中央集権性**