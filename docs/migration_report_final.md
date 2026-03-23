# Final migration report — Clean Architecture (closure)

## Physical repository layout (enforced)

As of the **api/frontend split** refactor, the canonical layout is:

- **Backend:** `api/src/` — top-level packages `domain`, `application`, `infrastructure`, `composition`, `interfaces` (FastAPI under `interfaces/http/`). Entry: `api/main.py`.
- **Frontend:** `frontend/src/` — Streamlit pages, components, services (former `frontend_gateway`), utils. Entry: `frontend/app.py`.
- **Tests:** `api/tests/` (architecture, appli, infra, `api/` HTTP contract tests, e2e, …) and `frontend/tests/`.
- **Removed:** root `src/`, root `apps/`, root `pages/`, root `streamlit_app.py` (replaced by the tree above).

### Structure cleanup closure (final)

The **api/frontend** split is the **only** supported physical layout. A final cleanup pass removed stale documentation references to `apps/api/`, monolithic root `src/`, `streamlit_app.py`, and legacy Streamlit paths. **Legacy roots and duplicate trees are not present** in the repository. **Structural and import drift is blocked** by **`api/tests/architecture/`** (required tree, forbidden roots, layer rules) — that suite is the **source of truth** for what the repository is allowed to look like; **`scripts/validate_architecture.sh`** / CI run the same tests.

### Blocking architecture guardrails (PROMPT 2)

The following **fail the test suite** (not advisory checks) when the repo drifts:

| Concern | Test module |
|---------|-------------|
| Required roots (`api/`, `frontend/`, `docs/`, `scripts/`, `api/src/`, `frontend/src/`), forbidden legacy roots (`src/`, `apps/` at repo root), FastAPI routers only under `api/src/interfaces/http/routers/`, Pydantic `BaseModel` HTTP types under `schemas/`, composition under `api/src/composition/`, orchestration under `api/src/application/orchestration/`, no UI trees under `api/src/` | **`api/tests/architecture/test_repository_structure.py`** |
| Domain / application / HTTP-router import boundaries | **`test_layer_import_rules.py`** |
| `interfaces/http` delivery (no Streamlit; no legacy monolith import paths) | **`test_fastapi_delivery_boundaries.py`**, **`test_fastapi_migration_guardrails.py`** |
| Frontend pages/components stay off domain/application/composition; infrastructure limited to `infrastructure.auth.*` | **`test_frontend_structure.py`** |

**Documented narrow exceptions (encoded in tests + this doc):**

- **Domain** and **application** may import **`infrastructure.config`** only (paths, shared config objects, exception types) — not persistence/RAG/evaluation adapters.
- **HTTP routers** must not import **`infrastructure.*`** at all (wiring goes through `dependencies` / use cases). Other files under `interfaces/http/` may still use **`infrastructure.config`** for errors and upload limits.
- **Streamlit** imports under **`api/src/infrastructure/auth`** and **`api/src/infrastructure/config`** remain allowed for session/UI shims (see **`test_layer_boundaries`**).
- **`frontend/src/services`** may import backend packages for the **in-process + HTTP gateway**; **pages** and **components** follow the stricter rules in **`test_frontend_structure.py`**.

CI-oriented scripts: **`scripts/validate_architecture.sh`** (architecture tests only), **`scripts/validate.sh`** (Ruff + architecture), **`scripts/run_tests.sh`**, **`scripts/lint.sh`**.

### Required repository skeleton (PROMPT 3)

**`api/tests/architecture/test_required_tree.py`** adds **positive** guardrails: it fails if required folders or **architectural anchor files** disappear (e.g. `api/src/composition/backend_composition.py`, `api/src/interfaces/http/dependencies.py`, router/schema modules listed in the test module, `frontend/app.py`, `frontend/src/pages/settings.py`, `frontend/src/state/session_state.py`, `frontend/src/services/api_client.py`, and the documented doc/script paths). It intentionally does **not** freeze every new feature file.

**Note on test directory names:** the suite expects **`api/tests/appli`**, **`api/tests/infra`**, and **`api/tests/api/`** (FastAPI tests; import package name **`api`** with **`api/tests`** on **`PYTHONPATH`** as in **`scripts/run_tests.*`** — distinct from the repo-root ASGI package **`api`** used for **`uvicorn api.main:app`** when the repository root is on **`PYTHONPATH`**). **`appli`** / **`infra`** avoid shadowing **`application`** / **`infrastructure`** under **`api/src`**.

