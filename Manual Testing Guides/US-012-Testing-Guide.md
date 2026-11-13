# US-012 — View Listing Details: QA Testing Guide

**Sprint 3 · Discovery & Search**

Manual test cases for the buyer's listing page: the photo gallery, title, description, condition, price, category path and
attributes, seller summary, listing age, the actions that exist today, the seller profile (their other listings and
reviews), and the unavailable and suspended states. The backend is checked with `curl`; the app is checked from the
Search results.

> **What ships:** `GET /api/v1/listings/{listingId}/public`, `GET /api/v1/sellers/{sellerId}/listings`,
> `GET /api/v1/sellers/{sellerId}/reviews` (backend); the listing page `/listing/:id` and the seller profile
> `/seller/:id` (mobile). A tap on a Search result card opens the listing page.
> **Not in this story:** the heart / saved items (US-073, `saved` is always `false`, no heart is shown), chat, call and
> video behaviour, Add to Cart and Buy Now (later sprints; shown disabled with "Coming soon"), seller reviews (Sprint 8,
> reported as "coming soon"), view counters (US-067), the Home cards (still "Coming soon").

| Setting | Value |
|---|---|
| Backend base URL | `http://localhost:8080` |
| Endpoints | the three above; any signed-in account (`Authorization: Bearer $TOKEN`) |
| Response header | `Cache-Control: no-store` on all three |
| Known gaps | Seller reviews always empty until Sprint 8 |

---

## Prerequisites

1. Backend, PostgreSQL, Redis and OpenSearch running (see the US-011 guide); the app running against it.
2. A buyer account (`$TOKEN`), and a seller account (`$TOKEN_S`) that is `ACTIVE`. As the seller publish:

| # | Title | Category | Price | Condition | Photos | Notes |
|---|---|---|---|---|---|---|
| L1 | iPhone 14 128GB | Smartphones (`CAT-0001`) | 42000 | GOOD | 3 | description, a few attributes filled |
| L2 | Wooden sofa 3 seater | Sofas (`CAT-0206`) | 15000 | LIKE_NEW | 1 | |
| L3 | Listing with no extra info | any | 500 | NEW | 1 | seller has only this and L1/L2 |
| L4 | 2 BHK apartment | Apartments & Condos (`CAT-0871`), intent SALE | 5500000 | - | 2 | for the Real Estate cases |

3. Handy variables:

```bash
B="localhost:8080/api/v1"
H="Authorization: Bearer $TOKEN"
L1=<listing id of L1>; SELLER=<seller id>
```

---

## A. Details of a live listing (AC1)

| ID | Steps | Expected |
|---|---|---|
| TC-001 | `curl -si -H "$H" "$B/listings/$L1/public"` | 200; `Cache-Control: no-store`; `title`, `description`, `condition {code,label}`, `price`, `currency: "INR"`, `category` (three steps), `attributes`, `photos` (3, in order, each with `thumbnailUrl`, `detailUrl`, `zoomUrl`), `seller`, `publishedAt`, `serverTime`, `capabilities`, `saved:false`, `ownListing:false` |
| TC-002 | Look through the whole body of TC-001 | No `status`, review reason, plan data, pincode, latitude/longitude, serial number, seller phone or email, Aadhaar state or seller full name |
| TC-003 | Compare `attributes` with the category form | Only filled attributes of the current form, with the form's label and unit; option values show the label, not the code |
| TC-004 | `curl -s "$B/listings/$L1/public"` (no token) | 401 |
| TC-005 | App: Search, tap the L1 card | The listing page opens with the photo gallery, category path, title, "Good", price, Negotiable (if set), location, "Posted … ago", description, item details and the seller card |
| TC-006 | App: check the page header | Back button and "Listing details"; no heart or save control |
| TC-007 | App: swipe the photos | The position ("2 / 3") changes; the thumbnail strip highlights the current photo |
| TC-008 | App: tap a thumbnail | The gallery jumps to that photo |
| TC-009 | App: tap a photo | A full-resolution, pinch-to-zoom view opens; Close returns to the page |
| TC-010 | App: open L2 (one photo) | No position badge and no thumbnail strip |
| TC-011 | App: attribute with yes/no, a list and a unit | "Yes"/"No", values joined with commas, the unit after the number (for example "91 %") |

## B. Listing age uses the server clock

| ID | Steps | Expected |
|---|---|---|
| TC-020 | `UPDATE listings SET published_at = now() - interval '3 days' WHERE id = '$L1'`, reopen L1 | "Posted 3 days ago" |
| TC-021 | Set the phone clock a month ahead or behind, reopen L1 | The text does not change |
| TC-022 | Set `published_at` to now | "Posted today"; one day earlier "Posted 1 day ago" |

## C. Real Estate (AC4)

