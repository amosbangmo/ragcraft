# Dependency rules

This document is the **authoritative description** of allowed dependencies and physical structure, aligned with **`api/tests/architecture/`**. If code and this file disagree, **fix the code** or **update this file** together with the tests. **`ARCHITECTURE_TARGET.md`** is a short summary of the same enforced tree (**five** packages under **`api/src/`** only).

---

## Validate locally (repo root)

| Intent | Command |
|--------|---------|
| Architecture + bootstrap (layout + ASGI entry smoke) | **`./scripts/validate_architecture.sh`** or **`.\scripts\validate_architecture.ps1`** |
| Lint + architecture | **`./scripts/validate.sh`** or **`.\scripts\validate.ps1`** |
| Full pytest (architecture first, then rest) | **`./scripts/run_tests.sh`** or **`.\scripts\run_tests.ps1`** |
| Lint only | **`./scripts/lint.sh`** or **`.\scripts\lint.ps1`** |

Scripts set **`PYTHONPATH=api/src:frontend/src:api/tests`** (use **`;`** on Windows in the `.ps1` scripts).

---

## Physical structure (enforced)

| Rule | Primary test |
|------|----------------|
| Required top-level areas: **`api/`**, **`frontend/`**, **`docs/`**, **`scripts/`**, **`api/src/`**, **`frontend/src/`** | **`test_repository_structure.py`** |
| **Forbidden** at repo root: **`src/`**, **`apps/`**, **`pages/`**, **`streamlit_app.py`** | **`test_repository_structure.py`** |
| Backend **application** `.py` only under **`api/src/`** (plus **`api/main.py`**, **`api/__init__.py`**, **`api/tests/**`) | **`test_repository_structure.py`** |
| Frontend **application** `.py` only under **`frontend/src/`** (plus **`frontend/app.py`**, **`frontend/tests/**`) | **`test_repository_structure.py`** |
| **Forbidden** under **`api/src/`**: top-level **`pages/`**, **`ui/`**; stray **`adapters/`**, **`backend/`**, **`services/`** packages; **`infrastructure/services/`** | **`test_repository_structure.py`**, **`test_deprecated_backend_shim_guardrails.py`** |
| **Forbidden** under **`frontend/src/`**: vendored **`domain`**, **`application`**, **`infrastructure`**, **`composition`**, **`interfaces`** trees | **`test_repository_structure.py`** |
| FastAPI **`APIRouter`** only under **`api/src/interfaces/http/routers/`** | **`test_repository_structure.py`** |
| Pydantic **`BaseModel`** HTTP types under **`interfaces/http/schemas/`** (not loose router files) | **`test_repository_structure.py`** |
| Required skeleton files and directories | **`test_required_tree.py`** |
| No alternate-tree path literals or **`frontend_`**+**`gateway`** segments in tracked text (see **`test_no_legacy_paths`** module) | **`test_no_legacy_paths.py`** |

---

## Layer imports (enforced)

| From | May import | Must not import (unless noted) |
|------|------------|--------------------------------|
| **`api/src/domain/`** | `domain`, stdlib, vetted third-party | `application`, `infrastructure` (except **`infrastructure.config`** per **`test_layer_import_rules.py`**), `composition`, `interfaces`, FastAPI, Starlette, Streamlit |
| **`api/src/application/`** | `domain`, `application` | FastAPI, Starlette, Streamlit, `interfaces`, concrete **`infrastructure`** (except **`infrastructure.config`** where allowed). **Use cases** must not import **`services`** (frontend package). |
| **`api/src/infrastructure/`** | `domain`, stdlib, third-party | **`application`** — **zero** imports (**`test_adapter_application_imports.py`**, with **`auth_credentials`** exception). Streamlit only on allowlisted shim files (**`test_layer_boundaries`**). |
| **`api/src/composition/`** | `domain`, `application`, `infrastructure` for wiring | Streamlit, **`services`** (frontend) |
| **`api/src/interfaces/http/routers/`** | FastAPI, `application`, `domain`, `composition` via deps | **`infrastructure.*`** (any) |
| **`api/src/interfaces/http/`** (non-router) | As needed for app, errors, upload | Streamlit; also no frontend top-level packages or monolith **`src`/`apps`** import roots (**`test_fastapi_delivery_boundaries`**) |
| **`frontend/src/services/`** | `domain`, `application`, `composition`, `infrastructure.config`, `infrastructure.auth` | Other **`infrastructure.*`** (**`test_frontend_services_infrastructure_imports_are_limited`** in **`test_deprecated_backend_shim_guardrails.py`**) |
| **`frontend/src/pages`**, **`components/`** | `services`, Streamlit, `infrastructure.auth` for guards | `domain`, `application`, `composition`, `interfaces` (**`test_frontend_structure.py`**) |

