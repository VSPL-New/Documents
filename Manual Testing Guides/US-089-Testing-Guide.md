# US-089 — Lifecycle State - Listing: QA Testing Guide

**Sprint 2 · Seller Listing Creation**

Test guide for the listing state machine and `ListingLifecycleService`, using SQL, application logs and the
automated tests.

> **What this story ships:** the reconciled `ListingStateMachine` (payment first, then Trust & Safety review,
> then publication), `ListingLifecycleService.transition(...)` (the only code allowed to change
> `listings.status` after a listing is created), `ListingStatusChangedEvent`, `ListingState.isLiveForBuyers()`
> and `ListingState.isTerminal()`, and the `action` column on `listing_status_history` (Flyway `V13`).
> **There is no REST endpoint for transitions.** Later stories call the service: US-008 (plan selection),
> US-009 and US-084 (payment result, review, publication), US-010 (edit and delete) and US-115 (notifications
> listen to the event). Until they are built, the only manual check on a running system is the draft-creation
> history row (TC-001); everything else is covered by automated tests (TC-002 to TC-006).

| Setting | Value |
|---|---|
| Base URL | `http://localhost:8080` |
| DB | PostgreSQL, `listings` and `listing_status_history` tables |
| Migration | `V13__listing_status_history_action.sql` (adds nullable `action VARCHAR(50)`) |
| Error for an invalid move | HTTP 400, `INVALID_STATE_TRANSITION` (shared with user accounts) |
| Automated coverage | `ListingStateMachineTest`, `ListingStateTest`, `ListingLifecycleServiceTest`, `ListingLifecycleIntegrationTest` (needs Docker) |

Run the automated tests:

```powershell
cd C:\ValueX-Code\valuex-backend
mvn test "-Dtest=ListingStateMachineTest,ListingStateTest,ListingLifecycleServiceTest"
# needs Docker Desktop running (Testcontainers PostgreSQL):
mvn test "-Dtest=ListingLifecycleIntegrationTest"
```

---

## Test Scenarios Overview

| TC | Scenario | Expected result |
|---|---|---|
| TC-001 | Create a listing draft (US-004) | New history row: `from_status` null, `to_status` `DRAFT`, `action` `CREATE` |
| TC-002 | Every allowed transition passes; skipping payment or review is refused | `ListingStateMachineTest` passes; `DRAFT → PUBLISHED`, `PLAN_PAYMENT_SUCCESS → PUBLISHED`, `TRUST_SAFETY_REVIEW → PUBLISHED`, `EXPIRED → PUBLISHED` all fail |
| TC-003 | Paid path from draft to published | `DRAFT → PLAN_SELECTION_PENDING → PLAN_PAYMENT_PENDING → PLAN_PAYMENT_SUCCESS → TRUST_SAFETY_REVIEW → APPROVED → PUBLISHED`, one history row and one event per step |
| TC-004 | Revise and resubmit loop, then final rejection | `TRUST_SAFETY_REVIEW → REVISION_REQUIRED → TRUST_SAFETY_REVIEW` twice with no payment step, then `TRUST_SAFETY_REVIEW → REJECTED`; nothing can leave `REJECTED` |
| TC-005 | Invalid transition or unknown listing | 400 `INVALID_STATE_TRANSITION` with no status change, no history row, no event; unknown ID gives `LISTING_NOT_FOUND` |
| TC-006 | Concurrent transitions and rollback | Only one of two simultaneous identical transitions succeeds; a failure after the status change rolls back both the status and the history row |
| TC-007 | Migration `V13` on a database with existing history rows | Applies cleanly; old rows have `action` null |
| TC-008 | Buyer visibility rule | `ListingState.isLiveForBuyers()` is true for `PUBLISHED` only |

---

## TC-001 — Draft Creation Writes the `CREATE` Action

**Steps:** Sign in as an `ACTIVE` seller and create a draft (`POST /api/v1/listings`, see
`US-004-Testing-Guide.md`). Note the `listingId` from the response.

**Verify:**

```sql
SELECT from_status, to_status, action, changed_by, reason, changed_at
FROM listing_status_history
WHERE listing_id = '<listingId>'
ORDER BY changed_at;
```

**Expected:** one row: `from_status` null, `to_status` `DRAFT`, `action` `CREATE`, `changed_by` the seller ID,
`reason` `DRAFT_CREATED`. The listing's own `status` is `DRAFT`.

---

## TC-002 — Allowed and Refused Transitions

**Steps:** `mvn test "-Dtest=ListingStateMachineTest"`.

**Expected:** all tests pass. The test covers every row of the transition table in
`Documents/US-Implementation-Plans/US-089-Implementation-Plan.md`, plus refused moves:
no publication without payment and review, `REJECTED` is final, `EXPIRED` returns only through plan
selection (`RENEW`), a valid pair with the wrong action name is refused, and the three AI-era states
(`MEDIA_UPLOAD_PENDING`, `AI_DETAILS_GENERATED`, `PRICE_PENDING`) have no transitions.

---

## TC-003 / TC-004 — Full Paths

**Steps:** `mvn test "-Dtest=ListingStateMachineTest,ListingLifecycleServiceTest"`.

**Expected:** the paid path walks all six steps with six history rows and six events; the revise loop runs twice
and then `REJECTED` allows no further transition (`getAvailableTargetStates(REJECTED)` is empty).

---

## TC-005 — Refused Transition Changes Nothing

**Steps:** `mvn test "-Dtest=ListingLifecycleServiceTest"`.

**Expected:** for an invalid move the service throws `ValidationException` (`INVALID_STATE_TRANSITION`, HTTP 400),
the listing's status is unchanged, and no history row or event is written. An unknown listing ID throws
`NotFoundException` with `LISTING_NOT_FOUND`. A reason longer than 255 characters is trimmed to 255.

---

## TC-006 — Row Lock and Rollback (needs Docker)

**Steps:** start Docker Desktop, then `mvn test "-Dtest=ListingLifecycleIntegrationTest"`.

**Expected:** all 3 tests pass: history carries `action`; a failure after the transition rolls back status and
history; of two simultaneous `SUBMIT_FOR_PLAN` calls exactly one succeeds and the other is refused.

---

## TC-007 — Migration `V13`

**Steps:** start the backend against a database that already has listings (migrations run on startup).

**Verify:**

```sql
SELECT version, description, success FROM flyway_schema_history WHERE version = '13';
SELECT COUNT(*) FROM listing_status_history WHERE action IS NULL;   -- rows written before V13
```

**Expected:** version 13 present with `success = true`; earlier rows keep working with `action` null.

---

## TC-008 — Visibility Rule

**Steps:** `mvn test "-Dtest=ListingStateTest"`.

**Expected:** `isLiveForBuyers()` is true only for `PUBLISHED`; `isTerminal()` is true only for `SOLD`,
`DEACTIVATED_BY_SELLER`, `REMOVED_BY_ADMIN` and `REJECTED`.

---

## Not Testable Yet

- No endpoint or screen changes a listing's status; calling `transition` needs code from US-008, US-009,
  US-084, US-010 or a test. Do not file a missing endpoint as a bug.
- Seller notifications for status changes are built by US-115; this story only publishes the event.
- Search visibility (Sprint 3) will read `isLiveForBuyers()`; there is no search to test yet.
- Decisions behind the design (in-code state machine, HTTP 400 error, `PUBLISHED` only visible, no
  `PUBLISHED → SOLD` shortcut) are recorded in the plan's Open Gaps.
