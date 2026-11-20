# US-019 - Add to Cart (Multi-Item): QA Testing Guide

**Sprint 5 · Cart, Checkout & Payments**

Manual test cases for the cart: adding an item while you hold an accepted price, the cart screen grouped by seller, the
status of each line, removing with Undo, the 20-item and 24-hour rules, the Buy Now hand-off, and the places that open
the cart (Home, Saved items). Backend and mobile.

> **What ships:** `GET /api/v1/cart`, `POST /api/v1/cart/items`, `DELETE /api/v1/cart/items/{itemId}`,
> `GET /api/v1/cart/summary`; migration `V41` (`carts`, `cart_items`, settings `CART_MAX_ITEMS` 20 and
> `CART_ITEM_TTL_HOURS` 24); the `cart` capability on the listing page with the new reason `NEGOTIATION_REQUIRED`; the
> expiry job (every 5 minutes, `valuex.cart.expiry-interval-ms`); the app's Cart screen (`/cart`), the Add to Cart
> button on the listing page and in Saved items, the Home cart icon and badge, and the Buy Now hand-off.
> **Not in this story:** "Proceed to checkout" (it is shown **disabled**, with "Checkout is coming soon"; US-021), choosing
> delivery per item (US-020: each line says "Choose at checkout"), paying, orders. The cart **ships dark**: with
> `CHECKOUT_ENABLED=false` (default) Add to Cart shows "Coming soon" and `POST /cart/items` answers 503; sections D
> onwards need `CHECKOUT_ENABLED=true`.

| Setting | Value |
|---|---|
| Backend base URL | `http://localhost:8080` |
| Admin settings | `CART_MAX_ITEMS` 20 (1 to 50), `CART_ITEM_TTL_HOURS` 24 (1 to 168) |
| Flag | `CHECKOUT_ENABLED=false` (default) or `true` |
| Error codes | 409 `ERROR_ITEM_UNAVAILABLE`, `ERROR_ITEM_RESERVED`, `ERROR_PRICE_NOT_ACCEPTED`, `ERROR_MAX_CART_ITEMS` (details `limit`), `ERROR_CHECKOUT_NOT_APPLICABLE`; 403 `ERROR_UNAUTHORIZED_CHECKOUT`, `AADHAAR_VERIFICATION_REQUIRED`; 404 `ERROR_CART_ITEM_NOT_FOUND`; 503 `ERROR_CHECKOUT_UNAVAILABLE`. In a line: `problem` `ERROR_ITEM_UNAVAILABLE`, `ERROR_PRICE_CHANGED`, `ERROR_CART_EXPIRED`, `ERROR_ACCEPTANCE_EXPIRED` |
| Known gaps | No checkout (US-021) and no delivery choice (US-020); Hindi texts need native review |

---

## Prerequisites

1. Backend, PostgreSQL and Redis running. For section C start the backend **without** the flag; for sections D to K
   start it with `CHECKOUT_ENABLED=true`.
2. Two sellers `$SELLER1` and `$SELLER2`, each with published goods listings (`$L1`, `$L2` for seller 1, `$L3` for
   seller 2, all negotiable); a published Real Estate listing `$PROPERTY`; two `ACTIVE`, Aadhaar-verified buyers `$BUYER1`
   and `$BUYER2`; one `ACTIVE` buyer without Aadhaar verification `$NEWBIE`.
3. Handy variables:

```bash
B="localhost:8080/api/v1"
H1="Authorization: Bearer $BUYER1"
H2="Authorization: Bearer $BUYER2"
HN="Authorization: Bearer $NEWBIE"
HS="Authorization: Bearer $SELLER1"
J="Content-Type: application/json"
buynow() { curl -s -i -X POST $B/listings/$1/buy-now -H "$2" -H "$J" -d '{"expectedPrice":"'$3'","clientRequestId":"'$(uuidgen)'"}'; }
addcart() { curl -s -i -X POST $B/cart/items -H "$2" -H "$J" -d '{"listingId":"'$1'"}'; }
```

---

## A. Migration and settings

| # | Steps | Expected |
|---|---|---|
| A1 | `SELECT version, success FROM flyway_schema_history WHERE version = '41';` | One successful row. |
| A2 | `\d cart_items` | `UNIQUE (cart_id, listing_id)`, `CHECK (negotiated_price > 0)`, the five delivery columns nullable, indexes on `expires_at` and `agreement_id`. `carts.buyer_id` is unique. |
| A3 | `SELECT setting_key, setting_value FROM platform_settings WHERE setting_key LIKE 'CART_%';` | `CART_MAX_ITEMS` 20 and `CART_ITEM_TTL_HOURS` 24. |

