# US-114: Listing Item Details Entry — Implementation Plan (category part superseded by US-006)

> **Update (2026-10-25, category taxonomy):** this plan was implemented as written. The category part is superseded by US-006 (`Documents/US-Implementation-Plans/US-006-Implementation-Plan.md`): `listings.category_slug` is replaced by an L3 `category_id`, the single-select chips are replaced by the category picker, and the page is driven by the category's listing schema (new common fields condition notes, negotiable and quantity; optional fields under "More details"). The maximum price is now ₹10,00,00,000 (`valuex.listing.max-price`); the figures below record the original ₹1,00,00,000.

## 1. Header

| Field | Value |
|---|---|
| Story ID | US-114 |
| Title | Listing Item Details Entry |
| Sprint | Sprint 2 — Seller Listing Creation |
| Story Points | 5 (proposed) |
| Repos | valuex-backend, valuex-mobile. `valuex-ai` out of scope |
| Dependency | US-004 (draft listing and photos); US-089 (listing states; `REVISION_REQUIRED` editing). Built after US-089 and before US-005 and US-007 |

**Status (2026-10-17): implemented on branch `feature/US-114-listing-item-details` (backend and mobile), awaiting review and push.** Not done here, by design: the US-007 restricted check call (US-007 is not built; the page saves and shows 'Details saved. Choosing a plan is coming soon.' until US-008), the OpenAPI example, and the Figma MCP design-context read (the Figma tools could not be loaded; the page was built from the Make source notes in section 3 and the design system). Hindi strings need native-speaker review.

**Scope decisions (product owner, 2026-10-16):**
1. One Flutter page, **Item Details**, from the Figma Make `CreateListingScreen` "details" step, with the content of Make's "Set Your Price" step merged into it. Brand theme and the existing design system, not Make's raw styling.
2. **Manual first.** With AI disabled or unavailable (default) the fields start empty. When AI has filled them (US-005) they are prefilled with a banner. Both variants are in the Make design.
3. Condition values are the plan's `NEW`, `LIKE_NEW`, `GOOD`, `FAIR`, `POOR` (shown as Brand New, Like New, Good, Fair, Poor).
4. One category only, until US-006 adds a primary plus 3 more.
5. **Location** is the user's current location as on Home (area and city), until the address stories are delivered. Only the city is sent to the server.
6. **Manual price entry is in this story.** Make's AI price suggestion card is not (price suggestion is on hold).
7. **At least 2 photos** (raises the US-004 minimum from 1). Review time shown to sellers: "a few hours".
8. Flow: Photos → Item Details → Listing Plan → Review & Pay → (payment) → Trust & Safety review → publish. The restricted item check (US-007) runs when the seller continues from this page, before plan selection.

## 2. Story Recap

**As a** seller **I want** to enter or review my item's title, category, condition, description, location and price on one screen **so that** my listing is complete and I can choose a listing plan.

**Acceptance Criteria:** see US-114 in `Documents/user-stories.md`. In short: empty fields when AI is off (with the US-005 message), prefilled and bannered when AI is on; required title, condition, description, category and price; condition chips; description; location from Home; price with the negotiation note; **Choose Listing Plan** saves, runs the US-007 check, then continues to US-008; details persist on the draft; editable in `DRAFT` and `REVISION_REQUIRED`.

**Validation Rules:** title required, up to 100 characters · one category from the Home category list · condition required, one of the five values · description required, up to 2000 characters · price required, above zero, at most 2 decimals, up to ₹1,00,00,000 · at least 2 photos · details editable only in `DRAFT` or `REVISION_REQUIRED`.

**Error Scenarios:** `ERROR_MIN_PHOTOS_REQUIRED` · `ERROR_TITLE_REQUIRED` · `ERROR_CATEGORY_REQUIRED` · `ERROR_CONDITION_REQUIRED` · `ERROR_DESCRIPTION_REQUIRED` · `ERROR_PRICE_INVALID` · `ERROR_LISTING_NOT_EDITABLE` · `ERROR_RESTRICTED_ITEM` (from US-007).

## 3. Design Reference

- Figma Make source: `CreateListingScreen.tsx` in Make file `tzrpUwfrR0SYeyKkv1p0co`, steps `details` and `price` (read through the Figma MCP on 2026-10-16). Make's content: header with back and progress bar; Title input; Category chips; Condition chips; Description text area (4 rows); Location input with pin; price block with ₹ prefix input and the note "Buyers can negotiate. You can accept, counter, or reject any offer."; gradient bottom button.
- [Flutter-Design-System.md](../../valuex-mobile/docs/Flutter-Design-System.md) wins over Make where they differ; US-110 accessibility rules apply (48 dp targets, labels, 4.5:1 contrast, 200% text).
- Existing code to reuse: `create_listing_screen.dart`, `create_listing_controller.dart`, `listing_repository.dart`, `listing_error_messages.dart` (listing feature); Home location (`HomeLocationController`, `home_location.dart`, location prompts); `BrandGradientButton`, theme inputs and chip styles; Home `categoriesProvider` for the category list.
- Backend: `Listing` already has `title`, `description`, `condition`, `price`, `seller_location`; `ListingDraftService`, `ListingController` (`/api/v1/listings`); LLD Part A and Part B (§1.3 suggestion fields).

