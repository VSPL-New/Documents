# US-115 — Listing Lifecycle Notifications: QA Testing Guide

**Sprint 2 · Seller Listing Creation**

Manual test cases for the notifications a seller gets after choosing a listing plan: under review, live, needs changes
(review n of 3), not approved after 3 reviews, refund being processed, payment unsuccessful, expired and removed. The app shows
them in English or Hindi from the event type and its values; email and SMS are English. The product name in all text is
**JustQlic**. The dummy gateway and the mock SMS and email providers are used; no money is charged and nothing is sent.

> **What ships:** migration `V23` (`notifications.params`, `notifications.dedupe_key`); `ListingEventNotificationListener`,
> `ListingNotificationCopy`, `NotificationPreferences`, `ListingOwnerLookupService`, `ListingPlanFeeLookupService`;
> `reviewKind` on `ListingReviewDecidedEvent`; `params` in `GET /api/v1/notifications`; in the app, localized listing messages,
> icons and alert colour, and opening Item Details and plan selection from a notification (the listing is loaded first), with a
> "Resubmit for review" action for a listing that needs changes.
> **Not in this story:** push notifications, email and SMS in Hindi, seller notification preferences (US-087), the listing
> details page (US-012, the "live" message shows "coming soon"), a support page, the "refund issued" message, renewing an expired
> listing, an expiry job and an admin console (expired and removed messages can only be produced by publishing the event).

| Setting | Value |
|---|---|
| Backend base URL | `http://localhost:8080` |
| Migration | `V23` (Flyway runs on start) |
| Providers | `NOTIFICATION_SMS_PROVIDER=mock`, `NOTIFICATION_EMAIL_PROVIDER=mock` (default): the text is written to the backend log |
| SMS switch | `NOTIFICATION_FINAL_REJECTION_SMS` (default `true`); keep `false` in production until the SMS template is approved |
| Review mode | `MODERATION_MANUAL_REVIEW_ENABLED=false` (default): a paid listing is approved at once. `true`: it waits for a decision |
| Error | `ERROR_NOTIFICATION_FAILED` is only logged, never shown, and never blocks the listing flow |

---

## Prerequisites

1. PostgreSQL and Redis from `valuex-backend/docker-compose.yml`; start the backend (`mvn spring-boot:run`).
2. An `ACTIVE` seller with Aadhaar verified and a token (`$TOKEN`), and a second seller (`$TOKEN_B`).
3. A complete draft of the seller with a cleared restricted check and a chosen plan (`US-008-Testing-Guide.md`). Note the
   listing id as `$LISTING` and the seller id as `$SELLER`.
4. The app on an emulator (`dev_android.json`), signed in as the seller.

Useful queries:

```sql
SELECT event_type, priority, title, deep_link, params, dedupe_key, read, created_at
FROM notifications WHERE user_id = '<seller id>' ORDER BY created_at DESC;
SELECT status FROM listings WHERE id = '<listing id>';
```

---

## Test cases: backend

