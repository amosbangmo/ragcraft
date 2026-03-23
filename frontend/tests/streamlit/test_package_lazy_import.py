from __future__ import annotations

import sys


def test_importing_streamlit_context_does_not_load_in_process_client() -> None:
    """
    ``services`` uses lazy exports so lightweight UI imports (e.g. ``streamlit_context``)
    avoid pulling :mod:`services.in_process` until something requests an in-process symbol.
    """
    prefix = "services."
    for key in list(sys.modules):
        if key.startswith(prefix) and key != "services":
            del sys.modules[key]
    if "services" in sys.modules:
        del sys.modules["services"]

    import services.streamlit_context  # noqa: F401

    assert "services.in_process" not in sys.modules
