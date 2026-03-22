# Migration final status (FastAPI-first, Streamlit decoupling)

This document summarizes what the migration achieved, what debt remains, and how a future Angular (or other) frontend should integrate. For a concise checklist, see **`BACKEND_MIGRATION_CHECKLIST.md`**. The **current** runtime model is described in **`ARCHITECTURE_TARGET.md`** at the repo root.

---

## Summary: can the frontend run entirely through the API?

**Partially — with an explicit split:**

| Surface | Through FastAPI HTTP? | Notes |
|--------|------------------------|--------|
| Chat, pipeline inspect, summary preview, retrieval compare | **Yes** | Routers under `apps/api/routers/chat.py` delegate to use cases. |
| Projects, documents, retrieval settings | **Yes** | `apps/api/routers/projects.py`. |
| Evaluation, QA dataset CRUD, benchmark export, query logs | **Yes** | `apps/api/routers/evaluation.py`. |
| Users / profile / avatar / password (SQLite-backed) | **Yes** | `apps/api/routers/users.py` (Streamlit can use `HttpBackendClient` + `X-User-Id`). |
| **Streamlit in-process mode** | **No (by design)** | Uses `InProcessBackendClient` + `BackendApplicationContainer` for zero-latency local dev without running uvicorn. |

**Conclusion:** A non-Streamlit frontend **can** be built against the HTTP API for the main RAG and workspace flows, provided it sends **`X-User-Id`** (and uses the same auth story the API expects today). **Gaps** are not hidden: see [Remaining limitations](#remaining-limitations-and-debt) below.

---

## Completed migration items (high level)

- **Single backend composition root for the API:** `build_backend_composition` → `build_backend_application_container`; FastAPI `Depends` getters in `apps/api/dependencies.py` resolve use cases from the container (not from a duplicate façade graph).
- **Streamlit decoupling from services:** Pages and `src/ui` do not import `src.infrastructure`, `src.composition`, or `apps.api` directly; RAG/workspace calls go through `BackendClient` (`protocol`, `HttpBackendClient`, `InProcessBackendClient`). See `docs/migration/streamlit-decoupling-checklist.md`.
- **Gateway layering:** `src/frontend_gateway/streamlit_context.py` isolates `src/ui` from `src.core.app_state` / `src.core.session` import paths.
- **Lazy `src.frontend_gateway` package init:** Submodules such as `streamlit_context` can import without eagerly loading `in_process` (helps tests and lighter tooling).
- **Dead API compatibility removed:** `get_ragcraft_app` was removed from `apps/api/dependencies.py` — no router used it; the container is the only FastAPI integration root.
- **Tests added/extended:** Public API routes (`/health`, `/version`), frontend gateway settings and lazy import, `streamlit_context` auth refresh delegation, serialization for `EffectiveRetrievalSettingsView`, dependency surface guard.

---

## Remaining limitations and debt

1. **In-process Streamlit** uses **`InProcessBackendClient`** wrapping **`BackendApplicationContainer`** (see `ARCHITECTURE_TARGET.md`). Further shrinking the client surface is optional hardening.
2. **Optional / heavy Python dependencies:** Full composition (e.g. ingestion with `unstructured`) may be missing in minimal environments; `/health` and lightweight tests should still run. Full integration and UI tests need the complete dependency set from the project’s environment spec.
3. **`BackendClient` protocol coverage vs REST:** The protocol is the Streamlit-facing contract. HTTP coverage should stay aligned when adding methods (see checklist in `streamlit-decoupling-checklist.md`).
4. **Auth model for external frontends:** Today the API uses **`X-User-Id`** as a header. A production SPA would typically replace this with JWT/OAuth and a verified principal; that is an explicit extension point, not implemented in this migration pass.
5. **Domain purity vs adapters:** Domain no longer imports LangChain; FAISS and LangChain stay in infrastructure. Broader DI cleanup remains optional.

---

## Recommended next steps before Angular (or SPA) work

1. **Contract-first API:** Generate or maintain an OpenAPI client from `apps/api` (FastAPI already exposes `/docs` / schema).
2. **Auth:** Replace or wrap `X-User-Id` with a real identity layer; keep user-scoping rules identical to SQLite/workspace layout.
3. **Parity checklist:** For each `BackendClient` method used by Streamlit in HTTP mode, confirm a matching route and error mapping (`src/frontend_gateway/http_error_map.py` / `ui_errors.py`).
4. **Retire Streamlit-only state:** Long term, move `src/core/chain_state.py` and Streamlit session singletons behind an explicit “host adapter” if the same process must serve both UIs.
5. **Run manual smoke:** `RAGCRAFT_BACKEND_CLIENT=in_process` and `RAGCRAFT_BACKEND_CLIENT=http` against local uvicorn per `docs/migration/streamlit-fastapi-dev.md`.

---

## Related documents

- `docs/migration/MIGRATION_COMPLETE_REPORT.md` — verification summary and honest SPA readiness  
- `docs/migration/BACKEND_MIGRATION_CHECKLIST.md` — done / remaining / temporary Streamlit pieces  
- `docs/migration/streamlit-decoupling-checklist.md`
- `docs/migration/streamlit-backend-client.md`
- `docs/migration/ragcraftapp-deprecation.md`
- `docs/migration/current-architecture-baseline.md`
