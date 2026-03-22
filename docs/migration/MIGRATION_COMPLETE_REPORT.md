# Migration completion report (FastAPI-first backend)

**Scope:** Backend HTTP boundary, Streamlit decoupling via `BackendClient`, automated guardrails.  
**Verification date:** repository scan + `pytest tests/architecture tests/apps_api tests/frontend_gateway tests/auth` (green).

---

## What is done

| Area | Status |
|------|--------|
| **FastAPI as integration root** | `BackendApplicationContainer` via `apps/api/dependencies.py`; no `RAGCraftApp` in API imports. |
| **No Streamlit in API code** | AST scan of `apps/api/`: no `streamlit` / `src.ui` imports; architecture tests enforce this. |
| **Streamlit → backend** | `pages/` and `src/ui/` use `BackendClient` / `get_backend_client()`; no direct `src.services`, `src.composition`, `src.app`, `src.infrastructure`, or `apps.api` imports (enforced by `tests/architecture/test_fastapi_migration_guardrails.py`). |
| **Users / profile / auth HTTP** | `/users/*` (header `X-User-Id`) and `/auth/login`, `/auth/register` wired; tests in `tests/apps_api/test_users_router.py`, `test_auth_router.py`. |
| **DTO boundary** | Chat/projects/evaluation use Pydantic response models; transport mappers in `apps/api/schemas/mappers.py` for document details, assets, QA rows, manual eval, query logs. |
| **Gateway parity** | `HttpBackendClient` vs `InProcessBackendClient` public surface aligned (tested); `isinstance(http_client, BackendClient)` checked. |
| **Docs** | `ARCHITECTURE_TARGET.md` describes runtime modes; migration folder has checklists and dev how-to. |

---

## What remains intentionally deferred (not blockers for “migration complete”)

1. **Production auth for SPAs** — Workspace identity is **`X-User-Id`** today. A real Angular (or other) deployment should add JWT/OAuth (or equivalent) and map to the same user-scoped data layout; this is an explicit product/security follow-up, not unfinished migration wiring.
2. **Generated OpenAPI client / CORS** — No checked-in codegen or default multi-origin CORS policy; teams add these per hosting environment.
3. **`RAGCraftApp`** — Kept **by design** for **in-process** Streamlit (`InProcessBackendClient`). Optional refactor: hold `BackendApplicationContainer` directly in the client and trim the adapter.
4. **Module-level LLM singletons** (`src/core/config.py`) — Still used widely; composition-root injection is a larger refactor than API/Streamlit decoupling.

---

## How Streamlit runs: `in_process` vs `http`

| Mode | Typical env | Call path |
|------|-------------|-----------|
| **In-process** | `RAGCRAFT_BACKEND_CLIENT` unset or `in_process` | Streamlit → `InProcessBackendClient` → `RAGCraftApp` → `BackendApplicationContainer` (no uvicorn). |
| **HTTP** | `RAGCRAFT_BACKEND_CLIENT=http`, `RAGCRAFT_API_BASE_URL=…` | Streamlit → `HttpBackendClient` → FastAPI (`X-User-Id` on scoped routes). |

Details: `docs/migration/streamlit-fastapi-dev.md`.

---

## Is the repo “Angular-ready” at the backend boundary?

**Partially — honestly:**

- **Ready:** OpenAPI at `/docs`, consistent JSON DTOs for main RAG/workspace/evaluation flows, header-based workspace scoping documented, auth endpoints for login/register exist for HTTP clients.
- **Not production-complete for a greenfield Angular app:** trust model (`X-User-Id` is not verified identity), auth/session story for SPAs (cookies vs tokens), CORS, and some UX flows still assume Streamlit unless duplicated behind API routes.

So: **the backend is suitable as the primary integration surface for a new SPA prototype** using the existing contract; **hardening identity and hosting is required before calling it production Angular-ready.**

---

## Anti-pattern re-scan (automated / manual)

- FastAPI importing Streamlit: **none** (grep + architecture tests).
- Pages/UI importing backend services directly: **none** (grep + architecture tests).
- Core composition/API TODOs from old migration passes: **none found** in `apps/api`, `src/composition`, `src/core` (spot grep for `TODO`/`FIXME`).

For ongoing regression protection, run:

```bash
pytest tests/architecture tests/apps_api tests/frontend_gateway tests/auth -q
```
