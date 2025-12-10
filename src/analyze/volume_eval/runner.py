import yaml
import pandas as pd
import os
import matplotlib.pyplot as plt
from .metrics import compute_logdet, compute_convex_hull_volume
from .utils import normalize_features
from sklearn.decomposition import PCA
from scipy.spatial import ConvexHull
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

def run_volume_analysis(config_path: str):
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    df = pd.read_csv(config['input_csv'])
    features = config['features']
    method_names = config.get('metrics', ['logdet'])
    norm_type = config.get('normalization', 'minmax')
    output_dir = config.get('output_dir', './volume_output')
    os.makedirs(output_dir, exist_ok=True)

    X_raw = df[features].values
    X_scaled = normalize_features(X_raw, norm_type)

    results = {}
    if 'logdet' in method_names:
        results['logdet'] = compute_logdet(X_scaled)
    if 'convex_hull_volume' in method_names:
        results['convex_hull_volume'] = compute_convex_hull_volume(X_scaled)

    result_path = os.path.join(output_dir, "volume_report.txt")
    with open(result_path, 'w') as f:
        f.write("Volume Evaluation Report\n")
        f.write(f"Features used: {features}\n")
        for key, val in results.items():
            f.write(f"{key}: {val:.6f}\n")

    if config.get("plot_curve", False):
        plot_curve(X_scaled, features, output_dir)

    if config.get("plot_pca_hull", False):
        plot_pca_convex_hull_2d(X_scaled, output_dir)

    if config.get("plot_pca_hull_3d", False):
        plot_pca_convex_hull_3d(X_scaled, output_dir)

    if config.get("plot_r_theta", False):
        plot_r_theta_distribution(X_scaled, features, output_dir)

def plot_curve(X, features, output_dir):
    xs, ys = [], []
    for i in range(2, len(X)+1):
        xs.append(i)
        ys.append(compute_logdet(X[:i]))
    plt.plot(xs, ys)
    plt.xlabel("# Samples")
    plt.ylabel("logdet (generalized variance)")
    plt.title("Diversity Growth Curve")
    plt.grid(True)
    plt.savefig(os.path.join(output_dir, "diversity_growth.png"))
    plt.close()

def plot_pca_convex_hull_2d(X, output_dir):
    pca = PCA(n_components=2)
    X_2d = pca.fit_transform(X)
    try:
        hull = ConvexHull(X_2d)
        plt.figure()
        plt.scatter(X_2d[:, 0], X_2d[:, 1], label='Points')
        for simplex in hull.simplices:
            plt.plot(X_2d[simplex, 0], X_2d[simplex, 1], 'k-')
        plt.title("PCA Projection with Convex Hull (2D)")
        plt.xlabel("PC1")
        plt.ylabel("PC2")
        plt.legend()
        plt.grid(True)
        plt.savefig(os.path.join(output_dir, "pca_convex_hull.png"))
        plt.close()
    except:
        print("Convex hull failed in 2D. Possibly due to colinear points.")

def plot_pca_convex_hull_3d(X, output_dir):
    pca = PCA(n_components=3)
    X_3d = pca.fit_transform(X)
    try:
        hull = ConvexHull(X_3d)
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        ax.scatter(X_3d[:, 0], X_3d[:, 1], X_3d[:, 2], s=20)
        for simplex in hull.simplices:
            vertices = [X_3d[simplex[0]], X_3d[simplex[1]], X_3d[simplex[2]]]
            tri = Poly3DCollection([vertices], color='lightblue', alpha=0.5)
            ax.add_collection3d(tri)
        ax.set_title("PCA Projection with Convex Hull (3D)")
        ax.set_xlabel("PC1")
        ax.set_ylabel("PC2")
        ax.set_zlabel("PC3")
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "pca_convex_hull_3d.png"))
        plt.close()
    except:
        print("Convex hull failed in 3D. Possibly due to degenerate geometry.")

def plot_r_theta_distribution(X, feature_names, output_dir):
    """
    各特徴量ごとに
      - 半径: 平均値 (0〜1 に正規化済みを想定)
      - 色   : 標準偏差（分散の大きさ）
    を表すポーラーバーチャートを描く。
    """
    num_feats = X.shape[1]

    # 角度軸（特徴量を 0〜2π に等間隔配置）
    theta = np.linspace(0, 2 * np.pi, num_feats, endpoint=False)

    # 各特徴の統計量
    mean_r = X.mean(axis=0)
    std_r = X.std(axis=0)

    # 分散（標準偏差）を色にマッピングするため 0〜1 に正規化
    if np.all(std_r == 0):
        norm_std = np.zeros_like(std_r)
    else:
        norm_std = (std_r - std_r.min()) / (std_r.max() - std_r.min())

    # カラーマップ（分散が大きいほど濃い色）
    cmap = plt.get_cmap("Blues")
    colors = [cmap(v) for v in norm_std]

    # バーの幅（全周を特徴量数で割る）
    width = 2 * np.pi / num_feats

    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(111, projection="polar")

    # ポーラーバー（棒グラフ）
    bars = ax.bar(theta, mean_r, width=width, bottom=0.0,
                  color=colors, alpha=0.8, edgecolor="black")

    # 目盛り & ラベル設定
    ax.set_xticks(theta)
    ax.set_xticklabels(feature_names, fontsize=8)
    ax.set_title("R-Theta Polar Chart (mean radius, std in color)")

    # 半径方向の範囲を 0〜1 に（正規化済み前提）
    ax.set_ylim(0, 1)

    # カラーバー（分散の凡例）— fig.colorbar で Axes を明示
    sm = plt.cm.ScalarMappable(cmap=cmap,
                               norm=plt.Normalize(vmin=float(std_r.min()),
                                                  vmax=float(std_r.max())))
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, pad=0.1)
    cbar.set_label("Std. Dev. (per feature)")

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "r_theta_distribution.png"))
    plt.close(fig)

