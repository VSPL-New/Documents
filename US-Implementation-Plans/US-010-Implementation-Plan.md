# US-010: View/Edit/Delete My Listings — Implementation Plan

> **Update (2026-10-25, category taxonomy):** A change of the L3 category is a major edit (re-moderation) and deletes attribute values outside the new category's schema (LLD Part C); metadata edits follow the category schema; the price maximum is ₹10,00,00,000. References to a primary category or US-006's old `V22` are superseded (US-006 takes `V16`; renumber at build time). **Superseded on 2026-11-02:** the L3 category cannot be changed once a listing has gone live, so a category change is no longer a major edit for live listings.

> **Update (2026-11-02, My Listings):** the story is now **View/Edit/Delete My Listings** and includes the My Listings screen, designed in Figma Make (link in section 3). The plan gains the Figma-to-scope mapping (section 3), a richer `GET /listings/mine` (summary counts, plan name, thumbnail) and the screen's widgets and tests. Decided with the product owner on 2026-11-02: 8 SP; views, chats and Total Views show 0 until US-067 supplies data; sold listings are never deleted and stay viewable; Pause (US-124) and Relist (US-125) are separate placeholder stories and are **not built here**; card tap and thumbnails as proposed. Second round (2026-11-02): undo window of 5 seconds; no refund on delete; a major edit hides the listing while the plan validity keeps running; Delete stays as the trash button on the card (not on sold listings); a card tap opens the item details (editable when unsold, read-only with the sale details when sold, US-126); sold listings are read-only. Third round (2026-11-02): once a listing has gone live its L3 category is locked; photos can be added (10 in total) and deleted except the main photo (never below 2), with the restricted-item check on new photos; there is no AI vision suggestion for live listings; retention goes to a new archival story (US-127). What is still open is in section 7.

## 1. Header

| Field | Value |
|---|---|
| Story ID | US-010 |
| Title | View/Edit/Delete My Listings |
| Sprint | Sprint 2 — Seller Listing Creation |
| Story Points | 8 (raised from 5 on 2026-11-02 because the My Listings screen is now part of the story; the Sprint plan is updated) |
| Repos | valuex-backend, valuex-mobile |
| Dependency | US-009 (published listings, `published_at`); US-084 (re-review of edited listings); US-089 (`ListingLifecycleService`, states); US-114 and US-006 (the details and category save that this story widens to published listings); US-007 (`RestrictedItemCheckService`); US-115 (notifications); US-123 (Preview, the read-only item details). US-126 (Sold Listing Details) is a later story: sold listings cannot exist before the order sprints. Built last in Sprint 2 |

**Scope decisions (proposed 2026-10-16, to be confirmed in Open Gaps):**
1. **My Listings is part of this story** (story updated 2026-11-02 from the Figma Make "My Listings" screen). It does not exist in the app yet (the Profile row is a placeholder), so this story builds the list screen: the listing count with Active and Sold cards, All/Active/Sold chips, and a card per listing with photo, title, price, plan, status, an Edit icon and a Delete button (neither on sold listings), and a card tap that opens the item details. Boost (US-064), Pause/Activate (US-124) and Relist Item (US-125) are in the design but belong to other stories; they are not built here (mapping table in section 3). View counts, chat counts and the Total Views card are shown and read 0 until US-067 supplies the data.
2. **Edit** reuses the endpoints and the Item Details page of US-114 and US-006, in edit mode:
   - `DRAFT` and `REVISION_REQUIRED` listings: Edit opens the listing flow where the seller left off (no new endpoint, no re-review rules).
   - `PUBLISHED` listings: Edit applies title, description, condition, price, location city and the category-specific details of the listing's own category. **The L3 category cannot be changed once a listing has gone live** (`published_at` is set): `ERROR_CATEGORY_LOCKED`.
   - Photos of a `PUBLISHED` listing: add photos up to 10 in total; delete any photo except the main one (the first), never below 2 photos. There is no AI photo suggestion for live listings. New photos go through the restricted-item check.
   - Any other status cannot be edited (`ERROR_LISTING_NOT_EDITABLE`).
3. **Minor edits** apply at once. **Major edits** (a price change of more than 20% against the last approved price, or new text or photos the restricted-item check finds unclear) apply and send the listing back to the Trust & Safety review; it is **hidden from buyers until approved**, and the plan validity keeps running meanwhile. The app asks the seller to confirm before this happens.
4. **Delete** is a **soft delete** kept for 90 days, with no refund of the plan fee. It is refused while a payment is in progress, the listing is in review, or (in later sprints) it has active orders, pending payments or open disputes.
5. In Sprint 2 there are no buyers, negotiations, orders or disputes, so the "notify active negotiations or viewers" part of the story is delivered as **events** that later sprints subscribe to (Open Gaps item 7).
6. The US-009 `ListingRecoveryJob` is extended in this story to restart reviews for listings stuck in `TRUST_SAFETY_REVIEW` with no open review row (a failed hand-over after a major edit); the same gap exists after payment (US-084 plan, Open Gaps item 7).
7. **Card tap** (decided 2026-11-02): an unsold listing opens its item details, editable when the status allows (the same as the Edit icon: the listing flow for drafts and revision-required listings, `ItemDetailsScreen` in edit mode for published ones); other unsold statuses (processing payment, under review, expired, rejected) open the same details read-only with the status (US-123 preview, Open Gaps item 29); a sold listing opens read-only item details plus the sale details (US-126, a later story; until it exists the app shows its coming-soon message).

