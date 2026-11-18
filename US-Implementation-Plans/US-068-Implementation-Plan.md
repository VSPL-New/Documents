# US-068: Direct Buy Now Flow - Implementation Plan

## 1. Header

| Field | Value |
|---|---|
| Story | US-068 - Direct Buy Now Flow |
| Sprint | Sprint 4 - Communication & Negotiation |
| Story points | 5 |
| Repos involved | valuex-backend (Buy Now endpoint and reservation, release endpoint, seller switch on the listing, price-change cancellation, capability reasons, search filter) and valuex-mobile (seller "Allow Buy Now" switch, Buy Now action and its errors, `ReservationTimer` widget). No `valuex-ai`, `valuex-web` or infra change. |
| Dependencies | US-012 (listing details, built), US-017 (price agreements, built), US-080 (the `AgreementExpiryJob` that ends reservations, built and merged 2026-11-18). US-018 (Part K) is not needed to build this story. |
| Date | 2026-11-18 |
| Design source | [Sprint 4 LLD](../LLD/Sprint-4-Communication-Negotiation-LLD.md) Part M (M.1 to M.10), D (capabilities), I.3 (`price_agreements`), J.5 and L.5 (agreement locking and expiry), decisions D9, D10, D11, D22, section 8.2 (error codes). |
| Branches (proposal) | `feature/US-068-direct-buy-now` in `valuex-backend` and `valuex-mobile`, cut from updated `main`, rebased before work starts (CLAUDE.md rule 5.1). |
| Flyway number | Next free number at branch time (V39 if nothing else lands first; the LLD's provisional V38 was taken by US-080). |

## 2. Story Recap

**As a** buyer **I want to** purchase an item immediately at the listed price **so that** I can skip negotiation for items I want to buy quickly.

> Update (2026-10-25, category taxonomy): not available for Real Estate listings (no purchase flow, US-118). Delivery follows category eligibility (US-122).

**Acceptance criteria (from `user-stories.md`):**

| ID | Criterion |
|---|---|
| AC1 | Given a listing with "Buy Now" enabled, when I tap "Buy Now", I skip the negotiation step. |
| AC2 | The item is added to the cart at the listed price and I proceed directly to checkout. |
| AC3 | When the seller has disabled "Buy Now", only "Make Offer" is available and I must negotiate. |

**Edge cases (story):** item sold to another buyer while the current buyer is checking out; seller changes the price during checkout; buyer wants to negotiate after using Buy Now; multiple buyers click Buy Now at once.
**Validation rules (story):** the Buy Now price is the listed price; the seller can enable or disable Buy Now per listing; Buy Now items follow the same escrow flow; the item is reserved for 15 minutes during checkout.
**Error scenarios (story):** `ERROR_ITEM_SOLD` ("This item is no longer available"), `ERROR_PRICE_CHANGED` ("Price has changed. Please review"), `ERROR_BUY_NOW_DISABLED` ("Seller requires price negotiation for this item").
**Flutter notes (story):** the listing page shows "Buy Now" and "Make Offer" as two distinct buttons; a 15-minute reservation countdown in the checkout header; a "Buy Now" switch in the seller's listing create and edit settings.

**Interpretation of AC2 (LLD M.1, M.2, decision D10):** the cart and checkout are Sprint 5 (US-019 to US-021). In this story Buy Now creates the 15-minute **reservation at the asking price** and hands over to checkout. Until checkout exists the `buyNow` capability stays `COMING_SOON` and the endpoint answers `ERROR_CHECKOUT_UNAVAILABLE` while `valuex.checkout.enabled` is false (see G2).

**What is already built (checked in the code on `main`, 2026-11-18):** `price_agreements` with `source IN ('OFFER','BUY_NOW')` and the one-active-per-listing unique index (V36); `PriceAgreementService` (lock, lazy clean-up of lapsed agreements, `reservedForOther`, cancel); `OfferEligibilityService` already refuses an offer while another buyer holds an agreement (`ERROR_ITEM_RESERVED`); `AgreementExpiryJob` (US-080) ends due agreements of any source, `BUY_NOW` ones silently; `ContactChannel.BUY_NOW` and `ContactGuard`; `capabilities.buyNow` and `capabilities.cart` in the public listing response, both `COMING_SOON` for goods and `NOT_APPLICABLE` for Real Estate; mobile `ListingActions` already renders the capability objects. **Not built:** the `buy_now_enabled` column, the endpoint, the release endpoint, the switch on the listing form, the price-change cancellation, search hiding of reserved listings, `ReservationTimer`, `valuex.checkout.enabled`. **Built by US-018 (merged, checked on `main`):** `AgreementUpdatedEvent` (CREATED, CANCELLED, CONSUMED; `negotiationId` may be null), `AgreementRealtimeListener` with `agreement.updated` to the buyer, `ClosedReason.PRICE_CHANGED`, `PriceAgreementResolver` (a `BUY_NOW` row already resolves to ACCEPTED for its buyer and RESERVED for others), `CheckoutPriceGuard` (maps an `ended_reason` of PRICE_CHANGED to `ERROR_PRICE_CHANGED`), the price status endpoints in `PriceAgreementController`, and the price agreement summary (with `source`) inside `ContactCapabilityPort.ContactOptions`. Still missing for Buy Now: `PriceAgreementRepository.insert` writes `'OFFER'` only; `PublicListingService.capabilities` still sets `buyNow` and `cart` to the constant `COMING_SOON`.

## 3. Design Reference

LLD Part M, with these points that matter for the build:

- **Reservation = a `price_agreements` row** with `source = 'BUY_NOW'`, `agreed_price` = the asking price at that moment, `valid_until = now + BUY_NOW_RESERVATION_MINUTES` (15). Exclusivity comes from `PriceAgreementService.lockListing` (advisory lock) plus the unique index. Expiry is done by `AgreementExpiryJob`; the lazy clean-up under the lock means a late job never blocks a buyer.
- **`BuyNowService.start` order of checks:** `ContactGuard.require(BUY_NOW)`; checkout flag; listing live (`ERROR_ITEM_SOLD` if sold, else `ERROR_LISTING_NOT_AVAILABLE`); not Real Estate; `buy_now_enabled`; price present; `expectedPrice` equals the current price (`ERROR_PRICE_CHANGED`); rate limit; then the listing lock, clean-up, and one of: same buyer's reservation returned (200), another buyer's gives `ERROR_ITEM_RESERVED`, otherwise insert (201), cancel the buyer's own open negotiation (`REPLACED_BY_BUY_NOW`), publish `agreement.updated`. The caller must be Aadhaar verified (decision D9).
- **Release:** `DELETE /price-agreements/{id}` by its buyer sets `CANCELLED`; for an `OFFER` agreement it also cancels the negotiation. Idempotent.
- **Price change cancels reservations synchronously:** `ListingEditedEvent` (published inside the edit transaction by `DomainEventPublisher`, a plain Spring event) gets a `BEFORE_COMMIT` listener in the negotiation module that, when `price` is among the changed fields, calls `PriceAgreementService.cancelBuyNowForPriceChange(listingId)` under the listing lock. Only `BUY_NOW` agreements are cancelled (`ended_reason = PRICE_CHANGED`); a negotiated `OFFER` price stands. The buyer is told in-app after commit.
- **Seller switch:** `buyNowEnabled` in the listing edit request; for goods, `negotiable` or `buyNowEnabled` must be true (`ERROR_NO_PURCHASE_OPTION`, D11); turning it off does not cancel an existing reservation.
- **Capabilities:** `buyNow` and `cart` `NOT_APPLICABLE` for Real Estate; `buyNow` `DISABLED_BY_SELLER`, `RESERVED` (another buyer holds an active agreement), `IDENTITY_REQUIRED`, `COMING_SOON` while the checkout flag is off, otherwise available; `cart` is not affected by the seller's switch.
- **Search (D22):** new `ListingIndexSourcePort.retainBrowsable(ids)` and `ListingEligibilityFilter.retainBrowsable`, used only by `ListingSearchService`; `retainLive` is unchanged for reconciliation, saved listings and saved-search alerts. Reserved listings stay in the index and keep their details page; they only drop out of result pages with the existing drop-and-keep-total behaviour. No index mapping change.

## 4. Implementation Steps

### Database
- [ ] `V39__buy_now.sql` (number at branch time): `ALTER TABLE listings ADD COLUMN buy_now_enabled BOOLEAN NOT NULL DEFAULT TRUE`; seed `BUY_NOW_RESERVATION_MINUTES` 15 and `BUY_NOW_PER_HOUR` 10 (`ON CONFLICT (setting_key) DO NOTHING`). Existing listings get `TRUE`.

### Backend - listing module (`com.valuex.listing`)
- [ ] `Listing.buyNowEnabled` (Boolean, default true); `UpdateListingDetailsRequest.buyNowEnabled`; `ListingDetailsService` applies it and enforces for goods `negotiable` or `buyNowEnabled` (`ERROR_NO_PURCHASE_OPTION`, 422) where the category shows the common fields; the field is not a re-moderation trigger (a minor field in `ListingEditService` history, G6).
- [ ] `ListingDraftResponse` and My Listings response gain `buyNowEnabled` (owner only); the public response keeps `capabilities.buyNow`, now computed from the facts below instead of the constant `COMING_SOON` in `PublicListingService.capabilities`.
- [ ] `ListingFactsPort.ListingFacts` (and its adapter) gain `buyNowEnabled` and the listing state needed to tell sold from not available (G4); the preview assembler shows the switch.
- [ ] Search: `ListingIndexSourcePort.retainBrowsable(ids)` in `ListingIndexSourceAdapter` (live and no `ACTIVE` agreement with `valid_until > now()`, one indexed `NOT EXISTS`); `ListingEligibilityFilter.retainBrowsable`; `ListingSearchService` switches to it; reconciliation, saved listings and alerts keep `retainLive`.

### Backend - negotiation module (`com.valuex.negotiation`)
- [ ] `NegotiationSetting`: add `BUY_NOW_RESERVATION_MINUTES` (default 15, range 1 to 60) and `BUY_NOW_PER_HOUR` (10, 1 to 60) (the LLD names only the second range; G5).
- [ ] `valuex.checkout.enabled` (default false) in `ValuexProperties` and `application.yml` (G2); the test profile or tests turn it on where needed.
- [ ] `BuyNowService` (`start`, `release`) as in Part M; `BuyNowController`: `POST /api/v1/listings/{listingId}/buy-now` (`{expectedPrice, clientRequestId}`, 201 or 200, `@RequiresIdentityVerification`) and `DELETE /api/v1/price-agreements/{agreementId}` (204, idempotent); response `{agreementId, source, agreedPrice, validUntil, serverTime}`; DTOs and OpenAPI annotations.
- [ ] `PriceAgreementService`: `insertBuyNow`, `cancelBuyNowForPriceChange(listingId)`, `release(agreementId, buyerId)`; `PriceAgreementRepository`: `insert` gets a `source` argument (today it writes `'OFFER'`; the existing caller passes `OFFER`), find by id with ownership, cancel by listing and source with a reason. The existing `createFromOffer` keeps working and refuses (`ERROR_ALREADY_ACCEPTED`) while a Buy Now reservation of another buyer is active (G7).
- [ ] `BuyNowPriceChangeListener` (`BEFORE_COMMIT` on `ListingEditedEvent`, only when `price` changed) and a post-commit notification to the buyer (G3).
- [ ] `OfferEligibilityService` or a new `BuyNowCapabilityService`: the reasons listed in section 3, wired into `PublicListingService` through the existing contact capability port; `ContactGuard` `BUY_NOW` channel and the hourly limit (G5).
- [ ] Realtime: reuse US-018's `AgreementUpdatedEvent` and `AgreementRealtimeListener` (no new event): Buy Now publishes CREATED on start and CANCELLED on release or price change; the listener already handles a null `negotiationId`. Add the in-app notification for the price-change cancellation (G3).
- [ ] Metrics: `buynow.started`, `buynow.refused{reason}`, `buynow.released`, `buynow.price_changed`.

### Mobile (`valuex-mobile`, `features/listing`, `features/listing_view`, `features/negotiation` or a new `features/buy_now`)
- [ ] Seller switch: **Allow Buy Now** (default on, helper text, validation message when it and "Price negotiable" are both off) in the price section of `item_details_screen.dart`, in the draft, live-edit and preview models (`listing_details.dart`, `existing_listing.dart`, `listing_preview.dart`), the error mapping (`ERROR_NO_PURCHASE_OPTION`), and ARB strings in English and Hindi.
- [ ] Buyer action: `ListingActions` Buy Now with the new reasons (`DISABLED_BY_SELLER`, `RESERVED` captions); `BuyNowRepository` (`POST /buy-now`, `DELETE /price-agreements/{id}`), a controller that sends the displayed price, maps `ERROR_PRICE_CHANGED` (refresh and ask the buyer to review the new price), `ERROR_ITEM_SOLD`, `ERROR_ITEM_RESERVED`, `ERROR_BUY_NOW_DISABLED`, rate limit and verification errors; on success it goes to the Sprint 5 checkout route, which does not exist yet (G2), so with the capability `COMING_SOON` the button stays disabled as today.
- [ ] `ReservationTimer` shared widget in `core/widgets/` (countdown from `validUntil` and `serverTime`, announced at intervals, warning colour in the last minute) with widget tests.
- [ ] Notification text for the price-change cancellation (English and Hindi) in `notification_text.dart`.

## 5. Test Plan (target above 90% on new and changed code)

**Unit (backend):** each refusal of `BuyNowService.start` in its order; idempotent repeat by the same buyer (200); another buyer's reservation (`ERROR_ITEM_RESERVED`); an existing lower `OFFER` agreement returned; own open negotiation replaced (`REPLACED_BY_BUY_NOW`); `expectedPrice` mismatch; Real Estate; sold versus unavailable; checkout flag off; hourly limit; release (own, someone else's, repeated); `cancelBuyNowForPriceChange` cancels only `BUY_NOW` rows; purchase-option rule in the details service (goods, Real Estate where `negotiable` is hidden); capability reasons; `retainBrowsable` versus `retainLive`.
**Controller:** statuses and envelopes, 201 versus 200, 204, Aadhaar gate, checkout-disabled 503.
**Integration (PostgreSQL):** two buyers racing (exactly one agreement); expiry job frees the listing and search shows it again; a reserved listing is hidden from search results but still opens in details; reconciliation, saved listings and alerts still see it (`retainLive`); a listing edit with a new price cancels the reservation in the same transaction and a rolled-back edit does not; the seller switch round trip through draft, live edit and My Listings; an offer from another buyer is refused while the reservation holds and allowed after release; Buy Now replaces the buyer's open negotiation.
**Mobile:** switch and validation, preview, button and caption per capability reason, error mapping, double tap, `ReservationTimer` (fake async, last-minute colour, Hindi, 200 percent text, 320 px width), notification text.
Maps to: AC1/AC2 (start, reservation, hand-over), AC3 (switch, capability), edge cases (race, sold, price change, negotiate after Buy Now).

