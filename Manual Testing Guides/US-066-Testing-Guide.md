# US-066 — Saved Searches and Alerts: Manual Testing Guide

**Sprint 3 · Discovery & Search**

Use this guide to validate saving a search, the Saved Searches screen, alerts on/off, deleting with undo, the daily
in-app digest and the alert deep link. The digest is **in-app only** (decision of 2026-11-09): there is no push, email or
SMS. Design: [Sprint 3 LLD, Part F and F.11](../LLD/Sprint-3-Discovery-Search-LLD.md); plan:
[US-066-Implementation-Plan.md](../US-Implementation-Plans/US-066-Implementation-Plan.md).

## Status and release gates

| Validation | Status |
|---|---|
| Backend source and automated tests (`mvn verify`: 2062 tests, checkstyle, JaCoCo gate) | Passed on the delivery branch |
| Backend Testcontainers tests against real PostgreSQL 16 and OpenSearch 2.17.1 (`SavedSearchIntegrationTest`, `OpenSearchBatchSearchIntegrationTest`) | Passed |
| Mobile source and automated tests (`flutter analyze --fatal-infos`, 1541 tests, 96.7% line coverage, gate 85%) | Passed on the delivery branch |
| SonarQube scan | **Pending** — it runs only on the Windows machine; run it there and record the result in both pull requests |
| Real iPhone check with the local test stack (cases marked *device*) | **Pending** — not done by the implementer |
| Android build and device checks | **Pending** — no Android SDK in the implementation environment |
| Hindi texts (screens and the digest) | Drafts — native-speaker review required before release |

## Prerequisites

1. `feature/US-066-saved-searches-alerts` checked out in `valuex-backend` and `valuex-mobile`. Flyway applies
   `V29__saved_searches.sql` on start (table `saved_searches` and four settings).
2. PostgreSQL, Redis and OpenSearch running (the local test stack, or `docker-compose`), with the search index filled
   (`POST /internal/v1/search/reindex`, see the backend README) or publish listings). At least two buyer accounts, **A** (saves searches) and **B**
   (publishes listings), both `ACTIVE`.
3. A goods category with facets (for example Smartphones, `CAT-0001`) and a Real Estate leaf (`CAT-0871`).
4. Handy settings (table `platform_settings`, key and value): `SAVED_SEARCH_MAX` (10), `SAVED_SEARCH_ALERT_MINUTE_OF_DAY`
   (540 = 09:00 Asia/Kolkata), `SAVED_SEARCH_ALERT_SAMPLE_TITLES` (3), `SAVED_SEARCH_ALERT_MIN_HOURS` (20). A change applies
   within about a minute (settings cache).

### Triggering the daily digest in a test environment

The job ticks every 15 minutes and sends once a day at the first tick at or after the Admin time. To test it safely:

1. Set `SAVED_SEARCH_ALERT_MINUTE_OF_DAY` to a minute that has already passed today in India time, for example `0`:
   `UPDATE platform_settings SET setting_value = '0' WHERE setting_key = 'SAVED_SEARCH_ALERT_MINUTE_OF_DAY';`
2. Delete today's Redis marker so the run is allowed: `DEL saved-search-alert:YYYY-MM-DD` (India date).
3. Start the backend with a one-minute tick: `-Dvaluex.search.saved-alerts.cron="0 * * * * *"` (or wait for the next quarter
   hour). The log shows `Saved-search alert run done: searches=… sent=…`.
4. To run it **again the same day**, delete the marker again (the repeat guard `SAVED_SEARCH_ALERT_MIN_HOURS` and the
   dedupe key still prevent a second message — that is test TC-013).
5. To make a search "older" so it has something new to announce, move its watermark back:
   `UPDATE saved_searches SET last_checked_at = now() - interval '2 days' WHERE id = '…';`

Reset the settings and the cron afterwards. Do not run the one-minute cron against a shared environment.

## Automated test subset

From `valuex-backend` (JDK 21, Colima/Testcontainers settings from the backend README):

