# Testing strategy

The suite is organized as a **pyramid**: fast **architecture** import and layout guards at the base, **unit** use-case and domain tests, **HTTP/API** tests with dependency overrides, then heavier **integration** / optional-dependency flows.

**CI lock-in:** `.github/workflows/ci.yml` sets **`PYTHONPATH=api/src:frontend/src:api/tests`**, runs **Ruff** on **`api/src`**, **`frontend/src`**, and **`api/tests/architecture`**, then **`pytest api/tests/architecture`**. Locally use **`scripts/validate.sh`**, **`scripts/validate_architecture.sh`**, or **`scripts/validate.ps1`** where available. **`pyproject.toml`** sets **`[tool.pytest.ini_options]`** **`pythonpath = ["api/tests", "api/src", "frontend/src"]`** so pytest resolves first-party packages from the repo root.

## Architecture tests (`api/tests/architecture/`)

| Area | Examples |
|------|-----------|
| **Physical layout** | `test_repository_structure.py` — required roots, forbidden legacy `src/` / `apps/` at repo root, FastAPI routers only under `interfaces/http/routers/`, schemas under `schemas/`, composition/orchestration trees |
| **Layer imports** | `test_layer_import_rules.py` — domain, application, HTTP routers (AST top-level imports) |
| **Infra + composition** | `test_layer_boundaries.py` — infrastructure vs application/Streamlit; composition vs Streamlit |
| **FastAPI delivery** | `test_fastapi_delivery_boundaries.py` — no Streamlit or legacy `src.*` / `apps.*` namespaces under `interfaces/http` |
| **Frontend thin UI** | `test_frontend_structure.py` — pages/components vs `services` gateway import policy |
| **Orchestration folders** | `test_orchestration_package_import_boundaries.py` — `use_cases/chat/orchestration`, `use_cases/evaluation`, and `application/rag` must not import `infrastructure`, FastAPI, Streamlit, LangChain, FAISS, … |
| **Application purity** | `test_application_orchestration_purity.py` — no FastAPI/Starlette/Streamlit/FAISS/LangChain in `application` |
| **Legacy packages** | `test_deprecated_backend_and_gateway_guardrails.py` — no `src.backend`, `src.adapters`, `infrastructure.services` |
| **FastAPI migration** | `test_fastapi_migration_guardrails.py` — HTTP stack + Streamlit surface regression checks |
| **Composition** | `test_composition_import_boundaries.py` — no `frontend_gateway` imports in `composition/*.py` |
| **Orchestration** | `test_orchestration_boundaries.py` — transport must not import `infrastructure.rag`; post-recall adapter rules |
| **RAG façade** | `test_no_rag_service_facade.py` — no `rag_service.py`, no `RAGService` class |
| **Adapters → no application imports** | `test_adapter_application_imports.py` — infrastructure adapter modules must not import `application` |
| **Chat RAG port wiring** | `test_application_chat_rag_boundary_ports.py` |
| **Regression flows** | `test_migration_regression_flows.py` — smoke imports for `build_backend` |
| **Manual eval orchestration** | `test_manual_evaluation_single_orchestrator.py` |

Shared helper: **`api/tests/architecture/import_scanner.py`**. Index: **`api/tests/architecture/README.md`** (if present).

## Integration and API tests

- **`api/tests/apps_api/`** — FastAPI contracts, dependency overrides, OpenAPI.
- **`api/tests/application_tests/_unclassified_tests/integration/`** — heavier flows (optional deps).
- **`api/tests/composition/`** — `build_backend_composition` / container wiring (may skip without unstructured/langchain).

## Service / use case unit tests

- **`api/tests/application_tests/`** — use case behavior with mocks.
- **`api/tests/domain/`** — pure domain policy.
- **`api/tests/infrastructure_tests/`** — adapter behavior.
- **`frontend/tests/`** — Streamlit/UI and gateway client tests.

## What architecture tests do *not* prove

- Full absence of logical coupling.
- Runtime security of **JWT bearer** verification and secret configuration in real deployments.

Run full suite (from repo root; `pyproject` supplies `pythonpath`):

```bash
pytest api/tests frontend/tests -q
```

**Lint (recommended on touched trees):** `ruff check api/src frontend/src` (see `pyproject.toml`).