## 6. Validation Checklist

- [ ] AC1: Buy Now creates a 15-minute reservation at the current asking price and no negotiation step is needed.
- [ ] AC2: the reservation is what Sprint 5 checkout consumes (`CheckoutPriceGuard` of Part K); the cart step is Sprint 5 (G1).
- [ ] AC3: with the switch off only Make Offer is offered; the endpoint answers `ERROR_BUY_NOW_DISABLED`.
- [ ] Edge cases: simultaneous Buy Now (one wins); item sold or gone; price changed during the reservation; negotiating after Buy Now (release, then offer); open offer replaced.
- [ ] Validation rules: price is the server's asking price (never the client's); per-listing switch; same escrow flow later; 15-minute reservation and expiry; Real Estate refused.
- [ ] Error scenarios: `ERROR_ITEM_SOLD`, `ERROR_ITEM_RESERVED`, `ERROR_PRICE_CHANGED`, `ERROR_BUY_NOW_DISABLED`, `ERROR_BUY_NOW_NOT_APPLICABLE`, `ERROR_CHECKOUT_UNAVAILABLE`, `ERROR_NO_PURCHASE_OPTION`, 403 verification, 429.
- [ ] Reserved listings hidden from search only; `retainLive` consumers unchanged.
- [ ] Release is idempotent and only by the buyer; no state needs an Admin to free the item.
- [ ] Coverage above 90 percent, checkstyle, `dart format` and `dart analyze`, SonarQube gate, LLD Part M and I.11 reconciled (M.11 as-built), testing guide `US-068-Testing-Guide.md`, user-stories and Sprint-plan updated.

