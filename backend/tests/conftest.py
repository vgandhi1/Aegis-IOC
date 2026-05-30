import os

import pytest
from fastapi.testclient import TestClient

# Disable background simulators for deterministic tests before settings load.
os.environ["AEGIS_ENABLE_SIMULATORS"] = "false"

from app.config import get_settings  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def _token(client: TestClient, username: str) -> str:
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": "demo"})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture
def analyst_headers(client):
    return {"Authorization": f"Bearer {_token(client, 'analyst')}"}


@pytest.fixture
def clinician_headers(client):
    return {"Authorization": f"Bearer {_token(client, 'clinician')}"}


@pytest.fixture
def officer_headers(client):
    return {"Authorization": f"Bearer {_token(client, 'officer')}"}


@pytest.fixture
def governor_headers(client):
    return {"Authorization": f"Bearer {_token(client, 'governor')}"}
