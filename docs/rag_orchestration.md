# RAG orchestration

This document describes **how RAG behavior is structured in the current codebase**: which use cases own which flows, where orchestration modules live, and how logging and typed boundaries work.

**Code roots:** orchestration modules under **`api/src/application/orchestration/`**, use cases under **`api/src/application/use_cases/`**, wiring in **`api/src/composition/chat_rag_wiring.py`** and **`evaluation_wiring.py`**, technical steps under **`api/src/infrastructure/rag/`**.

---

## Mode separation (ownership)

| Mode | Use case / function | Pipeline | Answer | Product query log |
|------|---------------------|----------|--------|-------------------|
| **Ask** | **`AskQuestionUseCase`** | Full (via **`BuildRagPipelineUseCase`**) | Yes | Yes, when **`QueryLogPort`** wired (deferred full log; optional build-stage log if port absent) |
| **Inspect** | **`InspectRagPipelineUseCase`** | Full | No | **No** — always **`emit_query_log=False`** |
| **Preview** | **`PreviewSummaryRecallUseCase`** | Recall only | No | **No** — no build port, no emitter |
| **Evaluation** | **`execute_rag_inspect_then_answer_for_evaluation`** + manual / gold-QA use cases | Via **inspect** port | Via **`GenerateAnswerFromPipelinePort`** | **No** — inspect contract |

**Rules:** one canonical evaluation orchestration (**`rag_pipeline_orchestration.py`**); no second inspect+answer path in **`infrastructure.evaluation`** (assembly helpers only). **`api/tests/appli/orchestration/test_rag_mode_contracts.py`** locks logging flags and build-emitter behavior.

---

## Entrypoints

| Entry | Where | Notes |
|-------|--------|------|
| **HTTP chat (ask)** | **`api/src/interfaces/http/routers/chat.py`** → **`AskQuestionUseCase`** via **`dependencies.py`** | Scoped routes require **`Authorization: Bearer`** → **`AuthenticatedPrincipal`**. |
| **In-process Streamlit ask** | **`frontend/src/services/in_process.py`** → container **`chat_ask_question_use_case`** | Same use cases as HTTP; different transport. |
| **Pipeline build** | **`BuildRagPipelineUseCase`** | Used by inspect, comparison, and evaluation paths. |
| **Inspect pipeline** | **`InspectRagPipelineUseCase`** | Uses **`RetrievalPort`**; composition injects the same **`BuildRagPipelineUseCase`** instance; inspect calls **`execute(..., emit_query_log=False)`**. |
| **Preview summary recall** | **`PreviewSummaryRecallUseCase`** | Stops after recall; returns preview DTOs, not a full pipeline. |
| **Answer from built pipeline** | **`GenerateAnswerFromPipelineUseCase`** | LLM answer given an already-built pipeline. |

The object graph is built in **`chat_rag_wiring.py`** and exposed on **`BackendApplicationContainer`** (e.g. **`chat_rag_use_cases`**, **`chat_*_use_case`** properties).

**Import guardrails:** **`test_orchestration_package_import_boundaries.py`** scans **`application/orchestration/{rag,evaluation}`**, **`application/use_cases/evaluation`**, and **`application/rag`** and forbids **`infrastructure`**, FastAPI, Streamlit, LangChain, FAISS, etc., so orchestration stays port-driven.

---

## Flow 1: Product ask (chat)

1. **`AskQuestionUseCase`** — builds the pipeline (via injected **`BuildRagPipelineUseCase`**), generates an answer through **`AnswerGenerationPort`**, then logs via **`QueryLogPort`** when configured (deferred full payload after answer).
2. **`BuildRagPipelineUseCase`** — runs **`run_recall_then_assemble_pipeline`** (see below) and, when **`emit_query_log=True`**, uses **`PipelineQueryLogEmitter`**. RAG infrastructure services do **not** log queries themselves.

---

## Flow 2: Inspect pipeline

- **`InspectRagPipelineUseCase`** — same **`BuildRagPipelineUseCase`** as ask, with **`emit_query_log=False`**. No answer generation on this path.

---

## Flow 3: Preview summary recall

- **`PreviewSummaryRecallUseCase`** — runs summary-recall–related work and returns preview data (**`SummaryRecallPreviewDTO`** and related shapes). Does not run full post-recall assembly or answer generation.

---

## Flow 4: Evaluation (gold QA, manual)

**Single inspect+answer path for evaluation:** **`execute_rag_inspect_then_answer_for_evaluation`** in **`api/src/application/orchestration/evaluation/rag_pipeline_orchestration.py`**.

- Input: **`RagEvaluationPipelineInput`** (**`api/src/application/dto/rag/evaluation_pipeline.py`**).  
- Coordinates **`InspectRagPipelinePort`** and **`GenerateAnswerFromPipelinePort`**; merges latency into **`PipelineBuildResult.latency`** as **`PipelineLatency`**.  
- Output: **`RagInspectAnswerRun`** (**`api/src/domain/rag/rag_inspect_answer_run.py`**); **`as_row_evaluation_input()`** yields **`GoldQaPipelineRowInput`** for **`RowEvaluationService`**.  
- **`BenchmarkExecutionUseCase`** requires each **`pipeline_runner`** result to be a **`RagInspectAnswerRun`** (**`TypeError`** otherwise).  
- **`GoldQaBenchmarkAdapter`** (**`api/src/application/orchestration/evaluation/gold_qa_benchmark_adapter.py`**) implements **`GoldQaBenchmarkPort`** for **`EvaluationService`**, wired from **`evaluation_wiring.py`**.  
- **`api/src/infrastructure/evaluation/manual_evaluation_service.py`** — row/result assembly helpers only; **does not** replace the application orchestration above.  
- **Manual evaluation:** **`RunManualEvaluationUseCase`** is the single application entry for that scenario (see **`test_manual_evaluation_single_orchestrator.py`**).

