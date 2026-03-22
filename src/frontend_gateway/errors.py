"""Errors raised by the HTTP :class:`~src.frontend_gateway.http_client.HttpBackendClient`."""

from __future__ import annotations

from typing import Any


class BackendHttpError(Exception):
    """
    Raised when the API returns a non-success status or an unreadable body.

    ``payload`` is the parsed JSON object when the server returned an API error body
    (``detail``, ``message``, ``code``, …); otherwise ``None``.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload
