# US-076 - Seller Negotiation Management: QA Testing Guide

**Sprint 4 · Communication & Negotiation**

Manual test cases for the seller's Offers screen, answering offers, the automatic decline of the other buyers' offers
when one is accepted, the Offers badge and the live updates. The backend is checked with `curl` and SQL; the app is
checked on three phones (or fewer phones and `curl`): one signed in as the **seller**, two as **buyers**.

> **What ships:** `GET /api/v1/offers/received` and `GET /api/v1/offers/received/summary`; migration `V37`
> (`idx_negotiations_seller_open` and the setting `NEGOTIATION_WARNING_BEFORE_HOURS`); accepting an offer for goods
> declines the other open offers of the item; the `OFFERS` badge in the profile menu summary and in the
> `badge.updated` live event; `ERROR_OFFER_EXPIRED` for a seller. In the app: Profile > Selling > Offers (Received and
> Sent tabs), the accept confirmation, the counter slider and the last-round note.
> **Not in this story:** an Offers tab inside the chat list; buyer ratings (the card shows "No ratings yet" until the
> rating module exists); the 48 hour expiry job and the expiry warning notification (US-080: until then an offer past
> its time stays listed and shows as expired); push notifications (US-131); the checkout button (US-018, Sprint 5).

| Setting | Value |
|---|---|
| Backend base URL | `http://localhost:8080` |
| Lists | `status` = `PENDING` (default; offers still in play, soonest expiry first), `ACCEPTED` (price still locked), `CLOSED`, `ALL`; `size` at most 50; an unknown `status` means `PENDING` |
| Summary | `pending` (waiting for the seller), `accepted` (locked prices), `expiringSoon` (pending offers that run out within `NEGOTIATION_WARNING_BEFORE_HOURS`, default 24) |
| Badge | One key `OFFERS`: offers waiting for the person's answer as seller (buyer offers) plus as buyer (seller counters), not past their time |
| Error codes | 409 `ERROR_OFFER_EXPIRED` (seller), `ERROR_NEGOTIATION_EXPIRED` (buyer), `ERROR_OFFER_NOT_CURRENT`, `ERROR_ALREADY_ACCEPTED`; 422 `ERROR_INVALID_COUNTER` (with the range); 409 `WARNING_MAX_NEGOTIATIONS` (seller at the round cap) |
| Known gaps | Hindi texts need native-speaker review |

---

## Prerequisites

1. Backend, PostgreSQL and Redis running; the app running against it. Realtime is on by default
   (`valuex.realtime.enabled=true`); for test F set it to `false` and restart.
2. A published, negotiable goods listing with a price of 14,500 owned by `$SELLER` (id `LISTING`), and two
   `ACTIVE`, Aadhaar-verified buyers `$BUYER1` and `$BUYER2`; a second listing `LISTING2` of `$SELLER` for the scoping
   test. Note the user ids.
3. Handy variables:

```bash
B="localhost:8080/api/v1"
HS="Authorization: Bearer $SELLER"
H1="Authorization: Bearer $BUYER1"
H2="Authorization: Bearer $BUYER2"
J="Content-Type: application/json"
```

4. Make the offers of buyer 1 (12000) and buyer 2 (10000) on `LISTING`:

```bash
curl -s -X POST $B/listings/$LISTING/offers -H "$H1" -H "$J" -d '{"amount":"12000","clientRequestId":"'$(uuidgen)'"}'
curl -s -X POST $B/listings/$LISTING/offers -H "$H2" -H "$J" -d '{"amount":"10000","clientRequestId":"'$(uuidgen)'"}'
```

---

## A. The Offers screen (AC1)

