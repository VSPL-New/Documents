# US-003 — User Profile Management: QA Testing Guide

**Sprint 1 · Identity & User Management**

Manual test cases for viewing/editing profile fields (display name, city) and avatar selection, using Swagger UI against a local dev environment.

> **Design note:** users do **not** upload a profile photo. They pick an `avatarId` from a fixed, backend-owned catalog (`GET /api/v1/avatars`). There is no file upload, no image content moderation, and no `ERROR_INAPPROPRIATE_CONTENT` in this version of the story — see `Documents/LLD/Sprint-1-Identity-User-Management-LLD.md` §7 (v1.4) for why.

| Setting | Value |
|---|---|
| Base URL | `http://localhost:8080` |
| Swagger UI | `http://localhost:8080/swagger-ui.html` |
| Avatar catalog (default) | `avatar-01` … `avatar-12` (see `valuex.avatar.available-ids` in `application.yml`) |
| Default avatar on a new account | `avatar-01` |
| DB Access | pgAdmin or `psql -U postgres -d valuex_dev` |

---

## Prerequisites — Get an Authenticated User

Profile endpoints only require a valid JWT — **not** email verification or Aadhaar. The fastest setup is Steps 1–2 of the US-001 flow (see `US-001-Testing-Guide.md` for full detail):

1. `POST /api/v1/auth/register/initiate`
   ```json
   { "mobile": "9000000010", "termsAccepted": true, "consentGiven": true }
   ```
2. Read the OTP from the console log (`[DEV-MOCK] OTP for mobile=9000000010 ...`), then:
   `POST /api/v1/auth/register/verify-mobile`
   ```json
   { "mobile": "9000000010", "otp": "XXXXXX" }
   ```
3. Copy `data.accessToken` and **Authorize** in Swagger UI (🔒 button, paste token, no `Bearer ` prefix).

Account state is now `EMAIL_VERIFICATION_PENDING` — sufficient for every test case below. TC-009 additionally needs Aadhaar verification completed (see that test case for the extra setup).

---

## Test Scenarios Overview

| TC | Scenario | Endpoint | Expected Result |
|---|---|---|---|
| TC-001 | View own profile (defaults) | `GET /users/me` | `200`, default avatar, masked mobile |
| TC-002 | Update display name and city | `PATCH /users/me` | `200`, both fields updated |
| TC-003 | Partial update leaves other field unchanged | `PATCH /users/me` | `200`, only the sent field changes |
| TC-004 | Reject invalid display name | `PATCH /users/me` | `400 VALIDATION_ERROR` |
| TC-005 | Reject invalid city | `PATCH /users/me` | `400 VALIDATION_ERROR` |
| TC-006 | List avatar catalog | `GET /avatars` | `200`, 12 IDs + default |
| TC-007 | Select a valid avatar | `PUT /users/me/avatar` | `200`, `avatarId` updated |
| TC-008 | Reject avatar not in catalog | `PUT /users/me/avatar` | `400 ERROR_INVALID_AVATAR` |
| TC-009 | Aadhaar-verified name is read-only | `GET/PATCH /users/me` | Field never changes via this API |
| TC-010 | Unauthenticated request rejected | `GET /users/me` | `401 UNAUTHORIZED` |

---

## TC-001 — View Own Profile (Defaults)

**Goal:** A freshly registered user has sane defaults before making any profile edits.

**Endpoint:** `GET /api/v1/users/me` *(requires JWT)*

No request body.

**Expected response (200 OK):**
```json
{
  "success": true,
  "data": {
    "userId": "uuid-here",
    "mobile": "90XXXX0010",
    "aadhaarVerified": false,
    "avatarId": "avatar-01",
    "status": "EMAIL_VERIFICATION_PENDING",
    "memberSince": "2026-08-07T..."
  }
}
```

> `displayName`, `email`, `city`, and `aadhaarName` are omitted entirely (not `null`) — the API uses `non_null` JSON inclusion, so unset fields simply don't appear. Don't file "displayName missing" as a bug; that's expected before the user ever calls `PATCH`.
>
> `avatarId` is `avatar-01` even though this user never called the avatar endpoint — it's assigned at account creation (`User.onCreate()`).

---

## TC-002 — Update Display Name and City

**Goal:** Both editable fields save correctly in a single request.