| ID | Steps | Expected |
|---|---|---|
| TC-030 | `curl -s -H "$H" "$B/listings/$L4/public"` | `transactionIntent: "SALE"`, `capabilities.cart` and `capabilities.buyNow` are `{available:false, reason:"NOT_APPLICABLE"}` |
| TC-031 | App: open L4 | "For sale" label, category path, attributes, price; **no** Add to Cart and **no** Buy Now |
| TC-032 | A new-development listing with `priceQualifier = STARTING_FROM` | The price reads "Starting from ₹…" |
| TC-033 | App: open a goods listing | Add to Cart and Buy Now are shown, disabled, with "Coming soon" |

## D. Actions that are not built yet

| ID | Steps | Expected |
|---|---|---|
| TC-040 | App: look at the action area of L1 | Chat, Call, Video, Add to Cart and Buy Now are disabled, each with "Coming soon" |
| TC-041 | Tap each of them | Nothing opens and no message appears |
| TC-042 | App: open one of your own listings through its link (`/listing/<id>`) | The actions say "Your listing"; `ownListing` is true in the API |
| TC-043 | Screen reader on | Each action is read as, for example, "Chat, Coming soon" and as disabled |

## E. Seller profile (AC3)

| ID | Steps | Expected |
|---|---|---|
| TC-050 | App: on L1 tap the seller card | The seller profile opens on Listings: the seller's other live listings, newest first |
| TC-051 | `curl -s -H "$H" "$B/sellers/$SELLER/listings?page=0&size=1"` | One card, `hasNext` true when there are more; same card shape as search; the viewed listing itself is included in this list (the profile shows all of the seller's live listings) |
| TC-052 | App: tap a card on the profile | That listing opens; Back returns to the profile |
| TC-053 | Seller with 25 live listings (or `size=2` in the API) | "Load more" at the bottom appends the next page; it disappears on the last page |
| TC-054 | A seller whose only listing is hidden or sold | "This seller has no other listings" |
| TC-055 | App: Reviews tab | "Seller reviews are coming soon" |
| TC-056 | `curl -s -H "$H" "$B/sellers/$SELLER/reviews"` | `{"reviewsAvailable":false,"items":[]}` |
| TC-057 | `curl -s -H "$H" "$B/sellers/00000000-0000-0000-0000-000000000000/listings"` | 404 `SELLER_NOT_FOUND` |
| TC-058 | `curl -s -H "$H" "$B/sellers/$SELLER/listings?size=0"` and `?page=-1` | 400 `ERROR_INVALID_FILTERS` |

## F. Unavailable listing and suspended seller (AC5)

| ID | Steps | Expected |
|---|---|---|
| TC-060 | Open L2 in the app, then in SQL `UPDATE listings SET status='SOLD' WHERE id='<L2>'`, then reopen it | 404 `ERROR_LISTING_NOT_AVAILABLE`; the app says "This listing is no longer available" and has no Retry; Back works |
| TC-061 | Repeat TC-060 with `DELETED`, `EXPIRED` and a listing under review | The same error each time; no photo links in the response |
| TC-062 | `UPDATE users SET status='SUSPENDED' WHERE id='$SELLER'`, then open L1 and the seller profile | 403 `ERROR_SELLER_SUSPENDED`; the app says "This seller's listings are not available right now"; no photos are returned |
| TC-063 | Open a listing id that does not exist | 404 `ERROR_LISTING_NOT_AVAILABLE` |
| TC-064 | Turn the network off, open a listing | "Unable to connect" style message with Retry; Retry loads the page once the network is back |
| TC-065 | A photo whose file is missing | That photo shows a neutral placeholder; the rest of the page and the other photos still work |
| TC-066 | Listing whose photos use signed fallback links (`expiresAt` set) | "Photos not loading? Refresh" appears under the gallery; it loads the page again with fresh links. It is not shown when links are permanent |

## G. Accessibility, language and layout

| ID | Steps | Expected |
|---|---|---|
| TC-070 | Language Hindi (Profile, Language) | Page title, "Posted …", seller card, actions and states are in Hindi; the listing's own text stays as written |
| TC-071 | Phone text size 200% | Nothing overflows; the action area scrolls with the page instead of staying pinned |
| TC-072 | Narrow phone (320 px wide) | No clipped text or overflow |
| TC-073 | Screen reader | Gallery photos are read as "Photo 1 of 3. Enlarge photo"; thumbnails as "Show photo 2"; attributes as "label: value"; the seller card as one button "Name. View seller profile" |

## H. Privacy and no side effects

| ID | Steps | Expected |
|---|---|---|
| TC-080 | Open a listing several times; check `listings` and any view counters | Nothing is written: no counter and no event |
| TC-081 | Backend log while opening listings | No seller phone, email or address text |
| TC-082 | Sign out, then open `/listing/<id>` from a deep link | The app sends you to sign in |

---

## Automated tests

```bash
# Backend (needs Docker for the integration tests)
mvn verify "-Dapi.version=1.44" "-Duser.timezone=Asia/Kolkata" \
  -Dtest='PublicListing*Test,ListingSearchServiceTest,SearchRequestValidatorTest,OpenSearchQueryBuilderTest,ServiceUnavailableHandlerTest'

# Mobile
cd valuex-mobile
flutter test test/features/listing_view test/core/routing/route_guard_test.dart
```
