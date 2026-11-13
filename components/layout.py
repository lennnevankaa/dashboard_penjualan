from pathlib import Path

import streamlit as st

CSS_FILE = Path(__file__).resolve().parent.parent / "assets" / "style.css"


def inject_css():
    st.markdown(f"<style>{CSS_FILE.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def hide_sidebar():
    st.markdown(
        "<style>[data-testid='stSidebar'],[data-testid='stSidebarCollapsedControl']{display:none}</style>",
        unsafe_allow_html=True,
    )


def page_title(text):
    st.markdown(f"<h1 class='page-title'>{text}</h1>", unsafe_allow_html=True)


def card(key, title=None):
    container = st.container(key=f"card_{key}")
    if title:
        container.markdown(f"<div class='card-title'>{title}</div>", unsafe_allow_html=True)
    return container