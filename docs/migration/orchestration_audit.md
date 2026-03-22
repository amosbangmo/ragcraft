# Orchestration ownership audit

This document inventories **application-flow orchestration** that still lives outside the application layer, is **duplicated** across transport paths, or sits behind **compatibility shims**. It follows the migration toward Clean Architecture with FastAPI.

**Scope:** no refactors were performed; file paths are concrete.

---

## Target orchestration rule (repository standard)

| Layer | Owns |
|--------|------|
| **Application** (`src/application/**`) | Use cases, workflow orchestration, command/query DTOs, cross-cutting application policies (e.g. pipeline query-log policy) that coordinate domain + ports. |
| **Domain** (`src/domain/**`) | Entities, value objects, pure rules, port interfaces (`domain/ports`, `domain/shared/*_port`). No I/O, no framework imports, no multi-step workflows that know about SQLite/FAISS/HTTP. |
| **Infrastructure** (`src/infrastructure/**`, `src/adapters/**`) | Concrete adapters: persistence, extractors, LLM clients, FAISS/vector I/O, SQLite query logs. **Not** multi-step user-facing workflows; thin technical helpers only. |
| **Interfaces** | **FastAPI** (`apps/api/**`): resolve dependencies, map HTTP ↔ DTOs, call use cases. **Streamlit** (`pages/**`, `src/ui/**`): session/UI state, call `BackendClient` only for backend work—no parallel business orchestration beyond presentation. |
| **Composition** (`src/composition/**`) | Wire ports to implementations and expose use-case factories (`BackendApplicationContainer`). |

**Corollary:** Anything named `*Service` under `src/infrastructure/services/` that **sequences** multiple domain steps for a user journey is a **misplaced orchestrator** until moved or split into a use case + true infrastructure adapters.

---

## Compatibility shims (should disappear after import migration)

- **`src/backend/`** — **Removed.** Canonical implementations live in `src/infrastructure/services/*`; architecture tests assert the directory is absent and nothing under `src/` imports `src.backend`.

- **`src/application/evaluation/__init__.py`** still documents benchmark math under `src/services/*`; **`src/services/` is empty** in this repo. **Target:** update that docstring to name real locations (`src/infrastructure/services/*`, `src/domain/evaluation/*`) when touching the package.

---

## Flow inventory

### 1. Project creation / project loading

| Item | Detail |
|------|--------|
| **Entrypoints (HTTP)** | `apps/api/routers/projects.py` — uses `CreateProjectUseCase`, `ListProjectsUseCase`, `ResolveProjectUseCase`, `GetProjectDocumentDetailsUseCase`, etc. via `apps/api/dependencies.py`. |
| **Entrypoints (Streamlit)** | `pages/projects.py`, `src/ui/project_selector.py`, `src/ui/page_header.py`, `src/ui/navigation.py` via `BackendClient`. |
| **Orchestrators today** | Use cases in `src/application/projects/use_cases/*` for API paths. **In-process Streamlit path:** `src/frontend_gateway/in_process.py` calls `ProjectService` directly for `list_projects`, `create_project`, `get_project` (**bypasses** `ListProjectsUseCase` / `CreateProjectUseCase`). |
| **Dependencies** | `src/infrastructure/services/project_service.py` (persistence/filesystem), `DocStoreService` for document detail rows. |
| **Target** | Application owns all mutations/queries: `InProcessBackendClient` should delegate to the same use cases as FastAPI (`projects_*_use_case`), not `project_service` directly. |
| **Action** | **Refactor** `in_process.py` + ensure HTTP client parity already hits REST routes that use use cases (no change needed there). **Rename/split** not required for `ProjectService` if it becomes a true adapter behind use cases only. |

### 2. Ingestion / reindex / deletion

| Item | Detail |
|------|--------|
| **Entrypoints (HTTP)** | `apps/api/routers/ingestion.py` (or projects router sections) + dependencies injecting `IngestUploadedFileUseCase`, `ReindexDocumentUseCase`, `DeleteDocumentUseCase`. |
| **Entrypoints (Streamlit)** | `pages/ingestion.py`, `src/ui/document_actions.py` → `BackendClient.ingest_uploaded_file`, `reindex_project_document`, `delete_project_document`. |
| **Orchestrators today** | **Application:** `src/application/ingestion/use_cases/{ingest_uploaded_file,reindex_document,delete_document}.py` — correct placement. **Infrastructure:** `src/infrastructure/services/ingestion_service.py` implements extraction/summarization **pipeline** (technical; acceptable as adapter if use case remains the entry). |
| **Dependencies** | `IngestionService`, `DocStoreService`, `VectorStoreService`, `invalidate_project_chain` hook. |
| **Target** | Keep orchestration in ingestion use cases; keep `IngestionService` as a **worker/adapter** (possibly rename later for clarity). |
| **Action** | **Keep** use cases; **optional** thin `in_process` already delegates to use cases for delete/reindex/ingest — aligned. |

