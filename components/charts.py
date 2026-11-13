import pandas as pd
import plotly.express as px
import streamlit as st

import config

PALETTE = ["#EE4D2D", "#010101", "#10B981", "#F59E0B", "#8B5CF6", "#EF4444", "#06B6D4", "#64748B"]


def _base(fig, height=290, legend=False):
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=legend,
        font=dict(color="#475569", size=12),
        colorway=PALETTE,
    )
    fig.update_xaxes(gridcolor="#E2E8F0", zeroline=False, title=None)
    fig.update_yaxes(gridcolor="#E2E8F0", zeroline=False, title=None)
    return fig


def show(fig):
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def revenue_balance(k):
    margin = k["total_sales"] - k["total_cogs"]
    df = pd.DataFrame({
        "Komponen": ["Sales", "COGS", "Margin", "Diskon"],
        "Nilai": [k["total_sales"], k["total_cogs"], margin, k["total_disc"]],
    })
    fig = px.bar(df, x="Komponen", y="Nilai", color="Komponen", color_discrete_sequence=PALETTE)
    return _base(fig)


def top_products(df):
    fig = px.bar(df.sort_values("total_qty"), x="total_qty", y="product_name", orientation="h", color_discrete_sequence=["#6D41A1"])
    return _base(fig)


def quarterly(df):
    fig = px.bar(df, x="periode", y="total_sales", color_discrete_sequence=["#EE4D2D"])
    return _base(fig)


def marketplace_donut(df):
    fig = px.pie(df, names="marketplace_name", values="total_sales", hole=0.62, color_discrete_sequence=PALETTE)
    fig.update_traces(textinfo="percent")
    fig = _base(fig, legend=True)
    fig.update_layout(legend=dict(orientation="h", y=-0.1))
    return fig
    
def cluster_scatter(df):
    fig = px.scatter(
        df, x="total_qty", y="total_sales", color="cluster_label",
        color_discrete_map=config.CLUSTER_COLORS, hover_name="product_name",
    )
    fig.update_traces(marker=dict(size=11, line=dict(width=1, color="#fff")))
    fig = _base(fig, legend=True)
    fig.update_layout(legend=dict(orientation="h", y=-0.15, title=None))
    return fig


def bundling_bar(df):
    fig = px.bar(df.sort_values("total_sales"), x="total_sales", y="bundling_name", orientation="h", color_discrete_sequence=["#F97316"])
    return _base(fig)


def elbow(df):
    fig = px.line(df, x="k", y="sse", markers=True, color_discrete_sequence=["#EE4D2D"])
    fig.update_xaxes(dtick=1)
    return _base(fig, height=240)


def dbi(df):
    fig = px.bar(df, x="k", y="dbi", color_discrete_sequence=["#10B981"])
    fig.update_xaxes(dtick=1)
    return _base(fig, height=240)