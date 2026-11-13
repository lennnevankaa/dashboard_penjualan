import numpy as np
import pandas as pd
from sqlalchemy import inspect, text

from database import bulk
from database.connection import get_engine

NULL_TOKENS = {"NULL", "NAN", "NONE", ""}
DATE_COLUMN = "Delivery_Date"
FRACTION_PATTERN = r"(\d{1,2}:\d{2}:\d{2})[.,:]\d+"

# ---------------------------------------------------------------------------
# Pengaturan filter produk FREE / harga 0
# ---------------------------------------------------------------------------
# Kata yang menandakan produk free (tidak case sensitive).
# Contoh yang terbuang: "Produk A (FREE)", "Free Gift Tumbler", "Gratis Sample"
FREE_PATTERN = r"\bfree\b|\bgratis\b|\bhadiah\b"
FREE_CHECK_ITEM_NAME = True      # cek kata free di Item_Name
FREE_CHECK_BUNDLING_NAME = False # cek kata free di Bundling_Name (hati-hati: bisa membuang SEMUA isi paket)
FREE_CHECK_ZERO_PRICE = True     # buang baris dengan harga 0

# ---------------------------------------------------------------------------
# Pengaturan bundling
# ---------------------------------------------------------------------------
# Bundling code hanya dipakai jika Bundling_Name juga terisi.
# Jika Bundling_Name kosong, baris dianggap TANPA bundling (NO-BUNDLING).
# False = baris tetap masuk sebagai "Tanpa Bundling"
# True  = baris yang tidak punya Bundling_Name dibuang sama sekali
BUNDLING_DROP_ROWS_WITHOUT_NAME = False

REQUIRED_STAGING = [
    "TransactionID",
    "Delivery_Date",
    "Market_Place",
    "Brand",
    "Bundling_Code",
    "Bundling_Name",
    "Item_Code",
    "Item_Name",
    "Total_Qty",
    "DISC_VALUE",
    "RRP",
    "Selling_Price",
    "COGS",
]


def _norm(name):
    return str(name).lower().replace("_", "").replace(" ", "").replace("-", "").strip()


def _txt(series):
    s = series.astype("string").str.strip()
    return s.mask(s.str.upper().isin(NULL_TOKENS))


def _num(series):
    s = _txt(series)
    has_both = s.str.contains(",", regex=False, na=False) & s.str.contains(".", regex=False, na=False)
    s = s.mask(has_both, s.str.replace(".", "", regex=False))
    s = s.str.replace(",", ".", regex=False)
    return pd.to_numeric(s, errors="coerce").astype("float64")


def clean_datetime_series(series):
    s = _txt(series).str.replace(FRACTION_PATTERN, r"\1", regex=True)
    parsed = pd.to_datetime(s, errors="coerce")
    missing = parsed.isna() & s.notna()
    if missing.any():
        parsed = parsed.where(~missing, pd.to_datetime(s.where(missing), errors="coerce", dayfirst=True))
    return parsed.dt.normalize()


def _free_mask(item_name, bundling_name, rrp, unit_price):
    """True untuk baris yang termasuk produk free / harga 0."""
    flag = pd.Series(False, index=item_name.index)

    if FREE_CHECK_ITEM_NAME:
        flag |= item_name.str.contains(FREE_PATTERN, case=False, regex=True, na=False).astype(bool)

    if FREE_CHECK_BUNDLING_NAME:
        flag |= bundling_name.str.contains(FREE_PATTERN, case=False, regex=True, na=False).astype(bool)

    if FREE_CHECK_ZERO_PRICE:
        # Pakai harga mentah (RRP, jika kosong pakai Selling_Price).
        # Harga kosong (NULL) TIDAK dianggap 0, jadi tidak ikut terbuang.
        price = rrp.fillna(unit_price)
        flag |= price.eq(0).fillna(False).astype(bool)

    return flag


def _staging_query(engine):
    actual = [c["name"] for c in inspect(engine).get_columns("stg_sales", schema="dbo")]
    lookup = {_norm(c): c for c in actual}

    missing = [c for c in REQUIRED_STAGING if _norm(c) not in lookup]
    if missing:
        raise ValueError(
            "Kolom tidak ditemukan di dbo.stg_sales: " + ", ".join(missing)
            + ". Kolom yang tersedia: " + ", ".join(actual)
        )

    select_parts = []
    for wanted in REQUIRED_STAGING:
        real = lookup[_norm(wanted)]
        if wanted == DATE_COLUMN:
            select_parts.append(f"CONVERT(VARCHAR(40), [{real}], 120) AS [{wanted}]")
        else:
            select_parts.append(f"CAST([{real}] AS NVARCHAR(MAX)) AS [{wanted}]")

    return f"SELECT {', '.join(select_parts)} FROM dbo.stg_sales"


