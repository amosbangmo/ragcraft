# Testing strategy

Tests are layered: **fast architecture and layout guards** at the base, then **unit** tests (domain, use cases, infrastructure), **HTTP/API** tests, **composition** smoke tests, **frontend** client/UI tests, and optional **e2e** flows. The goal is **structural confidence** (layers, contracts, orchestration modes) — not maximizing a coverage percentage alone.

---

## Test matrix (what proves what)

| Layer | Location | Proves |
|-------|----------|--------|
| **Architecture** | **`api/tests/architecture/`** | Repo layout, forbidden imports, router/schema placement, orchestration purity, frontend thinness |
| **Bootstrap** | **`api/tests/bootstrap/`** | **`api/main.py`** wiring, **`create_app()`**, **`/health`**, OpenAPI |
| **API / HTTP** | **`api/tests/api/`** | Route contracts, auth, validation (**422**), **`RAGCraftError`** envelope (**400/401/409/…**), multipart limits, cross-route conventions (e.g. empty **`project_id`** on chat / evaluation) |
| **Application** | **`api/tests/appli/`** | Use cases with fake ports; **`appli/orchestration/test_rag_mode_contracts.py`** — ask vs inspect vs preview vs evaluation and query-log rules |
| **Domain** | **`api/tests/domain/`** | Domain policy |
| **Infrastructure** | **`api/tests/infra/`** | Adapters, SQLite, services |
| **Composition** | **`api/tests/composition/`** | Wiring smoke |
| **E2E / regression** | **`api/tests/e2e/`** | Thresholds and heavier checks (may be environment-sensitive) |
| **Frontend** | **`frontend/tests/streamlit/`**, **`frontend/tests/ui/`** | HTTP client paths, wire JSON parsing, Streamlit helpers |

Together, these give **9/10+** confidence for **regressions in layering, HTTP contracts, RAG mode separation, and the Streamlit↔API boundary**, assuming normal CI runs (**`scripts/run_tests.sh`** / **`.ps1`**). The **feature matrix** in **`docs/product_features.md`** lists which behaviors are backed by which tests and UI paths. They do **not** replace production security review, load testing, or real LLM/vector SLO validation.

---

## Pytest markers (optional filters)

Markers are **registered** in **`api/tests/conftest.py`** (`pytest_configure`) and duplicated in root **`pyproject.toml`** for documentation. **`pytest_collection_modifyitems`** also **assigns** markers from each test file’s path (e.g. everything under **`api/tests/api/`** gets **`api_http`**).

Examples (repository root, **`PYTHONPATH=api/src:frontend/src:api/tests`**):

```bash
# Only FastAPI route tests
python -m pytest -m api_http -q

# Skip slower e2e folder
python -m pytest -m "not e2e" -q

# Application use cases only
python -m pytest -m appli -q
```

CI continues to use **path-based** runs (**`validate_architecture`** then **`api/tests`** minus **`architecture/`** and **`bootstrap/`** + **`frontend/tests`**); markers are for **local narrowing**, not a separate required gate.

---

## Commands (repository root)

These match **CI** (see **`.github/workflows/ci.yml`**) and the **`scripts/`** entrypoints.

| What | Bash | PowerShell |
|------|------|------------|
| Architecture + bootstrap (layout + ASGI smoke) | `./scripts/validate_architecture.sh` | `.\scripts\validate_architecture.ps1` |
| Lint + architecture | `./scripts/validate.sh` | `.\scripts\validate.ps1` |
| Full workflow (architecture, then rest) | `./scripts/run_tests.sh` | `.\scripts\run_tests.ps1` |
| Lint only | `./scripts/lint.sh` | `.\scripts\lint.ps1` |

**`PYTHONPATH`:** **`api/src:frontend/src:api/tests`** (order matters: **`api/src`** first so test packages do not shadow application code).

**Blocking gate (`validate_architecture.*`):** **`api/tests/architecture/`** (layout, imports) **and** **`api/tests/bootstrap/`** (FastAPI **`create_app`**, **`api/main.py`** wiring, OpenAPI/health). Step 2 of **`run_tests.sh`** skips **`bootstrap/`** so those tests are not duplicated after the gate.

**Frontend ↔ HTTP path literals:** **`frontend/tests/streamlit/test_http_client_route_contract.py`** fails if core route strings drift in **`http_client.py`** / **`streamlit_auth.py`**.

**From `api/`:** **`api/pyproject.toml`** limits pytest to **`tests/architecture`** so **`cd api && pytest`** matches the architecture script without scanning the whole repo.

**One-shot pytest (may duplicate architecture if run alone):**

```bash
export PYTHONPATH=api/src:frontend/src:api/tests
python -m pytest api/tests frontend/tests -q
```