| # | Steps | Expected |
|---|---|---|
| A1 | Seller, app: open Profile. | A row **Offers** is the first row under Selling, with a badge showing 2. |
| A2 | Tap Offers. | The Offers screen opens on the **Received** tab with the chips Pending (2), Accepted and Closed. Two cards: buyer name, "No ratings yet", the item title and thumbnail, "Offered ₹12,000 of ₹14,500" (and "Offered ₹10,000 of ₹14,500"), how long ago, "Needs your answer" and an expiry chip near "Expires in 48h 0m". |
| A3 | `UPDATE negotiations SET expires_at = now() + interval '2 hours' WHERE buyer_id = '<buyer 2>';` then pull down to refresh. | Buyer 2's card moves to the top (soonest expiry first); a line "1 expiring soon" shows under the chips. |
| A4 | `curl -s "$B/offers/received" -H "$HS"` and `curl -s "$B/offers/received/summary" -H "$HS"`. | Items in the same order with `buyer`, `listing`, `offeredPrice`, `offeredAt`, `round`, `expiresAt`, `priceLockExpiresAt: null`; summary `{"pending":2,"accepted":0,"expiringSoon":1}`. |
| A5 | `curl -s "$B/offers/received" -H "$H1"` (a buyer who owns no listing). | `totalItems` is 0: the list holds only the caller's own offers as seller. |
| A6 | `curl -s "$B/offers/received?status=PENDING&size=500" -H "$HS"` and `?status=NONSENSE`. | `size` in the answer is 50; the unknown status behaves as `PENDING`. |
| A7 | Tap a card. | The negotiation screen opens (US-017) with Accept, Counter and Decline. Back returns to the list, which reads again. |

## B. Accept, with the other offers declined (AC2, AC3, edge case 2)

| # | Steps | Expected |
|---|---|---|
| B1 | Open buyer 1's offer and tap **Accept ₹12,000**. | A dialog "Accept this offer?" says the price is locked for the buyer and the other offers on this item will be declined. **Keep** closes it and nothing changes. |
| B2 | Tap Accept again, then **Accept** in the dialog. | The screen shows "Accepted at ₹12,000", the price-lock banner with the time left, and the note "The buyer has been told and can now go to checkout." |
| B3 | Buyer 1, app: Notifications. | "Offer accepted for ..." with the agreed price. |
| B4 | Buyer 2, app: Notifications and the chat with the seller. | "Offer closed for ..." with "The seller accepted another offer for this item. You can make a new offer if it becomes available again"; the thread has a card with the same sentence. **Neither shows who won or any price.** |
| B5 | `SELECT state, closed_reason FROM negotiations WHERE listing_id = '<LISTING>';` | Buyer 1: `OFFER_ACCEPTED`, null; buyer 2: `OFFER_REJECTED`, `SUPERSEDED`. `SELECT status FROM offers ...` for buyer 2 is `REJECTED`. One `price_agreements` row is `ACTIVE`. |
| B6 | Seller, Offers > Accepted. | One card with "Accepted at ₹12,000" and "Price locked, 23h 59m left". Pending is empty; Closed shows buyer 2's card as "Declined". |
| B7 | Try to accept buyer 2's old offer id. | 409 `ERROR_OFFER_NOT_CURRENT`. |
| B8 | Two phones: seller accepts two different offers within the same second (or run two `curl` accepts in parallel). | One answers 200, the other 409; exactly one `ACTIVE` agreement exists. |
| B9 | `UPDATE price_agreements SET valid_until = now() - interval '1 minute' WHERE listing_id = '<LISTING>';` then buyer 2 offers again and the seller accepts. | The new offer is allowed and accepted; the first negotiation is `NEGOTIATION_EXPIRED`; one `ACTIVE` agreement. |
| B10 | A property listing (or `UPDATE negotiations SET real_estate = TRUE ...` on a test copy): accept one offer. | The dialog says the other offers on the property stay open; they stay `SELLER_REVIEWING`; no price lock. The seller does **not** see the checkout note. |

## C. Reject and counter (AC4, AC5)

| # | Steps | Expected |
|---|---|---|
| C1 | Seller: open an offer, tap **Decline**, confirm. | "Declined"; the buyer is notified "Offer declined for ..." and the negotiation ends; the card moves to Closed. |
| C2 | Open another offer, tap **Counter**. | A sheet with the range text "Enter between ₹X and ₹14,500", a field and a **slider**. |
| C3 | Drag the slider. | The field shows whole rupees; typing a value moves the slider; typing below or above the range keeps the slider at the end and shows "Counter offer must be between ...". |
| C4 | Send a counter inside the range. | The negotiation shows "Waiting for the buyer"; in the list the card says "Waiting for the buyer" (still under Pending). The buyer is notified "Counter offer on ...". |
| C5 | Buyer counters back until the round cap (round 5 of 5, a seller turn). | The seller sees "This is the last round. You can only accept or decline." and only Accept and Decline are offered; `curl` counter answers 409 `WARNING_MAX_NEGOTIATIONS`. |
| C6 | `curl` a counter of 100 on an offer of 12000. | 422 `ERROR_INVALID_COUNTER` with `details.min` and `details.max`; the app shows the range in words. |

