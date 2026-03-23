"""Mint real JWTs for API tests (uses ``RAGCRAFT_JWT_SECRET`` from the environment)."""

from __future__ import annotations

from src.infrastructure.adapters.auth.jwt_auth_settings import JwtAuthSettings
from src.infrastructure.adapters.auth.jwt_authentication_adapter import JwtAuthenticationAdapter


def bearer_headers(*, user_id: str, subject: str | None = None) -> dict[str, str]:
    adapter = JwtAuthenticationAdapter(JwtAuthSettings.from_env())
    token = adapter.issue_access_token(user_id=user_id, subject=subject)
    return {"Authorization": f"Bearer {token}"}
