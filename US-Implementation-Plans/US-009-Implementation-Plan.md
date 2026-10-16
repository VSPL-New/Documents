# US-009: Listing Publication After Payment — Implementation Plan

## 1. Header

| Field | Value |
|---|---|
| Story ID | US-009 |
| Title | Listing Publication After Payment |
| Sprint | Sprint 2 — Seller Listing Creation |
| Story Points | 5 |
| Repos | valuex-backend only |
| Dependency | US-008 (plan selection, plan price and validity snapshot on the listing, zero-price path); **US-117 (payment tables, signed callback handling, payment events, refund states)**; US-089 (`ListingLifecycleService`, states); US-007 (restricted-item gate); **US-084, developed and delivered together with this story** ([plan](US-084-Implementation-Plan.md)) |

**Combined delivery with US-084 (decided 2026-10-16):** one branch and one pull request for US-009 and US-084. Payment success hands the listing to the Trust & Safety review, and approval triggers publication, so neither half works alone. Both plans stay separate so each keeps its own acceptance criteria and tests; the shared order of work and end-to-end tests are in section 4.

**Scope decisions (product owner, 2026-10-16):**
1. Flow after payment: `PLAN_PAYMENT_SUCCESS` → Trust & Safety review (US-084) → `APPROVED` → `PUBLISHED`. A listing is never published straight from payment.
2. **Plan validity starts at publication**: `expires_at` is set when the listing is published, not at payment or approval.
3. Review attempts: 3 in total per paid plan. A failed attempt 1 or 2 sends the seller back to edit and resubmit without paying again. After the 3rd failed attempt the plan fee is refunded. The refund is only flagged here (`REFUND_REVIEW`); whether it is issued automatically or manually is decided later.
4. If the hand-over to review or the publish step fails after payment, the listing stays where it is (`PLAN_PAYMENT_SUCCESS` or `APPROVED`), a retry job completes the step, and unrecoverable cases are refunded manually by finance.
5. A plan priced at zero (none today; plans and prices are managed by the admin console, US-116) has no payment and no callback; it follows the same hand-over, publication and (no) refund rules.
6. **Gateway-neutral (decided 2026-10-16).** The payment gateway is not chosen. The signed callback, signature check, idempotency and payment settling belong to US-117. This story only reacts to the payment result for a listing plan payment and owns the listing side: hand-over to review, publication, validity and the refund flag.

## 2. Story Recap

**As a** seller **I want** my listing to be published immediately after successful payment **so that** buyers can discover it right away. Updated: published as soon as the review approves it.

**Acceptance Criteria** (`Documents/user-stories.md`, updated 2026-10-16): when payment succeeds (or my plan is priced at zero) the listing goes to the Trust & Safety review and the seller is told it is under review; when the review approves it, the listing is published instantly, appears in search, plan features are active, and the seller is notified; the seller sees the published listing with the plan badge.

**Edge Cases:** payment succeeds but publish fails · listing published but features not activated · duplicate payment for the same listing · network interruption after payment · listing rejected after payment (edit and resubmit, up to 3 reviews, refund after the third failure).

**Validation Rules:** payment confirmed before review and publishing · status path Draft → Plan payment → Trust & Safety review → Approved → Published · unrecoverable failure is refunded · plan duration starts at publication · activation within 5 minutes of approval.

**Error Scenarios:** `ERROR_PUBLISH_FAILED` (only when a refund is issued) · `ERROR_DUPLICATE_PAYMENT` (absorbed silently).

## 3. Design Reference

