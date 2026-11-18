# US-017 - Price Negotiation: QA Testing Guide

**Sprint 4 · Communication & Negotiation**

Manual test cases for making an offer, countering, accepting, declining, withdrawing, the locked price, and the live
and in-app updates. The backend is checked with `curl` and SQL; the app is checked on two phones (or one phone and
`curl`): one signed in as the **buyer**, one as the **seller**.

> **What ships:** `POST /api/v1/listings/{id}/offers`, `GET /api/v1/negotiations`, `GET /api/v1/negotiations/{id}`,
> `POST /api/v1/offers/{id}/accept`, `/reject`, `/counter`, `POST /api/v1/negotiations/{id}/cancel`; migration `V36`
> (`negotiations`, `offers`, `negotiation_status_history`, `price_agreements`) and the Admin settings of the negotiation
> rules. In the app: the Make an Offer sheet on the listing page, the negotiation screen (buyer and seller view), offer
> cards in the chat thread, in-app notifications with a link to the negotiation.
> **Not in this story:** the seller's offers inbox, badges and the automatic rejection of other buyers' offers when one
> is accepted (US-076); the 48 hour expiry job, the expiry warning and the end of the price lock by a job (US-080; a
> lock that ends is still handled when the next offer or accept is made); the checkout button and the checkout guard
> (US-018, Sprint 5); push notifications (US-131); an Admin screen for the numbers (US-116, until then change them in
> `platform_settings`); Make an Offer on the chat header (use the listing page).

| Setting | Value |
|---|---|
| Backend base URL | `http://localhost:8080` |
| Amount rules | First offer above 0 and not above the asking price; two decimals at most; below `NEGOTIATION_LOW_OFFER_PERCENT` (50) of the asking price needs confirmation. Seller counter: above the buyer's last offer, up to the asking price. Buyer counter: not below the buyer's previous offer, below the seller's last counter. |
| Limits (Admin settings) | `NEGOTIATION_MAX_ROUNDS` 5, `NEGOTIATION_INACTIVITY_HOURS` 48, `NEGOTIATION_MAX_LIFETIME_DAYS` 14, `PRICE_LOCK_HOURS` 24, `NEGOTIATION_REOFFER_COOLDOWN_HOURS` 24, `NEGOTIATION_OPEN_PER_BUYER_MAX` 20, `OFFERS_PER_MIN` 20 |
| Error codes | 422 `ERROR_INVALID_OFFER`, `ERROR_INVALID_COUNTER`, `WARNING_LOW_OFFER`; 409 `ERROR_NEGOTIATION_EXISTS`, `ERROR_NOT_NEGOTIABLE`, `ERROR_ITEM_RESERVED`, `ERROR_ITEM_UNAVAILABLE`, `ERROR_ALREADY_ACCEPTED`, `ERROR_OFFER_NOT_CURRENT`, `ERROR_NEGOTIATION_EXPIRED`, `ERROR_MAX_NEGOTIATIONS`, `WARNING_MAX_NEGOTIATIONS`, `ERROR_NEGOTIATION_COOLDOWN`, `ERROR_TOO_MANY_NEGOTIATIONS`, `ERROR_OWN_LISTING`; 403 `AADHAAR_VERIFICATION_REQUIRED`, `ERROR_BLOCKED`; 404 `ERROR_NEGOTIATION_NOT_FOUND`; 429 `RATE_LIMIT_EXCEEDED` |
| Known gaps | Hindi texts need native-speaker review; the seller has no offers inbox yet and reaches the negotiation from the notification or the chat card |

---

## Prerequisites

1. Backend, PostgreSQL and Redis running; the app running against it (see the US-011 guide). Realtime is on by default
   (`valuex.realtime.enabled=true`); for test E set it to `false` and restart.
2. A published, negotiable goods listing with a price of 14,500 owned by `$SELLER` (id `LISTING`), and a second
   `ACTIVE`, Aadhaar-verified buyer `$BUYER2`. `$BUYER` is also Aadhaar verified. Note the user ids.
3. Handy variables:

```bash
B="localhost:8080/api/v1"
HB="Authorization: Bearer $BUYER"
HS="Authorization: Bearer $SELLER"
H2="Authorization: Bearer $BUYER2"
J="Content-Type: application/json"
```

---

## A. Make an offer (AC1, AC2)

| # | Steps | Expected |
|---|---|---|
| A1 | App, buyer: open the listing. | Make an Offer is available (not "Coming soon"). The seller sees "Own listing". |
| A2 | Tap Make an Offer. | A sheet shows "Make an offer", "Asking price: ₹14,500" and "You can offer up to ₹14,500". |
| A3 | Enter 12000 and tap Send offer. | The negotiation screen opens: "Waiting for the seller", "Round 1 of 5", an expiry chip near "Expires in 48h 0m", the offer "You · round 1 ₹12,000" and a Cancel offer button. |
| A4 | Seller, app: open Notifications > Messages. | "New offer on Hero phone" (your listing title) with "A buyer offered ₹12,000"; tapping it opens the negotiation. |
| A5 | `SELECT state, round_count, last_offer_amount FROM negotiations ORDER BY created_at DESC LIMIT 1;` | `SELLER_REVIEWING`, 1, 12000.00. `SELECT status FROM offers ...` is `PENDING`. `negotiation_status_history` has 2 rows (`SEND_OFFER`, `NOTIFY_SELLER`). |
| A6 | Open the chat with the seller (header icon on the negotiation screen). | The thread has an offer card "You offered ₹12,000 · View offer"; the seller's thread shows "The buyer offered ₹12,000". Tapping a card opens the negotiation. |
| A7 | Buyer: back to the listing. | The button reads "View offer"; tapping it opens the same negotiation. |

