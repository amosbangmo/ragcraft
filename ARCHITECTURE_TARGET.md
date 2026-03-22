# Runtime architecture

This is the **source-of-truth layout** for how RAGCraft is structured today: backend boundary, clients, and where code belongs.

## Backend boundary — FastAPI

- **`apps/api/`** — FastAPI application factory, routers, dependency providers, HTTP error mapping, OpenAPI.
- **Composition** — `src/composition/` builds `BackendComposition` (services) and `BackendApplicationContainer` (services + use cases). FastAPI resolves the container via `apps.api.dependencies` (no `src.app` import).
- **Use cases** — `src/application/**/use_cases/` are the primary entry points routers call.

## Clients

- **Streamlit** — A **UI client** only: `pages/` and `src/ui/` depend on **`BackendClient`** (`src/frontend_gateway/protocol.py`), not on `src.services` or the container directly.
- **Angular / other SPAs** — Should use the **same HTTP API** as Streamlit in HTTP mode (`OpenAPI` at `/docs`, header `X-User-Id` for workspace identity today).

## Frontend integration seam — `BackendClient`

- **`HttpBackendClient`** — Calls FastAPI over HTTP (`RAGCRAFT_BACKEND_CLIENT=http`).
- **`InProcessBackendClient`** — Wraps **`RAGCraftApp`** (`src/app/ragcraft_app.py`), which holds a `BackendApplicationContainer` and small Streamlit-oriented helpers (e.g. chain session cache). Default for local dev without uvicorn.

## Layering (Clean Architecture direction)

| Area | Role |
|------|------|
| **`src/domain/`** | Entities, value objects, invariants — no FastAPI, Streamlit, SQLite, or FAISS imports. |
| **`src/application/`** | Use cases and orchestration; depends on domain and ports. |
| **`src/infrastructure/`** | Adapters: SQLite, FAISS, LLM clients, extraction, etc. |
| **`src/services/`** | Orchestration services composed by the backend graph (still central today). |
| **`src/frontend_gateway/`** | Protocol + HTTP/in-process clients + Streamlit auth/context wiring. |

**Dependency direction:** outer delivery (API, UI) → application/use cases → domain; infrastructure implements ports.

## Repository layout (high level)

- **`apps/api/`** — HTTP API only.
- **`pages/`**, **`streamlit_app.py`** — Streamlit entry and multipage app.
- **`src/app/`** — `RAGCraftApp` in-process adapter (not used by FastAPI).
- **`src/ui/`** — Streamlit widgets and layout helpers.

*(An older note referred to `src/interfaces/streamlit`; the real UI roots are `pages/` and `src/ui/`.)*

## Runtime modes — strategic vs local-only conveniences

| Mode | Env | Behavior |
|------|-----|----------|
| **HTTP client** | `RAGCRAFT_BACKEND_CLIENT=http` | Streamlit → FastAPI via `HttpBackendClient`. Same contract an Angular app would use. **Strategic** for split processes and production-shaped dev. |
| **In-process** | unset / `in_process` | Streamlit → `InProcessBackendClient(RAGCraftApp)` → shared container. **Strategic** for fast local dev without running uvicorn. |

**Local / transitional (not API concerns):** Streamlit `session_state` chain cache (`src/ui/streamlit_project_chain_session_cache.py`), optional legacy JSONL query-log import — kept for dev and migration utilities, not part of the public HTTP contract.

## Further reading

- **Verification summary (migration closure):** `docs/migration/MIGRATION_COMPLETE_REPORT.md`
- **Operational how-to:** `docs/migration/streamlit-fastapi-dev.md`
- **Migration outcomes and SPA checklist:** `docs/migration/final-status.md`, `docs/migration/BACKEND_MIGRATION_CHECKLIST.md`
- **In-process adapter detail:** `docs/migration/ragcraftapp-deprecation.md`