---

Sections below describe **behavior and history** using **filesystem paths** under the canonical tree (**`api/src/…`**, **`frontend/src/…`**). Python **import** names are unprefixed (`domain`, `application`, …) when **`PYTHONPATH`** includes **`api/src`** and **`frontend/src`** as in **`scripts/run_tests.sh`**.

**Related:** `docs/architecture.md`, `docs/rag_orchestration.md`, `docs/dependency_rules.md`, `docs/testing_strategy.md`, `docs/api.md`.

---

## 1. Current architecture (summary)

| Layer | Role |
|-------|------|
| **`api/src/domain/`** | Entities, value objects, **ports** (`Protocol` / ABC), **`AuthenticatedPrincipal`**, **`AuthenticationPort`**, **`AccessTokenIssuerPort`**, shared DTOs such as **`RagInspectAnswerRun`**, **`QueryLogIngressPayload`**, retrieval fusion helpers. |
| **`api/src/application/`** | **Use cases**, RAG orchestration under **`use_cases/chat/orchestration/`**, evaluation helpers (**`rag_pipeline_orchestration`**, **`GoldQaBenchmarkAdapter`**), **`frontend_support`** (HTTP-safe stubs, **`MemoryChatTranscript`**), policies, DTOs. **No** concrete `infrastructure` adapter imports (narrow **`infrastructure.config`** exception only). |
| **`api/src/infrastructure/`** | Adapters (RAG, evaluation, SQLite, query logging, ingestion, …), persistence, vector stores. Implements domain ports; **post-recall and summary-recall sequencing stay in application**. |
| **`api/src/composition/`** | **`build_backend_composition`**, **`build_backend`**, **`chat_rag_wiring`**, **`evaluation_wiring`** (**`EvaluationWiringParts`** + **`build_evaluation_service`**), **`BackendApplicationContainer`**. **No** frontend **`services`** imports. |
| **`api/src/interfaces/http/`** | FastAPI routers, schemas, **`dependencies.py`** → container / use cases; identity types from **`domain`**. Routers **must not** import **`infrastructure.*`**. |
| **`frontend/src/services/`** | **`BackendClient`**, HTTP and in-process clients, Streamlit factory + session transcript; **only** **`infrastructure.config`** and **`infrastructure.auth`** from backend infra (not adapters). |
| **`frontend/app.py`**, **`frontend/src/pages/`**, **`frontend/src/components/`** | Streamlit UI; **only** gateway + auth + view models toward the backend — no direct `domain` / `application` / `composition` / `interfaces` imports from pages/components. |

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
| Application does not import concrete infrastructure (outside `infrastructure.config`) | **Met** — `test_layer_import_rules.py` |
| Infrastructure adapters do not import application | **Met** — `test_adapter_application_imports.py` (no allowlist) |
| Gold-QA benchmark stack not constructed inside `EvaluationService` | **Met** — `evaluation_wiring.py` + `GoldQaBenchmarkAdapter` |
| Query-log / judge row DTOs in domain | **Met** — `QueryLogIngressPayload`, `EvaluationJudgeMetricsRow` |
| **`interfaces/http`** → routers no `infrastructure.*`; package avoids legacy paths | **Met** — `test_fastapi_migration_guardrails.py` |
| Gateway does not import infrastructure | **Met** — layer + gateway guardrails |
| Chat RAG uses **ports** for inspect / answer generation where required | **Met** — `test_application_chat_rag_boundary_ports.py` |
| Chat / eval / RAG-DTO subtrees avoid infra + delivery stacks | **Met** — `test_orchestration_package_import_boundaries.py` |
| Repo lint/format/typing config present for contributors | **Met** — `pyproject.toml` (Ruff, Black, mypy, pytest defaults) + `ruff` / `pytest` in `requirements.txt` |
| CI enforces architecture tests + Ruff on `api/src` / `frontend/src` | **Met** — `.github/workflows/ci.yml` + `scripts/validate.sh` / `validate.ps1` (**§14**) |

---

## 3. What was already strong (baseline)

