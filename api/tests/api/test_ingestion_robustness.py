"""API-layer robustness: bad inputs return structured errors, not uncaught exceptions."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.bearer_auth import bearer_headers
from interfaces.http.main import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_ingest_without_file_returns_422(client: TestClient) -> None:
    r = client.post(
        "/projects/p1/documents/ingest",
        headers=bearer_headers(user_id="robust-user"),
        data={},
    )
    assert r.status_code == 422


def test_ask_empty_body_returns_422(client: TestClient) -> None:
    r = client.post(
        "/chat/ask",
        headers=bearer_headers(user_id="robust-user"),
        json={},
    )
    assert r.status_code == 422


def test_projects_list_without_auth_returns_401(client: TestClient) -> None:
    r = client.get("/projects")
    assert r.status_code == 401
