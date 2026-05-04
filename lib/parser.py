"""Arval quote PDF -> structured JSON via Claude Haiku 4.5.

Per KB_SCAFFOLDING.md §5. Sends the PDF directly as a `document` content
block; no pdfplumber, no OCR, no regex.
"""
from __future__ import annotations

import base64
import json
import os
import re
from pathlib import Path
from typing import Any, Optional

import anthropic

PARSER_MODEL = "claude-haiku-4-5-20251001"
PARSER_VERSION = "claude-haiku-4-5-v1"

PARSER_SYSTEM_PROMPT = """You are an extraction agent for Italian long-term car rental quotes (NLT) from Arval. You receive an Arval quote PDF and return a single JSON object with the extracted fields. Return ONLY the JSON, no preamble, no markdown fences."""

PARSER_USER_PROMPT = """Extract the following fields from this Arval quote and return as JSON.

Required JSON schema:
{
  "offer_number": "string e.g. 15789678/1",
  "customer_code": "string e.g. N98926",
  "customer_type": "b2c | b2b",
  "customer_first_name": "string",
  "customer_last_name": "string",
  "customer_fiscal_code": "string",
  "customer_birth_date": "YYYY-MM-DD or null",
  "customer_gender": "M | F | null",
  "customer_birth_place": "string or null",
  "customer_address_city": "string or null",
  "customer_address_province": "string (2-letter) or null",
  "customer_address_cap": "string or null",
  "vehicle_brand": "string e.g. BYD",
  "vehicle_model": "string e.g. SEAL U DM-i",
  "vehicle_version": "string e.g. 1.5 324cv Design",
  "vehicle_year": integer or null,
  "vehicle_type": "city_car | berlina | sw | suv | crossover | monovolume | commercial",
  "motorization": "benzina | diesel | elettrico | hybrid_benzina | hybrid_diesel | phev | gpl | metano",
  "power_kw": integer,
  "co2_emissions": integer,
  "transmission": "manuale | automatico",
  "list_price": number (EUR including VAT),
  "optional_price": number (EUR including VAT, 0 if none),
  "duration_months": integer,
  "km_total": integer,
  "monthly_fee": number,
  "monthly_fee_lease": number,
  "monthly_fee_services": number,
  "anticipo": number (0 if none),
  "deposito": number or null,
  "services_included": [array of strings from: manutenzione, rca, soccorso_stradale, infortunio_conducente, kasko, pneumatici, veicolo_sostitutivo],
  "services_excluded": [array of strings, same enum]
}

Rules:
- All monetary values are in EUR with VAT included.
- vehicle_type: SUV → "suv", station wagon → "sw", etc. Use your judgment based on the model.
- If the PDF is not an Arval quote, return: {"error": "not_arval_quote"}
- If a field is genuinely missing, use null. Do not invent values.
- Return ONLY the JSON object, nothing else."""


def _resolve_api_key(api_key: Optional[str] = None) -> str:
    """Pick up the API key from the explicit arg, st.secrets, or env."""
    if api_key:
        return api_key
    try:
        import streamlit as st  # noqa: WPS433 — optional dep, only present in app

        return st.secrets["anthropic"]["api_key"]
    except Exception:
        env_key = os.environ.get("ANTHROPIC_API_KEY")
        if not env_key:
            raise RuntimeError(
                "Anthropic API key not found. Set [anthropic].api_key in "
                ".streamlit/secrets.toml or the ANTHROPIC_API_KEY environment variable."
            )
        return env_key


def parse_arval_pdf(pdf_bytes: bytes, api_key: Optional[str] = None) -> dict[str, Any]:
    """Send a PDF to Claude Haiku 4.5 and return the parsed JSON dict.

    Returns ``{"error": "not_arval_quote"}`` if the document isn't recognised.
    Raises ``json.JSONDecodeError`` if the model returns malformed JSON,
    or ``anthropic.APIError`` for transport-level failures.
    """
    client = anthropic.Anthropic(api_key=_resolve_api_key(api_key))
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")

    response = client.messages.create(
        model=PARSER_MODEL,
        max_tokens=2000,
        system=PARSER_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_b64,
                        },
                    },
                    {"type": "text", "text": PARSER_USER_PROMPT},
                ],
            }
        ],
    )

    raw_text = response.content[0].text.strip()
    # Strip optional code fences if the model added them despite instructions.
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
    parsed = json.loads(raw_text.strip())

    # Normalize offer_number: the model occasionally emits "15789678 / 1"
    # (matching the visual layout of the PDF cell) instead of "15789678/1".
    # Treat the canonical form as no-spaces so deduplication works.
    if isinstance(parsed, dict) and isinstance(parsed.get("offer_number"), str):
        parsed["offer_number"] = re.sub(r"\s*/\s*", "/", parsed["offer_number"]).strip()

    return parsed


def parse_arval_pdf_file(pdf_path: str | Path, api_key: Optional[str] = None) -> dict[str, Any]:
    """Convenience wrapper for CLIs and scripts."""
    return parse_arval_pdf(Path(pdf_path).read_bytes(), api_key=api_key)
