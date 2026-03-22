# Final migration verification report — RAGCraft (FastAPI-first)

**Document type:** Honest closure / gap analysis after automated verification.  
**Verification date:** Generated during Prompt 8 (full `pytest`, architecture scans, targeted greps).  
**Companion docs:** `ARCHITECTURE_TARGET.md` (layout), `README.md` (developer entry), `tests/architecture/README.md` (enforced import rules).

---

## Executive summary

The **structural** migration goals are **largely achieved**: FastAPI is the HTTP integration surface, use cases live in `src/application/`, long-running orchestration lives in `src/infrastructure/services/`, Streamlit is isolated behind `BackendClient`, and automated tests enforce several boundaries.

This is **not** a claim of “production-complete SaaS backend.” Identity is still header-based for scoped routes, some API modules intentionally touch `src.infrastructure.persistence` for SQLite bootstrap, and **`src/backend/`** remains as a **deprecated shim** package. An **Angular (or other) SPA can start integration now** against OpenAPI, but **must plan** for real auth, CORS, and hardening—called out explicitly below.

**Verdict:** Migration is **substantively complete for architecture and API-first development**; **product hardening** and **shim removal** remain.

---

## Verification performed (this pass)

| Check | Result |
|-------|--------|
| Full test suite | `563 passed`, `3 skipped` (skips: composition smoke tests when optional `unstructured` is not installed — see below) |
| Architecture pytest package | `15 passed`, `3 skipped` (same optional dependency) |
| `src.services` imports under `src/` | **None found** |
| `pages/` + `src/ui/` importing `src.domain` / `src.infrastructure` / `src.composition` | **None found** (grep) |
| `src/` (excl. `src/backend/`) importing `src.backend` | **None found** |
| `apps/api/routers/` importing `src.infrastructure` | **None found** |
| `BackendClient` vs `HttpBackendClient` surface alignment | Covered by `tests/architecture/test_fastapi_migration_guardrails.py` |

**Note on skips:** `tests/architecture/test_migration_regression_flows.py` calls `pytest.importorskip("unstructured.chunking.title")` before `build_backend()` because importing the full graph pulls `IngestionService` → `unstructured`. **CI environments that install `requirements.txt` should not skip these tests.**

---

## What is fully migrated (truthful list)

1. **HTTP API as primary contract** — `apps/api/` with routers, Pydantic schemas, and `Depends` → `BackendApplicationContainer` / use cases.
2. **Use-case layer** — `src/application/**/use_cases/` holds orchestration entry points consumed by FastAPI and by `RagService` / composition.
3. **Runtime service implementations** — `src/infrastructure/services/` (RAG, evaluation, ingestion, docstore, vectorstore, etc.); **no parallel `src/services` package**.
4. **Streamlit decoupling (import-level)** — `pages/` and `src/ui/` are forbidden by tests from importing domain, infrastructure, composition, or `apps.api`; they use `BackendClient` and `frontend_gateway` view models.
5. **Default Streamlit → HTTP** — `RAGCRAFT_BACKEND_CLIENT` defaults to **`http`** in `src/frontend_gateway/settings.py` (API-first local and deployed setups).
6. **In-process dev path** — `InProcessBackendClient` + `BackendApplicationContainer` (no `RAGCraftApp`).
7. **Domain purity** — No LangChain / FastAPI / Streamlit / `sqlite3` in `src/domain/`; summary recall DTOs use `SummaryRecallDocument`.
8. **Automated boundary tests** — `tests/architecture/` (domain, application, infrastructure, routers, gateway, deprecated `src.backend`, inline service construction in routers).
9. **Service-layer unit tests** — `tests/infrastructure_services/` (renamed from misleading `tests/backend/`).

---

## What remains transitional or partial

| Item | Detail |
|------|--------|
| **`src/backend/`** | Deprecated **re-export shims** to `src.infrastructure.services.*`. Safe to remove only after consumers stop importing it. |
| **`X-User-Id`** | Workspace identity for many routes is **trust-on-first-hop**. Fine for demos and trusted proxies; **not** browser-grade auth. |
| **`apps/api/dependencies.py`** | Uses a **lazy** `from src.infrastructure.persistence.db import init_app_db` inside `ensure_auth_database()` so SQLite app tables exist. This is **infrastructure in the API package** by design today; stricter layering would move DB bootstrap behind a port or lifespan hook. |
| **Streamlit product role** | Still the **reference UI**; long-term product may replace it with a SPA while keeping the same API. |
| **Optional heavy deps** | Full `build_backend()` requires **`unstructured`** (and related stack). Minimal envs can skip a few architecture regression tests. |
| **Historical markdown** | Some files under `docs/migration/` are **baseline snapshots** (e.g. `current-architecture-baseline.md`) and marked historical; they are not the live spec. |

