import html
import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import config
from components import filters, layout
from database import queries

# ---------------------------------------------------------------------------
# Daftar kemungkinan nama kolom (huruf besar/kecil dan spasi diabaikan).
# URUTAN PENTING: nama yang paling atas dipakai lebih dulu.
# ---------------------------------------------------------------------------
CANDIDATES = {
    "id": ["transaction_id", "id_transaksi", "order_id", "no_pesanan", "invoice", "id", "trx_id"],
    "date": ["delivery_date", "tanggal_kirim", "tgl_kirim", "date", "tanggal", "order_date", "delivery_dt"],
    "marketplace": ["marketplace", "platform", "platform_marketplace", "channel"],
    "product": ["product", "produk", "nama_produk", "product_name", "sku_name"],
    "bundling": ["bundling", "bundle", "promo", "jenis_promo", "bundling_type"],
    "qty": ["qty", "quantity", "jumlah", "total_qty", "qty_sold"],
    "sales": ["net_sales", "nett_sales", "total_net_sales", "total_sales", "sales", "revenue", "total_penjualan", "amount"],
    "cogs": ["cogs", "hpp", "total_cogs", "cost"],
}

OPTIONAL = {
    "gross": ["gross_sales", "total_gross_sales", "penjualan_kotor"],
    "discount": ["total_diskon", "diskon", "discount", "total_discount"],
}

# Nama kolom yang sudah pasti NET (gross - diskon)
NET_NAMES = {"net_sales", "nett_sales", "total_net_sales"}

# ---------------------------------------------------------------------------
# KPI: Target Sales Nominal per bulan (Rp)
# Urutan = Jan, Feb, ..., Des. Bulan tanpa target (mis. Des 2024) tidak dihitung.
# ---------------------------------------------------------------------------
TARGETS = {
    2025: [5_043_332, 5_187_117, 6_868_368, 8_359_417, 12_306_399, 9_175_472,
           10_974_979, 12_981_236, 13_467_988, 16_100_243, 15_271_397, 16_349_486],
    2026: [29_210_667, 58_421_334, 68_158_223, 58_421_334, 77_895_112, 97_368_890,
           87_632_001, 87_632_001, 97_368_890, 87_632_001, 107_105_779, 116_842_668],
}


def target_of(period):
    """Target nominal (Rp) satu bulan (pd.Period). 0 bila tahunnya belum punya target."""
    vals = TARGETS.get(period.year)
    return vals[period.month - 1] if vals else 0


N_CLUSTERS = 3

# Variasi penulisan Marketplace (huruf besar/kecil) agar mapping warna pasti terbaca
MP_COLORS = {
    "Shopee": "#EE4D2D", "SHOPEE": "#EE4D2D", "shopee": "#EE4D2D",
    "TikTok": "#000000", "TIKTOK": "#000000", "TikTok Shop": "#000000", "TIK-TOK SHOP": "#000000", "tiktok shop": "#000000",
    "Tokopedia": "#10B981", "TOKOPEDIA": "#10B981", "tokopedia": "#10B981",
}

CLUSTER_COLORS = {"High Performing": "#22C55E", "Medium": "#F59E0B", "Low Performing": "#EF4444"}
BLUE, PURPLE = "#3B82F6", "#8B5CF6"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]

# Ukuran seragam untuk 3 kartu baris ke-3 (Marketplace, K-Means, Bundling)
CHART_H = 300
ROW3_MARGIN = dict(l=10, r=10, t=10, b=70)  # b=70 = ruang untuk legend / label sumbu x


# ------------------------------- helper ------------------------------------
def rp(x):
    return "Rp " + f"{x:,.0f}".replace(",", ".")


def n(x):
    return f"{x:,.0f}".replace(",", ".")


def _norm(s):
    return str(s).strip().lower().replace(" ", "_")


def _parse_number(v):
    """Ubah teks angka (format Indonesia / internasional) menjadi float. Gagal -> NaN."""
    if v is None:
        return np.nan
    s = str(v).strip()
    if s == "" or s.lower() in ("nan", "none", "null"):
        return np.nan
    s = re.sub(r"(?i)rp", "", s).replace(" ", "")
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")  # 1.234,50
        else:
            s = s.replace(",", "")  # 1,234.50
    elif "," in s:
        if s.count(",") == 1 and len(s.split(",")[-1]) != 3:
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")
    elif s.count(".") > 1 or re.fullmatch(r"-?\d{1,3}(\.\d{3})+", s):
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return np.nan


def to_num(series):
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce").fillna(0)
    return series.map(_parse_number).fillna(0)


