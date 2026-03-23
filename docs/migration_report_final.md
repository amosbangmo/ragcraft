# Final report — architecture closure

This document is the **definitive closure statement** for RAGCraft’s **Clean Architecture** and **api / frontend** layout. It describes **the repository as it exists today**, how that state is **enforced**, and what remains **outside** architectural scope.

---

## 1. Canonical layout (current)

| Area | Path |
|------|------|
| Backend code | **`api/src/`** — `domain`, `application`, `infrastructure`, `composition`, `interfaces` |
| ASGI entry | **`api/main.py`** |
| Frontend code | **`frontend/src/`** — `pages`, `components`, `services`, `state`, `viewmodels`, `utils` |
| Streamlit entry | **`frontend/app.py`** |
| Backend tests | **`api/tests/`** (including **`api/tests/architecture/`**) |
| Frontend tests | **`frontend/tests/`** (including **`frontend/tests/streamlit/`**) |
| Docs | **`docs/`** |
| Validation scripts | **`scripts/`** (`validate_architecture`, `run_tests`, `lint`, `validate`, …) |

**Imports:** With **`PYTHONPATH`** as in **`scripts/run_tests.sh`**, backend and frontend use **top-level** package names (`domain`, `application`, `services`, …).

---

## 2. What was already strong

Before the documentation and structure closure passes, the codebase already had:

- Clear **hexagonal** layering: domain ports, application use cases, infrastructure implementations, composition wiring, FastAPI under **`interfaces/http`**, and a **Streamlit client** behind **`BackendClient`** in **`frontend/src/services`**.
- **RAG orchestration** owned in **application** (`application/orchestration/rag`, post-recall steps, summary recall workflow), not in a single infrastructure “god service”.
- A growing **`api/tests/architecture/`** suite blocking the worst dependency regressions.

The remaining work was **consistency** (paths, docs, tests naming), **guardrail completeness** (code-root isolation, transport vs **`infrastructure.rag`**), and **narrative alignment** so contributors see one story.

---

## 3. Structural closure

- **Single backend root:** all backend application modules live under **`api/src/`**, with **`api/main.py`** as the only ASGI bootstrap outside that tree (plus **`api/__init__.py`** if present). Tests live under **`api/tests/`**.
- **Single frontend root:** UI and client code under **`frontend/src/`**, entry **`frontend/app.py`**, tests under **`frontend/tests/`**.
- **CI and local scripts** use the same **`PYTHONPATH`** and pytest splits (**`scripts/validate_architecture.sh`**, **`run_tests.sh`**, **`lint.sh`**).
- **Architecture tests** forbid duplicate roots (`src/`, `apps/` at repo root), misplaced FastAPI routers, stray packages under **`api/src`**, and Python files outside the allowed trees (**`test_repository_structure.py`**).

---

## 4. Auth and HTTP boundary

- **JWT bearer** is the standard for scoped HTTP routes: **`Authorization: Bearer`**, verified via **`AuthenticationPort`** (**`JwtAuthenticationAdapter`** in **`infrastructure/auth`**).
- **Domain-owned identity:** **`AuthenticatedPrincipal`**, **`AuthenticationPort`**, **`AccessTokenIssuerPort`** under **`domain`**.
- **FastAPI** resolves the container and **`AuthenticatedPrincipal`** in **`interfaces/http/dependencies.py`**; **routers do not import **`infrastructure.*`**.
- **HTTP transcript** for the API worker uses **`application/frontend_support/memory_chat_transcript.py`**.

---

## 5. RAG orchestration and typing

