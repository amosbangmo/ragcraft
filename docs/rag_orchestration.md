# RAG orchestration (final model)

## Entrypoints

| Entry | Mechanism |
|-------|-----------|
| **HTTP chat** | `apps/api/routers/chat.py` → `AskQuestionUseCase` via `apps/api/dependencies.py` (scoped routes require **`Authorization: Bearer`** → **`AuthenticatedPrincipal`**) |
| **In-process UI** | `src/frontend_gateway/in_process.py` → `container.chat_ask_question_use_case.execute(...)` |
| **Pipeline build only** | `BuildRagPipelineUseCase` (inspect/compare/eval paths) |
| **Inspect pipeline** | `InspectRagPipelineUseCase` — depends on **`RetrievalPort`**; composition injects the same **`BuildRagPipelineUseCase`** instance and inspect calls **`execute(..., emit_query_log=False)`** |
| **Preview summary recall** | `PreviewSummaryRecallUseCase` |
| **Answer from built pipeline** | `GenerateAnswerFromPipelineUseCase` |

Composition builds the graph in `src/composition/chat_rag_wiring.py` and exposes it through `BackendApplicationContainer.chat_rag_use_cases` and the `chat_*_use_case` properties.

**Guardrails:** Folder-scoped import tests (**`test_orchestration_package_import_boundaries.py`**) ensure `use_cases/chat/orchestration`, `use_cases/evaluation`, and **`src/application/rag/`** do not import infrastructure adapters or HTTP/Streamlit/LangChain stacks — keeping orchestration **port-driven**.

### Typed orchestration contracts (boundaries)

- **Retrieval overrides:** Per-request partial settings use **`RetrievalSettingsOverrideSpec`** (`src/domain/retrieval_settings_override_spec.py`) on **`RetrievalPort`**, **`SummaryRecallStagePort`**, **`RAGPipelineQueryContext`**, and chat use cases — not raw ``dict[str, Any]``. FastAPI maps the JSON ``retrieval_settings`` object to a spec in **`apps/api/routers/chat.py`**; **`InProcessBackendClient`** does the same before calling use cases.
- **Recall fusion output:** **`fuse_vector_and_lexical_recalls`** returns **`VectorLexicalRecallBundle`** (`src/application/rag/dtos/recall_stages.py`).
- **Evaluation input:** **`execute_rag_inspect_then_answer_for_evaluation`** takes **`RagEvaluationPipelineInput`** (`src/application/rag/dtos/evaluation_pipeline.py`).
- **Evaluation result latency:** **`RagInspectAnswerRun.full_latency`** is **`PipelineLatency | None`**. **`RagInspectAnswerRun.as_row_evaluation_input()`** returns **`GoldQaPipelineRowInput`** for **`RowEvaluationService.process_row`** (no ad hoc ``dict`` at that boundary).

## Main use cases (happy path ask)

1. **`AskQuestionUseCase`** — calls injected `build_pipeline` (bound to `BuildRagPipelineUseCase.execute`), then **`AnswerGenerationPort`** for the LLM, then **`QueryLogPort`** when configured (deferred full payload after answer).
2. **`BuildRagPipelineUseCase`** — runs **`run_recall_then_assemble_pipeline`** then **`PipelineBuildQueryLogEmitterPort`** (`PipelineQueryLogEmitter`) when `emit_query_log=True`. RAG adapters do not log queries themselves.

## Orchestration sequence (application-owned)

**Recall + assemble helper:** `recall_then_assemble_pipeline.py` calls **`run_summary_recall_from_chat_request`** then **`PipelineAssemblyPort.build`**.

### Summary-recall stage

1. **`ApplicationSummaryRecallStage.summary_recall_stage(...)`** — **`src/application/use_cases/chat/orchestration/summary_recall_workflow.py`**. Implements **`SummaryRecallStagePort`**. Sequences: settings merge (**`RetrievalSettingsTuner`** via injected tuner), optional rewrite (**`QueryRewritePort`**), domain intent/table policy, domain **`resolve_summary_recall_execution_plan`**, then **`fuse_vector_and_lexical_recalls`** (vector + optional lexical ports + domain RRF merge).
2. **Technical adapters:** **`src/infrastructure/adapters/rag/summary_recall_technical_adapters.py`** — **`QueryRewriteAdapter`**, **`SummaryVectorRecallAdapter`**, **`SummaryLexicalRecallAdapter`** (FAISS, BM25/docstore). Wired as **`SummaryRecallTechnicalPorts`** in **`chat_rag_wiring.py`**.

### Post-recall assembly

