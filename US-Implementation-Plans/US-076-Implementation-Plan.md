# US-076: Seller Negotiation Management - Implementation Plan

## 1. Header

| Field | Value |
|---|---|
| Story | US-076 - Seller Negotiation Management |
| Sprint | Sprint 4 - Communication & Negotiation |
| Story points | 5 |
| Repos involved | valuex-backend (offers received list and summary, exclusivity auto-reject, badges, realtime badge event, notification) and valuex-mobile (Offers screen with Received and Sent, profile entry, counter sheet slider, accept confirmation). No `valuex-ai`, `valuex-web` or infra change. |
| Dependencies | US-017 (built and merged to `main`, gap G1 resolved), US-130 (realtime, merged), US-103 (profile hub badges, built). |
| Date | 2026-11-18 |
| Design source | [Sprint 4 LLD](../LLD/Sprint-4-Communication-Negotiation-LLD.md) Part J (J.1 to J.10), I.11 (what US-017 already built), section 1.6 (`NegotiationSetting`), [Sprint 1 LLD](../LLD/Sprint-1-Identity-User-Management-LLD.md) section 8.3 (menu badge keys). |
| Branches (proposal) | `feature/US-076-seller-negotiation-management` in `valuex-backend` and `valuex-mobile`, cut from `main` (US-017 is merged, G1), rebased before work starts (CLAUDE.md rule 5.1). |
| Flyway number | Next free number at branch time (V37 if nothing else lands first): one index and the seed of `NEGOTIATION_WARNING_BEFORE_HOURS` (G4). |

## 2. Story Recap

**As a** seller **I want to** manage buyer offers efficiently **So that** I can accept, reject, or counter offers quickly.

> Update (2026-10-25, category taxonomy): for Real Estate the seller can mark the property Sold or Rented after an agreed price (US-118); that action is separate and unchanged.

**Acceptance criteria (from `user-stories.md`):**

| ID | Criterion |
|---|---|
| AC1 | Given I have received buyer offers, when I open "Offers" or a notification, I see the pending offers with the buyer's name and rating, the item, the offered price against the listed price, and the offer time. |
| AC2 | When I tap an offer I see Accept, Reject and Counter. |
| AC3 | Accept: the buyer is notified at once, the price is locked for 24 hours and the buyer can proceed to checkout. |
| AC4 | Reject: the buyer is notified and the negotiation ends. |
| AC5 | Counter: I enter a counter offer and the buyer is notified to review. |

**Edge cases (story):** several buyers offer at once; the seller accepts one while others are pending; an offer expires while the seller reviews it; the buyer cancels before the seller responds.
**Validation rules (story):** offers expire after 48 hours without a seller response; accepting one offer auto-rejects the others for the same item; a counter is between the buyer's offer and the listed price; at most 5 rounds per pair; the seller must respond within 48 hours or the offer expires.
**Error scenarios (story):** `ERROR_OFFER_EXPIRED`, `ERROR_ALREADY_ACCEPTED`, `ERROR_INVALID_COUNTER` (with the range), `WARNING_MAX_NEGOTIATIONS`.
**Flutter notes (story):** an Offers tab in the Messages screen or a standalone Offers screen reachable from the Profile; offer cards sorted by expiry (soonest first) with countdown chips.

**What US-017 already delivers (LLD I.11):** the accept, reject, counter and cancel endpoints and their rules (corridor, round cap, expiry check, `ERROR_ALREADY_ACCEPTED` guard, price lock for goods, none for Real Estate), `GET /negotiations?role=SELLER`, the negotiation screen with Accept, Counter and Decline for the seller, notifications `OFFER_RECEIVED` and the others, realtime `negotiation.updated`, and the offer deep link. US-076 adds what is left of LLD Part J.

## 3. Design Reference

LLD Part J: J.3 index, J.4 API (`/offers/received` and its summary), J.5 backend design (query, exclusivity and auto-reject, badges), J.6 sequence, J.7 mobile (Offers screen, counter sheet, confirmations), J.8 codes, J.9 security, J.10 tests.

