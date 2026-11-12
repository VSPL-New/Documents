# US-120: OpenSearch Setup and Listing Indexing - Implementation Plan

## 1. Header

| Field | Value |
|---|---|
| Story | US-120 - OpenSearch Setup and Listing Indexing |
| Sprint | Sprint 3 - Discovery & Search |
| Story points | 8 (proposed) |
| Repos involved | valuex-backend (code, `docker-compose.yml`, README), valuex-mobile (one small change, section 4.7). No `valuex-ai` change. |
| Dependencies | US-006 (taxonomy, attribute values), US-089 (`ListingLifecycleService`, `ListingStatusChangedEvent`), US-009 (`published_at`, `expires_at`), US-010 (edit and delete events), US-088 (`UserStateChangedEvent`), US-008 (plan selection), US-115 (already sends the `EXPIRED` notification). Built in parallel with [US-128](US-128-Implementation-Plan.md); US-011 builds on this story. |
| Date | 2026-11-09 |
| Design source | [Sprint 3 LLD](../LLD/Sprint-3-Discovery-Search-LLD.md), Part A and sections 1.4 to 1.6 (final, approved 2026-11-09) |
| Branch (proposal) | `feature/US-120-opensearch-listing-indexing` from the latest `main` in `valuex-backend` (not from `feature/us-123-listing-preview`) |
| Flyway number | `V25` is provisional: `main` is at `V24` today. Take the next free number when the branch is cut; if US-128 merges first, this story takes the following number. |

## 2. Story Recap

**As a** platform **I want** a managed listing search index **so that** buyers get fast keyword, filter and facet search.

### Acceptance Criteria (user-stories.md, with the 2026-11-09 update)

| ID | Behaviour |
|---|---|
| AC1 | A listing that reaches `PUBLISHED` is indexed through an outbox with retries, and removed when it leaves `PUBLISHED`. |
| AC2 | The document carries the category (L1, L2, L3 codes and names), the normalised listing price, transaction intent, condition, location (city and state; property locality for Real Estate), plan type, seller rating, recency and typed attributes. No street address. |
| AC3 | Ranking inputs for the HLD order (exact match, category relevance, seller rating, plan boost, recency) exist in the index. The ranking itself runs in US-011. |
| AC4 | A disabled category, or any listing under a disabled parent, is excluded. |
| AC5 | OpenSearch downtime never blocks listing publication. |

**Edge cases:** reindex after taxonomy change; mapping change (versioned index behind an alias); attribute explosion (typed nested attributes); missing seller rating.
**Validation:** only published, non-expired listings are searchable; addresses and phone numbers are never indexed.

### Decisions this plan relies on (LLD section 9.1)
D1 city and state level location (no point); D2 hosting-neutral; D4 plan tier and badge are data; D5 this story owns the expiry sweep; D19 business numbers are Admin-managed settings.

## 3. Design Reference

Primary source: LLD Part A (A.3 data model, A.5 backend design, A.6 diagrams, A.8 NFR, A.9 tests) and LLD section 1.6 (Admin-managed settings).

### Verified Implementation Anchors (checked in the code on 2026-11-09)

