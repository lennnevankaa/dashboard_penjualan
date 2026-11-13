import streamlit as st

import config
from components import layout, sidebar
from database.connection import init_db
from services import auth
from views import dashboard, data_transaksi, login, proses_etl, upload_data

st.set_page_config(page_title=config.APP_TITLE, page_icon="📊", layout="wide")
layout.inject_css()


@st.cache_resource(show_spinner="Menyiapkan database...")
def boot():
    init_db()
    return True


auth_slot = st.empty()

if not auth.is_logged_in():
    with auth_slot.container():
        layout.hide_sidebar()
        login.render()
    st.stop()

auth_slot.empty()

try:
    boot()
except Exception as exc:
    st.error(f"Gagal terhubung ke SQL Server: {exc}")
    st.stop()

# Semua halaman yang ada. Kunci harus sama dengan config.ROLE_PAGES.
ALL_PAGES = {
    "dashboard": st.Page(dashboard.render, title="Halaman Dashboard", icon=":material/dashboard:", url_path="dashboard", default=True),
    "upload": st.Page(upload_data.render, title="Input Data (Upload File)", icon=":material/upload_file:", url_path="upload"),
    "etl": st.Page(proses_etl.render, title="Proses ETL", icon=":material/account_tree:", url_path="etl"),
    "transaksi": st.Page(data_transaksi.render, title="Data Transaksi", icon=":material/table_view:", url_path="transaksi"),
}

# Hanya halaman yang diizinkan untuk role yang login yang didaftarkan ke navigasi dan sidebar
pages = auth.allowed_pages(ALL_PAGES)

navigation = st.navigation(pages, position="hidden")
sidebar.render(pages)
navigation.run()