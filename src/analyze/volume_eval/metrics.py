import numpy as np
from scipy.spatial import ConvexHull

def compute_logdet(X):
    cov = np.cov(X.T) + 1e-8 * np.eye(X.shape[1])
    sign, logdet = np.linalg.slogdet(cov)
    return logdet if sign > 0 else float('-inf')

def compute_convex_hull_volume(X):
    if len(X) <= X.shape[1]:
        return 0.0
    try:
        hull = ConvexHull(X)
        return hull.volume
    except:
        return 0.0