## 2. Story Recap

**As a** seller **I want to** view, edit and delete my listings **so that** I can see where each listing stands, keep information accurate and remove listings I no longer want to sell.

**Acceptance Criteria** (`Documents/user-stories.md`, updated 2026-11-02): My Listings shows how many listings I have, how many are active and sold, and the total views (0 until view counts exist); each listing shows its photo (a placeholder when none), title, price, plan, status, and its views and chats (0 until that data exists); the All, Active and Sold chips filter the list; each listing offers Edit and Delete when its status allows; sold listings stay in the list with no Edit or Delete; tapping a listing shows its item details, editable when it is not sold, and for a sold listing read-only with the sale details (US-126); saved changes show immediately and active negotiations are notified; a listing with no active orders can be deleted and is removed from the platform; one with active orders cannot be deleted and an error is shown.

**Edge Cases:** no listings yet (empty state with a way to sell an item) · no photo or a very long title · edit price during active negotiation · delete while a buyer is viewing · drastic change to a different item · delete with a pending payment · an edit that violates new platform policies.

**Validation Rules:** My Listings shows only my own non-deleted listings, newest update first, in pages · sold listings are never deleted by the seller and stay visible · cannot delete with active orders, pending payment or open disputes · major edits (price over 20%, or content the restricted check cannot clear) need re-moderation · the L3 category cannot be changed once live · a live listing keeps 2 to 10 photos and its main photo cannot be deleted · no AI photo suggestion for live listings · edit history kept for audit · deleted listings kept 90 days (soft delete).

**Error Scenarios:** `ERROR_CANNOT_DELETE_ACTIVE_ORDER` · `ERROR_PRICE_CHANGE_TOO_HIGH` ("Price change >20% requires admin approval") · `WARNING_BUYERS_WILL_BE_NOTIFIED` · `ERROR_LOADING_MY_LISTINGS` ("Unable to load your listings. Try again") · `ERROR_LISTING_NOT_EDITABLE` · `ERROR_LISTING_NOT_DELETABLE` · `ERROR_REMODERATION_CONFIRMATION_REQUIRED` · `ERROR_CATEGORY_LOCKED` · `ERROR_MAIN_PHOTO_CANNOT_BE_DELETED` (added to the story on 2026-11-02; `ERROR_MAX_PHOTOS_EXCEEDED` and `ERROR_MIN_PHOTOS_REQUIRED` already exist).

**Flutter notes (story):** Edit opens the pre-filled create flow; Delete is the trash button on each card except sold ones, with a confirmation bottom sheet with a warning and an undo for 5 seconds (no swipe-to-delete); a card tap opens the item details.

## 3. Design Reference

