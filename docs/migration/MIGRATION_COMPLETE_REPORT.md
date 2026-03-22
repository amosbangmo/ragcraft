# Migration report — FastAPI-first backend (living document)

**Purpose:** Summarize what the migration delivered, how the tree is organized **today**, and what remains transitional.  
**Canonical layout:** `ARCHITECTURE_TARGET.md` at the repo root.  
**Last updated:** Post–`src.infrastructure.services` relocation, architecture guardrails, `SummaryRecallDocument` domain split.

---

## Migration status (at a glance)

| Area | Status |
|------|--------|
| **HTTP API** | **Complete** — `apps/api/` is the public contract; routers use `Depends` → `BackendApplicationContainer` / use cases. |
| **Use cases** | **Complete** — Primary entry points under `src/application/**/use_cases/`. |
| **Runtime orchestration** | **Complete** — Lives in **`src/infrastructure/services/`** (RAG, ingestion, evaluation, docstore, vectorstore, …). |
| **Deprecated shims** | **Transitional** — **`src/backend/`** re-exports `src.infrastructure.services.*` for old import paths; **new code must not use it** (architecture tests forbid imports outside `src/backend` itself). |
| **Streamlit** | **Transitional product role** — Reference UI; must use **`BackendClient`** only. Default **`RAGCRAFT_BACKEND_CLIENT=http`** targets the API; `in_process` is a dev shortcut. |
| **Domain purity** | **Complete** — No LangChain / FastAPI / Streamlit / `sqlite3` in `src/domain/`; summary hits use **`SummaryRecallDocument`**. |
| **Composition** | **Complete** — `src/composition/build_backend()` builds the full graph; FastAPI and Streamlit (in-process) share the same wiring patterns. |

---

## 1. What was migrated

| Topic | Outcome |
|-------|---------|
| **Service layer location** | Canonical code is **`src.infrastructure.services`**. **`src/backend`** is a **deprecated alias** only. |
| **Application layer** | Use cases in `src/application/`; may import **`src.infrastructure.services`** (not generic `src.infrastructure.*`). |
| **API boundary** | No `src.infrastructure` imports in `apps/api` (AST tests). |
| **Streamlit boundary** | `pages/` + `src/ui/` must not import domain, infrastructure, composition, or `apps.api` directly. |
| **In-process mode** | **`InProcessBackendClient`** holds **`BackendApplicationContainer`** — there is **no** `RAGCraftApp` type anymore. |
| **Wire payloads** | `src/application/http/wire.py` + `apps/api/schemas` keep JSON shapes stable. |

---

## 2. Removed or renamed (historical)

- **`src/services`** — package removed; functionality is under **`src.infrastructure.services`**.
- **`RAGCraftApp` / `src/app/ragcraft_app.py`** — removed from runtime; use **`InProcessBackendClient`** + container.
- **`tests/backend`** — renamed to **`tests/infrastructure_services`** (tests the service graph, not the HTTP “backend”).
- **`src.application.retrieval`** — removed; use **`src.application.chat.use_cases`** (`BuildRagPipelineUseCase`, `InspectRagPipelineUseCase`, `PreviewSummaryRecallUseCase`).

---

## 3. Architecture sketch

```
Clients (Streamlit, SPA, scripts)
        │  BackendClient (HTTP or in-process)
        ▼
apps/api  ──Depends──►  BackendApplicationContainer
        │                      │
        │                      ├── src/application/use_cases
        │                      ├── src/infrastructure/services
        │                      └── src/adapters/sqlite (ports)
        ▼
src/domain  (entities, ports, SummaryRecallDocument, …)
```

---

## 4. Verification commands

```bash
pytest tests/architecture -q
pytest tests/apps_api -q
```

**HTTP pipeline E2E (TestClient):** `tests/apps_api/test_http_pipeline_e2e.py` — projects → ingest → chat → inspect → evaluation → export (with dependency overrides where needed).

---

## 5. Intentional follow-ups (not blockers)

| Item | Notes |
|------|--------|
| **`src/backend` removal** | Can delete shims once external forks no longer rely on `src.backend.*` imports. |
| **`X-User-Id`** | Trust-on-first-hop for demos; production needs verified identity (JWT/OAuth, etc.). |
| **CORS / hosting** | Per-environment; not encoded as a single repo policy. |
| **Global config / LLM singletons** | `src/core/config` patterns; deeper DI is optional hardening. |

---

## 6. SPA / Angular readiness

**Works today:** OpenAPI (`/docs`, `/openapi.json`), same JSON as `HttpBackendClient`, E2E tests for main flows.

**Not production-complete without:** verified auth for browser clients, CORS policy, refresh tokens, rate limiting, and deployment hardening.

---

## 7. Streamlit runtime modes

| Mode | Configuration |
|------|----------------|
| **HTTP** | `RAGCRAFT_BACKEND_CLIENT=http`, `RAGCRAFT_API_BASE_URL=…` |
| **In-process** | Default / `RAGCRAFT_BACKEND_CLIENT=in_process` → `InProcessBackendClient` + container in-process |

See `docs/migration/streamlit-fastapi-dev.md`.
