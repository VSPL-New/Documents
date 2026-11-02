# US-115: Listing Lifecycle Notifications — Implementation Plan

## 1. Header

| Field | Value |
|---|---|
| Story | US-115 Listing Lifecycle Notifications |
| Sprint | Sprint 2 — Seller Listing Creation |
| Story points | 3 |
| Repos | valuex-backend, valuex-mobile |
| Naming | **JustQlic** is the app and business name of the ValueX project; "ValueX" is the project and code name. User-facing text (notifications, email, SMS) says JustQlic |
| Dependency | US-077 (notification module, done), US-089 (`ListingStatusChangedEvent`, done). The producing events now exist in the backend: `PaymentFailedEvent` and `PaymentSucceededEvent` (US-117), `ListingReviewDecidedEvent` and `ListingRefundDueEvent` (US-084/US-009). Unparked 2026-11-01 |

## 2. Story Recap

**As a** seller **I want** to be told, in the app and by email where it matters, what happens to my listing after I pay for a plan **so that** I know what to do next without checking the app.

Acceptance criteria (from `Documents/user-stories.md`, US-115):
- Payment succeeds (or the free plan is chosen): "under review" in the app.
- Listing approved and published: "your listing is live" in the app; tapping it opens the listing.
- Review 1 or 2 does not approve it: "needs changes" in the app and by email, with the reason and "review n of 3", saying the seller can update and resubmit without paying again; tapping it opens Item Details (US-114).
- Third review fails: "not approved after 3 reviews" in the app, by email and by SMS; with the plan fee refund amount when paid, no refund sentence for the free plan.
- Refund being processed: "refund is being processed" in the app and by email, with the amount ("refund issued" is added when the refund step is built).
- Payment fails: "payment unsuccessful" in the app; tapping it opens plan selection.
- Listing expires or an admin removes it: "listing expired" (renew action) or "listing removed" (support link) in the app; removal also by email.
- Notifications (US-077) lists them with the listing title, newest first, unread marked; one event never creates more than one notification, even when received twice.

Messages and channels (eight event types): `LISTING_UNDER_REVIEW` (in-app), `LISTING_PUBLISHED` (in-app), `LISTING_REVISION_REQUIRED` (in-app, email), `LISTING_REJECTED_FINAL` (in-app, email, SMS), `LISTING_REFUND_DUE` (in-app, email), `LISTING_PAYMENT_FAILED` (in-app), `LISTING_EXPIRED` (in-app), `LISTING_REMOVED_BY_ADMIN` (in-app, email). English and Hindi texts are in the story.

Edge cases: duplicate event delivery; long, quoted or non-Latin title (shortened for display); long review reason (full in app and email, shortened for SMS); preferences (US-087) followed except for the action-needed messages, which always stay in the in-app history; missing or bouncing email (in-app still created); listing deleted before the message arrives.

Validation rules: priority follows US-077 (high: needs changes, final rejection, refund, removal; medium: under review, published, payment failed, expired); one notification per listing, event type and review attempt; no card, bank or Aadhaar data; plain text only; messages carry the event type and values (title, reason, attempt, amount) so the app localizes; email and SMS are English; every message has a deep link; history kept 90 days. Error: `ERROR_NOTIFICATION_FAILED` is logged, never shown, and never blocks the listing flow.

## 3. Design Reference

No LLD section exists for US-115 (Open Gap 2). Used instead:
- Sprint 1 LLD, US-077: §6.2 event pattern, §6.4 `Notification` entity, §6.7 `NotificationDispatcher` (state machine, row persisted, SMS and email failures caught), §6.8 `AccountEventNotificationListener` (`@TransactionalEventListener(AFTER_COMMIT)`), §6.10 mobile page (tabs by `eventType` prefix; `LISTING_*` is already the Listings tab).
- Sprint 2 LLD, Part E (US-089) and Part I (payment): `ListingStatusChangedEvent`; Part I.5 names `LISTING_UNDER_REVIEW`, `LISTING_PUBLISHED`, `LISTING_REFUND_DUE`.
- Code as of 2026-11-01 (all built): `ListingStatusChangedEvent` (`fromState`, `toState`, `action`, `reason`); `ListingReviewDecidedEvent` (`listingId`, `attemptNumber`, `decision` = APPROVED/QUEUED/REVISION_REQUIRED/REJECTED, `reason`); `ListingRefundDueEvent` (`listingId` only, published on every third failed initial review, also for the free plan); `PaymentFailedEvent` / `PaymentSucceededEvent` (`referenceType`, `referenceId`, `amount`; for plan payments `referenceType` is `LISTING_PLAN`, `referenceId` is the listing id).

