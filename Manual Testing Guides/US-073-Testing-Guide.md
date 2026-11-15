# US-073 — Save and Bookmark Listings: QA Testing Guide

**Sprint 3 · Discovery & Search**

Manual test cases for saving a listing with the heart, the Saved Items page, and what happens to a saved listing when it
is sold, expires, is removed or deleted, its seller is no longer active, or it is only hidden for review. The backend is
checked with `curl` and SQL; the app is checked on Home, Search, the listing page, Profile and Notifications.

> **What ships:** `PUT` and `DELETE /api/v1/saved-listings/{listingId}` and `GET /api/v1/saved-listings`; the `saved`
> flag on search results, Home cards and the listing details; one in-app notification per buyer when a saved listing
> leaves the market; a daily cleanup of old unavailable entries; migration `V31`; Admin settings `SAVED_LISTING_MAX` and
> `SAVED_LISTING_RETENTION_DAYS` (backend). In the app: the heart on Home cards, search results and the listing page,
> the Saved Items page opened from Profile, and the notification link to it (mobile).
> **Not in this story:** Add to Cart or Buy from Saved Items (Sprint 5: the button is disabled), price-drop alerts, the
> count badge on the Profile hub's Saved Items row, an Admin screen for the two settings (US-116).

| Setting | Value |
|---|---|
| Backend base URL | `http://localhost:8080` |
| Endpoints | `PUT /api/v1/saved-listings/{id}` (200, repeat is harmless), `DELETE` (204, repeat is harmless), `GET ?page=0&size=20` (newest saved first; size 1 to 50) |
| Limit | `SAVED_LISTING_MAX`, default 200, allowed 10 to 500 |
| Retention | `SAVED_LISTING_RETENTION_DAYS`, default 90, allowed 7 to 365, counted from the day the listing became unavailable |
| Error codes | `ERROR_MAX_SAVED` (409), `ERROR_ITEM_UNAVAILABLE` (409), `LISTING_NOT_FOUND` (404) |
| Reasons | `SOLD`, `EXPIRED`, `REMOVED`, `DELETED`, `SELLER_SUSPENDED` (stored); `UNDER_REVIEW` (temporary, worked out when the list is read) |
| Known gaps | Hindi notification and screen texts need native-speaker review; the Profile Saved Items count badge is not built |

---

## Prerequisites

1. Backend, PostgreSQL and OpenSearch running (see the US-011 guide); the app running against it.
2. Three `ACTIVE` accounts, each with an access token: seller `$SELLER`, buyer `$BUYER` and a second buyer `$BUYER2`.
3. As the seller publish three goods listings (free Basic plan): `L1` (Smartphones, with photos), `L2` and `L3`.
4. Handy variables:

```bash
B="localhost:8080/api/v1"
HB="Authorization: Bearer $BUYER"
HB2="Authorization: Bearer $BUYER2"
```

---

## A. Save, list and remove (AC1, AC2)

| # | Steps | Expected |
|---|---|---|
| A1 | `curl -X PUT -H "$HB" $B/saved-listings/$L1` | 200. |
| A2 | Repeat A1 | 200 again; `SELECT count(*) FROM saved_listings WHERE listing_id = '<L1>'` is still 1. |
| A3 | `curl -H "$HB" "$B/saved-listings"` | `data.items` has `L1` with `title`, `price`, `condition` (a code such as `LIKE_NEW`), `photo.thumbnailUrl`, `available: true`, no `unavailableReason`, `savedAt`; `totalItems` 1; `maxSaved` 200. |
| A4 | `curl -H "$HB2" "$B/saved-listings"` | Empty list: another buyer never sees your list. |
| A5 | `curl -X DELETE -H "$HB" $B/saved-listings/$L1`, twice | 204 both times; the list is empty. |
| A6 | `curl -X PUT -H "$HB" $B/saved-listings/00000000-0000-0000-0000-000000000000` | 404 `LISTING_NOT_FOUND`. |
| A7 | Save a draft listing of the seller | 409 `ERROR_ITEM_UNAVAILABLE`: "This listing is no longer available". |
| A8 | Save `L1`, change its price in the database (`UPDATE listings SET price = 39000 WHERE id = '<L1>'`), list again | The item shows 39000: the list always shows the current price. |
| A9 | A buyer saves their own listing (`$SELLER` saves `L2`) | 200: there is no rule against it. |

## B. The heart in the app (AC1)

