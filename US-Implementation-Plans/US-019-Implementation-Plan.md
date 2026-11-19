# US-019: Add to Cart (Multi-Item) - Implementation Plan

## 1. Header

| Field | Value |
|---|---|
| Story | US-019 - Add to Cart (Multi-Item) |
| Sprint | Sprint 5 - Cart, Checkout & Payments |
| Story points | 5 |
| Repos involved | valuex-backend (`cart` module: tables, cart endpoints, expiry job, `cart` capability, `CheckoutSetting` registry with the two cart settings) and valuex-mobile (Cart screen, Add to Cart action, home cart badge, Buy Now hand-off). No `valuex-ai`, `valuex-web` or infra change. |
| Dependencies | US-018 (`CheckoutPriceGuard`, price status endpoints; built 2026-11-18), US-068 (`BUY_NOW` agreements, `valuex.checkout.enabled`; built 2026-11-18), US-012 (listing details; built). |
| Blocks | US-020 (delivery choice per cart line: its columns are created here), US-090/US-021 (order and payment created from the cart). |
| Date | 2026-11-19 (revised the same day against Sprint 5 LLD v0.1) |
| Design source | [Sprint 5 LLD](../LLD/Sprint-5-Cart-Checkout-Payments-LLD.md) v0.1: Part A (A.1 to A.7), section 0 (0.1 to 0.7, decisions D1 to D10), Part B (the delivery columns this story creates), Part N (N.2 NFR, N.3 tests, N.4 gaps G1, G4, G5, G7). Also: `user-stories.md` US-019; HLD 02 section 4.8, HLD 03 section 4.5; Sprint 4 LLD Part K (K.4, K.7) and Part M (M.11). The LLD is a **Draft**: decisions marked "Proposed" there are listed in section 7 and need your confirmation. |
| Branches (proposal) | `feature/US-019-add-to-cart` in `valuex-backend` and `valuex-mobile`; `docs/US-019-add-to-cart` in `Documents`, cut from updated `main`. |
| Flyway number | `V41__cart.sql` is the next free number **only if** backend PR #75 (US-131, `V40__device_tokens.sql`) is merged first; `main` today ends at `V39`. Re-check at branch time. |

## 2. Story Recap

**As a** buyer **I want to** add multiple items to my cart **so that** I can purchase them in one transaction.

> Update (2026-10-25, category taxonomy): Real Estate listings cannot be added to a cart. Delivery options depend on category eligibility and Shiprocket serviceability (US-122).

**Acceptance criteria:**

| ID | Criterion |
|---|---|
| AC1 | Given listing(s) with accepted prices, when I tap "Add to Cart", the item is added to my cart. |
| AC2 | In the cart I see all items with image, title, seller name, accepted price and delivery option selection. |
| AC3 | Items from several sellers are grouped by seller. |
| AC4 | On checkout I make one payment; the system creates one order per item, each with its own order number and escrow. |

**Edge cases:** item removed by the seller after adding; price changed after adding; mix of delivery and self-pickup items; cart abandoned for days; listing suspended while in the cart.

**Validation rules:** max 20 items; cart items expire after 24 hours; item must have an accepted price; stock check before checkout (sold item).

**Error codes:** `ERROR_ITEM_UNAVAILABLE` "This item is no longer available"; `ERROR_PRICE_CHANGED` "Price has changed. Please review"; `ERROR_MAX_CART_ITEMS` "Cart limit reached (20 items)"; `ERROR_CART_EXPIRED` "Cart items expired. Please add again".

**Flutter notes (story):** Cart grouped by seller with section headers; a subtle 24-hour countdown chip per item; cart kept locally and synced to the backend on open.

## 3. Design Reference and Key Decisions

LLD Part A (data A.2, API A.3, backend A.4, sequence A.5, mobile A.6, edge cases A.7) with section 0 decisions. What it means for this story:

