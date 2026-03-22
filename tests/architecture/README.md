# Architecture boundary tests

Pytest modules under this package scan **import statements** (via the AST) and fail if a layer pulls in a forbidden package prefix. Shared helper: `collect_import_violations` in `import_scanner.py`. The **intended runtime layout** is documented in **`ARCHITECTURE_TARGET.md`** at the repo root.

## Rules enforced

| Layer | Location | Must not import (prefix match) |
|--------|-----------|----------------------------------|
| **Domain** | `src/domain/` | `src.infrastructure`, `src.backend`, `src.services`, `src.application`, `streamlit`, `apps` |
| **Application** | `src/application/` | `streamlit`, `apps`, `src.infrastructure` except the **`src.infrastructure.services`** subtree |
| **Infrastructure** | `src/infrastructure/` | **`src.application`**, `streamlit`, `apps` — **except** `src/infrastructure/services/`, which may import `src.application` and `streamlit` (runtime graph moved from deprecated `src.backend`) |
| **API routers** | `apps/api/routers/` | `src.infrastructure` |
| **Composition root** | `src/composition/` | `streamlit`, `apps` |
| **FastAPI package** | `apps/api/` (all modules) | `streamlit`, `src.ui`, **`src.backend`**, **`src.services`**, **`src.infrastructure.services`** |
| **Streamlit surface** | `pages/`, `src/ui/` | `src.backend`, `src.infrastructure.services`, `src.services`, `src.composition`, `src.infrastructure`, `src.app`, `apps.api`, `apps` |

Module `test_fastapi_migration_guardrails.py` adds the last two rows plus **behavioral** checks that `HttpBackendClient` and `InProcessBackendClient` stay aligned and that the HTTP client satisfies `BackendClient` at runtime (`isinstance`).

## Intentional exceptions / non-goals

- **Domain** may import **`src.core`** (paths, config, shared exceptions) and third-party libraries (e.g. `langchain_core`).
- **Application** may import **`src.infrastructure.services`** (canonical runtime services) and **`src.domain`**.
- **Routers** wire use cases via **`Depends`** and must not import **`src.backend`**, **`src.infrastructure.services`**, or other **`src.infrastructure`** modules directly.
- **Streamlit pages and widgets** may import **`streamlit`**, **`src.domain`** (display/DTO types), **`src.frontend_gateway`**, and **`src.auth`**; they must not wire **`src.backend`**, **`src.infrastructure.services`**, **`src.services`**, or the composition/app entrypoints directly.
- We do **not** assert a clean `sys.modules` after `import apps.api.main`: third-party transitive imports can load unrelated packages; the **AST scan** of `apps/api` is the stable guard for “API code does not reference Streamlit”.
- These checks are **import-level** only: they do not prove absence of logical coupling.

## Running

```bash
pytest tests/architecture -q
```