## D. Expiry while reviewing (edge case 3)

| # | Steps | Expected |
|---|---|---|
| D1 | Open an offer. `UPDATE negotiations SET expires_at = now() - interval '1 minute' WHERE id = '<id>';` Tap Accept and confirm. | 409 `ERROR_OFFER_EXPIRED`: the app says "This offer has expired" and re-reads the negotiation, which shows "Expired". Nothing is accepted. |
| D2 | Seller, Offers > Pending. | The expired offer is still listed (until the US-080 job closes it) with "Expired" instead of a countdown and no "Needs your answer". |
| D3 | The same on the buyer side (a seller counter past its time, the buyer taps Accept). | 409 `ERROR_NEGOTIATION_EXPIRED` ("This negotiation has expired"). |

## E. Sent tab and buyer cancel (edge case 4)

| # | Steps | Expected |
|---|---|---|
| E1 | Buyer 1, app: Profile > Selling > Offers > **Sent**. | The offers the buyer made, with the seller's name (no rating), "Waiting for the seller" and a countdown; chips Pending, Accepted, Closed work. |
| E2 | Buyer cancels an offer before the seller answers. | The seller's Pending list no longer has it (it moves to Closed) and the badge drops. |
| E3 | Seller counters buyer 1's offer. | In buyer 1's Sent > Pending the card says "Needs your answer" and the buyer's badge counts it. |

## F. Badge and live updates

| # | Steps | Expected |
|---|---|---|
| F1 | `curl -s $B/users/me/menu-summary -H "$HS"` with 2 offers waiting. | `data.badges.OFFERS` is 2. After accepting one and the others are declined: 0 (the key can be absent at 0). |
| F2 | Seller has the Profile page open; buyer 2 makes a new offer. | The Offers badge changes to 1 without a refresh (event `badge.updated` with `offersAwaiting`). |
| F3 | Seller has the Offers screen open; a buyer makes an offer. | The new card appears without a refresh; the chip count rises. |
| F4 | Switch the realtime gateway off (`valuex.realtime.enabled=false`), restart, repeat F3. | The list updates within about 15 seconds by polling. |
| F5 | `UPDATE platform_settings SET setting_value = '60' WHERE setting_key = 'NEGOTIATION_WARNING_BEFORE_HOURS'` (inactivity is 48). Wait for the cache (about a minute) or restart. | The values are not used: both warning and inactivity hours return to 24 and 48 (a warning must stay below the inactivity time); the log says the settings contradict each other. |
| F6 | `GET /negotiations/{id}` for an open negotiation. | `warnAt` is `expiresAt` minus 24 hours (before, it was always null); null once the negotiation is closed. |

## G. Language and accessibility

| # | Steps | Expected |
|---|---|---|
| G1 | Switch the app to Hindi; open Offers, the accept dialog, the counter sheet and a notification of a declined buyer. | All texts are in Hindi (marked for native-speaker review); no overflow at 320 px width and 200 percent text. |
| G2 | TalkBack on the Offers screen. | Each card is read as one sentence: name, item, "Offered ₹12,000 of ₹14,500", time and status; the slider reads its value in rupees; the countdown chips are labelled; all targets are at least 48 dp. |

---

## How to run the automated tests

```bash
# backend (from valuex-backend; Docker running for the integration test)
export JAVA_TOOL_OPTIONS="-Dapi.version=1.44 -Duser.timezone=Asia/Kolkata"
mvn -o test -Dtest='NegotiationSupersedeServiceTest,ReceivedOffersServiceTest,OffersBadgeProviderTest,OffersReceivedControllerTest,ReceivedFilterTest,NegotiationServiceTest,NegotiationQueryServiceTest,NegotiationRealtimeListenerTest,NegotiationNotificationListenerTest,NegotiationSettingTest,PlatformSettingsServiceTest'
mvn -o test -Dtest='NegotiationIntegrationTest'

# mobile (from valuex-mobile)
flutter test test/features/negotiation test/features/profile --dart-define=SKIP_PIXEL_CONTRAST=true
```
