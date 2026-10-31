# US-115: Listing Lifecycle Notifications — Implementation Plan

## 1. Header

| Field | Value |
|---|---|
| Story | US-115 Listing Lifecycle Notifications |
| Sprint | Sprint 2 — Seller Listing Creation |
| Story points | 3 (see Open Gap 1: the full story waits for events that US-117, US-008, US-009 and US-084 publish) |
| Repos | valuex-backend, valuex-mobile |
| Dependency | US-077 (notification module, done), US-089 (`ListingStatusChangedEvent`, done). The events behind five of the eight messages come from US-117, US-009 and US-084, which are not built yet |

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
- Implementation plans of US-089, US-009 and US-084: which events they publish for this story (`ListingStatusChangedEvent` exists; the payment-succeeded, payment-failed and refund-started events and `ListingReviewDecidedEvent` are planned, not built).

Key facts from the code today:
- `Notification` has no `params` column; `NotificationDispatchRequest` has no params or dedupe key; the dispatcher always inserts a new row.
- `NotificationResponse` returns `eventType`, `title`, `body`, `deepLink`; the app shows the server's title and body text and has no per-event localization yet.
- The app opens only `/profile` and `/profile/account-security` from a deep link (`notification_deep_links.dart`); other links show "coming soon". There is no listing details page yet (US-012). Item Details and plan selection are routes that need a listing id passed as an argument.
- `AccountContactLookupService` gives mobile and email by user id; the listing gives `sellerId` and `title`.
- Listing actions from the state machine: `PUBLISH`, `EXPIRE`, `REMOVE`, `REQUEST_REVISION`, `REJECT`, `PAYMENT_FAIL`.

Key design decisions:
- One new listener, `ListingEventNotificationListener`, in the notification module, same pattern as `AccountEventNotificationListener`; it dispatches through `NotificationDispatcher` and never calls the listing services.
- Add nullable `params` (JSONB) and a unique `dedupe_key` (listing id, event type, attempt) to `notifications`; a duplicate event is ignored by catching the unique violation, inside the dispatch transaction.
- The server still stores English `title` and `body` (so email, SMS and old app versions work); the app uses `eventType` and `params` to show the Hindi or English text from the ARB files.

## 4. Implementation Steps

Stage 1 can be built now. Stage 2 is wired when the producing stories publish their events; each is a small addition to the listener.

### Database Migration (`valuex-backend`)
- [ ] Next free Flyway number after `V18` (see Open Gap 3): add `notifications.params JSONB NULL` and `notifications.dedupe_key VARCHAR(160) NULL` with a unique index on `dedupe_key` where it is not null.

### Backend — Notification module
- [ ] Add `params` and `dedupeKey` to `Notification`, `NotificationDispatchRequest` and `NotificationResponse` (the response gains `params`; existing fields unchanged).
- [ ] `NotificationDispatcher.dispatch`: when `dedupeKey` is set and a row with that key exists, return it without sending SMS or email (checked before insert; the unique index is the final guard for concurrent duplicates).
- [ ] `ListingNotificationCopy` (a small class or enum): per `eventType` the English title, body template, priority, channels and deep link; fills `{title}`, `{reason}`, `{n}`, `{amount}`; shortens the listing title (for example 60 characters), the reason for SMS, strips markup and control characters; refund sentence only when an amount is present.
- [ ] `ListingEventNotificationListener` (`@TransactionalEventListener(AFTER_COMMIT)`):
  - Stage 1, from `ListingStatusChangedEvent`: `toState PUBLISHED` → `LISTING_PUBLISHED`; `toState EXPIRED` → `LISTING_EXPIRED`; `toState REMOVED_BY_ADMIN` → `LISTING_REMOVED_BY_ADMIN` (in-app + email, link to support); other transitions give nothing.
  - Stage 2, when their events exist: payment succeeded for `LISTING_PLAN` or the zero-price handler (US-009) → `LISTING_UNDER_REVIEW`; payment failed (US-009/US-117) → `LISTING_PAYMENT_FAILED`; `ListingReviewDecidedEvent` (US-084) with attempt n → `LISTING_REVISION_REQUIRED` (n of 3, reason) or `LISTING_REJECTED_FINAL` (amount when paid); refund-started (US-009) → `LISTING_REFUND_DUE` with amount.
  - Resolve seller, title and contact (`ListingRepository` read through a small lookup interface in the listing module, `AccountContactLookupService`); skip and log when the listing or seller is gone. A missing email never stops the in-app row.
- [ ] Change the existing account copy from "JustQlic" to "ValueX" as the story asks (Open Gap 4).
- [ ] Deep links: `/listing/{listingId}` (published), `/sell/details?listingId={id}` (revision), `/sell/plan?listingId={id}` (payment failed, expired renew), `/support` (removed).

### Mobile (`valuex-mobile`)
- [ ] `AppNotification` reads `params`; a mapper turns `eventType` + `params` into the localized title and body (English and Hindi ARB strings for all eight types, title shortened and quotes kept as text); unknown types and old rows fall back to the server's text.
- [ ] Icons for the new types in `notification_presentation.dart`; action-needed types use the alert colour.
- [ ] `notification_deep_links.dart`: open Item Details and plan selection with the listing id from the link; the listing details and support links stay "coming soon" until US-012 and support exist.
- [ ] Hindi strings go in `app_hi.arb`; they need native-speaker review before release (story).