---

## Remaining risks

1. **Security:** Header-based user id without cryptographic verification is the **largest production risk** for any public deployment.
2. **Drift:** `HttpBackendClient` and `InProcessBackendClient` must stay aligned with `BackendClient`; tests exist but **new methods need dual implementation**.
3. **Shim debt:** `src/backend/` can hide lingering old import paths in forks or notebooks.
4. **SQLite + single process:** Typical deployment assumptions; scaling and multi-worker SQLite need explicit design.

---

## Architectural debt (honest)

- **Large `src/infrastructure/services/` modules** — RAG pipeline split into policies/use cases has started; further decomposition is optional.
- **Global config / embedding singletons** — `src/core/config` and similar patterns; full constructor injection not done.
- **Dual persistence story** — Some SQLite lives under `src/adapters/sqlite/`, some under `src/infrastructure/persistence/`; consolidation is incremental cleanup.
- **Protocol typing** — `BackendClient` uses `Any` in several places for pragmatic Streamlit/HTTP bridging.

---

## Can the frontend function through the API boundary?

**Yes, for the capabilities exposed on `BackendClient` and mirrored in OpenAPI.**

- Streamlit in **`http`** mode exercises the same REST surface as an external client.
- **Caveat:** Chat transcripts remain **Streamlit `session_state`** (`ChatService` in the UI process); they are **not** the API’s source of truth. A SPA would implement its own conversation state or a future server-side chat API.

**Coverage:** `tests/apps_api/` and `tests/apps_api/test_http_pipeline_e2e.py` exercise major flows (projects, ingest, chat, inspect, evaluation, export) with overrides where appropriate.

**Not guaranteed:** Every niche UI helper has a matching route—when adding screens, compare `protocol.py` to `apps/api/routers/` and extend both sides if needed.

---

## Can Angular migration proceed now?

**Yes, as a technical spike or internal prototype**, using OpenAPI (`/openapi.json`) and the same headers/env as `HttpBackendClient`.

**Not “production Angular-ready” without:**

- Verified **authentication** (e.g. JWT) replacing or securing `X-User-Id`
- **CORS**, cookies vs bearer tokens, refresh strategy
- **Deployment** concerns (TLS, rate limits, file upload limits)

So: **integration work can start immediately**; **launching a public SPA** requires the security and hosting items above.

---

## Follow-up tasks (priority order)

1. **P0 — Production identity** — Replace trust-on-header with verified principals for any internet-facing API.
2. **P0 — CORS + browser auth story** — Explicit policy when the SPA is served from a different origin.
3. **P1 — Remove `src/backend/` shims** — After confirming no remaining importers (grep across org/forks).
4. **P1 — Optional: lifespan DB init** — Move `init_app_db` out of router-adjacent `Depends` into FastAPI `lifespan` or an explicit migration command.
5. **P2 — Align `HttpBackendClient` / OpenAPI** — When adding `BackendClient` methods, add routes + client methods + contract tests in the same change.
6. **P2 — Consolidate persistence layout** — Reduce split between `adapters/sqlite` and `infrastructure/persistence` where redundant.
7. **P3 — Further split large services** — Continue extracting policies/use cases from the biggest `infrastructure.services` modules.
8. **P3 — CI guarantee for full graph** — Ensure CI always installs `requirements.txt` so composition regression tests are not skipped.

---

## Migration completeness statement

| Dimension | Status |
|-----------|--------|
| **Target architecture (layers, API-first, Streamlit as client)** | **Met** |
| **Automated enforcement of key boundaries** | **Met** (with documented exceptions above) |
| **Production SaaS readiness** | **Not claimed** — identity and deployment gaps remain |
| **Angular / SPA prototype** | **Unblocked** on API + OpenAPI |

---

## Quick reference commands

```bash
pytest -q
pytest tests/architecture -q
pytest tests/apps_api -q
```

For layout and rules: **`ARCHITECTURE_TARGET.md`**, **`tests/architecture/README.md`**, **`README.md`**.

---

## Streamlit runtime modes (reference)

| Mode | `RAGCRAFT_BACKEND_CLIENT` | Notes |
|------|---------------------------|--------|
| **HTTP** (default if unset) | `http` (default in `load_frontend_backend_settings`) | Streamlit calls FastAPI; same contract as a SPA. |
| **In-process** | `in_process` | `InProcessBackendClient` builds `BackendApplicationContainer` inside the Streamlit process (no uvicorn). |

See `docs/migration/streamlit-fastapi-dev.md`.
