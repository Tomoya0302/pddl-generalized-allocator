"""
階層的クラスタリング分析の設定スキーマ
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass
class FeatureExtractionConfig:
    """特徴量抽出の設定"""
    # 基本的な統計特徴量
    use_subtask_count: bool = True
    use_goal_variance: bool = True
    use_goal_mean: bool = True
    use_goal_min_max: bool = True
    use_agent_balance: bool = True
    
    # 汎用的な構造特徴量
    use_structural_features: bool = True
    role_config_file: Optional[str] = None
    structural_feature_types: List[str] = None  # ["role_diversity", "role_complexity", etc.]
    
    # 正規化設定
    normalize_features: bool = True
    normalization_method: str = "standard"  # "standard", "minmax", "robust"


@dataclass
class ClusteringConfig:
    """階層的クラスタリングの設定"""
    method: str = "ward"  # "ward", "complete", "average", "single"
    metric: str = "euclidean"  # "euclidean", "manhattan", "cosine", etc.
    num_clusters: Optional[int] = None  # Noneの場合は自動決定
    auto_cluster_method: str = "silhouette"  # "silhouette", "elbow", "dendrogram_gap"
    max_clusters: int = 10
    min_clusters: int = 2


@dataclass
class VisualizationConfig:
    """可視化の設定"""
    create_dendrogram: bool = True
    create_scatter_plots: bool = True
    create_feature_importance: bool = True
    create_cluster_summary: bool = True
    
    # 図のサイズとスタイル
    figure_size: tuple = (12, 8)
    dpi: int = 300
    style: str = "seaborn-v0_8"
    color_palette: str = "husl"


@dataclass
class OutputConfig:
    """出力設定"""
    output_dir: str = "clustering_analysis"
    save_features_csv: bool = True
    save_cluster_assignments: bool = True
    save_plots: bool = True
    save_summary_report: bool = True
    
    # ファイル名のプレフィックス
    prefix: str = "solution_clustering"


@dataclass
class ClusteringAnalysisConfig:
    """階層的クラスタリング分析の全体設定"""
    feature_extraction: FeatureExtractionConfig
    clustering: ClusteringConfig
    visualization: VisualizationConfig
    output: OutputConfig
    
    # データソース
    results_directory: str = "diverse_results"
    result_file_pattern: str = "result_*.json"


def load_clustering_analysis_config(config_file: str) -> ClusteringAnalysisConfig:
    """設定ファイルから階層的クラスタリング設定を読み込み"""
    import yaml
    
    with open(config_file, 'r') as f:
        config_dict = yaml.safe_load(f)
    
    # デフォルト値でDataClassを初期化
    feature_config = FeatureExtractionConfig()
    clustering_config = ClusteringConfig()
    viz_config = VisualizationConfig()
    output_config = OutputConfig()
    
    # 設定値で上書き
    if 'feature_extraction' in config_dict:
        for key, value in config_dict['feature_extraction'].items():
            if hasattr(feature_config, key):
                setattr(feature_config, key, value)
    
    if 'clustering' in config_dict:
        for key, value in config_dict['clustering'].items():
            if hasattr(clustering_config, key):
                setattr(clustering_config, key, value)
    
    if 'visualization' in config_dict:
        for key, value in config_dict['visualization'].items():
            if hasattr(viz_config, key):
                setattr(viz_config, key, value)
    
    if 'output' in config_dict:
        for key, value in config_dict['output'].items():
            if hasattr(output_config, key):
                setattr(output_config, key, value)
    
    # メイン設定
    main_config = ClusteringAnalysisConfig(
        feature_extraction=feature_config,
        clustering=clustering_config,
        visualization=viz_config,
        output=output_config
    )
    
    # トップレベル設定で上書き
    for key, value in config_dict.items():
        if hasattr(main_config, key) and key not in ['feature_extraction', 'clustering', 'visualization', 'output']:
            setattr(main_config, key, value)
    
    return main_config