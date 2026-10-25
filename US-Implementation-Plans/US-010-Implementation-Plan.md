# US-010: Edit/Delete Listing — Implementation Plan

> **Update (2026-10-25, category taxonomy):** A change of the L3 category is a major edit (re-moderation) and deletes attribute values outside the new category's schema (LLD Part C); metadata edits follow the category schema; the price maximum is ₹10,00,00,000. References to a primary category or US-006's old `V22` are superseded (US-006 takes `V16`; renumber at build time).

## 1. Header

| Field | Value |
|---|---|
| Story ID | US-010 |
| Title | Edit/Delete Listing |
| Sprint | Sprint 2 — Seller Listing Creation |
| Story Points | 5 (see Open Gaps item 1) |
| Repos | valuex-backend, valuex-mobile |
| Dependency | US-009 (published listings, `published_at`); US-084 (re-review of edited listings); US-089 (`ListingLifecycleService`, states); US-114 and US-006 (the details and category save that this story widens to published listings); US-007 (`RestrictedItemCheckService`); US-115 (notifications). Built last in Sprint 2 |

**Scope decisions (proposed 2026-10-16, to be confirmed in Open Gaps):**
1. **My Listings does not exist yet** in the app (the Profile row is a placeholder). This story builds the **My Listings list** with an Edit and a Delete action per listing, because the acceptance criteria start from "When I view my listings". Analytics (US-067) and plan upgrade (US-064) add to it later.
2. **Edit** reuses the endpoints and the Item Details page of US-114 and US-006, in edit mode:
   - `DRAFT` and `REVISION_REQUIRED` listings: Edit opens the listing flow where the seller left off (no new endpoint, no re-review rules).
   - `PUBLISHED` listings: Edit applies title, description, condition, price, location city and categories. **Photos are not editable here** (Open Gaps item 6).
   - Any other status cannot be edited (`ERROR_LISTING_NOT_EDITABLE`).
3. **Minor edits** apply at once. **Major edits** (a change of the primary category, a price change of more than 20% against the last approved price, or content the restricted-item check cannot clear) apply and send the listing back to the Trust & Safety review; it is **hidden from buyers until approved**. The app asks the seller to confirm before this happens.
4. **Delete** is a **soft delete** kept for 90 days. It is refused while a payment is in progress, the listing is in review, or (in later sprints) it has active orders, pending payments or open disputes.
5. In Sprint 2 there are no buyers, negotiations, orders or disputes, so the "notify active negotiations or viewers" part of the story is delivered as **events** that later sprints subscribe to (Open Gaps item 7).

## 2. Story Recap

**As a** seller **I want to** edit or delete my listings **so that** I can keep information accurate and remove sold items.

**Acceptance Criteria** (`Documents/user-stories.md`): I can choose Edit or Delete on my listings; saved changes show immediately and active negotiations are notified; a listing with no active orders can be deleted and is removed from the platform; one with active orders cannot be deleted and an error is shown.

**Edge Cases:** edit price during active negotiation · delete while a buyer is viewing · drastic change to a different item · delete with a pending payment · an edit that violates new platform policies.

**Validation Rules:** cannot delete with active orders, pending payment or open disputes · major edits (category, price over 20%) need re-moderation · edit history kept for audit · deleted listings kept 90 days (soft delete).

**Error Scenarios:** `ERROR_CANNOT_DELETE_ACTIVE_ORDER` · `ERROR_PRICE_CHANGE_TOO_HIGH` ("Price change >20% requires admin approval") · `WARNING_BUYERS_WILL_BE_NOTIFIED`.

**Flutter notes (story):** Edit opens the pre-filled create flow; Delete needs a confirmation bottom sheet with a warning; swipe-to-delete with undo within 2 seconds in My Listings.

## 3. Design Reference

