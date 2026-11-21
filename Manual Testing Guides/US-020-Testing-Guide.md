# US-020 - Choose Delivery or Self-Pickup: QA Testing Guide

**Sprint 5 · Cart, Checkout & Payments**

Manual test cases for choosing how a cart item is received: saving an address (the first one is the default, naming it,
changing the default), delivery with its cost and date, self-pickup with Pay Now or Pay at Pickup, the terms, the
refusals, and what the cart shows afterwards. Backend and mobile.

> **What ships:** `GET /api/v1/cart/items/{itemId}/delivery-options?addressId=`, `PUT /api/v1/cart/items/{itemId}/delivery`
> and `POST /api/v1/users/me/addresses` (saving an address; before this story the app could only verify and list
> addresses); migration `V42` (`listings.pickup_address_id`, the delivery details on `cart_items`, a database rule that a
> line never mixes the two choices, settings `SHIPPING_STUB_FLAT_RATE` 60 and `SHIPPING_STUB_ETA_DAYS` 5); the app's
> Delivery screen (`/cart/items/:itemId/delivery`), the "Choose delivery" and "Change" buttons on each cart item, and the
> new-address form.
> **Not in this story:** checkout and payment (US-021; "Proceed to checkout" is still disabled), a real courier price
> (every delivery costs the flat stand-in rate until US-122), the seller's Pay at Pickup switch (US-022), a map (the
> pickup place is text), a screen to edit or delete addresses (US-113). Everything needs `CHECKOUT_ENABLED=true`,
> because an item reaches the cart only with it on.

| Setting | Value |
|---|---|
| Backend base URL | `http://localhost:8080` |
| Admin settings | `SHIPPING_STUB_FLAT_RATE` 60 (0 to 1000), `SHIPPING_STUB_ETA_DAYS` 5 (1 to 15) |
| Flag | `CHECKOUT_ENABLED=true` |
| Error codes | 409 `ERROR_NO_DELIVERY_AVAILABLE`, `ERROR_NO_SELF_PICKUP`, `ERROR_SHIPPING_CHANGED` (details `shippingCost`), or the item's own problem code (`ERROR_ITEM_UNAVAILABLE`, `ERROR_PRICE_CHANGED`, `ERROR_CART_EXPIRED`, `ERROR_ACCEPTANCE_EXPIRED`, `ERROR_PRICE_NOT_ACCEPTED`); 422 `ERROR_INVALID_ADDRESS`; 404 `ERROR_CART_ITEM_NOT_FOUND`; 400 terms not accepted or no payment option; saving an address: 400 `ERROR_ADDRESS_INVALID`, `ERROR_INVALID_ADDRESS_STATE`, `ERROR_PINCODE_MISMATCH`, `ERROR_ADDRESS_NOT_VERIFIED`, 503 `ERROR_ADDRESS_SERVICE_UNAVAILABLE`, 429 `ERROR_ADDRESS_RATE_LIMIT` |
| Known gaps | Pickup place is text only; no pickup hours; Hindi texts (and the terms in both languages) need review |

---

## Prerequisites

1. Backend, PostgreSQL and Redis running with `CHECKOUT_ENABLED=true`; the address provider on its default `sandbox`
   (it accepts any address whose pincode fits the state, for example 560038 for Karnataka and 411004 for Maharashtra; a
   street line containing "unverified" is refused and one containing "unavailable" behaves like an outage).
2. A seller `$SELLER` with a published goods listing `$L1` (negotiable) in Pune or Bengaluru, a Real Estate listing is not
   needed; an Aadhaar-verified buyer `$BUYER`, a second buyer `$OTHER`.
3. `$BUYER` has `$L1` in the cart: Buy Now (or an accepted offer), then Add to Cart (see US-019-Testing-Guide.md).
4. Handy variables:

```bash
B="localhost:8080/api/v1"
HB="Authorization: Bearer $BUYER"
HO="Authorization: Bearer $OTHER"
J="Content-Type: application/json"
ITEM=$(curl -s $B/cart -H "$HB" | jq -r '.data.groups[0].items[0].itemId')
addr() { curl -s -X POST $B/users/me/addresses -H "$HB" -H "$J" -d "$1"; }
choose() { curl -s -i -X PUT $B/cart/items/$ITEM/delivery -H "${3:-$HB}" -H "$J" -d "$1"; }
```

---

## A. Migration and settings

