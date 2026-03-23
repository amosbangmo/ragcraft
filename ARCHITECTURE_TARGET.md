# Runtime architecture (source of truth)

Short form of the layout enforced in code. **Canonical detail:** `docs/architecture.md`, `docs/rag_orchestration.md`, `docs/migration_report_final.md`.

## HTTP backend — `apps/api/`

- **FastAPI** (`apps/api/main.py`), routers, schemas, **`apps/api/dependencies.py`** → **`BackendApplicationContainer`** and use cases.
- **`dependencies.py`** and routers use **composition + use cases** only; the **`apps/api`** tree must not import **`infrastructure.*`** (AST scan covers all modules, not only routers).

## Streamlit — reference UI client

- **Entry:** `streamlit_app.py`, **`pages/`**, **`src/ui/`**.
- **Rule:** Use **`BackendClient`** (`src/frontend_gateway/protocol.py`) and **`view_models`** — no direct `src.domain`, `src.infrastructure`, `src.composition`, or `apps.api`.
- **In-process backend:** `src/frontend_gateway/streamlit_backend_factory.py` → **`build_backend(..., backend=build_backend_composition(chat_transcript=StreamlitChatTranscript()))`**.

## Client modes (`RAGCRAFT_BACKEND_CLIENT`)

| Mode | Behavior |
|------|----------|
| **`http`** (default if unset) | `HttpBackendClient` → FastAPI (`RAGCRAFT_API_BASE_URL`). |
| **`in_process`** | `InProcessBackendClient` → **`BackendApplicationContainer`** in the Streamlit process. |

See **`docs/README.md`** (local development) for env vars.

## Layering (summary)

| Location | Role |
|----------|------|
| **`src/domain/`** | Entities, ports, payloads. No framework imports (see tests). |
| **`src/application/`** | Use cases, RAG orchestration (`use_cases/chat/orchestration/`), eval RAG helper (`rag_pipeline_orchestration.py`), policies, DTOs, `frontend_support` stubs. No `src.infrastructure`. |
| **`src/infrastructure/`** | Adapters (RAG, evaluation, workspace, …), persistence, vector stores, caching. RAG adapters do not own post-recall pipeline order or query logging. |
| **`src/composition/`** | **`build_backend_composition`**, **`evaluation_wiring`** (gold-QA stack), **`build_backend`**, **`chat_rag_wiring`**. No `src.frontend_gateway` imports. |
| **`src/frontend_gateway/`** | `BackendClient`, HTTP/in-process, **`StreamlitChatTranscript`**. No `src.infrastructure`. |
| **`src/auth/`** | Shared auth helpers. |

**Composition chat transcript:** callers pass **`ChatTranscriptPort`**. FastAPI and tests use **`application.frontend_support.memory_chat_transcript.MemoryChatTranscript`**; Streamlit uses **`StreamlitChatTranscript`** from **`streamlit_backend_factory`**. There is a single in-memory implementation (no duplicate under **`src/infrastructure/adapters`**).

## Removed legacy paths

**Do not reintroduce:** `src/backend/`, `src/adapters/`, `src/infrastructure/services/`, `src/services/` as a package, or `RAGService` / `rag_service.py` as an orchestration façade. Tests guard these.

## Further reading

- **`docs/README.md`** — doc index + local dev notes.
- **`docs/dependency_rules.md`** — import rules.
- **`tests/architecture/README.md`** — what pytest enforces.
- **`scripts/validate.sh`** / **`scripts/validate.ps1`** — local **Ruff** + **`pytest tests/architecture`** (mirrors CI).
