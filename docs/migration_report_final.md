# Final migration report — Clean Architecture (closure)

This report is the **canonical end-state** summary after the migration hardening passes: layer guardrails, documentation, and alignment with the code under `src/`, `apps/api/`, `src/frontend_gateway/`, and `tests/architecture/`.

**Related:** `docs/architecture.md` (includes a **mermaid** layer diagram), `docs/rag_orchestration.md`, `docs/dependency_rules.md`, `docs/final_orchestration_gap_analysis.md` (baseline → closure), `ARCHITECTURE_TARGET.md`.

---

## 1. Current architecture (summary)

| Layer | Role |
|-------|------|
| **`src/domain/`** | Entities, value objects, **ports** (`Protocol` / ABC), shared DTOs such as **`RagInspectAnswerRun`**, **`QueryLogIngressPayload`**, retrieval fusion helpers. |
| **`src/application/`** | **Use cases**, RAG orchestration under **`use_cases/chat/orchestration/`**, evaluation helpers (**`rag_pipeline_orchestration`**, **`GoldQaBenchmarkAdapter`**), **`frontend_support`** (HTTP-safe stubs, **`MemoryChatTranscript`**), policies, DTOs. **No** `src.infrastructure` imports. |
| **`src/infrastructure/`** | Adapters (RAG, evaluation, SQLite, query logging, ingestion, …), persistence, vector stores. Implements domain ports; **post-recall and summary-recall sequencing stay in application**. |
| **`src/composition/`** | **`build_backend_composition`**, **`build_backend`**, **`chat_rag_wiring`**, **`evaluation_wiring`** (**`EvaluationWiringParts`** + **`build_evaluation_service`**), **`BackendApplicationContainer`**. **No** `src.frontend_gateway`. |
| **`apps/api/`** | FastAPI app, routers, schemas, **`dependencies.py`** → container / use cases. **No** `src.infrastructure` imports (entire package scanned). |
| **`src/frontend_gateway/`** | **`BackendClient`**, HTTP and in-process clients, Streamlit factory + session transcript; **no** `src.infrastructure`. |
| **`pages/`**, **`src/ui/`** | Streamlit UI; **only** gateway + auth + view models toward the backend — no domain / infra / composition / `apps.api` imports. |

**Intended dependency flow:** delivery (API, gateway, UI) → **application** use cases → **domain** ports ← **infrastructure** adapters; **composition** constructs the graph.

**RAG inspect path:** **`InspectRagPipelineUseCase`** depends on **`RetrievalPort`**; composition injects the shared **`BuildRagPipelineUseCase`** and inspect calls **`execute(..., emit_query_log=False)`** (see `chat_rag_wiring.py`).

**Gold QA:** **`BenchmarkExecutionUseCase`** accepts only **`RagInspectAnswerRun`** from **`pipeline_runner`**; orchestration for eval uses **`execute_rag_inspect_then_answer_for_evaluation`** at the boundary.

---

## 2. Final architecture status (guardrails)

| Target | Status |
|--------|--------|
| No monolithic RAG façade (`rag_service` / `RAGService`) | **Met** — `test_no_rag_service_facade.py` |
| Use cases own scenarios; composition wires only | **Met** — `application_container.py`, `chat_rag_wiring.py`, `evaluation_wiring.py` |
| Post–summary-recall order in application | **Met** — `assemble_pipeline_from_recall` + `post_recall_pipeline_steps` |
| Summary-recall **sequencing** in application | **Met** — `ApplicationSummaryRecallStage` + `summary_recall_workflow.py`; infra = technical ports only |
| Application does not import infrastructure | **Met** — `test_layer_boundaries.py` |
| Infrastructure adapters → application (minimal allowlist) | **Met** — `test_adapter_application_imports.py` (allowlist: `rag/retrieval_settings_service.py`) |
| Gold-QA benchmark stack not constructed inside `EvaluationService` | **Met** — `evaluation_wiring.py` + `GoldQaBenchmarkAdapter` |
| Query-log / judge row DTOs in domain | **Met** — `QueryLogIngressPayload`, `EvaluationJudgeMetricsRow` |
| **`apps/api`** → no `src.infrastructure.adapters` / services legacy paths | **Met** — `test_fastapi_migration_guardrails.py` |
| Gateway does not import infrastructure | **Met** — layer + gateway guardrails |
| Chat RAG uses **ports** for inspect / answer generation where required | **Met** — `test_application_chat_rag_boundary_ports.py` |

---

## 3. Recent documentation / architecture passes (chronological, high level)

- **Ports and adapters** — **`RetrievalPort`**, **`AnswerGenerationPort`** (and aliases as documented in domain ports); inspect and generate-from-pipeline use cases depend on protocols, not concrete infra.
- **Evaluation wiring** — **`EvaluationWiringParts`**, **`default_evaluation_wiring_parts()`**, **`build_evaluation_service(parts)`**; **`RagInspectAnswerRun`**-only **`pipeline_runner`** contract in **`BenchmarkExecutionUseCase`**.
- **Composition root** — explicit **`chat_transcript`** and **`backend`** parameters; RAG subgraph construction centralized (**`build_rag_retrieval_subgraph`** always builds **`AnswerGenerationService`** internally).
- **Multimodal hints** — orchestration-adjacent logic in **`src/application/chat/multimodal_prompt_hints.py`** (injected from **`chat_rag_wiring`**), not a fat infrastructure façade.
- **API layer purity** — **`apps/api/dependencies.py`** uses **`src.application.frontend_support.memory_chat_transcript.MemoryChatTranscript`** so the FastAPI package never imports infrastructure adapters.
- **Docs** — this report, **`docs/architecture.md`** diagram, **`dependency_rules`**, **`rag_orchestration`**, **`ARCHITECTURE_TARGET`** aligned with the above.

