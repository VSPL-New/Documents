# US-068 - Direct Buy Now Flow: QA Testing Guide

**Sprint 4 · Communication & Negotiation**

Manual test cases for the Buy Now reservation: the seller's **Allow Buy Now** switch, the 15-minute reservation at the
asking price, the refusals, the release, how it interacts with offers and with a changed price, and the search page
that hides a held listing. Backend and mobile.

> **What ships:** `POST /api/v1/listings/{id}/buy-now`, `DELETE /api/v1/price-agreements/{id}`; migration `V39`
> (`listings.buy_now_enabled`, settings `BUY_NOW_RESERVATION_MINUTES` 15 and `BUY_NOW_PER_HOUR` 10); the flag
> `valuex.checkout.enabled` (environment `CHECKOUT_ENABLED`, default **false**); the capability reasons
> `DISABLED_BY_SELLER`, `RESERVED`, `IDENTITY_REQUIRED`, `COMING_SOON`; reserved listings are hidden from search
> result pages; a changed asking price cancels Buy Now reservations in the same transaction and tells the buyer
> (`BUY_NOW_PRICE_CHANGED`); the app has the switch, the Buy Now button with its messages, the shared
> `ReservationTimer` widget and the notification texts (English and Hindi).
> **Not in this story (Sprint 5):** the cart and the checkout screens. With `CHECKOUT_ENABLED` off, buyers see
> "Coming soon" on Buy Now and the endpoint answers 503; with it on, a successful tap only shows "Reserved for you.
> Checkout is coming soon" because the checkout route does not exist yet. The `ReservationTimer` is built and tested
> but is shown on no screen until the Sprint 5 checkout. Quantity above 1 is not handled (the whole listing is held).

| Setting | Value |
|---|---|
| Backend base URL | `http://localhost:8080` |
| Admin settings | `BUY_NOW_RESERVATION_MINUTES` 15 (1 to 60), `BUY_NOW_PER_HOUR` 10 (1 to 60) |
| Flag | `CHECKOUT_ENABLED=false` (default) or `true` |
| Error codes | 409 `ERROR_ITEM_SOLD`, `ERROR_ITEM_RESERVED`, `ERROR_PRICE_CHANGED` (details `currentPrice`), `ERROR_BUY_NOW_DISABLED`, `ERROR_BUY_NOW_NOT_APPLICABLE`, `ERROR_OWN_LISTING`; 404 `ERROR_LISTING_NOT_AVAILABLE`, `ERROR_AGREEMENT_NOT_FOUND`; 403 `AADHAAR_VERIFICATION_REQUIRED`, `ERROR_BLOCKED`; 422 `ERROR_NO_PURCHASE_OPTION` (listing save); 429 `RATE_LIMIT_EXCEEDED`; 503 `ERROR_CHECKOUT_UNAVAILABLE` |
| Known gaps | No checkout yet (Sprint 5); Hindi texts need native review |

---

## Prerequisites

1. Backend, PostgreSQL and Redis running. For sections D to J start the backend with `CHECKOUT_ENABLED=true`; for
   section C start it without.
2. A published goods listing `LISTING` owned by `$SELLER` with a price of 4500.50 and "Price negotiable" yes; a
   published Real Estate listing `PROPERTY`; two `ACTIVE`, Aadhaar-verified buyers `$BUYER1` and `$BUYER2`; one
   `ACTIVE` buyer without Aadhaar verification `$NEWBIE`.
3. Handy variables:

```bash
B="localhost:8080/api/v1"
HS="Authorization: Bearer $SELLER"
H1="Authorization: Bearer $BUYER1"
H2="Authorization: Bearer $BUYER2"
HN="Authorization: Bearer $NEWBIE"
J="Content-Type: application/json"
buynow() { curl -s -i -X POST $B/listings/$1/buy-now -H "$2" -H "$J" -d '{"expectedPrice":"'$3'","clientRequestId":"'$(uuidgen)'"}'; }
```

---

## A. Migration, settings and flag

| # | Steps | Expected |
|---|---|---|
| A1 | `SELECT version, success FROM flyway_schema_history WHERE version = '39';` | One successful row. |
| A2 | `SELECT column_name, column_default, is_nullable FROM information_schema.columns WHERE table_name = 'listings' AND column_name = 'buy_now_enabled';` and `SELECT count(*) FROM listings WHERE buy_now_enabled = FALSE;` | The column defaults to `true`, not null; no existing listing has it off. |
| A3 | `SELECT setting_key, setting_value FROM platform_settings WHERE setting_key LIKE 'BUY_NOW_%';` | `BUY_NOW_RESERVATION_MINUTES` 15 and `BUY_NOW_PER_HOUR` 10. |

## B. The seller's switch

