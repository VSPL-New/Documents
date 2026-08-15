# US-104 — Account Logout: QA Testing Guide

**Sprint 1 · Identity & User Management**

Manual test cases for the logout endpoint, using Swagger UI against a local dev environment.

> **What this story actually ships:** a single endpoint that blocklists the current session's
> `jti` in Redis. Every login/registration flow now mints one shared `jti` per access+refresh
> token pair, so this one blocklist entry invalidates **both** tokens from that session — not
> just the access token used to call `/logout`. There is **no** persisted `user_sessions` table
> and no "list my active devices" capability yet — that's US-105, built on top of this story's
> `jti` foundation but not part of it. See `Documents/LLD/Sprint-1-Identity-User-Management-LLD.md`
> §9 for the full design, and the **Not Testable Yet** section below before filing anything
> device/session-listing related as a bug.

| Setting | Value |
|---|---|
| Base URL | `http://localhost:8080` |
| Swagger UI | `http://localhost:8080/swagger-ui.html` (tag: **Authentication**) |
| Endpoint under test | `POST /api/v1/auth/logout` |
| Auth | Bearer access token required |

---

## Prerequisites — Get an Access + Refresh Token Pair

Any completed auth flow works. Fastest path (see `US-001-Testing-Guide.md` for full detail, or
`US-106` in the combined Sprint-1 guide for the login shortcut):

1. `POST /api/v1/auth/register/initiate`
   ```json
   { "mobile": "9000000050", "termsAccepted": true, "consentGiven": true }
   ```
2. Read the OTP from the console log, then `POST /api/v1/auth/register/verify-mobile`
   ```json
   { "mobile": "9000000050", "otp": "XXXXXX" }
   ```
3. Copy both `data.accessToken` and `data.refreshToken`. **Authorize** in Swagger UI with the
   access token (🔒 button, paste token, no `Bearer ` prefix).

---

## Test Scenarios Overview

| TC | Scenario | Expected Result |
|---|---|---|
| TC-001 | Logout with a valid access token | `200`, `"Logged out successfully"` |
| TC-002 | The logged-out access token is rejected on its next use | `401 UNAUTHORIZED` |
| TC-003 | The paired refresh token is also invalidated | `400 ERROR_REFRESH_TOKEN_EXPIRED` from `/auth/refresh` |
| TC-004 | Session stays revocable after a refresh (jti carries forward) | Logging out with a *refreshed* token still kills the *original* refresh token |
| TC-005 | Rapid retry with the same still-valid token succeeds twice | `200` both times — not an error |
| TC-006 | A later call with the same, now-blocklisted token | `401`, not a second `200` — documented boundary, not a bug |
| TC-007 | Unauthenticated logout call | `401 UNAUTHORIZED` |
| TC-008 | Refresh token submitted as the Bearer token to `/logout` | `401` — rejected before `LogoutService` is ever called |
| TC-009 | Logging out one session doesn't affect another session for the same user | The other session's token keeps working |

---

## TC-001 — Logout With a Valid Access Token

**Endpoint:** `POST /api/v1/auth/logout` *(Bearer token required, no request body)*

**Expected response (200 OK):**
```json
{
  "success": true,
  "data": { "message": "Logged out successfully" }
}
```

---

## TC-002 — Logged-Out Access Token Rejected on Next Use

**Steps:** Immediately after TC-001, call `GET /api/v1/users/me` with the **same** access token
still set in Swagger's Authorize dialog.

**Expected response (401 Unauthorized):**
```json
{
  "success": false,
  "error": { "code": "UNAUTHORIZED", "message": "Authentication required" }
}
```
> This is the same generic `401` shape as a missing/expired token — the filter doesn't
> distinguish "blocklisted" from "never valid" in its response, only in its server log
> (`Rejected blocklisted (logged-out) token`).

---

## TC-003 — Paired Refresh Token Also Invalidated

**Goal:** Confirm logout kills the *whole session*, not just the access token used to call it —
this is the gap US-107's own acceptance criteria flagged as deferred until this story shipped.

**Steps:**
1. Register a fresh user (mobile `9000000051`), keep both `accessToken` and `refreshToken` from
   the same response.
2. `POST /api/v1/auth/logout` using that `accessToken`.
3. `POST /api/v1/auth/refresh` *(public — no Bearer needed)* with that same `refreshToken`:
   ```json
   { "refreshToken": "<the paired refresh token from step 1>" }
   ```

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
> Reuses the existing `ERROR_REFRESH_TOKEN_EXPIRED` code rather than a new "revoked" code — from
> the client's perspective the recovery action is identical (log in again), matching this
> codebase's convention of not inventing near-duplicate error codes.

---

## TC-004 — Session Stays Revocable Across a Refresh

**Goal:** Confirm the reissued token pair from `/auth/refresh` keeps the *same* `jti` as the
token it refreshed — not a freshly minted one — so a later logout call still reaches the
original session.

**Steps:**
1. Register a fresh user (mobile `9000000052`), keep the initial `refreshToken_A`.
2. `POST /api/v1/auth/refresh` with `refreshToken_A` → note the new `accessToken_B` /
   `refreshToken_B`.
3. `POST /api/v1/auth/logout` using `accessToken_B`.
4. `POST /api/v1/auth/refresh` again, this time with the **original** `refreshToken_A`
   (issued *before* the refresh in step 2).

