# Runtime architecture (source of truth)

Short form of the layout enforced in code and tests. **Canonical detail:** `docs/architecture.md`, `docs/rag_orchestration.md`, `docs/migration_report_final.md`.

## HTTP backend — `api/src/interfaces/http/`

- **FastAPI** (`api/main.py` → `interfaces.http` app), routers under `routers/`, Pydantic schemas under `schemas/`, **`dependencies.py`** → **`BackendApplicationContainer`** and use cases.
- **Rule:** The whole **`interfaces/http`** tree must not import **`infrastructure.adapters`** or other heavy infra (AST scans cover all modules). Routers must not import **`infrastructure.*`** at all.

## Streamlit — reference UI client

- **Entry:** `frontend/app.py`, **`frontend/src/pages/`**, **`frontend/src/components/`**.
- **Rule:** Use **`BackendClient`** (`frontend/src/services/protocol.py`) and **`view_models`** — no direct `domain`, `application`, `composition`, or `interfaces` imports from pages/components (enforced by tests; **`services`** may use in-process wiring).
- **In-process backend:** `frontend/src/services/streamlit_backend_factory.py` → **`build_backend(..., backend=build_backend_composition(chat_transcript=StreamlitChatTranscript()))`**.

## Client modes (`RAGCRAFT_BACKEND_CLIENT`)

| Mode | Behavior |
|------|----------|
| **`http`** (default if unset) | `HttpBackendClient` → FastAPI (`RAGCRAFT_API_BASE_URL`). |
| **`in_process`** | `InProcessBackendClient` → **`BackendApplicationContainer`** in the Streamlit process. |

See **`docs/README.md`** (local development) for env vars.

## Layering (summary)

On disk under **`api/src/`**, the **only** top-level Python packages are **`domain`**, **`application`**, **`infrastructure`**, **`composition`**, and **`interfaces`** (no `src.` prefix in imports when **`PYTHONPATH`** includes **`api/src`**). There is **no** **`api/src/auth/`** or **`api/src/core/`** package — auth lives under **`domain`** (identity ports), **`application/use_cases/auth`**, and **`infrastructure/auth`** (JWT adapter, credentials).

| Location | Role |
|----------|------|
| **`api/src/domain/`** | Entities, ports, payloads. No framework imports (see tests). |
| **`api/src/application/`** | Use cases, RAG orchestration, policies, DTOs, `frontend_support` stubs. No `infrastructure` except the documented **`infrastructure.config`** narrow exception. |
| **`api/src/infrastructure/`** | Adapters, persistence, vector stores, caching. RAG adapters do not own post-recall pipeline order or query logging. |
| **`api/src/composition/`** | **`build_backend_composition`**, **`evaluation_wiring`**, **`build_backend`**, **`chat_rag_wiring`**. No imports of the frontend **`services`** package. |
| **`api/src/interfaces/http/`** | FastAPI app factory, routers, Pydantic schemas, upload adapters; thin handlers → use cases. |
| **`frontend/src/services/`** | `BackendClient`, HTTP/in-process clients, Streamlit factories, **`StreamlitChatTranscript`**. Only **`infrastructure.config`** and **`infrastructure.auth`** from backend infra (not adapters). |

**Composition chat transcript:** callers pass **`ChatTranscriptPort`**. FastAPI and tests use **`application.frontend_support.memory_chat_transcript.MemoryChatTranscript`**; Streamlit uses **`StreamlitChatTranscript`** from **`streamlit_backend_factory`**. There is a single in-memory implementation (no duplicate under **`infrastructure/adapters`**).

## Removed legacy paths

**Do not reintroduce at repository root:** `src/`, `apps/`, root `pages/`, `streamlit_app.py`, or monolithic layouts. **Do not reintroduce:** `api/src/backend/`, `api/src/adapters/`, `infrastructure/services/` as a package, or `RAGService` / `rag_service.py` as an orchestration façade. Tests guard these.

## Further reading

- **`docs/README.md`** — doc index + local dev notes.
- **`docs/dependency_rules.md`** — import rules.
- **`api/tests/architecture/README.md`** — what pytest enforces.
- **`scripts/validate.sh`** / **`scripts/validate.ps1`** — local **Ruff** + **`scripts/validate_architecture.*`** (**`api/tests/architecture`** + **`api/tests/bootstrap`**, same **`PYTHONPATH`** as CI).
