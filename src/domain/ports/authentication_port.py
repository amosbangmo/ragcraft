"""Port for verifying bearer access tokens (implemented in infrastructure)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.domain.authenticated_principal import AuthenticatedPrincipal


@runtime_checkable
class AuthenticationPort(Protocol):
    """Validate a raw JWT (or other) bearer secret and return a typed workspace principal."""

    def authenticate_bearer_token(self, raw_token: str) -> AuthenticatedPrincipal: ...
