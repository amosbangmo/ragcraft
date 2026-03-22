"""``src.backend.*`` remains a deprecated alias of :mod:`src.infrastructure.services`."""

from __future__ import annotations


def test_backend_rag_service_module_is_infrastructure_alias() -> None:
    import src.backend.rag_service as shim
    from src.infrastructure.services import rag_service as canonical

    assert shim is canonical
