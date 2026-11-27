# US-016 - Communication History Storage: QA Testing Guide

**Sprint 4 · Communication & Negotiation**

Manual and operational checks for communication closure, retention, legal holds, evidence access, and audit logging.
This guide validates backend behavior for chat/call history storage and retrieval safety.

> **What ships:** conversation closure/reopen rules, retention scheduling and purge safeguards, report/admin holds,
> admin evidence endpoints with audit logging, call-log retention parity with chat threads, and erasure/anonymisation
> protections for held data.
> **Not in this story:** call recording/transcript storage, admin UI, dispute workflow UI, account-closure trigger wiring,
> production role-authorisation replacement (US-053), and case-registry validation.

| Setting | Value |
|---|---|
| Backend base URL | `http://localhost:8080` |
| Retention defaults | `COMM_CHAT_RETENTION_DAYS=180`, `COMM_CALL_LOG_RETENTION_DAYS=180`, `COMM_INACTIVE_CLOSE_DAYS=90` |
| Batch behavior | retention job processes in bounded batches (up to 500) with `FOR UPDATE SKIP LOCKED` |
| Admin evidence precondition | non-production environment gate, `X-Case-Reference`, and reason length >= 10 |
| Key errors | `ERROR_STORAGE_FULL`, `ERROR_RETRIEVAL_FAILED`, `ERROR_EVIDENCE_PURGE_STARTED`, `ERROR_CONVERSATION_UNAVAILABLE` |

---

## Prerequisites

1. Backend, PostgreSQL, Redis running from `wt/US-016-backend`.
2. Test data with at least:
   - one buyer/seller pair with a chat thread and messages,
   - one or more call sessions linked to that thread,
   - at least one reportable pair.
3. Admin test token (`ADMIN` or `SUPER_ADMIN`) and normal user token.
4. Ability to inspect DB rows in communication tables and logs.
5. For retention staging checks, set shortened retention values in a non-prod environment.

---

## A. Closure and retention scheduling (AC1, AC3)

| # | Steps | Expected |
|---|---|---|
| A1 | Trigger listing state transition to `SOLD` or seller/admin closure state for a listing with active thread | Thread gets closed once (idempotent), closure reason recorded, chat/call purge deadlines set from closure time. |
| A2 | Trigger listing delete event on a listing with thread | Thread closure reason is `DELETED`; retention deadlines scheduled. |
| A3 | Run inactivity closure path for thread older than cutoff and not in active negotiation/live call | Thread closes with `INACTIVE`; deadlines set. |
| A4 | Send new user message on an `INACTIVE`-closed thread | Thread reopens; retention deadlines are cleared/reset per reopen rules. |
| A5 | Send new user message on thread closed due to sold/deleted listing | Original closure metadata stays; chat and related call-log retention deadlines restart from new message time. |
| A6 | Start call or offer on `INACTIVE`-closed thread | Thread reopens and retention deadlines clear to keep active conversation open. |

## B. Retention and purge safety (AC3 + edge cases)

| # | Steps | Expected |
|---|---|---|
| B1 | Prepare expired, unheld thread and run retention job | Eligible messages/thread/call logs are purged according to rules. |
| B2 | Prepare expired thread with active hold and run retention job | Thread and associated held evidence are preserved; no protected deletion. |
| B3 | Simulate image delete failure during retention | DB rows are not prematurely removed; retry path persists and later succeeds. |
| B4 | Simulate partial purge progress then rerun job | Job resumes safely; no duplicate destructive actions, no silent data loss. |
| B5 | Attempt new message/call/offer after purge has started for a conversation | Request is rejected with explicit conversation-unavailable conflict error. |

## C. Holds and report behavior (AC2, AC3, AC4)

| # | Steps | Expected |
|---|---|---|
| C1 | Create report against user pair with existing conversations | Report hold is applied to all existing shared conversations and related call logs. |
| C2 | Apply admin hold to thread with calls | Thread and related calls get admin hold entries; hold is independently tracked. |
| C3 | Release only admin hold for target/case reference | Only matching admin hold is released; report and other holds remain effective. |
| C4 | Attempt hold after purge has started | Hold request is explicitly refused and audited; no false protection claim. |
| C5 | Reconcile existing open reports before enabling purge in staging | Existing report-linked evidence remains protected; unresolved hold failures block purge. |

## D. Evidence retrieval and audit trail (AC2, AC4)

| # | Steps | Expected |
|---|---|---|
| D1 | Access admin evidence endpoint without admin role | Access denied. |
| D2 | Access with admin role but missing `X-Case-Reference` or short reason | Validation error; no evidence response. |
| D3 | Access thread/messages/call endpoints with valid headers and paging | Bounded page response with continuation behavior; no phone/email leakage. |
| D4 | Force retrieval failure path | `ERROR_RETRIEVAL_FAILED` returned and failed read is still audited. |
| D5 | Verify audit table immutability | update/delete on access log rows is refused; append-only behavior holds. |
| D6 | Simulate audit-write failure on evidence read | Evidence access fails closed (no data returned without durable audit). |

## E. Erasure and old-log handling (edge/error scenarios)

| # | Steps | Expected |
|---|---|---|
| E1 | Run `anonymiseUser` for user with eligible non-held evidence | Eligible message/user-identifying fields are anonymised; previews/flags adjusted as designed. |
| E2 | Run erasure where evidence is still held | Held evidence stays protected and is queued/deferred for retry after holds end. |
| E3 | Request very old unheld evidence after retention | Evidence unavailable response, without exposing sensitive metadata. |
| E4 | Generate high-storage pressure scenario in staging | Storage alerts fire; no data corruption; retention path remains safe. |

---

## Operational staging check

1. Set short non-prod retention (for example 1-2 days) and seed representative chat/call/report data.
2. Run retention and reconciliation jobs repeatedly with concurrent workers.
3. Confirm only eligible unheld evidence is deleted and held evidence remains intact.
4. Confirm retry queues drain for previously failed media/object cleanup tasks.
5. Capture DB snapshots before/after for audit evidence.

---

## Automated test subset

```bash
# Focused US-016 backend validations
mvn -f wt/US-016-backend/pom.xml "-Dtest=CommunicationRetentionJobTest,ChatIntegrationTest,CallIntegrationTest,BlockAndReportIntegrationTest,ReportServiceTest" test

# Full backend quality gate
mvn -f wt/US-016-backend/pom.xml verify
mvn -f wt/US-016-backend/pom.xml clean verify sonar:sonar "-Dsonar.token=$env:SONAR_TOKEN"
```

---

## Acceptance criteria map

| Criterion | Coverage |
|---|---|
| AC1 chat/call activity logged and secure storage behavior | A1-A6, B1-B5, D3 |
| AC2 admin access to relevant dispute evidence | C1-C4, D1-D4 |
| AC3 six-month retention from closure with hold protection | A1-A6, B1-B5, E3 |
| AC4 admin access logging and audit durability | D2-D6 |
| Edge cases and errors | B3-B5, D4-D6, E1-E4 |
