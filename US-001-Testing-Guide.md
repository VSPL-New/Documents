# US-001 — User Registration via Mobile OTP: QA Testing Guide

**Sprint 1 · Identity & User Management**

End-to-end test sequence for the full registration flow (mobile OTP → email OTP → Aadhaar) using Swagger UI against a local dev environment.

| Setting | Value |
|---|---|
| Base URL | `http://localhost:8080` |
| Swagger UI | `http://localhost:8080/swagger-ui.html` |
| SMS OTP Provider | `mock` (OTP printed to app console) |
| Email OTP Provider | `mock` (OTP printed to app console) |
| Aadhaar Provider | `sandbox` (no real Aadhaar call) |

---

## Registration Flow

```
Step 1 (Initiate) → Step 2 (Verify Mobile) → Authorize → Step 3 (Send Email OTP) → Step 4 (Verify Email OTP)
                                                                                              ↓
                                                                    Step 5a (Skip Aadhaar) ← → Step 5b (Initiate Aadhaar) → Step 6 (Verify Aadhaar)
```

| Step | Endpoint | Auth | Account State After |
|---|---|---|---|
| 1 | `POST /register/initiate` | None | `OTP_PENDING` |
| 2 | `POST /register/verify-mobile` | None | `EMAIL_VERIFICATION_PENDING` |
| 3 | `POST /email/send-otp` | JWT | `EMAIL_VERIFICATION_PENDING` |
| 4 | `POST /email/verify-otp` | JWT | `IDENTITY_VERIFICATION_PENDING` |
| 5a | `POST /register/skip-aadhaar` | JWT | `ACTIVE` (`aadhaarVerified=false`) |
| 5b | `POST /aadhaar/initiate` | JWT | `IDENTITY_VERIFICATION_PENDING` |
| 6 | `POST /aadhaar/verify` | JWT | `ACTIVE` (`aadhaarVerified=true`) |

> **Aadhaar is optional at registration.** A user who skips Aadhaar (Step 5a) reaches `ACTIVE` but cannot complete transactions until Aadhaar is verified.

---

## Step 1 — Initiate Registration

**Endpoint:** `POST /api/v1/auth/register/initiate` *(public — no token needed)*

**Request body:**
```json
{
  "mobile": "9876543210",
  "termsAccepted": true,
  "consentGiven": true
}
```

After executing, check the **application console log** for the OTP:
```
[DEV-MOCK] OTP for mobile=9876543210 purpose=MOBILE_VERIFY otp=XXXXXX
```

**Expected response (200 OK):**
```json
{
  "success": true,
  "data": {
    "message": "OTP sent to your mobile number",
    "otpExpiresInSeconds": 300
  }
}
```

---

## Step 2 — Verify Mobile OTP

**Endpoint:** `POST /api/v1/auth/register/verify-mobile` *(public — no token needed)*

**Request body:**
```json
{
  "mobile": "9876543210",
  "otp": "XXXXXX"
}
```
> Replace `XXXXXX` with the 6-digit code from the console log in Step 1.

**Expected response (200 OK):**
```json
{
  "success": true,
  "data": {
    "accessToken": "eyJhbGci...",
    "refreshToken": "eyJhbGci...",
    "aadhaarVerified": false,
    "userId": "uuid-here"
  }
}
```

> **Copy `data.accessToken`** — you need it for the next step.
>
> Account state after this step: `EMAIL_VERIFICATION_PENDING`.

---

## Step 2b — Authorize in Swagger UI

1. Click the **Authorize 🔒** button in the top-right of the Swagger UI page.
2. In the **bearerAuth** field, paste the `accessToken` value — **no `Bearer ` prefix**. Swagger adds it automatically.
3. Click **Authorize** → **Close**.

All subsequent calls will include `Authorization: Bearer <token>` automatically.

---

## Step 3 — Send Email OTP

**Endpoint:** `POST /api/v1/auth/email/send-otp` *(requires JWT)*

**Request body:**
```json
{
  "email": "user@example.com"
}
```

After executing, check the **application console log** for the email OTP:
```
[DEV-MOCK] Email OTP for email=user@example.com purpose=EMAIL_VERIFY otp=XXXXXX
```

**Expected response (200 OK):**
```json
{
  "success": true,
  "data": {
    "message": "OTP sent to user@example.com",
    "otpExpiresInSeconds": 300
  }
}
```

---

## Step 4 — Verify Email OTP

**Endpoint:** `POST /api/v1/auth/email/verify-otp` *(requires JWT)*

**Request body:**
```json
{
  "email": "user@example.com",
  "otp": "XXXXXX"
}
```
> Replace `XXXXXX` with the 6-digit code from the console log in Step 3.

**Expected response (200 OK):**
```json
{
  "success": true,
  "data": {
    "message": "Email verified successfully"
  }
}
```

> Account state is now `IDENTITY_VERIFICATION_PENDING`. Proceed to Step 5a (skip Aadhaar) or Step 5b (verify Aadhaar now).

