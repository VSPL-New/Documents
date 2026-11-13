# US-111 — Home Page: QA Testing Guide

**Sprint 3 · Discovery & Search**

Manual test cases for the data behind the Home page: the featured listings near the buyer, the active promos, the
popular category lists and the Home settings an Admin controls. The backend is checked with `curl` and SQL; the app is
checked on the Home tab.

> **What ships:** `GET /api/v1/home/featured`, `GET /api/v1/home/promos` (backend); the Home page reads them instead of
> sample data (mobile). Popular categories keep coming from `GET /api/v1/categories/children`, now limited by Admin
> settings.
> **Not in this story:** the buyer listing details screen (US-012 on mobile; a listing card or a promo for a listing says
> "This is coming soon"), the heart on cards (US-073), the cart count (Sprint 5, always 0), an Admin screen for promos
> and settings (Sprint 10; use SQL), category images from the server (artwork is chosen by category code).

| Setting | Value |
|---|---|
| Backend base URL | `http://localhost:8080` |
| Endpoints | the two above; any signed-in `ACTIVE` account (`Authorization: Bearer $TOKEN`) |
| Featured response header | `Cache-Control: private, max-age=60` |
| Promo cache | 5 minutes per language (delete the Redis keys `homePromos::EN` and `homePromos::HI` to skip the wait) |
| Known gaps | No promo rows are shipped; add them with SQL (case B). Search must be running for the featured feed |

---

## Prerequisites

1. Backend, PostgreSQL, Redis and OpenSearch running (see the US-011 guide); the app running against it.
2. A buyer account (`$TOKEN`) and a seller account that is `ACTIVE`. As the seller publish listings so the feed has
   something to rank:

| # | Title | Plan | City, State | Notes |
|---|---|---|---|---|
| L1 | Used office chair | Priority (top tier) | Pune, Maharashtra | |
| L2 | Samsung Galaxy phone | Boosted | Mumbai, Maharashtra | |
| L3 | Study table | none | Pune, Maharashtra | |
| L4 | Old bicycle | none | Delhi, Delhi | |
| L5 | Sofa | none | Pune, Maharashtra | published by the **buyer** account, to check own listings |

3. Handy variables:

```bash
B="localhost:8080/api/v1"
H="Authorization: Bearer $TOKEN"
```

---

## A. Featured Deals Near You (`/home/featured`)

