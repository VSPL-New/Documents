# US-088 — Lifecycle State - User Account: QA Testing Guide

**Sprint 1 · Identity & User Management**

Manual test cases for the user-account state machine's moderation transitions and the 7-day
suspension auto-lift job, using SQL + application log inspection against a local dev environment.

> **What this story actually ships:** the *moderation* half of `UserAccountStateMachine`
> (`FLAG_FOR_REVIEW`/`CLEAR_REVIEW`/`RESTRICT`/`LIFT_RESTRICTION`/`SUSPEND`/`LIFT_SUSPENSION`/`BAN`/`CLOSE`),
> implemented as `UserStateService`, plus `SuspendedAccountAutoLiftJob`, an hourly `@Scheduled` job
> that transitions expired `SUSPENDED` accounts back to `ACTIVE`. **There is no REST endpoint for
> any of this** — no admin authentication/RBAC exists yet (Sprint 10 owns that surface), so an
> unauthenticated moderation API would be a security hole. See
> `Documents/LLD/Sprint-1-Identity-User-Management-LLD.md` §7.6-§7.9 for the full reasoning, and
> the **Not Testable Yet** section below before filing anything here as a bug.

| Setting | Value |
|---|---|
| Base URL | `http://localhost:8080` |
| DB | PostgreSQL, `users` / `account_status_history` tables |
| Scheduled job | `SuspendedAccountAutoLiftJob.liftExpiredSuspensions()` — hourly cron `0 0 * * * *` |
| Automated coverage | `UserAccountStateMachineTest`, `UserStateServiceTest`, `SuspendedAccountAutoLiftJobTest` — run via `mvn test -Dtest=UserAccountStateMachineTest,UserStateServiceTest,SuspendedAccountAutoLiftJobTest` |

---

## Test Scenarios Overview

