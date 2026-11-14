# US-066: Saved Searches and Alerts - Implementation Plan

## 1. Header

| Field | Value |
|---|---|
| Story | US-066 - Saved Searches and Alerts |
| Sprint | Sprint 3 - Discovery & Search |
| Story points | 5 (Sprint plan and LLD Part F). Effort estimate below is about 8 working days; gap G2 is settled: keep 5 SP. |
| Repos involved | valuex-backend (table, 4 endpoints, daily alert job, notification, settings) and valuex-mobile (Saved Searches screen, Save Search button, Profile entry, alert deep link, strings). No `valuex-ai`, infra or `valuex-web` change. |
| Dependencies | US-011 (search API, `SearchRequestValidator`, `SearchCriteria`, results screen). Verified on 2026-11-13: US-011 is merged on `main` in both repos. US-129 (voice search), US-012 and US-111 were also merged by 2026-11-13 (user-confirmed and verified on GitHub), so the search files US-066 edits are current on `main` (gap G1 resolved). No other story depends on US-066. |
| Date | 2026-11-13 |
| Design source | [Sprint 3 LLD](../LLD/Sprint-3-Discovery-Search-LLD.md) Part F (F.1 to F.10), the settings table in section 1.6, and decisions D3 and C5 in section 9. |
| Branches (proposal) | `feature/US-066-saved-searches-alerts` in `valuex-backend` and `valuex-mobile`, cut from the current `main` of each repo (the US-129, US-012 and US-111 PRs are merged, gap G1). |
| Flyway number | **V29** as built: V27 was taken by US-111 and V28 by US-118 (`V28__listing_closed_outcome.sql`, merged while this story was built). The plan assumed V28; the LLD's provisional number was also V28; re-check the latest number when the branch is cut (gap G9). |
| Effort | About 8 working days: backend 3.5, mobile 3, tests and device checks 1, documents 0.5. |

## 2. Story Recap

**As a** buyer **I want to** save my search criteria and get alerts **so that** I'm notified when matching items are listed.

### Acceptance criteria (user-stories.md US-066, with the 2026-10-25 and 2026-11-09 updates)

| ID | Behaviour |
|---|---|
| AC1 | Given I performed a search, when I tap "Save Search", the criteria are saved: query, category code, facets, filters and, for Real Estate, the transaction intent. |
| AC2 | When a new listing matches a saved search, I get an alert. Decided on 2026-11-09: an **in-app daily digest** (one per saved search per day), not push. |
| AC3 | "Saved Searches" lists all my saved searches. |
| AC4 | I can enable or disable alerts per search, and delete a saved search any time. |

