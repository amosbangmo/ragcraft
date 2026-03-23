# Product features matrix

This matrix ties **user-visible capabilities** to **HTTP routes**, **schemas (DTOs)**, **error handling**, **tests**, and **Streamlit integration**. It is the reference for “what the product supports” and how it is verified.

**Conventions (API):**

- **Auth:** Scoped routes require **`Authorization: Bearer <JWT>`**. Public: **`/health`**, **`/version`**, **`/auth/login`**, **`/auth/register`**, OpenAPI docs.
- **`project_id`:** In JSON bodies for chat and evaluation POSTs, use non-empty strings (**`min_length=1`** in Pydantic). Resource routes use **`/projects/{project_id}/...`** path parameters.
- **Errors:** JSON envelope with **`detail`**, **`message`**, **`error_type`**, **`code`**, **`category`** (see **`docs/api.md`**).

---

## Matrix

| Feature | User outcome | Auth | Primary routes | HTTP / DTOs | Canonical errors | API tests | Frontend |
|--------|----------------|------|----------------|-------------|-------------------|-----------|----------|
| **Login** | JWT + user summary | Public | **`POST /auth/login`** | Body: credentials; response: token + user | **`401`** invalid creds; **`422`** validation | **`test_auth_router.py`** | **`streamlit_auth`**, **`http_client`** |
| **Register** | Account + token | Public | **`POST /auth/register`** | Registration body | **`400`** auth validation (e.g. password mismatch); **`422`** | **`test_auth_router.py`** | Same |
| **Profile / account** | Read/update self, avatar | Bearer | **`GET/PATCH /users/me`**, **`POST /users/me/avatar`** | User schemas; multipart avatar | **`413`** oversized avatar; **`401`** | **`test_users_router.py`** (if present) or core routes | Profile pages, HTTP client |
| **Project list / create** | See and add projects | Bearer | **`GET /projects`**, **`POST /projects`** | Project list/create DTOs | **`409`** duplicate; domain **`400`** | **`test_core_routes.py`**, **`test_projects_router.py`** | Projects UI |
| **Retrieval settings** | Effective settings + updates | Bearer | **`GET /projects/{id}/retrieval-settings`**, **`PATCH ...`** | **`EffectiveRetrievalSettings`**, update command wire | Validation / domain | Appli + API as wired | Settings pages via **`api_contract_models`** |
| **Document ingestion** | Upload + stable result | Bearer | **`POST /projects/{id}/documents/ingest`** | Multipart **`file`** → ingest result DTO | **`413`** size; **`503`** vector; **`401`** | **`test_core_routes.py`** (ingest paths) | Upload UI |
| **Document lifecycle** | List / delete docs as exposed | Bearer | Project document routes under **`/projects/{id}/...`** | List/delete responses | **`404`** / domain | Core / projects tests | Document browser |
| **Ask** | RAG answer | Bearer | **`POST /chat/ask`** | **`ChatPipelineRequestBase`**: **`project_id`**, **`question`**, optional **`filters`**, **`retrieval_settings`**, overrides | **`502`** LLM; **`503`** vector; **`400`** domain; **`422`** validation | **`test_core_routes.py`** | **`http_client`**, ask pages |
| **Inspect pipeline** | Pipeline snapshot | Bearer | **`POST /chat/pipeline/inspect`** | Same base body shape as ask | Same family as ask | **`test_core_routes.py`** | Inspector UI |
| **Preview summary recall** | Recall preview DTO | Bearer | **`POST /chat/pipeline/preview-summary-recall`** | Preview request body | Infrastructure errors | **`test_core_routes.py`** | Preview UI |
| **Manual evaluation** | Structured eval result | Bearer | **`POST /evaluation/manual`** | **`ManualEvaluationRequest`** → **`ManualEvaluationResponse`** | **`502`** judge/LLM; **`503`** | **`test_core_routes.py`** | Evaluation dashboard |
| **Benchmark run** | **`BenchmarkResult`** wire | Bearer | **`POST /evaluation/dataset/run`** | **`DatasetBenchmarkRunRequest`** → **`BenchmarkResultResponse`** | Same infra mapping | **`test_core_routes.py`** | Benchmark UI |
| **Benchmark export** | Download bundle / metadata | Bearer | **`POST /evaluation/benchmark/export`**, export info if exposed | **`BenchmarkExportRequest`**, file responses | Domain / infra | Core routes + export tests | Export flow |
| **QA dataset CRUD** | Manage gold rows | Bearer | **`GET/POST/PATCH/DELETE`** under **`/evaluation/qa-dataset/...`** | Entry list/create/update/delete schemas | **`404`** / validation | Evaluation / API tests | QA dataset UI |
| **QA dataset generation** | Generated questions payload | Bearer | **`POST /evaluation/qa-dataset/generate`** | **`QaDatasetGenerateRequest`** → **`QaDatasetGenerateResponse`** | LLM / domain | API + appli where covered | Generation UI |
| **Retrieval query logs** | Log rows for debugging | Bearer | Listing under **`/evaluation`** (retrieval logs) | **`RetrievalLogsResponse`** | Auth / empty | API tests | Optional / admin-style |

---

## Retrieval settings → RAG behavior

Updates via **`PATCH /projects/{project_id}/retrieval-settings`** feed **effective settings** used by **`AskQuestionUseCase`**, inspect, preview, and evaluation paths unless a request supplies **`retrieval_settings`** / **`enable_*_override`** in the body. Orchestration details: **`docs/rag_orchestration.md`**.

---

## Frontend contract

Streamlit must use **`frontend/src/services/api_client.py`** and wire parsers (**`http_payloads.py`**, **`evaluation_wire_parse.py`**) — not **`domain`** or **`application.dto`** on the HTTP path. Route literals are guarded by **`frontend/tests/streamlit/test_http_client_route_contract.py`** and **`test_frontend_api_contract.py`**.

---

## Related docs

- **`docs/api.md`** — runbook, auth, uploads, error envelope, Streamlit env vars  
- **`docs/testing_strategy.md`** — pytest layout and markers  
- **`docs/migration_report_final.md`** — closure and feature-quality iterations (e.g. §17)
