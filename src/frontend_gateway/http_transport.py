"""Low-level HTTP calls with explicit ``X-User-Id`` on every request."""

from __future__ import annotations

import json
from typing import Any

import httpx

from src.frontend_gateway.errors import BackendHttpError
from src.frontend_gateway.http_error_map import raise_for_api_response


class HttpTransport:
    """
    ``user_id`` is sent as ``X-User-Id`` on **every** request (including routes that also embed
    ``user_id`` in the JSON body) so the API sees a single explicit workspace identity header.
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
        user_id: str = "",
        json_body: Any | None = None,
        params: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        send_user_header: bool = True,
    ) -> Any:
        path = path if path.startswith("/") else f"/{path}"
        headers: dict[str, str] = {}
        if send_user_header:
            uid = str(user_id).strip()
            if not uid:
                raise BackendHttpError(
                    "X-User-Id is required for this call but user_id was empty.",
                    status_code=None,
                    payload=None,
                )
            headers["X-User-Id"] = uid
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
            raise BackendHttpError(f"HTTP request failed: {exc}", status_code=None, payload=None) from exc

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