## 7. Open Gaps / Questions

| # | Gap | Proposed answer |
|---|---|---|
| G1 (confirmed) | The story says "added to cart and proceed to checkout"; cart and checkout are Sprint 5. | Follow LLD M.1 and M.2: this story creates the reservation and the contract; the cart and checkout screens come with US-019 to US-021. Confirm. |
| G2 (confirmed) | `valuex.checkout.enabled` does not exist yet, and the mobile checkout route is Sprint 5. With the flag off (decision D10) the capability is `COMING_SOON` and the endpoint answers 503, so users cannot use Buy Now until Sprint 5. | Add the flag (default false). Everything is built and tested now (with the flag on in tests and through fakes in the app); the seller switch, the `DISABLED_BY_SELLER` and `RESERVED` reasons and the search hiding work immediately. Confirm that shipping it dark is intended. |
| G3 (confirmed) | The LLD says the buyer is told in-app after a price-change cancellation but names no notification type or text. | New in-app notification `BUY_NOW_PRICE_CHANGED` ("Price changed for {item}. Please review the new price"), dedupe `agr:{id}:PRICE_CHANGED`, deep link to the listing; Hindi text for native review. Confirm name and wording. |
| G4 (decided) | `ListingFacts` has `live` but not the listing state, and the LLD asks `ERROR_ITEM_SOLD` for a sold listing and `ERROR_LISTING_NOT_AVAILABLE` otherwise. | Add the state to `ListingFacts`. Existing `ListingState` values: DRAFT, PLAN_SELECTION_PENDING, PLAN_PAYMENT_PENDING, PLAN_PAYMENT_FAILED, PLAN_PAYMENT_SUCCESS, MEDIA_UPLOAD_PENDING, AI_DETAILS_GENERATED, PRICE_PENDING, TRUST_SAFETY_REVIEW, APPROVED, **PUBLISHED** (the only live one), BUYER_INQUIRY_PENDING, NEGOTIATION_IN_PROGRESS, OFFER_ACCEPTED, ORDER_CREATED, **SOLD**, EXPIRED, DEACTIVATED_BY_SELLER, REMOVED_BY_ADMIN, REJECTED, REVISION_REQUIRED. Decided: only `SOLD` gives `ERROR_ITEM_SOLD`; every other non-live state (including `ORDER_CREATED`) gives `ERROR_LISTING_NOT_AVAILABLE`. |
| G5 (confirmed) | The LLD uses both `ContactGuard.require(BUY_NOW)` (logged contact attempts with their own limits) and `BUY_NOW_PER_HOUR` (10 per buyer); only one range (1 to 60) is given, for the per-hour key. | Keep both: the guard for blocks and own listing, the setting for the hourly cap through the existing rate limiter (as `OFFERS_PER_MIN`); `BUY_NOW_RESERVATION_MINUTES` range 1 to 60. Confirm. |
| G6 (confirmed) | Whether `buyNowEnabled` appears for every category (the form shows `negotiable` only where the category's common fields do). | Show and store it for goods only; Real Estate ignores it (never Buy Now). Confirm. |
| G7 (confirmed) | A seller accepting an offer while another buyer holds a Buy Now reservation gets `ERROR_ALREADY_ACCEPTED` ("A price for this item has already been accepted"), which is wrong for a reservation. | Keep the code, make the text neutral ("This item is reserved for another buyer right now"). Small change in `PriceAgreementService.createFromOffer`; confirm. |
| G8 | RESOLVED: US-018 built `agreement.updated` (`AgreementUpdatedEvent`, `AgreementRealtimeListener`, `ClosedReason.PRICE_CHANGED`). | Reuse it; no new event. Buy Now publishes CREATED and CANCELLED through it. Expiry of an agreement publishes nothing in US-018 and stays so. |
| G9 (agreed) | The LLD's Flyway number (V38) collides with US-080's V38. Agreed. | Latest on `main` is V38 (checked after US-018 merged); use V39, or the next free number at branch time, and update M.3 in the as-built note. |
| G10 (confirmed) | Quantity above 1: the MVP reserves the whole listing for one buyer (decision O14). | No stock handling here; Sprint 5. |


## 8. Implementation notes (deviations from the plan above)

Built 2026-11-18 on branch `feature/US-068-direct-buy-now` in `valuex-backend` and `valuex-mobile`. The LLD is reconciled in Part M.11; the manual testing guide is `Manual Testing Guides/US-068-Testing-Guide.md`.

| # | Plan | Built | Why |
|---|---|---|---|
| D1 | `BUY_NOW_RESERVATION_MINUTES` range 1 to 60 (G5). | Range **5 to 60** as in the LLD settings table (section 1.6); `BUY_NOW_PER_HOUR` 1 to 60. | The plan misread the LLD, which does give the range. |
| D2 | Checks first, then the listing lock. | The listing lock comes first (right after the checkout flag), then every check, then the reservation. | The price edit takes the same lock before it commits, so a price change cannot slip between the price check and the insert. |
| D3 | `ERROR_ITEM_SOLD` after `ContactGuard`. | The sold check comes before the guard. | The guard answers any not-live listing with `ERROR_LISTING_NOT_AVAILABLE`, so a sold item could not be told apart. Only `SOLD` gives `ERROR_ITEM_SOLD` (G4). |
| D4 | The price-change cancellation publishes `CANCELLED`. | It publishes the new `AgreementUpdatedEvent.Kind.PRICE_CHANGED`. | The notification listener needs to tell it from a release; the realtime event still says status `NONE`. |
| D5 | Error texts of the LLD. | The three texts of the user story, word for word, on the server and in the app (English and Hindi). | The story names them. |
| D6 | "Own open offer cancelled". | Withdrawn like the buyer's own withdrawal: card in the thread, "Offer withdrawn" to the seller. `ClosedReason.RELEASED_BY_BUYER` added for a release. | The seller must not keep a card that waits for an answer. |
| D7 | `ListingFacts` gets the state. | It gets two booleans, `sold` and `buyNowEnabled`. | Smaller than passing the state. |
| D8 | A successful tap goes to checkout. | The app shows "Reserved for you. Checkout is coming soon" and reads the page again. `ReservationTimer` is built and tested but is on no screen until the Sprint 5 checkout. | The route does not exist (G1, G2). |
| D9 | Not planned. | The notification deep link `/listings/{id}` opens the listing in the app; the preview says "Buy Now on". | G3 asks for a deep link to the listing; the preview shows the switch. |

**Follow-ups:** Hindi texts need native review; Sprint 5 adds the cart, the checkout header with the timer, `requireValid` and `markConsumed` with a Buy Now agreement, and quantity above 1. Sonar reported five issues that are not in this story's files (four in US-018 tests, one `S2143` in `JwtTokenProvider`); they are listed in the pull request.

**Status: Approved (implemented)**
