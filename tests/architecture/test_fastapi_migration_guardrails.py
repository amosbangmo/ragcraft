"""
Regression tests for the Streamlit → FastAPI migration boundaries.

These checks complement :mod:`tests.architecture.test_layer_boundaries` by targeting the **slices**
that regressed historically: API packages importing UI/Streamlit, and Streamlit surfaces reaching
past the :class:`~src.frontend_gateway.protocol.BackendClient` façade into services or the
monolithic app / composition root.

They are **import-level** (AST of ``import`` / ``from … import``) and avoid brittle string matching
on unrelated formatting.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from tests.architecture.import_scanner import collect_import_violations

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_apps_api_package_avoids_streamlit_and_ui_layers() -> None:
    """HTTP stack must stay independent of Streamlit and ``src.ui`` widgets."""
    api_root = REPO_ROOT / "apps" / "api"
    violations = collect_import_violations(
        [api_root],
        forbidden=("streamlit", "src.ui"),
        repo_root=REPO_ROOT,
    )
    assert not violations, "apps/api must not import Streamlit or src.ui:\n" + "\n".join(violations)


def test_apps_api_package_avoids_runtime_services_layer() -> None:
    """
    FastAPI wires use cases from the composition root; it must not import the legacy ``src.services``
    namespace, deprecated ``src.backend`` shims, or the concrete runtime service package
    (``src.infrastructure.services``) directly.
    """
    api_root = REPO_ROOT / "apps" / "api"
    violations = collect_import_violations(
        [api_root],
        forbidden=("src.services", "src.backend", "src.infrastructure.services"),
        repo_root=REPO_ROOT,
    )
    assert not violations, (
        "apps/api must not import src.services, src.backend, or src.infrastructure.services:\n"
        + "\n".join(violations)
    )


def test_streamlit_pages_and_ui_avoid_direct_backend_internals() -> None:
    """
    ``pages/`` and ``src/ui/`` should talk to capabilities through the gateway (protocol + context),
    auth helpers, and domain **types** — not services, composition, infrastructure, ``src.app``, or
    ``apps.api`` (no accidental “call FastAPI from Streamlit” coupling).
    """
    roots = [REPO_ROOT / "pages", REPO_ROOT / "src" / "ui"]
    forbidden = (
        "src.backend",
        "src.infrastructure.services",
        "src.services",
        "src.composition",
        "src.infrastructure",
        "src.app",
        "apps.api",
        "apps.",
    )
    violations = collect_import_violations(roots, forbidden=forbidden, repo_root=REPO_ROOT)
    assert not violations, "Streamlit surface leaked backend internals:\n" + "\n".join(violations)


def test_http_and_in_process_backend_clients_expose_same_gateway_operations() -> None:
    """
    :class:`~src.frontend_gateway.http_client.HttpBackendClient` and
    :class:`~src.frontend_gateway.in_process.InProcessBackendClient` must stay aligned so switching
    ``use_http_backend_client`` does not drop operations Streamlit pages rely on.

    ``HttpBackendClient`` may add transport-only helpers (e.g. ``close``); in-process must implement
    every other public callable or property the HTTP client exposes.
    """
    from src.frontend_gateway.http_client import HttpBackendClient
    from src.frontend_gateway.in_process import InProcessBackendClient

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
    assert not unexpected, f"InProcessBackendClient missing operations present on HTTP client: {sorted(unexpected)}"

    missing_on_http = proc_api - http_api
    assert not missing_on_http, (
        "HttpBackendClient missing operations present on InProcessBackendClient "
        f"(gateway drift): {sorted(missing_on_http)}"
    )


def test_runtime_checkable_backend_client_accepts_http_client_instance() -> None:
    """Structural check: HTTP implementation satisfies the protocol used by pages."""
    import httpx

    from src.frontend_gateway.http_client import HttpBackendClient
    from src.frontend_gateway.protocol import BackendClient

    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={}))
    client = HttpBackendClient(base_url="http://test.invalid", transport=transport)
    try:
        assert isinstance(client, BackendClient)
    finally:
        client.close()
