# US-073: Save and Bookmark Listings - Implementation Plan

## 1. Header

| Field | Value |
|---|---|
| Story | US-073 - Save and Bookmark Listings |
| Sprint | Sprint 3 - Discovery & Search |
| Story points | 3 (Sprint plan and LLD Part D) |
| Repos involved | valuex-backend (table, 3 endpoints, availability listener, retention job, notification, settings, `saved` flag) and valuex-mobile (heart control, Saved Items screen, notification deep link, strings). No `valuex-ai`, infra or `valuex-web` change. |
| Dependencies | US-012 (listing details, `PublicListingResponse.saved`, `ListingCard.saved`). Verified 2026-11-14: US-012, US-011, US-111 and US-066 are merged on `main`. US-118 (PR open at the time of writing) leaves `SOLD` for this story to treat as unavailable. |
| Date | 2026-11-14 |
| Design source | [Sprint 3 LLD](../LLD/Sprint-3-Discovery-Search-LLD.md) Part D (D.1 to D.10), the settings table in section 1.6, and the US-073 notes in sections 8 and 9. |
| Branches (proposal) | `feature/US-073-save-bookmark-listings` in `valuex-backend` and `valuex-mobile`, cut from current `main`. |
| Flyway number | The LLD says V26 (provisional). `main` is at V30 (V28 is US-118, V29 US-066), so use the next free number when the branch is cut (gap G1). |

## 2. Story Recap

**As a** buyer **I want to** save listings I'm interested in **so that** I can review them later.

| ID | Behaviour |
|---|---|
| AC1 | Tapping Save or the heart on a listing adds it to my saved items and the icon changes to the Saved state. |
| AC2 | "Saved Items" shows all my bookmarked listings; I can view, remove or purchase them (purchase waits for Sprint 5). |
| AC3 | When a saved listing is sold or removed, I get a notification and the item shows "No longer available". |

**Edge cases:** hundreds of saved items; price change (list shows the current price); seller suspended; listing expires; listing hidden for review (temporary, no notification); double tap, repeat remove and two devices at the limit.
**Validation rules:** at most `SAVED_LISTING_MAX` (default 200) per user; unavailable entries kept `SAVED_LISTING_RETENTION_DAYS` (default 90) after they became unavailable, available ones never removed; can save from search results, Home and the listing page.
**Errors:** `ERROR_MAX_SAVED` (409), `ERROR_ITEM_UNAVAILABLE` (409), unknown listing 404.
**Out of scope:** Add to cart or Buy from Saved Items (Sprint 5, button disabled), price drop alerts, Profile hub badge.

## 3. Design Reference

LLD Part D: D.3 data model, D.4 API, D.5 backend, D.6 sequence, D.7 mobile, D.8 rules, D.9 security, D.10 tests; section 1.4 (`ListingCard`), section 1.6 (Admin-managed settings); US-012 notes that `saved` is `false` until this story.

### Key design decisions

- Table `saved_listings (user_id, listing_id, created_at, unavailable_at, unavailable_reason)`, primary key `(user_id, listing_id)`. Availability shown to the buyer is computed at read time from the listing; the two `unavailable_*` columns only drive the one-time notification and the retention clock.
- `PUT` and `DELETE` are idempotent. The limit check and insert run under a per-user `pg_advisory_xact_lock`, so two devices cannot pass the limit.
- A `ListingStatusChangedEvent`, `ListingDeletedEvent` or seller `UserStateChangedEvent` marks entries unavailable and sends one `IN_APP` notification per buyer (`SAVED_LISTING_UNAVAILABLE`, dedupe key `saved:{listingId}:{reason}`). `TRUST_SAFETY_REVIEW` is temporary: shown "Under review", no notification, nothing stored.
- The limit and retention are `DiscoverySetting` entries stored in `platform_settings`, read on every use so an Admin change applies without a restart.

### Verified implementation anchors (checked against `main` on 2026-11-14)

