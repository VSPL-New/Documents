# US-017: Price Negotiation - Implementation Plan

## 1. Header

| Field | Value |
|---|---|
| Story | US-017 - Price Negotiation |
| Sprint | Sprint 4 - Communication & Negotiation |
| Story points | 8 |
| Repos involved | valuex-backend (negotiation module, price agreement table and service, listing and account event listeners, notifications, chat cards) and valuex-mobile (`features/negotiation`, Make Offer sheet, negotiation screen, listing and chat integration). No `valuex-ai`, `valuex-web` or infra change. |
| Dependencies | US-013 (chat; built and merged to `main` on 2026-11-17 with US-069), US-069 (contact guard and capabilities), US-132 (blocks). US-130 (realtime gateway; merged to `main`, confirmed by the user 2026-11-17) provides the event channel (G2). US-017 blocks US-076, US-018, US-080 and US-068. |
| Date | 2026-11-17 |
| Design source | [Sprint 4 LLD](../LLD/Sprint-4-Communication-Negotiation-LLD.md) Part I (I.1 to I.10), section 1.4 (conversation thread, system message, price agreement, capability), 1.6 (`NegotiationSetting`), 1.7 (migrations), decisions D6 to D10, D16, D18, D20 and conflict C17. As-built notes D.11 and E.11 for what US-069 and US-013 already provide. |
| Branches (proposal) | `feature/US-017-price-negotiation` in `valuex-backend` and `valuex-mobile`, cut from current `main` and rebased before work starts (CLAUDE.md rule 5.1). |
| Flyway number | The LLD says V37 (provisional). `main` is at V35 (`V35__realtime_settings.sql` from US-130), so use the next free number when the branch is cut and update the LLD (as in Sprint 3). |

## 2. Story Recap

**As a** buyer **I want to** negotiate the price with the seller **So that** I can get a better deal.

> Update (2026-10-25, category taxonomy): applies to Real Estate listings against the normalised listing price; the property flow ends after negotiation, with no checkout (US-118).

**Acceptance criteria (from `user-stories.md`):**

| ID | Criterion |
|---|---|
| AC1 | Given I am viewing a listing, when I tap "Make Offer", I can enter my proposed price. |
| AC2 | When I submit the offer, the seller receives a notification. |
| AC3 | When the seller accepts, counters or rejects, I receive a notification. |
| AC4 | When the seller accepts my offer, the accepted price is locked and I can proceed to checkout. |
| AC5 | When the seller counters, I can accept, counter again or decline. |

**Edge cases (story):** absurdly low offer (for example 90 percent off); several buyers negotiating at once; seller changes mind after accepting; negotiation inactive for days; buyer makes an offer then ghosts.
**Validation rules (story):** offer greater than 0 and at most the listed price; at most 5 back-and-forth negotiations per buyer-seller pair; auto-expiry after 48 hours of inactivity; accepted price cannot change unless both parties agree; all negotiation activity is logged.
**Error scenarios (story):** `ERROR_INVALID_OFFER` ("Offer must be between ₹1 and ₹[listed_price]"), `ERROR_MAX_NEGOTIATIONS`, `ERROR_NEGOTIATION_EXPIRED`, `WARNING_LOW_OFFER`.

**Boundary with neighbouring stories (LLD I.2):** US-017 owns the negotiation, offer, history and agreement tables, the create, accept, reject, counter, cancel and read endpoints, the rules, the listing and account reactions, notifications and chat cards, and the buyer mobile screens. It does not own the seller's offers inbox, the exclusivity auto-reject of other offers and the seller screens (US-076), the checkout guard (US-018), the expiry jobs (US-080) or Buy Now (US-068).

## 3. Design Reference

LLD Part I: I.3 data model and state machine, I.4 API contract, I.5 backend design (rules, `createOffer`, `respond`, `cancel`, listing and account listener, notifications), I.6 sequence, I.7 mobile, I.8 codes, I.9 security, I.10 tests. Shared pieces: section 1.4 (thread, system message, price agreement, capability), 1.6 (`NegotiationSetting`), D.11 and E.11 (as-built).

