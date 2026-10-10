# US-107 — Access Token Refresh: QA Testing Guide

**Sprint 1 · Identity & User Management**

Manual test cases for the refresh-token exchange endpoint, using Swagger UI against a local dev environment.

> **What this story ships:** a refresh endpoint that validates the submitted refresh token (signature, expiry, type, session not logged out) and the account's current standing, then reissues a new access+refresh pair with fresh `status`/`aadhaarVerified` values. Refresh tokens are **single-use**: each successful refresh replaces the session's stored token, and presenting an already-used token revokes the session (see `Documents/LLD/Sprint-1-Identity-User-Management-LLD.md` §14.7).

| Setting | Value |
|---|---|
| Base URL | `http://localhost:8080` |
| Swagger UI | `http://localhost:8080/swagger-ui.html` (tag: **Authentication**) |
| Endpoint under test | `POST /api/v1/auth/refresh` |
| Access token TTL | 3,600,000 ms (1 hour) — `application.yml` → `valuex.jwt.access-token-expiry` |
| Refresh token TTL | 604,800,000 ms (7 days) — `application.yml` → `valuex.jwt.refresh-token-expiry` |

---

## Prerequisites — Get a Refresh Token

Any completed auth flow issues one. Fastest path (see `US-001-Testing-Guide.md` for full detail):

1. `POST /api/v1/auth/register/initiate`
   ```json
   { "mobile": "9000000030", "termsAccepted": true, "consentGiven": true }
   ```
2. Read the OTP from the console log, then `POST /api/v1/auth/register/verify-mobile`
   ```json
   { "mobile": "9000000030", "otp": "XXXXXX" }
   ```
3. Copy both `data.accessToken` and `data.refreshToken` from the response. This endpoint is **public** (no `Authorize` step needed) — you pass the refresh token in the request body, not as a Bearer header.

Alternatively, if the test user already exists, use `US-106-Implementation-Plan.md`'s login flow (`POST /auth/login/initiate` → `POST /auth/login/verify-mobile`) to get a fresh refresh token without re-registering.

---

## Test Scenarios Overview

| TC | Scenario | Expected Result |
|---|---|---|
| TC-001 | Refresh with a valid refresh token | `200`, new `accessToken` + `refreshToken`, both different from the originals |
| TC-002 | Refreshed token reflects current DB state, not stale claims | `200`, `aadhaarVerified`/`status` match the account's latest state |
| TC-003 | Malformed / tampered refresh token | `400 ERROR_INVALID_REFRESH_TOKEN` |
| TC-004 | Access token submitted instead of a refresh token | `400 ERROR_WRONG_TOKEN_TYPE` |
| TC-005 | Expired refresh token | `400 ERROR_REFRESH_TOKEN_EXPIRED` |
| TC-006 | Account suspended after the refresh token was issued | `400 ERROR_ACCOUNT_SUSPENDED` |
| TC-007 | Account banned/closed after the refresh token was issued | `400 ERROR_ACCOUNT_RECOVERY_REQUIRED` |
| TC-008 | Refresh token used a second time | `400 ERROR_INVALID_REFRESH_TOKEN`, session revoked |
| TC-009 | Refresh token rejected when used as a Bearer access token | `401`, protected endpoint denies the request |
| TC-010 | Missing `refreshToken` in request body | `400`, Jakarta validation error |

---

## TC-001 — Refresh With a Valid Refresh Token

**Endpoint:** `POST /api/v1/auth/refresh` *(public — no Bearer token needed)*

**Request body:**
```json
{ "refreshToken": "eyJhbGci..." }
```
> Use the `refreshToken` from the Prerequisites step.

**Expected response (200 OK):**
```json
{
  "success": true,
  "data": {
    "accessToken": "eyJhbGci...",
    "refreshToken": "eyJhbGci...",
    "aadhaarVerified": false,
    "userId": "uuid-here",
    "status": "EMAIL_VERIFICATION_PENDING"
  }
}
```

**Verify:** both `accessToken` and `refreshToken` in the response are **different strings** from the ones you submitted — a brand new pair is issued every time, not the same token echoed back.

---

## TC-002 — Refreshed Token Reflects Current DB State

**Goal:** Confirm `aadhaarVerified`/`status` are re-read fresh from the database at refresh time, not copied from the submitted token's claims.