| # | Steps | Expected |
|---|---|---|
| B1 | Create a goods listing (app: Sell, Item Details). | **Allow Buy Now** shows under "Price is negotiable", switched **on**, with "Buyers can reserve this item at your asking price without making an offer." |
| B2 | Choose "Price is negotiable: No" and switch Allow Buy Now off. | The message "Turn on Buy Now or allow offers so buyers can purchase" shows; Choose Listing Plan stays disabled. Switching either back on clears it. |
| B3 | Save with Buy Now off and negotiable yes; reopen the listing from My Listings. | The switch is off. `GET /listings/{id}` (owner) has `"buyNowEnabled": false`. |
| B4 | `curl -X PATCH $B/listings/$LISTING -H "$HS" -H "$J" -d '{...valid body..., "negotiable": false, "buyNowEnabled": false}'` | 422 `ERROR_NO_PURCHASE_OPTION`; nothing saved. |
| B5 | A body that does not mention `buyNowEnabled` (older app) on a listing where it is off. | The switch stays off. |
| B6 | Edit a published listing and change only the switch. | Saved at once, the listing stays live (no new review); `listing_edit_history.changed_fields` contains `buyNowEnabled`. |
| B7 | Create or edit a Real Estate listing. | No Allow Buy Now switch; the app does not send it; `buy_now_enabled` stays `true` and the details page shows no Buy Now button. |
| B8 | Open **Preview** of a goods listing (Buy Now on, then off). | "Buy Now on" appears next to the price while it is on and is gone when it is off. |

## C. Checkout switched off (default)

| # | Steps | Expected |
|---|---|---|
| C1 | `curl -s $B/listings/$LISTING -H "$H1" \| jq .data.capabilities.buyNow` | `{"available": false, "reason": "COMING_SOON"}`. In the app Buy Now is disabled and speaks "Buy Now, Coming soon". |
| C2 | `buynow $LISTING "$H1" 4500.50` | 503 `ERROR_CHECKOUT_UNAVAILABLE`; no `price_agreements` row. |
| C3 | Seller switch off, then C1. | `DISABLED_BY_SELLER` (the app speaks "Buy Now is off for this item"); the seller switch works before checkout exists. |

## D. Reserving (flag on)

| # | Steps | Expected |
|---|---|---|
| D1 | `buynow $LISTING "$H1" 4500.50` | 201 with `agreementId`, `source` `BUY_NOW`, `agreedPrice` 4500.50, `validUntil` about 15 minutes after `serverTime`. SQL: one `price_agreements` row `ACTIVE`, `negotiation_id` null. |
| D2 | Repeat D1 as the same buyer. | 200 with the **same** `agreementId`; still one `ACTIVE` row. |
| D3 | `buynow $LISTING "$H2" 4500.50` | 409 `ERROR_ITEM_RESERVED`; the answer names no one. |
| D4 | `buynow $LISTING "$H2" 4000.00` (after releasing D1, section F) | 409 `ERROR_PRICE_CHANGED`, `details.currentPrice` `4500.50`. Never a reservation at the client's price. |
| D5 | Send `"expectedPrice": "4500.5"` (other scale). | Accepted as the same price. |
| D6 | `buynow $PROPERTY "$H1" <price>` | 409 `ERROR_BUY_NOW_NOT_APPLICABLE`. |
| D7 | Switch the listing's Buy Now off, then `buynow`. | 409 `ERROR_BUY_NOW_DISABLED`. |
| D8 | `UPDATE listings SET status = 'SOLD' WHERE id = '$LISTING';` then `buynow` (restore afterwards). | 409 `ERROR_ITEM_SOLD`. Any other non-live status (for example `EXPIRED`, `ORDER_CREATED`) gives 404 `ERROR_LISTING_NOT_AVAILABLE`. |
| D9 | `buynow $LISTING "$HS" 4500.50` | 409 `ERROR_OWN_LISTING`. |
| D10 | `buynow $LISTING "$HN" 4500.50` | 403 `AADHAAR_VERIFICATION_REQUIRED`. |
| D11 | Block the seller from `$BUYER1`'s side (or the reverse), then `buynow`. | 403 `ERROR_BLOCKED` (same answer as chat). |
| D12 | Set `BUY_NOW_PER_HOUR` to 1; make two reservations for different listings within the hour. | The second is 429 `RATE_LIMIT_EXCEEDED`. Restore to 10. |
| D13 | Wait 15 minutes (or `UPDATE price_agreements SET valid_until = now() - interval '1 second'`), then `buynow` as `$BUYER2`. | Succeeds even before `AgreementExpiryJob` runs (a lapsed hold never blocks). Within a minute the job marks the old row `EXPIRED`. |

## E. Two buyers at once

| # | Steps | Expected |
|---|---|---|
| E1 | Fire D1 for `$BUYER1` and `$BUYER2` at the same moment (two terminals, or `xargs -P2`). | Exactly one 201 and one 409 `ERROR_ITEM_RESERVED`; one `ACTIVE` row. |

## F. Releasing

