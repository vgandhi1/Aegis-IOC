# Aegis IOC — Tri-Domain Institutional Operations Center

> A unified micro-frontend operations console sitting on top of a split-backend
> microservice mesh, governed by a cryptographic RBAC API gateway. One pane of
> glass for **Cybersecurity**, **HealthTech**, and **FinTech** operations.

This document is both the **architecture specification** and the **implementation
roadmap** for the reference implementation that lives in this repository.

The platform is composed of three modules over a shared shell:

| Module             | Domain        | Service prefix      |
| ------------------ | ------------- | ------------------- |
| **Aegis Threat**   | Cybersecurity | `/api/v1/cyber/*`   |
| **Aegis Clinical** | HealthTech    | `/api/v1/health/*`  |
| **Aegis Ledger**   | FinTech       | `/api/v1/fintech/*` |

---

## 1. System Architecture

```
                          +-----------------------------------+
                          |     UNIFIED SPA FRONTEND SHELL     |
                          | (Module Federation / Zustand Core) |
                          +-----------------------------------+
                                          |
                              (HTTPS & Secure WebSockets)
                                          |
                                          v
                          +-----------------------------------+
                          | ENVOY API GATEWAY / AUTH ENFORCER |
                          |     (JWT Scope Cryptography)      |
                          +-----------------------------------+
                                          |
        +---------------------------------+---------------------------------+
        | /api/v1/cyber/*                 | /api/v1/health/*                | /api/v1/fintech/*
        v                                 v                                 v
+--------------------------+   +--------------------------+   +--------------------------+
|   AEGIS THREAT (cyber)   |   | AEGIS CLINICAL (health)  |   |  AEGIS LEDGER (fintech)  |
|                          |   |                          |   |                          |
| Ingest:  Kafka Stream    |   | Ingest:  Mirth / HL7     |   | Ingest:  RabbitMQ Bus    |
| Hot:     ClickHouse OLAP |   | Store:   Azure FHIR      |   | Store:   CockroachDB     |
| Infer:   XGBoost/Llama-3 |   | Context: Qdrant Vector   |   | State:   Redis Cluster   |
| State:   PostgreSQL Meta |   | Infer:   BioBERT/Med-PaLM|   | Infer:   FinBERT/XGBoost |
+--------------------------+   +--------------------------+   +--------------------------+
```

### 1.1 Rationale for the Split-Backend Design

* **Data Velocity Asymmetry** — Cyber ingests up to ~1,000,000 unstructured
  events/sec, FinTech ~50,000 structured ACID transactions/sec, and HealthTech
  ~500 dense multi-modal documents/sec. A shared datastore would bottleneck.
* **Strict Regulatory Isolation** — Financial (PCI-DSS/FINRA), Healthcare
  (HIPAA/PHI), and Infrastructure (SOC 2 Type II) data must not co-mingle in one
  datastore. Separate stores let each domain be audited independently.
* **Granular RBAC** — Tokens issued by the IdP carry OAuth2 scopes. The gateway
  inspects the signed JWT and routes a request only if the proper domain
  privileges are satisfied.

### 1.2 Reference vs. Production

This repo ships a **pragmatic reference implementation** that is fully runnable
on a laptop. Heavy production infrastructure is *simulated* with clearly-marked
seams so it can be swapped for the real thing.

| Concern        | Production target              | Reference implementation                 |
| -------------- | ------------------------------ | ----------------------------------------- |
| API gateway    | Envoy + ext_authz              | FastAPI gateway middleware (`auth/`)      |
| Cyber ingest   | Kafka + Flink                  | In-process async queue + simulator        |
| FinTech ingest | RabbitMQ                       | In-process async queue + simulator        |
| Health ingest  | Mirth / HL7 router             | REST endpoint + simulator                 |
| Datastores     | ClickHouse/FHIR/CockroachDB    | In-memory ring-buffer stores              |
| Tier-1 ML      | XGBoost / Isolation Forest     | Deterministic heuristic scorers           |
| Tier-2 ML      | Llama-3 / Med-PaLM-2 / FinBERT | Rule-based grounded "agent" stubs         |
| Transport      | gRPC + WebSockets              | REST + WebSockets                         |

Each seam is a single module so a team can replace `inference.py` or `store.py`
without touching routes or the frontend.

### 1.3 Live External Data Feeds

The reference can ingest **real** data through per-domain `connectors.py` modules.
Every connector caches results, respects free-tier rate limits, and falls back to
the seeded/simulated data on any missing key, timeout, or error — so the console
never stops flowing. SSRF hardening: connectors only call operator-configured,
hardcoded HTTPS base URLs, validate IP inputs (Shodan/AbuseIPDB) against public
ranges, disable redirects, and send each API key only to its provider host.

