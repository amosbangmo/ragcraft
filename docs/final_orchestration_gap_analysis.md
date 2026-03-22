# Orchestration gap analysis — baseline → closure

This document began as a **pre-migration-closure baseline** (March 2025) listing orchestration responsibilities and gaps. **The migration described there is now complete** for architecture boundaries; see **`docs/migration_report_final.md`** (including **`## Final verdict`**) for the authoritative end state.

Use this file as a **historical checklist** of what was addressed; the **live** description of RAG flow is **`docs/rag_orchestration.md`**.

---

## What the baseline called out (resolved)

| Gap (baseline) | Resolution (current codebase) |
|------------------|--------------------------------|
| Monolithic **`SummaryRecallAdapter`** owned full recall sequencing | **`ApplicationSummaryRecallStage`** + **`summary_recall_workflow.py`** own sequencing; **`summary_recall_technical_adapters.py`** are thin I/O; domain **`summary_recall_execution_plan`**, **`classify_query_intent`**, **`is_table_focused_question`**, **`merge_summary_documents_weighted_rrf`**. |
| **`EvaluationService`** constructed **`BenchmarkExecutionUseCase`** (infra → application use case) | **`src/composition/evaluation_wiring.py`** builds row services + **`BenchmarkExecutionUseCase`** + **`GoldQaBenchmarkAdapter`**; **`EvaluationService`** receives **`GoldQaBenchmarkPort`** only. |
| Infrastructure imported application DTOs for query log / judge rows | **`QueryLogIngressPayload`** → **`src/domain/query_log_ingress_payload.py`**; **`EvaluationJudgeMetricsRow`** → **`src/domain/evaluation/judge_metrics_row.py`**. |
| **`benchmark_report_service`** wrapped application export use case | Removed; callers use **`BuildBenchmarkExportArtifactsUseCase`** directly. |
| RAG-only import test | Replaced by **`tests/architecture/test_adapter_application_imports.py`** (all adapters; allowlist **`rag/retrieval_settings_service.py`** only). |
| Unused **`application/chat/ports.py`** re-export barrel | **Removed.** |

**Still optional follow-ups (non-blocking for “architecture complete”):** dict-shaped **`pipeline_runner`** in gold QA (**`_coerce_gold_qa_runner_result`**); duplicate **`ManualEvaluationService.evaluate_question`** path; rename **`MultimodalOrchestrationService`**; **`README.github.md`** diagram drift.

---

## Updated orchestration map (canonical)

```text
HTTP / Streamlit
  → apps/api/routers/*.py | pages/*.py + BackendClient
       → ResolveProjectUseCase (where applicable)
       → Chat / evaluation use cases

End-to-end ask
  → ask_question.py
       → build_rag_pipeline.py → recall_then_assemble_pipeline.py
            → summary_recall_from_request.py → ApplicationSummaryRecallStage (SummaryRecallStagePort)
            → application_pipeline_assembly.py → assemble_pipeline_from_recall.py
       → AnswerGenerationPort
       → QueryLogPort (deferred)

Gold QA benchmark
  → run_gold_qa_dataset_evaluation.py → GoldQaBenchmarkPort (GoldQaBenchmarkAdapter)
  → benchmark_execution.py

Composition
  → backend_composition.py + evaluation_wiring.py + application_container.py + chat_rag_wiring.py
```

---

## Validation (re-run after changes)

```bash
pytest tests/architecture/ -q
pytest tests/application/chat/ -q
pytest tests/infrastructure_services/test_chat_rag_wiring.py -q
```

| Date | Change |
|------|--------|
| 2025-03-22 | Initial baseline |
| 2025-03-22 | Closure note + resolved table (migration complete) |
