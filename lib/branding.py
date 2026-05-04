"""Brand identity helpers — The Hurry logo + colors.

Streamlit's ``st.logo`` must be called once per page; the wrapper here keeps
the path resolution and the link in one place.
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

LOGO_PATH = str(Path(__file__).resolve().parent.parent / "assets" / "hurry_logo.svg")
HURRY_URL = "https://www.the-hurry.com/"

# Brand palette (mirrored in .streamlit/config.toml — keep in sync)
PRIMARY = "#710B41"   # Hurry maroon
DARK = "#4B072B"      # darker accent for hovers / shadows
ACCENT = "#F5EFF2"    # very light pink, used as soft surface


def apply_branding() -> None:
    """Render the Hurry logo at the top of the sidebar / page header.

    Idempotent — call this from every page (entry script + pages/*).
    """
    st.logo(LOGO_PATH, link=HURRY_URL, size="large")


def render_login_hero() -> None:
    """Centred wordmark above the login form."""
    svg = Path(LOGO_PATH).read_text()
    st.markdown(
        f"""
        <div style="display:flex;justify-content:center;margin:1.5rem 0 0.5rem;">
            <div style="width:140px;">{svg}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
