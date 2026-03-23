"""Environment-backed settings for HS256 workspace access tokens (no secrets in code)."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _strip_env(name: str) -> str | None:
    v = os.getenv(name)
    if v is None:
        return None
    s = v.strip()
    return s or None


@dataclass(frozen=True, slots=True)
class JwtAuthSettings:
    secret: str
    algorithm: str = "HS256"
    issuer: str | None = None
    audience: str | None = None
    access_token_expire_minutes: int = 60

    @classmethod
    def from_env(cls) -> JwtAuthSettings:
        secret = _strip_env("RAGCRAFT_JWT_SECRET")
        if not secret:
            raise ValueError(
                "RAGCRAFT_JWT_SECRET is required for API bearer authentication "
                "(set a long random secret; never commit it)."
            )
        issuer = _strip_env("RAGCRAFT_JWT_ISSUER")
        audience = _strip_env("RAGCRAFT_JWT_AUDIENCE")
        algo = _strip_env("RAGCRAFT_JWT_ALGORITHM") or "HS256"
        exp_raw = _strip_env("RAGCRAFT_ACCESS_TOKEN_EXPIRE_MINUTES")
        try:
            expire_minutes = int(exp_raw) if exp_raw else 60
        except ValueError:
            expire_minutes = 60
        return cls(
            secret=secret,
            algorithm=algo,
            issuer=issuer,
            audience=audience,
            access_token_expire_minutes=max(1, min(expire_minutes, 60 * 24 * 30)),
        )