### 3. Ask / inspect / retrieval preview (summary recall)

| Item | Detail |
|------|--------|
| **Entrypoints (HTTP)** | `apps/api/routers/chat.py` — `AskQuestionUseCase`, `InspectRagPipelineUseCase`, `PreviewSummaryRecallUseCase`, `ResolveProjectUseCase`. |
| **Entrypoints (Streamlit)** | `pages/chat.py`, `pages/search.py`, `pages/retrieval_inspector.py` → `BackendClient.ask_question`, `search_project_summaries`, `inspect_retrieval`. |
| **Orchestrators today** | Use cases live under `src/application/chat/use_cases/*` and **chat orchestration** under `src/application/chat/orchestration/*` (e.g. `PipelineQueryLogEmitter`). **However:** `src/infrastructure/services/rag_service.py` **constructs and owns** `BuildRagPipelineUseCase`, `AskQuestionUseCase`, `InspectRagPipelineUseCase`, `PreviewSummaryRecallUseCase`, `GenerateAnswerFromPipelineUseCase` internally and exposes `ask` / `inspect_pipeline` / `preview_summary_recall` shortcuts. `InProcessBackendClient` calls **`rag_service` methods**, not the use cases directly (unlike FastAPI). |
| **Dependencies** | Vector/doc/rerank/retrieval-settings services, `AnswerGenerationService`, optional `QueryLogService`. |
| **Target** | Application layer should **own use-case construction** (composition root or dedicated factory), not `RAGService`. `RAGService` should shrink to **adapter wiring** or be removed in favor of explicit use-case beans on `BackendApplicationContainer`. |
| **Action** | **Move/split:** lift RAG use-case wiring from `rag_service.py` into `application_container` (or a dedicated `composition/chat_wiring.py`). **Refactor** `InProcessBackendClient` to call the same use cases as `apps/api/routers/chat.py` (eliminate dual entrypath). |

### 4. Manual evaluation

| Item | Detail |
|------|--------|
| **Entrypoints (HTTP)** | `apps/api/routers/evaluation.py` → `RunManualEvaluationUseCase`. |
| **Entrypoints (Streamlit)** | `src/ui/evaluation_manual_tab.py` → `BackendClient.evaluate_manual_question`. |
| **Orchestrators today** | **Application:** `src/application/evaluation/use_cases/run_manual_evaluation.py` — sequences `ProjectService.get_project`, `RAGService.inspect_pipeline`, `RAGService.generate_answer_from_pipeline`, latency merge, then **`manual_evaluation_result_from_rag_outputs`** from `src/infrastructure/services/manual_evaluation_service.py`. |
| **Dependencies** | `RAGService`, `EvaluationService`, domain models in `manual_evaluation_result.py`. |
| **Target** | Use case keeps orchestration; **domain-style** helpers (expectation comparison, issue detection thresholds) in `manual_evaluation_service.py` should migrate toward **`src/domain/**`** (pure functions) with infrastructure holding only I/O-bound scoring if any. |
| **Action** | **Split** `manual_evaluation_service.py`: extract pure rules to domain; leave thin glue. **Deduplicate** with gold dataset runner (see below). |

### 5. Dataset (gold QA) evaluation

