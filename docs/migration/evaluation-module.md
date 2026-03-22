# Evaluation application module

## Layout (`src/application/evaluation`)

| Area | Location | Role |
|------|-----------|------|
| Commands / queries | `dtos.py` | Frozen dataclasses passed into use cases (`RunManualEvaluationCommand`, `RunGoldQaDatasetEvaluationCommand`, QA dataset CRUD commands, `ListRetrievalQueryLogsQuery`, `GenerateQaDatasetCommand`, `DeleteAllQaDatasetEntriesCommand`, export inputs in `benchmark_export_dtos.py`). |
| Manual eval | `use_cases/run_manual_evaluation.py` | Loads project, runs inspect + answer, delegates scoring to `manual_evaluation_result_from_rag_outputs` + `EvaluationService`. |
| Gold QA benchmark | `use_cases/run_gold_qa_dataset_evaluation.py` | Lists entries, per-row pipeline runner, `EvaluationService.evaluate_gold_qa_dataset`. |
| Row-level benchmark math | `use_cases/benchmark_execution.py` | Invoked from `EvaluationService` (service remains the façade for metric helpers). |
| QA dataset CRUD / generate | `use_cases/create_*`, `list_*`, `update_*`, `delete_*`, `generate_qa_dataset.py`, `delete_all_qa_dataset_entries.py` | Thin ports to `QADatasetService` / generation service. |
| Retrieval logs | `use_cases/list_retrieval_query_logs.py` | `QueryLogPort` read model; container property `evaluation_list_retrieval_query_logs_use_case` (alias `retrieval_analytics_list_query_logs_use_case`). |
| Export artifacts | `use_cases/build_benchmark_export_artifacts.py`, `benchmark_report_formatter.py` | `BuildBenchmarkExportCommand` → `BenchmarkExportArtifacts` (JSON/CSV/Markdown bytes). |

## API-ready (HTTP parity with use cases)

These routes under `/evaluation` call the same container-backed use cases as Streamlit (via `BackendClient` / HTTP parity):

- `POST /evaluation/manual` — manual evaluation (`RunManualEvaluationUseCase`).
- `POST /evaluation/dataset/run` — full gold QA benchmark (`RunGoldQaDatasetEvaluationUseCase`).
- `GET/POST /evaluation/dataset/entries`, `PUT/DELETE …/entries/{id}` — QA CRUD.
- `POST /evaluation/dataset/generate` — LLM QA generation (`GenerateQaDatasetUseCase`).
- `GET /evaluation/retrieval/logs` — query logs (`ListRetrievalQueryLogsUseCase`).
- `POST /evaluation/export/benchmark` — builds exports from a `BenchmarkResult` JSON body (base64 file payloads in the response). `GET` the same path returns discovery metadata.

## Streamlit-only (or UI-layer) today

- **Session-scoped benchmark history and dashboards** — `pages/evaluation.py` and `src/ui/evaluation_*` keep run history, widgets, and download buttons; they call **`BackendClient`** methods that delegate to the same use cases and orchestrate Streamlit `session_state` and layout.
- **Rich tables / plots** — presentation of `BenchmarkResult` and manual-eval results remains in UI modules, not duplicated in the API.
- **Retrieval comparison page** — `pages/retrieval_comparison.py` uses `BackendClient.compare_retrieval_modes` (application use case); not duplicated as a separate evaluation sub-router.

## Services vs application

- `EvaluationService` — infrastructure adapter composing `BenchmarkExecutionUseCase` and metric helpers; application use cases depend on **ports** (`GoldQaBenchmarkPort`, `ManualEvaluationFromRagPort`) satisfied by this service at the composition root.
- `ManualEvaluationService.evaluate_question` — deprecated path for tests; prefer `RunManualEvaluationUseCase`.

## Benchmark payload stability

- Domain aggregate remains `BenchmarkResult` / `BenchmarkRow` / `BenchmarkSummary`; `to_dict` / `from_plain_dict` / `coerce_benchmark_result` are the stable wire shapes for API and session round-trips.
- Export filenames and metadata fields follow `BenchmarkRunMetadata` and the formatter; API export only adds base64 encoding for transport.
