# Final Clean Architecture migration report

**Date:** March 2026 (final hardening pass)  
**Status:** Migration considered **complete for the agreed boundaries**; see candid assessment below.

This document summarizes the **target state** after the FastAPI-first migration, legacy shim removal, and orchestration extraction. Normative rules live in [`docs/architecture/clean_architecture_target.md`](../../architecture/clean_architecture_target.md) and [`ARCHITECTURE_TARGET.md`](../../ARCHITECTURE_TARGET.md). Enforcement: `pytest tests/architecture/`.

---

## 1. What now lives in `application` and why

**`src/application/`** owns anything that expresses **what the system does** in response to a user or API intent, without choosing concrete databases, vector libraries, or HTTP frameworks.

| Area | Role |
|------|------|
| **`use_cases/**`** | One class per workflow (`*UseCase`), e.g. ask question, ingest file, run benchmark, list projects. These orchestrate **ports** and DTOs. |
| **`settings/retrieval_settings_tuner.py`** | Retrieval preset, merge, and validation — **policy** previously mixed into an infrastructure “service” name; now explicitly application-owned. |
| **`chat/policies/**`** | Pure prompt / document-selection rules used by pipeline steps. |
| **`evaluation/**`, `ingestion/**`, `http/wire.py`, `json_wire.py`** | DTOs, report formatting, JSON normalization for APIs — **application-facing shapes**, not drivers. |
| **`frontend_support/http_backend_stubs.py`** | Factories for **HTTP client mode**: returns ports implemented by Streamlit session state or pure tuners, so `src.frontend_gateway` never touches infrastructure. |
| **`common/**`** | Shared use-case helpers (query log payloads, pipeline context) that stay free of SQLite/LangChain/FastAPI. |

**Why:** Clean Architecture keeps **use cases and policies** stable while adapters and UIs change. Architecture tests assert the application layer does not import `src.infrastructure`, `streamlit`, `fastapi`, `sqlite3`, LangChain, or FAISS (see `test_layer_boundaries.py`, `test_application_orchestration_purity.py`).

---

## 2. What now lives in `infrastructure/adapters` and why

**`src/infrastructure/adapters/**`** holds **technical implementations** of domain/application ports: I/O, third-party SDKs, and framework-adjacent glue.

| Subpackage | Examples |
|------------|-----------|
| **`rag/`** | Doc store, reranking, hybrid retrieval, pipeline assembly, retrieval settings **adapter name** (`RetrievalSettingsService` subclasses application `RetrievalSettingsTuner` for composition typing). |
| **`evaluation/`** | Benchmark row processing, LLM judge, correlation, explainability — **metrics and judges** backed by models and parsers. |
| **`document/`** | Ingestion, parsing, table QA helpers. |
| **`workspace/`**, **`qa_dataset/`**, **`query_logging/`** | Project files, QA dataset persistence hooks, query log persistence. |
| **`sqlite/`** | SQLite implementations of user, asset, and project-settings ports. |

**Why:** Adapters **implement** ports defined in `src/domain/ports` (and occasional application-local protocols). They may import `src.application` where an adapter intentionally wraps a use case (allowed by boundary tests for files under `adapters/` only).

**Non-adapter infrastructure** (`persistence/`, `vectorstores/`, `llm/`, etc.) remains **implementation detail** behind adapters or composition; it must not import `src.application` except through the adapter rules above.

---

## 3. What was deleted

| Removed | Notes |
|---------|--------|
| **`src/backend/`** | Compatibility tree; replaced by `src/infrastructure/adapters` + use cases + `src/composition`. |
| **`src/adapters/`** | SQLite port code moved to **`src/infrastructure/adapters/sqlite/`**. |
| **`src/infrastructure/services/`** | Empty / removed; responsibilities folded into **`adapters`** and **application**. |
| **`src/infrastructure/adapters/chat/`** | Streamlit-only transcript store was **not** an infrastructure adapter; moved to **`src/frontend_gateway/streamlit_chat_transcript.py`**. |
| **`failure_analysis_service.py`** (re-export) | Dead shim; callers use **`src.domain.benchmark_failure_analysis`**. |

Legacy package names **`src.services`**, **`src.app.ragcraft_app`** remain **forbidden** (guard tests + Streamlit wiring checks).

---

## 4. What was transformed into ports or use cases