### Key design decisions

- **Per pair negotiations, listing stays live (D6).** Each buyer negotiates on their own row; exclusivity exists only through `price_agreements` (one `ACTIVE` row per listing, partial unique index).
- **Four tables:** `negotiations` (partial unique index: one open negotiation per buyer and listing), `offers` (`round_no`, idempotency by `client_request_id`), `negotiation_status_history`, `price_agreements`; money is `NUMERIC(12,2)` and `BigDecimal`.
- **State machine reuse (C17).** `NegotiationState` and `NegotiationStateMachine` exist; add `BUYER_REVIEWING -> CANCELLED`, `OFFER_ACCEPTED -> EXPIRED` (`EXPIRE_ACCEPTANCE`), `OFFER_ACCEPTED -> CANCELLED` and a new state `NEGOTIATION_CONVERTED` (`CONSUME_ACCEPTANCE`). `BUYER_OFFER_SENT` and `SELLER_COUNTERED` are transient; every transition writes a history row.
- **Rules (`OfferRulesService`).** First offer more than 0 and not above the asking price; seller counter above the buyer's last offer and not above the asking price; buyer counter not below the buyer's previous offer and below the seller's last counter; every submitted price is one round, capped by `NEGOTIATION_MAX_ROUNDS` (5); after the cap only accept or reject remain (D8). Offers below `NEGOTIATION_LOW_OFFER_PERCENT` (50) need `confirmLowOffer = true`.
- **Accept** sets `agreed_price = MIN(offer, current asking price)`; for goods creates a `price_agreements` row valid `PRICE_LOCK_HOURS` (24); Real Estate creates none (D7). The seller cannot reverse an accepted price; the buyer can cancel (D20).
- **Concurrency:** row lock on the negotiation (`FOR UPDATE`) plus a `version` column; `pg_advisory_xact_lock` on the listing for agreements.
- **Chat integration (D16):** a negotiation belongs to the buyer-seller thread (found or created); each event posts an `OFFER_EVENT` system message card.
- **Privacy (D18):** push text is generic; amounts never appear in logs, metrics, push text or shared listing fields.

### Verified implementation anchors (checked against `origin/main` on 2026-11-17)

