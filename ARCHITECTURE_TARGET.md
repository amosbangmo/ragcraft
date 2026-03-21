# Target architecture (migration)

This document describes the **intended** layout for moving toward a FastAPI API and Clean Architecture. Existing modules are not required to live here yet; the tree is the target destination.

## `apps/api`

HTTP delivery layer: FastAPI app factory, router mounting, and dependency wiring that adapts infrastructure to the application layer. Keeps transport concerns out of `src/`.

## `apps/api/routers`

Route handlers only: parse requests, call application use cases, map results to HTTP responses.

## `apps/api/schemas`

Pydantic (or similar) request/response models and OpenAPI-facing DTOs. No business rules.

## `src/application`

Application services and **use cases**: orchestrate domain logic and ports, enforce workflows, stay framework-agnostic. Depends on `src/domain` and abstractions implemented in `src/infrastructure`.

## `src/application/common`

Cross-cutting application helpers shared by multiple bounded contexts (for example, pagination, correlation IDs, shared command/result types).

## `src/application/*/use_cases`

One folder per capability (`chat`, `ingestion`, `evaluation`, `projects`, `retrieval`): each use case is an explicit entry point for a user or system operation.

## `src/domain`

Core model: entities, value objects, domain events, and invariants. No FastAPI, Streamlit, SQLite, FAISS, or LLM SDK imports.

## `src/domain/chat`, `documents`, `evaluation`, `retrieval`, `shared`

Subdomains and shared kernel: group domain types by bounded context as they are migrated from the flat `src/domain` package.

## `src/infrastructure`

Adapters: implements interfaces defined by application/domain—databases, vector stores, file parsers, LLM clients, external HTTP, etc.

## `src/infrastructure/persistence/sqlite`

SQLite-specific persistence (repositories, migrations, connection handling).

## `src/infrastructure/vectorstores/faiss`

FAISS-backed vector store implementation details.

## `src/infrastructure/llm`

LLM provider clients, prompts as infrastructure, token accounting—anything that talks to model APIs.

## `src/infrastructure/ingestion`

Document loading, chunking, and extraction adapters (alongside or replacing pieces of the current ingestion stack as you migrate).

## `src/infrastructure/web`

Non-FastAPI web helpers if needed (for example, shared middleware concepts); keep FastAPI-specific wiring in `apps/api` when possible.

## `src/interfaces`

Delivery mechanisms other than the HTTP app: CLI, jobs, and **Streamlit**.

## `src/interfaces/streamlit` and `pages`

Streamlit-specific composition and page modules. This is the home for UI wiring as it is decoupled from core use cases.

## Dependency rule (summary)

**Domain** ← **Application** ← **Infrastructure / Interfaces / apps/api**

Dependencies point inward: outer layers depend on inner abstractions, not the reverse.
