# US-010 — View, Edit and Delete My Listings: QA Testing Guide

**Sprint 2 · Seller Listing Creation**

Manual test cases for My Listings (the seller's own listings with counts and filters), editing a listing that is live
(minor and major edits, photos, the locked category, refused text), and deleting a listing (soft delete with a five second
undo). The dummy gateway is used; no money is charged.

> **What ships:** migration `V24` (`listing_edit_history`, `listings.deleted_at`, `deleted_by`, `approved_price`);
> `GET /api/v1/listings/mine`; `PATCH /api/v1/listings/{id}` (now also for live listings, with `confirmRemoderation`,
> `addMediaIds` and `removeImageIds`); `DELETE /api/v1/listings/{id}`; `ListingEditService`, `ListingDeletionService`,
> `MyListingsService`, the edit and delete policies, `ListingEditedEvent` and `ListingDeletedEvent`; the restricted-item
> check also runs for a listing sent back for revision; the app screens My Listings (`/profile/listings`) and Item Details in
> edit mode.
> **Not in this story:** views, chats and Total Views (they read 0 until US-067), Pause and Relist (US-124, US-125), sale
> details of a sold listing (US-126, the app says "Sale details are coming soon"), the read-only page for a listing in review
> (US-123 now opens the read-only preview, see `US-123-Testing-Guide.md`), buyers, orders and negotiations, purging deleted listings after 90 days (US-127).

| Setting | Value |
|---|---|
| Backend base URL | `http://localhost:8080` |
| Migration | `V24` (Flyway runs on start) |
| Gateway | `PAYMENT_PROVIDER=mock` (default in `dev`); see `US-117-Testing-Guide.md` |
| Review mode | `MODERATION_MANUAL_REVIEW_ENABLED=false` (default): a major edit is approved again at once. `true`: it waits in the queue and the listing stays hidden |
| Rules | A price more than 20% away from the **last approved** price is a major edit; so is any added photo and text that needs a review. The category is locked once a listing has been published. A live listing keeps 2 to 10 photos and its main photo cannot be removed. Undo window 5 seconds |
| Errors | `ERROR_LISTING_NOT_EDITABLE` · `ERROR_LISTING_NOT_DELETABLE` · `ERROR_REMODERATION_CONFIRMATION_REQUIRED` (409) · `ERROR_CATEGORY_LOCKED` · `ERROR_MAIN_PHOTO_CANNOT_BE_DELETED` · `ERROR_MAX_PHOTOS_EXCEEDED` · `ERROR_MIN_PHOTOS_REQUIRED` · `ERROR_PHOTOS_NOT_EDITABLE` · `ERROR_INVALID_LISTING_FILTER` · `ERROR_RESTRICTED_ITEM` · `LISTING_NOT_FOUND` (404) |

---

## Prerequisites

1. PostgreSQL and Redis from `valuex-backend/docker-compose.yml`; start the backend (`mvn spring-boot:run`).
2. Two `ACTIVE` sellers with Aadhaar verified and tokens: `$TOKEN` (seller A) and `$TOKEN_B` (seller B).
3. A **published** listing of seller A with at least 3 photos and a phone category (`US-006-Testing-Guide.md` for the draft,
   `US-008-Testing-Guide.md` to choose the plan, `US-009-Testing-Guide.md` to pay it; with `UPDATE plans SET discounted_price = 0
   WHERE code = 'BASIC'` and the `BASIC` plan it publishes without a payment). Note its id as `$LISTING` and its price (for
   example 500) as `$PRICE`.
4. The current details of that listing as the app sends them, saved to a file `edit.json`, for example:

```json
{ "title": "Hero cycle", "condition": "GOOD", "conditionNotes": "Small scratch", "description": "Lightly used",
  "price": 500, "negotiable": true, "quantity": 1, "location": "Pune",
  "attributes": { "brand": "Apple", "model": "X", "storage_gb": "64 GB" } }
```

Edit it for each case and send it with:

```powershell
curl.exe -s -X PATCH "http://localhost:8080/api/v1/listings/$LISTING" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" --data-binary "@edit.json"
```

Useful queries:

```sql
SELECT status, price, approved_price, published_at, expires_at, deleted_at, deleted_by FROM listings WHERE id = '<id>';
SELECT action, from_status, to_status, reason FROM listing_status_history WHERE listing_id = '<id>' ORDER BY changed_at;
SELECT changed_fields, requires_remoderation, edited_at FROM listing_edit_history WHERE listing_id = '<id>' ORDER BY edited_at;
SELECT review_reason, attempt_number, auto_decision, admin_decision FROM listing_trust_safety_reviews WHERE listing_id = '<id>' ORDER BY created_at;
SELECT id, sort_order, media_asset_id FROM listing_images WHERE listing_id = '<id>' ORDER BY sort_order;
SELECT result, matched_policy_codes FROM listing_moderation_checks WHERE listing_id = '<id>' ORDER BY created_at;
```

---

## Test cases: backend

| ID | Acceptance criterion / edge case | Steps | Expected |
|---|---|---|---|
| TC-001 | Migration | `SELECT version FROM flyway_schema_history WHERE version = '24';` | One successful row; `listing_edit_history` exists; `listings` has `deleted_at`, `deleted_by`, `approved_price` |
| TC-002 | Approved price is remembered | Publish a listing (prerequisite 3) | `approved_price` equals the price at approval; a listing that was already live before `V24` got its price as the baseline |
| TC-003 | My Listings counts | `GET /api/v1/listings/mine` as seller A | `summary.total` counts every non-deleted listing of A, `active` counts `PUBLISHED` only, `sold` counts `SOLD`, `totalViews` is 0; `items` newest update first; each item has `planName`, `viewCount` 0, `chatCount` 0, `canEdit`, `canDelete` |
| TC-004 | Filters | `?status=ACTIVE`, `?status=SOLD`, `?status=DRAFT` | Only published / only sold listings; the summary does not change with the filter; `DRAFT` gives 400 `ERROR_INVALID_LISTING_FILTER` |
| TC-005 | Paging | `?size=1&page=0`, `?size=500`, `?page=-3` | One item and `hasNext` true when more exist; the size is capped at 50; a negative page reads as the first page |
| TC-006 | Only my listings | Call as seller B | B's own listings only; none of A's |
| TC-007 | Thumbnail | Item with photos; item without | A short-lived `thumbnailUrl` with `thumbnailExpiresAt` for the first photo; both null when there is no photo |
| TC-008 | Actions per status | Look at a published, a draft, a listing in review (`UPDATE listings SET status = 'TRUST_SAFETY_REVIEW'` on a copy) and a sold one (`SET status = 'SOLD'`) | Published and draft: `canEdit` and `canDelete` true. In review: both false, reasons `UNDER_REVIEW`. Sold: both false, reasons `SOLD` |
| TC-009 | Minor edit | Change the title and set the price to 550 (10%) | 200; status stays `PUBLISHED`; one `listing_edit_history` row with `price` and `title` before and after and `requires_remoderation` false; no new review row |
| TC-010 | Exactly 20% is minor | Price 600 against an approved 500 | 200, `PUBLISHED`, no review |
| TC-011 | Over 20% needs confirmation | Price 601 (or 399) | 409 `ERROR_REMODERATION_CONFIRMATION_REQUIRED`, `details.reasons` `PRICE_CHANGE_TOO_HIGH`; the price in the database is unchanged and there is no history row |
| TC-012 | Confirmed major edit | Repeat TC-011 with `?confirmRemoderation=true` | 200, response `status` `TRUST_SAFETY_REVIEW`; history row with `requires_remoderation` true; status history `EDIT_FOR_REVIEW`; with auto review the listing is `PUBLISHED` again within moments |
| TC-013 | Validity keeps running | After TC-012 | `published_at` and `expires_at` are the same as before; `approved_price` now equals the new price; review rows `INITIAL` then `EDIT`; no refund row; the three-attempt count is unaffected |
| TC-014 | Hidden while waiting | Run TC-012 with `MODERATION_MANUAL_REVIEW_ENABLED=true` | The listing stays `TRUST_SAFETY_REVIEW` (not live for buyers) until the review is approved; the plan validity dates do not change |
| TC-015 | Baseline is the approved price | Edit 500 to 580 (16%), then 580 to 620 | The second edit is 24% from the approved 500, so it is major, although it is only 7% from 580 |
| TC-016 | No change | Send `edit.json` unchanged | 200; no history row; no status change |
| TC-017 | Text the rules refuse | Title "Old Monk rum and red wine" | 400 `ERROR_RESTRICTED_ITEM`; the title is unchanged; a `listing_moderation_checks` row `RESTRICTED` is stored |
| TC-018 | Severe text | A severely prohibited title | 400 `ERROR_ACCOUNT_SUSPENDED`; nothing applied; the check is stored and the account is flagged for review (as for a draft) |
| TC-019 | Text that needs a review | A description that newly matches a Conditional policy (keywords in `US-007-Testing-Guide.md`) | 409 with `CONTENT_NEEDS_REVIEW` the first time; a policy the seller has already agreed to on this listing does not make an edit major; the policy is never agreed to for the seller (no `listing_compliance_acceptances` row is added for it) |
| TC-020 | Category is locked | `PUT /api/v1/listings/$LISTING/category` with another leaf | 400 `ERROR_CATEGORY_LOCKED`; setting the same category is accepted; a listing that was never published can still change category |
| TC-021 | Add a photo | `edit.json` plus `"addMediaIds": ["<ready media id>"]` (upload it first as in `US-004-Testing-Guide.md`, owner type `LISTING`) | 409 with `PHOTOS_ADDED`; with `?confirmRemoderation=true` the photo is added after the existing ones and the edit is major |
| TC-022 | Remove a photo | `"removeImageIds": ["<second photo image id>"]` | 200; `listing_images` has one fewer row, positions are 0..n-1 in order; not a major edit; the media asset is deleted; history `photos` `{"added":0,"removed":1}` |
| TC-023 | Main photo stays | `"removeImageIds"` with the first photo | 400 `ERROR_MAIN_PHOTO_CANNOT_BE_DELETED`; nothing changed |
| TC-024 | Never below 2 | Remove photos until two remain, then one more | 400 `ERROR_MIN_PHOTOS_REQUIRED` |
| TC-025 | At most 10 | Add photos until the total would be 11 | 400 `ERROR_MAX_PHOTOS_EXCEEDED` |
| TC-026 | Foreign photo | `removeImageIds` with an id of another listing | 404 `LISTING_IMAGE_NOT_FOUND` |
| TC-027 | Photo fields on a draft | Send `addMediaIds` for a draft listing | 400 `ERROR_PHOTOS_NOT_EDITABLE` (a draft uses the photo endpoints of US-004) |
| TC-028 | No AI for live listings | `POST /api/v1/listings/$LISTING/ai-suggestions` | 400 `LISTING_NOT_IN_DRAFT`; no call to the AI service |
| TC-029 | Not editable statuses | `PATCH` a listing in review, sold, expired, or waiting for payment | 400 `ERROR_LISTING_NOT_EDITABLE` |
| TC-030 | Ownership | Seller B sends the `PATCH`, the `DELETE`, and the category call for A's listing; no token | 404 `LISTING_NOT_FOUND`; 401 |
| TC-031 | Sent back for revision | With manual review on, reject the edit review (service `requestRevision`); edit the text; call `POST /restricted-check`; then `POST /trust-safety-review` | The edit and the check are accepted for a listing in `REVISION_REQUIRED`; the resubmission goes to review (`RESUBMIT`) without a payment |
| TC-032 | Delete | `DELETE /api/v1/listings/$LISTING` | 204; status `DEACTIVATED_BY_SELLER`, `deleted_at` and `deleted_by` set; status history action `DELETE`; no payment or refund row is touched (no refund of the plan fee) |
| TC-033 | Deleted is gone | After TC-032: `GET /listings/$LISTING`, `GET /listings/mine`, `PATCH`, `DELETE` again | 404 for the first, the third and the fourth; the list no longer has it and the counts drop; the row still exists in the database |
| TC-034 | Deletable statuses | Delete a draft, a listing waiting for a plan, one with a failed payment, one sent back for revision and an expired one | 204 each |
| TC-035 | Not deletable | Delete a listing with a payment in progress, in review or approved, a sold one, and a rejected one | 400 `ERROR_LISTING_NOT_DELETABLE`; nothing changes |
| TC-036 | Count of active listings | Delete a published listing while the seller is near the cap (US-008) | The deleted listing no longer counts toward the 50 active listings |
| TC-037 | Events | Edit and delete with a debug log on `com.valuex.listing` | `ListingEditedEvent` (changed field names, major flag) and `ListingDeletedEvent` are published after the commit |
| TC-038 | Review that never started | Make the review hand-over fail after a confirmed major edit (stop the app after the commit), restart | The listing is `TRUST_SAFETY_REVIEW` with no open review; within about 5 minutes the recovery job decides it |
| TC-039 | Edit and delete together | Send an edit and a delete at the same moment (two terminals) | The delete wins; the edit gets 404 or finishes before it; the listing ends deleted with consistent history |
| TC-040 | Languages | Use the app in Hindi and English for the error cases above | The backend answers with the same codes in both; the app shows its own translated message for each code |

---

## Test cases: app (emulator, `dev_android.json`)

| ID | Steps | Expected |
|---|---|---|
| TC-A01 | Profile, tap **My Listings** | The My Listings page opens: back button, "N total listings", the Active, Sold and Total Views cards (Total Views reads 0), chips All, Active and Sold, a card per listing |
| TC-A02 | Read a published card | Plan name ("Basic plan"), a green **Active** badge, title, price, "0 views", "0 chats", an edit icon (top right) and a trash button (bottom right); the photo, or a grey image icon when there is none |
| TC-A03 | Read other statuses | Draft: "Draft"; waiting for payment: "Processing payment"; in review: "Under review" (amber); sent back: "Needs changes" (red); expired: "Expired"; rejected: "Rejected"; sold: "Sold". Sold and in-review cards have no edit icon and no trash button |
| TC-A04 | Choose **Active**, **Sold**, **All** | The list follows the chip; the cards above do not change; an empty filter says so ("You have no active listings"); with no listings at all the page offers **List an item** |
| TC-A05 | Many listings | At more than 20 listings a **Load more** button appears and adds the next page |
| TC-A06 | Pull down; stop the backend and open the page | The list refreshes; a failed load shows an error with **Retry** that works once the backend is back |
| TC-A07 | Tap a published card, then the edit icon | Both open **Edit Listing** with the stored values, no progress steps, the category with a lock and the note that it cannot be changed, the **Photos** section and **Save changes** |
| TC-A08 | Tap a draft | Item Details opens with the draft's values; **Choose Listing Plan** is the button |
| TC-A09 | Tap a listing whose payment failed | Plan selection opens |
| TC-A10 | Tap a listing in review, one expired, one rejected, one with a payment in progress | The read-only preview (US-123) opens with a banner that says where it stands; back returns to My Listings. Each card also has its own **Preview** link |
| TC-A11 | Tap a sold listing | "Sale details are coming soon" |
| TC-A12 | Minor edit: change the description, **Save changes** | The page closes, "Changes saved", and the list shows the change |
| TC-A13 | Major edit: change the price by more than 20%, **Save changes** | A sheet "This change needs a review" lists the reason ("The price is more than 20% away from the approved price") and says "Your plan keeps running meanwhile"; **Keep editing** returns without saving anything |
| TC-A14 | Repeat TC-A13 and choose **Save and send for review** | "Sent for review. Your listing is hidden until it's approved"; the list shows the new status (briefly "Under review" with manual review on) |
| TC-A15 | Photos: look at the section | "n of 10"; the first photo carries **MAIN** and has no remove button; the others have a remove button while more than two remain; with exactly two there is none |
| TC-A16 | Remove a photo, **Save changes** | It disappears from the grid at once and is removed from the listing when saved |
| TC-A17 | **Add photos**, choose from gallery | The photo shows "uploading", then appears; **Save changes** stays off until the upload finishes; saving it asks for the review sheet with "You added photos" |
| TC-A18 | Add a photo with the network off | The photo is marked failed with a retry button; **Save changes** is off until it succeeds or is removed |
| TC-A19 | Add a text file or a photo over 10 MB | "Photo quality too low or invalid format" or "Photo exceeds 10MB limit"; nothing is added |
| TC-A20 | Edit with text the rules refuse | The page stays and shows "This item cannot be listed. See prohibited items policy" |
| TC-A21 | Tap the trash button | A sheet "Delete this listing?" says the plan fee is not refunded; **Cancel** closes it and nothing happens |
| TC-A22 | Confirm **Delete** | The card disappears at once and "Listing deleted" shows **Undo** for 5 seconds |
| TC-A23 | Tap **Undo** within 5 seconds | The card is back; no request was sent (the backend log shows no `DELETE`); the counts are as before |
| TC-A24 | Confirm **Delete** and wait | After the snackbar closes the `DELETE` is sent once; the counts drop; the listing is gone after a refresh |
| TC-A25 | Confirm **Delete**, then leave the page before 5 seconds | The delete is still sent when the window closes |
| TC-A26 | Delete a listing the server refuses (put it in review in the database first) | The card comes back and the reason is shown ("This listing can't be deleted right now…") |
| TC-A27 | Hindi, then the largest system text size, on a small screen | Every page above is in Hindi (the Hindi texts are for the product owner to review); nothing overflows; every control can be reached and is at least 48 dp |
| TC-A28 | TalkBack / VoiceOver | The title is a heading; each summary card reads as one phrase ("1 Active"); a card reads title, price and status; the edit and delete buttons say which listing; the selected chip says it is selected; photo tiles say "Photo 2" and "Remove photo 2" |
| TC-A29 | Signed out | Opening My Listings sends the visitor to Sign In |

---

## Running the automated tests

Backend (Docker must be running for the integration tests):

```powershell
cd valuex-backend
$env:JAVA_TOOL_OPTIONS='-Duser.timezone=Asia/Kolkata'
mvn verify '-Dtestcontainers.version=1.21.4'
mvn checkstyle:check
```

Only this story:

```powershell
mvn test '-Dtest=ListingEditServiceTest,ListingPoliciesTest,ListingDeletionServiceTest,MyListingsServiceTest,MyListingsControllerTest,ListingControllerTest,ListingCategoryServiceTest,ListingDetailsServiceTest,RestrictedItemCheckServiceTest,ListingLifecycleServiceTest,ContentFingerprintTest,GlobalExceptionHandlerTest,ListingStateMachineTest,ListingEditDeleteIntegrationTest'
```

Mobile:

```powershell
cd valuex-mobile
flutter gen-l10n
dart format lib test
flutter analyze --fatal-infos
flutter test test/features/listing/my_listings_test.dart test/features/listing/item_details_live_test.dart
```

(On Windows the two `google_accessibility_test` contrast tests fail on `main` as well; CI runs on macOS.)

Results at hand-over: backend `mvn verify` 1472 tests, 0 failures (this delivery adds unit tests for the edit and
deletion services, both policies, My Listings, the controllers, the restricted-item check of edited content, the 409 handler
and the approved price, and 13 Testcontainers cases in `ListingEditDeleteIntegrationTest`); Checkstyle 0 violations;
instruction coverage of the new and changed classes 93–100%. Mobile: `flutter analyze --fatal-infos` no issues, `dart format` no diff,
`my_listings_test.dart` (53) and `item_details_live_test.dart` (25) pass, total line coverage 91%; the full suite shows only
the two Windows-only contrast failures. SonarQube: see the pull request.