| Area | Finding and consequence |
|---|---|
| State machine | `negotiation/domain/NegotiationState` has `NEGOTIATION_STARTED`, `BUYER_OFFER_SENT`, `SELLER_REVIEWING`, `SELLER_COUNTERED`, `BUYER_REVIEWING`, `OFFER_ACCEPTED`, `OFFER_REJECTED`, `NEGOTIATION_EXPIRED`, `NEGOTIATION_CANCELLED`; `NegotiationStateMachine` exists; the `negotiation` package otherwise holds only `package-info.java`. `NEGOTIATION_CONVERTED` and three transitions are new. |
| Contact guard | `communication/application/service/ContactGuard` has `require(channel, callerId, listingId)` and `requireNewThread`; `ContactChannel` already has `OFFER`. It checks account, own listing, block, seller state and the per-pair hourly limit and logs every attempt (D.11 row 6). |
| Chat thread | `ChatThreadService.open(callerId, listingId)` finds or creates the thread; `ChatMessageStore.postSystemMessage(threadId, type, payload, ...)` and `ChatMessageType.OFFER_EVENT` already exist (V34 allows `OFFER_EVENT`). Mobile `system_card.dart` shows "Conversation update" for offer cards today (E.11 row 12). |
| Capability | `ContactEligibilityService` returns `offer` as `COMING_SOON` until US-017 (D.11 row 4) and already serves `NOT_NEGOTIABLE` and `IDENTITY_REQUIRED`; `PublicListingResponse` has `negotiable` and the `contact` block with `negotiationId` always null. This story turns `offer` on and fills `negotiationId`. |
| Listing facts | `ContactListingPort` returns `title`, `price`, `live`, `closedByAdmin` only. Offers also need `negotiable`, price qualifier, `realEstate` and the thumbnail (LLD names a `ListingContextPort` for this) (G3). |
| Listing and account events | `listing/domain/ListingStatusChangedEvent` (`listingId`, `fromState`, `toState`, `action`) and `ListingDeletedEvent`, and `auth/domain/UserStateChangedEvent` exist for the cancellation listener. |
| Aadhaar gating | `auth/security/RequiresIdentityVerification` exists; `ParticipantDirectoryPort.isIdentityVerified` was added in US-013. |
| Settings | `PlatformSettingsService` exposes `discovery()` and `communication()`; `NegotiationSetting` and `negotiation()` do not exist yet. This story creates them (LLD 1.6), with only the keys it needs (G4). |
| Notifications | `NotificationDispatcher` with `NotificationDispatchRequest` (`eventType`, `params`, `dedupeKey`, channels); `ChatMessageListener` is the pattern for an `AFTER_COMMIT` listener that never fails the caller. |
| Realtime | `negotiation.updated` and `badge.updated` are defined by US-130 (A.4.3). US-130 is on `main`: backend `realtime/application/RealtimePublisher.publishToUser(userId, type, data)` (already used by `communication/.../ChatRealtimeListener` after commit) and mobile `core/realtime` (`realtime_client`, `realtime_providers`), with `chat_polling.dart` as the polling-fallback pattern (G2). |
| Mobile | `features/chat` (thread screen, `system_card.dart`) and `features/listing_view` (`listing_actions.dart`, where Make an Offer is a disabled "preview" control driven by `capabilities.offer`) exist; `features/negotiation` does not. Strings are in `app_en.arb` and `app_hi.arb`; routes in `core/routing`. |

## 4. Implementation Steps

### Database
- [ ] Migration `V<next>__negotiation_and_price_agreements.sql`: `negotiations` (CHECKs, `uq_negotiations_open`, four indexes, `version`), `offers` (`uq_offers_round`, `uq_offers_client`, amount CHECK), `negotiation_status_history` (index), `price_agreements` (source and price CHECKs, `uq_price_agreements_active`, buyer and expiry indexes), exactly as LLD I.3. Add the `NEGOTIATION_CONVERTED` state to the state values.
- [ ] Seed the `NegotiationSetting` keys this story uses with `INSERT ... ON CONFLICT (setting_key) DO NOTHING`: `NEGOTIATION_MAX_ROUNDS` 5, `NEGOTIATION_INACTIVITY_HOURS` 48, `NEGOTIATION_MAX_LIFETIME_DAYS` 14, `PRICE_LOCK_HOURS` 24, `NEGOTIATION_LOW_OFFER_PERCENT` 50, `NEGOTIATION_REOFFER_COOLDOWN_HOURS` 24, `NEGOTIATION_OPEN_PER_BUYER_MAX` 20, `OFFERS_PER_MIN` 20 (the warning and Buy Now keys come with US-080 and US-068, G4).

