# Final migration report — Clean Architecture & RAG orchestration

This report describes the **end state of the codebase** after the RAG orchestration cleanup (application-owned post-recall sequencing, composition-only wiring, evaluation DTOs, and documentation alignment). It is the canonical “what we have now” summary alongside **`docs/architecture.md`** and **`docs/rag_orchestration.md`**.

---

## 1. Executive summary

RAGCraft’s backend is structured as **ports-and-adapters Clean Architecture**: **domain** holds types and port protocols, **application** owns use cases and RAG **orchestration helpers**, **infrastructure** supplies technical adapters, **composition** builds the graph, and **delivery** (FastAPI `apps/api/`, Streamlit via **`BackendClient`**) stays thin.

The legacy **`RAGService` / `rag_service.py`** orchestration façade is **gone**. RAG **post–summary-recall** ordering lives in **`assemble_pipeline_from_recall`** and **`post_recall_pipeline_steps`**, with **`PostRecallStagePorts`** delegating single technical steps to infrastructure. **Query logging** is coordinated from **application** use cases and helpers, not from vectorstore/docstore/rerank code.

**Gold QA and manual evaluation** reuse **`InspectRagPipelinePort`** + **`GenerateAnswerFromPipelinePort`** through **`execute_rag_inspect_then_answer_for_evaluation`** (`rag_pipeline_orchestration.py`), returning the domain DTO **`RagInspectAnswerRun`** (with backward-compatible dict coercion in **`BenchmarkExecutionUseCase`**).

The result is a **practical** Clean Architecture: boundaries are **test-guarded**, but a few **pragmatic compromises** remain (notably retrieval-stage sequencing inside **`SummaryRecallAdapter`** and some infrastructure adapters that still import application DTOs or helpers).

---

## 2. Architecture target reached

| Target | Status |
|--------|--------|
| No monolithic RAG façade in infrastructure | **Met** — `rag_service.py` removed; **`test_no_rag_service_facade.py`** |
| Use cases as scenario owners | **Met** — chat, eval, ingestion, projects, settings |
| Post-recall pipeline order in application | **Met** — `assemble_pipeline_from_recall` + `post_recall_pipeline_steps.py` |
| Composition root only wires concrete types | **Met** — `chat_rag_wiring.py`, `application_container.py` |
| API routers use `Depends` → container → use case | **Met** — **`test_fastapi_migration_guardrails.py`** |
| Application does not import infrastructure | **Met** — layer tests |
| Gateway does not import infrastructure | **Met** — `frontend_support` stubs for HTTP mode |

---

## 3. What was removed

| Removed | Notes |
|---------|--------|
| **`src/infrastructure/adapters/rag/rag_service.py`** | Orchestration façade; replaced by use cases + wiring |
| **`src/infrastructure/adapters/rag/pipeline_assembly_service.py`** | Post-recall assembly moved to application |
| **`src/backend/`**, **`src/adapters/`**, **`src/infrastructure/services/`** | Legacy trees; must not reappear (guardrail tests) |
| **`src/services/`** as an orchestration package | Same |
| **`rag_answer_for_eval.py`** | Replaced by **`rag_pipeline_orchestration.py`** + **`RagInspectAnswerRun`** |
| Older scattered **`docs/migration/*`** narratives | Superseded by this **`docs/`** set |

---

## 4. What was moved / introduced

| Item | Location / role |
|------|------------------|
| Post–summary-recall **step order** | `orchestration/assemble_pipeline_from_recall.py`, `post_recall_pipeline_steps.py` |
| **Shared summary-recall invocation** | `orchestration/summary_recall_from_request.py` (build + preview) |
| **Weighted RRF merge** (domain policy) | `src/domain/summary_document_fusion.py` (was under `application/chat/policies`) |
| **Summary recall implementation** | Renamed: `summary_recall_adapter.py`, class **`SummaryRecallAdapter`** |
| **Inspect pipeline wiring** | `InspectRagPipelineUseCase` takes `build_pipeline`; composition uses **`partial(..., emit_query_log=False)`** |
| **Eval inspect+answer orchestration** | `evaluation/rag_pipeline_orchestration.py` → **`execute_rag_inspect_then_answer_for_evaluation`** |
| **Eval run payload** | `src/domain/rag_inspect_answer_run.py` |
| **Ports for eval ↔ chat decoupling** | `pipeline_use_case_ports.py` (`InspectRagPipelinePort`, `GenerateAnswerFromPipelinePort`) |
| **Pipeline-build log hook as port** | `PipelineBuildQueryLogEmitterPort` + `PipelineQueryLogEmitter` |
| **RAG adapter → application import guard** | `test_rag_adapter_application_imports.py` (allowlist: `retrieval_settings_service.py`) |

---

## 5. Final orchestration model

### Chat / RAG (production)

