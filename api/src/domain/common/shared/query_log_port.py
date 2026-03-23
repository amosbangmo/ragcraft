from __future__ import annotations

from typing import Protocol, runtime_checkable

from domain.common.retrieval_query_log_record import RetrievalQueryLogRecord


@runtime_checkable
class QueryLogPersistencePort(Protocol):
    """Append and query structured query observability records."""

    def log(self, entry: dict) -> None: ...

    def list_logs(
        self,
        *,
        project_id: str | None = None,
        user_id: str | None = None,
        since_created_at: str | None = None,
        until_created_at: str | None = None,
        limit: int | None = None,
    ) -> list[RetrievalQueryLogRecord]: ...