- Primary source: [Sprint-2-Seller Listing Creation-LLD.md — Part J](../LLD/Sprint-2-Seller%20Listing%20Creation-LLD.md#part-j---us-010-editdelete-listing) §J.1–J.9, with the changes below.
- **No Figma frame is known for My Listings or the edit flow.** Build My Listings from the design system; Edit reuses the Item Details page. See Open Gaps item 2.
- Existing code to reuse: `ListingController` (`GET /{listingId}`, images), `ListingRepository.findByIdAndSellerIdForUpdate`, the US-114 details service and `ItemDetailsScreen`, the US-006 category service and picker, `ListingLifecycleService` and `ListingStatusChangedEvent` (US-089), `RestrictedItemCheckService` (US-007), `TrustSafetyReviewService` (US-084), `DomainEventPublisher`, the notification module (US-115), the Profile "My Listings" row, `ApiPage` and `ApiResponse`, `BrandGradientButton`, `ErrorView`.

**What differs from LLD Part J:**
- The LLD's `orderQueryPort`, `disputeQueryPort` and `activeViewerTracker` stubs ("always false") are replaced by a **collection of `ListingDeletionBlocker` beans**. Sprint 2 has none; Sprint 4, 5 and 8 add one each. No stubs to maintain, and no module is blocked from adding its own rule.
- Major-edit detection compares against the **last approved** price and primary category, not the previous edit, so five 10% price rises cannot slip through.
- The LLD does not re-check edited text. This plan runs the US-007 check when the title, description or category changes, because otherwise a seller could publish a clean listing and then edit it into a restricted one.
- The LLD returns the warning after the edit is applied. This plan asks for **confirmation first** (HTTP 409) so the seller is not surprised by a hidden listing.

**Key design decisions:**
- One endpoint for edits, `PATCH /api/v1/listings/{id}` (already created by US-114). The service branches on status: draft states follow US-114's rules; `PUBLISHED` follows this story's rules.
- **Baseline columns.** `listings.approved_price` and `listings.approved_primary_category_id` are written when a listing reaches `APPROVED` (a listener on `ListingStatusChangedEvent`), so they are always the values a reviewer saw.
- **Confirmation protocol.** If an edit is major and the request does not carry `confirmRemoderation=true`, nothing is applied and the server answers 409 `ERROR_REMODERATION_CONFIRMATION_REQUIRED` with the reasons (`PRICE_CHANGE_TOO_HIGH`, `CATEGORY_CHANGE`, `CONTENT_NEEDS_REVIEW`). The app shows the story's text for the price reason ("Price change >20% requires admin approval") and retries with the flag.
- **Re-review.** A confirmed major edit applies the fields, writes the history row and moves `PUBLISHED → TRUST_SAFETY_REVIEW` (new action `EDIT_FOR_REVIEW`) in one transaction; after the commit it calls `TrustSafetyReviewService.review(listingId)`. The review treats a listing that already has `published_at` as an **edit review** (see the US-084 and US-009 changes below): it never refunds, never closes the listing as `REJECTED`, and an approval returns the listing to `PUBLISHED` **without restarting its validity**.
- **Locking.** The edit and the delete take the same row lock as every other change (`findByIdAndSellerIdForUpdate`), so an edit cannot race with expiry, admin removal or a second request.
- **Soft delete.** `deleted_at` and `deleted_by` are set and the status moves to `DEACTIVATED_BY_SELLER` (action `DELETE`). Every read that serves the seller or buyers excludes rows with `deleted_at` set.

## 4. Implementation Steps

### Database Migration — `valuex-backend`
- [ ] `V23__listing_edit_and_delete.sql` (after US-006's `V22`; renumber at implementation time):
  - `listing_edit_history` (`id`, `listing_id`, `edited_by`, `changed_fields` JSONB, `requires_remoderation`, `edited_at`) with an index on `(listing_id, edited_at)`. Stores field-level before and after values only.
  - `listings.deleted_at TIMESTAMP`, `listings.deleted_by UUID`, an index for listings by seller excluding deleted rows.
  - `listings.approved_price NUMERIC(12,2)`, `listings.approved_primary_category_id UUID`.

### Backend — State Machine Changes (in US-089's table)
- [ ] `PUBLISHED → TRUST_SAFETY_REVIEW` with action `EDIT_FOR_REVIEW`.
- [ ] `DRAFT`, `PLAN_SELECTION_PENDING`, `PLAN_PAYMENT_FAILED`, `REVISION_REQUIRED` and `EXPIRED` → `DEACTIVATED_BY_SELLER` with action `DELETE` (`PUBLISHED → DEACTIVATED_BY_SELLER` already exists as `DEACTIVATE`; the delete path uses `DELETE` from every deletable state for a clear history).
- [ ] Update the US-089 plan with these rows and its tests. No other state changes.

### Backend — Edit
- [ ] Widen the editable-status check shared by US-114 and US-006 into a single `ListingEditPolicy` (editable states: `DRAFT`, `REVISION_REQUIRED`, `PUBLISHED`), used by the details, category and edit paths.
- [ ] `ListingEditService.edit(listingId, sellerId, request, confirmRemoderation)`:
  1. lock the listing for the owner; require an editable status (`ERROR_LISTING_NOT_EDITABLE`); draft states hand over to the US-114 service unchanged;
  2. validate with the same rules as US-114 (title, condition, description up to 2000, price above zero, 2 decimals, maximum from `valuex.listing.max-price`, city only for location); an empty request or one that changes nothing returns the listing with `changed = false` and writes nothing;
  3. compute `changedFields` as before and after values for only the fields that changed;
  4. decide **major**: primary category changed, or `abs(newPrice - approved_price) / approved_price > 0.20`, or the US-007 check (run when title, description or category changed) returns `UNCLEAR`. If the check returns `RESTRICTED` or `SEVERE_VIOLATION` the edit is refused with the US-007 error and nothing is applied (the check record is still stored, see below);
  5. if major and not confirmed, return 409 `ERROR_REMODERATION_CONFIRMATION_REQUIRED` with the reasons and apply nothing;
  6. apply the fields and categories (through the US-006 service), save, write the history row;
  7. if major, call `ListingLifecycleService.transition(PUBLISHED → TRUST_SAFETY_REVIEW, EDIT_FOR_REVIEW)` in the same transaction, and register an after-commit step that calls `TrustSafetyReviewService.review(listingId)`; a failure there is logged and counted, and the listing stays in review for the US-084 recovery path (Open Gaps item 8);
  8. publish `ListingEditedEvent` (listing ID, changed field names, major flag) after the commit.
- [ ] `PATCH /api/v1/listings/{listingId}` returns the updated listing, `majorEdit`, and `warnings` (empty in Sprint 2). The request gains an optional query parameter `confirmRemoderation`.
- [ ] The US-007 check record is stored even when the edit is refused or rolled back (use the same separate-transaction rule US-007 uses for drafts; confirm when building).
- [ ] A listener on `ListingStatusChangedEvent` with `toStatus = APPROVED` stores `approved_price` and `approved_primary_category_id` from the listing's current values.
- [ ] Price and category changes on a draft never count as major.

### Backend — Delete
- [ ] `ListingDeletionBlocker` interface (`Optional<DeletionBlock> check(UUID listingId)`) in the listing module; no implementation in Sprint 2. Later sprints add one each for active orders, a pending buyer payment and an open dispute; each returns the code `ERROR_CANNOT_DELETE_ACTIVE_ORDER`.
- [ ] `ListingDeletionService.delete(listingId, sellerId)`: lock for the owner; status must be deletable: `DRAFT`, `PLAN_SELECTION_PENDING`, `PLAN_PAYMENT_FAILED`, `REVISION_REQUIRED`, `PUBLISHED`, `EXPIRED`. `PLAN_PAYMENT_PENDING`, `PLAN_PAYMENT_SUCCESS`, `TRUST_SAFETY_REVIEW` and `APPROVED` answer `ERROR_LISTING_NOT_DELETABLE` ("This listing can't be deleted right now. Try again after the review is done"), because a payment or a review is in progress. Already deleted, `SOLD`, `REJECTED` and `REMOVED_BY_ADMIN` are not found or not deletable (same code). Run every blocker; the first block raises its error.
- [ ] Set `deleted_at` and `deleted_by`, transition to `DEACTIVATED_BY_SELLER` (action `DELETE`) through `ListingLifecycleService`, publish `ListingDeletedEvent` after the commit. Deleting twice is idempotent (the second call returns not found).
- [ ] `DELETE /api/v1/listings/{listingId}` returns 204. A deleted listing no longer counts toward the 50 active listings (US-008 counts statuses; `DEACTIVATED_BY_SELLER` is already excluded).
- [ ] No hard delete and no purge job in this story (Open Gaps item 5).

### Backend — My Listings
- [ ] `GET /api/v1/listings/mine?page=&size=&status=` for the authenticated seller: paged (default 20, maximum 50), newest update first, excludes deleted listings, returns for each listing id, title, price, first photo thumbnail, status, plan, `expiresAt`, and the actions the app may offer (`canEdit`, `canDelete`) computed by the same policies the edit and delete services use, so the app never guesses.
- [ ] The optional `status` filter takes one of the groups `ACTIVE` (`PUBLISHED`), `IN_PROGRESS` (draft, plan and review states, `REVISION_REQUIRED`), `ENDED` (`EXPIRED`, `SOLD`, `REJECTED`).

### Backend — Changes to Other Plans (listed so they are not missed)
- [ ] **US-084:** `TrustSafetyReviewService.review` derives an edit review when the listing has `published_at`. Edit reviews are never counted in the three attempts per plan, never produce `REJECTED` or `ListingRefundDueEvent`, and a failed edit review gives `REVISION_REQUIRED` (resubmit goes through `RESUBMIT` and is again an edit review). Add a nullable `review_reason` (`INITIAL`, `EDIT`) to the review row. The restricted-check prerequisite still applies.
- [ ] **US-009:** `ListingPublicationService.publishApprovedListing` keeps the existing `published_at` and `expires_at` when `published_at` is already set (re-approval after an edit); it only moves `APPROVED → PUBLISHED`.
- [ ] **US-115:** one more message for "your edited listing is back online" and one for "your edit needs review and your listing is hidden until then"; to be added to its message table.
- [ ] **US-089:** the two transition rows above.

### Mobile (Flutter)
No Figma frame (Open Gaps item 2). If one is supplied, follow `nova-figma-to-code`; otherwise use `valuex-mobile/docs/Flutter-Design-System.md`.
- [ ] `MyListingsScreen` under `lib/features/listing/presentation/`, reached from the Profile hub "My Listings" row (replace its coming-soon behaviour): app bar, optional segmented filter (Active, In progress, Ended), a paged list of listing cards (thumbnail, title, price, status chip with plain-language status, validity date for active ones), pull to refresh, empty state with a **Sell an item** action, loading and error with retry states.
- [ ] Per-card actions from `canEdit` and `canDelete`: an overflow menu with **Edit** and **Delete**, and **swipe to delete** on cards that can be deleted. Disabled actions show the reason in plain words (for example "Being reviewed").
- [ ] **Edit:** published listings open `ItemDetailsScreen` in edit mode (pre-filled from the listing; title, category picker, condition, description, location, price; the bottom button reads **Save changes**; no plan step). Draft and revision-required listings open the create flow at the right step (photos or Item Details).
- [ ] Edit save: call `PATCH`; on 409 `ERROR_REMODERATION_CONFIRMATION_REQUIRED`, show a confirmation sheet listing the reasons ("Price change >20% requires admin approval", "Changing the category needs a review", "This change needs a review") and the consequence ("Your listing will be hidden until it is approved"), with **Save and send for review** and **Cancel**; on confirm, repeat the call with `confirmRemoderation=true`. A minor edit shows "Changes saved" and the list updates at once.
- [ ] **Delete:** a confirmation bottom sheet with the warning ("This removes your listing from ValueX. This cannot be undone.", and, for a paid listing, "Your plan fee will not be refunded" unless product decides otherwise, Open Gaps item 4); after confirming, the card is removed and an **Undo** snackbar is shown for 2 seconds (as in the story); the delete request is sent only when the snackbar closes, so Undo needs no server call; if the app is closed during the window nothing is deleted. The duration is a single constant (2 seconds is short for some users; Open Gaps item 3). The explicit Delete menu item uses the same sheet and the same undo.
- [ ] Errors: `ERROR_LISTING_NOT_EDITABLE`, `ERROR_LISTING_NOT_DELETABLE`, `ERROR_CANNOT_DELETE_ACTIVE_ORDER`, `ERROR_REMODERATION_CONFIRMATION_REQUIRED`, `ERROR_PRICE_INVALID`, restricted item (US-007) mapped in `listing_error_messages.dart`, in English and Hindi (Hindi to be reviewed); a failed delete after the undo window puts the card back with the error.
- [ ] Tokens only; 48 dp tap targets; swipe has a menu alternative for screen readers; cards have labels with status; works at 200% text; accessibility guideline tests.

### Documentation/Quality
- [ ] OpenAPI for `PATCH` (the confirmation parameter and the 409), `DELETE` and `GET /listings/mine`.
- [ ] Update LLD Part J: stubs replaced by blockers, approved-price baseline, confirmation protocol, restricted check on edit, deletable statuses, My Listings endpoint, the US-084 edit-review behaviour. Update US-089, US-084, US-009 and US-115 plans as listed above.
- [ ] After implementation, create `Documents/Manual Testing Guides/US-010-Testing-Guide.md`.

## 5. Test Plan

Target >90% coverage for new code (`CLAUDE.md`).

### Backend Unit Tests
- [ ] Minor edit (title, description, condition, location, additional categories, price change of 20% or less): applied at once, history row with before and after values, status stays `PUBLISHED`, `ListingEditedEvent` published, no review call.
- [ ] Price change of exactly 20% is minor; above 20% is major; the baseline is the approved price (five 10% steps in a row become major on the step that crosses 20% of the approved price); a price decrease counts the same as an increase.
- [ ] Primary category change is major; changing only additional categories is minor.
- [ ] Major edit without confirmation: 409 with the right reasons, nothing applied or saved; with confirmation: applied, history row marked, `PUBLISHED → TRUST_SAFETY_REVIEW` through the lifecycle service, review called after the commit; a review call failure leaves the listing in review and is counted.
- [ ] Restricted check on edit: runs only when title, description or category changed; `RESTRICTED` refuses the edit and applies nothing; `SEVERE_VIOLATION` follows US-007; `UNCLEAR` makes the edit major; the check record is stored in all cases.
- [ ] No-op edit writes nothing; validation errors as in US-114; non-owner gets not found; non-editable statuses give `ERROR_LISTING_NOT_EDITABLE`; draft states still follow US-114.
- [ ] Delete: each deletable status transitions to `DEACTIVATED_BY_SELLER` with action `DELETE`, sets `deleted_at` and `deleted_by`, publishes the event; each blocked status gives `ERROR_LISTING_NOT_DELETABLE`; a test blocker gives `ERROR_CANNOT_DELETE_ACTIVE_ORDER`; no blockers in Sprint 2 means nothing else blocks; deleting twice is not found; non-owner is not found.
- [ ] `GET /listings/mine`: paging, order, filter groups, deleted rows excluded, `canEdit` and `canDelete` match the policies, another seller's listings never appear.
- [ ] Baseline listener stores `approved_price` and the primary category on `APPROVED` and only then.
- [ ] State machine: the new rows work, nothing else changed.
- [ ] US-084 edit review (in its own tests): approval after an edit review returns `PUBLISHED`; failure gives `REVISION_REQUIRED`; no refund event; attempts are not counted; US-009 re-publication keeps `published_at` and `expires_at`.

### Backend Integration Tests (Testcontainers PostgreSQL)
- [ ] `V23` applies on top of the previous versions.
- [ ] End to end with AI off and auto-approval: published listing, major edit confirmed → hidden (status in review) → auto-approved → `PUBLISHED` with the original validity dates; history rows complete; the listing is excluded from `isLiveForBuyers` while in review.
- [ ] Concurrent edit and delete (and an edit during expiry) on one listing: one wins, the other gets a clean error, no lost update.
- [ ] Delete end to end: the listing leaves `/listings/mine`, the 50-listing count drops, `GET /listings/{id}` returns not found for the seller.
- [ ] IDOR on `PATCH`, `DELETE` and `GET /mine`.

### Mobile Tests (Flutter)
- [ ] My Listings: loading, empty, error and retry, paging, filter, status chips, disabled actions with reasons.
- [ ] Edit: minor save; 409 confirmation sheet and retry with the flag; cancel leaves the listing unchanged; each error message shown.
- [ ] Delete: confirmation sheet, card removed, Undo within the window sends no request, no Undo sends the request when the snackbar closes, failure restores the card, closing the app during the window deletes nothing.
- [ ] Draft and revision-required Edit opens the create flow at the right step.
- [ ] Accessibility guideline tests (tap target, labels, swipe alternative) in English and Hindi, and 200% text.

## 6. Validation Checklist

- [ ] Only the owner can edit or delete; a published listing is edited under the row lock.
- [ ] A major edit can never go live without a new review; it is hidden while it waits.
- [ ] The price baseline is the last approved price, so small repeated edits cannot avoid review.
- [ ] An edit that becomes restricted content is refused.
- [ ] Re-approval after an edit never restarts the plan validity and never causes a refund or a final rejection.
- [ ] A listing with a payment in progress, in review, or (later) with orders, pending payments or disputes cannot be deleted.
- [ ] Deleted listings are kept 90 days as soft deletes, excluded from every read, with history intact.
- [ ] Every edit is in `listing_edit_history`; every status change is in `listing_status_history`.
- [ ] Edit and delete events are published for later sprints; no buyer or negotiation logic is built here.
- [ ] Brand theme and design system rules followed.
- [ ] Checkstyle, full tests, coverage, SonarQube (backend) and Flutter analyze and tests (mobile) pass before push.

## 7. Open Gaps / Questions

1. **Scope and points.** The story is 5 SP, but this plan includes the My Listings list (it does not exist yet), the confirmation protocol, the restricted check on edit and changes to the US-084 and US-009 plans. Proposed: 8 SP, or move the My Listings list to its own story. Which do you prefer?
2. **Design.** There is no Figma frame for My Listings, the delete sheet or edit mode. Is there one, or should they be built from the design system?
3. **Undo time.** The story says 2 seconds. That is short for users with motor or reading difficulties (US-110, WCAG). Keep 2 seconds, or use 5?
4. **Refund on delete.** Proposed default: no refund when a seller deletes a paid listing, shown in the confirmation. Only a failed third review refunds the plan fee. Please confirm.
5. **Purge after 90 days.** Soft-deleted rows are kept, but nothing removes them. A purge job (listing, photos in object storage, history) is not in this story. Retention rules for payments and audit may require longer. Who owns it, and which sprint?
6. **Photo edits on published listings.** Not included: adding or removing photos of a live listing. A drastic photo change is a way to change the item. Add to this story, a later story, or treat photo changes as a major edit?
7. **Active negotiations and viewers.** Nothing to notify in Sprint 2 (no buyers, chats or offers yet). This story publishes `ListingEditedEvent` and `ListingDeletedEvent`; Sprint 3 (viewers) and Sprint 4 (negotiations) subscribe and add `WARNING_BUYERS_WILL_BE_NOTIFIED` and the price-during-negotiation rule. Accepted?
8. **Re-review hand-over failure.** If the review call fails after the commit, the listing waits in review. US-084 needs a sweep for listings in review with no open review row (the US-009 hand-over recovery job has the same need); add one job covering both.
9. **Hide while re-reviewed (proposed default).** The LLD hides the whole listing until the edit is approved, which costs the seller visibility and does not pause the plan validity. A seller-friendlier option keeps the old version live while the new one is reviewed, but needs a second copy of the listing data. Keep the LLD behaviour for Sprint 2? Also, should the plan validity pause while hidden?
10. **Major edit definition.** Proposed: primary category change, or price change above 20% of the last approved price. Changes to title or description are minor unless the restricted check is unclear. Is that enough for "different item" edits?
11. **Restricted check on edit** is an addition to the LLD (which does not re-scan edits). Confirm it is wanted.
12. **New error codes** (`ERROR_LISTING_NOT_DELETABLE`, `ERROR_REMODERATION_CONFIRMATION_REQUIRED`) are not in the story text; add them to `Documents/user-stories.md` once confirmed.

---

**Status:** Draft
