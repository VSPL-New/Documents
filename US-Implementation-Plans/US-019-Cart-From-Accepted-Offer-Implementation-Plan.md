# US-019 Follow-up: Add to Cart from an Accepted Offer - Implementation Plan

## 1. Header

| | |
|---|---|
| Change | Move "Add to Cart" off the listing page into the accepted-offer card (chat) and the negotiation screen; Saved items gets "View details"; the seller sees a card and a notification when an accepted item goes into the cart |
| Belongs to | US-019 (cart), with edits to US-012 (listing page), US-017 (negotiation), US-013 (chat cards), US-018 (Saved items) |
| Sprint | 5 (Cart, Checkout, Payments); Sprint 4 chat and negotiation surfaces |
| Estimate | About 5 SP (backend 2, mobile 3). To be confirmed by the product owner. |
| Repos | `valuex-backend`, `valuex-mobile`, `Documents` |
| Dependency | US-019, US-017, US-013 (all built and merged) |
| Requested by | Product owner, 2026-11-24 (decisions below) |

## 2. Story Recap

**Why.** "Add to Cart" works only when the buyer holds an agreed price (an accepted offer, or a Buy Now hold, which already adds to the cart itself). On the listing page the button therefore only explains "make an offer or use Buy Now first" for most buyers, which confuses them. The accepted price already lives in the negotiation and in the chat, so the action belongs there.

**Decisions (product owner, 2026-11-24)**

1. Remove "Add to Cart" from the listing details page for all cases. Move the action into the offer-accepted card in the chat and into the negotiation screen.
2. When an accepted item is added to the cart, the **seller sees a neutral card in the chat** and gets an **in-app notification**; no push.
3. The card is neutral: it states what happened and until when the price is held; it does not say the buyer will pay.
4. Saved items: the "Add to Cart" button becomes **"View details"**, which opens the listing page (as a tap on the card already does). No capability data, no offer or Buy Now buttons on Saved items.

**Acceptance criteria**

- AC1. The listing page shows Chat, Call, Video, Make an Offer or View offer, and Buy Now. It never shows Add to Cart, and no "make an offer first" hint.
- AC2. A buyer whose offer was accepted sees "Add to cart" on the accepted-offer card of that chat and on the negotiation screen. The seller never sees it.
- AC3. Tapping it adds the item at the agreed price (existing `POST /cart/items`) and shows "Added to your cart" with a View cart action. If the price ended, the item is gone, the cart is full or the cart is off, the existing error text is shown instead.
- AC4. Only the newest accepted-offer card of a thread offers the button; an older card does not.
- AC5. When an accepted item is newly added to the cart, the seller gets one chat card ("<buyer> added this to the cart at <price>, held until <time>") and one in-app notification. Adding the same item again under the same agreement creates nothing new. Removing it or letting it expire creates nothing.
- AC6. If the buyer has no conversation yet for the listing (a Buy Now hold, for example), the server opens it, as it does for offers and calls, and posts the card there. If the thread is read-only (blocked, listing removed) the card and notification are skipped and the add still succeeds.
- AC7. Saved items shows "View details" instead of "Add to Cart" on an available item; it opens the listing page. Unavailable items are unchanged.
- AC8. The seller's card has its own look in the app, and an unknown card kind still falls back to the neutral "Conversation update" line (the existing behaviour for any unknown kind).
- AC9. The cart stays behind `valuex.checkout.enabled`: with it off, the new button is hidden (the cart is not available) and no card or notification is created.

**Not in this change:** a push to the seller, a seller action on the card, removing the capability from the API, changes to Buy Now, checkout or the cart screen.

## 3. Design Reference

- Sprint 5 LLD Part A (cart): A.3 rules and errors, A.4 API, A.8 as built. `CartService.add` returns `AddToCartResult(line, created)`; `created` is true only for a new line.
- Sprint 4 LLD Part M (Buy Now and agreements), Part B/chat cards: `NegotiationChatPort.postOfferCard` writes `OFFER_EVENT` cards through `ChatMessageStore.postSystemMessage`.
- Sprint 3 LLD Part C (listing page capabilities).

