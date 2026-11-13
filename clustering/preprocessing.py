import numpy as np


def min_max_normalize(df, columns):
    # Rumus: X' = (X - X_min) / (X_max - X_min)
    x = df[columns].astype(float).to_numpy()
    x_min = x.min(axis=0)
    x_max = x.max(axis=0)
    span = np.where(x_max - x_min == 0, 1.0, x_max - x_min)
    return (x - x_min) / span