Primary source: [Sprint-2-Seller Listing Creation-LLD.md — Part I](../LLD/Sprint-2-Seller%20Listing%20Creation-LLD.md#part-i---us-009-listing-publication-after-payment) (updated 2026-10-16), with Part H (US-008), Part F (US-084) and Part E (US-089).

**What already exists in the code:**
- `payment` module with `PaymentState` and `PaymentStateMachine` (`PAYMENT_INITIATED → PAYMENT_PENDING → PAYMENT_SUCCESS / PAYMENT_FAILED`, plus escrow and refund states `REFUND_REVIEW`, `REFUND_APPROVED`, `REFUND_PROCESSED`). No `payments` table, gateway client or callback exists yet (US-117 adds them, and US-008 adds the plan snapshot columns on `listings`).
- `ListingStatusHistory`, `ListingStateMachine` and (after US-089) `ListingLifecycleService` and `ListingStatusChangedEvent`.
- `listings.plan_type`, `listings.expires_at`; there is no `published_at` column yet.
- Notification module with event listeners (`AccountEventNotificationListener`).

**Key design decisions:**
- One shared handler, `ListingPaymentCompletedHandler.onPaymentSuccess(listingId)`, used by both the payment-succeeded event (priced plans) and US-008's zero-price path: it moves the listing to `PLAN_PAYMENT_SUCCESS` (if not already), calls `TrustSafetyReviewService.review` (US-084) and publishes the event that makes US-115 send the "under review" notification.
- `ListingPublicationService.publishApprovedListing(listingId)` listens for `ListingStatusChangedEvent` with `toStatus = APPROVED`, sets `expires_at` (from the validity days copied onto the listing by US-008) and `published_at`, and moves the listing to `PUBLISHED`.
- The refund is only flagged: a listener on US-084's `ListingRefundDueEvent` moves the payment to the existing `REFUND_REVIEW` state (a `PAYMENT_SUCCESS → REFUND_REVIEW` transition, action `REVIEW_REFUND`, is added to `PaymentStateMachine`, unless US-117 already added it) and publishes the event for the seller notification. No gateway refund call is built here; US-117 provides the refund call for when it is decided. A zero-price listing has no payment, so nothing is flagged.
- The callback is handled by US-117, which settles the payment and publishes `PaymentSucceededEvent` and `PaymentFailedEvent` with the reference type and ID; this story listens for reference type `LISTING_PLAN` only.

## 4. Implementation Steps

### Database Migration — `valuex-backend`
- [ ] Next free Flyway version after US-084's (for example `V21__listing_published_at.sql`, after US-078's `V17`, US-117's `V18`, US-008's `V19` and US-084's `V20`; renumber at implementation time): add nullable `published_at TIMESTAMP` to `listings`. Callback and idempotency columns on `payments` are created by US-117, not here.

### Backend — Payment Result Listeners
- [ ] Listener on US-117's `PaymentSucceededEvent` (reference type `LISTING_PLAN` only): call `ListingPaymentCompletedHandler.onPaymentSuccess(listingId)` after the payment change is committed. Duplicates are already filtered by US-117, and the handler is idempotent anyway.
- [ ] Listener on `PaymentFailedEvent` (`LISTING_PLAN` only), by `reason`: `FAILED` moves the listing `PLAN_PAYMENT_PENDING → PLAN_PAYMENT_FAILED` (the seller can retry or choose another plan, US-008); `EXPIRED` moves it `PLAN_PAYMENT_PENDING → PLAN_SELECTION_PENDING` (`PAYMENT_TIMEOUT`); `SUPERSEDED` is ignored (US-008 already moved the listing).
- [ ] Late success: a `PaymentSucceededEvent` with `late = true` continues as a normal success when the listing is still waiting for that plan payment (`PLAN_PAYMENT_PENDING`, `PLAN_PAYMENT_FAILED` or `PLAN_SELECTION_PENDING` with the same plan); otherwise the payment is flagged for refund review and a log and metric are written. Proposed default, see US-117 Open Gaps item 3.
- [ ] The webhook endpoint, signature check, amount check and unknown-order handling are US-117's and are not built here.

### Backend — Hand-over to Review
- [ ] `ListingPaymentCompletedHandler.onPaymentSuccess(listingId)`: transition to `PLAN_PAYMENT_SUCCESS` where needed (`PAYMENT_SUCCESS`), then call US-084's review, then publish the payment-succeeded event (US-115 sends the "under review" notification). US-008 calls this for a zero-price plan.
- [ ] A failure in the hand-over is caught and logged; the payment record and `PLAN_PAYMENT_SUCCESS` stay committed.

### Backend — Publication
- [ ] `ListingPublicationService.publishApprovedListing`: set `expires_at = published_at + the listing's plan validity days` (the snapshot taken by US-008, not the current catalog value) and `published_at = now` (only when `published_at` is empty: a re-approval after a seller edit, US-010, keeps both dates), transition `APPROVED → PUBLISHED` (`PUBLISH`); US-115 sends the "your listing is live" notification from the status change event. A failure keeps the listing `APPROVED` and is logged and counted.
- [ ] Plan features: boosted and priority placement are derived from `plan_type` and `published_at` (search ranking itself is Sprint 3); no extra table.

### Backend — Recovery Jobs
- [ ] Scheduled job: listings in `PLAN_PAYMENT_SUCCESS` for more than a few minutes get the review hand-over retried.
- [ ] Scheduled job: listings in `APPROVED` for more than a few minutes get publication retried; after the retry limit an alert is raised (metric and log) and finance refunds the payment manually. Intervals and limits come from configuration (approved 2026-10-16: check every minute, retry after 5 minutes, 5 attempts).
- [ ] Scheduled job (LLD §H.8): a listing in `PLAN_PAYMENT_PENDING` with no open payment for more than 30 minutes (the payment was expired by US-117's reconciliation, or the expiry event was missed) returns to `PLAN_SELECTION_PENDING` (`PAYMENT_TIMEOUT`, added in US-089's table). The normal path is the `EXPIRED` event above; this job is the safety net.
- [ ] The jobs go through `ListingLifecycleService`, whose row lock makes a retry safe if two instances run it.

### Backend — Refund Flag
- [ ] Add `PAYMENT_SUCCESS → REFUND_REVIEW` (`REVIEW_REFUND`) to `PaymentStateMachine`.
- [ ] Listener on US-084's `ListingRefundDueEvent`: payment → `REFUND_REVIEW`, then publish a refund-started event (US-115 sends `LISTING_REFUND_DUE` with the amount); do nothing for a zero-price listing.

### Backend — Notifications and Metrics
- [ ] This story sends no notification itself. It publishes domain events (payment succeeded, payment failed, refund started) and US-115 (Listing Lifecycle Notifications) turns them into seller notifications, with the copy in English and Hindi.
- [ ] Metrics: `payment_to_publish_latency_ms`, `listing_publish_failure_total`, `listing_review_handover_failure_total`.

### Combined Delivery With US-084 — Order of Work
1. Migrations for US-084 and US-009; `PaymentStateMachine` transition.
2. US-084 services (review, attempts, refund event) with their unit tests.
3. US-009 handler, payment result listeners, publication service, jobs, refund listener.
4. Shared end-to-end tests below; then lint, SonarQube and manual testing guides (`US-009-Testing-Guide.md` and `US-084-Testing-Guide.md`, or one shared guide referencing both).

### Documentation/Quality
- [ ] Update LLD Part I where the implementation differs (the webhook documentation belongs to US-117).
- [ ] No mobile change in this story; the app learns the listing state from the listing endpoints and notifications.

## 5. Test Plan

Target >90% coverage for new code (`CLAUDE.md`).

### Unit Tests
- [ ] Payment result listeners: a `LISTING_PLAN` success event calls the handler once and ignores other reference types; failure `reason` `FAILED`, `EXPIRED` and `SUPERSEDED` each take their own path; a late success continues or is flagged for refund review; a duplicate event is a no-op.
- [ ] Zero-price plan: `onPaymentSuccess` without a payment goes to review; no payment row is needed.
- [ ] Hand-over failure keeps `PLAN_PAYMENT_SUCCESS`; the retry job completes it; the job is idempotent.
- [ ] Publication: sets `published_at` from the publication time and `expires_at` from it plus the listing's snapshotted validity days (a later change to the plan's validity changes nothing), moves to `PUBLISHED`; failure keeps `APPROVED`; retry job publishes; alert after the retry limit.
- [ ] Event listener ignores every status other than `APPROVED`.
- [ ] Refund flag: third failure moves a paid payment to `REFUND_REVIEW` once; zero-price listing does nothing; duplicate event is a no-op.
- [ ] Unpaid timeout returns the listing to plan selection only after 30 minutes.
- [ ] `PaymentStateMachine`: `PAYMENT_SUCCESS → REFUND_REVIEW` allowed; unrelated transitions unchanged.