| # | Steps | Expected |
|---|---|---|
| A1 | `SELECT version, success FROM flyway_schema_history WHERE version = '42';` | One successful row. |
| A2 | `\d cart_items` and `\d listings` | `cart_items` has `shipping_eta`, `shipping_quote_valid_until`, `terms_accepted_at`, `terms_version` and the check `chk_cart_items_delivery`; `listings` has a nullable `pickup_address_id`. |
| A3 | `SELECT setting_key, setting_value FROM platform_settings WHERE setting_key LIKE 'SHIPPING_STUB_%';` | 60 and 5. |
| A4 | `UPDATE cart_items SET delivery_mode = 'DELIVERY' WHERE id = '<item>';` | Refused by the database (a delivery choice needs an address, a cost, a date and the terms). |

## B. Saving an address (API)

| # | Steps | Expected |
|---|---|---|
| B1 | `addr '{"address":"12 MG Road, Indiranagar","landmark":"Flat 4","city":"Bengaluru","state":"Karnataka","pincode":"560038","label":"Home"}'` for a buyer with **no** address. | 201; `defaultAddress` true, `verified` true, `label` "Home". SQL: one row, `is_default` true. |
| B2 | Save a second address (`"label":"Office"`, pincode 560025). | 201; `defaultAddress` **false**; the first is still the default. |
| B3 | Save a third with `"makeDefault": true`. | 201; it is now the default and `SELECT count(*) FROM addresses WHERE user_id = '<buyer>' AND is_default` is 1. |
| B4 | `curl -s $B/users/me/addresses -H "$HB"` | The three addresses, the default first. |
| B5 | Save with `"address":"1 unverified Street, Whitefield"`. | 400 `ERROR_ADDRESS_NOT_VERIFIED`; nothing saved. |
| B6 | Save with state Karnataka and pincode 411001. | 400 `ERROR_PINCODE_MISMATCH`. |
| B7 | Save with `"address":"short"`. | 400 (address between 10 and 255 characters). |
| B8 | Save with a label of 51 characters. | 400. |
| B9 | Two parallel saves of a first address for a new buyer. | Both 201; exactly one default. |

## C. What an item allows (API)

| # | Steps | Expected |
|---|---|---|
| C1 | `curl -s "$B/cart/items/$ITEM/delivery-options" -H "$HB"` | 200. `delivery.available` true with no cost (no address asked); `selfPickup.available` true with `pickupAddress` and `sellerDisplayName`. |
| C2 | The same with `?addressId=<home id>` | `delivery.cost` 60.00, `etaDate` five days from today (Indian time), `courierName` "Standard delivery", no `warning`. |
| C3 | Set `SHIPPING_STUB_FLAT_RATE` to 1000, restart or wait for the settings cache, and `UPDATE price_agreements SET agreed_price = 500 WHERE status = 'ACTIVE';`, then C2. | `warning` `SHIPPING_EXCEEDS_PRICE`. Restore both afterwards. |
| C4 | `?addressId=<$OTHER's address>` | 422 `ERROR_INVALID_ADDRESS`, "Please enter complete delivery address". |
| C5 | As `$OTHER`: `curl -s "$B/cart/items/$ITEM/delivery-options" -H "$HO"` | 404 `ERROR_CART_ITEM_NOT_FOUND`. |
| C6 | Make the item a whole vehicle: `UPDATE listings SET category_id = (SELECT c.id FROM categories c JOIN category_metadata_profiles cmp ON cmp.category_id = c.id JOIN metadata_profiles p ON p.id = cmp.profile_id WHERE p.code = 'CAR' LIMIT 1) WHERE id = '<listing>';` then C2. | `delivery.available` false, `reason` `ERROR_NO_DELIVERY_AVAILABLE`; `selfPickup.available` still true. |
| C7 | End the buyer's price (`UPDATE price_agreements SET status = 'CANCELLED' WHERE status = 'ACTIVE';`) then C1. | 409 `ERROR_ACCEPTANCE_EXPIRED`. Sold item: 409 `ERROR_ITEM_UNAVAILABLE`. Past 24 hours: 409 `ERROR_CART_EXPIRED`. |

## D. Where to collect (API)

| # | Steps | Expected |
|---|---|---|
| D1 | The seller has no saved address and typed "Whitefield, Bengaluru" on the listing. C1. | `pickupAddress` `line1` "Whitefield", `city` "Bengaluru", `pincode` null. |
| D2 | Save an address for the seller as the default (`INSERT INTO addresses ... is_default TRUE`) and repeat. | The seller's default address with its pincode. |
| D3 | `UPDATE listings SET pickup_address_id = '<another seller address>' WHERE id = '<listing>';` and repeat. | That address. |
| D4 | `UPDATE listings SET seller_location = NULL, seller_area = NULL, seller_state = NULL` for a seller with no address and repeat. | `selfPickup.available` false, `reason` `ERROR_NO_SELF_PICKUP`. |
| D5 | The full street address and the seller's phone. | Never in these answers: only line 1 (or the area), city, state and pincode. |

