# Testing strategy

The suite is organized as a **pyramid**: fast **architecture** import guards at the base, **unit** use-case and domain tests, **HTTP/API** tests with dependency overrides, then heavier **integration** / optional-dependency flows.

**CI lock-in:** GitHub Actions runs **`ruff check src apps tests/architecture`** and **`pytest tests/architecture`** (with **`PYTHONPATH=.`**). Locally use **`scripts/validate.sh`** or **`scripts/validate.ps1`** for the same subset. **`pyproject.toml`** sets **`[tool.pytest.ini_options]`** **`pythonpath = ["."]`** so pytest discovers **`src`** / **`apps`** from the repo root.

## Architecture tests (`tests/architecture/`)

| Area | Examples |
|------|-----------|
| **Layer imports** | `test_layer_boundaries.py` — domain / application / infrastructure / composition / routers |
| **Orchestration folders** | `test_orchestration_package_import_boundaries.py` — `use_cases/chat/orchestration`, `use_cases/evaluation`, and `application/rag` must not import `src.infrastructure`, FastAPI, Streamlit, LangChain, FAISS, … |
| **Application purity** | `test_application_orchestration_purity.py` — no FastAPI/Starlette/Streamlit/FAISS/LangChain in `src/application` (keeps multipart **`UploadFile`** and HTTP types out of use cases); use cases must not import `src.frontend_gateway` |
| **Legacy packages** | `test_deprecated_backend_and_gateway_guardrails.py` — no `src.backend`, `src.adapters`, `src.infrastructure.services` |
| **Gateway** | Same module — `src/frontend_gateway` must not import `src.infrastructure` |
| **FastAPI** | `test_fastapi_migration_guardrails.py` — no Streamlit/UI/infra adapters in `apps/api` source |
| **Composition** | `test_composition_import_boundaries.py` — no `src.frontend_gateway` imports in `src/composition/*.py` |
| **Orchestration** | `test_orchestration_boundaries.py` — transport must not import `src.infrastructure.adapters.rag`; post-recall adapter rules; assemble pipeline + steps module location |
| **RAG façade** | `test_no_rag_service_facade.py` — no `rag_service.py`, no `RAGService` class, container exposes `chat_rag_use_cases`, rag adapters don’t import chat use case types |
| **Adapters → no application imports** | `test_adapter_application_imports.py` — all of `src/infrastructure/adapters/**/*.py` must not import `src.application` |
| **Chat RAG port wiring** | `test_application_chat_rag_boundary_ports.py` — inspect / answer-generation boundaries stay on domain ports |
| **UI surface** | `test_streamlit_import_guardrails.py` — pages/ui import rules |
| **Regression flows** | `test_migration_regression_flows.py` — smoke imports for `build_backend` |
| **Manual eval orchestration** | `test_manual_evaluation_single_orchestrator.py` — no duplicate **`ManualEvaluationService`**-style orchestration in infrastructure |

Shared helper: **`tests/architecture/import_scanner.py`**. Index: **`tests/architecture/README.md`**.

## Integration and API tests

- **`tests/apps_api/`** — FastAPI contracts, dependency overrides, OpenAPI.
- **`tests/integration/`** — heavier flows (optional deps); may skip in minimal envs.
- **`tests/composition/`** — `build_backend_composition` / container wiring (may skip without unstructured/langchain).

## Service / use case unit tests

- **`tests/application/`** — use case behavior with mocks (e.g. **`test_ask_question_use_case.py`**, **`test_inspect_rag_pipeline_use_case.py`**, **`test_benchmark_execution_use_case.py`**, **`test_upload_policy.py`**, **`test_ingest_uploaded_file_use_case.py`**, **`test_get_project_document_details_use_case.py`**, **`test_generate_qa_dataset_use_case.py`**).
- **`tests/apps_api/test_upload_adapter.py`** — Starlette/FastAPI chunked reads for **document** and **avatar** adapters; oversize rejection.
- **`tests/application/users/test_avatar_upload_policy.py`** — application-layer avatar size/emptiness checks.
- **Config monkeypatching:** modules bind **`USER_PROFILE_UPLOAD_CONFIG`** at import time; tests that override avatar limits should patch **`apps.api.upload_adapter`**, **`src.application.users.avatar_upload_policy`**, or **`src.infrastructure.adapters.filesystem.file_avatar_storage`** as appropriate (not only **`src.core.config`**).
- **`tests/domain/`** — pure domain policy (e.g. `test_summary_document_fusion.py`, `test_rag_inspect_answer_run.py` covers **`GoldQaPipelineRowInput`** via **`as_row_evaluation_input()`**, `test_retrieval_settings_override_spec.py`).
- **`tests/application/use_cases/evaluation/test_rag_pipeline_orchestration.py`** — evaluation inspect+answer orchestration and **`RagInspectAnswerRun`** latency typing.
- **`tests/infrastructure_services/`** — adapter behavior (e.g. `test_chat_rag_wiring.py` asserts **`PipelineBuildResult.latency`** and **`RAGResponse.latency`** are **`PipelineLatency`**; **`test_manual_evaluation_service.py`** exercises **`RunManualEvaluationUseCase`** with mocked inspect/generate/benchmark, not a legacy service orchestrator).

## What architecture tests do *not* prove

- Full absence of logical coupling.
- Runtime security of **JWT bearer** verification (`AuthenticationPort` / `JwtAuthenticationAdapter`) and **`RAGCRAFT_JWT_SECRET`** configuration in real deployments.

Run full suite (from repo root, `PYTHONPATH` set):

```bash
pytest tests/ -q
```

**Lint (recommended on touched trees):** `ruff check src apps` and `ruff format src apps` (see `pyproject.toml`).
