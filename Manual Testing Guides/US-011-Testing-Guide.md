# US-011 — Browse and Search Listings: QA Testing Guide

**Sprint 3 · Discovery & Search**

Manual test cases for buyer search: keyword search ranked by relevance, category browsing (L1, L2, L3), filters
(price, condition, place, category facets, Real Estate intent), paging, and the error and empty states. The backend is
checked with `curl`; the app is checked on the Search tab. The dummy payment gateway is used.

> **What ships:** `GET /api/v1/search/listings` (backend); the Search tab, search screen, filter sheet, results list,
> category browsing and the Buy / Rent / Lease chooser (mobile); the Home search bar, "See All" and category tiles now
> open them.
> **Also included (user-approved extension, 2026-11-11):** search auto-complete suggestions (`GET /api/v1/search/suggestions` and the list under the search box).
> **Not in this story:** listing details (US-012), the heart / saved items (US-073, `saved` is always `false`), photo
> search, saved searches, the Home feed (US-111).

| Setting | Value |
|---|---|
| Backend base URL | `http://localhost:8080` |
| OpenSearch | `http://localhost:9200` (OpenSearch 2.17.x) |
| Endpoint | `GET /api/v1/search/listings`, any signed-in account (`Authorization: Bearer $TOKEN`) |
| Admin settings | `platform_settings`, keys `SEARCH_*` and `RATE_LIMIT_SEARCH_PER_MIN` (defaults in the LLD, section 1.6) |
| Known gaps | SonarQube not run (no server available); mobile cards show the real photo only for listings whose photo copies exist |

---

## Prerequisites

1. `docker compose up -d postgres redis opensearch` (or Colima + the same command), then `mvn spring-boot:run`.
   `curl -s localhost:9200/_cluster/health` must be `green` or `yellow`.
2. A buyer account (`$TOKEN`) and a seller account (`$TOKEN_S`), both `ACTIVE`. As the seller, publish at least these
   listings (steps of `US-008` / `US-009` guides; `UPDATE plans SET discounted_price = 0 WHERE code = 'BASIC'` skips
   payment). Wait about 5 seconds after each publish for the index worker.

| # | Title | Category | Price | Condition | Place | Plan |
|---|---|---|---|---|---|---|
| L1 | iPhone 14 128GB | Smartphones (`CAT-0001`) | 42000 | GOOD | Pune, Maharashtra | PRIORITY |
| L2 | Phone cover for iPhone 14 | Smartphones | 500 | NEW | Pune, Maharashtra | BASIC |
| L3 | Samsung Galaxy S23 | Smartphones | 38000 | LIKE_NEW | Chennai, Tamil Nadu | BASIC |
| L4 | Wooden sofa 3 seater | Sofas (`CAT-0206`) | 15000 | GOOD | Nashik, Maharashtra | BASIC |
| L5 | 2 BHK apartment | Apartments & Condos (`CAT-0871`), intent SALE | 5500000 | - | Pune, Maharashtra | BASIC |

3. Handy variables:

```bash
S="localhost:8080/api/v1/search/listings"
H="Authorization: Bearer $TOKEN"
```

---

## A. Keyword search (AC1)

| ID | Steps | Expected |
|---|---|---|
| TC-001 | `curl -s -H "$H" "$S?query=iphone+14+128gb"` | L1 first; `items[0].title` is "iPhone 14 128GB"; each item has `price`, `city`, `condition`, `badge`, `photo`, `saved:false` |
| TC-002 | `?query=iphone` | L1 and L2 (and nothing else); the PRIORITY listing L1 is above L2 |
| TC-003 | `?query=iphon` (typo) | L1 and L2 still found |
| TC-004 | `?query=zzzzqqqq` | 200, `items: []`, `advisory.code = NO_RESULTS_FOUND`, `totalItems = 0` |
| TC-005 | `?query=c%2B%2B+AND+title:*+%22` (special characters) | 200 with no error; the text is not treated as query syntax |
| TC-006 | `?query=` followed by 200 letters `a` | 200 (empty result) |
| TC-007 | `?query=` followed by 201 letters | 400 `ERROR_QUERY_TOO_LONG` |
| TC-008 | `?query=samsung&nearCity=Chennai&nearState=Tamil%20Nadu` then the same without `nearCity` | Same listings; the place only changes the order among similar matches (try `query=phone` with `nearCity=Pune`: Pune listings rise) |
| TC-009 | Search while signed in as the seller of L1 for `iphone` | L1 is not in the results (own listings are hidden) |

