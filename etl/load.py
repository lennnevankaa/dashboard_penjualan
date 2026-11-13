from sqlalchemy import text

from database.connection import get_engine

SQL_DIM_DATE = """
INSERT INTO dbo.dim_date (delivery_date, [day], [month], [year], [quarter])
SELECT DISTINCT c.delivery_date, DAY(c.delivery_date), MONTH(c.delivery_date), YEAR(c.delivery_date),
       'Q' + CAST(DATEPART(QUARTER, c.delivery_date) AS NVARCHAR(1))
FROM dbo.stg_sales_clean c
WHERE NOT EXISTS (SELECT 1 FROM dbo.dim_date x WHERE x.delivery_date = c.delivery_date)
"""

SQL_DIM_PRODUCT = """
INSERT INTO dbo.dim_product (sku_code, product_name, category_name)
SELECT c.sku_code, MAX(c.product_name), MAX(c.category_name)
FROM dbo.stg_sales_clean c
WHERE NOT EXISTS (SELECT 1 FROM dbo.dim_product x WHERE x.sku_code = c.sku_code)
GROUP BY c.sku_code
"""

SQL_DIM_MARKETPLACE = """
INSERT INTO dbo.dim_marketplace (marketplace_id, marketplace_name, company_name)
SELECT c.marketplace_id, MAX(c.marketplace_name), MAX(c.company_name)
FROM dbo.stg_sales_clean c
WHERE NOT EXISTS (SELECT 1 FROM dbo.dim_marketplace x WHERE x.marketplace_id = c.marketplace_id)
GROUP BY c.marketplace_id
"""

SQL_DIM_BUNDLING = """
INSERT INTO dbo.dim_bundling (bundling_id, bundling_name)
SELECT c.bundling_id, MAX(c.bundling_name)
FROM dbo.stg_sales_clean c
WHERE NOT EXISTS (SELECT 1 FROM dbo.dim_bundling x WHERE x.bundling_id = c.bundling_id)
GROUP BY c.bundling_id
"""

SQL_FACT = """
INSERT INTO dbo.fact_sales
    (sk_date, sk_product, sk_marketplace, sk_bundling, transaction_id, total_qty, selling_price, disc, sales, cogs)
SELECT d.sk_date, p.sk_product, m.sk_marketplace, b.sk_bundling,
       c.transaction_id, c.total_qty, c.selling_price, c.disc, c.sales, c.cogs
FROM dbo.stg_sales_clean c
JOIN dbo.dim_date d ON d.delivery_date = c.delivery_date
JOIN dbo.dim_product p ON p.sku_code = c.sku_code
JOIN dbo.dim_marketplace m ON m.marketplace_id = c.marketplace_id
JOIN dbo.dim_bundling b ON b.bundling_id = c.bundling_id
WHERE NOT EXISTS (
    SELECT 1 FROM dbo.fact_sales f
    WHERE f.transaction_id = c.transaction_id AND f.sk_product = p.sk_product
)
"""

INDEXES = [
    ("dim_date", "ix_etl_dim_date_delivery_date", "delivery_date"),
    ("dim_product", "ix_etl_dim_product_sku_code", "sku_code"),
    ("dim_marketplace", "ix_etl_dim_marketplace_marketplace_id", "marketplace_id"),
    ("dim_bundling", "ix_etl_dim_bundling_bundling_id", "bundling_id"),
    ("fact_sales", "ix_etl_fact_sales_trx_product", "transaction_id, sk_product"),
]

_indexes_ready = False


def ensure_indexes():
    global _indexes_ready
    if _indexes_ready:
        return
    engine = get_engine()
    for table, name, columns in INDEXES:
        sql = (
            f"IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = '{name}' "
            f"AND object_id = OBJECT_ID('dbo.{table}')) "
            f"CREATE INDEX [{name}] ON dbo.[{table}] ({columns})"
        )
        try:
            with engine.begin() as conn:
                conn.execute(text(sql))
        except Exception:
            pass
    _indexes_ready = True


def run():
    ensure_indexes()
    with get_engine().begin() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM dbo.stg_sales_clean")).scalar()
        if not total:
            raise ValueError("Tabel stg_sales_clean kosong. Jalankan Transform terlebih dahulu.")
        n_date = conn.execute(text(SQL_DIM_DATE)).rowcount
        n_product = conn.execute(text(SQL_DIM_PRODUCT)).rowcount
        n_marketplace = conn.execute(text(SQL_DIM_MARKETPLACE)).rowcount
        n_bundling = conn.execute(text(SQL_DIM_BUNDLING)).rowcount
        n_fact = conn.execute(text(SQL_FACT)).rowcount

    skipped = total - n_fact
    return {
        "fact_inserted": n_fact,
        "message": (
            f"Load selesai: dim_date +{n_date}, dim_product +{n_product}, dim_marketplace +{n_marketplace}, "
            f"dim_bundling +{n_bundling}, fact_sales +{n_fact:,} baris ({skipped:,} sudah ada, dilewati)"
        ),
    }