### Backend (`valuex-backend`)
- [ ] `plans/domain`: `NegotiationSetting` enum (same shape as `CommunicationSetting`: default, min, max, `parse`), `NegotiationSettings` snapshot, `PlatformSettingsService.negotiation()` with its own cache evicted by the existing `evict()`.
- [ ] `negotiation/domain`: add `NEGOTIATION_CONVERTED` to `NegotiationState` and the new transitions to `NegotiationStateMachine` (C17 table); entities `Negotiation` (with `@Version`), `Offer`, `NegotiationStatusHistory`, `PriceAgreement`; enums for party, offer status, agreement status and `closed_reason` (LLD list); `NegotiationUpdatedEvent` (ids only).
- [ ] `negotiation/infrastructure/persistence`: repositories with a `FOR UPDATE` lookup, the open-negotiation lookups (by buyer, listing, thread), the buyer and seller paged lists, and the open-count query.
- [ ] `negotiation/application/port`: a listing-facts port (`negotiable`, `priced`, price, qualifier, `realEstate`, thumbnail, status, owner; LLD `ListingContextPort`) implemented in the listing module, and a small `NegotiationChatPort` (post an `OFFER_EVENT` card, find or create the thread) implemented in communication, so the modules stay decoupled as in US-069 (G3).
- [ ] `OfferRulesService`: the amount, round-cap, low-offer, two-decimal and "use Accept" rules of I.5, in one place, shared by create and counter.
- [ ] `OfferEligibilityService`: live, `negotiable`, price present, not reserved by another buyer's active agreement (`ERROR_ITEM_RESERVED`), not Real Estate-specific except no agreement (D7).
- [ ] `PriceAgreementService`: `createFromOffer(...)` (valid `PRICE_LOCK_HOURS`, advisory lock on the listing, `expireDue(listingId)` first, `ERROR_ALREADY_ACCEPTED` when another agreement reserves the listing), `cancel`, `endForListing`. The auto-reject of other buyers' negotiations is US-076 (G5).
- [ ] `NegotiationService.createOffer` (`@Transactional`): `ContactGuard.require(OFFER, ...)`; `@RequiresIdentityVerification` on the endpoint; eligibility; `OFFERS_PER_MIN` through `CommunicationRateLimiter`/`checkRateLimit`; open-count cap; re-offer cooldown after `REJECTED_BY_SELLER`; existing open negotiation returns it (200) when `clientRequestId` matches its first offer, else `ERROR_NEGOTIATION_EXISTS` (409 with the id); rules and low-offer confirmation; find or create the thread; insert the negotiation as `SELLER_REVIEWING` with offer round 1; run `SEND_OFFER` and `NOTIFY_SELLER` through the state machine with both history rows; set `expires_at` and `max_lifetime_at`; post the `OFFER_EVENT` card. After commit: `NegotiationUpdatedEvent` (ids only) drives `NegotiationRealtimeListener`, which sends `negotiation.updated` to buyer and seller through `RealtimePublisher.publishToUser`, and the `OFFER_RECEIVED` notification to the seller. The same listener serves accept, counter, reject, cancel and the listing and account cancellations.
- [ ] `NegotiationService.respond` (accept, reject, counter): row lock; caller must be the party whose turn it is; offer must be the latest `PENDING` (`ERROR_OFFER_NOT_CURRENT`); deadline check against `expires_at` and `max_lifetime_at` (`ERROR_NEGOTIATION_EXPIRED`); listing still live (`ERROR_ITEM_UNAVAILABLE`); accept (`MIN(offer, asking)`, agreement for goods, none for Real Estate), reject (`REJECTED_BY_SELLER` or `DECLINED_BY_BUYER`), counter (corridor, `ERROR_INVALID_COUNTER`, previous offer `SUPERSEDED`, two-step transition, `expires_at` reset); every action updates `last_activity_at`, `expires_at = LEAST(now + inactivity, max_lifetime_at)` and clears `warning_sent_at`.
- [ ] `NegotiationService.cancel` (buyer): from `SELLER_REVIEWING`, `BUYER_REVIEWING` and `OFFER_ACCEPTED`; `CANCELLED_BY_BUYER`; ends the agreement for goods.
- [ ] `NegotiationQueryService` and the response mapper: the shared response of I.4 for both roles (`role`, `awaiting`, `actions` computed for the caller, `counterRange`, `agreedPrice`, `priceLockExpiresAt`, `expiresAt`, `serverTime`); a non-participant gets 404; `warnAt` is returned as null until US-080 supplies the warning setting (G4).
- [ ] `NegotiationController`: `POST /api/v1/listings/{listingId}/offers`, `GET /api/v1/negotiations?role=&status=&page=&size=`, `GET /api/v1/negotiations/{id}`, `POST /api/v1/offers/{offerId}/accept`, `/reject`, `/counter`, `POST /api/v1/negotiations/{id}/cancel`; request records with Bean Validation (amount as decimal), OpenAPI annotations.
- [ ] `NegotiationListingEventListener` (`AFTER_COMMIT`): on `ListingStatusChangedEvent` to `SOLD`, `REMOVED_BY_ADMIN`, `REJECTED`, `DEACTIVATED_BY_SELLER` or `EXPIRED`, and on `ListingDeletedEvent`, cancel every open negotiation with `LISTING_UNAVAILABLE` and end its agreement; on `UserStateChangedEvent` of either party to a non-active state cancel with `ACCOUNT_UNAVAILABLE`. Never fails the originating action.
- [ ] `NegotiationNotificationService` and `NegotiationNotificationCopy` (English and Hindi): `OFFER_RECEIVED`, `OFFER_COUNTERED`, `OFFER_ACCEPTED`, `OFFER_REJECTED`, `OFFER_WITHDRAWN`; dedupe key `neg:{negotiationId}:{eventType}:{round}`; generic push text (D18, push itself is US-131); the notification category mapping for `OFFER_` already exists.
- [ ] Contact integration: turn the `offer` capability on in `ContactEligibilityService` (reasons `NOT_NEGOTIABLE`, `IDENTITY_REQUIRED`, `UNAVAILABLE`, `RESERVED` as defined in 1.4) and fill `contact.negotiationId`; update `ContactEligibilityServiceTest`.
- [ ] Error codes of I.8 in `ErrorCodes` (reuse the 422 `UnprocessableException` added by US-013 for the 422 rows; `WARNING_LOW_OFFER` carries no state change); audit through `AuditLogger`; metrics `negotiation.offer{action}` with no amounts; log ids only.
- [ ] Update `negotiation/package-info.java`.