1. **Delivery:** `apps/api/routers/chat.py` resolves **`AskQuestionUseCase`**, **`InspectRagPipelineUseCase`**, **`PreviewSummaryRecallUseCase`** via **`BackendApplicationContainer`**.
2. **Ask:** **`AskQuestionUseCase`** → injected **`build_pipeline`** (**`BuildRagPipelineUseCase.execute`**) → **`AnswerGenerationPort`** → optional deferred **`QueryLogPort`** via **`log_query_safely`** / **`build_query_log_ingress_payload`**.
3. **Build pipeline:** **`BuildRagPipelineUseCase`** → **`run_recall_then_assemble_pipeline`** → **`PipelineBuildQueryLogEmitterPort`** when `emit_query_log=True`.
4. **Recall + assemble:** **`SummaryRecallStagePort`** (adapter) then **`PipelineAssemblyPort`** (**`ApplicationPipelineAssembly`** → **`assemble_pipeline_from_recall`**), stepping through **`PostRecallStagePorts`**.
5. **Adapters:** `infrastructure/adapters/rag/*` implement FAISS, docstore, rerank, LLM, etc., without owning full pipeline order or query logging.

### Evaluation (manual + gold QA)

- **`RunManualEvaluationUseCase`** / **`RunGoldQaDatasetEvaluationUseCase`** call **`execute_rag_inspect_then_answer_for_evaluation`** (ports only, no chat query log).
- **`BenchmarkExecutionUseCase`** accepts **`RagInspectAnswerRun`** or legacy **dict** per row (**`_coerce_gold_qa_runner_result`**).

### Composition

- **`chat_rag_wiring.build_rag_retrieval_subgraph`** + **`build_chat_rag_use_cases`** construct **`SummaryRecallAdapter`**, **`ApplicationPipelineAssembly`**, post-recall port bundle, and chat use cases.

---

## 6. Remaining acceptable compromises

1. **`SummaryRecallAdapter`** still sequences query rewrite, intent, adaptive strategy, hybrid recall, and merge — behind **`SummaryRecallStagePort`**. Domain policy for RRF is **`summary_document_fusion`**; further splitting would be a separate refactor.
2. **`retrieval_settings_service.py`** subclasses **`RetrievalSettingsTuner`** from application — intentional composition-facing bridge; allowlisted in RAG import tests.
3. **Some non-RAG adapters** (evaluation export, query log payload types, row evaluation metrics) import **application** modules for DTOs/helpers — accepted until those types move to domain or dedicated shared modules.
4. **Duplicate `MemoryChatTranscript`** (infrastructure default vs **`application/frontend_support`** for HTTP stubs) — keeps application free of infrastructure imports in the gateway path.
5. **`X-User-Id`** trust model — unchanged; not a substitute for verified OAuth/JWT.

---

## 7. Remaining technical debt (honest list)

- Narrow **`SummaryRecallAdapter`** with smaller ports if retrieval-stage steps should move further toward application.
- Reduce **infrastructure → application** imports in evaluation/query-log paths by lifting shared types to **domain** or thin shared packages.
- Migrate any remaining legacy **`ManualEvaluationService.evaluate_question`** call sites fully to **`RunManualEvaluationUseCase`** if duplicates still exist.
- Replace trust-header auth with verified principals when the product requires it.
- Optional: rename remaining `*service.py` files under **`infrastructure/adapters/rag/`** to `*adapter.py` for naming consistency (large churn).

---

## 8. Tests and architecture guards

Run: **`pytest tests/architecture -q`**

| Concern | Module(s) |
|---------|-----------|
| Domain / application / infrastructure import directions | **`test_layer_boundaries.py`**, **`test_application_orchestration_purity.py`** |
| Legacy packages & paths | **`test_deprecated_backend_and_gateway_guardrails.py`** |
| FastAPI surface | **`test_fastapi_migration_guardrails.py`** |
| Composition ↔ gateway | **`test_composition_import_boundaries.py`** |
| RAG façade absent; adapters don’t import chat use case classes | **`test_no_rag_service_facade.py`** |
| Post-recall adapter / assemble pipeline placement | **`test_orchestration_boundaries.py`** |
| RAG adapters must not import `src.application` (except allowlist) | **`test_rag_adapter_application_imports.py`** |
| Streamlit / UI import rules | **`test_streamlit_import_guardrails.py`** |
| Smoke: `build_backend` | **`test_migration_regression_flows.py`** |

See also **`docs/testing_strategy.md`** and **`tests/architecture/README.md`**.

---

## 9. Recommended next steps after migration

1. Keep **`pytest tests/architecture`** in CI for any change under **`src/`**, **`apps/api/`**, **`pages/`**, or **`src/ui/`**.
2. When changing RAG entrypoints or ports, update **`docs/rag_orchestration.md`** in the same PR.
3. Prefer **new behavior** as new or extended **use cases** rather than new infrastructure façades.
4. If splitting **`SummaryRecallAdapter`**, add **architecture tests** that pin the new boundaries.

---

## Repository tree (main architectural folders)

```text
apps/api/                    # FastAPI app, routers, dependencies, schemas
src/
  auth/
  composition/               # backend_composition, application_container, chat_rag_wiring, wiring
  core/
  domain/                    # entities, ports, payloads, summary_document_fusion, rag_inspect_answer_run
  application/
    use_cases/               # chat, evaluation, ingestion, projects, retrieval, settings
    use_cases/chat/orchestration/
    chat/policies/
    frontend_support/
    http/
  infrastructure/
    adapters/                # rag, evaluation, workspace, sqlite, chat_transcript, query_logging, …
    persistence/
    vectorstores/
    caching/
    logging/
  frontend_gateway/
pages/
src/ui/
tests/
  architecture/
  apps_api/
  application/
  composition/
  domain/
  integration/
  infrastructure_services/
```

This tree is descriptive; file counts evolve over time.
