"""End-to-end tests mirroring the spec's cross-domain verification tests."""


def test_login_and_me(client, analyst_headers):
    resp = client.get("/api/v1/auth/me", headers=analyst_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["role"] == "security_analyst"
    assert "cyber:read" in body["scopes"]
    assert body["tabs"] == ["cyber"]


def test_login_rejects_bad_password(client):
    resp = client.post("/api/v1/auth/login", json={"username": "analyst", "password": "wrong"})
    assert resp.status_code == 401


def test_unauthenticated_is_denied(client):
    resp = client.get("/api/v1/cyber/alerts")
    assert resp.status_code == 401


# --- 8.1 Cyber ingress ---
def test_cyber_telemetry_brute_force(client, analyst_headers):
    resp = client.post(
        "/api/v1/cyber/telemetry/submit",
        headers=analyst_headers,
        json={
            "source_ip": "185.220.101.5",
            "destination_ip": "10.0.4.112",
            "destination_port": 22,
            "protocol": "TCP",
            "bytes_transferred": 1420,
            "tcp_flags": ["SYN"],
            "failed_auth_attempts_1m": 42,
            "abuse_confidence_score": 98,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "PROCESSED"
    assert body["tier_1_anomaly_detected"] is True
    assert body["anomaly_score"] > 0.85
    assert body["remediation_action_initiated"] == "ISOLATE_HOST"


def test_cyber_remediation_requires_scope(client, governor_headers):
    # create an alert first
    submit = client.post(
        "/api/v1/cyber/telemetry/submit",
        headers=governor_headers,
        json={
            "source_ip": "45.155.205.233",
            "destination_ip": "10.0.4.55",
            "destination_port": 22,
            "bytes_transferred": 900,
            "tcp_flags": ["SYN"],
            "failed_auth_attempts_1m": 50,
            "abuse_confidence_score": 95,
        },
    )
    alert_id = submit.json()["alert_id"]
    resp = client.post(
        f"/api/v1/cyber/alerts/{alert_id}/remediate",
        headers=governor_headers,
        json={"action": "ISOLATE_HOST"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "APPLIED"


# --- 8.2 HealthTech reconcile ---
def test_health_reconcile_contraindication(client, clinician_headers):
    resp = client.post(
        "/api/v1/health/clinical/reconcile",
        headers=clinician_headers,
        json={
            "patient_id": "pat_hex_992104",
            "proposed_prescription_code": "RxNorm:1191",
            "proposed_prescription_display": "Aspirin",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["contraindication_flag"] is True
    assert body["severity_level"] == "CRITICAL"
    assert "manual_override_checkbox_acknowledgement" in body["required_human_actions"]


def test_health_reconcile_safe(client, clinician_headers):
    resp = client.post(
        "/api/v1/health/clinical/reconcile",
        headers=clinician_headers,
        json={
            "patient_id": "pat_hex_992104",
            "proposed_prescription_code": "RxNorm:161",
            "proposed_prescription_display": "Acetaminophen",
        },
    )
    assert resp.json()["contraindication_flag"] is False


# --- 8.3 FinTech evaluate ---
def test_fintech_evaluate_sanction_hit(client, officer_headers):
    resp = client.post(
        "/api/v1/fintech/transaction/evaluate",
        headers=officer_headers,
        json={
            "originating_account": "acc_intl_88201492",
            "originating_routing_bic": "CHASUS33XXX",
            "destination_account": "acc_shell_77411209",
            "beneficiary_jurisdiction_country": "KY",
            "amount": 450000.00,
            "currency": "USD",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["sanction_hit_detected"] is True
    assert body["flagged_entity_alias"] == "Shell Corp Proxy Logistics"
    assert body["compliance_decision"]["risk_score"] > 0.70


# --- RBAC cross-domain denial ---
def test_analyst_cannot_access_fintech(client, analyst_headers):
    resp = client.post(
        "/api/v1/fintech/transaction/evaluate",
        headers=analyst_headers,
        json={
            "originating_account": "a",
            "originating_routing_bic": "X",
            "destination_account": "b",
            "beneficiary_jurisdiction_country": "US",
            "amount": 10.0,
            "currency": "USD",
        },
    )
    assert resp.status_code == 403


def test_governor_has_all_domains(client, governor_headers):
    assert client.get("/api/v1/cyber/alerts", headers=governor_headers).status_code == 200
    assert client.get("/api/v1/health/clinical/reports", headers=governor_headers).status_code == 200
    assert client.get("/api/v1/fintech/assessments", headers=governor_headers).status_code == 200
