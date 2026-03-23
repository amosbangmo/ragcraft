"""Public system routes: liveness and version metadata (no auth)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from interfaces.http.main import create_app


def test_health_returns_ok() -> None:
    app = create_app()
    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


def test_version_returns_service_and_version_strings() -> None:
    app = create_app()
    with TestClient(app) as client:
        r = client.get("/version")
        assert r.status_code == 200
        body = r.json()
        assert "service" in body and "version" in body
        assert isinstance(body["service"], str) and len(body["service"].strip()) > 0
        assert isinstance(body["version"], str) and len(body["version"].strip()) > 0


def test_health_and_version_do_not_require_authorization() -> None:
    app = create_app()
    with TestClient(app) as client:
        assert client.get("/health", headers={"Authorization": "Bearer invalid"}).status_code == 200
        assert client.get("/version", headers={"Authorization": "Bearer invalid"}).status_code == 200
