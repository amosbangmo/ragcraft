from collections.abc import Callable
from typing import Any

import streamlit as st


def is_request_running(request_key: str) -> bool:
    return bool(st.session_state.get(request_key, False))


def clear_result_payload(result_key: str) -> None:
    st.session_state.pop(result_key, None)


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

    Flow:
    - user triggers an action
    - running state is set to True
    - page reruns so the button is rendered disabled
    - action is executed inside a spinner
    - result (or mapped error) is stored in session_state
    - running state is reset
    - page reruns so the UI becomes interactive again
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
            st.session_state[result_key] = {
                "error": error_mapper(exc),
            }
        finally:
            _finish_request(request_key)


def render_result_payload(
    *,
    result_key: str,
    on_success: Callable[[Any], None],
) -> None:
    payload = st.session_state.get(result_key)

    if payload is None:
        return

    if isinstance(payload, dict) and "error" in payload:
        st.error(payload["error"])
        return

    on_success(payload)
