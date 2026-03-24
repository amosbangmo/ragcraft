from __future__ import annotations

import sys


def test_importing_streamlit_context_does_not_load_removed_in_process_client() -> None:
    """Lightweight imports should not pull deleted ``in_process_backend_client``."""
    prefix = "services."
    for key in list(sys.modules):
        if key.startswith(prefix) and key != "services":
            del sys.modules[key]
    if "services" in sys.modules:
        del sys.modules["services"]
    for key in list(sys.modules):
        if key.startswith("application.frontend_support"):
            del sys.modules[key]

    import services.session.streamlit_context  # noqa: F401

    assert "application.frontend_support.in_process_backend_client" not in sys.modules
