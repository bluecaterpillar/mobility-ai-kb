"""Mocked authentication: hardcoded credentials in session state.

Per KB_SCAFFOLDING.md §6 / hard constraint #3. No real auth library.
"""
from __future__ import annotations

import streamlit as st

MOCK_USERS: dict[str, str] = {
    "demo.thehurry": "demo2026",
    "carlo.galati": "thehurry",
    "gabriele.lambiase": "thehurry",
}


def is_logged_in() -> bool:
    return bool(st.session_state.get("logged_in"))


def current_username() -> str | None:
    return st.session_state.get("username")


def logout() -> None:
    """Clear the session and force a rerun back to the login form."""
    for key in ("logged_in", "username"):
        st.session_state.pop(key, None)
    st.rerun()


def login_form() -> None:
    """Render the login form. On success, sets session state and reruns."""
    st.title("Mobility AI — Login")
    st.caption("Knowledge Base demo per The Hurry")

    with st.form("login"):
        username = st.text_input("Utenza", value="demo.thehurry")
        password = st.text_input("Password", type="password", value="demo2026")
        submitted = st.form_submit_button("Accedi", type="primary")

        if submitted:
            if MOCK_USERS.get(username) == password:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.rerun()
            else:
                st.error("Credenziali non valide")


def require_login() -> None:
    """Gate any page: if not logged in, show the form and stop the script."""
    if not is_logged_in():
        login_form()
        st.stop()


def render_sidebar_user_box() -> None:
    """Small footer in the sidebar with username + logout."""
    with st.sidebar:
        st.divider()
        st.caption(f"Connesso come: **{current_username()}**")
        if st.button("Esci", use_container_width=True):
            logout()