Key facts from the code today:
- `Notification` has no `params` column; `NotificationDispatchRequest` has no params or dedupe key; the dispatcher always inserts a new row.
- `NotificationResponse` returns `eventType`, `title`, `body`, `deepLink`; the app shows the server's title and body text and has no per-event localization yet.
- The app opens only `/profile` and `/profile/account-security` from a deep link (`notification_deep_links.dart`); other links show "coming soon". There is no listing details page yet (US-012). `/sell/details` and `/sell/plan` redirect to `/sell` unless the route `extra` is `ItemDetailsArgs(listingId)` or `PlanArgs(listingId, ListingSummary)`, so a deep link cannot open them directly; the app has to load the listing first.
- Free plan: no payment row and no `PaymentSucceededEvent` exist, but the listing still goes `PLAN_PAYMENT_SUCCESS` → `TRUST_SAFETY_REVIEW` (`ListingPaymentHandler`), so the status event is the one trigger for "under review" on both plans.
- `ListingPaymentResultListener` only moves the listing to `PLAN_PAYMENT_FAILED` / `PLAN_SELECTION_PENDING` when no newer payment is open, so the status event (not `PaymentFailedEvent`) is the accurate trigger for "payment unsuccessful".
- `ListingRefundDueEvent` carries no amount; `ListingRefundDueListener` flags the `PAYMENT_SUCCESS` plan payment as `REFUND_REVIEW` and does nothing when the plan was free. `ListingReviewDecidedEvent` (REJECTED) is published before the refund-due event, so the final-rejection message must look the plan payment up itself.
- `AccountEventNotificationListener` dispatches inside an AFTER_COMMIT callback through a plain `@Transactional` dispatcher. Spring joins the already-committed transaction there, so rows may not be saved when the event was published inside a transaction. Other AFTER_COMMIT listeners in the code (`ListingPaymentResultListener`) use `RequiresNewTransaction` for this reason.
- `AccountContactLookupService` gives mobile and email by user id; the listing gives `sellerId` and `title`.
- Listing actions from the state machine: `PUBLISH`, `EXPIRE`, `REMOVE`, `REQUEST_REVISION`, `REJECT`, `PAYMENT_FAIL`.

Key design decisions:
- One new listener, `ListingEventNotificationListener`, in the notification module, same pattern as `AccountEventNotificationListener`; it dispatches through `NotificationDispatcher` and never calls the listing services.
- Add nullable `params` (JSONB) and a unique `dedupe_key` (listing id, event type, attempt) to `notifications`; a duplicate event is ignored by catching the unique violation, inside the dispatch transaction.
- The server still stores English `title` and `body` (so email, SMS and old app versions work); the app uses `eventType` and `params` to show the Hindi or English text from the ARB files.

## 4. Implementation Steps

All eight messages can be built now; the producing events exist (Open Gap 1 resolved).

### Database Migration (`valuex-backend`)
- [x] `V23__notification_params_dedupe.sql` (`V22` is the latest): add `notifications.params JSONB NULL` and `notifications.dedupe_key VARCHAR(160) NULL` with a unique index on `dedupe_key` where it is not null.

