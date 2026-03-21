from __future__ import annotations

from typing import Any

from src.application.common.query_log_payload import QueryLogIngressPayload
from src.services.query_log_service import QueryLogService


def log_query_safely(
    query_log_service: QueryLogService | None,
    payload: QueryLogIngressPayload | dict[str, Any],
) -> None:
    if query_log_service is None:
        return
    try:
        raw = payload.to_log_dict() if isinstance(payload, QueryLogIngressPayload) else payload
        query_log_service.log_query(payload=raw)
    except Exception:
        pass
