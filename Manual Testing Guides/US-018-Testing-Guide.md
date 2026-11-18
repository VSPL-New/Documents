# US-018 - Prevent Checkout Without Price Acceptance: QA Testing Guide

**Sprint 4 · Communication & Negotiation**

Manual test cases for the rule that a buyer can check out only at a price the seller accepted: the price status of a
listing for one buyer and for a cart, the `agreement` block on the listing page, the live `agreement.updated` event,
and the guard that the checkout of Sprint 5 will call. This story is backend only: the status endpoints and the
listing page are checked with `curl` and SQL. **There is no checkout endpoint yet**, so the guard itself is checked
by the automated tests (section G); the manual cases below check the same rules through the status the app will use.

> **What ships:** `CheckoutPriceGuard` (`requireValid`, `markConsumed`; a Java contract called inside the order
> transaction, not an HTTP route); `GET /api/v1/listings/{listingId}/price-agreement` and
> `POST /api/v1/price-agreements/status`; `contact.agreement` on the listing details; the realtime event
> `agreement.updated`; the reusable `CheckoutPriceGuardContractTest`. No migration.
> **Not in this story (Sprint 5, US-019 to US-021):** the cart, the "Proceed to checkout" button and its text
> "Waiting for seller to accept your offer", the badge on each cart item, the order itself, and the English and Hindi
> texts of the error codes in the app. Buy Now agreements (US-068) are tested here only with rows inserted by hand.

