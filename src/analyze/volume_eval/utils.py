import numpy as np
from sklearn.preprocessing import MinMaxScaler, StandardScaler

def normalize_features(X, method='minmax'):
    if method == 'minmax':
        scaler = MinMaxScaler()
    elif method == 'standard':
        scaler = StandardScaler()
    else:
        raise ValueError(f"Unsupported normalization method: {method}")
    return scaler.fit_transform(X)