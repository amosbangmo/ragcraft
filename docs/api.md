# HTTP API (FastAPI)

## Authentication

1. **Obtain a token** — `POST /auth/login` or `POST /auth/register` with JSON credentials. The response includes:
   - `access_token` — JWT for subsequent requests
   - `token_type` — always `bearer`
   - `user` — profile summary (`user_id`, `username`, …)

2. **Call scoped routes** — send the header:

   `Authorization: Bearer <access_token>`

   Scoped areas include: **`/users/me`**, **`/projects`**, **`/chat/*`**, **`/evaluation/*`** (except routes explicitly documented as public, e.g. some export discovery endpoints).

   **Types:** **`AuthenticatedPrincipal`**, **`AuthenticationPort`**, and **`AccessTokenIssuerPort`** are defined under **`src/domain/`** (see **`docs/architecture.md`**). **`apps/api/dependencies.py`** resolves the JWT adapter from the composition root; routers depend on **`AuthenticatedPrincipal`** via **`Depends`**, not on infrastructure.

3. **Configuration** — the API process requires a strong random secret:

   - **`RAGCRAFT_JWT_SECRET`** (required) — symmetric key for HS256 signing and verification.
   - Optional: **`RAGCRAFT_JWT_ISSUER`**, **`RAGCRAFT_JWT_AUDIENCE`**, **`RAGCRAFT_JWT_ALGORITHM`** (default `HS256`), **`RAGCRAFT_ACCESS_TOKEN_EXPIRE_MINUTES`**.

## Error envelope

Failures return JSON with at least: `detail`, `message`, `error_type`, `code`, `category`. Authentication problems typically use `401` (`authentication_required`, `invalid_token`, `expired_token`) or `400` (`malformed_authorization_header`).

## Multipart uploads (documents and avatars)

**Strategy:** **bounded chunked buffering** — not streaming from the socket into parsers or vector indexing.

- **`POST /projects/{project_id}/documents/ingest`** — form field **`file`**. The router calls **`apps.api.upload_adapter.read_buffered_document_upload`**, which reads **`UploadFile`** in 1 MiB chunks and aborts if **`RAG_MAX_UPLOAD_BYTES`** (default 100 MiB, see **`INGESTION_CONFIG.max_upload_bytes`**) would be exceeded. On success, the full body is buffered into domain **`BufferedDocumentUpload`**, then **`IngestUploadedFileUseCase`** runs (application validation + persist + extraction from disk).
- **`POST /users/me/avatar`** — form field **`file`**. Same adapter pattern via **`read_buffered_avatar_upload`**, capped by **`RAG_MAX_AVATAR_UPLOAD_BYTES`** (default 2 MiB, **`USER_PROFILE_UPLOAD_CONFIG.max_avatar_bytes`**). Oversized bodies return **HTTP 413**; unreadable streams return **400**. **`UploadUserAvatarCommand`** carries **`BufferedDocumentUpload`** only (no raw **`await file.read()`** in the router).

Canonical description of the boundary: **`src/application/ingestion/upload_boundary.py`**.

## OpenAPI

Interactive docs: `/docs` and `/redoc`. The schema includes **`BearerAuth`** (JWT) under `components.securitySchemes`.
