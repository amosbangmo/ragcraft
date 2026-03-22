# Persistence and retrieval ports (dependency inversion)

Canonical import path: `src.domain.ports`. Protocols remain defined next to their bounded context where they already lived; `src.domain.ports` re-exports them for composition roots and use cases.

## Mapping

| Port (interface) | Canonical definition | Current implementation | Consumed by (examples) |
|------------------|----------------------|-------------------------|-------------------------|
| **AssetRepositoryPort** | `src.domain.documents.asset_repository_port` | `DocStoreService` → SQLite asset repository | Ingest/reindex/delete document use cases, `finalize_ingestion_pipeline`, `replace_document_assets_for_reingest`, `GetProjectDocumentDetailsUseCase`, `ListDocumentAssetsForSourceUseCase` |
| **VectorStorePort** | `src.domain.retrieval.vector_store_port` | `VectorStoreService` (FAISS) | Same ingestion paths as assets; RAG stack via services |
| **QueryLogPort** | `src.domain.ports.query_log_port` | `QueryLogService` | `AskQuestionUseCase`, `ListRetrievalQueryLogsUseCase` (evaluation module), `PipelineQueryLogEmitter` |
| **QueryLogPersistencePort** | `src.domain.shared.query_log_port` | `SQLiteQueryLogRepository` | Injected into `QueryLogService`; file-based legacy reader |
| **QADatasetEntriesPort** | `src.domain.ports.qa_dataset_entries_port` | `QADatasetService` | Gold QA CRUD/generate use cases |
| **QADatasetRepositoryPort** | `src.domain.evaluation.qa_dataset_repository_port` | `QADatasetRepository` | `QADatasetService` internally |
| **ProjectSettingsRepositoryPort** | `src.domain.shared.project_settings_repository_port` | `ProjectSettingsService` | `RAGCraftApp.project_settings_repository`, `GetProjectRetrievalPresetLabelUseCase`, `GetEffectiveRetrievalSettingsUseCase`, `UpdateProjectRetrievalSettingsUseCase` |

## Wiring

- **Composition:** `BackendComposition` still constructs concrete services; `BackendApplicationContainer` passes those instances into use cases where a port type is declared (structural typing).
- **Behavior:** Unchanged; services retain error translation (e.g. `DocStoreError`) and validation (e.g. QA dataset normalization).

## Layering note

- **QueryLogPort** is the application-facing contract (`log_query`, `load_logs`).
- **QueryLogPersistencePort** is the lower-level repository used inside `QueryLogService`.

## Follow-ups

- RAG / pipeline assembly services still depend directly on docstore and vectorstore types; a later pass can thread **AssetRepositoryPort** / **VectorStorePort** through `PipelineAssemblyService` and `SummaryRecallService`.
- Replace remaining `QueryLogService` mentions in docstrings with **QueryLogPort** where describing contracts.