## B. Seller answers (AC3, AC4)

| # | Steps | Expected |
|---|---|---|
| B1 | Seller, app: open the negotiation from the notification. | "Buyer offered ₹12,000", buttons Accept ₹12,000, Counter, Decline; no Cancel offer. |
| B2 | Tap Counter. | A sheet explains "Enter between ₹12,000.01 and ₹14,500". |
| B3 | Enter 12000, then 14501, then 13500. | The first two show "Counter offer must be between ₹12,000.01 and ₹14,500" and are not sent; 13500 is sent. |
| B4 | Buyer, app: the notification "Counter offer on ..." arrives; open it. | "Seller countered ₹13,500", Accept ₹13,500, Counter, Decline, Cancel offer; "Round 2 of 5". |
| B5 | Buyer: tap Accept ₹13,500. | "Accepted at ₹13,500" and a green banner "Price locked at ₹13,500. Ends in 24h 0m". |
| B6 | Seller: the notification "Offer accepted for ..." arrives; the negotiation shows the same banner. | Accepted at ₹13,500; no action buttons. |
| B7 | SQL: `SELECT status, valid_until FROM price_agreements ORDER BY created_at DESC LIMIT 1;` | `ACTIVE`, valid for 24 hours. `offers` statuses: `SUPERSEDED`, `SUPERSEDED`, `ACCEPTED` (as many as rounds). |
| B8 | Seller declines (new negotiation): Decline > confirm "Decline this offer?". | The buyer sees "Declined"; `negotiations.closed_reason` is `REJECTED_BY_SELLER`. Buyer's notification: "Offer declined for ...". |
| B9 | Buyer offers again on that listing within 24 hours. | "You can make a new offer on this item later" (cooldown). After setting `NEGOTIATION_REOFFER_COOLDOWN_HOURS` to 0 the offer is accepted. |

## C. Counter again, decline, withdraw (AC5)

| # | Steps | Expected |
|---|---|---|
| C1 | Buyer, on a seller counter of 13,500 after an offer of 12,000: Counter with 12999, then with 13500, then with 11000. | 12999 is sent; 13500 (the seller's price) and 11000 (below the buyer's own earlier offer) are refused with the allowed range. |
| C2 | Buyer: Decline > "Decline this offer?" > Decline. | "Declined"; `closed_reason` `DECLINED_BY_BUYER`. |
| C3 | Buyer, while the seller is reviewing: Cancel offer > Keep. | Nothing changes. |
| C4 | Cancel offer > Cancel offer. | "Cancelled"; the seller gets "Offer withdrawn for ..."; `closed_reason` `CANCELLED_BY_BUYER`. |
| C5 | Buyer cancels after the seller accepted. | The price lock is released: `price_agreements.status` is `CANCELLED`; another buyer can offer on the listing. |
| C6 | Round limit: go back and forth until round 5 (offer, counter, counter, counter, counter). | The person whose turn it is can only Accept or Decline (no Counter). `curl` a sixth price: buyer `ERROR_MAX_NEGOTIATIONS`, seller `WARNING_MAX_NEGOTIATIONS`. |

## D. Edge cases and validations

