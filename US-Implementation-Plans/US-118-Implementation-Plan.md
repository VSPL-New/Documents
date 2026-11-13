# US-118: Real Estate Listing Specifics — Implementation Plan

## 1. Header

| Field | Value |
|---|---|
| Story ID | US-118 |
| Title | Real Estate Listing Specifics |
| Sprint | Sprint 3 — Discovery & Search |
| Story Points | 5 |
| Repositories | valuex-backend, valuex-mobile |
| Dependency | US-006 and US-011 (both built on main). Sprint 3 LLD build order places US-012 before US-118. US-012 is merged on both repos (backend earlier; mobile #65 merged 2026-11-13, `lib/features/listing_view` is on mobile `main`), so the implementation gate is met. |

**Planning status:** Approved (2026-11-13). The user approved the revised plan and confirmed that US-012 mobile (#65) is merged. Revision history: revised on the same day after the earlier approval. The migration number, the US-012 gate status and Open Gap 1 (post-publication states) were refreshed, and a code check the same day found the buyer-side intent flow largely built (status snapshot in section 3), so the backend validator and mobile search steps were narrowed and Open Gaps 6 and 7 were added. The Part E/D10/C8 and user-story updates are still to be made first by the implementor.

## 2. Story Recap

**As a** buyer and seller of property, **I want** property listings to follow a sale, rent or lease flow that ends at price negotiation, **so that** property can be advertised and negotiated without the goods checkout and delivery flow.

**Acceptance Criteria** (from `Documents/user-stories.md`):
- Given a buyer opens Real Estate search, when no transaction intent has been chosen, then the app prompts for Buy, Rent or Lease before showing prices.
- The intent filter is mandatory before any price range or sorting, so sale, rent and lease prices are never mixed.
- New Developments show "Starting from" with the minimum price.
- When a buyer opens a property, they can chat, call or video call the seller and negotiate the price.
- There is no cart, checkout, escrow, payment or delivery, and "Buy Now" is not shown.
- After publication, the seller can mark the property Sold, Rented or Leased; the deal may be completed inside or outside JustQlic.

**Product clarifications (2026-11-12):** the seller may close a property deal made outside JustQlic and mark the property Sold, Rented or Leased in the app at any stage after publication. Closing must not depend on a JustQlic chat, call, video call or negotiation record. Negotiated prices are private to the buyer-seller pair and final only for that pair; they must never update the shared listing price. The close request records only the outcome, not the buyer identity or negotiated price.

**Edge cases:** intent not supported by the property family; changing intent after entering prices; New Development with minimum price above maximum price; Commercial Lease without the optional total lease amount; buyer searches without choosing an intent.

**Validation rules:** supported intents by family are Homes: Sale, Rent; New Developments: Sale; Land: Sale, Lease; Commercial: Sale, Rent, Lease; Shared and Managed Living: Rent. `listing_price_inr` is system-derived (Sale: sale price or minimum price; Rent and Lease: monthly rent). Maximum price is ₹10,00,00,000.

**Error scenarios:** `ERROR_INTENT_NOT_SUPPORTED` ("This option is not available for this property type"); `ERROR_PRICE_REQUIRED_FOR_INTENT` ("Enter the price for your option"); `ERROR_INVALID_PRICE_RANGE` ("Minimum price cannot be above maximum price").

## 3. Design Reference

- [Sprint-plan.md — Sprint 3](../Sprint-plan.md): the story goal is buyer discovery; its exit criterion says the property flow ends at price negotiation.
- [user-stories.md — US-118](../user-stories.md#us-118-real-estate-listing-specifics): authoritative acceptance criteria, intent-family rules and error scenarios.
- [Sprint-3-Discovery-Search-LLD.md — Part E, US-118](../LLD/Sprint-3-Discovery-Search-LLD.md#part-e---us-118-real-estate-listing-specifics): buyer-side intent search rules, category intent catalog, `STARTING_FROM`, detail capabilities, and seller close action.
- [Sprint-3-Discovery-Search-LLD.md — Part B, US-011](../LLD/Sprint-3-Discovery-Search-LLD.md#part-b---us-011-browse-and-search-listings): search request and result-card contract reused by US-118.
- [Sprint-3-Discovery-Search-LLD.md — Part C, US-012](../LLD/Sprint-3-Discovery-Search-LLD.md#part-c---us-012-view-listing-details): public property details, capability flags, and suppression of cart/Buy Now.
- [Sprint-2-Seller Listing Creation-LLD.md — Part C, US-006](../LLD/Sprint-2-Seller%20Listing%20Creation-LLD.md#part-c---us-006-category-taxonomy-and-category-driven-item-details): existing seller-side taxonomy, `transaction_intent`, supported intent values by profile, `ListingPriceResolver`, and normalized listing price behavior.
- [HLD 05 — Mobile Architecture](../HLD/05-Frontend-Architecture.md): records the intent prompt before showing Real Estate prices.
- [HLD 03 — Data Architecture](../HLD/03-Data-Architecture.md): states that Real Estate search filters on transaction intent before price range or sorting.

**Current implementation surfaces verified:** US-011 is merged to backend and mobile `main`. Backend search already validates intent; `ListingSearchDocumentFactory` emits `STARTING_FROM` for New Developments. Mobile has `SearchCriteria`, an intent sheet, and result cards carrying `priceQualifier` and `transactionIntent`. US-006 already derives the normalized property price. The US-118 LLD now specifies the close outcome and lifecycle transition; US-012's `listing_view` feature is not yet present in the current mobile repository.

**Key design decisions from Part E:** property and goods search results never mix; Real Estate price filters/sorts require an intent; L1/L2 supported intents are the union of descendant intents; New Developments use `STARTING_FROM`; the property close endpoint accepts `SOLD`, `RENTED` or `LEASED`, then records one lifecycle status (`SOLD`). Chat, calls, video and negotiation are explicitly out of scope for US-118 and remain Sprint 4 work.

**Product clarification superseding Part E's original restriction:** the close action must be available to the owner at any post-publication stage, including when a deal was completed outside JustQlic. Part E and decision D10 currently limit the action to `PUBLISHED`; revise the lifecycle allow-list before implementation to match the clarified requirement.

**Status snapshot (checked in the code on 2026-11-13, `main` of both repos).** No US-118 branch, pull request or closure code exists. A good part of the buyer-side behaviour already shipped with US-011, US-012 and US-006, so the steps below were narrowed to what is left:

| Piece | State |
|---|---|
| `ERROR_INTENT_REQUIRED` for any Real Estate scope without an intent; `ERROR_INTENT_NOT_SUPPORTED` at L3 (from the listing schema's `transactionIntents`) and for an intent on a non-Real-Estate search; `ERROR_INVALID_PRICE_RANGE` | **Built** (`SearchRequestValidator`, US-011) |
| Supported-intent check at L1 and L2 (`TransactionIntentCatalog`) | **Not built.** At L1/L2 any of Buy, Rent, Lease is accepted, so for example Rent under Land is not rejected |
| `STARTING_FROM` for New Developments in the search index and in the public details response | **Built** (`ListingSearchDocumentFactory`, `PublicListingService`) |
| Real Estate `capabilities` (`cart`, `buyNow` = `NOT_APPLICABLE`) on the public details response | **Built** on the backend (US-012). The details screen that reads them (`lib/features/listing_view`) was merged to mobile `main` on 2026-11-13 (PR #65) |
| Price derivation by intent (`ListingPriceResolver`) | **Built** (US-006) |
| `ERROR_PRICE_REQUIRED_FOR_INTENT` | **Not in the code**, only in the user story and Part E (Open Gap 6) |
| Mobile: `IntentSheet` (Buy, Rent, Lease), `chooseIntent`, intent in `SearchCriteria`, `ERROR_INTENT_REQUIRED` message, "Starting from" on cards | **Built** (US-011). `chooseIntent` only copies the intent; it does not clear the price range |
| Close action: migration, `ListingClosureService`, `POST /listings/{id}/close`, lifecycle whitelist rows, saver notification, My Listings "Mark as Sold, Rented or Leased", strings, tests, guide | **Not built.** This is the main remaining work |

## 4. Implementation Steps

### Design and prerequisites
- [ ] Complete and merge US-012 first, including the public detail response's `capabilities` flags; then pick up US-118 in the Sprint 3 LLD build order.
- [ ] Keep negotiated price private to its buyer-seller negotiation and separate from the shared listing price; closing records only the outcome. Do not write a negotiated price back to `listings.price` or expose one buyer's price to other buyers.

### Backend — `valuex-backend`
- [ ] Add `TransactionIntentCatalog` for L1/L2 scopes as the union of descendant profile options, cached with the taxonomy; reuse the L3 `transactionIntents` from the listing schema.
- [ ] Narrow `SearchRequestValidator.intent`: it already requires an intent for Real Estate scopes and checks L3 support. Add only the L1/L2 support check using `TransactionIntentCatalog` (previous step), so an intent no descendant supports returns `ERROR_INTENT_NOT_SUPPORTED`. Add tests for goods and property results staying separate and for price filters and sorts staying inside one intent only where US-011 does not already cover them.
- [ ] Verify, do not rebuild: `ListingSearchDocumentFactory.STARTING_FROM` for `PROP_NEW_DEV` and the public details response already carry the intent and qualifier; add one regression assertion that search card and details agree.
- [ ] Recheck the highest Flyway migration when implementation begins. `V27` was taken by US-111 (`V27__home_promos.sql`, merged 2026-11-13), so the next free number is `V28`: provisional `V28__listing_closed_outcome.sql` (`closed_outcome` values `SOLD`, `RENTED`, `LEASED` and its check constraint). US-073 or US-066 may take `V28` first; use the next free number and update Part E.3, which still says `V27`. The same migration widens `chk_trust_safety_admin_decision` for the review-queue decision below.
- [ ] Implement `ListingClosureService.close`: owner-only and row-locked; allow the action from exactly `PUBLISHED`, `BUYER_INQUIRY_PENDING`, `NEGOTIATION_IN_PROGRESS`, `OFFER_ACCEPTED`, `EXPIRED`, `TRUST_SAFETY_REVIEW` and `REVISION_REQUIRED` (one `<state> -> SOLD` whitelist row each, action `MARK_PROPERTY_CLOSED`; Open Gap 1), regardless of whether the deal or negotiation occurred in JustQlic, and reject every other state with `ERROR_LISTING_NOT_CLOSABLE`; require outcome to match intent; set `closed_outcome`; transition through `ListingLifecycleService` to `SOLD` with action `MARK_PROPERTY_CLOSED`.
- [ ] Remove a closed listing from the review queue (decided 2026-11-13, Open Gap 8): add `AdminReviewDecision.CLOSED_BY_OWNER` (proposed name) and widen `chk_trust_safety_admin_decision` in the same migration as `closed_outcome`; add `TrustSafetyReviewService.closePending(listingId)`, which, when the latest review `isPending()`, sets that decision and `reviewed_at` and leaves `admin_id` null; call it from `ListingClosureService.close` in the same transaction and under the same row lock. Keep `isFailed()` false for the new value. Resolve a pending appeal as moot if one can exist (check at build time).
- [ ] Keep `listings.price` unchanged by negotiation or closure; do not include buyer identity or negotiated deal price in the US-118 close request or shared listing/search/detail projections.
- [ ] Add the seller-side `ERROR_PRICE_REQUIRED_FOR_INTENT` check (decided 2026-11-13, Open Gap 6): where the price for the chosen intent is derived (`ListingPriceResolver`, called from `ListingDetailsService`), reject a missing price for that intent with "Enter the price for your option"; Sale needs the sale price (the minimum price for New Developments), Rent and Lease need the monthly rent, and the optional Commercial lease amount stays optional. Add the code to the mobile error mapping in English and Hindi.
- [ ] Add `POST /api/v1/listings/{listingId}/close` with `{ "outcome": "SOLD|RENTED|LEASED" }`, standard envelope and OpenAPI docs. Return `ERROR_NOT_A_PROPERTY_LISTING` for non-property or never-published listings and `ERROR_INTENT_NOT_SUPPORTED` for mismatched outcomes; define state-specific rejection behavior for already-closed or otherwise ineligible records in the LLD update.
- [ ] Verify the lifecycle event removes closed properties from search, makes saved entries unavailable and notifies savers; ensure goods listings still reach `SOLD` only through order completion.

### Mobile — `valuex-mobile`
- [ ] Extend the existing search flow (`features/search`): `IntentSheet` and `chooseIntent` already exist. Remaining: offer only the intents the selected category supports (today the sheet always lists Buy, Rent and Lease), keep the chosen intent visible as a chip that can be changed, and clear the price range when the intent changes (`chooseIntent` currently keeps `priceMin` and `priceMax`; confirm at build time).
- [ ] "Starting from" on New Development cards already works. Remaining: the intent label on property cards if it is not shown, and, now that mobile PR #65 has merged, check that the details screen in `lib/features/listing_view` uses the server `capabilities` (hide cart and Buy Now when `NOT_APPLICABLE`) rather than duplicating the Real Estate rule in the app.
- [ ] Keep a "Mark as Sold, Rented or Leased" action available on the seller's property listing after publication, regardless of subsequent in-app workflow stage. The action must support deals completed outside JustQlic, use the confirmation sheet and intent-matched outcome, then refresh card/status on success.
- [ ] Keep chat, call, video and negotiation behavior out of this story; US-012 may show unavailable actions as specified by Part C, and Sprint 4 will enable them.
- [ ] Add English and Hindi strings and cover loading, validation and retry states; preserve accessibility and responsive text behavior.
- [ ] Cover loading, empty, unsupported-intent, validation and retry states; preserve keyboard, screen-reader, tap-target and responsive text behavior.

### Tests and delivery
- [ ] Add backend unit/integration and Flutter widget/integration tests mapped to the acceptance criteria and edge cases; target greater than 90% coverage for new story code per `CLAUDE.md`.
- [ ] Before implementation, synchronize the user's closure decision in `Documents/user-stories.md` (US-118) and Part E plus decision D10 in `Documents/LLD/Sprint-3-Discovery-Search-LLD.md`; add the same external-deal and post-publication cases to `Documents/Manual Testing Guides/US-118-Testing-Guide.md` when creating it.
- [ ] Add tests and `Documents/Manual Testing Guides/US-118-Testing-Guide.md` for property-family intent rules, search separation, price qualifiers, detail capabilities, outside-deal Sold/Rented/Leased closure, and listing-price immutability. Update Part E with as-built notes after delivery.
- [ ] Follow `CLAUDE.md` workflow: create a US-118 feature branch from `main`, rebase with `main`, implement modularly, build, run tests and Checkstyle, run SonarQube, fix findings, and verify every acceptance criterion before pushing the story branch.

## 5. Test Plan

### Backend
- [ ] Search without intent for a Real Estate category is rejected before price/sort processing; non-Real-Estate searches retain their existing contract.
- [ ] Each property family accepts exactly its supported intents and rejects unsupported ones with `ERROR_INTENT_NOT_SUPPORTED`.
- [ ] Price ranges apply only after intent selection; changing intent cannot combine Sale, monthly Rent and monthly Lease prices.
- [ ] New Development indexing/search/detail responses carry the minimum price and qualifier required for "Starting from".
- [ ] Price derivation matches US-006: Sale uses `sale_price` or New Development `price_min`; Rent/Lease use `monthly_rent`; optional Commercial `lease_amount` does not become required unless the approved LLD changes that rule.
- [ ] `ListingClosureService` covers owner/non-owner, non-property, never-published, every allowed post-publication stage, outcome/intent mismatch, double submission, and closure without any JustQlic negotiation record.
- [ ] Closure writes the expected outcome and lifecycle history, removes the property from search, makes saved entries unavailable and notifies savers; goods listings cannot use the property-close endpoint.
- [ ] A negotiated price for one buyer-seller pair never changes the shared `listings.price` or appears in shared search/detail results; the close request accepts only the outcome.
- [ ] Property cannot use any goods checkout, escrow, payment or delivery path; existing goods flows remain unchanged.
- [ ] `ERROR_PRICE_REQUIRED_FOR_INTENT` for each property family and intent: Homes (Sale, Rent), New Developments (Sale, minimum price), Land (Sale, Lease), Commercial (Sale, Rent, Lease; lease amount optional), Shared and Managed Living (Rent); a present price passes.
- [ ] Closure from each of the seven allowed states succeeds with its own whitelist row, and from each excluded state (`ORDER_CREATED`, `SOLD`, `DEACTIVATED_BY_SELLER`, `REMOVED_BY_ADMIN`, `REJECTED`, every pre-publication state) returns `ERROR_LISTING_NOT_CLOSABLE`; closing from `TRUST_SAFETY_REVIEW` ends the pending review (Open Gap 8).
- [ ] Review queue: after closing a listing in `TRUST_SAFETY_REVIEW`, its latest review is no longer `isPending()` (decision `CLOSED_BY_OWNER`, `reviewed_at` set, `admin_id` null) and is not counted as failed; a listing whose latest review is already decided, or that has no review, is left alone; the review change and the close succeed or fail together; a later admin approve, reject or revision request on the closed listing fails with the invalid-transition error; `ListingRecoveryJob` does not pick the closed listing up; the pending-review check constraint accepts the new value.

### Mobile
- [ ] Real Estate search prompts for intent before showing prices; intent stays selected through filter and sort changes.
- [ ] Intent changes clear or revalidate a previously entered price range; unsupported intent and missing-intent responses show the specified localized errors.
- [ ] New Developments display "Starting from" and the minimum price in search results and details; other property families show the correct intent price.
- [ ] Property detail actions allow the approved chat/call/video/negotiation paths and never display cart, checkout or Buy Now.
- [ ] Seller Sold/Rented action displays only when allowed, confirms success/failure, and refreshes the listing/search state according to the LLD.
- [ ] Seller Sold/Rented/Leased action remains available after publication at every lifecycle stage permitted by the updated LLD, confirms success/failure, and refreshes listing/search state.
- [ ] Test empty results, intent not supported, invalid minimum/maximum, optional Commercial Lease total amount absent, network failure/retry, and localization/accessibility.

## 6. Validation Checklist

- [ ] Intent is selected before Real Estate prices, range filtering or sorting; sale, rent and lease prices are not mixed.
- [ ] Supported intent rules are enforced for every property family, on both backend and app.
- [ ] New Development uses its minimum price and the "Starting from" label.
- [ ] Sale, Rent and Lease use the US-006 normalized price derivation; the ₹10 crore maximum is enforced.
- [ ] A Commercial Lease without optional total lease amount remains valid if that optionality is retained in the approved design.
- [ ] Property detail exposes the approved communication and negotiation actions, with no goods purchase, payment or delivery actions.
- [ ] The property owner can close a deal made inside or outside JustQlic at any supported stage after publication, without requiring an in-app negotiation record.
- [ ] Negotiated price remains private to its buyer-seller pair and never mutates the shared listing price; US-118 closure stores only the outcome.
- [ ] Sold/Rented/Leased outcome matches the listing intent; closure is authorized, row-locked, audited and removes the property from search.
- [ ] Existing goods search, listing details and checkout behavior are not regressed.
- [ ] Tests, coverage, Checkstyle, SonarQube, manual guide and all story acceptance criteria are complete before marking the story done.

## 7. Open Gaps / Questions
1. **Part E and decision D10 need synchronization, and the eligible states need a decision.** Part E.5, D10 (LLD line 1806, 1838), conflict C8 and the US-118 user story still permit closure only from `PUBLISHED` and say Sprint 4 adds the negotiation-state rows. That is out of date: `ListingStateMachine` already has the whole chain (checked 2026-11-13): `PUBLISHED -> BUYER_INQUIRY_PENDING -> NEGOTIATION_IN_PROGRESS -> OFFER_ACCEPTED -> ORDER_CREATED -> SOLD`, plus `PUBLISHED -> EXPIRED / DEACTIVATED_BY_SELLER / REMOVED_BY_ADMIN / TRUST_SAFETY_REVIEW`, `EXPIRED -> PLAN_SELECTION_PENDING` (renew) and `DELETE` from several states. Nothing enters the inquiry and negotiation states yet (Sprint 4), but the rows exist. **Proposed rule (accepted by the user on 2026-11-13; extended by the review-state decision below):** a property may be closed from `PUBLISHED`, `BUYER_INQUIRY_PENDING`, `NEGOTIATION_IN_PROGRESS`, `OFFER_ACCEPTED` and `EXPIRED` (the deal was made outside JustQlic after the listing lapsed); a new whitelist row `<state> -> SOLD`, action `MARK_PROPERTY_CLOSED`, is added for each. Not allowed: `ORDER_CREATED` (a property has no order), `SOLD`, `DEACTIVATED_BY_SELLER`, `REMOVED_BY_ADMIN` and `REJECTED` (final, nothing reopens them), and the pre-publication states. **The two review states were decided on 2026-11-13 (allowed, see below):** `TRUST_SAFETY_REVIEW` and `REVISION_REQUIRED` (a published property that the owner edited and is back in review): allow closing, or require the review to finish first? The close request would return a clear error (a new code such as `ERROR_LISTING_NOT_CLOSABLE`, to be named in Part E) for any state not allowed. Update Part E, D10, C8 and the user story to match before implementing. **Decided 2026-11-13:** closing is also allowed from `TRUST_SAFETY_REVIEW` and `REVISION_REQUIRED`, so the final list is seven states (`PUBLISHED`, `BUYER_INQUIRY_PENDING`, `NEGOTIATION_IN_PROGRESS`, `OFFER_ACCEPTED`, `EXPIRED`, `TRUST_SAFETY_REVIEW`, `REVISION_REQUIRED`), each with its own `<state> -> SOLD` whitelist row, action `MARK_PROPERTY_CLOSED`. The error for any other state is named `ERROR_LISTING_NOT_CLOSABLE` (proposed name, to be written into Part E).
2. **Migration number.** `V27` is taken by US-111 (merged 2026-11-13). Use the next free number (`V28` today) and recheck at build time.
3. **Implementation gate.** US-012 must be implemented and merged before US-118 implementation starts; approval of this plan does not waive that dependency. Status 2026-11-13: met. US-012 backend is merged and mobile #65 was merged the same day, so both halves of US-118 can start. Branch from an up-to-date `main` in both repos.
4. **Communication and negotiation remain out of scope for US-118.** Part E assigns chat, calls, video and negotiation to Sprint 4; closure must not depend on those features or their records.
5. **This plan file is not in git.** `US-118-Implementation-Plan.md` is untracked in the `Documents` repo; it would be committed with the US-118 documents change.
6. **`ERROR_PRICE_REQUIRED_FOR_INTENT` has no implementation.** The US-118 story lists it ("Enter the price for your option") and Part E mentions it, but no backend code or mobile string uses it, and `ListingPriceResolver` (US-006) does not throw it. Decide before implementing: is it a seller-side check in the listing details flow (US-006 code, small change in this story), or is it already covered by another error the seller sees? If it belongs here, add the check and a test for each property family. I have not assumed an answer. **Decided 2026-11-13: add it in this story** (backend step and test added).
7. **The remaining size of the story.** With the buyer side largely built, most of the 5 SP is the close action, the L1/L2 intent check and two mobile adjustments. No change to the story points is proposed; say so if you want them reviewed.

8. **A closed property that is still in review. Decided 2026-11-13: closing removes the listing from the review queue.** What the code does today (checked 2026-11-13): the "queue" is not a table or a status; a review is pending when `ListingTrustSafetyReview.isPending()` is true (`auto_decision = QUEUED_FOR_REVIEW` and `admin_decision` is null, the partial index `idx_trust_safety_review_pending`). The only allowed `admin_decision` values are `APPROVED`, `REJECTED` and `REVISION_REQUESTED` (check constraint `chk_trust_safety_admin_decision`), and an admin decision (`TrustSafetyReviewService.approve`, `reject`, `requestRevision`) moves the listing through the lifecycle, which would fail on a `SOLD` listing. So closing must end the pending review in the same transaction. **Design to put in Part E (the value name is proposed, confirm or rename):** a new `AdminReviewDecision` value `CLOSED_BY_OWNER`; the closure migration also widens `chk_trust_safety_admin_decision` to allow it; a new `TrustSafetyReviewService.closePending(listingId)` finds the latest review (`findFirstByListingIdOrderByCreatedAtDesc`), and if `isPending()` sets `admin_decision = CLOSED_BY_OWNER`, `reviewed_at = now()` and leaves `admin_id` null, so the row drops out of the pending set; `ListingClosureService.close` calls it under the same row lock. The state change makes a later admin approve, reject or revision request on that listing fail with the normal invalid-transition error, which a test must pin. `isFailed()` must not treat the new value as a failed review. `ListingRecoveryJob.retryStuckReviews` only looks at listings still in `TRUST_SAFETY_REVIEW`, so it is not affected. **To check at build time (not assumed):** whether a pending seller appeal (`listing_trust_safety_appeals`, status `PENDING`) can exist on a listing closed from `REVISION_REQUIRED`; if it can, it must be resolved as moot in the same transaction. The admin queue screen is Sprint 10 (US-054); when it is built it should list only `isPending()` reviews.

**Status:** Approved (2026-11-13). The user approved the plan, including the decisions on the closable states (seven), the review states, `ERROR_PRICE_REQUIRED_FOR_INTENT` and the review queue (closing removes the listing from it). The US-012 gate is met.

## 8. As built: deviations from this plan

Recorded on 2026-11-13 during implementation (branches `feature/US-118-real-estate-listing-specifics` in backend and mobile, `docs/US-118-real-estate-listing-specifics` in Documents).

| Plan item | As built | Why |
|---|---|---|
| Migration `V28__listing_closed_outcome.sql` | Built as planned. It also adds `MOOT` to the appeal status check (`chk_trust_safety_appeal_status`) next to `CLOSED_BY_OWNER` on the review decision check | A pending appeal on a review of a property closed from `REVISION_REQUIRED` is settled as moot (Open Gap 8, "check at build time": it can exist) |
| `TrustSafetyReviewService.closePending(listingId)` | A new small component `TrustSafetyReviewCloser.closeFor(listingId)` | `TrustSafetyReviewService` already has nine dependencies; the same behaviour in a class of its own |
| Plan wrote `isPending()` | The code names it `isOpen()` | Naming in the existing code |
| New appeals | `TrustSafetyAppealService.submit` refuses an appeal on a `SOLD` listing (`ERROR_APPEAL_NOT_ALLOWED`) | The failed review of a property closed from `REVISION_REQUIRED` stays the latest one, so an appeal could otherwise still be filed on a closed listing |
| `TransactionIntentCatalog` "cached with the taxonomy" | One SQL query per L1 or L2 search with an intent, not cached | No taxonomy cache exists; adding one would be new infrastructure for one indexed query |
| `ERROR_PRICE_REQUIRED_FOR_INTENT` in `ListingPriceResolver` | Raised by `AttributeValidator` | The validator is where a missing price field is found first; the resolver's `ERROR_PRICE_INVALID` stays for an invalid number |
| Close error for a non-property | `ERROR_NOT_A_PROPERTY_LISTING` as 400 (LLD first said 409) | The shared handler answers business errors with 400 |
| Offer only supported intents in the sheet | The app remembers an intent the server refused for the category (`SearchState.unsupportedIntents`) and stops offering it; it is not known up front | No endpoint tells the app the intents of an L1 or L2 category; a new public endpoint was not in the plan |
| Mark as action on My Listings | The My Listings response gains `closeOutcome` (the outcome the owner can choose now) and `closedOutcome` (how a closed property ended) | The app cannot tell a property or its intent from the card; a rented property must not read as sold |
| Intent label on property cards | Not added | The search is already inside one intent shown in the chip, and the shared Home card has no field for it |
| Check that details use the server `capabilities` | Checked: `listing_view` hides cart and Buy Now for `NOT_APPLICABLE`; no change needed | |
| "Notify savers and make saved entries unavailable" | Not built | The saved-listings feature does not exist yet (US-073). US-073 must treat `SOLD` as unavailable and notify savers; written into the LLD |

Outcome: see the final summary of the implementation for test, coverage and scan results.