| Module         | Live feed     | Auth        | Role in pipeline                                                  |
| -------------- | ------------- | ----------- | ---------------------------------------------------------------- |
| Aegis Threat   | AbuseIPDB     | header key  | Real abuse confidence in the rate-limited ingestion poller       |
| Aegis Threat   | Shodan        | query key   | On-demand blast-radius enrichment (`GET /cyber/alerts/{id}/enrich`) |
| Aegis Clinical | openFDA       | none        | Real adverse-event totals injected into the contraindication report |
| Aegis Clinical | HAPI FHIR R4  | none        | Import real Patient/Observation (`POST /health/clinical/fhir/import`) |
| Aegis Ledger   | CoinGecko     | none        | Live prices drive the transaction stream (volatility → fraud)    |
| Aegis Ledger   | Alpha Vantage | query key   | FX reference rates (cached; 25/day free tier)                    |

Enable via the `AEGIS_*` env vars in `backend/.env.example`. The no-key feeds
(openFDA, HAPI FHIR, CoinGecko) are on by default.

---

## 2. Micro-Frontend Shell & Unified UI Layout

A React SPA. (Production uses Webpack Module Federation to mount standalone
domain micro-apps; the reference build uses a single Vite bundle with lazy-loaded
domain modules — same component boundaries, simpler tooling.)

### 2.1 UI Density & Workspace Optimization

Information density over aesthetic padding. A consistent **three-pane layout**
across every tab, tuned for multi-monitor operation centers:

* **Pane A (Left, ~20%)** — Live real-time activity ticker. Vertical stream of
  minimal alert boxes updating via WebSockets, colored by severity.
* **Pane B (Center, ~55%)** — Primary operations grid. Virtualized AG-Grid
  capable of rendering large record sets at 60 fps.
* **Pane C (Right, ~25%)** — Contextual investigation node & action overrides.
  Raw JSON metrics, AI explanations, grounding citations, and action targets.

---

## 3. Aegis Threat — Cybersecurity Threat Intelligence Tower

Intercepts, classifies, and remediates multi-vector infrastructure attacks at
line rate.

### 3.1 Raw Telemetry Ingestion Payload

```json
{
  "ingestion_metadata": {
    "timestamp": "2026-05-29T19:30:15.102Z",
    "source_stream": "edge_firewall_04",
    "event_id": "evt_8f3d1a9e4b7c2d10"
  },
  "network_packet": {
    "source_ip": "185.220.101.5",
    "destination_ip": "10.0.4.112",
    "source_port": 49152,
    "destination_port": 22,
    "protocol": "TCP",
    "bytes_transferred": 1420,
    "tcp_flags": ["SYN"]
  },
  "threat_intelligence": {
    "abuse_ip_db": {
      "ip_address": "185.220.101.5",
      "abuse_confidence_score": 98,
      "total_reports": 14205,
      "country_code": "DE"
    },
    "alien_vault_otx": {
      "pulse_count": 14,
      "indicators_of_compromise": ["tor_exit_node", "brute_force_actor"],
      "adversary_group": "Unknown/Botnet"
    }
  },
  "ml_feature_vector": {
    "failed_auth_attempts_1m": 42,
    "unique_destinations_5m": 1,
    "entropy_payload_score": 0.12,
    "historical_ip_variance": 0.89
  }
}
```

### 3.2 Core Analytical Outbound Event

```json
{
  "alert_id": "alt_9c8b7a6f5e4d3c2b",
  "associated_event_id": "evt_8f3d1a9e4b7c2d10",
  "timestamp": "2026-05-29T19:30:15.115Z",
  "target_identifier": "endpoint_prod_db_01",
  "ml_inference": {
    "anomaly_score": 0.9642,
    "classification": "Brute_Force_SSH_Tunneling",
    "model_version": "xgb_threat_v2.4.1",
    "confidence_intervals": { "lower_bound": 0.912, "upper_bound": 0.994 },
    "mitre_attack_mapping": {
      "tactic": "TA0001_Initial_Access",
      "technique": "T1110_Brute_Force",
      "sub_technique": "T1110.001_Credential_Stuffing"
    }
  },
  "autonomous_remediation": {
    "recommended_action": "ISOLATE_HOST",
    "policy_override_triggered": false,
    "sla_duration_seconds": 300,
    "playbook_id": "pb_ssh_contain_v1"
  }
}
```