| # | Steps | Expected |
|---|---|---|
| D1 | Offer 5000 (below 50 percent of the asking price, which is 7,250). | The app asks "Much lower than the asking price... Send anyway?". Change offer keeps the amount; Send anyway sends it. `curl` without `"confirmLowOffer": true` answers 422 `WARNING_LOW_OFFER` and stores nothing. |
| D2 | Offer 0, 14500.01, `abc` and `12.345`. | The sheet refuses each ("Offer must be between ₹1 and ₹14,500" or "Enter a valid amount..."); `curl` answers 422 `ERROR_INVALID_OFFER` with `details.min`, `details.max`. |
| D3 | Buyer taps Send twice quickly / `curl` the same `clientRequestId` twice. | One negotiation; the second call answers 200 with the same id. A different `clientRequestId` while one is open answers 409 `ERROR_NEGOTIATION_EXISTS` with `details.negotiationId`; the app opens that negotiation. |
| D4 | Two buyers offer on the same listing. | Two independent negotiations; the listing stays visible. The seller accepts buyer 1: buyer 2's negotiation is declined at once by US-076 (`closed_reason = SUPERSEDED`), so a later accept of its offer answers 409 `ERROR_OFFER_NOT_CURRENT` (the `ERROR_ALREADY_ACCEPTED` guard remains for a race, see the US-076 guide); buyer 3 sees Make an Offer disabled ("Reserved right now") and `curl` answers 409 `ERROR_ITEM_RESERVED`. |
| D5 | Seller changes the asking price down to 700 after an offer of 800, then accepts. | The agreed price is 700 (the lower of the offer and the asking price). |
| D6 | After a counter, `curl` accept with the old offer id. | 409 `ERROR_OFFER_NOT_CURRENT`; the app, when it was open on the old state, shows "This offer has changed. The latest is shown" and refreshes. |
| D7 | `UPDATE negotiations SET expires_at = now() - interval '1 minute' WHERE id = '<id>'`, then answer. | 409 `ERROR_OFFER_EXPIRED` when the seller answers (since US-076; the buyer still gets `ERROR_NEGOTIATION_EXPIRED`); the screen shows "Expired" for the chip. |
| D8 | Mark the listing sold (or delete it, or have an Admin remove it) while a negotiation is open. | Both people are told "Negotiation ended for ..."; the state is `NEGOTIATION_CANCELLED`, `closed_reason` `LISTING_UNAVAILABLE`; an accepted price lock is `CANCELLED`; the chat shows "Negotiation ended: the item is no longer available". |
| D9 | Suspend the seller's account while a negotiation is open. | Cancelled with `ACCOUNT_UNAVAILABLE`. |
| D10 | A listing that is not negotiable, or has no price: `curl` an offer. | 409 `ERROR_NOT_NEGOTIABLE`; in the app Make an Offer is disabled ("Not negotiable"). |
| D11 | The seller offers on their own listing. | 409 `ERROR_OWN_LISTING`. A blocked pair: 403 `ERROR_BLOCKED`. |
| D12 | An unverified (no Aadhaar) buyer: tap Make an Offer / `curl` with a token without the Aadhaar claim. | The button shows "Identity verification needed"; `curl` answers 403 `AADHAAR_VERIFICATION_REQUIRED`. |
| D13 | A user who is not in the negotiation: `curl -H "$H2" $B/negotiations/<id>` and accept/cancel with their token. | 404 `ERROR_NEGOTIATION_NOT_FOUND` for each. |
| D14 | Real Estate listing: offer and accept. | Accept works; no price lock banner, instead "Price agreed: ₹X. The owner will close the deal."; no `price_agreements` row. |
| D15 | 21 offers within a minute (set `OFFERS_PER_MIN` to 5 to test faster). | 429 `RATE_LIMIT_EXCEEDED` ("Too many offers. Try again in a minute"). 21 open negotiations by one buyer: 409 `ERROR_TOO_MANY_NEGOTIATIONS`. |
| D16 | The seller's listing page shows no "negotiated price". | The listing price is unchanged; the agreed price is only in the negotiation. |

## E. Live updates and fallback

| # | Steps | Expected |
|---|---|---|
| E1 | Both phones on the negotiation screen; the seller counters. | The buyer's screen updates within a second with no tap ("Seller countered ..."). |
| E2 | Buyer app in the background, then open it again. | The screen is read again on return. |
| E3 | Stop the realtime gateway (`valuex.realtime.enabled=false`) and make a counter. | The other phone updates within about 15 seconds (polling); pull down on the screen refreshes at once. |
| E4 | Turn Wi-Fi off, tap Accept. | A network message is shown; nothing is doubled when the network returns and Accept is tapped again. |

## F. Read endpoints

| # | Steps | Expected |
|---|---|---|
| F1 | `curl -H "$HB" "$B/negotiations?role=BUYER&status=OPEN"` | The buyer's open negotiations, newest activity first, with `role`, `awaiting`, `actions`, `counterRange`, `agreedPrice`, `priceLockExpiresAt`, `serverTime`. |
| F2 | `curl -H "$HS" "$B/negotiations?role=SELLER&status=CLOSED"` | The seller's closed ones. Without filters both roles and all states. |
| F3 | `curl "$B/listings/$LISTING/public" -H "$HB"` | `capabilities.offer.available` is true; `contact.negotiationId` is the open negotiation's id (null otherwise). For a third buyer after an accept: `offer.reason` `RESERVED`. |

## G. Language and accessibility

| # | Steps | Expected |
|---|---|---|
| G1 | Switch to Hindi: the sheet, the negotiation screen, the chat card and the notifications. | Texts appear in Hindi (to be reviewed by a native speaker). |
| G2 | Text size 200 percent on a 320 px wide phone. | No clipped text or overflow; the action buttons stay reachable. |
| G3 | A screen reader on the negotiation screen. | The status is read as a live region; amounts are read as rupees; the countdown is announced when it changes; buttons are at least 48 dp. |

---

## How to run the automated tests

```bash
# backend (from valuex-backend); Docker needed for the integration test
export JAVA_TOOL_OPTIONS="-Dapi.version=1.44 -Duser.timezone=Asia/Kolkata"
mvn -o test -Dtest='com.valuex.negotiation.**.*Test'
mvn -o test -Dtest='NegotiationIntegrationTest'

# mobile (from valuex-mobile)
flutter test test/features/negotiation test/features/listing_view --dart-define=SKIP_PIXEL_CONTRAST=true
```
