"""
Regression tests for the Streamlit → FastAPI migration boundaries.

These checks complement :mod:`tests.architecture.test_layer_boundaries` by targeting the **slices**
that regressed historically: API packages importing UI/Streamlit, and Streamlit surfaces reaching
past the :class:`~services.protocol.BackendClient` façade into services or the
monolithic app / composition root.

They are **import-level** (AST of ``import`` / ``from … import``) and avoid brittle string matching
on unrelated formatting.
"""

from __future__ import annotations

import inspect
from pathlib import Path

from architecture.import_scanner import collect_import_violations

REPO_ROOT = Path(__file__).resolve().parents[3]
_HTTP = REPO_ROOT / "api" / "src" / "interfaces" / "http"


def test_interfaces_http_package_avoids_streamlit_and_ui_layers() -> None:
    """HTTP stack must stay independent of Streamlit and legacy ``src.ui`` widgets."""
    violations = collect_import_violations(
        [_HTTP],
        forbidden=("streamlit", "src.ui"),
        repo_root=REPO_ROOT,
    )
    msg = (
        "The FastAPI package must stay free of Streamlit and ``src.ui`` "
        "(those belong to the Streamlit process only).\n"
    )
    assert not violations, msg + "\n".join(violations)


def test_interfaces_http_package_avoids_runtime_services_layer() -> None:
    """
    FastAPI wires use cases from the composition root; it must not import the legacy ``src.services``
    namespace, removed ``src.backend`` / ``src.adapters`` / ``infrastructure.services`` packages, or the
    concrete runtime service package (``infrastructure.adapters``) directly.
    """
    violations = collect_import_violations(
        [_HTTP],
        forbidden=(
            "src.services",
            "src.backend",
            "src.adapters",
            "infrastructure.services",
            "infrastructure.adapters",
        ),
        repo_root=REPO_ROOT,
    )
    msg = (
        "FastAPI should depend on use cases from ``interfaces.http.dependencies`` / the composition root, "
        "not on ``infrastructure.adapters``, ``infrastructure.services`` (removed), "
        "``src.adapters`` (removed), ``src.backend`` (removed), or ``src.services`` directly.\n"
    )
    assert not violations, msg + "\n".join(violations)


def test_streamlit_pages_and_ui_avoid_direct_backend_internals() -> None:
    """
    ``frontend/src/pages`` and ``frontend/src/components`` should use gateway services and auth guards,
    not legacy ``src.*`` monolith imports or ``apps.api``.
    """
    roots = [
        REPO_ROOT / "frontend" / "src" / "pages",
        REPO_ROOT / "frontend" / "src" / "components",
    ]
    forbidden = (
        "src.backend",
        "src.adapters",
        "src.domain",
        "src.services",
        "src.composition",
        "src.infrastructure",
        "src.app",
        "apps.api",
        "apps.",
    )
    violations = collect_import_violations(roots, forbidden=forbidden, repo_root=REPO_ROOT)
    msg = "Streamlit pages/components must not use removed ``src.*`` monolith imports or ``apps.api``.\n"
    assert not violations, msg + "\n".join(violations)


def test_http_and_in_process_backend_clients_expose_same_gateway_operations() -> None:
    """
    :class:`~services.http_client.HttpBackendClient` and
    :class:`~services.in_process.InProcessBackendClient` must stay aligned so switching
    ``use_http_backend_client`` does not drop operations Streamlit pages rely on.

    ``HttpBackendClient`` may add transport-only helpers (e.g. ``close``); in-process must implement
    every other public callable or property the HTTP client exposes.
    """
    from services.http_client import HttpBackendClient
    from services.in_process import InProcessBackendClient

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

    from services.http_client import HttpBackendClient
    from services.protocol import BackendClient

    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={}))
    client = HttpBackendClient(base_url="http://test.invalid", transport=transport)
    try:
        assert isinstance(client, BackendClient)
    finally:
        client.close()
