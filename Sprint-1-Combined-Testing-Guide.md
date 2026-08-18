# Sprint 1 — Identity & User Management: Combined QA Testing Guide

**Covers every Sprint 1 user story:** US-001 (Registration), US-101 (Google Sign-In), US-002 (One
Account Per User), US-003 (Profile Management), US-103 (Profile Hub / Menu Summary), US-104
(Account Logout), US-105 (Account Security Settings), US-106 (Mobile OTP Login), US-107 (Access
Token Refresh), US-077 (Critical Event Notifications), US-088 (Lifecycle State - User Account).

> **US-102 (Apple Sign-In) has been officially discarded from scope.** It is documented here only
> as a one-line note (see the section between US-101 and US-002) so testers don't go looking for
> it. Do not file "Apple Sign-In doesn't work" as a bug.

This guide is written for a tester with **no prior background on this project** — it assumes you
can install software and use a web browser, nothing more about ValueX itself. Each story keeps its
own section and TC (Test Case) numbering (`US-XXX / TC-00N`) so it can still be cross-referenced
the way the original per-story guides were.

> **Source guides:** this document combines `US-001-Testing-Guide.md`, `US-002-Testing-Guide.md`,
> `US-003-Testing-Guide.md`, `US-077-Testing-Guide.md`, `US-088-Testing-Guide.md`,
> `US-103-Testing-Guide.md`, `US-104-Testing-Guide.md`, `US-105-Testing-Guide.md`,
> `US-107-Testing-Guide.md`, and adds new sections for **US-101** and **US-106**, which previously
> had no standalone QA guide (US-106 only had an implementation plan). Every test case in every
> section — including the new ones — was written against the **actual shipped code**
> (`*Service.java`, `*Controller.java`, real error codes/messages), not assumed from a design
> document. Where the design doc (LLD) and the real code disagreed, the real code wins, and the
> discrepancy is called out inline.

---

# Part 1 — Getting Started (For First-Time Testers)

