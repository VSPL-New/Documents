# US-123 — Preview Listing: QA Testing Guide

**Sprint 2 · Seller Listing Creation**

Manual test cases for the owner's read-only preview of a saved listing: the status banner, photos, summary, the Overview and
Details tabs, the switched-off buyer actions, and who may open it. The dummy gateway is used; no money is charged.

> **What ships:** four new nullable fields on `GET /api/v1/listings/{id}` (`listingSchema`, `reviewReason`, `planName`,
> `publishedAt`), added by `ListingPreviewAssembler`; the app screen `ListingPreviewScreen`
> (`/profile/listings/:listingId/preview`) and the reusable `ListingPreview` widget; a **Preview your listing** button that now
> opens it (US-009 page); a **Preview** link on every My Listings card, and a card tap on a listing that cannot be edited now
> opens it instead of a status sheet (US-010).
> **Not in this story:** Chat, Call, Video, Make an Offer, Buy Now and Save do nothing (they are shown switched off); the sold
> listing sale details (US-126); the buyer page (US-012); Pause (US-124, there is no `PAUSED` state yet); no migration and no
> AI call.

| Setting | Value |
|---|---|
| Backend base URL | `http://localhost:8080` |
| Migration | none |
| Preview route | `/profile/listings/{listingId}/preview` |
| Tabs | **Overview** (every mandatory field of the category) and **Details** (every other populated field) |
| Errors | `LISTING_NOT_FOUND` (404): shown as "This listing is no longer available" |
| Known gaps | No automatic refresh of an expired photo link (use **Retry**); SonarQube not run; Hindi text is a draft |

---

## Prerequisites

1. PostgreSQL and Redis from `valuex-backend/docker-compose.yml`; start the backend (`mvn spring-boot:run`) and the app on an
   emulator (`flutter run --dart-define-from-file=config/dev_local.json`).
2. Two `ACTIVE` sellers with Aadhaar verified: seller A (`$TOKEN`) and seller B (`$TOKEN_B`).
3. Seller A needs these listings (`US-006-Testing-Guide.md` for drafts, `US-008` and `US-009` guides to pay and publish; with
   `UPDATE plans SET discounted_price = 0 WHERE code = 'BASIC'` the `BASIC` plan publishes without payment):
   - **L-PUB**: published, with 3 photos, a phone category and values for its mandatory and some optional fields.
   - **L-REV**: sent back for revision (`MODERATION_MANUAL_REVIEW_ENABLED=true`, then reject with a reason in
     `listing_trust_safety_reviews`), or set it by SQL below.
   - **L-DRAFT**: a draft with details saved but not submitted.
   - **L-REAL**: a Real Estate listing (sale intent).
4. Useful queries:

```sql
SELECT status, plan_type, published_at, category_id FROM listings WHERE id = '<id>';
SELECT admin_decision, rejection_reason, created_at FROM listing_trust_safety_reviews WHERE listing_id = '<id>' ORDER BY created_at DESC;
SELECT count(*) FROM listing_status_history WHERE listing_id = '<id>';   -- note it before and after a preview
```

---

## Test cases: backend

| ID | Acceptance criterion / edge case | Steps | Expected |
|---|---|---|---|
| TC-001 | AC1 owner reads | `curl -s "http://localhost:8080/api/v1/listings/$L_PUB" -H "Authorization: Bearer $TOKEN"` | 200; `listingSchema` has the category's fields, `planName` and `publishedAt` are set, `reviewReason` is null |
| TC-002 | AC1 another seller | Same call with `$TOKEN_B` | 404 `LISTING_NOT_FOUND`; no schema, plan or review data in the body |
| TC-003 | AC1 deleted or unknown id | Same call for a deleted listing and for a random UUID | 404 `LISTING_NOT_FOUND` |
| TC-004 | AC3 review reason | Call it for **L-REV** | `reviewReason` holds the reason of the review that sent it back |
| TC-005 | AC3 no stale reason | Approve and publish **L-REV** again, then call it | `reviewReason` is null |
| TC-006 | AC2 plan before publication | Call it for **L-DRAFT** | `publishedAt` is null; the app will show no plan badge |
| TC-007 | AC6 read-only | Count `listing_status_history` rows, call the GET three times, count again | The count is unchanged; no new review, payment or AI rows |
| TC-008 | Older listing, disabled category | `UPDATE categories SET admin_enabled = false WHERE id = (SELECT category_id FROM listings WHERE id = '<L-PUB>')`, then call the GET | 200 with `listingSchema` still filled; then `PUT /listings/{id}/category` for a draft in that category still answers `ERROR_CATEGORY_DISABLED`. Restore the flag afterwards |
| TC-009 | Other responses unchanged | `PATCH` a draft's details and `PUT` its category | The responses have `listingSchema`, `reviewReason`, `planName` and `publishedAt` as null |
| TC-010 | AC9 photo links | `POST /api/v1/media/{mediaId}/access` for a photo of **L-PUB** with `$TOKEN`, then with `$TOKEN_B` | 200 with a short-lived `accessUrl` and `expiresAt` for the owner; 404 for seller B. No public storage URL anywhere |

---

## Test cases: app

