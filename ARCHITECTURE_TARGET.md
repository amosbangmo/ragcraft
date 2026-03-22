# Runtime architecture (source of truth)

This document matches the **current** repository layout after the FastAPI-first migration. For a short migration checklist and history, see `docs/migration/MIGRATION_COMPLETE_REPORT.md`.

## HTTP backend — `apps/api/`

- **FastAPI** application (`apps/api/main.py`), routers, Pydantic schemas, dependency injection.
- **Composition** — `src/composition/` builds `BackendComposition` (service graph) and `BackendApplicationContainer` (services + memoized use cases). FastAPI resolves the container in `apps/api/dependencies.py`.
- **Routers** call **use cases** from `src/application/**/use_cases/`, not concrete SQLite/FAISS modules (enforced by architecture tests).

## Streamlit — reference UI client

- **Entry:** `streamlit_app.py`, multipage **`pages/`**, widgets **`src/ui/`**.
- **Rule:** No direct imports of `src.domain`, `src.infrastructure`, `src.composition`, or `apps.api`. Use **`BackendClient`** (`src/frontend_gateway/protocol.py`) and **`src.frontend_gateway.view_models`** for display shapes.
- **Session helpers:** `src/core/app_state.py` (`get_backend_client`) and optional in-process **`BackendApplicationContainer`** in Streamlit session state (`streamlit_backend_factory`).

**Role today:** Primary demo UI and internal tooling. **Strategic API consumers** should use **HTTP** + OpenAPI the same way `HttpBackendClient` does.

## Client modes (`RAGCRAFT_BACKEND_CLIENT`)

| Mode | Behavior |
|------|----------|
| **`http`** | `HttpBackendClient` → FastAPI (`RAGCRAFT_API_BASE_URL`). Matches how a SPA or automation would integrate. |
| **`in_process`** (default) | `InProcessBackendClient` → shared **`BackendApplicationContainer`** built in the Streamlit process (no uvicorn). Same use cases as the API; transport only differs. |

Details: `docs/migration/streamlit-fastapi-dev.md`.

## Layering

| Location | Role |
|----------|------|
| **`src/domain/`** | Entities, value objects, ports (protocols). No FastAPI, Streamlit, SQLite drivers, or LangChain imports. Summary recall uses **`SummaryRecallDocument`**, not LangChain `Document`. |
| **`src/application/`** | Use cases, DTOs, HTTP wire helpers, pure policies (e.g. `application/chat/policies/`). May import **`src.infrastructure.services`** only (orchestration services). |
| **`src/infrastructure/`** | Adapters: **`services/`** (runtime orchestration, LLM, FAISS, etc.), **`persistence/`**, **`vectorstores/`**, **`adapters/`** cross-cutting SQLite repos where used. |
| **`src/adapters/sqlite/`** | SQLite implementations of domain ports (users, assets, project settings). |
| **`src/composition/`** | Wires the graph; **`build_backend()`** is the single production entry for the full container. |
| **`src/frontend_gateway/`** | `BackendClient`, HTTP client, in-process adapter, Streamlit auth/session glue. Must not import **`src.infrastructure`** (stubs live under **`src/application/frontend_support/`**). |
| **`src/auth/`** | Authentication helpers shared by Streamlit and API-oriented flows. |

**Dependency direction:** delivery (API, UI) → application use cases → domain; infrastructure implements ports.

## Deprecated / transitional

| Item | Status |
|------|--------|
| **`src/backend/`** | **Deprecated** re-export shims → `src.infrastructure.services.*`. Do not add new code here; import canonical modules. |
| **`src/services/`** | **Removed** as a package name; do not reintroduce. |
| **`src/app/ragcraft_app.py`** | **Removed**; in-process mode uses **`InProcessBackendClient`** + **`BackendApplicationContainer`** directly. |

## Tests

- **`tests/architecture/`** — Import-boundary and migration guardrails.
- **`tests/infrastructure_services/`** — Unit tests for **`src.infrastructure.services`** (renamed from `tests/backend` to avoid confusion with `apps/api` or `src/backend`).
- **`tests/apps_api/`** — FastAPI contract and E2E-style HTTP tests.

## Further reading

- `README.md` — install, run, high-level diagram, **migration status**.
- `tests/architecture/README.md` — enforced import rules matrix.
- `docs/migration/streamlit-fastapi-dev.md` — env vars and local dev.
- `docs/migration/MIGRATION_COMPLETE_REPORT.md` — closure narrative and SPA readiness notes.