If you have never run this backend before, work through this part once, top to bottom, before
opening any story section below. If your environment is already running, skip to
[Part 2](#part-2--how-this-guide-is-organized).

## 1.1 What You're Testing

`valuex-backend` is a REST API — there is no web page to click through. You send HTTP requests
(via a tool called **Swagger UI**, a form-based interface that's part of the running application)
and read JSON responses back. Every test case in this guide tells you exactly which button to
click, what to type, and what response to expect.

## 1.2 Software You Need Installed First

| Tool | Why | How to check you have it |
|---|---|---|
| **Docker Desktop** | Runs the database (PostgreSQL) and cache (Redis) in isolated containers — you don't install either one directly | Open a terminal, run `docker --version` |
| **Java 21 (JDK)** | Runs the backend application itself | `java -version` — must say `21` |
| **Maven 3.9+** | Builds and starts the application | `mvn -version` |
| **A web browser** | To use Swagger UI | Any modern browser (Chrome, Edge, Firefox) |
| **A SQL client** (optional but recommended) | To run the "reset between tests" SQL commands in this guide | pgAdmin (GUI) or just `psql` from the command line — both work; instructions for both below |

If any of these are missing, ask your team lead for the install links used on this project before
continuing — this guide doesn't cover installing the tools themselves.

## 1.3 Step 1 — Start the Database and Cache

Open a terminal, navigate to the backend project folder (`valuex-backend`), and run:

```bash
docker compose up -d postgres redis
```

Wait about 10–15 seconds for both to finish starting. Check they're healthy:

```bash
docker compose ps
```

You should see two rows, `valuex-postgres` and `valuex-redis`, both with status `Up` (or
`healthy`). If either shows `Exit` or restarts in a loop, stop here and ask for help — nothing
else in this guide will work until both are running.

> **You only need to do this once per work session.** Leave these containers running in the
> background — you don't need to restart them between test cases, only if your machine reboots.

## 1.4 Step 2 — Start the Backend Application

From the same `valuex-backend` folder:

```bash
mvn spring-boot:run
```

This takes 30–60 seconds the first time (longer while Maven downloads dependencies). Watch the
terminal output — you're waiting for a line that looks like:

```
Started ValuexApplication in X.XXX seconds
```

**Leave this terminal window open** for your entire testing session — this is the running
application, and closing the window stops it. You will also be watching this same window
throughout testing: **every OTP code in this system is printed to this console log**, not sent
by real SMS/email (see §1.7).

## 1.5 Step 3 — Confirm It's Running

Open a **second** terminal (leave the app running in the first one) and run:

```bash
curl http://localhost:8080/actuator/health
```

**Expected:** `{"status":"UP"}`. If you get a connection error, the app isn't fully started yet —
wait a few more seconds and try again. If it never comes up, check the first terminal's output for
an error (commonly: Docker containers from Step 1 weren't actually running).

## 1.6 Step 4 — Open Swagger UI

In your browser, go to:

```
http://localhost:8080/swagger-ui.html
```

You'll see a page with a list of **tags** (grey bars) — each is a group of related endpoints:
**Authentication**, **User Profile**, **Avatars**, **Account Security**, **Notifications**, etc.
Click a tag to expand it and see its endpoints. Every test case in this guide names both the exact
**endpoint** (e.g. `POST /api/v1/auth/register/initiate`) and which **tag** it lives under, so you
can find it quickly.

**To try an endpoint:**
1. Click the endpoint to expand it.
2. Click **Try it out** (top right of the expanded box).
3. Edit the JSON request body shown in this guide into the text box.
4. Click **Execute**.
5. Scroll down to see the **Response body** and **Response code** — compare against what this
   guide says to expect.

## 1.7 Understanding Responses

Every response in this system follows one of two shapes:

**Success:**
```json
{
  "success": true,
  "data": { ... the actual result ... }
}
```

**Error:**
```json
{
  "success": false,
  "error": {
    "code": "SOME_ERROR_CODE",
    "message": "A human-readable explanation"
  }
}
```

This guide always shows you the `error.code` to expect for negative test cases — that code, not
the message text, is what you should match against ("does the response say
`ERROR_INVALID_OTP`?"), since messages can be reworded without it counting as a behavior change.

## 1.8 Where OTPs Come From ("Mock" Mode)

This environment does **not** send real SMS or email. Every OTP (registration, login, mobile
change, email change, Aadhaar) is instead printed as a log line in the terminal where you ran
`mvn spring-boot:run` (Step 2). It looks like this:

```
[DEV-MOCK] OTP for mobile=9876543210 purpose=MOBILE_VERIFY otp=482913
```

Every time this guide says "check the console log for the OTP," this is what you're looking for —
scroll up in that terminal window, find the most recent `[DEV-MOCK]` line matching your mobile
number, and use the 6-digit `otp=` value.

## 1.9 Authorizing With a Token (Bearer Auth)

Most endpoints require you to be "logged in." After a successful registration or login call, the
response includes an `accessToken` (a long string starting with `eyJ`). To use it for later calls:

1. In Swagger UI, click the green **Authorize 🔒** button (top-right of the page).
2. Paste **only the token itself** into the box — do **not** type `Bearer ` in front of it,
   Swagger adds that automatically.
3. Click **Authorize**, then **Close**.

Every subsequent request from this browser tab now automatically includes that token. When this
guide says a step needs a **different** user's token (e.g. testing two accounts), repeat this
process with the new token — it replaces the old one.

To simulate "logging out" in Swagger UI itself (not calling the real logout endpoint — that's
US-104), click **Authorize 🔒** again → **Logout** → **Close**.

## 1.10 Accessing the Database (for "Reset Between Tests" Steps)

Some test cases ask you to run a SQL command directly against the database — usually to force an
account into a specific state (e.g. `SUSPENDED`) that has no API to trigger it yet, or to clean up
test data. Two ways to do this:

**Option A — Command line (`psql`), no extra install needed** (Docker already has it):
```bash
docker compose exec postgres psql -U valuex_user -d valuex_dev
```
This drops you into a `valuex_dev=#` prompt. Paste any SQL command from this guide, press Enter,
then type `\q` to exit when done.

**Option B — pgAdmin (GUI)**, if you have it installed:
- Host: `localhost`, Port: `5432`, Database: `valuex_dev`, Username: `valuex_user`,
  Password: `changeme` (unless your team changed these in a local `.env` file).

## 1.11 Common Startup Problems

| Symptom | Likely Cause | Fix |
|---|---|---|
| `mvn spring-boot:run` fails immediately with a database connection error | Docker containers from Step 1 aren't running | Run `docker compose ps`, restart with `docker compose up -d postgres redis` |
| `curl http://localhost:8080/actuator/health` times out or refuses connection | App hasn't finished starting, or failed to start | Check the first terminal for a stack trace; wait longer for first-time startup |
| Port `8080` already in use | Another process (maybe a previous run) is still using it | Find and stop it, or ask your team how this project changes the port |
| Port `5432` or `6379` already in use | You have a different local Postgres/Redis already running | Stop the other service, or ask your team about remapping ports in `docker-compose.yml` |
| An OTP you copied doesn't work | You copied an OTP from an *older* log line, or the mobile number in the log doesn't match what you're testing | Scroll to the **most recent** `[DEV-MOCK]` line for **that exact mobile number** |

---

# Part 2 — How This Guide Is Organized

- Each story below has: a short **what this ships** summary, an **Environment/Setting** table if
  it needs anything beyond the defaults, a **Scenarios Overview** table (all TCs at a glance), then
  one subsection per TC with the exact request and expected response, a **Not Testable Yet**
  section (things that look like gaps but are deliberate — don't file these as bugs), a **Reset
  Between Tests** section, and an **Error Reference** table.
- **Test mobile numbers are pre-assigned per story** (see each section's table) so you can run
  every story's test cases in the same session without accounts colliding with each other. Using a
  **fresh, never-before-used mobile number per test case** is always the safest option if you're
  ever unsure whether leftover data from a previous run will interfere.
- A `200`/`201` at the start of an "Expected" line means HTTP success; `400`/`401`/`404` etc. are
  HTTP error status codes — both are shown so you can check the right number in Swagger's response
  panel.

---

## Environment Setting Reference

| Setting | Value |
|---|---|
| Base URL | `http://localhost:8080` |
| Swagger UI | `http://localhost:8080/swagger-ui.html` |
| SMS / Email OTP Provider | `mock` (OTP printed to app console — see §1.8) |
| Aadhaar Provider | `sandbox` (accepts any 12-digit number; OTP `123456` always passes) |
| Google Sign-In Provider | `mock` (accepts tokens of the form `mock-<anything>`; the literal string `invalid` is rejected) |
| OTP length / TTL | 6 digits / 300 seconds (`valuex.otp.expiry-seconds`) |
| OTP send limit | 3 per 10 min per mobile/email (`otp_rate:{target}`) |
| OTP verify-fail limit | 5 per 10 min per mobile/email (`otp_fail:{target}`) |
| Access token TTL | 3,600,000 ms (1 hour) |
| Refresh token TTL | 604,800,000 ms (7 days) |
| Social session TTL (Google Sign-In) | 600 seconds (10 minutes) |
| Notification retention | 90 days (background job, not manually testable in real time) |
| DB Access | see §1.10 |
| Default avatar | `avatar-01` (catalog: `avatar-01` … `avatar-12`) |

## Story Coverage Index

| Story | Title | Status | Section |
|---|---|---|---|
| US-001 | User Registration via Mobile OTP | ✅ Implemented | [Jump](#us-001--user-registration-via-mobile-otp) |
| US-101 | Google Sign-In | ✅ Implemented | [Jump](#us-101--google-sign-in-optional-convenience-login) |
| US-102 | Apple Sign-In | ❌ **Discarded — not built, not planned this sprint** | [Jump](#us-102--apple-sign-in-discarded) |
| US-002 | One Account Per User Enforcement | ✅ Implemented | [Jump](#us-002--one-account-per-user-enforcement) |
| US-003 | User Profile Management | ✅ Implemented | [Jump](#us-003--user-profile-management) |
| US-103 | Profile Hub / Account Menu Navigation | ✅ Implemented | [Jump](#us-103--profile-hub--account-menu-navigation) |
| US-104 | Account Logout | ✅ Implemented | [Jump](#us-104--account-logout) |
| US-105 | Account Security Settings | ✅ Implemented | [Jump](#us-105--account-security-settings) |
| US-106 | Mobile OTP Login for Returning Users | ✅ Implemented | [Jump](#us-106--mobile-otp-login-for-returning-users) |
| US-107 | Access Token Refresh | ✅ Implemented | [Jump](#us-107--access-token-refresh) |
| US-077 | Critical Event Notifications | 🟡 Implemented, **account-events only** (see section) | [Jump](#us-077--critical-event-notifications) |
| US-088 | Lifecycle State - User Account | 🟡 Implemented, **no admin endpoint yet** (see section) | [Jump](#us-088--lifecycle-state---user-account) |

## Suggested End-to-End Sequence

Running the stories in this order lets one test user carry state through the whole sprint,
exercising every endpoint once before diving into the negative/edge-case TCs in each section:

```
US-001 (register: mobile → email → Aadhaar)
   → US-101 (a second, separate user signs in with Google instead)
      → US-003 (view/edit profile, pick avatar)
         → US-103 (menu summary reflects those edits)
            → US-077 (a notification appears for "account created")
               → US-107 (refresh the access token, confirm it reflects current state)
                  → US-105 (view account security, change mobile/email, list sessions)
                     → US-104 (log out — confirm the token stops working)
                        → US-106 (log back in via mobile OTP)
                           → US-088 (via unit tests only — no HTTP endpoint yet — confirm the
                                     account-suspend → auto-lift pipeline)
                              → US-002 (negative cases: duplicate Aadhaar/mobile, banned-account
                                        handling — best run last since it deliberately puts test
                                        accounts into BANNED/SUSPENDED states)
```

---

## US-001 — User Registration via Mobile OTP

End-to-end registration: mobile OTP → email OTP → Aadhaar (optional).

**Test mobile numbers used in this section:** `9876543210` (primary flow user).

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

All six endpoints are under Swagger's **Authentication** tag.

> **Aadhaar is optional at registration.** A user who skips it (Step 5a) reaches `ACTIVE` but
> cannot complete marketplace transactions until Aadhaar is verified later.

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

Copy `accessToken` and **Authorize** in Swagger UI (see §1.9). Account is now
`EMAIL_VERIFICATION_PENDING`.

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

**200 OK:** new token pair, `aadhaarVerified: false`, account now `ACTIVE`. Re-authorize with the
new token.

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
**200 OK:** new token pair, `aadhaarVerified: true`, account now `ACTIVE`. Re-authorize with the
new token — required for marketplace transaction endpoints.

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

## US-101 — Google Sign-In (Optional Convenience Login)

Lets a user sign in with their Google account instead of mobile OTP. There are **three** distinct
flows depending on whether the Google account has been seen before and whether the mobile number
it links to already has a ValueX account. All three endpoints below are **public** (no JWT needed
going in — you get one back as the result).

**What this ships:** Google ID token validation (mock provider in this environment — see below),
new-account creation for first-time Google users (still requires mobile OTP verification, since
mobile is this platform's core identity), and linking Google to an existing mobile-OTP account.

> **Mock provider details (verified against `MockGoogleTokenAdapter.java`, not the older LLD
> draft — they disagree slightly, and the code is what actually runs):** any token of the form
> `mock-<anything>` is accepted and mapped to a fake Google user
> (`sub: google-sub-<anything>`, `email: <anything>@gmail.com`). The **literal string `"invalid"`**
> (not `"mock-invalid"`) is the one value that triggers a rejection. Any other token that doesn't
> start with `mock-` is still accepted, mapped to a generic `sub: google-sub-user`.

**Test mobile numbers used in this section:** `9111000001` (Flow A — brand new Google user),
`9111000002` (Flow C — linking Google to an existing account).

### The Three Flows

**Flow A — Brand-new Google user (not yet in ValueX at all):**
```
POST /api/v1/auth/social/google            { idToken }
  → returns { requiresMobileVerification: true, socialSessionToken, googleEmail }
POST /api/v1/auth/social/google/initiate-mobile
  { socialSessionToken, mobile, termsAccepted, consentGiven }
  → sends OTP to that new mobile number
POST /api/v1/auth/social/google/verify-mobile
  { socialSessionToken, mobile, otp }
  → creates a new user, links the Google account, returns a JWT
```

**Flow B — Returning user (already linked Google before):**
```
POST /api/v1/auth/social/google            { idToken }
  → Google sub recognized → returns { requiresMobileVerification: false, accessToken, refreshToken, aadhaarVerified, userId }
```
(Nothing else to call — one request, done.)

**Flow C — Link Google to an existing mobile-OTP account** (same three calls as Flow A, but at
step 2 you submit the mobile number of an **already-registered, ACTIVE** account instead of a new
one — no new user is created, Google is just attached to the existing one):
```
POST /api/v1/auth/social/google            { idToken }   (same as Flow A step 1 — Google sub not yet known)
POST /api/v1/auth/social/google/initiate-mobile
  { socialSessionToken, mobile: "<the existing account's mobile>", termsAccepted, consentGiven }
POST /api/v1/auth/social/google/verify-mobile
  { socialSessionToken, mobile, otp }
  → links Google to that existing account, no state change, returns a JWT
```

> **Constraint:** the existing account in Flow C must be `ACTIVE`. Accounts still mid-registration
> (`EMAIL_VERIFICATION_PENDING`/`IDENTITY_VERIFICATION_PENDING`) get `ERROR_INVALID_STATE` instead.

### Scenarios Overview

| TC | Scenario | Expected |
|---|---|---|
| TC-001 | Flow A step 1 — brand-new Google user | `200`, `requiresMobileVerification: true`, session token + email returned |
| TC-002 | Flow A step 2 — send mobile OTP for the new user | `200`, OTP sent (console log) |
| TC-003 | Flow A step 3 — verify OTP, account created | `200`, new JWT, `status: IDENTITY_VERIFICATION_PENDING` |
| TC-004 | Flow B — returning Google user signs in again | `200`, JWT issued immediately, no OTP step |
| TC-005 | Flow C — link Google to an existing ACTIVE account | `200`, JWT for the existing account, no new user created |
| TC-006 | Reject linking when the existing account isn't ACTIVE yet | `400 ERROR_INVALID_STATE` |
| TC-007 | Reject linking when Google is already linked to that account | `400 ERROR_SOCIAL_ACCOUNT_ALREADY_LINKED` |
| TC-008 | Invalid Google token | `400 ERROR_INVALID_GOOGLE_TOKEN` |
| TC-009 | Expired/unknown social session | `400 ERROR_SOCIAL_SESSION_EXPIRED` |
| TC-010 | Mobile number mismatch at verify step | `400 ERROR_MOBILE_MISMATCH` |
| TC-011 | Terms not accepted / consent not given | `400 ERROR_TERMS_NOT_ACCEPTED` / `ERROR_CONSENT_REQUIRED` |
| TC-012 | Wrong or expired OTP at verify step | `400 ERROR_INVALID_OTP` / `ERROR_OTP_EXPIRED` |
| TC-013 | Google Sign-In with a BANNED existing mobile | see cross-reference below |

### TC-001 — Flow A Step 1: Brand-New Google User

`POST /api/v1/auth/social/google` *(Authentication tag, public)*
```json
{ "idToken": "mock-newgoogleuser" }
```
**200 OK:**
```json
{
  "success": true,
  "data": {
    "requiresMobileVerification": true,
    "socialSessionToken": "...",
    "googleEmail": "newgoogleuser@gmail.com"
  }
}
```
Copy `socialSessionToken` — you need it for the next two steps.

### TC-002 — Flow A Step 2: Send Mobile OTP

`POST /api/v1/auth/social/google/initiate-mobile`
```json
{
  "socialSessionToken": "<from TC-001>",
  "mobile": "9111000001",
  "termsAccepted": true,
  "consentGiven": true
}
```
Check console log for `[DEV-MOCK] OTP for mobile=9111000001 purpose=MOBILE_VERIFY otp=XXXXXX`.

**200 OK:** `{ "success": true, "data": { "message": "OTP sent to your mobile number", "otpExpiresInSeconds": 300 } }`

### TC-003 — Flow A Step 3: Verify OTP, Account Created

`POST /api/v1/auth/social/google/verify-mobile`
```json
{ "socialSessionToken": "<same token>", "mobile": "9111000001", "otp": "XXXXXX" }
```
**200 OK:**
```json
{
  "success": true,
  "data": {
    "accessToken": "...", "refreshToken": "...",
    "aadhaarVerified": false, "userId": "...",
    "status": "IDENTITY_VERIFICATION_PENDING"
  }
}
```
> The account skips straight to `IDENTITY_VERIFICATION_PENDING` — Google already proved the email,
> so there's no separate email-OTP step like there is for mobile-only registration (US-001).
> Aadhaar is still separately optional, same as any other account.

### TC-004 — Flow B: Returning Google User

**Prerequisite:** TC-003 completed (a Google account is now linked).

`POST /api/v1/auth/social/google`
```json
{ "idToken": "mock-newgoogleuser" }
```
**200 OK:**
```json
{
  "success": true,
  "data": {
    "requiresMobileVerification": false,
    "accessToken": "...", "refreshToken": "...",
    "aadhaarVerified": false, "userId": "..."
  }
}
```
> One call, done — no OTP, no mobile step. Same `idToken` as TC-001 on purpose: it's the *same*
> Google account signing in a second time.

### TC-005 — Flow C: Link Google to an Existing ACTIVE Account

**Prerequisite:** an existing `ACTIVE` account with mobile `9111000002` — complete US-001 Steps
1–2 then Step 5a (skip Aadhaar) for that mobile first.

1. `POST /api/v1/auth/social/google` with a **different, not-yet-linked** token:
   ```json
   { "idToken": "mock-linkuser" }
   ```
   → `200`, `requiresMobileVerification: true`, new `socialSessionToken`.
2. `POST /api/v1/auth/social/google/initiate-mobile`
   ```json
   {
     "socialSessionToken": "<from step 1>",
     "mobile": "9111000002",
     "termsAccepted": true,
     "consentGiven": true
   }
   ```
   → `200`, OTP sent **to the existing account's mobile** (not a new user).
3. `POST /api/v1/auth/social/google/verify-mobile`
   ```json
   { "socialSessionToken": "<same token>", "mobile": "9111000002", "otp": "XXXXXX" }
   ```
   **200 OK:** JWT for the **existing** `userId` (same one from the account you set up in the
   prerequisite) — `status` stays whatever it already was (`ACTIVE`), no new user row created.

### TC-006 — Reject Linking When Existing Account Isn't ACTIVE

**Prerequisite:** an account stuck at `EMAIL_VERIFICATION_PENDING` (registered, mobile verified,
nothing else done) — use a mobile like `9111000003`.

Repeat TC-005 step 1, then step 2 with `"mobile": "9111000003"`.

**400 Bad Request:**
```json
{ "success": false, "error": { "code": "ERROR_INVALID_STATE", "message": "Please complete your existing registration before linking Google Sign-In" } }
```

### TC-007 — Reject Linking When Google Already Linked

**Prerequisite:** TC-005 completed (mobile `9111000002` already has Google linked).

Repeat TC-005 step 1 with a **new** token (`mock-linkuser2`), then step 2 targeting
`"mobile": "9111000002"` again.

**400 Bad Request:**
```json
{ "success": false, "error": { "code": "ERROR_SOCIAL_ACCOUNT_ALREADY_LINKED", "message": "This Google account is already linked to another ValueX account" } }
```

### TC-008 — Invalid Google Token

`POST /api/v1/auth/social/google`
```json
{ "idToken": "invalid" }
```
**400 Bad Request:**
```json
{ "success": false, "error": { "code": "ERROR_INVALID_GOOGLE_TOKEN", "message": "Google sign-in failed. Please try again" } }
```
> Use the exact string `invalid` — **not** `mock-invalid`, which the older design draft suggested
> but the real code does not check for (it would just be treated as a normal, if odd, new user).

### TC-009 — Expired/Unknown Social Session

`POST /api/v1/auth/social/google/initiate-mobile`
```json
{
  "socialSessionToken": "00000000-0000-0000-0000-000000000000",
  "mobile": "9111000005",
  "termsAccepted": true,
  "consentGiven": true
}
```
**400 Bad Request:** `ERROR_SOCIAL_SESSION_EXPIRED`, `"Google sign-in session expired. Please sign in with Google again"`.

Same result if you legitimately wait 10+ minutes between step 1 and step 2 of any flow.

### TC-010 — Mobile Number Mismatch at Verify Step

**Steps:** Run TC-001+TC-002 normally for mobile `9111000001`, but at the verify step submit a
**different** mobile number than what you used in step 2:
```json
{ "socialSessionToken": "<from step 1>", "mobile": "9111000099", "otp": "XXXXXX" }
```
**400 Bad Request:** `ERROR_MOBILE_MISMATCH`, `"Mobile number does not match the registered session"`.

### TC-011 — Terms Not Accepted / Consent Not Given

`POST /api/v1/auth/social/google/initiate-mobile`
```json
{ "socialSessionToken": "<valid>", "mobile": "9111000006", "termsAccepted": false, "consentGiven": true }
```
**400 Bad Request:** `ERROR_TERMS_NOT_ACCEPTED`. Repeat with `"consentGiven": false` (and
`termsAccepted: true`) → `ERROR_CONSENT_REQUIRED`.

### TC-012 — Wrong or Expired OTP at Verify Step

Wrong OTP: repeat TC-003's request with `"otp": "000000"` → **400** `ERROR_INVALID_OTP`.

Expired OTP: wait 300+ seconds after TC-002 before verifying (or temporarily reduce
`valuex.otp.expiry-seconds`) → **400** `ERROR_OTP_EXPIRED`.

### TC-013 — Google Sign-In With a BANNED Existing Mobile

This exact scenario is already documented in detail under **US-002 / TC-005** — see that section
rather than duplicating it here, since it's really a one-account-enforcement test that happens to
use this endpoint.

### Not Testable Yet (US-101)

- **Real Google account sign-in** — this environment only has the mock provider wired up
  (`valuex.oauth.google.provider=mock`). The real `HttpGoogleTokenAdapter` exists in code but
  needs real Google OAuth client IDs configured, which aren't set up in this local environment.
- **OTP rate-limit / max-attempt behavior specific to social sign-in** — it shares the exact same
  Redis buckets (`otp_rate:{mobile}`, `otp_fail:{mobile}`) as US-001/US-106. If you want to verify
  it, follow the same steps as US-001's rate-limit test cases against a social-flow mobile number.

### US-101 Reset Between Tests

```sql
DELETE FROM user_social_accounts WHERE user_id IN (
  SELECT id FROM users WHERE mobile IN ('9111000001','9111000002','9111000003','9111000005','9111000006')
);
DELETE FROM account_status_history WHERE user_id IN (
  SELECT id FROM users WHERE mobile IN ('9111000001','9111000002','9111000003','9111000005','9111000006')
);
DELETE FROM users WHERE mobile IN ('9111000001','9111000002','9111000003','9111000005','9111000006');
```

### US-101 Error Reference

| HTTP | Error Code | Cause |
|---|---|---|
| 400 | `ERROR_INVALID_GOOGLE_TOKEN` | Token is the literal string `invalid`, or fails real provider validation (TC-008) |
| 400 | `ERROR_SOCIAL_SESSION_EXPIRED` | `socialSessionToken` unknown or its 10-minute TTL elapsed (TC-009) |
| 400 | `ERROR_SOCIAL_SESSION_INVALID` | Session data malformed (not reachable through normal use) |
| 400 | `ERROR_MOBILE_MISMATCH` | Verify-step mobile doesn't match the initiate-step mobile (TC-010) |
| 400 | `ERROR_TERMS_NOT_ACCEPTED` / `ERROR_CONSENT_REQUIRED` | Missing consent flags at initiate-mobile (TC-011) |
| 400 | `ERROR_INVALID_STATE` | Linking target account isn't `ACTIVE` yet (TC-006) |
| 400 | `ERROR_SOCIAL_ACCOUNT_ALREADY_LINKED` | Target account already has a Google account linked (TC-007) |
| 400 | `ERROR_ACCOUNT_RECOVERY_REQUIRED` | Linking target account is `BANNED`/`CLOSED` (see US-002 TC-005) |
| 400 | `ERROR_OTP_RATE_LIMIT` / `ERROR_OTP_MAX_ATTEMPTS` | Same shared OTP buckets as US-001 |
| 400 | `ERROR_INVALID_OTP` / `ERROR_OTP_EXPIRED` | Wrong/expired OTP at verify (TC-012) |

---

## US-102 — Apple Sign-In (DISCARDED)

**This story is officially out of scope.** No code exists for it — no endpoint, no adapter, no
database column beyond a `provider` field designed to be reusable if the story is ever revisited.
**Do not attempt to test it, and do not file "Apple Sign-In doesn't exist" as a bug.** If you're
curious why, the decision and its rationale are recorded in
`Documents/LLD/Sprint-1-Identity-User-Management-LLD.md` §5.

---

## US-002 — One Account Per User Enforcement

Validates Aadhaar uniqueness, differentiated errors by account state, and Google Sign-In rejection
for banned mobiles.

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

> Non-ACTIVE accounts that aren't BANNED/CLOSED (e.g. `EMAIL_VERIFICATION_PENDING`) return
> `ERROR_INVALID_STATE` instead — same rule already covered in **US-101 / TC-006**.

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

> **Design note:** users pick an `avatarId` from a fixed catalog (`GET /api/v1/avatars`) — there
> is no photo upload or content moderation in this version. See
> `Documents/LLD/Sprint-1-Identity-User-Management-LLD.md` §7.

**Prerequisites:** Only a valid JWT is required (not email/Aadhaar verification) — Steps 1–2 of
US-001 are sufficient.

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
> `displayName`/`email`/`city`/`aadhaarName` are omitted entirely (not `null`) before ever set —
> not a bug. `avatarId` defaults to `avatar-01` at account creation.

### TC-002 — Update Display Name and City

`PATCH /api/v1/users/me`
```json
{ "displayName": "Abhay Kumar", "city": "Bengaluru" }
```
**200 OK**, confirm via `GET /users/me`.

### TC-003 — Partial Update Leaves Other Field Unchanged

Prerequisite: TC-002 done. `PATCH /api/v1/users/me` with `{ "city": "Mumbai" }` — `displayName`
must still read `"Abhay Kumar"`.

### TC-004 — Reject Invalid Display Name

Try each: `{ "displayName": "Ab" }` (too short), `{ "displayName": "Abhay123" }` (digits),
`{ "displayName": "Abhay@Kumar" }` (`@`).

**400:** `code: VALIDATION_ERROR` for each.

### TC-005 — Reject Invalid City

`{ "city": "P1" }` → **400** `VALIDATION_ERROR`.

> **Known simplification:** format-only validation, no exhaustive city whitelist —
> `"Notacity"` currently passes. Expected per LLD, not a bug.

### TC-006 — List Avatar Catalog

`GET /api/v1/avatars` *(JWT)* → **200**, `avatarIds: ["avatar-01" ... "avatar-12"]`,
`defaultAvatarId: "avatar-01"`.

### TC-007 — Select a Valid Avatar

`PUT /api/v1/users/me/avatar` with `{ "avatarId": "avatar-07" }` → **200**, confirm via
`GET /users/me`.

### TC-008 — Reject Avatar Not in Catalog

`{ "avatarId": "avatar-99" }` → **400** `ERROR_INVALID_AVATAR`, existing selection untouched.

Also try `{ "avatarId": "" }` → **400** `VALIDATION_ERROR` (different code — don't conflate).

### TC-009 — Aadhaar-Verified Name Is Read-Only

Prerequisite: complete Aadhaar verification (US-001 Steps 3–6). `GET /users/me` shows
`aadhaarName`.

`PATCH /api/v1/users/me`
```json
{ "displayName": "Abhay Kumar", "aadhaarName": "Someone Else" }
```
**200 OK** — request succeeds (unknown fields silently ignored), but `aadhaarName` in the response
is unchanged. `UpdateProfileRequest` has no `aadhaarName` property — structurally impossible to
write via this endpoint.

### TC-010 — Unauthenticated Request Rejected

Logout in Swagger UI, call `GET /api/v1/users/me` → **401** `UNAUTHORIZED`. Repeat for
`PATCH /users/me`, `PUT /users/me/avatar`, `GET /avatars`.

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

Backend deliverable is one summary endpoint: `GET /api/v1/users/me/menu-summary`, plus an
unused-so-far badge-provider extensibility hook.

> **`badges` is always `{}` today** — zero providers registered in Sprint 1. That's correct, not a
> bug (LLD §8).

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
> `displayName` omitted if unset (`non_null` inclusion). `memberSince` = `created_at` from
> registration, not "now."

### TC-002 — Reflects Display-Name Update

`PATCH /users/me` with `{ "displayName": "Abhay Kumar" }`, then `GET /users/me/menu-summary` →
`displayName` matches.

### TC-003 — Reflects Avatar Change

`PUT /users/me/avatar` with `{ "avatarId": "avatar-07" }`, then `GET /users/me/menu-summary` →
`avatarId` matches.

### TC-004 — Reflects Aadhaar Verification

Complete US-001 Aadhaar flow, then `GET /users/me/menu-summary` → `aadhaarVerified: true`.

### TC-005 — `badges` Always Empty Today

Regardless of prior activity, `data.badges` is always `{}` (present, empty).

> Don't file "no badges for orders/offers/notifications" as a bug — those keys only appear once
> their owning story registers a `ProfileMenuBadgeProvider` bean (Notifications, Sprint 11
> earliest — see US-077's own section below for why Sprint 1's notification work still didn't add
> one).

### TC-006 — Unauthenticated Request Rejected

Logout, call `GET /users/me/menu-summary` → **401** `UNAUTHORIZED`.

### TC-007 — `memberSince` Matches `GET /users/me`

Compare `memberSince` from both endpoints — must be character-for-character identical.

### Not Testable Yet (US-103)

- The actual mobile "Profile" tab UI — mobile-side work, not covered by this backend guide.
- Any badge count (`MY_ORDERS`, `SAVED_ITEMS`, `OFFERS`, `TRANSACTIONS`, `PAYOUTS`,
  `NOTIFICATIONS`, `SUPPORT_TICKETS`, `DISPUTES`) — none exist yet.
- `ERROR_SECTION_UNAVAILABLE` — applies to individual menu destinations, not this summary endpoint.
- Resilience against a broken badge provider — hardened in code (one bad provider only omits its
  badge; duplicate keys fail app startup) but not exercisable until a real provider exists.

### US-103 Error Reference

| HTTP | Error Code | Cause |
|---|---|---|
| 401 | `UNAUTHORIZED` | Missing/expired JWT |
| 404 | `NOT_FOUND` | JWT references a deleted user (not reachable via normal use) |

---

## US-104 — Account Logout

**What this ships:** a single endpoint that blocklists the current session's `jti` in Redis. Every
login/registration flow mints one shared `jti` per access+refresh token pair, so this one
blocklist entry invalidates **both** tokens from that session — not just the access token used to
call `/logout`. There is **no** persisted "list my active devices" capability in this story — that
arrives in US-105, built on top of this story's `jti` foundation but not part of it.

| Setting | Value |
|---|---|
| Endpoint | `POST /api/v1/auth/logout` *(Authentication tag, Bearer token required, no body)* |

**Test mobile numbers used in this section:** `9000000050` through `9000000055`.

### Scenarios

| TC | Scenario | Expected Result |
|---|---|---|
| TC-001 | Logout with a valid access token | `200`, `"Logged out successfully"` |
| TC-002 | The logged-out access token is rejected on its next use | `401 UNAUTHORIZED` |
| TC-003 | The paired refresh token is also invalidated | `400 ERROR_REFRESH_TOKEN_EXPIRED` from `/auth/refresh` |
| TC-004 | Session stays revocable after a refresh (jti carries forward) | Logging out with a *refreshed* token still kills the *original* refresh token |
| TC-005 | Rapid retry with the same still-valid token succeeds twice | `200` both times — not an error |
| TC-006 | A later call with the same, now-blocklisted token | `401`, not a second `200` — documented boundary, not a bug |
| TC-007 | Unauthenticated logout call | `401 UNAUTHORIZED` |
| TC-008 | Refresh token submitted as the Bearer token to `/logout` | `401` — rejected before the logout logic is ever reached |
| TC-009 | Logging out one session doesn't affect another session for the same user | The other session's token keeps working |

### TC-001 — Logout With a Valid Access Token

**Prerequisite:** register mobile `9000000050` via US-001 Steps 1–2, Authorize with the
`accessToken`.

**Expected response (200 OK):**
```json
{ "success": true, "data": { "message": "Logged out successfully" } }
```

### TC-002 — Logged-Out Access Token Rejected on Next Use

**Steps:** Immediately after TC-001, call `GET /api/v1/users/me` with the **same** access token
still set in Swagger's Authorize dialog.

**Expected response (401 Unauthorized):**
```json
{ "success": false, "error": { "code": "UNAUTHORIZED", "message": "Authentication required" } }
```
> Same generic `401` shape as a missing/expired token — the filter doesn't distinguish
> "blocklisted" from "never valid" in its response, only in its server log
> (`Rejected blocklisted (logged-out) token`).

### TC-003 — Paired Refresh Token Also Invalidated

**Goal:** confirm logout kills the *whole session*, not just the access token used to call it.

**Steps:**
1. Register mobile `9000000051`, keep both `accessToken` and `refreshToken`.
2. `POST /api/v1/auth/logout` using that `accessToken`.
3. `POST /api/v1/auth/refresh` *(public)* with that same `refreshToken`:
   ```json
   { "refreshToken": "<the paired refresh token from step 1>" }
   ```

**Expected response (400 Bad Request):**
```json
{ "success": false, "error": { "code": "ERROR_REFRESH_TOKEN_EXPIRED", "message": "Session expired. Please log in again" } }
```

### TC-004 — Session Stays Revocable Across a Refresh

**Steps:**
1. Register mobile `9000000052`, keep the initial `refreshToken_A`.
2. `POST /api/v1/auth/refresh` with `refreshToken_A` → note the new `accessToken_B`/`refreshToken_B`.
3. `POST /api/v1/auth/logout` using `accessToken_B`.
4. `POST /api/v1/auth/refresh` again, this time with the **original** `refreshToken_A`.

**Expected:** step 4 returns `400 ERROR_REFRESH_TOKEN_EXPIRED` — the two tokens share one `jti`
for the whole session, not just the most recent pair.

### TC-005 — Rapid Retry With the Same Still-Valid Token

Register mobile `9000000053`. Call `POST /api/v1/auth/logout` **twice in immediate succession**
with the same access token.

**Expected:** both calls return `200 OK` with the same body.

### TC-006 — Later Call With the Same, Now-Blocklisted Token

Register mobile `9000000054`. `POST /api/v1/auth/logout`, then call it **again** with the same,
already-blocklisted access token.

**Expected:** second call returns `401 Unauthorized`, **not** `200`. To log out "again," the
client must first obtain a fresh token. **Do not file as a bug.**

### TC-007 — Unauthenticated Logout Call

In Swagger UI, click **Authorize 🔒** → **Logout** (or omit the `Authorization` header), then
`POST /api/v1/auth/logout`.

**Expected response (401 Unauthorized):**
```json
{ "success": false, "error": { "code": "UNAUTHORIZED", "message": "Authentication required" } }
```

### TC-008 — Refresh Token Submitted as Bearer to `/logout`

Authorize in Swagger UI with a **refresh token** (not an access token), then call
`POST /api/v1/auth/logout`.

**Expected response (401 Unauthorized).** The refresh token is rejected before the logout logic is
ever reached — nothing is blocklisted by this call.

### TC-009 — Logging Out One Session Doesn't Affect Another

**Steps:**
1. Register mobile `9000000055` → **Session A** (`accessToken_A`).
2. `POST /api/v1/auth/login/initiate` + `POST /api/v1/auth/login/verify-mobile` for the same
   mobile (US-106) → **Session B** (`accessToken_B`), a different `jti`.
3. `POST /api/v1/auth/logout` using `accessToken_A`.
4. `GET /api/v1/users/me` using `accessToken_B`.

**Expected:** step 4 still returns `200 OK` — only Session A is blocklisted.

### Not Testable Yet (US-104)

- **Listing active sessions / devices** — that's US-105, built on top of this story's `jti`.
- **"Log out of all other devices"** — same as above, US-105.
- **True single-use refresh-token rotation** — a refresh token not tied to a logged-out session
  still works repeatedly until its own 7-day expiry (see US-107 TC-008). This story only adds
  *revocation on logout*, not rotation on every refresh.
- **"Logout triggered automatically after password/PIN change"** — categorically not applicable;
  there is no password or PIN anywhere in ValueX's auth design (mobile-OTP / social sign-in only).
- **In-flight upload cancellation on logout** — client-side mobile behavior, not observable here.
- **Rate limiting on `/auth/logout`** — deliberately not implemented; repeated logout calls are
  self-limiting.

### US-104 Reset Between Tests

Register a fresh mobile number per TC (recommended, as used above). To manually "undo" a logout
during exploratory testing, clear the Redis blocklist entry directly (`jti` is only visible by
decoding the JWT, e.g. at jwt.io — there's no API to look it up):
```
DEL blocklist:<jti>
```

### US-104 Error Reference

| HTTP | Error Code | Cause |
|---|---|---|
| 200 | — | Logout succeeded (TC-001, TC-005) |
| 401 | `UNAUTHORIZED` | Missing/expired/already-blocklisted access token (TC-002, TC-006, TC-007), or a refresh token presented as Bearer (TC-008) |
| 400 | `ERROR_REFRESH_TOKEN_EXPIRED` | Paired refresh token invalidated by a logout on the shared `jti` (TC-003, TC-004) |

---

## US-105 — Account Security Settings

**What this ships:** an account-security summary endpoint, OTP-verified mobile and email change,
an active-sessions list, and "log out of all other devices." It introduces the `user_sessions`
table — logging out one session (US-104) now also removes it from this story's session list. The
"Delete My Account" entry point is a **static URL only** — the real deletion flow is a much later
sprint; tapping it today is expected to be a dead end, not a bug.

| Setting | Value |
|---|---|
| Base tag | **Account Security** |
| OTP length / TTL | 6 digits / 300s (shared `otp.*` config, same as every other OTP flow) |
| OTP send limit | 3 per 10 min per target value |
| OTP verify-fail limit | 5 per 10 min per target value |
| Session list size | Top 10 non-revoked sessions, most recent first |

**Test mobile numbers used in this section:** `9000000060` through `9000000062`.

### Scenarios

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
| TC-013 | List active sessions with `isCurrent` flagged | `200`, exactly one session marked current |
| TC-014 | Log out of all other devices | `200`, other session's tokens die; caller's session untouched |
| TC-015 | Revoke-others with no other sessions | `400 ERROR_NO_OTHER_SESSIONS` |
| TC-016 | Logout (US-104) removes a session from this list | Session absent from a later `GET /sessions` |

### TC-001 — View Account Security Summary

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

### TC-002 — Unauthenticated Summary Request

Logout in Swagger UI, then call `GET /api/v1/users/me/account-security`.

**Expected response (401 Unauthorized):**
```json
{ "success": false, "error": { "code": "UNAUTHORIZED", "message": "Authentication required" } }
```

### TC-003 — Initiate Mobile Change

**Endpoint:** `POST /api/v1/users/me/mobile/change/initiate`
```json
{ "newMobile": "9000000061" }
```
Check console log: `[DEV-MOCK] OTP for mobile=9000000061 purpose=MOBILE_CHANGE otp=XXXXXX`.

**Expected response (200 OK):**
```json
{ "success": true, "data": { "message": "OTP sent to your new mobile number", "otpExpiresInSeconds": 300 } }
```

### TC-004 — Verify Mobile Change

**Endpoint:** `POST /api/v1/users/me/mobile/change/verify`
```json
{ "newMobile": "9000000061", "otp": "XXXXXX" }
```
**Expected response (200 OK):** `{ "success": true, "data": { "message": "Mobile number updated" } }`

### TC-005 — Reject Mobile Change to an Already-Registered Number

**Prerequisite:** a second account already exists with mobile `9000000062`.

`POST /api/v1/users/me/mobile/change/initiate`
```json
{ "newMobile": "9000000062" }
```
**Expected response (400):** `ERROR_MOBILE_ALREADY_REGISTERED`.

### TC-006 — Reject Mobile Verify With Wrong OTP

After TC-003, call verify with `{ "newMobile": "9000000061", "otp": "000000" }`.

**Expected response (400):** `ERROR_INVALID_OTP`. Confirm the mobile is unchanged.

### TC-007 — Reject Mobile Verify With Expired OTP

Initiate a mobile change, wait 300+ seconds, then verify with the original code.

**Expected response (400):** `ERROR_OTP_EXPIRED`.

### TC-008 — Old Mobile Stays Active Until Verified

1. `POST /api/v1/users/me/mobile/change/initiate` with a new mobile — **do not verify yet**.
2. `POST /api/v1/auth/login/initiate` with the **original** mobile (US-106).

**Expected:** step 2 succeeds normally.

### TC-009 — Initiate + Verify Email Change

Mirrors TC-003/TC-004 against `/email/change/initiate|verify`:
```json
{ "newEmail": "newaddress@example.com" }
```
then
```json
{ "newEmail": "newaddress@example.com", "otp": "XXXXXX" }
```
**Expected:** `200` on both; the second returns `{ "message": "Email updated" }`.

### TC-010 — Reject Email Change to an Already-Registered Email

Same shape as TC-005, against `/email/change/initiate` → `400 ERROR_EMAIL_ALREADY_REGISTERED`.

### TC-011 — OTP Send Rate Limit

Call `/mobile/change/initiate` (or `/email/change/initiate`) **4 times within 10 minutes**. The
4th call returns **400** `ERROR_OTP_RATE_LIMIT`.

### TC-012 — OTP Verify Fail Limit

Call the corresponding `/verify` endpoint with a wrong OTP **6 times within 10 minutes**. The 6th
call returns **400** `ERROR_OTP_MAX_ATTEMPTS`.

### TC-013 — List Active Sessions With `isCurrent` Flagged

**Steps:**
1. Log in for this account a second time (US-106) — now two sessions exist.
2. `GET /api/v1/users/me/sessions` using either session's token.

**Expected response (200 OK):**
```json
{
  "success": true,
  "data": [
    { "sessionId": "...", "deviceInfo": "...", "ipAddress": "127.0.0.1", "createdAt": "...", "lastActiveAt": "...", "isCurrent": true },
    { "sessionId": "...", "deviceInfo": "...", "ipAddress": "127.0.0.1", "createdAt": "...", "lastActiveAt": "...", "isCurrent": false }
  ]
}
```
Exactly **one** entry has `isCurrent: true`.

### TC-014 — Log Out of All Other Devices

**Steps:**
1. From TC-013's two-session setup, call `POST /api/v1/users/me/sessions/revoke-others` using
   Session A's token.
2. `GET /api/v1/users/me` using Session B's token.
3. `GET /api/v1/users/me` using Session A's token.

**Expected:**
- Step 1: `200`, `{ "message": "Logged out of 1 other device(s)" }`
- Step 2: **401 Unauthorized**
- Step 3: still **200**

### TC-015 — Revoke-Others With No Other Sessions

**Prerequisite:** an account with exactly one active session.

`POST /api/v1/users/me/sessions/revoke-others`

**Expected response (400):**
```json
{ "success": false, "error": { "code": "ERROR_NO_OTHER_SESSIONS", "message": "No other active sessions found" } }
```

### TC-016 — Logout Removes a Session From This List

**Steps:**
1. Set up two sessions as in TC-013.
2. `POST /api/v1/auth/logout` using Session B's token.
3. `GET /api/v1/users/me/sessions` using Session A's token.

**Expected:** the response list contains only Session A.

### Not Testable Yet (US-105)

- **Actual account deletion** — `deleteAccountUrl` is a static string; no endpoint behind it yet.
- **"Delete account only enabled if no active orders/disputes"** — N/A until orders/disputes exist.
- **Friendly device names** (e.g. "iPhone 14 / iOS 18") — `deviceInfo` stores the raw `User-Agent`
  header verbatim.
- **Notification on mobile/email change** — see the US-077 section below: notifications are scoped
  to account-lifecycle events only in Sprint 1, not contact-detail changes.
- **True single-use refresh-token rotation** — unrelated to this story; see US-107 TC-008.

### US-105 Reset Between Tests

Register a fresh mobile per TC (recommended), or reset directly:
```sql
UPDATE users SET mobile = '9000000060', email = NULL WHERE id = '<user-id>';
DELETE FROM user_sessions WHERE user_id = '<user-id>';
DELETE FROM contact_change_attempts WHERE user_id = '<user-id>';
```

### US-105 Error Reference

| HTTP | Error Code | Cause |
|---|---|---|
| 400 | `ERROR_MOBILE_ALREADY_REGISTERED` | `newMobile` already belongs to another user (TC-005) |
| 400 | `ERROR_EMAIL_ALREADY_REGISTERED` | `newEmail` already belongs to another user (TC-010) |
| 400 | `ERROR_INVALID_OTP` | Wrong OTP submitted at verify (TC-006) |
| 400 | `ERROR_OTP_EXPIRED` | OTP TTL (300s) elapsed (TC-007) |
| 400 | `ERROR_OTP_RATE_LIMIT` | >3 change-initiate calls in 10 min (TC-011) |
| 400 | `ERROR_OTP_MAX_ATTEMPTS` | >5 failed verify attempts in 10 min (TC-012) |
| 400 | `ERROR_NO_OTHER_SESSIONS` | `revoke-others` called with only one active session (TC-015) |
| 401 | `UNAUTHORIZED` | Missing/expired/blocklisted JWT (TC-002, TC-014) |
| 404 | `NOT_FOUND` | JWT references a deleted user (not reachable via normal use) |

---

## US-106 — Mobile OTP Login for Returning Users

Closes the gap where a returning mobile-OTP user had no way to log back in —
`POST /register/initiate` explicitly rejects an already-registered mobile, and Google Sign-In is a
shortcut around a primary login path that didn't otherwise exist. Login never transitions account
state or writes `account_status_history`; it only reads the account's current
`status`/`aadhaarVerified` fresh into a newly issued JWT.

| Setting | Value |
|---|---|
| Initiate endpoint | `POST /api/v1/auth/login/initiate` *(public)* |
| Verify endpoint | `POST /api/v1/auth/login/verify-mobile` *(public)* |
| OTP Redis key | `otp:{mobile}:LOGIN` (separate namespace from registration's `MOBILE_VERIFY`) |
| Rate-limit buckets | `otp_rate:{mobile}`, `otp_fail:{mobile}` — **shared** with registration (safe: a mobile can't be simultaneously eligible for both) |

### State-Eligibility Table

`assertLoginEligible` runs at **both** initiate and verify — this double-check is what covers
"account state changed between OTP send and verify."

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

**Setup:** register a user via US-001 Steps 1–2 (mobile `9000000040`), then either complete or
stop the flow at different states to hit each TC below.

### TC-001 — Initiate Login (Happy Path)

**Prerequisite:** user exists and is `ACTIVE`.

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
> `aadhaarVerified` and `status` are read fresh from the DB, not carried over from any earlier
> token.

### TC-003 — Mobile Not Registered

`POST /api/v1/auth/login/initiate` with a mobile that has no account, e.g. `{ "mobile": "9999999999" }`.

**400:** `{ "success": false, "error": { "code": "ERROR_MOBILE_NOT_REGISTERED", "message": "No account found with this mobile number. Please register" } }`

### TC-004 — Login Blocked Before Mobile Verification

**Prerequisite:** a user stuck at `NEW` or `OTP_PENDING`.

`POST /api/v1/auth/login/initiate` with that mobile.

**400:** `{ "success": false, "error": { "code": "ERROR_INVALID_STATE", "message": "Please complete your mobile number verification before logging in" } }`

### TC-005 — Login Resumes Mid-Registration

**Prerequisite:** a user at `EMAIL_VERIFICATION_PENDING` or `IDENTITY_VERIFICATION_PENDING`.

Both the initiate and verify calls succeed with **200 OK**, issuing a JWT with `aadhaarVerified:
false` and `status` matching the incomplete state.

### TC-006 — `UNDER_REVIEW` / `RESTRICTED` Can Still Log In

```sql
UPDATE users SET status = 'UNDER_REVIEW' WHERE mobile = '9000000040';
```
Run the login flow — expect **200 OK** with `status: "UNDER_REVIEW"`. Repeat with
`status = 'RESTRICTED'`.

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

### TC-009 — Invalid OTP

`POST /api/v1/auth/login/verify-mobile` with a wrong 6-digit code.

**400:** `{ "success": false, "error": { "code": "ERROR_INVALID_OTP", "message": "Invalid or expired OTP" } }`

### TC-010 — Expired OTP

Wait 300+ seconds after initiating login, then verify with the original OTP.

**400:** `{ "success": false, "error": { "code": "ERROR_OTP_EXPIRED", "message": "OTP has expired. Please request a new one" } }`

### TC-011 — Rate Limits

**Send limit:** call `/login/initiate` 4 times within 10 minutes → the 4th returns **400**
`ERROR_OTP_RATE_LIMIT`.

**Verify-fail limit:** call `/login/verify-mobile` with a wrong OTP 6 times within 10 minutes →
the 6th returns **400** `ERROR_OTP_MAX_ATTEMPTS`.

### TC-012 — Account Suspended Between Initiate and Verify

1. `POST /api/v1/auth/login/initiate` for an `ACTIVE` user — succeeds.
2. Suspend the account: `UPDATE users SET status = 'SUSPENDED' WHERE mobile = '9000000040';`
3. `POST /api/v1/auth/login/verify-mobile` with the correct OTP.

**400:** `ERROR_ACCOUNT_SUSPENDED` — no JWT issued even though the OTP was correct.

### TC-013 — Missing `mobile` / `otp`

`POST /api/v1/auth/login/initiate` with `{}` → **400** validation error.

`POST /api/v1/auth/login/verify-mobile` with `{ "mobile": "9000000040" }` → **400** validation
error, `otp` flagged.

### US-106 Reset Between Tests

```sql
UPDATE users SET status = 'ACTIVE' WHERE mobile = '9000000040';
```

### US-106 Error Reference

| HTTP | Error Code | Cause |
|---|---|---|
| 400 | `ERROR_MOBILE_NOT_REGISTERED` | No account exists for the submitted mobile (TC-003) |
| 400 | `ERROR_INVALID_STATE` | Account is `NEW`/`OTP_PENDING` (TC-004) |
| 400 | `ERROR_ACCOUNT_SUSPENDED` | Account suspended (TC-007, TC-012) |
| 400 | `ERROR_ACCOUNT_RECOVERY_REQUIRED` | Account banned or closed (TC-008) |
| 400 | `ERROR_OTP_RATE_LIMIT` | >3 send attempts in 10 min (TC-011) |
| 400 | `ERROR_OTP_MAX_ATTEMPTS` | >5 failed verify attempts in 10 min (TC-011) |
| 400 | `ERROR_OTP_EXPIRED` | OTP TTL (300s) elapsed (TC-010) |
| 400 | `ERROR_INVALID_OTP` | Wrong OTP value (TC-009) |
| 400 | Validation error | `mobile`/`otp` missing or malformed (TC-013) |

---

## US-107 — Access Token Refresh

**What this ships:** a **stateless** refresh endpoint. It validates the submitted refresh token
(signature, expiry, type) and the account's current standing, then reissues a fresh access+refresh
pair. It does **not** implement single-use rotation, theft detection, or logout-invalidation
beyond what US-104 already provides.

| Setting | Value |
|---|---|
| Endpoint | `POST /api/v1/auth/refresh` *(public)* |

**Prerequisites:** any completed auth flow (US-001, US-101, or US-106) issues a refresh token.

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
| TC-008 | Old refresh token still works after one use (if not logged out) | `200` — by design, not a bug |
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

1. Complete registration through email verification only (`IDENTITY_VERIFICATION_PENDING`), keep
   that `refreshToken`.
2. In a separate session, finish Aadhaar verification for the same user → `ACTIVE`,
   `aadhaarVerified: true`.
3. `POST /api/v1/auth/refresh` with the **original** (pre-Aadhaar) `refreshToken`.

**Expected:** response shows `aadhaarVerified: true`, `status: "ACTIVE"`.

### TC-003 — Malformed / Tampered Refresh Token

`{ "refreshToken": "not-a-real-jwt" }` → **400:** `ERROR_INVALID_REFRESH_TOKEN`.

### TC-004 — Access Token Instead of Refresh Token

Submit an `accessToken` value as `refreshToken` → **400:** `ERROR_WRONG_TOKEN_TYPE`.

### TC-005 — Expired Refresh Token

Not reachable in real time (7-day TTL). Temporarily set `valuex.jwt.refresh-token-expiry` to
`5000` (5s), restart, get a token, wait 6s, then refresh.

**400:** `ERROR_REFRESH_TOKEN_EXPIRED`. **Revert the config change** afterward.

### TC-006 — Account Suspended After Token Issuance

```sql
UPDATE users SET status = 'SUSPENDED' WHERE mobile = '9000000030';
```
Refresh with the still-valid token → **400:** `ERROR_ACCOUNT_SUSPENDED`.

### TC-007 — Account Banned/Closed After Token Issuance

Same as TC-006 with `status = 'BANNED'` → **400:** `ERROR_ACCOUNT_RECOVERY_REQUIRED`.

### TC-008 — Old Refresh Token Still Works After One Use

1. Get `refreshToken_A`.
2. `POST /auth/refresh` with `refreshToken_A` → note `refreshToken_B`.
3. `POST /auth/refresh` again with the **original** `refreshToken_A`.

**Expected:** step 3 **succeeds** (200) — no single-use rotation. **Do not file as a bug.**

### TC-009 — Refresh Token Rejected as Bearer Access Token

Authorize in Swagger UI with a **refresh token**, call `GET /api/v1/users/me` → **401**
`UNAUTHORIZED`.

### TC-010 — Missing `refreshToken`

`{}` → **400** validation error.

### Not Testable Yet (US-107)

- "Replayed rotated-out token → theft, invalidate token family" — conditional on session tracking
  this design intentionally keeps minimal.
- Concurrent refresh calls near expiry — both succeed independently; a direct consequence of the
  stateless design.
- Clock skew at the expiry boundary — a pre-existing, systemic JJWT configuration property.

### US-107 Reset Between Tests

```sql
UPDATE users SET status = 'ACTIVE' WHERE mobile = '9000000030';
```

### US-107 Error Reference

| HTTP | Error Code | Cause |
|---|---|---|
| 400 | `ERROR_INVALID_REFRESH_TOKEN` | Malformed/tampered token, signature mismatch, or unknown `sub` (TC-003) |
| 400 | `ERROR_REFRESH_TOKEN_EXPIRED` | Past 7-day expiry, or the session was logged out (TC-005) |
| 400 | `ERROR_WRONG_TOKEN_TYPE` | Non-refresh-type token submitted (TC-004) |
| 400 | `ERROR_INVALID_STATE` | Account is `NEW`/`OTP_PENDING` — not reachable via a real refresh token |
| 400 | `ERROR_ACCOUNT_SUSPENDED` | Suspended since token issuance (TC-006) |
| 400 | `ERROR_ACCOUNT_RECOVERY_REQUIRED` | Banned/closed since token issuance (TC-007) |
| 401 | `UNAUTHORIZED` | Refresh token presented as Bearer access token (TC-009) |
| 400 | Validation error | `refreshToken` missing/blank (TC-010) |

---

## US-077 — Critical Event Notifications

**What this ships:** notifications for **account lifecycle events only** — account created,
Aadhaar verified, and state transitions to `UNDER_REVIEW`/`SUSPENDED`/`BANNED`. Every notification
always gets an in-app row (`GET /api/v1/notifications`); SMS/email are additionally attempted per
the channel table below, via **mock adapters that only log to the console** — no real SMS/email
provider is wired up. Push notifications, order/payment/cart/dispute/message events, and
notification preferences are **not built yet** (see Not Testable Yet).

| Setting | Value |
|---|---|
| Base tag | **Notifications** |
| Endpoints | `GET /api/v1/notifications`, `PATCH /api/v1/notifications/{id}/read` |
| Retention job | Daily background job, deletes rows older than 90 days — not manually triggerable |

**Test mobile numbers used in this section:** `9000000080` through `9000000082`.

### Channel Table (What Fires For What)

| Event | Trigger | eventType | Channels | Priority |
|---|---|---|---|---|
| Account created | Registration reaches `ACTIVE` (skip Aadhaar **or** complete Aadhaar) | `ACCOUNT_CREATED` | In-app + SMS | HIGH |
| Aadhaar verified | Aadhaar verification completes (fires alongside Account created, same call) | `AADHAAR_VERIFIED` | In-app only | MEDIUM |
| Account flagged for review | Transition to `UNDER_REVIEW` — no HTTP trigger exists yet, see US-088 | `ACCOUNT_UNDER_REVIEW` | In-app + SMS | HIGH |
| Account suspended | Transition to `SUSPENDED` | `ACCOUNT_SUSPENDED` | In-app + SMS + Email | HIGH |
| Account banned | Transition to `BANNED` | `ACCOUNT_BANNED` | In-app + SMS + Email | HIGH |

### Scenarios

| TC | Scenario | Expected Result |
|---|---|---|
| TC-001 | Registering and skipping Aadhaar creates an `ACCOUNT_CREATED` notification | Row appears in `GET /notifications`; console logs a mock SMS |
| TC-002 | Completing Aadhaar verification creates two notifications | `ACCOUNT_CREATED` and `AADHAAR_VERIFIED` both appear |
| TC-003 | Non-critical state transitions do not notify | No new row for e.g. clearing a review back to `ACTIVE` |
| TC-004 | Unread count header decreases after marking read | `X-Unread-Notifications` reflects the change |
| TC-005 | Marking an already-read notification read again is a no-op | 200, no error, `readAt` unchanged |
| TC-006 | Cannot mark another user's notification as read | 404 |
| TC-007 | Pagination and default page size | `GET /notifications` with no params returns 20 per page |

### TC-001 — Account Created Notification (Skip-Aadhaar Path)

**Steps:**
1. Register and verify mobile/email OTP through to `IDENTITY_VERIFICATION_PENDING` for mobile
   `9000000080` (see US-001 section above).
2. `POST /api/v1/auth/aadhaar/skip` (Bearer token from step 1).
3. Watch the console log for:
   ```
   [DEV-MOCK] SMS notification for mobile=9000000080 message=Welcome to ValueX!: Your account has been created successfully.
   ```
4. `GET /api/v1/notifications` (Bearer token from step 1).

**Expected:** one row with `eventType: "ACCOUNT_CREATED"`, `title: "Welcome to ValueX!"`,
`deepLink: "/profile"`, `read: false`. Response header `X-Unread-Notifications: 1`.

### TC-002 — Account Created + Aadhaar Verified (Complete-Aadhaar Path)

**Steps:** Follow the US-001 section's Aadhaar verification steps (sandbox provider, mobile
`9000000081`) instead of skipping, then `GET /api/v1/notifications`.

**Expected:** **two** rows — `ACCOUNT_CREATED` (In-app + SMS) and `AADHAAR_VERIFIED` (In-app only,
no SMS log line for this second one). `X-Unread-Notifications: 2`.

### TC-003 — Non-Critical Transitions Do Not Notify

**Goal:** confirm `CLOSED`, `RESTRICTED`, and "back to `ACTIVE`" transitions are silent — the AC's
critical-event list only names "Account suspended/banned," not every possible transition.

Since there is no admin/moderation HTTP endpoint yet (see US-088 below), this specific check is
only exercisable at the unit-test level today —
`AccountEventNotificationListenerTest.shouldNotDispatchForNonCriticalStateChanges` covers it. If
you'd like to observe it manually anyway, see US-088's testing notes on invoking
`UserStateService` methods directly.

### TC-004 — Unread Count Decreases After Marking Read

**Steps:**
1. `GET /api/v1/notifications` — note `X-Unread-Notifications` and the `id` of the first row.
2. `PATCH /api/v1/notifications/{id}/read`.
3. `GET /api/v1/notifications` again.

**Expected:** step 3's `X-Unread-Notifications` is one less than step 1's. The marked row now
shows `"read": true`.

### TC-005 — Marking an Already-Read Notification Is Idempotent

Repeat `PATCH /api/v1/notifications/{id}/read` a second time on the same `id` from TC-004.

**Expected:** `200 OK`, no error. `X-Unread-Notifications` does not decrease again.

### TC-006 — Cannot Mark Another User's Notification as Read

Using User A's Bearer token, `PATCH /api/v1/notifications/{id}/read` where `{id}` belongs to
User B (mobile `9000000082`).

**Expected response (404 Not Found):**
```json
{ "success": false, "error": { "code": "NOT_FOUND", "message": "Notification not found" } }
```

### TC-007 — Pagination Defaults

`GET /api/v1/notifications` with no query parameters, having created more than 20 notifications
for the test user.

**Expected:** response `data` array has at most 20 entries; `metadata.size: 20`, `metadata.page: 0`.
Use `?page=1` for the next page.

### Not Testable Yet (US-077)

- **Any moderation-triggered notification via HTTP** (flag for review, suspend, ban) — no admin
  endpoint exists (see US-088 below).
- **Push notifications** — no channel, no device-token registration.
- **Order/payment/cart/dispute/message notifications** — those modules don't exist until later
  sprints.
- **Password-changed notifications** — not applicable; this auth model has no password.
- **Unknown-device-login notifications** — explicitly deferred to a future sprint.
- **Notification preferences / opt-out** — a later story (US-087). Every event notifies
  unconditionally today.
- **Real SMS/email delivery** — both channels are mock/console-log only in this environment.

### US-077 Reset Between Tests

```sql
DELETE FROM notifications WHERE user_id = (SELECT id FROM users WHERE mobile = '<test mobile>');
```

### US-077 Error Reference

| HTTP | Error Code | Cause |
|---|---|---|
| 404 | `NOT_FOUND` | Notification doesn't exist or belongs to a different user (TC-006) |

---

## US-088 — Lifecycle State - User Account

**What this ships:** the *moderation* half of the account state machine
(`FLAG_FOR_REVIEW`/`CLEAR_REVIEW`/`RESTRICT`/`LIFT_RESTRICTION`/`SUSPEND`/`LIFT_SUSPENSION`/`BAN`/`CLOSE`),
plus an hourly background job that transitions expired `SUSPENDED` accounts back to `ACTIVE` after
7 days. **There is no REST endpoint for any of this** — no admin authentication/authorization
exists yet in this sprint, so an unauthenticated moderation API would be a security hole. This
section is therefore SQL- and log-based, not a Swagger walkthrough, and the "moderation actions"
themselves can only be exercised via the automated test suite (see below), not via HTTP.

| Setting | Value |
|---|---|
| Scheduled job | Auto-lifts expired suspensions — hourly cron, not manually triggerable in real time without a code change |
| Automated coverage | `UserAccountStateMachineTest`, `UserStateServiceTest`, `SuspendedAccountAutoLiftJobTest` |

**Test mobile numbers used in this section:** `9000000090` through `9000000093`.

### Scenarios

| TC | Scenario | Expected Result |
|---|---|---|
| TC-001 | Registration flow still writes state-history correctly | Unchanged — proves this story didn't regress the existing path |
| TC-002 | `SUSPENDED` account auto-lifts to `ACTIVE` after its 7-day window expires | Job flips `status` to `ACTIVE`, writes a history row |
| TC-003 | A banned user's Aadhaar cannot be reused for a new registration | Registration/Aadhaar-verify rejects the duplicate hash |
| TC-004 | Login is blocked for a `SUSPENDED` account | `ERROR_ACCOUNT_SUSPENDED` on login (cross-reference to US-106) |
| TC-005 | Automated test suite covers every transition | All relevant tests pass |

### TC-001 — Registration Flow Unaffected

Follow the US-001 section end to end for mobile `9000000090`, then:
```sql
SELECT from_status, to_status, action, actor_id, reason, changed_at
FROM account_status_history
WHERE user_id = (SELECT id FROM users WHERE mobile = '9000000090')
ORDER BY changed_at;
```
Expect the same four rows as always (`NEW→OTP_PENDING`, `OTP_PENDING→EMAIL_VERIFICATION_PENDING`,
`EMAIL_VERIFICATION_PENDING→IDENTITY_VERIFICATION_PENDING`,
`IDENTITY_VERIFICATION_PENDING→ACTIVE`), each with `reason IS NULL`.

### TC-002 — Suspended Account Auto-Lifts After 7 Days

Waiting a real 7 days isn't practical — use this fast path:

1. Register mobile `9000000091` through to `ACTIVE`.
2. Manually put the account into `SUSPENDED` with an **already-past** lift time:
   ```sql
   UPDATE users
   SET status = 'SUSPENDED', suspension_lifted_at = now() - interval '1 minute'
   WHERE mobile = '9000000091';
   ```
3. Ask a developer to temporarily change the auto-lift job's schedule to run every few seconds
   instead of hourly (a one-line code change, reverted after the test) and restart the app — there
   is no way to trigger this job on demand otherwise.
4. Re-check:
   ```sql
   SELECT status, suspension_lifted_at FROM users WHERE mobile = '9000000091';
   ```

**Expected:** `status = 'ACTIVE'`, `suspension_lifted_at IS NULL`. The application log shows
`Auto-lifted 1 expired suspensions`.

### TC-003 — Banned User's Aadhaar Cannot Be Reused

1. Complete registration + Aadhaar verification for mobile `9000000092` (`ACTIVE`,
   `aadhaar_verified = true`).
2. Ban the account directly: `UPDATE users SET status = 'BANNED' WHERE mobile = '9000000092';`
3. Attempt to register a **new** account (mobile `9000000093`) using the **same Aadhaar number**
   as step 1.

**Expected:** the new registration's Aadhaar verification step is rejected with the same
duplicate-Aadhaar error covered in US-002 — the banned user's row (and its Aadhaar hash) was never
deleted, so it stays permanently claimed.

### TC-004 — Login Blocked for a Suspended Account

Already covered end-to-end in **US-106 / TC-007** — this is the same check, just confirming it
applies regardless of *how* the account became `SUSPENDED`.

### TC-005 — Automated Test Suite

Ask a developer to run:
```
cd valuex-backend
mvn test -Dtest=UserAccountStateMachineTest,UserStateServiceTest,SuspendedAccountAutoLiftJobTest
```
**Expected:** all tests pass. This is the fastest, most complete way to verify every documented
transition (18 valid, plus invalid/terminal/wrong-from-state rejections) and every moderation
action (flag for review, restrict, suspend, ban, close) — none of which are reachable through the
UI or Swagger yet.

### Not Testable Yet (US-088)

- **Any moderation action via HTTP** — no REST controller exists (no admin login exists to guard
  one yet).
- **`close()` blocking on active orders** — the order module doesn't exist yet; nothing to check.
- **Appeal submission for `SUSPENDED`/`BANNED` accounts** — no appeal endpoint/flow exists.
- **Any user-facing notification on `UNDER_REVIEW`/`CLOSED`** — see US-077's channel table; only
  `UNDER_REVIEW`/`SUSPENDED`/`BANNED` notify, and even those need `UserStateService` to be called
  from somewhere, which today only happens in automated tests.

### US-088 Reset Between Tests

```sql
UPDATE users SET status = 'ACTIVE', suspension_lifted_at = NULL WHERE mobile = '<test mobile>';
```
Remember to revert any temporary auto-lift-job schedule change from TC-002 before committing or
pushing code.

### US-088 Error Reference

| HTTP | Error Code | Cause |
|---|---|---|
| 400 | `ERROR_ACCOUNT_SUSPENDED` | Login attempted while `status = SUSPENDED` (TC-004) |
| 400 | (duplicate-Aadhaar error, same as US-002) | Registration attempted with an Aadhaar hash already claimed (TC-003) |

---

## Consolidated Error Code Reference (All Stories)

| HTTP | Error Code | Stories | Meaning |
|---|---|---|---|
| 400 | `ERROR_INVALID_STATE` | US-001, US-002, US-101, US-106, US-107 | Endpoint/flow called out of sequence for the account's current state |
| 400 | `ERROR_OTP_EXPIRED` | US-001, US-101, US-105, US-106 | OTP TTL (300s) elapsed |
| 400 | `ERROR_INVALID_OTP` | US-001, US-101, US-105, US-106 | Wrong OTP value submitted |
| 400 | `ERROR_OTP_MAX_ATTEMPTS` | US-001, US-101, US-105, US-106 | 5 failed verify attempts in 10 min |
| 400 | `ERROR_OTP_RATE_LIMIT` | US-001, US-101, US-105, US-106 | 3 send attempts in 10 min |
| 400 | `ERROR_MOBILE_ALREADY_REGISTERED` | US-001, US-002, US-105 | Mobile already has an account |
| 400 | `ERROR_EMAIL_ALREADY_REGISTERED` | US-001, US-105 | Email linked to another account |
| 400 | `ERROR_AADHAAR_ALREADY_USED` | US-001, US-002 | Aadhaar linked to an active account |
| 400 | `ERROR_ACCOUNT_RECOVERY_REQUIRED` | US-002, US-101, US-106, US-107 | Account is BANNED/CLOSED (or Aadhaar/Google tied to one) |
| 400 | `ERROR_AADHAAR_SESSION_EXPIRED` | US-002 | >10 min between Aadhaar initiate and verify |
| 400 | `ERROR_INVALID_GOOGLE_TOKEN` | US-101 | Google token is the literal string `invalid`, or fails real validation |
| 400 | `ERROR_SOCIAL_SESSION_EXPIRED` / `ERROR_SOCIAL_SESSION_INVALID` | US-101 | Social session token unknown, expired, or malformed |
| 400 | `ERROR_MOBILE_MISMATCH` | US-101 | Verify-step mobile doesn't match initiate-step mobile |
| 400 | `ERROR_SOCIAL_ACCOUNT_ALREADY_LINKED` | US-101 | Target account already has Google linked |
| 400 | `ERROR_TERMS_NOT_ACCEPTED` / `ERROR_CONSENT_REQUIRED` | US-001, US-101 | Missing consent flags |
| 400 | `VALIDATION_ERROR` | US-003, US-106, US-107 | Field fails Jakarta Bean Validation |
| 400 | `ERROR_INVALID_AVATAR` | US-003 | `avatarId` not in the published catalog |
| 400 | `ERROR_MOBILE_NOT_REGISTERED` | US-106 | No account for the submitted mobile |
| 400 | `ERROR_ACCOUNT_SUSPENDED` | US-088, US-106, US-107 | Account is SUSPENDED |
| 400 | `ERROR_INVALID_REFRESH_TOKEN` | US-104, US-107 | Malformed/tampered/unknown-subject refresh token |
| 400 | `ERROR_REFRESH_TOKEN_EXPIRED` | US-104, US-107 | Refresh token past 7-day expiry, or session was logged out |
| 400 | `ERROR_WRONG_TOKEN_TYPE` | US-107 | Non-refresh token submitted to `/refresh` |
| 400 | `ERROR_NO_OTHER_SESSIONS` | US-105 | `revoke-others` called with only one active session |
| 401 | `UNAUTHORIZED` | US-001, US-003, US-103, US-104, US-105, US-107 | Missing/expired/blocklisted JWT, or a refresh token used as Bearer |
| 404 | `NOT_FOUND` | US-003, US-077, US-103 | Resource doesn't exist or doesn't belong to the caller |

---

## Full Teardown (Every Test Mobile Used in This Guide)

```sql
DELETE FROM notifications WHERE user_id IN (
  SELECT id FROM users WHERE mobile LIKE '9000000%' OR mobile LIKE '9111000%' OR mobile = '9876543210'
);
DELETE FROM user_sessions WHERE user_id IN (
  SELECT id FROM users WHERE mobile LIKE '9000000%' OR mobile LIKE '9111000%' OR mobile = '9876543210'
);
DELETE FROM contact_change_attempts WHERE user_id IN (
  SELECT id FROM users WHERE mobile LIKE '9000000%' OR mobile LIKE '9111000%' OR mobile = '9876543210'
);
DELETE FROM user_social_accounts WHERE user_id IN (
  SELECT id FROM users WHERE mobile LIKE '9000000%' OR mobile LIKE '9111000%' OR mobile = '9876543210'
);
DELETE FROM aadhaar_verification_attempts WHERE user_id IN (
  SELECT id FROM users WHERE mobile LIKE '9000000%' OR mobile LIKE '9111000%' OR mobile = '9876543210'
);
DELETE FROM account_status_history WHERE user_id IN (
  SELECT id FROM users WHERE mobile LIKE '9000000%' OR mobile LIKE '9111000%' OR mobile = '9876543210'
);
DELETE FROM users WHERE mobile LIKE '9000000%' OR mobile LIKE '9111000%' OR mobile = '9876543210';
```

> This wildcard version is broader than the original per-section teardown blocks (which listed
> exact numbers) — safe for a full environment reset between test cycles, but **don't run it**
> if other testers might be using the same shared environment with real test accounts in this
> number range at the same time.
