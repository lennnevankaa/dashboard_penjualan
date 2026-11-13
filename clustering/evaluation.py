import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN, Birch, KMeans, MeanShift, estimate_bandwidth
from sklearn.metrics import silhouette_samples, silhouette_score
from sklearn.mixture import GaussianMixture

from clustering.kmeans import euclidean_distance


def sse(X, labels, centroids):
    # Rumus: SSE = sum_{k=1..K} sum_{x_i in C_k} ||x_i - mu_k||^2
    return float(((X - centroids[labels]) ** 2).sum())


def davies_bouldin(X, labels, centroids):
    # Rumus: s_i = (1 / |C_i|) * sum_{x in C_i} ||x - c_i||
    #        R_ij = (s_i + s_j) / d(c_i, c_j)
    #        D_i = max_{j != i} R_ij
    #        DBI = (1 / K) * sum_{i=1..K} D_i
    k = len(centroids)
    scatter = np.array([
        np.linalg.norm(X[labels == i] - centroids[i], axis=1).mean() if np.any(labels == i) else 0.0
        for i in range(k)
    ])
    separation = euclidean_distance(centroids, centroids)
    worst = []
    for i in range(k):
        ratios = [(scatter[i] + scatter[j]) / separation[i, j] for j in range(k) if j != i and separation[i, j] > 0]
        worst.append(max(ratios) if ratios else 0.0)
    return float(np.mean(worst))


# ---------------------------------------------------------------------------
# Silhouette Score
# ---------------------------------------------------------------------------
N_CLUSTERS = 3
DBSCAN_EPS = 0.8
DBSCAN_MIN_SAMPLES = 2
MEANSHIFT_QUANTILE = 0.3


def silhouette_overall(X, labels):
    # Rumus: s(i) = (b(i) - a(i)) / max(a(i), b(i)), skor = rata-rata s(i)
    labels = np.asarray(labels)
    k = len(set(labels))
    if k < 2 or len(X) <= k:
        return None
    return float(silhouette_score(X, labels))


def silhouette_per_sample(X, labels):
    labels = np.asarray(labels)
    k = len(set(labels))
    if k < 2 or len(X) <= k:
        return np.full(len(X), np.nan)
    return silhouette_samples(X, labels)


def silhouette_label(s):
    if s > 0.70:
        return "Struktur klaster kuat", "#16A34A"
    if s > 0.50:
        return "Struktur klaster baik", "#22C55E"
    if s > 0.25:
        return "Struktur klaster lemah", "#F59E0B"
    return "Struktur klaster tidak signifikan", "#EF4444"


def compare_algorithms(X, n_clusters=N_CLUSTERS):
    if len(X) <= n_clusters:
        return None

    def run_meanshift(Z):
        bw = estimate_bandwidth(Z, quantile=MEANSHIFT_QUANTILE)
        return MeanShift(bandwidth=bw if bw > 0 else None).fit_predict(Z)

    algos = {
        "K-Means": lambda Z: KMeans(n_clusters=n_clusters, n_init=10, random_state=42).fit_predict(Z),
        "GMM": lambda Z: GaussianMixture(n_components=n_clusters, random_state=42).fit_predict(Z),
        "DBSCAN": lambda Z: DBSCAN(eps=DBSCAN_EPS, min_samples=DBSCAN_MIN_SAMPLES).fit_predict(Z),
        "Mean-Shift": run_meanshift,
        "BIRCH": lambda Z: Birch(n_clusters=n_clusters).fit_predict(Z),
    }

    rows = []
    for name, fn in algos.items():
        score, k, noise = None, 0, 0
        try:
            labels = np.asarray(fn(X))
            mask = labels != -1
            noise = int((~mask).sum())
            k = len(set(labels[mask]))
            if k >= 2 and mask.sum() > k:
                score = float(silhouette_score(X[mask], labels[mask]))
        except Exception:
            pass
        rows.append({"Algoritma": name, "Silhouette": score, "Jumlah Klaster": k, "Noise": noise})
    return pd.DataFrame(rows)