Before the late hardening passes, the codebase already had:

- A **clear layer layout**: `domain` ports, `application` use cases and RAG orchestration modules, `infrastructure` adapters, `composition` wiring, FastAPI under `api/src/interfaces/http/`, and a **gateway** in **`frontend/src/services`** for Streamlit.
- **RAG orchestration** owned in application (`summary_recall_workflow`, `recall_then_assemble_pipeline`, post-recall steps) instead of a monolithic infrastructure façade.
- **Architecture tests** (`api/tests/architecture/`) catching the worst regressions (API importing infra, application importing LangChain, removed legacy packages).
- **Evaluation** wired through **`GoldQaBenchmarkAdapter`** and **`BenchmarkExecutionUseCase`** with an explicit **`RagInspectAnswerRun`** contract.

The remaining work was **contract tightness**, **transport clarity**, and **long-term guardrails** — not a rewrite.

---

## 4. Recent documentation / architecture passes (chronological, high level)

- **Ports and adapters** — **`RetrievalPort`**, **`AnswerGenerationPort`** (and aliases as documented in domain ports); inspect and generate-from-pipeline use cases depend on protocols, not concrete infra.
- **Evaluation wiring** — **`EvaluationWiringParts`**, **`default_evaluation_wiring_parts()`**, **`build_evaluation_service(parts)`**; **`RagInspectAnswerRun`**-only **`pipeline_runner`** contract in **`BenchmarkExecutionUseCase`**.
- **Composition root** — explicit **`chat_transcript`** and **`backend`** parameters; RAG subgraph construction centralized (**`build_rag_retrieval_subgraph`** always builds **`AnswerGenerationService`** internally).
- **Multimodal hints** — orchestration-adjacent logic in **`api/src/application/chat/multimodal_prompt_hints.py`** (injected from **`chat_rag_wiring`**), not a fat infrastructure façade.
- **API layer purity** — **`api/src/interfaces/http/dependencies.py`** uses **`application.frontend_support.memory_chat_transcript.MemoryChatTranscript`** so the HTTP delivery package never imports infrastructure adapters; **`get_authenticated_principal`** delegates JWT verification to **`AuthenticationPort`** from the composition root; auth and **`/users`** routes use application use cases and **`AuthenticatedPrincipal`**.
- **Docs** — this report, **`docs/architecture.md`** diagram, **`dependency_rules`**, **`rag_orchestration`**, **`ARCHITECTURE_TARGET`** aligned with the above.
- **Structural exceptions (final standard)** — **`test_adapter_application_imports.py`** enforces **zero** `application` imports under **`api/src/infrastructure/adapters`** (the old **`rag/retrieval_settings_service.py`** allowlist is gone). **`RetrievalSettingsTuner`** is constructed in **`backend_composition`** and passed as **`retrieval_settings_tuner`**. **`MemoryChatTranscript`** exists only under **`api/src/application/frontend_support`**. **`AuthenticatedPrincipal`**, **`AuthenticationPort`**, and **`AccessTokenIssuerPort`** live under **`api/src/domain/`** so the JWT adapter does not depend on **`application`** use-case modules.

---

## 5. Removed components (cumulative)