**Key design points**

- **No API removal (kept for simplicity).** `POST /cart/items`, the listing `capabilities.cart` and the cart screen are unchanged; only the app stops showing the button on the listing page. There is no installed older build to protect (development phase), so this is not a compatibility measure: removing the unused `capabilities.cart` field is a possible later clean-up and is out of scope here.
- **New card kind, existing card type.** The seller's card is an `OFFER_EVENT` with `kind` = `ADDED_TO_CART` and payload `{kind, listingId, amount, validUntil, by:"BUYER", negotiationId?}`. This needs no new message type and no migration.
- **Event after commit.** `CartService.add` publishes `CartItemAddedEvent` (ids, price, expiry) only when a line was created. A cart-side `@TransactionalEventListener(AFTER_COMMIT)` with `REQUIRES_NEW` calls a new port `CartChatPort`, implemented in the communication module (mirrors `NegotiationChatPort`). A failure is logged and never reaches the buyer.
- **One per agreement.** The listener claims `cart:added:{agreementId}` with a set-if-absent in Redis (48 hours). The notification also carries `dedupeKey = "cart-added:" + agreementId`. A Redis outage can at worst post a second card, which is harmless; it never blocks the add.
- **Live state at tap time.** A chat card is history. The button is shown on the newest accepted card only (AC4) and the server decides on tap, so an ended price answers with the existing error and the card does not need to poll.
- **Neutral text and privacy.** Ids, the listing title, the buyer's display name and the price, which the seller already knows from the offer. No cart contents beyond this item.

## 4. Implementation Steps

Create branches from `main`: `feature/US-019-cart-from-accepted-offer` in `valuex-backend` and `valuex-mobile`, and `docs/US-019-cart-from-accepted-offer` in `Documents`.

### Backend (`com.valuex.cart`, `com.valuex.communication`)

- [ ] `cart/domain/CartItemAddedEvent` (buyerId, sellerId, listingId, agreementId, price, expiresAt, listingTitle).
- [ ] `CartService.add`: publish the event only when the line was created and checkout is on.
- [ ] `cart/application/port/CartChatPort` with `postAddedToCart(...)`; `communication/application/service/CartChatAdapter` implements it: find or create the buyer's thread (`NegotiationChatAdapter.ensureThread`), skip when read-only, post the `OFFER_EVENT` card (`kind` `ADDED_TO_CART`, notify the seller).
- [ ] `cart/application/service/CartAddedListener` (`AFTER_COMMIT`, `REQUIRES_NEW`): Redis claim per agreement, call the port, dispatch an in-app notification to the seller (`CART_ITEM_ADDED`, IN_APP only, dedupe key per agreement, no push), swallow and log failures.
- [ ] Notification copy for `CART_ITEM_ADDED` ("<buyer> added <item> to the cart"), with a deep link to the chat thread. Add the type to the push policy as "never push".
- [ ] Metric `cart.seller_notified{outcome}`; no user content in logs.
- [ ] Settings: none. No migration.

### Mobile (`valuex-mobile`)

- [ ] `listing_actions.dart` and `listing_view_screen.dart`: remove the Add to Cart action, `onAddToCart`, `addToCartBusy`, `onNegotiationRequired`, `_addToCart`, `_explainNegotiationRequired` and their imports; keep Make an Offer or View offer and Buy Now. Remove strings that nothing uses any more.
- [ ] `system_card.dart`: render the `ADDED_TO_CART` card for the seller (and a quiet line for the buyer); add an "Add to cart" button on the **newest** accepted-offer card for the buyer when the cart is available; the tap uses `cartAdderProvider` and shows the result as the saved-items flow did ("Added to your cart" with View cart, or the cart error text). Pass `isNewestAccepted` and a callback from the chat screen.
- [ ] `negotiation_screen.dart`: an "Add to cart" button in the accepted state for the buyer (next to the price lock banner), same handler. Move the shared add-and-show-result code into one helper so the chat card, the negotiation screen and the cart re-add use it.
- [ ] `saved_items_screen.dart`: replace the Add to Cart button with "View details" that opens `RouteNames.listingView(item.id)`; remove `_addToCart` and the cart imports; only for available items.
- [ ] ARB (English and Hindi): `savedItemViewDetails` ("View details", "विवरण देखें"), the card texts (`offerCardAddedToCart`, `offerCardAddToCart`) and the notification text if shown in the app; regenerate localizations.
- [ ] Deep link: the `CART_ITEM_ADDED` notification opens the chat thread (existing `/chats/{id}`).

