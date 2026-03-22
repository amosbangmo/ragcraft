# Orchestration ownership audit

> **Status:** Snapshot / working notes. **Authoritative closure state** for the orchestration track is **[`MIGRATION_COMPLETE_REPORT.md`](MIGRATION_COMPLETE_REPORT.md)** (2026-03-22). Legacy package `src/infrastructure/adapters/` was **removed**; concrete code lives under **`src/infrastructure/adapters/`** (subpackages `rag`, `evaluation`, `document`, etc.).

This document inventories **application-flow orchestration** that still lives outside the application layer, is **duplicated** across transport paths, or sits behind **compatibility shims**. It follows the migration toward Clean Architecture with FastAPI.

**Scope:** Historical flow inventory; paths below use the **adapters** tree. Some narrative rows predate `InProcessBackendClient` delegating fully to use cases—verify against `src/frontend_gateway/in_process.py` before relying on them.

---

## Target orchestration rule (repository standard)

| Layer | Owns |
|--------|------|
| **Application** (`src/application/**`) | Use cases, workflow orchestration, command/query DTOs, cross-cutting application policies (e.g. pipeline query-log policy) that coordinate domain + ports. |
| **Domain** (`src/domain/**`) | Entities, value objects, pure rules, port interfaces (`domain/ports`, `domain/shared/*_port`). No I/O, no framework imports, no multi-step workflows that know about SQLite/FAISS/HTTP. |
| **Infrastructure** (`src/infrastructure/**`, `src/adapters/**`) | Concrete adapters: persistence, extractors, LLM clients, FAISS/vector I/O, SQLite query logs. **Not** multi-step user-facing workflows; thin technical helpers only. |
| **Interfaces** | **FastAPI** (`apps/api/**`): resolve dependencies, map HTTP ↔ DTOs, call use cases. **Streamlit** (`pages/**`, `src/ui/**`): session/UI state, call `BackendClient` only for backend work—no parallel business orchestration beyond presentation. |
| **Composition** (`src/composition/**`) | Wire ports to implementations and expose use-case factories (`BackendApplicationContainer`). |

**Corollary:** Anything named `*Service` under `src/infrastructure/adapters/` that **sequences** multiple domain steps for a user journey is a **misplaced orchestrator** until moved or split into a use case + true infrastructure adapters.

---

## Compatibility shims (should disappear after import migration)

- **`src/backend/`** — **Removed.** Canonical implementations live in `src/infrastructure/adapters/*`; architecture tests assert the directory is absent and nothing under `src/` imports `src.backend`.

- **`src/application/evaluation/__init__.py`** — docstring updated to reference `src.infrastructure.adapters.evaluation` and use cases (no stale `src/services/*` claim).

---

## Flow inventory

### 1. Project creation / project loading

| Item | Detail |
|------|--------|
| **Entrypoints (HTTP)** | `apps/api/routers/projects.py` — uses `CreateProjectUseCase`, `ListProjectsUseCase`, `ResolveProjectUseCase`, `GetProjectDocumentDetailsUseCase`, etc. via `apps/api/dependencies.py`. |
| **Entrypoints (Streamlit)** | `pages/projects.py`, `src/ui/project_selector.py`, `src/ui/page_header.py`, `src/ui/navigation.py` via `BackendClient`. |
| **Orchestrators today** | Use cases under `src/application/use_cases/projects/*`. **`InProcessBackendClient`** delegates to the same `projects_*_use_case` factories as FastAPI (e.g. `list_projects`, `create_project`, `get_project` → `ListProjectsUseCase`, `CreateProjectUseCase`, `ResolveProjectUseCase`). |
| **Dependencies** | `src/infrastructure/adapters/workspace/project_service.py` (persistence/filesystem), docstore paths via project use cases. |
| **Target** | Keep `ProjectService` as an adapter behind use cases only. |
| **Action** | **Done** for gateway parity; optional future rename `ProjectService` → adapter naming for clarity. |

### 2. Ingestion / reindex / deletion

| Item | Detail |
|------|--------|
| **Entrypoints (HTTP)** | `apps/api/routers/ingestion.py` (or projects router sections) + dependencies injecting `IngestUploadedFileUseCase`, `ReindexDocumentUseCase`, `DeleteDocumentUseCase`. |
| **Entrypoints (Streamlit)** | `pages/ingestion.py`, `src/ui/document_actions.py` → `BackendClient.ingest_uploaded_file`, `reindex_project_document`, `delete_project_document`. |
| **Orchestrators today** | **Application:** `src/application/use_cases/ingestion/{ingest_uploaded_file,reindex_document,delete_document}.py` — correct placement. **Infrastructure:** `src/infrastructure/adapters/document/ingestion_service.py` implements extraction/summarization **pipeline** (technical; acceptable as adapter if use case remains the entry). |
| **Dependencies** | `IngestionService`, `DocStoreService`, `VectorStoreService`, `invalidate_project_chain` hook. |
| **Target** | Keep orchestration in ingestion use cases; keep `IngestionService` as a **worker/adapter** (possibly rename later for clarity). |
| **Action** | **Keep** use cases; **optional** thin `in_process` already delegates to use cases for delete/reindex/ingest — aligned. |

