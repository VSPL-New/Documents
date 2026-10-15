# US-105 — Account Security Settings: QA Testing Guide

**Sprint 1 · Identity & User Management**

Manual test cases for mobile/email change, the account-security summary, and active-session
management, using Swagger UI against a local dev environment.

> **What this story actually ships:** an account-security summary endpoint, OTP-verified mobile
> and email change, an active-sessions list, and "log out of all other devices." It introduces the
> `user_sessions` table that US-104 (Logout) deliberately shipped without — logging out one
> session now also removes it from this story's session list. The "Delete My Account" entry point
> is a **static URL only** — the real deletion flow is Sprint 14 (US-063/US-098); tapping it today
> is expected to be a dead end, not a bug. See `Documents/LLD/Sprint-1-Identity-User-Management-LLD.md`
> §10 for the full design.

| Setting | Value |
|---|---|
| Base URL | `http://localhost:8080` |
| Swagger UI | `http://localhost:8080/swagger-ui.html` (tag: **Account Security**) |
| OTP length / TTL | 6 digits / 300 s (shared `otp.*` config, same as every other OTP flow) |
| OTP send limit | 3 per 10 min per target value |
| OTP verify-fail limit | 5 per 10 min per target value |
| Session list size | Top 10 non-revoked sessions, most recent first |

---

## Prerequisites — Get an Authenticated User

Any completed auth flow works (see `US-001-Testing-Guide.md` or the US-106 login flow in the
combined Sprint-1 guide). Fastest path:

1. `POST /api/v1/auth/register/initiate` with `{ "mobile": "9000000060", "termsAccepted": true, "consentGiven": true }`
2. Verify mobile OTP from console log → copy `accessToken` → **Authorize** in Swagger UI.
3. For email-related tests, also complete `POST /api/v1/auth/email/send-otp` +
   `POST /api/v1/auth/email/verify-otp` (see `US-001-Testing-Guide.md` Steps 3–4) so the account
   has an email on file.

---

## Test Scenarios Overview

| TC | Scenario | Expected |
|---|---|---|
| TC-001 | View account security summary | `200`, masked mobile/email, `deleteAccountUrl` present |
| TC-002 | Unauthenticated summary request | `401 UNAUTHORIZED` |
| TC-003 | Initiate mobile change | `200`, OTP sent to the **new** number |
| TC-004 | Verify mobile change | `200`, mobile updated; old number no longer valid for login |
| TC-005 | Reject mobile change to an already-registered number | `400 ERROR_MOBILE_ALREADY_REGISTERED` |
| TC-006 | Reject mobile verify with wrong OTP | `400 ERROR_INVALID_OTP`, mobile unchanged |
| TC-007 | Reject mobile verify with expired OTP | `400 ERROR_OTP_EXPIRED` |
| TC-008 | Old mobile stays active until the change is verified | Old number still works for login mid-flow |
| TC-009 | Initiate + verify email change | `200` both steps, email updated |
| TC-010 | Reject email change to an already-registered email | `400 ERROR_EMAIL_ALREADY_REGISTERED` |
| TC-011 | OTP send rate limit on change-initiate | `400 ERROR_OTP_RATE_LIMIT` on the 4th call |
| TC-012 | OTP fail limit on change-verify | `400 ERROR_OTP_MAX_ATTEMPTS` on the 6th wrong attempt |
| TC-013 | List active sessions with `current` flagged | `200`, exactly one session marked current |
| TC-014 | Log out of all other devices | `200`, other session's tokens die; caller's session untouched |
| TC-015 | Revoke-others with no other sessions | `400 ERROR_NO_OTHER_SESSIONS` |
| TC-016 | Logout (US-104) removes a session from this list | Session absent from a later `GET /sessions` |
| TC-017 | Reject mobile change to your own current number | `400 ERROR_SAME_MOBILE`, no OTP sent |
| TC-018 | Reject email change to your own current email | `400 ERROR_SAME_EMAIL` (any letter case), no OTP sent |

---

## TC-001 — View Account Security Summary

**Endpoint:** `GET /api/v1/users/me/account-security` *(JWT required)*

**Expected response (200 OK):**
```json
{
  "success": true,
  "data": {
    "mobile": "90XXXX0060",
    "email": "us***@example.com",
    "aadhaarVerified": false,
    "deleteAccountUrl": "/api/v1/users/me/deletion-request"
  }
}
```
> Masking reuses the same `maskMobile`/`maskEmail` logic already shown on `GET /users/me` (US-003)
> — expect identical masking behavior between the two endpoints.

---

## TC-002 — Unauthenticated Summary Request

Logout in Swagger UI (or omit the `Authorization` header), then call
`GET /api/v1/users/me/account-security`.