## B. Browse by category (AC2)

| ID | Steps | Expected |
|---|---|---|
| TC-010 | `?category=CAT-0001` | L1, L2, L3 only |
| TC-011 | L2 code of Smartphones (`L2-MOBILES_TABLETS-MOBILE_PHONES`) and L1 code (`L1-MOBILES_TABLETS`) | The same three phone listings; no sofa |
| TC-012 | No `category`, no `query` | Goods listings from every category (L1 to L4); L5 (property) is **not** included |
| TC-013 | `?category=NOPE` | 404 `CATEGORY_NOT_FOUND` |
| TC-014 | `UPDATE categories SET admin_enabled = FALSE WHERE code = 'CAT-0206'`, wait 60 seconds, then `?category=CAT-0206` and an unfiltered search | 404 for the category; L4 no longer appears anywhere. Re-enable afterwards |
| TC-015 | App: Search tab, "Browse all categories", pick an L1, an L2, an L3 | Popular categories first, then "Others"; the L3 opens its listings |

## C. Filters (AC3)

| ID | Steps | Expected |
|---|---|---|
| TC-020 | `?priceMin=1000&priceMax=40000` | L3 (38000) and L4 (15000) |
| TC-021 | `?priceMin=40000&priceMax=1000` | 400 `ERROR_INVALID_PRICE_RANGE` |
| TC-022 | `?priceMin=-5`, then `?priceMin=1.234` | 400 `ERROR_INVALID_PRICE_RANGE`; `?priceMin=abc` gives 400 `ERROR_INVALID_FILTERS` |
| TC-023 | `?condition=NEW&condition=LIKE_NEW` | L2 and L3 |
| TC-024 | `?condition=BROKEN` | 400 `ERROR_INVALID_FILTERS` |
| TC-025 | `?state=Maharashtra`, then `?state=Maharashtra&city=Pune` | L1, L2, L4; then L1, L2 |
| TC-026 | `?state=California` | 400 `ERROR_INVALID_FILTERS` (a state outside India) |
| TC-027 | `?category=CAT-0001&includeFacets=true` | `data.facets` lists the filterable attributes of phones (for example `storage_gb` with option buckets and counts, `screen_size_in` with `min` and `max`) |
| TC-028 | `?category=CAT-0001&facet=storage_gb:128_GB` (use a code from TC-027) | Only phones with that value; the `storage_gb` counts (with `includeFacets=true`) still show the other storage sizes |
| TC-029 | `?category=CAT-0001&facet=color:red` and `?facet=storage_gb:128_GB` (no category) | 400 `ERROR_INVALID_FILTERS` both times |
| TC-030 | Several filters at once: price, condition, state and a facet | Results satisfy all of them (AND) |
| TC-031 | `?category=CAT-0871` | 400 `ERROR_INTENT_REQUIRED` |
| TC-032 | `?category=CAT-0871&transactionIntent=SALE` | L5 only; `appliedIntent = "SALE"` |
| TC-033 | `?category=CAT-0871&transactionIntent=LEASE` (if the category does not offer lease) | 400 `ERROR_INTENT_NOT_SUPPORTED`; `?category=CAT-0001&transactionIntent=SALE` also gives that error |
| TC-034 | `?category=CAT-0871&transactionIntent=SALE&condition=NEW` | 400 `ERROR_INVALID_FILTERS` |

## D. Paging (AC4)

| ID | Steps | Expected |
|---|---|---|
| TC-040 | `?size=2&sort=NEWEST&page=0`, then `page=1` | Two items then the rest; `hasNext` true then false; `totalItems` the same on both |
| TC-041 | `?page=100&size=50` | 200, `items: []`, `hasNext: false`, no advisory |
| TC-042 | `?size=0`, `?size=51`, `?page=-1`, `?sort=BEST` | 400 `ERROR_INVALID_FILTERS` each |
| TC-043 | `?sort=PRICE_ASC`, then `PRICE_DESC` | Cheapest first, then dearest first |
| TC-044 | App: scroll the results to the bottom | The next page loads (a spinner row), until there is no more |

## E. Freshness, availability and limits