**Key design decisions:**
- **Mobile page.** `ItemDetailsScreen` under `lib/features/listing/presentation/`, opened after **Submit to AI** on the photo page. It receives the `listingId` and an optional AI suggestion. The progress bar has 4 steps (Photos, Details, Plan, Review) because the Price step is merged (see Open Gaps).
- **Server saves once, on Continue.** `PATCH /api/v1/listings/{listingId}` stores all fields; the page keeps typed values locally if the call fails.
- **Temporary category column.** `listings.category_slug` holds the chosen category until US-006 creates the taxonomy and `listing_categories`; US-006 migrates it and drops the column, and replaces the single-select category chips on this page with its category picker (the details save then no longer carries a category).
- **Location privacy.** The page reads the Home location (device location or saved), shows area and city, and sends only the city; coordinates never leave the device (same rule as Home).
- **After saving**, the page calls the US-007 restricted check; only a pass moves on to plan selection.

## 4. Implementation Steps

### Database Migration — `valuex-backend`
- [ ] `V14__listing_category_slug.sql` (after US-089's `V13`): add nullable `category_slug VARCHAR(100)` to `listings`. No other change (`title`, `description`, `condition`, `price`, `seller_location` exist).

### Backend — Domain and DTOs
- [ ] `ListingCondition` enum (`NEW`, `LIKE_NEW`, `GOOD`, `FAIR`, `POOR`); keep `listings.condition` a `VARCHAR` storing the enum name.
- [ ] Add `categorySlug` to `Listing`.
- [ ] `UpdateListingDetailsRequest` (title, categorySlug, condition, description, price, location) with Bean Validation (sizes, price scale 2) and plain-text trimming (strip control characters; no HTML is stored or rendered as markup).
- [ ] Extend `ListingDraftResponse` with title, categorySlug, condition, description, price and location so a resumed draft shows saved values.

### Backend — Service and API
- [ ] `ListingDetailsService.updateDetails(listingId, sellerId, request)`: load with the lock used for drafts, require owner, require status `DRAFT` or `REVISION_REQUIRED` (`ERROR_LISTING_NOT_EDITABLE`), require at least 2 READY photos (`ERROR_MIN_PHOTOS_REQUIRED`), validate required fields and price (`ERROR_TITLE_REQUIRED`, `ERROR_CATEGORY_REQUIRED`, `ERROR_CONDITION_REQUIRED`, `ERROR_DESCRIPTION_REQUIRED`, `ERROR_PRICE_INVALID`), save, return the draft response.
- [ ] Price limit from `ValuexProperties` (`valuex.listing.max-price`), default ₹1,00,00,000 (approved).
- [ ] `PATCH /api/v1/listings/{listingId}` in `ListingController` using the authenticated seller from the security context only; standard `ApiResponse` envelope and central exception handling.
- [ ] Do not change the listing status here; the status moves through `ListingLifecycleService` in US-007/US-008/US-084.
- [ ] Do not store coordinates or any location other than the city string.

### Mobile — Item Details (Flutter)
Follow `nova-figma-to-code`: call the Figma MCP `get_design_context` for the Make file (`tzrpUwfrR0SYeyKkv1p0co`, node `0:1`, then read `CreateListingScreen.tsx`), check the mapping file for drift, reuse existing components, and record the mapping entry after implementation.
- [ ] `ItemDetailsScreen` + `ItemDetailsController` (Riverpod), route under the Sell flow (for example `/sell/details`), opened from `_submit` in `create_listing_screen.dart` once the US-005 call returns or fails; manual variant is the default.
- [ ] Layout from Make: header (back, 4-step gradient progress bar, "Item Details", subtitle per variant); AI banner only in the AI variant; Title input; Category chips (list from Home `categoriesProvider`, single select); Condition chips (Brand New, Like New, Good, Fair, Poor); Description multi-line input; Location row; price block (₹ prefix, numeric keyboard, negotiation note); bottom `BrandGradientButton` **Choose Listing Plan**.
- [ ] Location row reads `HomeLocationController`; shows area and city; when the location is unknown shows the same prompts and the **Use my current location** action as Home (including denied, denied forever, service off); no free text.
- [ ] Button disabled until title, category, condition, description and price are valid; a hint under each missing field says what is missing.
- [ ] Tap saves through a new `ListingRepository` method for `PATCH /listings/{id}`; on success call the US-007 check (repository method for `POST .../restricted-check`, available once US-007 is built; until then the page goes straight on); on `ERROR_RESTRICTED_ITEM` show the message and stay.
- [ ] When an AI suggestion was supplied, on Continue send per-field feedback to the US-005 feedback endpoint (`ACCEPTED` if unchanged, `EDITED` if changed, `REJECTED` if cleared). Written against the contract and tested with a fake; not exercised against a real AI.
- [ ] Raise `ListingPhotoRules.minPhotos` from 1 to 2 and make **Submit to AI** follow it; update the photo-step hint text accordingly.
- [ ] Review text "usually within a few hours" is used wherever the review time is shown (for example on the later Review step).
- [ ] Add l10n strings for everything in English and Hindi (labels, hints, errors, banner, condition labels, price note); map the new error codes in `listing_error_messages.dart`.
- [ ] Update `docs/Flutter-Design-System.md` change log with the new page (tokens used, chip styles, any additions).
- [ ] Tokens only, no hard-coded colours; 48 dp tap targets; labels on every control; 200% text; Hindi.

### Documentation/Quality
- [ ] Update US-004 follow-ups for the minimum of 2 photos: LLD Part A (`ERROR_MIN_PHOTOS_REQUIRED` row and message "At least 2 photos required"), the US-004 implementation plan lines on min 1, and the US-004 testing guide rows.
- [ ] Update LLD Part B/C notes: temporary `category_slug`, `PATCH /listings/{id}` owned by this story.
- [ ] OpenAPI example for `PATCH /api/v1/listings/{listingId}`.
- [ ] After implementation, create `Documents/Manual Testing Guides/US-114-Testing-Guide.md`.

## 5. Test Plan

Target >90% coverage for new code (`CLAUDE.md`).

### Backend Unit Tests
- [ ] Valid update saves every field, trims text, and returns them on the draft.
- [ ] Rejects: not owner (not found), status other than `DRAFT`/`REVISION_REQUIRED`, fewer than 2 READY photos, missing title, missing category, missing condition, missing description, missing or zero or negative price, price with 3 decimals, price over ₹1,00,00,000, unknown condition, title over 100, description over 2000.
- [ ] `REVISION_REQUIRED` listing can be edited; `PUBLISHED` cannot.
- [ ] Control characters stripped; HTML tags stored as plain text, never interpreted.
- [ ] Status is unchanged by the update.

### Backend Integration Tests (Testcontainers PostgreSQL)
- [ ] `V14` applies on top of `V13`; existing listings unaffected.
- [ ] `PATCH` then `GET` returns the saved details; error envelope for each error code.
- [ ] IDOR: another seller gets not found.

### Mobile Tests (Flutter)
- [ ] Widget tests: manual variant (empty fields, "Fill in the details"), AI variant (prefilled, banner), button disabled and hints for missing fields, chip selection, price formatting, location row states (known, unknown, denied, service off), failure keeps typed values.
- [ ] Controller tests: validation, save call, restricted check result handling, feedback computation (accepted/edited/rejected).
- [ ] Accessibility guideline tests (tap target, label, contrast) in English and Hindi at 1.5x and 2x text.
- [ ] `ListingPhotoRules` min 2: Submit to AI disabled with one photo.

## 6. Validation Checklist

- [ ] With AI off, a seller can finish the page entirely by hand and reach plan selection.
- [ ] Prefilled AI values are fully editable and the AI banner appears only when AI filled them.
- [ ] Condition values match the plan exactly.
- [ ] Price entered manually, no AI price card.
- [ ] Location comes from Home; no coordinates sent or stored.
- [ ] At least 2 photos enforced on both the app and the server.
- [ ] Details editable only in `DRAFT` and `REVISION_REQUIRED`.
- [ ] US-007 check runs before plan selection.
- [ ] Brand theme and design-system tokens used; accessibility rules met.
- [ ] Figma-to-code mapping entry recorded.
- [ ] Checkstyle, full tests, coverage, SonarQube (backend) and Flutter analyze and tests (mobile) pass before push.

## 7. Open Gaps / Questions

1. **Required fields (decided).** Title, category, condition, description and price are all required.
2. **Maximum price (decided).** ₹1,00,00,000.
3. **Progress bar (decided).** 4 steps (Photos, Details, Plan, Review).
4. **Category list.** The page uses Home's category list (currently mock data) and stores a slug without server validation until US-006. US-007's category matching therefore cannot be properly tested until US-006 provides real taxonomy slugs.
5. **Rejected after payment (decided).** The seller is notified to modify the listing and resubmits it for review without paying again; no refund. The edit uses this page (`REVISION_REQUIRED`).
6. **Aadhaar check.** US-004 asks for Aadhaar before plan selection; this page continues into that step unchanged.
7. **Photo minimum on existing drafts.** Drafts with one photo created before this change can no longer continue until a second photo is added; acceptable?
8. **Manual-entry copy.** The AI-unavailable message (US-005) leads here; wording for the empty-state subtitle "Fill in the details" needs Hindi text.

---

**Status:** Approved (2026-10-16)
