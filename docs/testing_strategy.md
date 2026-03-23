# Testing strategy

Tests are layered: **fast architecture and layout guards** at the base, then **unit** tests (domain, use cases, infrastructure), **HTTP/API** tests, **composition** smoke tests, and optional **integration** flows.

---

## Commands (repository root)

These match **CI** (see **`.github/workflows/ci.yml`**) and the **`scripts/`** entrypoints.

| What | Bash | PowerShell |
|------|------|------------|
| Architecture tests only | `./scripts/validate_architecture.sh` | `.\scripts\validate_architecture.ps1` |
| Lint + architecture | `./scripts/validate.sh` | `.\scripts\validate.ps1` |
| Full workflow (architecture, then rest) | `./scripts/run_tests.sh` | `.\scripts\run_tests.ps1` |
| Lint only | `./scripts/lint.sh` | `.\scripts\lint.ps1` |

**`PYTHONPATH`:** **`api/src:frontend/src:api/tests`** (order matters: **`api/src`** first so test packages do not shadow application code).

**Architecture package:** everything under **`api/tests/architecture/`** — the primary structural gate. Optional pytest marker **`architecture`** exists in root **`pyproject.toml`**; day-to-day, use the path or **`validate_architecture`**.

**From `api/`:** **`api/pyproject.toml`** limits pytest to **`tests/architecture`** so **`cd api && pytest`** matches the architecture script without scanning the whole repo.

**One-shot pytest (may duplicate architecture if run alone):**

```bash
export PYTHONPATH=api/src:frontend/src:api/tests
python -m pytest api/tests frontend/tests -q
```

Prefer **`run_tests.sh`** for the ordered workflow (architecture once, then **`api/tests`** minus architecture + **`frontend/tests`**).

**Typing (optional):** not in **`lint.sh`**. Example:

```bash
set PYTHONPATH=api/src
mypy --config-file=pyproject.toml -p domain
```

---

## Architecture tests (`api/tests/architecture/`)

| Area | Role |
|------|------|
| **`test_repository_structure.py`** | Required roots, forbidden duplicate roots, **Python only** under **`api/src`** / **`frontend/src`** (plus documented entrypoints and test trees), router/schema placement |
| **`test_required_tree.py`** | Positive checks: anchor directories and files must exist |
| **`test_layer_import_rules.py`** | Domain, application, HTTP router import directions |
| **`test_layer_boundaries.py`** | Infrastructure vs application/Streamlit; composition vs Streamlit |
| **`test_fastapi_delivery_boundaries.py`** | **`interfaces/http`** — no Streamlit; no frontend package names or forbidden monolith import roots |
| **`test_fastapi_migration_guardrails.py`** | HTTP vs infra graph imports; **`BackendClient`** alignment checks |
| **`test_frontend_structure.py`** | Pages/components stay thin |
| **`test_orchestration_package_import_boundaries.py`** | Orchestration + **`application/rag`** avoid **`infrastructure`** and frameworks |
| **`test_orchestration_boundaries.py`** | Transport layers must not import **`infrastructure.rag`**; composition **`execute`** usage; adapter size ratchets |
| **`test_application_orchestration_purity.py`** | Application avoids FastAPI, Streamlit, FAISS, LangChain, etc.; use cases avoid **`services`** |
| **`test_deprecated_backend_and_gateway_guardrails.py`** | Forbidden directories under **`api/src`**, forbidden monolith **`import`** patterns, **`frontend/src/services`** infra limits |
| **`test_composition_import_boundaries.py`** | Composition must not import frontend **`services`** |
| **`test_adapter_application_imports.py`** | **`api/src/infrastructure`** must not import **`application`** (narrow exception documented) |
| **`test_no_rag_service_facade.py`** | No **`RAGService`** / **`rag_service.py`** façade |
| **`test_manual_evaluation_single_orchestrator.py`** | Single manual-eval orchestration path |
| **`test_application_chat_rag_boundary_ports.py`** | Chat RAG port wiring |
| **`test_migration_regression_flows.py`** | Smoke **`build_backend`** |
| Others | See **`api/tests/architecture/README.md`** |

Shared helper: **`import_scanner.py`**.

---

## Other backend tests

| Location | Role |
|----------|------|
| **`api/tests/api/`** | FastAPI routes, OpenAPI, **`dependencies`** overrides — import as package **`api`** with **`api/tests`** on **`PYTHONPATH`** |
| **`api/tests/appli/`** | Use-case behavior, mocks |
| **`api/tests/domain/`** | Domain policy |
| **`api/tests/infra/`** | Infrastructure services and adapters |
| **`api/tests/composition/`** | Wiring smoke (may skip without optional deps) |
| **`api/tests/e2e/`** | Heavier or environment-sensitive checks |

---

## Frontend tests

| Location | Role |
|----------|------|
| **`frontend/tests/streamlit/`** | **`frontend/src/services`**, HTTP vs in-process client, Streamlit wiring |
| **`frontend/tests/ui/`** | Streamlit/UI components where present |

---

## What architecture tests do not prove

- Absence of all logical coupling  
- Production security of JWT verification or secret handling  

---

## Lint paths

Match **`scripts/lint.sh`:**

`ruff check api/src frontend/src api/tests/architecture`