**Expected response (401 Unauthorized):**
```json
{ "success": false, "error": { "code": "UNAUTHORIZED", "message": "Authentication required" } }
```

---

## TC-003 — Initiate Mobile Change

**Endpoint:** `POST /api/v1/users/me/mobile/change/initiate` *(JWT required)*
```json
{ "newMobile": "9000000061" }
```
Check console log: `[DEV-MOCK] OTP for mobile=9000000061 purpose=MOBILE_CHANGE otp=XXXXXX`.

**Expected response (200 OK):**
```json
{ "success": true, "data": { "message": "OTP sent to your new mobile number", "otpExpiresInSeconds": 300 } }
```

---

## TC-004 — Verify Mobile Change

**Endpoint:** `POST /api/v1/users/me/mobile/change/verify`
```json
{ "newMobile": "9000000061", "otp": "XXXXXX" }
```

**Expected response (200 OK):** `{ "success": true, "data": { "message": "Mobile number updated" } }`

Confirm via `GET /api/v1/users/me/account-security` that the masked mobile now reflects
`9000000061`.

---

## TC-005 — Reject Mobile Change to an Already-Registered Number

**Prerequisite:** a second account already exists with mobile `9000000062` (any state).

`POST /api/v1/users/me/mobile/change/initiate`
```json
{ "newMobile": "9000000062" }
```

**Expected response (400 Bad Request):**
```json
{ "success": false, "error": { "code": "ERROR_MOBILE_ALREADY_REGISTERED", "message": "This mobile number is already registered with another account" } }
```
No OTP is sent for this call.

---

## TC-006 — Reject Mobile Verify With Wrong OTP

After TC-003's initiate step, call verify with an incorrect code:
```json
{ "newMobile": "9000000061", "otp": "000000" }
```

**Expected response (400 Bad Request):** `ERROR_INVALID_OTP`. Confirm via
`GET /api/v1/users/me/account-security` that the mobile is unchanged.

---

## TC-007 — Reject Mobile Verify With Expired OTP

Initiate a mobile change, wait 300+ seconds (or temporarily reduce `valuex.otp.expiry-seconds`),
then verify with the original code.

**Expected response (400 Bad Request):** `ERROR_OTP_EXPIRED`.

---

## TC-008 — Old Mobile Stays Active Until Verified

**Goal:** confirm the AC's "old value remains active until new one is verified" rule.

**Steps:**
1. `POST /api/v1/users/me/mobile/change/initiate` with a new mobile — **do not verify yet**.
2. In a separate flow, attempt `POST /api/v1/auth/login/initiate` with the **original** mobile
   (see US-106 login flow).

**Expected:** step 2 succeeds normally — the original mobile is still fully valid for login. The
pending change has no effect until its own verify step completes.

---

## TC-009 — Initiate + Verify Email Change

Mirrors TC-003/TC-004 exactly, against `/email/change/initiate|verify`:
```json
{ "newEmail": "newaddress@example.com" }
```
then
```json
{ "newEmail": "newaddress@example.com", "otp": "XXXXXX" }
```
**Expected:** `200` on both calls; the second returns `{ "message": "Email updated" }`. Confirm via
`GET /account-security` that the masked email changed.

---

## TC-010 — Reject Email Change to an Already-Registered Email

Same shape as TC-005, against `/email/change/initiate` with an email already used by another
account → `400 ERROR_EMAIL_ALREADY_REGISTERED`.

---

## TC-011 — OTP Send Rate Limit

Call `/mobile/change/initiate` (or `/email/change/initiate`) **4 times within 10 minutes** for the
same target value. The 4th call returns **400** `ERROR_OTP_RATE_LIMIT`.

---

## TC-012 — OTP Verify Fail Limit

Call the corresponding `/verify` endpoint with a wrong OTP **6 times within 10 minutes**. The 6th
call returns **400** `ERROR_OTP_MAX_ATTEMPTS` — checked before the OTP itself is even looked up,
same ordering as every other OTP-verify flow in this codebase.

---

## TC-013 — List Active Sessions With `current` Flagged

**Steps:**
1. Complete a login for this account in a second "session" (e.g. a second Swagger tab, or the
   US-106 login flow reusing the same mobile) — now two sessions exist.
2. `GET /api/v1/users/me/sessions` using either session's access token.

**Expected response (200 OK):**
```json
{
  "success": true,
  "data": [
    { "sessionId": "...", "deviceInfo": "...", "ipAddress": "127.0.0.1", "createdAt": "...", "lastActiveAt": "...", "current": true },
    { "sessionId": "...", "deviceInfo": "...", "ipAddress": "127.0.0.1", "createdAt": "...", "lastActiveAt": "...", "current": false }
  ]
}
```
Exactly **one** entry has `current: true` — the session whose token you called the endpoint
with. Calling the same endpoint with the *other* session's token flips which entry is `current`.

