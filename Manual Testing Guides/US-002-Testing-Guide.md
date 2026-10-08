# US-002 — One Account Per User Enforcement: QA Testing Guide

**Sprint 1 · Identity & User Management**

Manual test cases for validating Aadhaar uniqueness enforcement, differentiated error responses by account state, and Google Sign-In rejection for banned mobile accounts.

| Setting | Value |
|---|---|
| Base URL | `http://localhost:8080` |
| Swagger UI | `http://localhost:8080/swagger-ui.html` |
| Aadhaar Provider | `sandbox` (accepts any 12-digit number; OTP `123456` always passes) |
| DB Access | pgAdmin or `psql -U postgres -d valuex_dev` |

---

## Test Scenarios Overview

| TC | Scenario | Existing Account State | Expected Error |
|---|---|---|---|
| TC-001 | Duplicate Aadhaar — owner is ACTIVE | `ACTIVE` | `ERROR_AADHAAR_ALREADY_USED` |
| TC-002 | Duplicate Aadhaar — owner is SUSPENDED | `SUSPENDED` | `ERROR_ACCOUNT_RECOVERY_REQUIRED` |
| TC-003 | Duplicate Aadhaar — owner is BANNED | `BANNED` | `ERROR_ACCOUNT_RECOVERY_REQUIRED` + security log |
| TC-004 | Duplicate mobile at registration | Any | `ERROR_MOBILE_ALREADY_REGISTERED` |
| TC-005 | Google Sign-In with BANNED mobile | `BANNED` | `ERROR_ACCOUNT_RECOVERY_REQUIRED` |
| TC-006 | First-time Aadhaar use (happy path) | — | `200 OK` success |

---

## Setup — Register a Base User (User A)

All TC-001 through TC-003 require a user whose Aadhaar is already in the system. Complete the full US-001 registration flow for **User A** first:

1. `POST /api/v1/auth/register/initiate` with `"mobile": "9000000001"`
2. Verify mobile OTP from console → copy `accessToken`
3. Authorize in Swagger UI with that token
4. `POST /api/v1/auth/email/send-otp` → `POST /api/v1/auth/email/verify-otp`
5. `POST /api/v1/auth/aadhaar/initiate` with the **test Aadhaar for each TC** (see table below)
6. `POST /api/v1/auth/aadhaar/verify` with OTP `123456` → User A is now `ACTIVE` with Aadhaar verified

| TC | Use this Aadhaar for User A |
|---|---|
| TC-001 | `111111111111` |
| TC-002 | `222222222222` |
| TC-003 | `333333333333` |

After the base user is set up, proceed to the relevant TC.

---

## TC-001 — Duplicate Aadhaar, Owner is ACTIVE

**Goal:** A second user cannot verify with an Aadhaar already linked to an active account.

**Prerequisites:** User A registered with Aadhaar `111111111111` (ACTIVE, aadhaarVerified = true).

### Steps

**1. Register User B (new mobile)**

`POST /api/v1/auth/register/initiate`
```json
{
  "mobile": "9000000002",
  "termsAccepted": true,
  "consentGiven": true
}
```

**2. Verify mobile OTP, send + verify email OTP** — follow US-001 Steps 2–4.
User B is now `IDENTITY_VERIFICATION_PENDING`.

**3. Attempt Aadhaar initiation with User A's Aadhaar**

