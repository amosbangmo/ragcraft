# Orchestration migration — final verification report (RAGCraft)

**Document type:** Historical closure report for the orchestration / layering migration track.  
**Verification date:** 2026-03-22 (Prompt 6: audit, tests, legacy-import grep).  
**Live architecture spec:** [`ARCHITECTURE_TARGET.md`](../../ARCHITECTURE_TARGET.md)  
**Enforced import rules:** [`tests/architecture/README.md`](../../tests/architecture/README.md)

> **Authoritative orchestration verdict (Prompt 5):** See **[`ORCHESTRATION_MIGRATION_FINAL_REPORT.md`](./ORCHESTRATION_MIGRATION_FINAL_REPORT.md)** for the current end-state after RAG/composition/port refactors. Sections below labeled “remaining deviations” include **obsolete** items (e.g. `RAGService` and concrete use-case coupling were addressed in later commits).

---

## 1. Current architecture status

### Target structure (reached)

| Area | Location | Status |
|------|----------|--------|
| **HTTP API** | `apps/api/` | Primary integration surface; routers use `Depends` → `BackendApplicationContainer` / use cases. |
| **Application orchestration** | `src/application/use_cases/**`, `src/application/chat/orchestration/**` | Use cases own user-journey sequencing; chat helpers (e.g. pipeline query logging) live under `orchestration/`. |
| **Concrete runtime implementations** | `src/infrastructure/adapters/{rag,evaluation,document,workspace,chat,qa_dataset,query_logging}/` | Former `src/infrastructure/services` tree **removed**; code lives in typed adapter subpackages. |
| **Other infrastructure** | `src/infrastructure/persistence/`, `src/infrastructure/vectorstores/`, `src/infrastructure/llm/`, etc. | Technical I/O and drivers. |
| **SQLite port implementations** | `src/adapters/sqlite/` | Domain port implementations (users, assets, settings). |
| **Domain** | `src/domain/**` | Entities, value objects, ports; no framework / LangChain / sqlite imports (enforced by tests). |
| **Streamlit + UI** | `pages/`, `src/ui/` | Presentation; call **`BackendClient`** façade methods and view models — no direct `src.domain` / `src.infrastructure` / `src.composition` imports (enforced). |
| **Gateway** | `src/frontend_gateway/` | `HttpBackendClient`, `InProcessBackendClient`, `protocol.BackendClient`, HTTP payloads; **no** `src.infrastructure` imports (enforced). |
| **Composition** | `src/composition/` | `build_backend()`, `BackendApplicationContainer`, wiring graph. |
| **Removed shim** | `src/backend/` | **Absent** from tree; tests assert directory does not exist and `src/` does not import `src.backend`. |

### Remaining deviations (honest)

1. **Use cases depend on concrete adapter classes** — Several use cases import types such as `RAGService`, `EvaluationService`, `ProjectService`, `IngestionService` from `src.infrastructure.adapters.*` instead of narrow ports only. This is **not** a legacy package violation; it is **remaining coupling** that a future track could replace with explicit ports + injection.
2. **`RAGService` (adapter) still builds a subgraph of chat use cases** — Orchestration is largely in `src/application`, but `RAGService` remains a **composition-heavy adapter** that instantiates and exposes use-case shortcuts for the container. Works; further slimming is optional hardening.
3. **`HttpBackendClient` methods that have no REST equivalent** — e.g. `generate_answer_from_pipeline` / `evaluate_gold_qa_dataset_with_runner` raise `NotImplementedError`; callers use documented HTTP routes (`POST /evaluation/manual`, `POST /evaluation/dataset/run`) instead. This is intentional boundary documentation, not a missing migration step.
4. **FastAPI package touches SQLite bootstrap** — `apps/api/dependencies.py` may call `init_app_db` for app tables (documented transitional pattern).

---

## 2. Removed legacy areas

### `src/backend/`

- **Status:** **Removed.** No `src/backend/` directory under the repo’s `src/` tree.
- **Enforcement:** `tests/architecture/test_deprecated_backend_and_gateway_guardrails.py` asserts the path is absent and that no file under `src/` imports `src.backend`.
- **Residual mentions:** Only in **documentation and architecture test strings** (explaining the removal), not in production imports.

### `src/infrastructure/services`

- **Status:** **Removed** as a package. Runtime modules were moved to **`src/infrastructure/adapters/`** with subpackages: `rag`, `evaluation`, `document`, `workspace`, `chat`, `qa_dataset`, `query_logging`.
- **Enforcement:** Repository grep for `src.infrastructure.services` / `infrastructure.services` under Python sources: **no matches** (post–doc update). Application layer may import only `src.infrastructure.adapters` among infrastructure packages (see `tests/architecture/test_layer_boundaries.py`).
- **Tests:** `tests/infrastructure_services/` remains the historical name for unit tests targeting adapter modules (not a second `services` tree).

### `src.services` (legacy package name)

- **Status:** **Not used** as an import target under `src/` (forbidden by layer tests). References appear only in **forbidden-prefix lists** in architecture tests.

---

## 3. Application orchestration map

