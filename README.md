# Aegis IOC — Tri-Domain Institutional Operations Center

A unified operations console for **Cybersecurity**, **HealthTech**, and **FinTech**
operations. One micro-frontend shell over a split-backend microservice mesh,
governed by a cryptographic RBAC API gateway.

The platform ships three modules: **Aegis Threat** (cyber), **Aegis Clinical**
(health), and **Aegis Ledger** (fintech).

See [`AegisIOC.md`](./AegisIOC.md) for the full architecture specification and the
phased implementation roadmap.

```
┌────────────────────────────────────────────────────────────────┐
│  SPA SHELL  →  GATEWAY (JWT/RBAC)  →  cyber · health · fintech   │
│  three-pane operations UI            mock ML + live WebSockets   │
└────────────────────────────────────────────────────────────────┘
```

## What's implemented

* **Gateway + Auth** — JWT issuance/verification, OAuth2 scopes, default-deny
  RBAC guards per `/api/v1/<domain>/*` route, hardening headers.
* **Three domain services** — schemas, two-tier mock ML inference, in-memory
  stores, REST endpoints, background event simulators, and per-domain WebSocket
  streams with the spec's flush cadences (cyber 250ms / fintech 50ms / health 500ms).
* **SPA** — role login, scope-gated tabs, three-pane layout (live ticker /
  AG-Grid / investigation + action panel), live WebSocket updates.
* **Tests** — pytest suite mirroring the three cross-domain verification tests
  plus RBAC denial cases.

> The heavy production infra (Envoy, Kafka, FHIR, CockroachDB, XGBoost, Llama-3,
> etc.) is *simulated* behind single-module seams. See the "Reference vs.
> Production" table in `AegisIOC.md` for the swap points.

## Quickstart (local, no Docker)

### 1. Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API docs: <http://localhost:8000/docs> · Health: <http://localhost:8000/health>

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173> and sign in with a demo role.

### Demo accounts (password: `demo`)

| Username   | Role                          | Domains            |
| ---------- | ----------------------------- | ------------------ |
| `analyst`  | Infrastructure Sec. Analyst   | Cyber              |
| `clinician`| Attending Clinical Provider   | Health             |
| `officer`  | FinTech Compliance Officer    | FinTech            |
| `governor` | Institutional Governance Board| All three + admin  |

## Quickstart (Docker)

```bash
docker compose up --build
```

Frontend on <http://localhost:8080>, backend on <http://localhost:8000>.

## Tests

```bash
cd backend && source .venv/bin/activate && python -m pytest -q
```

## Verification (matches `AegisIOC.md` §8)

```bash
# get a token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"governor","password":"demo"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

# cyber ingress
curl -s -X POST http://localhost:8000/api/v1/cyber/telemetry/submit \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"source_ip":"185.220.101.5","destination_ip":"10.0.4.112","destination_port":22,"protocol":"TCP","bytes_transferred":1420,"tcp_flags":["SYN"]}'
```

## Security notes

This is a **reference implementation for local use**. Before any real deployment:

* Replace `AEGIS_SECRET_KEY` and wire a real Identity Provider (the demo users in
  `backend/app/auth/users.py` are local-only).
* Replace in-memory stores with the per-domain compliant datastores.
* Front the services with the real gateway (Envoy + ext_authz).

## Layout

```
AegisIOC/
├── AegisIOC.md        # architecture spec + roadmap
├── docker-compose.yml
├── backend/           # FastAPI gateway + Aegis Threat/Clinical/Ledger services
└── frontend/          # Vite + React + AG-Grid SPA
```