### Mobile (`valuex-mobile`)
- [ ] `features/negotiation/data/negotiation_repository.dart` (endpoints in `api_constants.dart`, amounts sent as decimal strings) and `domain/` (`Negotiation`, `Offer`, `NegotiationState`, `NegotiationActions`, `PriceAgreement`).
- [ ] `presentation/offer_sheet.dart` (Make Offer): rupee field with `Formatters.money`, asking price and allowed range helper text, the same rules as the server for live validation, `WARNING_LOW_OFFER` confirmation dialog that keeps the entered amount, progress state, "Chat with seller" link, wording for rent and lease listings.
- [ ] `negotiation_screen.dart` at `/negotiations/:id` (route in `core/routing`; notification deep link `/offers/{id}` maps to it): listing header, status chip and one-line explanation per state, `offer_timeline.dart`, expiry countdown chip computed from `expiresAt` and `serverTime`, Accept, Counter and Decline when it is the buyer's turn, Cancel offer while waiting, counter sheet with the corridor, `price_lock_banner.dart` with countdown. Role-aware from the shared response (`role`, `actions`, `counterRange`): the seller reaches the same screen from the `OFFER_RECEIVED` notification deep link and the chat `OFFER_EVENT` card and sees seller wording plus Accept, Reject and Counter on their turn (G6, Option A). Add seller-view widget tests.
- [ ] The Proceed to checkout control is in the layout but shown only when the `cart` or `buyNow` capability is on, which is false until Sprint 5 (D10); copy "Waiting for seller to accept your offer" belongs to US-018.
- [ ] Providers: `negotiation_controller`, `negotiations_list_controller`, `negotiation_events_provider` (refresh on `negotiation.updated` from the `core/realtime` client; poll every 15 s while the screen is visible when the socket is down, following `chat_polling.dart`, G2). `agreement.updated` is added by the stories that need it (US-018, US-080).
- [ ] Listing integration: turn the Make an Offer control in `listing_actions.dart` on when `capabilities.offer` is available (Aadhaar entry for `IDENTITY_REQUIRED` now wired, D.11 row 10); open the existing negotiation when `contact.negotiationId` is set.
- [ ] Chat integration: replace the "Conversation update" placeholder in `system_card.dart` with `OFFER_EVENT` cards (who did what, amount, View offer action); Make Offer button on the thread header when no negotiation is open.
- [ ] Error mapping to ARB strings for every code in I.8; English and Hindi in `app_en.arb` and `app_hi.arb`, regenerate l10n; amounts announced as currency, countdowns announced at intervals, 48 dp targets, 320 px and 200 percent text.

