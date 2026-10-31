# US-009: Listing Publication After Payment â€” Implementation Plan

> **Update (2026-10-31, after US-117 and US-008 were built; revised with the product owner):**
> 1. US-117 (payments, `PaymentSucceededEvent`, `PaymentFailedEvent`, `PaymentRefundService`) is on `main`; US-008 (`PlanSelectionService`, `ListingPaymentCompletedHandler`, migration `V20`) is on its own branches and this story is **stacked on them** (the implementation branch `feature/US-009-listing-publication-after-payment` is cut from `feature/US-008-seller-chooses-listing-plan` in backend and mobile).
> 2. **Migration numbers:** the latest is `V20` (US-008). US-084's reviews table is `V21` and this story's `published_at` is `V22`.
> 3. **Mobile is now in scope:** a "listing under review" page after payment with a "Preview your listing" button (section 4, Mobile). The preview page itself is the new story US-123 (placeholder).
> 4. **Decisions:** late payment success continues only when the amount matches (section 3); seller notifications stay with US-115 (this story publishes events only); the refund flag uses `PaymentRefundService.requestRefund`.

## 1. Header

| Field | Value |
|---|---|
| Story ID | US-009 |
| Title | Listing Publication After Payment |
| Sprint | Sprint 2 â€” Seller Listing Creation |
| Story Points | 5 |
| Repos | valuex-backend, valuex-mobile (the under-review page) |
| Dependency | US-008 (built: plan selection, plan snapshot on the listing, zero-price path, `ListingPaymentCompletedHandler` interface); **US-117 (built: payment tables, signed callback handling, payment events, refund service)**; US-089 (`ListingLifecycleService`, states); US-007 (restricted-item gate); **US-084, developed and delivered together with this story** ([plan](US-084-Implementation-Plan.md)); US-123 (Preview Listing, placeholder: the button destination) |

**Combined delivery with US-084 (decided 2026-10-16):** one branch and one pull request for US-009 and US-084. Payment success hands the listing to the Trust & Safety review, and approval triggers publication, so neither half works alone. Both plans stay separate so each keeps its own acceptance criteria and tests; the shared order of work and end-to-end tests are in section 4.

**Scope decisions (product owner, 2026-10-16):**
1. Flow after payment: `PLAN_PAYMENT_SUCCESS` â†’ Trust & Safety review (US-084) â†’ `APPROVED` â†’ `PUBLISHED`. A listing is never published straight from payment.
2. **Plan validity starts at publication**: `expires_at` is set when the listing is published, not at payment or approval.
3. Review attempts: 3 in total per paid plan. A failed attempt 1 or 2 sends the seller back to edit and resubmit without paying again. After the 3rd failed attempt the plan fee is refunded. The refund is only flagged here (`REFUND_REVIEW`); whether it is issued automatically or manually is decided later.
4. If the hand-over to review or the publish step fails after payment, the listing stays where it is (`PLAN_PAYMENT_SUCCESS` or `APPROVED`), a retry job completes the step, and unrecoverable cases are refunded manually by finance.
5. A plan priced at zero (none today; plans and prices are managed by the admin console, US-116) has no payment and no callback; it follows the same hand-over, publication and (no) refund rules.
6. **Gateway-neutral (decided 2026-10-16).** The payment gateway is not chosen. The signed callback, signature check, idempotency and payment settling belong to US-117. This story only reacts to the payment result for a listing plan payment and owns the listing side: hand-over to review, publication, validity and the refund flag.

## 2. Story Recap

**As a** seller **I want** my listing to be published immediately after successful payment **so that** buyers can discover it right away. Updated: published as soon as the review approves it.

**Acceptance Criteria** (`Documents/user-stories.md`, updated 2026-10-16): when payment succeeds (or my plan is priced at zero) the listing goes to the Trust & Safety review and the seller is told it is under review; when the review approves it, the listing is published instantly, appears in search, plan features are active, and the seller is notified; the seller sees the published listing with the plan badge.

**Edge Cases:** payment succeeds but publish fails Â· listing published but features not activated Â· duplicate payment for the same listing Â· network interruption after payment Â· listing rejected after payment (edit and resubmit, up to 3 reviews, refund after the third failure).