> `deviceInfo` reflects whatever `User-Agent` header Swagger/your HTTP client sent — don't expect
> a friendly device name like "iPhone 14," just the raw header value.

---

## TC-014 — Log Out of All Other Devices

**Steps:**
1. From TC-013's two-session setup, call `POST /api/v1/users/me/sessions/revoke-others` using
   Session A's token.
2. `GET /api/v1/users/me` using Session B's (the *other* session's) access token.
3. `GET /api/v1/users/me` using Session A's (the caller's) access token.

**Expected:**
- Step 1: `200`, `{ "message": "Logged out of 1 other device(s)" }`
- Step 2: **401 Unauthorized** — Session B's access token is now blocklisted.
- Step 3: still **200** — the caller's own session is untouched.

Also confirm Session B's refresh token now fails at `POST /api/v1/auth/refresh` with
`ERROR_REFRESH_TOKEN_EXPIRED` (same jti-sharing mechanism as US-104's single-session logout).

---

## TC-015 — Revoke-Others With No Other Sessions

**Prerequisite:** an account with exactly one active session (fresh registration, no second login).

`POST /api/v1/users/me/sessions/revoke-others`

**Expected response (400 Bad Request):**
```json
{ "success": false, "error": { "code": "ERROR_NO_OTHER_SESSIONS", "message": "No other active sessions found" } }
```

---

## TC-016 — Logout Removes a Session From This List

**Goal:** confirm US-104's `POST /auth/logout` and this story's session table stay consistent with
each other.

**Steps:**
1. Set up two sessions as in TC-013.
2. `POST /api/v1/auth/logout` using Session B's token.
3. `GET /api/v1/users/me/sessions` using Session A's token.

**Expected:** the response list contains only Session A — Session B no longer appears, even though
it was never explicitly "revoked" through this story's endpoint.

---

## TC-017 — Reject Mobile Change to Your Own Current Number

`POST /api/v1/users/me/mobile/change/initiate` with the account's **current** mobile
```json
{ "newMobile": "9000000060" }
```

**Expected response (400 Bad Request):**
```json
{ "success": false, "error": { "code": "ERROR_SAME_MOBILE", "message": "This is already your registered mobile number" } }
```
No OTP is sent (nothing new in the backend log) and the attempt does not count towards the OTP send limit (TC-011).

---

## TC-018 — Reject Email Change to Your Own Current Email

`POST /api/v1/users/me/email/change/initiate` with the account's **current** email, then again with the same address in a different letter case
```json
{ "newEmail": "User@Example.com" }
```

**Expected response (400 Bad Request):**
```json
{ "success": false, "error": { "code": "ERROR_SAME_EMAIL", "message": "This is already your registered email address" } }
```
No OTP is sent. The comparison ignores letter case.

---

## Mobile App (Flutter) — Account Security

Manual test cases for Profile > Account > Account Security in `valuex-mobile` against the local backend. Automated coverage is in `test/features/account_security/account_security_test.dart`.

| Setting | Value |
|---|---|
| Run | `flutter run -d <device> --dart-define-from-file=config/dev_local.json` (add `--dart-define=CLEAR_LOCAL_SESSION=true` to start signed out) |
| Sign in | Sign In with a registered `ACTIVE` account (mock OTP is in the backend log, search for `DEV-MOCK`) |
| Open | Home, then **Profile**, then **Account Security** |
| Endpoints used | `GET /users/me/account-security`, `GET /users/me/sessions`, `POST /users/me/{mobile,email}/change/{initiate,verify}`, `POST /users/me/sessions/revoke-others` |

| TC | Scenario | Expected Result |
|---|---|---|
| M-TC-001 | Open the screen | "Account Security" with the masked mobile (e.g. `90XXXX0000`) and masked email, each with a Change button; Aadhaar status shown as an icon and words |
| M-TC-002 | Aadhaar not verified | "Not verified yet" with "Verify now"; the button opens the Aadhaar step. A verified account shows "Verified" and no button |
| M-TC-003 | Active sessions list | Up to 10 devices, newest first, each with "Last active {date}" and the IP; exactly one has the "This device" tag |
| M-TC-004 | Device name | A session created by the app shows `JustQlic/0.1.0 (iOS)` (or Android); a Swagger session shows its raw header, or "Unknown device" |
| M-TC-005 | Change mobile, happy path | Change, enter a new unregistered number, Send code. The page moves to "Confirm new number". Enter the code from the backend log. "Mobile number updated" shows, you return to Account Security and the masked number is the new one |
| M-TC-006 | Change mobile to your current number | Enter your own registered number, Send code. "This is already your mobile number. Enter a different number." shows under the field, you stay on the entry step and no `DEV-MOCK` OTP line appears in the backend log |
| M-TC-007 | Change mobile to another account's number | "This mobile number is already registered" shows under the field; no OTP is sent |
| M-TC-008 | Wrong code | Enter a wrong 6-digit code: "Invalid or expired OTP" shows and the new number is not applied |
| M-TC-009 | Resend | The resend link is disabled for 30 s, then works, up to 3 sends; the backend also stops at 3 sends per 10 minutes |
| M-TC-010 | Leave midway | Send a code, then go back without confirming: the old number is still shown and still works for Sign In (TC-008) |
| M-TC-011 | Change email, happy path | As M-TC-005 using Change next to Email and the email OTP from the backend log; "Email updated" |
| M-TC-012 | Change email to your current email | Enter your own email in any letter case, Send code. "This is already your email address. Enter a different address." shows and no OTP is sent |
| M-TC-013 | Log out of other devices | With two or more sessions, tap "Log out of all other devices", confirm. "Logged out of {n} other devices" shows and the list shrinks to "This device" |
| M-TC-014 | Only one device | With a single session the log-out action is hidden and "This is the only device signed in" shows |
| M-TC-015 | Revoked device | On the other device, the next request returns 401 and the user is sent to Sign In with the session-expired message |
| M-TC-016 | Delete My Account | Shows the "coming soon" message; no navigation, no crash |
| M-TC-017 | Backend down | Stop the backend and open the screen: an error with Retry for the summary and sessions; start the backend and tap Retry |
| M-TC-018 | Language and large text | Switch to Hindi and set the largest text size: no clipped or overlapping text; both change pages scroll |
| M-TC-019 | Screen reader | TalkBack or VoiceOver: Change buttons say which field they change, the "This device" tag is read, and page titles are headings |

> **M-TC-006 and M-TC-012 need the backend fix** (valuex-backend PR for `ERROR_SAME_MOBILE` / `ERROR_SAME_EMAIL`). Against an older backend the app accepts the number and sends an OTP.

---

## Not Testable Yet (Don't File as Bugs)

- **Actual account deletion** — `deleteAccountUrl` is a static string; there is no
  `/deletion-request` endpoint behind it yet. That's US-063/US-098, Sprint 14.
- **"Delete account only enabled if no active orders/disputes"** — N/A until orders/disputes exist
  as domains (Sprint 5+ / Sprint 8).
- **Friendly device names** (e.g. "iPhone 14 / iOS 18") — `deviceInfo` stores the raw `User-Agent`
  header verbatim; no parsing/formatting layer exists.
- **Notification on mobile/email change** ("your mobile number was changed" alert to the old
  number) — depends on US-077 notification infrastructure, which doesn't exist beyond a lifecycle
  skeleton yet.
- **True single-use refresh-token rotation** — unrelated to this story; see
  `US-107-Testing-Guide.md` TC-008. A revoked session's refresh token is blocklisted via `jti`, not
  rotated.

---

## Reset Between Tests

Register a fresh mobile number per TC (recommended), or reset a test user's mobile/email directly:
```sql
UPDATE users SET mobile = '9000000060', email = NULL WHERE id = '<user-id>';
```
To clear session rows for a user:
```sql
DELETE FROM user_sessions WHERE user_id = '<user-id>';
DELETE FROM contact_change_attempts WHERE user_id = '<user-id>';
```

---

## Error Reference

| HTTP | Error Code | Cause |
|---|---|---|
| 400 | `ERROR_MOBILE_ALREADY_REGISTERED` | `newMobile` already belongs to another user (TC-005) |
| 400 | `ERROR_EMAIL_ALREADY_REGISTERED` | `newEmail` already belongs to another user (TC-010) |
| 400 | `ERROR_SAME_MOBILE` | `newMobile` equals the account's current mobile (TC-017) |
| 400 | `ERROR_SAME_EMAIL` | `newEmail` equals the account's current email, ignoring case (TC-018) |
| 400 | `ERROR_INVALID_OTP` | Wrong OTP submitted at verify (TC-006) |
| 400 | `ERROR_OTP_EXPIRED` | OTP TTL (300s) elapsed (TC-007) |
| 400 | `ERROR_OTP_RATE_LIMIT` | >3 change-initiate calls in 10 min for the same target value (TC-011) |
| 400 | `ERROR_OTP_MAX_ATTEMPTS` | >5 failed verify attempts in 10 min (TC-012) |
| 400 | `ERROR_NO_OTHER_SESSIONS` | `revoke-others` called with only one active session (TC-015) |
| 401 | `UNAUTHORIZED` | Missing/expired/blocklisted JWT on any endpoint in this guide (TC-002, TC-014) |
| 404 | `NOT_FOUND` | JWT references a deleted user (not reachable via normal use) |