| Setting | Value |
|---|---|
| Backend base URL | `http://localhost:8080` |
| Price lock | `PRICE_LOCK_HOURS` 24 (Admin setting) |
| Status limit | `RATE_LIMIT_DETAILS_PER_MIN` 120 per user (shared by the two status endpoints) |
| Status values | `NONE`, `PENDING` (waiting for the seller), `ACCEPTED` (with `agreedPrice`, `validUntil`), `EXPIRED`, `RESERVED` (another buyer's price holds the item) |
| Guard error codes | 409 `ERROR_PRICE_NOT_ACCEPTED` "Seller hasn't accepted your offer yet"; 409 `ERROR_ACCEPTANCE_EXPIRED` "Price acceptance expired. Please re-negotiate"; 403 `ERROR_UNAUTHORIZED_CHECKOUT` "Cannot proceed without seller acceptance"; 409 `ERROR_PRICE_CHANGED` "Price has changed. Please review"; 409 `ERROR_ITEM_RESERVED`; 409 `ERROR_CHECKOUT_NOT_APPLICABLE` (property); 409 `ERROR_ITEM_UNAVAILABLE` |
| Known gaps | App texts for the guard errors and the whole cart side are Sprint 5 |

---

## Prerequisites

1. Backend, PostgreSQL and Redis running.
2. A published, negotiable goods listing owned by `$SELLER` (id `LISTING`), a second published goods listing
   `LISTING2`, and three `ACTIVE`, Aadhaar-verified buyers `$BUYER1`, `$BUYER2` and `$BUYER3`.
3. Handy variables:

```bash
B="localhost:8080/api/v1"
HS="Authorization: Bearer $SELLER"
H1="Authorization: Bearer $BUYER1"
H2="Authorization: Bearer $BUYER2"
H3="Authorization: Bearer $BUYER3"
J="Content-Type: application/json"
status() { curl -s $B/listings/$1/price-agreement -H "$2"; }
```

4. To make an offer and accept it (used many times below):

```bash
curl -s -X POST $B/listings/$LISTING/offers -H "$H1" -H "$J" -d '{"amount":"4000","clientRequestId":"'$(uuidgen)'"}'
# note NEG (data.negotiationId) and OFFER (data.offers[0].offerId)
curl -s -X POST $B/offers/$OFFER/accept -H "$HS"
```

---

## A. Status of one listing (AC1, AC2)

| # | Steps | Expected |
|---|---|---|
| A1 | `status $LISTING "$H1"` before any offer. | 200, `data.status = NONE`, no price, no `negotiationId`, `serverTime` set. |
| A2 | Buyer 1 offers 4000 (not accepted). `status $LISTING "$H1"`. | `PENDING` with `negotiationId`; no `agreedPrice` or `validUntil`. This is the state the cart shows as "Waiting for seller to accept your offer". |
| A3 | The seller accepts. `status $LISTING "$H1"`. | `ACCEPTED`, `source = OFFER`, `agreedPrice = 4000`, `validUntil` about 24 hours ahead, `negotiationId`, `serverTime`. |
| A4 | The seller counters instead (new offer, counter 4200). | `PENDING` for the buyer (the buyer has to answer); still no price. |
| A5 | `status $LISTING` without the `Authorization` header. | 401. |
| A6 | `curl -s $B/listings/<random uuid>/price-agreement -H "$H1"`. | 200, `NONE` (no error for an unknown listing). |

## B. Taken by someone else (edge case "price accepted for another buyer")

| # | Steps | Expected |
|---|---|---|
| B1 | With buyer 1's price accepted, `status $LISTING "$H2"`. | `RESERVED`; no `agreedPrice`, no `validUntil`, no `negotiationId`: nothing about who holds it or at what price. |
| B2 | Buyer 1's lock ends (D1) or buyer 1 withdraws (`POST $B/negotiations/$NEG/cancel`). `status $LISTING "$H2"`. | No longer `RESERVED` (`NONE`, or `PENDING` if buyer 2 offers again). |

## C. A cart: several items at once (edge case "multiple items in cart")

| # | Steps | Expected |
|---|---|---|
| C1 | Buyer 1: price accepted on `LISTING`, an unanswered offer on `LISTING2`. `curl -s -X POST $B/price-agreements/status -H "$H1" -H "$J" -d '{"listingIds":["'$LISTING'","'$LISTING2'","'$(uuidgen)'"]}'` | 200, `data.items` has three entries in the order sent: `ACCEPTED` (with price and `validUntil`), `PENDING`, `NONE`; `serverTime` set. |
| C2 | Send the same id twice. | One entry for it (duplicates collapse). |
| C3 | The same request as buyer 3. | `LISTING` is `RESERVED` (no price), the others `NONE`. Nobody sees another buyer's data. |
| C4 | Send `{"listingIds":[]}`, 21 ids, and a body without `listingIds`. | 400 `VALIDATION_ERROR` each time. Exactly 20 ids: 200. |
| C5 | Send without the `Authorization` header. | 401. |
| C6 | Send the batch 121 times within a minute (or set `RATE_LIMIT_DETAILS_PER_MIN` low). | 429 `RATE_LIMIT_EXCEEDED` once the limit is passed; one call to `status $LISTING` counts in the same limit. The listing details page (section E) is not blocked by it. |

## D. Expiry judged by the clock (AC3, edge case "acceptance expires")

| # | Steps | Expected |
|---|---|---|
| D1 | Price accepted for buyer 1. `UPDATE price_agreements SET valid_until = now() - interval '1 second' WHERE listing_id = '<LISTING>';` and call `status $LISTING "$H1"` **before** the lock job runs (set `valuex.negotiation.job.expiry-interval-ms` high, or be quick). | `EXPIRED` at once, although the row is still `ACTIVE`. `status $LISTING "$H2"` is **not** `RESERVED` (a lock past its end holds nothing). |
| D2 | Wait for the lock job (US-080). | The agreement and the negotiation end as expired; `status` stays `EXPIRED` for buyer 1; both get `AGREEMENT_EXPIRED`. |
| D3 | Buyer 2 offers and the seller accepts (after D1 or D2). | Accepted (the stale lock never blocks a new accept); buyer 1 now sees `RESERVED`. |
| D4 | Buyer 1 offers again after D2. | `PENDING` (a new negotiation is newer than the old expired lock). |
| D5 | An offer nobody answered: `UPDATE negotiations SET expires_at = now() - interval '1 second' WHERE id = '<NEG>';` before the job runs. | `EXPIRED` for the buyer. |

## E. Listing page (K.4)

| # | Steps | Expected |
|---|---|---|
| E1 | `curl -s $B/listings/$LISTING/public -H "$H1"` with the price accepted. | `data.contact.agreement.status = ACCEPTED` with `agreedPrice`, `validUntil`, `serverTime`; `contact.negotiationId` as before. The app can show "Your offer was accepted: ₹4,000 until 9:40 am". |
| E2 | The same as buyer 3. | `agreement.status = RESERVED`, no price; `capabilities.offer.reason = RESERVED` as before. |
| E3 | The same as the seller (owner) and without any token. | `contact.agreement` is absent (null). |
| E4 | The same as a buyer who never negotiated. | `agreement.status = NONE`. |
| E5 | Call the listing page 130 times in a minute as buyer 1. | Never 429 (the page has its own limits; only the two status endpoints use `RATE_LIMIT_DETAILS_PER_MIN`). |

## F. Live update `agreement.updated` (real-time)

Open a WebSocket as buyer 1 as in the US-130 guide (ticket from `POST /api/v1/realtime/ticket`, then connect to `/ws/v1`).

| # | Steps | Expected |
|---|---|---|
| F1 | The seller accepts buyer 1's offer. | Buyer 1 receives `agreement.updated` with `listingId`, `negotiationId`, `kind = CREATED`, `status = ACCEPTED`, `validUntil`. No amount in the frame. The seller and buyer 2 receive none. |
| F2 | Buyer 1 cancels the negotiation. | `agreement.updated` with `kind = CANCELLED`, `status = NONE`. |
| F3 | The lock expires (D2). | Buyer 1 receives `negotiation.updated` (US-080) and the notification `AGREEMENT_EXPIRED`; there is **no** `agreement.updated` for expiry. The app should refresh the status on both events. |
| F4 | A checkout rolls back (see G3). | No `agreement.updated` (events are sent only after commit). |

## G. The guard (no endpoint yet: automated checks)

The rules of K.5, checked by the automated tests; run them as in the last section. Each row is a test:

| # | Case | Expected |
|---|---|---|
| G1 | The buyer never negotiated (direct call, "URL bypass"). | 403 `ERROR_UNAUTHORIZED_CHECKOUT`; nothing written. |
| G2 | Open offer not answered by the seller. | 409 `ERROR_PRICE_NOT_ACCEPTED`. |
| G3 | Accepted price, matching amount (`4000` and `4000.00` are equal). | Returns the agreement; `markConsumed` ends it as `CONSUMED` with `consumed_ref = order` and the negotiation as `NEGOTIATION_CONVERTED` (history `CONSUME_ACCEPTANCE`); repeating it for the same order changes nothing; inside a rolled back transaction nothing is stored. |
| G4 | The lock ran out and no job ran. | 409 `ERROR_ACCEPTANCE_EXPIRED`. |
| G5 | Another buyer holds the price. | 409 `ERROR_ITEM_RESERVED`. |
| G6 | The client sends another amount (or none). | 409 `ERROR_PRICE_CHANGED`. |
| G7 | A Buy Now row (inserted by hand) and the asking price changed; an agreement ended with reason `PRICE_CHANGED`. | 409 `ERROR_PRICE_CHANGED`. An offer agreement ignores later price edits. |
| G8 | A property, a listing no longer live. | 409 `ERROR_CHECKOUT_NOT_APPLICABLE` / `ERROR_ITEM_UNAVAILABLE`, before any agreement is looked at. |
| G9 | Two checkouts of one agreement at the same time. | Exactly one consumes it; the other gets 409 `ERROR_ITEM_RESERVED`. |
| G10 | The buyer withdraws while checkout runs. | No deadlock; both finish; afterwards 403 `ERROR_UNAUTHORIZED_CHECKOUT`. |
| G11 | Calling the guard outside a transaction. | `IllegalTransactionStateException` (it must run in the order transaction). |
| G12 | A second checkout after the first used the price. | 409 `ERROR_ITEM_RESERVED`. |

To try Buy Now rows by hand (US-068 does not exist yet):

```sql
INSERT INTO price_agreements (listing_id, buyer_id, seller_id, source, agreed_price, status, valid_until)
VALUES ('<LISTING>', '<BUYER1>', '<SELLER>', 'BUY_NOW', 4500.50, 'ACTIVE', now() + interval '15 minutes');
-- then change the asking price: UPDATE listings SET price = 4000 WHERE id = '<LISTING>';
-- the status endpoint still says ACCEPTED (price 4500.50); the guard now refuses with ERROR_PRICE_CHANGED (G7)
```

## H. Non-functional checks

| # | Steps | Expected |
|---|---|---|
| H1 | Look at the log and `GET /actuator/metrics/negotiation.checkout.refused` while running the guard tests. | Refusals are counted by code (`reason`); no amount, price or buyer name in any log line. |
| H2 | `EXPLAIN` of the batch queries on a database with many agreements. | Lookups by `listing_id`, `buyer_id` and the partial unique index; no sequential scan on a large table. |
| H3 | Run the status endpoints and the listing page while Redis is down. | They answer (the limit fails open and logs a warning). |

---

## How to run the automated tests

```bash
# backend (from valuex-backend; Java 21 and Docker running for the integration tests)
mvn test -Dtest='CheckoutPriceGuardServiceTest,PriceAgreementResolverTest,PriceAgreementStatusServiceTest,AgreementRealtimeListenerTest,PriceAgreementControllerTest,PriceAgreementServiceTest,NegotiationTransitionsTest,NegotiationAdaptersTest,PublicListingServiceTest,ContactEligibilityServiceTest'
mvn test -Dtest='PriceAgreementIntegrationTest,CheckoutPriceGuardIntegrationTest'
```

`PriceAgreementIntegrationTest` (13 tests) covers G1 to G7 and G9 to G12 and sections A to E on PostgreSQL, including
the two races; G8 and the realtime frames (section F) are covered by unit tests. **For Sprint 5:** extend `CheckoutPriceGuardContractTest` (package `com.valuex.negotiation.integration`),
implement `placeOrder` to call the real order creation, and keep its six cases green; `CheckoutPriceGuardIntegrationTest`
shows how.