### Backend — Notification module
- [x] Add `params` and `dedupeKey` to `Notification`, `NotificationDispatchRequest` and `NotificationResponse` (the response gains `params`; existing fields unchanged).
- [x] `NotificationDispatcher.dispatch`: when `dedupeKey` is set and a row with that key exists, return it without sending SMS or email (checked before insert; the unique index is the final guard for concurrent duplicates).
- [ ] Make sure the row is really saved when the listing event was published inside a transaction: the listener (or a new dispatcher method) runs the dispatch in `RequiresNewTransaction`, and an integration test publishes through `DomainEventPublisher` from inside a `@Transactional` method and asserts the row exists afterwards.
- [x] `ListingNotificationCopy` (a small class or enum): per `eventType` the English title, body template, priority, channels and deep link; fills `{title}`, `{reason}`, `{n}`, `{amount}`; shortens the listing title (for example 60 characters), the reason for SMS, strips markup and control characters; refund sentence only when an amount is present.
- [x] `ListingEventNotificationListener` (`@TransactionalEventListener(AFTER_COMMIT)`):
  - From `ListingStatusChangedEvent`: `toState TRUST_SAFETY_REVIEW` with `fromState PLAN_PAYMENT_SUCCESS` → `LISTING_UNDER_REVIEW` (paid and free plan; resubmits and edit reviews give nothing); `toState PUBLISHED` → `LISTING_PUBLISHED`; `toState PLAN_PAYMENT_FAILED`, or action `PAYMENT_TIMEOUT` → `LISTING_PAYMENT_FAILED` (Open Gap 13); `toState EXPIRED` → `LISTING_EXPIRED`; `toState REMOVED_BY_ADMIN` → `LISTING_REMOVED_BY_ADMIN` (in-app + email, link to support); other transitions give nothing.
  - From `ListingReviewDecidedEvent` (now with `reviewKind`, Open Gap 15): decision `REVISION_REQUIRED` → `LISTING_REVISION_REQUIRED` (reason; `attemptNumber` of 3 for `INITIAL` reviews, no "review n of 3" part and no `attempt` param for `EDIT` reviews); decision `REJECTED` → `LISTING_REJECTED_FINAL` (reason; plan fee amount when a plan payment exists, none for the free plan); `APPROVED` and `QUEUED` give nothing.
  - From `ListingRefundDueEvent`: `LISTING_REFUND_DUE` with the plan payment amount; nothing when the plan was free.
  - Plan fee amount: a small lookup interface in the payment module (for example `ListingPlanFeeLookup`, reading `PaymentRepository` for `LISTING_PLAN` payments in `PAYMENT_SUCCESS`, `REFUND_REVIEW`, `REFUND_APPROVED` or `REFUND_PROCESSED`), so the notification module does not read payment tables and does not depend on listener order.
  - Dedupe key: reviews use `listingId:eventType:reviewKind:attemptNumber`; refund due uses `listingId:eventType:paymentId`; status-event messages use `listingId:eventType:eventId` (Open Gap 14).
  - Resolve seller, title and contact (`ListingRepository` read through a small lookup interface in the listing module, `AccountContactLookupService`); skip and log when the listing or seller is gone. A missing email never stops the in-app row.
