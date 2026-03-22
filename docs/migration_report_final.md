# Final migration report — Clean Architecture (orchestration)

## Executive summary

RAGCraft was refactored so that **RAG orchestration lives in the application layer** (`src/application/use_cases/chat/` and `orchestration/`), **composition only wires** services and use cases, and **infrastructure provides technical adapters** behind ports. FastAPI and the Streamlit-facing **`BackendClient`** both resolve **the same use cases** from **`BackendApplicationContainer`**.

The repository **qualifies as a practical Clean Architecture implementation** for the RAG path: clear layer boundaries, enforced by tests, with a few **documented trade-offs** (retrieval-stage sequencing inside `SummaryRecallService`, some concrete adapter injection, legacy eval helpers).

---

## What was removed

- **`src/infrastructure/adapters/rag/rag_service.py`** (orchestration façade) — **gone**; no replacement façade in infrastructure.
- **`src/infrastructure/adapters/rag/pipeline_assembly_service.py`** — **gone**; post-recall sequencing moved to **`assemble_pipeline_from_recall`** + **`PostRecallStagePorts`** adapters.
- **Legacy packages** — **`src/backend`**, **`src/adapters`**, **`src/infrastructure/services`** — must not exist (guardrail tests).
- **Obsolete docs** — prior **`docs/migration/*`** and **`docs/architecture/*`** narratives were **deleted** and replaced by this doc set (single source under **`docs/`**).

---

## What was moved into application

- **Post–summary-recall pipeline assembly order** — `src/application/use_cases/chat/orchestration/assemble_pipeline_from_recall.py`.
- **Section expansion corpus policy** — `section_expansion_corpus.py`.
- **`ApplicationPipelineAssembly`** — implements **`PipelineAssemblyPort`** by delegating to `assemble_pipeline_from_recall`.
- **Chat use case bundle exposure** — `BackendApplicationContainer.chat_rag_use_cases` (public memoized bundle) plus `chat_*_use_case` accessors.
- **Ports** for post-recall stages — `src/application/use_cases/chat/orchestration/ports.py` (includes **`PostRecallStagePorts`**).
- **Domain DTO** — `SectionExpansionPoolResult` in `src/domain/pipeline_payloads.py` for expansion stage output.

---

## What remains in infrastructure and why

| Area | Why it stays |
|------|----------------|
| **`SummaryRecallService`** | Implements **`SummaryRecallStagePort`**; holds query rewrite, hybrid/RRF, and related retrieval **sequencing**. Further splitting would be a separate refactor. |
| **`post_recall_stage_adapters.py`** | Thin wrappers around rerank, prompt build, docstore, etc. — **technical** steps only; order is in application. |
| **`AnswerGenerationService`** | LLM invocation; injected into ask / generate use cases. |
| **SQLite, FAISS, Unstructured, evaluation row helpers** | Persistence and model I/O. |
| **`MemoryChatTranscript`** (infrastructure) | Default **`ChatTranscriptPort`** for **`build_backend_composition()`** without Streamlit. |
| **`ManualEvaluationService.evaluate_question`** (legacy) | Still sequences via **`BackendClient`**; docstring points to **`RunManualEvaluationUseCase`** for new wiring. |

---

## Final orchestration ownership

| Layer | Owns |
|--------|------|
| **Domain** | Types, ports, no framework |
| **Application** | Use cases, RAG **post-recall** order, evaluation **use case** flows, policies |
| **Composition** | Graph construction, **`chat_rag_wiring`**, **`post_recall_stage_ports_from_services`**, Streamlit transcript override in **`streamlit_backend_factory`** |
| **Infrastructure** | Adapter implementations, retrieval **implementation** inside `SummaryRecallService` |
| **`apps/api`** | HTTP mapping → use cases |
| **`frontend_gateway`** | **`BackendClient`** implementations only |

---

## Final known limitations / acceptable trade-offs

1. **Summary recall sequencing** is still **large and infrastructure-local** — acceptable as long as the port surface stays stable.
2. **Two copies of `MemoryChatTranscript`** (application `frontend_support` vs infrastructure `adapters/chat_transcript`) — keeps **application** free of **infrastructure** imports for HTTP stubs.
3. **`X-User-Id`** header trust — not replaced by OAuth/JWT in this codebase.
4. **Some use cases** still take **concrete** services (e.g. answer generation) where a narrower port could be introduced later.
5. **`test_chat_rag_wiring.py` previously registered a stub `hybrid_retrieval_service` in `sys.modules`**, which made `test_lexical_search_restricts_bm25_corpus` order-dependent. That stub was **removed** so the real `HybridRetrievalService` loads; the suite is stable again.

---

## Remaining debt (if any)

- Narrow **`SummaryRecallService`** behind smaller ports or move policy-heavy steps toward application helpers.
- Migrate remaining **`ManualEvaluationService.evaluate_question`** call sites to **`RunManualEvaluationUseCase`** and remove duplicate sequencing.
- Replace **`X-User-Id`** with verified principals when product requires it.
- Optionally introduce **`AnswerGenerationPort`** and inject a single adapter implementation.

---

## Recommended next steps after migration

1. Keep **`pytest tests/architecture`** in CI on every change touching `src/` or `apps/api`.
2. When touching RAG, update **`docs/rag_orchestration.md`** if entrypoints or ports change.
3. Prefer **new behavior** as new or extended **use cases** rather than new infrastructure façades.
4. If splitting recall further, add **architecture tests** that pin the new boundaries.

---

## Repository tree (main architectural folders)

```text
apps/api/                    # FastAPI app, routers, dependencies, schemas
src/
  auth/                      # Auth helpers
  composition/               # backend_composition, application_container, chat_rag_wiring, wiring
  core/                      # config, paths, errors
  domain/                    # entities, ports, pipeline payloads
  application/
    use_cases/               # feature use cases (chat, evaluation, ingestion, projects, …)
    chat/policies/           # pure RAG helpers
    frontend_support/        # HTTP client stubs, memory_chat_transcript
    http/                    # wire helpers
  infrastructure/
    adapters/                # rag, sqlite, evaluation, workspace, chat_transcript, …
    persistence/
    vectorstores/
    caching/
    logging/
  frontend_gateway/          # BackendClient, HTTP/in-process, Streamlit transcript, factory
pages/                       # Streamlit multipage
src/ui/                      # Streamlit widgets
tests/
  architecture/              # boundary and orchestration guardrails
  apps_api/
  application/
  composition/
  integration/
  infrastructure_services/
```

This tree is descriptive; exact file counts change over time.