| ID | Acceptance criterion / edge case | Steps | Expected |
|---|---|---|---|
| TC-A01 | AC1 from the submitted page | Pay a plan so the "Your listing is submitted" page opens, tap **Preview your listing** | The preview opens with the "Under review" banner and "Only you can see it until it's approved"; the back button returns to the submitted page |
| TC-A02 | AC1 from My Listings | Open **Profile > My Listings**; tap **Preview** on the **L-PUB** card | The preview opens; back returns to My Listings. Tapping the card or the Edit icon still opens the editor |
| TC-A03 | AC1 card tap on a listing that cannot be edited | Tap a card that is in review, expired, rejected or waiting for payment | The preview opens with a banner for that state. Sold card: the tap still says "Sale details are coming soon", its **Preview** link opens the preview |
| TC-A04 | AC1 owner only | Sign in as seller B and open `/profile/listings/<L-PUB>/preview` (for example from a deep link or by changing the id in a debug build) | "This listing is no longer available" with **Retry**; none of seller A's content is shown. Signed out: the sign-in page opens |
| TC-A05 | AC2 content | Open the preview of **L-PUB** | In order: banner, photos, category path, title with the condition at the right of the title, price (and "Negotiable" when set), the plan badge (for example "Boosted plan"), the city, then the **Overview** and **Details** tabs |
| TC-A06 | AC7 layout | Look at the tabs and the summary | Exactly two tabs, no Location tab; the city appears once. A very long title wraps without covering the condition |
| TC-A07 | AC4 Overview | Open **Overview** | "About this item" with the saved description, then "Key details": quantity, condition notes and every field the category marks as required. A field required only for one intent (Real Estate) appears when that intent is chosen |
| TC-A08 | AC5 Details | Open **Details** | Every other filled field with its option label, unit, date or Yes/No. Empty optional fields are absent; a value of `0` or "No" is shown. A category with none shows "No additional details" |
| TC-A09 | AC4 missing value | Make a mandatory value blank in the database for a draft (**L-DRAFT**) and open it | The row reads "Not provided" in Overview; nothing is invented |
| TC-A10 | AC6 AI or manual | Create one listing with the AI suggestions accepted and edited, and one typed by hand, with the same values | Both previews look identical; the preview does not mention AI and does not start any AI call (check the backend log) |
| TC-A11 | Real Estate | Open **L-REAL** | The price in the summary is the one for the chosen intent; it is not repeated in the tabs; Transaction intent is in Overview; condition and quantity are not shown |
| TC-A12 | AC3 states | Open previews of listings in each state: draft, payment pending, under review, revision required, published, sold, expired, rejected, removed | Each shows its own banner text. Revision required and rejected also show "Reason: ..." |
| TC-A13 | AC2 plan badge | Compare **L-PUB** with **L-DRAFT** | The badge shows only for the one that has been published |
| TC-A14 | AC8 buyer actions | Look at the bottom of the page | Row 1: Chat, Call, Video. Row 2: Make an Offer, Buy Now. A line says buyer actions are unavailable in preview. Tapping any button or the heart at the top does nothing; no dialler, camera or payment opens |
| TC-A15 | AC9 photos | Open **L-PUB**, swipe through the photos | The counter reads "1 / 3", "2 / 3", "3 / 3"; each photo loads; tapping a photo opens it larger and **Close** closes it |
| TC-A16 | AC9 photo failure | Turn off the network after the page opens, swipe to a photo not loaded yet | That photo shows "This photo could not be loaded" with **Retry**; the rest of the page still works; **Retry** works once the network is back |
| TC-A17 | AC9 no photos | Open **L-DRAFT** before adding photos (or remove them in the database) | "No photo" placeholder; the page still opens |
| TC-A18 | Details unavailable | Set `listings.category_id` to an id that no longer exists and open the preview | The page opens with the known values; the tabs say details cannot be shown right now, with **Retry** |
| TC-A19 | Load errors | Stop the backend and open a preview | A message and **Retry**; after starting the backend, **Retry** shows the listing |
| TC-A20 | AC10 Hindi | Switch the app language to Hindi (`adb shell cmd locale set-app-locales com.valuex.valuex_mobile --locales hi`) | All fixed text is Hindi (draft translation); saved values stay as the seller typed them |
| TC-A21 | AC10 large text | Set the system font size to the largest and open the preview on a small phone | Nothing is cut off or overlapping; the page scrolls to the last field and the buttons; above 1.3x text the banner and buttons scroll with the page |
| TC-A22 | AC10 screen reader | Turn on TalkBack and open the preview | The title is read as a heading; the tabs are announced as selected or not; each switched-off button is read as unavailable; each photo reads "Photo 1 of 3" with "Enlarge photo" |
| TC-A23 | Read-only | Open the preview, change tabs, open photos, go back | `listing_status_history` and `listing_edit_history` have no new rows and `updated_at` is unchanged |

---

## Automated tests

```bash
# Backend (uses JDK 21; Checkstyle runs first)
cd valuex-backend
mvn -o test -Dtest='ListingPreviewAssemblerTest,ListingDraftServiceTest,ListingControllerTest'

# Mobile
cd valuex-mobile
flutter test test/features/listing/listing_preview_test.dart test/features/listing/my_listings_test.dart \
  test/features/listing/listing_submitted_test.dart test/core/routing
```

`integration_test/listing_preview_flow_test.dart` (submitted page to preview and back) has only been run headlessly, as a
temporary copy under `test/`. Run it on a device only when you want to: `flutter test integration_test/listing_preview_flow_test.dart -d <device>`.

Known unrelated failure: `item_details_live_test.dart` "the page passes the tap target and label guidelines" fails on `main` as
well (condition-chip contrast on the Item Details page).
