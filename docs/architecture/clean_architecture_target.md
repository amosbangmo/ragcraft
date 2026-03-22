# Clean architecture target (canonical map)

This document is the **normative** layering contract for RAGCraft. It complements the **runtime** overview in [`ARCHITECTURE_TARGET.md`](../../ARCHITECTURE_TARGET.md) at the repo root and the enforced rules in [`tests/architecture/README.md`](../../tests/architecture/README.md).

## Canonical entrypoints (no `src/backend`)

There is **no** `src/backend` package and no legacy “backend” shim layer. Call sites must use:

| Concern | Where to go |
|---------|-------------|
| Use cases, application orchestration | `src/application/...` |
| Concrete adapters (RAG, DB, LLM, …) | `src/infrastructure/adapters/...` |
| Wiring the graph | `src/composition/...` (`build_backend`, `BackendApplicationContainer`, …) |
| HTTP API | `apps/api/...` |
| Streamlit → backend | `src/frontend_gateway/` — `BackendClient` over **HTTP** (`HttpBackendClient`) or **in-process** (`InProcessBackendClient` + `build_streamlit_backend_application_container` from `streamlit_backend_factory.py`, which calls `src.composition.build_backend` only) |

Guardrails: `tests/architecture/test_deprecated_backend_and_gateway_guardrails.py` (removed package directories absent + **no** imports of `src.backend` or `src.infrastructure.services` under `src/`, `apps/`, `pages/`, `tests/`, and `streamlit_app.py`).

## Canonical layers

| Layer | Path | Responsibility |
|--------|------|----------------|
| **Domain** | `src/domain/` | Entities, value objects, domain services, and **port protocols** (repository, gateway, and similar abstractions). No I/O drivers or framework imports. |
| **Application** | `src/application/` | **Use cases**, application orchestration, application services that coordinate domain logic and ports, command/query DTOs, and **application-level port interfaces** where they complement domain ports. No framework-specific HTTP handling, no Streamlit, no direct SQLite/FAISS/LangChain/FastAPI implementation code. |
| **Infrastructure** | `src/infrastructure/` | **Concrete adapters**: persistence (SQLite, files), vector stores, LLM/embeddings/reranker/OCR, logging repositories, etc. **`src/infrastructure/adapters/`** holds primary runtime implementations of ports. |
| **Composition** | `src/composition/` | Wires adapters to use cases and exposes `BackendComposition` / `BackendApplicationContainer`. No Streamlit or `apps`. |
| **Delivery — HTTP** | `apps/api/` | FastAPI routers, Pydantic schemas, dependency injection only. Resolves use cases from the composition container; does not import concrete adapters. |
| **Delivery — UI** | `pages/`, `src/ui/` | Streamlit UI; talks to backends via `src.frontend_gateway` (`BackendClient`), not via domain or infrastructure. |
| **Gateway** | `src/frontend_gateway/` | Protocol, HTTP and in-process clients, Streamlit session glue. Must not import `src.infrastructure`. |
| **Auth** | `src/auth/` | Shared authentication helpers used by API and Streamlit-oriented flows. |

## Allowed dependencies (summary)

- **Domain** → `src.core` only from outer layers (shared config/exceptions as already allowed by tests); **no** `src.application`, `src.infrastructure`, `apps`, Streamlit, FastAPI, LangChain, `sqlite3`.
- **Application** → `src.domain`, `src.core`, and (for HTTP stub factories only) `src.frontend_gateway` where needed — **no** `src.infrastructure` imports. Use cases under `src/application/use_cases/` must not import `src.frontend_gateway`. Wire concrete adapters in `src/composition/`.
- **Infrastructure (non-adapter)** → no `src.application`, no `streamlit`, no `apps`.
- **Infrastructure adapters** → may import `src.application` (use cases/DTOs) where an adapter deliberately orchestrates around a use case; must not host **cross–use-case** application workflow.
- **Composition** → application, domain, infrastructure, auth; no Streamlit/`apps`.
- **apps/api** → dependencies container, use cases, schemas; **no** `src.infrastructure`, `src.ui`, Streamlit.
- **pages / src/ui** → `streamlit`, `src.frontend_gateway`, `src.auth` as appropriate; **no** `src.domain`, `src.infrastructure`, `src.composition`, `apps.api`.

