# Runtime architecture (source of truth)

Short form of the layout enforced in code. **Canonical detail:** `docs/architecture.md`, `docs/rag_orchestration.md`, `docs/migration_report_final.md`.

## HTTP backend — `apps/api/`

- **FastAPI** (`apps/api/main.py`), routers, schemas, **`apps/api/dependencies.py`** → **`BackendApplicationContainer`** and use cases.
- Routers use **use cases**, not `src.infrastructure` directly (tests enforce).

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
| **`src/application/`** | Use cases, orchestration (`use_cases/chat/orchestration/`), policies, DTOs, `frontend_support` stubs. No `src.infrastructure`. |
| **`src/infrastructure/`** | Adapters, persistence, vector stores, caching. |
| **`src/composition/`** | **`build_backend_composition`**, **`build_backend`**, **`chat_rag_wiring`**. No `src.frontend_gateway` imports. |
| **`src/frontend_gateway/`** | `BackendClient`, HTTP/in-process, **`StreamlitChatTranscript`**. No `src.infrastructure`. |
| **`src/auth/`** | Shared auth helpers. |

**Composition chat transcript:** default **`MemoryChatTranscript`** (infrastructure) on the service graph; Streamlit overrides via **`streamlit_backend_factory`**.

## Removed legacy paths

**Do not reintroduce:** `src/backend/`, `src/adapters/`, `src/infrastructure/services/`, `src/services/` as a package, or `RAGService` / `rag_service.py` as an orchestration façade. Tests guard these.

## Further reading

- **`docs/README.md`** — doc index + local dev notes.
- **`docs/dependency_rules.md`** — import rules.
- **`tests/architecture/README.md`** — what pytest enforces.
