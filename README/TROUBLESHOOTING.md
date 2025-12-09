# トラブルシューティング

## 発見された問題と解決策

### 2025/12/09 - 制約違反問題の解決

#### 🚨 問題1: max_subtasks制約違反

**症状**: 
```bash
設定ファイル: max_subtasks: 40
実際の生成結果: 93個のサブタスク (制約違反!)
```

**原因**: 
[`src/cli/generate_diverse_solutions.py`](../src/cli/generate_diverse_solutions.py)の多様解生成ロジックで、制約値を無制限に増加させていました：

```python
# 問題のあったコード (修正前)
elif i % 4 == 1:  # サブタスク数を増やす設定
    config['clustering']['max_subtasks'] = config['clustering']['max_subtasks'] + 10
```

これにより、50解生成時に最大 `40 + 10×12 = 160` まで増加する可能性がありました。

**解決策**: 
制約調整をベース設定の範囲内に制限：

```python
# 修正後のコード
base_max_subtasks = base_config['clustering']['max_subtasks']

if i % 4 == 0:  # サブタスク数を抑える設定
    config['clustering']['max_subtasks'] = max(base_max_subtasks - 10, int(base_max_subtasks * 0.7))
elif i % 4 == 1:  # サブタスク数を少し増やす設定
    config['clustering']['max_subtasks'] = min(base_max_subtasks + 5, int(base_max_subtasks * 1.2))
```

**修正結果**:
- ベース設定 `max_subtasks: 40`
- 調整範囲: `28-45` (70%-120%の範囲内)

#### 🚨 問題2: クラスタリング分析エラー

**症状**:
```bash
❌ Analysis failed: No features extracted. Check the results directory and file pattern.
```

**原因**: 
設定ファイルの `results_directory` が実際のファイル生成場所と一致していませんでした：
- 設定: `results_directory: "diverse_results"`
- 実際: `analysis_dataset/`

**解決策**: 
[`configs/clustering_analysis_config.yaml`](../configs/clustering_analysis_config.yaml)を修正：

```yaml
# 修正前
results_directory: "diverse_results"

# 修正後  
results_directory: "analysis_dataset"
```

**修正結果**:
```bash
✅ Extracted 16 features from 50 solutions
📊 Clustering Quality:
   Silhouette Score: 0.412
   Calinski-Harabasz Score: 41.122
🎉 Analysis completed successfully!
```

## 修正されたワークフローの確認

### 1. 適切な制約での多様解生成
```bash
# 修正されたワークフロー
python -m src.cli.generate_diverse_solutions \
  --config configs/default_config.yaml \
  --num-solutions 50 \
  --output-dir analysis_dataset

# 期待される結果: 全ての解がmax_subtasks制約内 (28-48の範囲)
```

### 2. 正常なクラスタリング分析
```bash
# 設定ファイル修正後
python -m src.analyze.cluster_solutions \
  --config configs/clustering_analysis_config.yaml

# 成功結果: 50解を5クラスターに分類、Silhouette Score: 0.412
```

## 予防策

### 1. 制約検証の追加

今後の改良で制約検証を追加することを推奨：

```python
def validate_constraints(result, expected_max_subtasks):
    """生成された解の制約を検証"""
    actual_count = len(result.get('subtasks', []))
    if actual_count > expected_max_subtasks:
        print(f"⚠️ Constraint violation: {actual_count} > {expected_max_subtasks}")
        return False
    return True
```

### 2. 設定ファイル整合性チェック

クラスタリング分析実行前の事前チェック：

```python
def check_directory_exists(config_path):
    """結果ディレクトリの存在確認"""
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    results_dir = config['results_directory']
    if not os.path.exists(results_dir):
        raise ValueError(f"Results directory not found: {results_dir}")
```

### 3. パラメータ命名規則の遵守

以下の統一規則を使用：

| 用途 | パラメータ名 | 例 |
|------|------------|-----|
| 出力ディレクトリ | `output_dir` | `--output-dir analysis_dataset` |
| 結果ディレクトリ | `results_directory` | `results_directory: "analysis_dataset"` |
| 制約値 | `max_subtasks`, `max_goals_per_subtask` | 一貫した命名 |

## テスト手順

### 制約違反の確認
```bash
# 生成された解の制約チェック
python -c "
import json, glob
for file in glob.glob('analysis_dataset/result_*.json'):
    with open(file) as f: data = json.load(f)
    count = len(data['subtasks'])
    if count > 48:  # 120%の上限
        print(f'{file}: {count} subtasks (violation)')
"
```

### クラスタリング分析の動作確認
```bash
# 分析の実行とログ確認
python -m src.analyze.cluster_solutions --config configs/clustering_analysis_config.yaml
ls -la clustering_analysis/  # 生成ファイルの確認
```

#### 🚨 問題3: 解生成の無限待機（NEW）

**症状**:
```bash
⚙️  Running solution 5/20: diverse_config_004.yaml
# ここで無限に待機してフリーズ
```

**原因**:
実行可能解が見つからない難しい設定で、プログラムが無限ループに陥る

**解決策**:
タイムアウト機能を追加：

1. **設定スキーマ更新** ([`src/config/schema.py`](../src/config/schema.py)):
```python
solution_timeout: int = 120  # 各解の生成タイムアウト（秒）
```

2. **設定ファイル更新** ([`configs/default_config.yaml`](../configs/default_config.yaml)):
```yaml
clustering:
  solution_timeout: 120  # 各解の生成タイムアウト（秒）
```

