# PDDL Multi-Agent Task Decomposition & Allocation System

PDDL問題を複数エージェントによるサブタスクに分解・割当するシステムです。多様な最適化戦略と階層的クラスタリング分析機能を提供します。

## 🚀 クイックスタート

### 単一解の生成
```bash
# 基本実行
python -m src.cli.main --config configs/default_config.yaml --output solution.json
```

### 多様解の生成  
```bash
# 10個の多様な解を生成
python -m src.cli.generate_diverse_solutions \
  --config configs/default_config.yaml \
  --num-solutions 10 \
  --output-dir diverse_results
```

### 階層的クラスタリング分析
```bash
# 生成された解を分析
python -m src.analyze.cluster_solutions --config configs/clustering_analysis_config.yaml
```

## 📁 プロジェクト構成

```
pddl-generalized-allocator/
├── src/                          # ソースコード
│   ├── cli/                     # コマンドラインツール
│   │   ├── main.py             # 単一解生成
│   │   └── generate_diverse_solutions.py  # 多様解生成
│   ├── analyze/                 # 分析ツール
│   │   ├── cluster_solutions.py           # クラスタリング分析
│   │   ├── hierarchical_clustering.py     # 階層クラスタリング
│   │   └── feature_extractor.py          # 特徴量抽出
│   ├── config/                  # 設定管理
│   ├── pddl/                   # PDDLパーサー
│   ├── planning/               # プランニングエンジン
│   └── multiagent/             # マルチエージェント機能
├── configs/                     # 設定ファイル
│   ├── default_config.yaml     # デフォルト設定
│   ├── clustering_analysis_config.yaml  # クラスタリング設定
│   └── role_configs/           # 役割設定
├── pddl/                       # PDDLドメイン・問題ファイル
├── README/                     # ドキュメント
│   ├── README_usage_guide.md   # 📖 実行ガイド（必読）
│   ├── README_diverse_solutions.md      # 多様解生成詳細
│   └── README_clustering_analysis.md    # クラスタリング分析詳細
└── diverse_results/            # 生成結果（例）
└── clustering_analysis/        # 分析結果（例）
```

## 🎯 主要機能

### 1. 単一解生成 ([詳細](README/README_usage_guide.md#1-単一解の生成))
- PDDLドメイン・問題を読み込み
- 制約考慮型統合によるマルチエージェント対応サブタスクへの分解
- エージェントへの最適割当
- JSON形式での結果出力

### 2. 多様解生成 ([詳細](README/README_usage_guide.md#2-多様解の生成))
- 4つの最適化戦略（minimize_subtasks、balanced、distribute_goals、auto）
- seedベースでの多様性生成
- パラメータの自動調整
- 多様性メトリクスの自動分析

### 3. 階層的クラスタリング分析 ([詳細](README/README_usage_guide.md#3-階層的クラスタリング分析))
- 16種類の汎用的特徴量抽出
- Ward法による階層クラスタリング
- 自動クラスター数決定（silhouette、elbow、dendrogram_gap法）
- デンドログラム・散布図・重要度の可視化

### 4. 制約考慮型統合システム
- **制約遵守**: `reachable`制約と`weld_type`制約を厳密にチェック
- **role_signature保持**: 統合時に元の制約情報を適切に保持・統合
- **ドメイン汎化**: 制約述語を設定可能にしたドメイン依存性の排除
- **品質保証**: 制約を満たさないサブタスクペアの統合を防止

## 📖 ドキュメント

| ドキュメント | 内容 | 対象 |
|-------------|------|------|
| **[📖 実行ガイド](README/README_usage_guide.md)** | **全機能の統合実行方法** | **全ユーザー必読** |
| [多様解生成詳細](README/README_diverse_solutions.md) | 多様解生成の詳細仕様 | 多様解分析ユーザー |
| [クラスタリング分析詳細](README/README_clustering_analysis.md) | 階層クラスタリングの詳細 | 分析ユーザー |

## ⚙️ 設定ファイル

### パラメータ統一規則
| 用途 | パラメータ名 | 例 |
|------|------------|-----|
| ファイルパス | `config`, `output`, `output_dir` | `--config configs/default.yaml` |
| 数値設定 | `num_solutions`, `random_seed`, `max_subtasks` | `--num-solutions 20` |
| 手法選択 | `strategy`, `method`, `normalization_method` | `strategy: "auto"` |
| フラグ | `use_landmarks`, `normalize_features` | `use_landmarks: true` |

### 主要設定ファイル
- `configs/default_config.yaml`: 単一・多様解生成用
- `configs/clustering_analysis_config.yaml`: クラスタリング分析用
- `configs/role_configs/example_roles.json`: 役割定義

## 🔧 システム要件

### 依存ライブラリ
```bash
pip install numpy pandas scikit-learn matplotlib seaborn scipy pyyaml
```

### Python バージョン
- Python 3.8+ 推奨

## 💡 使用例

### 完全分析パイプライン
```bash
# Step 1: 多様解生成（20個）
python -m src.cli.generate_diverse_solutions \
  --config configs/default_config.yaml \
  --num-solutions 20 \
  --output-dir analysis_dataset

# Step 2: クラスタリング分析
python -m src.analyze.cluster_solutions \
  --config configs/clustering_analysis_config.yaml

# Step 3: 結果確認
ls analysis_dataset/          # 20個の解とメタデータ
ls clustering_analysis/       # クラスタリング結果と可視化
```

### 小規模テスト
```bash
# Step 1: 単一解テスト
python -m src.cli.main --config configs/default_config.yaml --output test_solution.json

# Step 2: 小規模多様解
python -m src.cli.generate_diverse_solutions \
  --config configs/default_config.yaml \
  --num-solutions 5 \
  --output-dir test_diverse

# Step 3: 分析テスト
python -m src.analyze.cluster_solutions --config configs/clustering_analysis_config.yaml
```

## 🎨 出力例

### 多様解生成結果
```
diverse_results/
├── result_000.json ~ result_019.json    # 20個の解
├── diverse_config_000.yaml ~ 019.yaml   # 使用設定
├── diversity_analysis.json              # 詳細データ
└── diversity_summary.txt                # 要約レポート
```

### クラスタリング分析結果  
```
clustering_analysis/
├── solution_clustering_features.csv          # 特徴量データ
├── solution_clustering_cluster_assignments.csv # クラスター結果
├── solution_clustering_summary.txt           # 分析レポート
├── solution_clustering_dendrogram.png        # デンドログラム
├── solution_clustering_scatter.png           # PCA散布図
└── solution_clustering_feature_importance.png # 重要度
```

## 🚨 トラブルシューティング

### よくあるエラー
1. **設定ファイルが見つからない**: パスを確認してください
2. **結果ディレクトリが存在しない**: 多様解生成を先に実行してください  
3. **メモリ不足**: 解の数や特徴量を制限してください
4. **依存ライブラリ不足**: `pip install` で必要ライブラリをインストールしてください

詳細は [📖 実行ガイド](README/README_usage_guide.md) のトラブルシューティングセクションを参照してください。

## 📄 ライセンス

このプロジェクトはMITライセンスのもとで公開されています。

## 🤝 貢献

バグレポート、機能提案、プルリクエストを歓迎します。

---

**📖 詳細な実行方法は [実行ガイド](README/README_usage_guide.md) をご覧ください。**