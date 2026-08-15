# Sprint 1 — Identity & User Management: Combined QA Testing Guide

**Covers:** US-001 (Registration), US-002 (One Account Per User), US-003 (Profile Management), US-103 (Profile Hub / Menu Summary), US-106 (Mobile OTP Login), US-107 (Access Token Refresh)

Manual test cases for the full Sprint 1 identity surface, using Swagger UI against a local dev environment. Each story keeps its own section and TC numbering (`US-XXX / TC-00N`) so this guide can be cross-referenced the same way the individual per-story guides were.

> **Source guides:** this document combines `US-001-Testing-Guide.md`, `US-002-Testing-Guide.md`, `US-003-Testing-Guide.md`, `US-103-Testing-Guide.md`, `US-107-Testing-Guide.md`, and adds a new section for **US-106**, which previously only had an implementation plan (`US-106-Implementation-Plan.md`) and no QA guide. The US-106 test cases below were written against the actual shipped code (`UserLoginService.java`, `AuthController.java`) — endpoints, DTOs, and error codes were verified directly from source, not assumed from the plan.

---

## Environment Setup

| Setting | Value |
|---|---|
| Base URL | `http://localhost:8080` |
| Swagger UI | `http://localhost:8080/swagger-ui.html` |
| SMS / Email OTP Provider | `mock` (OTP printed to app console) |
| Aadhaar Provider | `sandbox` (accepts any 12-digit number; OTP `123456` always passes) |
| OTP length / TTL | 6 digits / 300 s (`valuex.otp.expiry-seconds`) |
| OTP send limit | 3 per 10 min per mobile (`otp_rate:{mobile}`) |
| OTP verify-fail limit | 5 per 10 min per mobile (`otp_fail:{mobile}`) |
| Access token TTL | 3,600,000 ms (1 hour) |
| Refresh token TTL | 604,800,000 ms (7 days) |
| DB Access | pgAdmin or `psql -U postgres -d valuex_dev` |
| Default avatar | `avatar-01` (catalog: `avatar-01` … `avatar-12`) |

**Authorize in Swagger UI:** click **Authorize 🔒** (top-right) → paste the `accessToken` into the `bearerAuth` field **without** a `Bearer ` prefix (Swagger adds it) → **Authorize** → **Close**.

---

## Suggested End-to-End Sequence

Running the stories in this order lets one test user carry state through the whole sprint, exercising every endpoint once before diving into the negative/edge-case TCs below:

```
US-001 (register: mobile → email → Aadhaar)
   → US-003 (view/edit profile, pick avatar)
      → US-103 (menu summary reflects those edits)
         → US-107 (refresh the access token, confirm it reflects current state)
            → US-106 (discard token, log back in via mobile OTP)
               → US-002 (negative cases: duplicate Aadhaar/mobile, banned-account handling)
```

---

## US-001 — User Registration via Mobile OTP

End-to-end registration: mobile OTP → email OTP → Aadhaar (optional).

### Flow

```
Step 1 (Initiate) → Step 2 (Verify Mobile) → Authorize → Step 3 (Send Email OTP) → Step 4 (Verify Email OTP)
                                                                                              ↓
                                                                    Step 5a (Skip Aadhaar) ← → Step 5b (Initiate Aadhaar) → Step 6 (Verify Aadhaar)
```

| Step | Endpoint | Auth | Account State After |
|---|---|---|---|
| 1 | `POST /api/v1/auth/register/initiate` | None | `OTP_PENDING` |
| 2 | `POST /api/v1/auth/register/verify-mobile` | None | `EMAIL_VERIFICATION_PENDING` |
| 3 | `POST /api/v1/auth/email/send-otp` | JWT | `EMAIL_VERIFICATION_PENDING` |
| 4 | `POST /api/v1/auth/email/verify-otp` | JWT | `IDENTITY_VERIFICATION_PENDING` |
| 5a | `POST /api/v1/auth/register/skip-aadhaar` | JWT | `ACTIVE` (`aadhaarVerified=false`) |
| 5b | `POST /api/v1/auth/aadhaar/initiate` | JWT | `IDENTITY_VERIFICATION_PENDING` |
| 6 | `POST /api/v1/auth/aadhaar/verify` | JWT | `ACTIVE` (`aadhaarVerified=true`) |

> **Aadhaar is optional at registration.** A user who skips it (Step 5a) reaches `ACTIVE` but cannot complete transactions until Aadhaar is verified later.

### Step 1 — Initiate Registration *(public)*

`POST /api/v1/auth/register/initiate`
```json
{ "mobile": "9876543210", "termsAccepted": true, "consentGiven": true }
```
Check the console log for `[DEV-MOCK] OTP for mobile=9876543210 purpose=MOBILE_VERIFY otp=XXXXXX`.

**200 OK:** `{ "success": true, "data": { "message": "OTP sent to your mobile number", "otpExpiresInSeconds": 300 } }`

### Step 2 — Verify Mobile OTP *(public)*

`POST /api/v1/auth/register/verify-mobile`
```json
{ "mobile": "9876543210", "otp": "XXXXXX" }
```
**200 OK:** `{ "success": true, "data": { "accessToken": "...", "refreshToken": "...", "aadhaarVerified": false, "userId": "..." } }`

Copy `accessToken` and **Authorize** in Swagger UI. Account is now `EMAIL_VERIFICATION_PENDING`.

### Step 3 — Send Email OTP *(JWT)*

`POST /api/v1/auth/email/send-otp`
```json
{ "email": "user@example.com" }
```
Check console log for the email OTP. **200 OK:** `{ "success": true, "data": { "message": "OTP sent to user@example.com", "otpExpiresInSeconds": 300 } }`

