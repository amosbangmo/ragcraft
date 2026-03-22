# Current architecture baseline (RAGCraft)

This document captures the **as-is** layout, known Clean Architecture leaks, and **non-negotiable constraints** for the FastAPI-first migration. It is a snapshot baseline; target shape remains in [`ARCHITECTURE_TARGET.md`](../../ARCHITECTURE_TARGET.md).

---

## 1. Layer map and responsibilities

### `apps/api`

- **Role:** HTTP delivery for RAGCraft: `create_app()` in `apps/api/main.py`, router modules under `apps/api/routers/`, Pydantic DTOs under `apps/api/schemas/`, shared error handling (`error_handlers.py`, `error_payload.py`), settings (`config.py`), and upload bridging (`upload_adapter.py`).
- **Wiring:** `apps/api/dependencies.py` exposes FastAPI `Depends` providers from **`get_backend_application_container`** (process-wide `BackendComposition` + named use cases). Streamlit in-process mode still uses **`RAGCraftApp`** via `InProcessBackendClient` in `src/core/app_state.py`; the HTTP API does not depend on `get_ragcraft_app` (removed as dead compatibility code).
- **Deferred imports:** Dependency getters intentionally lazy-import heavy stacks (FAISS / LangChain) so lightweight routes (e.g. health) stay importable in minimal environments.

### `src/app`

- **Role:** `src/app/ragcraft_app.py` defines **`RAGCraftApp`**, a Streamlit-oriented façade over `BackendComposition`.
- **Responsibilities today:** Exposes almost all backend entry points used by pages—auth and profile helpers, project/document introspection, LangChain “chain” caching via `src/core/chain_state.py`, ingestion and document lifecycle (often by constructing application use cases inline), RAG / inspection / summary preview (delegating to `RAGService`), evaluation and QA dataset operations, benchmark export helpers, and retrieval comparison.
- **Coupling:** Pulls in domain types, application use cases, **and** `src/core` chain cache helpers; it is the main **integration hub** between UI expectations and the service layer.

### `src/composition`

- **Role:** `src/composition/backend_composition.py` is the **composition root** for service-level singletons: initializes SQLite via `init_app_db()`, constructs concrete services (`AuthService`, `ProjectService`, `IngestionService`, `VectorStoreService`, `EvaluationService`, `ChatService`, `DocStoreService`, `RerankingService`, QA dataset services, `ProjectSettingsService`, `QueryLogService`), and lazily builds `RAGService` and `RetrievalComparisonService`.
- **Boundary:** Owns **service wiring**, not full use-case wiring; comments note that many use cases are still built in `RAGCraftApp` or FastAPI `Depends` getters.

### `src/application`

- **Role:** Use-case modules grouped by area (`chat`, `ingestion`, `evaluation`, `projects`, `retrieval`) plus shared helpers (`application/common`, evaluation formatters/DTOs).
- **Reality vs target:** Several use cases are valuable orchestrators (`BuildPipelineUseCase`, `AskQuestionUseCase`, `RunManualEvaluationUseCase`, ingestion flows). Others are **thin adapters** that delegate directly to a concrete `src/services/*` class with little or no domain logic (e.g. `ListProjectsUseCase`, `CreateProjectUseCase`, `ListProjectDocumentsUseCase`, many QA dataset CRUD use cases).
- **Leaks:** Some application modules import **`langchain_core.documents.Document`** (`ingest_common.py`, `summary_recall_preview.py`). Retrieval payloads and comments reference FAISS / hybrid modes as strings.

### `src/domain`

- **Role:** Domain models, ports, filters, pipeline payloads, RAG response types, evaluation artifacts, etc., split across packages such as `domain/retrieval`, `domain/documents`, `domain/shared`.
- **Leaks:** Multiple modules import **`langchain_core.documents.Document`** (e.g. `vector_store_port.py`, `retrieval_filters.py`, `pipeline_payloads.py`). `Project` exposes **`faiss_index_path`**, coupling the domain naming to a specific index backend. Comments and serialization helpers reference Streamlit session behavior for **rehydration** of benchmark/manual evaluation results (documentation of UI constraints, not a runtime import, but a design coupling).

