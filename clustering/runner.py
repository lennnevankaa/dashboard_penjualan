import numpy as np
import pandas as pd
from sqlalchemy import text

import config
from clustering.evaluation import davies_bouldin, sse
from clustering.kmeans import kmeans
from clustering.preprocessing import min_max_normalize
from database.connection import get_engine

SQL_PRODUCTS = """
SELECT p.sk_product, p.sku_code, p.product_name,
       SUM(f.total_qty) AS total_qty, SUM(f.sales) AS total_sales, SUM(f.disc) AS total_disc,
       MAX(d.delivery_date) AS last_delivery_date
FROM dbo.fact_sales f
JOIN dbo.dim_product p ON p.sk_product = f.sk_product
JOIN dbo.dim_date d ON d.sk_date = f.sk_date
GROUP BY p.sk_product, p.sku_code, p.product_name
"""


def run():
    engine = get_engine()
    df = pd.read_sql(text(SQL_PRODUCTS), engine)
    n = len(df)
    if n < 3:
        return {"products": n, "message": f"Clustering dilewati: hanya {n} produk (minimal 3)"}

    X = min_max_normalize(df, config.CLUSTER_FEATURES)

    evaluations, models = [], {}
    for k in config.K_RANGE:
        if k >= n:
            continue
        labels, centroids = kmeans(X, k)
        models[k] = (labels, centroids)
        evaluations.append({"k": k, "sse": sse(X, labels, centroids), "dbi": davies_bouldin(X, labels, centroids)})

    best_k = min(evaluations, key=lambda e: e["dbi"])["k"]
    labels, centroids = models[best_k]

    order = np.argsort(-centroids.mean(axis=1))
    rank = {int(cluster): position for position, cluster in enumerate(order)}
    names = config.CLUSTER_LABELS[best_k]

    df["qty_norm"] = X[:, 0]
    df["sales_norm"] = X[:, 1]
    df["disc_norm"] = X[:, 2]
    df["cluster_id"] = [rank[int(label)] + 1 for label in labels]
    df["cluster_label"] = [names[rank[int(label)]] for label in labels]
    df["k"] = best_k

    result = pd.DataFrame(evaluations)
    result["is_best"] = (result["k"] == best_k).astype(int)

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE dbo.product_cluster"))
        conn.execute(text("TRUNCATE TABLE dbo.cluster_evaluation"))
        df.to_sql("product_cluster", conn, schema="dbo", if_exists="append", index=False, chunksize=1000)
        result.to_sql("cluster_evaluation", conn, schema="dbo", if_exists="append", index=False)

    best = result[result["k"] == best_k].iloc[0]
    return {
        "products": n,
        "best_k": best_k,
        "message": f"Clustering selesai: {n:,} produk, K terbaik = {best_k} (DBI {best['dbi']:.4f}, SSE {best['sse']:.4f})",
    }