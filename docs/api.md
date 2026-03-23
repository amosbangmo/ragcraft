# HTTP API (FastAPI)

## Authentication

1. **Obtain a token** — `POST /auth/login` or `POST /auth/register` with JSON credentials. The response includes:
   - `access_token` — JWT for subsequent requests
   - `token_type` — always `bearer`
   - `user` — profile summary (`user_id`, `username`, …)

2. **Call scoped routes** — send the header:

   `Authorization: Bearer <access_token>`

   Scoped areas include: **`/users/me`**, **`/projects`**, **`/chat/*`**, **`/evaluation/*`** (except routes explicitly documented as public, e.g. some export discovery endpoints).

3. **Configuration** — the API process requires a strong random secret:

   - **`RAGCRAFT_JWT_SECRET`** (required) — symmetric key for HS256 signing and verification.
   - Optional: **`RAGCRAFT_JWT_ISSUER`**, **`RAGCRAFT_JWT_AUDIENCE`**, **`RAGCRAFT_JWT_ALGORITHM`** (default `HS256`), **`RAGCRAFT_ACCESS_TOKEN_EXPIRE_MINUTES`**.

## Error envelope

Failures return JSON with at least: `detail`, `message`, `error_type`, `code`, `category`. Authentication problems typically use `401` (`authentication_required`, `invalid_token`, `expired_token`) or `400` (`malformed_authorization_header`).

## OpenAPI

Interactive docs: `/docs` and `/redoc`. The schema includes **`BearerAuth`** (JWT) under `components.securitySchemes`.