| # | Steps | Expected |
|---|---|---|
| F1 | `curl -s -i -X DELETE $B/price-agreements/$AGREEMENT -H "$H1"` | 204. SQL: `status` `CANCELLED`, `ended_reason` `RELEASED_BY_BUYER`. The listing is open to everyone at once. |
| F2 | Repeat F1. | 204 again, nothing changes. |
| F3 | `DELETE` the agreement as `$BUYER2`, or an unknown id. | 404 `ERROR_AGREEMENT_NOT_FOUND`. |
| F4 | Release an agreement that came from an accepted offer (buyer is `$BUYER1`). | 204; the negotiation becomes `NEGOTIATION_CANCELLED` (as if the buyer withdrew the offer) and the seller is told. |

## G. Buy Now and offers

| # | Steps | Expected |
|---|---|---|
| G1 | `$BUYER1` holds a Buy Now (D1). `$BUYER2` makes an offer. | 409 `ERROR_ITEM_RESERVED`. After F1, the offer is accepted (201). |
| G2 | `$BUYER2` has an offer waiting; `$BUYER1` starts a Buy Now; the seller accepts `$BUYER2`'s offer. | 409 `ERROR_ALREADY_ACCEPTED` with the neutral text "This item is reserved for another buyer right now". |
| G3 | `$BUYER1` has an open offer waiting for the seller, then taps Buy Now. | 201. The offer is `NEGOTIATION_CANCELLED` with `closed_reason` `REPLACED_BY_BUY_NOW`; the seller gets "Offer withdrawn", the thread shows a withdrawn card. |
| G4 | `$BUYER1`'s offer was accepted at 4000 (price lock active), then Buy Now. | 200 with the existing agreement (`source` `OFFER`, 4000); no second agreement. |
| G5 | Listing details as `$BUYER2` while `$BUYER1` holds it. | `capabilities.buyNow` is `RESERVED`, `capabilities.offer` is `RESERVED`; the app speaks "Buy Now, Reserved right now". |

## H. A changed price

| # | Steps | Expected |
|---|---|---|
| H1 | `$BUYER1` holds a Buy Now at 4500.50. The seller changes the price to 4000 (app Edit, or `PATCH` with `"price": 4000`). | The reservation is `CANCELLED` with `ended_reason` `PRICE_CHANGED` as part of the edit. `$BUYER1` has a notification "Price changed for <item>" / "Please review the new price" (Hindi in the Hindi app); tapping it opens the listing. |
| H2 | `$BUYER1` taps Buy Now again with the old price on screen. | 409 `ERROR_PRICE_CHANGED`; the app says "The price has changed. Please review the new price and try again" and reads the page again, which now shows 4000. |
| H3 | A price edit that fails validation (rolled back). | The reservation stays `ACTIVE`; no notification. |
| H4 | Edit only the title. | The reservation stays `ACTIVE`. |
| H5 | A price change while the holder has an accepted **offer** price (`source` `OFFER`). | The negotiated price stands; the agreement stays `ACTIVE`. |
| H6 | Turn the seller's switch off while a reservation is held. | The reservation stays; only new ones stop. |

## I. Search

| # | Steps | Expected |
|---|---|---|
| I1 | Search for the listing while it is free. | It is in the results. |
| I2 | Make a Buy Now reservation, search again (and open Home). | It is not in the result pages; opening it by link still works. |
| I3 | Release, or let it expire. | It shows in search again at once. |
| I4 | While it is held: saved listings and saved-search alerts. | The listing still shows as live in Saved Items (those use the live check only). |

## J. Mobile

| # | Steps | Expected |
|---|---|---|
| J1 | Buyer opens the listing with `CHECKOUT_ENABLED=true`, taps Buy Now. | One request; the message "Reserved for you. Checkout is coming soon" shows; the page is read again and, for you, Buy Now remains usable (the repeat returns the same reservation). |
| J2 | Tap twice quickly. | One request reaches the server. |
| J3 | Another buyer's hold, sold item, switched-off, price changed. | The messages of D3, D8, D7 and D4 in English and Hindi; the page is read again. |
| J4 | 320 px wide, 200 percent text, TalkBack/VoiceOver on the switch and the button. | No overflow; the switch is announced with its label and state; the caption of a disabled Buy Now is spoken. |
| J5 | `ReservationTimer` (widget tests only for now): counts down from the server time, red in the last minute, announces the minutes left once a minute and every 10 seconds in the last minute, "Reservation ended" at zero, Hindi. | See the automated tests below. |

---

## Automated tests

```bash
# backend (Docker running; the integration test starts PostgreSQL)
export JAVA_TOOL_OPTIONS="-Dapi.version=1.44 -Duser.timezone=Asia/Kolkata"
mvn -o test -Dtest='BuyNow*Test,PriceAgreementServiceTest,NegotiationServiceTest,ContactEligibilityServiceTest,PublicListingServiceTest,ListingDetailsServiceTest,ListingEditServiceTest,ListingEligibilityFilterTest,ListingSearchServiceTest'

# mobile
flutter test --dart-define=SKIP_PIXEL_CONTRAST=true test/features/buy_now test/core/widgets/reservation_timer_test.dart test/features/listing_view test/features/listing test/features/negotiation
```