All classes below live under **`src/application/use_cases/`** unless noted.

### Chat / RAG

| Use case | Module |
|----------|--------|
| `BuildRagPipelineUseCase` | `use_cases/chat/build_rag_pipeline.py` |
| `AskQuestionUseCase` | `use_cases/chat/ask_question.py` |
| `InspectRagPipelineUseCase` | `use_cases/chat/inspect_rag_pipeline.py` |
| `PreviewSummaryRecallUseCase` | `use_cases/chat/preview_summary_recall.py` |
| `GenerateAnswerFromPipelineUseCase` | `use_cases/chat/generate_answer_from_pipeline.py` |
| `CompareRetrievalModesUseCase` | `use_cases/retrieval/compare_retrieval_modes.py` |

**Application policies / helpers:** `src/application/use_cases/chat/orchestration/` — e.g. `PipelineQueryLogEmitter`, `recall_then_assemble_pipeline`, ports for pipeline steps.

### Projects / workspace

| Use case | Module |
|----------|--------|
| `CreateProjectUseCase` | `use_cases/projects/create_project.py` |
| `ListProjectsUseCase` | `use_cases/projects/list_projects.py` |
| `ResolveProjectUseCase` | `use_cases/projects/resolve_project.py` |
| `ListProjectDocumentsUseCase` | `use_cases/projects/list_project_documents.py` |
| `GetProjectDocumentDetailsUseCase` | `use_cases/projects/get_project_document_details.py` |
| `ListDocumentAssetsForSourceUseCase` | `use_cases/projects/list_document_assets_for_source.py` |
| `GetProjectRetrievalPresetLabelUseCase` | `use_cases/projects/get_project_retrieval_preset_label.py` |
| `InvalidateProjectChainCacheUseCase` | `use_cases/projects/invalidate_project_chain_cache.py` |

### Ingestion

| Use case | Module |
|----------|--------|
| `IngestUploadedFileUseCase` | `use_cases/ingestion/ingest_uploaded_file.py` |
| `IngestFilePathUseCase` | `use_cases/ingestion/ingest_file_path.py` |
| `ReindexDocumentUseCase` | `use_cases/ingestion/reindex_document.py` |
| `DeleteDocumentUseCase` | `use_cases/ingestion/delete_document.py` |

Shared helpers: `use_cases/ingestion/ingest_common.py`; asset replacement helpers in `use_cases/ingestion/replace_document_assets.py`.

### Evaluation / QA dataset / logs / export

| Use case | Module |
|----------|--------|
| `RunManualEvaluationUseCase` | `use_cases/evaluation/run_manual_evaluation.py` |
| `RunGoldQaDatasetEvaluationUseCase` | `use_cases/evaluation/run_gold_qa_dataset_evaluation.py` |
| `BenchmarkExecutionUseCase` | `use_cases/evaluation/benchmark_execution.py` |
| `GenerateQaDatasetUseCase` | `use_cases/evaluation/generate_qa_dataset.py` |
| `ListQaDatasetEntriesUseCase` | `use_cases/evaluation/list_qa_dataset_entries.py` |
| `CreateQaDatasetEntryUseCase` | `use_cases/evaluation/create_qa_dataset_entry.py` |
| `UpdateQaDatasetEntryUseCase` | `use_cases/evaluation/update_qa_dataset_entry.py` |
| `DeleteQaDatasetEntryUseCase` | `use_cases/evaluation/delete_qa_dataset_entry.py` |
| `DeleteAllQaDatasetEntriesUseCase` | `use_cases/evaluation/delete_all_qa_dataset_entries.py` |
| `ListRetrievalQueryLogsUseCase` | `use_cases/evaluation/list_retrieval_query_logs.py` |
| `BuildBenchmarkExportArtifactsUseCase` | `use_cases/evaluation/build_benchmark_export_artifacts.py` |

Supporting module: `use_cases/evaluation/rag_answer_for_eval.py` (RAG inspect + answer for eval flows).

### Settings

| Use case | Module |
|----------|--------|
| `GetEffectiveRetrievalSettingsUseCase` | `use_cases/settings/get_effective_retrieval_settings.py` |
| `UpdateProjectRetrievalSettingsUseCase` | `use_cases/settings/update_project_retrieval_settings.py` |

**Preset merge port:** `src/application/settings/retrieval_preset_merge_port.py` (used by UI and HTTP paths).

### Composition entry

- **`BackendApplicationContainer`** (`src/composition/application_container.py`) exposes memoized use-case factories consumed by FastAPI and `InProcessBackendClient`.

---

## 4. Boundary validation