- **A line rests on a price agreement (LLD D1, N.4 G1).** Add to Cart works only while the buyer holds an active agreement (`OFFER` accepted, or `BUY_NOW`). No agreement, no line; the app then shows "Make an offer or Buy Now" (new capability reason `NEGOTIATION_REQUIRED`).
- **Buy Now goes through the cart (D3).** The reservation of US-068 stays as built; the app then calls `POST /cart/items` for the same listing (the agreement exists, so it succeeds) and opens the Cart. Pre-selecting that line in checkout is US-021.
- **Ships dark, like Buy Now (D10 of Sprint 4, LLD 0.1).** `valuex.checkout.enabled` stays false until US-021 sets it. While false: `cart` capability is `COMING_SOON`, `POST /cart/items` answers 503 `ERROR_CHECKOUT_UNAVAILABLE` (the code Buy Now already uses), `GET /cart` and `GET /cart/summary` work (empty). Tests run with the flag on.
- **No client price, no stored status.** The cart never takes a price from the app. A line's price is the agreement price; its status (`ACCEPTED`, `PENDING`, `EXPIRED`, `UNAVAILABLE`) and `problem` code are computed on every read (A.3, A.4). A `BUY_NOW` line whose listing price changed shows `EXPIRED` with `ERROR_PRICE_CHANGED`; an `OFFER` price stands when the listing price changes (US-068 rule), so it stays `ACCEPTED`.
- **Endpoints (A.3):** `GET /cart`, `POST /cart/items` (201 first add, 200 when already in the cart), `DELETE /cart/items/{itemId}` (204, repeat 204), `GET /cart/summary` (`itemCount`, `validCount`). `POST /cart/checkout` is **not** here (US-021, AC4 only prepared).
- **Data (A.2):** `carts` (with `state`) and `cart_items` (with `seller_id`, `agreement_id`, `negotiated_price`, `expires_at`, and the US-020 columns `delivery_mode`, `delivery_address_id`, `shipping_quote_id`, `shipping_cost`, `payment_option`, all NULL until chosen), `UNIQUE (cart_id, listing_id)`. The HLD "Cart Locks" key is not used: exclusivity is the active agreement.
- **Expiry (A.4):** `CartItemExpiryJob` every 5 minutes deletes lines past `expires_at`, nothing else. A line whose agreement ended stays visible as `EXPIRED` until its own 24 hours pass, so the buyer can negotiate again.
- **Settings (0.4):** new `CheckoutSetting` registry, same pattern as `NegotiationSetting`; this story adds only `CART_MAX_ITEMS` (20, 1 to 50) and `CART_ITEM_TTL_HOURS` (24, 1 to 168). The other 0.4 keys come with their stories.
- **No new event (D9):** the app re-reads the cart on `agreement.updated`.
- **Money (D10):** `NUMERIC(12,2)`, `BigDecimal` scale 2, amounts as JSON strings.
- **Lock order (N.2):** listing advisory lock first (`PriceAgreementService.lockListing`), then the agreement row, as US-068.
- **Error codes (0.5):** new `ERROR_MAX_CART_ITEMS`, `ERROR_CART_EXPIRED`, `ERROR_CART_ITEM_NOT_FOUND`; reused as built: `ERROR_ITEM_UNAVAILABLE`, `ERROR_PRICE_CHANGED`, `ERROR_ITEM_RESERVED`, `ERROR_PRICE_NOT_ACCEPTED`, `ERROR_CHECKOUT_NOT_APPLICABLE` (Real Estate), `ERROR_UNAUTHORIZED_CHECKOUT` (own listing), `ERROR_CHECKOUT_UNAVAILABLE`.

### Verified implementation anchors (checked 2026-11-19 against `origin/main` of both repos)

