"""Mobility AI — Knowledge Base PoC (Streamlit entry point).

Per KB_SCAFFOLDING.md §6. Login gate runs first; on success the user lands
on this welcome page and uses the sidebar to reach Upload / Search / Browse.
"""
from __future__ import annotations

import streamlit as st

from lib.auth import render_sidebar_user_box, require_login

st.set_page_config(
    page_title="Mobility AI — Knowledge Base",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

require_login()

st.title("Mobility AI — Knowledge Base")
st.caption("Quote intelligence platform per The Hurry")

st.markdown(
    """
    Benvenuta/o nella **Knowledge Base** dei preventivi di noleggio a lungo termine.
    Usa la **sidebar** per:

    - 📤 **Carica** — invia un nuovo preventivo Arval (PDF) e salvalo nella KB.
    - 🔍 **Cerca** — interroga lo storico con filtri strutturati e ottieni
      preventivi simili con un punteggio di affinità (0.00–1.00).
    - 📊 **Esplora tutto** — sfoglia l'intero archivio in tabella.
    """
)

st.info(
    "Le pagine di Upload, Cerca ed Esplora arriveranno nelle Milestone C / E. "
    "Per ora questo è il punto di ingresso e la verifica della connessione Supabase."
)

with st.expander("Stato connessione (debug)"):
    try:
        from lib.storage import fetch_all_quotes, get_client

        client = get_client()
        rows = fetch_all_quotes(client)
        st.success(f"Supabase OK — {len(rows)} preventivi nel database.")
    except Exception as exc:  # noqa: BLE001 — surface any wiring problem
        st.error(f"Supabase non raggiungibile: {exc}")

render_sidebar_user_box()
