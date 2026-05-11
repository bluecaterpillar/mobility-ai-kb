"""Upload page: PDF → storage → parser → review → save (or rollback).

Per KB_SCAFFOLDING.md §6 + hard constraint #10 (transactional: PDF in
storage + row in DB must both succeed; on DB failure the storage object
is rolled back).
"""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import streamlit as st

from lib.auth import current_username, render_sidebar_user_box, require_login
from lib.branding import apply_branding
from lib.parser import PARSER_VERSION, parse_arval_pdf
from lib.storage import (
    delete_pdf,
    get_client,
    get_pdf_url,
    insert_quote,
    upload_pdf,
)

st.set_page_config(
    page_title="Carica preventivo · Mobility AI KB",
    page_icon="📤",
    layout="wide",
)

apply_branding()
require_login()


@st.cache_resource(show_spinner=False)
def supabase():
    return get_client()


MAX_PDF_BYTES = 50 * 1024 * 1024  # 50 MB hard cap (Claude PDF block limit is 32 MB)
SESSION_KEYS = (
    "upload_parsed",
    "upload_storage_path",
    "upload_pdf_url",
    "upload_filename",
    "upload_persisted",
    "upload_inserted_id",
    "upload_inserted_created_at",
    "upload_uploader_nonce",
)


def _reset(rollback: bool = False) -> None:
    """Wipe upload-flow session state. Optionally remove the orphan PDF first."""
    if rollback:
        path = st.session_state.get("upload_storage_path")
        if path and not st.session_state.get("upload_persisted"):
            try:
                delete_pdf(supabase(), path)
            except Exception:
                pass
    for key in SESSION_KEYS:
        st.session_state.pop(key, None)


def _phase() -> str:
    if st.session_state.get("upload_persisted"):
        return "saved"
    if st.session_state.get("upload_parsed"):
        return "review"
    return "idle"


# ---------------------------------------------------------------- header

st.title("📤 Carica preventivo Arval")
st.caption(
    "Carica un PDF Arval, controlla i campi estratti dal parser, "
    "salva il record nella Knowledge Base."
)

phase = _phase()

# ---------------------------------------------------------------- phase 1

if phase == "idle":
    uploaded = st.file_uploader(
        "Trascina o seleziona un PDF Arval",
        type=["pdf"],
        accept_multiple_files=False,
        help=f"Massimo {MAX_PDF_BYTES // (1024 * 1024)} MB. Solo preventivi Arval (vendor unico in PoC).",
        key=st.session_state.get("upload_uploader_nonce", "uploader_default"),
    )

    if uploaded is not None:
        st.caption(f"📎 **{uploaded.name}** — {uploaded.size / 1024:.1f} KB")

        if uploaded.size > MAX_PDF_BYTES:
            st.error(
                f"File troppo grande ({uploaded.size / 1024 / 1024:.1f} MB). "
                f"Massimo {MAX_PDF_BYTES // (1024 * 1024)} MB."
            )
        elif st.button("🤖 Analizza con Claude", type="primary"):
            pdf_bytes = uploaded.getvalue()
            client = supabase()

            object_path = (
                f"{datetime.utcnow().strftime('%Y/%m')}/{uuid4().hex}.pdf"
            )
            with st.spinner("Caricamento PDF su Supabase Storage…"):
                try:
                    storage_path = upload_pdf(client, pdf_bytes, filename=object_path)
                    pdf_url = get_pdf_url(client, storage_path)
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Caricamento fallito: {exc}")
                    st.stop()

            with st.spinner("Estrazione campi con Claude Haiku 4.5… (3–5 sec)"):
                try:
                    parsed = parse_arval_pdf(pdf_bytes)
                except Exception as exc:  # noqa: BLE001
                    try:
                        delete_pdf(client, storage_path)
                    except Exception:
                        pass
                    st.error(f"Parsing fallito (rollback storage eseguito): {exc}")
                    st.stop()

            if isinstance(parsed, dict) and parsed.get("error") == "not_arval_quote":
                try:
                    delete_pdf(client, storage_path)
                except Exception:
                    pass
                st.error(
                    "⚠️ Questo PDF non sembra un preventivo **Arval**. "
                    "Il file è stato rimosso dallo storage. "
                    "Riprova con un'offerta Arval valida."
                )
                st.stop()

            st.session_state.upload_parsed = parsed
            st.session_state.upload_storage_path = storage_path
            st.session_state.upload_pdf_url = pdf_url
            st.session_state.upload_filename = uploaded.name
            st.rerun()