- **Flows:** product ask (**`AskQuestionUseCase`**), inspect (**`InspectRagPipelineUseCase`** with **`emit_query_log=False`**), preview recall (**`PreviewSummaryRecallUseCase`**), evaluation (**`execute_rag_inspect_then_answer_for_evaluation`** in **`application/orchestration/evaluation`**).
- **Sequencing:** summary recall and post-recall assembly live in **`application/orchestration/rag`**; **`infrastructure/rag`** provides single-step adapters.
- **Typed boundaries:** e.g. **`RetrievalSettingsOverrideSpec`**, **`VectorLexicalRecallBundle`**, **`RagEvaluationPipelineInput`**, **`RagInspectAnswerRun`**, **`PipelineLatency`**, **`GoldQaPipelineRowInput`** — see **`docs/rag_orchestration.md`**.
- **Manual evaluation:** **`RunManualEvaluationUseCase`** is the single application orchestrator; **`manual_evaluation_service`** is assembly-only (**`test_manual_evaluation_single_orchestrator.py`**).
- **Gold QA:** **`BenchmarkExecutionUseCase`** requires **`RagInspectAnswerRun`** from **`pipeline_runner`**; **`GoldQaBenchmarkAdapter`** bridges **`EvaluationService`**.

---

## 6. Upload and ingestion

- **Bounded multipart reads** in **`interfaces/http/upload_adapter.py`** → domain **`BufferedDocumentUpload`** → ingestion use cases. Policy documented in **`application/ingestion/upload_boundary.py`** and **`docs/api.md`**.
- **Lazy optional deps:** heavy parsers (e.g. unstructured) load when extraction runs, not necessarily at **`create_app()`** import time — see **`infrastructure/rag/ingestion/unstructured_extractor.py`**.

---

## 7. Documentation and tests alignment (closure)

- **`docs/architecture.md`**, **`docs/dependency_rules.md`**, **`docs/rag_orchestration.md`**, **`docs/api.md`**, **`docs/testing_strategy.md`**, **`docs/README.md`**, and this file were **rewritten or updated** to describe **only** the **`api/src` + `frontend/src`** layout and the **current** test enforcement map.
- **Root `README.md`** project tree and run instructions match the same layout (no obsolete **`api/src/core`** or **`api/src/auth`** package roots unless they exist — they do **not** today; auth lives under **`domain`**, **`application/use_cases/auth`**, and **`infrastructure/auth`**).

---

## 8. Enforcement summary

| Mechanism | Role |
|-----------|------|
| **`api/tests/architecture/`** | Authoritative gate: layout, skeleton, imports, FastAPI/Streamlit boundaries, orchestration purity |
| **`scripts/validate_architecture.sh`** | Runs that package with correct **`PYTHONPATH`** |
| **`.github/workflows/ci.yml`** | Lint + architecture + pytest slice mirroring **`run_tests.sh`** |
| **Root `pyproject.toml`** | Ruff paths, pytest defaults |

---

## 9. Reference tree (simplified)

```text
api/
  main.py
  src/
    application/     # use_cases, orchestration, rag, dto, frontend_support, …
    composition/
    domain/
    infrastructure/  # rag, evaluation, persistence, auth, storage, observability, config
    interfaces/
      http/          # main, dependencies, routers/, schemas/, upload_adapter, …
  tests/
    architecture/
    api/
    appli/
    infra/
    e2e/
    …
frontend/
  app.py
  src/
    pages/
    components/
    services/
    state/
    viewmodels/
    utils/
  tests/
    streamlit/
    ui/
docs/
scripts/
```

---

## 10. Intentionally deferred (not architecture gaps)

- Full **production security program** (rotation runbooks, asymmetric JWTs, external IdP) beyond the current bearer-JWT design.
- **Performance SLOs** and caching strategy as product decisions.
- **mypy strict** on the entire tree in one step.
- **SQLite list endpoints** still dict-shaped in places — incremental typing improvement.

---

## 11. Verdict

**The architecture migration and physical layout for this repository are complete** for the stated scope: layers, dependency direction, orchestration ownership, FastAPI vs Streamlit boundaries, and **`api/src` / `frontend/src`** as the only application code roots are **implemented and enforced**.

Further work is **product quality and operational hardening** (**§10**), not structural migration.

**Primary references for day-to-day work:** **`docs/architecture.md`**, **`docs/dependency_rules.md`**, **`docs/rag_orchestration.md`**, **`docs/api.md`**, **`docs/testing_strategy.md`**.
