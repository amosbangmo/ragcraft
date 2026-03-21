from __future__ import annotations

from datetime import datetime, timezone

from src.services.query_log_service import QueryLogService


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
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class ListRetrievalQueryLogsUseCase:
    """List persisted query / retrieval logs (SQLite), optionally filtered by time and limit."""

    def __init__(self, *, query_log_service: QueryLogService) -> None:
        self._logs = query_log_service

    def execute(
        self,
        *,
        user_id: str,
        project_id: str,
        since_iso: str | None = None,
        until_iso: str | None = None,
        last_n: int | None = None,
    ) -> list[dict]:
        since_utc = _parse_iso_utc(since_iso)
        until_utc = _parse_iso_utc(until_iso)
        return self._logs.load_logs(
            project_id=project_id,
            user_id=user_id,
            since_utc=since_utc,
            until_utc=until_utc,
            last_n=last_n,
        )