| Area | Finding and consequence |
|---|---|
| Settings registry | `DiscoverySetting` has `SAVED_SEARCH_*` and `RATE_LIMIT_SAVE_PER_MIN` (60) but no `SAVED_LISTING_*`. Add `SAVED_LISTING_MAX` and `SAVED_LISTING_RETENTION_DAYS` (7 to 365, default 90). The LLD names `PlatformSettingsService`; `settingsService.discovery().integer(...)` is the real call (used in `SavedSearchService`). |
| `saved` flag | `ListingCard.saved` is set in `ListingSearchService` (line ~192) and `PublicListingResponse.saved` in `PublicListingService` (line ~86), both currently `false`. Each needs one batch or single lookup. The Home feed model has no `saved` field (US-111 note); see gap G3. |
| Events | `ListingStatusChangedEvent` (fromState, toState, action), `ListingDeletedEvent`, and `UserStateChangedEvent` (auth module, `UserAccountState`) exist. `SOLD` becomes reachable through US-118's `MARK_PROPERTY_CLOSED`. |
| Notifications | `NotificationDispatcher.dispatch` with a dedupe key; `SavedSearchNotificationCopy` and `ListingEventNotificationListener` show the copy and "never block the flow" patterns to copy. |
| Errors | `ConflictException(errorCode, message)` has a 409 handler, so both 409 codes need no new handler (the US-066 plan's gap on 409 is already solved). |
| Mobile | `profile_screen.dart` already lists "Saved Items" (`ProfileMenuKeys.savedItems`); `notification_deep_links.dart`, `saved_searches` feature (screen, repository, controller) and `listing_view` are the patterns to follow. `ListingCard` widgets: `home/.../listing_card.dart` and `search_results_view.dart`. |

## 4. Implementation Steps

### Database
- [ ] Migration `V<next>__saved_listings.sql`: table, three indexes of D.3, and `INSERT ... ON CONFLICT (setting_key) DO NOTHING` seeds for `SAVED_LISTING_MAX` = 200 and `SAVED_LISTING_RETENTION_DAYS` = 90.

### Backend (`valuex-backend`)
- [ ] `DiscoverySetting`: add `SAVED_LISTING_MAX` (range per gap G2) and `SAVED_LISTING_RETENTION_DAYS` (7 to 365).
- [ ] New package `savedlisting` (or under `search`; gap G4): entity `SavedListing`, repository, `SavedListingService` (`save`, `remove`, `list`), `SavedListingController` (`PUT`/`DELETE /api/v1/saved-listings/{listingId}`, `GET` with `page`, `size`), DTO `SavedListingItem` (card plus `available`, `unavailableReason`, `savedAt`) and page response with `maxSaved`.
- [ ] `save`: advisory lock, 404 for unknown id, `ERROR_ITEM_UNAVAILABLE` when not live, idempotent when present, `ERROR_MAX_SAVED` at the limit, insert. `remove` deletes if present.
- [ ] `list`: one joined query for status, price, seller state; `UNDER_REVIEW` for `TRUST_SAFETY_REVIEW`; batch `THUMBNAIL` photo URLs for available items only.
- [ ] Rate limit save and remove with `RATE_LIMIT_SAVE_PER_MIN` (gap G5).
- [ ] `SavedListingUnavailableListener` (`AFTER_COMMIT`, async): map status change, delete, and seller state to `SOLD`, `EXPIRED`, `REMOVED`, `DELETED`, `SELLER_SUSPENDED`; `UPDATE ... RETURNING user_id`; notify in chunks of 200; clear `unavailable_at` when the listing is live again. Failures are logged, never thrown.
- [ ] `SavedListingNotificationCopy` (English and Hindi, Hindi marked for native review).
- [ ] `SavedListingRetentionJob` (daily): delete rows with `unavailable_at` older than the setting; invalid value falls back to 90 with a warning.
- [ ] Set `saved` on `ListingCard` (batch) and `PublicListingResponse` (single) from `saved_listings`, for the caller only (anonymous callers get `false`).

### Mobile (`valuex-mobile`)
- [ ] `api_constants.dart`, `saved_listings_repository.dart`, domain model and Riverpod controller.
- [ ] Shared `SaveHeart` widget: optimistic toggle, rollback and snackbar on failure, 48 dp target, semantic label; use it on search cards, Home cards and the details action bar.
- [ ] `SavedItemsScreen` and route: paged list, unavailable cards greyed with "No longer available" and Remove only, "Under review" label, empty, error with Retry, pull to refresh, disabled "Add to cart".
- [ ] Wire the existing Profile "Saved Items" entry; add the `notification_deep_links.dart` entry.
- [ ] English and Hindi strings (`app_en.arb`, `app_hi.arb`, regenerate l10n).

### Documents
- [ ] Update LLD Part D with as-built notes and the changelog; `user-stories.md` US-073 status; Sprint-plan status line; `US-073-Testing-Guide.md`.

## 5. Test Plan

| Level | Cases | Covers |
|---|---|---|
| Unit | `SavedListingServiceTest`: save, idempotent save, limit, not live, unknown id, remove twice, list mapping (available, each unavailable reason, under review, no photo URLs for unavailable) | AC1, AC2, edge cases |
| Unit | Listener: each event maps to the right reason; review state does nothing; reinstated listing clears the mark; second event sends no second notification | AC3 |
| Unit | Retention job (default, changed setting, invalid value); copy test; settings registry range | rules |
| Integration (Testcontainers) | Save then list; two concurrent saves at the limit; sold, expired, removed, deleted and suspended-seller flows notify once per buyer; major edit shows under review with no notification; user A cannot see user B's list; `saved` flag on card and details | all |
| Controller | 200/204/409/404/401, paging, rate limit | API |
| Mobile | Heart optimistic update and rollback; Saved Items loading, empty, error, unavailable, under review states; deep link; Hindi at 200% text; accessibility | AC1 to AC3 |

Target above 90% line coverage on new and changed code.

## 6. Validation Checklist

- [ ] AC1, AC2 and AC3 each have a passing test.
- [ ] 201st save returns `ERROR_MAX_SAVED`; a non-live listing returns `ERROR_ITEM_UNAVAILABLE`.
- [ ] Repeat `PUT` and `DELETE` are harmless.
- [ ] Price shown is the current price.
- [ ] Review hold: label only, no notification; sold (including US-118 property close), expired, removed, deleted and suspended seller: notification once.
- [ ] Retention applies only to unavailable entries and follows the Admin setting.
- [ ] No endpoint can read or change another user's list; no listing ids are logged.
- [ ] Checkstyle, SonarQube, `dart format` and `flutter analyze` clean.

## 7. Open Gaps / Questions

| ID | Gap | Proposal |
|---|---|---|
| G1 | The LLD's migration number (V26) is stale; `main` is at V30. | Use the next free number at branch time and update the LLD. |
| G2 | The LLD gives no allowed range for `SAVED_LISTING_MAX`. | 10 to 500, default 200. Needs your confirmation. |
| G3 | LLD D.7 puts the heart on Home cards, but the Home feed model has no `saved` field. | Add `saved` to the Home feed response, or start with search and details only. Needs a decision. |
| G4 | The LLD does not say which package owns the code. | A new `savedlisting` module package, like `search` for saved searches. |
| G5 | The LLD names no rate limit for save and remove, but `RATE_LIMIT_SAVE_PER_MIN` exists. | Reuse it, with a separate counter from saved searches. |
| G6 | The story says "purchase saved items" but cart is Sprint 5. | Disabled "Add to cart" until Sprint 5, as in LLD D.7. |
| G7 | A reinstated seller or a republished listing needs `unavailable_at` cleared, and the only trigger is the same events. | The listener clears it, as D.5 step 4 says; the integration test covers it. |
| G8 | The Hindi notification texts need native-speaker review before release. | Mark in code and in the testing guide. |

**Status: Draft**