## B. Reads work without items

| # | Steps | Expected |
|---|---|---|
| B1 | `curl -s $B/cart -H "$H1"` | 200, `itemCount` 0, `validCount` 0, `groups` `[]`, `serverTime` set. |
| B2 | `curl -s $B/cart/summary -H "$H1"` | 200 `{"itemCount":0,"validCount":0}`. |
| B3 | `curl -s -i $B/cart` (no token) | 401. |

## C. Checkout switched off (default)

| # | Steps | Expected |
|---|---|---|
| C1 | `curl -s $B/listings/$L1/public -H "$H1" \| jq .data.capabilities.cart` | `{"available": false, "reason": "COMING_SOON"}`. In the app Add to Cart is dimmed; a screen reader says "Add to Cart, Coming soon". |
| C2 | `addcart $L1 "$H1"` | 503 `ERROR_CHECKOUT_UNAVAILABLE`; no `cart_items` row. |
| C3 | Reads (B1, B2) | Still 200. |

## D. Adding (flag on)

| # | Steps | Expected |
|---|---|---|
| D1 | `$BUYER1` has no price agreement on `$L1`. `curl -s $B/listings/$L1/public -H "$H1" \| jq .data.capabilities.cart`. | `{"available": false, "reason": "NEGOTIATION_REQUIRED"}`. In the app the button is **tappable**; the tap shows "Make an offer or Buy Now first" and sends nothing. |
| D2 | `addcart $L1 "$H1"` | 409 `ERROR_PRICE_NOT_ACCEPTED`. |
| D3 | `$BUYER1` makes an offer on `$L1` in the app and it is still waiting; `addcart $L1 "$H1"`. | 409 `ERROR_PRICE_NOT_ACCEPTED` ("Seller hasn't accepted your offer yet"). |
| D4 | The seller accepts the offer (price lock). The buyer opens the listing. | Capability `cart` available. `addcart $L1 "$H1"` returns **201** with `itemId`, `agreedPrice` equal to the accepted price, `status` `ACCEPTED`, `expiresAt` about 24 hours after `addedAt`. SQL: one `carts` row (`state` `CART_ACTIVE`) and one `cart_items` row with `negotiated_price` equal to the agreed price. |
| D5 | Repeat D4. | **200** with the **same** `itemId`; still one row; `expires_at` not extended. |
| D6 | In the app, open the listing and tap Add to Cart. | Snackbar "Added to your cart" with **View cart**; View cart opens the Cart. A second quick tap sends one request only. |
| D7 | `buynow $L3 "$H1" <price>` then `addcart $L3 "$H1"`. | The Buy Now agreement counts: 201. |
| D8 | `$BUYER1` taps Add to Cart on a listing with a bad network (airplane mode). | A message about the connection; nothing added. |

## E. Refusals

| # | Steps | Expected |
|---|---|---|
| E1 | As `$SELLER1` `addcart $L1 "$HS"` | 403 `ERROR_UNAUTHORIZED_CHECKOUT`; the app shows "You can't add your own item to the cart". |
| E2 | `addcart $PROPERTY "$H1"` | 409 `ERROR_CHECKOUT_NOT_APPLICABLE`. In the app a Real Estate page has no Add to Cart. |
| E3 | `$BUYER2` holds a Buy Now on `$L2`; `$BUYER1` calls `addcart $L2 "$H1"`. | 409 `ERROR_ITEM_RESERVED`; the capability for `$BUYER1` is `RESERVED`. |
| E4 | The listing is sold or unpublished (`UPDATE listings SET status = 'SOLD' ...`), then `addcart`. | 409 `ERROR_ITEM_UNAVAILABLE`. |
| E5 | `addcart $L1 "$HN"` as `$NEWBIE` | 403 `AADHAAR_VERIFICATION_REQUIRED`; the capability is `IDENTITY_REQUIRED`. |
| E6 | `curl -s -i -X POST $B/cart/items -H "$H1" -H "$J" -d '{}'` | 400 (listing id required). |
| E7 | `$BUYER1`'s accepted price on `$L1` has ended (`UPDATE price_agreements SET valid_until = now() - interval '1 second' WHERE ...`) and `$L1` is not in the cart; `addcart $L1 "$H1"`. | 409 `ERROR_PRICE_NOT_ACCEPTED` ("Make an offer or use Buy Now first"). |