| ID | Steps | Expected |
|---|---|---|
| TC-050 | Mark L2 sold in SQL (`UPDATE listings SET status='SOLD' WHERE id=...`) without waiting for the worker, then `?query=iphone` | L2 is not in the results even though the index still holds it (the database re-check) |
| TC-051 | `docker stop valuex-opensearch`, then any search | 503 `ERROR_SEARCH_UNAVAILABLE`; after about 10 failed searches the answer is instant (circuit breaker open); `docker start` and wait 15 s, searches work again. Publishing still works while it is down |
| TC-052 | Run 70 searches inside a minute (`for i in $(seq 70); do curl -s -o /dev/null -w "%{http_code}\n" -H "$H" "$S?query=a"; done`) | The 61st onward answer 429; `UPDATE platform_settings SET setting_value='10' WHERE setting_key='RATE_LIMIT_SEARCH_PER_MIN'` and wait 60 seconds changes the limit |
| TC-053 | Search without a token | 401 |
| TC-054 | Look at the backend log after the searches above | No query text, no `nearCity`, no filter values anywhere; only result count, page and latency |
| TC-055 | `UPDATE platform_settings SET setting_value='3' WHERE setting_key='SEARCH_TIER_WEIGHT'` and wait 60 seconds, repeat TC-002 | The PRIORITY listing ranks even higher, still only among similar text matches (a weak match never beats a strong one) |

## E2. Auto-complete suggestions

| ID | Steps | Expected |
|---|---|---|
| TC-056 | `curl -s -H "$H" "localhost:8080/api/v1/search/suggestions?query=iph"` | 200; `data` is a list: up to 3 `CATEGORY` lines (with `categoryCode`) first, then `LISTING` titles such as "iPhone 14 128GB" and "Phone cover for iPhone 14" |
| TC-057 | `?query=cov` | "Phone cover for iPhone 14" (a later word of the title matches too); `?query=IPH` gives the same as `iph` |
| TC-058 | `?query=i`, `?query=%20`, no `query` | 200, `data: []` |
| TC-059 | `?query=iphone%201` | The iPhone titles still come (a one-letter word is ignored) |
| TC-060 | `?query=iph&limit=3`, `limit=50`, `limit=0` | 3 lines at most; capped at 10; raised to 1 |
| TC-061 | Signed in as the seller of L1, `?query=iph` | L1's title is not suggested; a sold or removed listing's title is not suggested either; property titles never are |
| TC-062 | `?query=` followed by 201 letters | 400 `ERROR_QUERY_TOO_LONG`; without a token 401 |
| TC-063 | Stop OpenSearch, `?query=iph` | 503 `ERROR_SEARCH_UNAVAILABLE` |
| TC-064 | Backend log after the calls above | No typed text |

## F. Mobile app

| ID | Steps | Expected |
|---|---|---|
| TC-060 | Home: tap the search bar | Search opens with popular category cards beneath the pinned text field; tap the field to type |
| TC-061 | Type "iphone", pause | After about 0.4 s results appear, relevant first; there is no character counter; pasting 250 characters is quietly cut at 200 |
| TC-062 | Keep typing quickly | Only the last text's results are shown (no flicker back to older results) |
| TC-063 | Open Filters: price min 5000, max 1000 | The error appears under the fields and Apply is blocked; fix it and apply, the filter badge shows the count |
| TC-064 | Filters: condition chips, state and city, sort | Results update; "Clear filters" on the empty state resets them |
| TC-065 | Browse to an L3 phone category, open Filters | A form built from the facets (options with counts, a number range, yes/no) |
| TC-066 | Expand Real Estate, then choose View all or an L3 tile | Browsing itself does not prompt; opening listings asks Buy / Rent / Lease before searching |
| TC-067 | Stop the backend search (TC-051), open the results | An error state with Retry; Retry works after the cluster is back |
| TC-068 | Switch the app to Hindi and set text size to 200% | All new screens readable, no overflow, tap targets stay 48 dp |
| TC-069 | Sign out, tap the Home search bar | Sent to Sign In |
| TC-070 | Result card | Photo, price (with paise when present), "Starting from" for new developments, Featured / Boosted badge; tapping shows "coming soon" (US-012) |

---

### F2. Auto-complete in the app

| ID | Steps | Expected |
|---|---|---|
| TC-071 | On the search screen type one letter, then a second | Nothing for one letter; after about 0.25 s a list appears under the field with up to 3 category lines (grid icon, "in Category" label) then listing titles (search icon, the typed part in bold) |
| TC-072 | Tap a listing title | The field takes that text, the list closes and results for it show |
| TC-073 | Tap a category line | That category's results open (Real Estate shows the Buy / Rent / Lease sheet first) |
| TC-074 | Press the keyboard Search key with partial text | Results for the typed text, as before; the list closes |
| TC-075 | Clear the field, or type faster than the delay | The list disappears; only suggestions for the latest text are shown |
| TC-076 | Stop OpenSearch and type | No list and no error message; the normal search shows its own error state |

