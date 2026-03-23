"""
Legacy bridge: map an already-trusted opaque user id into a principal.

Production HTTP uses :class:`~src.domain.ports.authentication_port.AuthenticationPort` with
signed bearer tokens instead of trusting client-supplied user ids.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.domain.authenticated_principal import AuthenticatedPrincipal


@runtime_checkable
class TrustedTransportIdentityPort(Protocol):
    """Maps an already-trusted opaque user id string into a principal record."""

    def principal_from_trusted_user_id(self, raw_user_id: str) -> AuthenticatedPrincipal: ...
