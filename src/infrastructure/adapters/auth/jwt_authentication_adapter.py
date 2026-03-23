"""JWT issue + validate for workspace bearer authentication."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError as PyJWTInvalidTokenError

from src.application.auth.access_token_issuer_port import AccessTokenIssuerPort
from src.application.auth.authenticated_principal import AuthenticatedPrincipal
from src.application.auth.authentication_port import AuthenticationPort
from src.core.exceptions import ExpiredTokenError, InvalidTokenError
from src.infrastructure.adapters.auth.jwt_auth_settings import JwtAuthSettings


class JwtAuthenticationAdapter(AuthenticationPort, AccessTokenIssuerPort):
    """Sign and verify HS256 JWTs; maps ``user_id`` claim to :class:`AuthenticatedPrincipal`."""

    __slots__ = ("_settings",)

    def __init__(self, settings: JwtAuthSettings) -> None:
        self._settings = settings

    def issue_access_token(self, *, user_id: str, subject: str | None = None) -> str:
        uid = str(user_id).strip()
        if not uid:
            raise ValueError("user_id is required to issue an access token")
        now = datetime.now(timezone.utc)
        exp = now + timedelta(minutes=self._settings.access_token_expire_minutes)
        payload: dict[str, str | int] = {
            "sub": subject or uid,
            "user_id": uid,
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
        }
        if self._settings.issuer:
            payload["iss"] = self._settings.issuer
        if self._settings.audience:
            payload["aud"] = self._settings.audience
        return jwt.encode(payload, self._settings.secret, algorithm=self._settings.algorithm)

    def authenticate_bearer_token(self, raw_token: str) -> AuthenticatedPrincipal:
        token = str(raw_token).strip()
        if not token:
            raise InvalidTokenError("empty bearer token", user_message="Invalid or missing access token.")

        decode_kw: dict[str, object] = {
            "algorithms": [self._settings.algorithm],
            "options": {"require": ["exp", "iat", "sub", "user_id"]},
        }
        if self._settings.issuer:
            decode_kw["issuer"] = self._settings.issuer
        if self._settings.audience:
            decode_kw["audience"] = self._settings.audience

        try:
            claims = jwt.decode(token, self._settings.secret, **decode_kw)
        except ExpiredSignatureError as exc:
            raise ExpiredTokenError(
                "jwt expired",
                user_message="Access token expired. Please sign in again.",
            ) from exc
        except PyJWTInvalidTokenError as exc:
            raise InvalidTokenError(
                "jwt invalid",
                user_message="Invalid access token.",
            ) from exc

        uid = str(claims.get("user_id") or "").strip()
        if not uid:
            raise InvalidTokenError(
                "jwt missing user_id",
                user_message="Invalid access token.",
            )
        sub = str(claims.get("sub") or uid)
        return AuthenticatedPrincipal(user_id=uid, subject=sub, auth_method="jwt_bearer", is_authenticated=True)