### Step 4 — Verify Email OTP *(JWT)*

`POST /api/v1/auth/email/verify-otp`
```json
{ "email": "user@example.com", "otp": "XXXXXX" }
```
**200 OK:** `{ "success": true, "data": { "message": "Email verified successfully" } }`

Account is now `IDENTITY_VERIFICATION_PENDING`. Proceed to 5a or 5b.

### Step 5a — Skip Aadhaar *(JWT, optional path)*

`POST /api/v1/auth/register/skip-aadhaar` — no body.

**200 OK:** new token pair, `aadhaarVerified: false`, account now `ACTIVE`. Re-authorize with the new token.

### Step 5b — Initiate Aadhaar Verification *(JWT)*

`POST /api/v1/auth/aadhaar/initiate`
```json
{ "aadhaarNumber": "123456789012", "consentToken": "consent-ts-123" }
```
**200 OK:** `{ "success": true, "data": { "transactionId": "sandbox-txn-..." } }` — copy `transactionId`.

### Step 6 — Complete Aadhaar Verification *(JWT)*

`POST /api/v1/auth/aadhaar/verify`
```json
{ "transactionId": "sandbox-txn-...", "otp": "123456" }
```
**200 OK:** new token pair, `aadhaarVerified: true`, account now `ACTIVE`. Re-authorize with the new token — required for marketplace transaction endpoints.

### US-001 Error Reference

| HTTP | Error Code | Cause & Fix |
|---|---|---|
| 401 | `UNAUTHORIZED` | Missing/expired JWT. Repeat Steps 2–2b for a fresh token. |
| 400 | `ERROR_INVALID_STATE` | Endpoint called out of order. Follow the flow above. |
| 400 | `ERROR_OTP_EXPIRED` | OTP TTL is 300s. Re-run Step 1 or 3 for a new one. |
| 400 | `ERROR_INVALID_OTP` | Wrong OTP value — check the console log. |
| 400 | `ERROR_OTP_MAX_ATTEMPTS` | 5 failed verify attempts within 10 min. |
| 400 | `ERROR_OTP_RATE_LIMIT` | 3 send attempts within 10 min. |
| 400 | `ERROR_MOBILE_ALREADY_REGISTERED` | Mobile already has an account. |
| 400 | `ERROR_EMAIL_ALREADY_REGISTERED` | Email linked to another account. |
| 400 | `ERROR_AADHAAR_ALREADY_USED` | Aadhaar linked to another account. |

---

## US-002 — One Account Per User Enforcement

Validates Aadhaar uniqueness, differentiated errors by account state, and Google Sign-In rejection for banned mobiles.

### Scenarios

| TC | Scenario | Existing Account State | Expected Error |
|---|---|---|---|
| TC-001 | Duplicate Aadhaar — owner ACTIVE | `ACTIVE` | `ERROR_AADHAAR_ALREADY_USED` |
| TC-002 | Duplicate Aadhaar — owner SUSPENDED | `SUSPENDED` | `ERROR_ACCOUNT_RECOVERY_REQUIRED` |
| TC-003 | Duplicate Aadhaar — owner BANNED | `BANNED` | `ERROR_ACCOUNT_RECOVERY_REQUIRED` + security log |
| TC-004 | Duplicate mobile at registration | Any | `ERROR_MOBILE_ALREADY_REGISTERED` |
| TC-005 | Google Sign-In with BANNED mobile | `BANNED` | `ERROR_ACCOUNT_RECOVERY_REQUIRED` |
| TC-006 | First-time Aadhaar use (happy path) | — | `200 OK` |

### Setup — Register Base User A

Complete US-001 for User A with mobile `9000000001`, using the test Aadhaar for the TC being run:

| TC | Aadhaar for User A |
|---|---|
| TC-001 | `111111111111` |
| TC-002 | `222222222222` |
| TC-003 | `333333333333` |

### TC-001 — Duplicate Aadhaar, Owner ACTIVE

Register User B (`9000000002`), verify mobile + email → `IDENTITY_VERIFICATION_PENDING`. Then:

