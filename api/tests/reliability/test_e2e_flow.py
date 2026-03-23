"""Short HTTP chain: project → ingest → ask (stubbed use cases, no real vector store)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.bearer_auth import bearer_headers
from interfaces.http.schemas.chat import ChatAskResponse
from interfaces.http.schemas.projects import CreateProjectResponse, IngestDocumentResponse


@pytest.mark.reliability
def test_project_ingest_ask_chain(e2e_flow_client: tuple[TestClient, FastAPI]) -> None:
    tc, _ = e2e_flow_client
    uid = "reliability-e2e-user"
    project_id = "reliability-e2e-project"
    h = bearer_headers(user_id=uid)

    r0 = tc.post("/projects", headers=h, json={"project_id": project_id})
    assert r0.status_code == 201
    created = CreateProjectResponse.model_validate(r0.json())
    assert created.project_id == project_id

    r1 = tc.post(
        f"/projects/{project_id}/documents/ingest",
        headers=h,
        files={"file": ("note.txt", b"reliability", "text/plain")},
    )
    assert r1.status_code == 200
    ing = IngestDocumentResponse.model_validate(r1.json())
    assert len(ing.raw_assets) >= 1

    r2 = tc.post(
        "/chat/ask",
        headers=h,
        json={"project_id": project_id, "question": "What did we ingest?"},
    )
    assert r2.status_code == 200
    ask = ChatAskResponse.model_validate(r2.json())
    assert ask.status == "answered"
    assert ask.answer == "reliability-e2e-answer"