### 3. Ask / inspect / retrieval preview (summary recall)

| Item | Detail |
|------|--------|
| **Entrypoints (HTTP)** | `apps/api/routers/chat.py` — `AskQuestionUseCase`, `InspectRagPipelineUseCase`, `PreviewSummaryRecallUseCase`, `ResolveProjectUseCase`. |
| **Entrypoints (Streamlit)** | `pages/chat.py`, `pages/search.py`, `pages/retrieval_inspector.py` → `BackendClient.ask_question`, `search_project_summaries`, `inspect_retrieval`. |
| **Orchestrators today** | Use cases under `src/application/use_cases/chat/*` plus `src/application/chat/orchestration/*`. **`RAGService`** (`src/infrastructure/adapters/rag/rag_service.py`) still **constructs** several chat use cases internally (composition-heavy adapter). **`InProcessBackendClient`** calls **`chat_*_use_case.execute`** for ask / inspect / preview (aligned with FastAPI routers). |
| **Dependencies** | Vector/doc/rerank/retrieval-settings adapters, `AnswerGenerationService`, optional query log adapter. |
| **Target** | Optional: move RAG use-case wiring from `RAGService` into `composition/` so the adapter stays thin. |
| **Action** | Gateway **aligned**; **optional** slim `RAGService` when touching composition. |

### 4. Manual evaluation

| Item | Detail |
|------|--------|
| **Entrypoints (HTTP)** | `apps/api/routers/evaluation.py` → `RunManualEvaluationUseCase`. |
| **Entrypoints (Streamlit)** | `src/ui/evaluation_manual_tab.py` → `BackendClient.evaluate_manual_question`. |
| **Orchestrators today** | **Application:** `src/application/use_cases/evaluation/run_manual_evaluation.py` — uses `run_rag_inspect_and_answer_for_eval` + **`manual_evaluation_result_from_rag_outputs`** in `src/infrastructure/adapters/evaluation/manual_evaluation_service.py`. |
| **Dependencies** | `RAGService`, `EvaluationService`, domain models in `manual_evaluation_result.py`. |
| **Target** | Use case keeps orchestration; **domain-style** helpers (expectation comparison, issue detection thresholds) in `manual_evaluation_service.py` should migrate toward **`src/domain/**`** (pure functions) with infrastructure holding only I/O-bound scoring if any. |
| **Action** | **Split** `manual_evaluation_service.py`: extract pure rules to domain; leave thin glue. **Deduplicate** with gold dataset runner (see below). |

### 5. Dataset (gold QA) evaluation

| Item | Detail |
|------|--------|
| **Entrypoints (HTTP)** | `apps/api/routers/evaluation.py` → `RunGoldQaDatasetEvaluationUseCase`. |
| **Entrypoints (Streamlit)** | `src/ui/evaluation_dataset_tab.py` → `BackendClient.evaluate_gold_qa_dataset`. |
| **Orchestrators today** | **Application:** `src/application/use_cases/evaluation/run_gold_qa_dataset_evaluation.py` — loads entries, builds **`pipeline_runner`** closure. Delegates aggregation to **`EvaluationService.evaluate_gold_qa_dataset`** → **`BenchmarkExecutionUseCase`** (`src/application/use_cases/evaluation/benchmark_execution.py`). |
| **Dependencies** | `ListQaDatasetEntriesUseCase`, `RAGService`, `EvaluationService`, many `src/infrastructure/adapters/*` row/metric helpers composed **inside** `EvaluationService.__init__`. |
| **Target** | Single shared application helper (e.g. “run RAG pipeline + answer for evaluation”) used by manual and gold flows. **`EvaluationService` should not construct `BenchmarkExecutionUseCase`** — composition root should wire `BenchmarkExecutionUseCase` with injected collaborators. |
| **Action** | **Move** benchmark execution wiring out of `evaluation_service.py` into `BackendApplicationContainer` / factory module. **Refactor** duplicate `pipeline_runner` logic shared with `RunManualEvaluationUseCase`. |

### 6. QA dataset CRUD and generation

| Item | Detail |
|------|--------|
| **Entrypoints (HTTP)** | `apps/api/routers/evaluation.py` + DTOs; dependencies for create/list/update/delete/generate. |
| **Entrypoints (Streamlit)** | Evaluation tabs / `pages/evaluation.py` session helpers → `BackendClient` QA methods. |
| **Orchestrators today** | **Application:** `src/application/use_cases/evaluation/*` (`create_qa_dataset_entry`, `list_qa_dataset_entries`, `update_qa_dataset_entry`, `delete_qa_dataset_entry`, `generate_qa_dataset`). `GenerateQaDatasetUseCase` correctly orchestrates modes (append/replace/dedup) and calls `QADatasetGenerationService`. |
| **Dependencies** | `QADatasetService`, `QADatasetGenerationService`, `src/infrastructure/llm/qa_dataset_llm_gateway.py`. |
| **Target** | Already largely correct; generation service remains infrastructure **adapter** behind the use case. |
| **Action** | **Keep**; optionally rename `*Service` to `*Adapter` when touching files. |

