# Final orchestration gap analysis (Clean Architecture baseline)

This document freezes the **target design** and inventories **remaining orchestration responsibilities** as of the repository state when it was written. It is derived from the actual modules under `src/`, `apps/api/`, `pages/`, and `src/frontend_gateway/`.

---

## 1. Repository-wide orchestration inventory

### 1.1 Request / transport entrypoints

| Path | Role | Delegates to |
|------|------|----------------|
| `apps/api/routers/chat.py` | HTTP: ask, pipeline inspect, preview summary recall, retrieval compare | `ResolveProjectUseCase` + chat / retrieval use cases; wire payloads in `src/application/http/wire.py` |
| `apps/api/routers/evaluation.py` | HTTP: manual eval, gold QA run, QA dataset CRUD, query logs, benchmark export | Evaluation and query-log use cases |
| `pages/chat.py`, `pages/retrieval_inspector.py`, `src/ui/*` | Streamlit | `BackendClient` only (`src/frontend_gateway/`); no direct RAG adapter imports |
| `src/frontend_gateway/http_client.py` | HTTP `BackendClient` | FastAPI JSON contracts |
| `src/frontend_gateway/in_process.py` | In-process `BackendClient` | `BackendApplicationContainer` use-case properties |

**Alignment:** Transport does not import `src.infrastructure.adapters.rag` (enforced by `tests/architecture/test_orchestration_boundaries.py`).

### 1.2 Use-case entrypoints (canonical RAG)

| Use case | File | Responsibility |
|----------|------|----------------|
| End-to-end ask | `src/application/use_cases/chat/ask_question.py` | `BuildRagPipelineUseCase`-compatible callable → answer → latency merge → optional deferred query log → `RAGResponse` |
| Pipeline build + optional build-time log | `src/application/use_cases/chat/build_rag_pipeline.py` | `run_recall_then_assemble_pipeline` → `PipelineQueryLogEmitter` |
| Pipeline inspect (no answer, no log) | `src/application/use_cases/chat/inspect_rag_pipeline.py` | Same build as above via `partial(..., emit_query_log=False)` |
| Preview recall only | `src/application/use_cases/chat/preview_summary_recall.py` | Summary recall → `SummaryRecallPreviewDTO.to_dict()` |
| Answer from built pipeline | `src/application/use_cases/chat/generate_answer_from_pipeline.py` | `AnswerGenerationPort.execute` |
| Recall → assemble (no logging) | `src/application/use_cases/chat/orchestration/recall_then_assemble_pipeline.py` | Sequences recall port + assembly port |
| Post-recall assembly | `src/application/use_cases/chat/orchestration/assemble_pipeline_from_recall.py` + `post_recall_pipeline_steps.py` | Ordered steps via `PostRecallStagePorts` |
| Manual evaluation | `src/application/use_cases/evaluation/run_manual_evaluation.py` | Resolve project → `execute_rag_inspect_then_answer_for_evaluation` → `ManualEvaluationFromRagPort` |
| Gold QA benchmark run | `src/application/use_cases/evaluation/run_gold_qa_dataset_evaluation.py` | List entries → per-row `execute_rag_inspect_then_answer_for_evaluation` → `GoldQaBenchmarkPort` |
| Benchmark aggregation | `src/application/use_cases/evaluation/benchmark_execution.py` | Row processing, summary, correlations, failure report, explainability |
| Eval pipeline helper | `src/application/use_cases/evaluation/rag_pipeline_orchestration.py` | Inspect + answer + latency merge for evaluation (empty chat history) |
| Retrieval mode comparison | `src/application/use_cases/retrieval/compare_retrieval_modes.py` | Resolve project → twice `InspectRagPipelinePort` via `compare_retrieval_modes_for_project` |

### 1.3 Composition / wiring

| Module | Role |
|--------|------|
| `src/composition/application_container.py` | Memoizes use cases; injects chat RAG bundle, evaluation, query log; **no multi-step RAG sequencing** except chain invalidation admin |
| `src/composition/chat_rag_wiring.py` | Builds `SummaryRecallAdapter`, `PostRecallStageServices`, `ApplicationPipelineAssembly`, `BuildRagPipelineUseCase`, `AskQuestionUseCase`, etc. |
| `src/composition/backend_composition.py` | Service graph: vectorstore, docstore, `QueryLogService`, `EvaluationService`, … |

### 1.4 Summary-recall stage (current)

**Single port:** `SummaryRecallStagePort.summary_recall_stage` → implemented by `src/infrastructure/adapters/rag/summary_recall_adapter.py` (`SummaryRecallAdapter`).

