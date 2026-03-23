"""
Regression tests for HTTP vs Streamlit transport boundaries.

These complement :mod:`architecture.test_layer_boundaries` and
:mod:`architecture.test_fastapi_delivery_boundaries`. Streamlit surfaces must stay behind
:class:`~application.frontend_support.backend_client_protocol.BackendClient`; FastAPI must not pull monolith shims or infra adapter graphs
directly.

Checks are **import-level** (AST of ``import`` / ``from … import``).
"""

from __future__ import annotations

import inspect
from pathlib import Path

from architecture.import_scanner import collect_import_violations

REPO_ROOT = Path(__file__).resolve().parents[3]
_HTTP = REPO_ROOT / "api" / "src" / "interfaces" / "http"


def test_interfaces_http_package_avoids_runtime_services_layer() -> None:
    """
    FastAPI wires use cases from the composition root; it must not import removed monolith ``src.*``
    shims, ``infrastructure.services``, or ``infrastructure.adapters`` directly.
    """
    violations = collect_import_violations(
        [_HTTP],
        forbidden=(
            "src",
            "infrastructure.services",
            "infrastructure.adapters",
        ),
        repo_root=REPO_ROOT,
    )
    msg = (
        "FastAPI should depend on use cases from ``interfaces.http.dependencies`` / the composition root, "
        "not on ``infrastructure.adapters``, ``infrastructure.services`` (removed), "
        "or monolith ``src.*`` imports.\n"
    )
    assert not violations, msg + "\n".join(violations)


def test_streamlit_pages_and_ui_avoid_direct_backend_internals() -> None:
    """
    ``frontend/src/pages`` and ``frontend/src/components`` should use ``services`` and auth guards,
    not monolith ``src.*`` or ``apps.*`` import roots.
    """
    roots = [
        REPO_ROOT / "frontend" / "src" / "pages",
        REPO_ROOT / "frontend" / "src" / "components",
    ]
    forbidden = ("src", "apps")
    violations = collect_import_violations(roots, forbidden=forbidden, repo_root=REPO_ROOT)
    msg = "Streamlit pages/components must not import monolith ``src.*`` or ``apps.*`` roots.\n"
    assert not violations, msg + "\n".join(violations)


def test_http_and_in_process_backend_clients_expose_same_gateway_operations() -> None:
    """
    :class:`~application.frontend_support.http_backend_client.HttpBackendClient` and
    :class:`~application.frontend_support.in_process_backend_client.InProcessBackendClient` must stay aligned so switching
    ``use_http_backend_client`` does not drop operations Streamlit pages rely on.

    ``HttpBackendClient`` may add transport-only helpers (e.g. ``close``); in-process must implement
    every other public callable or property the HTTP client exposes.
    """
    from application.frontend_support.http_backend_client import HttpBackendClient
    from application.frontend_support.in_process_backend_client import InProcessBackendClient

    def _surface(cls: type) -> set[str]:
        names: set[str] = set()
        for name, member in inspect.getmembers(cls):
            if name.startswith("_"):
                continue
            if isinstance(member, property):
                names.add(name)
            elif callable(member):
                names.add(name)
        return names

    http_api = _surface(HttpBackendClient)
    proc_api = _surface(InProcessBackendClient)

    http_only = http_api - proc_api
    allowed_http_only = {"close"}
    unexpected = http_only - allowed_http_only
    assert not unexpected, (
        f"InProcessBackendClient missing operations present on HTTP client: {sorted(unexpected)}"
    )

    missing_on_http = proc_api - http_api
    assert not missing_on_http, (
        "HttpBackendClient missing operations present on InProcessBackendClient "
        f"(gateway drift): {sorted(missing_on_http)}"
    )


def test_runtime_checkable_backend_client_accepts_http_client_instance() -> None:
    """Structural check: HTTP implementation satisfies the protocol used by pages."""
    import httpx

    from application.frontend_support.backend_client_protocol import BackendClient
    from application.frontend_support.http_backend_client import HttpBackendClient

    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={}))
    client = HttpBackendClient(base_url="http://test.invalid", transport=transport)
    try:
        assert isinstance(client, BackendClient)
    finally:
        client.close()
