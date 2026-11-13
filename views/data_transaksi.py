import streamlit as st

import config
from components import filters, layout
from database import queries
from services.formatting import num


def render():
    layout.page_title(config.APP_TITLE)

    with layout.card("trx_filter", "Filter Data"):
        f = filters.render("trx", inline=True)

    df = queries.transactions(f)
    with layout.card("trx_table", f"Data Transaksi fact_sales ({num(len(df))} baris, maks. 5.000)"):
        if df.empty:
            st.info("Belum ada data transaksi untuk filter ini.")
            return
        st.dataframe(df, hide_index=True, width="stretch", height=520)
        st.download_button(
            "Unduh CSV",
            df.to_csv(index=False).encode("utf-8-sig"),
            file_name="fact_sales.csv",
            mime="text/csv",
        )