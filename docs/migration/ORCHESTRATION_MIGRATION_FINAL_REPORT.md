# Orchestration migration — final report (Prompt 5)

**Date:** 2026-03-22  
**Purpose:** Close the orchestration track: confirm no legacy runtime paths, correct layering, and document any intentional compatibility seams.  
**Architecture source of truth:** [`ARCHITECTURE_TARGET.md`](../../ARCHITECTURE_TARGET.md)

---

## 1. Orchestration problems fully resolved

| Issue | Resolution |
|-------|------------|
| **God-object RAG façade** | `RAGService` **removed**. Chat/RAG orchestration lives in **`src/application/use_cases/chat/**`** and **`src/composition/chat_rag_wiring.py`** (subgraph build + use-case wiring from technical services). |
| **Retrieval comparison in infrastructure** | `RetrievalComparisonService` **removed**. **`CompareRetrievalModesUseCase`** + **`retrieval_mode_comparison.py`** own FAISS vs hybrid comparison. |
| **Composition root mixing orchestration** | **`BackendComposition`** holds **technical adapters only** (no lazy RAG subgraph). RAG subgraph assembly runs in **`BackendApplicationContainer._chat_rag_use_cases`**. |
| **Use cases coupled to concrete adapters** | Application **use cases** depend on **`src/domain/ports/*`** protocols; **`EvaluationService`**, **`ProjectService`**, **`IngestionService`**, etc. satisfy them at the container. |
| **Benchmark execution importing many concretes** | **`BenchmarkExecutionUseCase`** depends on **narrow benchmark orchestration ports**; **`EvaluationService`** wires concrete row/aggregation/correlation services. |
| **Duplicate FastAPI DB bootstrap** | **`ensure_auth_database`** removed from `apps/api/dependencies.py`. **`get_user_repository`** now depends on **`BackendContainerDep`**, so **`init_app_db()`** runs once via **`build_backend_composition()`** (same path as the rest of the graph). |
| **Streamlit tied to `RAGCraftApp`** | **`RAGCraftApp` removed** from runtime. **`InProcessBackendClient`** wraps **`BackendApplicationContainer`**; **`src/core/app_state.py`** documents this (no `src.app` import). |

---

## 2. Legacy runtime paths — status

| Path | Status |
|------|--------|
| **`src/backend/`** | **Absent** (enforced by `tests/architecture/test_deprecated_backend_and_gateway_guardrails.py`). |
| **`src/infrastructure/services/`** | **Absent** — adapters live under **`src/infrastructure/adapters/`**. |
| **`src.services`** | **Absent** as a package; only mentioned in docs/tests as a **forbidden** legacy name. |
| **`src/app/ragcraft_app.py` / `RAGCraftApp`** | **Removed**; tests assert no production import. A stray **untracked** `src/app/__pycache__` may exist locally — not part of the shipped tree. |

---

## 3. `BackendComposition` — technical dependencies only

**Verdict: yes.**  
`BackendComposition` exposes singleton **adapters and repositories** (auth, projects, ingestion, vector store, evaluation **service instance**, chat transcript service, doc store, reranking, QA services, project settings repository, retrieval settings service, query log). It does **not** build RAG use cases, retrieval subgraph bundles, or `rag_service`.

---

## 4. Application use cases own orchestration

**Verdict: yes** for user-visible flows:

- Ask, inspect, preview recall, compare retrieval modes, ingestion, projects, settings, evaluation, QA dataset, etc. are **`UseCase.execute`** entrypoints.
- **`chat_rag_wiring`** is **composition-only** (object graph), not business rules.
- **`EvaluationService`** remains an **infrastructure façade** that composes benchmark row processing and delegates to **`BenchmarkExecutionUseCase`** (application). Manual/gold flows use **ports** at the use-case boundary.

---

## 5. Temporary compatibility façades still in play

| Facade | Role | Orchestration? |
|--------|------|----------------|
| **`InProcessBackendClient`** | Maps **`BackendClient`** protocol to container use cases. | **No** — thin delegation. |
| **`HttpBackendClient`** | REST transport; stubs for attributes not exposed over HTTP. | **No**. |
| **`http_backend_stubs.py`** | Lazy-instantiates **`ChatService`** / **`RetrievalSettingsService`** for HTTP mode helpers (architecture: gateway must not import infra at module top). | **No** — technical defaults only. |
| **`retrieval_merge_default.py`** | Lazy default **`RetrievalPresetMergePort`** for UI helpers. | **No**. |
| **`EvaluationService`** | Wires evaluation adapters + **`BenchmarkExecutionUseCase`**. | **Infrastructure-side assembly**, not application use-case orchestration of HTTP/Streamlit journeys. |

None of the above reintroduce **`RAGCraftApp`** or **`src/backend`**.

---

## 6. Remaining gaps / non-blocking follow-ups

1. **`HttpBackendClient`** — some protocol methods intentionally **`NotImplementedError`** where there is no REST equivalent (documented; callers use specific routes).
2. **`X-User-Id`** — trust-on-wire identity until real auth is wired.
3. **Optional docs** — older files such as **`current-architecture-baseline.md`** remain as **historical snapshots** (header already warns); safe to trim or archive later.
4. **README variants** (`README.github.md`) may still show legacy diagrams; product **`README.md`** is canonical for current architecture.

---

## 7. Final verdict — orchestration migration status

**COMPLETE for the stated goals.**  

- Legacy orchestration packages (**`src/backend`**, **`src/infrastructure/services`**) are **gone** from the runtime tree.  
- **RAG and retrieval comparison** orchestration live in the **application layer** + **composition wiring**, not in removed façade types.  
- **FastAPI `dependencies.py`** resolves **container, identity (`X-User-Id`), user repository, and use cases**; it does **not** run a separate **`init_app_db`** hook.  
- **Streamlit** uses **`BackendClient`** and **`BackendApplicationContainer`** — not **`RAGCraftApp`**.

---

## Verification performed (this pass)

- Full test suite: `python -m pytest tests/` (project CI expectation).  
- App import: `from apps.api.main import app`.  
- Grep audits: no `src.backend` imports under `src/`; no `src.infrastructure.services` package; no `RAGCraftApp` in production `src/` / `apps/api` (tests reference forbidden strings by design).

---

## Related documents

- [`MIGRATION_COMPLETE_REPORT.md`](./MIGRATION_COMPLETE_REPORT.md) — earlier detailed audit (partially superseded; see note at top).  
- [`ragcraftapp-deprecation.md`](./ragcraftapp-deprecation.md) — removal of `RAGCraftApp`.  
- [`BACKEND_MIGRATION_CHECKLIST.md`](./BACKEND_MIGRATION_CHECKLIST.md) — FastAPI + Streamlit checklist (updated for current wiring).
