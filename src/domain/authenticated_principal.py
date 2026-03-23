"""Framework-agnostic identity passed from transport into application use cases."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuthenticatedPrincipal:
    """Workspace identity produced by the authentication port after verified bearer credentials."""

    user_id: str
    subject: str | None = None
    auth_method: str = "jwt_bearer"
    is_authenticated: bool = True