**Inside the adapter today:** merge retrieval settings (via `RetrievalSettingsService` / `RetrievalSettingsTuner`), query rewrite, intent classification, table-QA gating, adaptive vs fixed retrieval strategy, FAISS recall, optional BM25 + asset listing, RRF-style summary merge (`merge_summary_documents_weighted_rrf`), assembly of `SummaryRecallResult`.

**Application touchpoints:** `summary_recall_from_request.py` builds `RAGPipelineQueryContext` and calls the port; domain helpers used from adapter (`filter_summary_documents_by_filters`, `vector_search_fetch_k`, merge policy).

### 1.5 Post-recall pipeline assembly

Owned by application: `assemble_pipeline_from_recall.py` orchestrates `post_recall_pipeline_steps.py` (hydration → section expansion → rerank → compression → prompt assembly → confidence). Technical work behind `PostRecallStagePorts` adapters in `src/infrastructure/adapters/rag/post_recall_stage_adapters.py`.

### 1.6 Answer generation

| Layer | File |
|-------|------|
| Port | `src/domain/ports/answer_generation_port.py` |
| Adapter | `src/infrastructure/adapters/rag/answer_generation_service.py` → `LLMAnswerGenerator` |

### 1.7 Query logging

| Concern | File |
|---------|------|
| Port | `src/domain/ports` (`QueryLogPort`) |
| Infrastructure | `src/infrastructure/adapters/query_logging/query_log_service.py`, `src/infrastructure/logging/query_log_repository.py` |
| Application | `PipelineQueryLogEmitter` (`orchestration/pipeline_query_log_emitter.py`), `AskQuestionUseCase` deferred path, `build_query_log_ingress_payload`, `log_query_safely` |

Two intentional moments: immediate log after pipeline build (`emit_query_log=True`) vs deferred log after answer (`AskQuestionUseCase` with `QueryLogPort`).

### 1.8 Manual evaluation orchestration

**Canonical:** `RunManualEvaluationUseCase` + `rag_pipeline_orchestration.execute_rag_inspect_then_answer_for_evaluation` + `ManualEvaluationFromRagPort` (implemented by `EvaluationService.build_manual_evaluation_result`).

**Parallel path:** `ManualEvaluationService.evaluate_question` in `src/infrastructure/adapters/evaluation/manual_evaluation_service.py` duplicates inspect + generate answer + latency merge (same sequencing as `rag_pipeline_orchestration.py`) for `BackendClient` call sites, then fabricates a dict-shaped `pipeline_runner` to reuse gold-QA benchmark machinery.

### 1.9 Gold-QA evaluation orchestration

**Canonical:** `RunGoldQaDatasetEvaluationUseCase` closes over `execute_rag_inspect_then_answer_for_evaluation` and passes `pipeline_runner` into `GoldQaBenchmarkPort.evaluate_gold_qa_dataset`.

**Port implementation:** `EvaluationService.evaluate_gold_qa_dataset` forwards to `BenchmarkExecutionUseCase`.

**Legacy hook:** `BenchmarkExecutionUseCase` coerces `pipeline_runner` results via `_coerce_gold_qa_runner_result` to accept either `RagInspectAnswerRun` or a **dict** (still used by `manual_evaluation_service` and some tests).

---

## 2. Bucketed inventory of remaining issues

### 2.1 Still in application and should stay there

- `BuildRagPipelineUseCase`, `AskQuestionUseCase`, `InspectRagPipelineUseCase`, `PreviewSummaryRecallUseCase`, `GenerateAnswerFromPipelineUseCase`
- `run_recall_then_assemble_pipeline`, `assemble_pipeline_from_recall`, `post_recall_pipeline_steps`
- `execute_rag_inspect_then_answer_for_evaluation`, `RunManualEvaluationUseCase`, `RunGoldQaDatasetEvaluationUseCase`, `BenchmarkExecutionUseCase`
- `CompareRetrievalModesUseCase` and `retrieval_mode_comparison` helpers
- `RetrievalSettingsTuner` (`src/application/settings/retrieval_settings_tuner.py`) — preset/merge/validation without infrastructure imports
- `PipelineQueryLogEmitter` and query-log payload builders under `src/application/common/`

### 2.2 Currently in infrastructure but should become a port, use-case collaborator, or composition-only wiring