| Before / issue | After |
|----------------|--------|
| Monolithic app façade | **`BackendApplicationContainer`** + **`BackendClient`** (HTTP / in-process). |
| Retrieval merge logic in a fat “service” under infra | **`RetrievalSettingsTuner`** (application) + thin **`RetrievalSettingsService`** subclass for wiring. |
| Chat transcript class under `infrastructure/adapters/chat` | **`ChatService`** in **`frontend_gateway`** (delivery concern). |
| LangChain `Document` in application ingestion / JSON wire | **Duck-typed** summaries and document-like JSON (`ingest_common`, `json_wire`). |
| API dependencies constructing SQLite user repo directly | **`get_user_repository`** resolves **`auth_service.user_repository`** from composition. |
| Orchestration spread in docs only | **Explicit use cases** for chat, ingestion, evaluation, projects, settings; **ports** for ingestion, vector store, query logs, benchmarks, etc. |

---

## 5. What remains intentionally out of scope

| Item | Rationale |
|------|-----------|
| **Large RAG pipeline assembly** (e.g. `PipelineAssemblyService`) | Still coordinates many adapters inside **`infrastructure/adapters/rag/`**. Extracting it fully behind narrow application ports would be a **large** refactor with high regression risk; behavior is already reachable through use cases that depend on injected ports. |
| **Strict “composition-only” adapter imports** | We do not statically prove that *only* `src/composition` imports every adapter; tests guarantee **routers** and **application** do not import infrastructure, which covers the main leakage vectors. |
| **Renaming every `*Service` in adapters** | Many names are historical; renaming wholesale would churn imports and tests without changing semantics. Convention: **adapter** = implementation under `infrastructure/adapters`; **use case** = `*UseCase` under `application/use_cases`. |
| **SPA frontend** | Not part of this repo; **`pages/`**, **`src/ui/`**, and **`streamlit_app.py`** are the reference UI (not `apps/streamlit`). |

---

## 6. Candid assessment: aligned with Clean Architecture?

**Reasonably aligned — with one explicit caveat.**

**Strengths**

- **Dependency direction** is enforced for the critical paths: domain pure; application free of infrastructure and delivery frameworks; routers free of infrastructure; gateway free of infrastructure; composition builds the graph.
- **Use cases** are the primary entry for behavior invoked by FastAPI and by **`InProcessBackendClient`**.
- **Ports** live in domain (and a few application protocols for pipeline stages).
- **Legacy shims** are gone and **guarded** against reintroduction (`src.backend`, `src.adapters`, `src.infrastructure.services`).

**Caveat**

- Some **multi-step RAG assembly** still lives in infrastructure adapters. That is **orchestration-shaped** code. It does not violate import rules, but it is **not** the textbook ideal (ideal: application use case + small adapter steps). Accepting this is a **pragmatic** tradeoff until a dedicated pipeline use case + ports is justified.

**Verdict:** The repo matches **practical** Clean Architecture for this codebase: clear layers, testable boundaries, and a single composition root. It is **not** a purist extraction of every workflow line into application modules.

---

## 7. Remaining risks / future improvements

1. **Pipeline assembly extraction** — Introduce application-level `BuildRagPipelineOrchestrator` (or similar) and thin adapter facades; reduce `PipelineAssemblyService` to technical steps only.
2. **Application ↔ adapter naming** — Gradually rename confusing `*Service` types in adapters to `*Adapter` where it improves readability.
3. **Streamlit in API process** — Composition imports **`streamlit_chat_transcript`**, which imports **Streamlit**; API workers load Streamlit as a side effect today (pre-existing pattern). A future improvement is a **`NoOpChatTranscript`** for headless/API-only deployments injected at composition.
4. **Documentation drift** — Older migration markdown may mention “application may import adapters”; **current** rule is **no** `src.infrastructure` under `src/application`. Trust **`ARCHITECTURE_TARGET.md`**, **`clean_architecture_target.md`**, and **`tests/architecture/README.md`**.

---

## Verification performed (this pass)

- **FastAPI:** `create_app()` imports and builds successfully (local smoke).
- **Tests:** Full `pytest` suite green after the migration series.
- **Guards:** `pytest tests/architecture` covers removed packages, application purity, router persistence, gateway boundaries, and FastAPI package rules.

---

## Layer map (quick reference)

| Layer | Path |
|--------|------|
| Domain | `src/domain/` |
| Application | `src/application/` |
| Infrastructure adapters | `src/infrastructure/adapters/` |
| Other infrastructure | `src/infrastructure/{persistence,vectorstores,llm,...}` |
| Composition | `src/composition/` |
| HTTP transport | `apps/api/` |
| Frontend (Streamlit) | `streamlit_app.py`, `pages/`, `src/ui/` |
| Client / gateway | `src/frontend_gateway/` |
