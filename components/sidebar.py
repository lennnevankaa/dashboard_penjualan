import streamlit as st

from services import auth


def render(pages):
    with st.sidebar:
        st.markdown("<div class='side-brand'>📊 BI Sales Dashboard</div>", unsafe_allow_html=True)
        for page in pages:
            st.page_link(page)
        st.markdown("<div class='side-spacer'></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='side-user'>Login sebagai {st.session_state.get('username', '')}</div>", unsafe_allow_html=True)
        if st.button("Logout", key="logout_btn", width="stretch"):
            auth.logout()
            st.rerun()