| Issue | Current location | Target |
|-------|------------------|--------|
| **Summary-recall stage mixes application-order policy with I/O** | `SummaryRecallAdapter` | **Split** (see §4): application-owned step list or helper module; thin adapters for rewrite, vector search, BM25, intent, adaptive strategy |
| **Gold-QA + manual scoring façade** | `EvaluationService` bundles `BenchmarkExecutionUseCase` construction, implements `GoldQaBenchmarkPort` + `ManualEvaluationFromRagPort`, exposes many metric helpers | **Move** benchmark use-case wiring to `BackendApplicationContainer` (or a dedicated `evaluation_wiring` module); keep `EvaluationService` as **narrow adapter(s)** implementing domain ports, or **replace** with separate classes per port |
| **Row-shaped dict contract for benchmark rows** | `_coerce_gold_qa_runner_result` + `manual_evaluation_service` synthetic dict runners | **Unify** on `RagInspectAnswerRun` at the port boundary; **delete** dict branch once call sites updated |

### 2.3 Currently duplicated and should be unified

| Duplication | Files | Action |
|-------------|-------|--------|
| Inspect + answer + latency merge | `rag_pipeline_orchestration.py` vs `ManualEvaluationService.evaluate_question` (lines ~442–469) | **Replace** inline sequence in `manual_evaluation_service.py` with a call to the same application helper (via injected use case or shared function already used by `RunManualEvaluationUseCase`), or require HTTP/in-process clients to use `RunManualEvaluationUseCase` only and **delete** the duplicate path |
| Manual eval via fake gold-QA run | `manual_evaluation_result_from_rag_outputs` builds a one-entry dataset + dict `pipeline_runner` | **Replace** with direct `ManualEvaluationFromRagPort` implementation that does not route through `evaluate_gold_qa_dataset` |

### 2.4 Currently legacy and should be removed (when preconditions met)

| Item | File(s) | Precondition |
|------|---------|--------------|
| Dict return type for `pipeline_runner` | `GoldQaBenchmarkPort`, `benchmark_execution._coerce_gold_qa_runner_result`, `frontend_gateway/protocol.py`, tests | All runners return `RagInspectAnswerRun` |
| `RAGPipelineQueryContext.from_legacy` naming | `src/application/common/pipeline_query_context.py` | **Rename** to `from_chat_request` (or similar) — no behavior change |
| `SummaryRecallPreviewDTO` “legacy dict contract” wording / shape | `preview_summary_recall.py`, `summary_recall_preview.py` | Optionally **replace** `dict` return with a stable DTO / wire type end-to-end; until then **keep** but stop calling it legacy in docstrings after wire is canonical |
| `ManualEvaluationService.evaluate_question` | `manual_evaluation_service.py` | **Delete** after Streamlit/tests use `RunManualEvaluationUseCase` or a thin gateway that delegates to it |

### 2.5 Acceptable as technical detail; remain in infrastructure

- `VectorStoreService`, `HybridRetrievalService`, `QueryRewriteService`, `QueryIntentService`, `AdaptiveRetrievalService`, `DocStoreService`, `TableQAService`
- `post_recall_stage_adapters.py` (adapter pattern; must not import use cases — tested)
- `AnswerGenerationService`, `LLMAnswerGenerator`
- `QueryLogService` persistence and `import_legacy_file_logs` (explicit migration utility)
- `MultimodalOrchestrationService` (hint text for prompt; name is “orchestration” but scope is prompt augmentation, not RAG sequencing)
- `summary_recall_document_from_langchain` bridge in `src/infrastructure/adapters/summary_recall_document_adapter.py`

---

## 3. Target orchestration map (canonical owner by responsibility)

```text
HTTP / Streamlit
  → apps/api/routers/*.py | pages/*.py + BackendClient
       → ResolveProjectUseCase (where applicable)
       → Chat / evaluation use cases (below)

End-to-end ask
  → ask_question.py
       → build_rag_pipeline.py → recall_then_assemble_pipeline.py
            → summary_recall_from_request.py → SummaryRecallStagePort
            → application_pipeline_assembly.py → assemble_pipeline_from_recall.py
       → AnswerGenerationPort
       → QueryLogPort (deferred)

Pipeline inspect / compare / preview
  → inspect_rag_pipeline.py | compare_retrieval_modes.py | preview_summary_recall.py
       → (inspect/preview) same recall/assembly chain as above

Evaluation inspect + answer
  → rag_pipeline_orchestration.py
       → InspectRagPipelinePort + GenerateAnswerFromPipelinePort

Gold QA benchmark
  → run_gold_qa_dataset_evaluation.py → GoldQaBenchmarkPort
  → benchmark_execution.py (+ domain ports for row/summary/correlation/failure/explain/debug)

Query logging
  → pipeline_query_log_emitter.py (build-time) | ask_question.py (post-answer)

Composition
  → application_container.py + chat_rag_wiring.py + backend_composition.py
```

