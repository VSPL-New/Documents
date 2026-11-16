# US-132 - Block and Report User: QA Testing Guide

**Sprint 4 · Communication & Negotiation**

Manual test cases for blocking and unblocking a user, the Blocked users page, and reporting a user. The backend is
checked with `curl` and SQL; the app is checked on the seller profile and in Profile > Account.

> **What ships:** `PUT` and `DELETE /api/v1/users/{userId}/block`, `GET /api/v1/users/me/blocks`,
> `POST /api/v1/reports`; migration `V32` (`user_blocks`, `communication_reports`); the Admin setting
> `REPORTS_PER_DAY` (backend). In the app: Block user and Report user on the seller profile, and Profile > Account >
> Blocked users (mobile). `BlockService.requireNotBlocked` is the guard that chat, calls and offers will call.
> **Not in this story:** the chat menu, the read-only chat banner and composer (US-013); reporting a thread, message or
> call (US-013, US-014: until then these targets answer 404); the Admin review screen (US-057, US-055); penalties
> (US-051); an Admin screen for `REPORTS_PER_DAY` (US-116). The `ERROR_BLOCKED` refusal has no endpoint to test until
> US-069 and US-013 use the guard; it is covered by the automated tests (section G).

| Setting | Value |
|---|---|
| Backend base URL | `http://localhost:8080` |
| Endpoints | `PUT /api/v1/users/{id}/block` (204, repeat is harmless), `DELETE` (204, repeat is harmless), `GET /api/v1/users/me/blocks?page=0&size=20` (newest first; size 1 to 50), `POST /api/v1/reports` (201 `{reportId}`) |
| Limit | `REPORTS_PER_DAY`, default 10, allowed 1 to 50, a rolling 24 hours from the first report |
| Error codes | `ERROR_INVALID_BLOCK` (400), `ERROR_INVALID_REPORT_REASON` (400), `USER_NOT_FOUND` (404), `REPORT_TARGET_NOT_FOUND` (404), `RATE_LIMIT_EXCEEDED` (429); `ERROR_BLOCKED` (403, from the guard) |
| Reasons | `SPAM`, `HARASSMENT`, `SCAM_OR_FRAUD`, `INAPPROPRIATE_CONTENT`, `OFFENSIVE_BEHAVIOUR`, `SHARING_CONTACT_DETAILS`, `OTHER` |
| Known gaps | Hindi texts need native-speaker review; thread, message and call reports and the read-only chat arrive with US-013 and US-014 |

---

## Prerequisites

1. Backend, PostgreSQL and Redis running; the app running against it (see the US-011 guide).
2. Three `ACTIVE` accounts, each with an access token: `$ME`, `$OTHER` (give them a display name, for example "Asha K")
   and `$THIRD`. Note their user ids as `ME_ID`, `OTHER_ID` and `THIRD_ID`.
3. Handy variables:

```bash
B="localhost:8080/api/v1"
HM="Authorization: Bearer $ME"
HO="Authorization: Bearer $OTHER"
HT="Authorization: Bearer $THIRD"
```

---

## A. Block, list and unblock (AC1, AC3)

| # | Steps | Expected |
|---|---|---|
| A1 | `curl -i -X PUT -H "$HM" $B/users/$OTHER_ID/block` | 204. |
| A2 | Repeat A1 | 204 again; `SELECT count(*) FROM user_blocks WHERE blocker_id = '<ME_ID>'` is still 1. |
| A3 | `curl -H "$HM" "$B/users/me/blocks"` | `data.items` has `OTHER` with `userId`, `displayName` ("Asha K") and `blockedAt`; `total` 1; `hasNext` false. |
| A4 | `curl -H "$HO" "$B/users/me/blocks"` and the same with `$HT` | Both lists are empty: the blocked person and everyone else never see your list. |
| A5 | `curl -i -X DELETE -H "$HM" $B/users/$OTHER_ID/block`, twice | 204 both times; the list is empty. |
| A6 | Block a user who has no display name | The list shows "ValueX user" for them. |
| A7 | Block yourself: `curl -i -X PUT -H "$HM" $B/users/$ME_ID/block` | 400 `ERROR_INVALID_BLOCK`; nothing stored. |
| A8 | Block an unknown id (`00000000-0000-0000-0000-000000000000`) | 404 `USER_NOT_FOUND`. |
| A9 | Set a user's status to `CLOSED` in the database and block them | 404 `USER_NOT_FOUND`. |
| A10 | Block five users, then `curl -H "$HM" "$B/users/me/blocks?page=0&size=2"` and `page=1` and `page=2` | Pages of 2, 2 and 1; `hasNext` true, true, false; `total` 5; newest block first. |
| A11 | Request without a token | 401. |
| A12 | Try to insert a self block in SQL: `INSERT INTO user_blocks VALUES ('<id>','<id>')` | Refused by the database CHECK. |

