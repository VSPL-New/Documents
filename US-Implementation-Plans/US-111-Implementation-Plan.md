# US-111: Home Page — Implementation Plan

## 1. Header

| Field | Value |
|---|---|
| Story ID | US-111 |
| Title | Home Page (backend feed, categories, promos; the mobile page is already built on a mock repository) |
| Sprint | Sprint 3 — Discovery & Search |
| Story Points | 8 (proposed in `Sprint-plan.md`; covers the backend endpoints and switching the app from the mock repository to them) |
| Repositories | valuex-backend, valuex-mobile |
| Dependency | US-011 (backend merged). US-012 is on its own branch and is not required. The heart (US-073) and the cart count (Sprint 5) are not built, so they stay stubbed. |
| Design | [Sprint-3-Discovery-Search-LLD.md](../LLD/Sprint-3-Discovery-Search-LLD.md) Part G (final, 2026-11-09), with the shared ranking in B.5 and the Admin settings in section 1.6 |

**Planning status:** Approved (2026-11-13). The user decided G1 to G10 (section 7) and approved the plan. Implemented 2026-11-13, see section 8.

## 2. Story Recap

**As a** logged-in buyer, **I want** a home page that shows items near me, lets me search, browse categories and reach the main areas of the app, **so that** I can find something to buy quickly and start from one familiar place.

**Acceptance criteria** (from `Documents/user-stories.md`, with the 2026-11-09 update):
- With an `ACTIVE` account, Home shows from top to bottom: a gradient header, a promo card, a "Browse" category row, "Featured Deals Near You" and the bottom navigation. The header shows my area and city, a cart icon and a notifications bell, then the search bar and camera icon.
- Location comes from the device when allowed; otherwise I am offered "Use my current location" and "Use my saved location". I can never type an address on Home. The place chosen is used only to find listings near it; it is not saved. Only its city and state go to the server, as transient search parameters that are never logged.
- Bell opens notifications (US-077) with an unread badge; cart opens the cart (US-019) with an item badge; search bar opens search (US-011); camera starts photo search for premium buyers, else the paywall (US-038).
- A promo card shows when a promo is active (title, short text, call-to-action) and opens the promo's target; with no active promo the section is hidden.
- "Browse" shows up to 15 popular L1 categories from the backend, ordered by Admin rank, each with image and name, plus an "Others" tile for the remaining enabled L1 categories; tapping a category opens its listings (US-011).
- "Featured Deals Near You" shows listing cards in two columns (image, title, INR price, city, seller rating, condition), Boosted and Priority first with their badge; a card opens details (US-012); "See All" opens the full list near me, in the same order, paginated (US-011).
- Pull to refresh. Bottom navigation goes to Home, Search, Sell, Chats and Profile. With the network down: last loaded content with a message and Retry, or an error state with Retry.

**Edge cases** (from the story): location denied once, permanently or off; location slow or outside India; no saved location; no saved addresses or the list fails to load; no listings near the place; fewer than 15 popular categories; promo expires while open; listing image fails; listing sold or removed while on screen; long titles, Hindi, 200% text; counts above 99; slow or partial responses; location changed during a refresh.

**Validation rules and error scenarios:** as in the story. Server side: only published, non-expired listings; at most `HOME_FEATURED_MAX` cards; promos in-app targets only; `ERROR_INVALID_FILTERS` (400) for a bad state; promo or category load failure returns 503. The location errors (`ERROR_LOCATION_*`, `NO_SAVED_LOCATIONS`, `ERROR_SAVED_LOCATIONS_FAILED`) stay in the app.

## 3. Design Reference

LLD Part G (G.1 to G.9) is the design; summary of what drives the work:

- **Endpoints.** `GET /api/v1/home/featured?city&state` returns `{items, nearMatch}` and `GET /api/v1/home/promos` returns at most `HOME_PROMO_MAX` active promos with text chosen by `Accept-Language`. Categories use the existing `GET /api/v1/categories/children?scope=POPULAR|OTHERS`. No badge endpoint is added.
- **Featured is a thin wrapper over search.** Same ranking as Part B (plan tier, then same city, then same state, then rating and recency), no text query, own listings excluded. "See All" opens the Part B search with the same `nearCity` and `nearState`, so order matches.
- **Data model.** New table `home_promos` (in-app targets only, enforced by a CHECK constraint, with a time window and Hindi text columns) and four Admin settings: `HOME_FEATURED_MAX` 20, `HOME_PROMO_MAX` 5, `CATEGORY_POPULAR_L1_MAX` 15, `CATEGORY_POPULAR_L2_MAX` 10. Promo rows are loaded by a SQL seed until an admin story exists.
- **Mobile.** Replace `MockHomeRepository` with `ApiHomeRepository` behind the existing `HomeRepository`; each section loads independently so one failure does not blank the page.
- **Docs to correct.** The old wording "never sent to the server" (US-111 text, HLD 05) becomes "never saved or stored; city and state are sent as query parameters for ranking only" (LLD 9.2 C2).