---

## Step 5a — Skip Aadhaar (optional path)

**Endpoint:** `POST /api/v1/auth/register/skip-aadhaar` *(requires JWT)*

No request body required.

**Expected response (200 OK):**
```json
{
  "success": true,
  "data": {
    "accessToken": "eyJhbGci...",
    "refreshToken": "eyJhbGci...",
    "aadhaarVerified": false,
    "userId": "uuid-here"
  }
}
```

> Account state is now `ACTIVE`. The user can browse the marketplace but **cannot complete transactions** until Aadhaar is verified.
>
> Re-authorize in Swagger UI (Step 2b) with the new `accessToken` if you plan to test more endpoints.

---

## Step 5c — Completing Aadhaar Later, After Skipping (Bug-001, fixed)

**Goal:** confirm a user who took the Step 5a skip path can still come back later and complete
Aadhaar verification — this was broken (GitHub issue #158 / Bug-001) until it was fixed: the
account is `ACTIVE` at this point, but `POST /aadhaar/initiate` used to reject anything other than
`IDENTITY_VERIFICATION_PENDING`, leaving skip-path users with no way back in.

**Steps:** with the `ACTIVE`, `aadhaarVerified: false` token from Step 5a still authorized, run
Steps 5b and 6 exactly as written below — no different request shape, just a different starting
account state than the normal flow.

**Expected:** both calls succeed exactly as documented in Steps 5b/6. The final `GET /users/me`
(or the `AuthResponse` from Step 6) shows `status: "ACTIVE"` (unchanged — there was no state to
transition, the account was already `ACTIVE`) and `aadhaarVerified: true`.

```sql
-- Confirm the audit trail recorded it even though from_status = to_status = ACTIVE:
SELECT from_status, to_status, action, changed_at FROM account_status_history
WHERE user_id = '<the test user id>' ORDER BY changed_at DESC LIMIT 1;
-- Expect: from_status=ACTIVE, to_status=ACTIVE, action=VERIFY_IDENTITY
```

---

## Step 5b — Initiate Aadhaar Verification

**Endpoint:** `POST /api/v1/auth/aadhaar/initiate` *(requires JWT)*

**Request body:**
```json
{
  "aadhaarNumber": "123456789012",
  "consentToken": "consent-ts-123"
}
```

**Expected response (200 OK):**
```json
{
  "success": true,
  "data": {
    "transactionId": "sandbox-txn-..."
  }
}
```

> **Copy `data.transactionId`** — you need it for Step 6.
>
> The sandbox provider generates a `transactionId` prefixed `sandbox-txn-`. No real Aadhaar OTP is sent.

---

## Step 6 — Complete Aadhaar Verification

**Endpoint:** `POST /api/v1/auth/aadhaar/verify` *(requires JWT)*

**Request body:**
```json
{
  "transactionId": "sandbox-txn-...",
  "otp": "123456"
}
```
> `transactionId` is from Step 5b. The sandbox accepts `"123456"` as the passing OTP.

**Expected response (200 OK):**
```json
{
  "success": true,
  "data": {
    "accessToken": "eyJhbGci...",
    "refreshToken": "eyJhbGci...",
    "aadhaarVerified": true,
    "userId": "uuid-here"
  }
}
```

> Account state is now `ACTIVE` with `aadhaarVerified: true`. Re-authorize in Swagger UI with the new token — this token is required for marketplace transaction endpoints.

---

## Common Errors

| HTTP | Error Code | Cause & Fix |
|---|---|---|
| 401 | `UNAUTHORIZED` | Missing or expired JWT on a protected endpoint. Repeat Steps 2–2b to get a fresh token. |
| 400 | `ERROR_INVALID_STATE` | Endpoint called out of order (e.g., Aadhaar before email, or email OTP before mobile verify). Follow the flow above. |
| 400 | `ERROR_OTP_EXPIRED` | OTP TTL is 300 s. Re-run Step 1 (mobile) or Step 3 (email) to generate a new one. |
| 400 | `ERROR_INVALID_OTP` | Wrong OTP value. Check the console log for the correct 6-digit code. |
| 400 | `ERROR_OTP_MAX_ATTEMPTS` | 5 failed verify attempts within the 10-minute window. Wait for the window to reset or request a new OTP. |
| 400 | `ERROR_OTP_RATE_LIMIT` | 3 send attempts within the 10-minute window. Wait before requesting another OTP. |
| 400 | `ERROR_MOBILE_ALREADY_REGISTERED` | Mobile already has an account. Use a different number or clear the `users` table in the dev DB. |
| 400 | `ERROR_EMAIL_ALREADY_REGISTERED` | Email is linked to another account. Use a different email address. |
| 400 | `ERROR_AADHAAR_ALREADY_USED` | Aadhaar number is linked to another account. Use a different 12-digit number in Step 5b. |
