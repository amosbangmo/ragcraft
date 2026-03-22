# Dependency rules

Import directions enforced in code and by **`tests/architecture/`** (AST scans). When in doubt, run:

```bash
pytest tests/architecture -q
```

## Allowed directions

| From | May import |
|------|------------|
| **Domain** | `src.core` (as established), stdlib, third-party **without** pulling app/infra (see tests for forbidden list) |
| **Application** | `src.domain`, `src.core`; **`frontend_support`** may use `src.frontend_gateway` for stubs only |
| **Infrastructure (non-adapter)** | Technical deps; **not** `src.application` (see `test_layer_boundaries`) |
| **Infrastructure adapters** | **Domain** always; **`src.application`** only where the codebase explicitly allows (see below) |
| **Composition** | Domain ports, infrastructure adapters, application use cases for typing/wiring; **not** `src.frontend_gateway` |
| **`apps/api`** | FastAPI, `src.composition`, `src.application` (types), **not** `streamlit`, **`src.infrastructure`** in routers |
| **`src/frontend_gateway`** | `src.composition`, `src.application` (DTOs/support), **not** `src.infrastructure` |
| **`pages/`, `src/ui/`** | `streamlit`, `src.frontend_gateway`, `src.auth`, view models; **not** `src.domain`, `src.infrastructure`, `src.composition`, `apps.api` |

### Infrastructure adapters (`src/infrastructure/adapters/`)

- Must **not** import **`src.application`** except files on the **explicit allowlist** in **`tests/architecture/test_adapter_application_imports.py`**.
- Today the only allowlisted file is **`rag/retrieval_settings_service.py`** (thin subclass of application **`RetrievalSettingsTuner`**).
- RAG adapters must **not** import chat **use case classes** from `src.application.use_cases.chat` (see **`test_no_rag_service_facade.py`**).

### Shared boundary types (query log, evaluation rows)

- **`QueryLogIngressPayload`** lives in **`src/domain/query_log_ingress_payload.py`** so query logging adapters accept the same typed shape the application builds without importing application modules.
- **`EvaluationJudgeMetricsRow`** lives in **`src/domain/evaluation/judge_metrics_row.py`** for benchmark row judge slices.
- Gold-QA benchmark **orchestration** (**`BenchmarkExecutionUseCase`**) is wired in **`src/composition/evaluation_wiring.py`**; **`GoldQaBenchmarkAdapter`** (application) implements **`GoldQaBenchmarkPort`** for **`EvaluationService`**.

## Anti-patterns

1. **Routers instantiating** `VectorStoreService`, `EvaluationService`, or other infra services — use **`Depends`** → container → use case.
2. **Application importing** `src.infrastructure` — wire in **`src/composition`**.
3. **Composition importing** `src.frontend_gateway` — use **`ChatTranscriptPort`** and pass **`StreamlitChatTranscript`** only from **`streamlit_backend_factory`**.
4. **Gateway importing** `src.infrastructure` — use **`application.frontend_support`** stubs for HTTP mode.
5. **Reintroducing** `src/backend`, `src/adapters`, `src/infrastructure/services` — removed; tests fail if directories or imports return.
6. **New `rag_service.py`** orchestration façade under infrastructure that constructs chat use cases — forbidden; see **`tests/architecture/test_no_rag_service_facade.py`**.

## Duplicate `MemoryChatTranscript`

- **`src/infrastructure/adapters/chat_transcript/memory_chat_transcript.py`** — default for **`build_backend_composition()`** (API process graph).
- **`src/application/frontend_support/memory_chat_transcript.py`** — **`http_client_chat_service()`** so **`src/application`** does not import **`src.infrastructure`** (layer test). Same behavior; intentional small duplication.