| Removed | Notes |
|---------|--------|
| **`infrastructure/adapters/rag/rag_service.py`** (historical path) | Legacy orchestration façade |
| **`infrastructure/adapters/rag/pipeline_assembly_service.py`** | Post-recall assembly moved to application |
| **`infrastructure/adapters/rag/summary_recall_adapter.py`** | Replaced by app workflow + **`summary_recall_technical_adapters.py`** |
| **`infrastructure/adapters/evaluation/benchmark_report_service.py`** | Callers use **`BuildBenchmarkExportArtifactsUseCase`** |
| **`api/src/backend/`**, **`api/src/adapters/`**, **`infrastructure.services/`** | Legacy trees; directory + import guardrails |
| Top-level **`api/src/services/`** package (monolith-style) | Removed / guarded |
| Legacy **`ragcraft_app`** / monolithic app wrapper | Removed; composition + API entrypoints only |
| **`src/application/chat/ports.py`** | Unused re-export barrel |
| **`src/application/common/query_log_payload.py`**, **`evaluation_judge_metrics.py`** | Obsolete re-exports; domain types are canonical |
| **`tests/architecture/test_rag_adapter_application_imports.py`** | Superseded by **`test_adapter_application_imports.py`** |
| **`BenchmarkExecutionUseCase._coerce_gold_qa_runner_result`** | **Removed** — runner must return **`RagInspectAnswerRun`** |
| **Trusted `X-User-Id` header** | **Removed** — replaced by **`Authorization: Bearer`** + **`JwtAuthenticationAdapter`** implementing **`AuthenticationPort`** / **`AccessTokenIssuerPort`** |
| **`rag/retrieval_settings_service.py`** | **Removed** — empty infra subclass of **`RetrievalSettingsTuner`**; composition constructs **`RetrievalSettingsTuner`** directly (**`retrieval_settings_tuner`** on **`BackendComposition`**) |
| **`src/infrastructure/adapters/chat_transcript/`** | **Removed** — duplicate **`MemoryChatTranscript`**; callers use **`application/frontend_support/memory_chat_transcript.py`** |
| **`application/auth/{authenticated_principal,authentication_port,access_token_issuer_port}.py`** (historical) | **Moved** — canonical types under **`api/src/domain/authenticated_principal.py`** and **`api/src/domain/ports/authentication_port.py`**, **`access_token_issuer_port.py`** |

---

## 6. Acceptable residual detail (intentional)

| Item | Rationale |
|------|-----------|
| ~~**`ManualEvaluationService.evaluate_question`**~~ | **Removed** — manual eval uses **`RunManualEvaluationUseCase`** only (see §11b) |
| **`import_legacy_file_logs`** on **`QueryLogService`** | One-off migration utility |
| **JWT operational model** | Single access token (HS256), no refresh-token rotation or OAuth2 provider in-repo — product choice for a later pass |
| Architecture **line-count ratchets** in `test_orchestration_boundaries.py` | Prevents silent growth of coordinator modules |

---

## 7. Remaining risks (non-architectural)

These do **not** invalidate the migration but are worth tracking:

- **AuthN/AuthZ:** Symmetric JWTs require **`RAGCRAFT_JWT_SECRET`** rotation discipline, HTTPS in production, and optional issuer/audience tightening. **`TrustedTransportIdentityPort`** remains for non-JWT bridges if needed.
- **Operational drift:** Contributors may reintroduce **`infrastructure.*`** imports under **`interfaces/http/routers/`** or legacy roots; **`pytest api/tests/architecture/`** in CI reduces regression risk.
- **Duplicate eval paths:** **Closed for manual evaluation** — only **`RunManualEvaluationUseCase`** orchestrates; **`manual_evaluation_service`** is assembly-only.
- **Third-party weight:** Heavy optional stacks (e.g. ingestion) can still complicate test envs; architecture tests are **import-level**, not full integration proof.

---

## 8. Is the migration “complete”?

**Verdict: yes — the Clean Architecture migration is complete for this repository’s stated scope.** The codebase matches the target layering, dependency direction, and orchestration ownership described in **`docs/architecture.md`**, **`docs/dependency_rules.md`**, and **`docs/rag_orchestration.md`**, and **§10** / **§14** describe how that state is enforced in CI and locally.

**Auth / users (final model):** **`AuthenticatedPrincipal`**, **`AuthenticationPort`**, and **`AccessTokenIssuerPort`** are **domain** types (`api/src/domain/`). The API uses **`get_authenticated_principal` → `AuthenticationPort.authenticate_bearer_token` → `AuthenticatedPrincipal`**. Transport parses **`Authorization: Bearer`** in **`api/src/interfaces/http/dependencies.py`**; **`JwtAuthenticationAdapter`** implements both ports and validates HS256 JWTs (**`RAGCRAFT_JWT_SECRET`**). The trusted **`X-User-Id`** header is **removed**. Login/register issue tokens via **`AccessTokenIssuerPort`**. **`/users/*`** goes through account use cases; hashing and avatar storage use **`PasswordHasherPort`** / **`AvatarStoragePort`**.