**Steps:**
1. Complete registration through email verification only (`IDENTITY_VERIFICATION_PENDING`), keep the `refreshToken` from that point.
2. In a separate session, finish Aadhaar verification for the same user (`POST /aadhaar/initiate` + `POST /aadhaar/verify`, sandbox provider — see `US-001-Testing-Guide.md` Steps 5b–6). The account is now `ACTIVE` with `aadhaarVerified: true`.
3. `POST /api/v1/auth/refresh` using the **original** `refreshToken` from step 1 (issued while the account was still `IDENTITY_VERIFICATION_PENDING`).

**Expected:** the refreshed response shows `"aadhaarVerified": true` and `"status": "ACTIVE"` — the *current* account state, even though the refresh token itself was issued before Aadhaar was verified.

---

## TC-003 — Malformed / Tampered Refresh Token

**Request body:**
```json
{ "refreshToken": "not-a-real-jwt" }
```

**Expected response (400 Bad Request):**
```json
{
  "success": false,
  "error": {
    "code": "ERROR_INVALID_REFRESH_TOKEN",
    "message": "Session expired. Please log in again"
  }
}
```

> Same result for a real token with characters altered (signature mismatch) or a refresh token issued with a different `JWT_SECRET` (e.g. after an env restart with a new secret).

---

## TC-004 — Access Token Submitted Instead of a Refresh Token

**Steps:** Take the `accessToken` (not `refreshToken`) from any auth response and submit it to `/auth/refresh`:
```json
{ "refreshToken": "eyJ...<the accessToken value>..." }
```

**Expected response (400 Bad Request):**
```json
{
  "success": false,
  "error": {
    "code": "ERROR_WRONG_TOKEN_TYPE",
    "message": "Invalid token for this operation"
  }
}
```

> If the access token has *also* already expired by the time you test this, you'll get `ERROR_REFRESH_TOKEN_EXPIRED`/`ERROR_INVALID_REFRESH_TOKEN` instead of `ERROR_WRONG_TOKEN_TYPE` — the `type` claim can only be read after the token parses successfully. Both outcomes tell the caller to log in again; this is a documented, accepted imprecision (LLD §14.5, item 7), not a bug.

---

## TC-005 — Expired Refresh Token

**Not reachable in 7 real days of normal testing.** To test this without waiting a week:

1. Temporarily set `valuex.jwt.refresh-token-expiry` to a small value (e.g. `5000` for 5 seconds) in `application.yml` or via the `JWT_REFRESH_TOKEN_EXPIRY` env var, and restart the app.
2. Get a fresh refresh token (Prerequisites).
3. Wait 6+ seconds.
4. `POST /api/v1/auth/refresh` with that token.

**Expected response (400 Bad Request):**
```json
{
  "success": false,
  "error": {
    "code": "ERROR_REFRESH_TOKEN_EXPIRED",
    "message": "Session expired. Please log in again"
  }
}
```

**Revert the config change** afterward — don't leave a shortened refresh expiry in a shared dev environment.

---

## TC-006 — Account Suspended After Token Issuance

**Goal:** Confirm the "fail closed regardless of token expiry" validation rule — there's no admin/suspend endpoint yet, so this requires direct DB access in the dev environment.

**Steps:**
1. Get a refresh token for a test user (Prerequisites).
2. Suspend the account directly:
   ```sql
   UPDATE users SET status = 'SUSPENDED' WHERE mobile = '9000000030';
   ```
3. `POST /api/v1/auth/refresh` with the refresh token obtained in step 1 — still well within its 7-day expiry.

**Expected response (400 Bad Request):**
```json
{
  "success": false,
  "error": {
    "code": "ERROR_ACCOUNT_SUSPENDED",
    "message": "Your account is suspended. Please contact support"
  }
}
```

**Revert:** `UPDATE users SET status = 'ACTIVE' WHERE mobile = '9000000030';`

---

## TC-007 — Account Banned/Closed After Token Issuance

Same as TC-006, but:
```sql
UPDATE users SET status = 'BANNED' WHERE mobile = '9000000030';
```

**Expected response (400 Bad Request):**
```json
{
  "success": false,
  "error": {
    "code": "ERROR_ACCOUNT_RECOVERY_REQUIRED",
    "message": "Your account requires recovery. Please contact support"
  }
}
```
Same result for `status = 'CLOSED'`.

---

## TC-008 — Used Refresh Token Is Rejected and Revokes the Session

**Goal:** Confirm single-use rotation and reuse detection.

