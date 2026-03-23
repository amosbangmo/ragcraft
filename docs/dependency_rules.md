# Dependency rules

Import directions enforced in code and by **`api/tests/architecture/`** (AST scans).

**Validate from repo root (exact commands):**

| Intent | Command |
|--------|---------|
| Architecture tests only | **`./scripts/validate_architecture.sh`** or **`.\scripts\validate_architecture.ps1`** |
| Ruff + architecture (CI-style) | **`./scripts/validate.sh`** or **`.\scripts\validate.ps1`** |
| Full pytest (architecture first, then rest) | **`./scripts/run_tests.sh`** or **`.\scripts\run_tests.ps1`** |

Scripts set **`PYTHONPATH=api/src:frontend/src:api/tests`**. See **`docs/testing_strategy.md`** and **`docs/README.md`**.

**Required skeleton:** **`test_required_tree.py`** asserts that canonical directories (e.g. `api/src/domain/`, `frontend/src/pages/`, `api/tests/application_tests/`) and **anchor files** (composition wiring modules, core routers/schemas, `frontend/app.py`, key docs/scripts) still exist. It does not list every future module—only the architectural spine—so legitimate feature growth stays unblocked.

## Allowed directions

| From | May import |
|------|------------|
| **Domain** | `domain`, stdlib, third-party **without** transport or concrete infrastructure. **Narrow exception:** imports under **`infrastructure.config`** only (paths/constants), enforced explicitly in **`test_layer_import_rules.py`**. |
| **Application** | `domain`, **`application` DTOs/ports**; **not** FastAPI/Starlette/Streamlit/`interfaces`. **Narrow exception:** **`infrastructure.config`** only for shared config/exceptions (same test module). |
| **Infrastructure (non-adapter)** | Technical deps; **not** `application` (except Streamlit shims whitelisted in **`test_layer_boundaries`**) |
| **Infrastructure adapters** | **Domain** always; **not** **`application`** (see **`test_adapter_application_imports.py`**) |
| **Composition** | Domain ports, infrastructure, application use cases for typing/wiring; **not** Streamlit |
| **`interfaces/http`** | FastAPI, `composition`, `application`, `domain` types as needed; **not** `streamlit`. Routers must not import **`infrastructure.*`** at all (even config); other HTTP modules may use **`infrastructure.config`** for errors/settings. |
| **`frontend/src/services`** | May import `domain`, `application`, `composition`, and **`infrastructure.config`** (and related auth helpers) for the in-process/HTTP gateway; see **`test_frontend_structure.py`** for **pages/components** (thinner rules). |
| **`frontend/src/pages`, `components`** | **Not** `domain`, `application`, `composition`, or `interfaces`; **infrastructure** limited to **`infrastructure.auth.*`** (session guards). |

### Infrastructure adapters (`src/infrastructure/adapters/`)

- Must **not** import **`src.application`** (enforced by **`tests/architecture/test_adapter_application_imports.py`**). Retrieval tuning is **`RetrievalSettingsTuner`** in **`src/application/settings/`**, wired from **`src/composition/backend_composition.py`** — not via an infra subclass.
- RAG adapters must **not** import chat **use case classes** from `application.use_cases.chat` (see **`test_no_rag_service_facade.py`**).

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
| Physical layout (roots, FastAPI file locations, forbidden trees) | **`test_repository_structure.py`** |
| Required directories + anchor files (positive skeleton) | **`test_required_tree.py`** |
| Domain / application / HTTP router import directions | **`test_layer_import_rules.py`** |
| Infrastructure + composition Streamlit rules | **`test_layer_boundaries.py`** |
| `interfaces/http` no Streamlit / legacy namespaces | **`test_fastapi_delivery_boundaries.py`**, **`test_fastapi_migration_guardrails.py`** |
| Frontend pages/components import thinness | **`test_frontend_structure.py`** |
| No FastAPI/LC/FAISS in `application` | **`test_application_orchestration_purity.py`** |
| Chat orchestration + evaluation + `application/rag` no infra / frameworks | **`test_orchestration_package_import_boundaries.py`** |
| Adapters must not import application | **`test_adapter_application_imports.py`** |
| Manual eval single orchestrator | **`test_manual_evaluation_single_orchestrator.py`** |
| No RAG monolith façade | **`test_no_rag_service_facade.py`** |
| RAG post-recall / router rag imports | **`test_orchestration_boundaries.py`** |

## Lint and format

**Ruff** / **Black** / **mypy** settings: **`pyproject.toml`**. Ruff complements AST tests by catching issues such as **undefined names** in modules that still type-check at runtime under lazy evaluation.