## Forbidden dependencies (high-signal)

- **Removed packages:** `src.backend`, `src.services`, **`src.adapters`**, **`src.infrastructure.services`** — do not reintroduce; concrete adapters live under `src/infrastructure/adapters/`, orchestration under `src/application/`.
- **Routers** must not import `src.infrastructure` (any submodule).
- **Streamlit** must not import `src.infrastructure` or `src.composition` directly.
- **Domain** must not import LangChain, SQLite drivers, or FastAPI.

## Naming conventions

- **Use cases:** `*UseCase` in `src/application/use_cases/...`, one primary public operation (`execute` or a domain-verbed method).
- **Ports:** `*Port` protocols in `src/domain/ports/` (or `src/domain/shared/`) unless an application-only abstraction is intentionally kept in `src/application/`.
- **Concrete adapters:** `*Service`, `*Repository`, `*Adapter` under `src/infrastructure/adapters/` (or `persistence/` / `vectorstores/` when not folded into `adapters` yet).
- **DTOs:** colocated with the use case package or under `application/.../dtos`.

## Migration rules for contributors

1. **New feature:** define or reuse a port in domain (or application if strictly delivery-agnostic but not domain-core); implement it in `src/infrastructure/adapters` (or existing persistence/vector subpackages); wire in `src/composition/`.
2. **No new compatibility re-export modules** unless a test explicitly requires a temporary alias — prefer updating imports.
3. **Orchestration** that sequences multiple collaborators for an application workflow belongs in **application** (use case or small application service), not in infrastructure, unless it is purely technical (e.g. connection pooling).
4. **FastAPI-specific** code stays in `apps/api/`; **Streamlit-specific** code stays in `pages/` and `src/ui/`.

## Audit snapshot (this change set)

| Finding | Action |
|---------|--------|
| Retrieval preset/merge/validate logic in `RetrievalSettingsService` | **Moved** to `src/application/settings/retrieval_settings_tuner.py`; infrastructure keeps a thin subclass for composition typing. |
| Streamlit `ChatService` under `infrastructure/adapters/chat` | **Moved** to `src/frontend_gateway/streamlit_chat_transcript.py`; composition imports it from the gateway. |
| LangChain `Document` in ingestion / JSON wire | **Removed** from application; duck-typed summaries and document-like JSON normalization. |
| `src/infrastructure/services/` | **Already absent** from the tree (logic lives in `src/infrastructure/adapters/` and `src/application/`). **Guard tests** prevent the package or imports from returning. |
| SQLite port implementations lived under `src/adapters/sqlite/` | **Moved** to `src/infrastructure/adapters/sqlite/`; `src/adapters/` removed. |
| `failure_analysis_service.py` only re-exported domain | **Removed**; callers import `FailureAnalysisService` from `src.domain.benchmark_failure_analysis`. |
| `src/infrastructure/persistence/sqlite/asset_repository.py` | Kept as a thin **forwarding** module to the new adapter path (existing imports preserved). |

## Remaining migrations (entangled / larger refactors)

These are **documented** as follow-up; not moved in this pass to avoid risky rewires:

- **`PipelineAssemblyService`** (`src/infrastructure/adapters/rag/pipeline_assembly_service.py`) — coordinates many RAG adapters; ideal home is an application-layer pipeline orchestrator behind narrow ports, with adapters injected from composition.
- **Pipeline assembly** and other RAG orchestration still concentrated in some infrastructure adapter modules — further extraction behind application ports as needed.
- **`EvaluationService`** and similar **façades** in infrastructure — acceptable as adapter bundles while use cases own orchestration; further split can move pure orchestration into application and leave thin delegating adapters.

## Tests

Boundary enforcement: `pytest tests/architecture -q` (includes `test_application_orchestration_purity` for application/use-case purity and router persistence guards). Full suite: `pytest` from repo root.