### Documents (at the end)
- [ ] Update LLD Part I with as-built notes and the change log (Part C.10 and D.11 style), `user-stories.md` and Sprint-plan status, and write `Manual Testing Guides/US-017-Testing-Guide.md` (seller steps by API until US-076, G6).

## 5. Test Plan

| Level | Cases | Covers |
|---|---|---|
| Unit | `OfferRulesServiceTest`: first offer 0, negative, 1 paisa, equal to asking price, above asking; two-decimal limit; seller counter at, below and above the buyer's last offer and the asking price; buyer counter at and below its previous offer and at the seller's counter; counter equal to the other side's price points to Accept; low-offer threshold (49.99, 50, 90 percent off) with and without `confirmLowOffer`; round cap for each side | AC1, validation, edge cases |
| Unit | `NegotiationStateMachineTest` additions: every new transition and a rejected illegal one; history row per transition including the transient states | I.3 |
| Unit | `NegotiationServiceTest` create: eligibility failures (not negotiable, no price, reserved, unavailable), own listing, blocked, not Aadhaar verified, rate limit, open cap, cooldown after rejection and none after expiry, idempotent retry (200) and `ERROR_NEGOTIATION_EXISTS`, thread found or created, `expires_at` and `max_lifetime_at` set | AC1, AC2 |
| Unit | `NegotiationServiceTest` respond and cancel: not your turn, stale offer, expired by `expires_at` and by `max_lifetime_at`, listing gone, accept `MIN` rule (listing price lowered, raised), agreement created for goods and not for Real Estate, `ERROR_ALREADY_ACCEPTED`, reject by each side, counter and `SUPERSEDED`, counter at the round cap, buyer cancel from each of the three states, accepted price cannot be reversed by the seller | AC3, AC4, AC5, D20 |
| Unit | `PriceAgreementServiceTest`: valid until `PRICE_LOCK_HOURS`, `expireDue` clears stale rows first, single active agreement per listing, cancel and end for listing | AC4 |
| Unit | `NegotiationListingEventListenerTest`: each listing state and deletion cancels open negotiations and ends agreements, account state change of buyer or seller, a failure does not break the originating action | edge cases |
| Unit | `NegotiationNotificationServiceTest`: event type per action, dedupe key, generic push text, no amount in logs | AC2, AC3 |
| Unit | `NegotiationSettingTest` and `PlatformSettingsServiceTest` additions: ranges, defaults on invalid value, cache eviction; `ContactEligibilityServiceTest`: `offer` available and each reason | settings, capability |
| Controller | Statuses and envelopes for each endpoint (200 and 201, 401, 403 including the Aadhaar gate, 404 for strangers, 409 set, 422 set, 429); the amount as a decimal string | API |
| Integration (Testcontainers PostgreSQL) | Full flow offer, counter, counter, accept; two buyers on one listing negotiate independently; two simultaneous first offers by one buyer create one negotiation; stale offer id after a counter; accept after expiry; cancel from each state; listing sold cancels negotiations; the partial unique indexes and CHECKs are enforced by the database; concurrent accepts on two negotiations of one listing leave one active agreement | AC1 to AC5, concurrency |
| Mobile | Offer sheet validation, helper text, low-offer dialog keeps the amount, submit progress and each error mapping; negotiation screen for every `state` and `actions` combination; countdown from `serverTime`; polling and event refresh; checkout control hidden while the capability is off; chat card rendering; Hindi, 320 px and 200 percent text; accessibility labels | AC1 to AC5 |

Target above 90 percent line coverage on new and changed code (CODING_STANDARDS 1.8). Local note: Testcontainers runs need a working Docker engine (see the local-dev workarounds memory); the integration test runs in CI if Docker does not respond locally.

