"""Low-level HTTP calls with ``Authorization: Bearer`` for authenticated routes."""

from __future__ import annotations

import json
from typing import Any

import httpx

from services.errors import BackendHttpError
from services.http_error_map import raise_for_api_response


class HttpTransport:
    """
    Authenticated calls send ``Authorization: Bearer <access_token>`` (JWT from ``/auth/login`` or
    ``/auth/register``). The token carries the workspace ``user_id``; callers must not spoof identity
    via separate headers.
    """

    __slots__ = ("_client", "_base")

    def __init__(
        self,
        *,
        base_url: str,
        connect_timeout: float = 10.0,
        read_timeout: float = 300.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base = base_url.rstrip("/")
        timeout = httpx.Timeout(
            connect=connect_timeout,
            read=read_timeout,
            write=read_timeout,
            pool=connect_timeout,
        )
        client_kw: dict[str, Any] = {"base_url": self._base, "timeout": timeout}
        if transport is not None:
            client_kw["transport"] = transport
        self._client = httpx.Client(**client_kw)

    def close(self) -> None:
        self._client.close()

    def request_json(
        self,
        method: str,
        path: str,
        *,
        bearer_token: str = "",
        json_body: Any | None = None,
        params: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        send_authorization: bool = True,
    ) -> Any:
        path = path if path.startswith("/") else f"/{path}"
        headers: dict[str, str] = {}
        if send_authorization:
            tok = str(bearer_token).strip()
            if not tok:
                raise BackendHttpError(
                    "Bearer access token is required for this call but none was provided.",
                    status_code=None,
                    payload=None,
                )
            headers["Authorization"] = f"Bearer {tok}"
        try:
            req_kw: dict[str, Any] = {
                "headers": headers,
                "params": params,
                "files": files,
                "data": data,
            }
            if json_body is not None and files is None:
                req_kw["json"] = json_body
            resp = self._client.request(method, path, **req_kw)
        except httpx.RequestError as exc:
            raise BackendHttpError(
                f"HTTP request failed: {exc}", status_code=None, payload=None
            ) from exc

        if httpx.codes.is_success(resp.status_code):
            if not resp.content:
                return None
            try:
                return resp.json()
            except json.JSONDecodeError as exc:
                raise BackendHttpError(
                    "Response was not valid JSON.",
                    status_code=resp.status_code,
                    payload=None,
                ) from exc

        payload: dict[str, Any] | None = None
        try:
            raw = resp.json()
            if isinstance(raw, dict):
                payload = raw
        except json.JSONDecodeError:
            payload = None

        raise_for_api_response(resp.status_code, payload, resp.text)