def load(f):
    try:
        df = queries.transactions(f, limit=None).copy()
    except TypeError:
        df = queries.transactions(f).copy()
        if len(df) >= 5000:
            st.error(
                f"queries.transactions masih dibatasi {len(df):,} baris, sehingga sebagian bulan hilang dan angka "
                "tidak sama dengan SQL. Tambahkan parameter limit di database/queries.py."
            )
    if df.empty:
        return df

    lookup = {_norm(c): c for c in df.columns}
    rename, missing = {}, []
    for std, names in CANDIDATES.items():
        found = next((lookup[_norm(x)] for x in names if _norm(x) in lookup), None)
        if found is None:
            missing.append(std)
        else:
            rename[found] = std
    if missing:
        st.error(f"Kolom belum terdeteksi: {missing}")
        st.write("Kolom yang tersedia di data kamu:", list(df.columns))
        st.stop()

    for std, names in OPTIONAL.items():
        found = next((lookup[_norm(x)] for x in names if _norm(x) in lookup and lookup[_norm(x)] not in rename), None)
        if found is not None:
            rename[found] = std

    sales_src = next((k for k, v in rename.items() if v == "sales"), "sales")

    df = df.rename(columns=rename)
    df["date"] = pd.to_datetime(df["date"])
    for c in ("qty", "sales", "cogs", "gross", "discount"):
        if c in df.columns:
            df[c] = to_num(df[c])

    if _norm(sales_src) not in NET_NAMES and "gross" in df.columns and "discount" in df.columns:
        df["sales"] = df["gross"] - df["discount"]
        sales_src = "gross_sales - total_diskon"

    df["cogs"] = df["qty"] * df["cogs"]
    df["profit"] = df["sales"] - df["cogs"]
    df.attrs["sales_source"] = sales_src
    return df


def _filter_dates(f):
    try:
        if f.get("date_from") is not None and f.get("date_to") is not None:
            return pd.Timestamp(f["date_from"]), pd.Timestamp(f["date_to"])
    except Exception:
        pass
    try:
        items = list(f.items()) if isinstance(f, dict) else list(vars(f).items())
    except TypeError:
        return None, None
    try:
        for k, v in items:
            kl = str(k).lower()
            if ("date" in kl or "tanggal" in kl) and isinstance(v, (list, tuple)) and len(v) == 2:
                return pd.Timestamp(v[0]), pd.Timestamp(v[1])
        start = end = None
        for k, v in items:
            kl = str(k).lower()
            if v is None or isinstance(v, (list, tuple, dict)):
                continue
            if any(x in kl for x in ("start", "from", "dari", "mulai")):
                start = pd.Timestamp(v)
            elif any(x in kl for x in ("end", "to", "sampai", "akhir")):
                end = pd.Timestamp(v)
        return start, end
    except Exception:
        return None, None


def analysis_months(f, df):
    dmin, dmax = df["date"].min().to_period("M"), df["date"].max().to_period("M")
    fs, fe = _filter_dates(f)
    start = pd.Timestamp(fs).to_period("M") if fs is not None else dmin
    end = pd.Timestamp(fe).to_period("M") if fe is not None else dmax
    end = min(end, max(pd.Period(pd.Timestamp.today(), "M"), dmax))
    start, end = min(start, dmin), max(end, dmax)
    return pd.period_range(start, end, freq="M")


def base_layout(fig, height=260):
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=12, color="#334155"),
        showlegend=False,
    )
    return fig


def row3_layout(fig, legend=False, legend_y=0):
    """Layout seragam untuk kartu baris 3 agar tinggi & bentuk sejajar."""
    base_layout(fig, CHART_H)
    fig.update_layout(
        margin=ROW3_MARGIN,
        showlegend=legend,
        legend=dict(
            orientation="h",
            x=0.5, xanchor="center",
            y=legend_y, yanchor="top",
            font=dict(size=11),
            tracegroupgap=0,
        ),
    )
    return fig


def show(fig):
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def product_matrix(df):
    p = df.groupby("product").agg(qty=("qty", "sum"), sales=("sales", "sum"), profit=("profit", "sum")).reset_index()
    X = None
    if len(p) > N_CLUSTERS:
        from sklearn.preprocessing import StandardScaler

        X = StandardScaler().fit_transform(p[["qty", "sales", "profit"]])
    return p, X


