"""Issue signed access tokens after successful login/registration (adapter in infrastructure)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class AccessTokenIssuerPort(Protocol):
    """Create a bearer token string for a persisted workspace user id."""

    def issue_access_token(self, *, user_id: str, subject: str | None = None) -> str: ...