# ---------------------------------------------------------------- phase 2

elif phase == "review":
    parsed: dict = st.session_state.upload_parsed
    pdf_url: str = st.session_state.upload_pdf_url
    filename: str = st.session_state.upload_filename

    st.success(f"PDF caricato: **{filename}**")
    st.markdown(f"[📄 Apri PDF originale]({pdf_url})")

    # Quick summary so the operator doesn't need to scroll the JSON
    customer = " ".join(
        filter(None, [parsed.get("customer_first_name"), parsed.get("customer_last_name")])
    ) or "—"
    vehicle = " ".join(
        filter(None, [parsed.get("vehicle_brand"), parsed.get("vehicle_model"), parsed.get("vehicle_version")])
    ) or "—"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cliente", customer)
    c2.metric("Veicolo", vehicle)
    c3.metric("Canone", f"{parsed.get('monthly_fee', 0):.2f} €/mese")
    c4.metric("Durata × km", f"{parsed.get('duration_months', '—')} mesi · {parsed.get('km_total', 0):,} km".replace(",", "."))

    st.subheader("Campi estratti (JSON)")
    st.json(parsed)

    st.divider()
    confirm_col, reject_col = st.columns(2)

    if confirm_col.button(
        "✅ Conferma e salva nella KB", type="primary", use_container_width=True
    ):
        client = supabase()

        record = dict(parsed)
        record.pop("error", None)  # safety
        record["vendor"] = "arval"
        record["uploaded_by"] = current_username() or "unknown"
        record["pdf_url"] = pdf_url
        record["parsed_raw_json"] = parsed
        record["parser_version"] = PARSER_VERSION

        try:
            inserted = insert_quote(client, record)
        except Exception as exc:  # noqa: BLE001 — rollback below covers any failure
            try:
                delete_pdf(client, st.session_state.upload_storage_path)
            except Exception:
                pass
            st.error(
                f"Salvataggio nel database fallito (storage rollback eseguito): {exc}"
            )
            st.stop()

        st.session_state.upload_persisted = True
        st.session_state.upload_inserted_id = inserted.get("id")
        st.session_state.upload_inserted_created_at = inserted.get("created_at")
        st.toast("Preventivo salvato nella KB ✅", icon="✅")
        st.rerun()

    if reject_col.button("🗑️ Scarta e ricomincia", use_container_width=True):
        _reset(rollback=True)
        st.session_state.upload_uploader_nonce = uuid4().hex  # force re-mount of file_uploader
        st.rerun()

# ---------------------------------------------------------------- phase 3

elif phase == "saved":
    st.success("✅ Preventivo salvato nella Knowledge Base.")

    parsed = st.session_state.get("upload_parsed", {})
    inserted_id = st.session_state.get("upload_inserted_id")
    pdf_url = st.session_state.get("upload_pdf_url")
    created_at = st.session_state.get("upload_inserted_created_at")

    def _fmt_created(value):
        if not value:
            return "—"
        if isinstance(value, datetime):
            return value.strftime("%d/%m/%Y %H:%M")
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00")).strftime("%d/%m/%Y %H:%M")
        except Exception:
            return str(value)

    info_cols = st.columns(2)
    with info_cols[0]:
        if inserted_id:
            st.markdown(f"**ID record:** `{inserted_id}`")
        st.markdown(f"**Offerta:** {parsed.get('offer_number', '—')}")
        st.markdown(
            f"**Cliente:** {parsed.get('customer_first_name', '')} "
            f"{parsed.get('customer_last_name', '')}"
        )
        st.markdown(f"**Data preventivo:** {_fmt_created(created_at)}")
    with info_cols[1]:
        st.markdown(
            f"**Veicolo:** {parsed.get('vehicle_brand', '')} "
            f"{parsed.get('vehicle_model', '')}"
        )
        st.markdown(f"**Canone:** {parsed.get('monthly_fee', 0):.2f} €/mese")
        if pdf_url:
            st.markdown(f"[📄 Apri PDF]({pdf_url})")

    st.divider()
    if st.button("📤 Carica un altro preventivo", type="primary"):
        _reset(rollback=False)
        st.session_state.upload_uploader_nonce = uuid4().hex
        st.rerun()

render_sidebar_user_box()