**Endpoint:** `PATCH /api/v1/users/me` *(requires JWT)*

**Request body:**
```json
{
  "displayName": "Abhay Kumar",
  "city": "Bengaluru"
}
```

**Expected response (200 OK):**
```json
{
  "success": true,
  "data": {
    "displayName": "Abhay Kumar",
    "city": "Bengaluru",
    "avatarId": "avatar-01",
    "...": "..."
  }
}
```

Confirm via `GET /api/v1/users/me` that the change persisted.

---

## TC-003 — Partial Update Leaves the Other Field Unchanged

**Goal:** `PATCH` semantics — a field omitted from the request body is left as-is, not cleared.

**Prerequisite:** TC-002 completed (`displayName = "Abhay Kumar"`, `city = "Bengaluru"`).

**Request body:**
```json
{
  "city": "Mumbai"
}
```

**Expected response (200 OK):**
```json
{
  "success": true,
  "data": {
    "displayName": "Abhay Kumar",
    "city": "Mumbai",
    "...": "..."
  }
}
```

> `displayName` must still read `"Abhay Kumar"` — sending `city` alone must not null out `displayName`.

---

## TC-004 — Reject Invalid Display Name

**Goal:** Display name validation (3–50 chars, letters/spaces/`.`/`'`/`-` only) is enforced.

**Endpoint:** `PATCH /api/v1/users/me`

Try each of these bodies in turn:

| Request | Reason it should fail |
|---|---|
| `{ "displayName": "Ab" }` | Below 3-character minimum |
| `{ "displayName": "Abhay123" }` | Digits are not allowed |
| `{ "displayName": "Abhay@Kumar" }` | `@` is not allowed |

**Expected response (400 Bad Request) for each:**
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": {
      "displayName": "Display name must be between 3 and 50 characters"
    }
  }
}
```
> The `details.displayName` message differs depending on which constraint fails (`@Size` vs `@Pattern`) — either is a correct pass for this TC, the important thing is `code: VALIDATION_ERROR` and a 400.

---

## TC-005 — Reject Invalid City

**Goal:** City validation (2–100 chars, same character rule as display name) is enforced.

**Endpoint:** `PATCH /api/v1/users/me`

**Request body:**
```json
{ "city": "P1" }
```

**Expected response (400 Bad Request):**
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": {
      "city": "City must be a valid location name"
    }
  }
}
```

> **Known simplification:** this is format validation only (letters/spaces/punctuation) — there is no exhaustive Indian city/state whitelist backing it, so a nonsense-but-alphabetic value (e.g. `"Notacity"`) will currently **pass**. That's expected per the LLD, not a bug to file.

---

## TC-006 — List Avatar Catalog

**Goal:** The catalog endpoint returns the full set of selectable avatars.

**Endpoint:** `GET /api/v1/avatars` *(requires JWT)*

**Expected response (200 OK):**
```json
{
  "success": true,
  "data": {
    "avatarIds": [
      "avatar-01", "avatar-02", "avatar-03", "avatar-04",
      "avatar-05", "avatar-06", "avatar-07", "avatar-08",
      "avatar-09", "avatar-10", "avatar-11", "avatar-12"
    ],
    "defaultAvatarId": "avatar-01"
  }
}
```

---

## TC-007 — Select a Valid Avatar

**Goal:** Choosing an avatar from the catalog updates the profile.

**Endpoint:** `PUT /api/v1/users/me/avatar` *(requires JWT)*

**Request body:**
```json
{ "avatarId": "avatar-07" }
```

**Expected response (200 OK):**
```json
{
  "success": true,
  "data": {
    "avatarId": "avatar-07",
    "...": "..."
  }
}
```

Confirm via `GET /api/v1/users/me` that `avatarId` is now `"avatar-07"`.

---

## TC-008 — Reject Avatar Not in Catalog

**Goal:** An `avatarId` that isn't published is rejected, and the user's existing selection is untouched.

**Endpoint:** `PUT /api/v1/users/me/avatar`

**Request body:**
```json
{ "avatarId": "avatar-99" }
```

**Expected response (400 Bad Request):**
```json
{
  "success": false,
  "error": {
    "code": "ERROR_INVALID_AVATAR",
    "message": "Selected avatar is not available. Please choose another"
  }
}
```