---

## 4. Target ownership table

| Responsibility | Current file(s) | Target file(s) | Action |
|----------------|-----------------|----------------|--------|
| HTTP chat routes | `apps/api/routers/chat.py` | same | keep |
| Chat wire DTOs | `src/application/http/wire.py` | same | keep |
| Ask question | `ask_question.py` | same | keep |
| Build pipeline | `build_rag_pipeline.py` | same | keep |
| Recall then assemble | `recall_then_assemble_pipeline.py` | same | keep |
| Summary recall from request kwargs | `summary_recall_from_request.py`, `pipeline_query_context.py` | same; rename factory | rename (`from_legacy` → `from_chat_request`) |
| Summary recall port impl | `summary_recall_adapter.py` | `summary_recall_adapter.py` + new `application/.../summary_recall_stage.py` (or split port methods) | split |
| Retrieval settings merge / presets | `retrieval_settings_tuner.py`, `retrieval_settings_service.py` | same | keep |
| Post-recall steps | `assemble_pipeline_from_recall.py`, `post_recall_pipeline_steps.py` | same | keep |
| Post-recall adapters | `post_recall_stage_adapters.py` | same | keep |
| Inspect pipeline (thin) | `inspect_rag_pipeline.py` | same or fold into `build_rag_pipeline.py` with flags | keep (or merge later) |
| Preview summary recall | `preview_summary_recall.py`, `summary_recall_preview.py` | same; optional wire DTO | keep |
| Generate answer from pipeline | `generate_answer_from_pipeline.py` | same | keep |
| Answer generation I/O | `answer_generation_service.py` | same | keep |
| Pipeline build query log | `pipeline_query_log_emitter.py` | same | keep |
| Deferred ask query log | `ask_question.py`, `safe_query_log.py`, `build_query_log_ingress_payload` | same | keep |
| Eval inspect+answer | `rag_pipeline_orchestration.py` | same | keep |
| Manual evaluation | `run_manual_evaluation.py` | same | keep |
| Gold QA run | `run_gold_qa_dataset_evaluation.py` | same | keep |
| Benchmark execution | `benchmark_execution.py` | same | keep |
| Dict coercion for benchmark rows | `benchmark_execution.py` | remove branch | delete (after callers fixed) |
| Evaluation façade + port impl | `evaluation_service.py` | `application_container.py` wires `BenchmarkExecutionUseCase`; slim adapter module(s) | split / move |
| Duplicate eval orchestration in manual service | `manual_evaluation_service.py` | delegate to `rag_pipeline_orchestration` or use case | delete / replace |
| Retrieval compare | `compare_retrieval_modes.py`, `retrieval_mode_comparison.py` | same | keep |
| Chat RAG wiring | `chat_rag_wiring.py` | same (+ any new summary-recall adapters) | keep |
| Container façade | `application_container.py` | same | keep |
| Port re-exports | `src/application/chat/ports.py` | same or fold imports to `orchestration/ports.py` only | keep |

---

## 5. Façades, convenience wrappers, legacy compatibility layers

| File / symbol | Kind | Verdict |
|---------------|------|---------|
| `BackendApplicationContainer` | Composition façade (typed access to use cases) | **Keep** — not RAG sequencing |
| `EvaluationService` | Infrastructure façade implementing two domain ports + benchmark delegate | **Split / thin** — orchestration wiring should live in composition/application |
| `InspectRagPipelineUseCase` | Thin wrapper over `partial(BuildRagPipelineUseCase.execute, emit_query_log=False)` | **Keep** for intent, or **merge** into build use case with a flag |
| `GenerateAnswerFromPipelineUseCase` | Thin wrapper over `AnswerGenerationPort` | **Keep** (stable evaluation entry) |
| `ApplicationPipelineAssembly` | One-method delegate to `assemble_pipeline_from_recall` | **Keep** (implements `PipelineAssemblyPort`) |
| `src/application/chat/ports.py` | Re-export barrel | **Delete** when no remaining imports depend on it, or **keep** as stable import path |
| `RAGPipelineQueryContext.from_legacy` | Name encodes old API | **Rename** |
| `PreviewSummaryRecallUseCase` + `to_dict()` | UI/API dict contract | **Keep** until wire models replace dicts everywhere |
| `BenchmarkExecutionUseCase._coerce_gold_qa_runner_result` | dict compatibility | **Remove** after runner contract is `RagInspectAnswerRun` only |
| `ManualEvaluationService.evaluate_question` | Duplicate orchestration + benchmark hack | **Remove** after migration of callers |
| `README.github.md` “Application Facade (RAGCraftApp)” diagram | Documentation drift | **Delete or rewrite** — not code, but misleading vs `BackendApplicationContainer` |

