# Testing strategy

The suite is organized as a **pyramid**: fast **architecture** import and layout guards at the base, **unit** use-case and domain tests, **HTTP/API** tests with dependency overrides, then heavier **integration** / optional-dependency flows.

## Commands (repo root)

Use these for **local** work and as the **reference for CI** (see **`.github/workflows/ci.yml`**).

| What | Bash | PowerShell |
|------|------|------------|
| **Architecture validation only** (blocking layout + imports + required tree) | `./scripts/validate_architecture.sh` | `.\scripts\validate_architecture.ps1` |
| **Lint (Ruff) + architecture tests** | `./scripts/validate.sh` | `.\scripts\validate.ps1` |
| **Full pytest workflow** (architecture first, then rest of `api/tests` + `frontend/tests`) | `./scripts/run_tests.sh` | `.\scripts\run_tests.ps1` |
| **Lint only** | `./scripts/lint.sh` | `.\scripts\lint.ps1` |

**Environment:** scripts set **`PYTHONPATH=api/src:frontend/src:api/tests`** (Linux `:` / Windows `;` inside the respective script). **`api/src` is listed first** so application packages are never shadowed by anything under **`api/tests`**.

**Strict subset:** architecture tests are exactly everything under **`api/tests/architecture/`** — no need for a pytest marker for day-to-day use. Optional marker **`architecture`** exists in root **`pyproject.toml`** for future filtering; the **canonical gate** is the path + **`validate_architecture`**.

**From `api/` only:** **`api/pyproject.toml`** limits pytest to **`tests/architecture`** so `cd api && pytest` matches **`validate_architecture.sh`** without scanning the whole repo.

**Full pytest in one shot (no script):**

```bash
export PYTHONPATH=api/src:frontend/src:api/tests
python -m pytest api/tests frontend/tests -q
```

(Runs architecture tests twice if you already ran **`validate_architecture.sh`**; prefer **`run_tests.sh`** for a single ordered workflow.)

**Typing (optional):** incremental **mypy** is not wired into **`lint.sh`**. Example:

```bash
mypy --config-file=pyproject.toml -p domain
```

(Adjust **`-p`** to the package under **`api/src`**; see **`pyproject.toml`** **`[tool.mypy]`**.)

**CI lock-in:** **`.github/workflows/ci.yml`** runs **`bash scripts/lint.sh`**, **`bash scripts/validate_architecture.sh`**, then **`python -m pytest api/tests --ignore=api/tests/architecture frontend/tests`** (same split as **`run_tests.sh`** step 2), plus existing **unittest** jobs and boot check.

Root **`pyproject.toml`** sets **`[tool.pytest.ini_options]`** **`testpaths`** and **`pythonpath`** when you invoke pytest from the repo root without the scripts.

## Architecture tests (`api/tests/architecture/`)

| Area | Examples |
|------|-----------|
| **Physical layout** | `test_repository_structure.py` — required roots, forbidden legacy `src/` / `apps/` at repo root, FastAPI routers only under `interfaces/http/routers/`, schemas under `schemas/`, composition/orchestration trees |
| **Required skeleton** | `test_required_tree.py` — explicit **must-exist** directories and anchor files (backend composition + HTTP stack, frontend entry/pages/services/state, docs/scripts, test subtrees `appli` / `infra` / `api` / `e2e`) without enumerating every future file |
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

- **`api/tests/api/`** — FastAPI contracts, dependency overrides, OpenAPI (import as ``api`` only with ``api/tests`` on ``PYTHONPATH``, e.g. ``scripts/run_tests.sh``).
- **`api/tests/appli/_unclassified_tests/integration/`** — heavier flows (optional deps).
- **`api/tests/composition/`** — `build_backend_composition` / container wiring (may skip without unstructured/langchain).

## Service / use case unit tests

- **`api/tests/appli/`** — use case behavior with mocks.
- **`api/tests/domain/`** — pure domain policy.
- **`api/tests/infra/`** — adapter behavior.
- **`frontend/tests/`** — Streamlit/UI and gateway client tests.

## What architecture tests do *not* prove

- Full absence of logical coupling.
- Runtime security of **JWT bearer** verification and secret configuration in real deployments.

**Lint (paths match `lint.sh`):** `ruff check api/src frontend/src api/tests/architecture` (see **`pyproject.toml`**).
