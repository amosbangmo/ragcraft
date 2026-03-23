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
| Chat / eval / RAG-DTO subtrees avoid infra + delivery stacks | **Met** — `test_orchestration_package_import_boundaries.py` |
| Repo lint/format/typing config present for contributors | **Met** — `pyproject.toml` (Ruff, Black, mypy) + `ruff` in `requirements.txt` |

---

## 3. What was already strong (baseline)

Before the late hardening passes, the codebase already had:

- A **clear layer layout**: `domain` ports, `application` use cases and RAG orchestration modules, `infrastructure` adapters, `composition` wiring, FastAPI in `apps/api`, and a **gateway** for Streamlit.
- **RAG orchestration** owned in application (`summary_recall_workflow`, `recall_then_assemble_pipeline`, post-recall steps) instead of a monolithic infrastructure façade.
- **Architecture tests** (`tests/architecture/`) catching the worst regressions (API importing infra, application importing LangChain, removed legacy packages).
- **Evaluation** wired through **`GoldQaBenchmarkAdapter`** and **`BenchmarkExecutionUseCase`** with an explicit **`RagInspectAnswerRun`** contract.

The remaining work was **contract tightness**, **transport clarity**, and **long-term guardrails** — not a rewrite.

---

## 4. Recent documentation / architecture passes (chronological, high level)

- **Ports and adapters** — **`RetrievalPort`**, **`AnswerGenerationPort`** (and aliases as documented in domain ports); inspect and generate-from-pipeline use cases depend on protocols, not concrete infra.
- **Evaluation wiring** — **`EvaluationWiringParts`**, **`default_evaluation_wiring_parts()`**, **`build_evaluation_service(parts)`**; **`RagInspectAnswerRun`**-only **`pipeline_runner`** contract in **`BenchmarkExecutionUseCase`**.
- **Composition root** — explicit **`chat_transcript`** and **`backend`** parameters; RAG subgraph construction centralized (**`build_rag_retrieval_subgraph`** always builds **`AnswerGenerationService`** internally).
- **Multimodal hints** — orchestration-adjacent logic in **`src/application/chat/multimodal_prompt_hints.py`** (injected from **`chat_rag_wiring`**), not a fat infrastructure façade.
- **API layer purity** — **`apps/api/dependencies.py`** uses **`src.application.frontend_support.memory_chat_transcript.MemoryChatTranscript`** so the FastAPI package never imports infrastructure adapters; auth and **`/users`** routes use application use cases and **`AuthenticatedPrincipal`**.
- **Docs** — this report, **`docs/architecture.md`** diagram, **`dependency_rules`**, **`rag_orchestration`**, **`ARCHITECTURE_TARGET`** aligned with the above.

---

## 5. Removed components (cumulative)

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

## 6. Acceptable residual detail (intentional)

| Item | Rationale |
|------|-----------|
| **`rag/retrieval_settings_service.py`** imports **`RetrievalSettingsTuner`** | Typed composition bridge; sole allowlisted adapter → application import |
| **Two `MemoryChatTranscript` modules** | Application copy satisfies **`apps/api`** layer scans; infra copy remains for adapter-adjacent tests and optional wiring |
| **`ManualEvaluationService.evaluate_question`** | Overlaps eval orchestration with **`rag_pipeline_orchestration`**; **product/DX** consolidation optional |
| **`import_legacy_file_logs`** on **`QueryLogService`** | One-off migration utility |
| **`X-User-Id` trust header** | **Security / product** concern — transport still trusts the header, but the API boundary is now an **`AuthenticatedPrincipal`**, not a bare string |
| Architecture **line-count ratchets** in `test_orchestration_boundaries.py` | Prevents silent growth of coordinator modules |

---

## 7. Remaining risks (non-architectural)

These do **not** invalidate the migration but are worth tracking:

- **AuthN/AuthZ:** Header-based **`X-User-Id`** is not a verified identity for hostile networks; replace with JWT/OAuth where needed. The application layer now has **`TrustedTransportIdentityPort`** as an extension point and typed **`AuthenticatedPrincipal`** at the HTTP boundary.
- **Operational drift:** Contributors may reintroduce **`src.infrastructure`** imports under **`apps/api`**; **`pytest tests/architecture/`** in CI on touched trees reduces regression risk.
- **Duplicate eval paths:** Manual eval service vs use-case orchestration may diverge behavior over time unless consolidated.
- **Third-party weight:** Heavy optional stacks (e.g. ingestion) can still complicate test envs; architecture tests are **import-level**, not full integration proof.