---

## 6. Summary-recall stage: monolithic?

**Yes.** The port is a single method whose implementation in `SummaryRecallAdapter` still owns the **full ordered policy** (settings → rewrite → intent → table flag → adaptive strategy → vector + optional BM25 → merge → `SummaryRecallResult`).

### 6.1 Extract to pure domain policy

- **Already in domain:** `merge_summary_documents_weighted_rrf`, `filter_summary_documents_by_filters`, `vector_search_fetch_k`, `RetrievalStrategy` / `QueryIntent` types.
- **Move or duplicate into domain (if not already):** explicit “execution plan” from `RetrievalSettings` + `QueryIntent` + override flags when **adaptive is off** (today `_execution_plan_for_retrieval` in adapter). Keeps branching testable without FAISS/BM25.

### 6.2 Application orchestration helper / use case

- New module e.g. `src/application/use_cases/chat/orchestration/summary_recall_stage_flow.py` (name illustrative) that sequences:
  1. Resolve effective `RetrievalSettings` (call existing `RetrievalSettingsTuner` APIs).
  2. Rewrite + classify (via **narrow ports** or existing services behind ports).
  3. Choose strategy (domain policy + optional `AdaptiveRetrievalPort`).
  4. Call **RecallVectorPort** / **RecallLexicalPort** / **MergeSummariesPort** (or equivalent split of `SummaryRecallStagePort`).

Alternatively, expand `SummaryRecallStagePort` into multiple protocol methods without changing outer use-case signatures, implemented by the same adapter class file split into cohesive units.

### 6.3 Infrastructure adapter / technical implementation

- **Keep in infrastructure:** embedding search, BM25 over materialized asset text, LLM query rewrite, intent classifier model, loading project assets for BM25, LangChain document conversion, logging timings.
- **Target files:** slim `summary_recall_adapter.py` (or package `summary_recall/`) with focused collaborators; no high-level `if/else` strategy blocks left as the only readable spec of the pipeline.

---

## 7. Must fix now (blocking “100% clean” orchestration clarity)

1. **Split summary-recall policy from I/O** — `SummaryRecallAdapter` (`summary_recall_adapter.py`) remains the largest orchestration blob outside application; extract domain + application sequencing per §6.
2. **Dismantle `EvaluationService` as a dual-purpose façade** — wire `BenchmarkExecutionUseCase` in `application_container.py` (or sibling wiring module); implement `GoldQaBenchmarkPort` / `ManualEvaluationFromRagPort` with classes that do not also own unrelated metric helper surface.
3. **Remove duplicate inspect+answer+latency logic** — `ManualEvaluationService.evaluate_question` must not reimplement `rag_pipeline_orchestration.execute_rag_inspect_then_answer_for_evaluation`.
4. **Narrow gold-QA runner contract** — eliminate dict `pipeline_runner` results: update `manual_evaluation_result_from_rag_outputs` path to use `RagInspectAnswerRun`, then delete `_coerce_gold_qa_runner_result` dict branch and update `GoldQaBenchmarkPort` typing.

---

## 8. Can stay as technical debt (short, bounded)

| Item | Rationale |
|------|-----------|
| `InspectRagPipelineUseCase` vs `BuildRagPipelineUseCase` duplication | One-line partial binding; acceptable until a single “build pipeline” use case exposes `emit_query_log` explicitly |
| `import_legacy_file_logs` on `QueryLogService` | Explicit one-off migration; not on hot path |
| `README.github.md` outdated diagram | Docs only; fix when touching docs |
| `MultimodalOrchestrationService` naming | Confusing word “orchestration”; behavior is prompt hinting — **rename** optional, low risk |
| Architecture line-count ratchets in `test_orchestration_boundaries.py` | Prevents silent growth; not user-facing debt |

---

## 9. Validation

Commands (repository root):

```bash
pytest tests/architecture/ -q
pytest tests/application/chat/ -q
pytest tests/infrastructure_services/test_chat_rag_wiring.py -q
```

**Last validated:** 2025-03-22 — `tests/architecture/`: 43 passed, 3 skipped; `tests/application/chat/`: 14 passed; `tests/infrastructure_services/test_chat_rag_wiring.py`: 10 passed.

---

## 10. Document history

| Date | Change |
|------|--------|
| 2025-03-22 | Initial baseline for final migration step |