**RAG orchestration (final model):** Application-owned sequencing (**`ApplicationSummaryRecallStage`**, **`ApplicationPipelineAssembly`**, **`post_recall_pipeline_steps`**); infrastructure supplies single-step adapters. Typed boundaries: **`RetrievalSettingsOverrideSpec`**, **`VectorLexicalRecallBundle`**, **`RagEvaluationPipelineInput`**, **`RagInspectAnswerRun`** / **`PipelineLatency`**, **`GoldQaPipelineRowInput`**. **`InspectRagPipelineUseCase`** shares **`BuildRagPipelineUseCase`** with **`emit_query_log=False`**.

**Upload / ingestion (final model):** Bounded chunked buffering via **`api/src/interfaces/http/upload_adapter.py`** → **`BufferedDocumentUpload`** → use cases; documented in **`api/src/application/ingestion/upload_boundary.py`** and **`docs/api.md`**. Avatars share the same transport pattern with a smaller byte cap.

**Evaluation (final model):** Single manual-eval orchestrator (**`RunManualEvaluationUseCase`**). Gold-QA via **`BenchmarkExecutionUseCase`** and **`RagInspectAnswerRun`** only. **`test_manual_evaluation_single_orchestrator.py`** guards against a second orchestration class on the manual-eval infrastructure module.

**Explicitly not claimed as “done”:** production security program (beyond bearer JWT design), performance SLOs, **mypy strict** on the full tree, and typed rows for every SQLite list endpoint — see **§6**, **§7**, and **§9**.

---

## 9. Post-migration improvements (optional backlog)

- **Security:** Add refresh tokens, asymmetric signing (JWKS), or an external IdP; rate-limit **`/auth/login`**.
- **Performance:** Caching, batching, async retrieval, index maintenance.
- **DX:** Keep **`README.github.md`** diagrams aligned with **`docs/architecture.md`**.
- **Typing:** Tighten **mypy** beyond incremental packages when convenient; **`src.domain`** is not yet error-free under strict checking.

---

## 10. Tests and architecture guards

**Local / CI:** from repo root with **`PYTHONPATH`** including **`api/src`**, **`frontend/src`**, and **`api/tests`** (see **`.github/workflows/ci.yml`**):

```bash
./scripts/validate.sh
# Architecture-only:
./scripts/validate_architecture.sh
# Windows PowerShell:
# .\scripts\validate.ps1
```

Equivalent manual steps:

```bash
ruff check api/src frontend/src api/tests/architecture
pytest api/tests/architecture/ -q
```

| Concern | Module(s) |
|---------|-----------|
| Physical layout + delivery tree | **`test_repository_structure.py`**, **`test_fastapi_delivery_boundaries.py`**, **`test_frontend_structure.py`** |
| Layer directions | **`test_layer_import_rules.py`**, **`test_layer_boundaries.py`**, **`test_application_orchestration_purity.py`** |
| Legacy paths | **`test_deprecated_backend_and_gateway_guardrails.py`**, **`test_legacy_app_wrapper_removed.py`** |
| FastAPI | **`test_fastapi_migration_guardrails.py`** |
| Composition | **`test_composition_import_boundaries.py`** |
| RAG façade absent; adapters vs chat use case classes | **`test_no_rag_service_facade.py`** |
| Post-recall / transport RAG imports | **`test_orchestration_boundaries.py`** |
| **All adapters** → **no** `src.application` imports | **`test_adapter_application_imports.py`** |
| Chat RAG port names / boundaries | **`test_application_chat_rag_boundary_ports.py`** |
| UI surface | **`test_frontend_structure.py`**, **`test_fastapi_migration_guardrails.py`** |
| Smoke `build_backend` | **`test_migration_regression_flows.py`** |
| Orchestration subtrees (chat/eval/rag) | **`test_orchestration_package_import_boundaries.py`** |
| Manual evaluation single orchestrator | **`test_manual_evaluation_single_orchestrator.py`** |

**Multipart / upload:** `application` must not import **FastAPI** or **Starlette** (`test_application_orchestration_purity.py`); ingest use cases accept **`BufferedDocumentUpload`** only. Transport reads live in **`api/src/interfaces/http/upload_adapter.py`** (see §12).

---

## 11. RAG orchestration typed contracts (orchestration hardening)

This pass removed loose retrieval-settings ``dict`` shapes from core RAG orchestration boundaries and formalized DTOs for recall fusion and evaluation input.