Confirm via `GET /api/v1/users/me` that `avatarId` is unchanged from before this call.

**Also try:** `{ "avatarId": "" }` — expect `400 VALIDATION_ERROR` (`avatarId` is `@NotBlank`), a different code than `ERROR_INVALID_AVATAR`. Don't conflate the two in a bug report.

---

## TC-009 — Aadhaar-Verified Name Is Read-Only

**Goal:** There is no way to set or change `aadhaarName` through the profile API — it only ever comes from Aadhaar verification (US-001).

**Prerequisites:** Complete the full US-001 flow through Aadhaar verification for this user (email OTP, then `POST /aadhaar/initiate` + `POST /aadhaar/verify` with the sandbox provider — see `US-001-Testing-Guide.md` Steps 3–6). After this, `GET /api/v1/users/me` should show an `aadhaarName` field.

### Step 1 — Confirm the field is present after verification
`GET /api/v1/users/me` → response should include `"aadhaarName": "..."` and `"aadhaarVerified": true`.

### Step 2 — Attempt to overwrite it via PATCH
`PATCH /api/v1/users/me`
```json
{
  "displayName": "Abhay Kumar",
  "aadhaarName": "Someone Else"
}
```

**Expected response (200 OK)** — the request succeeds (unknown JSON fields are silently ignored, not rejected), but:
```json
{
  "success": true,
  "data": {
    "displayName": "Abhay Kumar",
    "aadhaarName": "<original value from Aadhaar verification, unchanged>",
    "...": "..."
  }
}
```

> `UpdateProfileRequest` has no `aadhaarName` property at all — there is structurally no code path that could write to it from this endpoint. This is a stronger guarantee than "the field is ignored"; it's "the field cannot exist in the parsed request object."

---

## TC-010 — Unauthenticated Request Rejected

**Goal:** All profile/avatar endpoints require a valid JWT.

**Steps:** In Swagger UI, click **Authorize 🔒** → **Logout** (or open the endpoint in an incognito tab / curl without an `Authorization` header), then call `GET /api/v1/users/me`.

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

Repeat for `PATCH /api/v1/users/me`, `PUT /api/v1/users/me/avatar`, and `GET /api/v1/avatars` — all four must reject with the same `401`.

---

## Not Testable Yet (Don't File as Bugs)

- **Viewing another user's profile** (e.g. as a buyer looking at a seller) — there is no public "view profile by ID" endpoint yet. `GET /api/v1/users/me` only ever returns the caller's own profile. Public profile viewing arrives with listing details in a later sprint (US-012).
- **Rating/joined-date shown alongside profile** — ratings don't exist until the Ratings & Reviews sprint; `memberSince` (from `createdAt`) is the only "joined date" available right now.
- **Profile photo upload / image moderation** — intentionally removed from this story. See the design note at the top of this document.

---

## Reset Between Tests

Either register a fresh mobile number per TC (recommended — matches how the app actually issues accounts), or reset the same test user's editable fields directly:

```sql
UPDATE users
SET display_name = NULL,
    city = NULL,
    avatar_id = 'avatar-01'
WHERE mobile = '9000000010';
```

To remove the test user entirely (cascades to related tables):
```sql
DELETE FROM aadhaar_verification_attempts WHERE user_id IN (SELECT id FROM users WHERE mobile = '9000000010');
DELETE FROM user_social_accounts WHERE user_id IN (SELECT id FROM users WHERE mobile = '9000000010');
DELETE FROM account_status_history WHERE user_id IN (SELECT id FROM users WHERE mobile = '9000000010');
DELETE FROM users WHERE mobile = '9000000010';
```

---

## Error Reference

| HTTP | Error Code | Cause |
|---|---|---|
| 400 | `VALIDATION_ERROR` | `displayName`/`city`/`avatarId` fails `@Size`/`@Pattern`/`@NotBlank` (TC-004, TC-005, TC-008) |
| 400 | `ERROR_INVALID_AVATAR` | `avatarId` is well-formed but not in `valuex.avatar.available-ids` (TC-008) |
| 401 | `UNAUTHORIZED` | Missing or expired JWT (TC-010) |
| 404 | `NOT_FOUND` | JWT references a user that no longer exists in the DB — not reachable via normal API use; only occurs if the account row was deleted out-of-band after the token was issued |