---

## 4. Removed components (cumulative)

| Removed | Notes |
|---------|--------|
| **`src/infrastructure/adapters/rag/rag_service.py`** | Legacy orchestration façade |
| **`src/infrastructure/adapters/rag/pipeline_assembly_service.py`** | Post-recall assembly moved to application |
| **`src/infrastructure/adapters/rag/summary_recall_adapter.py`** | Replaced by app workflow + **`summary_recall_technical_adapters.py`** |
| **`src/infrastructure/adapters/evaluation/benchmark_report_service.py`** | Callers use **`BuildBenchmarkExportArtifactsUseCase`** |
| **`src/backend/`**, **`src/adapters/`**, **`src.infrastructure.services/`** | Legacy trees; directory + import guardrails |
| **`src/services/`** (package) | Removed / guarded |
| Legacy **`ragcraft_app`** / monolithic app wrapper | Removed; composition + API entrypoints only |
| **`src/application/chat/ports.py`** | Unused re-export barrel |
| **`src/application/common/query_log_payload.py`**, **`evaluation_judge_metrics.py`** | Obsolete re-exports; domain types are canonical |
| **`tests/architecture/test_rag_adapter_application_imports.py`** | Superseded by **`test_adapter_application_imports.py`** |
| **`BenchmarkExecutionUseCase._coerce_gold_qa_runner_result`** | **Removed** — runner must return **`RagInspectAnswerRun`** |

---

## 5. Acceptable residual detail (intentional)

| Item | Rationale |
|------|-----------|
| **`rag/retrieval_settings_service.py`** imports **`RetrievalSettingsTuner`** | Typed composition bridge; sole allowlisted adapter → application import |
| **Two `MemoryChatTranscript` modules** | Application copy satisfies **`apps/api`** layer scans; infra copy remains for adapter-adjacent tests and optional wiring |
| **`ManualEvaluationService.evaluate_question`** | Overlaps eval orchestration with **`rag_pipeline_orchestration`**; **product/DX** consolidation optional |
| **`import_legacy_file_logs`** on **`QueryLogService`** | One-off migration utility |
| **`X-User-Id` trust header** | **Security / product** concern, not layer completeness |
| Architecture **line-count ratchets** in `test_orchestration_boundaries.py` | Prevents silent growth of coordinator modules |

---

## 6. Remaining risks (non-architectural)

These do **not** invalidate the migration but are worth tracking:

- **AuthN/AuthZ:** Header-based **`X-User-Id`** is not a verified identity for hostile networks; replace with JWT/OAuth where needed.
- **Operational drift:** Contributors may reintroduce **`src.infrastructure`** imports under **`apps/api`**; **`pytest tests/architecture/`** in CI on touched trees reduces regression risk.
- **Duplicate eval paths:** Manual eval service vs use-case orchestration may diverge behavior over time unless consolidated.
- **Third-party weight:** Heavy optional stacks (e.g. ingestion) can still complicate test envs; architecture tests are **import-level**, not full integration proof.

---

## 7. Is the migration “complete”?

**For Clean Architecture boundaries and RAG orchestration ownership: yes.** Layers, guardrail tests, and docs describe the same dependency rules and flows.

**Not claimed:** production security hardening, performance tuning, or elimination of every duplicate convenience API in evaluation — see **§6**.

---

## 8. Post-migration improvements (optional backlog)

- **Security:** Verified principals instead of **`X-User-Id`** for browser clients.
- **Performance:** Caching, batching, async retrieval, index maintenance.
- **DX:** Deduplicate **`ManualEvaluationService.evaluate_question`** vs **`RunManualEvaluationUseCase`**; keep **`README.github.md`** diagrams aligned with **`docs/architecture.md`**.
- **CI:** Run **`pytest tests/architecture/`** when `src/`, `apps/api`, `pages/`, or `src/ui/` change.

---

## 9. Tests and architecture guards

```bash
pytest tests/architecture/ -q
```

| Concern | Module(s) |
|---------|-----------|
| Layer directions | **`test_layer_boundaries.py`**, **`test_application_orchestration_purity.py`** |
| Legacy paths | **`test_deprecated_backend_and_gateway_guardrails.py`**, **`test_legacy_app_wrapper_removed.py`** |
| FastAPI | **`test_fastapi_migration_guardrails.py`** |
| Composition | **`test_composition_import_boundaries.py`** |
| RAG façade absent; adapters vs chat use case classes | **`test_no_rag_service_facade.py`** |
| Post-recall / transport RAG imports | **`test_orchestration_boundaries.py`** |
| **All adapters** → application import allowlist | **`test_adapter_application_imports.py`** |
| Chat RAG port names / boundaries | **`test_application_chat_rag_boundary_ports.py`** |
| UI surface | **`test_streamlit_import_guardrails.py`** |
| Smoke `build_backend` | **`test_migration_regression_flows.py`** |

---

## 10. Repository tree (main folders)

```text
apps/api/
src/
  auth/
  composition/          # backend_composition, evaluation_wiring, application_container, chat_rag_wiring, wiring
  core/
  domain/               # entities, ports, payloads, retrieval policies, …
  application/
    use_cases/          # chat (orchestration/), evaluation, ingestion, projects, retrieval, settings
    chat/               # policies, multimodal_prompt_hints, …
    frontend_support/
    http/
    common/
  infrastructure/
    adapters/           # rag, evaluation, workspace, query_logging, …
    persistence/
    vectorstores/
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

---

## Final verdict

The Clean Architecture migration is **complete** for enforced boundaries and documented runtime layout. Treat **§6** as the living risk register for product and operations follow-up.
