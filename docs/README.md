# RAGCraft documentation

Index of **code-aligned** docs for the current repository layout.

## Layout (today)

- **Backend:** **`api/src/`** (packages `domain`, `application`, `infrastructure`, `composition`, `interfaces`). ASGI entry **`api/main.py`**.
- **Frontend:** **`frontend/pages/`** (Streamlit multipage), **`frontend/src/`** (components, **`services`**, utils). Entry **`frontend/app.py`**.
- **Tests:** **`api/tests/`**, **`frontend/tests/`**.
- **Tooling:** root **`pyproject.toml`**, **`requirements.txt`**, **`scripts/`** (validate, lint, run_tests).

Structural rules are **enforced in CI** by **`api/tests/architecture/`** (see **`docs/testing_strategy.md`**).

**Closure baseline (9/10+):** The repository claims **9/10+** quality on migration, layering, orchestration, integration, tests, and feature coherence **for the scoped product** — with explicitly **deferred** items only in **`docs/migration_report_final.md`** §10 and §13 (production security, real LLM/vector SLOs, browser E2E, load). The **definitive** statement is **`docs/migration_report_final.md`** §18.

---

## Documents

| Document | Contents |
|----------|----------|
| **[architecture.md](architecture.md)** | Layers, dependency direction, orchestration ownership, FastAPI and Streamlit integration, diagram |
| **[dependency_rules.md](dependency_rules.md)** | Import rules, forbidden paths, mapping to architecture tests |
| **[rag_orchestration.md](rag_orchestration.md)** | Ask, inspect, preview recall, evaluation flows; logging; typed DTOs |
| **[api.md](api.md)** | How to run Uvicorn, JWT auth, uploads, OpenAPI, route ownership, API conventions |
| **[product_features.md](product_features.md)** | Supported features matrix: routes, DTOs, errors, tests, Streamlit |
| **[testing_strategy.md](testing_strategy.md)** | Scripts, pytest layout, architecture test index |
| **[cypress_scope.md](cypress_scope.md)** | Cypress (parcours HTTP + Streamlit), artefacts, commandes locales / CI |
| **[migration_report_final.md](migration_report_final.md)** | Closure report: what is fixed, what is enforced, what is out of scope |

---

## First commands (repo root)

**Architecture gate:**

```bash
export PYTHONPATH=api/src:frontend/src:api/tests
python -m pytest api/tests/architecture -q
```

Or: **`./scripts/validate_architecture.sh`** / **`.\scripts\validate_architecture.ps1`**.

**Lint + architecture:** **`./scripts/validate.sh`**

**Full tests:** **`./scripts/run_tests.sh`**

---

## Local development

- **API:** set **`RAGCRAFT_JWT_SECRET`**, then **`scripts/run_api.sh`** or **`scripts/run_api.ps1`** (repo root on **`PYTHONPATH`**) or the manual **`uvicorn`** command (see **`docs/api.md`**).
- **Streamlit:** from repo root, **`scripts/run_streamlit.sh`** or **`scripts/run_streamlit.ps1`** (sets **`api/src`** + **`frontend/src`** on **`PYTHONPATH`**); see root **`README.md`**.
- **Streamlit → API:** **`RAGCRAFT_API_BASE_URL`** (and optional timeout env vars — see **`docs/api.md`**). The UI uses **HTTP only**; run Uvicorn for the API separately.

Optional upload caps: **`RAG_MAX_UPLOAD_BYTES`**, **`RAG_MAX_AVATAR_UPLOAD_BYTES`** (**`docs/api.md`**, **`migration_report_final.md`**).
