# US-020: Choose Delivery or Self-Pickup - Implementation Plan

## 1. Header

| Field | Value |
|---|---|
| Story | US-020 - Choose Delivery or Self-Pickup |
| Sprint | Sprint 5 - Cart, Checkout & Payments |
| Story points | 5 |
| Repos involved | valuex-backend (`cart` delivery endpoints, a `shipping` port with a stub adapter, a create-address endpoint in `user`, a pickup-location read) and valuex-mobile (delivery screen reached from each cart line, address entry, cart line summary). No `valuex-ai`, `valuex-web` or infra change. |
| Dependencies | US-019 (cart lines and the five delivery columns; **built and merged 2026-11-20**: backend #76, mobile #83, Documents #296 and #298), US-108 (address verification and the address component; built). |
| Blocks | US-090 and US-091 (order lifecycle), US-021 (checkout refuses a line with no delivery choice), US-022 (pay at pickup rules), US-122 (replaces the stub quote adapter). |
| Date | 2026-11-20 (revised 2026-11-21 with your answers to the open gaps) |
| Design source | [Sprint 5 LLD](../LLD/Sprint-5-Cart-Checkout-Payments-LLD.md): Part B (B.1 to B.5), D6 and D7 of section 0.7, settings 0.4, error codes 0.5, Part M (My Addresses placeholder), N.4 gaps G2, G3, G6, G7, G18, G19 (all agreed or decided 2026-11-20). Also `user-stories.md` US-020 and its 2026-10-25 category update. |
| Branches | `feature/US-020-delivery-or-pickup` in `valuex-backend` and `valuex-mobile`; `docs/US-020-delivery-or-pickup` in `Documents`; all cut from updated `main` (G1: US-019 is merged). |
| Flyway number | `V42__cart_delivery.sql` (`V41` is the cart, now on `main`). Re-check at branch time. |

## 2. Story Recap

**As a** buyer **I want to** choose between delivery or self-pickup **so that** I have flexibility in receiving my item.

> Update (2026-10-25, category taxonomy): home delivery is offered only for delivery-eligible categories where Shiprocket serviceability returns a courier (US-122). Whole vehicles and Real Estate are never delivery-eligible.

**Acceptance criteria:**

| ID | Criterion |
|---|---|
| AC1 | When I view delivery options for an item I am checking out, I see **Delivery** (address selection, estimated delivery date, shipping cost) and **Self-Pickup** (seller's pickup location, pickup hours). |
| AC2 | Choosing Delivery lets me add or select an address. With no saved address I am asked to enter one (entry and verification: US-108) and it is saved as my default; with saved addresses my default is preselected, I can pick another or enter a new one and name it (Home, Office, custom). Shipping cost is calculated. |
| AC3 | Choosing Self-Pickup lets me choose "Pay Now" (escrow) or "Pay at Pickup" (direct to seller), and I see the seller's pickup address and contact. |

**Edge cases:** seller does not offer delivery; seller does not offer self-pickup; buyer's address is outside the serviceable area; shipping cost exceeds the item price; seller location too far for self-pickup.

**Validation rules:** at least one option available; delivery address complete with pincode; self-pickup address valid; shipping cost calculated before checkout; buyer agrees to the terms for the selected option.

**Error codes:** `ERROR_NO_DELIVERY_AVAILABLE` "Seller doesn't offer delivery to your location"; `ERROR_NO_SELF_PICKUP` "Self-pickup not available for this item"; `ERROR_INVALID_ADDRESS` "Please enter complete delivery address".

**Flutter notes (story):** delivery option card with the reusable address component and the saved addresses; shipping cost from a backend API on address selection; self-pickup location on an embedded map.

## 3. Design Reference and Key Decisions

LLD Part B with section 0 and N.4. What it means for this story:

- **The choice lives on the cart line.** `cart_items` already has `delivery_mode`, `delivery_address_id`, `shipping_quote_id`, `shipping_cost`, `payment_option` (V41, all NULL). US-020 fills them. Checkout (US-021) refuses a line without a choice (`ERROR_DELIVERY_NOT_CHOSEN`, decided in Part B.5, built there).
- **Two endpoints (B.2):** `GET /cart/items/{itemId}/delivery-options?addressId=` (what the line allows, HTTP 200 even when nothing is available) and `PUT /cart/items/{itemId}/delivery` (store the choice).
- **No distance rule, no pickup hours (G6).** Self-pickup is offered from any city or state, delivery at any serviceable distance. The pickup block shows the address only; the seller's city may be shown as information.
- **Pickup details before an order (B.2):** the pickup address is shown as line 1, city and pincode; the full address and the seller's phone are revealed only after the order exists (Part H). See gap G4: the story says "address and contact".
- **Shipping quotes (D6, G3):** `ShippingQuotePort` with `StubShippingQuoteAdapter` (`valuex.shipping.provider=stub`): flat `SHIPPING_STUB_FLAT_RATE` (60), ETA today plus `SHIPPING_STUB_ETA_DAYS` (5). `DeliveryEligibilityPort`: goods are eligible; whole vehicles and Real Estate are not (from `CategoryLeaf.group()`). US-122 replaces both adapters by configuration.
- **Pickup address (G2):** new nullable `listings.pickup_address_id`; when null, the seller's default address; see gap G3 for sellers who have no address.
- **Address rules (B.2):** `addressId` belongs to the buyer and has line 1, city, state and a valid pincode (`ERROR_INVALID_ADDRESS`, 422). Naming uses `addresses.label`.
- **Amounts are server decided.** The app never sends a price or a shipping cost. Shipping above the item price is allowed and returned with `warning: SHIPPING_EXCEEDS_PRICE`.
- **Settings (0.4):** `SHIPPING_STUB_FLAT_RATE` (0 to 1000) and `SHIPPING_STUB_ETA_DAYS` (1 to 15) join `CheckoutSetting`; seeded in V42.
- **Not in this story:** checkout and its terms record (US-021), the Pay at Pickup seller switch and order rules (US-022, G19), the My Addresses screen (US-113), real couriers (US-122), a map widget (address text until one exists, G7).

### Verified implementation anchors (checked 2026-11-20 against the working copies)

| Area | Finding and consequence |
|---|---|
| Addresses (backend) | `AddressController` has only `GET /users/me/addresses` and `POST /addresses/verify`. **Nothing saves an address**: `AddressService` never calls `save`, and the one row in the dev database was inserted by hand. The LLD sentence "a new address is created through the existing `AddressController`" is therefore wrong. A create endpoint is needed (gap G2). |
| Addresses (data) | `addresses` has `label`, `is_default` (unique per user), `verified`, `place_id`; no phone and no contact name. `cart_items.delivery_address_id` already references it, so an address used by a line cannot be deleted (the G18 guard has nothing to guard until US-113 adds a delete endpoint). |
| Listings | No `pickup_address_id`; only `seller_location`, `seller_area`, `seller_state` text columns. |
| Category group | `CategoryLeaf.group()` returns `GOODS`, `WHOLE_VEHICLE` or `REAL_ESTATE`; `ListingFactsAdapter` already uses it for `realEstate`. Eligibility reads it the same way; there is no weight or per-category delivery data (US-122). |
| Cart | `CartLine.Delivery(mode, shippingCost, paymentOption)` exists in the DTO and is always null; `CartRepository` has no update for the delivery columns; `CartService.view` assembles the line. |
| Mobile | `features/address` has `AddressRepository.savedAddresses`, `verify`, `SavedAddress` (id, label, address, landmark, city, state, pincode, isDefault), `AddressSearchField` (used in one place) and `addressVerificationProvider`. There is no save call and no "choose an address" widget. The cart line shows the fixed text "Choose at checkout". Profile > My Addresses stays "Coming soon". |

## 4. Implementation Steps

### Database
- [ ] `V42__cart_delivery.sql`: `listings.pickup_address_id UUID REFERENCES addresses (id)`; `cart_items` gains `shipping_eta DATE`, `shipping_quote_valid_until TIMESTAMPTZ`, `terms_accepted_at TIMESTAMPTZ`, `terms_version VARCHAR(30)`; CHECKs: `delivery_mode IN ('DELIVERY','SELF_PICKUP')`, `payment_option IN ('PAY_NOW','PAY_AT_PICKUP')`, a `DELIVERY` row has an address and a cost and no payment option, a `SELF_PICKUP` row has a payment option and no address; seeds `SHIPPING_STUB_FLAT_RATE` 60 and `SHIPPING_STUB_ETA_DAYS` 5 in `platform_settings` (`ON CONFLICT DO NOTHING`).

### Backend
- [ ] `plans/domain/CheckoutSetting`: add the two stub keys with defaults and ranges; test in `CheckoutSettingTest`.
- [ ] `shipping` module: `ShippingQuotePort` and `DeliveryEligibilityPort` as LLD B.3; `StubShippingQuoteAdapter` (flat rate and ETA from the settings, `@ConditionalOnProperty valuex.shipping.provider=stub`, matchIfMissing); `ShippingProperties`; `package-info.java`.
- [ ] `user`: `POST /users/me/addresses` (G2): body is the verified address (line 1, landmark, city, state, pincode, `placeId`) plus `label` (max 50, optional) and `makeDefault`; the server runs the same provider verification as `verify` (rate limit included), saves with `verified = true`, and makes it the default when the user has none (or `makeDefault` is true, clearing the old default in the same transaction). Response `SavedAddressResponse`. `AddressService.create`, request DTO with validation, `ERROR_INVALID_ADDRESS` (422) for an incomplete address.
- [ ] `cart/application/port`: `CartAddressPort` (buyer's own address by id, complete or not; adapter in `user`) and `CartPickupPort` (`pickupFor(listingId)`: `pickup_address_id`, else the seller's default address, else empty; adapter in `listing`). Both return line 1, city, state, pincode only.
- [ ] `listing`: `Listing.pickupAddressId` (column mapping); the adapters above; `DeliveryEligibilityPort` adapter reads `CategoryLeaf.group()`.
- [ ] `cart/application/service/DeliveryOptionsService`: `options(buyerId, itemId, addressId)` as LLD B.2: `selfPickup` (available when `CartPickupPort` returns a location; `{ pickupAddress, sellerDisplayName }`), `delivery` (eligible and a quote returned: `{ cost, etaDate, courierName, warning? }`; with no `addressId` it returns eligibility only), and the reasons `ERROR_NO_DELIVERY_AVAILABLE` and `ERROR_NO_SELF_PICKUP` as fields of the 200 response. Only the buyer's own live line (`ERROR_CART_ITEM_NOT_FOUND` otherwise); an expired or unavailable line answers its `problem` code.
- [ ] `cart/application/service/DeliveryChoiceService.choose(buyerId, itemId, request)` (one transaction, cart row locked as `CartService.add` does): `DELIVERY` validates the address (`ERROR_INVALID_ADDRESS`), eligibility (`ERROR_NO_DELIVERY_AVAILABLE`), re-quotes, compares `expectedShippingCost` when sent (`ERROR_SHIPPING_CHANGED` 409 with the new cost, G5), stores address, cost, ETA, quote id and `shipping_quote_valid_until`; `SELF_PICKUP` validates a pickup location (`ERROR_NO_SELF_PICKUP`) and a `paymentOption`, clears the delivery columns. Both need `termsAccepted = true` (400 with the field error otherwise) and set `terms_accepted_at` and `terms_version` (`DELIVERY-1`, `PICKUP_PAY_NOW-1` or `PICKUP_PAY_AT_PICKUP-1`, the variant the buyer saw; wording in section 8). Returns the updated `CartLine`.
- [ ] `CartRepository`: update and clear the delivery columns; `CartItemRow` and `CartItemViewAssembler` carry them; `CartLine.Delivery` becomes `(mode, addressId, shippingCost, shippingEta, paymentOption, warning)`; `GET /cart` fills it.
- [ ] `CartController`: the two endpoints, OpenAPI text for every error, `@RequiresIdentityVerification` is not needed (the line already exists).
- [ ] `CartErrors`: `NO_DELIVERY_AVAILABLE`, `NO_SELF_PICKUP`, `SHIPPING_CHANGED`, `DELIVERY_NOT_CHOSEN` (constant only, used by US-021); reuse `ERROR_INVALID_ADDRESS` from `user`.
- [ ] Metrics: `cart.delivery.chosen{mode}`, `cart.delivery.refused{reason}`.

### Mobile (`valuex-mobile`, `features/cart` and `features/address`)
- [ ] `AddressRepository.create` (`POST /users/me/addresses`); `CartRepository.deliveryOptions` and `chooseDelivery`; `CartLine.delivery` model with mode, address id, cost, ETA, payment option and the cost warning.
- [ ] `DeliveryScreen` (route `/cart/items/:itemId/delivery`, `RouteNames.cartDelivery`, signed-in only): two option cards. **Delivery:** the default address preselected, a list of saved addresses to pick from, "Add a new address" (reuses `AddressSearchField` and `addressVerificationProvider`, with a name field Home, Office or custom, and "set as default"; saved through `AddressRepository.create`), the cost and the estimated date after an address is chosen, the "shipping costs more than the item" notice. **Self-pickup:** the pickup location (address text, no map yet), "Pay Now" and "Pay at Pickup" choice, and the banner "Pay at Pickup is not protected by escrow". An unavailable option is dimmed with its reason text. A terms checkbox per mode with the wording of section 8; Save is disabled until a mode, its required inputs and the checkbox are set.
- [ ] `CartLineCard`: replace "Choose at checkout" with the chosen summary ("Delivery to Home, ₹60, by 25 Nov" or "Self-pickup, Pay now") and a "Choose delivery" or "Change" button (min 48 dp) that opens the screen; the line text stays "Choose at checkout" only when nothing is chosen (the button is the entry point because the checkout screen is US-021).
- [ ] `cartProvider` re-reads after a save; the footer total stays the item total; "Proceed to checkout" stays disabled (US-021).
- [ ] l10n: every text in English and Hindi in `app_en.arb` and `app_hi.arb`, `flutter gen-l10n`; error texts from 0.5; semantic labels; 320 px width and 200 percent text.

### Docs (with the code)
- [ ] Sprint 5 LLD: "As built" B.6 with the deviations, change-log row, Part M note (the create-address endpoint now exists); fix B.2 (the address is created by a new endpoint, quote id handling).
- [ ] `Manual Testing Guides/US-020-Testing-Guide.md`; `Sprint-plan.md` and `user-stories.md` built notes; update the US-019 testing guide ("Choose at checkout").

## 5. Test Plan (target above 90% on new and changed code)

| Area | Tests |
|---|---|
| `StubShippingQuoteAdapter`, `DeliveryEligibilityPort` | flat rate and ETA follow the settings; goods eligible, whole vehicle and Real Estate not; settings ranges (`CheckoutSettingTest`). |
| `DeliveryOptionsService` (unit) | delivery only; pickup only; both; neither (both reasons, still 200); pickup from `pickup_address_id`, from the seller default, none; no address given returns eligibility only; another buyer's line `ERROR_CART_ITEM_NOT_FOUND`; expired or unavailable line; shipping above the price returns the warning. |
| `DeliveryChoiceService` (unit) | delivery happy path (address, cost, ETA, terms time and version stored, self-pickup columns cleared); self-pickup happy path (delivery columns cleared); changing mode overwrites; `termsAccepted` false; the stored `terms_version` follows the chosen mode and payment option; address of another user, incomplete address, missing pincode (`ERROR_INVALID_ADDRESS`); not eligible (`ERROR_NO_DELIVERY_AVAILABLE`); no pickup location (`ERROR_NO_SELF_PICKUP`); `expectedShippingCost` mismatch (`ERROR_SHIPPING_CHANGED`); missing `paymentOption`. |
| Address create (unit and controller) | first address becomes default; second does not; `makeDefault` swaps the default; label length; incomplete, unsupported state, pincode mismatch, provider down, rate limit; the response shape. |
| Controller | auth, validation, status codes and error mapping of the two cart endpoints; `GET /cart` carries the delivery block. |
| Integration (Testcontainers) | `V42` applies and the CHECKs reject a half-filled row; full flow add line, create address, choose delivery, read the cart; mode switch; parallel `PUT` on one line (last write wins, no mixed columns); seller deletes the pickup address reference (falls back); Real Estate and vehicle lines refuse delivery; the default-address swap under two parallel creates keeps exactly one default (unique index). |
| Mobile | repository calls; `DeliveryScreen` states (options loading, error and retry, only delivery, only pickup, none, saved addresses with the default preselected, new address with name and default, cost and date shown, cost warning, pay option, escrow banner, terms checkbox gating Save, save error texts); `CartLineCard` summary and button; route guard; English and Hindi; 320 px and 200 percent text; semantics and 48 dp targets. |
| Manual | `US-020-Testing-Guide.md` with the flag on: first address saved as default, name and change default, delivery with cost and date, pickup with both payment choices, no option available, shipping above price, terms, switch mode, a line whose price agreement ended. |

## 6. Validation Checklist

- [ ] AC1 to AC3 each mapped to a test; AC2's "saved as my default" and the name work through the new create endpoint.
- [ ] Each edge case has a test: no delivery, no self-pickup, address outside the serviceable area (stub: any pincode is serviceable, so tested through the port returning empty), shipping above price (warning), seller location (no distance rule, G6: tested that a far pickup is offered).
- [ ] Validation rules: at least one option; address complete with pincode; pickup address valid; cost calculated and stored before checkout; terms accepted.
- [ ] The three error codes with the exact story texts in English and Hindi; `ERROR_SHIPPING_CHANGED` text; reused codes keep their texts.
- [ ] No client price or shipping cost is trusted (only `expectedShippingCost`, compared and never stored).
- [ ] Pickup address shows only line 1, city and pincode; no phone before an order.
- [ ] A buyer cannot read or change another buyer's line or use another buyer's address.
- [ ] Hand-offs closed: the "Choose at checkout" text, LLD B and M notes, US-019 guide.
- [ ] Checkstyle, build, SonarQube clean; `dart format`, `dart analyze --fatal-infos` clean; coverage above 90% in both repos.

## 7. Open Gaps / Questions

| # | Gap | Proposal |
|---|---|---|
| G1 (Done 2026-11-21) | **US-019 was not merged**, and the Documents tree had uncommitted edits to the Sprint 5 LLD, `Sprint-plan.md` and `user-stories.md`. | US-019 is merged (backend #76, mobile #83, Documents #296 and #298) and the LLD edits are in `main` through #297. US-020 branches from updated `main`. |
| G2 (Confirmed 2026-11-21) | **No API saves an address**; the LLD assumes one. AC2 ("saved as my default", "give it a name") cannot work without it. | Add `POST /users/me/addresses` here (verify again server-side, save, first one is default, optional label, optional `makeDefault`). Edit, rename, delete and change default stay with US-113. **Confirm.** |
| G3 (Confirmed 2026-11-21) | **Sellers have no pickup address.** Nothing saves addresses (G2) and there is no seller UI to choose a pickup address on a listing, so `pickup_address_id` and the seller default would be empty for almost every listing and self-pickup would show `ERROR_NO_SELF_PICKUP` everywhere. | Fall back one more step: `pickup_address_id`, then the seller's default address, then the listing's own `seller_area`, `seller_location` (city) and `seller_state` text (no street, no pincode). A seller picker is a later story. **Confirm**, or tell me where the seller should choose the pickup address. |
| G4 (Confirmed 2026-11-21) | **AC3 says the buyer sees the seller's pickup address and contact**; LLD B.2 reveals the full address and phone only after the order. No seller phone is in `addresses`. | Keep the LLD rule: line 1, city and pincode now (or the city text from G3); full address and contact after the order (Part H). **Confirm.** |
| G5 (Confirmed 2026-11-21) | The LLD makes the app send a `quoteId` that the server must match within 10 minutes; no table stores quotes, and the stub is deterministic. | No `quoteId` from the app. `PUT` re-quotes on the server and stores the result; the app may send `expectedShippingCost` and gets `ERROR_SHIPPING_CHANGED` when it differs. The stored `shipping_quote_valid_until` lets US-021 re-quote when old. **Confirm.** |
| G6 (Wording drafted 2026-11-21, **for your review**) | **Terms:** "buyer must agree to terms for the selected option" but no terms text or version exists. | A checkbox per option with the English and Hindi wording of section 8; the line stores `terms_accepted_at` and `terms_version`; the versioned terms record is US-021. **Please review or edit the wording in section 8.** |
| G7 (Confirmed 2026-11-21) | **Where the buyer chooses.** Checkout is US-021 and its button is disabled. | A "Choose delivery" button on each cart line opens `DeliveryScreen`; US-021's checkout reuses the screen. **Confirm.** |
| G8 (Confirmed 2026-11-21) | **Pay at Pickup:** the seller switch and its rules are US-022 (G19, `pay_at_pickup_enabled`), so US-020 cannot refuse it per seller. | Store the buyer's choice; no seller check until US-022; show the "not protected by escrow" banner (LLD B.4). **Confirm.** |
| G9 (Confirmed 2026-11-21) | Does the cart total include shipping? | No: the footer stays the item total; shipping is shown on the line; US-021 builds the summary with shipping. **Confirm.** |
| G10 (Confirmed 2026-11-21) | The "address outside the serviceable area" edge case has no data until Shiprocket (US-122); the stub quotes every pincode. | The port returns empty for "not serviceable" and the code path and texts are built and tested; only the stub never triggers it. |
| G11 (Confirmed 2026-11-21) | G18 (`ERROR_ADDRESS_IN_USE` guard in `AddressService`): no delete endpoint exists. | Nothing to add now; the foreign key already blocks a delete in SQL; the guard comes with US-113. |
| G12 (Agreed 2026-11-21) | Hindi texts. | Drafted in the PR, reviewed by a native speaker later (as US-019). |
| G13 (Agreed 2026-11-21) | Self-pickup map widget (story note). | Address text only for now (LLD G7, B.4); no map package is added. MapmyIndia services will be used for the map and for address search soon, as a new adapter behind the existing address provider (`AddressProviderConfig`), so this story needs no change then. |

**Decisions (2026-11-21, user: "G1 to G5 and G7 to G11 confirmed, G12 and G13 agreed; G6 wording to be written for review"):** every proposal in the table stands as written. In short: G1 US-019 is merged and the work branches from `main`; G2 the create-address endpoint is part of this story; G3 pickup falls back from `pickup_address_id` to the seller's default address to the listing's own area, city and state text; G4 line 1, city and pincode before an order and the full address and contact after; G5 no `quoteId` from the app, the server re-quotes and `expectedShippingCost` is compared; G7 a "Choose delivery" button on each cart line; G8 Pay at Pickup is stored with no seller check until US-022; G9 the cart total stays the item total; G10 the not-serviceable path is built and tested but the stub never triggers it; G11 no address-in-use guard until US-113; G12 English and Hindi drafted in the PR; G13 address text now, MapmyIndia map and search later behind the address provider. **Only G6 (the terms wording) still needed your review; it was approved with the plan on 2026-11-21.**

## 8. Terms wording (G6, draft for your review)

The buyer must tick one checkbox before Save, and the text depends on what they chose. The checkbox label is "I agree to the terms above" (Hindi: "मैं ऊपर दी गई शर्तों से सहमत हूँ"). The line stores the time and the version below (`terms_accepted_at`, `terms_version`), so a later change of wording is traceable. The versioned terms record for the whole checkout is US-021. These are plain-language drafts, not legal text: please review them, and have them checked by whoever signs off the terms of service.

| Version | When shown | English | Hindi |
|---|---|---|---|
| `DELIVERY-1` | Delivery | I agree that this item will be delivered to the address I chose by JustQlic's delivery partner. The shipping cost and date shown are estimates and may change if the address is wrong or incomplete. My payment stays in escrow until I confirm that I received the item. | मैं सहमत हूँ कि यह वस्तु JustQlic के डिलीवरी पार्टनर द्वारा मेरे चुने हुए पते पर पहुँचाई जाएगी। दिखाया गया शिपिंग शुल्क और तारीख अनुमानित हैं और पता गलत या अधूरा होने पर बदल सकते हैं। वस्तु मिलने की पुष्टि करने तक मेरा भुगतान एस्क्रो में सुरक्षित रहेगा। |
| `PICKUP_PAY_NOW-1` | Self-pickup with Pay Now | I agree to collect this item myself from the seller's pickup location. My payment stays in escrow and is released to the seller only after I confirm that I received the item. | मैं सहमत हूँ कि मैं यह वस्तु विक्रेता के पिकअप स्थान से स्वयं लूँगा/लूँगी। मेरा भुगतान एस्क्रो में रहेगा और वस्तु मिलने की मेरी पुष्टि के बाद ही विक्रेता को जारी किया जाएगा। |
| `PICKUP_PAY_AT_PICKUP-1` | Self-pickup with Pay at Pickup | I agree to collect this item myself and to pay the seller directly at pickup. I understand that a payment made directly to the seller is not protected by escrow, and JustQlic cannot refund or recover it. | मैं सहमत हूँ कि मैं यह वस्तु स्वयं लूँगा/लूँगी और पिकअप के समय विक्रेता को सीधे भुगतान करूँगा/करूँगी। मैं समझता/समझती हूँ कि विक्रेता को सीधे किया गया भुगतान एस्क्रो से सुरक्षित नहीं है और JustQlic उसे वापस नहीं कर सकता और न ही वसूल कर सकता है। |

Points to check in the wording: it says the payment is held in escrow until the buyer confirms receipt (the Sprint 6 delivery confirmation, US-031, and the escrow design of Sprint 5 Part D); it does not mention a return or refund right for delivery orders (Sprint 7); it does not name a pickup time or hours (G6 of the LLD: none exist); and the "Pay at Pickup" text matches the banner "Pay at Pickup is not protected by escrow" of LLD B.4.

## 9. As built (2026-11-21)

The LLD table is Sprint 5 LLD B.6; this section lists only where the build differs from this plan.

- **Pickup column (step "map `pickup_address_id` on `Listing`"):** not mapped. `CartPickupAdapter` reads it by SQL, because nothing writes it yet and an unused entity field would be dead code.
- **Address errors (G2):** saving an address reuses the verify endpoint's codes (`ERROR_ADDRESS_INVALID`, `ERROR_INVALID_ADDRESS_STATE`, `ERROR_PINCODE_MISMATCH`, `ERROR_ADDRESS_NOT_VERIFIED`, `ERROR_ADDRESS_SERVICE_UNAVAILABLE`, `ERROR_ADDRESS_RATE_LIMIT`); the plan said `ERROR_INVALID_ADDRESS` 422, which is kept for the delivery endpoints (address missing, not the buyer's, or incomplete). The server verifies again on save, so one save makes two provider calls and counts twice against the rate limit.
- **Options endpoint:** always 200 with both options (`available` and `reason`); an item that cannot be bought answers 409 with its own code.
- **Cart total (G9):** unchanged; "Choose at checkout" shows only while nothing is chosen.
- **Address form:** US-108 had no form screen, so `AddressFormSheet` was built on its search field, state picker and verification status.
- **Delivery endpoints and the flag:** they do not read `valuex.checkout.enabled`; they work only on a line that exists, which needs the flag on.

**Results:** backend `mvn clean verify` 3,469 tests, 0 failures (7 skipped, libvips not installed), 0 Checkstyle violations; 21 new integration tests on PostgreSQL. Sonar: new-code coverage 94.3%, no issue in US-020 files; the gate reads ERROR only for 4 issues already in other stories' tests (S5853 `AgreementRealtimeListenerTest`; S5778 `PriceAgreementStatusServiceTest`, `CheckoutPriceGuardContractTest`, `PriceAgreementIntegrationTest`). Mobile: 2,293 tests pass; 2 `google_accessibility_test` tests fail as before this story; coverage `delivery_screen` 99%, `address_form_sheet`, `delivery`, `delivery_format`, `delivery_providers` 100%, `cart_line_card` 97%. `dart format` clean; `dart analyze` shows only the 10 Firebase environment errors that also appear on `main` locally.

**Status: Approved** (2026-11-21, user: "Approved"; the terms wording of section 8 is part of the approved plan). **Implemented** 2026-11-21, awaiting commit approval.
