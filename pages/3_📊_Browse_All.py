"""Browse All page: plain table view of every quote.

Per KB_SCAFFOLDING.md §6. Sortable dataframe + CSV download.
"""
from __future__ import annotations

import io

import pandas as pd
import streamlit as st

from lib.auth import render_sidebar_user_box, require_login
from lib.branding import apply_branding
from lib.storage import fetch_all_quotes, get_client

st.set_page_config(
    page_title="Esplora tutti i preventivi · Mobility AI KB",
    page_icon="📊",
    layout="wide",
)

apply_branding()
require_login()


@st.cache_resource(show_spinner=False)
def supabase():
    return get_client()


@st.cache_data(ttl=60, show_spinner=False)
def load_all() -> pd.DataFrame:
    rows = fetch_all_quotes(supabase())
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    # Friendly columns for display + CSV
    return df


st.title("📊 Esplora tutti i preventivi")
st.caption("Vista tabellare dell'intera Knowledge Base. Ordina cliccando le intestazioni.")

df = load_all()

if df.empty:
    st.info("La KB è vuota. Carica un preventivo dalla pagina **Upload** o esegui `db/03_seed.sql`.")
    st.stop()

# Default column order — keep the most useful at the left
preferred = [
    "created_at", "customer_type", "customer_first_name", "customer_last_name",
    "offer_number", "vendor", "vehicle_brand", "vehicle_model", "vehicle_version",
    "vehicle_type", "motorization", "duration_months", "km_total", "km_annual",
    "monthly_fee", "monthly_fee_lease", "monthly_fee_services", "anticipo",
    "list_price", "optional_price", "power_kw", "co2_emissions", "transmission",
    "customer_address_city", "customer_address_province",
    "services_included", "services_excluded",
    "uploaded_by", "parser_version", "pdf_url", "id",
]
ordered = [c for c in preferred if c in df.columns] + [c for c in df.columns if c not in preferred]
df = df[ordered]

# Header metrics
m1, m2, m3, m4 = st.columns(4)
m1.metric("Totale preventivi", len(df))
m2.metric("B2C / B2B", f"{(df['customer_type'] == 'b2c').sum()} / {(df['customer_type'] == 'b2b').sum()}")
m3.metric("Brand distinti", df["vehicle_brand"].nunique())
m4.metric(
    "Canone medio",
    f"{pd.to_numeric(df['monthly_fee'], errors='coerce').mean():.0f} €/mese",
)

st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "created_at":           st.column_config.DatetimeColumn("Caricato il", format="DD/MM/YYYY HH:mm"),
        "customer_type":        st.column_config.TextColumn("Tipo", width="small"),
        "customer_first_name":  "Nome",
        "customer_last_name":   "Cognome",
        "offer_number":         st.column_config.TextColumn("Offerta n°", width="small"),
        "vendor":               st.column_config.TextColumn("Vendor", width="small"),
        "vehicle_brand":        "Brand",
        "vehicle_model":        "Modello",
        "vehicle_version":      "Versione",
        "vehicle_type":         st.column_config.TextColumn("Tipo veicolo", width="small"),
        "motorization":         st.column_config.TextColumn("Motor", width="small"),
        "duration_months":      st.column_config.NumberColumn("Durata (mesi)", format="%d"),
        "km_total":             st.column_config.NumberColumn("Km totali", format="%d"),
        "km_annual":            st.column_config.NumberColumn("Km/anno", format="%d"),
        "monthly_fee":          st.column_config.NumberColumn("Canone", format="%.2f €"),
        "monthly_fee_lease":    st.column_config.NumberColumn("Quota locazione", format="%.2f €"),
        "monthly_fee_services": st.column_config.NumberColumn("Quota servizi", format="%.2f €"),
        "anticipo":             st.column_config.NumberColumn("Anticipo", format="%.0f €"),
        "list_price":           st.column_config.NumberColumn("Listino", format="%.0f €"),
        "optional_price":       st.column_config.NumberColumn("Optional", format="%.0f €"),
        "power_kw":             st.column_config.NumberColumn("kW", format="%d"),
        "co2_emissions":        st.column_config.NumberColumn("CO₂", format="%d"),
        "pdf_url":              st.column_config.LinkColumn("PDF", display_text="Apri 📄"),
    },
)

# --- CSV download
csv_buf = io.StringIO()
df.to_csv(csv_buf, index=False)
st.download_button(
    label="⬇️ Scarica CSV",
    data=csv_buf.getvalue(),
    file_name="quotations.csv",
    mime="text/csv",
    type="primary",
)

render_sidebar_user_box()
