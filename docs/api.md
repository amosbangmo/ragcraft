# HTTP API (FastAPI)

The HTTP API is implemented under **`api/src/interfaces/http/`** (routers, schemas, dependencies, upload helpers). The ASGI application object is built by **`create_app()`** in that package and exposed as **`app`** from **`api/main.py`** for Uvicorn.

**Regression tests:** **`api/tests/bootstrap/test_asgi_entrypoint.py`** asserts **`api/main.py`** still wires **`interfaces.http.main:create_app`**, that **`create_app()`** serves **`/health`** and **`/openapi.json`**, and that the **`api/main.py`** file can be executed like Uvicorn (without conflicting with the **`api`** test package on **`PYTHONPATH`**). HTTP contracts live under **`api/tests/api/`** (e.g. **`test_core_routes.py`**, **`test_http_pipeline_e2e.py`**).

**Run locally (repository root on `PYTHONPATH` so the `api` package resolves):**

```bash
export PYTHONPATH="$(pwd)"   # Linux / macOS / Git Bash
python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

**PowerShell:**

```powershell
$env:PYTHONPATH = (Get-Location).Path
python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

Set **`RAGCRAFT_JWT_SECRET`** (see below) before starting the server.

---

## Authentication

1. **Obtain a token** — `POST /auth/login` or `POST /auth/register` with JSON credentials. The response includes:
   - **`access_token`** — JWT for subsequent requests  
   - **`token_type`** — always **`bearer`**  
   - **`user`** — profile summary (`user_id`, `username`, …)

2. **Call scoped routes** — send:

   `Authorization: Bearer <access_token>`

   Typical scoped areas: **`/users/me`**, **`/projects`**, **`/chat/*`**, **`/evaluation/*`** (unless a route is explicitly public).

   **Types:** **`AuthenticatedPrincipal`**, **`AuthenticationPort`**, and **`AccessTokenIssuerPort`** live under **`api/src/domain/`** (e.g. **`domain/auth/`**, **`domain/common/ports/`**).  
   **`api/src/interfaces/http/dependencies.py`** obtains **`AuthenticationPort`** from the composition root; routers depend on **`AuthenticatedPrincipal`** via **`Depends`**, not on infrastructure types.

3. **Configuration**

   - **`RAGCRAFT_JWT_SECRET`** (required) — symmetric key for HS256 signing and verification.  
   - Optional: **`RAGCRAFT_JWT_ISSUER`**, **`RAGCRAFT_JWT_AUDIENCE`**, **`RAGCRAFT_JWT_ALGORITHM`** (default **`HS256`**), **`RAGCRAFT_ACCESS_TOKEN_EXPIRE_MINUTES`**.

---

## Error envelope

Failures return JSON with at least: **`detail`**, **`message`**, **`error_type`**, **`code`**, **`category`**. Authentication problems typically use **`401`** (`authentication_required`, `invalid_token`, `expired_token`) or **`400`** (`malformed_authorization_header`).

---

## Multipart uploads (documents and avatars)

**Strategy:** bounded chunked buffering — the server reads **`UploadFile`** in chunks and enforces a maximum size before passing a **`BufferedDocumentUpload`** into use cases (not raw socket-to-parser streaming).

- **`POST /projects/{project_id}/documents/ingest`** — form field **`file`**. Implemented via **`interfaces.http.upload_adapter.read_buffered_document_upload`**, capped by **`RAG_MAX_UPLOAD_BYTES`** (default 100 MiB; see **`INGESTION_CONFIG.max_upload_bytes`**).  
- **`POST /users/me/avatar`** — form field **`file`**. Uses **`read_buffered_avatar_upload`**, capped by **`RAG_MAX_AVATAR_UPLOAD_BYTES`** (default 2 MiB). Oversized bodies → **HTTP 413**.

Canonical contract: **`api/src/application/ingestion/upload_boundary.py`**.

---

## OpenAPI

Interactive docs: **`/docs`** and **`/redoc`**. The schema includes **`BearerAuth`** (JWT) under **`components.securitySchemes`**.

---

## Route ownership

Routers live only under **`api/src/interfaces/http/routers/`**. Each route module should stay thin: validate input, resolve **`AuthenticatedPrincipal`** where required, call a use case from **`BackendApplicationContainer`**, and map results to Pydantic response types from **`api/src/interfaces/http/schemas/`**.

---

## API conventions (consistency)

- **`project_id` in JSON bodies** (chat, manual evaluation, benchmark run, etc.): required **non-empty string**; invalid or missing fields yield **`422`** with FastAPI validation detail (and, where configured, the shared error helper’s **`error_type`** / **`code`** for app-level errors).
- **`project_id` in paths** (`**/projects/{project_id}/**`): identifies the project resource; resolution failures map to the appropriate **`4xx`** / **`5xx`** via use cases and exception handlers.
- **Bearer JWT** on all scoped routes; omitting or sending a bad token yields **`401`** (or **`400`** for malformed `Authorization`), not **`5xx`**.
- **Multipart** document and avatar uploads use bounded readers and return **`413`** when over policy limits (see **Multipart uploads** above).

**Product ↔ route map (tests + Streamlit):** **`docs/product_features.md`**.

---

## Streamlit client (frontend) — canonical contract

The Streamlit app must not treat **`application.dto`** or **`domain`** types as the HTTP wire shape. Integration is owned by:

| Piece | Path | Role |
|-------|------|------|
| Public façade | **`frontend/src/services/api_client.py`** | Re-exports **`HttpBackendClient`**, **`get_backend_client`**, wire types, and transport helpers |
| HTTP implementation | **`frontend/src/services/http_client.py`** | Builds requests and parses JSON using **only** wire modules (no **`domain`** / **`application.dto`** imports on the hot path) |
| Wire DTOs | **`frontend/src/services/api_contract_models.py`** | Projects, chat (**`RAGAnswer`**), retrieval filters/settings, ingestion/QA payloads |
| Evaluation wire | **`frontend/src/services/evaluation_wire_models.py`**, **`evaluation_wire_parse.py`** | Manual eval + benchmark results from API JSON |
| JSON helpers | **`frontend/src/services/http_payloads.py`** | **`rag_answer_from_ask_api_dict`**, retrieval settings, QA generate, export artifacts, … |
| In-process mapping | **`frontend/src/services/client_wire_mappers.py`** | Maps domain/application results → wire types at the **`InProcessBackendClient`** boundary |

**Environment (local dev):** set **`RAGCRAFT_BACKEND_CLIENT`** to **`http`** (default), **`api`**, or **`remote`** to use **`HttpBackendClient`**; set **`RAGCRAFT_API_BASE_URL`** to the API root (no trailing slash), e.g. **`http://127.0.0.1:8000`**. Optional: **`RAGCRAFT_API_CONNECT_TIMEOUT_SECONDS`**, **`RAGCRAFT_API_READ_TIMEOUT_SECONDS`** (or legacy **`RAGCRAFT_API_TIMEOUT_SECONDS`**). The JWT from Streamlit session state is sent as **`Authorization: Bearer`** on scoped calls (**`services/http_transport.py`**).

**Errors:** non-success responses are turned into **`BackendHttpError`** or mapped **`RAGCraftError`** subclasses when **`error_type`** is present (**`services/http_error_map.py`**).