## E. Choosing (API)

| # | Steps | Expected |
|---|---|---|
| E1 | `choose '{"mode":"DELIVERY","addressId":"<home id>","expectedShippingCost":60,"termsAccepted":true}'` | 200 with the line: `delivery.mode` DELIVERY, `shippingCost` 60, `shippingEta`, `addressId`. SQL: `terms_version` `DELIVERY-1`, `terms_accepted_at` now, `shipping_quote_id` set. |
| E2 | `curl -s $B/cart -H "$HB"` | The line carries the same `delivery` block. |
| E3 | `choose '{"mode":"SELF_PICKUP","paymentOption":"PAY_NOW","termsAccepted":true}'` | 200; `delivery.mode` SELF_PICKUP, `paymentOption` PAY_NOW, no cost. SQL: the address, cost, date and quote columns are NULL; `terms_version` `PICKUP_PAY_NOW-1`. |
| E4 | The same with `"PAY_AT_PICKUP"`. | 200; `terms_version` `PICKUP_PAY_AT_PICKUP-1`. |
| E5 | Choose delivery again after E4. | 200; `payment_option` is NULL again: the line never mixes the two. |
| E6 | `"termsAccepted": false`, or leave it out. | 400 "You must agree to the terms to continue"; nothing changed. |
| E7 | `SELF_PICKUP` without `paymentOption`. | 400 "Choose Pay Now or Pay at Pickup". |
| E8 | `DELIVERY` without `addressId`, with another buyer's address, or with an address saved with an empty street line. | 422 `ERROR_INVALID_ADDRESS`. |
| E9 | `DELIVERY` with `"expectedShippingCost": 45` while the cost is 60. | 409 `ERROR_SHIPPING_CHANGED`, `details.shippingCost` "60.00"; nothing changed. |
| E10 | Whole vehicle (C6): `DELIVERY`; then `SELF_PICKUP`. | 409 `ERROR_NO_DELIVERY_AVAILABLE`; 200. |
| E11 | No pickup place (D4): `SELF_PICKUP`. | 409 `ERROR_NO_SELF_PICKUP`. |
| E12 | As `$OTHER`: `choose ... "$HO"`. | 404 `ERROR_CART_ITEM_NOT_FOUND`; the buyer's choice is untouched. |
| E13 | Six parallel choices on one item, mixed delivery and pickup. | All 200; the final row is consistent (a delivery has a cost and no payment option; a pickup the opposite). |
| E14 | Add the same listing to the cart again after a choice. | 200 and the choice is still there. |

## F. The Delivery screen (app)

Open the Cart, tap **Choose delivery** on an item.

| # | Steps | Expected |
|---|---|---|
| F1 | Look at the cart item before choosing. | "Choose at checkout" under the price and a **Choose delivery** button. An item that cannot be bought (Expired, Unavailable, Pending) has no button. |
| F2 | Open the screen. | Title "Delivery or pickup", the item and its agreed price, "How do you want to receive this?", two cards: Delivery and Self-pickup. |
| F3 | Tap Delivery. | Your saved addresses, the default preselected and marked "Default", "Add a new address", then the cost ("Shipping ₹60") and the date ("Arrives by Nov 25"). Save is off. |
| F4 | Tap the other address. | The cost and date are worked out again. |
| F5 | Tick "I agree to the terms above" under the delivery terms, then Save. | "Delivery choice saved", back to the Cart; the item shows "Delivery, ₹60, by Nov 25" and its button now reads **Change**. |
| F6 | Change the address after ticking the terms. | The tick is cleared: agree again. |
| F7 | Make shipping dearer than the item (C3 settings) and open Delivery. | "Shipping costs more than this item" under the cost; you can still save. |
| F8 | While the screen is open change `SHIPPING_STUB_FLAT_RATE` to 90 and tap Save. | "Shipping cost has changed to ₹90. Please review"; the new cost shows, the terms are cleared; Save again works. |
| F9 | Tap Self-pickup. | "Pickup location" with the place as text, "Seller: <name>", the note that the full address and contact come after the order, and **Pay Now** and **Pay at Pickup**. |
| F10 | Choose Pay Now, read the terms (escrow), tick, Save. | Saved; the item shows "Self-pickup, pay now". |
| F11 | Choose Pay at Pickup. | The red notice "Pay at Pickup is not protected by escrow" and the terms about paying the seller directly; Save; the item shows "Self-pickup, pay at pickup". |
| F12 | Open the screen again on a saved item. | It opens on the earlier choice (the address or the payment option selected). |
| F13 | Whole vehicle (C6). | Delivery is dimmed with "Seller doesn't offer delivery to your location"; Self-pickup opens by itself. |
| F14 | No pickup place (D4). | Self-pickup is dimmed with "Self-pickup not available for this item"; Delivery opens by itself. |
| F15 | A buyer with no saved address taps Delivery. | "Add an address to see the shipping cost and date" and the add button; Save is off. |
| F16 | Back button. | Returns to the Cart. |
| F17 | Stop the backend and open the screen. | An error with **Retry**; Retry works once the backend is back. |
| F18 | Open the screen for an item the seller sold meanwhile. | The reason ("No longer available" style text) with Retry/Back; nothing is saved. |