def cluster_products(df):
    p, X = product_matrix(df)
    if X is None:
        p["cluster"] = "Medium"
        p["silhouette"] = np.nan
        return p, None
    try:
        from sklearn.cluster import KMeans
        from sklearn.metrics import silhouette_samples, silhouette_score

        p["k"] = KMeans(n_clusters=N_CLUSTERS, n_init=10, random_state=42).fit_predict(X)
        order = p.groupby("k")["sales"].mean().sort_values(ascending=False).index.tolist()
        names = dict(zip(order, ["High Performing", "Medium", "Low Performing"]))
        p["cluster"] = p["k"].map(names)

        p["silhouette"] = silhouette_samples(X, p["k"])
        score = float(silhouette_score(X, p["k"]))
        return p, score
    except Exception:
        r = p["sales"].rank(pct=True)
        p["cluster"] = np.where(r > 0.66, "High Performing", np.where(r > 0.33, "Medium", "Low Performing"))
        p["silhouette"] = np.nan
        return p, None


def kpi(label, value, sub="", value_color="#1E293B", bar=None):
    bar_html = ""
    if bar is not None:
        bar_html = f'<div class="kpi-bar"><span style="width:{min(bar, 100):.1f}%"></span></div>'
    st.markdown(
        f'<div class="kpi"><div class="kpi-label">{label}</div>'
        f'<div class="kpi-value" style="color:{value_color}">{value}</div>'
        f'{bar_html}<div class="kpi-sub">{sub}</div></div>',
        unsafe_allow_html=True,
    )


