# RAGCraftApp legacy façade — deprecation note

See **`BACKEND_MIGRATION_CHECKLIST.md`** for migration-complete criteria and what stays temporary for Streamlit in-process mode.

## What changed

- Introduced :class:`~src.composition.application_container.BackendApplicationContainer` as the **primary backend composition boundary**. It wraps :class:`~src.composition.backend_composition.BackendComposition` and exposes explicit, named dependencies for project, chat, ingestion, evaluation, and retrieval-analytics use cases (plus shared services).
- FastAPI wiring in ``apps/api/dependencies.py`` now resolves ``Depends`` from :func:`~apps.api.dependencies.get_backend_application_container` instead of treating :class:`~src.app.ragcraft_app.RAGCraftApp` as the integration root.
- :class:`~src.app.ragcraft_app.RAGCraftApp` remains but is documented as **Streamlit compatibility only**: it holds a ``BackendApplicationContainer`` and mirrors its services as **mutable instance attributes** (so tests and callers can swap mocks). Ingestion façade methods build use cases from those attributes each call; ``rag_service`` / ``retrieval_comparison_service`` stay as properties on ``self._backend`` so patterns like ``app._backend._rag_service = mock`` keep working. Evaluation helpers still call cached use cases on the container.

## Why RAGCraftApp is now legacy

- The façade mixed **UI-oriented helpers** (auth profile, document detail dicts, Streamlit chain cache) with **backend integration**, which forced the HTTP API to depend on a Streamlit-shaped entrypoint.
- The new container gives FastAPI (and future non-UI callers) a **single, explicit application boundary** without importing page-level concepts, while preserving identical service singletons and use-case wiring.

## What remains before RAGCraftApp can be removed

1. **Migrate Streamlit** — Replace ``pages/*`` and ``src/ui/*`` imports of ``RAGCraftApp`` with either:
   - a small Streamlit-specific adapter that holds ``BackendApplicationContainer`` and only UI helpers, or
   - HTTP client calls into the FastAPI app where appropriate.
2. **Move session-only state** — ``src/core/app_state.py`` and ``src/core/chain_state.py`` should live under an interfaces layer (per ``ARCHITECTURE_TARGET.md``) so the core package is not Streamlit-coupled.
3. **Update remaining references** — For example docstrings and modules that mention ``RAGCraftApp`` as the canonical orchestration path (e.g. some evaluation use-case module headers, ``manual_evaluation_service`` type hints) should point at the container or use cases.
4. **Remove ``get_ragcraft_app`` from ``apps/api/dependencies.py``** — **done** (no routers depended on it).
5. **Confirm parity** — Integration tests for upload / ingest / ask and API smoke tests should pass with only the container on the critical path.

Until those steps are done, **do not delete** ``RAGCraftApp``: it keeps Streamlit behavior and constructor patterns stable for existing sessions.
