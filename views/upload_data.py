from datetime import datetime

import streamlit as st

import config
from components import layout
from etl import pipeline


def render():
    layout.page_title(config.APP_TITLE)
    with layout.card("upload", "Input Data Penjualan (Upload Berkas Mentah)"):
        file = st.file_uploader(
            "Tarik & Lepas File di Sini (Drag and Drop File)",
            type=[ext.strip(".") for ext in config.ALLOWED_EXT],
            key="uploader",
        )
        auto = st.toggle("Jalankan ETL otomatis setelah upload", value=True)

        if file is not None and st.button("Upload & Proses", type="primary", key="btn_upload"):
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = config.UPLOAD_DIR / f"{stamp}_{file.name}"
            path.write_bytes(file.getvalue())

            try:
                with st.status("Memproses data...", expanded=True) as status:
                    if auto:
                        results = pipeline.run_all(path, on_step=lambda r: st.write(f"✅ {r['message']}"))
                    else:
                        result = pipeline.run_extract(path)
                        st.write(f"✅ {result['message']}")
                        results = [result]
                    status.update(label="Proses selesai", state="complete")
                st.session_state["etl_results"] = {r["step"]: r for r in results}
                st.cache_data.clear()
                if not auto:
                    st.info("Data masuk ke staging. Lanjutkan di menu Proses ETL.")
            except Exception as exc:
                st.error(f"Gagal memproses file: {exc}")