import datetime
import re
import sys
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

try:
    import pyodbc as ODBC

    FAST = True
except ImportError:
    import pypyodbc as ODBC

    sys.modules["pyodbc"] = ODBC
    FAST = False

from sqlalchemy import create_engine, text

import config

SCHEMA_FILE = Path(__file__).resolve().parent / "schema.sql"


def _safe_timestamp(value):
    if isinstance(value, bytes):
        value = value.decode("ascii")
    value = value.strip()
    if not value:
        return None
    fraction = value[20:26].ljust(6, "0")
    return datetime.datetime(
        int(value[0:4]),
        int(value[5:7]),
        int(value[8:10]),
        int(value[11:13]),
        int(value[14:16]),
        int(value[17:19]),
        int(fraction),
    )


def _patch_timestamp_converter():
    original = ODBC.dttm_cvt
    ODBC.dttm_cvt = _safe_timestamp
    for key, spec in list(ODBC.SQL_data_type_dict.items()):
        if spec[1] is original:
            ODBC.SQL_data_type_dict[key] = (spec[0], _safe_timestamp) + tuple(spec[2:])


if not FAST:
    _patch_timestamp_converter()


def _driver():
    found = [d for d in ODBC.drivers() if "SQL Server" in d]
    modern = sorted(d for d in found if d.startswith("ODBC Driver"))
    if modern:
        return modern[-1]
    if found:
        return found[-1]
    raise RuntimeError("ODBC Driver for SQL Server tidak ditemukan. Install ODBC Driver 17 atau 18 for SQL Server.")


def _url(database):
    odbc = (
        f"DRIVER={{{_driver()}}};SERVER={config.SERVER};DATABASE={database};"
        "Trusted_Connection=yes;Encrypt=no;TrustServerCertificate=yes;"
    )
    return "mssql+pyodbc:///?odbc_connect=" + quote_plus(odbc)


@lru_cache(maxsize=1)
def get_engine():
    if FAST:
        return create_engine(_url(config.DATABASE), pool_pre_ping=True, fast_executemany=True)
    return create_engine(_url(config.DATABASE), pool_pre_ping=True)


def ensure_database():
    engine = create_engine(_url("master"), isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        conn.execute(text(f"IF DB_ID('{config.DATABASE}') IS NULL CREATE DATABASE [{config.DATABASE}]"))
    engine.dispose()


def init_schema():
    sql = SCHEMA_FILE.read_text(encoding="utf-8")
    statements = [s.strip() for s in re.split(r"^\s*GO\s*$", sql, flags=re.M | re.I) if s.strip()]
    with get_engine().begin() as conn:
        for statement in statements:
            conn.execute(text(statement))


def init_db():
    ensure_database()
    init_schema()