| ID | Acceptance criterion / edge case | Steps | Expected |
|---|---|---|---|
| TC-001 | Migration | `SELECT version FROM flyway_schema_history WHERE version = '23';` | One successful row; `notifications.params` (jsonb) and `dedupe_key` exist; index `uq_notifications_dedupe_key` exists |
| TC-002 | Payment received: under review | Pay the plan with the dummy gateway (`US-009-Testing-Guide.md`, prerequisite 4) | A `LISTING_UNDER_REVIEW` row: medium priority, no deep link, `params` has `listingId`; text "Payment received. Your listing is under review and will be checked within a few hours." |
| TC-003 | Approved and published: live | Same payment (manual review off) | A `LISTING_PUBLISHED` row: medium priority, `deep_link` `/listing/<id>`, `params.title` is the listing title; text "Your listing \"<title>\" is now live. Buyers can find it." Newest first: live, then under review |
| TC-004 | Free plan | Make `BASIC` free (`US-009-Testing-Guide.md`, TC-005) and choose it | The same two rows (under review, live); no payment row |
| TC-005 | Notifications API | `GET /api/v1/notifications` as the seller | The rows come back newest first with `eventType`, `title`, `body`, `deepLink`, `params`, `priority`, `read`; unread count in the `X-Unread-Notifications` header |
| TC-006 | Only the owner sees them | `GET /api/v1/notifications` as seller B | None of seller A's rows; marking A's notification read as B gives 404 |
| TC-007 | Same event twice: one notification | Run the automated test `ListingNotificationIntegrationTest` (see below) | One row per event; the same event published twice gives one row |
| TC-008 | Plan payment fails | Choose a plan and simulate `FAILURE` | A `LISTING_PAYMENT_FAILED` row: medium priority, `deep_link` `/sell/plan?listingId=<id>` |
| TC-009 | Unpaid payment times out | Age the payment and run reconciliation (`US-117-Testing-Guide.md`) | A `LISTING_PAYMENT_FAILED` row (listing back at plan selection). Changing the plan before paying gives no message |
| TC-010 | Newer payment open | Fail a payment while a newer one for the same listing is pending | No `LISTING_PAYMENT_FAILED` row, because the listing did not move |
| TC-011 | Needs changes, review 1 or 2 | Manual review on; pay; reject the review with a reason (a developer calls `TrustSafetyReviewService.reject`, there is no endpoint) | A `LISTING_REVISION_REQUIRED` row: high priority, `params` has `title`, `reason`, `attempt` (1, then 2); text ends "Update it and resubmit (review 1 of 3). You will not be charged again."; email in the backend log; `deep_link` `/sell/details?listingId=<id>`; key `…:INITIAL:<attempt>` |
| TC-012 | Third review fails, paid plan | Reject the third review | A `LISTING_REJECTED_FINAL` row: "…was not approved after 3 reviews. Your plan fee of ₹<amount> will be refunded."; `params.amount`; email and SMS in the backend log; then a `LISTING_REFUND_DUE` row "Your refund of ₹<amount> for the listing plan is being processed." (in-app and email) |
| TC-013 | Third review fails, free plan | TC-004, manual review on, three rejections | `LISTING_REJECTED_FINAL` without a refund sentence and with no `amount`; no `LISTING_REFUND_DUE` row |
| TC-014 | SMS switch | Start with `NOTIFICATION_FINAL_REJECTION_SMS=false` and repeat TC-012 | The in-app row and email, but no SMS in the log |
| TC-015 | Edit review | Reject a review of an edited published listing (US-010) | `LISTING_REVISION_REQUIRED` without "(review n of 3)" and without `params.attempt` |
| TC-016 | Expired and removed | Run the automated listener test (the events have no producer yet) | `LISTING_EXPIRED` (medium, in-app, link `/sell/plan?listingId=<id>`) and `LISTING_REMOVED_BY_ADMIN` (high, in-app and email, link `/support`, text "…was removed by JustQlic. Contact support for details.") |
| TC-017 | Long, quoted and non-Latin titles | Set a listing title of 200 characters, one with `"quotes"`, one with `<b>markup</b>`, one in Hindi, then publish | The text uses at most 60 characters followed by "…"; quotes stay as text; markup and control characters are removed; Hindi stays readable |
| TC-018 | Missing email | Remove the seller's email, then reject a review | The in-app row is still created; the email is skipped |
| TC-019 | Notification failure never blocks | Make the mock email provider throw | The listing still moves; `ERROR_NOTIFICATION_FAILED` appears in the log; the in-app row exists |
| TC-020 | Listing deleted before the message | Delete the listing between the event and the message | No error; "Listing not found, notification skipped" in the log |
| TC-021 | Plain text and no sensitive data | Read every row | No HTML, no card, bank or Aadhaar data |
| TC-022 | Retention | `NotificationRetentionCleanupJobTest` | Rows older than 90 days are still removed |
| TC-023 | Existing account notifications | Create an account | "Welcome to JustQlic!" as before |

---

## Test cases: app

Insert test notifications for the signed-in seller (replace the ids); each row also has a real producer, see the backend cases.

```sql
INSERT INTO notifications (user_id, status, event_type, title, body, deep_link, priority, params) VALUES
 ('<seller id>', 'SENT', 'LISTING_REVISION_REQUIRED', 'Your listing needs changes', 'server text',
  '/sell/details?listingId=<listing id>', 'HIGH',
  '{"listingId":"<listing id>","title":"Blue bike","reason":"Photos are blurry","attempt":1}'),
 ('<seller id>', 'SENT', 'LISTING_PAYMENT_FAILED', 'Payment unsuccessful', 'server text',
  '/sell/plan?listingId=<listing id>', 'MEDIUM', '{"listingId":"<listing id>"}'),
 ('<seller id>', 'SENT', 'LISTING_PUBLISHED', 'Your listing is live', 'server text',
  '/listing/<listing id>', 'MEDIUM', '{"listingId":"<listing id>","title":"Blue bike"}'),
 ('<seller id>', 'SENT', 'LISTING_REJECTED_FINAL', 'Listing not approved', 'server text', NULL, 'HIGH',
  '{"listingId":"<listing id>","title":"Blue bike","attempt":3,"amount":"49"}'),
 ('<seller id>', 'SENT', 'LISTING_REMOVED_BY_ADMIN', 'Listing removed', 'server text', '/support', 'HIGH',
  '{"listingId":"<listing id>","title":"Blue bike"}');
```

