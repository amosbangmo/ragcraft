"""Re-export for callers that imported the query-log payload from ``application.common``."""

from src.domain.query_log_ingress_payload import QueryLogIngressPayload

__all__ = ["QueryLogIngressPayload"]
