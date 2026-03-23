from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path

from domain.common.retrieval_query_log_record import (
    RetrievalQueryLogRecord,
    retrieval_query_log_record_from_plain_mapping,
)
from domain.common.shared.query_log_port import QueryLogPersistencePort
from infrastructure.config.paths import get_data_root


def _parse_entry_timestamp(entry: dict) -> datetime | None:
    raw = entry.get("timestamp")
    if not isinstance(raw, str) or not raw.strip():
        return None
    s = raw.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


QueryLogStore = QueryLogPersistencePort


class QueryLogRepository:
    """
    Append-only query log storage (newline-delimited JSON in a single file).

    Each line is one JSON object. Thread-safe for concurrent writers.
    File-based store for tests and optional one-off import paths (see ``QueryLogService.import_legacy_file_logs``).
    """

    def __init__(self, *, log_path: Path | None = None) -> None:
        root = log_path if log_path is not None else get_data_root() / "logs" / "query_logs.json"
        self._path = Path(root)
        self._lock = threading.Lock()

    def _ensure_parent(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, entry: dict) -> None:
        try:
            line = json.dumps(entry, ensure_ascii=False) + "\n"
            with self._lock:
                self._ensure_parent()
                with self._path.open("a", encoding="utf-8") as handle:
                    handle.write(line)
                    handle.flush()
        except Exception:
            return

    def list_logs(
        self,
        *,
        project_id: str | None = None,
        user_id: str | None = None,
        since_created_at: str | None = None,
        until_created_at: str | None = None,
        limit: int | None = None,
    ) -> list[RetrievalQueryLogRecord]:
        try:
            with self._lock:
                if not self._path.is_file():
                    return []
                text = self._path.read_text(encoding="utf-8")
        except Exception:
            return []

        rows: list[RetrievalQueryLogRecord] = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            if project_id is not None and row.get("project_id") != project_id:
                continue
            if user_id is not None and row.get("user_id") != user_id:
                continue
            ts = _parse_entry_timestamp(row)
            if since_created_at is not None and since_created_at.strip():
                since_dt = _parse_entry_timestamp({"timestamp": since_created_at})
                if since_dt is not None and (ts is None or ts < since_dt):
                    continue
            if until_created_at is not None and until_created_at.strip():
                until_dt = _parse_entry_timestamp({"timestamp": until_created_at})
                if until_dt is not None and (ts is None or ts > until_dt):
                    continue
            rows.append(retrieval_query_log_record_from_plain_mapping(row))

        rows.sort(
            key=lambda r: _parse_entry_timestamp(r.to_log_entry_dict()) or datetime.min.replace(tzinfo=UTC),
            reverse=True,
        )
        if limit is not None and limit >= 0:
            rows = rows[: int(limit)]
        return rows
