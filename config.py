import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

SERVER = "db79693.public.databaseasp.net,1433"
DATABASE = os.getenv("DB_DATABASE", "db79693")
DB_USERNAME = os.getenv("DB_USERNAME") or "db79693"
DB_PASSWORD = os.getenv("DB_PASSWORD", "sK@83!qD?gT5")
DB_AUTO_CREATE = os.getenv("DB_AUTO_CREATE", "false").strip().lower() in {"1", "true", "yes"}

# ---------------------------------------------------------------------------
# Akun & hak akses
# role "admin"     -> semua menu
# role "manajemen" -> hanya Dashboard
# ---------------------------------------------------------------------------
USERS = {
    "admin": {"password": "admin123", "role": "admin"},
    "manajemen": {"password": "manajemen123", "role": "manajemen"},
}

# Kunci halaman yang boleh dibuka tiap role (kunci sama dengan ALL_PAGES di app.py)
ROLE_PAGES = {
    "admin": ["dashboard", "upload", "etl", "transaksi"],
    "manajemen": ["dashboard"],
}

# Tetap dipertahankan agar file lain yang masih memakainya tidak error
LOGIN_USERNAME = "admin"
LOGIN_PASSWORD = USERS["admin"]["password"]

APP_TITLE = "Dashboard Business Intelligence PT X"
ALLOWED_EXT = {".csv", ".txt", ".xlsx", ".xls"}

STG_COLUMNS = [
    "TransactionID", "Delivery_Date", "OrderNumber", "No_Sales_Order", "Market_Place",
    "Bundling_Code", "Item_Code", "Client_Code", "Item_Name", "Selling_Price", "Total_Qty",
    "Line_Amount", "Line_Amount_Return", "Total_Amount", "RRP", "TOTAL_RRP", "DISC_VALUE",
    "ASP", "TOTAL_SALES", "SUBSIDI_MP", "PENJUALAN", "SETTLEMENT_AMOUNT", "Disc",
    "Created_Date", "Brand", "Bundling_Name", "COGS", "Total_COGS", "DNI_CBP",
    "Total_DNI_CBP", "Total_Promo", "Klaim_MIC", "Total_Klaim_MIC", "Support_DNI",
    "Total_Support", "Fee_Mp", "Total_Fee_Mp", "FEE_DNI", "FEE_DNI_8",
]
REQUIRED_COLUMNS = ["TransactionID", "Delivery_Date", "Market_Place", "Item_Code", "Item_Name", "Total_Qty"]

K_RANGE = (2, 3, 4)
CLUSTER_FEATURES = ["total_qty", "total_sales", "total_disc"]
CLUSTER_LABELS = {
    2: ["High Performing", "Low Performing"],
    3: ["High Performing", "Medium Performing", "Low Performing"],
    4: ["High Performing", "Medium Performing", "Low Performing", "Very Low Performing"],
}
CLUSTER_COLORS = {
    "High Performing": "#10B981",
    "Medium Performing": "#F59E0B",
    "Low Performing": "#EF4444",
    "Very Low Performing": "#64748B",
}