| Item | Detail |
|------|--------|
| **Entrypoints (HTTP)** | `apps/api/routers/evaluation.py` → `RunGoldQaDatasetEvaluationUseCase`. |
| **Entrypoints (Streamlit)** | `src/ui/evaluation_dataset_tab.py` → `BackendClient.evaluate_gold_qa_dataset`. |
| **Orchestrators today** | **Application:** `src/application/evaluation/use_cases/run_gold_qa_dataset_evaluation.py` — loads entries, builds **`pipeline_runner`** closure (duplicate structure to manual eval: inspect → generate answer → latency). Delegates aggregation to **`EvaluationService.evaluate_gold_qa_dataset`** → **`BenchmarkExecutionUseCase`** (`src/application/evaluation/use_cases/benchmark_execution.py`). |
| **Dependencies** | `ListQaDatasetEntriesUseCase`, `RAGService`, `EvaluationService`, many `src/infrastructure/services/*` row/metric helpers composed **inside** `EvaluationService.__init__`. |
| **Target** | Single shared application helper (e.g. “run RAG pipeline + answer for evaluation”) used by manual and gold flows. **`EvaluationService` should not construct `BenchmarkExecutionUseCase`** — composition root should wire `BenchmarkExecutionUseCase` with injected collaborators. |
| **Action** | **Move** benchmark execution wiring out of `evaluation_service.py` into `BackendApplicationContainer` / factory module. **Refactor** duplicate `pipeline_runner` logic shared with `RunManualEvaluationUseCase`. |

### 6. QA dataset CRUD and generation

| Item | Detail |
|------|--------|
| **Entrypoints (HTTP)** | `apps/api/routers/evaluation.py` + DTOs; dependencies for create/list/update/delete/generate. |
| **Entrypoints (Streamlit)** | Evaluation tabs / `pages/evaluation.py` session helpers → `BackendClient` QA methods. |
| **Orchestrators today** | **Application:** `src/application/evaluation/use_cases/*` (`create_qa_dataset_entry`, `list_qa_dataset_entries`, `update_qa_dataset_entry`, `delete_qa_dataset_entry`, `generate_qa_dataset`). `GenerateQaDatasetUseCase` correctly orchestrates modes (append/replace/dedup) and calls `QADatasetGenerationService`. |
| **Dependencies** | `QADatasetService`, `QADatasetGenerationService`, `src/infrastructure/llm/qa_dataset_llm_gateway.py`. |
| **Target** | Already largely correct; generation service remains infrastructure **adapter** behind the use case. |
| **Action** | **Keep**; optionally rename `*Service` to `*Adapter` when touching files. |

### 7. Retrieval comparison (FAISS vs hybrid)

| Item | Detail |
|------|--------|
| **Entrypoints (HTTP)** | `apps/api/routers/chat.py` → `CompareRetrievalModesUseCase`. |
| **Entrypoints (Streamlit)** | `pages/retrieval_comparison.py` → `BackendClient.compare_retrieval_modes`. |
| **Orchestrators today** | **Application:** `src/application/chat/use_cases/compare_retrieval_modes.py` (resolve project + delegate). **Infrastructure:** `src/infrastructure/services/retrieval_comparison_service.py` implements the **full multi-question loop**, latency extraction, and summary — this is **application orchestration**, not an adapter. |
| **Dependencies** | `RAGService.inspect_pipeline` (twice per question). |
| **Target** | Move comparison workflow into **`src/application/chat/`** (use case module or `application/chat/services/retrieval_comparison.py`), keeping only RAG/pipeline calls as ports. |
| **Action** | **Move** `RetrievalComparisonService` logic into application. **Fix** `InProcessBackendClient.compare_retrieval_modes` — it currently calls `self._container.backend.retrieval_comparison_service.compare` and **skips** `CompareRetrievalModesUseCase` (duplicates FastAPI path). Should call `container.chat_compare_retrieval_modes_use_case.execute(...)`. |

### 8. Query logging and benchmark export orchestration

| Item | Detail |
|------|--------|
| **Query logging** | **Application:** `AskQuestionUseCase` (`src/application/chat/use_cases/ask_question.py`) defers logging via `QueryLogPort`; `BuildRagPipelineUseCase` uses `PipelineQueryLogEmitter` (`src/application/chat/orchestration/pipeline_query_log_emitter.py`). **Infrastructure:** `src/infrastructure/services/query_log_service.py` implements persistence. **Listing logs:** `ListRetrievalQueryLogsUseCase` (`src/application/evaluation/use_cases/list_retrieval_query_logs.py`) — correct. |
| **Benchmark export** | **Application:** `BuildBenchmarkExportArtifactsUseCase` + `BenchmarkReportFormatter` — correct, thin. |
| **Action** | **Keep**; ensure all “ask” entrypoints go through the same use case so logging policy stays consistent (see §3). |

---

## Additional misplaced composition

