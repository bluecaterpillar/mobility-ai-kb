<div align="center">
  <img src="assets/hurry_logo.svg" width="120" alt="The Hurry"/>
  <h1>Mobility AI — Knowledge Base PoC</h1>
  <p><em>Quote intelligence platform per <a href="https://www.the-hurry.com/">The Hurry</a></em></p>
  <p>
    <strong>Live demo:</strong>
    <a href="https://mobility-ai-kb-sy7hhwyck9omfdxiqk5zmt.streamlit.app/">mobility-ai-kb-…streamlit.app</a>
    &nbsp;·&nbsp; login: <code>demo.thehurry / demo2026</code>
  </p>
</div>

---

Proof-of-Concept funzionale del componente **Knowledge Base** della piattaforma **Mobility AI / Intelligence Hub** — il SaaS per i broker italiani di Noleggio a Lungo Termine come **The Hurry**.

La KB riceve **PDF di preventivi Arval**, li analizza con Claude Haiku 4.5, normalizza i dati su Supabase Postgres, archivia i PDF originali su Supabase Storage ed espone una **API di ricerca strutturata** che restituisce i preventivi storici ordinati per affinità (punteggio 0.00–1.00; ≥ 0.80 = match forte).

> **È un PoC reale, non un mock.** Il parser estrae davvero, il database fa query vere, il punteggio di ricerca è calcolato dal motore. Gira su free tier ma le code-path sono "production-shaped".

L'unica fonte di verità del design è `KB_SCAFFOLDING.md` (fuori dal repo). Tutti i vincoli "hard" elencati lì si applicano.

---

## Architettura (un diagramma, in prosa)

1. **App Streamlit** (singolo processo Python) → Login → pagine Upload / Cerca / Esplora.
2. **Upload PDF** → bucket Supabase Storage `arval_quotes` (lettura pubblica).
3. **Parser** → Claude Haiku 4.5 legge il PDF nativamente, restituisce JSON strict.
4. **Insert** → riga su Postgres tabella `quotations`.
5. **Cerca** → form filters → `POST /rest/v1/rpc/search_quotations` (PostgREST espone la SQL function automaticamente — *no FastAPI, nessun servizio API separato*).

Vincoli di progetto: niente FastAPI, niente embeddings/pgvector, niente auth reale (mocked), niente ORM, niente Docker, build pipeline limitata a `requirements.txt`.

---

## Struttura del repository

```
.
├── streamlit_app.py              # entry point: gate di login + welcome page
├── requirements.txt
├── .streamlit/
│   ├── config.toml               # tema brand The Hurry (#710B41 primary) + maxUploadSize
│   └── secrets.toml.example      # template — il file vero resta locale o su Streamlit Cloud
├── assets/
│   ├── hurry_logo.svg            # logo wordmark Hurry (colorato in maroon brand)
│   └── hurry_punto.svg           # accent del punto esclamativo
├── lib/
│   ├── __init__.py
│   ├── auth.py                   # mock login (dict MOCK_USERS + gate di sessione)
│   ├── branding.py               # st.logo() helper + palette
│   ├── parser.py                 # Claude Haiku 4.5: PDF → JSON
│   ├── storage.py                # wrapper Supabase (Postgres + Storage + RPC)
│   └── schemas.py                # Pydantic QuoteRecord + SearchFilters
├── pages/
│   ├── 1_📤_Upload.py            # upload PDF → parse → review → save (con rollback)
│   ├── 2_🔍_Search.py            # filtri strutturati → risultati ranked + breakdown
│   └── 3_📊_Browse_All.py        # tabella ordinabile + download CSV
├── db/
│   ├── 01_schema.sql             # tabella quotations + 6 indici
│   ├── 01b_quotations_rls.sql    # disabilita RLS su quotations (PoC ha solo mock auth)
│   ├── 02_search_function.sql    # RPC search_quotations() + GRANT
│   ├── 02b_storage_policies.sql  # policy storage per il bucket arval_quotes
│   └── 03_seed.sql               # 20 record curati a mano + backfill CF di Mattina
├── data/
│   └── mattina_napoli.pdf        # preventivo Arval canonico (anonimizzato)
├── scripts/
│   └── test_parser.py            # CLI: parsa un PDF, stampa il JSON
├── DEPLOY.md                     # guida completa deploy (Supabase + Streamlit Cloud)
└── README.md                     # questo file
```

---

## Prerequisiti

- **Python 3.11+** (Streamlit Cloud usa 3.11; testato in locale su 3.12).
- Un progetto **Supabase** (free tier basta — 500 MB DB, 1 GB Storage). Servono:
  - Project URL (`SUPABASE_URL`)
  - chiave API `anon` (usata sia dalla UI sia dalla REST API pubblica)
  - chiave API `service_role` (solo per script admin/seed; mai esposta in UI)
- Una **API key Anthropic** con accesso a `claude-haiku-4-5-20251001`.
- Il **PDF canonico** in `data/mattina_napoli.pdf` (già committato).

