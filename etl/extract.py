from pathlib import Path

import pandas as pd
from sqlalchemy import text

import config
from database import bulk
from database.connection import get_engine


def _detect_separator(path, encoding):
    with open(path, "r", encoding=encoding, errors="replace") as handle:
        header = handle.readline()
    return max(["\t", ";", ",", "|"], key=header.count)


def read_source(path):
    path = Path(path)
    if path.suffix.lower() in (".xlsx", ".xls"):
        return pd.read_excel(path, dtype=str)

    for encoding in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            sep = _detect_separator(path, encoding)
            return pd.read_csv(path, sep=sep, dtype=str, encoding=encoding)
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue

    raise ValueError("Encoding atau format file tidak dikenali.")


def _normalize_string(s):
    return str(s).lower().replace("_", "").replace(" ", "").replace("-", "").strip()


def run(path):
    df = read_source(path)
    df.columns = [str(c).strip() for c in df.columns]

    stg_map = {_normalize_string(col): col for col in config.STG_COLUMNS}
    new_columns = {}
    for col in df.columns:
        norm_col = _normalize_string(col)
        if norm_col in stg_map:
            new_columns[col] = stg_map[norm_col]
    df = df.rename(columns=new_columns)

    missing = [c for c in config.REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError("Kolom wajib tidak ditemukan: " + ", ".join(missing))

    df = df[[c for c in config.STG_COLUMNS if c in df.columns]]
    payload = df.astype(object).where(df.notna(), None)

    with get_engine().begin() as conn:
        conn.execute(text("TRUNCATE TABLE dbo.stg_sales"))
        bulk.insert(conn, payload, "stg_sales")

    return {"rows": len(df), "message": f"Extract selesai: {len(df):,} baris dari {Path(path).name} masuk ke stg_sales"}