| Location | Issue | Target action |
|----------|--------|----------------|
| `src/infrastructure/services/evaluation_service.py` | Instantiates `BenchmarkExecutionUseCase` and many metric services in `__init__`. | **Move** wiring to `BackendApplicationContainer` (or evaluation composition module). |
| `src/infrastructure/services/rag_service.py` | Builds chat use-case graph. | **Move** to application/composition (see §3). |
| `src/frontend_gateway/in_process.py` | Duplicates orchestration: `get_project_document_details` reimplements `GetProjectDocumentDetailsUseCase` inline; `compare_retrieval_modes` bypasses use case; chat paths use `rag_service` not use cases; project create/list bypass use cases. | **Refactor** to delegate exclusively to `BackendApplicationContainer` use-case properties. |
| `src/frontend_gateway/http_client.py` | Correctly maps to REST (good); ensure any new use-case-only APIs stay the single system of record. | **Maintain** parity when refactoring in-process client. |
| `src/ui/navigation.py` | Loads `backend_client.list_projects` for session sync (acceptable UI). Sidebar block references **`auth_service`** without import — **bug**, not orchestration (fix separately). | **Fix** import / use `streamlit_auth` consistently. |

---

## Streamlit / UI orchestration (acceptable vs not)

- **Acceptable:** `pages/evaluation.py` session reset (`_reset_evaluation_context_if_project_changed`), benchmark history in `evaluation_dataset_tab.py`, request runners — **presentation state** only.
- **Acceptable:** `pages/ingestion.py` looping uploaded files and calling `client.ingest_uploaded_file` per file — **I/O batching at UI** (could later become one use case if needed).
- **Not ideal long-term:** Any new business rules added under `src/ui/**` should move to application use cases.

---

## Summary: remaining orchestration problems

1. **Dual entrypaths (partially addressed):** FastAPI and in-process `BackendClient` should both go through the same use cases; any remaining `RAGService` shortcuts should be narrowed over time.
2. **Orchestration inside infrastructure:** `RAGService`, `RetrievalComparisonService`, and `EvaluationService` **construct or encode** multi-step workflows that belong in `src/application` or the composition root.
3. **Duplicated evaluation pipeline:** Manual and gold dataset use cases both encode inspect → answer → latency merge; should be one internal application helper.
4. **Docs:** `src/application/evaluation/__init__.py` may still reference a **non-existent** `src/services` tree in prose.
5. **`src/backend/`** — **removed** (canonical: `src.infrastructure.adapters`).

---

## Target ownership by module (after migration)

| Module / area | Owns orchestration? |
|---------------|---------------------|
| `src/application/use_cases/**` | **Yes** — primary home. |
| `src/application/use_cases/chat/orchestration/` | **Yes** — RAG-specific policies (query log emission, etc.). |
| `src/composition/application_container.py` | **Wires** use cases + ports; should own all use-case singleton construction currently hidden in `RAGService` / `EvaluationService`. |
| `src/infrastructure/services/rag_service.py` | **No** (target: thin legacy façade or deleted). |
| `src/infrastructure/services/retrieval_comparison_service.py` | **No** (target: application module). |
| `src/infrastructure/services/evaluation_service.py` | **No** (target: adapter façade only, or split by port). |
| `src/infrastructure/services/ingestion_service.py` | **Adapter** — single-document technical pipeline OK behind ingestion use cases. |
| `apps/api/**` | **No** — transport only. |
| `pages/**`, `src/ui/**` | **No** — UI + `BackendClient` calls only. |

---

## Exact files to move / refactor in next steps (ordered suggestion)

1. `src/frontend_gateway/in_process.py` — route all operations through `BackendApplicationContainer` use cases; remove inline `get_project_document_details` duplication.
2. `src/infrastructure/services/retrieval_comparison_service.py` — **move** workflow into `src/application/chat/`; update `BackendComposition` / container wiring.
3. `src/infrastructure/services/rag_service.py` — **extract** use-case construction to composition; narrow `RAGService` or remove.
4. `src/infrastructure/services/evaluation_service.py` — **extract** `BenchmarkExecutionUseCase` wiring to container.
5. `src/application/evaluation/use_cases/run_manual_evaluation.py` + `run_gold_qa_dataset_evaluation.py` — **extract** shared “eval pipeline run” helper.
6. `src/infrastructure/services/manual_evaluation_service.py` — **split** pure domain helpers → `src/domain/`.
7. `src/application/evaluation/__init__.py` — **fix** stale `src/services` documentation if still present.

---

*Generated as part of the Clean Architecture migration audit; commit: `docs(migration): audit remaining orchestration ownership`.*
