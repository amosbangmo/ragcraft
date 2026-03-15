import streamlit as st


def is_request_running(key: str) -> bool:
    return bool(st.session_state.get(key, False))


def start_request(key: str) -> None:
    st.session_state[key] = True


def stop_request(key: str) -> None:
    st.session_state[key] = False


def trigger_request(key: str) -> None:
    """
    Mark a request as running and force a rerun so the UI can render
    the disabled button before the heavy work starts.
    """
    start_request(key)
    st.rerun()


def finish_request(key: str) -> None:
    """
    Mark a request as completed and rerun so the UI is rendered again
    with the button enabled.
    """
    stop_request(key)
    st.rerun()
