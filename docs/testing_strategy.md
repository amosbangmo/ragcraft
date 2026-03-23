# Testing strategy

Tests are **layered** for **structural confidence**: layout and imports, bootstrap, **reliability** flows, HTTP contracts, use cases, infra, e2e, and frontend wire/UI. Goal: **regressions in layering, RAG mode separation, and Streamlit↔API wiring** — not a coverage percentage alone.

**Related:** **`docs/architecture.md`**, **`docs/migration_report_final.md`** §13, §16, §18. **CI:** **`.github/workflows/ci.yml`**, **`scripts/run_tests.sh`** / **`.ps1`**.

---

## 1. Test matrix

| Layer | Location | Proves |
|-------|----------|--------|
| **Architecture** | **`api/tests/architecture/`** | Layout, forbidden imports, router placement, orchestration purity, **`test_no_legacy_paths.py`**, **`test_no_dict_in_usecases.py`**, Streamlit **`services`** allowlist |
| **Bootstrap** | **`api/tests/bootstrap/`** | **`api/main.py`** → **`create_app`**, **`/health`**, **`/openapi.json`** |
| **Reliability** | **`api/tests/reliability/`** | Boot (**`test_app_boot.py`**), auth → **`/users/me`** (**`test_auth_flow.py`**), **`POST /chat/ask`** (**`test_chat_flow.py`**), project → ingest → ask (**`test_e2e_flow.py`**) — **`TestClient`**, stubbed use cases |
| **API / HTTP** | **`api/tests/api/`** | Routes, auth, **422**, **`RAGCraftError`**, multipart, **`test_http_pipeline_e2e.py`** |
| **Application** | **`api/tests/appli/`** | Use cases, **`test_rag_mode_contracts.py`** |
| **Domain** | **`api/tests/domain/`** | Domain policy |
| **Infrastructure** | **`api/tests/infra/`** | Adapters, SQLite, services |
| **Composition** | **`api/tests/composition/`** | Wiring smoke |
| **E2E / regression** | **`api/tests/e2e/`** | Heavier / env-sensitive gates |
| **Browser E2E** | **`cypress/e2e/`** | Cypress against **live uvicorn**: surface publique (`public_surface.cy.js`) + parcours API aligné Streamlit HTTP (`workspace_journey.cy.js` — auth, projet, ingest, ask/sources, réglages retrieval, évaluation manuelle, erreurs JSON) via **`npm run cy:ci`** / **`scripts/run_cypress_e2e.py`**. |
| **Frontend** | **`frontend/tests/`** | **`test_api_client.py`**, Streamlit, wire parsing, route literal contract |

**Product matrix:** **`docs/product_features.md`**.

---

## 2. Pytest markers

Registered in **`api/tests/conftest.py`** and **`pyproject.toml`**. Paths auto-tag (**`api/tests/reliability/`** → **`reliability`**, **`api/tests/api/`** → **`api_http`**, …).

```bash
export PYTHONPATH=api/src:frontend/src:api/tests

python -m pytest -m api_http -q
python -m pytest -m appli -q
python -m pytest -m reliability -q
python -m pytest -m "not e2e" -q
```

CI uses **path-based** runs; markers are for **local** narrowing.

---

## 3. Commands (repo root)

| Step | Bash | PowerShell |
|------|------|------------|
| Architecture + bootstrap | **`./scripts/validate_architecture.sh`** | **`.\scripts\validate_architecture.ps1`** |
| Lint + architecture | **`./scripts/validate.sh`** | **`.\scripts\validate.ps1`** |
| Full tests | **`./scripts/run_tests.sh`** | **`.\scripts\run_tests.ps1`** |
| Lint only | **`./scripts/lint.sh`** | **`.\scripts\lint.ps1`** |

**`PYTHONPATH`:** **`api/src:frontend/src:api/tests`** (**`api/src`** first).

**Gate:** **`validate_architecture.*`** = **`api/tests/architecture`** + **`api/tests/bootstrap`**. **`run_tests.*`** repeats the gate then **`api/tests`** (skipping duplicate arch/bootstrap in step 2 where scripted) + **`frontend/tests`**.

**HTTP path literals (Streamlit):** **`frontend/tests/streamlit/test_http_client_route_contract.py`** scans **`frontend/src/services/http_backend_client.py`** and **`frontend/src/services/streamlit_auth.py`**.

**`cd api && pytest`:** **`api/pyproject.toml`** limits to **`tests/architecture`** by default.

**Full pytest (duplicates gate if run alone):**

```bash
export PYTHONPATH=api/src:frontend/src:api/tests
python -m pytest api/tests frontend/tests -q
```

**mypy (optional):** **`PYTHONPATH=api/src`** then e.g. **`-p domain`**.

---

## 4. Architecture tests (index)

| Module | Role |
|--------|------|
| **`test_repository_structure.py`** | Allowed trees, router/schema locations |
| **`test_no_legacy_paths.py`** | Banned path tokens in tracked text |
| **`test_no_dict_in_usecases.py`** | Use-case modules avoid **`to_dict`** / **`jsonify_value`** contracts |
| **`test_frontend_streamlit_services_entrypoint.py`** | Pages/components: allowlisted **`services.*`** only |
| **`test_fastapi_migration_guardrails.py`**, **`test_layer_boundaries.py`**, … | Layers and delivery boundaries |
| **`test_composition_import_boundaries.py`** | Composition must not import **`services`** |

Full list: **`api/tests/architecture/README.md`**, **`import_scanner.py`**.

---

## 5. Other backend suites (summary)

- **`api/tests/api/`** — OpenAPI, **`dependencies`**, ingest caps, RAG/evaluation JSON.  
- **`api/tests/appli/`** — Use cases; **`appli/http/test_wire_payloads.py`** for typed HTTP DTOs.  
- **`api/tests/reliability/`** — Runtime confidence (see §1).  
- **`api/tests/e2e/`** — Quality gates / thresholds.

---

## 6. Frontend tests

| Location | Role |
|----------|------|
| **`frontend/tests/test_api_client.py`** | Canonical **`services.api_client`** exports |
| **`frontend/tests/streamlit/`** | Wire parsing (**`test_frontend_api_contract.py`**), HTTP client mocks, auth, lazy imports |
| **`frontend/tests/ui/`** | UI helpers |

Imports in tests should mirror production: UI-facing symbols from **`services.api_client`** where the app uses the façade; low-level wire types from **`services.evaluation_wire_models`** / **`api_contract_models`** when testing parsers directly.

---

## 7. What tests do not prove

Full security audit of JWT deployment, production load, or real LLM/vector SLOs.

---

## 8. Closure checklist (9/10+)

1. **`./scripts/validate_architecture.sh`** (or **`.ps1`**)  
2. **`./scripts/run_tests.sh`** (or **`.ps1`**)  

**Rationale:** **`docs/migration_report_final.md`** §10, §18.

---

## 9. Lint scope

Per **`scripts/lint.sh`:**

`ruff check api/src frontend/src api/tests/architecture`
