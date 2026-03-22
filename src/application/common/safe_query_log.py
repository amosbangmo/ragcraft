from __future__ import annotations

from typing import Any

from src.domain.query_log_ingress_payload import QueryLogIngressPayload


def log_query_safely(
    query_log_service: Any,
    payload: QueryLogIngressPayload | dict[str, Any],
) -> None:
    if query_log_service is None:
        return
    try:
        raw = payload.to_log_dict() if isinstance(payload, QueryLogIngressPayload) else payload
        query_log_service.log_query(payload=raw)
    except Exception:
        pass