| Area | Finding and consequence |
|---|---|
| `cart` package | Only `CartState`, `CartStateMachine` and `package-info.java` exist. The machine has `ADD_ITEM` (EMPTY to ITEM_ADDED, CART_ACTIVE to ITEM_ADDED), `ACTIVATE` (ITEM_ADDED to CART_ACTIVE), `REMOVE_ITEM`, `ITEM_STILL_IN_CART`, `ALL_ITEMS_REMOVED`. An add therefore runs `ADD_ITEM` then `ACTIVATE`; a remove runs `REMOVE_ITEM` then `ITEM_STILL_IN_CART` or `ALL_ITEMS_REMOVED`. See G7 for the expiry job. |
| Price agreement access | `PriceAgreementResolver` is package-private in `negotiation.application.service` (`resolve(buyerId, listingIds, now)` gives an outcome of NONE, ACCEPTED, RESERVED, PENDING or EXPIRED). The LLD puts the `CartAgreementPort` adapter in the negotiation module, so it can wrap the resolver without opening it. `PriceAgreementService` has public `lockListing`, `reservedForOther`, `reserving`, `findOwned`. |
| Listing facts | `ListingFactsPort.ListingFacts` (negotiation port) has `listingId, sellerId, title, price, negotiable, realEstate, live, buyNowEnabled, sold` but **no image and no seller name**. Cart needs both, so it gets its own `CartListingPort` (adapter in the listing module); the image comes from `media.port.ListingPhotoLinkPort` (`PhotoUrls.thumbnailUrl()`, as `ReceivedOffersService` does) and the seller name from `communication...ParticipantDirectoryPort.displayNames`. `ListingFactsPort` is not extended (it belongs to negotiation). |
| Capability | `ContactEligibilityService` returns `ContactOptions(chat, call, video, offer, buyNow, threadId, negotiationId, agreement)`; `PublicListingService.capabilities` sets `cart` statically: NOT_APPLICABLE or COMING_SOON. Adding a `cart` `Option` to `ContactOptions` changes its constructor, so the capability tests and every `new ContactOptions(...)` caller change. It reuses `OfferAvailabilityPort.availability` (agreement summary and `reservedForOther`). |
| Errors and flag | `NegotiationErrors` already has `ITEM_UNAVAILABLE`, `PRICE_CHANGED`, `ITEM_RESERVED`, `PRICE_NOT_ACCEPTED`, `UNAUTHORIZED_CHECKOUT`, `CHECKOUT_NOT_APPLICABLE`, `CHECKOUT_UNAVAILABLE`; the cart reuses those strings (shared constants, not a second copy). |
| Home badge | The backend home feed has no cart count; `ApiHomeRepository.badges()` returns `HomeBadges()` (zero) and the notification count comes from its own provider. The badge is therefore a mobile provider (`cartSummaryProvider`), and `HomeScreen.onCart` still calls `showComingSoon`. |
| Mobile hooks | `ListingActions` shows `capabilities.cart` with `onUnbuilt`; `SavedItemsScreen` has a disabled "Add to Cart" button (line about 290, `homeFeatureComingSoon` tooltip) that this story must wire (hand-off). `ReservationTimer` (US-068) exists in `core/widgets`. The negotiation screen comment says Add to Cart and Buy Now are not on yet (D10). |

## 4. Implementation Steps

### Database
- [ ] `V41__cart.sql` exactly as LLD A.2: `carts` (`buyer_id UNIQUE`, `state`), `cart_items` (`seller_id`, `agreement_id` to `price_agreements`, `negotiated_price` with `CHECK > 0`, the five US-020 columns left NULL, `added_at`, `expires_at`, `UNIQUE (cart_id, listing_id)`, `ON DELETE CASCADE` from the cart), indexes `idx_cart_items_expiry` and `idx_cart_items_agreement`; seeds `CART_MAX_ITEMS` 20 and `CART_ITEM_TTL_HOURS` 24 in `platform_settings` (`ON CONFLICT DO NOTHING`, same style as `V39`).