| ID | Steps | Expected |
|---|---|---|
| TC-001 | `curl -si -H "$H" "$B/home/featured?city=Pune&state=Maharashtra"` | 200; `Cache-Control: private, max-age=60`; body `data` has `items`, `nearMatch: true`; no `advisory` |
| TC-002 | Read the order of `items` in TC-001 | Priority and Boosted listings first (L1, then L2), then Pune before other cities (L3), then the rest |
| TC-003 | Look at one card | `listingId`, `title`, `price`, `city`, `condition`, `sellerRating` (absent if none), `badge` (`FEATURED` or `BOOSTED` for paid plans), `photo.cardUrl`, `saved: false` |
| TC-004 | Sign in as the buyer, repeat TC-001 | L5 (the buyer's own listing) is not in `items` |
| TC-005 | `curl -s -H "$H" "$B/home/featured?city=Chennai&state=Tamil%20Nadu"` | 200; the best listings elsewhere are still returned; `nearMatch: false` |
| TC-006 | `curl -s -H "$H" "$B/home/featured"` (no place) | 200; listings in the national order; `nearMatch: false` |
| TC-007 | `curl -s -H "$H" "$B/home/featured?city=bangalore&state=karnataka"` after publishing a listing in Bengaluru | `nearMatch: true` (the city alias matches) |
| TC-008 | `curl -s -H "$H" "$B/home/featured?city=Pune&state=Atlantis"` | 400, `error.code` = `ERROR_INVALID_FILTERS` |
| TC-009 | `curl -s "$B/home/featured"` (no token) | 401 |
| TC-010 | Unpublish or delete every listing, repeat TC-001 | 200; `items` empty; `advisory.code` = `NO_LISTINGS_NEAR_YOU` |
| TC-011 | Stop OpenSearch, repeat TC-001 | 503, `error.code` = `ERROR_SEARCH_UNAVAILABLE`; start it again and the call works |
| TC-012 | Call `featured` 100 times in a minute, then search once: `curl -s -H "$H" "$B/search/listings?query=chair"` | Every `featured` call is 200 (no 429); the search is still allowed within its own limit (60 per minute) |

## B. Promos (`/home/promos`)

Add promos (run each once; `ends_at` and `starts_at` are relative to now):

```sql
INSERT INTO home_promos (badge, title, body, cta_label, title_hi, body_hi, cta_label_hi, image_key,
                         target_type, target_value, starts_at, ends_at, display_order) VALUES
 ('This week', 'Used cars sale', 'Find your next car', 'Shop cars', 'पुरानी कारों की सेल', 'अपनी अगली कार खोजें',
  'कारें देखें', 'home_promo_1', 'CATEGORY', 'L1-CARS', now() - interval '1 hour', now() + interval '1 day', 1),
 ('Deal', 'Chairs for less', 'Sit well', 'Shop chairs', NULL, NULL, NULL, NULL,
  'SEARCH', 'office chair', now() - interval '1 hour', now() + interval '1 day', 2);
```

| ID | Steps | Expected |
|---|---|---|
| TC-020 | `curl -s -H "$H" "$B/home/promos"` | 200; two promos in `display_order`; each has `id`, `badge`, `title`, `body`, `ctaLabel`, `imageKey`, `target {type, value}`; English text |
| TC-021 | Repeat with `-H "Accept-Language: hi"` | First promo in Hindi; second promo (no Hindi text) in English |
| TC-022 | Repeat with `-H "Accept-Language: en-IN,en;q=0.9,hi;q=0.8"` | English |
| TC-023 | `UPDATE home_promos SET ends_at = now() - interval '1 minute' WHERE title = 'Chairs for less'`, clear the Redis keys, repeat TC-020 | Only the cars promo |
| TC-024 | Set `starts_at` in the future for the cars promo, clear the keys, repeat | No promo (`data` is an empty list) |
| TC-025 | Set `enabled = false` for a promo, clear the keys, repeat | That promo is not returned |
| TC-026 | `INSERT` a promo with `target_type = 'URL'` | The database refuses it (check constraint): promos can never link outside the app |
| TC-027 | `INSERT` a promo with `ends_at` before `starts_at` | The database refuses it |
| TC-028 | `UPDATE platform_settings SET setting_value = '1' WHERE setting_key = 'HOME_PROMO_MAX'`, wait a minute, clear the keys, repeat TC-020 | One promo |
| TC-029 | `curl -s "$B/home/promos"` (no token) | 401 |
| TC-030 | Call twice in a row, change a promo's title in SQL, call again within 5 minutes | The old title is still served until the cache entry expires or is deleted |

## C. Home settings and popular categories

| ID | Steps | Expected |
|---|---|---|
| TC-040 | `SELECT setting_key, setting_value FROM platform_settings WHERE setting_key IN ('HOME_FEATURED_MAX','HOME_PROMO_MAX','CATEGORY_POPULAR_L1_MAX','CATEGORY_POPULAR_L2_MAX')` | `20`, `5`, `15`, `10` on a fresh database |
| TC-041 | `curl -s "$B/categories/children?scope=POPULAR"` | 15 L1 categories, in rank order |
| TC-042 | Set `CATEGORY_POPULAR_L1_MAX` to `5`, wait a minute, repeat TC-041 | 5 categories; `scope=OTHERS` is unchanged |
| TC-043 | Set `CATEGORY_POPULAR_L2_MAX` to `1`, wait a minute, call `scope=POPULAR` under any L1 | At most 1 sub-category |
| TC-044 | Set `HOME_FEATURED_MAX` to `4`, wait a minute, repeat TC-001 | At most 4 items |
| TC-045 | Set `HOME_FEATURED_MAX` to `40`, and both `SEARCH_PAGE_SIZE_DEFAULT` and `SEARCH_PAGE_SIZE_MAX` to `10` (the default may not be above the maximum, or the page-size settings go back to their defaults), wait a minute, repeat TC-001 | At most 10 items (never above a search page) |
| TC-046 | Set a value out of range (for example `HOME_FEATURED_MAX` = `3`), wait a minute, repeat TC-001 | The default of 20 is used and a warning is logged; the request does not fail |
| TC-047 | Re-run the V27 seed insert for `HOME_PROMO_MAX` (`... ON CONFLICT (setting_key) DO NOTHING`) after setting it to `3` | The value stays `3` |

## D. The Home tab in the app

| ID | Steps | Expected |
|---|---|---|
| TC-060 | App: sign in, open Home with location allowed | Header, promo card, "Browse" categories, "Featured Deals Near You" with real listings in two columns; no sample items (no "Sony A7 IV Camera") |
| TC-061 | Check the order against TC-002 | Boosted and Priority cards first with their badge |
| TC-062 | Look at one card | Image, title, price with Indian digit grouping (for example ₹1,85,000), city, rating with one decimal (hidden when none), condition |
| TC-063 | Tap the promo for a category | The Search screen opens with that category's listings |
| TC-064 | Tap the promo for a search text | The Search screen opens for that text |
| TC-065 | With no active promo | No promo section at all |
| TC-066 | Switch the app language to Hindi, pull down to refresh | The first promo shows its Hindi text; the second promo shows English |
| TC-067 | Tap a listing card | "This is coming soon" (until US-012 is merged on mobile) |
| TC-068 | Tap "See All" | The Search screen lists the same listings in the same order, with paging |
| TC-069 | Choose "Use my saved location" and a saved address in another city | The feed reorders for that city; check the backend log: the request has `city` and `state` but no pincode, area or coordinates |
| TC-070 | Deny location access, no saved place | The "use my location / saved location" prompt shows instead of the feed (unchanged behaviour) |
| TC-071 | Make the notification count 120 (insert unread notifications) | The bell badge shows "99+" |
| TC-072 | Cart icon | No badge (the cart count is 0 until Sprint 5) |

## E. Failures and partial responses

| ID | Steps | Expected |
|---|---|---|
| TC-080 | Stop OpenSearch, pull down to refresh | The promo card and categories stay; the featured section shows "Unable to load Home. Pull down or tap Retry" with a Retry button |
| TC-081 | Start OpenSearch, tap Retry | The listings appear and the message goes |
| TC-082 | Break only the promos call (for example rename the `home_promos` table, clear the Redis keys, refresh) | The promo card is hidden; categories and listings still show; no error message for promos |
| TC-083 | Turn the phone offline after Home has loaded, pull down | The last content stays with the error message and Retry |
| TC-084 | Turn the phone offline and open Home for the first time | The error state with Retry |
| TC-085 | An empty feed (TC-010) | "No items near you yet. Try another location" |

## F. Accessibility

| ID | Steps | Expected |
|---|---|---|
| TC-090 | Turn on the screen reader and open Home | Promo, category, card and navigation controls have labels; the empty cart reads "Cart, empty" and the bell reads its unread count |
| TC-091 | Set the text size to 200% and the language to Hindi | Nothing is cut off on the promo and cards |
| TC-092 | Check the tap areas | Every control is at least 48 by 48 dp |

---

## Automated tests for this story

```bash
# backend (from valuex-backend)
mvn test -Dtest='PromoLanguageTest,PromoServiceTest,PromoServiceCachingTest,HomeFeedServiceTest,HomeControllerTest,ListingSearchServiceTest,DiscoverySettingTest,CategoryServicePopularLimitTest'
mvn test -Dtest=HomeIntegrationTest        # needs Docker (PostgreSQL container)

# mobile (from valuex-mobile)
flutter test test/features/home test/core/network
```

On a machine where Docker 29 or later refuses the older Testcontainers client, add
`"-DargLine=-Dapi.version=1.44"`; if PostgreSQL rejects the `Asia/Calcutta` time zone, add `-Duser.timezone=Asia/Kolkata`
inside the same `argLine`.