`POST /api/v1/auth/aadhaar/initiate` *(requires User B's JWT)*
```json
{
  "aadhaarNumber": "111111111111",
  "consentToken": "consent-ts-001"
}
```

**Expected response (400 Bad Request):**
```json
{
  "success": false,
  "error": {
    "code": "ERROR_AADHAAR_ALREADY_USED",
    "message": "This Aadhaar is already linked to an account"
  }
}
```

**Console log:** No security event log (normal duplicate — not a threat).

---

## TC-002 — Duplicate Aadhaar, Owner is SUSPENDED

**Goal:** Attempting to use an Aadhaar belonging to a suspended account returns a recovery-specific error.

**Prerequisites:** User A registered with Aadhaar `222222222222` (ACTIVE). Then set their status to SUSPENDED via SQL.

### DB Setup — Suspend User A

```sql
UPDATE users SET status = 'SUSPENDED' WHERE mobile = '9000000001';
```

Verify:
```sql
SELECT mobile, status, aadhaar_verified FROM users WHERE mobile = '9000000001';
```

### Steps

**1. Register User B** with `"mobile": "9000000002"` → complete mobile + email verification → `IDENTITY_VERIFICATION_PENDING`.

**2. Attempt Aadhaar initiation**

`POST /api/v1/auth/aadhaar/initiate` *(requires User B's JWT)*
```json
{
  "aadhaarNumber": "222222222222",
  "consentToken": "consent-ts-002"
}
```

**Expected response (400 Bad Request):**
```json
{
  "success": false,
  "error": {
    "code": "ERROR_ACCOUNT_RECOVERY_REQUIRED",
    "message": "This Aadhaar is linked to a suspended account. Please contact support"
  }
}
```

---

## TC-003 — Duplicate Aadhaar, Owner is BANNED (Security Event)

**Goal:** Attempting to use an Aadhaar from a banned account is blocked AND logged as a security event.

**Prerequisites:** User A registered with Aadhaar `333333333333` (ACTIVE). Then set their status to BANNED via SQL.

### DB Setup — Ban User A

```sql
UPDATE users SET status = 'BANNED' WHERE mobile = '9000000001';
```

### Steps

**1. Register User B** with `"mobile": "9000000002"` → complete mobile + email verification → `IDENTITY_VERIFICATION_PENDING`.

**2. Attempt Aadhaar initiation**

`POST /api/v1/auth/aadhaar/initiate` *(requires User B's JWT)*
```json
{
  "aadhaarNumber": "333333333333",
  "consentToken": "consent-ts-003"
}
```

**Expected response (400 Bad Request):**
```json
{
  "success": false,
  "error": {
    "code": "ERROR_ACCOUNT_RECOVERY_REQUIRED",
    "message": "This Aadhaar is linked to a closed account. Please contact support"
  }
}
```

**Expected console log (WARN level):**
```
WARN  AadhaarVerificationService - SECURITY_EVENT: Aadhaar reuse on BANNED/CLOSED account
      requesterUserId=<User B UUID> existingUserId=<User A UUID>
```

> This log entry is the audit trail required by US-002 acceptance criteria.

---

## TC-004 — Duplicate Mobile at Registration

**Goal:** A mobile number already registered cannot be used to create a second account.

**Prerequisites:** Any existing account with mobile `9000000001` (any state).

### Steps

`POST /api/v1/auth/register/initiate`
```json
{
  "mobile": "9000000001",
  "termsAccepted": true,
  "consentGiven": true
}
```

**Expected response (400 Bad Request):**
```json
{
  "success": false,
  "error": {
    "code": "ERROR_MOBILE_ALREADY_REGISTERED",
    "message": "An account with this mobile number already exists"
  }
}
```

> This check fires before any OTP is sent, so no console OTP log appears.

---

## TC-005 — Google Sign-In with BANNED Mobile

**Goal:** When a Google user tries to link to a mobile number that belongs to a BANNED account, they receive a recovery error instead of proceeding.

**Prerequisites:** An account exists with mobile `9000000001` and status `BANNED`.

```sql
-- If no such account exists, create one first via US-001 flow then:
UPDATE users SET status = 'BANNED' WHERE mobile = '9000000001';
```

### Steps

**1. Initiate Google Sign-In**

`POST /api/v1/auth/social/google`
```json
{
  "idToken": "mock-newuser"
}
```

Expected: `requiresMobileVerification: true` with a `socialSessionToken`.

**2. Attempt to link the banned mobile**

`POST /api/v1/auth/social/google/initiate-mobile`
```json
{
  "socialSessionToken": "<token from step 1>",
  "mobile": "9000000001",
  "termsAccepted": true,
  "consentGiven": true
}
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

> Non-ACTIVE accounts that are not BANNED/CLOSED (e.g., `EMAIL_VERIFICATION_PENDING`) return `ERROR_INVALID_STATE` instead — the user should complete their original registration.

---

## TC-006 — First-Time Aadhaar Use (Happy Path)

**Goal:** Confirm that a unique Aadhaar number (not previously used) passes the uniqueness check and proceeds to OTP verification.

**Prerequisites:** No account in the system has Aadhaar `999999999999`.

```sql
-- Verify no existing record:
SELECT id FROM users WHERE aadhaar_hash IS NOT NULL;
-- Or check specific hash (SHA-256 of "999999999999")
```

### Steps

Register a fresh user → complete mobile + email OTP → `IDENTITY_VERIFICATION_PENDING`, then:

`POST /api/v1/auth/aadhaar/initiate`
```json
{
  "aadhaarNumber": "999999999999",
  "consentToken": "consent-ts-999"
}
```

**Expected response (200 OK):**
```json
{
  "success": true,
  "data": {
    "transactionId": "sandbox-txn-...",
    "message": "OTP sent to your Aadhaar-linked mobile number"
  }
}
```

Then complete with `POST /api/v1/auth/aadhaar/verify` using OTP `123456`.

---

## Reset Between Tests

After each TC, clean up the test users to avoid state leaking into the next test:

```sql
-- Delete by mobile (cascades to social_accounts, aadhaar_attempts)
DELETE FROM user_social_accounts WHERE user_id IN (
  SELECT id FROM users WHERE mobile IN ('9000000001', '9000000002')
);
DELETE FROM aadhaar_verification_attempts WHERE user_id IN (
  SELECT id FROM users WHERE mobile IN ('9000000001', '9000000002')
);
DELETE FROM account_status_history WHERE user_id IN (
  SELECT id FROM users WHERE mobile IN ('9000000001', '9000000002')
);
DELETE FROM users WHERE mobile IN ('9000000001', '9000000002');
```

---

## Error Reference

| HTTP | Error Code | Scenario |
|---|---|---|
| 400 | `ERROR_AADHAAR_ALREADY_USED` | Aadhaar is linked to an active/normal account (TC-001) |
| 400 | `ERROR_ACCOUNT_RECOVERY_REQUIRED` | Aadhaar linked to SUSPENDED/UNDER_REVIEW/RESTRICTED account (TC-002) |
| 400 | `ERROR_ACCOUNT_RECOVERY_REQUIRED` | Aadhaar linked to BANNED/CLOSED account — also logs security event (TC-003) |
| 400 | `ERROR_MOBILE_ALREADY_REGISTERED` | Mobile number already has an account (TC-004) |
| 400 | `ERROR_ACCOUNT_RECOVERY_REQUIRED` | Google linking attempted on BANNED/CLOSED mobile (TC-005) |
| 400 | `ERROR_INVALID_STATE` | Google linking attempted on incomplete-registration mobile (not TC-005 — separate case) |
| 400 | `ERROR_AADHAAR_SESSION_EXPIRED` | More than 10 minutes elapsed between initiate and verify — re-run initiate |
| 400 | `ERROR_INVALID_STATE` | Aadhaar initiation attempted before email verification is complete |