### Key design decisions

- **Exclusivity is completed here.** US-017 stops a second accept with `ERROR_ALREADY_ACCEPTED`; US-076 adds, inside the same accept transaction, the rejection of every other open negotiation of the listing (`REJECT_OFFER`, `closed_reason = SUPERSEDED`, their pending offers `REJECTED`), goods only (decision D7). The other buyers get a neutral `OFFER_SUPERSEDED` notification and a neutral chat card that never says who won or at what price (J.9).
- **A read model for the seller.** `OffersReceivedQuery` is one query over `negotiations` and the latest offer, scoped to `seller_id = caller`, bounded by `idx_negotiations_seller_open`, page size at most 50, sorted by `expires_at` ascending for Pending.
- **Badges.** `OffersBadgeProvider implements ProfileMenuBadgeProvider` feeds the profile hub (`OFFERS`/`OFFERS_RECEIVED`/`MY_OFFERS`, see G3); the same counts travel in a `badge.updated` realtime event.
- **Seller wording.** An expired offer answered by the seller reads `ERROR_OFFER_EXPIRED` ("This offer has expired"); the condition is the same as `ERROR_NEGOTIATION_EXPIRED` (G6).
- **Real Estate:** steps of exclusivity are skipped; only the accepted negotiation changes (J.5).

### Verified implementation anchors (checked 2026-11-18)

| Area | Finding and consequence |
|---|---|
| Base code | The negotiation module (US-017) is merged to `main`; US-076 starts from `main` (G1 resolved). |
| Accept path | `NegotiationService.accept` already locks the negotiation row and calls `PriceAgreementService.createFromOffer`, which takes the listing advisory lock, clears lapsed agreements and throws `ERROR_ALREADY_ACCEPTED`. The auto-reject is added after `createFromOffer`, inside the same transaction. `NegotiationRepository.lockOpenByListing(listingId)` already locks open negotiations in a fixed order. |
| Transitions and events | `NegotiationTransitions.move` (state machine, history row, update) and `NegotiationUpdatedEvent` with kinds `OFFER_RECEIVED`, `OFFER_COUNTERED`, `OFFER_ACCEPTED`, `OFFER_REJECTED`, `OFFER_WITHDRAWN`, `NEGOTIATION_CANCELLED`; listeners `NegotiationNotificationListener` and `NegotiationRealtimeListener`. A `SUPERSEDED` kind is added. |
| Cards | `NegotiationChatPort.postOfferCard` writes `OFFER_EVENT` cards; the mobile `SystemCard` renders them by `payload.kind`. |
| Seller list today | `GET /negotiations?role=SELLER&status=OPEN` already lists the seller's negotiations in the full shape but with no summary, no sort by expiry and no buyer-and-offer card shape. |
| Profile badges | `auth.application.port.ProfileMenuBadgeProvider` (`menuKey()`, `badgeCount(userId)`; must be fast, one indexed count; keys unique across providers). Mobile `ProfileMenuKeys` has no offers key yet and `profile_screen.dart` has no Offers row. The Sprint 1 LLD menu table lists one row "Offers" with key `OFFERS`, destination US-076 (G3). |
| Ratings | `listing.application.port.SellerReputationPort` exists (used for the seller of a listing); a buyer rating is null until the rating module exists, so the card shows "No ratings yet". |
| Realtime | `RealtimeEvents.NEGOTIATION_UPDATED` exists; `badge.updated` (`{chatsUnread, offersAwaiting}`, LLD A.4.3) is not defined yet. Mobile `negotiationEventsProvider` already filters `negotiation.` and `agreement.` prefixes. |
| Settings | `NegotiationSetting` has 8 keys; `NEGOTIATION_WARNING_BEFORE_HOURS` (needed for "expiring soon") is not seeded (G4). |
| Mobile | `features/negotiation` has the screen, sheets, controller and deep link; no list screen, no list controller, no `/offers` route. `CounterSheet` has a text field only (the LLD wants a slider as well). |

