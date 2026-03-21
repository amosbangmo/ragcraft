from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from src.domain.query_intent import QueryIntent
from src.infrastructure.logging.query_log_repository import QueryLogRepository, QueryLogStore
from src.infrastructure.logging.sqlite_query_log_repository import SQLiteQueryLogRepository


def parse_query_log_timestamp(entry: dict) -> datetime | None:
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
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

_MAX_TEXT_FIELD_LEN = 2000
_MAX_LIST_IDS = 200
_VALID_QUERY_INTENTS = frozenset(i.value for i in QueryIntent)


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
    def __init__(self, repository: QueryLogStore | None = None) -> None:
        self._repository = repository or SQLiteQueryLogRepository()

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

        def _optional_stage_ms(key: str) -> int | None:
            raw = payload.get(key)
            if raw is None:
                return None
            try:
                return int(round(float(raw)))
            except (TypeError, ValueError):
                return None

        project_id = payload.get("project_id")
        user_id = payload.get("user_id")
        proj_str = project_id if isinstance(project_id, str) else (None if project_id is None else str(project_id))
        user_str = user_id if isinstance(user_id, str) else (None if user_id is None else str(user_id))

        entry: dict = {
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

        for stage_key in (
            "query_rewrite_ms",
            "retrieval_ms",
            "reranking_ms",
            "prompt_build_ms",
            "answer_generation_ms",
            "total_latency_ms",
        ):
            stage_val = _optional_stage_ms(stage_key)
            if stage_val is not None:
                entry[stage_key] = stage_val

        h = payload.get("hybrid_retrieval_enabled")
        if h is not None:
            entry["hybrid_retrieval_enabled"] = bool(h)
        rm = payload.get("retrieval_mode")
        if isinstance(rm, str) and rm.strip():
            entry["retrieval_mode"] = rm.strip()

        qi = payload.get("query_intent")
        if isinstance(qi, str):
            s = qi.strip()
            if s in _VALID_QUERY_INTENTS:
                entry["query_intent"] = s

        rs = payload.get("retrieval_strategy")
        if isinstance(rs, dict):
            strat: dict[str, object] = {}
            if "k" in rs:
                try:
                    strat["k"] = int(rs["k"])
                except (TypeError, ValueError):
                    pass
            if "use_hybrid" in rs:
                strat["use_hybrid"] = bool(rs["use_hybrid"])
            if "apply_filters" in rs:
                strat["apply_filters"] = bool(rs["apply_filters"])
            if strat:
                entry["retrieval_strategy"] = strat

        for ck in ("context_compression_chars_before", "context_compression_chars_after"):
            raw_cc = payload.get(ck)
            if raw_cc is None:
                continue
            try:
                entry[ck] = int(round(float(raw_cc)))
            except (TypeError, ValueError):
                pass

        cc_ratio = payload.get("context_compression_ratio")
        if cc_ratio is not None:
            try:
                entry["context_compression_ratio"] = float(cc_ratio)
            except (TypeError, ValueError):
                pass

        for sec_key in ("section_expansion_count", "expanded_assets_count"):
            raw_sec = payload.get(sec_key)
            if raw_sec is None:
                continue
            try:
                entry[sec_key] = int(round(float(raw_sec)))
            except (TypeError, ValueError):
                pass

        ta = payload.get("table_aware_qa_enabled")
        if ta is not None:
            entry["table_aware_qa_enabled"] = bool(ta)

        return entry

    def load_logs(
        self,
        *,
        project_id: str | None = None,
        user_id: str | None = None,
        since_utc: datetime | None = None,
        until_utc: datetime | None = None,
        last_n: int | None = None,
    ) -> list[dict]:
        since_s = since_utc.isoformat() if since_utc is not None else None
        until_s = until_utc.isoformat() if until_utc is not None else None
        return self._repository.list_logs(
            project_id=project_id,
            user_id=user_id,
            since_created_at=since_s,
            until_created_at=until_s,
            limit=last_n,
        )

    def import_legacy_file_logs(self, *, log_path: Path | None = None) -> int:
        """
        One-time import from newline-delimited JSON (legacy file store).
        Re-importing the same file may create duplicate rows in SQLite.
        """
        try:
            legacy = QueryLogRepository(log_path=log_path)
            records = legacy.list_logs()
            if not records:
                return 0
            sink = SQLiteQueryLogRepository()
            for entry in records:
                sink.log(entry)
            return len(records)
        except Exception:
            return 0