> _Nota sul sample canonico:_ i criteri di accettazione della spec referenziano `chiara_innocenti.pdf` (cliente reale). Il PDF demo nel repo usa il cliente fittizio **Mattina Napoli** con stesso numero offerta, veicolo, canone e km — quindi il parser produce comunque `offer_number "15789678/1"`, `monthly_fee 646.21`, `vehicle_brand "BYD"`. Il campo CF è vuoto sul PDF; il file `db/03_seed.sql` fa il backfill con il mock `RSSMRA80A01H501U`.

---

## Setup locale

```bash
# 1. Clone del repo
git clone https://github.com/bluecaterpillar/mobility-ai-kb.git
cd mobility-ai-kb

# 2. Virtualenv
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. Dipendenze
pip install -r requirements.txt

# 4. Provision dei secret
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Apri .streamlit/secrets.toml e incolla URL Supabase + anon key + Anthropic key
```

### Provisioning del database (una volta sola, nel SQL editor di Supabase)

Esegui i 5 file in `db/` **in quest'ordine** (un nuovo SQL Editor query per ognuno):

| | File | A cosa serve |
|---|---|---|
| 1 | `db/01_schema.sql` | tabella `quotations` + indici |
| 2 | `db/01b_quotations_rls.sql` | disabilita RLS su `quotations` (il PoC ha solo mock auth) |
| 3 | `db/02_search_function.sql` | RPC `search_quotations()` + `GRANT EXECUTE` ad `anon` |
| 4 | `db/02b_storage_policies.sql` | policy INSERT/SELECT/DELETE su `storage.objects` per il bucket |
| 5 | `db/03_seed.sql` | 20 record seed + backfill CF mock di Mattina |

Su **Storage** crea un bucket `arval_quotes` con flag **Public bucket** ✅.

Walkthrough completo del deploy (Streamlit Community Cloud incluso): vedi [`DEPLOY.md`](DEPLOY.md).

---

## Esecuzione in locale

### Smoke-test del parser

```bash
# Legge la API key da .streamlit/secrets.toml o ANTHROPIC_API_KEY.
python scripts/test_parser.py data/mattina_napoli.pdf
```

Output JSON atteso (campi load-bearing):

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

### Avvio dell'app Streamlit

```bash
streamlit run streamlit_app.py
```

Login con `demo.thehurry / demo2026` (mock — `lib/auth.py`). Altri account demo elencati in `.streamlit/secrets.toml.example`.

---

## Test della API pubblica

Supabase espone automaticamente la SQL function come `POST /rest/v1/rpc/search_quotations`. La stessa `anon` key usata dall'app Streamlit è la chiave per i caller esterni — *no FastAPI, nessun backend separato*.

```bash
ANON_KEY="eyJ..."   # da Supabase → Settings → API → Project API keys → anon public

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

Prime tre righe attese (con `db/03_seed.sql` caricato **e** Mattina già uploadata via app):

```json
{ "customer_full_name": "Mattina Napoli", "score": "0.998", "monthly_fee": "646.21", "vehicle_full_name": "BYD SEAL U DM-i 1.5 324cv Design" }
{ "customer_full_name": "Sofia Bari",     "score": "0.913", "monthly_fee": "720.00", "vehicle_full_name": "Volvo XC40 Recharge T5 PHEV Inscription" }
{ "customer_full_name": "Andrea Trento",  "score": "0.894", "monthly_fee": "580.00", "vehicle_full_name": "Cupra Formentor 1.5 e-Hybrid 245cv VZ" }
```

Tutti i parametri della RPC sono opzionali — passa solo quelli che ti interessano; lo score è una media pesata sulle sole feature presenti. Pesi e formula nella spec §4.

---

## Identità visiva

Il PoC adotta i colori di [The Hurry](https://www.the-hurry.com):

| Elemento | Colore | Hex |
|---|---|---|
| Primary | Maroon Hurry | `#710B41` |
| Dark accent | Maroon scuro | `#4B072B` |
| Surface secondaria | Rosa chiarissimo | `#F5EFF2` |
| Background | Bianco | `#FFFFFF` |

Il logo `assets/hurry_logo.svg` viene mostrato:
- in alto nella sidebar di tutte le pagine (via `st.logo()` in `lib/branding.py`)
- come hero centrato sulla pagina di login (`render_login_hero()`)

---

## Milestone

| | Milestone | Stato |
|---|---|---|
| A | Schema DB + RPC + parser + storage + schemas + CLI | ✅ done |
| B | Skeleton Streamlit + login mockato | ✅ done |
| C | Pagina Upload (end-to-end con rollback) | ✅ done |
| D | 20 record seed curati a mano | ✅ done |
| E | Pagine Cerca + Esplora | ✅ done |
| F | Polish + `DEPLOY.md` + acceptance review + brand The Hurry + deploy live | ✅ done |

Walkthrough completo del deploy: [`DEPLOY.md`](DEPLOY.md).