**Expected:** step 4 returns `400 ERROR_REFRESH_TOKEN_EXPIRED` — logging out with the
*post-refresh* token also killed the *pre-refresh* token, because they share one `jti` for the
whole lifetime of that login session, not just the most recent pair.

---

## TC-005 — Rapid Retry With the Same Still-Valid Token

**Goal:** A client retry after a network blip (before the first response is confirmed received)
must not error out.

**Steps:** Register a fresh user (mobile `9000000053`). Call `POST /api/v1/auth/logout` **twice
in immediate succession** with the same access token, without any other call in between.

**Expected:** both calls return `200 OK` with the same body. Setting the same Redis blocklist key
twice is a harmless overwrite.

---

## TC-006 — Later Call With the Same, Now-Blocklisted Token

**Goal:** Confirm the documented idempotency boundary — logout is idempotent *within* a token's
validity, not indefinitely.

**Steps:**
1. Register a fresh user (mobile `9000000054`). `POST /api/v1/auth/logout`.
2. Wait a moment (or make any other call), then `POST /api/v1/auth/logout` **again** with the
   same, already-blocklisted access token.

**Expected:** step 2 returns `401 Unauthorized`, **not** `200`. There is no valid session left to
authenticate the request with, so `JwtAuthenticationFilter` rejects it before the controller ever
runs. **Do not file this as a bug** — see LLD §9.5. To log out "again," the client must first
obtain a fresh token (which itself means the previous session was already gone).

---

## TC-007 — Unauthenticated Logout Call

**Steps:** In Swagger UI, click **Authorize 🔒** → **Logout** (or call without an `Authorization`
header), then `POST /api/v1/auth/logout`.

**Expected response (401 Unauthorized):**
```json
{
  "success": false,
  "error": { "code": "UNAUTHORIZED", "message": "Authentication required" }
}
```

---

## TC-008 — Refresh Token Submitted as Bearer to `/logout`

**Steps:** Authorize in Swagger UI with a **refresh token** (not an access token), then call
`POST /api/v1/auth/logout`.

**Expected response (401 Unauthorized).** `JwtAuthenticationFilter` already rejects any non-access
token used as a Bearer token (fixed under US-107) — `LogoutService.logout(...)` is never reached,
so nothing is blocklisted by this call.

---

## TC-009 — Logging Out One Session Doesn't Affect Another

**Goal:** Confirm the AC edge case *"User has multiple active sessions on other devices"* —
logout only revokes the session tied to the token presented, not every session for that user.

**Steps:**
1. Register a fresh user (mobile `9000000055`) → this is **Session A** (`accessToken_A`).
2. `POST /api/v1/auth/login/initiate` + `POST /api/v1/auth/login/verify-mobile` for the same
   mobile (see US-106) → this is **Session B** (`accessToken_B`), a different `jti` from Session A.
3. `POST /api/v1/auth/logout` using `accessToken_A`.
4. `GET /api/v1/users/me` using `accessToken_B`.

**Expected:** step 4 still returns `200 OK` — Session B is untouched. Only `accessToken_A` (and
its paired refresh token) is blocklisted.

---

## Not Testable Yet (Don't File as Bugs)

- **Listing active sessions / devices** (`GET /users/me/sessions`) — doesn't exist. US-105
  territory, built on top of this story's `jti` but not part of it.
- **"Log out of all other devices"** — same as above, US-105.
- **True single-use refresh-token rotation** — a refresh token not tied to a logged-out session
  still works repeatedly until its own 7-day expiry (see `US-107-Testing-Guide.md` TC-008). This
  story only adds *revocation on logout*, not rotation on every refresh.
- **"Logout triggered automatically after password/PIN change"** (a user-stories.md edge case) —
  categorically not applicable to this system. There is no password or PIN anywhere in ValueX's
  auth design; every flow is mobile-OTP or social sign-in. Not a gap, just an inapplicable edge
  case carried over from the story template.
- **In-flight upload cancellation on logout** — client-side mobile behavior (per the LLD's edge
  case note), not observable through this backend API.
- **Rate limiting on `/auth/logout`** — deliberately not implemented; see LLD §17.5. Repeated
  logout calls are self-limiting (each just blocklists the token used), so there's no abuse
  surface to guard against.

---

## Reset Between Tests

Register a fresh mobile number per TC (recommended, and used throughout this guide), or manually
clear a blocklist entry in Redis if you need to "undo" a logout during exploratory testing:
```
DEL blocklist:<jti>
```
(`jti` is only visible by decoding the JWT — e.g. paste it into jwt.io — there's no API to look it
up directly.)

---

## Error Reference

| HTTP | Error Code | Cause |
|---|---|---|
| 200 | — | Logout succeeded (TC-001, TC-005) |
| 401 | `UNAUTHORIZED` | Missing/expired/already-blocklisted access token (TC-002, TC-006, TC-007), or a refresh token presented as Bearer (TC-008) |
| 400 | `ERROR_REFRESH_TOKEN_EXPIRED` | The paired refresh token was invalidated by a logout call on the shared `jti` (TC-003, TC-004) |
| 400 | `ERROR_LOGOUT_FAILED` | Defined in `user-stories.md`; not reachable via any real failure path in this design — the only external call is a Redis write |
