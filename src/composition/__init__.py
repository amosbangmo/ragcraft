"""
Backend composition root (no DI framework).

* :func:`build_backend_composition` — technical infrastructure adapters only (callers pass ``chat_transcript``).
* :func:`build_backend_application_container` — attaches lazy use-case wiring to a given ``BackendComposition``
  and ``invalidate_chain_key`` (no branching).
* :func:`build_backend` — full graph: pass a built ``BackendComposition`` plus ``invalidate_chain_key``.
* :mod:`src.composition.wiring` — shared hooks (e.g. process-scoped chain eviction for FastAPI).

FastAPI should obtain a process-wide :class:`BackendApplicationContainer` via ``apps.api.dependencies``.

**Final orchestration target (locked for migration):**

- **Application** ``src/application/use_cases`` owns RAG/chat orchestration (sequence of recall → assembly →
  answer, retrieval comparison, evaluation runners calling inspect + generate).
- **Application services** (``src/application/...`` outside ``use_cases``) hold only framework-agnostic helpers
  (policies, DTOs, pure orchestration snippets), not transport or adapter construction.
- **Infrastructure** ``src/infrastructure/adapters`` implements ports and technical services; adapters must not
  construct use cases or own end-user flow sequencing where a use case already exists.
- **Composition** (this package + :mod:`src.composition.chat_rag_wiring`) wires instances only — no business
  sequencing beyond delegating to a single use case ``execute`` for cache invalidation on the container.
- **Transport** (``apps/api``, ``src/frontend_gateway``) resolves use cases from the container / dependencies;
  it must not import RAG orchestration adapters under ``src.infrastructure.adapters.rag`` directly.
"""

from src.composition.application_container import (
    BackendApplicationContainer,
    build_backend,
    build_backend_application_container,
)
from src.composition.backend_composition import BackendComposition, build_backend_composition
from src.composition.wiring import process_scoped_chain_invalidate_key

__all__ = [
    "BackendApplicationContainer",
    "BackendComposition",
    "build_backend",
    "build_backend_application_container",
    "build_backend_composition",
    "process_scoped_chain_invalidate_key",
]