---

## 8. Is the migration “complete”?

**For Clean Architecture boundaries and RAG orchestration ownership: yes.** Layers, guardrail tests, and docs describe the same dependency rules and flows.

**Auth / users (corrected):** The API boundary uses **`get_authenticated_principal` → `AuthenticatedPrincipal`** instead of passing raw header strings through handlers. Login and registration are **`LoginUserUseCase`** / **`RegisterUserUseCase`**; **`/users/*`** uses account use cases. Password and avatar I/O sit behind **`PasswordHasherPort`** and **`AvatarStoragePort`**. Streamlit reuses the same use cases via **`auth_credentials`**.

**RAG orchestration (corrected):** Typed overrides (**`RetrievalSettingsOverrideSpec`**), recall/assembly DTOs, explicit eval input (**`RagEvaluationPipelineInput`**), and **`RagInspectAnswerRun`** with **`PipelineLatency`**. Ask vs inspect vs preview vs evaluation modes are documented in **`docs/rag_orchestration.md`**.

**Ingestion / settings / evaluation edges (corrected):** **`BufferedDocumentUpload`**, chunked multipart reads + **`RAG_MAX_UPLOAD_BYTES`**, **`ProjectDocumentDetailRow`**, **`GenerateQaDatasetResult`** + wire payloads, benchmark export bundle typing.

**Structural guardrails (final pass):** **`test_orchestration_package_import_boundaries.py`**; **`pyproject.toml`** for **Ruff**, **Black**, and incremental **mypy**; **Ruff** surfaced missing **`RetrievalSettingsOverrideSpec`** imports in **`build_rag_pipeline.py`** / **`summary_recall_workflow.py`** (fixed).

**Not claimed:** production security hardening, performance tuning, full **mypy --strict** across the repo, or deduplicating every evaluation convenience path — see **§7** and **§6**.

---

## 9. Post-migration improvements (optional backlog)

- **Security:** Implement **`TrustedTransportIdentityPort`** with JWT/OAuth and stop treating **`X-User-Id`** as trusted on public networks.
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
| Orchestration subtrees (chat/eval/rag) | **`test_orchestration_package_import_boundaries.py`** |

---

## 11. RAG orchestration typed contracts (orchestration hardening)

This pass removed loose retrieval-settings ``dict`` shapes from core RAG orchestration boundaries and formalized DTOs for recall fusion and evaluation input.

| Removed / tightened | Replacement |
|--------------------|-------------|
| ``retrieval_settings: dict[str, Any] \| None`` on **`RetrievalPort.execute`**, **`SummaryRecallStagePort`**, **`RAGPipelineQueryContext`**, **`run_recall_then_assemble_pipeline`**, chat use cases | **`RetrievalSettingsOverrideSpec \| None`** (domain); validated partial merge mapping keyed only to **`RetrievalSettings`** fields |
| Ad hoc recall fusion return shape | **`VectorLexicalRecallBundle`** in **`src/application/rag/dtos/recall_stages.py`** |
| Untyped evaluation orchestration inputs | **`RagEvaluationPipelineInput`** |
| **`RagInspectAnswerRun.full_latency`** as loose dict | **`PipelineLatency \| None`**; row export still uses **`to_row_evaluation_dict()`** |

**Execution modes (unchanged intent, clearer contracts):**

| Mode | Use case / entry | Query log | Answer generation |
|------|------------------|-----------|-------------------|
| Product ask | **`AskQuestionUseCase`** | Yes (via **`QueryLogPort`** / safe helpers, deferred) | Yes |
| Inspect | **`InspectRagPipelineUseCase`** | **No** (`emit_query_log=False`) | **No** |
| Preview recall | **`PreviewSummaryRecallUseCase`** | **No** | **No** (stops at recall; **`SummaryRecallPreviewDTO`**) |
| Evaluation | **`execute_rag_inspect_then_answer_for_evaluation`** | **No** | Yes, via **`GenerateAnswerFromPipelinePort`**; returns **`RagInspectAnswerRun`** for **`BenchmarkExecutionUseCase`** |

