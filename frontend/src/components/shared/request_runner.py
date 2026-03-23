from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

import streamlit as st

if TYPE_CHECKING:
    from services.view_models import BenchmarkResult

# Session payload convention: failures from ``run_request_action`` use this key.
# Success payloads must not use a top-level key with this name.
RUNNER_ERROR_KEY = "error"

DatasetEvalSessionKind = Literal[
    "missing",
    "runner_error",
    "invalid_shape",
    "invalid_result",
    "ok",
]


@dataclass(frozen=True)
class DatasetEvaluationSessionView:
    """
    Normalized read of a dataset-evaluation value from ``st.session_state``.

    Separates runner transport errors, shape errors, empty session, and coercible results
    so the UI does not treat broken payloads like “no data yet”.
    """

    kind: DatasetEvalSessionKind
    result: Any = None  # ``BenchmarkResult`` when ``kind == "ok"``
    meta: dict[str, Any] = field(default_factory=dict)
    runner_error_message: str | None = None


def is_request_running(request_key: str) -> bool:
    return bool(st.session_state.get(request_key, False))


def is_runner_error_payload(payload: Any) -> bool:
    """True when ``payload`` is the standard runner error envelope ``{error: ...}``."""
    return isinstance(payload, dict) and RUNNER_ERROR_KEY in payload


def get_session_payload(result_key: str) -> Any:
    """Read a runner result (success value, error dict, or None) from session_state."""
    return st.session_state.get(result_key)


def clear_result_payload(result_key: str) -> None:
    st.session_state.pop(result_key, None)


def analyze_dataset_evaluation_session_payload(raw: Any) -> DatasetEvaluationSessionView:
    """
    Classify a dataset-evaluation session payload without conflating states.

    Use :func:`read_dataset_evaluation_session_payload` when you only need a coerced
    ``BenchmarkResult``; use this when the UI must distinguish **invalid_result** from **missing**.
    """
    from services.view_models import coerce_benchmark_result

    if raw is None:
        return DatasetEvaluationSessionView(kind="missing")
    if is_runner_error_payload(raw):
        msg = raw.get(RUNNER_ERROR_KEY)
        text = msg if isinstance(msg, str) else (str(msg) if msg is not None else "")
        return DatasetEvaluationSessionView(kind="runner_error", runner_error_message=text or None)
    if not isinstance(raw, dict) or "result" not in raw:
        return DatasetEvaluationSessionView(kind="invalid_shape")
    coerced = coerce_benchmark_result(raw.get("result"))
    if coerced is None:
        return DatasetEvaluationSessionView(kind="invalid_result")
    meta: dict[str, Any] = {
        "enable_query_rewrite": bool(raw.get("enable_query_rewrite")),
        "enable_hybrid_retrieval": bool(raw.get("enable_hybrid_retrieval")),
        "generated_at": raw.get("generated_at"),
    }
    return DatasetEvaluationSessionView(kind="ok", result=coerced, meta=meta)


def read_dataset_evaluation_session_payload(
    raw: Any,
) -> tuple[BenchmarkResult, dict[str, Any]] | None:
    """
    Parse a completed **dataset evaluation** result stored by ``run_request_action``.

    Returns ``(BenchmarkResult, meta)`` when ``raw`` is a success dict with a coercible
    ``result`` field; otherwise None. ``meta`` includes ``enable_query_rewrite``,
    ``enable_hybrid_retrieval``, and ``generated_at`` when present on the payload.
    """

    view = analyze_dataset_evaluation_session_payload(raw)
    if view.kind != "ok" or view.result is None:
        return None
    return view.result, view.meta


def _start_request(request_key: str) -> None:
    st.session_state[request_key] = True


def _stop_request(request_key: str) -> None:
    st.session_state[request_key] = False


def _trigger_request(request_key: str) -> None:
    _start_request(request_key)
    st.rerun()


def _finish_request(request_key: str) -> None:
    _stop_request(request_key)
    st.rerun()


def _store_runner_error(result_key: str, message: str) -> None:
    st.session_state[result_key] = {RUNNER_ERROR_KEY: message}


def run_request_action(
    *,
    request_key: str,
    result_key: str,
    trigger: bool,
    can_run: bool,
    action: Callable[[], Any],
    spinner_text: str,
    error_mapper: Callable[[Exception], str],
) -> None:
    """
    Reusable request runner for Streamlit pages and dialogs.

    State machine (per user click):

    1. **Idle** — ``request_key`` is false; ``result_key`` may hold the last outcome.
    2. **Armed** — User clicks: ``result_key`` is cleared to ``None``, ``request_key``
       becomes true, then ``st.rerun()`` so widgets redraw with the button disabled.
    3. **Executing** — On the next run, while ``request_key`` is true, ``action`` runs
       inside a spinner; the return value or a mapped error is written to ``result_key``.
    4. **Settled** — ``request_key`` is reset to false and the app reruns so the UI is
       interactive again and ``render_result_payload`` can display the outcome.

    Callers should pass ``trigger`` only when the primary control fired and ``can_run``
    reflects input validation, so idle reruns do not re-enter the executing phase.
    """

    if trigger:
        if not can_run:
            return

        st.session_state[result_key] = None
        _trigger_request(request_key)

    if is_request_running(request_key):
        try:
            with st.spinner(spinner_text):
                result = action()

            st.session_state[result_key] = result

        except Exception as exc:
            try:
                mapped = error_mapper(exc)
            except Exception:
                mapped = str(exc)
            if not isinstance(mapped, str):
                mapped = str(mapped)
            _store_runner_error(result_key, mapped)
        finally:
            _finish_request(request_key)


def render_result_payload(
    *,
    result_key: str,
    on_success: Callable[[Any], None],
) -> None:
    payload = get_session_payload(result_key)

    if payload is None:
        return

    if is_runner_error_payload(payload):
        raw_msg = payload.get(RUNNER_ERROR_KEY)
        st.error(raw_msg if isinstance(raw_msg, str) else str(raw_msg))
        return

    on_success(payload)
