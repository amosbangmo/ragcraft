from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from infrastructure.config.exceptions import ExpiredTokenError, InvalidTokenError
from infrastructure.auth.jwt_auth_settings import JwtAuthSettings
from infrastructure.auth.jwt_authentication_adapter import JwtAuthenticationAdapter


@pytest.fixture
def adapter() -> JwtAuthenticationAdapter:
    return JwtAuthenticationAdapter(
        JwtAuthSettings(
            secret=os.environ["RAGCRAFT_JWT_SECRET"],
            algorithm="HS256",
            issuer=None,
            audience=None,
            access_token_expire_minutes=60,
        )
    )


def test_issue_and_authenticate_round_trip(adapter: JwtAuthenticationAdapter) -> None:
    tok = adapter.issue_access_token(user_id="user-99", subject="alice")
    p = adapter.authenticate_bearer_token(tok)
    assert p.user_id == "user-99"
    assert p.subject == "alice"
    assert p.auth_method == "jwt_bearer"
    assert p.is_authenticated is True


def test_authenticate_expired_token(adapter: JwtAuthenticationAdapter) -> None:
    secret = os.environ["RAGCRAFT_JWT_SECRET"]
    past = int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp())
    payload = {"sub": "u", "user_id": "u", "iat": past - 3600, "exp": past}
    tok = jwt.encode(payload, secret, algorithm="HS256")
    with pytest.raises(ExpiredTokenError):
        adapter.authenticate_bearer_token(tok)


def test_authenticate_wrong_secret() -> None:
    a = JwtAuthenticationAdapter(
        JwtAuthSettings(
            secret="a" * 40,
            algorithm="HS256",
            issuer=None,
            audience=None,
            access_token_expire_minutes=60,
        )
    )
    tok = a.issue_access_token(user_id="x")
    b = JwtAuthenticationAdapter(
        JwtAuthSettings(
            secret="b" * 40,
            algorithm="HS256",
            issuer=None,
            audience=None,
            access_token_expire_minutes=60,
        )
    )
    with pytest.raises(InvalidTokenError):
        b.authenticate_bearer_token(tok)


def test_authenticate_garbage_token(adapter: JwtAuthenticationAdapter) -> None:
    with pytest.raises(InvalidTokenError):
        adapter.authenticate_bearer_token("not-a-jwt")
