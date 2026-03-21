from __future__ import annotations

import json
import threading
from pathlib import Path

from src.core.paths import get_data_root


class QueryLogRepository:
    """
    Append-only query log storage (newline-delimited JSON in a single file).

    Each line is one JSON object. Thread-safe for concurrent writers.
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

    def list_logs(self, *, project_id: str | None = None) -> list[dict]:
        try:
            with self._lock:
                if not self._path.is_file():
                    return []
                text = self._path.read_text(encoding="utf-8")
        except Exception:
            return []

        rows: list[dict] = []
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
            rows.append(row)
        return rows