| Area | Finding and consequence |
|---|---|
| Events | `ListingStatusChangedEvent` (`getFromState`, `getToState`, `getListingId`), `ListingEditedEvent`, `ListingDeletedEvent` (soft delete also moves the listing to `DEACTIVATED_BY_SELLER` through `ListingLifecycleService`, so the status event already covers it), `UserStateChangedEvent` (`getUserId`, `getToState`). `ListingState.isLiveForBuyers()` returns `PUBLISHED` only and is the single membership rule. |
| Transactions | `ListingLifecycleService.transition` is `@Transactional`. `ListingDraftService` publishes `ListingCreatedEvent` through `ApplicationEventPublisher`. A `BEFORE_COMMIT` listener is silently skipped when there is no transaction, so the writer uses `fallbackExecution = true` and a test covers a call outside a transaction. |
| Listing columns | `Listing` has `price`, `condition`, `categoryId`, `sellerLocation`, `planType`, `publishedAt`, `expiresAt`, `deletedAt`, `approvedPrice`; no state, tier or badge yet (V25 adds them). |
| Attribute reads | `ListingAttributeService` reads `listing_attribute_values` and `listing_attribute_option_values` with `JdbcTemplate` (SQL near lines 105 and 115). The document factory follows the same style. |
| Category reads | `CategoryService` has the enabled-leaf query with ancestors (`LEAF_SELECT`) and `AttributeRules.EXCLUDED_KEYS`. Reuse them rather than writing a second tree walk. |
| Plans | `PlanSelectionService` (lines 106 to 109) copies plan code, price, validity and tax mode onto the listing. `Plan` has no tier or badge. |
| Reputation | `SellerReputationPort.findReputation` exists; `NoReputationDataAdapter` returns nothing, so `sellerRating` is null. |
| Expiry | `ListingStateMachine` has `PUBLISHED -> EXPIRED` (`EXPIRE`); no job calls it. `ListingEventNotificationListener` already sends the `EXPIRED` message, so the sweep notifies sellers for free. |
| Internal endpoints | `InternalSecurityConfig` protects `/internal/v1/**` with `InternalApiKeyFilter`, keyed by `valuex.ai.internal.api-key` (the AI service's key). The reindex endpoint gets its own key and chain (decision G1, section 4.5). |
| Settings | `platform_settings(setting_key, setting_value, updated_at, updated_by)` exists (V15). No settings service exists yet. |
| Test setup | Each integration test declares its own PostgreSQL container; `application-test.yml` has no search section. All existing `@SpringBootTest` tests would load the new beans, so search is switched off in the test profile (section 4.2). |
| Build | Maven, JDK 21, Checkstyle max line 120, Testcontainers 1.19.8 (see the repository notes). |

## 4. Implementation Steps

### 4.1 Branch and setup
- [ ] Cut the branch from `main`; confirm the next free Flyway number; run the existing backend tests once to get a green baseline.
- [ ] Record the pinned OpenSearch server version (2.x) and the matching client version in the pull request.

### 4.2 Infrastructure and configuration
- [ ] `pom.xml`: OpenSearch Java client with the Apache HttpClient 5 transport (compile); an OpenSearch container for Testcontainers (test). Pin both to the same major version.
- [ ] `docker-compose.yml`: service `opensearch` (single node, security plugin off for local use only, 512 MB heap, port 9200, named volume, health check on `/_cluster/health`), added to `valuex-network` and documented in the README with a reset command.
- [ ] `ValuexProperties.SearchSettings` (deployment values only, LLD 1.5): `enabled`, `opensearch.uris`, `username`, `password`, `internal.api-key` (key for the reindex endpoint only; empty means every call is refused), timeouts, index aliases, shards and replicas, outbox batch size, poll interval, max attempts, `expiry.cron`, `settings.cache-ttl`. Defaults in `application.yml`; credentials only from environment variables.
- [ ] `application-test.yml`: `valuex.search.enabled: false`, so existing tests neither start an OpenSearch client nor run the worker. Search integration tests enable it explicitly with their own container.
- [ ] Checkstyle passes for all new classes (line length 120).

### 4.3 Database migration `V25__search_index_outbox_and_listing_search_columns.sql`
- [ ] `search_index_outbox` with its three indexes and the status check (LLD A.3.1).
- [ ] `listings.seller_state`, `listings.plan_search_tier`, `listings.plan_badge`; `plans.search_tier` (default 0, check 0 to 3) and `plans.listing_badge`.
- [ ] Seed Boosted (tier 1, badge `BOOSTED`) and Priority (tier 2, badge `FEATURED`); backfill the listing columns from the plan by `plan_type`.
- [ ] Backfill outbox rows (`BACKFILL`) for every `PUBLISHED`, not deleted listing.
- [ ] Seed the search settings keys in `platform_settings` with their defaults (`ON CONFLICT DO NOTHING`): every `SEARCH_*`, `RATE_LIMIT_*` and `PHOTO_FALLBACK_LINK_MINUTES` key of LLD 1.6.
- [ ] Update the entities: `Listing` (three fields), `Plan` (two fields).

### 4.4 Admin settings foundation (LLD 1.6)
- [ ] `DiscoverySettingDefinition` registry (key, type, default, min, max, cross-field rules) declaring the keys seeded above. Later stories add their own definitions.
- [ ] `PlatformSettingsService.discovery()` returning an immutable `DiscoverySettings` snapshot, cached per instance for `valuex.settings.cache-ttl`; an invalid or missing value falls back to the default, logs a warning and counts `settings.invalid{key}`.
- [ ] `DiscoverySettingsService.update(changes, adminId)`: validates every key and the cross-field rules together, writes all or nothing, sets `updated_by`, evicts the cache on every instance through a Redis message. No controller in this story (the Admin API comes with US-116).

### 4.5 Search module (`com.valuex.search`)
- [ ] Ports: `ListingSearchPort` (`ensureIndex`, `upsert`, `delete`, `idsPage`, `existingIds`, `count`) and `ListingIndexSourcePort` (implemented in the listing module by `ListingIndexSourceAdapter`). US-011 adds `search` and `msearch`.
- [ ] `OpenSearchConfig` and `OpenSearchListingSearchAdapter`: client from properties, external-version writes, a version conflict returned as a distinct result, a Resilience4j `searchBreaker` created programmatically (as `AiGatewayConfig` does), search-only; indexing relies on the outbox for retries.
- [ ] `resources/search/listings-mapping-v1.json` (LLD A.3.2) and `resources/search/city-aliases.csv`; `CityNormalizer` (trim, lower-case, ASCII fold, aliases; states matched against `IndianStates`).
- [ ] `IndexBootstrap` on `ApplicationReadyEvent`: creates `valuex-listings-v1` and both aliases when missing; catches connection errors (the app must start with OpenSearch down) and retries from the worker before its first drain.
- [ ] `SearchIndexOutboxWriter` with `@TransactionalEventListener(phase = BEFORE_COMMIT, fallbackExecution = true)` for the four event types and conditions of LLD A.5.1. For `UserStateChangedEvent` it enqueues one `SELLER_STATE` row per `PUBLISHED` listing of the seller (new repository query `findIdsBySellerIdAndStatus`).
- [ ] `ListingSearchDocumentFactory.buildIfLive` (LLD A.5.3): live check (`PUBLISHED`, not deleted, not expired, enabled category chain, `ALLOWED` or `CONDITIONAL`, seller `ACTIVE`); category from the existing leaf query; attributes allow-listed by `filterable` and `searchable` in the profile, never `EXCLUDED_KEYS`, never `pincode`, `latitude`, `longitude` or serial values; New Development price qualifier; Real Estate city and locality from the property attributes; rating from `SellerReputationPort`; first photo by `sort_order`. Batch loading for a page of ids.
- [ ] `SearchIndexWorker` (`@Scheduled`): claim with `FOR UPDATE SKIP LOCKED`, newest row per listing, state-based upsert or delete, external version = outbox id, retry with backoff (5s, 30s, 2m, 10m, 1h), `FAILED` after the maximum, `DONE` cleanup after 7 days. Does nothing when `valuex.search.enabled` is false.
- [ ] `SearchReindexService`: `rebuildAll`, `rebuildCategory`, `rebuildListing` enqueue `REINDEX` rows in pages of 1,000; `SearchReconciliationJob` (daily 03:00) repairs missing and extra documents in both directions and re-queues `FAILED` rows once.
- [ ] `InternalSearchController` `POST /internal/v1/search/reindex` (LLD A.4), `202` with the number enqueued. Decision G1: it has its **own** key. `InternalSecurityConfig` gets a second filter chain for `/internal/v1/search/**`, ordered before the existing `/internal/v1/**` chain, using `InternalApiKeyFilter` with `valuex.search.internal.api-key`; the AI key must not open it, and the search key must not open the AI endpoints.
- [ ] Health indicator `opensearch` in `/actuator/health`, excluded from the readiness group; Micrometer metrics and alerts of LLD A.8 (`search.outbox.pending`, `.failed`, `.lag.seconds`, `search.index.errors.total`, `search.reconcile.repaired`, `search.expiry.expired.total`).

### 4.6 Listing module changes
- [ ] `ListingRepository.findExpiredPublishedIds(now, Pageable)` with `FOR UPDATE SKIP LOCKED`, and `ListingExpiryJob` (`@Scheduled`, default every 10 minutes): `ListingLifecycleService.transition(id, EXPIRED, "EXPIRE", null, "plan_validity_ended")`, skipping any listing another instance or the seller already moved.
- [ ] `PlanSelectionService`: copy `search_tier` and `listing_badge` onto the listing next to the existing snapshot (lines 106 to 109).
- [ ] `ListingIndexSourceAdapter`: batch reads for the factory, `ListingEligibilityFilter.retainLive(ids)` (used here by reconciliation, by US-011 for search).

### 4.7 Location state (cross-story change, kept minimal)
- [ ] Backend: `ListingDetailsRequest.locationState` (optional, validated against `IndianStates`), saved by `ListingDetailsService` into `seller_state`; `ListingEditService` treats a location change as one change of city and state; both returned by the draft response.
- [ ] Mobile: `ListingDetailsDraft` sends `locationState` from `HomeLocation.state` next to the existing `location` (`listing_details.dart`, `item_details_controller.dart`); regenerate no `.g.dart` unless a `@riverpod` source changes; run `dart format` and the analyzer.
- [ ] Existing listings keep a null state and still match by city.

### 4.8 Documentation and quality
- [ ] README: how to start OpenSearch, reset the index, run the reindex endpoint, and the mapping-change procedure (LLD A.5.5).
- [ ] OpenAPI entry for the internal endpoint is not published (internal path), documented in the README instead.
- [ ] LLD Part A: update with an "As built" note for any deviation.
- [ ] After implementation, `Documents/Manual Testing Guides/US-120-Testing-Guide.md` (start OpenSearch, publish, edit, expire, stop OpenSearch, restart and watch the outbox drain, reindex).
- [ ] Checkstyle, full backend tests, coverage above 90% for new code, and SonarQube before any push. Never push or open a pull request without asking.

## 5. Test Plan

### 5.1 Unit tests (JUnit 5, Mockito, AssertJ)
- [ ] `ListingSearchDocumentFactoryTest`: every field; forbidden keys never present (`pincode`, `latitude`, `longitude`, serial, `EXCLUDED_KEYS`, seller name, phone, email); New Development `STARTING_FROM`; Real Estate property city and locality; option attributes by code; null rating and null state; disabled category chain returns empty; expired and deleted return empty.
- [ ] `SearchIndexOutboxWriterTest`: row per event type and condition; no row for an unrelated status change; fallback outside a transaction; seller state fan-out.
- [ ] `SearchIndexWorkerTest`: newest row per listing wins and older rows are marked done; delete when not live; version conflict is success; retry schedule and `FAILED` after the maximum; disabled switch does nothing; OpenSearch error never throws out of the scheduler.
- [ ] `CityNormalizerTest`, `DiscoverySettingDefinitionTest` and `PlatformSettingsServiceTest` (default fallback, invalid value, cross-field rules, cache expiry), `ListingExpiryJobTest`, `PlanSelectionServiceTest` (tier and badge copied), `SearchReindexServiceTest`.

### 5.2 Integration tests (Testcontainers PostgreSQL and OpenSearch)
- [ ] Publish a listing, drain the outbox: the document exists with the expected values and no forbidden field.
- [ ] Edit the price, hide for review (major edit), delete, expire and suspend the seller: the document is updated or removed each time.
- [ ] OpenSearch stopped while publishing: publication succeeds, rows stay pending, and they drain after the container restarts. App starts with OpenSearch down.
- [ ] Two workers racing on one listing end with the newest state; a stale write is rejected.
- [ ] Rebuild by category and in full; alias swap keeps the read alias answering.
- [ ] Reconciliation repairs one missing and one extra document.
- [ ] Plan tier and badge stay on an existing listing after the plan is edited.
- [ ] Migration test: V25 applies on a database with `PUBLISHED` listings and creates the backfill rows.
- [ ] The existing integration suite stays green with `valuex.search.enabled=false`.
- [ ] Internal key separation: the search key reaches `POST /internal/v1/search/reindex` and not the AI endpoints; the AI key reaches the AI endpoints and gets 401 or 403 on the reindex path; an empty search key refuses every call; no JWT is accepted on the internal chains.

### 5.3 Mobile
- [ ] Unit test that the item details request includes `locationState`; analyzer and existing tests pass.

## 6. Validation Checklist

- [ ] AC1: publishing writes an outbox row in the same transaction; the worker indexes it; leaving `PUBLISHED` removes it; retries and `FAILED` handling work.
- [ ] AC2: document fields match LLD A.3.2; city and state only; no address, pincode, phone or seller name.
- [ ] AC3: tier, badge, rating, publication date and category name fields are present for US-011's ranking.
- [ ] AC4: disabled categories and children of disabled parents are not indexed and are removed by a category reindex.
- [ ] AC5: with OpenSearch down, publication, edit and delete all succeed.
- [ ] Edge cases: taxonomy reindex, versioned mapping with alias swap, nested typed attributes, null rating.
- [ ] Only published, non-expired listings are searchable: query-time `expiresAt` filter is documented for US-011 and the expiry sweep runs.
- [ ] The app starts and the existing test suite passes with search disabled; health reports OpenSearch separately and readiness is unaffected.
- [ ] Settings foundation works: defaults seeded, invalid value falls back, update is all-or-nothing.
- [ ] Checkstyle, tests, coverage above 90%, SonarQube pass; testing guide written.

## 7. Open Gaps / Questions

1. **G1 Reindex endpoint authentication (decided 2026-11-09).** The endpoint gets its own key, `valuex.search.internal.api-key`, and its own filter chain, so the AI service's key cannot trigger a reindex. Implemented in section 4.5.
2. **G2 OpenSearch versions and CI.** Pin the server and client versions; confirm the S0-006 runner has memory for an OpenSearch Testcontainer (about 1 GB). If not, mark the OpenSearch integration tests to run only where Docker memory allows and say so in the pull request.
3. **G3 Taxonomy flags.** The document factory depends on `metadata_profile_attributes.searchable` and `filterable` being set in the imported profiles. Check the loaded data before coding; if many are false, facets will be empty and US-011 needs a data fix (not a code change here).
4. **G4 Which seller states hide listings.** The LLD says any state other than `ACTIVE`. Confirm for `UNDER_REVIEW` and `RESTRICTED` with the US-088 rules before the writer is finished.
5. **G5 Live states beyond `PUBLISHED`.** Listings in `BUYER_INQUIRY_PENDING` and `NEGOTIATION_IN_PROGRESS` leave the index. Not an issue until Sprint 4, which decides through `isLiveForBuyers()`.
6. **G6 Settings seeds.** Each later story adds its own keys and definitions; the registry must tolerate keys present in the database but not yet declared.

---

**Status:** Approved (2026-11-09). The user approved this plan and asked for implementation to start.

## 8. As Built (2026-11-09)

Deviations from this plan, with the reasons; the full table is LLD Sprint 3, section A.10.

- No Redis pub/sub eviction of the settings cache; other instances see a change within 60 seconds.
- No search circuit breaker yet; it arrives with the query adapter in US-011.
- `ListingExpiryJob` does not use `SKIP LOCKED`; each listing is moved through `ListingLifecycleService`, which locks it.
- `locationState` is stored but not returned on the draft response.
- Index creation uses the generic client; HTTP errors from the Apache 5 transport arrive as `ResponseException`, handled with the status code.
- The live predicate compares `expires_at` with `now() AT TIME ZONE 'UTC'` (the column holds UTC wall-clock time).
- The four existing `RestClient` users are pinned to `SimpleClientHttpRequestFactory`, because `httpclient5` on the classpath would otherwise switch them to Apache (which retries 429 and 503 on its own; `AiGatewayClientTest` caught it).
- The mobile change is carried on `ListingDetailsDraft.locationState`, so the repository method signatures did not change.
- Added tests beyond the plan: `InternalSearchSecurityIntegrationTest` (key separation) and a mapping-compatibility test in `OpenSearchListingSearchAdapterTest`.
- Not run: OpenSearch integration tests (no Docker on the build machine), SonarQube (see the final report).