| Layer | Responsibility | Verification |
|--------|------------------|--------------|
| **Domain** | Pure models, domain services, ports (`domain/ports`, `domain/shared/*_port`). | `tests/architecture/test_layer_boundaries.py::test_domain_does_not_depend_on_outer_layers` |
| **Application** | Use cases, DTOs, HTTP wire helpers, policies; **no** `src.infrastructure` imports (wiring in composition). Use cases must not import `src.frontend_gateway`. | `test_application_does_not_depend_on_ui_or_infrastructure`, `test_application_orchestration_purity` |
| **Infrastructure** | Adapters, persistence, vector stores, LLM integration. Adapters under `adapters/` may import `src.application` where needed; other infra packages may not import application (test). | `test_infrastructure_does_not_depend_on_application_or_streamlit` |
| **API routers** | Map HTTP ↔ use cases; no direct infrastructure imports. | `test_api_routers_do_not_import_infrastructure` |
| **Streamlit / UI** | No `src.domain`, `src.infrastructure`, `src.composition`, `apps.api` imports. | `test_streamlit_pages_and_ui_avoid_direct_backend_internals` |
| **Frontend gateway** | No `src.infrastructure` imports. | `test_frontend_gateway_does_not_import_infrastructure_internals` |
| **FastAPI package** | No `src.infrastructure.adapters`, `src.infrastructure.services`, `src.backend`, `src.adapters`, `src.services` imports. | `test_apps_api_package_avoids_runtime_services_layer` |

**UI / API vs orchestration:** Pages and `src/ui` call **`BackendClient`** façade methods (including chat session helpers and existing ask/inspect/evaluate routes). **`InProcessBackendClient`** delegates to the **same use cases** as HTTP for the operations it implements. No `pages/` or `src/ui/` imports of `src.composition` were found in a repo grep.

---

## 5. Remaining issues

Only **real** follow-ups worth tracking:

1. **Production identity** — `X-User-Id` (and similar) are not browser-grade auth for a public API.
2. **Concrete types in use cases** — Prefer ports + smaller adapters over importing large `*Service` facades from application code (incremental refactor).
3. **`RAGService` composition** — Optional: move use-case wiring fully into `composition/` and leave `RAGService` as a thin delegate.
4. **Persistence layout** — SQLite port implementations live under **`src/infrastructure/adapters/sqlite/`**; some forwarding modules remain under **`src/infrastructure/persistence/sqlite/`** for historical import paths.
5. **Optional deps** — Full `build_backend()` may require `unstructured`; some architecture tests skip if missing — ensure CI installs full `requirements.txt` if you want zero skips.

**Explicit non-issues (do not mistake for drift):**

- Mentions of `src.backend` / `src.services` inside **architecture test sources** are **intentional** forbidden-prefix checks.
- `HttpBackendClient` / `InProcessBackendClient` **must** stay aligned; `tests/architecture/test_fastapi_migration_guardrails.py` guards public surface drift.

---

## 6. Recommended next priorities (after orchestration)

Ordered shortlist for **subsequent** tracks (not required to call orchestration “done”):

1. **P0 — AuthN/Z** — Verified principals (e.g. JWT), CORS, and a clear browser security story.
2. **P1 — Application ↔ adapter ports** — Replace direct `RAGService` / `EvaluationService` constructor coupling in use cases with narrower protocols where ROI is high.
3. **P1 — API lifespan / DB bootstrap** — Move `init_app_db` style setup out of hot `Depends` paths if desired.
4. **P2 — Persistence consolidation** — Single obvious home for SQLite helpers and migrations.
5. **P2 — OpenAPI / client parity** — Any new `BackendClient` method should ship with route + contract test in the same change.
6. **P3 — CI determinism** — Install full deps so composition/architecture tests never skip in CI.

---

## Verification performed (this pass)

| Check | Result |
|-------|--------|
| Full test suite | **562 passed**, **4 skipped** |
| `src/backend/` exists | **No** |
| `src/infrastructure/services/` exists | **No** |
| Python imports of `src.infrastructure.services` | **None** |
| Python imports of `src.backend` under `src/` | **None** (tests only reference the string as a forbidden module) |
| `pages/` + `src/ui/` importing `src.composition` | **None** (grep) |

```bash
pytest -q
pytest tests/architecture -q
pytest tests/apps_api -q
```

---

## Migration completeness statement

| Dimension | Status |
|-----------|--------|
| Legacy orchestration packages (`src/backend`, `src/infrastructure/services`) | **Removed** |
| Use-case ownership of user journeys | **Met** (with noted adapter coupling) |
| UI / API entrypoints without parallel ad-hoc orchestration in `pages/` / `src/ui/` | **Met** for `BackendClient`-driven flows |
| Automated boundary enforcement | **Met** (`tests/architecture/`) |
| Production SaaS readiness | **Not claimed** |

---

## Streamlit runtime modes (reference)

| Mode | `RAGCRAFT_BACKEND_CLIENT` | Notes |
|------|---------------------------|--------|
| **HTTP** (default if unset) | `http` | Streamlit calls FastAPI; same contract as a SPA. |
| **In-process** | `in_process` | `InProcessBackendClient` + `BackendApplicationContainer` in the Streamlit process. |

See [`docs/migration/streamlit-fastapi-dev.md`](streamlit-fastapi-dev.md).

---

## Related documents

- **[`docs/migration/orchestration_audit.md`](orchestration_audit.md)** — Older flow inventory; paths were updated to `src/infrastructure/adapters/` where applicable. For **closure truth**, prefer **this report** and **`ARCHITECTURE_TARGET.md`**.