### 7. Retrieval comparison (FAISS vs hybrid)

| Item | Detail |
|------|--------|
| **Entrypoints (HTTP)** | `apps/api/routers/chat.py` → `CompareRetrievalModesUseCase`. |
| **Entrypoints (Streamlit)** | `pages/retrieval_comparison.py` → `BackendClient.compare_retrieval_modes`. |
| **Orchestrators today** | **Application:** `src/application/use_cases/retrieval/compare_retrieval_modes.py` (resolve project + delegate). **Infrastructure:** `src/infrastructure/adapters/rag/retrieval_comparison_service.py` implements the **full multi-question loop**, latency extraction, and summary — this is **application orchestration**, not an adapter. |
| **Dependencies** | `RAGService.inspect_pipeline` (twice per question). |
| **Target** | Move comparison workflow into **`src/application/chat/`** (use case module or `application/chat/services/retrieval_comparison.py`), keeping only RAG/pipeline calls as ports. |
| **Action** | **Optional:** move multi-question loop from `RetrievalComparisonService` into application if you want stricter “adapter = thin” semantics. **`InProcessBackendClient.compare_retrieval_modes`** now calls **`chat_compare_retrieval_modes_use_case.execute`** (aligned with HTTP). |

### 8. Query logging and benchmark export orchestration

| Item | Detail |
|------|--------|
| **Query logging** | **Application:** `AskQuestionUseCase` (`src/application/use_cases/chat/ask_question.py`) defers logging via `QueryLogPort`; `BuildRagPipelineUseCase` uses `PipelineQueryLogEmitter` (`src/application/use_cases/chat/orchestration/pipeline_query_log_emitter.py`). **Infrastructure:** `src/infrastructure/adapters/query_logging/query_log_service.py` implements persistence. **Listing logs:** `ListRetrievalQueryLogsUseCase` (`src/application/use_cases/evaluation/list_retrieval_query_logs.py`) — correct. |
| **Benchmark export** | **Application:** `BuildBenchmarkExportArtifactsUseCase` + `BenchmarkReportFormatter` — correct, thin. |
| **Action** | **Keep**; ensure all “ask” entrypoints go through the same use case so logging policy stays consistent (see §3). |

---

## Additional misplaced composition

| Location | Issue | Target action |
|----------|--------|----------------|
| `src/infrastructure/adapters/evaluation/evaluation_service.py` | Instantiates `BenchmarkExecutionUseCase` and many metric services in `__init__`. | **Move** wiring to `BackendApplicationContainer` (or evaluation composition module). |
| `src/infrastructure/adapters/rag/rag_service.py` | Builds chat use-case graph. | **Move** to application/composition (see §3). |
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
| `src/infrastructure/adapters/rag/rag_service.py` | **No** (target: thin legacy façade or deleted). |
| `src/infrastructure/adapters/rag/retrieval_comparison_service.py` | **No** (target: application module). |
| `src/infrastructure/adapters/evaluation/evaluation_service.py` | **No** (target: adapter façade only, or split by port). |
| `src/infrastructure/adapters/document/ingestion_service.py` | **Adapter** — single-document technical pipeline OK behind ingestion use cases. |
| `apps/api/**` | **No** — transport only. |
| `pages/**`, `src/ui/**` | **No** — UI + `BackendClient` calls only. |

---

## Exact files to move / refactor in next steps (ordered suggestion)

1. `src/frontend_gateway/in_process.py` — route all operations through `BackendApplicationContainer` use cases; remove inline `get_project_document_details` duplication.
2. `src/infrastructure/adapters/rag/retrieval_comparison_service.py` — **move** workflow into `src/application/use_cases/chat/` (or `retrieval/`); update `BackendComposition` / container wiring.
3. `src/infrastructure/adapters/rag/rag_service.py` — **extract** use-case construction to composition; narrow `RAGService` or remove.
4. `src/infrastructure/adapters/evaluation/evaluation_service.py` — **extract** `BenchmarkExecutionUseCase` wiring to container.
5. `src/application/use_cases/evaluation/run_manual_evaluation.py` + `run_gold_qa_dataset_evaluation.py` — **extract** shared “eval pipeline run” helper.
6. `src/infrastructure/adapters/evaluation/manual_evaluation_service.py` — **split** pure domain helpers → `src/domain/`.
7. `src/application/evaluation/__init__.py` — **fix** stale `src/services` documentation if still present.

---

*Generated as part of the Clean Architecture migration audit; commit: `docs(migration): audit remaining orchestration ownership`.*
