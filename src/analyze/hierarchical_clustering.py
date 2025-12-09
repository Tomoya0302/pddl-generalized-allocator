"""
階層的クラスタリング分析モジュール
"""
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import silhouette_score, calinski_harabasz_score
from scipy.cluster.hierarchy import dendrogram, linkage, fcluster
from scipy.spatial.distance import pdist
import matplotlib.pyplot as plt
import seaborn as sns
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
import json

from .feature_extractor import extract_features_from_directory
from ..config.clustering_analysis_schema import ClusteringAnalysisConfig


class HierarchicalClusteringAnalyzer:
    """階層的クラスタリング分析クラス"""
    
    def __init__(self, config: ClusteringAnalysisConfig):
        self.config = config
        self.features = None
        self.feature_names = None
        self.solution_names = None
        self.normalized_features = None
        self.scaler = None
        self.cluster_labels = None
        self.linkage_matrix = None
        
        # 出力ディレクトリを作成
        self.output_dir = Path(config.output.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def load_and_extract_features(self):
        """特徴量の読み込みと抽出"""
        print("🔍 Extracting features from solutions...")
        
        role_config_path = self.config.feature_extraction.role_config_file
        
        self.features, self.feature_names, self.solution_names = extract_features_from_directory(
            self.config.results_directory,
            self.config,
            role_config_path
        )
        
        if len(self.features) == 0:
            raise ValueError("No features extracted. Check the results directory and file pattern.")
        
        print(f"✅ Extracted {len(self.feature_names)} features from {len(self.solution_names)} solutions")
        print(f"📊 Features: {', '.join(self.feature_names[:5])}{'...' if len(self.feature_names) > 5 else ''}")
        
        # 特徴量をCSVで保存
        if self.config.output.save_features_csv:
            features_df = pd.DataFrame(
                self.features,
                index=self.solution_names,
                columns=self.feature_names
            )
            features_csv_path = self.output_dir / f"{self.config.output.prefix}_features.csv"
            features_df.to_csv(features_csv_path)
            print(f"💾 Features saved to {features_csv_path}")
    
    def normalize_features(self):
        """特徴量の正規化"""
        if not self.config.feature_extraction.normalize_features:
            self.normalized_features = self.features
            return
        
        print("📏 Normalizing features...")
        
        method = self.config.feature_extraction.normalization_method
        if method == "standard":
            self.scaler = StandardScaler()
        elif method == "minmax":
            self.scaler = MinMaxScaler()
        elif method == "robust":
            self.scaler = RobustScaler()
        else:
            raise ValueError(f"Unknown normalization method: {method}")
        
        self.normalized_features = self.scaler.fit_transform(self.features)
        print(f"✅ Features normalized using {method} scaling")
    
    def perform_clustering(self):
        """階層的クラスタリングの実行"""
        print("🔗 Performing hierarchical clustering...")
        
        # Linkage matrix計算
        method = self.config.clustering.method
        metric = self.config.clustering.metric
        
        self.linkage_matrix = linkage(
            self.normalized_features,
            method=method,
            metric=metric
        )
        
        # クラスター数の決定
        if self.config.clustering.num_clusters:
            n_clusters = self.config.clustering.num_clusters
        else:
            n_clusters = self._determine_optimal_clusters()
        
        print(f"📈 Using {n_clusters} clusters")
        
        # クラスター割り当て
        self.cluster_labels = fcluster(
            self.linkage_matrix,
            n_clusters,
            criterion='maxclust'
        )
        
        # クラスター品質評価
        self._evaluate_clustering()
        
        print("✅ Hierarchical clustering completed")
    
    def _determine_optimal_clusters(self) -> int:
        """最適なクラスター数を自動決定"""
        method = self.config.clustering.auto_cluster_method
        max_k = min(self.config.clustering.max_clusters, len(self.solution_names) - 1)
        min_k = self.config.clustering.min_clusters
        
        print(f"🎯 Determining optimal number of clusters using {method}...")
        
        if method == "silhouette":
            best_k = self._find_best_k_silhouette(min_k, max_k)
        elif method == "elbow":
            best_k = self._find_best_k_elbow(min_k, max_k)
        elif method == "dendrogram_gap":
            best_k = self._find_best_k_dendrogram_gap(min_k, max_k)
        else:
            print(f"⚠️  Unknown method {method}, using silhouette")
            best_k = self._find_best_k_silhouette(min_k, max_k)
        
        return best_k
    
    def _find_best_k_silhouette(self, min_k: int, max_k: int) -> int:
        """シルエット係数による最適クラスター数決定"""
        best_score = -1
        best_k = min_k
        
        for k in range(min_k, max_k + 1):
            labels = fcluster(self.linkage_matrix, k, criterion='maxclust')
            if len(set(labels)) > 1:  # 最低2つのクラスターが必要
                score = silhouette_score(self.normalized_features, labels)
                if score > best_score:
                    best_score = score
                    best_k = k
        
        print(f"🎯 Best silhouette score: {best_score:.3f} with {best_k} clusters")
        return best_k
    
    def _find_best_k_elbow(self, min_k: int, max_k: int) -> int:
        """エルボー法による最適クラスター数決定"""
        inertias = []
        
        for k in range(min_k, max_k + 1):
            clustering = AgglomerativeClustering(n_clusters=k)
            labels = clustering.fit_predict(self.normalized_features)
            
            # クラスター内平均距離を計算
            inertia = 0
            for cluster_id in set(labels):
                cluster_points = self.normalized_features[labels == cluster_id]
                if len(cluster_points) > 1:
                    cluster_center = cluster_points.mean(axis=0)
                    distances = np.sum((cluster_points - cluster_center) ** 2, axis=1)
                    inertia += distances.sum()
            
            inertias.append(inertia)
        
        # エルボーポイントを見つける（簡易版）
        diffs = np.diff(inertias)
        elbow_k = min_k + np.argmax(diffs[:-1] - diffs[1:]) + 1
        
        print(f"🎯 Elbow method suggests {elbow_k} clusters")
        return elbow_k
    
    def _find_best_k_dendrogram_gap(self, min_k: int, max_k: int) -> int:
        """デンドログラムのギャップによる最適クラスター数決定"""
        # デンドログラムの高さの差を計算
        heights = self.linkage_matrix[:, 2]
        height_diffs = np.diff(heights[::-1])  # 逆順（上から下へ）
        
        # 最大のギャップを見つける
        max_gap_idx = np.argmax(height_diffs[:max_k-min_k])
        optimal_k = max_k - max_gap_idx
        
        # 範囲内に収める
        optimal_k = max(min_k, min(optimal_k, max_k))
        
        print(f"🎯 Dendrogram gap suggests {optimal_k} clusters")
        return optimal_k
    
    def _evaluate_clustering(self):
        """クラスタリング結果の評価"""
        if len(set(self.cluster_labels)) > 1:
            silhouette = silhouette_score(self.normalized_features, self.cluster_labels)
            calinski_harabasz = calinski_harabasz_score(self.normalized_features, self.cluster_labels)
            
            print(f"📊 Clustering Quality:")
            print(f"   Silhouette Score: {silhouette:.3f}")
            print(f"   Calinski-Harabasz Score: {calinski_harabasz:.3f}")
    
    def create_visualizations(self):
        """可視化の作成"""
        if not self.config.visualization.create_dendrogram and \
           not self.config.visualization.create_scatter_plots and \
           not self.config.visualization.create_feature_importance:
            return
        
        print("📊 Creating visualizations...")
        
        # スタイル設定
        plt.style.use(self.config.visualization.style)
        colors = sns.color_palette(self.config.visualization.color_palette, 
                                 len(set(self.cluster_labels)))
        
        # デンドログラム
        if self.config.visualization.create_dendrogram:
            self._create_dendrogram()
        
        # 散布図
        if self.config.visualization.create_scatter_plots:
            self._create_scatter_plots(colors)
        
        # 特徴量重要度
        if self.config.visualization.create_feature_importance:
            self._create_feature_importance_plot()
        
        print("✅ Visualizations created")
    
    def _create_dendrogram(self):
        """デンドログラムの作成"""
        plt.figure(figsize=self.config.visualization.figure_size)
        
        dendrogram(
            self.linkage_matrix,
            labels=self.solution_names,
            orientation='top',
            distance_sort='descending',
            show_leaf_counts=True
        )
        
        plt.title('Hierarchical Clustering Dendrogram')
        plt.xlabel('Solution')
        plt.ylabel('Distance')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        if self.config.output.save_plots:
            dendrogram_path = self.output_dir / f"{self.config.output.prefix}_dendrogram.png"
            plt.savefig(dendrogram_path, dpi=self.config.visualization.dpi, bbox_inches='tight')
        
        # plt.show()
    
    def save_results(self):
        """結果の保存"""
        print("💾 Saving clustering results...")
        
        # クラスター割り当ての保存
        if self.config.output.save_cluster_assignments:
            cluster_assignments = pd.DataFrame({
                'solution': self.solution_names,
                'cluster': self.cluster_labels
            })
            assignments_path = self.output_dir / f"{self.config.output.prefix}_cluster_assignments.csv"
            cluster_assignments.to_csv(assignments_path, index=False)
        
        # 要約レポートの作成
        if self.config.output.save_summary_report:
            self._create_summary_report()
        
        print(f"✅ Results saved to {self.output_dir}")
    
    def _create_summary_report(self):
        """要約レポートの作成"""
        report_path = self.output_dir / f"{self.config.output.prefix}_summary.txt"
        
        with open(report_path, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("HIERARCHICAL CLUSTERING ANALYSIS REPORT\n")
            f.write("=" * 80 + "\n\n")
            
            # 基本情報
            f.write(f"Total Solutions Analyzed: {len(self.solution_names)}\n")
            f.write(f"Number of Features: {len(self.feature_names)}\n")
            f.write(f"Number of Clusters: {len(set(self.cluster_labels))}\n")
            f.write(f"Clustering Method: {self.config.clustering.method}\n")
            f.write(f"Distance Metric: {self.config.clustering.metric}\n\n")
            
            # クラスター情報
            f.write("CLUSTER SUMMARY:\n")
            f.write("-" * 50 + "\n")
            
            from collections import Counter
            cluster_counts = Counter(self.cluster_labels)
            
            for cluster_id, count in sorted(cluster_counts.items()):
                f.write(f"Cluster {cluster_id}: {count} solutions\n")
                
                # このクラスターに属する解をリスト
                cluster_solutions = [name for name, label in zip(self.solution_names, self.cluster_labels)
                                   if label == cluster_id]
                f.write(f"  Solutions: {', '.join(cluster_solutions)}\n")
                
                # このクラスターの特徴量平均
                cluster_mask = self.cluster_labels == cluster_id
                cluster_features = self.normalized_features[cluster_mask].mean(axis=0)
                
                # 上位3つの特徴量
                top_feature_indices = np.argsort(np.abs(cluster_features))[-3:]
                f.write(f"  Top features: ")
                for idx in reversed(top_feature_indices):
                    feature_name = self.feature_names[idx]
                    feature_value = cluster_features[idx]
                    f.write(f"{feature_name}({feature_value:.2f}) ")
                f.write("\n\n")
            
            # 特徴量情報
            f.write("FEATURE SUMMARY:\n")
            f.write("-" * 50 + "\n")
            f.write(f"Features used: {', '.join(self.feature_names)}\n\n")
            
            # 設定情報
            f.write("CONFIGURATION:\n")
            f.write("-" * 50 + "\n")
            f.write(f"Results Directory: {self.config.results_directory}\n")
            f.write(f"Normalization: {self.config.feature_extraction.normalization_method}\n")
            f.write(f"Structural Features: {self.config.feature_extraction.use_structural_features}\n")
    
    def analyze(self):
        """完全な分析パイプラインを実行"""
        try:
            # ステップ1: 特徴量抽出
            self.load_and_extract_features()
            
            # ステップ2: 正規化
            self.normalize_features()
            
            # ステップ3: クラスタリング
            self.perform_clustering()
            
            # ステップ4: 可視化
            self.create_visualizations()
            
            # ステップ5: 結果保存
            self.save_results()
            
            print("🎉 Hierarchical clustering analysis completed successfully!")
            
            return {
                'cluster_labels': self.cluster_labels,
                'solution_names': self.solution_names,
                'feature_names': self.feature_names,
                'n_clusters': len(set(self.cluster_labels))
            }
            
        except Exception as e:
            print(f"❌ Analysis failed: {e}")
            raise


    def _create_scatter_plots(self, colors):
        """散布図の作成（PCA使用）"""
        if self.normalized_features.shape[1] < 2:
            print("⚠️  Not enough features for scatter plot")
            return
        
        from sklearn.decomposition import PCA
        
        # PCAで2次元に削減
        pca = PCA(n_components=2)
        features_2d = pca.fit_transform(self.normalized_features)
        
        plt.figure(figsize=self.config.visualization.figure_size)
        
        for i, cluster_id in enumerate(set(self.cluster_labels)):
            mask = self.cluster_labels == cluster_id
            plt.scatter(
                features_2d[mask, 0],
                features_2d[mask, 1],
                c=[colors[i]],
                label=f'Cluster {cluster_id}',
                s=100,
                alpha=0.7
            )
            
            # 解の名前をラベルとして表示
            for j, (x, y) in enumerate(features_2d[mask]):
                solution_name = np.array(self.solution_names)[mask][j]
                plt.annotate(solution_name, (x, y), xytext=(5, 5),
                           textcoords='offset points', fontsize=8, alpha=0.8)
        
        plt.xlabel(f'PC1 ({pca.explained_variance_ratio_[0]:.1%} variance)')
        plt.ylabel(f'PC2 ({pca.explained_variance_ratio_[1]:.1%} variance)')
        plt.title('Solution Clusters (PCA projection)')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        if self.config.output.save_plots:
            scatter_path = self.output_dir / f"{self.config.output.prefix}_scatter.png"
            plt.savefig(scatter_path, dpi=self.config.visualization.dpi, bbox_inches='tight')
        
        # plt.show()
    
    def _create_feature_importance_plot(self):
        """特徴量重要度プロットの作成"""
        if len(set(self.cluster_labels)) <= 1:
            print("⚠️  Cannot compute feature importance with only one cluster")
            return
        
        # 各特徴量のクラスター間分散を計算
        feature_importance = []
        
        for i, feature_name in enumerate(self.feature_names):
            feature_values = self.normalized_features[:, i]
            cluster_means = []
            
            for cluster_id in set(self.cluster_labels):
                cluster_mask = self.cluster_labels == cluster_id
                cluster_mean = feature_values[cluster_mask].mean()
                cluster_means.append(cluster_mean)
            
            # クラスター間の分散を重要度とする
            importance = np.var(cluster_means)
            feature_importance.append((feature_name, importance))
        
        # 重要度でソート
        feature_importance.sort(key=lambda x: x[1], reverse=True)
        
        # 上位10個を表示
        top_features = feature_importance[:10]
        
        plt.figure(figsize=(10, 6))
        feature_names_plot = [f[0] for f in top_features]
        importances = [f[1] for f in top_features]
        
        bars = plt.barh(range(len(top_features)), importances)
        plt.yticks(range(len(top_features)), feature_names_plot)
        plt.xlabel('Feature Importance (Inter-cluster variance)')
        plt.title('Top 10 Most Important Features for Clustering')
        plt.gca().invert_yaxis()
        
        # 色付け
        colors_grad = plt.cm.viridis(np.linspace(0, 1, len(top_features)))
        for bar, color in zip(bars, colors_grad):
            bar.set_color(color)
        
        plt.tight_layout()
        
        if self.config.output.save_plots:
            importance_path = self.output_dir / f"{self.config.output.prefix}_feature_importance.png"
            plt.savefig(importance_path, dpi=self.config.visualization.dpi, bbox_inches='tight')
        
        # plt.show()


def run_clustering_analysis(config_path: str):
    """設定ファイルから階層的クラスタリング分析を実行"""
    from ..config.clustering_analysis_schema import load_clustering_analysis_config
    
    config = load_clustering_analysis_config(config_path)
    analyzer = HierarchicalClusteringAnalyzer(config)
    
    return analyzer.analyze()
        