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
    num_feats = X.shape[1]
    theta = np.linspace(0, 2 * np.pi, num_feats, endpoint=False)
    X_plot = np.concatenate([X, X[:, [0]]], axis=1)
    theta = np.append(theta, theta[0])

    plt.figure(figsize=(8, 8))
    ax = plt.subplot(111, polar=True)
    for row in X_plot:
        ax.plot(theta, row, color='blue', alpha=0.1)
    ax.plot(theta, np.mean(X_plot, axis=0), color='red', linewidth=2, label='Mean')
    ax.set_xticks(theta[:-1])
    ax.set_xticklabels(feature_names, fontsize=8)
    ax.set_title("R-Theta Coverage over Features")
    ax.legend()
    ax.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "r_theta_distribution.png"))
    plt.close()
