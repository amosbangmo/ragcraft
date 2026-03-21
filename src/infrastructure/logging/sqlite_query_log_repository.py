from __future__ import annotations

import json
from datetime import datetime, timezone

from src.infrastructure.persistence.db import get_connection


def _json_list(value: object | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False)
    return None


def _parse_json_list(raw: str | None) -> list[str] | None:
    if raw is None or not raw.strip():
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, list):
        return None
    return [str(x) for x in data]


def _maybe_int_ms(value: object | None) -> int | None:
    if value is None:
        return None
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def _maybe_float(value: object | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _retrieval_strategy_columns(entry: dict) -> tuple[int | None, int | None, int | None]:
    rs = entry.get("retrieval_strategy")
    if not isinstance(rs, dict):
        return None, None, None
    k_sql: int | None = None
    try:
        k_raw = rs.get("k")
        if k_raw is not None:
            k_sql = int(k_raw)
    except (TypeError, ValueError):
        k_sql = None
    uh = rs.get("use_hybrid")
    uh_sql = None if uh is None else (1 if bool(uh) else 0)
    af = rs.get("apply_filters")
    af_sql = None if af is None else (1 if bool(af) else 0)
    return k_sql, uh_sql, af_sql


class SQLiteQueryLogRepository:
    """
    Persist query observability rows in SQLite (separate from docstore tables).
    """

    def log(self, entry: dict) -> None:
        try:
            question = entry.get("question")
            q = question if isinstance(question, str) else ("" if question is None else str(question))

            created_at = entry.get("timestamp")
            if not isinstance(created_at, str) or not created_at.strip():
                created_at = datetime.now(timezone.utc).isoformat()

            hybrid = entry.get("hybrid_retrieval_enabled")
            hybrid_sql = None if hybrid is None else (1 if bool(hybrid) else 0)

            qi = entry.get("query_intent")
            qi_sql = qi.strip() if isinstance(qi, str) and qi.strip() else None

            rsk, rs_hybrid, rs_filters = _retrieval_strategy_columns(entry)

            params = (
                entry.get("user_id"),
                entry.get("project_id"),
                q,
                entry.get("rewritten_query"),
                entry.get("retrieval_mode"),
                hybrid_sql,
                _json_list(entry.get("selected_doc_ids")),
                _json_list(entry.get("retrieved_doc_ids")),
                _maybe_float(entry.get("confidence")),
                entry.get("answer"),
                _maybe_float(entry.get("latency_ms")),
                _maybe_float(entry.get("query_rewrite_ms")),
                _maybe_float(entry.get("retrieval_ms")),
                _maybe_float(entry.get("reranking_ms")),
                _maybe_float(entry.get("prompt_build_ms")),
                _maybe_float(entry.get("answer_generation_ms")),
                _maybe_float(entry.get("total_latency_ms")),
                qi_sql,
                rsk,
                rs_hybrid,
                rs_filters,
                created_at.strip(),
            )

            conn = get_connection()
            try:
                conn.execute(
                    """
                    INSERT INTO query_logs (
                        user_id, project_id, question, rewritten_query, retrieval_mode,
                        hybrid_retrieval_enabled, selected_doc_ids_json, recalled_doc_ids_json,
                        confidence, answer_preview, latency_ms,
                        query_rewrite_ms, retrieval_ms, reranking_ms, prompt_build_ms,
                        answer_generation_ms, total_latency_ms, query_intent,
                        retrieval_strategy_k, retrieval_strategy_use_hybrid,
                        retrieval_strategy_apply_filters, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    params,
                )
                conn.commit()
            finally:
                conn.close()
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
    ) -> list[dict]:
        try:
            clauses: list[str] = []
            params: list[object] = []

            if project_id is not None:
                clauses.append("project_id = ?")
                params.append(project_id)
            if user_id is not None:
                clauses.append("user_id = ?")
                params.append(user_id)
            if since_created_at is not None and since_created_at.strip():
                clauses.append("created_at >= ?")
                params.append(since_created_at.strip())
            if until_created_at is not None and until_created_at.strip():
                clauses.append("created_at <= ?")
                params.append(until_created_at.strip())

            where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
            sql = f"SELECT * FROM query_logs {where} ORDER BY created_at DESC"
            qparams: list[object] = list(params)
            if limit is not None and limit >= 0:
                sql += " LIMIT ?"
                qparams.append(int(limit))

            conn = get_connection()
            try:
                cur = conn.execute(sql, qparams)
                rows = cur.fetchall()
            finally:
                conn.close()

            return [self._row_to_dict(r) for r in rows]
        except Exception:
            return []

    @staticmethod
    def _row_to_dict(row: object) -> dict:
        r = dict(row)  # sqlite3.Row
        out: dict = {
            "question": r.get("question"),
            "rewritten_query": r.get("rewritten_query"),
            "project_id": r.get("project_id"),
            "user_id": r.get("user_id"),
            "retrieval_mode": r.get("retrieval_mode"),
            "confidence": r.get("confidence"),
            "timestamp": r.get("created_at"),
            "selected_doc_ids": _parse_json_list(r.get("selected_doc_ids_json")),
            "retrieved_doc_ids": _parse_json_list(r.get("recalled_doc_ids_json")),
        }
        prev = r.get("answer_preview")
        if prev is not None:
            out["answer"] = prev

        h = r.get("hybrid_retrieval_enabled")
        if h is not None:
            out["hybrid_retrieval_enabled"] = bool(h)

        intent = r.get("query_intent")
        if isinstance(intent, str) and intent.strip():
            out["query_intent"] = intent.strip()

        rsk = r.get("retrieval_strategy_k")
        rsh = r.get("retrieval_strategy_use_hybrid")
        rsa = r.get("retrieval_strategy_apply_filters")
        if rsk is not None or rsh is not None or rsa is not None:
            strat: dict[str, object] = {}
            if rsk is not None:
                try:
                    strat["k"] = int(rsk)
                except (TypeError, ValueError):
                    strat["k"] = rsk
            if rsh is not None:
                strat["use_hybrid"] = bool(rsh)
            if rsa is not None:
                strat["apply_filters"] = bool(rsa)
            if strat:
                out["retrieval_strategy"] = strat

        for key in (
            "latency_ms",
            "query_rewrite_ms",
            "retrieval_ms",
            "reranking_ms",
            "prompt_build_ms",
            "answer_generation_ms",
            "total_latency_ms",
        ):
            v = r.get(key)
            mi = _maybe_int_ms(v)
            if mi is not None:
                out[key] = mi

        return out