## 4. Implementation Steps

### Database
- [ ] Migration `V<next>__offers_received.sql`: `idx_negotiations_seller_open ON negotiations (seller_id, expires_at) WHERE state IN ('SELLER_REVIEWING', 'BUYER_REVIEWING', 'OFFER_ACCEPTED')` exactly as LLD J.3.
- [ ] Seed `NEGOTIATION_WARNING_BEFORE_HOURS` = 24 with `INSERT ... ON CONFLICT (setting_key) DO NOTHING` (G4).

### Backend (`valuex-backend`)
- [ ] `plans/domain`: add `NEGOTIATION_WARNING_BEFORE_HOURS` (24, range 1 to 72) to `NegotiationSetting`, and the cross-field rule "warning is lower than `NEGOTIATION_INACTIVITY_HOURS`" in `NegotiationSettings` (a broken rule resets both to defaults and counts `settings.invalid`, like `DiscoverySettings`). Fill `warnAt` in `NegotiationResponse` (currently always null) from it.
- [ ] Exclusivity (goods only): in `NegotiationService.accept`, after `createFromOffer`, `NegotiationCancellationService`-style helper `supersedeOthers(listingId, acceptedNegotiationId)` locks every other open negotiation of the listing in `SELLER_REVIEWING` or `BUYER_REVIEWING` (`lockOpenByListing`), rejects their pending offers, moves them with `REJECT_OFFER` to `OFFER_REJECTED` (`closed_reason = SUPERSEDED`), writes a neutral card and publishes a `SUPERSEDED` event. Negotiations already `OFFER_ACCEPTED` are never touched (the unique agreement index forbids a second one). Real Estate skips it.
- [ ] `NegotiationEventKind.OFFER_SUPERSEDED`; `NegotiationNotificationCopy` text "The seller accepted another offer for {item}. You can make a new offer if it becomes available again" (no name, no price); `NegotiationNotificationListener` sends it in-app to each other buyer (dedupe `neg:{id}:OFFER_SUPERSEDED:{round}:{buyer}`); `NegotiationRealtimeListener` already sends `negotiation.updated` to both people of each.
- [ ] `OffersReceivedQuery` and `OffersReceivedService` (`negotiation/application`): `GET /api/v1/offers/received?status=PENDING|ACCEPTED|CLOSED|ALL&page=&size=` (default `PENDING`, size at most 50, clamped like the existing lists) and `GET /api/v1/offers/received/summary` returning `{pending, accepted, expiringSoon}`. `PENDING` = awaiting the seller sorted by `expires_at`; `ACCEPTED` = accepted with a live price lock; `CLOSED` = the rest newest first. Item shape as LLD J.4 (`negotiationId`, `offerId` of the latest pending offer, `state`, `buyer {userId, displayName, rating, ratingCount}`, `listing {listingId, title, thumbnailUrl, askingPrice}`, `offeredPrice`, `offeredAt`, `round`, `expiresAt`, `priceLockExpiresAt`, `serverTime`). Buyer names in one batch through `ParticipantDirectoryPort`; rating null. A new `OffersReceivedController` (or additions to `NegotiationController`); offers of other sellers are simply not in the list; an offer id of another seller still answers 404 on the Part I endpoints.
- [ ] `OffersBadgeProvider implements ProfileMenuBadgeProvider` in `negotiation/application`: the count of open negotiations awaiting the caller (one indexed count over `idx_negotiations_seller_open` plus the buyer side). Keys per gap G3.
- [ ] Realtime `badge.updated` (`{chatsUnread, offersAwaiting}`, A.4.3): `RealtimeEvents.BADGE_UPDATED`; `NegotiationRealtimeListener` also publishes it to the seller on a new offer, an answer, a withdrawal and a supersede. The `chatsUnread` part is filled by the chat side if it already has a count port, otherwise the event carries `offersAwaiting` only (G7).
- [ ] `ERROR_OFFER_EXPIRED` for a seller who acts on an expired offer (same condition as `ERROR_NEGOTIATION_EXPIRED`, kept for the buyer); update the US-017 tests that assert the code for the seller (G6).
- [ ] Metrics `negotiation.offer{action=supersede}`; logs ids only; audit record for each superseded negotiation.
- [ ] Update `negotiation/package-info.java` if it lists the module's parts.

