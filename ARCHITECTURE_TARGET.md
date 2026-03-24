# Runtime architecture (source of truth)

Short form of the layout enforced in code and tests. **Canonical detail:** `docs/architecture.md`, `docs/rag_orchestration.md`, `docs/migration_report_final.md`.

## HTTP backend — `api/src/interfaces/http/`

- **FastAPI** (`api/main.py` → `interfaces.http` app), routers under `routers/`, Pydantic schemas under `schemas/`, **`dependencies.py`** → **`BackendApplicationContainer`** and use cases.
- **Rule:** The whole **`interfaces/http`** tree must not import **`infrastructure.adapters`** or other heavy infra (AST scans cover all modules). Routers must not import **`infrastructure.*`** at all.

## Streamlit — reference UI client

- **Entry:** `frontend/app.py`, **`frontend/pages/`** (Streamlit multipage), **`frontend/src/components/`**.
- **Rule:** Import **`BackendClient`**, **`get_backend_client`**, and UI-facing helpers **only** from **`frontend/src/services/api_client.py`**. No direct `domain`, `application`, `composition`, or `interfaces` imports from pages/components (enforced by tests). **`frontend/src/services`** implements **`HttpBackendClient`** and must not import **`domain`** / **`application`** (architecture tests).
- **Backend transport:** Streamlit calls FastAPI **only over HTTP** at **`RAGCRAFT_API_BASE_URL`** (see **`docs/api.md`**). There is **no** supported in-process or alternate transport for the UI.

## Test-only composition helper

- **`api/tests/support/backend_container.py`** — **`build_backend_container_for_tests`** and **`build_streamlit_session_aware_backend_container_for_tests`** (pytest / E2E). Same **`build_backend`** graph as production; **not** used by the Streamlit product shell.

## Backend client

**Only** **`HttpBackendClient`** (`frontend/src/services/http_backend_client.py`) → FastAPI. Cached in **`infrastructure.config.app_state`**.

**`BackendClient`** protocol: canonical definition **`frontend/src/services/backend_client_protocol.py`**. **`api/src/application/frontend_support/backend_client_protocol.py`** is an optional type re-export for merged **`PYTHONPATH`** workspaces; it is **not** a second client implementation.

See **`docs/README.md`** (local development) for env vars.

## Layering (summary)

On disk under **`api/src/`**, the **only** top-level Python packages are **`domain`**, **`application`**, **`infrastructure`**, **`composition`**, and **`interfaces`** (no `src.` prefix in imports when **`PYTHONPATH`** includes **`api/src`**). There is **no** **`api/src/auth/`** or **`api/src/core/`** package — auth lives under **`domain`** (identity ports), **`application/use_cases/auth`**, and **`infrastructure/auth`** (JWT adapter, credentials).

| Location | Role |
|----------|------|
| **`api/src/domain/`** | Entities, ports, payloads. No framework imports (see tests). |
| **`api/src/application/`** | Use cases, RAG orchestration, policies, DTOs, **`frontend_support/`** (protocol re-export only). No `infrastructure` except the documented **`infrastructure.config`** narrow exception. |
| **`api/src/infrastructure/`** | Adapters, persistence, vector stores, caching. RAG adapters do not own post-recall pipeline order or query logging. |
| **`api/src/composition/`** | **`build_backend_composition`**, **`evaluation_wiring`**, **`build_backend`**, **`chat_rag_wiring`**. No imports of the frontend **`services`** package. |
| **`api/src/interfaces/http/`** | FastAPI app factory, routers, Pydantic schemas, upload adapters; thin handlers → use cases. |
| **`frontend/src/services/`** | **`api_client.py`** (canonical façade), **`http_backend_client.py`**, wire DTOs, Streamlit auth/session, HTTP transport. **`StreamlitChatTranscript`** via **`services.factories.chat_service_factory`**. Only **`infrastructure.config`** and **`infrastructure.auth`** from backend infra (not adapters). |

**Composition chat transcript:** callers pass **`ChatTranscriptPort`**. FastAPI and tests use **`application.services.memory_chat_transcript.MemoryChatTranscript`**; Streamlit wiring uses **`build_chat_service()`** in the frontend factory (session-backed transcript).

## Removed legacy paths

**Do not reintroduce at repository root:** `src/`, `apps/`, root `pages/`, `streamlit_app.py`, or monolithic layouts. **Do not reintroduce:** `api/src/backend/`, `api/src/adapters/`, `infrastructure/services/` as a package, or `RAGService` / `rag_service.py` as an orchestration façade. Tests guard these.

## Further reading

- **`docs/README.md`** — doc index + local dev notes.
- **`docs/dependency_rules.md`** — import rules.
- **`api/tests/architecture/README.md`** — what pytest enforces.
- **`scripts/validate.sh`** / **`scripts/validate.ps1`** — local **Ruff** + **`scripts/validate_architecture.*`** (**`api/tests/architecture`** + **`api/tests/bootstrap`**, same **`PYTHONPATH`** as CI).
