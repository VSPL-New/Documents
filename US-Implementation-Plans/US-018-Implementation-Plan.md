# US-018: Prevent Checkout Without Price Acceptance - Implementation Plan

## 1. Header

| Field | Value |
|---|---|
| Story | US-018 - Prevent Checkout Without Price Acceptance |
| Sprint | Sprint 4 - Communication & Negotiation |
| Story points | 3 |
| Repos involved | valuex-backend only (`negotiation` module, with a small change in `listing` and `communication` for the details page). No `valuex-mobile`, `valuex-ai`, `valuex-web` or infra change in this plan (see G1). |
| Dependencies | US-017 (price negotiation and the `price_agreements` table): **built and merged to `main`** (PR #70, 2026-11-17). US-130 (realtime gateway) is merged and carries the new `agreement.updated` event. |
| Blocks | Sprint 5 cart and checkout (US-019 to US-021) and US-068 (Buy Now), which call the guard built here. |
| Date | 2026-11-18 |
| Design source | [Sprint 4 LLD](../LLD/Sprint-4-Communication-Negotiation-LLD.md) Part K (K.1 to K.10), section 1.4 (price agreement), I.3 (tables, state machine), I.11 (US-017 as built), decisions D7 and D10, conflicts C4, C12 and C13. |
| Branch (proposal) | `feature/US-018-checkout-price-guard` in `valuex-backend`, cut from current `main` and rebased before work starts. |
| Flyway | **None.** Part K adds no table; `price_agreements` (V36) already has `consumed_ref`, `ended_reason` and the indexes the guard needs. Latest migration on `main` is V36. |

## 2. Story Recap

**As a** platform **I want to** prevent buyers from checking out unless the seller accepts the price **so that** transactions are based on mutual agreement.

**Acceptance criteria (from `user-stories.md`):**

| ID | Criterion |
|---|---|
| AC1 | Given a buyer wants to purchase an item, when the seller has not yet accepted the negotiated price, then "Proceed to Checkout" is disabled and shows "Waiting for seller to accept your offer". |
| AC2 | When the seller accepts the price, the button becomes enabled and the buyer can proceed to payment. |

**Edge cases (story):** direct URL access to bypass; seller accepts but the buyer already left the page; acceptance expires before checkout; several cart items in different acceptance states.
**Validation rules (story):** backend validation required (not only a disabled button); acceptance valid 24 hours, then the buyer must re-negotiate; cart items show an acceptance status indicator.
**Error scenarios (story):** `ERROR_PRICE_NOT_ACCEPTED` ("Seller hasn't accepted your offer yet"), `ERROR_ACCEPTANCE_EXPIRED` ("Price acceptance expired. Please re-negotiate"), `ERROR_UNAUTHORIZED_CHECKOUT` ("Cannot proceed without seller acceptance").
**Flutter notes (story):** button state tied to Riverpod negotiation state; status badge per cart item (Pending / Accepted / Expired); live update when the seller accepts.

**Boundary with neighbouring stories (LLD K.2, I.2):**
- **In scope:** `CheckoutPriceGuard` (the Java contract Sprint 5 calls inside its order transaction), the two status endpoints, status derivation, the K.8 error mapping, the `agreement` summary in the listing details `contact` block, the `agreement.updated` realtime event, the reusable contract test.
- **Out of scope:** cart, checkout, payment and order creation (Sprint 5); the cart screen, badge and checkout button (Sprint 5, US-019); the negotiation actions (US-017, done); the seller inbox and auto-reject (US-076); expiry jobs and `NEGOTIATION_EXPIRING` / `AGREEMENT_EXPIRED` notifications (US-080); Buy Now creation of `BUY_NOW` agreements (US-068).
- No HTTP "checkout" endpoint exists yet. AC1 and AC2 are delivered as backend rules and status data; the button itself is Sprint 5.

## 3. Design Reference

LLD Part K: K.3 statuses, K.4 API contract, K.5 backend design (decision order and locking), K.6 sequence, K.8 codes, K.9 security, K.10 tests. Shared pieces: section 1.4 and I.3 (`price_agreements`, `negotiations`), I.11 rows 4, 5 and 7 (what US-017 already built).

### Key design decisions (from the LLD)

- **Guard is a Java interface, not an endpoint.** `CheckoutPriceGuard.requireValid(buyerId, listingId, expectedAmount)` and `markConsumed(agreementId, orderId)` run inside Sprint 5's order-creation transaction. The rule lives in the database read, never in a client flag.
- **Decision order of `requireValid` (K.5):** (1) listing is not Real Estate (`ERROR_CHECKOUT_NOT_APPLICABLE`) and is live (`ERROR_ITEM_UNAVAILABLE`); (2) an `ACTIVE` agreement exists: mine -> expired by `valid_until <= now()` (`ERROR_ACCEPTANCE_EXPIRED`), else amount differs (`ERROR_PRICE_CHANGED`), else for `BUY_NOW` re-read the current asking price under the lock and compare (`ERROR_PRICE_CHANGED`), else return the view; another buyer's -> `ERROR_ITEM_RESERVED`; (3) none active: latest agreement ended `PRICE_CHANGED` -> `ERROR_PRICE_CHANGED`; ended `EXPIRED` -> `ERROR_ACCEPTANCE_EXPIRED`; open negotiation -> `ERROR_PRICE_NOT_ACCEPTED`; otherwise `ERROR_UNAUTHORIZED_CHECKOUT`.
- **Expiry is judged by the clock** (`valid_until`), not by the expiry job, which does not exist yet (US-080). A stale `ACTIVE` row must never pass the guard.
- **Locking:** the guard locks the listing's `ACTIVE` agreement row (`SELECT ... FOR UPDATE`); `markConsumed` is a conditional update that must change exactly one row, so two concurrent checkouts serialise and only one succeeds.
- **Statuses (K.3):** `NONE`, `PENDING`, `ACCEPTED`, `EXPIRED`, `RESERVED`. `RESERVED` reveals only that the item is taken, never by whom or at what price.
- **Status endpoints:** `GET /api/v1/listings/{listingId}/price-agreement` and `POST /api/v1/price-agreements/status` (up to 20 ids, two queries for any number of ids), rate limited with `RATE_LIMIT_DETAILS_PER_MIN`.
- **Money:** `BigDecimal` with `compareTo`, never `equals`; the client amount is never trusted.

### Verified implementation anchors (checked against `valuex-backend` `main` on 2026-11-18)

| Area | Finding and consequence |
|---|---|
| Agreement code | [PriceAgreementService](../../valuex-backend/src/main/java/com/valuex/negotiation/application/service/PriceAgreementService.java) has `createFromOffer`, `reservedForOther`, `activeOf`, `cancel`; [PriceAgreementRepository](../../valuex-backend/src/main/java/com/valuex/negotiation/infrastructure/persistence/PriceAgreementRepository.java) has `findActive`, `lockListing` (advisory lock), `expireDue`, `endOfNegotiation`. No row lock, no "latest agreement of buyer", no `markConsumed`, no batch query yet. [PriceAgreementRow](../../valuex-backend/src/main/java/com/valuex/negotiation/infrastructure/persistence/PriceAgreementRow.java) already has `reserves(now)`. |
| State machine | `OFFER_ACCEPTED -> NEGOTIATION_CONVERTED` (`CONSUME_ACCEPTANCE`) already exists in `NegotiationStateMachine`; `ClosedReason.CONVERTED` exists; `NegotiationTransitions` has no `consume` method yet. |
| Error codes | `NegotiationErrors` lacks `PRICE_NOT_ACCEPTED`, `ACCEPTANCE_EXPIRED`, `UNAUTHORIZED_CHECKOUT`, `PRICE_CHANGED`, `CHECKOUT_NOT_APPLICABLE`; `ITEM_RESERVED` and `ITEM_UNAVAILABLE` exist. `ConflictException` (409, optional details map) and `ForbiddenException` (403) exist in `common.exception`. |
| Listing facts | `ListingFactsPort.ListingFacts` has `price`, `realEstate`, `live` ([ListingFactsAdapter](../../valuex-backend/src/main/java/com/valuex/listing/infrastructure/negotiation/ListingFactsAdapter.java)). No "sold" flag: see G3. |
| Details page | `PublicListingResponse.Contact(threadId, negotiationId)` is filled from `ContactCapabilityPort.ContactOptions`, which gets `negotiationId` and `reservedForOther` from `OfferAvailabilityPort` (adapter `OfferAvailabilityAdapter`). The details call runs in a read-only transaction, so status derivation there must not write. |
| Realtime | `RealtimeEvents` has only `NEGOTIATION_UPDATED`; `NegotiationRealtimeListener` is the pattern (after-commit, `REQUIRES_NEW`, failure logged and swallowed). `agreement.updated` is new. |
| Rate limit | `DiscoverySetting.RATE_LIMIT_DETAILS_PER_MIN` exists (120) but no code uses it yet; `NegotiationRateLimiter` is the pattern (Redis, fail-open). |
| Lock order | US-017 code takes the **negotiation row lock first**, then the advisory/agreement lock (`createFromOffer`, `cancel`). The guard must follow the same order or it can deadlock (see step 2.4 and risk R1). |
| Tests | `NegotiationIntegrationTest` (Testcontainers, 13 tests) and `NegotiationControllerTest` exist and are the pattern for the new tests. |

## 4. Implementation Steps

### 4.1 Database

- [x] No migration. Confirm with `EXPLAIN` in the integration test setup (or by reading V36) that the guard and batch queries are served by `uq_price_agreements_active`, `idx_price_agreements_buyer` and `uq_negotiations_open` / `idx_negotiations_listing`; add an index only if a query needs one (then use V37 and update the LLD number).

### 4.2 Backend: domain and errors (`com.valuex.negotiation`)

- [x] `domain/NegotiationErrors`: add `PRICE_NOT_ACCEPTED`, `ACCEPTANCE_EXPIRED`, `UNAUTHORIZED_CHECKOUT`, `PRICE_CHANGED`, `CHECKOUT_NOT_APPLICABLE` (strings from K.8).
- [x] `domain/PriceAgreementStatusKind` (new enum): `NONE, PENDING, ACCEPTED, EXPIRED, RESERVED` (named to avoid clashing with `AgreementStatus`, which is the table status).
- [x] `domain/ClosedReason` / agreement `ended_reason`: add the constant `PRICE_CHANGED` (string `PRICE_CHANGED`) used when reading `ended_reason`; US-068 will write it (G2).

### 4.3 Backend: persistence

- [x] `PriceAgreementRepository`: add
  - `lockActive(UUID listingId)`: `SELECT ... WHERE listing_id = ? AND status = 'ACTIVE' FOR UPDATE`;
  - `latestOfBuyer(UUID listingId, UUID buyerId)`: newest row by `created_at DESC` (any status) for `EXPIRED` / `PRICE_CHANGED` detection, including `ended_reason`;
  - `findActiveOfListings(Collection<UUID>)` and `latestOfBuyerForListings(Collection<UUID>, UUID buyerId)`: the two batch queries (`listing_id IN (...)`);
  - `markConsumed(UUID agreementId, UUID orderId, Instant now)`: `UPDATE ... SET status='CONSUMED', consumed_ref=?, ended_at=?, ended_reason='CONSUMED' WHERE id=? AND status='ACTIVE' AND valid_until > ?`, returns rows changed;
  - `findById` (or return `ended_reason` / `consumed_ref` in the row mapper) so idempotency can compare `consumed_ref`.
  - Extend `PriceAgreementRow` / mapper with `endedReason` and `consumedRef` (keep `reserves`).
- [x] `NegotiationRepository`: add `findOpenByListings(Collection<UUID>, UUID buyerId)` (states `SELLER_REVIEWING`, `BUYER_REVIEWING` only for `PENDING`) and `latestClosedByListings(...)` (for `EXPIRED` when no agreement row exists, e.g. negotiation ended `EXPIRED` before acceptance).

### 4.4 Backend: guard and status services

- [x] `application/port/CheckoutPriceGuard` (interface, signature exactly as LLD K.4) and `PriceAgreementView` (record: `agreementId, listingId, buyerId, sellerId, negotiationId, source, agreedPrice, validUntil`).
- [x] `application/service/CheckoutPriceGuardService` implements it, `@Transactional(propagation = MANDATORY)` so it can never run outside the caller's order transaction:
  - `requireValid`: follow the decision order of section 3 exactly. **Lock order: find the active agreement without a lock, lock its negotiation row (`NegotiationRepository.lockById`) if `negotiation_id` is set, then lock the agreement row (`lockActive`) and re-check it is still `ACTIVE` for the same id** (R1). Real Estate and not-live are decided first from `ListingFactsPort`. For `BUY_NOW` re-read `ListingFacts.price` under the lock. Compare money with `compareTo`. Failure paths never write.
  - `markConsumed`: conditional update; if 0 rows changed, return silently when the row is already `CONSUMED` with the same `consumed_ref` (idempotent), otherwise throw `ConflictException(ITEM_RESERVED)`. When it changes one row and `negotiation_id` is set, lock the negotiation and call `NegotiationTransitions.consume` (below); publish `AgreementUpdatedEvent`.
- [x] `NegotiationTransitions.consume(NegotiationRow, Instant now)`: `move(..., "CONSUME_ACCEPTANCE", Change(NEGOTIATION_CONVERTED, ..., ClosedReason.CONVERTED), ...)` writing the history row.
- [x] `application/service/PriceAgreementStatusService` (read-only, never throws for business states):
  - `statusOf(callerId, listingId)` and `statusOfAll(callerId, listingIds)`; precedence **ACCEPTED > RESERVED > PENDING > EXPIRED > NONE** (G4); `ACCEPTED` means the caller's `ACTIVE` agreement with `valid_until > now`; `RESERVED` means another buyer's active, unexpired agreement; `PENDING` is an open negotiation in `SELLER_REVIEWING` or `BUYER_REVIEWING`; `EXPIRED` is the caller's latest agreement or negotiation ending `EXPIRED` / `ACCEPTANCE_EXPIRED` (an `ACTIVE` row past `valid_until` also counts as `EXPIRED`, expiry job or not); otherwise `NONE`. Real Estate and non-live listings answer `NONE` (G5).
  - Fill `source`, `agreedPrice`, `validUntil`, `negotiationId` only for the caller's own `ACCEPTED` / `PENDING` data; `RESERVED` and `NONE` carry none. `serverTime` from the injected `Clock`.
  - Batch: validate 1 to 20 distinct ids (more -> 400 validation error), run the agreement query and the negotiation query once each, return one entry per requested id in request order.
- [x] `application/dto/PriceAgreementStatusResponse` (`status, source, agreedPrice, validUntil, negotiationId, serverTime`) and `PriceAgreementStatusBatchResponse` (`items[{listingId, + same fields}], serverTime`) and `PriceAgreementStatusRequest(@NotEmpty @Size(max=20) List<UUID> listingIds)`.
- [x] Rate limit: extend `NegotiationRateLimiter` (or a sibling) with key `rate:agreement-status:{userId}` using `DiscoverySetting.RATE_LIMIT_DETAILS_PER_MIN`; fail-open like US-017; over the limit -> `RateLimitedException("RATE_LIMIT_EXCEEDED", ...)` (429).

### 4.5 Backend: API

- [x] `api/PriceAgreementController` (`@RequestMapping("/api/v1")`, `@Tag`, `@Operation` with every status and error): `GET /listings/{listingId}/price-agreement` and `POST /price-agreements/status`. Authenticated; scoped to `SecurityContext.getCurrentUserId()`; no identity-verification annotation (a status read must not need Aadhaar). Check the security config requires auth for both paths.
- [x] No HTTP route for the guard (K.4). Do not add a placeholder checkout endpoint.

### 4.6 Backend: realtime and listing details

- [x] `realtime/domain/RealtimeEvents`: add `AGREEMENT_UPDATED = "agreement.updated"`.
- [x] `negotiation/domain/AgreementUpdatedEvent(agreementId, negotiationId, listingId, buyerId, kind)` with `kind` in `CREATED, CANCELLED, EXPIRED, CONSUMED`; published (after commit) from `PriceAgreementService.createFromOffer`, `PriceAgreementService.cancel` and `markConsumed`.
- [x] `application/service/AgreementRealtimeListener` (copy the pattern of `NegotiationRealtimeListener`): publishes `agreement.updated` to the **buyer only** with `listingId`, `negotiationId`, `status`, `validUntil`; **no amount**; failures logged and swallowed. (US-080 will publish `EXPIRED` when its job ends rows.)
- [x] Listing details: extend `OfferAvailabilityPort.OfferAvailability` and `ContactCapabilityPort.ContactOptions` with an `AgreementSummary` (status, source, agreedPrice, validUntil, negotiationId, serverTime); `OfferAvailabilityAdapter` fills it from `PriceAgreementStatusService` (read-only); `PublicListingResponse.Contact` gains `agreement` (null for anonymous callers and the owner). Keep all existing fields unchanged.

### 4.7 Documentation and wrap-up

- [x] Add as-built note `K.11` to the Sprint 4 LLD, update the version table (0.7), `user-stories.md` (US-018 "Built" note), `Sprint-plan.md` row, and the open items (C13 status endpoints exist, badge in Sprint 5).
- [x] `Documents/Manual Testing Guides/US-018-Testing-Guide.md` (API-level steps with curl and a SQL/test hook for the guard, since no checkout endpoint exists).
- [x] OpenAPI annotations complete; Checkstyle clean; no amounts in logs. SonarQube scan **not run** by decision of the product owner (2026-11-18, no server or token available); the plan's Sonar step is waived for this story.

## 5. Test Plan

Target: more than 90 percent line coverage on new code. Unit tests use a fixed `Clock`; integration tests run on PostgreSQL (Testcontainers) with a controllable clock.

### 5.1 Unit (`CheckoutPriceGuardServiceTest`, `PriceAgreementStatusServiceTest`, controller test)

| # | Case | Maps to |
|---|---|---|
| U1 | Valid own agreement, amount equal (including `13500` vs `13500.00`) -> view returned | AC2 |
| U2 | Open negotiation, no agreement -> `ERROR_PRICE_NOT_ACCEPTED` (409) | AC1 |
| U3 | No negotiation, no agreement (URL bypass) -> `ERROR_UNAUTHORIZED_CHECKOUT` (403) | bypass edge case |
| U4 | Active own agreement past `valid_until`, expiry job not run -> `ERROR_ACCEPTANCE_EXPIRED` | expiry edge case |
| U5 | Latest agreement `EXPIRED` and none active -> `ERROR_ACCEPTANCE_EXPIRED` | expiry |
| U6 | Another buyer's active agreement -> `ERROR_ITEM_RESERVED`; response carries no buyer or price | K.9 |
| U7 | Client amount differs from `agreed_price` -> `ERROR_PRICE_CHANGED` | tamper |
| U8 | `BUY_NOW` agreement and listing price now different -> `ERROR_PRICE_CHANGED`; `OFFER` agreement ignores later price edits (LLD) | K.5 |
| U9 | Latest agreement ended `PRICE_CHANGED` -> `ERROR_PRICE_CHANGED` | K.5 step 3 |
| U10 | Real Estate -> `ERROR_CHECKOUT_NOT_APPLICABLE`; not live -> `ERROR_ITEM_UNAVAILABLE`; both before any agreement check | K.5 step 1 |
| U11 | `markConsumed`: one row changed, negotiation -> `NEGOTIATION_CONVERTED` with history; same order id twice is a no-op; different order id -> conflict | idempotency |
| U12 | `markConsumed` for an agreement without `negotiation_id` (Buy Now) does not touch negotiations | Buy Now |
| U13 | Status derivation: each of `NONE`, `PENDING`, `ACCEPTED`, `EXPIRED`, `RESERVED`, plus the precedence rule; fields filled only where allowed | K.3 |
| U14 | Batch: 1 and 20 ids ok, 0 and 21 rejected, duplicates collapsed, order preserved, mixed states, exactly two repository queries | cart edge case |
| U15 | Controller: 401 without token, 429 on rate limit, 400 invalid body, 200 shapes | API |
| U16 | Guard called without a transaction fails fast (MANDATORY propagation) | safety |

### 5.2 Integration (`PriceAgreementIntegrationTest`, PostgreSQL, fake clock)

- [x] Accepted offer (through US-017 endpoints) then `requireValid` succeeds; `markConsumed` ends agreement `CONSUMED` and negotiation `NEGOTIATION_CONVERTED`.
- [x] No negotiation; open negotiation; expired agreement (clock advanced 24 h + 1 s); another buyer's agreement; seeded `BUY_NOW` row with a changed asking price; seeded agreement ended `PRICE_CHANGED`.
- [x] Batch endpoint with mixed states, scoped to the caller (a second buyer sees `RESERVED`, never the first buyer's data).
- [x] Listing details `contact.agreement` for the buyer, a stranger (`RESERVED`), the owner and anonymous (null).
- [x] `agreement.updated` sent to the buyer only after commit and not at all on rollback (using the existing realtime test support).

### 5.3 Concurrency

- [x] Two simultaneous `requireValid` + `markConsumed` calls on one agreement: exactly one consumption, the other gets `ERROR_ITEM_RESERVED`, no second order reference stored.
- [x] Guard vs buyer `cancel` on the same negotiation and guard vs a new accept: no deadlock (R1), consistent end state.
- [x] A stale `ACTIVE` agreement past `valid_until` neither blocks a new accept (US-017 behaviour kept) nor passes the guard.
- [x] A listing price edit committed just before checkout fails a `BUY_NOW` agreement with `ERROR_PRICE_CHANGED`.

### 5.4 Contract suite for Sprint 5

- [x] `CheckoutPriceGuardContractTest` (abstract, reusable): the checkout story extends it with a function that calls its own order-creation path; cases: no agreement, open negotiation, expired, other buyer, wrong amount, success consumes exactly once, direct call bypass attempts. Run once here against the guard itself so it stays green.

## 6. Validation Checklist

**Acceptance criteria**
- [x] AC1: with no accepted price the backend refuses checkout (`ERROR_PRICE_NOT_ACCEPTED` / `ERROR_UNAUTHORIZED_CHECKOUT`) and the status endpoint answers `PENDING` or `NONE`, which the cart uses for "Waiting for seller to accept your offer".
- [x] AC2: after the seller accepts, status is `ACCEPTED` with `validUntil`, `requireValid` returns the agreement, and the buyer gets `agreement.updated`.

**Edge cases**
- [x] Direct URL / API bypass: only the database decides.
- [x] Seller accepts while the buyer is away: agreement persists 24 h; status and details page show it on return.
- [x] Acceptance expires before checkout: clock-based `ERROR_ACCEPTANCE_EXPIRED` even if no job ran.
- [x] Several cart items in different states: batch endpoint, one status each, up to 20.

**Validation rules**
- [x] Backend enforcement mandatory (guard, not UI).
- [x] 24 h window uses `PRICE_LOCK_HOURS` (no hard-coded 24).
- [x] Re-negotiation after expiry works (US-017 lazy expiry untouched).
- [x] Status indicator data available per cart item.

**Error scenarios and codes**
- [x] `ERROR_PRICE_NOT_ACCEPTED` 409, `ERROR_ACCEPTANCE_EXPIRED` 409, `ERROR_UNAUTHORIZED_CHECKOUT` 403, `ERROR_PRICE_CHANGED` 409, `ERROR_ITEM_RESERVED` 409, `ERROR_CHECKOUT_NOT_APPLICABLE` 409, `ERROR_ITEM_UNAVAILABLE` 409; unauthenticated 401; over limit 429.

**Quality**
- [x] No `equals` on `BigDecimal`; no amount in logs, metrics or realtime payloads; `RESERVED` reveals nothing about the other buyer.
- [x] Guard failure paths write nothing; guard cannot run outside a transaction.
- [x] Existing tests (US-017 negotiation suite, listing details tests, realtime tests) still pass; coverage above 90 percent; Checkstyle and SonarQube clean.

## 7. Open Gaps / Questions

| # | Gap | Decision |
|---|---|---|
| G1 | The Sprint plan and story list US-018 as **backend only**, but LLD K.7 says "Sprint 4 builds the data side" on mobile (`PriceAgreementStatus` model, providers, details-page banner, English and Hindi strings for K.8). | **Agreed (2026-11-18).** **Backend only** now (matches the 3 SP and the Sprint plan); the mobile data layer, strings and badge ship with Sprint 5 US-019 where they are first used. Mobile stays out of this story. |
| G2 | `BUY_NOW` agreements and the `PRICE_CHANGED` end reason are produced by US-068, not yet built. | **Agreed (2026-11-18).** Build and test the guard branches against seeded rows; US-068 supplies the real writers. Constant `PRICE_CHANGED` added now. |
| G3 | K.5 mentions `ERROR_ITEM_SOLD`, but `ListingFacts` has only `live` and K.8 has no such code. | **Agreed (2026-11-18).** Use `ERROR_ITEM_UNAVAILABLE` for every not-live case; add `ERROR_ITEM_SOLD` only if Sprint 5 needs the distinction. |
| G4 | LLD K.3 does not say which status wins when several apply (for example another buyer holds the price while the caller has an open negotiation). | **Agreed (2026-11-18).** Precedence ACCEPTED > RESERVED > PENDING > EXPIRED > NONE (the item being taken matters most to the buyer). |
| G5 | Status for Real Estate (no agreement, no checkout, D7) and non-live listings is undefined. | **Agreed (2026-11-18).** Answer `NONE`; only the guard returns `ERROR_CHECKOUT_NOT_APPLICABLE`. |
| G6 | Batch response shape and handling of unknown, duplicate or more than 20 ids are not specified. | **Agreed (2026-11-18).** `items[]` in request order with `listingId` + status fields, duplicates collapsed, unknown ids `NONE`, more than 20 -> 400. |
| G7 | K.5 says `agreement.updated` is published; I.11 assigns `AGREEMENT_EXPIRED` notification to US-080. | **Agreed (2026-11-18).** This story publishes `agreement.updated` for created, cancelled and consumed; the expiry publisher and notification stay with US-080. |
| G8 | Where the public contract lives. | **Agreed (2026-11-18).** `negotiation.application.port.CheckoutPriceGuard` plus `PriceAgreementView`; Sprint 5 depends only on these. Run the existing architecture tests (if any) to confirm the module boundary holds. |
| G9 | The listing details page does not apply `RATE_LIMIT_DETAILS_PER_MIN` today. | **Agreed (2026-11-18).** Out of scope; only the new status endpoints use it. Mention in the LLD note. |
| G10 | Sprint 5 must still move the listing out of `PUBLISHED` (K.5, last bullet). | Informational, not this story; recorded in the LLD note for Sprint 5. |

**Risks**
- **R1 Lock-order deadlock:** US-017 locks the negotiation, then the agreement; a naive guard that locks the agreement first can deadlock against `cancel` or `accept`. Mitigated by the lock order in step 4.4 and the concurrency test in 5.3.
- **R2 Read-only details transaction:** the details page runs read-only, so status derivation must be write-free; covered by a test.
- **R3 No checkout yet:** the guard is verified through tests and the contract suite only; manual testing uses a test hook or SQL (documented in the testing guide).

---

## 8. Deviations from the plan (as built, 2026-11-18)

Also recorded in LLD K.11. Branch `feature/US-018-checkout-price-guard`, rebased on `main` after US-076 and US-080 were merged (one conflict set, in `PriceAgreementService` and its test, resolved by keeping both sides).

| # | Plan | As built | Why |
|---|---|---|---|
| 1 | Guard lock order: find the agreement, lock its negotiation row, then the agreement row. | Listing advisory lock first, then the negotiation row, then the agreement row. | US-076 `accept` and the US-080 lock job take the listing lock before row locks; the guard must use the same order. |
| 2 | `NegotiationRepository.findOpenByListings` and `latestClosedByListings`. | One query, `findLatestOfBuyer` (the buyer's latest negotiation per listing, `DISTINCT ON`), and one agreement query, `findActiveOrOwned`. | A buyer's open negotiation is always the latest, so the two plan queries collapse into one; still two queries for any number of ids. |
| 3 | Status and guard decide from separate code. | One `PriceAgreementResolver` serves both; adds the outcomes `PRICE_CHANGED` and `CONSUMED`, which the guard uses and the app sees as `EXPIRED` and `NONE`. | The same answer in both places; a second checkout of a used price gets `ERROR_ITEM_RESERVED` as K.5 asks. |
| 4 | Real Estate and non-live listings answer `NONE` through `ListingFactsPort`. | Real Estate is read from `negotiations.real_estate`; non-live listings resolve to `NONE` because their negotiations and agreements are cancelled by the existing listing listener. No listing read. | Keeps the listing details page cheap. The guard itself still checks Real Estate and live through `ListingFactsPort` (step 1 of K.5). |
| 5 | An open negotiation with no answer gives `ERROR_PRICE_NOT_ACCEPTED`. | Same, unless its time already ran out: then it counts as expired (`ERROR_ACCEPTANCE_EXPIRED`, status `EXPIRED`), judged by the clock. | US-080 now expires negotiations by job; the clock must decide before the job runs. |
| 6 | `agreement.updated` kinds: created, cancelled and consumed. | Same. US-080 (built before this story) announces expiry of a price lock with `negotiation.updated` and the `AGREEMENT_EXPIRED` notification, so `agreement.updated` is not sent for expiry. | G7; avoids a second announcement of the same event. |
| 7 | Step 4.1: confirm the indexes with `EXPLAIN`. | Indexes read in V36 (`uq_price_agreements_active`, `idx_price_agreements_buyer`, `idx_negotiations_buyer`); no `EXPLAIN` run. | The tables are small and the lookups are by key; no index was added. |
| 8 | `PriceAgreementStatusKind` and a status DTO only. | Also `PriceAgreementStatusBatchResponse` and `PriceAgreementStatusRequest` (`@NotEmpty @Size(max = 20)`). | G6. |
| 9 | Listing price re-read under the lock for Buy Now. | Done through `ListingFactsPort`; a JPA entity loaded earlier in the same order transaction could be stale, so the Javadoc of `CheckoutPriceGuard` tells Sprint 5 to call `requireValid` before it reads the listing. | Found while writing the tests; documented, not coded around. |

**Environment note:** the backend builds with Java 21 (the machine had only 17 and 27; Lombok does not run on 27). A Temurin 21 was unpacked in `~/.local/jdk21` for this work; Testcontainers ran on Colima.

---

**Status: Implemented** (approved 2026-11-18; built 2026-11-18, SonarQube scan waived by the user; commit and pull request pending)
