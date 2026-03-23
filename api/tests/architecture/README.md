# Architecture boundary tests

Pytest modules under this package scan **import statements** (via the AST) and fail if a layer pulls in a forbidden package prefix. Shared helper: `collect_import_violations` in `import_scanner.py`. The **intended runtime layout** is documented in **`ARCHITECTURE_TARGET.md`** (repo root), **`docs/architecture.md`**, and **`docs/dependency_rules.md`**.

## Rules enforced

| Layer | Location | Must not import (prefix match) |
|--------|-----------|----------------------------------|
| **Domain** | `src/domain/` | `src.infrastructure`, `src.backend`, `src.services`, `src.application`, `src.ui`, `streamlit`, `fastapi`, `starlette`, `sqlite3`, any `langchain*`, `apps` |
| **Application** | `src/application/` | `streamlit`, `apps`, **`src.adapters`** (removed), **any** `src.infrastructure` (including adapters — wire in composition only). Use cases must not import `src.frontend_gateway` (see `test_application_orchestration_purity`) |
| **Orchestration subtrees** | `src/application/use_cases/chat/orchestration/`, `…/evaluation/`, `src/application/rag/` | `src.infrastructure`, `fastapi`, `starlette`, `streamlit`, `uvicorn`, `langchain*`, `langgraph`, `faiss`, `sqlite3` — see **`test_orchestration_package_import_boundaries.py`** |
| **Infrastructure** | `src/infrastructure/` | **`src.application`**, `streamlit`, `apps` — adapters additionally scanned by **`test_adapter_application_imports.py`** (no `src.application` imports) |
| **API routers** | `apps/api/routers/` | `src.infrastructure` |
| **Composition root** | `src/composition/` | `streamlit`, `apps` |
| **FastAPI package** | `apps/api/` (all modules) | `streamlit`, `src.ui`, **`src.services`**, **`infrastructure.adapters`**, **`src.backend`**, **`src.adapters`** |
| **Streamlit surface** | `pages/`, `src/ui/` | `src.backend`, `src.adapters`, `src.domain`, `src.services`, `src.composition`, `src.infrastructure`, `src.app`, `apps.api`, `apps` |

Module `test_fastapi_migration_guardrails.py` adds the last two rows plus **behavioral** checks that `HttpBackendClient` and `InProcessBackendClient` stay aligned and that the HTTP client satisfies `BackendClient` at runtime (`isinstance`).

## Intentional exceptions / non-goals

- **Domain** may import **`src.core`** (paths, config, shared exceptions). Summary-level retrieval uses **`SummaryRecallDocument`** in-domain — not LangChain `Document`.
- **Application** may import **`src.domain`** and **`src.core`**; it must not import **`src.infrastructure`** (implementations are composed in ``src/composition``). **Use cases** must not import **`src.frontend_gateway`**; **`application.frontend_support`** may import the gateway for HTTP-mode stubs.
- **Routers** wire use cases via **`Depends`** and must not import **`infrastructure.adapters`** or other **`src.infrastructure`** modules directly (and must not reference the removed **`src.backend`** package).
- **Streamlit pages and widgets** may import **`streamlit`**, **`src.frontend_gateway`** (including **`view_models`** for display types), and **`src.auth`**; they must not import **`src.domain`** directly, nor **`src.backend`**, **`src.infrastructure`**, **`src.services`**, or the composition/app entrypoints.
- **`src.frontend_gateway`** must not import **`src.infrastructure`**. HTTP-mode placeholders live in **`application.frontend_support`** (they may import **`src.frontend_gateway`** and application helpers such as **`retrieval_settings_tuner`** — not infrastructure).
- **Codebase Python** (`src/`, `apps/`, `pages/`, `tests/`, `streamlit_app.py`) must not import **`src.backend`**; the **`src/backend/`** directory must not exist (`test_codebase_python_does_not_import_removed_backend_package` and `test_legacy_backend_package_directory_is_absent`).
- **`src/infrastructure/services/`** must not exist, and nothing may import **`infrastructure.services`** (`test_legacy_infrastructure_services_package_directory_is_absent`, `test_codebase_python_does_not_import_removed_infrastructure_services_package`).
- **`src/adapters/`** must not exist; use **`src/infrastructure/adapters`** (see guardrails in `test_deprecated_backend_and_gateway_guardrails.py`).
- We do **not** assert a clean `sys.modules` after `import interfaces.http.main`: third-party transitive imports can load unrelated packages; the **AST scan** of `apps/api` is the stable guard for “API code does not reference Streamlit”.
- These checks are **import-level** only: they do not prove absence of logical coupling.

## Running

From repo root with **`PYTHONPATH=.`**:

```bash
./scripts/validate.sh
# or:
pytest tests/architecture -q
```

**Windows:** **`.\scripts\validate.ps1`**. Same steps run in **`.github/workflows/ci.yml`**.
