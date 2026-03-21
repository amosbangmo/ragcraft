# Architecture boundary tests

Pytest module `test_layer_boundaries.py` scans **import statements** (via the AST) and fails if a layer pulls in a forbidden package prefix.

## Rules enforced

| Layer | Location | Must not import (prefix match) |
|--------|-----------|----------------------------------|
| **Domain** | `src/domain/` | `src.infrastructure`, `src.services`, `src.application`, `streamlit`, `apps` |
| **Application** | `src/application/` | `streamlit`, `apps`, `src.infrastructure` |
| **Infrastructure** | `src/infrastructure/` | `src.application`, `streamlit`, `apps` |
| **API routers** | `apps/api/routers/` | `src.infrastructure` |
| **Composition root** | `src/composition/` | `streamlit`, `apps` |

## Intentional exceptions / non-goals

- **Domain** may import **`src.core`** (paths, config, shared exceptions) and third-party libraries (e.g. `langchain_core`).
- **Application** may import **`src.services`** and **`src.domain`**; orchestration still lives here until more ports exist.
- **Routers** may import **`src.services`** only for type hints / thin `Depends` wiring (e.g. `ProjectService`). Direct **`src.infrastructure`** imports are forbidden so persistence and adapters stay behind use cases and the composition root.
- These checks are **import-level** only: they do not prove absence of logical coupling.

## Running

```bash
pytest tests/architecture -q
```