- Primary source: [Sprint-2-Seller Listing Creation-LLD.md — Part J](../LLD/Sprint-2-Seller%20Listing%20Creation-LLD.md#part-j---us-010-vieweditdelete-my-listings) §J.1–J.9 (updated on 2026-11-02 to match this plan).
- **Figma Make "My Listings" screen:** <https://www.figma.com/make/tzrpUwfrR0SYeyKkv1p0co/Mobile-App-UI-Design?p=f&t=eUJZNXvydJQrelSu-0> (file `tzrpUwfrR0SYeyKkv1p0co`). The table below was made from the screenshot supplied on 2026-11-02: the Figma tools were not available when this plan was written, so the file itself has not been read (Open Gaps item 24). There is no frame yet for the delete sheet, the edit mode, the empty state or the loading and error states: Edit reuses the Item Details page and the rest uses the design system.

| Element in the design | In this story? | Handling |
|---|---|---|
| Back arrow, title "My Listings", "N total listings" | Yes | `summary.total` |
| Active and Sold cards | Yes | `summary.active`, `summary.sold` (Sold stays 0 until orders exist, Sprint 5 onwards) |
| Total Views card | Yes, value 0 | `summary.totalViews`, 0 until US-067 supplies view data |
| Chips All / Active / Sold | Yes | `status` filter; the Paused chip comes with US-124 |
| Plan label (Boosted, Priority, Basic) and status badge | Yes | Plan name from the plan snapshot; badge from the status table below |
| Edit icon | Yes | `canEdit` |
| Photo, with placeholder icon | Yes | First photo; placeholder when none or when it fails to load |
| Title, price | Yes | |
| Views and chat counts | Yes, value 0 | `viewCount`, `chatCount`, 0 until US-067 and the chat stories supply data |
| Boost button | No (US-064) | Not shown; US-064 adds it to the card |
| Pause / Activate | No (US-124) | Not shown; US-124 adds them and the Paused chip |
| Relist Item | No (US-125) | Not shown; US-125 adds it to Expired cards only. Sold listings cannot be relisted, so the design's Relist Item on the Sold card is dropped |
| Delete (trash) | Yes | `canDelete`; confirmation sheet and 5-second undo; not on Sold cards |
| Card tap | Yes (product owner's rule) | Scope decision 7: editable details for unsold listings, read-only details when the status does not allow editing, sale details for Sold (US-126, later) |

**Status badges (proposed copy, English and Hindi to be reviewed, item 20):** `PUBLISHED` Active · `SOLD` Sold · `DRAFT`, `PLAN_SELECTION_PENDING`, `PLAN_PAYMENT_FAILED` Draft · `PLAN_PAYMENT_PENDING`, `PLAN_PAYMENT_SUCCESS` Processing payment · `TRUST_SAFETY_REVIEW`, `APPROVED` Under review · `REVISION_REQUIRED` Needs changes · `EXPIRED` Expired · `REJECTED` Rejected.
- Existing code to reuse: `ListingController` (`GET /{listingId}`, images), `ListingRepository.findByIdAndSellerIdForUpdate`, the US-114 details service and `ItemDetailsScreen`, the US-006 category service and picker, `ListingLifecycleService` and `ListingStatusChangedEvent` (US-089), `RestrictedItemCheckService` (US-007), `TrustSafetyReviewService` (US-084), `DomainEventPublisher`, the notification module (US-115), `MediaAssetService.createAccess` (short-lived photo read links), the Profile "My Listings" row, `ApiPage` and `ApiResponse`, `BrandGradientButton`, `ErrorView`.

**What differs from the earlier LLD Part J** (Part J and Part C were updated on 2026-11-02 and now describe all of these):
- The earlier Part J was titled Edit/Delete Listing and had **no list endpoint or screen**; this plan adds `GET /api/v1/listings/mine` and the My Listings screen.
- The LLD's `orderQueryPort`, `disputeQueryPort` and `activeViewerTracker` stubs ("always false") are replaced by a **collection of `ListingDeletionBlocker` beans**. Sprint 2 has none; Sprint 4, 5 and 8 add one each. No stubs to maintain, and no module is blocked from adding its own rule.
- Major-edit detection compares against the **last approved** price, not the previous edit, so five 10% price rises cannot slip through. The category is no longer a major-edit trigger: it cannot be changed once a listing has gone live (the earlier LLD Parts C and J treated a category change as a major edit; both were updated on 2026-11-02).
- The LLD does not re-check edited text. This plan runs the US-007 check when the title, description or photos change, because otherwise a seller could publish a clean listing and then edit it into a restricted one.
- LLD Part J does not cover photos. This plan lets a seller add photos (10 in total) and delete non-main photos of a live listing (decided 2026-11-02).
- The LLD returns the warning after the edit is applied. This plan asks for **confirmation first** (HTTP 409) so the seller is not surprised by a hidden listing.

**Key design decisions:**
- One endpoint for edits, `PATCH /api/v1/listings/{id}` (already created by US-114). The service branches on status: draft states follow US-114's rules; `PUBLISHED` follows this story's rules.
- **Baseline columns.** `listings.approved_price` is written when a listing reaches `APPROVED` (a listener on `ListingStatusChangedEvent`), so it is always the price a reviewer saw.
- **Confirmation protocol.** If an edit is major and the request does not carry `confirmRemoderation=true`, nothing is applied and the server answers 409 `ERROR_REMODERATION_CONFIRMATION_REQUIRED` with the reasons (`PRICE_CHANGE_TOO_HIGH`, `CONTENT_NEEDS_REVIEW`). The app shows the story's text for the price reason ("Price change >20% requires admin approval") and retries with the flag.
- **Re-review.** A confirmed major edit applies the fields, writes the history row and moves `PUBLISHED → TRUST_SAFETY_REVIEW` (new action `EDIT_FOR_REVIEW`) in one transaction; after the commit it calls `TrustSafetyReviewService.review(listingId)`. The review treats a listing that already has `published_at` as an **edit review** (see the US-084 and US-009 changes below): it never refunds, never closes the listing as `REJECTED`, and an approval returns the listing to `PUBLISHED` **without restarting its validity**.
- **Locking.** The edit and the delete take the same row lock as every other change (`findByIdAndSellerIdForUpdate`), so an edit cannot race with expiry, admin removal or a second request.
- **Soft delete.** `deleted_at` and `deleted_by` are set and the status moves to `DEACTIVATED_BY_SELLER` (action `DELETE`). Every read that serves the seller or buyers excludes rows with `deleted_at` set.

## 4. Implementation Steps

### Database Migration — `valuex-backend`
- [ ] `V23__listing_edit_and_delete.sql` (after US-006's `V22`; renumber at implementation time):
  - `listing_edit_history` (`id`, `listing_id`, `edited_by`, `changed_fields` JSONB, `requires_remoderation`, `edited_at`) with an index on `(listing_id, edited_at)`. Stores field-level before and after values only.
  - `listings.deleted_at TIMESTAMP`, `listings.deleted_by UUID`, an index for listings by seller excluding deleted rows.
  - `listings.approved_price NUMERIC(12,2)`.

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
  4. refuse a category change on a listing that has `published_at` (`ERROR_CATEGORY_LOCKED`); decide **major**: `abs(newPrice - approved_price) / approved_price > 0.20`, or the US-007 check (run when the title or description changed) returns `UNCLEAR`. If the check returns `RESTRICTED` or `SEVERE_VIOLATION` the edit is refused with the US-007 error and nothing is applied (the check record is still stored, see below);
  5. if major and not confirmed, return 409 `ERROR_REMODERATION_CONFIRMATION_REQUIRED` with the reasons and apply nothing;
  6. apply the fields and the category-specific details (through the US-006 service), save, write the history row;
  7. if major, call `ListingLifecycleService.transition(PUBLISHED → TRUST_SAFETY_REVIEW, EDIT_FOR_REVIEW)` in the same transaction, and register an after-commit step that calls `TrustSafetyReviewService.review(listingId)`; a failure there is logged and counted, and the listing stays in review for the US-084 recovery path (Open Gaps item 8);
  8. publish `ListingEditedEvent` (listing ID, changed field names, major flag) after the commit.
- [ ] `PATCH /api/v1/listings/{listingId}` returns the updated listing, `majorEdit`, and `warnings` (empty in Sprint 2). The request gains an optional query parameter `confirmRemoderation`.
- [ ] The US-007 check record is stored even when the edit is refused or rolled back (use the same separate-transaction rule US-007 uses for drafts; confirm when building).
- [ ] A listener on `ListingStatusChangedEvent` with `toStatus = APPROVED` stores `approved_price` from the listing's current price.
- [ ] Price changes on a draft never count as major; a draft that was never published can still change its category.

### Backend — Photos and Category on Live Listings
- [ ] "Gone live" means `listings.published_at` is set (published, paused, expired, sold, or back in review after an edit).
- [ ] **Category lock:** `ListingCategoryService` (US-006) refuses a category change when `published_at` is set (`ERROR_CATEGORY_LOCKED`, HTTP 400). A listing that was never published (a draft, or revision-required after its first review) can still change category.
- [ ] **Add a photo:** `POST /api/v1/listings/{listingId}/images` accepts a `PUBLISHED` listing of the owner: lock the listing; the total after adding is at most `Listing.MAX_PHOTOS` (`ERROR_MAX_PHOTOS_EXCEEDED`); same media checks as US-004; the new photo is appended after the existing ones, so it can never take the main position.
- [ ] The restricted-item check (US-007, which looks at photos) runs on the listing as it would be with the new photo, before the photo is attached: `RESTRICTED` or `SEVERE_VIOLATION` refuses it (US-007 error, nothing attached); `UNCLEAR` is a major edit, answered with 409 `ERROR_REMODERATION_CONFIRMATION_REQUIRED` until the request carries `confirmRemoderation=true`, then the photo is attached and the listing goes to review as in step 7 above; a clear result attaches it at once.
- [ ] **Delete a photo:** `DELETE /api/v1/listings/{listingId}/images/{imageId}` accepts a `PUBLISHED` listing of the owner: the main photo (the lowest sort position) is refused with `ERROR_MAIN_PHOTO_CANNOT_BE_DELETED`; the delete must leave at least `Listing.MIN_PHOTOS` (`ERROR_MIN_PHOTOS_REQUIRED`); no restricted check and not a major edit. The remaining photos keep their order.
- [ ] Photo adds and deletes write `listing_edit_history` rows and publish `ListingEditedEvent`.
- [ ] **No AI photo suggestion for live listings:** `POST /ai-suggestions` already refuses any listing that is not a `DRAFT` (`LISTING_NOT_IN_DRAFT`), so live listings never reach the vision model; keep that guard and add a regression test. The app shows no AI controls when editing a live listing.
- [ ] No reordering and no change of the main photo on live listings (Open Gaps item 30).

### Backend — Delete
- [ ] `ListingDeletionBlocker` interface (`Optional<DeletionBlock> check(UUID listingId)`) in the listing module; no implementation in Sprint 2. Later sprints add one each for active orders, a pending buyer payment and an open dispute; each returns the code `ERROR_CANNOT_DELETE_ACTIVE_ORDER`.
- [ ] `ListingDeletionService.delete(listingId, sellerId)`: lock for the owner; status must be deletable: `DRAFT`, `PLAN_SELECTION_PENDING`, `PLAN_PAYMENT_FAILED`, `REVISION_REQUIRED`, `PUBLISHED`, `EXPIRED`. `PLAN_PAYMENT_PENDING`, `PLAN_PAYMENT_SUCCESS`, `TRUST_SAFETY_REVIEW` and `APPROVED` answer `ERROR_LISTING_NOT_DELETABLE` ("This listing can't be deleted right now. Try again after the review is done"), because a payment or a review is in progress. Already deleted listings are not found; `SOLD` (sold listings are never deleted by the seller, decided 2026-11-02), `REJECTED` and `REMOVED_BY_ADMIN` give `ERROR_LISTING_NOT_DELETABLE`. Run every blocker; the first block raises its error.
- [ ] Set `deleted_at` and `deleted_by`, transition to `DEACTIVATED_BY_SELLER` (action `DELETE`) through `ListingLifecycleService`, publish `ListingDeletedEvent` after the commit. Deleting twice is idempotent (the second call returns not found).
- [ ] `DELETE /api/v1/listings/{listingId}` returns 204. A deleted listing no longer counts toward the 50 active listings (US-008 counts statuses; `DEACTIVATED_BY_SELLER` is already excluded).
- [ ] No hard delete and no purge job in this story (Open Gaps item 5).

### Backend — My Listings
- [ ] `GET /api/v1/listings/mine?page=&size=&status=` for the authenticated seller: paged (default 20, maximum 50), newest update first, excludes deleted listings. The optional `status` filter takes `ACTIVE` (`PUBLISHED`) or `SOLD`, matching the chips; without it every non-deleted listing is returned, so drafts, review and revision states, and expired or rejected listings appear under All with their own badge.
- [ ] Response: `summary` (`total`, `active`, `sold`, `totalViews`) counted over all of the seller's non-deleted listings whatever the page or filter, and `items`: id, title, price, status, `planName` (from the US-008 plan snapshot, null before a plan is chosen), `expiresAt`, `updatedAt`, `viewCount`, `chatCount`, `thumbnailUrl` and `thumbnailExpiresAt` (first photo by sort order, null when there is none), `canEdit`, `canDelete`, and `editBlockedReason` / `deleteBlockedReason` codes when false so the app can say why. The actions come from the same policies the edit and delete services use, so the app never guesses. A `SOLD` listing has neither action (the app hides them rather than disabling them).
- [ ] Thumbnail (decided 2026-11-02): a short-lived read link for the first photo from `MediaAssetService.createAccess`, never a public storage URL; shared with US-123.
- [ ] `totalViews`, `viewCount` and `chatCount` are 0 for now, set in one place that US-067 and the chat stories replace with real data, so the response shape does not change later.

### Backend — Changes to Other Plans (listed so they are not missed)
- [ ] **US-084:** `TrustSafetyReviewService.review` derives an edit review when the listing has `published_at`. Edit reviews are never counted in the three attempts per plan, never produce `REJECTED` or `ListingRefundDueEvent`, and a failed edit review gives `REVISION_REQUIRED` (resubmit goes through `RESUBMIT` and is again an edit review). Add a nullable `review_reason` (`INITIAL`, `EDIT`) to the review row. The restricted-check prerequisite still applies.
- [ ] **US-009:** `ListingPublicationService.publishApprovedListing` keeps the existing `published_at` and `expires_at` when `published_at` is already set (re-approval after an edit); it only moves `APPROVED → PUBLISHED`.
- [ ] **US-115:** one more message for "your edited listing is back online" and one for "your edit needs review and your listing is hidden until then"; to be added to its message table.
- [ ] **US-089:** the two transition rows above.
- [ ] **US-009 / US-084 recovery job:** extend `ListingRecoveryJob` to find listings in `TRUST_SAFETY_REVIEW` with no open review row and call `TrustSafetyReviewService.review` again, with the existing retry limit and alert.
- [ ] **US-004:** the image attach and delete endpoints accept `PUBLISHED` listings under the live-listing rules above.
- [ ] **US-006:** `ListingCategoryService` refuses category changes once `published_at` is set, and the category picker is read-only when editing a live listing; update the US-006 plan (LLD Part C is already updated).
- [ ] **US-007:** `RestrictedItemCheckService` also checks a live listing as it would be after the change (candidate text and photos) instead of requiring a draft; the check record is stored as for drafts.
- [ ] **US-005:** no code change; the existing `DRAFT`-only guard on AI suggestions is covered by a new regression test.

### Mobile (Flutter)
Follow the Figma Make My Listings screen (link in section 3). Per `nova-figma-to-code`: get fresh design context from the Figma file, check `.figma/mapping.json` for drift and add the My Listings mapping before coding; the screenshot alone is not enough to implement from (Open Gaps item 24). Without the design context, use `valuex-mobile/docs/Flutter-Design-System.md`.
- [ ] `MyListingsScreen` under `lib/features/listing/presentation/`, reached from the Profile hub "My Listings" row (replace its coming-soon behaviour): back arrow, title and "N total listings", Active, Sold and Total Views summary cards (Total Views reads 0), All/Active/Sold chips, a paged list of cards (plan name and status badge, edit icon, photo with a placeholder icon when none or when it fails to load, title, price, views and chat counts reading 0, delete button), pull to refresh, an empty state with a **Sell an item** action (a short message when only the filter is empty), loading and error with retry states (`ERROR_LOADING_MY_LISTINGS`). Small reusable widgets for the summary card, the filter chips and the listing card in `lib/features/listing/presentation/widgets/`.
- [ ] Only the actions that exist are shown: the Edit icon (`canEdit`) and the Delete button (`canDelete`). Sold cards show neither and have no action row. No placeholders for Boost, Pause, Activate or Relist (US-064, US-124 and US-125 add them). A disabled action says why in plain words (for example "Being reviewed") from the `editBlockedReason` and `deleteBlockedReason` codes.
- [ ] **Card tap** (scope decision 7): an editable unsold listing opens the Edit destination; another unsold listing opens the read-only details with a status banner (US-123); a sold listing opens the sale details (US-126) or, until it exists, the app's coming-soon message.
- [ ] **Edit:** published listings open `ItemDetailsScreen` in edit mode (pre-filled from the listing; title, condition, description, location, price and the category-specific details; the category is shown read-only because it is locked once live; the bottom button reads **Save changes**; no plan step; no AI suggestion controls). Draft and revision-required listings open the create flow at the right step (photos or Item Details).
- [ ] **Photos of a live listing** (reuse the US-004 photo widgets in edit mode): the main photo carries a **Main** label and no delete control; other photos have a delete control while more than 2 remain; an **Add photos** control shows "n of 10" and disappears at 10; a new photo the restricted check finds unclear shows the same confirmation sheet as other major edits; no reordering.
- [ ] Edit save: call `PATCH`; on 409 `ERROR_REMODERATION_CONFIRMATION_REQUIRED`, show a confirmation sheet listing the reasons ("Price change >20% requires admin approval", "Changing the category needs a review", "This change needs a review") and the consequence ("Your listing will be hidden until it is approved. Your plan keeps running meanwhile"), with **Save and send for review** and **Cancel**; on confirm, repeat the call with `confirmRemoderation=true`. A minor edit shows "Changes saved" and the list updates at once.
- [ ] **Delete:** a reusable confirmation bottom sheet with the warning ("This removes your listing from ValueX. This cannot be undone." and, for a paid listing, "Your plan fee will not be refunded"), shown by the trash button on the card. After confirming, the card is removed and an **Undo** snackbar is shown for 5 seconds (one constant); the delete request is sent only when the snackbar closes, so Undo needs no server call; if the app is closed during the window nothing is deleted. No swipe-to-delete.
- [ ] Errors: `ERROR_LISTING_NOT_EDITABLE`, `ERROR_LISTING_NOT_DELETABLE`, `ERROR_CANNOT_DELETE_ACTIVE_ORDER`, `ERROR_REMODERATION_CONFIRMATION_REQUIRED`, `ERROR_CATEGORY_LOCKED`, `ERROR_MAIN_PHOTO_CANNOT_BE_DELETED`, `ERROR_MAX_PHOTOS_EXCEEDED`, `ERROR_MIN_PHOTOS_REQUIRED`, `ERROR_PRICE_INVALID`, restricted item (US-007) mapped in `listing_error_messages.dart`, in English and Hindi (Hindi to be reviewed); a failed delete after the undo window puts the card back with the error.
- [ ] Tokens only; 48 dp tap targets for the edit icon, the delete button and the card; cards have labels with plan and status; the chips announce which one is selected; works at 200% text and in Hindi; accessibility guideline tests.

### Documentation/Quality
- [ ] OpenAPI for `PATCH` (the confirmation parameter and the 409), `DELETE` and `GET /listings/mine`.
- [x] Update LLD Part J (its title and the contents link become View/Edit/Delete My Listings): blockers instead of stubs, approved-price baseline, confirmation protocol, restricted check on edit, deletable statuses, My Listings endpoint and screen, photos and the category lock, the US-084 edit-review behaviour. Done on 2026-11-02, together with LLD Part C (`ERROR_CATEGORY_LOCKED`). Still to do while building: update the US-089, US-084, US-009, US-115, US-004, US-006 and US-007 plans as listed above.
- [ ] After implementation, create `Documents/Manual Testing Guides/US-010-Testing-Guide.md`.

## 5. Test Plan

Target >90% coverage for new code (`CLAUDE.md`).

### Backend Unit Tests
- [ ] Minor edit (title, description, condition, location, category-specific details, price change of 20% or less): applied at once, history row with before and after values, status stays `PUBLISHED`, `ListingEditedEvent` published, no review call.
- [ ] Price change of exactly 20% is minor; above 20% is major; the baseline is the approved price (five 10% steps in a row become major on the step that crosses 20% of the approved price); a price decrease counts the same as an increase.
- [ ] A category change on a listing with `published_at` (published, expired, back in review) is refused with `ERROR_CATEGORY_LOCKED` and changes nothing; a draft that was never published can still change its category.
- [ ] Major edit without confirmation: 409 with the right reasons, nothing applied or saved; with confirmation: applied, history row marked, `PUBLISHED → TRUST_SAFETY_REVIEW` through the lifecycle service, review called after the commit; a review call failure leaves the listing in review and is counted.
- [ ] Restricted check on edit: runs only when title, description or a new photo changed; `RESTRICTED` refuses the edit and applies nothing; `SEVERE_VIOLATION` follows US-007; `UNCLEAR` makes the edit major; the check record is stored in all cases.
- [ ] No-op edit writes nothing; validation errors as in US-114; non-owner gets not found; non-editable statuses give `ERROR_LISTING_NOT_EDITABLE`; draft states still follow US-114.
- [ ] Delete: each deletable status transitions to `DEACTIVATED_BY_SELLER` with action `DELETE`, sets `deleted_at` and `deleted_by`, publishes the event; each blocked status (including `SOLD`) gives `ERROR_LISTING_NOT_DELETABLE`; a test blocker gives `ERROR_CANNOT_DELETE_ACTIVE_ORDER`; no blockers in Sprint 2 means nothing else blocks; deleting twice is not found; non-owner is not found.
- [ ] `GET /listings/mine`: paging, order, the `ACTIVE` and `SOLD` filters, summary counts (including `totalViews` 0) independent of page and filter, `viewCount` and `chatCount` 0, deleted rows excluded, a `SOLD` listing is listed with neither action, plan name null before a plan is chosen, a thumbnail link only when a photo exists, `canEdit`, `canDelete` and the blocked reasons match the policies, another seller's listings never appear.
- [ ] Baseline listener stores `approved_price` on `APPROVED` and only then.
- [ ] Photos on a live listing: adding up to 10 in total works and appends after the main photo; the 11th gives `ERROR_MAX_PHOTOS_EXCEEDED`; the main photo cannot be deleted; a non-main photo can be deleted, but not when only 2 remain (`ERROR_MIN_PHOTOS_REQUIRED`); a new photo runs the restricted check first (clear: attached at once; restricted: refused and nothing attached; unclear: 409 until confirmed, then attached and the listing goes to review); deletes are not major edits; history rows are written; non-owners and non-`PUBLISHED` listings are refused; `POST /ai-suggestions` on a live listing is refused with no gateway call.
- [ ] State machine: the new rows work, nothing else changed.
- [ ] Recovery job: a listing in `TRUST_SAFETY_REVIEW` with no open review row gets its review started; one with an open review is left alone; failures follow the existing retry limit and alert.
- [ ] US-084 edit review (in its own tests): approval after an edit review returns `PUBLISHED`; failure gives `REVISION_REQUIRED`; no refund event; attempts are not counted; US-009 re-publication keeps `published_at` and `expires_at`.

### Backend Integration Tests (Testcontainers PostgreSQL)
- [ ] `V23` applies on top of the previous versions.
- [ ] End to end with AI off and auto-approval: published listing, major edit confirmed → hidden (status in review) → auto-approved → `PUBLISHED` with the original validity dates; history rows complete; the listing is excluded from `isLiveForBuyers` while in review.
- [ ] Concurrent edit and delete (and an edit during expiry) on one listing: one wins, the other gets a clean error, no lost update.
- [ ] Delete end to end: the listing leaves `/listings/mine`, the 50-listing count drops, `GET /listings/{id}` returns not found for the seller.
- [ ] IDOR on `PATCH`, `DELETE`, `GET /mine` and the image endpoints of a live listing.
- [ ] Photo end to end on a published listing: add, delete, and the main-photo, 10-photo and 2-photo limits; the media of a deleted photo is removed.

### Mobile Tests (Flutter)
- [ ] My Listings: loading, empty (no listings, and an empty filter), error and retry, paging, summary cards, All/Active/Sold chips, plan and status badges for every status, photo and placeholder (no photo and a failed load), a long title and a large price at 320 wide and 2x text in English and Hindi, edit icon and delete button shown or disabled with reasons, a Sold card with neither, the card tap for each kind of listing (editable details, read-only details, sold details or the coming-soon message), views, chats and Total Views reading 0, and no Boost, Pause or Relist controls.
- [ ] Edit: minor save; 409 confirmation sheet and retry with the flag; cancel leaves the listing unchanged; each error message shown.
- [ ] Delete: confirmation sheet, card removed, Undo within the window sends no request, no Undo sends the request when the snackbar closes, failure restores the card, closing the app during the window deletes nothing.
- [ ] Draft and revision-required Edit opens the create flow at the right step.
- [ ] Live listing edit: the category is read-only; the main photo has no delete control; other photos can be deleted down to 2; Add photos is hidden at 10; an unclear new photo shows the confirmation sheet; no AI controls.
- [ ] Accessibility guideline tests (tap target, labels, selected chip state) in English and Hindi, and 200% text.

## 6. Validation Checklist

- [ ] My Listings shows only the seller's own non-deleted listings, with summary counts that match, and nothing that belongs to other stories (no Boost, Pause or Relist; views, chats and Total Views read 0).
- [ ] Sold listings stay in My Listings and cannot be edited or deleted.
- [ ] A card tap opens the right screen for each status: editable details, read-only details, or (later) the sold details.
- [ ] The plan validity keeps running while a listing is hidden for re-review.
- [ ] The screen matches the Figma Make design for the parts in scope.
- [ ] Only the owner can edit or delete; a published listing is edited under the row lock.
- [ ] A major edit can never go live without a new review; it is hidden while it waits.
- [ ] The price baseline is the last approved price, so small repeated edits cannot avoid review.
- [ ] An edit or a new photo that becomes restricted content is refused.
- [ ] The L3 category of a listing that has gone live can never be changed.
- [ ] A live listing keeps 2 to 10 photos and its main photo cannot be deleted.
- [ ] No AI vision suggestion call is possible for a live listing.
- [ ] Re-approval after an edit never restarts the plan validity and never causes a refund or a final rejection.
- [ ] A listing with a payment in progress, in review, or (later) with orders, pending payments or disputes cannot be deleted.
- [ ] Deleted listings are kept 90 days as soft deletes, excluded from every read, with history intact.
- [ ] Every edit is in `listing_edit_history`; every status change is in `listing_status_history`.
- [ ] Edit and delete events are published for later sprints; no buyer or negotiation logic is built here.
- [ ] Brand theme and design system rules followed.
- [ ] Checkstyle, full tests, coverage, SonarQube (backend) and Flutter analyze and tests (mobile) pass before push.

## 7. Open Gaps / Questions

1. **Resolved (2026-11-02): 8 SP.** The My Listings list is part of the story, so it is 8 SP; the Sprint plan (US-010 8, Sprint 2 78, total 696) is updated.
2. **Resolved (2026-11-02):** the delete sheet, edit mode, empty, loading and error states are built from the design system and tokens. (The Figma file itself is still unread, item 24.)
3. **Resolved (2026-11-02): the undo window is 5 seconds.**
4. **Resolved (2026-11-02): no refund** when a seller deletes a paid listing; the confirmation sheet says so. Only a failed third review refunds the plan fee.
5. **Resolved (2026-11-02): purge and retention** are handled by the archival story US-127 (placeholder drafted, proposed Sprint 10). No purge job in this story.
6. **Resolved (2026-11-02): photo edits on live listings are part of this story**, with no separate story: add photos up to 10 in total, delete any but the main photo (never below 2), restricted check on new photos (an unclear result is a major edit), no AI vision suggestion.
7. **Resolved (2026-11-02):** this story publishes `ListingEditedEvent` and `ListingDeletedEvent`; Sprint 3 (viewers) and Sprint 4 (negotiations) subscribe and add `WARNING_BUYERS_WILL_BE_NOTIFIED` and the price-during-negotiation rule.
8. **Resolved (2026-11-02):** the existing recovery job (US-009) is extended in this story to restart stuck reviews (scope decision 6).
9. **Resolved (2026-11-02):** a major edit hides the whole listing until the Trust & Safety review approves it; the plan validity keeps running meanwhile.
10. **Resolved (2026-11-02): major edit** means a price change above 20% of the last approved price; a title, description or new-photo change is major only when the restricted check is unclear. The category cannot be changed once a listing is live.
11. **Resolved (2026-11-02):** the restricted check runs when the title, description or photos of a live listing change; every major edit goes to the Trust & Safety review again.
12. **Resolved (2026-11-02):** `ERROR_LISTING_NOT_EDITABLE`, `ERROR_LISTING_NOT_DELETABLE`, `ERROR_REMODERATION_CONFIRMATION_REQUIRED` and `ERROR_LOADING_MY_LISTINGS` are in the story text.
13. **Resolved (2026-11-02): views, chats and Total Views show 0** (not hidden) until US-067 and the chat stories supply data. Shown as `0`; the design's two-digit style is not needed.
14. **Boost button.** Belongs to US-064 (Upgrade Listing Plan, enhancement backlog). Not shown in this story; US-064 adds it to the card when built.
15. **Resolved (2026-11-02): Pause/Activate and Relist Item** are drafted as placeholder stories US-124 (Pause and Resume Listing) and US-125 (Relist Listing) in `Documents/user-stories.md`; not built here. See item 23 for the interpretations to confirm.
16. **Resolved (2026-11-02): sold listings are never deleted.** They stay in My Listings, can be viewed like any other listing (US-123 now covers sold, paused and expired listings), and show no Edit icon; their details page offers no Edit or Delete.
17. **Resolved (2026-11-02): card tap** per scope decision 7: editable details for unsold listings, read-only details for unsold listings that cannot be edited, sale details for sold ones (US-126).
18. **Resolved (2026-11-02): thumbnails** come from the list response as a short-lived `thumbnailUrl` built with `MediaAssetService.createAccess` for the first photo.
19. **Resolved (2026-11-02): no swipe-to-delete.** Delete is the trash button on the card, as in the design, except on sold listings.
20. **Resolved (2026-11-02): status labels** as proposed in section 3; Hindi to be reviewed.
21. **Resolved (2026-11-02): card layout** as in the design: the Edit icon at the top right and the trash button at the bottom; Boost, Pause and Relist buttons join the bottom row when their stories are built; sold cards have no action row.
22. **Resolved (2026-11-02): "N total listings"** counts every non-deleted listing, including drafts and rejected ones; Active counts published listings only.
23. **US-124 and US-125 interpretations (corrected 2026-11-02).** Recorded from your answers: (a) Pause warns that the plan validity keeps running, Activate works only within validity, and a paused listing past expiry becomes Expired; (b) Relist Item is shown on Expired cards only; sold listings cannot be relisted; (c) an unsold Expired listing is relisted by buying a plan and is published with no review and no restricted-item check. Both stories also need US-089 changes (a Paused state, an Expired to Published path) and have no sprint or points yet.
24. **Figma Make file not read.** The Figma tools were not available while writing this plan, so the mapping in section 3 comes from the screenshot. Before coding the screen, fetch the design context from the link and follow `nova-figma-to-code` (mapping, drift check); card layout, plan colours and chip styles may differ from what the screenshot shows.
25. **Resolved (2026-11-02): Delete** is the trash button on the card, as in the design, and is not offered on sold listings. The View Details button idea is dropped; the card tap opens the details (item 17).
26. **US-126 (Sold Listing Details).** Drafted as a placeholder with the sale details you listed (order, payout, buyer identity, key dates, shipping and after-sale items). It needs order, payout and shipping data, so it is not part of Sprint 2 and has no sprint or points yet (proposed Sprint 6 or later). Open: how much buyer identity to show (proposed: name and city only) and whether it is one page with the US-123 preview.
27. **Resolved (2026-11-02): archival story** drafted as the placeholder US-127 (Listing Archival and Retention), proposed Sprint 10.
28. **Resolved (2026-11-02): no separate photo-edit story**; photo rules are part of this story (item 6).
29. **Resolved (2026-11-02):** an unsold listing that cannot be edited (processing payment, under review, expired, rejected) opens the same details read-only with a status banner.
30. **Resolved (2026-11-02):** live listings cannot delete the main photo, reorder photos or pick another main photo in this story.
31. **Resolved (2026-11-02):** "gone live" means `published_at` is set, so the category stays locked for published, paused, expired, sold and back-in-review listings; a listing that was never published (revision-required after its first review) can still change category.

---

**Status:** Approved (by the product owner, 2026-11-02)
