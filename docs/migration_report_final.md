# Final architecture report (current system)

This document describes **what the repository implements today**, how it is **enforced in tests**, and **known limits**. It is not a roadmap.

---

## 1. Execution model: HTTP only

- **Streamlit** talks to the backend **only** through **`services.http_backend_client.HttpBackendClient`** (cached in **`infrastructure.config.app_state`**).
- **`InProcessBackendClient`**, dual **`RAGCRAFT_BACKEND_CLIENT`** modes, and **`streamlit_backend_access`** are **removed**. There is no alternate transport behind the UI protocol.
- **`application.frontend_support.backend_client_protocol`** remains a **thin re-export** of **`services.backend_client_protocol`** for compatibility with older import strings in tests or tools.

---

## 2. Frontend boundary: wire types only

- **`frontend/src/pages`** and **`frontend/src/components`** must not import **`domain`** or **`application`** (see **`api/tests/architecture/test_frontend_structure.py`**).
- **`frontend/src/services`** must not import **`domain`**, **`application`**, **`composition`**, or **`interfaces`** (see **`api/tests/architecture/test_fastapi_migration_guardrails.py`**).
- Presentation helpers that previously lived under **`application.frontend_support.view_models`** now live under **`frontend/src/services/`** (`benchmark_compare_ui`, `failure_analysis_ui`, `retrieval_preset_ui`, `retrieval_preset_merge_service`, etc.).
- **`services.api_client`** re-exports the façade: **`BackendClient`**, **`HttpBackendClient`**, wire DTOs, and UI helpers.

---

## 3. Guarantees tested in code

| Guarantee | Where |
|-----------|--------|
| HTTP client satisfies **`BackendClient`** at runtime | **`test_fastapi_migration_guardrails.test_runtime_checkable_backend_client_accepts_http_client_instance`** |
| Inspect vs ask **latency merge** and **pipeline dict** shape | **`api/tests/appli/rag/test_rag_pipeline_invariants.py`** |
| FAISS vs hybrid **mode strings** on **`PipelineBuildResult`** | same module |
| Invalid ingest / ask / unauthenticated project list → **422 / 401** | **`api/tests/api/test_ingestion_robustness.py`** |
| Full HTTP walk (mocked use cases) | **`api/tests/api/test_http_pipeline_e2e.py`** |
| Composition smoke upload → ask (mocked services) | **`api/tests/e2e/test_smoke_upload_ingest_ask.py`** |
| Mocked ask **wall time** bound | **`api/tests/appli/test_performance_smoke.py`** |
| Browser / API E2E on **live uvicorn** (`/docs`, `/health`, parcours workspace HTTP) | **`cypress/e2e/`** (Cypress, **`npm run cy:ci`**) |

---

## 4. CI (`.github/workflows/ci.yml`)

- Lint (Ruff), architecture scripts, main pytest slice, infra/appli unittest slices.
- **Boot check:** **`create_app()`** from **`interfaces.http.main`** (not Streamlit composition).
- **Cypress:** **`npm ci`** then **`npm run cy:ci`** (**`scripts/run_cypress_e2e.py`**: API + **`cypress run`**).
- **Coverage:** pytest-cov over **`api/tests/appli`** + **`api/tests/domain`** for packages **`application`** and **`domain`**, XML report **`coverage.xml`** (no fixed fail-under in CI; tune locally before raising a gate).

---

## 5. Limitations (factual)

- **Cypress E2E** covers the **OpenAPI UI + health** in a browser and, via **`cy.request`**, le même parcours **HTTP** que Streamlit en mode backend HTTP (inscription, login, projet, ingest, ask + champs sources, réglages retrieval, évaluation manuelle, erreurs API structurées). L’UI Streamlit widgets n’est pas pilotée au pixel près; le contrat réseau l’est.
- **Mypy** is **not** strict repo-wide; **`pyproject.toml`** enables **`warn_return_any`** and **`no_implicit_optional`** as incremental tightening — full strict passes are optional developer commands.
- **Heavy parsers** (e.g. unstructured) and **external LLM/embedding** calls are not required for the default CI pytest slice; many tests use **mocks** or **dependency overrides**.

---

## 6. Docs index

| Doc | Purpose |
|-----|---------|
| **`docs/architecture.md`** | Layers and layout |
| **`docs/dependency_rules.md`** | Import rules ↔ architecture tests |
| **`docs/api.md`** | HTTP, JWT, env vars |
| **`docs/testing_strategy.md`** | Pytest layout and markers |
| **`docs/rag_orchestration.md`** | RAG flows (update in-process Streamlit notes manually if any remain) |

---

## 7. Removed / obsolete paths

Do not reference these as living code:

- **`api/src/application/frontend_support/http_backend_client.py`** (moved to **`frontend/src/services/http_backend_client.py`**)
- **`api/src/application/frontend_support/in_process_backend_client.py`**
- **`api/src/application/frontend_support/client_wire_mappers.py`**
- **`api/src/application/frontend_support/view_models.py`**
- **`api/src/application/frontend_support/streamlit_backend_access.py`**
- **`api/src/application/services/http_backend_stubs.py`**