### 3.3 ML Execution Strategy (Cyber)

* **Tier 1 (sub-15ms anomaly detection)** — XGBoost binary classifiers against
  streaming features from Apache Flink.
* **Tier 2 (agentic triage)** — If Tier-1 score > 0.85, a Llama-3-8B-Instruct
  agent evaluates log context against threat feeds and emits a structured
  assessment (blast radius + remediation playbook).

---

## 4. Aegis Clinical — HealthTech Clinical Decision Support Hub

Monitors longitudinal health informatics, patient charts, and lab readings to
reduce adverse events.

### 4.1 Raw Ingestion Profile (HL7 FHIR Mapping)

```json
{
  "fhir_bundle_metadata": { "resourceType": "Bundle", "type": "collection" },
  "patient_resource": {
    "resourceType": "Patient",
    "id": "pat_hex_992104",
    "gender": "female",
    "birthDate": "1968-04-12"
  },
  "observation_resource": {
    "resourceType": "Observation",
    "id": "obs_vitals_99411",
    "status": "final",
    "code": { "coding": [{ "system": "http://loinc.org", "code": "8867-4", "display": "Heart rate" }] },
    "subject": { "reference": "Patient/pat_hex_992104" },
    "valueQuantity": { "value": 114, "unit": "beats/minute", "code": "/min" }
  },
  "active_medication_requests": [
    {
      "resourceType": "MedicationRequest",
      "id": "med_req_4011",
      "status": "active",
      "medicationCodeableConcept": {
        "coding": [{ "system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "11124", "display": "Warfarin" }]
      }
    }
  ]
}
```

### 4.2 Core Clinical Decision Support Report

```json
{
  "reconciliation_id": "rec_01h7x22b9m8r4",
  "patient_id": "pat_hex_992104",
  "proposed_action": { "medication_code": "RxNorm:1191", "medication_display": "Aspirin" },
  "clinical_decision_support": {
    "contraindication_detected": true,
    "severity_index": "CRITICAL",
    "fda_adverse_event_summary": {
      "total_matching_case_reports": 24012,
      "primary_co_manifestation_consequence": "Severe Gastrointestinal Hemorrhage",
      "odds_ratio_increase": 4.21
    },
    "evidence_grounding": {
      "source_database": "openFDA Drug Event Repository",
      "peer_reviewed_guideline_citation": "ACC/AHA Guidelines on Dual Antiplatelet Therapy, Section 7.2"
    }
  }
}
```

### 4.3 ML Execution Strategy (HealthTech)

* **Tier 1 (clinical entity parsing)** — BioBERT NER extracts/encodes medical
  tokens into RxNorm, SNOMED-CT, LOINC.
* **Tier 2 (grounded RAG)** — Med-PaLM-2 runs a constrained RAG loop against
  evidence repositories and openFDA to evaluate treatment safety.

---

## 5. Aegis Ledger — FinTech Transaction & Compliance Radar

Intercepts payment records, tracks money routing, and enforces AML/CFT
compliance.

### 5.1 Raw Transaction Event Ingestion

```json
{
  "transaction_metadata": {
    "timestamp": "2026-05-29T19:30:15.200Z",
    "transaction_id": "tx_fa7e9301b2c4",
    "ingress_channel": "SWIFT_ISO_20022_MX"
  },
  "payment_entities": {
    "originating_account": "acc_intl_88201492",
    "originating_routing_bic": "CHASUS33XXX",
    "destination_account": "acc_shell_77411209",
    "destination_routing_bic": "BPCKCY22XXX",
    "beneficiary_jurisdiction_country": "KY"
  },
  "financial_quantification": {
    "amount": 450000.00,
    "currency": "USD",
    "clearing_velocity_tier": "IMMEDIATE"
  },
  "velocity_features_1h": {
    "account_cumulative_volume_usd": 1250000.00,
    "distinct_beneficiaries_count_1h": 4,
    "historical_max_single_tx_ratio": 8.5
  }
}
```

### 5.2 Financial Risk & Fraud Assessment Output

```json
{
  "assessment_id": "fin_risk_88c7d2e1",
  "associated_transaction_id": "tx_fa7e9301b2c4",
  "compliance_decision": {
    "risk_score": 0.9180,
    "action_protocol": "HOLD_FOR_COMPLIANCE_REVIEW",
    "regulatory_triggers": ["BSA_31_CFR_1010", "FATF_Recommendation_16"]
  },
  "ml_fraud_indicators": {
    "structured_smurfing_probability": 0.892,
    "layered_routing_score": 0.941,
    "anomaly_model_version": "fin_isolation_forest_v4.2"
  },
  "nlp_compliance_grounding": {
    "entity_match_detected": true,
    "sanction_list_hits": [
      { "list_name": "OFAC_SDN_LIST", "matched_term": "Shell Corp Proxy Logistics", "confidence_match_score": 0.975 }
    ],
    "contextual_summary": "Flagged due to sudden asset-flight velocity targeting an offshore banking center. Entity matches active OFAC SDN proxy aliases."
  }
}
```