---

## Orchestration sequence (recall → assembly)

**Coordinator:** **`recall_then_assemble_pipeline.py`** calls **`run_summary_recall_from_chat_request`** then **`PipelineAssemblyPort.build`**.

### Summary-recall stage

1. **`ApplicationSummaryRecallStage`** — **`api/src/application/orchestration/rag/summary_recall_workflow.py`**. Implements **`SummaryRecallStagePort`**: settings merge (**`RetrievalSettingsTuner`**), optional rewrite (**`QueryRewritePort`**), domain policies, **`resolve_summary_recall_execution_plan`**, **`fuse_vector_and_lexical_recalls`**.  
2. **Infrastructure technical adapters** — **`api/src/infrastructure/rag/summary_recall_technical_adapters.py`** (**`QueryRewriteAdapter`**, vector/lexical adapters). Exposed as **`SummaryRecallTechnicalPorts`** from **`chat_rag_wiring.py`**.

### Post-recall assembly

- **`ApplicationPipelineAssembly`** (**`api/src/application/orchestration/rag/application_pipeline_assembly.py`**) implements **`PipelineAssemblyPort`**; **`assemble_pipeline_from_recall`** sequences **`post_recall_pipeline_steps`**.  
- **Infrastructure** — **`api/src/infrastructure/rag/post_recall_stage_adapters.py`** — one thin adapter per **`PostRecallStagePorts`** slot.

---

## Typed boundaries (orchestration ↔ domain)

- **Retrieval overrides:** **`RetrievalSettingsOverrideSpec`** (**`api/src/domain/rag/retrieval_settings_override_spec.py`**) on **`RetrievalPort`**, **`SummaryRecallStagePort`**, **`RAGPipelineQueryContext`**, and chat use cases. FastAPI maps JSON in **`routers/chat.py`**; **`InProcessBackendClient`** maps before calling use cases.  
- **Recall fusion output:** **`VectorLexicalRecallBundle`** (**`api/src/application/rag/dtos/recall_stages.py`**).  
- **Evaluation orchestration input:** **`RagEvaluationPipelineInput`**.  
- **Latency:** **`PipelineLatency`** on **`RagInspectAnswerRun`**, **`RAGResponse`**, and **`RagAnswerWirePayload`** (wire holds the domain type until **`as_json_dict()`** serializes for JSON).

---

## Logging boundaries

- **Ask only:** **`AskQuestionUseCase`** may persist product retrieval/answer logs via **`QueryLogPort`** (after answer), using **`build_query_log_ingress_payload`** → **`QueryLogIngressPayload`** and **`log_query_safely`** (logging failure does not suppress **`RAGResponse`**).  
- **Build-stage log (ask path without deferred port):** **`PipelineQueryLogEmitter`** runs inside **`BuildRagPipelineUseCase.execute`** only when **`emit_query_log=True`**.  
- **Inspect, preview, evaluation:** must not hit the ask-only deferred log path; inspect/evaluation rely on **`emit_query_log=False`** on **`BuildRagPipelineUseCase`**. Infrastructure adapters do **not** own product query logging.

---

## Answer generation

- **`api/src/infrastructure/rag/answer_generation_service.py`** — LLM invocation behind **`AnswerGenerationPort`**, used by **`AskQuestionUseCase`** and **`GenerateAnswerFromPipelineUseCase`**.

---

## Retrieval comparison

- **`CompareRetrievalModesUseCase`** — uses **`InspectRagPipelinePort`**; no direct **`infrastructure.rag`** imports from routers or **`frontend/src/services`** (enforced by **`test_orchestration_boundaries.py`** among others).
- **Typed result:** **`RetrievalModeComparisonResult`** (**`application/dto/retrieval_comparison.py`**) with **`RetrievalModeComparisonRow`** / **`RetrievalModeComparisonSummary`**. Pure comparison logic lives in **`application/use_cases/retrieval/retrieval_mode_comparison.py`**. HTTP and in-process clients serialize via **`RetrievalComparisonWirePayload`** / **`retrieval_comparison_to_wire_dict`** (dict shape only at the transport edge).

---

## Document ingestion (orthogonal to query path)

- **HTTP:** **`POST /projects/{project_id}/documents/ingest`** → **`upload_adapter.read_buffered_document_upload`** → **`IngestUploadedFileUseCase`** with domain **`BufferedDocumentUpload`**.  
- **Application:** validation and commands under **`application/use_cases/ingestion`** and **`application/ingestion`**.  
- **Infrastructure:** **`IngestionService`** and related modules persist and run on-disk extraction (see **`docs/api.md`** for upload caps).
