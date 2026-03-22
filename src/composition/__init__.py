"""
Backend composition root (no DI framework).

* :func:`build_backend_composition` — service adapters and orchestration services only.
* :func:`build_backend_application_container` — same, plus lazy use-case wiring (explicit ``invalidate_chain_key``).
* :func:`build_backend` — **preferred** full-graph entrypoint (alias of application container build).

FastAPI should obtain a process-wide :class:`BackendApplicationContainer` via ``apps.api.dependencies``.
"""

from src.composition.application_container import (
    BackendApplicationContainer,
    build_backend,
    build_backend_application_container,
)
from src.composition.backend_composition import BackendComposition, build_backend_composition

__all__ = [
    "BackendApplicationContainer",
    "BackendComposition",
    "build_backend",
    "build_backend_application_container",
    "build_backend_composition",
]