### Integration Tests (Testcontainers PostgreSQL)
- [ ] Payment events: a `PaymentSucceededEvent` published by US-117 (using its sandbox adapter) drives the listing to review; migration applies on top of the previous versions.

### Combined End-to-End Tests (US-009 + US-084)
- [ ] AI off (default), manual review off: pay → `PLAN_PAYMENT_SUCCESS` → review auto-approves (`AUTO_APPROVED_NO_AI`) → `PUBLISHED`, `expires_at` counted from publication, history shows every step.
- [ ] Manual review on: pay → `TRUST_SAFETY_REVIEW` waits; approval through the service → `PUBLISHED`.
- [ ] Reject twice with resubmission each time (no second payment), approve on attempt 3 → `PUBLISHED`.
- [ ] Reject three times → `REJECTED`, payment `REFUND_REVIEW`, seller notified, no further resubmission.
- [ ] Zero-price plan end to end, including a third rejection with no refund flag.
- [ ] Hand-over or publish forced to fail once, recovered by the job.

## 6. Validation Checklist

- [ ] No listing is published without a successful payment (or a zero-price plan) and an approved review.
- [ ] Plan validity starts at publication and uses the validity snapshot.
- [ ] Only `LISTING_PLAN` payment events are handled; signature and duplicate handling stay in US-117.
- [ ] A payment is never lost: a failed hand-over or publish leaves the listing in a retryable state.
- [ ] A seller is never charged twice for the same listing, including after revisions.
- [ ] After the third failed review the payment is flagged `REFUND_REVIEW` and no gateway refund is called.
- [ ] Every status change goes through `ListingLifecycleService`.
- [ ] Notifications sent for under review, published and refund due (through US-115).
- [ ] Checkstyle, full tests, coverage and SonarQube pass before push.

## 7. Open Gaps / Questions

1. **Order of work.** US-117 and US-008 must be built before this story. US-008 calls `ListingPaymentCompletedHandler` for the zero-price path.
2. **Refund execution (decided: later).** Only the `REFUND_REVIEW` flag is built; automatic or manual refund is decided later. The existing refund states (`REFUND_APPROVED`, `REFUND_PROCESSED`) are ready for it.
3. **Retry settings (decided 2026-10-16).** Check every minute, retry after 5 minutes, up to 5 attempts, then alert.
4. **Gateway (decided 2026-10-16: not chosen).** Gateway, webhook secret and signature format are US-117's open items; this story is independent of them.
5. **Notification copy (decided).** Owned by US-115, including the Hindi text.
6. **Search ranking for boosted and priority** is Sprint 3; this story only sets `plan_type` and `published_at`.

---

**Status:** Draft