---

## RAG-specific rules

- Infrastructure **must not** host a second RAG orchestration façade (**`test_no_rag_service_facade.py`**).  
- Chat orchestration folders **must not** import **`infrastructure`** or delivery stacks (**`test_orchestration_package_import_boundaries.py`**).  
- **`interfaces/http`** and **`frontend/src/services`** **must not** import **`infrastructure.rag`** directly (**`test_orchestration_boundaries.py`**).  
- **Composition** **must not** import **`services`** (frontend); Streamlit transcript wiring lives in **`application.frontend_support.streamlit_backend_factory`** (**`test_composition_import_boundaries.py`**).

---

## Shared boundary types (examples)

- **`QueryLogIngressPayload`** — **`api/src/domain/rag/query_log_ingress_payload.py`**.  
- **`EvaluationJudgeMetricsRow`** — **`api/src/domain/evaluation/judge_metrics_row.py`**.  
- **`GoldQaPipelineRowInput`** — **`api/src/domain/evaluation/gold_qa_row_input.py`**.  
- **`RetrievalModeComparisonResult`** / **`RetrievalModeComparisonRow`** — **`api/src/application/dto/retrieval_comparison.py`** (FAISS vs hybrid comparison; wire serialization via **`application/http/wire`**).  
- **`MemoryChatTranscript`** — only **`api/src/application/frontend_support/memory_chat_transcript.py`** (HTTP worker + tests); no duplicate under **`infrastructure`**.

---

## Anti-patterns

1. Routers constructing **`VectorStoreService`**, **`EvaluationService`**, or other infra services inline — use **`Depends`** → container → use case.  
2. Application importing concrete persistence/RAG modules — wire in **composition**.  
3. Reintroducing forbidden directories under **`api/src`** or forbidden roots at repo root — tests fail.  
4. Python **`import`** of legacy monolith package names (**`src.backend`**, **`src.services`**, **`infrastructure.services`**, etc.) — forbidden across scanned trees (**`test_deprecated_backend_shim_guardrails.py`**).

---

## Enforcement index

| Concern | Test module(s) |
|---------|----------------|
| Layout + code roots | **`test_repository_structure.py`**, **`test_required_tree.py`**, **`test_no_legacy_paths.py`** |
| Use-case typing (no dict contracts) | **`test_no_dict_in_usecases.py`** |
| Domain / application / router imports | **`test_layer_import_rules.py`** |
| Infrastructure / composition | **`test_layer_boundaries.py`**, **`test_adapter_application_imports.py`** |
| FastAPI package purity | **`test_fastapi_delivery_boundaries.py`**, **`test_fastapi_migration_guardrails.py`** |
| Frontend imports | **`test_frontend_structure.py`**, **`test_deprecated_backend_shim_guardrails.py`** (`test_frontend_services_infrastructure_imports_are_limited`) |
| Application tech purity | **`test_application_orchestration_purity.py`** |
| Orchestration subtrees | **`test_orchestration_package_import_boundaries.py`**, **`test_orchestration_boundaries.py`** |
| Composition vs `services` | **`test_composition_import_boundaries.py`** |
| RAG façade | **`test_no_rag_service_facade.py`** |
| Manual eval single path | **`test_manual_evaluation_single_orchestrator.py`** |
| Chat RAG ports | **`test_application_chat_rag_boundary_ports.py`** |

---

## Tests should respect the same boundaries

**`api/tests/architecture/`** encodes this document mechanically. **`api/tests/appli/`** and **`api/tests/api/`** should import **`domain`** / **`application`** / **`interfaces`** from their **real** package locations (not stale convenience paths removed during refactors). **`frontend/tests`** that assert on **API-shaped** types should use **`services.evaluation_wire_models`** / **`services.api_client`** wire exports where production code does, so **collection** and **runtime** agree.

Optional **pytest markers** (path-assigned in **`api/tests/conftest.py`**) help run slices (**`api_http`**, **`appli`**, **`e2e`**, …); see **`docs/testing_strategy.md`**.

---

## Lint and format

**Ruff**, **Black**, and **mypy** are configured in the root **`pyproject.toml`**. Ruff catches issues architecture tests do not (e.g. undefined names).