### `src/services`

- **Role:** **Service-heavy orchestration** and legacy “application” behavior: vector store loading/saving, hybrid retrieval, pipeline assembly, answer generation, ingestion, doc store, evaluation, query logging, reranking, prompts, etc.
- **Characteristics:** Many services depend on LangChain types, FAISS paths, and infrastructure modules directly (e.g. `VectorStoreService` → `src/infrastructure/vectorstores/faiss/...`). `RAGService` **constructs and owns** several retrieval/chat use cases and multiple sub-services (`PipelineAssemblyService`, `SummaryRecallService`, …), acting as a **secondary composition root** for the RAG path.
- **God-object risk:** `RAGCraftApp` (wide surface for UI) and **`RAGService`** (RAG pipeline + use case construction) concentrate responsibilities that target architecture would split between composition and explicit use cases.

### `src/infrastructure`

- **Role:** Adapters: SQLite persistence (`persistence/db.py`, `persistence/sqlite/*`), FAISS vector store (`vectorstores/faiss/*`), LLM-facing helpers (`llm/*`), ingestion (`ingestion/*`), logging (`logging/query_log_repository.py`), minimal `web/` package.
- **Fit:** This layer is the **correct** home for LangChain/FAISS/SQLite specifics; leaks are mainly where **upper layers import those concepts directly** instead of going through ports.

### `pages`

- **Role:** Streamlit **multi-page** scripts (`chat`, `projects`, `ingestion`, `search`, `evaluation`, `retrieval_inspector`, `retrieval_comparison`, `profile`, etc.).
- **Coupling:** Pages (and some `src/ui` modules) obtain a **`RAGCraftApp`** instance from session/header state and call façade methods directly. They do **not** talk to FastAPI; there is no shared HTTP client abstraction for the desktop UI in this baseline.

### `src/ui`

- **Role:** Reusable Streamlit UI components (cards, dashboards, evaluation tabs, project selector, request runner, etc.).
- **Coupling:** Evaluation tabs import **`RAGCraftApp`** and call it with structured payloads—**direct coupling to the backend façade**, not to REST boundaries.

### Related (not in target tree but load-bearing)

- **`src/core`:** `app_state.py` and `chain_state.py` use **`streamlit`** session state and own the **`RAGCraftApp`** singleton and per-session LangChain cache. This places **framework-specific state** outside `pages/` and `src/interfaces/`, conflicting with the target layout in `ARCHITECTURE_TARGET.md`.

---

## 2. Clean Architecture violations and leaks (explicit)

### Dependencies on LangChain, FAISS, Streamlit, or framework-specific types

| Area | Issue |
|------|--------|
| **Domain** | `langchain_core.documents.Document` appears in ports and filters; `Project.faiss_index_path` bakes in FAISS layout. |
| **Application** | `Document` imported in ingestion/summary-recall helpers; pipeline modes described as `"faiss"` / `"faiss+bm25"` in domain/application payloads. |
| **Services** | Widespread LangChain document usage; `VectorStoreService` and hybrid retrieval are FAISS- and LangChain-aware (some TODOs acknowledge `VectorStorePort` gap). |
| **API** | Routers are FastAPI-specific (expected). **Leak:** dependency graph resolves chat/retrieval use cases **through `RAGService` on `RAGCraftApp`**, not through a neutral application composition root. |
| **Streamlit in core** | `src/core/chain_state.py` and `src/core/app_state.py` import Streamlit—violates “domain/application agnostic” goals and blocks reuse outside Streamlit. |

### Façades and oversized responsibilities

- **`RAGCraftApp`:** Large, multi-concern façade (auth, projects, documents, caching, ingestion, RAG, evaluation, exports). Duplicates or parallels logic also present on services (e.g. `list_project_documents` mirrors `ProjectService.list_project_documents`), increasing drift risk.
- **`RAGService`:** Builds `BuildPipelineUseCase`, `InspectPipelineUseCase`, `PreviewSummaryRecallUseCase`, `AskQuestionUseCase` internally—**composition inside a service** rather than at `BackendComposition` or API-only wiring.
- **`BackendComposition`:** Owns many singletons but **does not** own the full use-case graph; split brain with `RAGCraftApp` and FastAPI `Depends`.

