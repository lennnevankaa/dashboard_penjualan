import streamlit as st

from components import layout
from services import auth


def render():
    _, center, _ = st.columns([1.2, 1, 1.2])
    with center:
        st.markdown("<div style='height:12vh'></div>", unsafe_allow_html=True)
        with layout.card("login"):
            st.markdown("<h2 class='login-title'> BI Sales Dashboard</h2>", unsafe_allow_html=True)
            st.markdown("<p class='login-sub'>Dashboard Business Intelligence PT X</p>", unsafe_allow_html=True)
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Masuk", type="primary", width="stretch")
            if submitted:
                if auth.login(username, password):
                    st.rerun()
                else:
                    st.error("Username atau password salah")