**Future hardening (optional):** Gateway HTTP client method signatures may still accept ``dict`` for ``retrieval_settings`` as transport-only JSON; tightening those to a shared wire type would be cosmetic unless validation is duplicated outside the API boundary.

---

## 11. Ingestion, project document details, and evaluation wire (API / application hardening)

**Document upload boundary**

- **Transport:** ``apps/api/upload_adapter.py`` reads multipart bodies in **chunks** (1 MiB) and rejects payloads larger than ``INGESTION_CONFIG.max_upload_bytes`` (env **`RAG_MAX_UPLOAD_BYTES`**, default 100 MiB) with **HTTP 413** before the ingest use case runs.
- **Domain:** **`BufferedDocumentUpload`** (`src/domain/buffered_document_upload.py`) is the stable name + bytes (+ optional declared media type) object passed into **`DocumentIngestionPort.ingest_uploaded_file`** and **`IngestUploadedFileCommand`** (field **`upload`**).
- **Application validation:** **`validate_buffered_document_upload`** (`src/application/ingestion/upload_policy.py`) enforces non-empty body, size cap (defense in depth), and basename-only filenames.
- **Streaming:** Extraction still runs from a **persisted file** on disk (existing pipeline); streaming directly into unstructured is **not** implemented — the adapter documents this limitation.

**Settings**

- Retrieval GET/PUT already used **`EffectiveRetrievalSettingsView`** + **`EffectiveRetrievalSettingsWirePayload`**; **`src/application/settings/dtos.py`** docstrings now spell out query/command/view roles and wire mapping.

**Row-dict leakage reduced**

- **`GetProjectDocumentDetailsUseCase`** returns **`list[ProjectDocumentDetailRow]`** (`src/application/projects/dtos.py`); the projects router maps rows via **`project_document_detail_row_to_item`** (`apps/api/schemas/mappers.py`).
- **QA dataset generation:** **`ProposedQaDatasetRow`** (domain), **`QaDatasetGenerationPort`** returns typed proposals, **`GenerateQaDatasetResult`** (`src/application/evaluation/dtos.py`), **`QaDatasetGenerateWirePayload`** for FastAPI **`QaDatasetGenerateResponse`**. **`BenchmarkExportBundleWirePayload`** wraps **`BenchmarkExportArtifacts.to_http_bundle_dict()`** for the export ``all`` format.

**Residual**

- **SQLite asset listing** for document assets is still ``list[dict]`` from the repository; a typed asset row model can follow the same pattern as document details.
- **`ListRetrievalQueryLogsUseCase`** / log entries may remain dict-shaped at the HTTP mapper where the store is JSON-oriented.

---

## 13. Repository tree (main folders)

```text
apps/api/
src/
  auth/
  composition/          # backend_composition, evaluation_wiring, application_container, chat_rag_wiring, wiring
  core/
  domain/               # entities, ports, payloads, retrieval policies, …
  application/
    use_cases/          # chat (orchestration/), evaluation, ingestion, projects, retrieval, settings
    rag/                # orchestration DTOs (recall bundle, eval pipeline input, …)
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

## Final verdict (architecture maturity)

The repository is an **excellent long-term base** for feature work **within** the chosen Clean Architecture style:

- **Layers and dependency direction** are **enforced by tests**, not only described in docs.
- **RAG orchestration** is **application-owned**, typed at the main boundaries, and **split by execution mode** (ask / inspect / preview / evaluation) with **logging only through ports** on product paths.
- **Delivery** (FastAPI, gateway, UI) stays **thin** relative to use cases; **composition** is the only place that should know about concrete adapters.
- **Tooling** (**`pyproject.toml`**) gives contributors a **shared Ruff/Black/mypy baseline**; **mypy strict** for the entire tree remains **deferred** (incremental adoption is intentional).

**Intentionally deferred:** verified identity on public networks (**JWT/OAuth**), **mypy strict** everywhere, optional consolidation of duplicate evaluation helpers, and typed rows for every SQLite-backed list endpoint.

Treat **§7** (risks) and **§6** (acceptable residual) as the living registers for product and operations follow-up.