# ------------------------------- halaman -----------------------------------
def render():
    layout.page_title("Dashboard Business Intelligence PT X")

    with layout.card("dash_filters", "Filter Dashboard"):
        f = filters.render("dash", inline=True)
    df = load(f)
    if df.empty:
        st.info("Belum ada data untuk filter ini.")
        return

    st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)

    # ------------------------------- KPI -----------------------------------
    months = analysis_months(f, df)

    fs, _ = _filter_dates(f)
    first_data = df["date"].min().to_period("M")
    if fs is not None and first_data > pd.Timestamp(fs).to_period("M"):
        st.warning(
            f"Data baru tersedia mulai {MONTHS[first_data.month - 1]} {first_data.year}, padahal filter dimulai "
            f"{MONTHS[fs.month - 1]} {fs.year}. Bulan sebelumnya dihitung Rp 0 terhadap target. "
            "Cek query/ETL (database/queries.py) kalau datanya seharusnya ada."
        )

    total_sales = df["sales"].sum()
    total_qty = df["qty"].sum()

    sales_by_month = df.groupby(df["date"].dt.to_period("M"))["sales"].sum()
    sales_by_month = sales_by_month.reindex(months.union(sales_by_month.index), fill_value=0).sort_index()
    target_by_month = pd.Series({p: target_of(p) for p in sales_by_month.index}, dtype="float64")
    has_target = target_by_month > 0
    n_months = int(has_target.sum())
    target_total = float(target_by_month.sum())
    avg_target = target_total / n_months if n_months else 0
    sales_vs_target = float(sales_by_month[has_target].sum())
    pct = sales_vs_target / target_total * 100 if target_total else 0

    k1, k2, k3, k4 = st.columns([1.1, 1.5, 1, 1])
    with k1:
        kpi("TOTAL SALES (NETT)", rp(total_sales), f"Periode terpilih (kolom: {df.attrs.get('sales_source', 'sales')})", "#2563EB")
    with k2:
        kpi(
            "PENCAPAIAN TARGET SALES (NOMINAL)",
            f"{pct:.1f}%",
            f"{rp(sales_vs_target)} realisasi / {rp(target_total)} target ({n_months} bulan)",
            "#16A34A" if pct >= 100 else "#F59E0B",
            bar=pct,
        )
    with k3:
        kpi("RATA RATA TARGET / BULAN", rp(avg_target), "Dari bulan yang punya target")
    with k4:
        kpi("TOTAL QUANTITY TERJUAL", f'{n(total_qty)} <span class="kpi-unit">Unit</span>')

    st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)

    # ------------------------------ baris 2 --------------------------------
    c1, c2, c3 = st.columns([1.3, 1.2, 1])

    with c1, layout.card("dash_monthly", "Realisasi vs Target Bulanan"):
        m = sales_by_month.copy()
        labels = [f"{MONTHS[p.month - 1]} {p.year}" for p in m.index]

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=labels, y=m.values, mode="lines+markers",
                                 line=dict(color="#0EA5E9", width=2.5), marker=dict(size=9),
                                 fill="tozeroy", fillcolor="rgba(14,165,233,.10)", name="Realisasi"))

        tp = list(m.index)
        nz = np.flatnonzero(m.values > 0)
        if len(nz) >= 3:
            xs = np.arange(nz[0], len(m))
            a, b = np.polyfit(xs, m.values[nz[0]:], 1)
            fut = [m.index[-1] + i for i in range(1, 4)]
            tp += fut
            fx = [labels[-1]] + [f"{MONTHS[p.month - 1]} {p.year}" for p in fut]
            fy = [m.values[-1]] + [max(a * (len(m) - 1 + i) + b, 0) for i in range(1, 4)]
            fig.add_trace(go.Scatter(x=fx, y=fy, mode="lines",
                                     line=dict(color="#EF4444", width=2, dash="dot"), name="Proyeksi"))

        tl = [f"{MONTHS[p.month - 1]} {p.year}" for p in tp]
        tv = [target_of(p) or None for p in tp]
        fig.add_trace(go.Scatter(x=tl, y=tv, mode="lines+markers", name="Target",
                                 line=dict(color="#94A3B8", width=2, dash="dash"),
                                 marker=dict(size=6, symbol="diamond"), connectgaps=False))
        fig.update_yaxes(showgrid=True, gridcolor="#E2E8F0", tickformat=".2s")
        show(base_layout(fig, 280))

    with c2, layout.card("dash_top5", "Top 5 Produk Terlaris"):
        t = df.groupby("product")["qty"].sum().nlargest(5).sort_values()
        fig = go.Figure(go.Bar(x=t.values, y=t.index, orientation="h", marker_color=BLUE,
                               text=[n(v) for v in t.values], textposition="outside"))
        fig.update_xaxes(visible=False)
        fig.update_layout(bargap=0.35)
        show(base_layout(fig, 280))

    with c3, layout.card("dash_quarter", "Penjualan per Kuartal"):
        q = df.groupby(df["date"].dt.quarter)["qty"].sum().reindex([1, 2, 3, 4]).fillna(0)
        fig = go.Figure(go.Bar(x=["Q1", "Q2", "Q3", "Q4"], y=q.values, marker_color=["#0EA5E9"] * 3 + [BLUE],
                               text=[n(v) for v in q.values], textposition="outside"))
        fig.update_yaxes(showgrid=True, gridcolor="#E2E8F0")
        fig.update_layout(bargap=0.3)
        show(base_layout(fig, 280))

    st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)

    # ------------- tabel target vs realisasi per bulan -------------
    with layout.card("dash_target_table", "Target vs Realisasi per Bulan"):
        real = sales_by_month.values.astype(float)
        targ = target_by_month.values.astype(float)

        def _status(t, r):
            if t == 0:
                return "Tanpa target"
            if r == 0:
                return "Data kosong"
            return "Tercapai" if r >= t else "Belum tercapai"

        tt = pd.DataFrame({
            "Bulan": [f"{MONTHS[p.month - 1]} {p.year}" for p in sales_by_month.index],
            "Target": [rp(v) if v else "-" for v in targ],
            "Realisasi (Net Sales)": [rp(v) for v in real],
            "Pencapaian": [f"{r / t * 100:.1f}%" if t else "-" for t, r in zip(targ, real)],
            "Selisih": [rp(r - t) if t else "-" for t, r in zip(targ, real)],
            "Status": [_status(t, r) for t, r in zip(targ, real)],
        })
        total_row = pd.DataFrame([{
            "Bulan": "TOTAL",
            "Target": rp(target_total),
            "Realisasi (Net Sales)": rp(sales_vs_target),
            "Pencapaian": f"{pct:.1f}%",
            "Selisih": rp(sales_vs_target - target_total),
            "Status": f"{n_months} bulan bertarget",
        }])
        st.dataframe(pd.concat([tt, total_row], ignore_index=True), hide_index=True, width="stretch")
        st.caption(
            "Realisasi = Net Sales (gross - diskon). Status 'Data kosong' berarti dashboard tidak menerima "
            "transaksi pada bulan itu (cek query/ETL), bukan berarti target hilang."
        )

    st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)

    # ------------------------------ baris 3 --------------------------------
    # Ketiga kartu memakai CHART_H dan ROW3_MARGIN yang sama (lewat row3_layout)
    d1, d2, d3 = st.columns([1, 1.4, 1])

    # ---- Marketplace (donut) ----
    with d1, layout.card("dash_mp", "Marketplace"):
        mp = df.groupby("marketplace")["sales"].sum()
        mp_colors_list = [MP_COLORS.get(str(k).strip(), "#94A3B8") for k in mp.index]

        fig = go.Figure(go.Pie(
            labels=mp.index,
            values=mp.values,
            hole=0.55,
            sort=False,
            marker=dict(colors=mp_colors_list),
            textinfo="percent",
            domain=dict(x=[0, 1], y=[0, 1]),
        ))
        show(row3_layout(fig, legend=True, legend_y=0))

    prod, _sil = cluster_products(df)

    # ---- K-Means ----
    with d2, layout.card("dash_cluster", "Pemetaan K-Means Clustering Produk"):
        fig = go.Figure()
        for name, color in CLUSTER_COLORS.items():
            s = prod[prod["cluster"] == name]
            fig.add_trace(go.Scatter(
                x=s["qty"], y=s["profit"], mode="markers",
                name=name.replace(" Performing", ""),  # legend singkat: High / Medium / Low
                text=s["product"],
                hovertemplate=f"<b>{name}</b><br>%{{text}}<br>Qty %{{x}}<br>Profit %{{y:,.0f}}<extra></extra>",
                marker=dict(size=12, color=color),
            ))
        fig.update_xaxes(title="Quantity", title_standoff=6, showgrid=False)
        fig.update_yaxes(title="Gross Profit", showgrid=True, gridcolor="#E2E8F0", tickformat=".2s")
        # legend_y negatif = turun menjauhi sumbu x (ubah -0.22 -> -0.26 bila terlalu dekat)
        show(row3_layout(fig, legend=True, legend_y=-0.22))

    # ---- Bundling ----
    # Judul dipendekkan agar tidak turun ke 2 baris (penyebab kartu ini lebih tinggi dari yang lain)
    with d3, layout.card("dash_bundling", "Bundling / Promo Terlaris"):
        b = df.groupby("bundling")["sales"].sum().nlargest(4)
        short = [(str(k)[:12] + "…") if len(str(k)) > 12 else str(k) for k in b.index]
        fig = go.Figure(go.Bar(
            x=short, y=b.values, marker_color=PURPLE,
            customdata=[str(k) for k in b.index],
            hovertemplate="<b>%{customdata}</b><br>Sales %{y:,.0f}<extra></extra>",
            text=[f"{v / 1e6:,.0f}M" for v in b.values], textposition="outside",
        ))
        fig.update_yaxes(visible=False)
        fig.update_xaxes(tickangle=-20, automargin=False)
        fig.update_layout(bargap=0.35)
        row3_layout(fig, legend=False)
        fig.update_layout(margin=dict(l=40, r=10, t=10, b=70))  # l lebih besar agar label pertama tidak terpotong
        show(fig)

    # Catatan: Silhouette Score sudah dipindah ke halaman Proses ETL
    # (expander "Evaluasi Elbow (SSE), Davies-Bouldin Index, dan Silhouette Score").

    st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)

    # ------------------------------ tabel ----------------------------------
    with layout.card("dash_table", "Rincian Transaksi Penjualan"):
        keyword = st.text_input("Cari", placeholder="Cari nama produk / ID...", key="dash_search", label_visibility="collapsed")
        t = df.merge(prod[["product", "cluster"]], on="product", how="left")
        if keyword:
            kw = keyword.lower()
            t = t[t["product"].astype(str).str.lower().str.contains(kw) | t["id"].astype(str).str.lower().str.contains(kw)]
        t = t.sort_values("date").head(50).reset_index(drop=True)

        cls = {"High Performing": "b-high", "Medium": "b-medium", "Low Performing": "b-low"}
        rows = ""
        for i, r in t.iterrows():
            color = MP_COLORS.get(r["marketplace"], "#94A3B8")
            mp_badge = f'<span class="badge" style="background:{color};color:#fff">{html.escape(str(r["marketplace"]))}</span>'
            cl_badge = f'<span class="badge {cls.get(r["cluster"], "b-very")}">{html.escape(str(r["cluster"]))}</span>'
            rows += (
                f"<tr><td>{i + 1}</td><td>{html.escape(str(r['id']))}</td><td>{r['date']:%Y-%m-%d}</td><td>{mp_badge}</td>"
                f"<td>{html.escape(str(r['product']))}</td><td>{html.escape(str(r['bundling']))}</td>"
                f"<td>{n(r['qty'])}</td><td>{rp(r['sales'])}</td><td>{rp(r['cogs'])}</td><td>{rp(r['profit'])}</td><td>{cl_badge}</td></tr>"
            )
        st.markdown(
            '<div class="table-wrap"><table class="etl-table"><thead><tr><th>No</th><th>ID Transaksi</th><th>Tanggal Kirim</th>'
            "<th>Marketplace</th><th>Nama Produk</th><th>Jenis Promo / Bundling</th><th>Qty</th><th>Total Sales (Rp)</th>"
            f"<th>COGS (Rp)</th><th>Gross Profit (Rp)</th><th>Cluster Kinerja</th></tr></thead><tbody>{rows}</tbody></table></div>",
            unsafe_allow_html=True,
        )