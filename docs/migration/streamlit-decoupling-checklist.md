# Streamlit decoupling checklist

Use this before treating Streamlit as “done” for an Angular or HTTP-only migration.

## Pages (`pages/`)

- [x] No imports from `src.app`, `src.application`, `src.services`, or `src.infrastructure`.
- [x] All data access goes through `BackendClient` from `get_backend_client()` / `render_page_header()["backend_client"]`.
- [x] User-facing errors use `src.frontend_gateway.ui_errors` (or equivalent) instead of reaching into `src.core` from page modules.
- [x] Auth flows use `AuthService` / guards only; no direct DB or repository imports. (Login/sign-up still use `AuthService`; profile session refresh after API mutations uses `src.frontend_gateway.streamlit_context.refresh_streamlit_auth_session_from_user_id`.)

## UI helpers (`src/ui/`)

- [x] No imports from `src.application` or `src.services` (pure display helpers may use `src.domain` for DTOs and labels).
- [x] No imports from `src.core` — resolve the Streamlit client and user id via `src.frontend_gateway.streamlit_context` instead of `src.core.app_state` / `src.core.session`.
- [x] Retrieval preset merge defaults go through `src.frontend_gateway.retrieval_settings_merge` (not `RetrievalSettingsService` in UI modules).
- [x] Benchmark comparison / failure analysis for charts use `src.domain.benchmark_comparison` and `src.domain.benchmark_failure_analysis`, not service facades.
- [x] Shared “thin gateway” DTOs for settings commands come from `src.frontend_gateway.settings_dtos` when the UI must build a typed command.

## Gateway (`src/frontend_gateway/`)

- [x] `BackendClient` is the only backend entry type pages depend on.
- [ ] HTTP and in-process implementations stay in sync for every protocol method pages call.

## Manual smoke

- [ ] Run Streamlit with `RAGCRAFT_BACKEND_CLIENT=in_process` on a representative project (chat, evaluation, profile).
- [ ] Run Streamlit with `RAGCRAFT_BACKEND_CLIENT=http` against a local FastAPI instance (see `docs/migration/streamlit-fastapi-dev.md`).

## Related docs

- `docs/migration/streamlit-backend-client.md` — client abstraction and HTTP mode.
- `docs/migration/streamlit-fastapi-dev.md` — running API + Streamlit.

## Prompt 11 — final pass (completed)

**Goal:** Streamlit pages and `src/ui` avoid backend internals (services, composition, façade imports) and depend on the replaceable frontend boundary.

**Done:**

- Added `src/frontend_gateway/streamlit_context.py`: `get_backend_client`, `get_user_id`, and `refresh_streamlit_auth_session_from_user_id` so `src/ui` (and profile) do not import `src.core.app_state` / `src.core.session` directly.
- Audited `pages/*.py`: no `src.services`, `src.app`, `src.application`, `src.composition`, or `src.infrastructure`; RAG data paths use `BackendClient` + `ui_errors`; domain imports are limited to request/view DTOs (e.g. retrieval filters, benchmark types).
- Left intentional auth boundaries: `pages/login.py` uses `AuthService` for credentials; guards remain on protected pages.

**Still manual / ongoing:**

- Keep `HttpBackendClient` and `InProcessBackendClient` in lockstep when extending `BackendClient`.
- Run the two manual smoke modes above before calling migration complete.