def _standardize_columns(raw):
    lookup = {_norm(c): c for c in raw.columns}
    missing = [c for c in REQUIRED_STAGING if _norm(c) not in lookup]
    if missing:
        raise ValueError(
            "Kolom tidak ada di hasil query: " + ", ".join(missing)
            + ". Kolom hasil query: " + ", ".join(map(str, raw.columns))
        )
    rename = {lookup[_norm(c)]: c for c in REQUIRED_STAGING}
    return raw.rename(columns=rename)[REQUIRED_STAGING]


def run(path=None, *args, **kwargs):
    engine = get_engine()
    raw = pd.read_sql(text(_staging_query(engine)), engine)
    raw = _standardize_columns(raw)
    rows_in = len(raw)
    if rows_in == 0:
        raise ValueError("Tabel stg_sales kosong. Jalankan Extract terlebih dahulu.")

    marketplace = _txt(raw["Market_Place"])
    parts = marketplace.str.split(" - ", n=1, expand=True)
    if parts.shape[1] < 2:
        parts[1] = pd.NA
    company = parts[0].where(parts[1].notna(), "UMUM").fillna("UMUM")
    marketplace_name = parts[1].fillna(parts[0]).fillna("UNKNOWN")
    marketplace_id = marketplace.fillna("UNKNOWN")

    brand = _txt(raw["Brand"])
    bundling_code = _txt(raw["Bundling_Code"])
    bundling_label = _txt(raw["Bundling_Name"])
    item_name = _txt(raw["Item_Name"])

    # Bundling dianggap ada hanya jika code DAN name terisi
    has_bundling = bundling_code.notna() & bundling_label.notna()

    qty = _num(raw["Total_Qty"])
    disc = _num(raw["DISC_VALUE"]).fillna(0)
    rrp = _num(raw["RRP"])
    unit_price = _num(raw["Selling_Price"])
    selling_price = rrp.fillna(unit_price + disc / qty.replace(0, np.nan)).fillna(0)
    cogs = _num(raw["COGS"]).fillna(0)

    sales = qty * selling_price - disc

    # Tandai produk free / harga 0 (dihitung dari data mentah)
    free = _free_mask(item_name, bundling_label, rrp, unit_price)

    clean = pd.DataFrame({
        "transaction_id": _txt(raw["TransactionID"]),
        "delivery_date": clean_datetime_series(raw[DATE_COLUMN]),
        "marketplace_id": marketplace_id,
        "marketplace_name": marketplace_name,
        "company_name": company,
        "bundling_id": bundling_code.where(has_bundling).fillna("NO-BUNDLING"),
        "bundling_name": bundling_label.where(has_bundling).fillna("Tanpa Bundling"),
        "sku_code": _txt(raw["Item_Code"]),
        "product_name": item_name,
        "category_name": brand.fillna(company),
        "total_qty": qty,
        "selling_price": selling_price.round(2),
        "disc": disc.round(2),
        "sales": sales.round(2),
        "cogs": cogs.round(2),
        "_is_free": free,
    })

    base_valid = (
        clean["transaction_id"].notna()
        & clean["delivery_date"].notna()
        & clean["sku_code"].notna()
        & clean["total_qty"].notna()
    )
    if BUNDLING_DROP_ROWS_WITHOUT_NAME:
        base_valid = base_valid & has_bundling
    invalid = int((~base_valid).sum())
    free_removed = int((base_valid & clean["_is_free"]).sum())

    clean = clean[base_valid & ~clean["_is_free"]].drop(columns=["_is_free"]).copy()

    before = len(clean)
    clean = clean.drop_duplicates(subset=["transaction_id", "sku_code"], keep="first")
    duplicates = before - len(clean)
    clean["total_qty"] = clean["total_qty"].round().astype(int)

    payload = clean.astype(object).where(clean.notna(), None)
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE dbo.stg_sales_clean"))
        bulk.insert(conn, payload, "stg_sales_clean")

    return {
        "rows_in": rows_in,
        "rows_out": len(clean),
        "message": (
            f"[transform v7] Transform selesai: {rows_in:,} baris masuk, {len(clean):,} baris bersih "
            f"({invalid:,} tidak valid, {free_removed:,} produk free/harga 0 dibuang, "
            f"{duplicates:,} duplikat dibuang)"
        ),
    }