## B. Reports (AC4, AC5)

| # | Steps | Expected |
|---|---|---|
| B1 | `curl -i -X POST -H "$HM" -H "Content-Type: application/json" -d '{"targetType":"USER","targetId":"'$OTHER_ID'","reason":"HARASSMENT","details":"rude messages"}' $B/reports` | 201 `{"data":{"reportId":"..."}}`. A row exists with `reporter_id` = me, `reported_user_id` = other, `target_type` USER, `source` USER, `status` OPEN. |
| B2 | Repeat B1 | 201 with the same `reportId`; still one OPEN row for this reporter and target. |
| B3 | `UPDATE communication_reports SET status = 'CLOSED' WHERE reporter_id = '<ME_ID>'`, then repeat B1 | A new report with a new id: a closed report no longer blocks a new one. |
| B4 | Reason `RUDE` | 400 `ERROR_INVALID_REPORT_REASON`. |
| B5 | `details` of 501 characters | 400; nothing stored. |
| B6 | Report with no `details`, and with `details` containing only spaces | 201; `details` is empty in the row. |
| B7 | Report yourself (`targetId` = your id) | 404 `REPORT_TARGET_NOT_FOUND`. |
| B8 | Report an unknown user id | 404 `REPORT_TARGET_NOT_FOUND`. |
| B9 | Report with `targetType` `THREAD` (any id) | 404 `REPORT_TARGET_NOT_FOUND` until US-013 adds threads. |
| B10 | Report with `targetType` `WHATEVER` | 400 (not a valid type). |
| B11 | Is there any endpoint that returns reports to a user? | No: reports are write-only for users. |
| B12 | Report as `$HO` the user `$THIRD` | 201; the reporter's id is taken from the token, never from the body. |

## C. Report limit and the Admin setting (rules)

| # | Steps | Expected |
|---|---|---|
| C1 | `SELECT setting_value FROM platform_settings WHERE setting_key = 'REPORTS_PER_DAY'` | `10`. |
| C2 | As one user, send ten different reports (ten different target users), then an eleventh | The first ten return 201; the eleventh returns 429 `RATE_LIMIT_EXCEEDED`; nothing stored for it. |
| C3 | `UPDATE platform_settings SET setting_value = '2' WHERE setting_key = 'REPORTS_PER_DAY'`, wait for the settings cache (about a minute) or restart the backend, use a fresh user | The third report in 24 hours returns 429. |
| C4 | Set `REPORTS_PER_DAY` to `0` or `100` or `abc` | The backend keeps working and uses the default 10; a warning is logged and `settings.invalid{key="REPORTS_PER_DAY"}` counts up. |
| C5 | Stop Redis and send a report | The report is accepted (the limit cannot be checked, so it is allowed) and a warning is logged. |

## D. In the app (AC1, AC3, AC4)