### Documentation
- [ ] Add the US-115 part to the Sprint 2 LLD (Open Gap 2) and `Documents/Manual Testing Guides/US-115-Testing-Guide.md` after implementation.

## 5. Test Plan

Target above 90 % coverage for new code.

Unit tests (backend)
- [ ] `ListingNotificationCopy`: every event type gives the right title, body, priority, channels and link; long, quoted, markup-bearing and non-Latin titles; long reason in app and shortened for SMS; refund sentence present with an amount and absent without.
- [ ] Listener: `PUBLISHED`, `EXPIRED` and `REMOVED_BY_ADMIN` notify; other transitions do not; the dispatch happens after commit only; listing or seller missing is skipped and logged; missing email still creates the in-app row.
- [ ] Dispatcher: same dedupe key twice gives one row and one email or SMS; a channel failure does not roll back the row; no key keeps the old behaviour (existing US-077 tests still pass).
- [ ] Stage 2 handlers (when added): attempt 1, 2 and 3 messages, paid and free plan, payment failed, refund due.

Integration tests (Testcontainers)
- [ ] Migration applies; a real `ListingStatusChangedEvent` to `PUBLISHED` creates one notification with `params`, priority and deep link; the event published twice gives one row; `GET /api/v1/notifications` returns it with `params`, newest first, unread marked.
- [ ] Only the owner sees it (IDOR); 90-day retention job still removes old rows.

Mobile tests
- [ ] Localized title and body for each type in English and Hindi; fallback for an unknown type and for a row without `params`.
- [ ] Tapping opens Item Details or plan selection with the right listing; unbuilt targets show "coming soon".
- [ ] Notifications page lists them under the Listings tab; accessibility guidelines for the new rows and at 2x text size.

## 6. Validation Checklist

- [ ] Each of the eight messages exists with the story's wording, channels and priority (Stage 1 events work; Stage 2 events listed as pending until their producers exist).
- [ ] One event gives one notification, also when delivered twice or re-run.
- [ ] Final rejection mentions a refund only for a paid plan.
- [ ] No card, bank or Aadhaar data, no HTML, titles and reasons are plain text and shortened where needed.
- [ ] SMS and email failures never block the listing flow and are logged as `ERROR_NOTIFICATION_FAILED`.
- [ ] Action-needed messages are always in the in-app history, whatever the preferences (US-087 not built; keep a single place to apply them later).
- [ ] The app shows Hindi or English from `eventType` and `params`; older app versions still show the server text.
- [ ] A notification for a deleted listing does not fail the event.
- [ ] Checkstyle, full tests, coverage and SonarQube pass before push.

## 7. Open Gaps / Questions

1. **Build now or after US-009 and US-084? (needs your decision.)** Only `ListingStatusChangedEvent` exists today. The events for "under review", "payment failed", "needs changes (review n of 3)", "final rejection" and "refund due" are published by US-117, US-009 and US-084, which are planned but not built, so five of the eight messages cannot be triggered yet. The sprint plan lists only US-077 and US-089 as dependencies, but the other plans assume US-115 is built last. Options: (a) build Stage 1 now (framework, params, dedupe, mobile rendering, published, expired and removed) and add the other five with their producers; (b) build the whole story after US-009 and US-084. I recommend (b) for a single clean delivery, or (a) if you want the framework reviewed early. The earlier suggestion that this story is small and independent holds only for (a).
2. **No LLD section for US-115.** Add one (listener, `params`, dedupe key, copy table, deep links) to the Sprint 2 LLD; confirm it is wanted before implementation.
3. **Migration number.** `V19` is planned for US-117 and `V20` for US-008. If US-115 is built first it takes the next free number and the others move; if built last it is `V21`. Decide when the order is fixed.
4. **Brand name.** The story says to change the account copy from "JustQlic" to "ValueX", but the app, taxonomy files and user agent still say JustQlic. Confirm the name to use.
5. **Deep link targets.** There is no listing details page (US-012), and Item Details and plan selection need a listing id as an argument. Confirm the link formats in step 4, and whether tapping "listing is live" may show "coming soon" until US-012.
6. **Preferences.** US-087 is not built. Confirm that messages are sent unconditionally for now.
7. **Final-rejection SMS.** The story leaves open whether it is wanted; the plan sends it as written until you decide.
8. **Email and SMS language.** English only until a language preference is stored on the server (story, Open).
9. **Push** is not built; medium-priority messages are in-app only until push exists (US-077).
10. **Hindi wording** needs a native-speaker review before release.
11. **"Refund issued"** is added when the refund step is built (story); not in this story.
12. **Follow-ups from US-009 (2026-10-31).** (a) US-009's "listing under review" page deliberately promises no notification; when this story sends the notifications, change its text to "We will notify you if any action is required" (English and Hindi). (b) The migration numbers moved: US-008 took `V20`, US-084 plans `V21` and US-009 `V22`, so this story takes `V23` if built last. (c) A late payment flagged for refund review by US-009 and the refund-due event both produce events this story can notify on.

---

**Status:** Draft — parked (2026-10-30) until US-009 and US-084 are built, so that all eight messages can be delivered together (Open Gap 1, option b).