**Validation Rules:** payment confirmed before review and publishing Â· status path Draft â†’ Plan payment â†’ Trust & Safety review â†’ Approved â†’ Published Â· unrecoverable failure is refunded Â· plan duration starts at publication Â· activation within 5 minutes of approval.

**Error Scenarios:** `ERROR_PUBLISH_FAILED` (only when a refund is issued) Â· `ERROR_DUPLICATE_PAYMENT` (absorbed silently).

## 3. Design Reference

Primary source: [Sprint-2-Seller Listing Creation-LLD.md â€” Part I](../LLD/Sprint-2-Seller%20Listing%20Creation-LLD.md#part-i---us-009-listing-publication-after-payment) (updated 2026-10-16), with Part H (US-008), Part F (US-084) and Part E (US-089).

**What already exists in the code (as built, 2026-10-31):**
- `payment` module (US-117): `payments`, `payment_attempts`, `payment_gateway_events`, `payment_refunds`; `PaymentSucceededEvent` (`paymentId`, `referenceType`, `referenceId`, `amount`, `late`) and `PaymentFailedEvent` (same fields and `reason` `FAILED`, `EXPIRED` or `SUPERSEDED`), published inside the settling transaction; `PaymentRefundService.requestRefund(paymentId, amount, reason, requestedBy)` which records a `REQUESTED` refund and moves the payment `PAYMENT_SUCCESS â†’ REFUND_REVIEW` (the transition `REVIEW_REFUND` and the late-success transition exist already); `PaymentRepository.findFirstByReferenceTypeAndReferenceIdAndStatusIn`.
- US-008: `PlanSelectionService` copies `plan_price`, `plan_validity_days` and `plan_price_includes_gst` onto the listing, creates the payment (`LISTING_PLAN`, listing id), and for a plan priced at zero walks the listing to `PLAN_PAYMENT_SUCCESS` and then calls `ListingPaymentCompletedHandler.onPaymentSuccess(listingId)` **inside its own transaction**. The handler is an interface in `listing.application.service`; `ListingPaymentHandlerConfig` provides a logging default (`@ConditionalOnMissingBean`) that this story replaces. A seller can re-select a plan from `PLAN_PAYMENT_PENDING`, `PLAN_PAYMENT_FAILED` or `PLAN_SELECTION_PENDING`.
- `ListingStatusHistory`, `ListingStateMachine` (all transitions used here exist, including `PAYMENT_SUCCESS`, `PAYMENT_FAIL`, `PAYMENT_TIMEOUT`, `SUBMIT_FOR_REVIEW`, `PUBLISH`), `ListingLifecycleService` and `ListingStatusChangedEvent` (`listingId`, `fromState`, `toState`, `action`).
- `listings.plan_type`, `expires_at`, the plan snapshot columns; there is no `published_at` column yet.
- Notification module with `@TransactionalEventListener(AFTER_COMMIT)` listeners (`AccountEventNotificationListener`); no listing notifications (US-115 is parked).
- Mobile: the Review & Publish page (US-008) shows a snackbar and goes Home after a confirmed payment, a plan priced at zero, or a payment still being confirmed.

**Key design decisions:**
- One shared handler, `ListingPaymentCompletedHandler.onPaymentSuccess(listingId)`, used by both the payment-succeeded event (priced plans) and US-008's zero-price path: it moves the listing to `PLAN_PAYMENT_SUCCESS` (if not already) and calls `TrustSafetyReviewService.review` (US-084). **Transactions:** the review runs in its own transaction (`REQUIRES_NEW`) with the failure caught and logged, so that a failed review never rolls back US-008's selection or the payment settlement; `PLAN_PAYMENT_SUCCESS` stays committed and the recovery job retries. Listeners on payment events use `@TransactionalEventListener(AFTER_COMMIT)` plus `@Transactional(REQUIRES_NEW)`, because the events are published inside the payment transaction and a plain after-commit write would not be saved.
- `ListingPublicationService.publishApprovedListing(listingId)` listens for `ListingStatusChangedEvent` with `toState = APPROVED`, sets `expires_at` (from the validity days copied onto the listing by US-008) and `published_at`, and moves the listing to `PUBLISHED`.
- **Refund flag (decided 2026-10-31):** a listener on US-084's `ListingRefundDueEvent` finds the listing's `PAYMENT_SUCCESS` payment and calls `PaymentRefundService.requestRefund(paymentId, full amount, "LISTING_REJECTED_AFTER_MAX_REVIEWS", null)`, which records a `REQUESTED` refund and moves the payment to `REFUND_REVIEW`; no gateway call is made, and finance later approves it with `approveAndExecute`. A zero-price listing has no payment, so nothing is flagged.
- **Late payment success (decided 2026-10-31, option A):** a `PaymentSucceededEvent` with `late = true` continues as a normal success only when the listing is still waiting for payment (`PLAN_PAYMENT_PENDING`, `PLAN_PAYMENT_FAILED` or `PLAN_SELECTION_PENDING`) **and** the paid amount equals the amount the listing's snapshot expects: `plan_price` when `plan_price_includes_gst` is true, otherwise `plan_price` plus GST at the current rate (`TaxSettingsService`). Anything else (listing already paid or past review, another amount, no snapshot) flags the payment for refund review through `requestRefund`, with a log line and a metric. If the GST mode changed after the snapshot the amounts differ, which fails safe into refund review.
- The callback is handled by US-117, which settles the payment and publishes `PaymentSucceededEvent` and `PaymentFailedEvent` with the reference type and ID; this story listens for reference type `LISTING_PLAN` only.

## 4. Implementation Steps

### Database Migration â€” `valuex-backend`
- [ ] `V22__listing_published_at.sql` (US-008 took `V20`, US-084's reviews table is `V21`; renumber at implementation time if the order changes): add nullable `published_at TIMESTAMP` to `listings`. Callback and idempotency columns on `payments` are created by US-117, not here.

### Backend â€” Payment Result Listeners
- [ ] Listener on US-117's `PaymentSucceededEvent` (reference type `LISTING_PLAN` only), `AFTER_COMMIT` and `REQUIRES_NEW`: call `ListingPaymentCompletedHandler.onPaymentSuccess(listingId)`. Duplicates are already filtered by US-117, and the handler is idempotent anyway (a listing already at or past `PLAN_PAYMENT_SUCCESS` is left alone).
- [ ] Listener on `PaymentFailedEvent` (`LISTING_PLAN` only), by `reason`: `FAILED` moves the listing `PLAN_PAYMENT_PENDING â†’ PLAN_PAYMENT_FAILED` (the seller can retry or choose another plan, US-008) **only if the failed payment is the listing's latest one** (no other open payment exists for the listing); `EXPIRED` moves it `PLAN_PAYMENT_PENDING â†’ PLAN_SELECTION_PENDING` (`PAYMENT_TIMEOUT`) under the same check; `SUPERSEDED` is ignored (US-008 already moved the listing).
- [ ] Late success (`late = true`): the rule in section 3 (continue when the listing still awaits payment and the amount matches the snapshot; otherwise `requestRefund` and a log and metric). The listener must tell "the listing awaits payment" from "already paid": a second payment for a listing in `PLAN_PAYMENT_SUCCESS` or later is always flagged for refund review.
- [ ] The webhook endpoint, signature check, amount check and unknown-order handling are US-117's and are not built here.

### Backend â€” Hand-over to Review
- [ ] `ListingPaymentCompletedHandler.onPaymentSuccess(listingId)`: implement the US-008 interface as a `@Component` in the listing module (the logging default backs off; cover this with a test), transition to `PLAN_PAYMENT_SUCCESS` where needed (`PAYMENT_SUCCESS`), then call US-084's review in a separate transaction. US-008 calls this for a zero-price plan after it has already reached `PLAN_PAYMENT_SUCCESS`; US-008's call is inside its own transaction, so the review must not share it (see section 3). The handler publishes no notification; US-115 does that from the status change event.
- [ ] A failure in the hand-over is caught and logged; the payment record and `PLAN_PAYMENT_SUCCESS` stay committed.

### Backend â€” Publication
- [ ] `ListingPublicationService.publishApprovedListing`: set `expires_at = published_at + the listing's plan validity days` (the snapshot taken by US-008, not the current catalog value) and `published_at = now` (only when `published_at` is empty: a re-approval after a seller edit, US-010, keeps both dates), transition `APPROVED â†’ PUBLISHED` (`PUBLISH`); US-115 sends the "your listing is live" notification from the status change event. A failure keeps the listing `APPROVED` and is logged and counted.
- [ ] Plan features: boosted and priority placement are derived from `plan_type` and `published_at` (search ranking itself is Sprint 3); no extra table.

### Backend â€” Recovery Jobs
- [ ] Scheduled job: listings in `PLAN_PAYMENT_SUCCESS` for more than a few minutes get the review hand-over retried.
- [ ] Scheduled job: listings in `APPROVED` for more than a few minutes get publication retried; after the retry limit an alert is raised (metric and log) and finance refunds the payment manually. Intervals and limits come from configuration (approved 2026-10-16: check every minute, retry after 5 minutes, 5 attempts).
- [ ] Scheduled job (LLD Â§H.8): a listing in `PLAN_PAYMENT_PENDING` with no open payment for more than 30 minutes (the payment was expired by US-117's reconciliation, or the expiry event was missed) returns to `PLAN_SELECTION_PENDING` (`PAYMENT_TIMEOUT`, added in US-089's table). The normal path is the `EXPIRED` event above; this job is the safety net.
- [ ] The jobs go through `ListingLifecycleService`, whose row lock makes a retry safe if two instances run it.

### Backend â€” Refund Flag
- [ ] Listener on US-084's `ListingRefundDueEvent`: find the listing's `PAYMENT_SUCCESS` payment (`LISTING_PLAN`, listing id) and call `PaymentRefundService.requestRefund(paymentId, amount, reason, null)`; do nothing for a zero-price listing or a payment that is already `REFUND_REVIEW` or later (a duplicate event is a no-op). The `PAYMENT_SUCCESS â†’ REFUND_REVIEW` transition already exists (US-117).

### Backend â€” Notifications and Metrics
- [ ] This story sends no notification itself. It publishes the domain events US-117 and US-084 already define and `ListingStatusChangedEvent`; US-115 (Listing Lifecycle Notifications, parked) turns them into seller notifications, with the copy in English and Hindi. Until US-115 is built the seller gets no notification (decided 2026-10-31: events only).
- [ ] Metrics (Micrometer counters and timers as in `PaymentMetrics`, dotted names): `payment.to.publish.latency`, `listing.publish.failure`, `listing.review.handover.failure`, `payment.late.refund.review`.

### Mobile (Flutter) â€” "Listing under review" page
Follow the brand design tokens and existing components; English and Hindi.
- [ ] `ListingSubmittedScreen` (route `/sell/submitted`, `extra` the listing id), a success page shown after the payment is confirmed by the server and after a plan priced at zero. Content: a success mark, the title "Your listing is submitted", and the message "Your listing is under Trust & Safety compliance review. It may take a few minutes. If any action is required, you will see it in your listing updates; otherwise your listing goes live automatically if it is compliant." Buttons: **Preview your listing** and a secondary **Back to Home**. The copy is softened (2026-10-31) so it promises no notification until US-115 is built; when US-115 adds the notifications, the message is changed to "We will notify you if any action is required". Hindi to be reviewed.
- [ ] **Preview your listing** opens the preview page of US-123 once it exists. Until then it shows a short "Preview is coming soon" message (confirmed 2026-10-31).
- [ ] Change US-008's Review page: after `PaymentResult.confirmed`, and after the zero-price "Publish", go to the new page instead of Home with a snackbar. `PaymentResult.pending` keeps the "We're confirming your payment" message and Home, because the listing is not known to be paid yet. Remove the strings `reviewPaymentReceived` and `reviewSubmitted` that become unused.
- [ ] Tests: the page text and both buttons; Hindi; 2x text; tap target and label guidelines; the Review page navigates to it for confirmed and zero-price; pending still goes Home.
- [ ] The page promises no notification until US-115 exists; see Open Gap 7.

### Combined Delivery With US-084 â€” Order of Work
1. Migrations for US-084 and US-009; `PaymentStateMachine` transition.
2. US-084 services (review, attempts, refund event) with their unit tests.
3. US-009 handler, payment result listeners, publication service, jobs, refund listener.
4. Shared end-to-end tests below; then lint, SonarQube and manual testing guides (`US-009-Testing-Guide.md` and `US-084-Testing-Guide.md`, or one shared guide referencing both).

### Documentation/Quality
- [ ] Update LLD Part I where the implementation differs (the webhook documentation belongs to US-117).
- [ ] Mobile: only the under-review page above; the listing state otherwise reaches the app through the listing endpoints and notifications (US-115). The preview page is US-123.

## 5. Test Plan

Target >90% coverage for new code (`CLAUDE.md`).

### Unit Tests
- [ ] Payment result listeners: a `LISTING_PLAN` success event calls the handler once and ignores other reference types; failure `reason` `FAILED`, `EXPIRED` and `SUPERSEDED` each take their own path; a `FAILED` or `EXPIRED` event for a payment that is not the listing's latest does nothing; a duplicate event is a no-op.
- [ ] Late success: continues when the listing awaits payment and the amount equals the snapshot's expected amount (GST inclusive and exclusive); flagged for refund review (`requestRefund` once) when the amount differs, the listing is already paid or past review, or there is no snapshot.
- [ ] The real handler replaces the logging default in the application context.
- [ ] A failing review in the zero-price path does not roll back US-008's selection.
- [ ] Zero-price plan: `onPaymentSuccess` without a payment goes to review; no payment row is needed.
- [ ] Hand-over failure keeps `PLAN_PAYMENT_SUCCESS`; the retry job completes it; the job is idempotent.
- [ ] Publication: sets `published_at` from the publication time and `expires_at` from it plus the listing's snapshotted validity days (a later change to the plan's validity changes nothing), moves to `PUBLISHED`; failure keeps `APPROVED`; retry job publishes; alert after the retry limit.
- [ ] Event listener ignores every status other than `APPROVED`.
- [ ] Refund flag: third failure calls `requestRefund` once for a paid payment (payment `REFUND_REVIEW`, one `REQUESTED` refund row, no gateway call); zero-price listing does nothing; duplicate event is a no-op.
- [ ] Unpaid timeout returns the listing to plan selection only after 30 minutes.

### Integration Tests (Testcontainers PostgreSQL)
- [ ] Payment events: a `PaymentSucceededEvent` published by US-117 (using its dummy gateway: create a payment through US-008's plan selection, then simulate success) drives the listing to review; migration applies on top of `V21`.
- [ ] Late success after the seller switched plans: the old payment's late success is flagged for refund review (amount differs); the same plan's late success after expiry continues.
- [ ] Both listener types run after commit in their own transaction and the listing and payment changes are saved.

### Combined End-to-End Tests (US-009 + US-084)
- [ ] AI off (default), manual review off: pay â†’ `PLAN_PAYMENT_SUCCESS` â†’ review auto-approves (`AUTO_APPROVED_NO_AI`) â†’ `PUBLISHED`, `expires_at` counted from publication, history shows every step.
- [ ] Manual review on: pay â†’ `TRUST_SAFETY_REVIEW` waits; approval through the service â†’ `PUBLISHED`.
- [ ] Reject twice with resubmission each time (no second payment), approve on attempt 3 â†’ `PUBLISHED`.
- [ ] Reject three times â†’ `REJECTED`, payment `REFUND_REVIEW`, seller notified, no further resubmission.
- [ ] Zero-price plan end to end, including a third rejection with no refund flag.
- [ ] Hand-over or publish forced to fail once, recovered by the job.

### Mobile Tests (Flutter)
Listed under the under-review page in section 4.

## 6. Validation Checklist

- [ ] No listing is published without a successful payment (or a zero-price plan) and an approved review.
- [ ] Plan validity starts at publication and uses the validity snapshot.
- [ ] Only `LISTING_PLAN` payment events are handled; signature and duplicate handling stay in US-117.
- [ ] A payment is never lost: a failed hand-over or publish leaves the listing in a retryable state.
- [ ] A seller is never charged twice for the same listing, including after revisions.
- [ ] After the third failed review the payment is `REFUND_REVIEW` with a `REQUESTED` refund row and no gateway refund is called.
- [ ] A payment that arrives late is never silently kept: it continues the listing or is flagged for refund review.
- [ ] After a confirmed payment the seller sees the under-review page, not a bare message, and it never says the listing is live.
- [ ] Every status change goes through `ListingLifecycleService`.
- [ ] Notifications sent for under review, published and refund due (through US-115).
- [ ] Checkstyle, full tests, coverage and SonarQube pass before push.

## 7. Open Gaps / Questions

1. **Order of work (resolved 2026-10-31).** US-117 is on `main`; US-008 is built on its branches and US-009 is stacked on them. US-008 calls `ListingPaymentCompletedHandler` for the zero-price path.
2. **Refund execution (decided: later).** Only the `REFUND_REVIEW` flag is built; automatic or manual refund is decided later. The existing refund states (`REFUND_APPROVED`, `REFUND_PROCESSED`) are ready for it.
3. **Retry settings (decided 2026-10-16).** Check every minute, retry after 5 minutes, up to 5 attempts, then alert.
4. **Gateway (decided 2026-10-16: not chosen).** Gateway, webhook secret and signature format are US-117's open items; this story is independent of them.
5. **Notification copy (decided).** Owned by US-115, including the Hindi text.
6. **Search ranking for boosted and priority** is Sprint 3; this story only sets `plan_type` and `published_at`.
7. **Notification promise (decided 2026-10-31).** The page wording is softened and promises no notification. The notifications will be built under US-115, which then also changes the page text to "We will notify you if any action is required" (add that to the US-115 plan).
8. **Preview button before US-123 (decided 2026-10-31).** The button shows "Preview is coming soon" until US-123 is built.
9. **Late payment (decided 2026-10-31).** Option A in section 3. The expected amount is derived from the snapshot (price, plus GST at the current rate in exclusive mode); a later change of GST mode makes it fail safe into refund review. If this proves too fragile, store the charged amount on the listing in a later migration.
10. **Notifications (decided 2026-10-31).** Events only; US-115 later.
11. **Refund flag (decided 2026-10-31).** `requestRefund` (a `REQUESTED` refund row plus `REFUND_REVIEW`), no gateway call.
12. **Duplicate payment (accepted 2026-10-31).** Two simultaneous plan selections for one listing can give the seller `400 ERROR_DUPLICATE_PAYMENT` (try again) in US-117's create race; the user story's "already paid and published" message is not shown (a listing already past payment gets `ERROR_PLAN_SELECTION_NOT_ALLOWED` from US-008). Accepted for now; business will review the wording and any change is raised as a bug or enhancement.
13. **US-123 (decided 2026-10-31).** The preview page is a separate placeholder story (`user-stories.md`, Sprint 2 table); only its button is part of this story.

---

## 8. Implementation Notes (2026-10-31)

Built together with US-084 on branches `feature/US-009-listing-publication-after-payment` (backend, mobile). All steps in section 4 are done; the deviations from the plan are:

1. **One shared testing guide:** [US-009-Testing-Guide.md](../Manual%20Testing%20Guides/US-009-Testing-Guide.md) covers both stories.
2. **Transactions:** the zero-price hand-over from US-008 is registered to run after US-008's transaction commits (running the review `REQUIRES_NEW` inside it would wait on the listing row lock that the outer transaction still holds). Every after-commit listener runs its writes through `RequiresNewTransaction`. The logging default (`ListingPaymentHandlerConfig`) was deleted instead of backing off.
3. **Retry count is in memory** (per listing and state, limit 5, alert once), not stored; a restart gives a stuck listing a fresh set of attempts. Exhaustion logs `ALERT` and raises metric `listing.recovery.exhausted`.
4. **Recovery job extras:** it also decides a listing stuck in `TRUST_SAFETY_REVIEW` with no review waiting for a person (US-084 open gap 7), and continues a listing whose payment succeeded but was never applied (checked by the unpaid-timeout task).
5. **Late success that continues the listing** also supersedes any other open payment of the listing, so the seller cannot be charged twice.
6. **Not built / deferred:** seller notifications (US-115), the listing preview (US-123). A non-late success event for a listing that is already past payment is ignored (no refund flag), because a duplicate delivery must never refund a good payment.
7. **Integration tests** use `LocalDateTime` in UTC to age rows, because Hibernate writes an `Instant` as UTC wall-clock time in a `TIMESTAMP` column, which differs from `NOW()` when the JVM zone is not UTC.

**Status:** Implemented
