# US-011: Browse and Search Listings - Implementation Plan

## 1. Header

| Field | Value |
|---|---|
| Story | US-011 - Browse and Search Listings |
| Sprint | Sprint 3 - Discovery & Search |
| Story points | 8 |
| Repos involved | valuex-backend (search API, query building, ranking, card assembly), valuex-mobile (search screen, filter sheet, results, category browsing and Home wiring). No `valuex-ai` change. |
| Dependencies | US-009 and US-120 (built and merged: backend PRs #54, #55, #56, mobile PR #63; `main` of both repos is at the merge). Photo variants (US-128) are merged and supply the card and thumbnail images. |
| Date | 2026-11-09 |
| Design source | [Sprint 3 LLD](../LLD/Sprint-3-Discovery-Search-LLD.md) Part B (B.1 to B.11), section 1.4 (shared blocks) and 1.6 (Admin settings); LLD Part A "As built" (A.10) for what US-120 actually delivered |
| Branches (proposal) | `feature/US-011-browse-search-listings` from the latest `main` in `valuex-backend` and in `valuex-mobile` |
| Flyway number | None. The `SEARCH_*` and `RATE_LIMIT_*` settings were seeded by V25. |

## 2. Story Recap

**As a** buyer **I want to** browse and search for items **so that** I can find what I need.

### Acceptance Criteria (user-stories.md US-011, with the 2026-10-25 and 2026-11-09 updates)

| ID | Behaviour |
|---|---|
| AC1 | Given I am on the home page, when I enter search keywords, I see relevant listings ranked by relevance. |
| AC2 | When I browse by category (L1, then L2, then L3; popular first, then Others), I see listings in that category. |
| AC3 | When I apply filters (price, condition, location, the L3 category's facets, Real Estate transaction intent), results are filtered accordingly. |
| AC4 | When I scroll down, more results load (pagination). |

**Edge cases:** no results; special characters or very long text; several filters at once; a location outside India; `priceMin` above `priceMax`; Real Estate without an intent; a disabled category; index lag (a listing sold a moment ago); OpenSearch down; paging past the window.
**Validation rules:** query at most 200 characters (the setting `SEARCH_QUERY_MAX_LENGTH`); only published, non-expired listings of active sellers; paid plans rank higher but a weak text match never beats a strong one; a minimum relevance applies to text queries; the chosen place (city and state) is used only for ranking and is never stored or logged.
**Errors:** `NO_RESULTS_FOUND` (advisory, 200), `ERROR_INVALID_FILTERS`, `ERROR_QUERY_TOO_LONG`, `ERROR_INVALID_PRICE_RANGE`, `ERROR_INTENT_REQUIRED`, `ERROR_INTENT_NOT_SUPPORTED`, `ERROR_SEARCH_UNAVAILABLE`, rate limit (429).

## 3. Design Reference

LLD Part B (API in B.4, ranking in B.5, flow in B.6, mobile in B.8, errors in B.9, tests in B.11) and LLD 1.4 (listing card, photo variants per surface, city normaliser, eligibility filter).

### Verified Implementation Anchors (checked in the merged code on 2026-11-09)

| Area | Finding and consequence |
|---|---|
| Search port | `ListingSearchPort` has only index operations (`ensureIndex`, `upsert`, `delete`, `existingIds`, `idsAfter`, `count`). A `search(...)` operation is added; OpenSearch types stay inside `OpenSearchListingSearchAdapter` (it has a read client with a 2 s socket timeout and a write client). |
| Index document | `ListingSearchDocument` holds `listingId`, `sellerId`, `transactionIntent`, `title`, `description`, `searchText`, `category {l1..l3 codes and names}`, `categoryCodes`, `profileCode`, `price`, `priceQualifier`, `condition`, `location {city, cityKey, state, stateKey, locality}`, nested `attributes {key, type, keywordValue, numberValue, booleanValue}`, `sellerRating`, `planTier`, `planBadge`, `publishedAt`, `expiresAt`, `primaryMediaId`, `indexedAt`. This is everything a card needs, so cards are built from `_source` plus one photo lookup. Mapping `listings-mapping-v1.json` is `dynamic: strict`; `title` has `.prefix` and `.exact` subfields; `city`, `state` and `locality` are stored but not searchable. |
| Eligibility | `ListingEligibilityFilter.retainLive(ids)` already checks status, expiry, seller `ACTIVE` and the enabled category chain in one query. |
| Settings | `PlatformSettingsService.discovery()` returns the cached `DiscoverySettings`; all 27 keys (`SEARCH_TIER_WEIGHT` to `SEARCH_FACET_BUCKETS`, `RATE_LIMIT_SEARCH_PER_MIN`) exist with defaults and ranges (`DiscoverySetting`). |
| Taxonomy | `CategoryService.children(parentCode, Scope)` serves browsing; `findSelectableLeaf` and `requireSelectableLeaf` serve L3 only. There is **no helper for an L1 or L2 code** (level, enabled, descendants) and `CategoryLeaf.group()` (Real Estate when the profile code starts with `PROP_`) exists for L3 only. `ListingSchemaService.schemaFor(leaf)` returns `transactionIntents` and fields, but the field DTO does not carry the profile's `filterable` flag. |
| Photos | `ListingPhotoLinkPort.urls(listingId, mediaIds)` (US-128) works for **one listing**. A page of 20 cards would run it 20 times, so a batch method is added (step 4.2). It lives in `media/port`, not in the search package as the LLD sketched. |
| Rate limit | `RedisCacheService.checkRateLimit(key, max, window)` returns a boolean; `RateLimitedException` and `ServiceUnavailableException` (503) exist. |
| Security | `SecurityConfig` ends with `anyRequest().authenticated()`, so `/api/v1/search/**` needs a valid token without any change. The caller comes from `SecurityContext.getCurrentUserId()`. |
| Config | `valuex.search.enabled` defaults to `true`; the test profile sets it to `false`, and then `OpenSearchListingSearchAdapter` is not a bean (it is conditional on the switch). |
| Mobile | Home search bar, the Search bottom-nav item, category tiles, "See All" and listing cards all call `showComingSoon` (`home_screen.dart`, `main_nav.dart`). `CategorySelectionScreen` lists categories and says opening them "comes with search (US-011)". `ListingRepository.categoryChildren` already calls `/categories/children` with a scope. The Home `Listing` entity has `priceInr` as a whole-rupee `int`, one `image` string and an `isBoosted` flag. `ApiPage` and the Dio `api_client` exist. `homeLocationControllerProvider` supplies city and state. |
| US-120 on a real cluster | Nothing in US-120 ran against a real OpenSearch (stub tests only). US-011 is the first real use, so the plan starts with a spike (4.1). |

## 4. Implementation Steps

### 4.1 Branches and OpenSearch spike
- [x] Cut `feature/US-011-browse-search-listings` from `main` in both repos; run the backend and mobile baselines. Set up the local container runtime first if decision G8 is accepted (`brew install colima docker`).
- [x] Spike before coding queries: start a real OpenSearch 2.17 (`docker compose up -d opensearch`, or `brew install opensearch` where Docker is not available), start the backend, publish three listings, and confirm the index and aliases are created, the documents arrive, and a hand-written `function_score` query with the Painless script from B.5 runs. Fix any mapping or serialization surprise in US-120 code first (small commits on this branch, noted in the PR).

### 4.2 Backend: ports, settings and shared pieces
- [x] `ListingSearchQuery` (immutable port-level criteria: text, category scope, intent, price range, conditions, city and state filters, facet filters, near place, sort, page, size, excluded seller, disabled category codes, ranking parameters, window) and `ListingSearchResult` (hits with their `_source` card fields, total, facet results) in `search/application/port`. `ListingSearchPort.search(ListingSearchQuery)` is added. OpenSearch query building lives in `search/infrastructure/opensearch/OpenSearchQueryBuilder` (so the application layer has no OpenSearch types); this replaces the LLD's `SearchQueryBuilder` under `application/service`.
- [x] `DisabledListingSearchPort` (a bean only when `valuex.search.enabled=false`) that throws `ServiceUnavailableException("ERROR_SEARCH_UNAVAILABLE")`, so the controller, service and tests work with the switch off.
- [x] `ListingPhotoLinkPort`: add a batch method (for example `urlsForPrimaryPhotos(Map<UUID listingId, UUID mediaId>)`) that confirms each photo belongs to its listing and is a ready listing photo in one query, reads variants for the page in one query, and creates fallback links only where copies are missing. Update `ListingPhotoLinkAdapter` and its tests.
- [x] `CategoryService`: add `resolveScope(code)` returning level, enabled flag and group for an L1, L2 or L3 code (enabled means the category and all its ancestors are enabled), throwing the existing `CATEGORY_NOT_FOUND` otherwise; and `leafCodesUnder(code)` if the facet and intent checks need it. Real Estate scope is decided from the profile codes of the leaves under it (see gap G2).
- [x] `SearchFacetCatalog`: for an L3 code, the filterable attributes of its profile (key, label, type `OPTION`/`NUMBER`/`BOOLEAN`, option codes and labels) read from `metadata_profile_attributes` and `attribute_*` with the dictionary labels; cached per category code for 5 minutes with the cache mechanism the taxonomy services already use, evicted by the taxonomy import.
- [x] `DisabledCategoryProvider`: codes of categories that are disabled or sit under a disabled parent, cached for 60 seconds (LLD B.6.1). A disable takes effect before any reindex.

### 4.3 Backend: validation, query and ranking
- [x] `SearchRequest` (query parameters of LLD B.4) and `SearchRequestValidator`: trim and strip control characters from `query`; length limit from `SEARCH_QUERY_MAX_LENGTH`; `priceMin`/`priceMax` not negative, at most two decimals, ordered; `condition` codes from `ListingCondition`; `state` must be a known state (`IndianStates.canonical`), `city` normalised with `CityNormalizer`; `nearCity`/`nearState` normalised the same way (never logged); `facet` grammar `key:code`, `key:min..max`, `key:true`, only with an L3 `category`, keys and option codes checked against `SearchFacetCatalog`, at most `SEARCH_MAX_FACETS`; `sort` allow-list; `page` and `size` bounds from `SEARCH_PAGE_SIZE_*`; `includeFacets` honoured only for an L3 on page 0. Errors and HTTP codes per LLD B.9.
- [x] Intent rules: a Real Estate scope without `transactionIntent` gives `ERROR_INTENT_REQUIRED`; an intent the L3 does not support (from `ListingSchemaService.schemaFor(leaf).transactionIntents`) gives `ERROR_INTENT_NOT_SUPPORTED`; condition filters are rejected for Real Estate; price sorts need an intent for Real Estate. A search with no category, or a goods category, never returns property listings (filter: no `transactionIntent`); a Real Estate scope returns only the chosen intent. The applied intent is echoed as `appliedIntent`.
- [x] `OpenSearchQueryBuilder`: filters (`categoryCodes`, `transactionIntent`, price range, `condition`, `cityKey`/`stateKey`, one `nested` filter per facet), `must_not` for the caller's own `sellerId` and for disabled category codes, `function_score` with `boost_mode: multiply` and the Painless `script_score` of B.5 fed from the `DiscoverySettings` snapshot as script parameters (null-safe on `sellerRating`), the text query exactly as in B.5 (`match_phrase` on `title.exact`, `multi_match` with `operator: and` then `minimum_should_match`, fuzziness only for terms of `SEARCH_FUZZY_MIN_TERM_LENGTH` or more, category-name match, plain-text only, never `query_string`), `min_score` only when there is a text query, sorts (`NEWEST`, `PRICE_ASC`, `PRICE_DESC` with `publishedAt` tie-break), `from`/`size` capped by `SEARCH_MAX_WINDOW`, `track_total_hits` up to the window, and facet aggregations (`nested` `terms` of `keywordValue` limited to `SEARCH_FACET_BUCKETS`, `stats` of `numberValue`) that leave out the facet's own selection. Field names and sort keys come from allow-lists.
- [x] `OpenSearchListingSearchAdapter.search`: executes with the search client; wraps transport failures in `SearchIndexException`; adds a programmatic Resilience4j circuit breaker for search calls (the same style as `AiGatewayConfig`; the breaker was deferred from US-120, LLD A.10) and maps an open breaker or a failure to `ERROR_SEARCH_UNAVAILABLE` (503).

### 4.4 Backend: service, controller, metrics
- [x] `ListingSearchService.search(request, callerId)`: validate, resolve the category, build the criteria with the current settings, call the port, run `ListingEligibilityFilter.retainLive` on the hit ids (a page may hold fewer than `size`; `hasNext` comes from the OpenSearch total capped at the window), assemble cards (`ListingCard`: `listingId`, `title`, `price`, `priceQualifier`, `transactionIntent`, `city`, `condition`, `sellerRating`, `badge`, `photo {thumbnailUrl, cardUrl, expiresAt}`, `publishedAt`, `category {l3Code, l3Name}`, `saved`) from `_source` and the batch photo call, and return `SearchPage` (`items`, `page`, `size`, `totalItems`, `hasNext`, `appliedIntent`, `facets`, `advisory`). An empty first page carries `advisory.code = NO_RESULTS_FOUND`. `saved` is `false` until US-073 (gap G1).
- [x] `SearchController` `GET /api/v1/search/listings` returning `ApiResponse<SearchPage>`, with the OpenAPI annotations the other controllers use; per-user rate limit from `RATE_LIMIT_SEARCH_PER_MIN` (key per user, 1 minute window) throwing `RateLimitedException`.
- [x] Logging: never log the query text, `nearCity`, `nearState` or any filter value; log request id, result count and latency. Check that no existing request logging filter writes query strings.
- [x] Metrics: `search.requests.total{result}`, `search.latency` timer, `search.results.empty.total`, `search.eligibility.dropped.total`.
- [x] Config: no new `application.yml` keys are expected (circuit breaker numbers go under `valuex.search.opensearch`, deployment values); document them in the README search section.

### 4.5 Mobile (`valuex-mobile`, new feature `lib/features/search`)
- [x] `domain`: `SearchCriteria` (immutable, `copyWith`, equality; reusable by US-066), `SearchListing` and `SearchPage`, `SearchFacet` and `FacetBucket`, `SearchSort`, `TransactionIntent`.
- [x] `data`: `SearchRepository` (Dio, same pattern as `ListingRepository`) calling `ApiConstants.searchListings`; maps the response and the error codes (`ERROR_QUERY_TOO_LONG`, `ERROR_INVALID_PRICE_RANGE`, `ERROR_INVALID_FILTERS`, `ERROR_INTENT_REQUIRED`, `ERROR_INTENT_NOT_SUPPORTED`, `ERROR_SEARCH_UNAVAILABLE`, 429) to messages in `api_error_messages.dart`. Sends only city and state of the Home place (`nearCity`, `nearState`), never coordinates.
- [x] `presentation`: `SearchScreen` (search field with a 200 character limit and counter, 400 ms debounce, popular categories as the empty state), `SearchResultsView` (infinite scroll with pages of 20, pull to refresh, skeletons, no-results state with "clear filters", error state with Retry), `FilterSheet` (price range with min above max shown inline, condition chips, state and city, the L3 facet form built from the response `facets`), category browsing reusing `categoryChildren` with `POPULAR` then `OTHERS`, and a Riverpod controller keeping the criteria, the pages and the latest request id so a response for an older request is ignored.
- [x] Card: the Home `ListingCard` is extended (or fed through a small card view model) to show a network photo (`cardUrl`, with `cacheWidth` so a 600 px copy is never decoded at full size), paise-accurate prices, a "Starting from" label when `priceQualifier` is set, and the "BOOSTED" or "Featured" badge. The Home mock path keeps working unchanged until US-111.
- [x] Wiring: Search bottom-nav item, Home search bar and the Home category tiles, "See All" and `CategorySelectionScreen` open the search routes (new names in `route_names.dart`, `app_router.dart`); a Real Estate category first shows a minimal Buy, Rent or Lease chooser (decision G3), and the chooser reopens if the backend answers `ERROR_INTENT_REQUIRED`.
- [x] Strings in the English and Hindi ARB files (`flutter gen-l10n`), 48 dp tap targets, headings and semantic labels, readable at 200% text; register the screens in `all_screens_accessibility_test.dart` and `screen_headings_test.dart`; satisfy `test/l10n/no_hardcoded_strings_test.dart`.
- [x] `dart format lib test`, `flutter analyze`, tests; run `build_runner` if any `@riverpod` source changes and commit the generated files.

### 4.6 Documentation and quality
- [x] Backend README: search API section (parameters, example call, errors, the real-cluster setup).
- [x] After implementation: `Documents/Manual Testing Guides/US-011-Testing-Guide.md`; LLD Part B "As built" note for every deviation (at least the query builder moving to the adapter package, the batch photo call, the category scope helper, the Real Estate chooser scope).
- [x] Checkstyle, full backend and mobile tests, coverage above 90% for new code, SonarQube where a server is available, before any push. Never push or open a pull request without asking.

## 5. Test Plan

### 5.1 Backend unit
- [x] `SearchRequestValidatorTest`: every rule and code (long query, control characters, price range, bad facet key, bad option code, too many facets, facet without an L3, unknown state, condition for Real Estate, intent missing and unsupported, page and size bounds, `includeFacets` rules), and facet grammar.
- [x] `OpenSearchQueryBuilderTest`: serialize the built request to JSON and compare with expected fragments (filters, `must_not` own and disabled, intent, goods-only filter, nested facet filters, aggregations that skip their own selection, window cap, sorts, `min_score` only with a text query, script parameters taken from the settings snapshot).
- [x] `ListingSearchServiceTest` (mocked port, eligibility filter, photo port): eligibility drops hits and `hasNext` still follows the total; card assembly; advisory on an empty first page; unavailable port gives 503; rate limit; no query text in logs.
- [x] `ListingPhotoLinkAdapterTest` additions for the batch method; `CategoryServiceTest` additions for `resolveScope`; `SearchFacetCatalogTest`; `DisabledCategoryProviderTest`; `DisabledListingSearchPortTest`; breaker behaviour in the adapter test (HTTP stub).
- [x] `SearchControllerTest` (request binding, envelope, error codes).

### 5.2 Backend integration (Testcontainers PostgreSQL and OpenSearch; skipped without Docker)
- [x] Index a fixture corpus and run: keyword, category (L1, L2, L3), price, condition, city and state, facet, Real Estate intent searches (AC1 to AC3).
- [x] Ranking golden-order tests: exact title first; Priority above Basic at a similar score; a weak match with a high tier does not beat a strong match; recency and rating effects; a missing rating is neutral; the chosen place lifts same-city then same-state listings.
- [x] Disabled category and disabled parent excluded; own listings excluded; an indexed listing sold a moment ago is dropped by the re-check; empty advisory; paging and the window cap (AC4); special characters and a 200 character query; OpenSearch stopped gives 503; unauthenticated call is 401; goods search never returns property listings.
- [x] If Docker is not available on the build machine, run these against a locally installed OpenSearch and say so in the report (the US-120 lesson).

### 5.3 Mobile
- [x] Repository payload and error mapping tests; controller tests for debounce and stale responses; infinite scroll; filter sheet validation (min above max inline); empty, error and Retry states; Real Estate intent chooser; Hindi at 200% text; accessibility guidelines and headings tests; Home wiring (search bar, tiles and nav open the new screens).

## 6. Validation Checklist

- [x] AC1: a keyword search returns ranked, relevant listings; exact title matches come first.
- [x] AC2: browsing L1 to L2 to L3 (popular, then Others) opens that category's listings.
- [x] AC3: price, condition, city and state, facets and intent filter correctly and combine with AND.
- [x] AC4: results page on scroll; a page past the window is empty with `hasNext = false`.
- [x] Edge cases: no results advisory, special characters, long text (rejected), many filters, a state outside India rejected, `priceMin` above `priceMax`, Real Estate without an intent, disabled category, index lag, OpenSearch down, rate limit.
- [x] Only published, non-expired listings of active sellers; the caller's own listings are not shown; property and goods are never mixed.
- [x] Paid plans rank higher but a weak match does not win; a minimum relevance applies to text queries.
- [x] No PII in responses; the query text and the chosen place are never stored or logged.
- [x] Ranking numbers, limits and the rate limit come from the Admin settings, not constants.
- [x] Strings in both languages, accessibility tests pass; Checkstyle, tests, coverage above 90%, SonarQube (where available) pass; testing guide written.

## 7. Decisions and Open Gaps

### Decided by the user (2026-11-09)
1. **G1 Saved flag: accepted.** `saved` is in the response and always `false` until US-073 fills it from one batch query on `saved_listings`.
2. **G3 Real Estate chooser: included.** US-011 ships a minimal Buy, Rent or Lease chooser (a bottom sheet with three options), shown when a Real Estate category is opened or when the backend answers `ERROR_INTENT_REQUIRED`. US-118 builds the full property flow on top of it.
3. **G4 Screens: build what is missing.** The Home screen already has the search box and category tiles, but they only show "coming soon". This story creates the search screen, results list, filter sheet, category browse screens and the intent chooser (4.5), following the design system and the Home card, with no Figma frames. The Home search box, the Search bottom-nav item, the category tiles and "See All" are wired to them.

### Confirmed by the user (2026-11-10)
4. **G2 Real Estate scope above L3: confirmed with the recommendation below.** Checked on the loaded taxonomy (`valuex_dev`): the only category with property leaves is the L1 "Real Estate" (37 leaves, all with `PROP_` profiles) and its five L2 groups (Commercial and Workspaces 8, Shared and Managed Living 6, Homes and Residences 9, Land and Plots 7, New Developments 7). None of them contains a goods leaf, and no goods L1 or L2 contains a property leaf, so nothing is mixed today.
   - **Rule:** a scope is Real Estate when all its enabled leaves have `PROP_` profiles; it is goods when none has. This is what `CategoryService.resolveScope` returns.
   - **Recommendation for a mixed scope:** treat it as goods (property listings are excluded) rather than rejecting the request, so a future taxonomy edit can never show property in a goods list or break search. A taxonomy-import validator check (or a unit test over the seed data) fails the import when an L1 or L2 mixes the two, so the case is caught when the taxonomy changes and never reaches a buyer. The same rule keeps "a search with no category returns goods only" true.
5. **G8 Cluster for real-cluster tests: Colima confirmed.** Docker is not installed here, and that has limited every story so far (the Testcontainers tests had to be run through local copies). Options, with the recommendation first:
   - **Recommended:** install Colima and the Docker CLI with Homebrew (`brew install colima docker`, `colima start`). It is lighter than Docker Desktop and needs no licence. It runs the project's own `docker-compose.yml` OpenSearch 2.17.1 (the version the code targets and the CI service uses) and lets the Testcontainers tests run locally for this and every later story. If Testcontainers does not find the socket, set `DOCKER_HOST` to the Colima socket.
   - **Fallback:** `brew install opensearch` installs 3.9.0, not 2.17.1, and the backend client is `opensearch-java` 2.20. Basic indexing and search normally work across that gap, but it is not guaranteed and a 3.x result is weaker evidence for production. Use it only if Colima is not wanted, and note the version in the report.
   - **CI** (GitHub Actions has Docker) runs the Testcontainers tests on every pull request and stays the authoritative run; the local cluster is for the 4.1 spike and for fast iteration.
6. **G5 Ranking calibration.** `SEARCH_MIN_SCORE` (1.0) and the boosts were chosen on paper. BM25 scores depend on corpus size, so the defaults are checked on the first real data in step 4.1 and in the golden tests; the values are Admin-tunable and need no deploy.
7. **G6 Batch photo call and query builder location** differ from the LLD sketch (batch method on `ListingPhotoLinkPort`, query builder in the OpenSearch package). Both are recorded in the LLD "As built" note when done.
8. **G7 Facet counts.** Facets that "reflect the current filters except their own selection" cost one filtered aggregation per facet; the cap of `SEARCH_MAX_FACETS` keeps it bounded. Measure on the spike data; if p95 exceeds the 300 ms target, drop the own-selection exclusion and note it.

---

**Status:** Approved (2026-11-10). The user approved this plan, confirmed the Real Estate scope rule (G2) and Colima as the local container runtime (G8). Gaps G5 to G7 stay as implementation checks.

## 8. Implementation Notes (2026-11-10)

Built on `feature/US-011-browse-search-listings` in `valuex-backend` and `valuex-mobile` (not committed yet). Steps 4.1 to 4.6 and test plans 5.1 to 5.3 are done, except SonarQube (no server available). Deviations from this plan and why are in the LLD, section B.12; in short:

- Query builder writes JSON and lives in the OpenSearch package; batch photo method is `ListingPhotoLinkPort.mainPhotos`.
- `SearchFacetCatalog` and `DisabledCategoryProvider` are in the taxonomy module with process-local TTL caches, cleared by a `TaxonomyImportedEvent` (the plan said "the cache mechanism taxonomy services already use"; there is none).
- G2 check is a test over the seed data (`ListingSearchIntegrationTest`), not an import validator.
- Rate limit sits in the service and fails open when Redis fails.
- 4.1 spike: no US-120 code needed fixing; index creation, documents and the Painless script ran on OpenSearch 2.17.1 without change. G8: Colima was installed; behind the corporate proxy the VM needed the Zscaler root CA, and Docker 29 needs `DOCKER_MIN_API_VERSION=1.24` for Testcontainers 1.19.8 (documented in the backend README).
- Mobile: Home tiles open a text search (mock ids), Real Estate is recognised by name, search routes need sign-in (LLD B.12).
- Results: backend `mvn verify` 1837 tests green (20 real-cluster tests), checkstyle clean, coverage checks met (new classes 94% to 100% lines); mobile `flutter analyze` clean, format clean, 1290 tests green with `SKIP_PIXEL_CONTRAST=true` (one pre-existing unrelated contrast test in `item_details_live_test` fails without it). Testing guide: `Documents/Manual Testing Guides/US-011-Testing-Guide.md`.

All implementation step checkboxes above are complete.

## 9. Extension: search auto-complete suggestions (2026-11-11)

Requested by the user after testing; not in the approved plan or in the acceptance criteria, so it is recorded here as an explicit extension of US-011 (no new migration, no new setting).

- [x] Backend: `GET /api/v1/search/suggestions` (`SearchSuggestionService`, `ListingSearchPort.suggest`, `OpenSearchQueryBuilder.buildSuggest`, `SearchSuggestion`), unit tests, and 3 real-cluster tests in `ListingSearchIntegrationTest` (23 tests in total).
- [x] Mobile: suggestion list on the search screen (debounced, stale-safe, silent on failure).
- [x] Docs: backend README, testing guide (TC-056 to TC-064, TC-071 to TC-076), LLD B.12, `user-stories.md` update note.
- Design choices: categories first (at most 3), then titles; the category name must have a word starting with the typed text (the existing category search matches anywhere, which made `iph` suggest "Computer Speakers"); rate limit is 4 times the search limit instead of a new setting.

## 10. Extension: single-screen category browser (2026-11-11)

**Status:** Approved by the user after reviewing the design proposal.

- Replace separate level-by-level navigation with inline L1 cards, L2 expandable headings and L3 icon tiles. Keep one L1 and one L2 expanded at a time.
- Reuse the taxonomy providers: top-level popular parents first and expandable remaining L1 categories. Minimum-click revision (2026-11-11): expanding L1 loads `ALL` L2 groups (popular first); expanding L2 shows `ALL` L3 tiles. No Other groups or leaf Show more / Show less controls.
- Keep the search field pinned, autocomplete and the hidden 200-character limit unchanged. Show filters on results. Parent View all and L3 taps open the existing results route, including the Real Estate intent chooser.
- Share the browser with existing category routes. Parent deep links begin with that parent expanded; Browse all returns to the full taxonomy inline.
- Preserve expansion and scroll position when returning from results and while temporarily showing typed search results/suggestions. Reflow tiles for large text and preserve 48 dp targets.
- Use existing brand tokens and a shared curated Material vector icon catalog, not new category photo assets. Apply it to Search, Home and the Home category list. The taxonomy generator covers every current L1/L2/L3 code and Home alias; related categories share families and distinct products have exact leaf overrides. No backend changes.
- Validate inline expansion/collapse, complete L2/L3 visibility without extra clicks, top-level remaining categories, L1/L2/L3 result scopes, property intent, loading/error/retry, state restoration, icon coverage across all category surfaces, English/Hindi and 200% text. Run formatting, analysis, mobile tests/coverage and an iOS simulator build. Sonar remains a reported limitation unless a configured server is available.

Implemented on `feature/US-011-browse-search-listings`; not committed or pushed.
Shared widgets: `category_browser.dart` and `category_browser_tiles.dart`; the old list tile was
replaced. Search and category routes, English/Hindi translations and widget tests were updated.
LLD B.12 and testing guide F3 describe the implementation and manual cases CAT-01 to CAT-11.

Validation:
- Full mobile suite: 1,334 passing tests with `SKIP_PIXEL_CONTRAST=true` (the previously documented unrelated contrast limitation remains).
- After the final compact L2 View all adjustment: 252 search/localization/accessibility/heading regression tests pass.
- Final line coverage: browser 129/130 (99.2%), browser tiles 66/67 (98.5%), search screen 143/143 and category route wrapper 9/9 (100% each).
- `dart format lib test`, `flutter analyze` and `git diff --check` clean.
- iOS simulator debug build succeeds; expanded layout rendered and visually inspected. Existing `flutter_secure_storage` Swift Package Manager warning remains.
- SonarQube not run: no configured mobile scanner/server. No backend changes or backend rerun needed for this UI extension.

Minimum-click/icon revision verification (2026-11-11):
- 287 targeted Search, Home, icon, localization, accessibility and heading tests passed.
- The generator's `--check` confirms the catalog matches the full taxonomy and curated assignments.
- Shared icon and Home category tile coverage: 100%; browser: 99.1%; browser tiles: 98.2%.
- Format, analyzer and `git diff --check` clean; final iOS simulator debug build passed and was installed.
- Search layout and all 39 root icons were rendered and visually inspected. The local backend was
  offline, so this revision's live API/simulator search was not exercised; widget tests cover routing
  and the `ALL` requests. No backend code changed. No commit or push.