### 5.3 ML Execution Strategy (FinTech)

* **Tier 1 (sub-20ms outlier detection)** — Isolation Forest + tabular XGBoost
  ensemble scoring instant payment anomalies.
* **Tier 2 (semantic sanctions & layering)** — Tier-1 > 0.70 triggers FinBERT +
  Llama-3-Finance fuzzy matching across OFAC/EU/UN directories, producing
  suspicious-activity summaries mapped to BSA codes.

```
PROMPT TEMPLATE (Tier-2 compliance agent):
You are an expert financial-crimes compliance system. Evaluate the payment
profile below for money laundering, asset flight, and sanctions evasion.

### TRANSACTION DATA METRICS
- Originating Node: {originating_account} via BIC {originating_routing_bic}
- Destination Node: {destination_account} in Country: {beneficiary_jurisdiction_country}
- Ledger Amount: {amount} {currency}
- Velocity Max Variance Ratio: {historical_max_single_tx_ratio}

### MANDATE
Cross-reference entities against global AML frameworks. Return a structured
evaluation with classification ("CLEARED", "MONITOR_FLOW", "HOLD_FOR_REVIEW",
"BLOCK_TRANSACTION") and compliance reasoning. Do not introduce outside
assumptions.

### OUTPUT JSON
{ "sanction_hit_detected": bool, "risk_rating": "string",
  "compliance_justification": "string", "regulatory_framework_citation": "string" }
```

---

## 6. Shared Component Specifications & Performance

### 6.1 AG-Grid High-Density Configurations

Each domain reuses a shared grid infrastructure with domain-specific column
definitions (see `frontend/src/domains/*/columns.ts`):

* **Cyber** — anomaly-score progress bar with severity coloring.
* **Health** — pinned verify checkbox, interacting-compound value getter,
  severity cell-styling.
* **FinTech** — currency value formatter, monospace right-aligned amounts,
  fraud-index coloring.

### 6.2 Connection Transport Optimization

* **Cyber stream** — persistent WebSocket; backend buffers analytics and flushes
  a combined batch every **250 ms** to avoid UI-thread locking.
* **FinTech ledger** — WebSocket + strict queue manager; flagged transactions
  (risk > 0.70) surface within **50 ms**, regular updates are buffered.
* **HealthTech sync** — controlled long-poll / WebSocket with a **500 ms**
  heartbeat to keep the view stable for clinicians.

---

## 7. RBAC & Compliance Matrices

### 7.1 Cryptographic RBAC Matrix

| Institutional Role               | Module Tabs                 | API Scopes                        | Permitted Actions                                             |
| -------------------------------- | --------------------------- | --------------------------------- | ------------------------------------------------------------- |
| **Infrastructure Sec. Analyst**  | Cyber Threat Tower          | `cyber:read`, `cyber:remediate`   | Isolate node, invalidate sessions, block IPs                  |
| **Attending Clinical Provider**  | Clinical Support Hub        | `clinical:read`, `clinical:write` | Approve prescription overrides, sign chart records            |
| **FinTech Compliance Officer**   | FinTech Transaction Radar   | `fintech:read`, `fintech:transact`| Release hold, freeze beneficiary assets, file SAR             |
| **Institutional Governance Board** | Cyber, Clinical, FinTech, Admin | `cyber:*`, `clinical:*`, `fintech:*` | Modify AI thresholds, roll back model versions           |

### 7.2 Compliance Foundations

* **PCI-DSS v4.0 & FINRA (FinTech)** — column-level encryption (HMAC-SHA256),
  strict serializable ACID isolation.
* **HIPAA / PHI (HealthTech)** — patient charts isolated from telemetry &
  transactions; every view/mutation/override is audited.
* **SOC 2 Type II & ISO 42001 (Cyber)** — tracks system performance and pipeline
  changes; checks for model drift.

---

## 8. Cross-Domain Verification Tests

### 8.1 Cyber Ingress

