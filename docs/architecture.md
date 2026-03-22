# Architecture (Clean Architecture)

RAGCraft follows a **ports-and-adapters** style: **domain** at the center, **application** orchestrates, **infrastructure** implements technical details, **composition** wires objects, **delivery** (FastAPI, Streamlit client) stays thin.

**Canonical flow details for RAG:** **`docs/rag_orchestration.md`**. **Import rules:** **`docs/dependency_rules.md`**. **End-state migration summary:** **`docs/migration_report_final.md`**.

## `src/domain/`

**Belongs here:** entities, value objects, pure domain logic, **ports** (`Protocol` / ABC), and shared types such as `PipelineBuildResult`, `SummaryRecallDocument`, `RetrievalSettings`, **`RagInspectAnswerRun`**, and **`merge_summary_documents_weighted_rrf`** (`summary_document_fusion.py`).

**Does not belong:** FastAPI, Streamlit, SQLite drivers, LangChain, calls into `src.application` or `src.infrastructure`. (Domain may use `src.core` for config paths and shared exceptions where already established.)

## `src/application/`

**Belongs here:**

- **Use cases** under `src/application/use_cases/` — one primary workflow per class (e.g. `AskQuestionUseCase`, `BuildRagPipelineUseCase`, `RunManualEvaluationUseCase`).
- **RAG orchestration helpers** under `src/application/use_cases/chat/orchestration/` — e.g. `recall_then_assemble_pipeline`, `summary_recall_from_request`, `assemble_pipeline_from_recall`, `post_recall_pipeline_steps`, `ApplicationPipelineAssembly`, `PipelineQueryLogEmitter`, port definitions (`ports.py` including **`PostRecallStagePorts`**, **`PipelineBuildQueryLogEmitterPort`**).
- **Evaluation RAG helper** — `execute_rag_inspect_then_answer_for_evaluation` in **`use_cases/evaluation/rag_pipeline_orchestration.py`** (inspect + answer + latency for eval; no production query log).
- **Pipeline use-case ports** — `use_cases/chat/pipeline_use_case_ports.py` (`InspectRagPipelinePort`, `GenerateAnswerFromPipelinePort`) so evaluation does not depend on concrete chat use case classes.
- **Policies** under `src/application/chat/policies/` — pure helpers (dedupe, wire shapes) used by orchestration; RRF merge lives in **domain** (`summary_document_fusion`).
- **DTOs / wire helpers** — `application/http/wire.py`, evaluation DTOs, settings DTOs, query log ingress payload builders used by use cases.
- **`frontend_support/`** — HTTP-mode stubs for the gateway (`http_backend_stubs.py`, `memory_chat_transcript.py`) so `src/frontend_gateway` does not import infrastructure.

**Does not belong:** importing `src.infrastructure` (wiring uses composition). Use cases must not import `src.frontend_gateway`.

## `src/infrastructure/`

**Belongs here:**

- **`adapters/`** — concrete implementations: RAG stack (`docstore_service`, **`summary_recall_adapter`**, `post_recall_stage_adapters`, …), evaluation, workspace, SQLite repositories, `chat_transcript/memory_chat_transcript.py` (default process-local transcript for the service graph), query logging, vector store helpers, ingestion loaders, etc.
- **`persistence/`**, **`vectorstores/`**, **`caching/`**, **`logging/`** — technical subsystems.

**Rules:**

- Post–summary-recall **sequencing** lives in **application** (`assemble_pipeline_from_recall` + `post_recall_pipeline_steps`); adapters behind **`PostRecallStagePorts`** perform single technical steps.
- **RAG adapters** under `src/infrastructure/adapters/rag/` must **not** import `src.application`, except **`retrieval_settings_service.py`** (subclasses application **`RetrievalSettingsTuner`**). Enforced by **`test_rag_adapter_application_imports.py`**.
- **Query logging** is **not** implemented inside vectorstore/docstore/rerank modules; the application coordinates **`QueryLogPort`** and pipeline-stage logging via **`PipelineQueryLogEmitter`** / **`AskQuestionUseCase`**.
- Other adapters (e.g. evaluation export, query log service, row evaluation) may still import **application** DTOs or helpers where the codebase does so today — see **`docs/migration_report_final.md`** (technical debt).
- Non-adapter infrastructure must not depend on application (see layer tests).

## `src/composition/`

**Belongs here:** building the object graph only.

| Module | Role |
|--------|------|
| `backend_composition.py` | `BackendComposition` — technical services only. `build_backend_composition(chat_transcript=...)` defaults to `MemoryChatTranscript` from infrastructure. **No** `src.frontend_gateway` imports. |
| `application_container.py` | `BackendApplicationContainer` — memoized use cases, delegates to `chat_rag_wiring` for the RAG bundle. Exposes `chat_rag_use_cases` and `chat_*_use_case` accessors. |
| `chat_rag_wiring.py` | Builds `RagRetrievalSubgraph` and `ChatRagUseCases`; wires **`InspectRagPipelineUseCase`** with **`partial(build_rag_pipeline.execute, emit_query_log=False)`**. |
| `wiring.py` | Process-scoped chain cache invalidation hook for FastAPI. |

**Does not belong:** business flow sequencing (beyond one administrative `execute` for chain invalidation), Streamlit imports.

**Streamlit transcript:** `streamlit_backend_factory.build_streamlit_backend_application_container()` passes `backend=build_backend_composition(chat_transcript=StreamlitChatTranscript())` so the UI implementation stays in `src/frontend_gateway/`.

## `apps/api/`

**Belongs here:** FastAPI app (`main.py`), routers, Pydantic schemas, `dependencies.py` resolving `BackendApplicationContainer` and use cases via `Depends`.

**Rule:** Routers depend on **use cases** (or dependency callables that return them), not on `src.infrastructure.adapters.*` directly.

## `src/frontend_gateway/`

**Belongs here:** `BackendClient` protocol, `HttpBackendClient`, `InProcessBackendClient`, HTTP transport/payloads, Streamlit auth glue, `StreamlitChatTranscript` (session-backed transcript), `streamlit_backend_factory`.

**Rule:** No imports of `src.infrastructure`. HTTP placeholders come from `src.application.frontend_support`. Gold-QA **`pipeline_runner`** types may return **`RagInspectAnswerRun`** or a legacy dict (see **`BenchmarkExecutionUseCase`**).

## Other roots

- **`src/auth/`** — authentication helpers shared by API and Streamlit.
- **`src/core/`** — config, paths, shared errors.
- **`src/ui/`**, **`pages/`**, **`streamlit_app.py`** — Streamlit UI; must use `BackendClient`, not domain/infrastructure/composition directly (enforced by tests).

**Dependency direction (target):** delivery → application use cases → domain ports ← infrastructure adapters. Composition instantiates and injects.
