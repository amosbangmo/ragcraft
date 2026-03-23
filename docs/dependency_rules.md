# Dependency rules

Import directions enforced in code and by **`tests/architecture/`** (AST scans). When in doubt, run **`./scripts/validate.sh`** (or **`pytest tests/architecture -q`** with **`PYTHONPATH=.`**).

## Allowed directions

| From | May import |
|------|------------|
| **Domain** | `src.core` (as established), stdlib, third-party **without** pulling app/infra (see tests for forbidden list). RAG-related typed transport for retrieval overrides lives in **`src/domain/retrieval_settings_override_spec.py`** so **`RetrievalPort`** and related protocols stay dict-free at the orchestration boundary. **`BufferedDocumentUpload`** and **`ProposedQaDatasetRow`** keep ingest and QA-generation ports off anonymous dict payloads at those boundaries. |
| **Application** | `src.domain`, `src.core`; **`frontend_support`** may use `src.frontend_gateway` for stubs only |
| **Infrastructure (non-adapter)** | Technical deps; **not** `src.application` (see `test_layer_boundaries`) |
| **Infrastructure adapters** | **Domain** always; **not** **`src.application`** (see **`test_adapter_application_imports.py`**) |
| **Composition** | Domain ports, infrastructure adapters, application use cases for typing/wiring; **not** `src.frontend_gateway` |
| **`apps/api`** | FastAPI, `src.composition`, `src.application` (DTOs, **`frontend_support`** transcript), **`src.domain`** (**`AuthenticatedPrincipal`**, **`AuthenticationPort`** / **`AccessTokenIssuerPort`** types for dependencies), **not** `streamlit`, **`src.ui`**, or **`src.infrastructure.*`** anywhere in the package (AST guard in **`test_fastapi_migration_guardrails`**) |
| **`src/frontend_gateway`** | `src.composition`, `src.application` (DTOs/support), **not** `src.infrastructure` |
| **`pages/`, `src/ui/`** | `streamlit`, `src.frontend_gateway`, `src.auth`, view models; **not** `src.domain`, `src.infrastructure`, `src.composition`, `apps.api` |

### Infrastructure adapters (`src/infrastructure/adapters/`)

- Must **not** import **`src.application`** (enforced by **`tests/architecture/test_adapter_application_imports.py`**). Retrieval tuning is **`RetrievalSettingsTuner`** in **`src/application/settings/`**, wired from **`src/composition/backend_composition.py`** — not via an infra subclass.
- RAG adapters must **not** import chat **use case classes** from `src.application.use_cases.chat` (see **`test_no_rag_service_facade.py`**).

### Shared boundary types (query log, evaluation rows)

- **`QueryLogIngressPayload`** lives in **`src/domain/query_log_ingress_payload.py`** so query logging adapters accept the same typed shape the application builds without importing application modules.
- **`EvaluationJudgeMetricsRow`** lives in **`src/domain/evaluation/judge_metrics_row.py`** for benchmark row judge slices.
- **`GoldQaPipelineRowInput`** (`src/domain/evaluation/gold_qa_row_input.py`) is the typed input to **`BenchmarkRowProcessingPort.process_row`** / **`RowEvaluationService.process_row`** (replacing an ad hoc ``dict`` runner payload).
- **`ManualEvaluationFromRagPort.build_manual_evaluation_result`** takes **`full_latency: PipelineLatency | None`**; **`ManualEvaluationPipelineSignals.stage_latency`** is the same type (JSON round-trip via **`manual_evaluation_result_from_plain_dict`** maps ``stage_latency`` dict → **`PipelineLatency`**).
- **Manual evaluation orchestration** is **`RunManualEvaluationUseCase`** only (plus shared **`execute_rag_inspect_then_answer_for_evaluation`**). Do not add a parallel “evaluate question” orchestrator in infrastructure; **`src/infrastructure/adapters/evaluation/manual_evaluation_service.py`** is for **row/result assembly**, not inspect+answer sequencing.
- Gold-QA benchmark **orchestration** (**`BenchmarkExecutionUseCase`**) is wired in **`src/composition/evaluation_wiring.py`**; **`GoldQaBenchmarkAdapter`** (application) implements **`GoldQaBenchmarkPort`** for **`EvaluationService`**.

## Anti-patterns

1. **Routers instantiating** `VectorStoreService`, `EvaluationService`, or other infra services — use **`Depends`** → container → use case.
2. **Application importing** `src.infrastructure` — wire in **`src/composition`**.
3. **Composition importing** `src.frontend_gateway` — use **`ChatTranscriptPort`** and pass **`StreamlitChatTranscript`** only from **`streamlit_backend_factory`**.
4. **Gateway importing** `src.infrastructure` — use **`application.frontend_support`** stubs for HTTP mode.
5. **Reintroducing** `src/backend`, `src/adapters`, `src/infrastructure/services` — removed; tests fail if directories or imports return.
6. **New `rag_service.py`** orchestration façade under infrastructure that constructs chat use cases — forbidden; see **`tests/architecture/test_no_rag_service_facade.py`**.

## `MemoryChatTranscript` (canonical)

- **`src/application/frontend_support/memory_chat_transcript.py`** — in-process **`ChatTranscriptPort`** used by **`apps/api/dependencies.py`**, tests, and any **`build_backend_composition(chat_transcript=...)`** caller. There is **no** duplicate under **`src/infrastructure/adapters`**.

## Enforcement map (concrete tests)

| Rule | Primary test module |
|------|---------------------|
| Domain / application / infra layer directions | **`test_layer_boundaries.py`** |
| No FastAPI/LC/FAISS in `src/application` | **`test_application_orchestration_purity.py`** |
| Chat orchestration + evaluation + `application/rag` no infra / frameworks | **`test_orchestration_package_import_boundaries.py`** |
| `apps/api` no `src.infrastructure.adapters` | **`test_fastapi_migration_guardrails.py`** |
| Adapters must not import application | **`test_adapter_application_imports.py`** |
| Manual eval single orchestrator | **`test_manual_evaluation_single_orchestrator.py`** |
| No RAG monolith façade | **`test_no_rag_service_facade.py`** |
| RAG post-recall / router rag imports | **`test_orchestration_boundaries.py`** |

## Lint and format

**Ruff** / **Black** / **mypy** settings: **`pyproject.toml`**. Ruff complements AST tests by catching issues such as **undefined names** in modules that still type-check at runtime under lazy evaluation.