3. **実行時タイムアウト** ([`src/cli/generate_diverse_solutions.py`](../src/cli/generate_diverse_solutions.py)):
```python
result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
```

**修正結果**:
```bash
⚙️  Running solution 5/20: diverse_config_004.yaml (timeout: 120s)
⏰ Timeout (120s): Skipping config diverse_config_004.yaml
⚙️  Running solution 6/20: diverse_config_005.yaml (timeout: 120s)

📊 GENERATION SUMMARY:
   ✅ Successfully generated: 15/20 solutions
   ⏰ Timed out or failed: 5 solutions
   🕒 Timeout setting: 120 seconds per solution
```

#### 🚨 問題4: 制約不整合問題（NEW）

**症状**:
```bash
# 統合時にhand_type制約が不整合な組み合わせになる
"role_signature": {
  "base": "base_pos_1|base_pos_5",
  "hand_type": "0|1"  // 不正：実際のreachable制約を満たさない
}
```

**原因**:
多目的最適化統合（`multi_objective_merge_subtasks`）で制約チェックが不十分でした：
1. `hand_type`が異なるサブタスクの統合で"0|1"のような不整合な組み合わせ
2. `reachable`制約を満たさないbase組み合わせの統合
3. role_signature情報の不適切な再計算

**解決策**:
制約考慮型統合システム（`constraint_aware_merge_subtasks`）に変更：

1. **統合アルゴリズム変更** ([`src/planning/clustering.py`](../src/planning/clustering.py)):
```python
# 修正前
subtasks = multi_objective_merge_subtasks(subtasks, ...)

# 修正後
subtasks = constraint_aware_merge_subtasks(
    subtasks,
    task,  # 制約情報を含むタスクを渡す
    cfg_cluster.max_goals_per_subtask,
    cfg_cluster.max_subtasks,
    constraint_config
)
```

2. **制約設定の汎用化** ([`src/planning/clustering.py`](../src/planning/clustering.py)):
```python
# ドメイン汎化された制約設定
constraint_config = {
    'binary_constraints': cfg_cluster.constraint_binary_predicates or ['reachable'],
    'type_constraints': cfg_cluster.constraint_type_predicates or ['weld_type'],
    'goal_object_index': cfg_cluster.constraint_goal_object_index
}
```

3. **role_signature保持ロジック修正** ([`src/planning/constraint_aware_merge.py`](../src/planning/constraint_aware_merge.py)):
```python
# 元のrole_signatureを保持・統合（制約設定からの再計算を避ける）
role_signature = _merge_role_signatures_constraint_aware(
    subtask1.role_signature,
    subtask2.role_signature
)
```

**修正結果**:
```bash
# 制約考慮型統合後の正しい結果
Debug: After role-based partition: 169 subtasks
Debug: After constraint-aware merging: 30 subtasks (was 169)

# 適切な制約保持
"role_signature": {
  "base": "base_pos_20|base_pos_22",  // reachable制約を満たす組み合わせ
  "hand_type": "0"                    // 単一値で保持 ✅
}
```

**効果**:
- hand_type制約不整合の完全解決
- reachable制約を満たさない統合の防止
- 制約を厳密に遵守した効率的な統合（169→30サブタスク）
- ドメイン汎化による他のPDDLドメインへの適用可能性

#### 🚨 問題5: エラーログの冗長性（NEW）

**症状**:
```bash
⚠️  Warning: Failed to run config analysis_dataset/diverse_config_019.yaml
Error: Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  ... (長いstacktrace)
RuntimeError: Cannot satisfy max_subtasks=16 even after 50 retries.
```

**原因**:
制約違反やランタイムエラー時に完全なstacktraceが出力され、ログが見づらくなる

**解決策**:
エラータイプを判定して簡潔なメッセージに変更（[`src/cli/generate_diverse_solutions.py`](../src/cli/generate_diverse_solutions.py)）：

```python
# 修正前
if result.returncode != 0:
    print(f"⚠️  Warning: Failed to run config {config_file}")
    print(f"Error: {result.stderr}")

# 修正後
if result.returncode != 0:
    error_msg = result.stderr.strip()
    if "Cannot satisfy max_subtasks=" in error_msg:
        print(f"🚫 Constraint failure: Skipping config {os.path.basename(config_file)} (max_subtasks not satisfiable)")
    elif "RuntimeError" in error_msg:
        print(f"❌ Runtime error: Skipping config {os.path.basename(config_file)}")
    else:
        print(f"⚠️  Error: Skipping config {os.path.basename(config_file)}")
```

**修正結果**:
```bash
⚙️  Running solution 5/5: diverse_config_004.yaml (timeout: 120s)
🚫 Constraint failure: Skipping config diverse_config_004.yaml (max_subtasks not satisfiable)

📊 GENERATION SUMMARY:
   ✅ Successfully generated: 4/5 solutions
   ⏰ Timed out or failed: 1 solutions
```

**効果**:
- ログの可読性向上
- タイムアウトと同様の簡潔なエラー表示
- エラータイプの視覚的な区別（🚫, ❌, ⚠️）

## 関連ドキュメント

- [実行ガイド](README_usage_guide.md#統合ワークフロー例): 修正されたワークフロー
- [多様解生成詳細](README_diverse_solutions.md): パラメータ調整の詳細
- [クラスタリング分析詳細](README_clustering_analysis.md): 設定ファイルの説明