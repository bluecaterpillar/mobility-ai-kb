"""Supabase client wrappers (Postgres + Storage) for the Mobility AI KB.

Per KB_SCAFFOLDING.md §6/§10. The Streamlit pages wrap ``get_client``
with ``@st.cache_resource``; CLIs/scripts call it directly.
"""
from __future__ import annotations

import os
from typing import Any, Optional
from uuid import uuid4

from supabase import Client, create_client

DEFAULT_BUCKET = "arval_quotes"


def _get_secrets() -> tuple[str, str, str]:
    """Read Supabase URL/anon key/bucket from st.secrets, falling back to env vars."""
    try:
        import streamlit as st  # noqa: WPS433 — optional dep, only present in app

        url = st.secrets["supabase"]["url"]
        anon_key = st.secrets["supabase"]["anon_key"]
        bucket = st.secrets["supabase"].get("storage_bucket", DEFAULT_BUCKET)
        return url, anon_key, bucket
    except Exception:
        url = os.environ.get("SUPABASE_URL")
        anon_key = os.environ.get("SUPABASE_ANON_KEY")
        bucket = os.environ.get("SUPABASE_BUCKET", DEFAULT_BUCKET)
        if not url or not anon_key:
            raise RuntimeError(
                "Supabase credentials not found. Set [supabase] in "
                ".streamlit/secrets.toml or SUPABASE_URL / SUPABASE_ANON_KEY env vars."
            )
        return url, anon_key, bucket


def get_client() -> Client:
    """Return a fresh Supabase client built from secrets/env."""
    url, anon_key, _ = _get_secrets()
    return create_client(url, anon_key)


def get_bucket_name() -> str:
    """Return the configured storage bucket name."""
    _, _, bucket = _get_secrets()
    return bucket


def upload_pdf(client: Client, file_bytes: bytes, filename: Optional[str] = None) -> str:
    """Upload a PDF to the storage bucket. Returns the object path inside the bucket."""
    bucket = get_bucket_name()
    object_path = filename or f"{uuid4().hex}.pdf"
    client.storage.from_(bucket).upload(
        path=object_path,
        file=file_bytes,
        file_options={"content-type": "application/pdf", "upsert": "false"},
    )
    return object_path


def get_pdf_url(client: Client, storage_path: str) -> str:
    """Return the public URL for an object in the storage bucket."""
    bucket = get_bucket_name()
    return client.storage.from_(bucket).get_public_url(storage_path)


def delete_pdf(client: Client, storage_path: str) -> None:
    """Remove an object from storage. Used to roll back when DB insert fails."""
    bucket = get_bucket_name()
    client.storage.from_(bucket).remove([storage_path])


def insert_quote(client: Client, record: dict[str, Any]) -> dict[str, Any]:
    """Insert a parsed quote into the quotations table. Returns the inserted row."""
    response = client.table("quotations").insert(record).execute()
    return response.data[0] if response.data else {}


def fetch_all_quotes(client: Client) -> list[dict[str, Any]]:
    """Return every quote, newest first."""
    response = (
        client.table("quotations")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return response.data or []


def search_quotes(client: Client, filters: dict[str, Any]) -> list[dict[str, Any]]:
    """Call the search_quotations RPC.

    ``filters`` keys must match the RPC parameter names (with ``p_`` prefix).
    Keys whose value is ``None`` are dropped so the SQL function uses its defaults.
    """
    cleaned = {key: value for key, value in filters.items() if value is not None}
    response = client.rpc("search_quotations", cleaned).execute()
    return response.data or []
