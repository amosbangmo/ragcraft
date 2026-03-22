# Final migration report — FastAPI-first backend

**Purpose:** Single place to describe what changed, how the repo is structured today, and what is left before a production SPA (e.g. Angular).  
**Last updated:** Reflects post-migration tree (`src/backend`, `src/adapters`, HTTP E2E tests, architecture guardrails).

---

## 1. What has been migrated

| Area | Outcome |
|------|---------|
| **HTTP API** | FastAPI in `apps/api/` is the primary integration surface: routers depend on **use cases** and **composition** (`BackendApplicationContainer`), not on `src.backend` or Streamlit. |
| **Routers** | Chat, projects, evaluation, users, auth, system — wired through `apps/api/dependencies.py` and explicit Pydantic schemas under `apps/api/schemas/`. |
| **Application layer** | Use cases in `src/application/**/use_cases/` orchestrate behavior; examples include `ResolveProjectUseCase`, `CompareRetrievalModesUseCase`, ingestion and evaluation commands. |
| **Persistence ports** | `ProjectSettingsRepositoryPort`, `UserRepositoryPort`, `AssetRepositoryPort`, etc., with SQLite adapters under `src/adapters/sqlite/` (project settings, users, RAG assets). |
| **Legacy “services” package** | Former `src/services` **renamed to `src/backend`** — same runtime graph, clearer name; **no `src/services` package** remains. Imports are `src.backend.*`. |
| **Streamlit** | `pages/` and `src/ui/` use `BackendClient` (`HttpBackendClient` / `InProcessBackendClient`); architecture tests forbid direct imports of `src.backend`, `src.composition`, `src.app`, `src.infrastructure`, and `apps.api` from UI code. |
| **Auth / users HTTP** | `/auth/login`, `/auth/register`, `/users/me` (+ profile, password, avatar) with `X-User-Id` for authenticated profile routes. |
| **Observability & safety** | Canonical error envelope, avatar MIME/size checks, OpenAPI customization. |

---

## 2. What was removed or reduced

- **`src/services`** — **removed** as a package path; logic lives under **`src/backend`** (or adapters / use cases where extracted).
- **`ProjectSettingsService`** (SQLite in a “service” class) — **removed**; replaced by **`SqliteProjectSettingsRepository`** implementing the port.
- **Monolithic `UserRepository` implementation in auth** — SQL moved to **`SqliteUserRepository`** in adapters; `src.auth.user_repository` remains a thin re-export for compatibility.
- **Direct `src.backend` / `src.services` imports from `apps/api`** — **forbidden** by architecture tests (AST import scan on the whole `apps/api` tree).
- **Tight coupling of API to legacy service facades** — reduced in favor of use-case injection (e.g. project resolution, retrieval comparison).

---

## 3. Current architecture overview

```
┌─────────────────────────────────────────────────────────────┐
│  Clients: Angular / other SPA, Streamlit (gateway), curl    │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP (+ X-User-Id) or InProcessBackendClient
┌───────────────────────────▼─────────────────────────────────┐
│  apps/api          FastAPI routers, schemas, dependencies   │
└───────────────────────────┬─────────────────────────────────┘
                            │ Depends → use cases / container
┌───────────────────────────▼─────────────────────────────────┐
│  src/composition   BackendApplicationContainer + build_backend│
└───────────────────────────┬─────────────────────────────────┘
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                  ▼
┌────────────────┐  ┌─────────────────┐  ┌──────────────────────┐
│ src/application│  │ src/backend     │  │ src/adapters/sqlite │
│ use cases      │  │ RAG, ingest,    │  │ ports’ SQLite impls │
│                │  │ eval, projects… │  │ (+ infra shims)     │
└────────┬───────┘  └────────┬────────┘  └──────────┬─────────┘
         │                   │                      │
         └───────────────────┴──────────────────────┘
                             ▼
                    ┌─────────────────┐
                    │ src/domain      │
                    │ entities, ports │
                    └─────────────────┘
```

- **`src/domain`:** types, ports (protocols), no imports from application/backend/infrastructure.
- **`src/application`:** use cases; may import `src.backend` and `src.domain`; must not import `src.infrastructure` or `apps`.
- **`src/backend`:** large orchestration and integration layer (LangChain, FAISS wiring, evaluation pipelines, etc.).
- **`src/adapters`:** persistence and similar concrete implementations behind ports.
- **`apps/api`:** transport only; must not import `src.backend` or `src.services` (enforced by tests).

---

## 4. Verification

Recommended CI-style bundle:

```bash
pytest tests/architecture tests/apps_api tests/frontend_gateway tests/auth -q
```

**End-to-end HTTP pipeline (TestClient):** `tests/apps_api/test_http_pipeline_e2e.py` chains, without calling backend modules directly from tests:

- `POST /projects` → `POST …/documents/ingest` → `POST /chat/ask` → `POST /chat/pipeline/inspect` → `POST /evaluation/dataset/run` → benchmark export GET/POST  

Uses dependency overrides so a full local ML/unstructured stack is not required; still validates **status codes**, **response models**, **`X-User-Id`** enforcement, and **422** validation envelope.

---

## 5. Remaining technical debt

| Item | Notes |
|------|--------|
| **`src/backend` size** | Most orchestration still lives in one package; further splits (more use cases, thinner facades) are optional hardening. |
| **QA / query-log SQLite** | Some persistence remains under `src/infrastructure/persistence/sqlite/` with shims; can be aligned with `src/adapters` over time. |
| **Identity** | `X-User-Id` is a **trust-on-first-hop** header; production needs JWT/OAuth (or similar) and mapping to the same user-scoped storage layout. |
| **CORS & OpenAPI codegen** | Per-environment configuration; not checked in as a single policy. |
| **`RAGCraftApp`** | Still the in-process adapter for Streamlit; could eventually hold only `BackendApplicationContainer` and trim surface area. |
| **Global config / LLM singletons** | `src/core/config` patterns remain; full constructor injection would be a larger refactor. |

---

## 6. Readiness for an Angular (or other) frontend

**Suitable today for:**

- Prototype or internal SPA consuming **OpenAPI** (`/docs`, `/openapi.json`).
- Flows mirrored in **E2E tests**: projects, ingest, chat, pipeline inspect, dataset benchmark run, export.
- **Stable JSON** shapes via Pydantic response models and shared wire helpers.

**Not production-complete without additional work:**

- **Authenticated identity** (verifying the principal, not only echoing a header).
- **Session vs token** strategy for SPAs, refresh, logout.
- **CORS** and hosting security headers for browser clients.
- **Rate limiting / abuse controls** at the edge.

**Bottom line:** The backend is a **credible single source of truth** for API-driven clients; treat **identity and deployment hardening** as the main gap before calling it **production Angular-ready**.

---

## 7. Streamlit runtime modes (reference)

| Mode | Configuration | Data path |
|------|----------------|-----------|
| **In-process** | Default / `RAGCRAFT_BACKEND_CLIENT=in_process` | `InProcessBackendClient` → `RAGCraftApp` → container |
| **HTTP** | `RAGCRAFT_BACKEND_CLIENT=http`, `RAGCRAFT_API_BASE_URL=…` | `HttpBackendClient` → FastAPI |

Details: `docs/migration/streamlit-fastapi-dev.md`.