**`ApplicationPipelineAssembly`** (bound into **`BuildRagPipelineUseCase`** as its assembly collaborator) implements **`PipelineAssemblyPort`**: **`build(...)`** delegates to **`assemble_pipeline_from_recall`**, which sequences **`post_recall_pipeline_steps`** (`step_docstore_hydration`, `step_section_expansion`, …).

**Technical implementations:** `src/infrastructure/adapters/rag/post_recall_stage_adapters.py` — one thin adapter class per port, delegating to existing services.

## Ports involved (representative)

- **`SummaryRecallStagePort`**, **`PipelineAssemblyPort`** — recall + assembly boundary.
- **`SummaryRecallTechnicalPorts`** — query rewrite, vector recall, lexical recall (application-defined protocols; infrastructure adapters).
- **`PostRecallStagePorts`** (dataclass) — docstore read, section expansion, reranking, table QA hints, compression, prompt sources, layout, multimodal, prompt render, confidence.
- **`QueryLogPort`** — query logging (implemented by infrastructure query log service).
- **`AnswerGenerationPort`** — LLM answer from a built pipeline; implemented by **`AnswerGenerationService`**.

## Where logging happens

- **After pipeline build (no answer yet):** `PipelineQueryLogEmitter` in `BuildRagPipelineUseCase.execute` when `emit_query_log=True`.
- **After full ask:** `AskQuestionUseCase` uses `log_query_safely` + `build_query_log_ingress_payload` (builds domain **`QueryLogIngressPayload`**) when a `QueryLogPort` is wired — never from vectorstore/docstore/rerank adapters.

## Manual and gold-QA evaluation (inspect + answer, no production query log)

**Single orchestration path:** Inspect + answer + latency merge for evaluation is always **`execute_rag_inspect_then_answer_for_evaluation`** (`src/application/use_cases/evaluation/rag_pipeline_orchestration.py`). There is **no** parallel “service” entry point that re-implements that sequence.

- **`execute_rag_inspect_then_answer_for_evaluation`** — takes **`RagEvaluationPipelineInput`**, coordinates **`InspectRagPipelinePort`** + **`GenerateAnswerFromPipelinePort`**, merges per-stage latency into **`PipelineBuildResult.latency`** as **`PipelineLatency`** (same type as inspect/ask paths).
- **`RagInspectAnswerRun`** — `src/domain/rag_inspect_answer_run.py`; **`as_row_evaluation_input()`** yields **`GoldQaPipelineRowInput`** for **`BenchmarkRowProcessingPort` / `RowEvaluationService`**.
- **`RunManualEvaluationUseCase`** — `POST /evaluation/manual`, **`InProcessBackendClient.evaluate_manual_question`**, and composition **`evaluation_run_manual_evaluation_use_case`** all delegate here → canonical orchestration above → **`ManualEvaluationFromRagPort.build_manual_evaluation_result`** (implemented by **`EvaluationService`**). **`RunGoldQaDatasetEvaluationUseCase`** shares the same inspect/answer ports and gold-QA benchmark wiring. **`GoldQaBenchmarkPort`** is implemented by **`GoldQaBenchmarkAdapter`** (application), wired from **`src/composition/evaluation_wiring.py`**. **`BenchmarkExecutionUseCase.execute`** requires each **`pipeline_runner(entry)`** return value to be a **`RagInspectAnswerRun`** (otherwise **`TypeError`**).
- **`src/infrastructure/adapters/evaluation/manual_evaluation_service.py`** — **result assembly helpers only** (e.g. **`manual_evaluation_result_from_eval_row`**, **`manual_evaluation_result_from_rag_outputs`**); it does **not** orchestrate inspect/answer.

## Where answer generation happens

- **`src/infrastructure/adapters/rag/answer_generation_service.py`** — LLM invoke, used by **`AskQuestionUseCase`** and **`GenerateAnswerFromPipelineUseCase`**.

## Retrieval comparison

- **`CompareRetrievalModesUseCase`** — uses **`InspectRagPipelinePort`** (application); no direct RAG adapter imports from routers or gateway.

## Document ingestion (orthogonal to RAG query path)

- **HTTP:** `POST /projects/{project_id}/documents/ingest` uses **`read_buffered_document_upload`** (`apps/api/upload_adapter.py`) then **`IngestUploadedFileUseCase`** with **`IngestUploadedFileCommand.upload`** = domain **`BufferedDocumentUpload`**.
- **Application:** **`validate_buffered_document_upload`** applies basename-only names, non-empty body, and size limits (aligned with **`RAG_MAX_UPLOAD_BYTES`**).
- **Infrastructure:** **`IngestionService.ingest_uploaded_file`** persists via **`save_uploaded_file`** then runs the existing on-disk extraction pipeline (not streaming from the socket into unstructured).
