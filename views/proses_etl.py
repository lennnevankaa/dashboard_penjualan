import html

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import config
from clustering import evaluation as ev
from components import charts, layout
from database import queries
from etl import pipeline
from services.formatting import num, rp

BADGE = {
    "High Performing": "b-high",
    "Medium Performing": "b-medium",
    "Low Performing": "b-low",
    "Very Low Performing": "b-very",
}
STEP_ORDER = ("extract", "transform", "load", "clustering")
ALGO_COLORS = ["#8DB3D1", "#6A9AC0", "#4A86B5", "#3F6A8C", "#3A4B5A"]

# Kolom fitur clustering (nama pertama yang ditemukan dipakai)
FEATURE_CANDIDATES = [
    ["total_qty", "qty", "quantity", "total_quantity"],
    ["total_sales", "sales", "net_sales"],
    ["total_disc", "diskon", "discount", "total_diskon"],
]


def _store(results):
    stored = st.session_state.setdefault("etl_results", {})
    for result in results:
        stored[result["step"]] = result


def _run_step(step):
    try:
        with st.spinner("Memproses..."):
            if step == "extract":
                path = pipeline.latest_upload()
                if path is None:
                    st.warning("Belum ada file. Upload dulu di menu Input Data.")
                    return
                results = [pipeline.run_extract(path)]
            elif step == "transform":
                results = [pipeline.run_transform()]
            else:
                results = [pipeline.run_load(), pipeline.run_clustering()]
        _store(results)
        st.cache_data.clear()
    except Exception as exc:
        st.error(f"Gagal: {exc}")


def _run_all():
    path = pipeline.latest_upload()
    if path is None:
        st.warning("Belum ada file. Upload dulu di menu Input Data.")
        return
    try:
        with st.status("Menjalankan ETL...", expanded=True) as status:
            results = pipeline.run_all(path, on_step=lambda r: st.write(f"✅ {r['message']}"))
            status.update(label="ETL selesai", state="complete")
        _store(results)
        st.cache_data.clear()
    except Exception as exc:
        st.error(f"Gagal: {exc}")