### Mobile (`valuex-mobile`)
- [ ] `features/negotiation/domain`: `ReceivedOffer`, `OffersSummary`, a status filter enum; `data/negotiation_repository.dart`: `receivedOffers(status, page)`, `sentOffers(status, page)` (via `GET /negotiations?role=BUYER`), `offersSummary()`; endpoints in `api_constants.dart`.
- [ ] `presentation/offers_screen.dart` at `/offers` (`RouteNames.offers`, router and `route_guard.dart`): two tabs **Received** and **Sent**, chips Pending, Accepted, Closed, cards with the buyer's name and rating chip ("No ratings yet" when absent), the item thumbnail and title, "Offered ₹12,000 of ₹14,500", the time and an expiry countdown chip (`CountdownText` from US-017); Pending sorted by soonest expiry; empty, loading and error states with Retry; pull to refresh; paging; refresh on `negotiation.updated` and `badge.updated` with the 15 second polling fallback while the live connection is down. A card opens `/negotiations/{id}`.
- [ ] Controllers `received_offers_controller` and `sent_offers_controller` (family by status) following `chat_list_controller`; `offers_badge_provider` from the summary and `badge.updated`.
- [ ] Profile hub: `ProfileMenuKeys` gets the offers key (G3); a new Activity row "Offers" with its badge in `profile_screen.dart` opens `/offers`.
- [ ] `CounterSheet` (US-017): add the slider between the buyer's offer and the asking price (steps of ₹1) kept in sync with the amount field, the range text, and, at the round cap, a banner "only Accept or Reject remain" in place of the sheet; slider semantics speak rupees.
- [ ] `NegotiationScreen` (seller role): Accept asks for confirmation and explains "The price is locked for 24 hours and other offers on this item will be declined" (goods) or only the agreement (property); Reject asks for confirmation (already built); after accepting the banner says the buyer can now check out (checkout itself is Sprint 5). Map `ERROR_OFFER_EXPIRED` ("This offer has expired") and the existing seller texts.
- [ ] Notification text: `OFFER_SUPERSEDED` English and Hindi in `notification_text.dart` (title with item, no price).
- [ ] English and Hindi strings (`app_en.arb`, `app_hi.arb`, regenerate l10n); 48 dp targets; semantic labels on countdowns; no overflow at 320 px and 200 percent text; Hindi marked for native-speaker review.

### Documents (at the end)
- [ ] Update LLD Part J with as-built notes (J.11) and the change log, `user-stories.md` and Sprint-plan status, the Sprint 1 LLD menu table if the key differs (G3), and write `Manual Testing Guides/US-076-Testing-Guide.md`.

## 5. Test Plan

