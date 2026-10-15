# US-077 — Critical Event Notifications: QA Testing Guide

**Sprint 1 · Identity & User Management**

Manual test cases for the notification pipeline (account created, Aadhaar verified, and critical
account-state changes), using Swagger UI + console log inspection + SQL against a local dev
environment.

> **What this story actually ships:** notifications for **account lifecycle events only** —
> account created, Aadhaar verified, and state transitions to UNDER_REVIEW/SUSPENDED/BANNED. Every
> notification always gets an in-app row (`GET /api/v1/notifications`); SMS/email are additionally
> attempted per the channel table below, via **mock adapters that only log to the console** — no
> real SMS/email provider is wired up. Push notifications, order/payment/cart/dispute/message
> events, and notification preferences are **not built** (see Not Testable Yet). See
> `Documents/LLD/Sprint-1-Identity-User-Management-LLD.md` §6.6-§6.9 for the full design.

| Setting | Value |
|---|---|
| Base URL | `http://localhost:8080` |
| Swagger UI | `http://localhost:8080/swagger-ui.html` (tag: **Notifications**) |
| Endpoints under test | `GET /api/v1/notifications`, `PATCH /api/v1/notifications/{id}/read`, `PATCH /api/v1/notifications/read-all` |
| Retention job | `NotificationRetentionCleanupJob` — daily cron `0 0 3 * * *`, deletes rows older than 90 days |

---

## Channel Table (What Fires For What)

