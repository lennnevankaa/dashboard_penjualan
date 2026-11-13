from datetime import date

import pandas as pd
import streamlit as st

from database import queries


def _to_date(value, fallback):
    return pd.Timestamp(value).date() if pd.notna(value) else fallback


def render(prefix, inline=False):
    options = queries.filter_options()
    today = date.today()
    d_min = _to_date(options["date_min"], today)
    d_max = _to_date(options["date_max"], today)

    slots = st.columns(5) if inline else [st.container() for _ in range(5)]

    with slots[0]:
        picked = st.date_input("Delivery Date", value=(d_min, d_max), min_value=d_min, max_value=d_max, key=f"{prefix}_date")
    with slots[1]:
        company = st.selectbox("Company", options["company"], key=f"{prefix}_company")
    with slots[2]:
        marketplace = st.selectbox("Marketplace", options["marketplace"], key=f"{prefix}_marketplace")
    with slots[3]:
        product = st.selectbox("Product", options["product"], key=f"{prefix}_product")
    with slots[4]:
        bundling = st.selectbox("Bundling", options["bundling"], key=f"{prefix}_bundling")

    if isinstance(picked, (tuple, list)) and len(picked) == 2:
        date_from, date_to = picked
    else:
        date_from, date_to = d_min, d_max

    return {
        "date_from": date_from,
        "date_to": date_to,
        "company": company,
        "marketplace": marketplace,
        "product": product,
        "bundling": bundling,
    }