### Documents

- [ ] User stories: US-012 (listing page action list), US-017 (accepted offer card and screen), US-018 (Saved items button), US-019 (where Add to Cart lives, seller card and notification); Sprint 3 LLD Part C, Sprint 4 LLD (card kind), Sprint 5 LLD Part A (A.3, A.8 as built); testing guides for US-019 and US-012.
- [ ] A short testing guide section for this change.

## 5. Test Plan (target above 90 percent on new and changed code)

**Backend**

- Unit: `CartService.add` publishes the event once for a new line, not for an existing or expired-then-readded line under the same agreement, and not when checkout is off. `CartAddedListener`: posts the card and the notification once per agreement, skips when Redis says it was done, swallows port and notification failures, never throws. `CartChatAdapter`: creates the thread when missing, skips a read-only thread, card payload (kind, amount, validUntil, by), seller is the notified user.
- Integration (PostgreSQL): accepted offer, then add to cart creates one card and one notification for the seller; a second add does not; remove and re-add under the same agreement does not; a Buy Now hold with no thread creates the thread and the card; a blocked pair adds to the cart but posts nothing; checkout off posts nothing; the seller's chat list shows the card with the preview and an unread count.

**Mobile**

- Listing page: no Add to Cart for any capability combination, no hint; Make an Offer or View offer and Buy Now unchanged; layout at 320 dp and 200 percent text.
- Chat: the button shows for the buyer on the newest accepted card only, never for the seller or on an older card; success shows "Added to your cart" with View cart; each error code shows its text; the seller's `ADDED_TO_CART` card renders with the buyer, price and time; an unknown kind keeps the neutral line (AC8).
- Negotiation screen: the button in the accepted state for the buyer only; none for the seller or other states.
- Saved items: "View details" opens the listing page for an available item; unavailable items have no button; Hindi; large text. The old Add to Cart tests are replaced.
- Shared helper: success, refusal and busy-tap guard.

## 6. Validation Checklist

- [ ] AC1 to AC9 each checked by a test or a manual case.
- [ ] Edge: item already in the cart; price ended between accept and tap; own listing; cart full (20); read-only thread; two taps at once; offer re-accepted at a new price (new agreement, so a new card).
- [ ] No Add to Cart left anywhere on the listing page, and no dead strings or imports.
- [ ] Backend `mvn clean verify` and checkstyle clean; SonarQube new-code gate; mobile `dart format --output=none --set-exit-if-changed lib test integration_test`, `dart analyze`, full test run.
- [ ] Hindi strings flagged for review.
- [ ] LLDs, user stories and testing guides updated; hand-offs from other stories searched (US-012, US-018, US-019, US-017).

## 7. Open Gaps / Questions

| # | Item | Decision (2026-11-24) |
|---|---|---|
| 1 | Where the "one per agreement" marker lives | **Redis** set-if-absent (48 hours); a lost key can only repeat a harmless card. |
| 2 | Should the buyer also see a line in the chat? | **Yes**, a quiet "You added this to the cart" line on the buyer's side (the same card with buyer wording). |
| 3 | A card for removal or expiry | None. |
| 4 | Estimate | **About 5 SP**, agreed. |
| 5 | Notification deep link | The chat thread, as for other chat notifications. |
| 6 | This work and the US-014/US-015 branches | Independent. It starts from `main` and merges separately. The un-pushed US-014/US-015 branches must not carry it. |
| 7 | Older app builds | Not a concern: development phase, no installed older app. |

## 8. As built (2026-11-24)