**Edge cases:** more than 10 saved searches; many matches in one day (digest with a count and up to 3 sample titles); criteria that become invalid (category disabled or removed); same criteria saved twice; suspended or inactive user; job re-run or two instances.
**Validation rules:** at most `SAVED_SEARCH_MAX` (default 10) per user; alerts at most once a day per search; a search the user cannot reach (another user's id) is a 404.
**Errors:** `ERROR_MAX_SAVED_SEARCHES` ("Maximum {n} saved searches allowed"); `ERROR_INVALID_CRITERIA` ("Search criteria no longer valid").
**Out of scope:** push notifications and FCM topics (decision D3 and C5), real-time alerts, email and SMS alerts.

## 3. Design Reference

LLD Part F: F.3 (data model), F.4 (API), F.5 (backend and alert job), F.6 (sequence), F.7 (mobile), F.8 (rules and codes), F.9 (security and metrics), F.10 (tests); section 1.6 (Admin-managed settings); section 9.1 (D3) and 9.3 (C5); cross-cutting items 4, 6 and 7 of section 8 (notification types, Flyway numbers, job observability). HLD 07 section 6 already lists the four endpoints.

### Key design decisions

- No new Admin screen. The four limits are Admin-managed settings read through `PlatformSettingsService.discovery()`; the existing settings endpoint picks up new registry entries.
- A saved search stores the same fields a search request takes (`query`, `category`, `transactionIntent`, `facet[]`, `priceMin`, `priceMax`, `condition[]`, `city`, `state`). It never stores `nearCity`, `nearState`, the sort, or `source` (US-129). This lets one validator serve both search and saved search.
- Validation reuses `SearchRequestValidator.validate` and wraps any failure as `ERROR_INVALID_CRITERIA`; the same call re-checks validity on list and on every job run.
- The alert job runs every 15 minutes, fires once a day at the first tick at or after the Admin time, guarded by a Redis `SET NX` marker; a `last_checked_at` watermark per search and a notification dedupe key make a re-run harmless.
- Notification: `SAVED_SEARCH_MATCHES`, `IN_APP` channel only, dedupe key `saved-search:{id}:{yyyy-MM-dd}`.

### Verified implementation anchors (checked against `origin/main` on 2026-11-13)

| Area | Finding and consequence |
|---|---|
| Migrations | Latest is `V26__listing_photo_variants.sql`; V25 seeds the discovery settings with `INSERT ... ON CONFLICT (setting_key) DO NOTHING` into `platform_settings`. The new migration follows that pattern. |
| Settings registry | `DiscoverySetting` has only `Kind.INTEGER` and `Kind.DECIMAL` and no `SAVED_*` entries. `SAVED_SEARCH_MAX` (1 to 50, 10), `SAVED_SEARCH_ALERT_SAMPLE_TITLES` (0 to 5, 3) and `SAVED_SEARCH_ALERT_MIN_HOURS` (1 to 24, 20) fit. The LLD's `SAVED_SEARCH_ALERT_TIME` is an `HH:mm` time and does not fit, so it is stored as whole minutes after midnight under the name `SAVED_SEARCH_ALERT_MINUTE_OF_DAY` (0 to 1439, default 540 = 09:00 Asia/Kolkata; gap G3, decided). |
| Search validator | `SearchRequestValidator.validate(SearchRequest, UUID callerId)` is a pure check with no rate limit (the limit is in `ListingSearchService.checkRate`), so it can be reused. It throws `NotFoundException("CATEGORY_NOT_FOUND")` for a removed category and for a disabled one (`!scope.enabled()`); `CategoryService.resolveScope` itself returns `enabled=false` for disabled and throws only for removed, which lets the checker tell `CATEGORY_DISABLED` from `CATEGORY_REMOVED`. |
| Search port | `ListingSearchPort` has `search`, `suggest` and index methods only: no `_msearch`, and `ListingSearchQuery` has no `publishedAt` window. Both must be added (gap G4). The adapter calls `searchClient.generic().execute(Requests.builder()...json(...))` inside a Resilience4j breaker. |
| Exceptions | `BusinessException` always returns HTTP 400, and `GlobalExceptionHandler` has no plain 409 handler (`ConfirmationRequiredException` is the only 409 and has other semantics). `ERROR_MAX_SAVED_SEARCHES` is 409 in the LLD (gap G5). |
| Notifications | `NotificationDispatcher.dispatch(NotificationDispatchRequest)` with `userId`, `eventType` (column 50), `title`, `body`, `deepLink` (column 255), `params`, `dedupeKey` (column 160, unique partial index `uq_notifications_dedupe_key`), `priority`, `channels`. `NotificationChannelType` has `IN_APP`, `SMS`, `EMAIL` (no `PUSH`). `ListingEventNotificationListener` shows the pattern: dispatch inside `newTransaction.run(...)`, treat `DataIntegrityViolationException` as a duplicate. |
| Jobs | Existing jobs use `@Scheduled` with a property cron (for example `ListingExpiryJob`); Redis `setIfAbsent(key, value, ttl)` exists on `RedisCacheService` (Redis rule: always set a TTL). No advisory-lock pattern exists yet. |
| Live users | The live check for listings joins `users u ... u.status = 'ACTIVE'` inside `ListingIndexSourceAdapter` (listing module implements the search port). Reading `users.status` for the job follows the same pattern: a port in `search/application/port`, implemented outside the search module (gap G10). |
| Mobile criteria | `SearchCriteria` already says it describes a saved search; it has `toQueryParameters()` (names equal the API's) but also carries UI-only fields (`categoryName`, `categoryLevel`, `realEstate`, `browseAll`) and `sort`. `searchLocation`/`searchCriteriaFromParams` in `search_routes.dart` rebuild criteria from a deep link but carry no filters. |
| Mobile notifications | `notificationTargetFor` maps only `/profile`, `/profile/account-security`, `/sell/details` and `/sell/plan`; `notification_text.dart` localises by `eventType` and `params`, falling back to the server's English text. A tap on an unknown link shows "coming soon". |
| Mobile entry points | `RouteNames` has no saved-search route. The Profile screen has a static "Saved items" row (`ProfileMenuKeys.savedItems`); the results view is a `CustomScrollView` whose header can take the Save button. |

## 4. Implementation Steps

### 4.1 Branches and baselines (about 0.5 day)
- [ ] Pull the latest `main` in `valuex-backend` and `valuex-mobile`, confirm the US-129, US-012 and US-111 merges are present, then cut `feature/US-066-saved-searches-alerts` from it in both repos.
- [ ] Baselines: backend `mvn verify` with JDK 21 pinned (the Colima and Testcontainers settings from the backend README); mobile `dart format`, `flutter analyze`, `flutter test --dart-define=SKIP_PIXEL_CONTRAST=true`. Record any pre-existing failure so it is not blamed on this story.
- [ ] G3 (alert time stored as minutes after midnight), G4 (`_msearch` spike, falling back to one search per saved search) and G5 (`ConflictException`, 409) are decided; update the LLD Part F and the settings table in section 1.6 where they differ (the setting is renamed `SAVED_SEARCH_ALERT_MINUTE_OF_DAY`).

### 4.2 Database (V29 as built; re-check the latest number at branch time)
- [ ] `V{N}__saved_searches.sql`: table `saved_searches` exactly as LLD F.3 (`criteria JSONB`, `criteria_hash CHAR(64)`, `alerts_enabled`, `invalid_reason`, `last_checked_at`, `last_alert_at`, timestamps, `UNIQUE (user_id, criteria_hash)`), plus an index on `user_id` (standard 2.7: every foreign key is indexed) and the partial alerts index of F.3.
- [ ] Same migration seeds the settings with `ON CONFLICT (setting_key) DO NOTHING`: `SAVED_SEARCH_MAX=10`, `SAVED_SEARCH_ALERT_SAMPLE_TITLES=3`, `SAVED_SEARCH_ALERT_MIN_HOURS=20` and `SAVED_SEARCH_ALERT_MINUTE_OF_DAY=540` (09:00 Asia/Kolkata).
- [ ] Constraint for `invalid_reason` values (`CATEGORY_DISABLED`, `CATEGORY_REMOVED`, `ATTRIBUTE_REMOVED`).

### 4.3 Backend: settings, exceptions and search port
- [ ] `DiscoverySetting`: add the `SAVED_SEARCH_*` entries with the ranges of LLD 1.6, with the alert time as `SAVED_SEARCH_ALERT_MINUTE_OF_DAY` (`Kind.INTEGER`, default 540, range 0 to 1439); extend `DiscoverySettingsTest`-style tests for default, range and parse.
- [ ] 409 handling for `ERROR_MAX_SAVED_SEARCHES` per G5 (a small `ConflictException` with a `GlobalExceptionHandler` mapping, or a documented 400).
- [ ] `ListingSearchQuery`: optional `publishedAfter` (exclusive) and `publishedAtOrBefore` (inclusive) bounds; `OpenSearchQueryBuilder` adds a `range` on `publishedAt` when set. Update every `new ListingSearchQuery(` call (validator, tests) and keep search results unchanged when the bounds are null.
- [ ] `ListingSearchPort`: a batch method for the digest (count and the first N titles per query) implemented per G4. It uses the same breaker and maps failures to `SearchUnavailableException`. `DisabledListingSearchPort` returns "nothing found" like its other methods.

### 4.4 Backend: saved-search module (`com.valuex.search`)
- [ ] `domain/SavedSearch` (JPA entity), `SavedSearchCriteria` (the stored record), `InvalidReason` enum; `infrastructure/persistence/SavedSearchRepository` (by user, by `(user, hash)`, count by user).
- [ ] `application/service/SavedSearchCriteriaMapper`: canonical form (sorted `facet[]` and `condition[]`, trimmed text, no `nearCity`, `nearState`, `sort`, `source`) and the SHA-256 hash; unit-test that order does not change the hash.
- [ ] `application/service/SavedSearchCriteriaChecker`: builds a `SearchRequest` from the stored criteria, runs `SearchRequestValidator.validate`, and returns valid or the `InvalidReason`. It calls `CategoryService.resolveScope` first so removed and disabled categories get different reasons; any other validator failure becomes `ATTRIBUTE_REMOVED` or `ERROR_INVALID_CRITERIA` on create.
- [ ] `SavedSearchService`: `create` (validate, hash, return existing on a hash match with HTTP 200, otherwise enforce the limit under a per-user lock and insert; handle the unique-constraint race by returning the existing row), `list` (revalidates each row live; fills `valid` and `invalidMessage`; adds the resolved category name, level and Real Estate flag for the app, see G7), `update` (alerts toggle and name), `delete`. Every statement is scoped to the caller; another user's id gives the same 404 as an unknown id.
- [ ] Default name when omitted: built from query and category name, plain text, at most 80 characters (`PlainText.clean`); a supplied name is cleaned and limited the same way.
- [ ] `api/SavedSearchController` (`/api/v1/search/saved`, JWT, `@Tag`/`@Operation` docs): `POST` 201 or 200, `GET`, `PATCH`, `DELETE` 204, with request/response DTOs (`SavedSearchRequest`, `SavedSearchResponse`) and bean validation. The standard `ApiResponse` envelope.
- [ ] Rate limit on writes: decide in G11 whether the existing `RATE_LIMIT_SAVE_PER_MIN` applies.

### 4.5 Backend: daily alert job and notification
- [ ] `application/service/SavedSearchAlertJob`: `@Scheduled` every 15 minutes (cron in `ValuexProperties`, deployment configuration); runs when the time of day in Asia/Kolkata is at or after `SAVED_SEARCH_ALERT_MINUTE_OF_DAY` minutes after midnight (converted with the `Asia/Kolkata` zone) and the Redis marker `saved-search-alert:{yyyy-MM-dd}` was set by this instance (`setIfAbsent` with a TTL of about 26 hours). Use the injected `Clock`, never `Instant.now()`.
- [ ] Batch loop as in LLD F.5: `runStart = now`; page through alert-enabled searches of `ACTIVE` users (100 per batch); build digest queries (criteria plus `publishedAt > last_checked_at AND <= runStart`, `size = SAMPLE_TITLES`, own listings and disabled categories excluded exactly as in Part B); re-check sample ids with `ListingEligibilityFilter`; dispatch one `SAVED_SEARCH_MATCHES` per search with matches; then advance `last_checked_at = runStart` (and `last_alert_at` when a message was sent) only after the batch succeeded. Skip a search alerted less than `SAVED_SEARCH_ALERT_MIN_HOURS` ago. Re-validate every alert-enabled search each run and write `invalid_reason` when it changes (recovery, G6).
- [ ] Paging and locking as decided in G8: keyset paging in id order with a compare-and-set update of `last_checked_at` (a deliberate change from the LLD's `FOR UPDATE SKIP LOCKED`; record it in "As built"). No database transaction may stay open across an OpenSearch call.
- [ ] A failure in one batch is logged (counts and ids only, never criteria text) and the job continues; a Redis failure follows G12 and a job that stops halfway follows G13.
- [ ] `SavedSearchNotificationCopy`: English title and body (count and up to 3 titles shortened to 60 characters with `PlainText`), `IN_APP` only, `MEDIUM` priority, deep link per G7, `params` with `searchId`, `count`, `name` and `titles` so the app can show Hindi.
- [ ] Observability: `saved_search.alert.runs.total`, `saved_search.alert.sent.total`, `saved_search.alert.invalid.total`, a job timer; one start/end log line with counts and duration only.
- [ ] README (backend): endpoints, settings, job time and the marker key.

### 4.6 Mobile: data and domain (`lib/features/saved_searches/{data,domain}`)
- [ ] `domain/saved_search.dart` (id, name, criteria, `alertsEnabled`, `valid`, `invalidMessage`, `lastAlertAt`, category info) and mapping to and from `SearchCriteria`. The request body reuses `SearchCriteria.toQueryParameters()` minus `sort`; facets are split on the first `:`.
- [ ] `data/saved_searches_repository.dart` (Dio, same pattern as `SearchRepository`): create, list, update, delete; map `ERROR_MAX_SAVED_SEARCHES` and `ERROR_INVALID_CRITERIA` to typed errors; add the four paths to `ApiConstants`.
- [ ] A test that the body never contains `source`, `sort`, `nearCity` or `nearState` (also the US-129 rule that saved searches never carry `source`).

### 4.7 Mobile: presentation
- [ ] `providers/saved_searches_controller.dart` (`@riverpod`, generated file committed): load, toggle alerts (optimistic with rollback), delete with undo (the delete request is sent when the undo window closes), create with the "already saved" and "limit" outcomes.
- [ ] `SavedSearchesScreen`: card per search with name, readable criteria summary, alerts switch, delete with undo snackbar; invalid state shows `ERROR_INVALID_CRITERIA` text with Delete only; empty and error states with Retry; 48 dp targets, semantic labels, Hindi at 200% text.
- [ ] "Save Search" button in the results header of the Search screen: disabled when `criteria.isBlank`; shows the limit message at the maximum; shows "Already saved" when the server returns the existing search. Does not change the typed-versus-voice marker of US-129.
- [ ] Routes and entry points: `RouteNames.savedSearches`; link from the Search results header and a new Profile row ("Saved searches"); tapping a card opens the results page with its criteria (G7).
- [ ] Alert deep link: extend `notificationTargetFor` so the alert opens that saved search's results; `notification_text.dart` gets the `SAVED_SEARCH_MATCHES` title and body in English and Hindi (count and titles from `params`), with the server text as fallback.
- [ ] Strings: new keys in `app_en.arb` and `app_hi.arb` (screen title, empty/error/invalid states, buttons, undo, limit and "already saved" messages, criteria summary words, notification text); `flutter gen-l10n`. Hindi texts are drafts for native-speaker review (gap G14).

### 4.8 Documentation and quality
- [ ] `Documents/Manual Testing Guides/US-066-Testing-Guide.md`: save, list, toggle, delete, limit, duplicate, invalid category, digest at the Admin time (including how to trigger a run safely in a test environment), Hindi, deep link.
- [ ] LLD Part F "As built" note for every deviation (same style as B.12 and I.12), Sprint plan status, HLD 05 and HLD 07 section 6 notes (cross-cutting item 8 of the LLD).
- [ ] `dart format lib test`, `flutter analyze`, full mobile tests with at least 85% line coverage of the new hand-written code; backend `mvn verify` with Checkstyle and at least 80% coverage of new classes; run the Windows Sonar scan and report the result (the Sonar scan is not available on this Mac).
- [ ] Real iPhone check with the local test stack (same launcher as US-129): create searches, publish a matching listing from a second account, trigger the digest, open the alert.

## 5. Test Plan

Targets: backend 80% and mobile 85% line coverage for new code (CODING_STANDARDS 1.8), aiming above 90% for the new classes.

### 5.1 Backend unit
- [ ] `SavedSearchCriteriaMapperTest`: facets, conditions and keys in any order give one hash; `nearCity`, `nearState`, `sort` and `source` are never stored; whitespace and case of the text.
- [ ] `SavedSearchCriteriaCheckerTest`: valid; removed category gives `CATEGORY_REMOVED`; disabled gives `CATEGORY_DISABLED`; a removed facet attribute gives `ATTRIBUTE_REMOVED`; Real Estate without intent is invalid.
- [ ] `SavedSearchServiceTest` (AC1, AC3, AC4): create, duplicate returns the existing row (200), limit of `SAVED_SEARCH_MAX` (409), the limit follows an Admin change, a unique-constraint race returns the existing row, list fills `valid` and `invalidMessage`, update toggles alerts and renames (clean, 80 characters), delete, foreign id gives 404, name sanitised.
- [ ] `SavedSearchControllerTest`: status codes (201, 200, 409, 400, 404, 204), envelope, bean validation, authentication required.
- [ ] `SavedSearchAlertJobTest`: runs once a day at the first tick at or after the setting; a changed time applies at the next tick; the Redis marker blocks a second run; batching; watermark advances only after the batch succeeded; a batch failure does not stop later batches and loses no match; repeat guard (`MIN_HOURS`); inactive user, invalid and alerts-off searches are skipped; recovery of a search whose category is enabled again; a zero-match search still advances its watermark.
- [ ] `SavedSearchNotificationCopyTest`: count, up to 3 titles, 60-character title limit, markup removed, `params` content, deep link, `IN_APP` only.
- [ ] `DiscoverySettingTest` additions for the new entries; `OpenSearchQueryBuilderTest` for the `publishedAt` bounds (and unchanged output when absent); adapter test for the digest method (breaker open, HTTP error).

### 5.2 Backend integration (Testcontainers)
- [ ] Create, list, toggle, delete through the real API; the limit under two concurrent creates; listings published before and after the watermark; one digest per day (a second run sends nothing); a disabled category flips the search to invalid in the list without a job; another user cannot read or change a search; a Real Estate saved search keeps its intent; the own-listings exclusion.

### 5.3 Mobile unit and widget
- [ ] `saved_search_test` and repository tests: mapping both ways, facets with `:` and ranges, request body has no `sort` or `source`, error mapping.
- [ ] Controller tests: optimistic toggle and rollback, delete with undo (request only after the undo window), limit and "already saved" outcomes.
- [ ] Screen tests (AC3, AC4): list, empty, error with Retry, invalid card (Delete only), switch, delete and undo; Hindi and English at 200% text on a small screen; accessibility guidelines (tap target, labels, contrast) and headings; `no_hardcoded_strings_test`; localization key parity.
- [ ] Search screen test (AC1): button disabled with no criteria, saves the current criteria including category, filters and Real Estate intent, limit message, "already saved".
- [ ] Notification tests: `SAVED_SEARCH_MATCHES` shows English and Hindi text; tap opens the saved search; an unknown deep link still shows "coming soon".

### 5.4 Real device (recorded in the testing guide)
- [ ] iPhone with the local stack: two accounts, a matching listing published after the save, the digest at the (temporarily changed) alert time, tap the notification; Hindi; delete with undo; limit message at 10.

## 6. Validation Checklist

- [ ] AC1: Save Search stores query, category code, facets, filters and the Real Estate intent; nothing else (no sort, near place or `source`).
- [ ] AC2: a new matching listing produces one in-app digest per saved search per day with the count and up to 3 titles; none for searches with alerts off, invalid criteria or inactive users.
- [ ] AC3: Saved Searches lists all my searches with name, criteria summary and alert state.
- [ ] AC4: alerts can be switched on and off per search; delete works at any time (with undo).
- [ ] Limit: the 11th search gives `ERROR_MAX_SAVED_SEARCHES` with the Admin-managed maximum in the message.
- [ ] Duplicate: saving the same criteria again returns the existing search ("Already saved").
- [ ] Invalid criteria: a disabled or removed category shows `ERROR_INVALID_CRITERIA` on the card, with Delete only, and stops alerts; it recovers if the category is enabled again.
- [ ] Many matches: one digest, not one per listing; the watermark moves so the same listings are not announced twice.
- [ ] Re-run and two instances: the Redis marker, the repeat guard and the dedupe key give one notification per search per day.
- [ ] Security: all statements are scoped to the caller; foreign ids give the same 404; stored criteria are validated on write and on every run; titles are plain text.
- [ ] Privacy and logging: no query text, place or title in logs; metrics and job logs carry counts and ids only.
- [ ] Both languages complete; 48 dp targets; 200% text; no hard-coded strings; accessibility guidelines pass.
- [ ] Alert deep link opens the saved search's results; older app versions still show the server's English text.
- [ ] Checkstyle, tests and coverage pass; Windows Sonar result reported; testing guide, LLD "As built", Sprint plan, HLD notes updated.

## 7. Open Gaps / Questions

Decisions recorded on 2026-11-13. **All gaps (G1 to G17) are resolved.**

| # | Gap or question | Decision | Remaining action |
|---|---|---|---|
| G1 | US-066 edits files that US-129, US-012 and US-111 also changed. | **Resolved:** the user confirmed all open PRs are merged; verified on GitHub (mobile #65 and #66, backend #59 and #60, documents #203, AI #11). | Branch from the current `main` in step 4.1. |
| G2 | The LLD states 5 SP; the plan is about 8 working days. | **Resolved:** accepted, keep 5 SP. | Note the effort difference in the Sprint plan. |
| G3 | `SAVED_SEARCH_ALERT_TIME` is an `HH:mm` value, but the settings registry (`DiscoverySetting`) holds only whole numbers and decimals. | **Resolved by the user (Option A):** store the time as whole minutes after midnight in `SAVED_SEARCH_ALERT_MINUTE_OF_DAY` (0 to 1439, default 540 = 09:00 Asia/Kolkata). No change to the settings engine. This renames the LLD setting; record it in LLD section 1.6 and Part F "As built". An Admin screen (US-121) can later show it as `HH:mm`. | Steps 4.2, 4.3 and 4.5. |
| G4 | The LLD uses one `_msearch` per batch; the search port has no multi-search or `publishedAt` window. | **Resolved:** accepted. Add the `publishedAt` bounds and spike `_msearch`; if it is not clean, run one search per saved search (at most 100 per batch) behind the same port method. | Spike in step 4.3; record the result in section 8. |
| G5 | `BusinessException` always returns 400, but the LLD gives `ERROR_MAX_SAVED_SEARCHES` as 409. | **Resolved by the user:** add a small `ConflictException` mapped to 409 in `GlobalExceptionHandler`. | Step 4.3. |
| G6 | How an invalid saved search becomes valid again. | **Resolved:** the job re-validates every alert-enabled search each run and clears or sets `invalid_reason`; the list endpoint always shows the live result. | Step 4.5. |
| G7 | What an alert or a saved-search tap opens; no `GET /search/saved/{id}`; stored criteria lack UI fields. | **Resolved:** deep link `/search/saved?id={uuid}`, resolved from the list (no new endpoint); the list response adds the category name, level and Real Estate flag. Record both in LLD F.4 "As built". | Step 4.4 and 4.7. |
| G8 | `FOR UPDATE SKIP LOCKED` keeps a transaction open during OpenSearch and notification calls. | **Resolved:** keyset paging in id order with a compare-and-set update of `last_checked_at`; short transactions. Record the deviation from LLD F.5 in "As built". | Step 4.5. |
| G9 | Flyway numbers are provisional. | **Resolved:** use the next free number. Verified on 2026-11-13: V27 is taken by US-111, so the next is **V28**; re-check at branch time. | Step 4.2. |
| G10 | The job needs each owner's `ACTIVE` status without the search module querying user tables. | **Resolved:** a small port in `search/application/port`, implemented by the user or auth module (check CODING_STANDARDS 2.2 and 2.3 for placement). | Step 4.5. |
| G11 | Rate limit on saved-search writes. | **Resolved:** apply `RATE_LIMIT_SAVE_PER_MIN` to `POST` and `PATCH`. | Step 4.4. |
| G12 | Behaviour when Redis is down. | **Resolved:** skip the run and log a warning; the next 15-minute tick retries and no matches are lost. | Step 4.5. |
| G13 | The job dies halfway after setting its Redis marker. | **Resolved:** accept; the watermark advances only after a successful batch, and a run over 30 minutes raises an alert (LLD F.9). | Step 4.5. |
| G14 | Hindi strings are drafts. | **Resolved:** a native speaker reviews them before release. | Before release. |
| G15 | No Figma frames for Saved Searches or the Save button. | **Resolved:** follow the design system and existing Search, Home and Notifications styles; confirm in review. | Step 4.7. |
| G16 | The digest count can include a listing that just expired. | **Resolved:** accept; word the message "N new items match". | Step 4.5. |
| G17 | SonarQube runs only on the Windows machine. | **Resolved:** run it there before merge and report the result in the PRs. | End of build. |

## 8. Spike Findings

**G4, `_msearch` through the existing client (2026-11-14): clean, no fallback needed.** `ListingSearchPort.searchBatch` sends
one `POST /{read-alias}/_msearch` with an NDJSON body (`{}` header line plus the query body per search) through
`searchClient.generic()` using `Requests.create(...)` and `Body.from(bytes, "application/x-ndjson")`. Tested against a real
OpenSearch 2.17.1 (Testcontainers, `OpenSearchBatchSearchIntegrationTest`): several queries in one round trip each keep
their own publication window (lower bound exclusive, upper bound inclusive), their own excluded seller and their own total
and sample hits, newest first. A per-item error in the response gives an empty entry for that search only; HTTP errors, a
wrong number of responses, and an open breaker give `SearchUnavailableException` (same breaker as search). The alert-time
setting (G3, minutes after midnight) and the lock approach (G8, keyset paging with compare-and-set) were decided before the
build.

## 9. Implementation Status and Deviations (2026-11-14)

All of steps 4.1 to 4.7 and the code and document parts of 4.8 are done on `feature/US-066-saved-searches-alerts` in
`valuex-backend` and `valuex-mobile` (documents on `docs/US-066-saved-searches-alerts`). Results: backend `mvn verify` 2062
tests passed, checkstyle and the JaCoCo gate met, about 97% line coverage of the new and changed backend classes; mobile
`flutter analyze --fatal-infos` clean, 1541 tests passed, 96.7% line coverage (gate 85%), new hand-written files about 97%.

**Pending:** the Windows SonarQube scan (G17), the real-iPhone check with the local stack (4.8 last item, 5.4), the Android
build, and native-speaker review of the Hindi texts (G14). They are listed in the
[testing guide](../Manual%20Testing%20Guides/US-066-Testing-Guide.md).

Deviations from this plan and the LLD are recorded in [LLD F.11](../LLD/Sprint-3-Discovery-Search-LLD.md). In short: the
setting is `SAVED_SEARCH_ALERT_MINUTE_OF_DAY`; keyset paging and compare-and-set replace `FOR UPDATE SKIP LOCKED`; the partial
alerts index is `WHERE alerts_enabled` (invalid searches are re-checked for recovery); and these small additions were made
while building, each for a reason given in F.11: empty criteria are refused with `ERROR_INVALID_CRITERIA`; switching alerts
from off to on restarts the watermark; searches of inactive owners and invalid searches are skipped without moving their
watermark; when the search index is unavailable the run stops and releases the Redis marker so the next tick retries; the
mobile app calls `POST` through a new `ApiClient.postWithStatus` to tell 201 from 200; the alert shows under "Others" in
Notifications.

---

**Status:** Approved (2026-11-13). Approved by the user in so many words. All gaps G1 to G17 are resolved (G3: Option A, minutes after midnight). Implemented on 2026-11-14 on the story branches (not committed, pushed or reviewed yet); SonarQube, device checks and Hindi review are pending.