Prefer **`run_tests.sh`** for the ordered workflow (architecture + bootstrap once, then **`api/tests`** minus **`architecture/`** and **`bootstrap/`** + **`frontend/tests`**).

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
| **`test_deprecated_backend_shim_guardrails.py`** | Forbidden directories under **`api/src`**, forbidden monolith **`import`** patterns, **`frontend/src/services`** infra limits |
| **`test_no_legacy_paths.py`** | Text scan: banned pre-migration path tokens and no **`frontend_`**+**`gateway`** directory segments |
| **`test_no_dict_in_usecases.py`** | Use-case modules must not annotate or call **`to_dict`** / **`jsonify_value`**; contracts use DTOs / domain records |
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
| **`api/tests/api/`** | FastAPI routes, OpenAPI, **`dependencies`** overrides, auth envelope, ingest caps, RAG + evaluation + retrieval-settings JSON contracts; **`test_http_pipeline_e2e.py`** — HTTP-only walk (project → ingest → ask → inspect → preview → retrieval settings → benchmark → export) |
| **`api/tests/appli/`** | Use-case behavior, mocks; HTTP wire DTOs (**`appli/http/test_wire_payloads.py`**) assert typed payloads; **`appli/orchestration/test_rag_mode_contracts.py`** asserts RAG **mode separation** (ask vs inspect vs preview vs evaluation) and **query-log** flags on **`BuildRagPipelineUseCase`** / **`InspectRagPipelineUseCase`** |
| **`api/tests/domain/`** | Domain policy |
| **`api/tests/infra/`** | Infrastructure services and adapters |
| **`api/tests/composition/`** | Wiring smoke (may skip without optional deps) |
| **`api/tests/e2e/`** | Heavier or environment-sensitive checks |

---

## Frontend tests

| Location | Role |
|----------|------|
| **`frontend/tests/streamlit/`** | **`frontend/src/services`**, HTTP vs in-process client, Streamlit wiring; **`test_http_client_route_contract.py`** (path literals); **`test_streamlit_http_client.py`** (mock transport + ask/inspect/benchmark); **`test_frontend_api_contract.py`** (wire parsing **`rag_answer_from_ask_api_dict`**, retrieval settings payload, **`http_error_map`**, ingest copy helpers, error envelope → **`VectorStoreError`**, **`api_client`** re-exports) |
| **`frontend/tests/ui/`** | Streamlit/UI components; imports should follow the same **wire vs domain** rules as production (e.g. **`LOWER_IS_BETTER_METRICS`** from **`domain.evaluation.benchmark_comparison`**, **`BenchmarkResult`** from **`services.evaluation_wire_models`** where the UI contract is wire-shaped) |

### Recently strengthened API tests

- **`api/tests/api/test_system_routes.py`** — **`GET /health`**, **`GET /version`**, no auth required (even with bogus **`Authorization`**).
- **`api/tests/api/test_auth_router.py`** — login **422** envelope (**`RequestValidationError`**); register password mismatch **400** with **`AuthValidationError`** / **`auth_validation_failed`**.

### Recently strengthened application tests

- **`api/tests/appli/settings/test_retrieval_settings_use_cases.py`** — update use case accepts **legacy UI preset labels** (via **`PRESET_UI_LABELS`**) and persists canonical preset values.

### Import hygiene in tests

Several tests previously imported symbols from the wrong module after refactors (e.g. **`parse_query_log_timestamp`** lives under **`domain.rag.query_log_timestamp`**, not **`query_log_service`**; **`LOWER_IS_BETTER_METRICS`** under **`domain.evaluation.benchmark_comparison`**). Keeping test imports aligned with **real modules** avoids **collection failures** and false confidence.

---

## What architecture tests do not prove

- Absence of all logical coupling  
- Production security of JWT verification or secret handling  

---

## Final verification (closure checklist)

To **lock** the **9/10+** baseline before release or a major tag, run from the repository root (same order as CI):

1. **`./scripts/validate_architecture.sh`** (or **`.\scripts\validate_architecture.ps1`**) — **`api/tests/architecture`** + **`api/tests/bootstrap`**.
2. **`./scripts/run_tests.sh`** (or **`.\scripts\run_tests.ps1`**) — step 1 again, then **`api/tests`** (minus architecture/bootstrap) + **`frontend/tests`**.

Optional quicker gate: **`./scripts/validate.sh`** = **Ruff** + step 1. **Rationale and deferred scope** for the rating: **`docs/migration_report_final.md`** §10 and **§18**.

---

## Lint paths

Match **`scripts/lint.sh`:**

`ruff check api/src frontend/src api/tests/architecture`