**What already exists in the code (checked 2026-11-13):**

| Piece | State |
|---|---|
| `search` module: `ListingSearchService.search(SearchRequest, callerId)`, `SearchRequest` with `nearCity`/`nearState`, `CityNormalizer`, `ListingEligibilityFilter`, `ListingCard` | Built (US-011, merged). No `browseNear` method exists, which the LLD names (G1/G2). |
| `DiscoverySetting` registry, `DiscoverySettings`, `DiscoverySettingsService` (`com.valuex.plans`) | Built, with no `HOME_*` or `CATEGORY_POPULAR_*` keys yet. |
| `CategoryService` popular limits | Hard-coded constants `POPULAR_L1_LIMIT = 15` and `POPULAR_L2_LIMIT = 10` (`CategoryService.java:26-27`, used at `:127`). `CategoryNode` has no image field. |
| Home promos, `home_promos`, `HomeController`, `HomeFeedService`, `PromoService` | Do not exist. Latest migration is `V26`; no branch holds `V27` or later. |
| Mobile Home page, location sheets, `HomeRepository` interface, `MockHomeRepository` | Built. Provider `homeRepository` returns `MockHomeRepository`. |
| Mobile categories on Home | Already real: `home_screen.dart` reads `categoryChildrenProvider` (POPULAR scope), not the mock. |
| Mobile `SearchRepository` | Already sends `nearCity`/`nearState`; `SearchListing.fromJson` already parses the card payload. |

## 4. Implementation Steps

### Backend — `valuex-backend`

