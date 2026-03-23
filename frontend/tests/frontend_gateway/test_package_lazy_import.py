from __future__ import annotations

import sys


def test_importing_streamlit_context_does_not_load_in_process_client() -> None:
    """
    ``src.frontend_gateway.__init__`` uses lazy exports so lightweight UI imports
    (protocol + streamlit_context) avoid pulling :mod:`src.frontend_gateway.in_process`
    until something requests an in-process symbol.
    """
    prefix = "src.frontend_gateway."
    for key in list(sys.modules):
        if key.startswith(prefix) and key != "src.frontend_gateway":
            del sys.modules[key]
    if "src.frontend_gateway" in sys.modules:
        del sys.modules["src.frontend_gateway"]

    import services.streamlit_context  # noqa: F401

    assert "src.frontend_gateway.in_process" not in sys.modules
