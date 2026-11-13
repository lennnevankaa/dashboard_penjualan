import hmac

import streamlit as st

import config


def is_logged_in():
    return st.session_state.get("logged_in", False)


def current_role():
    return st.session_state.get("role")


def login(username, password):
    user = config.USERS.get(str(username).strip())
    ok = user is not None and hmac.compare_digest(
        str(password).encode("utf-8"), str(user["password"]).encode("utf-8")
    )
    if ok:
        st.session_state["logged_in"] = True
        st.session_state["username"] = str(username).strip()
        st.session_state["role"] = user["role"]
    return ok


def logout():
    st.session_state.clear()


def allowed_pages(all_pages):
    """Daftar halaman (urut sesuai config.ROLE_PAGES) yang boleh dibuka role yang sedang login."""
    keys = config.ROLE_PAGES.get(current_role(), ["dashboard"])
    return [all_pages[k] for k in keys if k in all_pages]