### F3. Single-screen categories (approved redesign, 2026-11-11)

Use Search from the bottom navigation. The current mock Home category tiles still perform text
searches; they do not carry live taxonomy codes. Expand categories using the live Search browser.

| ID | Steps | Expected |
|---|---|---|
| CAT-01 | Tap Mobiles & Tablets, then Mobile Phones | Every L2 group is immediately available under L1, and every L3 tile under L2 (scroll if needed); no extra reveal taps or category-route pushes |
| CAT-02 | Expand another L2, then another L1; tap an expanded heading again | Only one L1 and one L2 open at once; a second tap collapses the heading |
| CAT-03 | Expand an L1 with popular and non-popular groups; use top-level More categories | All L2 groups appear with popular first; no Other groups control. More categories still toggles the remaining L1 cards only |
| CAT-04 | Expand a group with more than three leaves | All leaves appear immediately; no Show more or Show less. The fourth and later tiles are reachable by scrolling without another tap |
| CAT-05 | Use View all at L1 and L2, then tap an L3 tile | Results use the selected parent/leaf scope; L3 results still offer category facets |
| CAT-06 | Scroll an expanded tree, open results, then Back | Expanded headings and scroll offset are restored |
| CAT-07 | Expand a group, type a query, clear it | Autocomplete/results replace the tree while typing; clearing restores its expansion and scroll state; no visible character counter |
| CAT-08 | Enter via an existing parent category link; tap Browse all categories | Parent starts expanded with the same pinned field; Browse all switches to the full taxonomy inline |
| CAT-09 | Fail a child-category request, then restore connectivity and tap Retry | Error appears inline under the usable parent; Retry reloads that section; empty groups show No more categories |
| CAT-10 | Use English and Hindi at 200% text on a narrow phone | Tiles reflow to fewer columns, labels wrap without truncation, controls remain reachable and at least 48 dp |
| CAT-11 | Scroll the category tree | Search field and bottom navigation remain fixed; filters are shown when viewing results |
| CAT-12 | Compare Search, Home and Home > More category artwork | Consistent blue vector icon style; every existing category uses an appropriate family, not a missing-image placeholder. Listing photos remain unchanged |
| CAT-13 | Expand Mobile Phones and Personal Audio | Smartphones, feature phones and foldables have distinct icons; headphones never use the phone glyph |

Redesign validation (2026-11-11): 1,334 full-suite tests passed, followed by 252 targeted tests
after the final layout adjustment; browser/widget line coverage 99.2% / 98.5%, route/search
screens 100%. Format and analysis clean; iOS simulator debug build passed. Tests use the existing
`SKIP_PIXEL_CONTRAST=true` flag for the unrelated pre-existing contrast failure. SonarQube
remains unavailable. The expanded layout was visually inspected using a widget-rendered preview.

Minimum-click/icon follow-up (2026-11-11): 287 targeted tests passed, including all taxonomy code
assignments and L2 lists beyond the popular API limit. The icon generator freshness check, analyzer
and iOS simulator build passed. New icon widget coverage is 100%; browser coverage is 99.1%.
Widget-rendered Search and a 39-root icon gallery were inspected. The updated simulator app is
installed; the local backend was offline during verification, so start it before live API testing.

## Automated tests

```bash
# Backend: unit tests plus the real-cluster test (needs Docker; with Colima set DOCKER_HOST, see README)
mvn verify
mvn test -Dtest='SearchRequestValidatorTest,OpenSearchQueryBuilderTest,ListingSearchServiceTest,SearchSuggestionServiceTest,SearchControllerTest'
mvn test -Dtest=ListingSearchIntegrationTest      # OpenSearch 2.17.1 + PostgreSQL via Testcontainers

# Mobile
cd valuex-mobile
dart format lib test && flutter analyze
flutter test --dart-define=SKIP_PIXEL_CONTRAST=true test/features/search
flutter test --dart-define=SKIP_PIXEL_CONTRAST=true          # full suite, as CI runs it
```

`ListingSearchIntegrationTest` covers keyword, category (L1 to L3), price, condition, place, facet and Real Estate
intent searches, the ranking order (exact title, plan tier, weak match versus tier, recency, rating, nearby place),
disabled categories, own listings, a listing sold a moment ago, paging and the window, special characters and a
200-character query, the empty advisory, a missing token, the rate limit, and the cluster being unreachable.
