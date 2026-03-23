# Architecture boundary tests

Pytest modules under this package scan **import statements** (via the AST) and fail if a layer pulls in a forbidden package prefix. **Physical layout** is enforced by **`test_repository_structure.py`**; **required anchor files and directories** by **`test_required_tree.py`**; **legacy path strings** in docs and sources by **`test_no_legacy_paths.py`**. Run from repo root: **`./scripts/validate_architecture.sh`** or **`pytest api/tests/architecture -q`** (see **`docs/testing_strategy.md`**). Shared helper: `collect_import_violations` in `import_scanner.py`. The **intended runtime layout** is documented in **`docs/architecture.md`** and **`docs/dependency_rules.md`**.

## Rules enforced

Paths below are **on-disk** under the repository root. Python imports use package names **`domain`**, **`application`**, etc., with **`PYTHONPATH`** including **`api/src`** and **`frontend/src`**.

| Layer | Location | Must not import (prefix match) |
|--------|-----------|----------------------------------|
| **Domain** | `api/src/domain/` | `infrastructure` (except narrow **`infrastructure.config`** per tests), `application`, `streamlit`, `fastapi`, `starlette`, `sqlite3`, any `langchain*`, `interfaces`, `composition` |
| **Application** | `api/src/application/` | `streamlit`, **`interfaces`**, **any** `infrastructure` except **`infrastructure.config`** where allowed. Use cases must not import frontend **`services`** (see `test_application_orchestration_purity`) |
| **Orchestration subtrees** | `api/src/application/orchestration/{rag,evaluation}/`, `application/use_cases/evaluation/`, `api/src/application/rag/` | `infrastructure`, `fastapi`, `starlette`, `streamlit`, `uvicorn`, `langchain*`, `langgraph`, `faiss`, `sqlite3` — see **`test_orchestration_package_import_boundaries.py`** |
| **Infrastructure** | `api/src/infrastructure/` | **`application`**, `streamlit`, `interfaces` — adapters additionally scanned by **`test_adapter_application_imports.py`** (no `application` imports) |
| **API routers** | `api/src/interfaces/http/routers/` | `infrastructure` |
| **Composition root** | `api/src/composition/` | `streamlit`, `interfaces` |
| **FastAPI / HTTP package** | `api/src/interfaces/http/` (all modules) | `streamlit`, top-level frontend packages (`pages`, `components`, …), monolith roots **`src`**, **`apps`**, **`infrastructure.services`**, **`infrastructure.adapters`** |
| **Frontend pages / components** | `frontend/src/pages/`, `frontend/src/components/` | `domain`, `application`, `composition`, `interfaces`; **infrastructure** limited to **`infrastructure.auth.*`** |
| **Frontend services** | `frontend/src/services/` | **`infrastructure.*`** except **`infrastructure.config`** and **`infrastructure.auth`** (`test_frontend_services_infrastructure_imports_are_limited`) |

Module `test_fastapi_migration_guardrails.py` adds **behavioral** checks that `HttpBackendClient` and `InProcessBackendClient` stay aligned and that the HTTP client satisfies `BackendClient` at runtime (`isinstance`).

## Intentional exceptions / non-goals

- **Domain** may import **`infrastructure.config`** and **`core`** (paths, config, shared exceptions) per **`test_layer_import_rules.py`**.
- **Application** may import **`domain`** and **`core`**; it must not import concrete **`infrastructure`** adapters (implementations are composed in **`composition`**). **Use cases** must not import **`services`** from the frontend tree; **`application.frontend_support`** supplies HTTP-mode stubs.
- **Routers** wire use cases via **`Depends`** and must not import **`infrastructure.*`** directly.
- **Streamlit pages and components** use **`services`** and **`streamlit`**; they must not import **`domain`** or **`application`** directly.
- **`frontend/src/services`** must not import **`infrastructure`** beyond **`infrastructure.config`** / **`infrastructure.auth`** (no persistence, RAG, or vector stores).
- **Codebase Python** under **`api/src`**, **`frontend/src`**, tests, and **`frontend/app.py`** must not import monolith **`src.*`** / **`apps.*`** shims or removed package names checked in **`test_deprecated_backend_shim_guardrails.py`**; stray **`api/src/adapters`**, **`api/src/backend`**, **`api/src/services`**, **`api/src/infrastructure/services`** must stay absent.
- **`api/src/infrastructure/services/`** must not exist, and nothing may import **`infrastructure.services`**.
- We do **not** assert a clean `sys.modules` after `import interfaces.http.main`: third-party transitive imports can load unrelated packages; the **AST scan** of **`interfaces/http`** is the stable guard for “HTTP delivery code does not reference Streamlit”.
- These checks are **import-level** only: they do not prove absence of logical coupling.

## Running

From repo root (scripts set **`PYTHONPATH`**):

```bash
./scripts/validate.sh
# or:
pytest api/tests/architecture -q
```

**Windows:** **`.\scripts\validate.ps1`**. Same steps run in **`.github/workflows/ci.yml`**.