| Removed / tightened | Replacement |
|--------------------|-------------|
| ``retrieval_settings: dict[str, Any] \| None`` on **`RetrievalPort.execute`**, **`SummaryRecallStagePort`**, **`RAGPipelineQueryContext`**, **`run_recall_then_assemble_pipeline`**, chat use cases | **`RetrievalSettingsOverrideSpec \| None`** (domain); validated partial merge mapping keyed only to **`RetrievalSettings`** fields |
| Ad hoc recall fusion return shape | **`VectorLexicalRecallBundle`** in **`api/src/application/rag/dtos/recall_stages.py`** |
| Untyped evaluation orchestration inputs | **`RagEvaluationPipelineInput`** |
| **`RagInspectAnswerRun`** → row evaluation as anonymous ``dict`` | **`as_row_evaluation_input()` → `GoldQaPipelineRowInput`**; **`BenchmarkRowProcessingPort.process_row`** takes that DTO |
| **`PipelineBuildResult.latency`** as ``dict[str, float]`` | **`PipelineLatency`** (merged after answer on ask/eval paths; **`PipelineBuildResult.to_dict()`** still emits a JSON object for wire) |
| **`RAGResponse.latency`** as loose dict | **`PipelineLatency \| None`**; **`RagAnswerWirePayload`** / API serialization call **`to_dict()`** at the transport edge |
| **`latency_stage_row_fields`** input shape | **`PipelineLatency \| None`** (benchmark row **`data`** remains a wide metric map for aggregation/export) |
| **`full_latency_dict`** on manual-eval assembly | **`full_latency: PipelineLatency \| None`** on **`ManualEvaluationFromRagPort`** and **`manual_evaluation_result_from_rag_outputs`** |
| **`ManualEvaluationPipelineSignals.stage_latency`** as ``dict[str, float]`` | **`PipelineLatency \| None`**; **`manual_evaluation_result_from_plain_dict`** maps JSON ``stage_latency`` back to **`PipelineLatency`** |
| **`to_row_evaluation_dict()`** on **`RagInspectAnswerRun`** | **Removed** in favor of **`as_row_evaluation_input()`** |

**Where plain dicts remain (by design):**

- **`BenchmarkRow.data`** — wide per-row metric map for summaries, CSV export, and correlation helpers (not the runner→row-processor boundary).
- **HTTP JSON** — FastAPI/Pydantic and **`rag_response_to_wire_dict`** use dict-shaped latency only after mapping from **`PipelineLatency`**.

**Execution modes (unchanged intent, clearer contracts):**

| Mode | Use case / entry | Query log | Answer generation |
|------|------------------|-----------|-------------------|
| Product ask | **`AskQuestionUseCase`** | Yes (via **`QueryLogPort`** / safe helpers, deferred) | Yes |
| Inspect | **`InspectRagPipelineUseCase`** | **No** (`emit_query_log=False`) | **No** |
| Preview recall | **`PreviewSummaryRecallUseCase`** | **No** | **No** (stops at recall; **`SummaryRecallPreviewDTO`**) |
| Evaluation | **`execute_rag_inspect_then_answer_for_evaluation`** | **No** | Yes, via **`GenerateAnswerFromPipelinePort`**; returns **`RagInspectAnswerRun`** for **`BenchmarkExecutionUseCase`** |

**Future hardening (optional):** Gateway HTTP client method signatures may still accept ``dict`` for ``retrieval_settings`` as transport-only JSON; tightening those to a shared wire type would be cosmetic unless validation is duplicated outside the API boundary.

### 11b. Manual evaluation — single orchestrator (final)

| Before | After |
|--------|--------|
| **`ManualEvaluationService.evaluate_question`** duplicated inspect → answer → latency → gold-QA benchmark → **`manual_evaluation_result_from_eval_row`** alongside **`RunManualEvaluationUseCase`** | **Removed** class; one path only |

**Canonical flow:** **`RunManualEvaluationUseCase.execute`** → **`execute_rag_inspect_then_answer_for_evaluation`** → **`ManualEvaluationFromRagPort.build_manual_evaluation_result`** (**`EvaluationService`**, which calls **`manual_evaluation_result_from_rag_outputs`** / row assembly in **`manual_evaluation_service.py`**).

