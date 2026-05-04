# Deploy guide — Mobility AI Knowledge Base PoC

End-to-end setup: Supabase free project + Streamlit Community Cloud + Anthropic API. Roughly **30 minutes** start to finish, assuming you already have accounts.

---

## TL;DR

1. Create a Supabase project and run the five SQL migrations in `db/` (order below).
2. Create the `arval_quotes` storage bucket (Public, with the included policies).
3. Drop your Supabase + Anthropic keys into `.streamlit/secrets.toml`, run `streamlit run streamlit_app.py`.
4. Push to GitHub, connect at [share.streamlit.io](https://share.streamlit.io), paste the same secrets in the Settings → Secrets dialog.
5. Verify the acceptance checklist at the bottom of this file.

---

## Prerequisites

- A **Supabase** account ([supabase.com](https://supabase.com), free tier).
- An **Anthropic** account with API access to `claude-haiku-4-5-20251001`.
- A **GitHub** account (the repo must be public for Streamlit Community Cloud's free tier).
- A **Streamlit Community Cloud** account ([share.streamlit.io](https://share.streamlit.io)).
- Local: **Python 3.11+** and **git**.

---

## Step 1 · Supabase

### 1.1 — Create the project

[supabase.com/dashboard](https://supabase.com/dashboard) → **New project** → free tier, region close to your users (e.g. `eu-central-1`).

Wait for provisioning (~2 min). Then **Settings → API** and copy:

- **Project URL** (e.g. `https://xxxxxxxxxxxx.supabase.co`)
- **`anon` public key** — used by the Streamlit app and the public REST API.
- **`service_role` secret key** — used only by admin/seed scripts; **never** expose to the UI or commit.

### 1.2 — Run the SQL migrations (in order)

Open **SQL Editor** → **New query**. Run each file's contents from `db/`, **in this order**:

| Order | File | What it does |
|---|---|---|
| 1 | `db/01_schema.sql` | Creates the `quotations` table with enum CHECKs, a generated `km_annual` column, and six search indexes |
| 2 | `db/01b_quotations_rls.sql` | Disables RLS on `quotations` (PoC has no real auth — see hard constraint #3) |
| 3 | `db/02_search_function.sql` | Creates the `search_quotations()` RPC and grants `EXECUTE` to `anon`/`authenticated` |
| 4 | `db/02b_storage_policies.sql` | Adds INSERT / SELECT / DELETE policies on `storage.objects` for the `arval_quotes` bucket |
| 5 | `db/03_seed.sql` | Inserts the 20 hand-crafted demo records |

Each `Run` should report `Success. No rows returned`.

> **Re-runnable:** all five files are idempotent. The seed wipes prior `parser_version='seed-v1'` rows before inserting, so re-running is safe.

### 1.3 — Create the storage bucket

**Storage** → **New bucket** → Name: `arval_quotes` → **Public bucket** ✅ → Create.

> If you forget the public flag the PDFs upload fine but `get_pdf_url()` returns 404s. You can flip it later via SQL: `update storage.buckets set public = true where id = 'arval_quotes';`

### 1.4 — Verify

In the SQL editor:

```sql
select count(*) from quotations;                                  -- expect 20
select vehicle_type, count(*) from quotations group by 1;         -- 7 enum values present
select motorization, count(*)  from quotations group by 1;        -- 8 enum values, each ≥ 2
select * from search_quotations(p_target_monthly_fee := 650);     -- returns ranked rows, no error
```

In **Storage** → `arval_quotes` should be visible and Public.

---

## Step 2 · Anthropic

[console.anthropic.com](https://console.anthropic.com) → **API Keys** → Create Key → copy.

The parser uses `claude-haiku-4-5-20251001`. Cost ≈ **$0.005/quote** (3 KB in, 600 tokens out × $0.80/$4 per MTok), so 100 demo uploads cost ≈ $0.50. Confirm your account has credit/billing enabled.

---

## Step 3 · Local development

```bash
git clone https://github.com/bluecaterpillar/mobility-ai-kb.git
cd mobility-ai-kb

python3 -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit .streamlit/secrets.toml — paste your real values (see template below)
```

`.streamlit/secrets.toml` minimum:

```toml
[supabase]
url              = "https://YOUR_PROJECT.supabase.co"
anon_key         = "eyJ..."
service_role_key = "eyJ..."           # admin scripts only
storage_bucket   = "arval_quotes"

[anthropic]
api_key = "sk-ant-..."
model   = "claude-haiku-4-5-20251001"

[app]
mock_users = ["demo.thehurry:demo2026"]
```

The file is git-ignored — `git status` should never show it.

### Smoke-test the parser

```bash
python scripts/test_parser.py data/mattina_napoli.pdf
```

You should see a JSON dict with `offer_number: "15789678/1"`, `monthly_fee: 646.21`, `vehicle_brand: "BYD"`, etc.

### Run the app

```bash
streamlit run streamlit_app.py
```

[localhost:8501](http://localhost:8501) → log in with `demo.thehurry / demo2026` → walk through Upload → Search → Browse.

---

## Step 4 · Streamlit Community Cloud

### 4.1 — Push to GitHub

The repo is already at [github.com/bluecaterpillar/mobility-ai-kb](https://github.com/bluecaterpillar/mobility-ai-kb) (public). For your own fork:

```bash
git remote add origin https://github.com/<your-org>/mobility-ai-kb.git
git push -u origin main
```

### 4.2 — Connect

[share.streamlit.io](https://share.streamlit.io) → **Create app** → pick the repo, branch `main`, main file path `streamlit_app.py`.

### 4.3 — Configure secrets

**Settings** → **Secrets** → paste the entire contents of your `.streamlit/secrets.toml` (verbatim, including the `[supabase]` / `[anthropic]` headers). Save.

### 4.4 — Deploy

Click **Deploy**. First build takes ~3 min (pip resolves the deps). On success you get a `https://<app-name>.streamlit.app` URL. Auto-redeploys on every push to `main`.

> **Heads-up:** Streamlit Community Cloud requires a public GitHub repo on the free tier. Make sure no secret ever lands in a commit. The `.gitignore` covers `.streamlit/secrets.toml` — verify with `git status` before each push.

---

## Step 5 · Post-deploy verification (acceptance criteria, spec §11)

Run through this on the deployed URL.

- [ ] Streamlit app reachable at the `*.streamlit.app` URL.
- [ ] Login with `demo.thehurry / demo2026` works; reload preserves the session; **Esci** (sidebar) returns to the login form.
- [ ] **📤 Upload** → upload `data/mattina_napoli.pdf` → spinner runs → preview shows `offer_number "15789678/1"`, `monthly_fee 646.21`, `vehicle_brand "BYD"`, `customer_fiscal_code` → null (the source PDF leaves "CF Cliente" blank — Mattina's seed UPDATE in `db/03_seed.sql` backfills `RSSMRA80A01H501U`).
- [ ] After **✅ Conferma e salva** the row appears in **📊 Esplora tutti** with the PDF link working.
- [ ] **🔍 Cerca** with `vehicle_type=suv`, `motorization=phev`, `target_fee=650`, `target_duration=48`, `target_km=100000`, `min_score=0.80` → Mattina is the top match at score ≥ 0.95 (actual: ≈ 0.998).
- [ ] Each result shows the per-feature score breakdown (fee / duration / km / type / brand / anticipo / motorization).
- [ ] Public REST API call (see "Public REST API" below) returns the same ranked rows.
- [ ] `git status` of the deployed branch shows no `secrets.toml`, no `.env`, no `.venv/`.
- [ ] [`README.md`](README.md) describes local run; [`DEPLOY.md`](DEPLOY.md) (this file) describes deployment.

---

## Public REST API

Supabase auto-exposes the SQL function as `POST /rest/v1/rpc/search_quotations`. Authentication uses the same `anon` key as the Streamlit app — it is intended to be public.

```bash
ANON_KEY="eyJ..."   # the same key from Settings → API → Project API keys → anon public

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

Expected first three rows (after `db/03_seed.sql` is loaded and Mattina has been uploaded):

```json
{ "customer_full_name": "Mattina Napoli",  "score": "0.998", "monthly_fee": "646.21" }
{ "customer_full_name": "Sofia Bari",       "score": "0.913", "monthly_fee": "720.00" }
{ "customer_full_name": "Andrea Trento",    "score": "0.894", "monthly_fee": "580.00" }
```

All RPC parameters are optional. Pass `null` (omit) to skip a filter; the score is a weighted average over only the features you provided.

---

## Operational notes

- **Free-tier projects pause after 7 days of inactivity.** Set a calendar reminder before the demo and ping the dashboard to wake it.
- **Public bucket = public URLs.** Anyone with a `pdf_url` from the `quotations` table can download the PDF. Acceptable for a demo with synthetic data; for real production switch to **signed URLs** (replace `get_public_url` with `create_signed_url(path, expires_in=3600)` in `lib/storage.py`).
- **Storage budget.** 1 GB free. Each Arval PDF is ~500 KB, so room for ~2,000 uploads before hitting the cap.
- **DB budget.** 500 MB free. Each row averages ~5 KB (including `parsed_raw_json`), so ~100 k rows before the cap.
- **Anon key rotation.** If you ever leak the `anon` key (it's public by design, but still): regenerate from Supabase Settings → API → click "Reset" on `anon`. Then update Streamlit Cloud secrets and re-deploy.
- **Cron / keep-alive.** Streamlit Community Cloud sleeps idle apps after ~15 minutes of no traffic; the next visitor waits ~10 s for the warm-up. No fix on free tier; Cloud Pro removes this.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Caricamento fallito: 403 / new row violates row-level security policy` on upload | RLS on `storage.objects` blocks anon INSERT | Re-run `db/02b_storage_policies.sql` |
| `Salvataggio nel database fallito: 42501 / new row violates row-level security policy for table "quotations"` | RLS enabled on the public-schema table | Run `db/01b_quotations_rls.sql` |
| `Apri PDF` → `404 Object not found` | Bucket isn't public | `update storage.buckets set public = true where id = 'arval_quotes';` |
| `Errore durante il parsing: anthropic.NotFoundError: model not found` | Wrong model id or no access | Verify your account has access to `claude-haiku-4-5-20251001` |
| `Errore durante il parsing: anthropic.AuthenticationError: invalid api key` | Stale or wrong key | Regenerate at console.anthropic.com → update Streamlit secrets |
| `streamlit run` shows no error but app is blank in Cloud | Secrets not set or section names wrong | Check Settings → Secrets uses `[supabase]` / `[anthropic]` headers exactly |
| `select count(*)` shows more than 21 after a single Mattina upload | Two parser runs returned slightly different `offer_number` formats (e.g. `"15789678 / 1"` vs `"15789678/1"`) | Use the dedupe script in this repo's git history (commit `1c43997`); the parser now normalises slash whitespace |
| Search returns nothing despite obviously matching rows | All filters left blank — the weighted-average denominator is 0 → `final_score` is NULL → row excluded | Set at least one target or categorical filter, or use **Esplora tutto** |
| `Module not found: lib.parser` after `git pull` | Old `__pycache__/` shadowing | `find . -name __pycache__ -exec rm -rf {} +` and re-run |

---

## File reference

```
.
├── streamlit_app.py              entry point; login gate + welcome page
├── pages/
│   ├── 1_📤_Upload.py            PDF → storage → parser → confirm → DB (with rollback)
│   ├── 2_🔍_Search.py            structured filters → ranked results + per-row breakdown
│   └── 3_📊_Browse_All.py        sortable dataframe + CSV download
├── lib/
│   ├── auth.py                   mocked login + session gate
│   ├── parser.py                 Claude Haiku 4.5 PDF → JSON
│   ├── storage.py                Supabase client wrappers
│   └── schemas.py                Pydantic QuoteRecord + SearchFilters
├── db/
│   ├── 01_schema.sql             quotations table + 6 indexes
│   ├── 01b_quotations_rls.sql    disable RLS on quotations (PoC has no real auth)
│   ├── 02_search_function.sql    search_quotations() RPC + grants
│   ├── 02b_storage_policies.sql  storage policies (anon CRUD on arval_quotes)
│   └── 03_seed.sql               20 hand-crafted demo rows + Mattina CF backfill
├── data/
│   └── mattina_napoli.pdf        canonical real Arval quote
├── scripts/
│   └── test_parser.py            CLI for the parser
├── .streamlit/
│   ├── config.toml               theme + maxUploadSize
│   └── secrets.toml.example      template (real file is git-ignored)
└── requirements.txt
```
