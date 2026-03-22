# Testing strategy

## Architecture tests (`tests/architecture/`)

| Area | Examples |
|------|-----------|
| **Layer imports** | `test_layer_boundaries.py` — domain / application / infrastructure / composition / routers |
| **Application purity** | `test_application_orchestration_purity.py` — no FastAPI/Streamlit/FAISS/LangChain in `src/application`; use cases must not import `src.frontend_gateway` |
| **Legacy packages** | `test_deprecated_backend_and_gateway_guardrails.py` — no `src.backend`, `src.adapters`, `src.infrastructure.services` |
| **Gateway** | Same module — `src/frontend_gateway` must not import `src.infrastructure` |
| **FastAPI** | `test_fastapi_migration_guardrails.py` — no Streamlit/UI/infra adapters in `apps/api` source |
| **Composition** | `test_composition_import_boundaries.py` — no `src.frontend_gateway` imports in `src/composition/*.py` |
| **Orchestration** | `test_orchestration_boundaries.py` — transport must not import `src.infrastructure.adapters.rag`; post-recall adapter rules; assemble pipeline + steps module location |
| **RAG façade** | `test_no_rag_service_facade.py` — no `rag_service.py`, no `RAGService` class, container exposes `chat_rag_use_cases`, rag adapters don’t import chat use case types |
| **RAG adapter layering** | `test_rag_adapter_application_imports.py` — `src/infrastructure/adapters/rag/*.py` must not import `src.application` (except `retrieval_settings_service.py`) |
| **UI surface** | `test_streamlit_import_guardrails.py` — pages/ui import rules |
| **Regression flows** | `test_migration_regression_flows.py` — smoke imports for `build_backend` |

Shared helper: **`tests/architecture/import_scanner.py`**. Index: **`tests/architecture/README.md`**.

## Integration and API tests

- **`tests/apps_api/`** — FastAPI contracts, dependency overrides, OpenAPI.
- **`tests/integration/`** — heavier flows (optional deps); may skip in minimal envs.
- **`tests/composition/`** — `build_backend_composition` / container wiring (may skip without unstructured/langchain).

## Service / use case unit tests

- **`tests/application/`** — use case behavior with mocks.
- **`tests/domain/`** — pure domain policy (e.g. `test_summary_document_fusion.py`, `test_rag_inspect_answer_run.py`).
- **`tests/infrastructure_services/`** — adapter behavior (e.g. `test_chat_rag_wiring.py` for composition-wired RAG subgraph).

## What architecture tests do *not* prove

- Full absence of logical coupling.
- Runtime security of **`X-User-Id`** (trust header model).

Run full suite (from repo root, `PYTHONPATH` set):

```bash
pytest tests/ -q
```