def _table(df):
    rows = ""
    for r in df.itertuples():
        css = BADGE.get(r.cluster_label, "b-very")
        rows += (
            f"<tr><td>{html.escape(str(r.sku_code))}</td><td>{r.last_delivery_date}</td>"
            f"<td>{rp(r.total_sales)}</td><td>{rp(r.total_disc)}</td>"
            f"<td><span class='badge {css}'>{html.escape(r.cluster_label)}</span></td></tr>"
        )
    return (
        "<table class='etl-table'><thead><tr><th>Product SKU</th><th>Closest Date</th>"
        "<th>Calculated Sales</th><th>Diskon (Rp)</th><th>Cluster Result</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )


def _feature_matrix(clusters):
    """Bentuk matriks fitur (Min-Max) dari hasil clustering. Return (X, kolom_dipakai) atau (None, [])."""
    cols = []
    for names in FEATURE_CANDIDATES:
        found = next((c for c in names if c in clusters.columns), None)
        if found:
            cols.append(found)
    if len(cols) < 2:
        return None, []
    try:
        from sklearn.preprocessing import MinMaxScaler

        data = clusters[cols].apply(pd.to_numeric, errors="coerce").fillna(0)
        return MinMaxScaler().fit_transform(data), cols
    except Exception:
        return None, []


def _silhouette_section(clusters):
    st.markdown("---")
    st.markdown("**Silhouette Score**")

    if clusters.empty or "cluster_label" not in clusters.columns:
        st.caption("Silhouette Score belum bisa dihitung. Jalankan ETL terlebih dahulu.")
        return

    X, cols = _feature_matrix(clusters)
    if X is None:
        st.caption("Silhouette Score belum bisa dihitung (kolom fitur qty/sales/diskon tidak ditemukan).")
        return

    labels = clusters["cluster_label"].astype(str).to_numpy()
    score = ev.silhouette_overall(X, labels)
    if score is None:
        st.caption("Silhouette Score belum bisa dihitung (minimal 2 klaster dan data lebih banyak dari jumlah klaster).")
        return

    ket, warna = ev.silhouette_label(score)
    st.markdown(
        f'<div style="text-align:center;font-size:.95rem;margin:.4rem 0 .6rem">'
        f'Silhouette Score K-Means: <b style="color:{warna}">{score:.3f}</b> ({ket})</div>',
        unsafe_allow_html=True,
    )
    st.caption(f"Fitur: {', '.join(cols)} (Min-Max). Skor makin mendekati 1 makin baik.")

    # ---- detail per produk ----
    with st.expander("Detail Silhouette per produk"):
        detail = pd.DataFrame({
            "Produk": clusters["sku_code"].astype(str).to_numpy(),
            "Klaster": labels,
            "s(i)": ev.silhouette_per_sample(X, labels),
        }).sort_values(["Klaster", "s(i)"], ascending=[True, False])
        st.dataframe(detail.round(4), hide_index=True, width="stretch")

    # ---- perbandingan antar algoritma ----
    st.markdown("**Silhouette Score Comparison**")
    cmp = ev.compare_algorithms(X)
    if cmp is None:
        st.caption("Perbandingan belum bisa dihitung (data terlalu sedikit).")
        return

    col_a, col_b = st.columns([1.7, 1])
    with col_a:
        vals = cmp["Silhouette"].fillna(0).tolist()
        texts = [f"{v:.3f}" if pd.notna(s) else "n/a" for v, s in zip(vals, cmp["Silhouette"])]
        fig = go.Figure(go.Bar(
            x=cmp["Algoritma"], y=vals, width=0.5,
            marker=dict(color=ALGO_COLORS[: len(cmp)]),
            text=texts, textposition="inside", insidetextanchor="middle",
            textfont=dict(color="white", size=14),
            hovertemplate="%{x}<br>Silhouette: %{text}<extra></extra>",
        ))
        fig.update_yaxes(title="Silhouette Score", showgrid=True, gridcolor="#D1D5DB",
                         range=[0, max(0.8, max(vals) + 0.1)])
        fig.update_xaxes(showgrid=False)
        fig.update_layout(
            height=320, margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(size=12, color="#334155"), showlegend=False,
        )
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    with col_b:
        tbl = cmp.copy()
        tbl["Silhouette"] = tbl["Silhouette"].map(lambda v: "-" if pd.isna(v) else f"{v:.3f}")
        st.dataframe(tbl, hide_index=True, width="stretch")
        best = cmp.dropna(subset=["Silhouette"])
        if not best.empty:
            top = best.loc[best["Silhouette"].idxmax()]
            st.caption(
                f"Skor tertinggi: {top['Algoritma']} ({top['Silhouette']:.3f}). "
                "Pada DBSCAN, titik noise tidak ikut dihitung. Skor tinggi dengan sedikit klaster "
                "belum tentu lebih baik, cek kolom Jumlah Klaster."
            )


def render():
    layout.page_title(config.APP_TITLE)

    with layout.card("etl", "Pemrosesan ETL Data Mart"):
        if st.button("Jalankan Seluruh ETL Otomatis", type="primary", key="btn_all"):
            _run_all()

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("1. EXTRACT", key="btn_extract", width="stretch"):
                _run_step("extract")
            st.markdown("<div class='etl-desc'>Ambil data mentah dari file upload terakhir ke tabel staging stg_sales.</div>", unsafe_allow_html=True)
        with c2:
            if st.button("2. TRANSFORM", key="btn_transform", width="stretch"):
                _run_step("transform")
            st.markdown("<div class='etl-desc'>Bersihkan data, ubah tipe data, hapus duplikat, hitung sales dan cogs.</div>", unsafe_allow_html=True)
        with c3:
            if st.button("3. LOAD", key="btn_load", width="stretch"):
                _run_step("load")
            st.markdown("<div class='etl-desc'>Muat dim_* lebih dulu, lalu fact_sales, kemudian clustering K-Means.</div>", unsafe_allow_html=True)

        try:
            counts = queries.etl_counts()
            c1.markdown(f"<div class='etl-count'>Staging: {num(counts['staging'])} baris</div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='etl-count'>Data bersih: {num(counts['clean'])} baris</div>", unsafe_allow_html=True)
            c3.markdown(f"<div class='etl-count'>fact_sales: {num(counts['fact'])} baris</div>", unsafe_allow_html=True)
        except Exception:
            pass

        stored = st.session_state.get("etl_results", {})
        for step in STEP_ORDER:
            if step in stored:
                st.success(f"{stored[step]['message']} ({stored[step]['seconds']} dtk)")

    clusters = queries.cluster_data()

    with layout.card("etl_result", "Hasil Transformed & Clustering K-Means"):
        if clusters.empty:
            st.info("Belum ada hasil clustering. Jalankan ETL terlebih dahulu.")
        else:
            st.caption("Hasil pengelompokan produk berdasarkan kuantitas, sales, dan diskon (Min-Max + K-Means).")
            st.markdown(_table(clusters.head(50)), unsafe_allow_html=True)

    evaluation = queries.cluster_evaluation()
    if not evaluation.empty or not clusters.empty:
        with st.expander("Evaluasi Elbow (SSE), Davies-Bouldin Index, dan Silhouette Score"):
            if not evaluation.empty:
                e1, e2 = st.columns(2)
                with e1:
                    st.caption("Elbow Method: SSE per K")
                    charts.show(charts.elbow(evaluation))
                with e2:
                    st.caption("Davies-Bouldin Index per K (makin kecil makin baik)")
                    charts.show(charts.dbi(evaluation))
                st.dataframe(evaluation, hide_index=True, width="stretch")

            _silhouette_section(clusters)