| Event | Trigger | eventType | Channels | Priority |
|---|---|---|---|---|
| Account created | Registration reaches ACTIVE (skip Aadhaar **or** complete Aadhaar) | ACCOUNT_CREATED | In-app + SMS | HIGH |
| Aadhaar verified | Aadhaar verification completes (fires alongside Account created, same call) | AADHAAR_VERIFIED | In-app only | MEDIUM |
| Account flagged for review | Admin/system transitions account to UNDER_REVIEW (US-088, no endpoint yet — see that story's testing guide) | ACCOUNT_UNDER_REVIEW | In-app + SMS | HIGH |
| Account suspended | Transition to SUSPENDED | ACCOUNT_SUSPENDED | In-app + SMS + Email | HIGH |
| Account banned | Transition to BANNED | ACCOUNT_BANNED | In-app + SMS + Email | HIGH |

---

## Test Scenarios Overview

| TC | Scenario | Expected Result |
|---|---|---|
| TC-001 | Registering and skipping Aadhaar creates an ACCOUNT_CREATED notification | Row appears in `GET /notifications`; console logs a mock SMS |
| TC-002 | Completing Aadhaar verification creates two notifications | ACCOUNT_CREATED and AADHAAR_VERIFIED both appear |
| TC-003 | Suspending an account creates a notification on all three channels | Row's SMS + Email both logged to console |
| TC-004 | Non-critical state transitions do not notify | No new row for e.g. CLEAR_REVIEW back to ACTIVE |
| TC-005 | Unread count header decreases after marking read | `X-Unread-Notifications` reflects the change |
| TC-006 | Marking an already-read notification read again is a no-op | 200, no error, `readAt` unchanged |
| TC-007 | Cannot mark another user's notification as read | 404 |
| TC-008 | A failed SMS/email send doesn't block notification creation | Row still appears; only an ERROR log line, no user-facing error |
| TC-009 | Pagination and default page size | `GET /notifications` with no params returns 20 per page |
| TC-010 | Mark all notifications read | `200`, `markedRead` equals the unread count, `X-Unread-Notifications: 0` |
| TC-011 | Mark all read with nothing unread | `200`, `markedRead: 0` |
| TC-012 | Mark all read only affects the caller | Another user's unread rows stay unread |

---

## TC-001 — Account Created Notification (Skip-Aadhaar Path)

**Steps:**
1. Register and verify mobile/email OTP through to `IDENTITY_VERIFICATION_PENDING` (see
   `US-001-Testing-Guide.md`).
2. `POST /api/v1/auth/aadhaar/skip` (Bearer token from step 1).
3. Watch the console log for:
   ```
   [DEV-MOCK] SMS notification for mobile=<mobile> message=Welcome to ValueX!: Your account has been created successfully.
   ```
4. `GET /api/v1/notifications` (Bearer token from step 1).

**Expected:** one row with `eventType: "ACCOUNT_CREATED"`, `title: "Welcome to ValueX!"`,
`deepLink: "/profile"`, `read: false`. Response header `X-Unread-Notifications: 1`.

---

## TC-002 — Account Created + Aadhaar Verified (Complete-Aadhaar Path)

**Steps:** Follow `US-001-Testing-Guide.md`'s Aadhaar verification steps (sandbox provider) instead
of skipping, then `GET /api/v1/notifications`.

**Expected:** **two** rows — `ACCOUNT_CREATED` (In-app + SMS) and `AADHAAR_VERIFIED` (In-app only,
no SMS log line for this second one). `X-Unread-Notifications: 2`.

---

## TC-003 — Suspension Notifies All Three Channels

**Goal:** Confirm HIGH-priority state-change events reach SMS and Email.

**Steps:**
1. Register a test user through to ACTIVE.
2. Suspend directly via SQL (no admin endpoint exists yet — see `US-088-Testing-Guide.md`):
   ```sql
   UPDATE users SET status = 'SUSPENDED', suspension_lifted_at = now() + interval '7 days'
   WHERE mobile = '9000000050';
   ```
   This bypasses `UserStateService`, so **no `UserStateChangedEvent` fires this way** — the console
   log / notification row will not appear from a raw SQL update. To actually exercise the
   notification path, suspend through code instead: temporarily call
   `userStateService.suspend(userId, actorId, reason)` from a scratch test or breakpoint, since no
   HTTP endpoint exists yet (documented gap, `US-088-Testing-Guide.md`'s TC list). Alternatively,
   run `UserStateServiceTest`/`AccountEventNotificationListenerTest` directly — they exercise this
   exact path end-to-end at the unit level.
3. Watch for both:
   ```
   [DEV-MOCK] SMS notification for mobile=<mobile> message=Account Suspended: Your account has been suspended. Contact support for details.
   [DEV-MOCK] Email notification for email=<email> subject=Account Suspended body=Your account has been suspended. Contact support for details.
   ```

**Expected:** a notification row with `eventType: "ACCOUNT_SUSPENDED"`, `deepLink: "/support"`.

---

## TC-004 — Non-Critical Transitions Do Not Notify

**Goal:** Confirm CLOSED, RESTRICTED, and "back to ACTIVE" transitions are silent (not in the AC's
critical-event list).

**Steps:** Using `UserStateService.clearReview(userId, actorId, reason)` (UNDER_REVIEW → ACTIVE) or
`.close(...)` (ACTIVE → CLOSED), confirm no new `Notification` row is created and no SMS/email log
line appears, even though `UserStateChangedEvent` still fires (and `account_status_history` still
gets its row — only the notification side is silent).

---

## TC-005 — Unread Count Decreases After Marking Read

**Steps:**
1. `GET /api/v1/notifications` — note `X-Unread-Notifications` and the `id` of the first row.
2. `PATCH /api/v1/notifications/{id}/read`.
3. `GET /api/v1/notifications` again.

**Expected:** step 3's `X-Unread-Notifications` is one less than step 1's. The marked row now shows
`"read": true` in the list response.

---

## TC-006 — Marking an Already-Read Notification Is Idempotent

**Steps:** Repeat `PATCH /api/v1/notifications/{id}/read` a second time on the same `id` from TC-005.

**Expected:** `200 OK`, same response shape, no error. `X-Unread-Notifications` does not decrease
again (it was already excluded).

---

## TC-007 — Cannot Mark Another User's Notification as Read

**Steps:** Using User A's Bearer token, `PATCH /api/v1/notifications/{id}/read` where `{id}`
belongs to User B.

**Expected response (404 Not Found):**
```json
{
  "success": false,
  "error": {
    "code": "NOT_FOUND",
    "message": "Notification not found"
  }
}
```

---

## TC-008 — Channel Failure Doesn't Block Notification Creation

**Not directly triggerable via the mock adapters** (they never throw). Confirmed instead by
`NotificationDispatcherTest.shouldPersistNotificationEvenWhenSmsChannelThrows` and
`.shouldStillSendEmailWhenSmsChannelFails` — both assert the notification row is still created and
saved when a channel adapter throws, and that the failure is logged as
`ERROR_NOTIFICATION_FAILED channel=... userId=... reason=...` rather than surfaced to the caller.

---

## TC-009 — Pagination Defaults

**Steps:** `GET /api/v1/notifications` with no query parameters, having created more than 20
notifications for the test user.

**Expected:** response `data` array has at most 20 entries; `metadata.size: 20`, `metadata.page: 0`,
`metadata.totalElements` reflects the real count. Use `?page=1` for the next page.

---

## TC-010 — Mark All Notifications Read

**Steps:**
1. `GET /api/v1/notifications` — note `X-Unread-Notifications` (for example `3`).
2. `PATCH /api/v1/notifications/read-all`.
3. `GET /api/v1/notifications` again.

**Expected response (200 OK):**
```json
{ "success": true, "data": { "markedRead": 3 } }
```
Step 3: `X-Unread-Notifications: 0`, every row has `"read": true`, and each previously unread row has a `readAt`.

---

## TC-011 — Mark All Read With Nothing Unread

**Steps:** `PATCH /api/v1/notifications/read-all` a second time.

**Expected:** `200 OK` with `{ "markedRead": 0 }`; no error and no `readAt` changes.

---

## TC-012 — Mark All Read Only Affects the Caller

**Steps:** With User A and User B both holding unread notifications, call `PATCH /read-all` as User A, then `GET /notifications` as User B.

**Expected:** User B's `X-Unread-Notifications` is unchanged.

---

## Mobile App (Flutter) — Notifications

Manual test cases for the Notifications page in `valuex-mobile` against the local backend. Automated coverage is in `test/features/notifications/notifications_test.dart`.

| Setting | Value |
|---|---|
| Run | `flutter run -d <device> --dart-define-from-file=config/dev_local.json` |
| Sign in | A registered `ACTIVE` account (mock OTP is in the backend log, search for `DEV-MOCK`) |
| Open | Home bell, or Profile > Account > Notifications |
| Endpoints used | `GET /notifications`, `PATCH /notifications/{id}/read`, `PATCH /notifications/read-all` |
| Sample data | Only account events exist, so insert other types with SQL (see below) to see every tab and a second page |

```sql
INSERT INTO notifications (user_id, status, event_type, title, body, deep_link, priority, read)
VALUES ('<user-id>', 'SENT', 'ORDER_DELIVERED', 'Order Delivered', 'Your order has been delivered.', NULL, 'HIGH', false),
       ('<user-id>', 'SENT', 'MESSAGE_RECEIVED', 'New Message', 'You have a message.', NULL, 'MEDIUM', false),
       ('<user-id>', 'SENT', 'LISTING_BOOSTED', 'Listing Boosted', 'Your listing is boosted.', NULL, 'MEDIUM', true),
       ('<user-id>', 'SENT', 'PRICE_DROP', 'Price Drop Alert', 'A price dropped.', NULL, 'LOW', true);
```

| TC | Scenario | Expected Result |
|---|---|---|
| M-TC-001 | Home bell count | Bell announces "Notifications, {n} unread" and shows a dot while `n` > 0; no dot at 0 |
| M-TC-002 | Open the page | Title "Notifications", "{n} unread" (or "You're all caught up"), cards newest first with a relative time ("5 minutes ago", "2 hours ago", "3 days ago", then the date after a week) |
| M-TC-003 | Unread look | Unread cards have a tint, a left bar and a dot; a screen reader says "Unread" first |
| M-TC-004 | Alert colour | Under review, suspended and banned cards use a red icon tile; the others use the blue tile |
| M-TC-005 | Tabs | All plus one tab per category that has notifications (Account, Orders, Messages, Listings, Others); a tab with none is hidden, and with only one category there is no tab row |
| M-TC-006 | Filtering | Each tab lists only its category; All lists everything; an unknown event type is under Others |
| M-TC-007 | Open a notification | Tapping marks it read (count drops, tint goes) and follows its link: `/profile` opens the Profile tab, `/profile/account-security` opens Account Security |
| M-TC-008 | Link not built yet | `/support` shows "This is coming soon" and stays on the page; a notification with no link is only marked read |
| M-TC-009 | Mark all read | Every card turns read, the button disappears, "You're all caught up" shows, the Home bell and Profile row clear; `GET /notifications` shows `X-Unread-Notifications: 0` |
| M-TC-010 | Mark all read fails | Stop the backend, tap it: "Unable to mark all as read. Try again" and the list stays unread |
| M-TC-011 | Paging | With more than 20 rows, scrolling to the end loads the next page; stop the backend first to see "Unable to load more notifications" and Retry |
| M-TC-012 | Pull to refresh | A notification inserted in SQL appears after pulling down |
| M-TC-013 | Empty | A user with no rows sees "No notifications yet" |
| M-TC-014 | Backend down | The first load shows an error with Retry |
| M-TC-015 | Guest | Tapping the bell while signed out sends the user to Sign In |
| M-TC-016 | Language and large text | In Hindi the labels, tabs and times are Hindi (titles and text come from the backend, so stay in English); at the largest text size nothing is clipped or overlaps |
| M-TC-017 | Screen reader | Each card reads as one button (unread state, title, text, time); tabs say selected; the title is a heading |

---

## Not Testable Yet (Don't File as Bugs)

- **Push notifications** — no channel, no device-token registration, nothing to test.
- **Order/payment/cart/dispute/message notifications** — those modules don't exist until Sprint 4+.
- **Password-changed notifications** — not applicable; this auth model has no password.
- **Unknown-device-login notifications** — explicitly deferred to a future sprint per the LLD.
- **Notification preferences / opt-out** — that's US-087, not yet built. Every event notifies
  unconditionally.
- **Client-side grouping of rapid notifications** — a display concern, not a backend behavior.
- **Real SMS/email delivery** — both channels are mock/console-log only in this environment.

---

## Reset Between Tests

```sql
DELETE FROM notifications WHERE user_id = (SELECT id FROM users WHERE mobile = '<test mobile>');
```

---

## Error Reference

| HTTP | Error Code | Cause |
|---|---|---|
| 404 | `NOT_FOUND` | Notification doesn't exist or belongs to a different user (TC-007) |