## 6. Validation Checklist

- [ ] AC1 to AC5 each have a passing test, backend and mobile where applicable.
- [ ] Offer greater than 0 and at most the asking price; every amount rule of I.5 holds at its boundary.
- [ ] A low offer needs confirmation; `WARNING_LOW_OFFER` changes nothing until the offer is re-sent with `confirmLowOffer`.
- [ ] At most `NEGOTIATION_MAX_ROUNDS` (5) prices per negotiation; after the cap only accept and reject work (`ERROR_MAX_NEGOTIATIONS` buyer, `WARNING_MAX_NEGOTIATIONS` seller).
- [ ] The accepted price is the lower of the offer and the current asking price, is locked for 24 hours for goods, and the seller cannot reverse it; the buyer can cancel.
- [ ] Real Estate: acceptance creates no agreement and no reservation (D7); no negotiated price is ever written to the listing.
- [ ] Several buyers can negotiate on one listing; one buyer has one open negotiation per listing (database enforced); a double tap or retry creates one.
- [ ] Expired and inactive negotiations answer `ERROR_NEGOTIATION_EXPIRED` on any action (the expiry job itself is US-080).
- [ ] A listing sold, removed, deleted or expired, or an account that stops being active, cancels open negotiations and tells both people.
- [ ] Seller notified of an offer, buyer notified of accept, counter and reject; in-app text may name the item and amount, push text is generic.
- [ ] All negotiation activity is in `negotiation_status_history`, `offers` and the audit log; logs and metric labels contain no amounts or message text.
- [ ] Non-participants get 404; blocked, own-listing and unverified callers get their codes; the offer capability and `contact.negotiationId` are correct on the listing details.
- [ ] Checkout control is hidden until `cart` or `buyNow` is on; no checkout code is added.
- [ ] Hindi strings marked for native-speaker review; Checkstyle, SonarQube, `dart format` and `flutter analyze` clean; build passes; coverage above 90 percent.

## 7. Open Gaps / Questions

| ID | Gap | Proposal |
|---|---|---|
| G1 | The story has no pointer to what happens when the seller proposes a lower price than the buyer's offer, and the LLD rules table only constrains counters upward for the seller. | Follow the LLD rules table exactly (seller counter above the buyer's last offer; buyer counter below the seller's last counter). No extra rule. |
| G2 | US-130 realtime is merged to `main`; US-131 (push) is not built. | **Decided (2026-11-17):** a `NegotiationRealtimeListener` (`AFTER_COMMIT`, like `ChatRealtimeListener`) sends `negotiation.updated` to both parties through `RealtimePublisher`. `badge.updated` waits for US-076 (it is the offers badge). Mobile uses the realtime client and polls only when the socket is down. Push stays generic and is added by US-131. |
| G3 | The listing module does not yet expose `negotiable`, the price qualifier, `realEstate` and the thumbnail through a port (`ContactListingPort` has only price and state). | Add a small listing-facts port (LLD `ListingContextPort`) and a chat port for the thread and the card, implemented as adapters in `listing` and `communication`, as US-069 did. |
| G4 | `NegotiationSetting` and `negotiation()` do not exist; the LLD lists 11 keys, but `NEGOTIATION_WARNING_BEFORE_HOURS`, `BUY_NOW_*` belong to US-080 and US-068. | Create the registry with the 8 keys this story uses; later stories add theirs. The Admin screen is US-116 (Sprint 10); until then values change by database update, as for the other settings. `warnAt` is null until US-080. |
| G5 | LLD I.5 says accept "applies the exclusivity rule of Part J", but J.2 puts auto-reject of other offers and neutral notices in US-076. | US-017 builds the agreement, the advisory lock and `ERROR_ALREADY_ACCEPTED` (needed for correctness) but not the auto-reject (`SUPERSEDED`) of other buyers' negotiations or `OFFER_SUPERSEDED`; those arrive with US-076. Until then other negotiations on the listing stay open and fail at accept with `ERROR_ALREADY_ACCEPTED`. Confirm this split. |
| G6 | There is no seller offers inbox or seller navigation until US-076, so a seller cannot reach the negotiation screen from the app except through a notification deep link or chat card. | The deep link and the `OFFER_EVENT` card open the role-aware negotiation screen for the seller too (it already shows Accept, Reject and Counter by `actions`); the inbox, badges and navigation are US-076. Manual testing of the seller side is by that route or by API. **Decided (2026-11-17): Option A.** The seller uses the screen in this story; the inbox, badges and navigation stay with US-076. |
| G7 | The story says "Max 5 back-and-forth negotiations per buyer-seller pair"; the LLD defines it as 5 prices per negotiation (D8), not per pair over time. | Follow the LLD (D8, `NEGOTIATION_MAX_ROUNDS`). A new offer after a closed negotiation is a new negotiation, limited by the cooldown and open-count rules. |
| G8 | The LLD migration number (V37) is stale: `main` is at V35 (US-130). | Use the next free number at branch time and update the LLD. |
| G9 | `ERROR_ITEM_RESERVED` and `RESERVED` need reserving agreements, which exist only from accept (and Buy Now in US-068). | Implement the check against `price_agreements` now; it is fully testable with offer agreements. |
| G10 | Hindi copy for notifications, errors and the sheet is not in the LLD. | Draft English and Hindi in the PR; Hindi marked for native-speaker review (LLD O5). |

