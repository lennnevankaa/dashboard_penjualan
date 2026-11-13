from textwrap import dedent

import streamlit as st

from components import layout
from services import auth


def render():
    brand, form_column = st.columns([1.1, 0.9], gap="large")
    with brand:
        with st.container(key="login_hero"):
            st.markdown(
                dedent("""
                <div class="login-brand-copy">
                  <div class="login-brand-tag">BUSINESS INTELLIGENCE</div>
                  <h1 class="login-brand-title">BI Sales Dashboard</h1>
                  <p class="login-brand-description">
                    Pantau performa penjualan dan temukan insight bisnis dalam satu tampilan.
                  </p>
                </div>
                <div class="login-illustration">
                  <svg viewBox="0 0 560 330" role="img" aria-label="Ilustrasi grafik penjualan">
                    <defs>
                      <linearGradient id="chart-bg" x1="0" y1="0" x2="1" y2="1">
                        <stop offset="0" stop-color="#FFFFFF" stop-opacity=".2"/>
                        <stop offset="1" stop-color="#C7D2FE" stop-opacity=".08"/>
                      </linearGradient>
                      <linearGradient id="chart-line" x1="0" y1="0" x2="1" y2="0">
                        <stop offset="0" stop-color="#A5B4FC"/>
                        <stop offset="1" stop-color="#67E8F9"/>
                      </linearGradient>
                    </defs>
                    <circle cx="470" cy="72" r="52" fill="#A5B4FC" opacity=".14"/>
                    <circle cx="76" cy="272" r="74" fill="#67E8F9" opacity=".12"/>
                    <rect x="38" y="27" width="484" height="276" rx="24" fill="url(#chart-bg)" stroke="#FFFFFF" stroke-opacity=".3"/>
                    <rect x="66" y="54" width="428" height="220" rx="15" fill="#111B37" fill-opacity=".72"/>
                    <rect x="91" y="77" width="112" height="9" rx="4.5" fill="#FFFFFF" opacity=".84"/>
                    <rect x="91" y="94" width="72" height="6" rx="3" fill="#C7D2FE" opacity=".55"/>
                    <path d="M92 232H468M92 191H468M92 150H468" stroke="#FFFFFF" stroke-opacity=".12"/>
                    <rect x="116" y="194" width="36" height="38" rx="7" fill="#818CF8"/>
                    <rect x="174" y="169" width="36" height="63" rx="7" fill="#818CF8"/>
                    <rect x="232" y="180" width="36" height="52" rx="7" fill="#818CF8"/>
                    <rect x="290" y="137" width="36" height="95" rx="7" fill="#818CF8"/>
                    <rect x="348" y="121" width="36" height="111" rx="7" fill="#818CF8"/>
                    <rect x="406" y="99" width="36" height="133" rx="7" fill="#67E8F9"/>
                    <path d="M134 174L192 151L250 159L308 126L366 109L424 86" fill="none" stroke="url(#chart-line)" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
                    <circle cx="424" cy="86" r="7" fill="#67E8F9" stroke="#FFFFFF" stroke-width="3"/>
                  </svg>
                </div>
                <div class="login-brand-footer">
                  <span class="login-brand-dot"></span>
                  Dashboard analitik penjualan PT X
                </div>
                """),
                unsafe_allow_html=True,
            )

    with form_column:
        with layout.card("login"):
            st.markdown("<div class='login-kicker'>AKSES DASHBOARD</div>", unsafe_allow_html=True)
            st.markdown("<h2 class='login-title'>Selamat datang</h2>", unsafe_allow_html=True)
            st.markdown("<p class='login-sub'>Masuk dengan akun yang telah terdaftar.</p>", unsafe_allow_html=True)
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Masuk", type="primary", width="stretch")
            if submitted:
                if auth.login(username, password):
                    st.rerun()
                else:
                    st.error("Username atau password salah")