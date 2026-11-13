import pandas as pd
import streamlit as st
from sqlalchemy import text

from database.connection import get_engine

CACHE_TTL = 30

FROM_SQL = """
FROM dbo.fact_sales f
JOIN dbo.dim_date d ON d.sk_date = f.sk_date
JOIN dbo.dim_product p ON p.sk_product = f.sk_product
JOIN dbo.dim_marketplace m ON m.sk_marketplace = f.sk_marketplace
JOIN dbo.dim_bundling b ON b.sk_bundling = f.sk_bundling
"""


def clear_cache():
    st.cache_data.clear()


def _read(sql, params=None):
    return pd.read_sql(text(sql), get_engine(), params=params or {})


def _where(f):
    clauses = ["d.delivery_date BETWEEN :d1 AND :d2"]
    params = {"d1": f["date_from"], "d2": f["date_to"]}
    mapping = (
        ("company", "m.company_name"),
        ("marketplace", "m.marketplace_name"),
        ("product", "p.product_name"),
        ("bundling", "b.bundling_name"),
    )
    for key, column in mapping:
        if f.get(key) and f[key] != "ALL":
            clauses.append(f"{column} = :{key}")
            params[key] = f[key]
    return " AND ".join(clauses), params


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def filter_options():
    dates = _read("SELECT MIN(delivery_date) AS dmin, MAX(delivery_date) AS dmax FROM dbo.dim_date").iloc[0]

    def values(sql):
        return ["ALL"] + _read(sql).iloc[:, 0].dropna().tolist()

    return {
        "date_min": dates["dmin"],
        "date_max": dates["dmax"],
        "company": values("SELECT DISTINCT company_name FROM dbo.dim_marketplace ORDER BY 1"),
        "marketplace": values("SELECT DISTINCT marketplace_name FROM dbo.dim_marketplace ORDER BY 1"),
        "product": values("SELECT DISTINCT product_name FROM dbo.dim_product WHERE product_name IS NOT NULL ORDER BY 1"),
        "bundling": values("SELECT DISTINCT bundling_name FROM dbo.dim_bundling ORDER BY 1"),
    }


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def kpi(f):
    where, params = _where(f)
    sql = f"""
    SELECT ISNULL(SUM(f.sales), 0) AS total_sales,
           ISNULL(SUM(f.total_qty), 0) AS total_qty,
           ISNULL(SUM(f.disc), 0) AS total_disc,
           ISNULL(SUM(f.total_qty * f.cogs), 0) AS total_cogs,
           COUNT(DISTINCT f.transaction_id) AS n_trx,
           COUNT(*) AS n_rows
    {FROM_SQL} WHERE {where}
    """
    row = _read(sql, params).iloc[0]
    return {key: float(row[key]) for key in row.index}


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def top_products(f, n=5):
    where, params = _where(f)
    sql = f"""
    SELECT TOP ({int(n)}) p.product_name, SUM(f.total_qty) AS total_qty
    {FROM_SQL} WHERE {where}
    GROUP BY p.product_name ORDER BY total_qty DESC
    """
    return _read(sql, params)


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def sales_by_quarter(f):
    where, params = _where(f)
    sql = f"""
    SELECT d.[year] AS yr, d.[quarter] AS qtr,
           CAST(d.[year] AS NVARCHAR(4)) + '-' + d.[quarter] AS periode,
           SUM(f.sales) AS total_sales
    {FROM_SQL} WHERE {where}
    GROUP BY d.[year], d.[quarter] ORDER BY d.[year], d.[quarter]
    """
    return _read(sql, params)


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def sales_by_marketplace(f):
    where, params = _where(f)
    sql = f"""
    SELECT m.marketplace_name, SUM(f.sales) AS total_sales
    {FROM_SQL} WHERE {where}
    GROUP BY m.marketplace_name ORDER BY total_sales DESC
    """
    return _read(sql, params)


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def sales_by_bundling(f, n=8):
    where, params = _where(f)
    sql = f"""
    SELECT TOP ({int(n)}) b.bundling_name, SUM(f.sales) AS total_sales
    {FROM_SQL} WHERE {where}
    GROUP BY b.bundling_name ORDER BY total_sales DESC
    """
    return _read(sql, params)


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def transactions(f, limit=5000):
    where, params = _where(f)
    top = f"TOP ({int(limit)}) " if limit else ""
    sql = f"""
    SELECT {top}
           f.transaction_id AS [Transaction ID], d.delivery_date AS [Delivery Date],
           m.company_name AS [Company], m.marketplace_name AS [Marketplace],
           p.sku_code AS [SKU], p.product_name AS [Produk], b.bundling_name AS [Bundling],
           f.total_qty AS [Qty], f.selling_price AS [Harga], f.disc AS [Diskon],
           f.sales AS [Sales], f.cogs AS [COGS]
    {FROM_SQL} WHERE {where}
    ORDER BY d.delivery_date DESC, f.sk_sales DESC
    """
    return _read(sql, params)


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def cluster_data():
    return _read("SELECT * FROM dbo.product_cluster ORDER BY total_sales DESC")


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def cluster_evaluation():
    return _read("SELECT k, sse, dbi, is_best FROM dbo.cluster_evaluation ORDER BY k")


def etl_counts():
    sql = """
    SELECT (SELECT COUNT(*) FROM dbo.stg_sales) AS staging,
           (SELECT COUNT(*) FROM dbo.stg_sales_clean) AS clean,
           (SELECT COUNT(*) FROM dbo.fact_sales) AS fact
    """
    row = _read(sql).iloc[0]
    return {key: int(row[key]) for key in row.index}