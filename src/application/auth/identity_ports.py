"""
Future identity resolution (JWT, OAuth) can implement this port.

Today FastAPI builds :class:`~src.application.auth.authenticated_principal.AuthenticatedPrincipal`
directly from the trusted ``X-User-Id`` header after syntactic validation.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.application.auth.authenticated_principal import AuthenticatedPrincipal


@runtime_checkable
class TrustedTransportIdentityPort(Protocol):
    """Maps an already-trusted opaque user id string into a principal record."""

    def principal_from_trusted_user_id(self, raw_user_id: str) -> AuthenticatedPrincipal: ...