## F. Cart limit

| # | Steps | Expected |
|---|---|---|
| F1 | `UPDATE platform_settings SET setting_value = '2' WHERE setting_key = 'CART_MAX_ITEMS';` (restart or wait for the settings cache), add two items, then a third. | 409 `ERROR_MAX_CART_ITEMS` with `details.limit` = 2; the app says "Cart limit reached (2 items)". Adding an item that is **already** in the cart still returns 200. |
| F2 | Two parallel `addcart` calls for **different** listings when one slot is left. | Exactly one succeeds. |
| F3 | Restore the setting to 20. | The limit is 20 again. |

## G. The Cart screen

Open the Cart from the header cart icon on Home (signed in).

| # | Steps | Expected |
|---|---|---|
| G1 | With items from `$SELLER1` (two) and `$SELLER2` (one). | One header per seller (the seller's name, or "Seller" when the name is not known), lines under their seller; the title shows "3 items"; each line has photo (or a placeholder), title, "Agreed price ₹...", a status badge "Accepted", "Price held for ..." until the agreement ends, "Leaves your cart in 23h ...", and "Choose at checkout". |
| G2 | Look at the footer. | "Total" with the sum of **Accepted** lines only, and **Proceed to checkout** dimmed, with "Checkout is coming soon". Tapping it does nothing. |
| G3 | Lower the listing price on a Buy Now line (seller edits price). | After a refresh the line shows "Expired", "Price changed. Please review" and "Now asking ₹..."; it is not in the total. An accepted **offer** line keeps its price and stays Accepted. |
| G4 | The seller suspends or sells a listing that is in the cart. | The line shows "Unavailable" and "No longer available"; it is not in the total. |
| G5 | `UPDATE price_agreements SET valid_until = now() - interval '1 second' ...` for a line. | After a pull to refresh the line shows "Expired" and "Price acceptance expired. Make a new offer". It stays 24 hours from when it was added. |
| G6 | A negotiation is open but not accepted for an item already in the cart. | "Pending", not in the total. |
| G7 | Pull down. | The cart is read again; with the network off, the lines stay and a message says "Couldn't refresh your cart. Showing what it held a moment ago". |
| G8 | While the Cart is open the seller cancels the agreement (or it is consumed). | The line changes without a manual refresh (event `agreement.updated`). |
| G9 | Kill the app's connection and reopen it (reconnect). | The cart is read again. |
| G10 | Empty cart. | "Your cart is empty" with a hint; no footer, no count. |
| G11 | First load fails (backend stopped). | An error with **Retry**; Retry reads again. |
| G12 | Back button. | Returns to the previous screen, or to Home if the Cart was opened first. |
| G13 | Sign out and open `/cart` (deep link). | Sent to Sign In. |

## H. Remove and Undo

| # | Steps | Expected |
|---|---|---|
| H1 | Tap **Remove** on a line. | The line goes at once with "Removed from your cart" and **Undo**; the Home badge drops by one. SQL: the row is gone; removing the last line sets `carts.state` back to `EMPTY`. |
| H2 | Tap **Undo** while the agreement still stands. | The line is back (a new 24 hours), the badge goes up. |
| H3 | Tap Undo after the agreement ended. | "Make an offer or use Buy Now first"; the line stays out. |
| H4 | `curl -s -i -X DELETE $B/cart/items/$ITEM -H "$H1"` twice. | 204 both times. |
| H5 | `DELETE` the line of `$BUYER1` as `$BUYER2`. | 404 `ERROR_CART_ITEM_NOT_FOUND`; the line is untouched. |
| H6 | Remove fails (backend stopped). | The line stays and a message says why. |

## I. 24-hour expiry

| # | Steps | Expected |
|---|---|---|
| I1 | `UPDATE cart_items SET expires_at = now() - interval '1 second' WHERE id = '<item>';` then `curl -s $B/cart -H "$H1"` **before** the job runs. | The line is `EXPIRED` with `problem` `ERROR_CART_EXPIRED`; in the app "Cart item expired. Please add again" and no "Leaves your cart in" line. |
| I2 | Add the same listing again at once. | 201: the expired line is replaced by a new one with a new 24 hours. |
| I3 | Wait up to 5 minutes (or set `valuex.cart.expiry-interval-ms` low). | The expired rows are deleted; a cart left with no lines goes to `EMPTY`; the metric `cart.expired` counts them. A line whose **agreement** ended but is not 24 hours old is **not** deleted. |
| I4 | Set `CART_ITEM_TTL_HOURS` to 1, add an item. | `expires_at` is about one hour after `added_at`. Restore 24. |

## J. Buy Now hand-off and other entry points

| # | Steps | Expected |
|---|---|---|
| J1 | In the app tap **Buy Now** on a listing. | One request; "Reserved for you and added to your cart"; the Cart opens with the item, "Accepted", "Price held for 14m" (the 15-minute hold). Back returns to the listing, read again. |
| J2 | Make the cart full, then tap Buy Now on another listing. | The reservation is made, the cart refuses: "Cart limit reached..."; the Cart does **not** open; the listing still shows Buy Now usable (a repeat tap returns the same reservation). |
| J3 | Saved items: an available item with an accepted price, tap **Add to Cart**. | "Added to your cart" with View cart. |
| J4 | Saved items: an item with no accepted price. | "Your price hasn't been accepted yet. Make an offer or use Buy Now first". |
| J5 | Saved items: a sold or under-review item. | No Add to Cart button (as before). |
| J6 | Home header. | The cart icon opens the Cart; the badge shows the number of lines (nothing when zero or when the cart cannot be read); a screen reader says "Cart, 2 items". |

## K. Races

| # | Steps | Expected |
|---|---|---|
| K1 | Two devices of `$BUYER1` tap Add to Cart on `$L1` together. | One row; one 201 and one 200. |
| K2 | `$BUYER1` has the agreement on `$L1`; `$BUYER2` calls `addcart $L1` at the same moment. | `$BUYER1` succeeds; `$BUYER2` gets `ERROR_ITEM_RESERVED` or `ERROR_PRICE_NOT_ACCEPTED`. |

## L. Language, layout and accessibility

| # | Steps | Expected |
|---|---|---|
| L1 | Switch the app to Hindi and open the Cart, the add messages and the errors. | Every text is in Hindi (draft; a native speaker reviews later). |
| L2 | A 320 px wide screen with text at 200 percent. | No overflow; remove, undo and the footer stay reachable. |
| L3 | Screen reader. | The title and each seller name are headers; each line is one sentence ("Hero phone, ₹4,500.50, Accepted, from Asha K"), with the problem read after it; **Remove** is a separate button of at least 48 dp; the total is one sentence. |

---

## Automated tests

```bash
# backend
cd valuex-backend
mvn test "-Dtest=Cart*Test,CheckoutSettingTest,ContactEligibilityServiceTest,PublicListingServiceTest,PlatformSettingsServiceTest"
$env:JAVA_TOOL_OPTIONS='-Dapi.version=1.44 -Duser.timezone=UTC'   # PowerShell, Testcontainers
mvn test "-Dtest=CartIntegrationTest,PublicListingIntegrationTest"

# mobile
cd valuex-mobile
flutter test --no-pub --dart-define=SKIP_PIXEL_CONTRAST=true test/features/cart test/features/listing_view test/features/saved_listings test/features/home test/core/routing
```

| Test | Covers |
|---|---|
| `CartServiceTest`, `CartIntegrationTest` | add order and refusals (D, E), idempotent re-add, limit and parallel adds (F, K), remove (H), expiry replacement (I2). |
| `CartItemViewAssemblerTest` | every status and `problem` (G3 to G6, I1). |
| `CartItemExpiryJobTest`, `CartIntegrationTest` | I3. |
| `ContactEligibilityServiceTest`, `PublicListingServiceTest`, `PublicListingIntegrationTest` | the `cart` capability and its reasons (C1, D1, E3, E5). |
| `cart_screen_test.dart`, `cart_providers_test.dart`, `cart_repository_test.dart` | G, H, L. |
| `listing_actions_test.dart`, `listing_add_to_cart_test.dart`, `listing_buy_now_test.dart` | D6, J1, J2. |
| `saved_items_screen_test.dart`, `home_screen_test.dart`, `api_home_repository_test.dart`, `route_guard_test.dart` | J3 to J6, G13. |