| TC | Scenario | Expected Result |
|---|---|---|
| TC-001 | Registration flow (US-001) still writes `account_status_history` correctly | Unchanged — proves this story didn't regress the existing NEW→ACTIVE path |
| TC-002 | SUSPENDED account auto-lifts to ACTIVE after its 7-day window expires | Hourly job flips `status` to `ACTIVE`, clears `suspension_lifted_at`, writes a history row with `action = 'LIFT_SUSPENSION'` and `actor_id IS NULL` |
| TC-003 | SUSPENDED account with `suspension_lifted_at` still in the future is left alone | Job does not touch it; still `SUSPENDED` after the job runs |
| TC-004 | A banned user's Aadhaar cannot be reused for a new registration | `ERROR_AADHAAR_ALREADY_REGISTERED` (or equivalent) on `POST /register/initiate` / Aadhaar verify — banned row's `aadhaar_hash` still holds the unique constraint |
| TC-005 | Login is blocked for a SUSPENDED account | `ERROR_ACCOUNT_SUSPENDED` on `POST /auth/login/initiate` (pre-existing `UserLoginService` behavior, confirms it still applies to accounts reached via this story's transitions) |
| TC-006 | State-machine unit tests pass in full | All 34 tests across the three new/updated test classes pass |

---

## TC-001 — Registration Flow Unaffected

**Goal:** Confirm adding `UserStateService`/`suspensionLiftedAt` did not disturb the existing
registration-flow transitions (`UserRegistrationService` et al.), which share the same
`UserAccountStateMachine` and `account_status_history` table.

**Steps:** Follow `US-001-Testing-Guide.md` end to end (register → verify mobile → verify email →
skip or complete Aadhaar).

**Verify:**
```sql
SELECT from_status, to_status, action, actor_id, reason, changed_at
FROM account_status_history
WHERE user_id = '<the test user's id>'
ORDER BY changed_at;
```
Expect the same four rows as before this story (`NEW→OTP_PENDING`, `OTP_PENDING→EMAIL_VERIFICATION_PENDING`,
`EMAIL_VERIFICATION_PENDING→IDENTITY_VERIFICATION_PENDING`, `IDENTITY_VERIFICATION_PENDING→ACTIVE`),
each with `reason IS NULL` (registration-flow history writes don't pass a reason — only
`UserStateService`'s do).

---

## TC-002 — Suspended Account Auto-Lifts After 7 Days

**Goal:** Confirm the hourly job actually flips an expired suspension back to `ACTIVE`.

Waiting a real 7 days (or a real hour for the cron to fire) isn't practical for a test pass — use
this fast path instead:

1. Register a test user through to `ACTIVE` (see TC-001).
2. Manually put the account into `SUSPENDED` with an **already-past** lift time (simulates "7 days
   have elapsed"):
   ```sql
   UPDATE users
   SET status = 'SUSPENDED', suspension_lifted_at = now() - interval '1 minute'
   WHERE mobile = '9000000040';
   ```
3. Temporarily shorten the job's cron so it fires within the test session — in
   `SuspendedAccountAutoLiftJob`, change:
   ```java
   @Scheduled(cron = "0 0 * * * *")   // every hour
   ```
   to:
   ```java
   @Scheduled(fixedRate = 10000)      // every 10 seconds, TEST ONLY
   ```
   and restart the app. **Revert this change before committing/pushing** — don't leave a 10-second
   cron in the codebase.
4. Wait up to 10 seconds, then re-check:
   ```sql
   SELECT status, suspension_lifted_at FROM users WHERE mobile = '9000000040';
   ```

**Expected:** `status = 'ACTIVE'`, `suspension_lifted_at IS NULL`.

**Also verify:**
```sql
SELECT from_status, to_status, action, actor_id, reason
FROM account_status_history
WHERE user_id = (SELECT id FROM users WHERE mobile = '9000000040')
ORDER BY changed_at DESC LIMIT 1;
```
Expect `from_status = SUSPENDED`, `to_status = ACTIVE`, `action = 'LIFT_SUSPENSION'`,
`actor_id IS NULL` (system-triggered, not an admin), `reason = 'Automatic 7-day suspension expiry'`.

**Application log** should show:
```
State transition successful: Suspended -> Active via LIFT_SUSPENSION
Auto-lifted 1 expired suspensions
```

---

## TC-003 — Suspension Not Yet Expired Is Left Alone

**Steps:**
1. Same as TC-002 step 2, but with a **future** lift time:
   ```sql
   UPDATE users
   SET status = 'SUSPENDED', suspension_lifted_at = now() + interval '1 day'
   WHERE mobile = '9000000041';
   ```
2. With the shortened test cron from TC-002 still active, wait 10+ seconds.
3. Re-check the row.

**Expected:** `status` is still `SUSPENDED`, `suspension_lifted_at` unchanged. The job's query
(`findByStatusAndSuspensionLiftedAtBefore`) must not select this row.

---

## TC-004 — Banned User's Aadhaar Cannot Be Reused

**Goal:** Confirm the AC's "BANNED users' Aadhaar is blacklisted" — satisfied entirely by the
pre-existing `users.aadhaar_hash` unique constraint, no new code from this story.

**Steps:**
1. Complete registration + Aadhaar verification for a test user (`ACTIVE`, `aadhaar_verified = true`).
2. Ban the account directly (no admin endpoint exists yet):
   ```sql
   UPDATE users SET status = 'BANNED' WHERE mobile = '9000000042';
   ```
3. Attempt to register a **new** account using the **same Aadhaar number** as step 1 (see
   `US-001-Testing-Guide.md` / `US-002-Testing-Guide.md` for the Aadhaar verification steps).

**Expected:** the new registration's Aadhaar verification step is rejected with the existing
duplicate-Aadhaar error (same behavior as US-002's one-account enforcement) — because the banned
user's row (and its `aadhaar_hash`) was never deleted, the unique constraint still blocks reuse.

---

## TC-005 — Login Blocked for a Suspended Account

**Goal:** Confirm accounts reached via `UserStateService.suspend()` are correctly blocked by the
pre-existing `UserLoginService.assertLoginEligible` check (proves the two pieces integrate, even
though neither was changed to accommodate the other).

**Steps:**
1. Register a test user through to `ACTIVE`.
2. `UPDATE users SET status = 'SUSPENDED', suspension_lifted_at = now() + interval '7 days' WHERE mobile = '9000000043';`
3. `POST /api/v1/auth/login/initiate` with `{ "mobile": "9000000043" }`.

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

---

## TC-006 — Automated Test Suite

```
cd valuex-backend
mvn test -Dtest=UserAccountStateMachineTest,UserStateServiceTest,SuspendedAccountAutoLiftJobTest
```

**Expected:** `Tests run: 34, Failures: 0, Errors: 0`. This is the fastest way to verify every
documented transition (18 valid, plus invalid/terminal/wrong-from-state rejections), every
`UserStateService` action (including `account_status_history` writes and `UserStateChangedEvent`
publication, captured via Mockito), and both the happy and partial-failure paths of the auto-lift
job.

---

## Not Testable Yet (Don't File as Bugs)

- **Any moderation action via HTTP** (flag for review, restrict, suspend, ban, close) — there is no
  REST controller. `UserStateService` is a plain Spring `@Service`; the only way to exercise it
  today is the automated unit tests (TC-006) or direct SQL manipulation of `users.status` combined
  with observing downstream effects (TC-002 through TC-005). This is intentional — see the LLD
  §7.9 for why an endpoint isn't built yet (Sprint 10 admin auth doesn't exist).
- **`close()` blocking on active orders** — the AC says active orders must complete before
  closure, but the order module doesn't exist until Sprint 5. There is nothing to check against
  yet; `close()` will succeed regardless of any hypothetical "active order."
- **Appeal submission for SUSPENDED/BANNED accounts** — no appeal endpoint/flow exists anywhere in
  the codebase; the AC's "appeals allowed within 30 days" is a validation-rule line with no
  corresponding user story.
- **Any user-facing notification on state change** — `com.valuex.notification` is still the
  Sprint-0 scaffold; US-077 (Critical Event Notifications) isn't built. `UserStateChangedEvent` is
  published but nothing consumes it yet.

---

## Reset Between Tests

```sql
UPDATE users SET status = 'ACTIVE', suspension_lifted_at = NULL WHERE mobile = '<test mobile>';
```

Remember to revert `SuspendedAccountAutoLiftJob`'s cron back to `"0 0 * * * *"` if you used the
TC-002 fast-path override, before committing or pushing.

---

## Error Reference

| HTTP | Error Code | Cause |
|---|---|---|
| 400 | `ERROR_ACCOUNT_SUSPENDED` | Login attempted while `status = SUSPENDED` (TC-005) — pre-existing `UserLoginService` behavior |
| 400 | (duplicate-Aadhaar error, same as US-002) | Registration attempted with an Aadhaar hash already claimed by a banned (or any other) user row (TC-004) |