```bash
mvn test checkstyle:check -Dtest='SavedSearch*Test,OpenSearchQueryBuilderTest,OpenSearchListingSearchAdapterTest,DiscoverySettingTest,GlobalExceptionHandlerTest'
mvn test -Dtest='SavedSearchIntegrationTest,OpenSearchBatchSearchIntegrationTest'   # needs Docker
mvn verify
```

From `valuex-mobile`:

```bash
dart run build_runner build --delete-conflicting-outputs && flutter gen-l10n
dart format lib test integration_test && flutter analyze --fatal-infos
flutter test test/features/saved_searches test/features/notifications/saved_search_notifications_test.dart --dart-define=SKIP_PIXEL_CONTRAST=true
flutter test --coverage --dart-define=SKIP_PIXEL_CONTRAST=true && tool/check_coverage.sh coverage/lcov.info 85
```

## Manual test cases

| ID | AC / edge case | Steps | Expected |
|---|---|---|---|
| TC-001 | AC1 — save | As A, search `iphone`, pick an L3 category, add a price range, a condition and a facet; tap **Save search** | Message "Search saved. You will get a daily alert about new items". In `saved_searches`, `criteria` holds `query`, `category`, `facet`, `priceMin`/`priceMax`, `condition` (and `city`/`state` if set) and **no** `sort`, `nearCity`, `nearState` or `source`. `alerts_enabled` is true. |
| TC-002 | AC1 — voice and sort are not saved | Search by voice (US-129) and change the sort, then save | Same as TC-001: no `source`, no `sort` in the stored criteria. |
| TC-003 | AC1 — Real Estate intent | Open a Real Estate category, choose **Rent**, save. Then open another Real Estate category and, before choosing Buy/Rent/Lease, look at the button | The saved criteria contain `transactionIntent: RENT`. With no intent chosen the **Save search** button is disabled. |
| TC-004 | AC1 — nothing to save | Open the Search screen with no text, category or filter (or "See All" from Home) | No results header, or the **Save search** button is disabled. Posting empty criteria to the API gives `ERROR_INVALID_CRITERIA` (400). |
| TC-005 | AC3 — list | Open **Profile → Saved searches** (also reachable from the Search screen link) | Every saved search appears newest first with its name, a one-line summary (text · category · Buy/Rent/Lease · price · conditions · place · "n filters") and an **Alerts** switch. A signed-out visitor cannot open it (sent to Sign In). |
| TC-006 | AC3 — empty and error | Use an account with none; then stop the backend and pull to refresh | Empty state "No saved searches yet" with a hint. Error state with **Retry** that works once the backend is back. |
| TC-007 | AC4 — alerts switch | Switch alerts off, close and reopen the app; switch on again | The state persists. Turning alerts on again moves `last_checked_at` to now (listings published while off are not announced). If the server is unreachable the switch goes back and "Unable to change alerts. Try again" shows. |
| TC-008 | AC4 — delete with undo | Delete a search; tap **Undo** within five seconds. Delete again and do nothing | Undo restores the card in its place and nothing is sent. Without undo the card stays hidden and the DELETE is sent after five seconds; reopening the list confirms it. If the DELETE fails the card returns with "Unable to delete the saved search. It was put back". Leaving the screen inside the five seconds still deletes it. |
| TC-009 | Edge — same criteria twice | Save the same search again; save it with the facets chosen in a different order, extra spaces or different letter case in the text | "Already saved" (HTTP 200 and the same id); only one row exists. |
| TC-010 | Edge — more than the limit | Set `SAVED_SEARCH_MAX` to 2, save three different searches | The third gives "Maximum 2 saved searches allowed" (HTTP 409, `ERROR_MAX_SAVED_SEARCHES`). Raising the setting lets the next save through. Saving an already-saved search at the limit still answers "Already saved". |
| TC-011 | Edge — criteria become invalid | Save a search in category X; disable X (or its L1) in `categories.admin_enabled`; open the list; enable X again | The card shows "Search criteria no longer valid", has **Delete** only (no switch, tap does nothing); the daily job sets `invalid_reason` and sends nothing. After X is enabled again the card is valid at once and the next run clears `invalid_reason`. |
| TC-012 | AC2 — digest | As A save a search for `iphone` (alerts on); run the trigger steps so its watermark is 2 days back; as B publish two matching listings published after that, plus one before it; run the job | A gets **one** notification "New matches for your saved search": "2 new items match "<name>": <title>; <title>." Listings published before the watermark and A's own listings are not counted. Tapping it opens that search's results page with all saved filters. |
| TC-013 | Edge — job re-run, two instances | Run the job twice the same day (delete the marker in between); start two backend instances | A second message is not created: the repeat guard, the dedupe key `saved-search:{id}:{yyyy-MM-dd}` and the compare-and-set watermark each stop it. With the marker present the job does not run at all. |
| TC-014 | Edge — many matches | Publish more than 3 matching listings | One digest with the real count ("12 new items match…") and at most 3 titles followed by "and more". |
| TC-015 | Edge — no digest | Alerts off; the owner suspended (`users.status`); invalid criteria; no matching listing | No notification for those searches. A search with no matches still moves its watermark (not for suspended or invalid ones). |
| TC-016 | Admin time | Set `SAVED_SEARCH_ALERT_MINUTE_OF_DAY` in the future, tick; then set it to a passed minute | No run before the time; the next tick after the change runs once. |
| TC-017 | Failure — Redis and OpenSearch down | Stop Redis for one tick, then OpenSearch for one run | Redis down: warning "Saved-search alert run skipped…", no messages, the next tick retries. OpenSearch down: the run stops with a warning, the Redis marker is released and the next tick retries; no watermark moved, no match lost. |
| TC-018 | Security — other users | With A's token call `PATCH` and `DELETE /api/v1/search/saved/{id of a search of B}` and with a random id; call without a token | The same 404 for B's and unknown ids; 401 without a token; nothing of B's changes. |
| TC-019 | API contract (curl) | `POST` new / duplicate / empty / invalid category / over the limit; `GET`; `PATCH {}`; `PATCH {"alertsEnabled":false}`; `DELETE`; more than `RATE_LIMIT_SAVE_PER_MIN` writes in a minute | 201 / 200 / 400 `ERROR_INVALID_CRITERIA` / 400 / 409 / 200 / 400 / 200 / 204 / 429. Responses use the standard envelope; `valid` and `invalidMessage` come with each search, plus `categoryName`, `categoryLevel`, `realEstate`. |
| TC-020 | Notifications screen | Open Notifications with a digest, an older app build (or edit `params` to remove `count`), and a notification whose link is unknown | The digest shows under **Others** with its own icon in English and Hindi (count, name, titles). With missing `count` or `name` the server's English text shows. An unknown link still says "This is coming soon". |
| TC-021 | Hindi and text size | Switch the app to Hindi; open Saved searches, save, delete with undo, open the digest; set the phone to 200% text on a small screen | Every text is in Hindi (drafts), nothing is clipped or overflows, the card actions stay reachable, tap targets are at least 48 dp. |
| TC-022 | Accessibility | TalkBack / VoiceOver on the list and the Save search button | The screen title is a heading; each card reads its name and summary and is a button; the switch reads "Alerts for <name>"; delete reads "Delete saved search <name>"; the invalid message is announced. |
| TC-023 | Privacy | Capture the backend log while saving, listing and running the job | Logs contain counts and ids only: no query text, place, search name or listing title. Metrics `saved_search.alert.runs.total`, `…sent.total`, `…invalid.total` and the duration timer are present. |

## Device matrix (pending)

Record OS version, device model, app build and results for each *device* case (TC-001, TC-005, TC-007, TC-008, TC-012,
TC-020 to TC-022):

| Device | OS | Result | Notes |
|---|---|---|---|
| iPhone (local test stack) | | | |
| Android phone | | | |

## Known limits

- The digest count can include a listing that expired a moment ago (decision G16); the sample titles are re-checked against
  the database, so a dead listing is never shown.
- The alert shows under **Others** in Notifications (no dedicated tab).
- Alerts are in-app only; no push, email or SMS (decisions D3 and C5).
- The Hindi texts are drafts.
