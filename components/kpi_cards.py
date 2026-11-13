import streamlit as st

from services.formatting import num, pct, rp


def _card(label, value, color="#1E293B", bar=None):
    bar_html = f"<div class='kpi-bar'><span style='width:{bar}%'></span></div>" if bar is not None else ""
    return (
        f"<div class='kpi'><div class='kpi-label'>{label}</div>"
        f"<div class='kpi-value' style='color:{color}'>{value}</div>{bar_html}</div>"
    )


def render(k):
    margin = k["total_sales"] - k["total_cogs"]
    margin_pct = margin / k["total_sales"] * 100 if k["total_sales"] > 0 else 0
    avg_sales = k["total_sales"] / k["n_trx"] if k["n_trx"] > 0 else 0

    cols = st.columns(4)
    cols[0].markdown(_card("Total Sales (Rp)", rp(k["total_sales"]), "#2563EB"), unsafe_allow_html=True)
    cols[1].markdown(
        _card("Gross Margin (%)", pct(margin_pct), "#10B981", bar=min(100, max(0, margin_pct))),
        unsafe_allow_html=True,
    )
    cols[2].markdown(_card("Rata-rata Sales / Transaksi (Rp)", rp(avg_sales), "#2563EB"), unsafe_allow_html=True)
    cols[3].markdown(_card("Total Quantity Sold", f"{num(k['total_qty'])} unit", "#FF9B9B"), unsafe_allow_html=True)