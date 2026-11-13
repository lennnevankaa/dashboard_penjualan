import numpy as np


def euclidean_distance(X, C):
    # Rumus: d(x_i, c_k) = sqrt( sum_{j=1..p} (x_j - c_j)^2 )
    return np.sqrt(((X[:, None, :] - C[None, :, :]) ** 2).sum(axis=2))


def update_centroids(X, labels, old):
    # Rumus: mu_j = (1 / |S_j|) * sum_{x_i in S_j} x_i
    new = old.copy()
    for j in range(len(old)):
        members = X[labels == j]
        if len(members):
            new[j] = members.sum(axis=0) / len(members)
    return new


def kmeans(X, k, max_iter=300, n_init=10, seed=42, tol=1e-6):
    rng = np.random.default_rng(seed)
    best = None
    for _ in range(n_init):
        centroids = X[rng.choice(len(X), k, replace=False)].copy()
        for _ in range(max_iter):
            labels = euclidean_distance(X, centroids).argmin(axis=1)
            updated = update_centroids(X, labels, centroids)
            shift = np.abs(updated - centroids).max()
            centroids = updated
            if shift < tol:
                break
        labels = euclidean_distance(X, centroids).argmin(axis=1)
        error = float(((X - centroids[labels]) ** 2).sum())
        if best is None or error < best[0]:
            best = (error, labels, centroids)
    return best[1], best[2]