**Ownership:** Application use case owns the scenario; **`EvaluationService`** is a façade over **`GoldQaBenchmarkPort`** + manual-result assembly; **`manual_evaluation_service` module** holds pure helpers and **`manual_evaluation_result_from_rag_outputs`**, not a second orchestration entry point.

**Enforcement:** **`api/tests/architecture/test_manual_evaluation_single_orchestrator.py`** asserts **`ManualEvaluationService`** is not reintroduced on that module.

---

## 12. Ingestion, project document details, and evaluation wire (API / application hardening)

**Multipart upload boundary (documents + avatars)**

- **Final strategy (explicit):** **bounded chunked buffering** — reads proceed in **1 MiB** slices while tracking cumulative size; if the cap is exceeded, the adapter raises **before** buffering the remainder. After a successful read, bytes are concatenated in memory for the application. This is **not** true streaming from the socket into extraction or indexing.
- **Canonical module:** **`api/src/application/ingestion/upload_boundary.py`** documents the contract; transport implementation is **`api/src/interfaces/http/upload_adapter.py`** (**`read_buffered_document_upload`**, **`read_buffered_avatar_upload`** sharing **`_read_starlette_upload_bounded`**).
- **Documents:** cap **`INGESTION_CONFIG.max_upload_bytes`** (**`RAG_MAX_UPLOAD_BYTES`**, default 100 MiB) → **HTTP 413** on oversize → **`IngestUploadedFileCommand`** / **`validate_buffered_document_upload`** (defense in depth).
- **Avatars:** cap **`USER_PROFILE_UPLOAD_CONFIG.max_avatar_bytes`** (**`RAG_MAX_AVATAR_UPLOAD_BYTES`**, default 2 MiB); routers no longer use raw **`await file.read()`**. **`UploadUserAvatarCommand`** carries **`BufferedDocumentUpload`** only; **`validate_buffered_avatar_upload`** (`api/src/application/users/avatar_upload_policy.py`) + **`FileAvatarStorage`** (infrastructure) enforce format and size again at save time.
- **Domain:** **`BufferedDocumentUpload`** — shared typed payload for both flows after transport adaptation.
- **On-disk pipeline:** Document extraction still runs from a **persisted file**; streaming multipart directly into unstructured is **not** implemented.
- **Lazy unstructured imports:** **`src/infrastructure/ingestion/unstructured_extractor.py`** imports **`unstructured`** chunking/partition entry points **on first extraction**, not at module import time, so **`create_app()`** / **`BackendApplicationContainer`** construction does not pull optional partition backends (e.g. **pdfminer**) until a document is actually parsed. A full **`requirements.txt`** install remains required for real PDF/DOCX/PPTX extraction.

**Settings**

- Retrieval GET/PUT already used **`EffectiveRetrievalSettingsView`** + **`EffectiveRetrievalSettingsWirePayload`**; **`src/application/settings/dtos.py`** docstrings now spell out query/command/view roles and wire mapping.

**Row-dict leakage reduced**

- **`GetProjectDocumentDetailsUseCase`** returns **`list[ProjectDocumentDetailRow]`** (`api/src/application/projects/dtos.py`); the projects router maps rows via **`project_document_detail_row_to_item`** (`api/src/interfaces/http/schemas/mappers.py`).
- **QA dataset generation:** **`ProposedQaDatasetRow`** (domain), **`QaDatasetGenerationPort`** returns typed proposals, **`GenerateQaDatasetResult`** (`api/src/application/evaluation/dtos.py`), **`QaDatasetGenerateWirePayload`** for FastAPI **`QaDatasetGenerateResponse`**. **`BenchmarkExportBundleWirePayload`** wraps **`BenchmarkExportArtifacts.to_http_bundle_dict()`** for the export ``all`` format.

**Residual**

- **SQLite asset listing** for document assets is still ``list[dict]`` from the repository; a typed asset row model can follow the same pattern as document details.
- **`ListRetrievalQueryLogsUseCase`** / log entries may remain dict-shaped at the HTTP mapper where the store is JSON-oriented.

---

## 13. Repository tree (main folders)

