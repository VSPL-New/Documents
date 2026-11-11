# US-120 — OpenSearch Setup and Listing Indexing: QA Testing Guide

**Sprint 3 · Discovery & Search**

Manual test cases for the listing search index: how a listing reaches OpenSearch through the outbox, what the document
holds, what keeps a listing out, and what happens when the cluster is down. There is no buyer search screen yet
(US-011); this guide checks the index directly with `curl` and SQL. The dummy payment gateway is used.

> **What ships:** `search_index_outbox` and migration `V25`; the `SearchIndexWorker` that drains it into OpenSearch;
> `ListingExpiryJob` (moves listings past `expires_at` to `EXPIRED`); a reconciliation job; the internal reindex
> endpoint `POST /internal/v1/search/reindex`; the Admin-managed settings (`platform_settings`, keys `SEARCH_*`,
> `RATE_LIMIT_*`, `PHOTO_FALLBACK_LINK_MINUTES`); the plan fields `plans.search_tier` and `plans.listing_badge`,
> copied onto the listing when a plan is chosen; the seller's state (`listings.seller_state`), sent by the app from
> the place chosen on Home.
> **Not in this story:** the search API and screen (US-011), ranking itself (US-011), Admin screens for the settings
> (US-121), the in-app alerts (later in Sprint 3).

| Setting | Value |
|---|---|
| Backend base URL | `http://localhost:8080` |
| OpenSearch | `http://localhost:9200` (`docker compose up -d opensearch`) |
| Migration | `V25__search_index_outbox_and_listing_search_columns.sql` |
| Aliases | `valuex-listings-read`, `valuex-listings-write` over `valuex-listings-v1` |
| Reindex endpoint | `POST /internal/v1/search/reindex`, header `X-Internal-Api-Key` = `SEARCH_INTERNAL_API_KEY` |
| Worker timing | polls every 2 s; failed rows retry after 5 s, 30 s, 2 min, 10 min, 1 h, then `FAILED` after 8 attempts |
| Known gaps | Sonar not run; OpenSearch tests could not run without Docker on the build machine (see "Automated tests") |

---

## Prerequisites

1. `docker compose up -d postgres redis opensearch`, then start the backend with `SEARCH_INTERNAL_API_KEY=dev-search-key`
   (`mvn spring-boot:run`). Check `curl -s localhost:9200/_cluster/health` is `green` or `yellow`.
2. An `ACTIVE` seller with a token (`$TOKEN`) and a second seller (`$TOKEN_B`). Publish listings with the steps of
   `US-008-Testing-Guide.md` and `US-009-Testing-Guide.md`; `UPDATE plans SET discounted_price = 0 WHERE code = 'BASIC'`
   makes the `BASIC` plan publish without payment.
3. Handy commands:

```bash
curl -s "localhost:9200/valuex-listings-read/_doc/$LISTING" | jq .          # one document
curl -s "localhost:9200/valuex-listings-read/_count" | jq .count            # documents in the index
curl -s "localhost:9200/_alias/valuex-listings-read"                         # which index the alias points to
```

```sql
SELECT id, listing_id, reason, status, attempts, last_error FROM search_index_outbox ORDER BY id DESC LIMIT 10;
SELECT setting_key, setting_value FROM platform_settings WHERE setting_key LIKE 'SEARCH_%' ORDER BY 1;
SELECT status, expires_at, seller_state, plan_search_tier, plan_badge FROM listings WHERE id = '<id>';
```

---

## Test cases: indexing (AC1, AC5)

| ID | Criterion / edge case | Steps | Expected |
|---|---|---|---|
| TC-001 | AC1 publish | Publish a listing | Within a few seconds the document exists; its outbox row is `DONE` |
| TC-002 | AC1 edit | Change the price of the live listing | The document `price` changes; a new `EDITED` outbox row is `DONE` |
| TC-003 | AC1 leave `PUBLISHED` | Delete the listing, or mark it sold | The document is gone (404 on the `_doc` call) |
| TC-004 | AC1 review hold | Edit a live listing with a major change (it goes back to review) | The document is removed; it returns when the listing is published again |
| TC-005 | AC1 seller suspended | Suspend the seller (`UserStateService`, or `UPDATE users SET status = 'SUSPENDED'` followed by the state event) | Every document of the seller is removed; they come back when the seller is `ACTIVE` again |
| TC-006 | AC1 expiry | `UPDATE listings SET expires_at = (now() AT TIME ZONE 'UTC') - interval '1 hour' WHERE id = '<id>'`, wait up to 10 minutes | Status `EXPIRED`, a status-history row `EXPIRE`, the document is removed, the seller gets the existing expired notification |
| TC-007 | AC5 cluster down | `docker compose stop opensearch`, publish a listing | Publication succeeds; the outbox row stays `PENDING` with `attempts` rising and `last_error` set; `/actuator/health` shows `openSearch` as `DEGRADED`, overall status `UP` |
| TC-008 | AC5 recovery | `docker compose start opensearch` | Pending rows drain without any action; the document appears |
| TC-009 | AC5 gave up | Keep the cluster down until a row shows `FAILED` (or set it with SQL), start the cluster | The nightly reconciliation (or `POST` reindex, TC-020) repairs it; the row is requeued |
| TC-010 | Backend started while the cluster is down | Stop OpenSearch, restart the backend, then start OpenSearch | The backend starts; the index and aliases are created by the worker before its first write |

## Test cases: the document (AC2, AC3, AC4)

