# Clean architecture target (canonical map)

This document is the **normative** layering contract for RAGCraft. It complements the **runtime** overview in [`ARCHITECTURE_TARGET.md`](../../ARCHITECTURE_TARGET.md) at the repo root and the enforced rules in [`tests/architecture/README.md`](../../tests/architecture/README.md).

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
- **Application** → `src.domain`, `src.core`, and — in the **current** codebase — `src.infrastructure.adapters` only (not `src.infrastructure.persistence`, `vectorstores`, `llm`, etc.). *Strategic target:* depend on **ports** only; compose concrete adapters in `src/composition/`.
- **Infrastructure (non-adapter)** → no `src.application`, no `streamlit`, no `apps`.
- **Infrastructure adapters** → may import `src.application` (use cases/DTOs) where an adapter deliberately orchestrates around a use case; must not host **cross–use-case** application workflow.
- **Composition** → application, domain, infrastructure, auth; no Streamlit/`apps`.
- **apps/api** → dependencies container, use cases, schemas; **no** `src.infrastructure`, `src.ui`, Streamlit.
- **pages / src/ui** → `streamlit`, `src.frontend_gateway`, `src.auth` as appropriate; **no** `src.domain`, `src.infrastructure`, `src.composition`, `apps.api`.

## Forbidden dependencies (high-signal)

- **Removed packages:** `src.backend`, `src.services`, **`src.adapters`** — do not reintroduce; implementations live under `src/infrastructure/adapters/`.
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
| SQLite port implementations lived under `src/adapters/sqlite/` | **Moved** to `src/infrastructure/adapters/sqlite/`; `src/adapters/` removed. |
| `failure_analysis_service.py` only re-exported domain | **Removed**; callers import `FailureAnalysisService` from `src.domain.benchmark_failure_analysis`. |
| `src/infrastructure/persistence/sqlite/asset_repository.py` | Kept as a thin **forwarding** module to the new adapter path (existing imports preserved). |

## Remaining migrations (entangled / larger refactors)

These are **documented** as follow-up; not moved in this pass to avoid risky rewires:

- **`PipelineAssemblyService`** (`src/infrastructure/adapters/rag/pipeline_assembly_service.py`) — coordinates many RAG adapters; ideal home is an application-layer pipeline orchestrator behind narrow ports, with adapters injected from composition.
- **Application imports of `src.infrastructure.adapters`** in a few modules (e.g. `frontend_support`, `settings/retrieval_merge_default.py`) — strategic direction is to replace with ports + composition-only wiring.
- **`EvaluationService`** and similar **façades** in infrastructure — acceptable as adapter bundles while use cases own orchestration; further split can move pure orchestration into application and leave thin delegating adapters.

## Tests

Boundary enforcement: `pytest tests/architecture -q`. Full suite: `pytest` from repo root.