### Pass-through use cases

Examples (non-exhaustive): `ListProjectsUseCase`, `CreateProjectUseCase`, `ListProjectDocumentsUseCase`, `CreateQaDatasetEntryUseCase`, `DeleteQaDatasetEntryUseCase`, `UpdateQaDatasetEntryUseCase`, `ListQaDatasetEntriesUseCase`—each largely forwards to a concrete `*Service` with minimal invariants or domain rules in the use-case type itself.

### UI still coupled to orchestration, not HTTP/API boundaries

- **`pages/*`** and **`src/ui/*`** depend on **`RAGCraftApp`** and service behavior, not on versioned API contracts.
- **FastAPI** is a parallel entrypoint that reuses the same façade-backed graph rather than a dedicated application-facing composition module used by both transports.

---

## 3. Migration constraints (must remain true during refactor)

1. **FastAPI endpoints must keep working** — Same route paths, request/response contracts, and status/error semantics unless changes are versioned and callers updated; existing tests and clients should not break silently.
2. **Streamlit must keep working during migration** — All current `pages/` and dependent `src/ui` flows remain functional; session-based app singleton and chain cache behavior preserved until explicitly replaced with a documented alternative.
3. **No breaking change to persisted SQLite data** without an explicit migration — Schema, table names, column meanings, and repository read/write contracts for app DB (including QA dataset, assets, query logs, settings) stay compatible or are migrated with a checked-in migration step.
4. **No breaking change to ingestion, evaluation, or query logging behavior** unless documented — Ingested asset shapes, vector index updates, evaluation outputs, benchmark serialization, and query log fields/filters should remain observably equivalent; any intentional change gets a short behavioral note (changelog or this doc series).

---

## 4. Target refactor invariants

1. **Inward dependencies:** `src/domain` never imports FastAPI, Streamlit, SQLite drivers, FAISS, or LangChain packages; only pure Python and stdlib (plus typing) unless a deliberate, documented exception is retired.
2. **Ports at boundaries:** Vector store, embeddings, LLM calls, file IO, and persistence are accessed through **domain/application ports** implemented in `src/infrastructure`, not through ad hoc imports from services into domain.
3. **Single composition story:** One primary composition path (or clearly layered facades) builds use cases for a process—**API and Streamlit share instances where state must match** (e.g. query log), without duplicating hidden singletons.
4. **Transport ignorance:** `src/application` use cases do not depend on `Request`, `st.session_state`, or Pydantic API models; HTTP and Streamlit map DTOs at the edge.
5. **Routers stay thin:** `apps/api/routers/*` parse/validate, call use cases, map to schemas—**no new business rules** in route handlers.
6. **Streamlit lives under interfaces:** Streamlit-specific state, caching, and page wiring migrate toward `src/interfaces/streamlit` (and `pages/`) per target tree; **`src/core` loses Streamlit imports** or is renamed/absorbed into interfaces.
7. **Façade shrink:** `RAGCraftApp` either dissolves into explicit interface adapters or shrinks to **delegation only**, without duplicating service methods that already exist on use cases or services.
8. **Use cases earn their keep:** Pass-through use cases are merged upward into coherent application services **or** gain real orchestration/invariants—no long-term “use case = one service call” indirection without justification.
9. **Persistence evolution is explicit:** Any SQLite shape change ships with a **migration or backward-compatible dual-read** period; no silent incompatible writes.
10. **Behavioral parity is test-backed:** Ingestion, evaluation, RAG answers, and query logging keep **integration or contract tests** green when refactoring; intentional deltas are documented before merge.

---

## 5. Document control

| Version | Date | Notes |
|---------|------|--------|
| 1.0 | 2025-03-22 | Initial baseline from repository inspection. |

When the architecture changes materially, update this file or add a dated successor under `docs/migration/`.
