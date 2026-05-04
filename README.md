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
├── streamlit_app.py              # Entry point: login gate + welcome page
├── requirements.txt
├── .streamlit/
│   ├── config.toml               # Brand theme (#1B3A8A primary) + maxUploadSize
│   └── secrets.toml.example      # Template — real secrets stay local / in Streamlit Cloud
├── lib/
│   ├── __init__.py
│   ├── auth.py                   # Mocked login (MOCK_USERS dict + session gate)
│   ├── parser.py                 # Claude Haiku 4.5: PDF → JSON
│   ├── storage.py                # Supabase wrappers (Postgres + Storage + RPC)
│   └── schemas.py                # Pydantic QuoteRecord + SearchFilters
├── pages/
│   ├── 1_📤_Upload.py            # Upload PDF → parse → review → save (with rollback)
│   ├── 2_🔍_Search.py            # Structured filters → ranked results + breakdown
│   └── 3_📊_Browse_All.py        # Sortable dataframe + CSV download
├── db/
│   ├── 01_schema.sql             # quotations table + 6 indexes
│   ├── 01b_quotations_rls.sql    # disable RLS on quotations (PoC mock auth)
│   ├── 02_search_function.sql    # search_quotations() RPC + grants
│   ├── 02b_storage_policies.sql  # storage policies for arval_quotes bucket
│   └── 03_seed.sql               # 20 hand-crafted records + Mattina CF backfill
├── data/
│   └── mattina_napoli.pdf        # canonical real Arval quote
├── scripts/
│   └── test_parser.py            # CLI: parse a PDF, print JSON
├── DEPLOY.md                     # Supabase + Streamlit Cloud walkthrough
└── README.md                     # this file
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

Run the five files in `db/` **in this order** (paste each into a new SQL Editor query and run):

| | File | Purpose |
|---|---|---|
| 1 | `db/01_schema.sql` | `quotations` table + indexes |
| 2 | `db/01b_quotations_rls.sql` | disable RLS on `quotations` (PoC has mock auth only) |
| 3 | `db/02_search_function.sql` | `search_quotations()` RPC + `GRANT EXECUTE` to `anon` |
| 4 | `db/02b_storage_policies.sql` | INSERT/SELECT/DELETE policies on `storage.objects` for the bucket |
| 5 | `db/03_seed.sql` | 20 hand-crafted demo rows + backfill of Mattina's mock CF |

In Supabase **Storage**, create a bucket named `arval_quotes` with **Public bucket** ✅ enabled.

For the full deployment walkthrough (including Streamlit Community Cloud setup and troubleshooting) see [`DEPLOY.md`](DEPLOY.md).

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

Login with `demo.thehurry / demo2026` (mock — see `lib/auth.py`). Other demo accounts are listed in `.streamlit/secrets.toml.example`.

---

## Test the public API

Supabase auto-exposes the SQL function at `POST /rest/v1/rpc/search_quotations`. The same `anon` key the Streamlit app uses is the API key for external callers — *no FastAPI, no separate backend.*

```bash
ANON_KEY="eyJ..."   # from Supabase → Settings → API → Project API keys → anon public

curl -X POST "https://YOUR_PROJECT.supabase.co/rest/v1/rpc/search_quotations" \
  -H "apikey: $ANON_KEY" \
  -H "Authorization: Bearer $ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "p_target_monthly_fee": 650,
    "p_target_duration_months": 48,
    "p_target_km_total": 100000,
    "p_vehicle_type": "suv",
    "p_motorization": "phev",
    "p_min_score": 0.8,
    "p_limit": 5
  }' | jq '.[] | {customer_full_name, score, monthly_fee, vehicle_full_name}'
```

Expected first three rows after `db/03_seed.sql` is loaded **and** the Mattina PDF has been uploaded via the Upload page:

```json
{ "customer_full_name": "Mattina Napoli", "score": "0.998", "monthly_fee": "646.21", "vehicle_full_name": "BYD SEAL U DM-i 1.5 324cv Design" }
{ "customer_full_name": "Sofia Bari",     "score": "0.913", "monthly_fee": "720.00", "vehicle_full_name": "Volvo XC40 Recharge T5 PHEV Inscription" }
{ "customer_full_name": "Andrea Trento",  "score": "0.894", "monthly_fee": "580.00", "vehicle_full_name": "Cupra Formentor 1.5 e-Hybrid 245cv VZ" }
```

Every RPC parameter is optional — pass only the ones you care about; the score is a weighted average over the active features only. See spec §4 for the full weight table.

---

## Milestones

| | Milestone | Status |
|---|---|---|
| A | DB schema + RPC + parser + storage + schemas + CLI | ✅ done |
| B | Streamlit skeleton + mocked login | ✅ done |
| C | Upload page (end-to-end with rollback) | ✅ done |
| D | 20 hand-crafted seed records | ✅ done |
| E | Search + Browse pages | ✅ done |
| F | Polish + `DEPLOY.md` + acceptance review | ✅ done |

Full deployment walkthrough: [`DEPLOY.md`](DEPLOY.md).