## G. Adding an address (app)

On the Delivery screen tap **Add a new address**.

| # | Steps | Expected |
|---|---|---|
| G1 | Look at the form. | "New address", a search box, street, landmark (optional), city, state, pincode, "Name this address" (Home, Office, Other), and for a buyer with no address "Your first address is saved as your default". Save is off. |
| G2 | Type in the search box and tap a suggestion (mock suggestions in dev). | Street, city, state and pincode fill in and stay editable. |
| G3 | Or fill the fields by hand: a street line of at least 10 characters, city, state, a 6-digit pincode not starting with 0. | Save turns on; after a pause "Address verified" appears. |
| G4 | Pincode that does not fit the state. | "The pincode does not match the selected city or state". |
| G5 | Pick Home, Save address. | The sheet closes; the new address is selected on the Delivery screen and priced. |
| G6 | A buyer who already has an address. | A switch "Make this my default address"; on, the new address becomes the default in the list. |
| G7 | Pick **Other** and type "Mum's flat". | That name is saved and shown in the list. |
| G8 | Stop the backend and tap Save address. | "We couldn't save the address. Please try again"; the form stays with your input. |

## H. Language, layout and accessibility

| # | Steps | Expected |
|---|---|---|
| H1 | Switch the app to Hindi and go through F and G. | Every text in Hindi (draft), including the three terms texts. |
| H2 | 320 px wide screen, text at 200 percent. | No overflow on the Cart, the Delivery screen or the form; every button stays reachable. |
| H3 | Screen reader. | Each option card and each address is one button that says whether it is selected; the cart item reads its delivery line after its price and status; the shipping cost is announced when it appears; every tap target is at least 48 dp. |
| H4 | Date format. | English "Nov 25"; Hindi in its own month name. |

---

## Automated tests

```bash
# backend
cd valuex-backend
mvn test "-Dtest=Delivery*Test,CartPickupAdapterTest,CartAddressAdapterTest,StubShippingQuoteAdapterTest,AddressCreationServiceTest,AddressControllerTest,CartControllerTest,CartItemViewAssemblerTest,CheckoutSettingTest"
$env:JAVA_TOOL_OPTIONS='-Dapi.version=1.44 -Duser.timezone=UTC'   # PowerShell, Testcontainers
mvn test "-Dtest=CartDeliveryIntegrationTest"

# mobile
cd valuex-mobile
flutter test --no-pub --dart-define=SKIP_PIXEL_CONTRAST=true test/features/cart test/features/address test/core/routing
```

| Test | Covers |
|---|---|
| `DeliveryLineGuardTest`, `DeliveryOptionsServiceTest` | C (every way an item can or cannot be received, the warning, the address rules). |
| `DeliveryChoiceServiceTest`, `DeliveryChoiceRequestTest` | E. |
| `CartDeliveryIntegrationTest` | A, B (including the parallel saves), C, D, E (including the parallel choices and the database rule). |
| `AddressCreationServiceTest`, `AddressControllerTest` | B. |
| `StubShippingQuoteAdapterTest`, `DeliveryEligibilityAdapterTest`, `CartPickupAdapterTest`, `CartAddressAdapterTest` | the ports and adapters behind C and D. |
| `delivery_screen_test.dart`, `address_form_sheet_test.dart` | F, G, H. |
| `cart_screen_test.dart`, `cart_repository_test.dart`, `delivery_models_test.dart`, `address_create_test.dart`, `cart_error_messages_test.dart`, `route_guard_test.dart` | F1, F5, the API calls, the models, the texts, the route. |