| Level | Cases | Covers |
|---|---|---|
| Unit | `NegotiationServiceTest` additions: accept supersedes only the other open negotiations of the same listing, leaves closed and `OFFER_ACCEPTED` ones alone, rejects their pending offers with `SUPERSEDED`, writes a neutral card and an event for each; a property accept supersedes nothing; accept that fails with `ERROR_ALREADY_ACCEPTED` supersedes nothing | AC3, edge case 2 |
| Unit | `OffersReceivedServiceTest`: filter `PENDING`/`ACCEPTED`/`CLOSED`/`ALL`, order by expiry then newest, page and size clamping, seller scoping, buyer name fallback, null rating, `expiringSoon` against the warning setting, summary counts, expired-while-pending shown as expired | AC1, J.4 |
| Unit | `OffersBadgeProviderTest`: counts both sides, zero when none, key per G3, never negative | badges |
| Unit | `NegotiationSettingTest`/`PlatformSettingsServiceTest`: the new key, range, the cross-field rule (warning not below inactivity resets both) and `warnAt` in the response | G4 |
| Unit | `NegotiationNotificationListenerTest` and `NegotiationRealtimeListenerTest`: `OFFER_SUPERSEDED` text has no name or price, dedupe key, `badge.updated` to the seller on each change | AC3, J.5 |
| Unit | Seller expiry code: `ERROR_OFFER_EXPIRED` for the seller, `ERROR_NEGOTIATION_EXPIRED` for the buyer | J.8 |
| Controller | Statuses and envelopes of the two new endpoints (200, 401, size above 50 clamped, unknown status falls back to `PENDING`) | API |
| Integration (Testcontainers PostgreSQL) | Three buyers offer, the seller accepts one: the others are `OFFER_REJECTED`/`SUPERSEDED` and notified neutrally; a second accept returns `ERROR_ALREADY_ACCEPTED`; **two simultaneous accepts leave exactly one active agreement**; lock expiry frees the listing and the seller can accept another offer; Real Estate acceptance leaves the others open; the received list is scoped to the seller and sorted; the summary and badge counts match | AC1 to AC5, J.10 |
| Mobile | Received and Sent tabs, chips, sort order, countdown chips, empty, error with Retry, paging, refresh on events and polling fallback; Offers row and badge in the profile; accept and reject confirmations (texts for goods and property); counter sheet slider and field stay in sync, both ends of the range, cap banner; Hindi, 320 px and 200 percent text; accessibility labels | AC1 to AC5 |

Target above 90 percent line coverage on new and changed code (CODING_STANDARDS 1.8).

## 6. Validation Checklist

- [ ] AC1 to AC5 each have a passing test, backend and mobile where applicable.
- [ ] The pending list shows buyer name and rating, item, offered against listed price and time, sorted by soonest expiry, with a countdown.
- [ ] Accepting one offer rejects all other open negotiations on a goods listing in the same transaction; none is touched on a property; a rolled-back accept rejects nothing.
- [ ] The other buyers' message is neutral: no winner, no price, in the notification and in the chat card.
- [ ] Two simultaneous accepts leave exactly one active price agreement.
- [ ] `ERROR_OFFER_EXPIRED`, `ERROR_ALREADY_ACCEPTED`, `ERROR_INVALID_COUNTER` (with the range) and `WARNING_MAX_NEGOTIATIONS` are produced and shown in words, English and Hindi.
- [ ] The list and summary only show the caller's own negotiations as seller; another seller's offer id answers 404.
- [ ] Badges: the profile hub and `badge.updated` show the same count and drop to zero when nothing awaits.
- [ ] A negotiation expiring while the seller reviews it fails the action and shows as expired after refresh.
- [ ] The counter slider never leaves the corridor; at the round cap only Accept and Reject remain.
- [ ] No amount or buyer name in logs or push-style text of the superseded message.
- [ ] Checkstyle, SonarQube, `dart format` and `flutter analyze` clean; build passes; coverage above 90 percent; Hindi marked for native-speaker review.

## 7. Open Gaps / Questions

