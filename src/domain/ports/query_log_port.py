from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class QueryLogPort(Protocol):
    """
    Application-level query observability (structured ingest + listing).

    ``payload`` is a plain dict or :class:`~src.application.common.query_log_payload.QueryLogIngressPayload`
    (avoid importing that type here to keep domain free of application dependencies).

    Implemented by :class:`~src.infrastructure.adapters.query_logging.query_log_service.QueryLogService`; SQLite persistence
    remains behind :class:`~src.domain.shared.query_log_port.QueryLogPersistencePort`.
    """

    def log_query(self, *, payload: Any) -> None: ...

    def load_logs(
        self,
        *,
        project_id: str | None = None,
        user_id: str | None = None,
        since_utc: datetime | None = None,
        until_utc: datetime | None = None,
        last_n: int | None = None,
    ) -> list[dict]: ...