- [x] **Migration** `V27__home_promos.sql` (LLD says `V29` provisionally; take the next free number at build time, see G6): create `home_promos` per LLD G.3 with the target and window CHECK constraints and the partial index; seed `HOME_FEATURED_MAX`, `HOME_PROMO_MAX`, `CATEGORY_POPULAR_L1_MAX`, `CATEGORY_POPULAR_L2_MAX` into `platform_settings` the same way V25 seeds the search keys (an Admin value is never overwritten). No `categories.image_key` column (G1): the app keeps choosing category artwork by taxonomy code.
- [x] **Settings registry:** add the four keys to `DiscoverySetting` with the LLD ranges (20 / 4 to 40, 5 / 1 to 10, 15 / 1 to 30, 10 / 1 to 20). No new cross-field rule: `HomeFeedService` clamps the size to `SEARCH_PAGE_SIZE_MAX` (G8).
- [x] **Taxonomy:** `CategoryService` reads the popular limits from `DiscoverySettings` instead of the two constants; update any test that references the constants. `CategoryNode` is unchanged (G1).
- [x] **Promos:** `HomePromo` entity (`search/domain`), `HomePromoRepository` (`search/infrastructure/persistence`), `HomePromoResponse` DTO, and `PromoService.active(locale)`: enabled promos with `starts_at <= now < ends_at`, ordered by `display_order`, limited to `HOME_PROMO_MAX`, Hindi columns when the locale is Hindi and the Hindi text exists, else English.
- [x] **Promo cache:** cache `homePromos` for 5 minutes with the locale in the key. The global cache TTL is 1 hour (`application.yml`), so add a per-cache TTL of 5 minutes in `RedisConfig` (G5).
- [x] **Search without the rate limit (G2):** in `ListingSearchService`, split `search` into the rate check followed by the existing pipeline, and add `browseNear(SearchRequest, callerId)`, which runs the same validation, ranking and eligibility pipeline but skips `checkRate`. `search` keeps its `RATE_LIMIT_SEARCH_PER_MIN` behaviour unchanged. The LLD already names `browseNear`; no separate Home rate limit is added.
- [x] **Featured feed:** `HomeFeedService.featured(callerId, city, state)` builds a `SearchRequest` (no query, `sort` relevance, page 0, size = `HOME_FEATURED_MAX` clamped to `SEARCH_PAGE_SIZE_MAX`, `nearCity`, `nearState`) and calls `browseNear`; sets `nearMatch` by city only (G4: true when any returned card's city equals the normalised buyer city, through `CityNormalizer`); returns the advisory `NO_LISTINGS_NEAR_YOU` with an empty list when there are no listings at all. City and state are never logged.
- [x] **Controller:** `HomeController` with `GET /api/v1/home/featured` (`Cache-Control: private, max-age=60`) and `GET /api/v1/home/promos` (reads `Accept-Language`), OpenAPI annotations like `SearchController`; `ApiResponse` envelope; 503 when the dependency is down; confirm the default authenticated rule in `SecurityConfig` already covers `/api/v1/home/**` for `ACTIVE` accounts.
- [x] **Seed data:** `V27` ships no promo rows, so the promo section stays hidden until the product team supplies promos (G9). Add an optional dev-only seed script, kept out of the Flyway migrations, for local testing.

### Mobile — `valuex-mobile`

- [x] **Constants and client:** add `homeFeatured` and `homePromos` to `api_constants.dart`.
- [x] **`ApiHomeRepository`** (`features/home/data/`) implementing `HomeRepository`: `promos()` from `/home/promos`; `featuredListings(location)` from `/home/featured` with `city` and `state` only (never area, pincode or coordinates), parsing cards with the existing `SearchListing.fromJson` and mapping to the Home `Listing` (badge to `isBoosted`/`isFeatured`, `STARTING_FROM` to `startingFrom`, `cardUrl` to `image`, condition code to `ListingCondition`); `badges()` per G7.
- [x] **Promo entity and card:** extend `Promo` with the target type and value and the server image; tapping routes by target (`CATEGORY` opens category results, `SEARCH` opens search with the text, `LISTING` opens details) using the existing search and listing routes.
- [x] **Providers:** switch `homeRepositoryProvider` to `ApiHomeRepository`; keep the mock for widget tests and, if the app already has a config flag for it, as the Dev fallback (check `app_config.dart`).
- [x] **Sections fail alone:** a failed promo call hides only the promo card; a failed featured call shows the section error with Retry; stale content stays with the offline banner. Check what the current `home_screen.dart` already does and add only what is missing.
- [x] **"See All" and card taps:** open the existing search with the same `nearCity`/`nearState` and no query; card tap opens US-012 details.
- [x] **Strings:** add any missing error and empty-state texts (`ERROR_HOME_LOAD_FAILED`, `NO_LISTINGS_NEAR_YOU`, and so on) to the English and Hindi ARB files, then regenerate localisations.
- [x] **Language header (G3):** the app sends no `Accept-Language` today. Make the API client send the app language (English or Hindi, from the US-044 language setting) on every request, and read it in `HomeController`; Hindi falls back to English when a promo has no Hindi text.
- [x] **Badges (G7):** read the unread count from the existing US-077 notifications endpoint if the app already has a data source for it; if it does not, return 0 and record the deviation. The cart count stays 0 behind a `CartBadgeSource` stub until Sprint 5, and `saved` stays `false` until US-073.

### Tests and delivery (CLAUDE.md section 5)

- [x] Branch each repo from an up-to-date `main` (`feature/US-111-home-page`). The current branch in every repo is `us-012-view-listing-details`; the mobile working tree holds uncommitted US-012 test changes, so decide with the user how to handle them before branching.
- [x] Backend: `mvn clean verify`, `mvn checkstyle:check`, SonarQube scan; coverage above 90% on new code. Mobile: `dart format lib test`, `flutter analyze`, `flutter test`.
- [x] Update LLD Part G with an "As built" section; fix the "never sent to the server" wording in `user-stories.md` (line 5274 region), US-111's Backend Notes, and HLD 05 if it carries it; update the Sprint 3 row in `Sprint-plan.md` if the points or scope change.
- [x] Write `Documents/Manual Testing Guides/US-111-Testing-Guide.md`.
- [ ] Commit, push and PR only after separate approvals, with Conventional Commits titles (`feat(US-111): home page feed, promos and categories`).

## 5. Test Plan

### Backend

| Test | Covers |
|---|---|
| `PromoServiceTest`: window start and end edges, disabled promo, expired promo, Hindi text with and without Hindi columns, limit of `HOME_PROMO_MAX`, display order, cache hit and per-locale key | AC promo card; edge: promo expired or removed |
| `HomeFeedServiceTest`: request built with the near place and the clamped size (including `HOME_FEATURED_MAX` above `SEARCH_PAGE_SIZE_MAX`); own listings excluded; `nearMatch` by city only (true for a city alias, false when no card is in the buyer's city); empty result gives `NO_LISTINGS_NEAR_YOU`; city and state not logged | AC featured deals; edges: no listings near, long names |
| `ListingSearchServiceTest` additions: `browseNear` never touches the rate limit, however many calls; `search` still enforces it exactly as before | G2 |
| `DiscoverySettingTest`/`DiscoverySettingsTest`: new keys default, range, parse errors; limit clamp from G8 | Settings validation |
| `CategoryServiceTest`: popular lists honour the L1 and L2 settings (including values other than 15 and 10), fewer than the limit returned as is | AC "Browse"; edge: fewer than 15 categories |
| `HomeControllerTest` (MockMvc): envelope, `Cache-Control`, invalid state gives 400 `ERROR_INVALID_FILTERS`, header locale, unauthenticated gives 401 | API contract |
| Integration (existing search integration style): Priority and Boosted first, then same city, then recency; city alias match; no near match still returns listings; promos active versus expired; each endpoint fails alone when its dependency is down | AC ordering; partial failure |
| Migration test: constraints reject a non-in-app `target_type` and `ends_at <= starts_at`; seeded settings are not overwritten on re-run | Data rules |

### Mobile

| Test | Covers |
|---|---|
| `ApiHomeRepository` mapping from API payloads (badge, price qualifier, condition, rating absent, image URL), and that only city and state are sent | AC listing cards; location privacy |
| Section failure states: promo fails (card hidden), featured fails (error with Retry), both fail, offline with stale content and banner | AC network down; edge: partial responses |
| Promo routing for `CATEGORY`, `SEARCH` and `LISTING` targets; no promo hides the section | AC promo |
| API client sends `Accept-Language` for English and Hindi | G3 |
| "See All" and card taps; badges above 99 show "99+"; pull to refresh; location change during refresh | AC and edges |
| Hindi at 200% text, long titles, accessibility guidelines and heading tests for Home | Validation rules (US-110, US-099) |
| Existing Home widget tests keep passing on the mock | Regression |

## 6. Validation Checklist

- [x] Every acceptance criterion above is covered by a test or a manual test case in the testing guide.
- [x] Only published, non-expired listings are shown, at most `HOME_FEATURED_MAX`, Boosted and Priority first; own listings never appear.
- [x] Prices in INR with Indian digit grouping; rating shown with one decimal or hidden; condition from the listing condition values.
- [x] Categories, their order and names come from the backend, not hard-coded in the app; limits come from the Admin settings.
- [x] Promo targets are in-app only (database constraint) and promo text renders as plain text.
- [x] Only city and state reach the server; coordinates, area and pincode do not; neither value is logged or stored on the server.
- [x] Location permission is requested on Home with an explanation, not at app start; no address entry or Google Places call from Home.
- [ ] Every control has a 48 dp tap area and a label; titles are headings; contrast and text-size rules pass; Home is in the accessibility and heading tests.
- [x] Each section degrades alone; error messages match the story's error scenarios in English and Hindi.
- [ ] Checkstyle, tests, coverage above 90%, SonarQube clean; LLD, user story text, HLD wording, testing guide updated.

## 7. Decisions and Open Questions

All ten gaps from the first draft were decided by the user on 2026-11-13. No question is open.

| # | Gap | Decision | Where it lands |
|---|---|---|---|
| G1 | Category `imageKey` versus code-based artwork already in the app | Skip `image_key`; keep choosing category artwork by taxonomy code. | Migration, `CategoryNode` unchanged |
| G2 | `browseNear` missing; `search()` is rate limited per user | Build the feed on `search()` through a small method (`browseNear`) that skips the search rate limit. `search` is unchanged. | Backend step "Search without the rate limit" |
| G3 | No `Accept-Language` handling in backend or app | App sends its language on every request; `HomeController` reads it; English fallback. | Mobile step "Language header" |
| G4 | `nearMatch` rule | By city only (through `CityNormalizer`); no state on the card. | `HomeFeedService` |
| G5 | Promo cache TTL (global is 1 hour) | Per-cache TTL of 5 minutes for `homePromos`, locale in the key. | `RedisConfig` |
| G6 | Migration number (LLD says V29, latest is V26) | Take the next free number at build time (V27 today) and rebase if another Sprint 3 story lands first. | Migration step |
| G7 | Badge sources | Unread count from the US-077 endpoint if the app has a source, else 0 and a recorded deviation; cart 0 behind a stub; `saved` false until US-073. | Mobile step "Badges" |
| G8 | `HOME_FEATURED_MAX` versus `SEARCH_PAGE_SIZE_MAX` | Clamp in `HomeFeedService`; no new cross-field rule. | `HomeFeedService`, tests |
| G9 | No promo content supplied | `V27` ships no promo rows (section hidden); dev-only seed script outside Flyway. | Seed data step |
| G10 | LLD Part G drifts from the code | The plan follows the code; LLD Part G gets an "As built" section (categories already real, `Listing` already has `startingFrom`, `isBoosted`, `isFeatured`, `image`). | Delivery step |

**Still to confirm during implementation, not blocking:** whether the app already has a notifications data source (G7); how the current branches and the uncommitted US-012 mobile test changes are handled before branching (section 4, Tests and delivery).

**Status:** Approved (2026-11-13). Implemented 2026-11-13 on `feature/US-111-home-page` (valuex-backend, valuex-mobile); not committed, pushed or reviewed. See section 8.

## 8. Implementation Deviations and Results (2026-11-13)

**Deviations from the plan**

| # | Plan | As built | Why |
|---|---|---|---|
| 1 | Card tap and a `LISTING` promo open US-012 details | Both say "Coming soon" | The buyer details screen is in the open US-012 mobile PR #65 and is not on `main`. When it merges both open `/listing/:id` (small follow-up) |
| 2 | Badges (G7): a `CartBadgeSource` stub | `ApiHomeRepository.badges()` returns `HomeBadges()` (cart 0); the unread count already came from `NotificationsRepository` | The notifications source existed, and a class that only returns 0 was not worth adding |
| 3 | Dev-only promo seed script outside Flyway | Not created; the SQL inserts are in the testing guide (case B) | The guide covers local testing; a script was optional |
| 4 | Providers: mock as Dev fallback "if a flag exists" | No flag exists in `AppConfig`; the mock is used in tests only | As the plan allowed |
| 5 | Fix the "never sent to the server" wording in `user-stories.md` and HLD 05 | No change needed | The US-111 story text already carried the corrected wording (2026-11-09) and HLD has none left; line 5274 is about seller coordinates and stays true |
| 6 | Mobile "sections fail alone" work | No screen change beyond the promo tap | The screen already behaved that way; tests were added for it |
| 7 | Generated Riverpod file via `build_runner` | `home_providers.g.dart` hash updated by hand | Dart cannot reach pub.dev through the corporate proxy here. The hash is SHA-1 of the annotated function source (checked against the old value); CI regenerates and diffs, which confirms it |

**Results**

- Backend: `mvn clean verify` green, 1,974 tests, 0 failures; checkstyle clean; JaCoCo gate met, project coverage 95.5%; new classes 100% except `RedisConfig` (the new cache-TTL bean runs only with a real Redis cache manager). `HomeIntegrationTest` (PostgreSQL) 12 of 12.
- SonarQube (local server): new-code coverage 93.2%, duplication 0.18%. Four findings in this story's code were fixed (two redundant `@ApiResponses` wrappers in `HomeController`, two lambdas in new `ListingSearchServiceTest` cases). No open issue remains in a file this story created. The gate still reads ERROR on `new_violations` (77) because this is the project's first analysis, so every older issue counts as new; none of them is in code this story changed (for example `ListingSearchService` line 157 and `CategoryService` line 138 pre-date it).
- Mobile: `dart format` and `flutter analyze` clean; with CI's flags (`--dart-define=SKIP_PIXEL_CONTRAST=true`) 1,383 tests pass and 3 fail (two Google sign-in contrast checks and an L3 artwork test); the same 3 fail on a clean `main` with this work stashed. New files `api_home_repository.dart` and `promo_routes.dart` are at 100% line coverage.
- Environment only (nothing committed): on this machine Testcontainers needs `JAVA_TOOL_OPTIONS="-Dapi.version=1.44 -Duser.timezone=Asia/Kolkata"` (Docker 29 and the legacy `Asia/Calcutta` zone name).
- Not yet done: the manual checks in the testing guide, the screen reader pass (validation item on accessibility), and the HLD/Sprint-plan row review.

**Status:** Approved (2026-11-13). Implemented; awaiting approval to commit, push and open pull requests.
