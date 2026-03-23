from __future__ import annotations

from src.domain.ports.query_log_port import QueryLogPort
from src.domain.query_log_ingress_payload import QueryLogIngressPayload


def log_query_safely(
    query_log_service: QueryLogPort | None,
    payload: QueryLogIngressPayload,
) -> None:
    if query_log_service is None:
        return
    try:
        query_log_service.log_query(payload=payload.to_log_dict())
    except Exception:
        pass
