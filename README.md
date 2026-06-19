

# Aegis IOC

### Tri-Domain Institutional Operations Center

A single pane of glass for **Cybersecurity**, **HealthTech**, and **FinTech** operations — a unified micro-frontend shell over a split-backend microservice mesh, governed by a cryptographic RBAC API gateway.

[Backend](https://fastapi.tiangolo.com/)
[Frontend](https://vitejs.dev/)
[Grid](https://www.ag-grid.com/)
[Auth](#rbac)
[Tests](#tests)
[License](#security-notes)



---

## Modules


| Module             | Domain        | Service prefix      | What it does                                         |
| ------------------ | ------------- | ------------------- | ---------------------------------------------------- |
| **Aegis Threat**   | Cybersecurity | `/api/v1/cyber/`*   | Threat-intelligence triage & autonomous remediation  |
| **Aegis Clinical** | HealthTech    | `/api/v1/health/`*  | Medication reconciliation & contraindication support |
| **Aegis Ledger**   | FinTech       | `/api/v1/fintech/`* | AML / sanctions screening & fraud risk scoring       |


```
┌──────────────────────────────────────────────────────────────────────┐
│  SPA SHELL  →  GATEWAY (JWT / RBAC)  →  Threat · Clinical · Ledger      │
│  three-pane operations UI              two-tier ML + live WebSockets    │
└──────────────────────────────────────────────────────────────────────┘
```

See `[AegisIOC.md](./AegisIOC.md)` for the full architecture specification and the phased implementation roadmap.

---

## Highlights

- **Gateway + Auth** — JWT issuance/verification, OAuth2 scopes, default-deny RBAC guards per `/api/v1/<domain>/`* route, hardening headers.
- **Three domain services** — typed schemas, two-tier mock ML inference, in-memory stores, REST endpoints, background event simulators, and per-domain WebSocket streams with tuned flush cadences (cyber 250 ms · fintech 50 ms · health 500 ms).
- **Live external feeds (optional)** — real data from AbuseIPDB, Shodan, openFDA, HAPI FHIR, CoinGecko, and Alpha Vantage, each with graceful fallback to the simulators.
- **Bright, dense SPA** — a sky-blue three-pane operations console (live ticker · AG-Grid · investigation & action panel) with scope-gated tabs and real-time WebSocket updates.
- **Tested** — a pytest suite mirroring the three cross-domain verification flows plus RBAC denial cases.

> Heavy production infra (Envoy, Kafka, FHIR, CockroachDB, XGBoost, Llama-3, …) is *simulated* behind single-module seams. See the "Reference vs. Production" table in `[AegisIOC.md](./AegisIOC.md)` for the swap points.

---

## Quickstart

You need two terminals: one for the API, one for the UI.

### 1 · Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)  ·  Health: [http://localhost:8000/health](http://localhost:8000/health)

### 2 · Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) and sign in with a demo role.

### Demo accounts  (password: `demo`)


| Username    | Role                            | Accessible modules |
| ----------- | ------------------------------- | ------------------ |
| `analyst`   | Infrastructure Security Analyst | Aegis Threat       |
| `clinician` | Attending Clinical Provider     | Aegis Clinical     |
| `officer`   | FinTech Compliance Officer      | Aegis Ledger       |
| `governor`  | Institutional Governance Board  | All three + admin  |


### Or run everything with Docker

```bash
docker compose up --build
```

Frontend on [http://localhost:8080](http://localhost:8080), backend on [http://localhost:8000](http://localhost:8000).

---

## Live external data feeds (optional)

The console runs on simulators by default. Each module can also pull **real** data; every connector falls back to seeded data on any missing key, timeout, or error, so it never stops flowing. Configure via `backend/.env` (template in `[backend/.env.example](./backend/.env.example)`).


| Module         | Feed          | Key required | Powers                                                             |
| -------------- | ------------- | ------------ | ------------------------------------------------------------------ |
| Aegis Threat   | AbuseIPDB     | yes (free)   | Real IP abuse scores in the live ingestion poller                  |
| Aegis Threat   | Shodan        | yes (free)   | On-demand blast-radius enrichment (open ports / vulns)             |
| Aegis Clinical | openFDA       | no           | Real adverse-event case counts in contraindication reports         |
| Aegis Clinical | HAPI FHIR     | no           | Import real FHIR R4 patients (`POST /health/clinical/fhir/import`) |
| Aegis Ledger   | CoinGecko     | no           | Live market prices drive the transaction stream                    |
| Aegis Ledger   | Alpha Vantage | yes (free)   | FX reference rates                                                 |


The no-key feeds (openFDA, HAPI FHIR, CoinGecko) are **on by default**. Enable the keyed ones by adding keys and flags:

```bash
# backend/.env
AEGIS_ABUSEIPDB_API_KEY=...
AEGIS_ENABLE_LIVE_CYBER=true
AEGIS_SHODAN_API_KEY=...          # powers the "Enrich blast radius (live)" button
AEGIS_ALPHAVANTAGE_API_KEY=...
```

In the UI, select a cyber alert and click **Enrich blast radius (live)** to pull Shodan / AbuseIPDB data into the investigation panel.

---

## RBAC

Access is enforced at the gateway via signed JWTs carrying OAuth2 scopes (default-deny):


| Role               | Scopes                               | Permitted actions                                  |
| ------------------ | ------------------------------------ | -------------------------------------------------- |
| Security Analyst   | `cyber:read`, `cyber:remediate`      | Isolate node, block IP, invalidate sessions        |
| Clinical Provider  | `clinical:read`, `clinical:write`    | Approve prescription overrides, sign chart records |
| Compliance Officer | `fintech:read`, `fintech:transact`   | Release hold, freeze assets, file SAR              |
| Governance Board   | `cyber:`*, `clinical:*`, `fintech:*` | All of the above + admin                           |


---

## Tests

```bash
cd backend && source .venv/bin/activate && python -m pytest -q
```

Covers the three cross-domain verification flows and RBAC denial cases.

### Manual verification (matches `[AegisIOC.md](./AegisIOC.md)` )

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"governor","password":"demo"}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

curl -s -X POST http://localhost:8000/api/v1/cyber/telemetry/submit \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"source_ip":"185.220.101.5","destination_ip":"10.0.4.112","destination_port":22,"protocol":"TCP","bytes_transferred":1420,"tcp_flags":["SYN"]}'
```

---

## Project layout

```
AegisIOC/
├── AegisIOC.md          # architecture spec + roadmap
├── docker-compose.yml
├── backend/             # FastAPI gateway + Threat / Clinical / Ledger services
│   ├── app/
│   │   ├── auth/        # JWT, scopes, RBAC, login
│   │   ├── core/        # event bus, stores, shared HTTP client
│   │   ├── domains/     # cyber · health · fintech (schemas, inference, connectors)
│   │   └── ws/          # WebSocket streams
│   └── tests/
└── frontend/            # Vite + React + TypeScript + AG-Grid SPA
    └── src/
        ├── api/         # REST + WebSocket clients
        ├── components/  # layout, ticker, grid, context panel
        ├── domains/     # per-module grid columns + actions
        └── store/       # Zustand state
```

---

## Security notes

This is a **reference implementation for local use**. Before any real deployment:

- Replace `AEGIS_SECRET_KEY` and wire a real Identity Provider — the demo users in `backend/app/auth/users.py` are local-only.
- Replace the in-memory stores with the per-domain compliant datastores.
- Front the services with the real gateway (Envoy + ext_authz).
- API keys for live feeds belong in `backend/.env` (git-ignored), never in source.

