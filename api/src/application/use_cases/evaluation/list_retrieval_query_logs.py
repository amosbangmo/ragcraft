from __future__ import annotations

from datetime import UTC, datetime

from application.dto.evaluation import ListRetrievalQueryLogsQuery
from domain.common.ports import QueryLogPort


def _parse_iso_utc(value: str | None) -> datetime | None:
    if value is None or not str(value).strip():
        return None
    s = str(value).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


class ListRetrievalQueryLogsUseCase:
    """List persisted query / retrieval logs (SQLite), optionally filtered by time and limit."""

    def __init__(self, *, query_log: QueryLogPort) -> None:
        self._logs = query_log

    def execute(self, query: ListRetrievalQueryLogsQuery) -> list[dict]:
        since_utc = _parse_iso_utc(query.since_iso)
        until_utc = _parse_iso_utc(query.until_iso)
        return self._logs.load_logs(
            project_id=query.project_id,
            user_id=query.user_id,
            since_utc=since_utc,
            until_utc=until_utc,
            last_n=query.last_n,
        )