Branches: backend and mobile `feature/US-019-cart-from-accepted-offer`; Documents `docs/US-019-cart-from-accepted-offer-plan`. LLD: Sprint 5 A.9 (also Sprint 4 change log 0.14 and the Sprint 3 D.11 note).

- **Backend.** `CartService.add` publishes `CartItemAddedEvent` for a newly created line. `CartAddedListener` (after commit, own transaction) takes a Redis marker `cart:added:{agreementId}` for 48 hours, then `CartChatPort` (adapter `CartChatAdapter`, communication module) posts the `ADDED_TO_CART` card and an in-app `CART_ITEM_ADDED` notification (dedupe key `cart-added:{agreementId}`, link `/chats/{thread}`). No push. A read-only or blocked thread gets no card. `CartMetrics.sellerNotified(outcome)`.
- **Mobile.** Add to Cart removed from the listing page (`ListingActions`, `ListingViewScreen`); Saved items shows "View details"; the chat's newest accepted card and the negotiation screen give the buyer "Add to cart" through `addAcceptedToCart`; `SystemCard` renders `ADDED_TO_CART` with "Price held until"; new English and Hindi strings (`offerCardAddedToCart`, `offerCardHeldUntil`, `offerCardAddToCart`, `savedItemViewDetails`); `listingViewAddToCart` and `listingViewNegotiationRequired` removed.
- **Deviation (AC9).** With `valuex.checkout.enabled` off the button stays **visible** and a tap shows the existing "not available yet" text (the add answers 503 `ERROR_CHECKOUT_UNAVAILABLE`); no card or notification is created. Hiding it would have needed a new capability read on the chat and the negotiation screen for no gain while the cart ships dark.
- **Hindi.** `offerCardAddedToCart` is "{who} इसे {amount} पर कार्ट में जोड़ा": the "who" word already carries "ने" (a test caught a doubled "ने"). Needs native review with the other Hindi texts.
- **Tests.** Backend `mvn clean verify`: 3,745 run, 0 failures, 9 skipped; checkstyle clean; new code 100 percent lines and branches (`CartService` 77/77, `CartAddedListener`, `CartChatAdapter`, `CartItemAddedEvent`, `CartMetrics`). New: `CartAddedListenerTest` (4), `CartChatAdapterTest` (5), 4 cases each in `CartServiceTest` and `CartIntegrationTest`. Mobile: 2,415 pass, only the 2 known `google_accessibility_test` failures; `dart analyze lib test` clean; `dart format` clean on touched files; new or changed files 91 to 100 percent. New: `add_accepted_to_cart_test.dart` (replaces the old listing-page cart test), chat thread, card, negotiation screen, listing and Saved items cases.
- **SonarQube.** No issue in any file this change adds or edits. The quality gate stays ERROR on 24 pre-existing new-code issues in other stories' tests (`DeliveryChoiceServiceTest`, `CartItemViewAssemblerTest`, `StubShippingQuoteAdapterTest`, and others) and one INFO in `ValuexProperties`.
- **Hand-offs closed.** The Saved items "Add to Cart" of US-019, the listing-page action of US-012 and its testing guide, the US-073 and US-069 guides, and the user-story notes were updated; the old listing-page cart widget test was replaced.
- **Bug fix found while testing (2026-11-24).** `PriceAgreementService.createFromOffer` refused the seller's accept with `ERROR_ALREADY_ACCEPTED` while the **same buyer** held a Buy Now reservation. It now cancels the buyer's own hold (`REPLACED_BY_OFFER`) and creates the offer's agreement; another buyer's hold is still refused. Tests: `PriceAgreementServiceTest` (own hold replaced) and `BuyNowIntegrationTest` (seller accepts while the buyer holds Buy Now). A cart line that pointed at the replaced Buy Now agreement shows as expired until the buyer taps Add to cart on the accepted offer, which re-points it.
- **Open.** Hindi review; iOS not verified; `capabilities.cart` and `NEGOTIATION_REQUIRED` remain in the API unused by the app (removal is a separate clean-up). Device check on two phones: see the testing guide, section M.

**Status: Approved** (2026-11-24, product owner: "Approved"). Implemented; waiting for the owner's approval to commit, push and open the pull requests.
