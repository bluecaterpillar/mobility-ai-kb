# Mobility AI — Knowledge Base PoC

Functional Proof-of-Concept of the **Knowledge Base** component of *Mobility AI / Intelligence Hub* — a SaaS for Italian Long-Term Rental (NLT) brokers like **The Hurry**.

The KB receives **Arval quote PDFs**, parses them with Claude Haiku 4.5, normalizes the data into Supabase Postgres, stores the original PDFs in Supabase Storage, and exposes a **structured search API** that returns historical quotes ranked by similarity to a query (scores 0.00–1.00; ≥ 0.80 = strong match).

> **This is a real PoC, not a mock.** The parser actually parses, the database actually queries, the search actually scores. It runs on free-tier infrastructure but the code paths are production-shaped.

The single source of truth for the design is `KB_SCAFFOLDING.md` (kept outside this repo). All hard constraints listed there apply.

---

## Architecture (one diagram, in prose)

1. **Streamlit app** (single Python process) → Login → Upload / Search / Browse pages.
2. **PDF upload** → Supabase Storage bucket `arval_quotes` (public read).
3. **Parser** → Claude Haiku 4.5 reads the PDF natively, returns strict JSON.
4. **Insert** → row in Supabase Postgres `quotations` table.
5. **Search** → form filters → `POST /rest/v1/rpc/search_quotations` (PostgREST exposes the SQL function automatically — *no FastAPI, no separate API service*).

Hard constraints: no FastAPI, no embeddings/pgvector, no real auth (mocked), no ORM, no Docker, no build pipeline beyond `requirements.txt`.

---

## Repository layout

```
.
├── streamlit_app.py              # Entry point (Milestone B)
├── requirements.txt
├── .streamlit/
│   ├── config.toml               # Theme (Milestone B)
│   └── secrets.toml.example      # Template — real secrets stay local / in Streamlit Cloud
├── lib/
│   ├── __init__.py
│   ├── auth.py                   # Mocked login (Milestone B)
│   ├── parser.py                 # Claude API call, PDF → dict
│   ├── storage.py                # Supabase wrappers (DB + bucket)
│   └── schemas.py                # Pydantic QuoteRecord, SearchFilters
├── pages/                        # Streamlit multi-page (Milestones C / E)
├── db/
│   ├── 01_schema.sql             # quotations table + indexes
│   ├── 02_search_function.sql    # search_quotations RPC
│   └── 03_seed.sql               # 20 hand-crafted records (Milestone D)
├── data/
│   └── mattina_napoli.pdf        # canonical real Arval quote
├── scripts/
│   └── test_parser.py            # CLI: parse a PDF, print JSON
└── DEPLOY.md                     # Supabase + Streamlit Cloud walkthrough (Milestone F)
```

---

## Prerequisites

- **Python 3.11+** (Streamlit Cloud uses 3.11; local dev tested on 3.12).
- A **Supabase** project (free tier is enough — 500 MB DB, 1 GB Storage). Generated:
  - Project URL (`SUPABASE_URL`)
  - `anon` API key (used by both the UI and the public REST API)
  - `service_role` API key (only for one-shot admin/seed scripts; never embed in UI)
- An **Anthropic API key** with access to `claude-haiku-4-5-20251001`.
- The **canonical PDF** at `data/mattina_napoli.pdf` (already committed).

> _Note on the canonical sample:_ the spec's acceptance criteria reference `chiara_innocenti.pdf` (the original real customer). The shareable demo PDF in this repo uses the fictitious customer **Mattina Napoli** with the same offer number, vehicle, fee, and km — so the parser still produces `offer_number "15789678/1"`, `monthly_fee 646.21`, `vehicle_brand "BYD"`. The fiscal-code field is absent on this sample (the PDF leaves "CF Cliente" blank).

---

## Local setup

```bash
# 1. Clone & enter the repo
git clone <this-repo-url> mobility-ai-kb
cd mobility-ai-kb

# 2. Create & activate a virtualenv
python3 -m venv .venv
source .venv/bin/activate   # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Provision secrets
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Then edit .streamlit/secrets.toml and paste your real Supabase + Anthropic keys.
```

### Provision the database (one-time, in the Supabase SQL editor)

```sql
-- Run in this order:
\i db/01_schema.sql
\i db/02_search_function.sql
-- (db/03_seed.sql will arrive in Milestone D)
```

In Supabase **Storage**, create a bucket named `arval_quotes` (Public read).

---

## Run locally

### Smoke-test the parser (Milestone A)

```bash
# Reads the API key from .streamlit/secrets.toml or ANTHROPIC_API_KEY.
python scripts/test_parser.py data/mattina_napoli.pdf
```

Expected fields in the printed JSON include:

```json
{
  "offer_number": "15789678/1",
  "customer_code": "N98926",
  "customer_first_name": "Mattina",
  "customer_last_name": "Napoli",
  "vehicle_brand": "BYD",
  "vehicle_model": "SEAL U DM-i",
  "vehicle_type": "suv",
  "motorization": "phev",
  "duration_months": 48,
  "km_total": 100000,
  "monthly_fee": 646.21,
  "monthly_fee_lease": 450.83,
  "monthly_fee_services": 195.38,
  "anticipo": 6000
}
```

### Run the Streamlit app

```bash
streamlit run streamlit_app.py
```

Login with `demo.thehurry / demo2026` (mock — see `lib/auth.py` once Milestone B lands).

---

## Public search API

Once Milestones A + D are live the search RPC is reachable as a plain HTTPS POST — no separate backend, no FastAPI:

```bash
curl -X POST "https://YOUR_PROJECT.supabase.co/rest/v1/rpc/search_quotations" \
  -H "apikey: $SUPABASE_ANON_KEY" \
  -H "Authorization: Bearer $SUPABASE_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "p_target_monthly_fee": 650,
    "p_target_duration_months": 48,
    "p_target_km_total": 100000,
    "p_vehicle_type": "suv",
    "p_motorization": "phev",
    "p_min_score": 0.8,
    "p_limit": 5
  }'
```

(Full curl + response example will land with Milestone F.)

---

## Milestones

| | Milestone | Status |
|---|---|---|
| A | DB schema + RPC + parser + storage + schemas + CLI | **in review** |
| B | Streamlit skeleton + mocked login | pending |
| C | Upload page (end-to-end) | pending |
| D | 20 hand-crafted seed records | pending |
| E | Search + Browse pages | pending |
| F | Polish + DEPLOY.md + acceptance review | pending |

Deployment walkthrough lives in [`DEPLOY.md`](DEPLOY.md) (Milestone F).
