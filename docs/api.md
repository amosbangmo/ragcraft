# HTTP API (FastAPI)

The HTTP API is implemented under **`api/src/interfaces/http/`** (routers, schemas, dependencies, upload helpers). The ASGI application object is built by **`create_app()`** in that package and exposed as **`app`** from **`api/main.py`** for Uvicorn.

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