| ID | Criterion / edge case | Steps | Expected |
|---|---|---|---|
| TC-011 | AC2 content | Read the document of a phone listing | Has `category` (L1, L2, L3 codes and names), `categoryCodes`, `price`, `condition`, `location.cityKey` and `stateKey` (lower case), `planTier`, `planBadge`, `publishedAt`, `expiresAt`, typed `attributes`, `searchText` (lower case) |
| TC-012 | AC2 privacy | Read documents of listings with an address, pincode, phone or Aadhaar-related values | None of the document keys or values contains an address, pincode, latitude, longitude, phone, email, serial number or seller name |
| TC-013 | AC2 Real Estate | Publish a Real Estate listing (sale intent) with city and locality | `transactionIntent` is set; `location.cityKey` is the property city and `location.locality` the locality, not the seller's |
| TC-014 | AC2 New Development | Publish a New Development listing | `priceQualifier` is `STARTING_FROM` |
| TC-015 | AC3 ranking inputs | Look at `sellerRating`, `planTier`, `planBadge`, `publishedAt` | Present when known; `sellerRating` is absent for a seller without ratings (no error) |
| TC-016 | AC2 plan snapshot | Publish with `BOOSTED`, then `UPDATE plans SET search_tier = 3 WHERE code = 'BOOSTED'`, edit the listing | `planTier` stays 1: the plan is copied onto the listing when it is chosen |
| TC-017 | AC2 state | Choose a place on Home (state known), create a listing, save details | `listings.seller_state` is the canonical state name (for example `Karnataka`); the document has `location.stateKey` |
| TC-018 | AC4 disabled category | `UPDATE categories SET admin_enabled = FALSE WHERE id = '<category of a live listing>'`, then `POST` reindex with `{"scope":"CATEGORY","categoryCode":"<code>"}` | The documents of that category are removed; enabling the category and reindexing brings them back |
| TC-019 | AC4 disabled parent | Disable the parent (L2 or L1) of a live listing's category and reindex all | The listing is removed |

## Test cases: reindex and safety

| ID | Criterion / edge case | Steps | Expected |
|---|---|---|---|
| TC-020 | Reindex all | `curl -s -X POST localhost:8080/internal/v1/search/reindex -H "X-Internal-Api-Key: dev-search-key" -H "Content-Type: application/json" -d '{"scope":"ALL"}'` | `202`, `{"enqueued": n}` with n equal to the live listings; documents rebuilt |
| TC-021 | Reindex one listing | Same with `{"scope":"LISTING","listingId":"<id>"}` | `202`, `enqueued` 1 |
| TC-022 | Reindex by category | Same with `{"scope":"CATEGORY","categoryCode":"<code>"}` | `202`, only that category |
| TC-023 | Wrong scope | `{"scope":"EVERYTHING"}`, or `CATEGORY` without a code, or `LISTING` without an id | `400` `ERROR_INVALID_REINDEX_SCOPE` |
| TC-024 | Key required | Call TC-020 without the header, with a wrong key, and with the AI service key (`AI_INTERNAL_API_KEY`) | `401` each time |
| TC-025 | Key isolation | Call `GET /internal/v1/taxonomy/snapshot` with the search key | `401`; with the AI key it is `200` |
| TC-026 | Public API closed | Call the reindex endpoint with a user token | `401` or `403`, nothing queued |
| TC-027 | Correct after a mismatch | Delete a document by hand (`curl -X DELETE`), wait for the reconciliation (or run a full reindex) | The document is back; add a stray document for a deleted listing and it is removed |
| TC-028 | Two instances | Start a second backend instance on another port; publish ten listings quickly | Every row is `DONE` once; no duplicates; no errors about version conflicts in the log beyond debug level |
| TC-029 | Stale write | Edit a listing twice within a second | The index ends with the latest values (the worker applies the newest outbox row only) |

## Test cases: Admin settings

| ID | Criterion / edge case | Steps | Expected |
|---|---|---|---|
| TC-030 | Defaults exist | Run the `SEARCH_%` query above | The keys exist with their defaults (23 `SEARCH_` keys plus 3 `RATE_LIMIT_` keys and `PHOTO_FALLBACK_LINK_MINUTES`, for example `SEARCH_BOOST_CITY` 1.3, `SEARCH_PAGE_SIZE_DEFAULT` 20, `RATE_LIMIT_SEARCH_PER_MIN`, `PHOTO_FALLBACK_LINK_MINUTES`) |
| TC-031 | Bad value | `UPDATE platform_settings SET setting_value = 'abc' WHERE setting_key = 'SEARCH_PAGE_SIZE_DEFAULT'`, wait 60 s | The default is used and the `settings.invalid` metric increases; no error reaches a user |
| TC-032 | Rule between two values | Set `SEARCH_BOOST_STATE` above `SEARCH_BOOST_CITY` by SQL | The pair is reset to the defaults (the rule is "state boost is not above city boost") |

---

## Automated tests

```bash
cd valuex-backend
mvn verify                                              # unit tests, Checkstyle, JaCoCo gate
mvn -Dtest='Search*Test,ListingExpiryJobTest,OpenSearch*Test,Discovery*Test,PlatformSettingsServiceTest' test
```

Integration tests `ListingSearchIndexIntegrationTest` and `InternalSearchSecurityIntegrationTest` need Docker
(Testcontainers PostgreSQL) and are skipped without it. `OpenSearchListingSearchAdapterTest` runs against a local HTTP
stub, so the request shapes (external version, `409` as stale, strict mapping fields) are checked without a cluster; the
real cluster is covered by TC-001 to TC-010 above.

Mobile: `cd valuex-mobile && flutter test test/features/listing/listing_schema_test.dart test/features/listing/item_details_test.dart`.
