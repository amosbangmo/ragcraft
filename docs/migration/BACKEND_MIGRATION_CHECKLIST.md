# Backend migration checklist — FastAPI as primary surface

This checklist records **completed** HTTP backend work and **follow-ups** for non-Streamlit frontends. The authoritative runtime description is **`ARCHITECTURE_TARGET.md`**. Streamlit **in-process** mode uses **`InProcessBackendClient`** + **`BackendApplicationContainer`** (the old **`RAGCraftApp`** type was removed; see **`ragcraftapp-deprecation.md`**).

---

## Done (backend migration)

| Item | Notes |
|------|--------|
| **FastAPI integration root** | `apps/api/dependencies.get_backend_application_container` → `build_backend()` / `BackendApplicationContainer`. No `get_ragcraft_app`, no import of `src.app.ragcraft_app` in `apps/api`. |
| **Routers** | Projects, chat, evaluation, users, system under `apps/api/routers/`; handlers delegate to use cases or header-scoped services. |
| **Identity** | Workspace user from `X-User-Id` on scoped routes; chat bodies do not duplicate `user_id` (header is source of truth). |
| **Errors** | Canonical JSON envelope via `apps/api/error_payload.py` + `register_exception_handlers`; `RAGCraftError` mapped by layer/status. |
| **OpenAPI** | `apps/api/openapi_common.py`, tag descriptions, `XUserId` scheme for codegen; contract tests in `tests/apps_api/test_openapi_contract.py`. |
| **Wire DTOs** | `src/application/http/wire.py` separates application results from FastAPI schemas. |
| **Streamlit → API path** | `HttpBackendClient` + env (`RAGCRAFT_BACKEND_CLIENT=http`); pages use `BackendClient` protocol, not direct service imports (see `docs/migration/streamlit-decoupling-checklist.md`). |
| **Automated API tests** | `tests/apps_api/test_core_routes.py` (overrides, no full heavy graph), `test_benchmark_export.py`, dependency surface guards. |

---

## Remaining for a future Angular (or other SPA) frontend

| Item | Notes |
|------|--------|
| **Generated client** | Point OpenAPI Generator (or similar) at `/openapi.json` from `apps.api.main:create_app`. |
| **Auth** | Replace or wrap `X-User-Id` with JWT/OAuth; keep user/workspace directory rules aligned with SQLite layout. |
| **Parity** | For each screen, confirm route + error codes vs `BackendClient` / `http_error_map` behavior. |
| **CORS / hosting** | Configure origins and cookies if the SPA is on another origin. |
| **Login/register** | Today some flows are Streamlit-only; expose or proxy via API when the SPA owns auth. |

---

## Streamlit / in-process — supported (not part of FastAPI)

These modules are **not** imported by `apps/api`. They exist so the UI can run **without uvicorn** and still share the same composition root as the HTTP API.

| Piece | Role |
|-------|------|
| **`RAGCraftApp`** (`src/app/ragcraft_app.py`) | **Strategic** in-process adapter over `BackendApplicationContainer`; used by `InProcessBackendClient`. |
| **`src/core/app_state.py`** | Streamlit session wiring for `get_backend_client()`. |
| **`src/core/chain_state.py`** | Session-scoped chain cache keys in the Streamlit process. |
| **`src/frontend_gateway/streamlit_*.py`** | Auth/session/header glue for the UI. |

**Optional follow-up:** `InProcessBackendClient` could hold `BackendApplicationContainer` directly and move remaining helpers off `RAGCraftApp` — a refactor, not a migration blocker.

---

## Verification commands

```powershell
# From repo root — full test suite (API tests use overrides where needed)
$env:PYTHONPATH = (Get-Location).Path
python -m pytest -q

# API only
python -m pytest tests/apps_api -q
```

---

## Related docs

- `docs/migration/final-status.md` — narrative summary and limitations  
- `docs/migration/streamlit-fastapi-dev.md` — run Streamlit against HTTP API  
- `docs/migration/ragcraftapp-deprecation.md` — why `RAGCraftApp` still exists  
- `docs/migration/streamlit-backend-client.md` — `BackendClient` protocol  
- `ARCHITECTURE_TARGET.md` — runtime architecture (source of truth)  