| # | Steps | Expected |
|---|---|---|
| D1 | Open another user's seller profile (listing details > seller) | A "more options" menu (three dots) is in the header. |
| D2 | Open your own seller profile | There is no menu. |
| D3 | Menu > Block user | A dialog "Block this user?" explains what changes (no messages, calls or offers; existing orders and accepted prices stay; unblock any time from Profile > Blocked users) with Cancel and Block. |
| D4 | Cancel | Nothing is blocked. |
| D5 | Block | A message "User blocked"; `user_blocks` has the row. |
| D6 | Turn on airplane mode and try Block | "Unable to block this user. Try again"; nothing stored. |
| D7 | Menu > Report user | A sheet "Report this user" with seven reasons, an optional details box with a 0/500 counter and Submit report (off until a reason is chosen). |
| D8 | Choose Spam, type details, Submit report | The sheet closes and a message "Thanks. We've received your report" shows; the row exists. |
| D9 | Report the same user again | The same thanks message; still one OPEN row. |
| D10 | Submit when the daily limit is used up | The sheet stays open with "You've reached today's report limit. Try again tomorrow"; no thanks message. |
| D11 | Submit with no network | "Unable to send your report. Try again"; the button works again and the second try succeeds. |
| D12 | Dismiss the sheet by tapping outside | Nothing is sent. |
| D13 | Profile > Account > Blocked users | The page lists the user you blocked, newest first, each with Unblock. |
| D14 | Tap Unblock | The row disappears at once and "User unblocked" shows; `user_blocks` no longer has the row. |
| D15 | Unblock with no network | The row comes back and "Unable to unblock this user. Try again" shows. |
| D16 | Open the page with nobody blocked | "You haven't blocked anyone" with a short explanation. |
| D17 | Open the page with no network | An error with Retry; Retry loads the list when the network is back. |
| D18 | Block more than 20 users and scroll the page | The next page loads at the end; a failed page load shows "Unable to load more users. Try again". |
| D19 | Pull down on the list | The list reloads. |

## E. Accessibility and language (rules)

| # | Steps | Expected |
|---|---|---|
| E1 | Turn on a screen reader on Blocked users | The title is read as a heading; each Unblock reads "Unblock {name}"; targets are at least 48 dp. |
| E2 | Report sheet with a screen reader | Reasons read as selectable choices with their selected state; the error message is announced when it appears. |
| E3 | Set the phone to Hindi and open the menu, dialog, sheet and Blocked users | All texts are in Hindi (marked for native-speaker review before release). |
| E4 | Set text size to 200 percent on a small phone | Nothing overflows on Blocked users or the report sheet; Submit stays reachable. |

## F. Database checks

| # | Check | Expected |
|---|---|---|
| F1 | `SELECT version, success FROM flyway_schema_history WHERE version = '32'` | One row, success. |
| F2 | `\d user_blocks` and `\d communication_reports` | The primary key, the self-block CHECK, the target, reason, source and status CHECKs and the partial unique index `uq_reports_open_per_target` are present. |
| F3 | Insert two OPEN reports for the same reporter, target type and target id | The second is refused by the unique index. |
| F4 | Insert a report with reason `RUDE` | Refused by the CHECK. |

## G. Automated tests

```bash
# backend (unit tests; the integration test needs Docker)
mvn test -Dtest='BlockServiceTest,ReportServiceTest,UserReportTargetResolverTest,BlockControllerTest,ReportControllerTest,ReportReasonTest,CommunicationReportRepositoryTest,ParticipantDirectoryAdapterTest,CommunicationSettingTest,PlatformSettingsServiceTest'
mvn test -Dtest=BlockAndReportIntegrationTest     # real PostgreSQL: constraints, privacy, limit, concurrent duplicates

# mobile
flutter test test/features/communication_safety test/features/profile
dart format lib test && flutter analyze --fatal-infos
```

The integration test also proves the guard: a blocked pair is refused in both directions with `ERROR_BLOCKED` and
"You cannot contact this seller", an unrelated pair is not, and unblocking lifts it.

## Acceptance criteria map

| Criterion | Cases |
|---|---|
| AC1 block and unblock, idempotent, never told | A1 to A5, D3 to D5, D14 |
| AC2 `ERROR_BLOCKED` either way, no hint of who blocked | Automated tests (section G); endpoints arrive with US-069 and US-013 |
| AC3 Blocked users page | A3, A4, A10, D13 to D19 |
| AC4 report, one open report per reporter and target, limit | B1 to B12, C1 to C5, D7 to D12 |
| AC5 evidence hold on a report | The hold port is a no-op until US-016; the call is verified by the unit tests |
| AC6 read-only thread after a block | `UserBlockedEvent` and `UserUnblockedEvent` are published; US-013 consumes them |
| AC7 price agreements and orders untouched | Nothing in this story touches them |