### Backend (`com.valuex.cart`, package layout as the negotiation module)
- [ ] `CheckoutSetting` registry (domain, like `NegotiationSetting`: default, min, max, `parse`) with the two keys, a `checkout()` accessor on `PlatformSettingsService` and its settings holder; unit test for defaults and ranges.
- [ ] `domain`: `CartErrors` (`ERROR_MAX_CART_ITEMS`, `ERROR_CART_EXPIRED`, `ERROR_CART_ITEM_NOT_FOUND`; the reused codes come from `NegotiationErrors`, not copied), `CartRow`, `CartItemRow`, `CartLineStatus` (`ACCEPTED`, `PENDING`, `EXPIRED`, `UNAVAILABLE`).
- [ ] `infrastructure/persistence`: `CartRepository` (JdbcTemplate, like `PriceAgreementRepository`): find or create the cart, count lines, insert (conflict on `(cart_id, listing_id)` returns the existing line), delete, delete expired in batches, lines of a cart.
- [ ] `application/port`: `CartAgreementPort` (`activeFor(buyerId, listingId)` and `statusFor(buyerId, listingIds)`; adapter `negotiation/.../CartAgreementAdapter` wrapping `PriceAgreementResolver` and `PriceAgreementService`, returning `{ agreementId, price, validUntil, source }` and the outcome), `CartListingPort` (title, current price, `sellerId`, `sellerName`, `imageUrl`, `live`, `sold`, `realEstate`, batch `findAll`; adapter in `listing`, photo through `ListingPhotoLinkPort`, name through `ParticipantDirectoryPort`).
- [ ] `application/service/CartService`: `add(buyerId, listingId)` in one transaction in this order: flag (`ERROR_CHECKOUT_UNAVAILABLE`), `PriceAgreementService.lockListing`, listing facts (`ERROR_ITEM_UNAVAILABLE` when not live or sold, `ERROR_CHECKOUT_NOT_APPLICABLE` for Real Estate, `ERROR_UNAUTHORIZED_CHECKOUT` for the buyer's own listing), agreement (`ERROR_ITEM_RESERVED` when another buyer holds it, `ERROR_PRICE_NOT_ACCEPTED` when the buyer has no active agreement (an ended one counts as none), already in cart (return the line, 200), count against `CART_MAX_ITEMS` (`ERROR_MAX_CART_ITEMS`), insert with `expires_at = now + CART_ITEM_TTL_HOURS`, `CartStateMachine` `ADD_ITEM` then `ACTIVATE`. `remove(buyerId, itemId)`: idempotent for a line already gone, `ERROR_CART_ITEM_NOT_FOUND` for another buyer's line, `REMOVE_ITEM` then `ITEM_STILL_IN_CART` or `ALL_ITEMS_REMOVED`. `view(buyerId)` and `summary(buyerId)` with at most one listing call and one agreement call for up to 20 lines.
- [ ] `CartItemViewAssembler`: pure function, no writes: status and `problem` per line from the listing facts and the agreement outcome as in LLD A.3 and A.4 (`ERROR_ITEM_UNAVAILABLE`, `ERROR_PRICE_CHANGED` with `currentPrice` for a `BUY_NOW` line whose listing price changed, `ERROR_CART_EXPIRED` past `expires_at`); groups ordered by the earliest `addedAt`, lines newest first.
- [ ] `api/CartController` (`/api/v1/cart`) and DTOs `CartResponse`, `CartGroup`, `CartLine` (`delivery` block with nulls until US-020), `CartSummary`, `AddToCartRequest(@NotNull listingId)`; 201 or 200 on add; OpenAPI text for each error.
- [ ] `CartItemExpiryJob`: every 5 minutes, ShedLock as `AgreementExpiryJob`, batches like the negotiation jobs, deletes lines past `expires_at`, applies the state-machine transition for a cart that becomes empty (G7); `CartMetrics`: `cart.added`, `cart.refused{reason}`, `cart.expired`.
- [ ] Capability: add a `cart` `Option` to `ContactCapabilityPort.ContactOptions`; `ContactEligibilityService.cart(...)` as LLD A.4 (own listing and unavailable are handled before; `IDENTITY_REQUIRED`, `RESERVED`, `COMING_SOON` while the flag is off, then `NEGOTIATION_REQUIRED` without an active agreement, else available; `DISABLED_BY_SELLER` is not used); `PublicListingService.capabilities` takes it from the contact options (Real Estate stays `NOT_APPLICABLE`); update the DTO comment and existing tests.
- [ ] Update `cart/package-info.java`.

### Mobile (`valuex-mobile`)
- [ ] `features/cart/{domain,data,presentation}`: `CartGroup`, `CartLine`, `CartLineStatus`, `CartRepository` (`get`, `add`, `remove`, `summary`; `add` reports created or existing), `cartProvider` (server is the source of truth; re-read on open, after each action and on `agreement.updated`; the last response is kept in memory only, N.4 G5), `cartSummaryProvider`.
- [ ] `CartScreen` (route `/cart`, `RouteNames.cart`): a section header per seller, line card (image, title, agreed price, status badge, 24-hour countdown chip with `ReservationTimer`, remove with an undo snackbar that adds the line again while its agreement still stands), the line text "Choose at checkout" for delivery, a footer with the total of the valid lines and "Proceed to checkout" disabled (US-021), empty state, error and retry, pull to refresh.
- [ ] Add to Cart: `ListingActions` calls the cart provider; `NEGOTIATION_REQUIRED` shows the hint "Make an offer or Buy Now first"; the refusal codes of the API use texts in `app_en.arb` and `app_hi.arb`; the page is re-read when what the buyer saw is stale (same helper as Buy Now).
- [ ] Buy Now hand-off (D3): after a successful reservation the app calls `add`, then opens the Cart; a refusal is shown and the reservation stays.
- [ ] Hand-offs: wire the disabled "Add to Cart" button of `SavedItemsScreen` to the same action; `HomeScreen.onCart` opens `/cart` and the header badge reads `cartSummaryProvider` (not the zero `HomeBadges.cartItems`); update the comment in the negotiation screen.
- [ ] l10n: every text in English and Hindi, regenerate with `flutter gen-l10n`; semantic labels for status badges and the countdown; 320 px width and 200 percent text.

### Docs (with the code)
- [ ] LLD Sprint 5: "As built" section for Part A with the deviations, change log row; fix A.4 if the build differs.
- [ ] `Manual Testing Guides/US-019-Testing-Guide.md`; `Sprint-plan.md` and `user-stories.md` built notes; Sprint 4 LLD K.7 and M.11 (cart hand-offs closed) and the "Coming soon" text in the US-018 and US-068 testing guides.

## 5. Test Plan (target above 90% on new and changed code)

| Area | Tests |
|---|---|
| `CartService` (unit) | add happy path (state `ADD_ITEM` then `ACTIVATE`, `expires_at` from the setting); idempotent re-add returns the same line; refusals in order: flag off, own listing, not live, sold, Real Estate, another buyer's agreement, no agreement, ended agreement; 21st line gives `ERROR_MAX_CART_ITEMS` and the limit follows the setting; remove idempotent; another buyer's line gives `ERROR_CART_ITEM_NOT_FOUND`; remove of the last line gives `ALL_ITEMS_REMOVED`; `summary` counts `validCount` without expired or unavailable lines. |
| `CartItemViewAssembler` (unit) | every status and `problem`: accepted, pending, ended agreement, sold, suspended or deleted listing, `BUY_NOW` price changed (`ERROR_PRICE_CHANGED` with `currentPrice`), `OFFER` price kept after a listing price change, past `expires_at` (`ERROR_CART_EXPIRED`); group and line ordering; amounts as scale 2 strings. |
| `CartItemExpiryJob` | deletes only lines past `expires_at`; keeps a line whose agreement ended; batches; two runs do no double work; cart state reset when it empties; metric. |
| Capability | `cart` reason order for each case (own listing, unavailable, identity, reserved, `COMING_SOON` with the flag off, `NEGOTIATION_REQUIRED`, available, Real Estate `NOT_APPLICABLE`); existing `ContactEligibilityService` and `PublicListingService` tests updated for the new field. |
| `CheckoutSetting` | defaults and ranges of both keys; migration seeds. |
| Controller | validation (`listingId` required), auth, 201 and 200 on add, 204 twice on remove, 503 with the flag off, error mapping of every code above, response shape. |
| Integration (Testcontainers) | `V41` applies; add race on the same listing from two buyers (the agreement holder wins, the other gets `ERROR_ITEM_RESERVED`); 20-line limit under parallel adds from one buyer; the same add twice in parallel gives one line; seller suspends or the listing sells (line `UNAVAILABLE`); price edit on a `BUY_NOW` line and on an `OFFER` line; multi-seller grouping; `GET /cart` with 20 lines uses two batched reads (query count). |
| Mobile | repository (all four calls, 201 versus 200), `cartProvider` and `cartSummaryProvider` (re-read on open, after actions and on `agreement.updated`), `CartScreen` (grouping by seller, status badges, countdown, remove and undo, empty, error and retry, disabled checkout button), `ListingActions` Add to Cart and the `NEGOTIATION_REQUIRED` hint, Buy Now hand-off (add then open the Cart; refusal keeps the reservation), saved items button, home badge and header route, refusal texts in English and Hindi, 320 px and 200 percent text, semantics. |
| Manual | `US-019-Testing-Guide.md` with the flag on: offer accepted, Add to Cart, two sellers, remove and undo, 24-hour expiry (set `CART_ITEM_TTL_HOURS` low), price change, seller suspends, Buy Now hand-off, flag off shows "Coming soon". |

## 6. Validation Checklist

- [ ] AC1 to AC3 each mapped to a test; AC4 is only prepared here (G2).
- [ ] Each edge case in section 2 has a test: item removed or suspended, price changed, mix of delivery and pickup (columns exist, no UI), abandoned cart (expiry job), listing suspended.
- [ ] Max 20, 24-hour expiry, accepted-price rule, sold check; both numbers are Admin-managed settings.
- [ ] The four story error codes with the exact texts in English and Hindi, plus `ERROR_CART_ITEM_NOT_FOUND`; reused codes keep their texts.
- [ ] Real Estate refused (category update); own listing refused.
- [ ] No client-sent price is trusted; no line is stored with a status.
- [ ] Flag off: capability `COMING_SOON`, add answers 503, reads work; flag on: everything works.
- [ ] Hand-offs closed: saved items button, home cart icon and badge, Buy Now hand-off, negotiation screen comment, Sprint 4 LLD K.7 and M.11.
- [ ] Checkstyle, build, SonarQube clean; `dart format`, `dart analyze --fatal-infos` clean; coverage above 90% in both repos.

## 7. Open Gaps / Questions

"LLD" ids point to Sprint 5 LLD 0.7 (D) and N.4 (G). Every item is a proposal that needs your answer; none is decided yet.

| # | Gap | Proposal |
|---|---|---|
| G1 | **A cart line needs an active price agreement** (LLD D1, N.4 G1), but an agreement lasts only until its own `valid_until` (an offer, or the 15-minute Buy Now reservation) while a line lasts 24 hours. | Add only while an agreement is active; the line stays up to 24 hours with status `EXPIRED` once the agreement ends, so the buyer can negotiate again; checkout extends the agreements (LLD D4, US-021). A Buy Now line therefore shows `EXPIRED` after 15 minutes unless checkout started. Alternative: Add to Cart at the asking price with no agreement (checkout then reserves like Buy Now). **Confirm.** |
| G2 | **AC4 (one payment, one order per item)** needs orders and payment (US-021, US-023). | This story ends at the cart and a disabled "Proceed to checkout"; `POST /cart/checkout` is not built (LLD 0.3, Part E). **Confirm.** |
| G3 | **Ships dark.** The LLD keeps `valuex.checkout.enabled` false until US-021, so the buyer cannot use the cart in a released build. | Capability `COMING_SOON`, `POST /cart/items` answers 503 `ERROR_CHECKOUT_UNAVAILABLE` (as Buy Now), reads work. Not stated in LLD Part A: **confirm** that the 503 on add is wanted, and that nothing in this story sets the flag true. |
| G4 | The story keeps the cart locally (`isar` or `drift`) (N.4 G5). Neither package is in the app. | Server is the source of truth; last response kept in memory only; no local database. **Confirm.** |
| G5 | **Delivery option selection in the cart** (AC2) is US-020's job (LLD B, G6). | Show "Choose at checkout" only; the US-020 columns are created here but unused. **Confirm.** |
| G6 | Live cart updates. | Reuse `agreement.updated`, no `cart.updated` (LLD D9). **Confirm.** |
| G7 | `carts.state` and `CartStateMachine`: the LLD stores the state but does not say who moves it when the expiry job empties a cart. | The service and the job apply `REMOVE_ITEM` then `ITEM_STILL_IN_CART` or `ALL_ITEMS_REMOVED` in the same transaction as the delete; checkout states stay for US-021. Alternative: drop the column and derive the state from the line count. **Confirm.** |
| G8 | `ListingFactsPort` has no image or seller name; LLD A.4 does not name a port for them. | A new `CartListingPort` (adapter in `listing`, photo via `ListingPhotoLinkPort`, name via `ParticipantDirectoryPort`) instead of widening negotiation's port. **Confirm.** |
| G9 | The story says an item in a cart should not hide the listing from others. | No: only an active agreement reserves an item (LLD A.7, US-068 rule). No decision needed unless you disagree. |
| G10 | Hindi texts (the four error texts, status badges, countdown, undo, the `NEGOTIATION_REQUIRED` hint) are not in the LLD. | Draft English and Hindi in the PR; Hindi is reviewed together later. |
| G11 | `V41` is right only after backend PR #75 (US-131, `V40`) is merged; LLD A.2 already assumes `V40` is taken. | Re-check the number at branch time. |
| G12 | The Sprint 5 LLD and this plan are **untracked** in `Documents` (not in any branch or PR). | Commit both with the first Documents PR of this story (`docs/US-019-add-to-cart`), after you approve; Sprint-plan and user-stories need only the built note. |

**Decided 2026-11-19 (user: "G1 - G12 - All confirmed and agreed"):** every proposal above stands as written: G1 a line rests on an active agreement and shows `EXPIRED` when it ends; G2 no checkout here; G3 ships dark with 503 on add while the flag is off and nothing here sets the flag; G4 no local database; G5 "Choose at checkout" only; G6 reuse `agreement.updated`; G7 the service and the job move `carts.state` in the same transaction as the line change; G8 new `CartListingPort`; G9 a cart line does not hide the listing; G10 English and Hindi drafted in the PR; G11 re-check `V41` after backend PR #75 merges; G12 the Sprint 5 LLD and this plan go in the first Documents PR of the story.

## 8. As built (2026-11-19)

All steps of section 4 are done in `valuex-backend`, `valuex-mobile` and `Documents`. Deviations from this plan and from the LLD are in Sprint 5 LLD **A.8** (rows 1 to 14). In short:

- `V41__cart.sql`; no ShedLock exists, so `CartItemExpiryJob` uses `@Scheduled` and `DELETE ... FOR UPDATE SKIP LOCKED` (safe on several instances).
- Seller names come from `ParticipantDirectoryPort` in `CartService`, not from `CartListingAdapter` (G8 said the adapter would).
- A fourth line problem, `ERROR_ACCEPTANCE_EXPIRED`, for a line whose agreement ended; `ERROR_MAX_CART_ITEMS` carries `details.limit`; `POST /cart/items` also needs Aadhaar verification.
- No `cartSummaryProvider`: the home badge reads `GET /cart/summary` through `ApiHomeRepository.badges()`. The line countdown uses `CountdownText`, not `ReservationTimer`.
- `CartAdder` is not auto-dispose: a first version was, and the Saved items screen (which only reads it) lost it during a request; a test now covers that.
- The "comment in the negotiation screen" hand-off needed no change (it names no cart text).
- Hand-offs closed: Saved items button, Home cart icon and badge, Buy Now hand-off, Sprint 4 LLD K.11 row 11 and M.11, the "Coming soon" text in the US-012, US-018, US-068 and US-073 testing guides.

**Results.** Backend: `mvn clean verify` 3,364 tests, 0 failures (the cart has 81 unit tests and 18 integration tests on real PostgreSQL, including parallel-add races); checkstyle clean; Sonar new-code coverage above 94 percent. Mobile: 2,184 tests pass (two known failures in `google_accessibility_test`, not from this story), the new cart files are covered at about 99 percent, `dart format` and `dart analyze --fatal-infos` are clean.

**Sonar.** No open issue in US-019 code. Old issues in other stories' files stay: S5853 in `AgreementRealtimeListenerTest`, S5778 in `PriceAgreementStatusServiceTest`, `CheckoutPriceGuardContractTest` and `PriceAgreementIntegrationTest`, and S2143 in `JwtTokenProvider`.

**Still open:** Hindi texts need native review; the l10n files of this story and mobile PR #82 (US-131) both change `app_en.arb`, `app_hi.arb` and the generated localization files, so the second to merge resolves a conflict; US-021 must turn `valuex.checkout.enabled` on.

**Status: Approved** (2026-11-19, user: "G1 - G12 - All confirmed and agreed"); **Implemented** 2026-11-19, pending pull requests.