```bash
curl -X POST 'http://localhost:8000/api/v1/cyber/telemetry/submit' \
  -H 'Authorization: Bearer <cyber_token>' \
  -H 'Content-Type: application/json' \
  -d '{ "source_ip": "185.220.101.5", "destination_ip": "10.0.4.112",
        "destination_port": 22, "protocol": "TCP",
        "bytes_transferred": 1420, "tcp_flags": ["SYN"] }'
```

Expected:

```json
{
  "status": "PROCESSED",
  "event_id": "evt_...",
  "tier_1_anomaly_detected": true,
  "anomaly_score": 0.9642,
  "websocket_broadcast_queued": true,
  "remediation_action_initiated": "ISOLATE_HOST"
}
```

### 8.2 HealthTech Reconcile

```bash
curl -X POST 'http://localhost:8000/api/v1/health/clinical/reconcile' \
  -H 'Authorization: Bearer <health_token>' \
  -H 'Content-Type: application/json' \
  -d '{ "patient_id": "pat_hex_992104",
        "proposed_prescription_code": "RxNorm:1191",
        "proposed_prescription_display": "Aspirin" }'
```

Expected:

```json
{
  "reconciliation_id": "rec_...",
  "patient_id": "pat_hex_992104",
  "contraindication_flag": true,
  "severity_level": "CRITICAL",
  "alert_message": "Severe Gastrointestinal Hemorrhage Risk detected via openFDA historical profile matching.",
  "required_human_actions": ["manual_override_checkbox_acknowledgement", "clinician_electronic_signature_seal"]
}
```

### 8.3 FinTech Evaluate

```bash
curl -X POST 'http://localhost:8000/api/v1/fintech/transaction/evaluate' \
  -H 'Authorization: Bearer <fintech_token>' \
  -H 'Content-Type: application/json' \
  -d '{ "originating_account": "acc_intl_88201492",
        "originating_routing_bic": "CHASUS33XXX",
        "destination_account": "acc_shell_77411209",
        "beneficiary_jurisdiction_country": "KY",
        "amount": 450000.00, "currency": "USD" }'
```

Expected:

```json
{
  "assessment_id": "fin_risk_...",
  "associated_transaction_id": "tx_...",
  "compliance_decision": {
    "risk_score": 0.9180,
    "action_protocol": "HOLD_FOR_COMPLIANCE_REVIEW",
    "regulatory_triggers": ["BSA_31_CFR_1010", "FATF_Recommendation_16"]
  },
  "sanction_hit_detected": true,
  "flagged_entity_alias": "Shell Corp Proxy Logistics"
}
```

---

## 9. Implementation Roadmap (Phased)

The reference implementation is delivered in four phases. Each phase is
independently runnable.

### Phase 1 — Backend Core
* FastAPI app + config.
* JWT issuance & verification, OAuth2 scopes, RBAC dependency guards.
* Gateway-style scope enforcement per `/api/v1/<domain>/*` prefix.
* In-process event bus + per-domain WebSocket broadcaster.

### Phase 2 — Domain Services
* `cyber`, `health`, `fintech` packages, each with: Pydantic schemas, a Tier-1 +
  Tier-2 mock inference engine, an in-memory store, REST endpoints (matching the
  verification tests), and a background event simulator.

### Phase 3 — Frontend SPA
* Vite + React + TypeScript + Zustand.
* Role login, scope-gated tabs, three-pane layout.
* AG-Grid grids per domain, live WebSocket ticker, context/action panel.

### Phase 4 — Integration
* `docker-compose` to run backend + frontend.
* Backend pytest suite covering the three verification tests + RBAC denials.
* End-to-end smoke run.

### Project Layout

```
AegisIOC/
├── AegisIOC.md           # this document
├── README.md             # quickstart
├── docker-compose.yml
├── backend/
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py            # app factory, gateway wiring
│   │   ├── config.py
│   │   ├── auth/              # jwt, scopes, rbac, login routes
│   │   ├── core/             # event bus, in-memory stores, ids
│   │   ├── domains/
│   │   │   ├── cyber/         # Aegis Threat: schemas, inference, service, routes, simulator
│   │   │   ├── health/        # Aegis Clinical
│   │   │   └── fintech/       # Aegis Ledger
│   │   └── ws/                # websocket routes
│   └── tests/
└── frontend/
    ├── package.json
    └── src/
        ├── api/              # rest + ws clients
        ├── store/            # zustand
        ├── auth/             # login
        ├── components/       # layout, ticker, context panel, topbar
        └── domains/          # cyber / health / fintech modules + columns
```

> **Security note:** the reference uses a static demo JWT secret and seeded demo
> users for local use only. Replace `SECRET_KEY` and wire a real IdP before any
> non-local deployment.