`POST /api/v1/auth/aadhaar/initiate` *(User B's JWT)*
```json
{ "aadhaarNumber": "111111111111", "consentToken": "consent-ts-001" }
```
**400:** `{ "success": false, "error": { "code": "ERROR_AADHAAR_ALREADY_USED", "message": "This Aadhaar is already linked to an account" } }`

No security log (normal duplicate, not a threat).

### TC-002 — Duplicate Aadhaar, Owner SUSPENDED

```sql
UPDATE users SET status = 'SUSPENDED' WHERE mobile = '9000000001';
```
Register User B, verify mobile + email, then attempt Aadhaar init with `222222222222`.

**400:** `{ "success": false, "error": { "code": "ERROR_ACCOUNT_RECOVERY_REQUIRED", "message": "This Aadhaar is linked to a suspended account. Please contact support" } }`

### TC-003 — Duplicate Aadhaar, Owner BANNED (Security Event)

```sql
UPDATE users SET status = 'BANNED' WHERE mobile = '9000000001';
```
Register User B, verify mobile + email, then attempt Aadhaar init with `333333333333`.

**400:** `{ "success": false, "error": { "code": "ERROR_ACCOUNT_RECOVERY_REQUIRED", "message": "This Aadhaar is linked to a closed account. Please contact support" } }`

**Console log (WARN):**
```
WARN  AadhaarVerificationService - SECURITY_EVENT: Aadhaar reuse on BANNED/CLOSED account
      requesterUserId=<User B UUID> existingUserId=<User A UUID>
```
This log entry is the audit trail required by US-002's acceptance criteria.

### TC-004 — Duplicate Mobile at Registration

`POST /api/v1/auth/register/initiate` with `"mobile": "9000000001"` (already exists, any state).

**400:** `{ "success": false, "error": { "code": "ERROR_MOBILE_ALREADY_REGISTERED", "message": "An account with this mobile number already exists" } }`

Fires before any OTP is sent — no console OTP log.

### TC-005 — Google Sign-In with BANNED Mobile

```sql
UPDATE users SET status = 'BANNED' WHERE mobile = '9000000001';
```
1. `POST /api/v1/auth/social/google` with `{ "idToken": "mock-newuser" }` → `requiresMobileVerification: true` + `socialSessionToken`.
2. `POST /api/v1/auth/social/google/initiate-mobile`
   ```json
   { "socialSessionToken": "<from step 1>", "mobile": "9000000001", "termsAccepted": true, "consentGiven": true }
   ```
**400:** `{ "success": false, "error": { "code": "ERROR_ACCOUNT_RECOVERY_REQUIRED", "message": "Your account requires recovery. Please contact support" } }`

> Non-ACTIVE accounts that aren't BANNED/CLOSED (e.g. `EMAIL_VERIFICATION_PENDING`) return `ERROR_INVALID_STATE` instead.

### TC-006 — First-Time Aadhaar Use (Happy Path)

Fresh user through mobile + email OTP, then:
`POST /api/v1/auth/aadhaar/initiate`
```json
{ "aadhaarNumber": "999999999999", "consentToken": "consent-ts-999" }
```
**200 OK:** `transactionId` returned. Complete with `POST /api/v1/auth/aadhaar/verify`, OTP `123456`.

### US-002 Reset Between Tests

```sql
DELETE FROM user_social_accounts WHERE user_id IN (SELECT id FROM users WHERE mobile IN ('9000000001', '9000000002'));
DELETE FROM aadhaar_verification_attempts WHERE user_id IN (SELECT id FROM users WHERE mobile IN ('9000000001', '9000000002'));
DELETE FROM account_status_history WHERE user_id IN (SELECT id FROM users WHERE mobile IN ('9000000001', '9000000002'));
DELETE FROM users WHERE mobile IN ('9000000001', '9000000002');
```

### US-002 Error Reference

| HTTP | Error Code | Scenario |
|---|---|---|
| 400 | `ERROR_AADHAAR_ALREADY_USED` | Aadhaar linked to an active account (TC-001) |
| 400 | `ERROR_ACCOUNT_RECOVERY_REQUIRED` | Aadhaar linked to SUSPENDED/UNDER_REVIEW/RESTRICTED (TC-002) |
| 400 | `ERROR_ACCOUNT_RECOVERY_REQUIRED` | Aadhaar linked to BANNED/CLOSED — also logs security event (TC-003) |
| 400 | `ERROR_MOBILE_ALREADY_REGISTERED` | Mobile already has an account (TC-004) |
| 400 | `ERROR_ACCOUNT_RECOVERY_REQUIRED` | Google linking on BANNED/CLOSED mobile (TC-005) |
| 400 | `ERROR_INVALID_STATE` | Google linking on incomplete-registration mobile |
| 400 | `ERROR_AADHAAR_SESSION_EXPIRED` | >10 min between initiate and verify |
| 400 | `ERROR_INVALID_STATE` | Aadhaar initiation before email verification complete |

---

## US-003 — User Profile Management

Viewing/editing profile fields (display name, city) and avatar selection.

> **Design note:** users pick an `avatarId` from a fixed catalog (`GET /api/v1/avatars`) — there is no photo upload or content moderation in this version. See `Documents/LLD/Sprint-1-Identity-User-Management-LLD.md` §7.

**Prerequisites:** Only a valid JWT is required (not email/Aadhaar verification) — Steps 1–2 of US-001 are sufficient.

### Scenarios

| TC | Scenario | Endpoint | Expected |
|---|---|---|---|
| TC-001 | View own profile (defaults) | `GET /users/me` | `200`, default avatar, masked mobile |
| TC-002 | Update display name and city | `PATCH /users/me` | `200`, both fields updated |
| TC-003 | Partial update leaves other field unchanged | `PATCH /users/me` | `200`, only sent field changes |
| TC-004 | Reject invalid display name | `PATCH /users/me` | `400 VALIDATION_ERROR` |
| TC-005 | Reject invalid city | `PATCH /users/me` | `400 VALIDATION_ERROR` |
| TC-006 | List avatar catalog | `GET /avatars` | `200`, 12 IDs + default |
| TC-007 | Select a valid avatar | `PUT /users/me/avatar` | `200`, `avatarId` updated |
| TC-008 | Reject avatar not in catalog | `PUT /users/me/avatar` | `400 ERROR_INVALID_AVATAR` |
| TC-009 | Aadhaar-verified name is read-only | `GET/PATCH /users/me` | Field never changes via this API |
| TC-010 | Unauthenticated request rejected | `GET /users/me` | `401 UNAUTHORIZED` |

### TC-001 — View Own Profile (Defaults)

`GET /api/v1/users/me` *(JWT)* — no body.

**200 OK:**
```json
{ "success": true, "data": { "userId": "...", "mobile": "90XXXX0010", "aadhaarVerified": false, "avatarId": "avatar-01", "status": "EMAIL_VERIFICATION_PENDING", "memberSince": "..." } }
```
> `displayName`/`email`/`city`/`aadhaarName` are omitted entirely (not `null`) before ever set — not a bug. `avatarId` defaults to `avatar-01` at account creation.

### TC-002 — Update Display Name and City

`PATCH /api/v1/users/me`
```json
{ "displayName": "Abhay Kumar", "city": "Bengaluru" }
```
**200 OK**, confirm via `GET /users/me`.

### TC-003 — Partial Update Leaves Other Field Unchanged

Prerequisite: TC-002 done. `PATCH /api/v1/users/me` with `{ "city": "Mumbai" }` — `displayName` must still read `"Abhay Kumar"`.

### TC-004 — Reject Invalid Display Name

Try each: `{ "displayName": "Ab" }` (too short), `{ "displayName": "Abhay123" }` (digits), `{ "displayName": "Abhay@Kumar" }` (`@`).

**400:** `code: VALIDATION_ERROR` for each.

### TC-005 — Reject Invalid City

`{ "city": "P1" }` → **400** `VALIDATION_ERROR`.

> **Known simplification:** format-only validation, no exhaustive city whitelist — `"Notacity"` currently passes. Expected per LLD, not a bug.

### TC-006 — List Avatar Catalog

`GET /api/v1/avatars` *(JWT)* → **200**, `avatarIds: ["avatar-01" ... "avatar-12"]`, `defaultAvatarId: "avatar-01"`.

### TC-007 — Select a Valid Avatar

`PUT /api/v1/users/me/avatar` with `{ "avatarId": "avatar-07" }` → **200**, confirm via `GET /users/me`.

### TC-008 — Reject Avatar Not in Catalog

`{ "avatarId": "avatar-99" }` → **400** `ERROR_INVALID_AVATAR`, existing selection untouched.

Also try `{ "avatarId": "" }` → **400** `VALIDATION_ERROR` (different code — don't conflate).

### TC-009 — Aadhaar-Verified Name Is Read-Only

Prerequisite: complete Aadhaar verification (US-001 Steps 3–6). `GET /users/me` shows `aadhaarName`.

`PATCH /api/v1/users/me`
```json
{ "displayName": "Abhay Kumar", "aadhaarName": "Someone Else" }
```
**200 OK** — request succeeds (unknown fields silently ignored), but `aadhaarName` in the response is unchanged. `UpdateProfileRequest` has no `aadhaarName` property — structurally impossible to write via this endpoint.

### TC-010 — Unauthenticated Request Rejected

Logout in Swagger UI, call `GET /api/v1/users/me` → **401** `UNAUTHORIZED`. Repeat for `PATCH /users/me`, `PUT /users/me/avatar`, `GET /avatars`.

### Not Testable Yet (US-003)

- Viewing another user's profile — no public "view by ID" endpoint yet (arrives with US-012).
- Rating/joined-date alongside profile — ratings don't exist until the Ratings sprint.
- Profile photo upload / image moderation — intentionally out of scope for this story.

### US-003 Reset Between Tests

```sql
UPDATE users SET display_name = NULL, city = NULL, avatar_id = 'avatar-01' WHERE mobile = '9000000010';
```
Full teardown:
```sql
DELETE FROM aadhaar_verification_attempts WHERE user_id IN (SELECT id FROM users WHERE mobile = '9000000010');
DELETE FROM user_social_accounts WHERE user_id IN (SELECT id FROM users WHERE mobile = '9000000010');
DELETE FROM account_status_history WHERE user_id IN (SELECT id FROM users WHERE mobile = '9000000010');
DELETE FROM users WHERE mobile = '9000000010';
```

### US-003 Error Reference

| HTTP | Error Code | Cause |
|---|---|---|
| 400 | `VALIDATION_ERROR` | `displayName`/`city`/`avatarId` fails `@Size`/`@Pattern`/`@NotBlank` |
| 400 | `ERROR_INVALID_AVATAR` | `avatarId` well-formed but not in the catalog |
| 401 | `UNAUTHORIZED` | Missing/expired JWT |
| 404 | `NOT_FOUND` | JWT references a deleted user (not reachable via normal use) |

---

## US-103 — Profile Hub / Account Menu Navigation

Backend deliverable is one summary endpoint: `GET /api/v1/users/me/menu-summary`, plus an unused-so-far badge-provider extensibility hook.

> **`badges` is always `{}` today** — zero providers registered in Sprint 1. That's correct, not a bug (LLD §8).

**Prerequisites:** valid JWT only (same as US-003).

### Scenarios

| TC | Scenario | Expected |
|---|---|---|
| TC-001 | Fresh account defaults | `200`, default avatar, `memberSince` set, empty `badges` |
| TC-002 | Reflects display-name update | `200`, `displayName` matches latest `PATCH` |
| TC-003 | Reflects avatar change | `200`, `avatarId` matches latest `PUT` |
| TC-004 | Reflects Aadhaar verification | `200`, `aadhaarVerified: true` |
| TC-005 | `badges` always empty today | `200`, `badges: {}` regardless of activity |
| TC-006 | Unauthenticated request rejected | `401 UNAUTHORIZED` |
| TC-007 | `memberSince` matches `GET /users/me` | Identical value on both endpoints |

### TC-001 — Fresh Account Defaults

`GET /api/v1/users/me/menu-summary` *(JWT)*

**200 OK:**
```json
{ "success": true, "data": { "avatarId": "avatar-01", "aadhaarVerified": false, "memberSince": "2026-08-12T10:30:00Z", "badges": {} } }
```
> `displayName` omitted if unset (`non_null` inclusion). `memberSince` = `created_at` from registration, not "now."

### TC-002 — Reflects Display-Name Update

`PATCH /users/me` with `{ "displayName": "Abhay Kumar" }`, then `GET /users/me/menu-summary` → `displayName` matches.

### TC-003 — Reflects Avatar Change

`PUT /users/me/avatar` with `{ "avatarId": "avatar-07" }`, then `GET /users/me/menu-summary` → `avatarId` matches.

### TC-004 — Reflects Aadhaar Verification

Complete US-001 Aadhaar flow, then `GET /users/me/menu-summary` → `aadhaarVerified: true`.

### TC-005 — `badges` Always Empty Today

Regardless of prior activity, `data.badges` is always `{}` (present, empty).

> Don't file "no badges for orders/offers/notifications" as a bug — those keys only appear once their owning story registers a `ProfileMenuBadgeProvider` bean (Notifications, Sprint 11 earliest).

### TC-006 — Unauthenticated Request Rejected

Logout, call `GET /users/me/menu-summary` → **401** `UNAUTHORIZED`.

### TC-007 — `memberSince` Matches `GET /users/me`

Compare `memberSince` from both endpoints — must be character-for-character identical.

### Not Testable Yet (US-103)

- The actual mobile "Profile" tab UI — mobile-side work, not covered by this backend guide.
- Any badge count (`MY_ORDERS`, `SAVED_ITEMS`, `OFFERS`, `TRANSACTIONS`, `PAYOUTS`, `NOTIFICATIONS`, `SUPPORT_TICKETS`, `DISPUTES`) — none exist yet.
- `ERROR_SECTION_UNAVAILABLE` — applies to individual menu destinations, not this summary endpoint.
- Resilience against a broken badge provider — hardened in code (one bad provider only omits its badge; duplicate keys fail app startup) but not exercisable until a real provider exists.

### US-103 Error Reference

| HTTP | Error Code | Cause |
|---|---|---|
| 401 | `UNAUTHORIZED` | Missing/expired JWT |
| 404 | `NOT_FOUND` | JWT references a deleted user (not reachable via normal use) |

---

## US-106 — Mobile OTP Login for Returning Users

Closes the gap where a returning mobile-OTP user had no way to log back in — `POST /register/initiate` explicitly rejects an already-registered mobile, and Google/Apple Sign-In are a shortcut around a primary login path that didn't otherwise exist. Implemented as a **separate** `UserLoginService` (mirrors this codebase's one-service-per-concern convention) — login never transitions account state or writes `account_status_history`; it only reads the account's current `status`/`aadhaarVerified` fresh into a newly issued JWT.

| Setting | Value |
|---|---|
| Initiate endpoint | `POST /api/v1/auth/login/initiate` *(public)* |
| Verify endpoint | `POST /api/v1/auth/login/verify-mobile` *(public)* |
| OTP Redis key | `otp:{mobile}:LOGIN` (separate namespace from registration's `MOBILE_VERIFY`) |
| Rate-limit buckets | `otp_rate:{mobile}`, `otp_fail:{mobile}` — **shared** with registration (safe: a mobile can't be simultaneously eligible for both) |

### State-Eligibility Table

`assertLoginEligible` runs at **both** initiate and verify — this double-check is what covers "account state changed between OTP send and verify."

| Account State | Login Allowed? | Result |
|---|---|---|
| `NEW`, `OTP_PENDING` | No | `ERROR_INVALID_STATE` — mobile never verified |
| `EMAIL_VERIFICATION_PENDING` | **Yes** | resumes at email step |
| `IDENTITY_VERIFICATION_PENDING` | **Yes** | resumes at Aadhaar step |
| `ACTIVE` | **Yes** | home |
| `UNDER_REVIEW`, `RESTRICTED` | **Yes** | can log in, just can't list/buy |
| `SUSPENDED` | No | `ERROR_ACCOUNT_SUSPENDED` |
| `BANNED`, `CLOSED` | No | `ERROR_ACCOUNT_RECOVERY_REQUIRED` |

### Scenarios

| TC | Scenario | Expected |
|---|---|---|
| TC-001 | Initiate login, mobile registered (ACTIVE) | `200`, OTP sent |
| TC-002 | Verify login, happy path | `200`, new JWT reflecting current DB state |
| TC-003 | Mobile not registered | `400 ERROR_MOBILE_NOT_REGISTERED` |
| TC-004 | Login blocked before mobile verification | `400 ERROR_INVALID_STATE` |
| TC-005 | Login resumes mid-registration | `200`, JWT issued for incomplete account |
| TC-006 | `UNDER_REVIEW` / `RESTRICTED` can still log in | `200` |
| TC-007 | Suspended account rejected | `400 ERROR_ACCOUNT_SUSPENDED` |
| TC-008 | Banned/closed account rejected | `400 ERROR_ACCOUNT_RECOVERY_REQUIRED` |
| TC-009 | Invalid OTP | `400 ERROR_INVALID_OTP` |
| TC-010 | Expired OTP | `400 ERROR_OTP_EXPIRED` |
| TC-011 | OTP send rate limit / verify fail limit | `400 ERROR_OTP_RATE_LIMIT` / `ERROR_OTP_MAX_ATTEMPTS` |
| TC-012 | Account suspended between initiate and verify | `400 ERROR_ACCOUNT_SUSPENDED` at verify, even though initiate succeeded |
| TC-013 | Missing `mobile`/`otp` | `400` validation error |

**Setup:** register a user via US-001 Steps 1–2 (mobile `9000000040`), then either complete or stop the flow at different states to hit each TC below.

### TC-001 — Initiate Login (Happy Path)

**Prerequisite:** user exists and is `ACTIVE` (complete full US-001 flow, or skip Aadhaar).

`POST /api/v1/auth/login/initiate` *(public)*
```json
{ "mobile": "9000000040" }
```
Check console log: `[DEV-MOCK] OTP for mobile=9000000040 purpose=LOGIN otp=XXXXXX`.

**200 OK:** `{ "success": true, "data": { "message": "OTP sent to your mobile number", "otpExpiresInSeconds": 300 } }`

### TC-002 — Verify Login, Happy Path

`POST /api/v1/auth/login/verify-mobile` *(public)*
```json
{ "mobile": "9000000040", "otp": "XXXXXX" }
```
**200 OK:**
```json
{ "success": true, "data": { "accessToken": "...", "refreshToken": "...", "aadhaarVerified": true, "userId": "...", "status": "ACTIVE" } }
```
> `aadhaarVerified` and `status` are read fresh from the DB, not carried over from any earlier token. To prove this: log in once while the account is `IDENTITY_VERIFICATION_PENDING` / `aadhaarVerified: false`, then complete Aadhaar verification in a separate session, then log in again with the same mobile — the second login's JWT must show `aadhaarVerified: true`.

### TC-003 — Mobile Not Registered

`POST /api/v1/auth/login/initiate` with a mobile that has no account, e.g. `{ "mobile": "9999999999" }`.

**400:** `{ "success": false, "error": { "code": "ERROR_MOBILE_NOT_REGISTERED", "message": "No account found with this mobile number. Please register" } }`

Same code/message if this mobile is submitted to `/login/verify-mobile` directly.

### TC-004 — Login Blocked Before Mobile Verification

**Prerequisite:** a user stuck at `NEW` or `OTP_PENDING` — i.e., `POST /register/initiate` was called but `verify-mobile` never was.

`POST /api/v1/auth/login/initiate` with that mobile.

**400:** `{ "success": false, "error": { "code": "ERROR_INVALID_STATE", "message": "Please complete your mobile number verification before logging in" } }`

### TC-005 — Login Resumes Mid-Registration

**Prerequisite:** a user at `EMAIL_VERIFICATION_PENDING` (mobile verified, email/Aadhaar not done) — or `IDENTITY_VERIFICATION_PENDING`.

`POST /api/v1/auth/login/initiate` → `POST /api/v1/auth/login/verify-mobile` — both succeed with **200 OK**, issuing a JWT with `aadhaarVerified: false` and `status` matching the incomplete state. Confirms a returning user isn't locked out just because they didn't finish registration in one sitting.

### TC-006 — `UNDER_REVIEW` / `RESTRICTED` Can Still Log In

```sql
UPDATE users SET status = 'UNDER_REVIEW' WHERE mobile = '9000000040';
```
Run the login flow — expect **200 OK** with `status: "UNDER_REVIEW"` in the response. Repeat with `status = 'RESTRICTED'`.

> These states can authenticate; they're just blocked elsewhere (listing/buying) by other checks — not this endpoint's concern.

### TC-007 — Suspended Account Rejected

```sql
UPDATE users SET status = 'SUSPENDED' WHERE mobile = '9000000040';
```
`POST /api/v1/auth/login/initiate` → **400:** `{ "success": false, "error": { "code": "ERROR_ACCOUNT_SUSPENDED", "message": "Your account is suspended. Please contact support" } }`

### TC-008 — Banned/Closed Account Rejected

```sql
UPDATE users SET status = 'BANNED' WHERE mobile = '9000000040';
```
`POST /api/v1/auth/login/initiate` → **400:** `{ "success": false, "error": { "code": "ERROR_ACCOUNT_RECOVERY_REQUIRED", "message": "Your account requires recovery. Please contact support" } }`

Same result for `status = 'CLOSED'`.

### TC-009 — Invalid OTP

`POST /api/v1/auth/login/initiate` (valid `ACTIVE` user), then `POST /api/v1/auth/login/verify-mobile` with a wrong 6-digit code.

**400:** `{ "success": false, "error": { "code": "ERROR_INVALID_OTP", "message": "Invalid or expired OTP" } }`

### TC-010 — Expired OTP

Initiate login, wait 300+ seconds (or reduce `valuex.otp.expiry-seconds` temporarily), then verify with the original OTP.

**400:** `{ "success": false, "error": { "code": "ERROR_OTP_EXPIRED", "message": "OTP has expired. Please request a new one" } }`

### TC-011 — Rate Limits

**Send limit:** call `/login/initiate` 4 times within 10 minutes for the same mobile → the 4th call returns **400** `ERROR_OTP_RATE_LIMIT`.

**Verify-fail limit:** call `/login/verify-mobile` with a wrong OTP 6 times within 10 minutes → the 6th call returns **400** `ERROR_OTP_MAX_ATTEMPTS` (checked *before* the mobile-registered/eligibility checks, same ordering as `verify-mobile` in US-001).

### TC-012 — Account Suspended Between Initiate and Verify

**Goal:** confirm `assertLoginEligible` is re-checked at verify time, not just at initiate.

1. `POST /api/v1/auth/login/initiate` for an `ACTIVE` user — succeeds, OTP sent.
2. Before verifying, suspend the account: `UPDATE users SET status = 'SUSPENDED' WHERE mobile = '9000000040';`
3. `POST /api/v1/auth/login/verify-mobile` with the correct OTP from step 1.

**400:** `{ "success": false, "error": { "code": "ERROR_ACCOUNT_SUSPENDED", "message": "Your account is suspended. Please contact support" } }` — no JWT is issued even though the OTP itself was correct.

### TC-013 — Missing `mobile` / `otp`

`POST /api/v1/auth/login/initiate` with `{}` → **400** validation error, `mobile` flagged `"Mobile number is required"`.

`POST /api/v1/auth/login/verify-mobile` with `{ "mobile": "9000000040" }` (no `otp`) → **400** validation error, `otp` flagged `"OTP is required"`.

### US-106 Reset Between Tests

Register a fresh mobile per TC (recommended), or reset status directly:
```sql
UPDATE users SET status = 'ACTIVE' WHERE mobile = '9000000040';
```

### US-106 Error Reference

| HTTP | Error Code | Cause |
|---|---|---|
| 400 | `ERROR_MOBILE_NOT_REGISTERED` | No account exists for the submitted mobile (TC-003) |
| 400 | `ERROR_INVALID_STATE` | Account is `NEW`/`OTP_PENDING` — mobile never verified (TC-004) |
| 400 | `ERROR_ACCOUNT_SUSPENDED` | Account suspended, checked at initiate and verify (TC-007, TC-012) |
| 400 | `ERROR_ACCOUNT_RECOVERY_REQUIRED` | Account banned or closed (TC-008) |
| 400 | `ERROR_OTP_RATE_LIMIT` | >3 send attempts in 10 min (TC-011) |
| 400 | `ERROR_OTP_MAX_ATTEMPTS` | >5 failed verify attempts in 10 min (TC-011) |
| 400 | `ERROR_OTP_EXPIRED` | OTP TTL (300s) elapsed (TC-010) |
| 400 | `ERROR_INVALID_OTP` | Wrong OTP value (TC-009) |
| 400 | Validation error | `mobile`/`otp` missing or malformed (TC-013) |

---

## US-107 — Access Token Refresh

**What this ships:** a **stateless** refresh endpoint. It validates the submitted refresh token (signature, expiry, type) and the account's current standing, then reissues a fresh access+refresh pair. It does **not** implement single-use rotation, theft detection, or logout-invalidation — those require session/`jti` tracking that doesn't exist yet (deferred to US-104/US-105). See LLD §14 before filing anything in "Not Testable Yet" as a bug.

| Setting | Value |
|---|---|
| Endpoint | `POST /api/v1/auth/refresh` *(public)* |

**Prerequisites:** any completed auth flow (US-001 registration, or **US-106 login**) issues a refresh token.

### Scenarios

| TC | Scenario | Expected |
|---|---|---|
| TC-001 | Refresh with a valid refresh token | `200`, new token pair, both different from originals |
| TC-002 | Refreshed token reflects current DB state | `200`, `aadhaarVerified`/`status` match latest state |
| TC-003 | Malformed/tampered refresh token | `400 ERROR_INVALID_REFRESH_TOKEN` |
| TC-004 | Access token submitted instead of refresh token | `400 ERROR_WRONG_TOKEN_TYPE` |
| TC-005 | Expired refresh token | `400 ERROR_REFRESH_TOKEN_EXPIRED` |
| TC-006 | Account suspended after token issuance | `400 ERROR_ACCOUNT_SUSPENDED` |
| TC-007 | Account banned/closed after token issuance | `400 ERROR_ACCOUNT_RECOVERY_REQUIRED` |
| TC-008 | Old refresh token still works after one use | `200` — by design, not a bug |
| TC-009 | Refresh token rejected as Bearer access token | `401` |
| TC-010 | Missing `refreshToken` in body | `400`, validation error |

### TC-001 — Refresh With a Valid Refresh Token

`POST /api/v1/auth/refresh`
```json
{ "refreshToken": "eyJhbGci..." }
```
**200 OK:** `{ "success": true, "data": { "accessToken": "...", "refreshToken": "...", "aadhaarVerified": false, "userId": "...", "status": "EMAIL_VERIFICATION_PENDING" } }`

Both tokens in the response must differ from the ones submitted.

### TC-002 — Refreshed Token Reflects Current DB State

1. Complete registration through email verification only (`IDENTITY_VERIFICATION_PENDING`), keep that `refreshToken`.
2. In a separate session, finish Aadhaar verification for the same user → `ACTIVE`, `aadhaarVerified: true`.
3. `POST /api/v1/auth/refresh` with the **original** (pre-Aadhaar) `refreshToken`.

**Expected:** response shows `aadhaarVerified: true`, `status: "ACTIVE"` — current state, not the state at token issuance.

### TC-003 — Malformed / Tampered Refresh Token

`{ "refreshToken": "not-a-real-jwt" }` → **400:** `ERROR_INVALID_REFRESH_TOKEN`, `"Session expired. Please log in again"`.

### TC-004 — Access Token Instead of Refresh Token

Submit an `accessToken` value as `refreshToken` → **400:** `ERROR_WRONG_TOKEN_TYPE`, `"Invalid token for this operation"`.

> If the access token has also expired, you may get `ERROR_REFRESH_TOKEN_EXPIRED`/`ERROR_INVALID_REFRESH_TOKEN` instead — the `type` claim is only readable after the token parses. Both tell the caller to log in again; documented, accepted imprecision (LLD §14.5 item 7).

### TC-005 — Expired Refresh Token

Not reachable in real time (7-day TTL). Temporarily set `valuex.jwt.refresh-token-expiry` to `5000` (5s), restart, get a token, wait 6s, then refresh.

**400:** `ERROR_REFRESH_TOKEN_EXPIRED`. **Revert the config change** afterward.

### TC-006 — Account Suspended After Token Issuance

```sql
UPDATE users SET status = 'SUSPENDED' WHERE mobile = '9000000030';
```
Refresh with the still-valid token → **400:** `ERROR_ACCOUNT_SUSPENDED`.

Revert: `UPDATE users SET status = 'ACTIVE' WHERE mobile = '9000000030';`

### TC-007 — Account Banned/Closed After Token Issuance

Same as TC-006 with `status = 'BANNED'` → **400:** `ERROR_ACCOUNT_RECOVERY_REQUIRED`. Same for `CLOSED`.

### TC-008 — Old Refresh Token Still Works After One Use

1. Get `refreshToken_A`.
2. `POST /auth/refresh` with `refreshToken_A` → note `refreshToken_B`.
3. `POST /auth/refresh` again with the **original** `refreshToken_A`.

**Expected:** step 3 **succeeds** (200) — no single-use rotation yet. **Do not file as a bug** — deferred to US-104/US-105 (LLD §14.2, §14.5 item 1).

### TC-009 — Refresh Token Rejected as Bearer Access Token

Authorize in Swagger UI with a **refresh token** (not access), call `GET /api/v1/users/me` → **401** `UNAUTHORIZED`.

> Before this story, a refresh token used this way authenticated successfully with a broken `role=null`. Confirming 401 here confirms the fix — flag clearly if it ever regresses to 200.

### TC-010 — Missing `refreshToken`

`{}` → **400** Jakarta validation error, `refreshToken` flagged `"Refresh token is required"`.

### Not Testable Yet (US-107)

- Single-use rotation / invalidate-on-reuse (TC-008) — deferred to US-104/US-105.
- "Replayed rotated-out token → theft, invalidate token family" — conditional on session tracking that doesn't exist.
- "Logout invalidates the refresh token" — no logout endpoint exists at all yet (US-104).
- Concurrent refresh calls near expiry — both succeed independently; direct consequence of the stateless design.
- Clock skew at the expiry boundary — pre-existing JJWT config property, not changed by this story.

### US-107 Reset Between Tests

```sql
UPDATE users SET status = 'ACTIVE' WHERE mobile = '9000000030';
```

### US-107 Error Reference

| HTTP | Error Code | Cause |
|---|---|---|
| 400 | `ERROR_INVALID_REFRESH_TOKEN` | Malformed/tampered token, signature mismatch, or unknown `sub` (TC-003) |
| 400 | `ERROR_REFRESH_TOKEN_EXPIRED` | Past 7-day expiry (TC-005) |
| 400 | `ERROR_WRONG_TOKEN_TYPE` | Non-refresh-type token submitted (TC-004) |
| 400 | `ERROR_INVALID_STATE` | Account is `NEW`/`OTP_PENDING` — not reachable via a real refresh token |
| 400 | `ERROR_ACCOUNT_SUSPENDED` | Suspended since token issuance (TC-006) |
| 400 | `ERROR_ACCOUNT_RECOVERY_REQUIRED` | Banned/closed since token issuance (TC-007) |
| 401 | `UNAUTHORIZED` | Refresh token presented as Bearer access token (TC-009) |
| 400 | Validation error | `refreshToken` missing/blank (TC-010) |

---

## Consolidated Error Code Reference (All Six Stories)

| HTTP | Error Code | Stories | Meaning |
|---|---|---|---|
| 400 | `ERROR_INVALID_STATE` | US-001, US-002, US-106, US-107 | Endpoint/flow called out of sequence for the account's current state |
| 400 | `ERROR_OTP_EXPIRED` | US-001, US-106 | OTP TTL (300s) elapsed |
| 400 | `ERROR_INVALID_OTP` | US-001, US-106 | Wrong OTP value submitted |
| 400 | `ERROR_OTP_MAX_ATTEMPTS` | US-001, US-106 | 5 failed verify attempts in 10 min |
| 400 | `ERROR_OTP_RATE_LIMIT` | US-001, US-106 | 3 send attempts in 10 min |
| 400 | `ERROR_MOBILE_ALREADY_REGISTERED` | US-001, US-002 | Mobile already has an account |
| 400 | `ERROR_EMAIL_ALREADY_REGISTERED` | US-001 | Email linked to another account |
| 400 | `ERROR_AADHAAR_ALREADY_USED` | US-001, US-002 | Aadhaar linked to an active account |
| 400 | `ERROR_ACCOUNT_RECOVERY_REQUIRED` | US-002, US-106, US-107 | Account is BANNED/CLOSED (or Aadhaar tied to one) |
| 400 | `ERROR_AADHAAR_SESSION_EXPIRED` | US-002 | >10 min between Aadhaar initiate and verify |
| 400 | `VALIDATION_ERROR` | US-003, US-106, US-107 | Field fails Jakarta Bean Validation |
| 400 | `ERROR_INVALID_AVATAR` | US-003 | `avatarId` not in the published catalog |
| 400 | `ERROR_MOBILE_NOT_REGISTERED` | US-106 | No account for the submitted mobile |
| 400 | `ERROR_ACCOUNT_SUSPENDED` | US-106, US-107 | Account is SUSPENDED |
| 400 | `ERROR_INVALID_REFRESH_TOKEN` | US-107 | Malformed/tampered/unknown-subject refresh token |
| 400 | `ERROR_REFRESH_TOKEN_EXPIRED` | US-107 | Refresh token past 7-day expiry |
| 400 | `ERROR_WRONG_TOKEN_TYPE` | US-107 | Non-refresh token submitted to `/refresh` |
| 401 | `UNAUTHORIZED` | US-001, US-003, US-103, US-107 | Missing/expired JWT, or a refresh token used as Bearer |
| 404 | `NOT_FOUND` | US-003, US-103 | JWT references a deleted user (not reachable via normal use) |

---

## Full Teardown (All Test Mobiles Used in This Guide)

```sql
DELETE FROM user_social_accounts WHERE user_id IN (
  SELECT id FROM users WHERE mobile IN (
    '9876543210','9000000001','9000000002','9000000010','9000000020','9000000030','9000000040'
  )
);
DELETE FROM aadhaar_verification_attempts WHERE user_id IN (
  SELECT id FROM users WHERE mobile IN (
    '9876543210','9000000001','9000000002','9000000010','9000000020','9000000030','9000000040'
  )
);
DELETE FROM account_status_history WHERE user_id IN (
  SELECT id FROM users WHERE mobile IN (
    '9876543210','9000000001','9000000002','9000000010','9000000020','9000000030','9000000040'
  )
);
DELETE FROM users WHERE mobile IN (
  '9876543210','9000000001','9000000002','9000000010','9000000020','9000000030','9000000040'
);
```