- [x] Keep the existing account copy as "JustQlic" (the app's name, Open Gap 4). Write the new listing messages with "JustQlic" too: `LISTING_REMOVED_BY_ADMIN` reads "removed by JustQlic" (English and Hindi), as in the corrected story.
- [x] Put the send-or-not check for preferences in one method, `shouldSend(userId, eventType, channel)`, that returns true until US-087 is built (Open Gap 6).
- [ ] Final-rejection SMS behind a config switch; confirm the SMS template with the SMS provider before production (Open Gap 7).
- [x] Deep links: `/listing/{listingId}` (published), `/sell/details?listingId={id}` (revision), `/sell/plan?listingId={id}` (payment failed, expired renew), `/support` (removed). Under review has no link (stays on Notifications).

### Mobile (`valuex-mobile`)
- [x] `AppNotification` reads `params`; a mapper turns `eventType` + `params` into the localized title and body (English and Hindi ARB strings for all eight types, title shortened and quotes kept as text); unknown types and old rows fall back to the server's text.
- [x] Icons for the new types in `notification_presentation.dart`; action-needed types use the alert colour.
- [x] `notification_deep_links.dart`: `_targets` maps fixed paths only and the routes need `extra`. Extend `NotificationTarget` with the query `listingId`; for `/sell/details` push `ItemDetailsArgs(listingId)`, for `/sell/plan` first load the listing through the listing repository to build `PlanArgs(listingId, ListingSummary)`; show an error snackbar when the listing no longer exists. The listing details and support links stay "coming soon" until US-012 and support exist.
- [ ] Hindi strings go in `app_hi.arb`; they need native-speaker review before release (story).
- [x] "Listing submitted" page: change `submittedActionMessage` from "It will appear in your listing updates." to "We will notify you if any action is required" in `app_en.arb` and the Hindi equivalent in `app_hi.arb` (Open Gap 12a).
- [x] Revision message without "review n of 3" when `params.attempt` is absent (edit reviews).

### Backend — Listing module (small change to US-084 code)
- [x] Add `reviewKind` (`INITIAL` / `EDIT`) to `ListingReviewDecidedEvent` and pass `review.getReviewKind()` from `TrustSafetyReviewService.publishDecision`; update the tests that construct the event.

### Documentation
- [ ] Add the US-115 part to the Sprint 2 LLD (Open Gap 2) and `Documents/Manual Testing Guides/US-115-Testing-Guide.md` after implementation.

## 5. Test Plan

Target above 90 % coverage for new code.

Unit tests (backend)
- [x] `ListingNotificationCopy`: every event type gives the right title, body, priority, channels and link; long, quoted, markup-bearing and non-Latin titles; long reason in app and shortened for SMS; refund sentence present with an amount and absent without.
- [x] Listener: `PUBLISHED`, `EXPIRED` and `REMOVED_BY_ADMIN` notify; other transitions do not; the dispatch happens after commit only; listing or seller missing is skipped and logged; missing email still creates the in-app row.
- [x] Dispatcher: same dedupe key twice gives one row and one email or SMS; a channel failure does not roll back the row; no key keeps the old behaviour (existing US-077 tests still pass).
- [x] Review and payment handlers: attempt 1, 2 and 3 messages, paid and free plan, payment failed and payment timeout, refund due with and without a plan payment, a newer open payment (no payment-failed message because the listing did not move), edit-review revision (Open Gap 15).

Integration tests (Testcontainers)
- [ ] Migration applies; a real `ListingStatusChangedEvent` to `PUBLISHED` creates one notification with `params`, priority and deep link; the event published twice gives one row; `GET /api/v1/notifications` returns it with `params`, newest first, unread marked.
- [ ] Only the owner sees it (IDOR); 90-day retention job still removes old rows.

Mobile tests
- [x] Localized title and body for each type in English and Hindi; fallback for an unknown type and for a row without `params`.
- [x] Tapping opens Item Details or plan selection with the right listing; unbuilt targets show "coming soon".
- [x] Notifications page lists them under the Listings tab; accessibility guidelines for the new rows and at 2x text size.

## 6. Validation Checklist

- [x] Each of the eight messages exists with the story's wording, channels and priority (expired and removed can only be triggered by a published test event until US-054 and the expiry job exist).
- [x] One event gives one notification, also when delivered twice or re-run.
- [x] Final rejection mentions a refund only for a paid plan.
- [x] No card, bank or Aadhaar data, no HTML, titles and reasons are plain text and shortened where needed.
- [x] SMS and email failures never block the listing flow and are logged as `ERROR_NOTIFICATION_FAILED`.
- [x] Action-needed messages are always in the in-app history, whatever the preferences (US-087 not built; keep a single place to apply them later).
- [x] The app shows Hindi or English from `eventType` and `params`; older app versions still show the server text.
- [x] A notification for a deleted listing does not fail the event.
- [ ] Checkstyle, full tests, coverage and SonarQube pass before push.

## 7. Open Gaps / Questions

1. **Resolved (2026-11-01): build the whole story now.** US-117, US-009 and US-084 are built, so all eight messages can be triggered (expired and removed only by a test event until their producers exist).
2. **No LLD section for US-115.** Decided (2026-11-01): write a short US-115 part in the Sprint 2 LLD (listener, `params`, dedupe key, copy table, deep links) as the first documentation step; it does not block coding.
3. **Migration number.** Resolved: `V22` is the latest, so this story takes `V23`.
4. **Brand name.** Decided (2026-11-01): JustQlic is the app and business name of the ValueX project, so the account copy stays "JustQlic" and the new messages say JustQlic. The story's earlier instruction to change "JustQlic" to "ValueX", and "removed by ValueX" in its message table, were corrected in `Documents/user-stories.md` on 2026-11-01.
5. **Deep link targets.** Decided (2026-11-01): use the formats in section 4. Tapping "your listing is live" shows "coming soon" until US-012 exists; the same for `/support`.
6. **Preferences.** Decided (2026-11-01): send unconditionally for now, through a single `shouldSend` method that US-087 can fill in later; action-needed messages always stay in the in-app history.
7. **Final-rejection SMS.** Decided (2026-11-01): build it as the story says, behind a config switch; the SMS template must be confirmed with the SMS provider before production, otherwise the switch stays off.
8. **Email and SMS language.** Decided (2026-11-01): English only until a language preference is stored on the server.
9. **Push** Decided (2026-11-01): not built; medium-priority messages are in-app only until push exists (US-077).
10. **Hindi wording.** Decided (2026-11-01): use the story's draft text; native-speaker review is a release gate.
11. **"Refund issued"** Decided (2026-11-01): left out; added when the refund step is built.
12. **Follow-ups from US-009 (2026-10-31).** (a) Decided (2026-11-01): change the "listing submitted" page text to "We will notify you if any action is required", English and Hindi (step in section 4). (b) Resolved: this story takes `V23`. (c) Decided (2026-11-01): a late payment sent to refund review by US-009 (reason `LATE_PAYMENT_NOT_APPLICABLE`) gets no message for now; add it when the refund step is built.
13. **Payment-timeout message.** Decided (2026-11-01): "payment unsuccessful" is sent for both a failed payment and a timed-out payment, and nothing for a superseded payment.
14. **Dedupe key.** Decided (2026-11-01): review messages use `listingId:eventType:reviewKind:attemptNumber`, refund due uses `listingId:eventType:paymentId`, status-based messages use `listingId:eventType:eventId` (so a re-approved edit gives a second "live" message).
15. **Edit reviews.** Decided (2026-11-01): add `reviewKind` to `ListingReviewDecidedEvent`; edit reviews drop "review n of 3" and leave `params.attempt` empty (steps in section 4).
16. **Refund amount.** Decided (2026-11-01): show the plan payment amount, GST included, as the "plan fee".

---

**Status:** Approved — approved by the user on 2026-11-01; all open gaps decided. Implemented on branch `feature/US-115-listing-lifecycle-notifications` (2026-11-01); not yet committed. See section 8.

---

## 8. Implementation Notes (2026-11-01)

**Done and verified:** backend `mvn clean verify` (1,296 tests, checkstyle clean, JaCoCo check passed; new classes at 100 % line coverage) and mobile `dart format`, `flutter analyze` (no issues) and `flutter test` (986 passed). The LLD part is Part K of `Documents/LLD/Sprint-2-Seller Listing Creation-LLD.md`.

**Not done or not verified (still open):**
- `ListingNotificationIntegrationTest` is written but was skipped here (no Docker on this machine); it must run in CI or on a machine with Docker. This also covers the "saved when published inside a transaction" check and the IDOR / 90-day retention items.
- SonarQube was not run: no server on `localhost:9000` and no token in this environment.
- The final-rejection SMS template must be confirmed with the SMS provider before production; native-speaker review of the Hindi text is a release gate.

**Deviations from this plan:**
1. **Scope added (decided 2026-11-01, option A):** the app could not open an existing listing, so Item Details and plan selection could not be reached from a notification. Added `ExistingListing`, `ListingRepository.getListing` and `resubmitForReview`, Item Details starting from stored values, a "Resubmit for review" action for a listing in `REVISION_REQUIRED` (calls `POST /listings/{id}/trust-safety-review`, no payment), and a loader (`notification_navigation.dart`) that opens each page only for the right status. Statuses: details for `REVISION_REQUIRED`; plan selection for `PLAN_SELECTION_PENDING` and `PLAN_PAYMENT_FAILED`; otherwise "This listing can no longer be changed here". The renew link for an `EXPIRED` listing therefore shows that message until a renewal story exists.
2. **Refund dedupe key** is `listingId:LISTING_REFUND_DUE:refund`, not the payment id (a rejected listing is final, so one refund per listing). `PaidPlanFee.paymentId` is returned but not used for the key.
3. **Final-rejection message** has no review reason (the story table has none); the reason appears in the "needs changes" messages.
4. **SMS text** is the title and body; the separate shortened-reason SMS text from the plan was not needed because no SMS carries a reason.
5. Existing tests in `listing_submitted_test.dart` were updated for the new "We will notify you if any action is required" text (English and Hindi); the test that said the page never promises a notification was replaced.
6. New backend contracts: `ListingOwnerLookupService` (listing module), `ListingPlanFeeLookupService` and `PaidPlanFee` (payment module), `NotificationPreferences` (notification module).
7. `AccountEventNotificationListener` uses the plain `@Transactional` dispatcher in an AFTER_COMMIT callback, which may not persist when its event is published inside a transaction. Not changed here; worth a separate check.
