"""Framework-agnostic identity passed from transport into application use cases."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuthenticatedPrincipal:
    """Trusted workspace user identity (today: derived from ``X-User-Id``)."""

    user_id: str
    auth_method: str = "x_user_id_header"
    is_authenticated: bool = True