```text
api/
  main.py               # ASGI entry (uvicorn)
  src/
    auth/
    composition/        # backend_composition, evaluation_wiring, application_container, chat_rag_wiring, wiring
    core/
    domain/
    application/
      use_cases/        # chat (orchestration/), evaluation, ingestion, projects, retrieval, settings
      rag/
      chat/
      frontend_support/
      http/
    infrastructure/
      adapters/
      persistence/
      vectorstores/
    interfaces/
      http/             # FastAPI app, routers, schemas, dependencies, upload_adapter
  tests/
    architecture/
    api/
    appli/
    composition/
    domain/
    e2e/
    infra/
frontend/
  app.py                # Streamlit entry
  src/
    pages/
    components/
    services/           # BackendClient, HTTP/in-process clients, Streamlit factories
    state/
    utils/
  tests/
docs/
scripts/
data/
```

---

## 14. Lock-in (CI and validation — first-class scripts)

**Goal:** Structural and import drift fails **immediately** in CI and is **trivial to run locally** with the same entrypoints.

### How drift is prevented

1. **`api/tests/architecture/`** — blocking pytest package (layout, required skeleton, import boundaries, FastAPI/Streamlit rules). This is the **authoritative** architecture gate.
2. **`.github/workflows/ci.yml`** — calls the same shell scripts as developers (see below), then runs additional **unittest** discover jobs and a Streamlit boot smoke check.
3. **Documentation** — **`README.md`**, **`docs/README.md`**, **`docs/testing_strategy.md`**, and **`docs/dependency_rules.md`** list the **exact** commands.

### Commands (repository root)

| Script | Behavior |
|--------|----------|
| **`scripts/validate_architecture.sh`** | **`pytest api/tests/architecture`** only; **`set -euo pipefail`**; **`PYTHONPATH=api/src:frontend/src:api/tests`**. |
| **`scripts/lint.sh`** | **`ruff check`** on **`api/src`**, **`frontend/src`**, **`api/tests/architecture`**. |
| **`scripts/validate.sh`** | **`lint.sh`** then **`validate_architecture.sh`** (quick CI-style check). |
| **`scripts/run_tests.sh`** | **`validate_architecture.sh`**, then **`pytest api/tests --ignore=api/tests/architecture frontend/tests`** (architecture is **not** run twice). |

**Windows:** **`scripts/validate_architecture.ps1`**, **`lint.ps1`**, **`validate.ps1`**, **`run_tests.ps1`** mirror the bash scripts.

**CI mapping:** **`.github/workflows/ci.yml`** runs **`bash scripts/lint.sh`**, **`bash scripts/validate_architecture.sh`**, then the same non-architecture **pytest** line as step 2 of **`run_tests.sh`**, plus **unittest** jobs. You can reproduce the pytest portion locally with **`./scripts/run_tests.sh`**.

**Optional `cd api` workflow:** **`api/pyproject.toml`** configures pytest to run only **`tests/architecture`** when pytest is invoked from the **`api/`** directory.

| Config | Role |
|--------|------|
| **Root `pyproject.toml`** | **`[tool.pytest.ini_options]`** — default **`testpaths`**, **`pythonpath`** when running pytest from repo root. |
| **`api/pyproject.toml`** | Narrow pytest defaults for backend-only architecture runs. |

**Optional typing:** incremental **`mypy`** — not part of **`lint.sh`**; see **`docs/testing_strategy.md`**.

---

## Final verdict (architecture maturity — declaration of completion)

This repository **meets the completion standard** for the **Clean Architecture migration** as defined in this report and **`ARCHITECTURE_TARGET.md`**:

- **Enforced boundaries:** Layering, adapter purity (no **`src.application`** inside **`src/infrastructure/adapters`**), FastAPI isolation from infrastructure, gateway/UI isolation from domain and composition, and RAG orchestration folder purity are **checked by automated tests** (**§10**, **§14**).
- **Documented end state:** **`docs/architecture.md`**, **`docs/dependency_rules.md`**, **`docs/testing_strategy.md`**, **`docs/api.md`**, **`docs/rag_orchestration.md`**, and this file are **aligned with the current code** after the lock-in pass.
- **Honest scope:** Remaining items are **product or incremental-quality** work (**§6**, **§7**, **§9**), not missing migration steps.

The codebase is **ready for feature development** on top of this architecture without further structural migration passes unless requirements change materially.

Treat **§7** (risks) and **§6** (acceptable residual) as the living registers for operations and follow-up quality work.