| ID | Steps | Expected |
|---|---|---|
| TC-A01 | Open **Notifications** (bell on Home or Profile) | The rows are under the **Listings** tab, newest first, unread marked; each has its icon; needs changes, not approved and removed use the alert colour |
| TC-A02 | Read the text in English | The text of the story: "Your listing "Blue bike" needs changes: Photos are blurry. Update it and resubmit (review 1 of 3). You will not be charged again.", "Your listing "Blue bike" was not approved after 3 reviews. Your plan fee of ₹49 will be refunded.", "…removed by JustQlic…"; the app uses its own text, not the "server text" |
| TC-A03 | Switch the app to Hindi | The same messages in Hindi, with the title, reason and amount filled in |
| TC-A04 | A row without `params` (old row), and an unknown `LISTING_*` type | The server's English text is shown |
| TC-A05 | Set the listing to `REVISION_REQUIRED` (`UPDATE listings SET status = 'REVISION_REQUIRED' WHERE id = '<listing id>';`, use a listing that was paid) and tap "needs changes" | The row is marked read; Item Details opens with the title, category, condition, description, price and category fields filled in; the button says **Resubmit for review** |
| TC-A06 | Change a field and tap **Resubmit for review** | The details are saved, the restricted item check runs, the review is requested again with no payment, and "Your listing is submitted" opens (it says "We will notify you if any action is required") |
| TC-A07 | In TC-A06 clear a required field | The button stays disabled with the usual hints |
| TC-A08 | In TC-A06 go offline before tapping | The error message appears; the page stays open with the typed values |
| TC-A09 | Set the listing to `PLAN_PAYMENT_FAILED` and tap "payment unsuccessful" | Plan selection opens for that listing with the plans; choosing one continues as in US-008 |
| TC-A10 | Tap "needs changes" or "payment unsuccessful" for a listing that is `PUBLISHED` | The message "This listing can no longer be changed here"; stay on the list |
| TC-A11 | Delete the listing, then tap one of them | "This listing is no longer available" |
| TC-A12 | Go offline and tap one of them | The usual network message; stay on the list |
| TC-A13 | Tap "your listing is live" and "listing removed" | "This is coming soon" (US-012, support) |
| TC-A14 | Tap "not approved" (no link) | Only marked read |
| TC-A15 | Open the "Listing submitted" page after a payment | The line under "Anything needed from you?" says "We will notify you if any action is required" (Hindi: आपसे किसी कार्रवाई की ज़रूरत होने पर हम आपको सूचित करेंगे।) |
| TC-A16 | Largest system text size, and a screen reader | No overflow; each row reads as unread, title, text, time |

---

## Running the automated tests

Backend (Docker must be running for the integration tests):

```bash
cd valuex-backend
mvn verify
mvn checkstyle:check
```

Only this story:

```bash
mvn test -Dtest='ListingNotificationCopyTest,ListingEventNotificationListenerTest,NotificationDispatcherTest,NotificationPreferencesTest,ListingOwnerLookupServiceTest,ListingPlanFeeLookupServiceTest,TrustSafetyReviewServiceTest,AccountEventNotificationListenerTest,NotificationControllerTest,ListingNotificationIntegrationTest'
```

`ListingNotificationIntegrationTest` needs Docker (Testcontainers); it covers TC-001, TC-003, TC-007, TC-016 and the case where the
event is published inside a transaction.

Mobile:

```bash
cd valuex-mobile
flutter gen-l10n
dart format lib test
flutter analyze
flutter test test/features/notifications test/features/listing
```

Results at hand-over (2026-11-01): backend `mvn clean verify` 1,296 tests, 0 failures, 114 skipped (Docker tests, no Docker on
the build machine), checkstyle clean; mobile `flutter test` 986 passed, `flutter analyze` no issues. The Hindi text is a draft that
needs native-speaker review before release.
