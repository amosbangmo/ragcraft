# Architecture (Clean Architecture)

RAGCraft follows a **ports-and-adapters** style: **domain** at the center, **application** orchestrates, **infrastructure** implements technical details, **composition** wires objects, **delivery** (FastAPI, Streamlit client) stays thin.

## `src/domain/`

**Belongs here:** entities, value objects, domain services that are pure, **ports** (`Protocol` / ABC) describing what the application needs from the outside (e.g. `ChatTranscriptPort`, `ProjectSettingsRepositoryPort`, `VectorStorePort`), and shared types such as `PipelineBuildResult`, `SummaryRecallDocument`, `RetrievalSettings`.

**Does not belong:** FastAPI, Streamlit, SQLite drivers, LangChain, calls into `src.application` or `src.infrastructure`. (Domain may use `src.core` for config paths and shared exceptions where already established.)

## `src/application/`

**Belongs here:**

- **Use cases** under `src/application/use_cases/` — one primary workflow per class (e.g. `AskQuestionUseCase`, `BuildRagPipelineUseCase`).
- **Orchestration helpers** under `src/application/use_cases/chat/orchestration/` — e.g. `assemble_pipeline_from_recall`, `recall_then_assemble_pipeline`, `PipelineQueryLogEmitter`, port definitions (`ports.py`).
- **Policies** under `src/application/chat/policies/` — pure helpers (dedupe, wire shapes) used by orchestration.
- **DTOs / wire helpers** — `application/http/wire.py`, evaluation DTOs, settings DTOs.
- **`frontend_support/`** — HTTP-mode stubs for the gateway (`http_backend_stubs.py`, `memory_chat_transcript.py`) so `src/frontend_gateway` does not import infrastructure.

**Does not belong:** importing `src.infrastructure` (wiring uses composition). Use cases should not import `src.frontend_gateway`.

## `src/infrastructure/`

**Belongs here:**

- **`adapters/`** — concrete implementations: RAG stack (`docstore_service`, `summary_recall_adapter`, `post_recall_stage_adapters`, …), evaluation, workspace, SQLite repositories, `chat_transcript/memory_chat_transcript.py` (default process-local transcript for the service graph), query logging, vector store helpers, ingestion loaders, etc.
- **`persistence/`**, **`vectorstores/`**, **`caching/`**, **`logging/`** — technical subsystems.

**Rule:** Adapters implement **narrow** behaviors behind ports. Post–summary-recall **sequencing** lives in application (`assemble_pipeline_from_recall`); adapters behind `PostRecallStagePorts` perform single technical steps.

**Exception (pragmatic):** `src/infrastructure/adapters/**` may import `src.application` for shared types or small helpers where the codebase already does so; non-adapter infrastructure must not depend on application (see architecture tests).

## `src/composition/`

**Belongs here:** building the object graph only.

| Module | Role |
|--------|------|
| `backend_composition.py` | `BackendComposition` — technical services only. `build_backend_composition(chat_transcript=...)` defaults to `MemoryChatTranscript` from infrastructure. **No** `src.frontend_gateway` imports. |
| `application_container.py` | `BackendApplicationContainer` — memoized use cases, delegates to `chat_rag_wiring` for the RAG bundle. Exposes `chat_rag_use_cases` and `chat_*_use_case` accessors. |
| `chat_rag_wiring.py` | Builds `RagRetrievalSubgraph` and `ChatRagUseCases`. |
| `wiring.py` | Process-scoped chain cache invalidation hook for FastAPI. |

**Does not belong:** business flow sequencing (beyond one administrative `execute` for chain invalidation), Streamlit imports.

**Streamlit transcript:** `streamlit_backend_factory.build_streamlit_backend_application_container()` passes `backend=build_backend_composition(chat_transcript=StreamlitChatTranscript())` so the UI implementation stays in `src/frontend_gateway/`.

## `apps/api/`

**Belongs here:** FastAPI app (`main.py`), routers, Pydantic schemas, `dependencies.py` resolving `BackendApplicationContainer` and use cases via `Depends`.

**Rule:** Routers depend on **use cases** (or dependency callables that return them), not on `src.infrastructure.adapters.*` directly.

## `src/frontend_gateway/`

**Belongs here:** `BackendClient` protocol, `HttpBackendClient`, `InProcessBackendClient`, HTTP transport/payloads, Streamlit auth glue, `StreamlitChatTranscript` (session-backed transcript), `streamlit_backend_factory`.

**Rule:** No imports of `src.infrastructure`. HTTP placeholders come from `src.application.frontend_support`.

## Other roots

- **`src/auth/`** — authentication helpers shared by API and Streamlit.
- **`src/core/`** — config, paths, shared errors.
- **`src/ui/`**, **`pages/`**, **`streamlit_app.py`** — Streamlit UI; must use `BackendClient`, not domain/infrastructure/composition directly (enforced by tests).

**Dependency direction (target):** delivery → application use cases → domain ports ← infrastructure adapters. Composition instantiates and injects.
