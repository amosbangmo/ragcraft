from __future__ import annotations

from datetime import datetime, timezone

from src.infrastructure.logging.query_log_repository import QueryLogRepository

_MAX_TEXT_FIELD_LEN = 2000
_MAX_LIST_IDS = 200


def _truncate_str(value: str | None, max_len: int) -> str | None:
    if value is None:
        return None
    if len(value) <= max_len:
        return value
    return value[: max_len - 1] + "…"


def _normalize_id_list(value: object) -> list[str] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        return None
    out: list[str] = []
    for item in value[:_MAX_LIST_IDS]:
        if item is None:
            continue
        out.append(str(item))
    return out


class QueryLogService:
    def __init__(self, repository: QueryLogRepository | None = None) -> None:
        self._repository = repository or QueryLogRepository()

    def log_query(self, *, payload: dict) -> None:
        try:
            entry = self._build_entry(payload)
            self._repository.log(entry)
        except Exception:
            return

    def _build_entry(self, payload: dict) -> dict:
        ts = payload.get("timestamp")
        if not isinstance(ts, str) or not ts.strip():
            ts = datetime.now(timezone.utc).isoformat()

        question = payload.get("question")
        rewritten = payload.get("rewritten_query")
        answer = payload.get("answer")

        q_str = question if isinstance(question, str) else (None if question is None else str(question))
        rw_str = rewritten if isinstance(rewritten, str) else (None if rewritten is None else str(rewritten))
        ans_str = answer if isinstance(answer, str) else (None if answer is None else str(answer))

        confidence = payload.get("confidence")
        conf_val: float | None
        if confidence is None:
            conf_val = None
        else:
            try:
                conf_val = float(confidence)
            except (TypeError, ValueError):
                conf_val = None

        latency = payload.get("latency_ms")
        lat_val: int | None
        if latency is None:
            lat_val = None
        else:
            try:
                lat_val = int(round(float(latency)))
            except (TypeError, ValueError):
                lat_val = None

        project_id = payload.get("project_id")
        user_id = payload.get("user_id")
        proj_str = project_id if isinstance(project_id, str) else (None if project_id is None else str(project_id))
        user_str = user_id if isinstance(user_id, str) else (None if user_id is None else str(user_id))

        return {
            "question": _truncate_str(q_str, _MAX_TEXT_FIELD_LEN),
            "rewritten_query": _truncate_str(rw_str, _MAX_TEXT_FIELD_LEN),
            "project_id": proj_str,
            "user_id": user_str,
            "selected_doc_ids": _normalize_id_list(payload.get("selected_doc_ids")),
            "retrieved_doc_ids": _normalize_id_list(payload.get("retrieved_doc_ids")),
            "latency_ms": lat_val,
            "confidence": conf_val,
            "answer": _truncate_str(ans_str, _MAX_TEXT_FIELD_LEN),
            "timestamp": ts,
        }