| ID | Gap | Proposal |
|---|---|---|
| G1 | US-017 is pushed on its own branches and not merged to `main`; US-076 builds on its negotiation module. | Open and merge the US-017 pull requests first, then cut the US-076 branches from `main`. If you prefer to start now, cut from `feature/US-017-price-negotiation` and rebase after the merge. |
| G2 | Much of Part J is already built by US-017 (answer endpoints, seller negotiation screen, seller list through `GET /negotiations?role=SELLER`). | Scope as in section 4: only what Part J adds. Keep `GET /negotiations` for the buyer's Sent tab. |
| G3 | The badge keys differ: Sprint 1 LLD lists one "Offers" row with key `OFFERS`; Part J names `OFFERS_RECEIVED` and `MY_OFFERS`. | Use the Sprint 1 table: one "Offers" row, key `OFFERS`, count = offers awaiting the caller's answer as seller plus as buyer; `badge.updated` carries `offersAwaiting` with the same number. Update Part J. |
| G4 | "Expiring soon" needs `NEGOTIATION_WARNING_BEFORE_HOURS`, which US-080 was to add; `warnAt` is null today. | Add the setting, its seed and the cross-field rule here (small), fill `warnAt`; US-080 then only adds the warning job. |
| G5 | Part J says the Offers entry can also be a tab in the chat list when the user has offers. | Build the profile row and the notification link only; the chat-list tab is left out (the Messages screen has its own tabs and offers already show as cards in threads). Confirm. |
| G6 | `ERROR_OFFER_EXPIRED` and `ERROR_NEGOTIATION_EXPIRED` are "the same condition shown with seller wording". | Backend answers `ERROR_OFFER_EXPIRED` when the actor is the seller and `ERROR_NEGOTIATION_EXPIRED` for the buyer; mobile maps both. Update the US-017 test that asserts the old code for the seller. |
| G7 | `badge.updated` also carries `chatsUnread` (A.4.3); the chat unread count is read by REST today. | Send `offersAwaiting` always and `chatsUnread` only if a count port is already available when coding; otherwise the field is omitted and the app keeps reading chat unread over REST. |
| G8 | Buyer ratings do not exist yet. | Rating null, "No ratings yet" in the app, as in US-017. |
| G9 | Push collapse key `neg:{id}` (J.5) needs US-131. | Out of scope here; in-app notification is not coalesced, as the LLD says. |
| G10 | Hindi copy for the Offers screen, confirmations and the superseded notice is not in the LLD. | Draft English and Hindi in the PR; Hindi marked for native-speaker review (LLD O5). |

**Resolutions (user review):** G1 US-017 is merged to `main`, so the US-076 branches are cut from `main`. G2 to G10 agreed as proposed (G5 confirmed: no chat-list tab; G3 single `OFFERS` key; G4 seed here; G6 seller wording).

## 8. Deviations from the plan (as built, 2026-11-18)

The full table is in LLD J.11. In short:

| # | Plan | As built | Why |
|---|---|---|---|
| D1 | The listing advisory lock is taken by `createFromOffer`. | `NegotiationService.accept` also takes it **before** the negotiation row lock (goods, participants only). | The winner locks the other rows; two accepts that locked rows first would deadlock. Found while writing the race integration test. |
| D2 | `PENDING` is awaiting the seller. | `PENDING` also lists offers waiting for the buyer after a seller counter (the card says whose turn it is); `summary.pending` and the badge keep the narrower meaning. | The seller sees the whole negotiation in one list; without it a countered offer would fall under Closed. |
| D3 | Accept explains "locked for 24 hours". | The text says the price is locked for the buyer, without a number. | `PRICE_LOCK_HOURS` is an Admin setting. |
| D4 | Row "Offers" in the Activity group. | First row under Selling. | The app has no Activity section. |
| D5 | `SellerReputationPort` for the buyer rating. | Rating null, count 0. | The port is for listing sellers and there is no rating module (plan G8). |
| D6 | A new `OffersReceivedQuery` class. | `ReceivedOfferRepository` (SQL) and `ReceivedOffersService`. | Matches the module layout of the other repositories. |
| D7 | `OffersBadgeProvider` counts "awaiting the caller". | Counts `SELLER_REVIEWING` (as seller) plus `BUYER_REVIEWING` (as buyer), not past their time. | Defines "awaiting" precisely. |

Open items for the product owner: the Hindi texts need native-speaker review; the chat-list Offers tab is not built (G5); `chatsUnread` is not part of `badge.updated` (G7); an expired offer stays listed until the US-080 job closes it.

**Status: Approved (implemented 2026-11-18)**
