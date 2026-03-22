from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import app


def test_health_returns_ok() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_version_returns_metadata() -> None:
    client = TestClient(app)
    response = client.get("/version")
    assert response.status_code == 200
    body = response.json()
    assert "service" in body and "version" in body
    assert isinstance(body["service"], str) and body["service"]
    assert isinstance(body["version"], str) and body["version"]
