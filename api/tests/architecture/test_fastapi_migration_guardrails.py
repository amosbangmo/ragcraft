"""
Regression tests for HTTP vs Streamlit transport boundaries.

These complement :mod:`architecture.test_layer_boundaries` and
:mod:`architecture.test_fastapi_delivery_boundaries`. Streamlit surfaces must stay behind
:class:`~services.backend_client_protocol.BackendClient`; FastAPI must not pull monolith shims or infra adapter graphs
directly.

Checks are **import-level** (AST of ``import`` / ``from … import``).
"""

from __future__ import annotations

from pathlib import Path

from architecture.import_scanner import collect_import_violations

REPO_ROOT = Path(__file__).resolve().parents[3]
_HTTP = REPO_ROOT / "api" / "src" / "interfaces" / "http"
_FRONTEND_SERVICES = REPO_ROOT / "frontend" / "src" / "services"


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


def test_frontend_services_avoid_domain_and_application_packages() -> None:
    """``frontend/src/services`` must depend only on wire types, infra config, and stdlib/third-party."""
    violations = collect_import_violations(
        [_FRONTEND_SERVICES],
        forbidden=(
            "domain",
            "application",
            "composition",
            "interfaces",
        ),
        repo_root=REPO_ROOT,
    )
    assert not violations, (
        "frontend services must not import domain, application, composition, or interfaces.\n"
        + "\n".join(violations)
    )


def test_runtime_checkable_backend_client_accepts_http_client_instance() -> None:
    """Structural check: HTTP implementation satisfies the protocol used by pages."""
    import httpx

    from services.backend_client_protocol import BackendClient
    from services.http_backend_client import HttpBackendClient

    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={}))
    client = HttpBackendClient(base_url="http://test.invalid", transport=transport)
    try:
        assert isinstance(client, BackendClient)
    finally:
        client.close()
