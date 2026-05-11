"""Search page: structured filters → ranked results.

Per KB_SCAFFOLDING.md §6. Calls the search_quotations RPC; for multi-value
categorical filters (vehicle_type, motorization) it runs the RPC over the
cartesian product and merges by row id, keeping the highest score per row.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Iterable, Optional

import pandas as pd
import streamlit as st

from lib.auth import render_sidebar_user_box, require_login
from lib.branding import apply_branding
from lib.storage import get_client, search_quotes

st.set_page_config(
    page_title="Cerca preventivi · Mobility AI KB",
    page_icon="🔍",
    layout="wide",
)

apply_branding()
require_login()


@st.cache_resource(show_spinner=False)
def supabase():
    return get_client()


VEHICLE_TYPES = ["city_car", "berlina", "sw", "suv", "crossover", "monovolume", "commercial"]
MOTORIZATIONS = [
    "benzina", "diesel", "elettrico",
    "hybrid_benzina", "hybrid_diesel", "phev", "gpl", "metano",
]
DURATIONS = [24, 36, 48, 60]


@st.cache_data(ttl=300, show_spinner=False)
def fetch_brands() -> list[str]:
    """Distinct vehicle_brand values, alphabetical, used as autocomplete options."""
    rows = supabase().table("quotations").select("vehicle_brand").execute().data or []
    return sorted({r["vehicle_brand"] for r in rows if r.get("vehicle_brand")})


def _none_if_empty(value: Any) -> Any:
    if value in (None, "", 0, 0.0, [], "Qualsiasi"):
        return None
    return value


@st.cache_data(ttl=60, show_spinner=False)
def cached_search(filters_json: str) -> list[dict[str, Any]]:
    """Run the search; multi-call when vehicle_type / motorization are multi-valued.

    Cache key is the JSON-stringified filters so identical re-submissions hit cache.
    """
    filters = json.loads(filters_json)
    base = {k: v for k, v in filters.items() if k not in {"_vehicle_types", "_motorizations"}}
    vts: list[Optional[str]] = filters.get("_vehicle_types") or [None]
    mts: list[Optional[str]] = filters.get("_motorizations") or [None]

    client = supabase()
    by_id: dict[str, dict[str, Any]] = {}
    for vt in vts:
        for mt in mts:
            call_filters = dict(base)
            call_filters["p_vehicle_type"] = vt
            call_filters["p_motorization"] = mt
            for row in search_quotes(client, call_filters):
                rid = row["id"]
                # Keep the variant where this row scored highest
                if rid not in by_id or float(row["score"] or 0) > float(by_id[rid]["score"] or 0):
                    by_id[rid] = row
    merged = sorted(by_id.values(), key=lambda r: -float(r["score"] or 0))
    return merged[: int(base.get("p_limit", 10))]


def _score_emoji(score: float | None) -> str:
    if score is None:
        return "—"
    s = float(score)
    if s >= 0.80:
        return "🟢"
    if s >= 0.50:
        return "🟡"
    return "⚪"


def _format_breakdown(breakdown: dict[str, Any] | None) -> pd.DataFrame:
    """Compact per-feature score table: feature, peso, score.

    Includes the recency feature added in 2026-05 (weight 0.10, always active
    because every row has a created_at).
    """
    if not breakdown:
        return pd.DataFrame()
    weights = {
        "fee": 0.30, "duration": 0.15, "km": 0.15, "vehicle_type": 0.15,
        "vehicle_brand": 0.10, "anticipo": 0.10, "recency": 0.10, "motorization": 0.05,
    }
    labels = {
        "fee": "Canone",
        "duration": "Durata",
        "km": "Km totali",
        "vehicle_type": "Tipo veicolo",
        "vehicle_brand": "Brand",
        "anticipo": "Anticipo",
        "motorization": "Motorizzazione",
        "recency": "Recency",
    }
    rows = []
    for k, w in weights.items():
        v = breakdown.get(k)
        rows.append({
            "Feature": labels[k],
            "Peso": f"{int(w * 100)} %",
            "Score": "—" if v is None else f"{float(v):.3f}",
        })
    return pd.DataFrame(rows)


def _parse_created_at(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    # Supabase returns ISO 8601 with timezone, e.g. "2026-04-05T09:14:00+00:00"
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _format_date(value: Any, *, with_time: bool = False) -> str:
    dt = _parse_created_at(value)
    if not dt:
        return "—"
    return dt.strftime("%d/%m/%Y %H:%M" if with_time else "%d/%m/%Y")


# ---------------------------------------------------------------- header

st.title("🔍 Cerca nella Knowledge Base")
st.caption(
    "Imposta i target e i filtri categorici. Lo score (0.00–1.00) misura la "
    "vicinanza pesata; ≥ 0.80 = match forte 🟢, 0.50–0.79 = simile 🟡, < 0.50 = debole ⚪. "
    "**A parità di match il preventivo più recente vince** (peso recency 10%, decadimento lineare su 24 mesi)."
)

# ---------------------------------------------------------------- form

with st.form("search"):
    c1, c2, c3, c4 = st.columns(4)
    customer_type = c1.selectbox(
        "Tipo cliente",
        ["Qualsiasi", "b2c", "b2b"],
        format_func=lambda v: v.upper() if v in ("b2c", "b2b") else v,
    )
    duration_opt = c2.selectbox(
        "Durata target (mesi)",
        ["Qualsiasi", *DURATIONS],
        format_func=lambda v: f"{v} mesi" if isinstance(v, int) else v,
    )
    target_fee = c3.number_input(
        "Canone target (€/mese)", min_value=0.0, value=None, step=10.0,
        placeholder="es. 650",
    )
    target_anticipo = c4.number_input(
        "Anticipo target (€)", min_value=0.0, value=None, step=500.0,
        placeholder="es. 6000",
    )

    c5, c6, c7, c8 = st.columns(4)
    target_km = c5.number_input(
        "Km totali target", min_value=0, value=None, step=10000,
        placeholder="es. 100000",
    )
    vehicle_types = c6.multiselect("Tipo veicolo", VEHICLE_TYPES)
    brand_options = ["Qualsiasi", *fetch_brands()]
    brand = c7.selectbox(
        "Brand",
        brand_options,
        help="Solo i brand già presenti nella KB sono selezionabili.",
    )
    motorizations = c8.multiselect("Motorizzazione", MOTORIZATIONS)

    c9, c10, c11 = st.columns([2, 1, 1])
    min_score = c9.slider("Score minimo", 0.0, 1.0, 0.50, 0.05)
    limit = c10.number_input("Risultati max", min_value=1, max_value=50, value=10)
    submit = c11.form_submit_button("🔎 Cerca", type="primary", use_container_width=True)


# ---------------------------------------------------------------- submit

if submit:
    base_filters: dict[str, Any] = {
        "p_vendor": "arval",
        "p_customer_type": _none_if_empty(customer_type),
        "p_target_monthly_fee": _none_if_empty(target_fee),
        "p_target_duration_months": _none_if_empty(duration_opt),
        "p_target_km_total": _none_if_empty(target_km),
        "p_target_anticipo": _none_if_empty(target_anticipo),
        "p_vehicle_brand": _none_if_empty(brand),
        "p_min_score": float(min_score),
        "p_limit": int(limit),
        # categorical multi-values handled outside the RPC params
        "_vehicle_types": list(vehicle_types) if vehicle_types else None,
        "_motorizations": list(motorizations) if motorizations else None,
    }

    # The RPC's score is a weighted average over the *active* features only.
    # If the user has neither targets nor categorical filters, every row has
    # final_score = NULL and nothing comes back. Catch that early.
    has_targets = any(
        base_filters[k] is not None
        for k in (
            "p_target_monthly_fee", "p_target_duration_months",
            "p_target_km_total", "p_target_anticipo",
        )
    )
    has_categoricals = (
        base_filters["_vehicle_types"]
        or base_filters["_motorizations"]
        or base_filters["p_vehicle_brand"]
    )
    # With the recency factor always active (weight 0.10 on every row), the
    # search is meaningful even without explicit filters — it falls back to a
    # "most recent quotes first" feed. We still show a hint so the operator
    # knows what they're getting.
    if not (has_targets or has_categoricals):
        st.caption(
            "ℹ️ Nessun filtro impostato → ranking solo per **data più recente**."
        )

    with st.spinner("Interrogo la KB…"):
        results = cached_search(json.dumps(base_filters, default=str, sort_keys=True))

    st.divider()
    if not results:
        st.info(
            "Nessun preventivo sopra lo score minimo. "
            "Prova ad abbassare la soglia o allargare i filtri."
        )
    else:
        st.subheader(f"Risultati ({len(results)})")

        # --- summary table with color-coded score + date column
        summary = pd.DataFrame([
            {
                "Match": _score_emoji(r["score"]),
                "Score": float(r["score"] or 0),
                "Data": _parse_created_at(r.get("created_at")),
                "Cliente": r["customer_full_name"],
                "Veicolo": r["vehicle_full_name"],
                "Tipo": r["vehicle_type"],
                "Motor": r["motorization"],
                "Canone €/mese": float(r["monthly_fee"] or 0),
                "Durata": int(r["duration_months"] or 0),
                "Km": int(r["km_total"] or 0),
                "Anticipo €": float(r["anticipo"] or 0),
            }
            for r in results
        ])

        st.dataframe(
            summary,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Match": st.column_config.TextColumn("", width="small"),
                "Score": st.column_config.ProgressColumn(
                    "Score", min_value=0.0, max_value=1.0, format="%.3f", width="small",
                ),
                "Data": st.column_config.DatetimeColumn(
                    "Data preventivo", format="DD/MM/YYYY", width="small",
                ),
                "Canone €/mese": st.column_config.NumberColumn(format="%.2f €"),
                "Anticipo €": st.column_config.NumberColumn(format="%.0f €"),
                "Km": st.column_config.NumberColumn(format="%d"),
            },
        )

        # --- per-result expanders with breakdown + PDF link
        st.subheader("Dettagli")
        for r in results:
            data_str = _format_date(r.get("created_at"))
            title = (
                f"{_score_emoji(r['score'])}  "
                f"**{float(r['score'] or 0):.3f}** · "
                f"{r['customer_full_name']} — {r['vehicle_full_name']} · "
                f"📅 {data_str}"
            )
            with st.expander(title):
                left, right = st.columns([3, 2])
                with left:
                    st.markdown(
                        f"**Offerta:** `{r['offer_number']}` · "
                        f"**Data preventivo:** {_format_date(r.get('created_at'), with_time=True)}"
                    )
                    st.markdown(
                        f"**Canone:** {float(r['monthly_fee'] or 0):.2f} €/mese · "
                        f"**Durata:** {r['duration_months']} mesi · "
                        f"**Km:** {int(r['km_total'] or 0):,}".replace(",", ".")
                    )
                    st.markdown(
                        f"**Tipo:** {r['vehicle_type']} · "
                        f"**Motor:** {r['motorization']} · "
                        f"**Anticipo:** {float(r['anticipo'] or 0):.0f} €"
                    )
                    if r.get("pdf_url"):
                        st.markdown(f"[📄 Apri PDF]({r['pdf_url']})")
                    else:
                        st.caption("📄 PDF non disponibile (record di seed).")
                with right:
                    st.markdown("**Score breakdown**")
                    st.dataframe(
                        _format_breakdown(r.get("score_breakdown")),
                        hide_index=True,
                        use_container_width=True,
                    )

render_sidebar_user_box()
