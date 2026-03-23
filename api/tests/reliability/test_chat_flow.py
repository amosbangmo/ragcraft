"""Chat flow: bearer + ``POST /chat/ask`` returns an answered payload."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.bearer_auth import bearer_headers
from interfaces.http.schemas.chat import ChatAskResponse


@pytest.mark.reliability
def test_chat_ask_flow_returns_answered(chat_flow_client: tuple[TestClient, FastAPI]) -> None:
    tc, _ = chat_flow_client
    uid = "reliability-chat-user"
    project_id = "reliability-chat-project"
    h = bearer_headers(user_id=uid)
    r = tc.post(
        "/chat/ask",
        headers=h,
        json={"project_id": project_id, "question": "Hello reliability?"},
    )
    assert r.status_code == 200
    body = ChatAskResponse.model_validate(r.json())
    assert body.status == "answered"
    assert body.answer == "reliability-chat-answer"
    assert body.confidence == pytest.approx(0.9)