**Steps:**
1. Log in (`/auth/login/*`) and note `refreshToken_A` and `accessToken_A`.
2. `POST /api/v1/auth/refresh` with `refreshToken_A` → `200`; note `refreshToken_B` (different from A).
3. `POST /api/v1/auth/refresh` **again with `refreshToken_A`**.
4. `POST /api/v1/auth/refresh` with `refreshToken_B`.
5. `GET /api/v1/users/me` with the access token from step 2.

**Expected:**
- Step 3: **400 `ERROR_INVALID_REFRESH_TOKEN`** — `refreshToken_A` was spent by step 2. The backend log shows `Refresh token reuse detected, revoking session`.
- Step 4: **400 `ERROR_REFRESH_TOKEN_EXPIRED`** — the whole session was revoked by the reuse in step 3.
- Step 5: **401** — the session's access token is blocklisted too.
- `GET /users/me/sessions` no longer lists the session; `user_sessions.revoked_reason = 'REFRESH_TOKEN_REUSE'`.

**Also check — chained use is fine:** log in, refresh with A → B, refresh with B → C, refresh with C → D. Every step returns `200` with a new token.

**Also check — concurrency:** send two refreshes with the same token at once; exactly one returns `200`, the other `ERROR_INVALID_REFRESH_TOKEN` (and the session is then revoked, per LLD §14.7).

**Also check — logout:** log out, wait longer than the access-token lifetime, then refresh with the pre-logout refresh token → **400 `ERROR_REFRESH_TOKEN_EXPIRED`** (the Redis blocklist entry has expired by then; the revoked session row still rejects it).

---

## TC-009 — Refresh Token Rejected as a Bearer Access Token

**Goal:** Confirm the `JwtAuthenticationFilter` fix — a refresh token can no longer authenticate a protected endpoint.

**Steps:**
1. Get a refresh token.
2. In Swagger UI, click **Authorize 🔒** and paste the **refresh token** (not the access token) into the `bearerAuth` field.
3. Call any protected endpoint, e.g. `GET /api/v1/users/me`.

**Expected response (401 Unauthorized):**
```json
{
  "success": false,
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Authentication required"
  }
}
```

> Before this story, a refresh token used this way would authenticate successfully (with a broken `role=null` authority). Confirming the 401 here is confirming the fix, not incidental — worth flagging clearly if this ever regresses to a 200.

---

## TC-010 — Missing `refreshToken` in Request Body

**Request body:**
```json
{}
```

**Expected response (400 Bad Request):** standard Jakarta Bean Validation error — `refreshToken` field flagged with message `"Refresh token is required"`.

---

## Not Testable Yet (Don't File as Bugs)

- **Grace window for a lost refresh response** — not built. A refresh response that never reaches the device leaves it with a spent token; its next refresh is treated as reuse and the user signs in again (LLD §14.7).
- **Clock skew at the expiry boundary** — a pre-existing, systemic property of `JwtTokenProvider`'s JJWT configuration (zero tolerance), not something this story changed either way.

---

## Reset Between Tests

Register a fresh mobile number per TC (recommended), or reset the same test user's status directly:
```sql
UPDATE users SET status = 'ACTIVE' WHERE mobile = '9000000030';
```

---

## Error Reference

| HTTP | Error Code | Cause |
|---|---|---|
| 400 | `ERROR_INVALID_REFRESH_TOKEN` | Malformed/tampered token, signature mismatch, or the token's `sub` no longer matches any user (TC-003) |
| 400 | `ERROR_REFRESH_TOKEN_EXPIRED` | Refresh token past its 7-day expiry (TC-005) |
| 400 | `ERROR_WRONG_TOKEN_TYPE` | An access token (or any non-refresh-type token) submitted to `/refresh` (TC-004) |
| 400 | `ERROR_INVALID_STATE` | Account is `NEW`/`OTP_PENDING` — not reachable via a real refresh token, since those states never receive one |
| 400 | `ERROR_ACCOUNT_SUSPENDED` | Account suspended since the refresh token was issued (TC-006) |
| 400 | `ERROR_ACCOUNT_RECOVERY_REQUIRED` | Account banned or closed since the refresh token was issued (TC-007) |
| 401 | `UNAUTHORIZED` | Refresh token presented as a Bearer access token — correctly rejected (TC-009) |
| 400 | Validation error | `refreshToken` missing/blank in the request body (TC-010) |