G1 to G10: all decided by the user on 2026-11-17 (G6: Option A).

**Status: Approved** (user, 2026-11-17)

---

## 8. As built: deviations (2026-11-17)

The full account is in LLD Part I.11. Where the built story differs from this plan:

| # | Plan | As built | Why |
|---|---|---|---|
| D1 | Next free Flyway number. | `V36__negotiation_and_price_agreements.sql` (V35 is US-130). | As planned. |
| D2 | Entities `Negotiation`, `Offer`, ... with a `version` column. | Plain JDBC repositories and record rows; `version` is raised by each update and the row lock serialises actions. | Matches the communication module. |
| D3 | Ports `ListingContextPort` and a chat port. | `ListingFactsPort`, `NegotiationChatPort` and, for the listing page, `OfferAvailabilityPort` (communication side). | Module boundaries; no cycle. |
| D4 | `PriceAgreementService.expireDue` only ended agreements. | It also moves the negotiation to `NEGOTIATION_EXPIRED` so the buyer can offer again; `reservedForOther` only reads (the listing page is read-only). A write there failed the page in the integration test. | Found by `NegotiationIntegrationTest`. |
| D5 | `badge.updated` and `agreement.updated` events. | Only `negotiation.updated`; the others come with US-076 and US-018 (G2). | Scope. |
| D6 | Make Offer button on the chat thread header. | Not built: the thread has offer cards with `View offer`, and the listing page has the button. The header button needs the thread response to say whether the listing is negotiable. | Open item for the product owner. |
| D7 | The Proceed to checkout control in the layout (hidden). | Not built; nothing to show while `cart` and `buyNow` are off. It belongs to US-018 and Sprint 5. | Decision D10. |
| D8 | `GET /negotiations` list screen on mobile. | Backend list endpoint is built and tested; the mobile list and seller inbox are US-076. | Scope (G6, Option A). |
| D9 | Countdown "from `expiresAt` and `serverTime`". | The same, rounded up to whole minutes so 4 hours 20 minutes shows "4h 20m". | Readability. |
| D10 | Hindi notification text from the server. | The app localises the offer notifications from `eventType` and `params`, like the listing messages; the server text is English. Hindi needs native-speaker review (G10). | Existing pattern. |

Verification: backend `mvn clean verify` 2,881 tests green (13 in `NegotiationIntegrationTest` with real PostgreSQL), checkstyle clean, line coverage of the `negotiation` package 99.1 percent; mobile `flutter analyze` clean and the negotiation, listing and chat suites green.