| # | Steps | Expected |
|---|---|---|
| B1 | Search for a phone; tap the heart on a result | The heart fills at once; `saved_listings` has the row. |
| B2 | Tap it again | The heart empties; the row is gone. |
| B3 | Open that listing from the result | Its page shows the heart filled (the server's `saved` flag) in the header. |
| B4 | Save it from the listing page, go back to the result list and to Home | The same listing's heart is filled on every screen. |
| B5 | Turn on airplane mode; tap a heart | The heart goes back and a message says it could not be updated. |
| B6 | Tap a heart very fast five times | One request is sent at a time; the end state matches the last settled tap. |
| B7 | Home > Featured Deals | Every card has a heart; one saved earlier is filled. |
| B8 | Turn on a screen reader | The heart reads "Save listing" or "Remove from saved" and is a button on its own, separate from the card. |

## C. Saved Items page (AC2)

| # | Steps | Expected |
|---|---|---|
| C1 | Profile > Saved Items | The page lists saved items newest first, each with photo, title, price and condition. |
| C2 | Tap an available item | Its listing page opens. |
| C3 | Look at "Add to Cart" | Shown disabled until Sprint 5. |
| C4 | Tap "Remove from saved" on an item | It leaves the list at once; the heart on that listing elsewhere is empty. |
| C5 | Remove while offline | The item comes back and a message says it could not be removed. |
| C6 | Remove every item | The empty state explains how to save one. |
| C7 | Pull down | The list reloads. |
| C8 | Save 25 items and scroll to the end | The next page loads without repeating an item. |
| C9 | Switch the app to Hindi and set the text size to 200% | The page reads in Hindi and nothing overflows. |

## D. When a saved listing is no longer available (AC3)

Save `L1`, `L2` and `L3` as `$BUYER`, and `L1` as `$BUYER2`.

| # | Steps | Expected |
|---|---|---|
| D1 | As the seller, delete `L2` in My Listings (or `UPDATE` through the admin tools: the status moves to `DEACTIVATED_BY_SELLER`) | `saved_listings` rows for `L2` have `unavailable_reason = 'DELETED'` and `unavailable_at` set. Each buyer has one `SAVED_LISTING_UNAVAILABLE` notification. |
| D2 | Open Saved Items | `L2` is greyed and says "No longer available"; it has no photo and only a Remove action. |
| D3 | Run the expiry sweep or move `L3` to `EXPIRED` | Reason `EXPIRED`; one notification per buyer: `"<title>" has expired.` |
| D4 | Remove `L1` as an admin | Reason `REMOVED`; both buyers are told once. |
| D5 | Mark a saved property Sold, Rented or Leased as its owner (US-118) | Reason `SOLD`; the buyer is told once. |
| D6 | Repeat the same change or event | No second notification (`SELECT count(*) FROM notifications WHERE event_type = 'SAVED_LISTING_UNAVAILABLE' AND user_id = '<buyer>'`). |
| D7 | Tap the notification | Saved Items opens. |
| D8 | Try to save an unavailable listing again | 409 `ERROR_ITEM_UNAVAILABLE`. |
| D9 | The notification text in Hindi | Names the listing; a native speaker should review the wording. |

## E. Review hold and seller changes

| # | Steps | Expected |
|---|---|---|
| E1 | Save `L1`; the seller edits it so it goes back to review (a major edit) | Saved Items shows `L1` as "Under review"; **no** notification; `unavailable_at` is null. |
| E2 | The listing is approved and published again | `L1` is available again in Saved Items. |
| E3 | Flag the seller for review (admin tools or `UserStateService.flagForReview`) | Saved entries of the seller's published listings show "No longer available" (`SELLER_SUSPENDED`); each buyer gets one message that says the listing "is no longer available" (the seller's account status is not disclosed). |
| E4 | Clear the review (the seller is `ACTIVE` again) | Those entries are available again; entries unavailable for another reason (for example sold) are not touched. |

## F. Limit and retention

| # | Steps | Expected |
|---|---|---|
| F1 | `UPDATE platform_settings SET setting_value = '10' WHERE setting_key = 'SAVED_LISTING_MAX'` (wait for the settings cache, a minute, or restart), save 10 listings, then an 11th | The 11th returns 409 `ERROR_MAX_SAVED`: "Maximum 10 saved items reached. Remove some to add more". In the app a message with the same text appears. Saving one that is already saved still answers 200. |
| F2 | Two devices save the 10th item at the same moment | Exactly one succeeds. |
| F3 | Set `unavailable_at` of one entry to 100 days ago and run the job (`SavedListingRetentionJob.purge`, or wait for 03:30) | That entry is deleted; an entry of an available listing is never deleted, however old. |
| F4 | Set `SAVED_LISTING_RETENTION_DAYS` to 7 and run the job | Entries unavailable for more than 7 days go at the next run, with no restart. |
| F5 | Set the setting to `abc` and run the job | The job uses 90 days and a warning is logged. |

---

## Edge cases and error scenarios

- Saving hundreds of items: the list is paged; page and size out of range are brought into range.
- A deleted or unknown listing id: 404; a listing that is not live: 409.
- A failure while sending a notification is logged (`ERROR_NOTIFICATION_FAILED`) and never changes the listing flow.
- Another buyer's list is never readable: every query is scoped to the caller.

## Automated tests

```bash
# backend (needs Docker for the integration test)
set JAVA_TOOL_OPTIONS=-Dapi.version=1.44 -Duser.timezone=Asia/Kolkata
mvn test -Dtest="SavedListing*Test,DiscoverySettingTest,ListingSearchServiceTest,PublicListingServiceTest"

# mobile
flutter test --no-pub --dart-define=SKIP_PIXEL_CONTRAST=true test/features/saved_listings test/features/notifications test/features/home test/features/listing_view test/features/search
```

Mapping: AC1 to A1, A2, B1 to B8; AC2 to A3, A5, C1 to C8; AC3 to D1 to D8; edge cases to A8, E1 to E4, F1 to F5.
