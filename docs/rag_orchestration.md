# RAG orchestration

How **RAG** is split across use cases, **application/orchestration**, **composition** wiring, and **infrastructure/rag** technical adapters.

**Related:** **`docs/architecture.md`**, **`docs/api.md`**, **`docs/migration_report_final.md`** (§12). **Tests:** **`api/tests/appli/orchestration/test_rag_mode_contracts.py`**, **`api/tests/api/test_http_pipeline_e2e.py`**.

---

## 1. Code map

| Layer | Path |
|--------|------|
| Orchestration | **`api/src/application/orchestration/rag/`**, **`orchestration/evaluation/`** |
| Use cases | **`api/src/application/use_cases/`** |
| Wiring | **`api/src/composition/chat_rag_wiring.py`**, **`evaluation_wiring.py`** |
| Technical RAG | **`api/src/infrastructure/rag/`** |

---

## 2. Mode separation

| Mode | Use case / entry | Pipeline | Answer | Product query log |
|------|------------------|----------|--------|-------------------|
| **Ask** | **`AskQuestionUseCase`** | Full (**`BuildRagPipelineUseCase`**) | Yes | Yes when **`QueryLogPort`** wired |
| **Inspect** | **`InspectRagPipelineUseCase`** | Full | No | **No** — **`emit_query_log=False`** always |
| **Preview** | **`PreviewSummaryRecallUseCase`** | Recall only | No | **No** |
| **Evaluation** | **`execute_rag_inspect_then_answer_for_evaluation`** (+ manual / gold QA) | Via inspect port | Via **`GenerateAnswerFromPipelinePort`** | **No** |

**Enforced by:** **`test_rag_mode_contracts.py`**. One canonical evaluation orchestrator in **`rag_pipeline_orchestration.py`**; **`infrastructure/evaluation`** does assembly helpers only, not a second inspect+answer orchestration.

---

## 3. Entrypoints

| Flow | Where |
|------|--------|
| HTTP ask | **`interfaces/http/routers/chat.py`** → **`AskQuestionUseCase`** (**`dependencies.py`**) — Bearer JWT → **`AuthenticatedPrincipal`**. |
| Streamlit ask (in-process) | **`application/frontend_support/in_process_backend_client.py`** → container **`chat_ask_question_use_case`** — same use cases as HTTP. |
| Pipeline build | **`BuildRagPipelineUseCase`** — shared by inspect, comparison, evaluation. |
| Inspect | **`InspectRagPipelineUseCase`** — same **`BuildRagPipelineUseCase`** instance, **`emit_query_log=False`**. |
| Preview recall | **`PreviewSummaryRecallUseCase`** — **`SummaryRecallPreviewDTO`**, no full assembly. |
| Answer from built pipeline | **`GenerateAnswerFromPipelineUseCase`**. |

**Graph:** **`chat_rag_wiring.py`** → **`BackendApplicationContainer`** (**`chat_rag_use_cases`**, …).

**Imports:** **`test_orchestration_package_import_boundaries.py`** — orchestration packages avoid **`infrastructure`**, FastAPI, Streamlit, LangChain, FAISS, etc.

---

## 4. Product flows (summary)

### 4.1 Ask (chat)

**`AskQuestionUseCase`** builds the pipeline (**`BuildRagPipelineUseCase`**), answers via **`AnswerGenerationPort`**, may log via **`QueryLogPort`**. **`BuildRagPipelineUseCase`** runs **`run_recall_then_assemble_pipeline`** and, when **`emit_query_log=True`**, uses **`PipelineQueryLogEmitter`**. Infrastructure does **not** own product query logging.

### 4.2 Inspect

**`InspectRagPipelineUseCase`** — full pipeline, no answer, **`emit_query_log=False`**.

### 4.3 Preview

**`PreviewSummaryRecallUseCase`** — recall / preview only; no post-recall assembly or answer.

### 4.4 Evaluation (gold QA, manual)

**`execute_rag_inspect_then_answer_for_evaluation`** (**`rag_pipeline_orchestration.py`**) coordinates **`InspectRagPipelinePort`** and **`GenerateAnswerFromPipelinePort`**. Input: **`RagEvaluationPipelineInput`**; output: **`RagInspectAnswerRun`**. **`GoldQaBenchmarkAdapter`** implements **`GoldQaBenchmarkPort`**. **`RunManualEvaluationUseCase`** is the application entry for manual eval.

---

## 5. Recall → assembly sequence

**Coordinator:** **`recall_then_assemble_pipeline.py`** → **`run_summary_recall_from_chat_request`** then **`PipelineAssemblyPort.build`**.

- **Summary recall:** **`ApplicationSummaryRecallStage`** (**`summary_recall_workflow.py`**) — settings merge, optional rewrite, **`fuse_vector_and_lexical_recalls`**, …  
- **Technical adapters:** **`infrastructure/rag/summary_recall_technical_adapters.py`** → **`SummaryRecallTechnicalPorts`**.  
- **Assembly:** **`ApplicationPipelineAssembly`** (**`application_pipeline_assembly.py`**) → **`post_recall_pipeline_steps`**.  
- **Post-recall adapters:** **`infrastructure/rag/post_recall_stage_adapters.py`**.

---

## 6. Typed boundaries

- **`RetrievalSettingsOverrideSpec`** — chat, **`RetrievalPort`**, **`SummaryRecallStagePort`**, HTTP router JSON, **`InProcessBackendClient`**.  
- **`VectorLexicalRecallBundle`**, **`RagEvaluationPipelineInput`**, **`PipelineLatency`** — see domain and **`application/rag/dtos`**.  
- Wire payloads use **`as_json_dict()`** / **`RetrievalComparisonWirePayload`** at the HTTP edge only.

---

## 7. Logging

- **Ask:** **`QueryLogPort`** after answer; **`build_query_log_ingress_payload`**.  
- **Build-stage:** **`PipelineQueryLogEmitter`** when **`emit_query_log=True`**.  
- **Inspect / preview / evaluation:** no ask-only deferred log path; infrastructure adapters do not own product query logs.

---

## 8. Answer generation

**`infrastructure/rag/answer_generation_service.py`** behind **`AnswerGenerationPort`** — used by ask and **`GenerateAnswerFromPipelineUseCase`**.

---

## 9. Retrieval comparison

**`CompareRetrievalModesUseCase`** — **`InspectRagPipelinePort`**; typed **`RetrievalModeComparisonResult`** (**`application/dto/retrieval_comparison.py`**). HTTP and in-process serialize at the edge (**`RetrievalComparisonWirePayload`**, **`retrieval_comparison_to_wire_dict`**). Delivery layers must not import **`infrastructure.rag`** directly (**`test_orchestration_boundaries.py`**).

---

## 10. Document ingestion

**HTTP:** **`POST /projects/{project_id}/documents/ingest`** → **`upload_adapter`** → **`IngestUploadedFileUseCase`** (**`BufferedDocumentUpload`**). See **`docs/api.md`** for size limits.

---

## 11. Verification checklist

| Check | Test / doc |
|-------|------------|
| Mode + query-log rules | **`api/tests/appli/orchestration/test_rag_mode_contracts.py`** |
| HTTP walk (ask, inspect, preview, settings, benchmark, export) | **`api/tests/api/test_http_pipeline_e2e.py`** |
| Single manual-eval orchestrator | **`api/tests/architecture/test_manual_evaluation_single_orchestrator.py`** |

Auth code lives under **`domain`**, **`application/use_cases/auth`**, **`infrastructure/auth`** — not a separate **`api/src/auth`** package.
