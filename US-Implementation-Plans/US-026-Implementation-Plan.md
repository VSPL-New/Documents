# US-026: Seller Prepares Package and Uploads Proof — Implementation Plan

## 1. Header

| Field | Value |
|---|---|
| Story ID | US-026 |
| Title | Seller Prepares Package and Uploads Proof |
| Sprint | Sprint 6 — Shipping & Delivery |
| Story Points | 5 |
| Repos | valuex-backend, valuex-mobile |
| Dependency | US-023 (`Sprint-plan.md`); opened from US-112 ("Start Packing", "Continue Packing"). **US-023 is not built**, nor is US-021, which creates orders and shipments. Like US-090, US-092 and US-112, the backend is built and tested by inserting orders and shipments directly (G1). It also uses the packed weight and size from US-122, which is not built either (G2). On `main` already: US-090 (orders, `UPLOAD_PROOF` transition), US-092 (`shipments` with the package columns), US-112 (seller queue, `SellerOrderAction.CONTINUE_PACKING`, `FulfilmentSetting`), media purpose `SELLER_PRE_SHIPMENT_EVIDENCE` |
| Branches | `feature/US-026-pack-and-upload-proof` in `valuex-backend` (worktree `wt/US-026-backend`) and in `valuex-mobile` (worktree `wt/US-026-mobile`), each from an up-to-date `origin/main`. Documents: `docs/US-026-plan` (worktree `wt/US-026-plan`) |

## 2. Story Recap

**As a** seller **I want to** upload package photos before pickup **so that** there's proof of item condition at shipping.

**Acceptance Criteria** (`user-stories.md`):
- Given buyer has placed an order, when I receive the order notification, then I am prompted to prepare the item for shipping.
- When I package the item, then I must upload proof images:
  - item condition (before packaging)
  - packaged item (sealed)
- When I upload images, then I can schedule pickup.
- And the buyer can view the proof images.

**Edge Cases:** the seller uploads incorrect or fake images; skips the upload and schedules pickup; images fail to upload on a poor network; the seller packages the wrong item.

**Validation Rules:**
- at least 2 images (item and package), at most 5
- images must be clear (at least 480 × 480)
- upload is required before pickup can be scheduled
- images are timestamped and stored

**Error Scenarios:**

| Code | Message |
|---|---|
| `ERROR_IMAGE_REQUIRED` | Please upload package images before scheduling pickup |
| `ERROR_IMAGE_UPLOAD_FAILED` | Failed to upload images. Try again |
| `WARNING_IMAGE_QUALITY_LOW` | Image quality low. Upload clearer photo |

**Related:** US-112. This screen opens from "Start Packing" and "Continue Packing" on the seller's Incoming Orders page.

## 3. Design Reference

**Primary source:** [Sprint-6-Shipping-Delivery-LLD.md — Part D](../LLD/Sprint-6-Shipping-Delivery-LLD.md#part-d---us-026-seller-prepares-package-and-uploads-proof), revision 0.6.

**Also read:**
- Part 0: settings `PROOF_MIN_IMAGES` (2), `PROOF_MAX_IMAGES` (5) and `PROOF_MIN_PIXELS` (480) (the two counts are replaced by four per-section settings, G10); error codes, including the new `ERROR_PROOF_LIMIT`; the order state flow `SELLER_PACKING_PENDING → SELLER_PROOF_UPLOADED`
- A.5 and A.12: the US-112 buckets. After packing, `SELLER_PROOF_UPLOADED` with shipment `SHIPPING_REQUIRED` shows in the Packing group with the `SCHEDULE_PICKUP` action.
- C.4.1: packed weight 0.05 to 30 kg and each side 1 to 150 cm. These limits are **Proposed** (G5 in the LLD).
- M.4: G16, which covers evidence photo retention (2 years after completion) and the fact that photos are not matched to the listing automatically.
- Sprint 5 LLD Part H (US-023): the buyer's order detail, which gains `sellerProofs`.

**What already exists on `main`:**
- `OrderStateMachine`: `SELLER_PACKING_PENDING → SELLER_PROOF_UPLOADED` via `UPLOAD_PROOF`, and `OrderTransitionService`
- `OrderRepository.findByIdAndSellerIdForUpdate`, the row lock added in US-112
- `shipments` (V46), with `weight_grams`, `length_cm`, `breadth_cm` and `height_cm` all null. The `Shipment` entity doesn't map them yet.
- `MediaPurpose.SELLER_PRE_SHIPMENT_EVIDENCE`. Media stores it in the private `-evidence` bucket. `MediaAssetService` rejects images under 480 px on either side, with `ERROR_INVALID_PHOTO` when the upload completes (G3).
- `ChatImagePort` / `ChatImageService`: the pattern for a media port that checks owner, purpose and `READY`, sanitises, and returns signed links
- `media_assets.retention_until`
- Mobile:
  - `features/order` with the US-112 screen; `continuePacking` and the step after Start Packing currently show "coming soon"
  - `listing/data/photo_source.dart` (`PhotoSource`: camera or gallery, `inspect`)
  - the chat and listing upload flow over `/media/uploads` → `/media/{id}/complete`

**Key design decisions (LLD Part D):**
- `order_proofs` table:
  - holds seller and buyer proofs; US-026 writes only `SELLER`
  - a proof is a draft until packing completes
  - a submitted proof can't be changed or removed: this is enforced in the service and by a trigger
- Each photo is uploaded on its own and attached as a draft, so a poor network loses nothing. "Continue Packing" reopens the screen with the draft photos.
- `complete` runs in one transaction:
  - row lock, then the rules check
  - submit the drafts and store the package on the shipment
  - `UPLOAD_PROOF` (actor seller)
  - Repeating it after success answers 200 with the same order.
- The server sets `uploaded_at` and ignores the EXIF time. Location data in EXIF is removed.
- Ports:
  - `OrderEvidencePort`, implemented by media
  - `ShipmentPackagePort`, implemented by shipping
  - The order module never touches media or shipping tables.
- The buyer only ever sees submitted photos, as signed links valid for 10 minutes.

**Out of scope:** pickup scheduling and the Schedule Pickup screen (US-027); the buyer's order detail screen (US-023, G1); automatic checks that photos are fake or show the wrong item (G16, later AI story); Shiprocket booking and quotes (US-122).

## 4. Implementation Steps

### 0. Workflow (CLAUDE.md §5)
- [x] Create worktrees `wt/US-026-backend` and `wt/US-026-mobile` on `feature/US-026-pack-and-upload-proof` from up-to-date `origin/main`. Keep your main checkouts and uncommitted work untouched.

### 1. Backend: database (`V47__order_proofs.sql`, G8)
- [x] `order_proofs` table and index as LLD D.2.
- [x] Immutability trigger (`forbid_submitted_proof_change`):
  - refuses an `UPDATE` of `media_id`, `kind` or `submitted_at` once `submitted_at` is set
  - refuses a `DELETE` of a submitted row
- [x] `fulfilment_settings` rows for `PROOF_ITEM_MIN`, `PROOF_ITEM_MAX`, `PROOF_PACKAGE_MIN`, `PROOF_PACKAGE_MAX` and `PROOF_MIN_PIXELS`, if settings are seeded by migration. Otherwise the enum defaults are enough, as with `PICKUP_SLA_HOURS`.

### 2. Backend: domain and settings
- [x] `order.domain.OrderProof` (entity), `ProofParty` (`SELLER`, `BUYER`) and `ProofKind` (`ITEM_CONDITION`, `PACKAGE_SEALED`, `PACKAGE_RECEIVED`, `ITEM_RECEIVED`, with its party)
- [x] `FulfilmentSetting`:
  - `PROOF_ITEM_MIN("2","1","4")` and `PROOF_ITEM_MAX("4","1","8")` (G10)
  - `PROOF_PACKAGE_MIN("1","1","2")` and `PROOF_PACKAGE_MAX("2","1","4")` (G10); the service also refuses a maximum below its minimum
  - `PROOF_MIN_PIXELS("480","240","1080")`
- [x] `OrderErrors`: `ERROR_IMAGE_REQUIRED` (422), `ERROR_PROOF_LIMIT` (422), `WARNING_IMAGE_QUALITY_LOW` (422), each with the story text

### 3. Backend: ports and adapters
- [x] `order.application.port.OrderEvidencePort`:
  - `accept(mediaId, uploaderId, purpose)` → `EvidenceImage(width, height)`; refuses not-owner, wrong purpose or not `READY` with a typed rejection
  - `links(mediaIds)` → signed URLs, 10 minutes
  - `discard(mediaId)` for a removed draft
- [x] `media.infrastructure.order.OrderEvidenceAdapter`, written like `ChatImageService.sanitise`: strip EXIF location and keep the server time.
- [x] `MediaAssetService.minSideFor`: evidence purposes use 1 px, as chat does, so the order module can answer `WARNING_IMAGE_QUALITY_LOW` from the configurable setting (G3).
- [x] `order.application.port.ShipmentPackagePort`:
  - `storePackage(orderId, weightGrams, lengthCm, breadthCm, heightCm)`
  - `listingPackage(orderId)` for the prefill
- [x] Adapters:
  - `shipping.infrastructure.order.ShipmentPackageAdapter`: map the four package columns on `Shipment`
  - the listing side reads `weight_kg` and `dimensions_cm` when present (G2)

### 4. Backend: persistence
- [x] `OrderProofRepository`:
  - drafts and submitted proofs by order and party, in `uploaded_at` order
  - count by order and party
  - `findByIdAndOrderId`

### 5. Backend: application (`order.application.service.PackingService`)
- [x] `view(sellerId, orderId)`, returning:
  - the order summary in the US-112 card shape
  - proofs (id, kind, signed URL, `uploadedAt`, `submitted`)
  - the package prefill
  - the rules (`minImages`, `maxImages`, `minPixels`)
- [x] `attach(sellerId, orderId, mediaId, kind)` (row lock, then in order):
  1. The order must be in `SELLER_PACKING_PENDING`, otherwise 409 `ERROR_ORDER_ACTION_NOT_ALLOWED`.
  2. Fewer than that section's maximum (`PROOF_ITEM_MAX` or `PROOF_PACKAGE_MAX`), otherwise `ERROR_PROOF_LIMIT` with the section and the maximum ("You can add up to 4 item photos").
  3. `OrderEvidencePort.accept` must succeed, otherwise 400 `ERROR_VALIDATION`.
  4. The shorter side must be at least `PROOF_MIN_PIXELS`, otherwise `WARNING_IMAGE_QUALITY_LOW`.
  5. Save a draft with the server time.
  6. Re-attaching the same media answers with the same proof, thanks to the unique `media_id`.
- [x] `remove(sellerId, orderId, proofId)`:
  - drafts only, otherwise 409
  - deletes the row, then discards the media after commit
- [x] `complete(sellerId, orderId, package)` (row lock):
  1. If the order is already `SELLER_PROOF_UPLOADED`, answer 200 with the same card (idempotent).
  2. If it is in any other state than packing, answer 409.
  3. At least `PROOF_ITEM_MIN` `ITEM_CONDITION` and `PROOF_PACKAGE_MIN` `PACKAGE_SEALED` photos, otherwise `ERROR_IMAGE_REQUIRED` with the missing counts.
  4. Validate the package against the C.4.1 limits (`ERROR_VALIDATION` with field errors).
  5. Set `submitted_at`, convert kg to grams and store the package through `ShipmentPackagePort`, then `UPLOAD_PROOF`.
  6. After commit, return the US-112 card (`actions: [SCHEDULE_PICKUP]`), using the US-112 pattern of moving the order first and reading the card afterwards.
- [x] Micrometer: `seller.orders.packing.attach` and `seller.orders.packing.complete`, each with a `result` tag, as in US-112.
- [x] Buyer proofs, `sellerProofs(orderId)`: submitted photos only, as signed links. Exposed for the US-023 order detail (G1).

### 6. Backend: API (`order.api.PackingController`, under `/api/v1/seller/orders/{orderId}/packing`)
- [x] The four endpoints, exactly as LLD D.3.
- [x] Access rules:
  - The seller must be `ACTIVE` (`requireActive`, as in US-112).
  - Someone else's order answers 404 `ERROR_ORDER_NOT_FOUND`, so other orders can't be discovered.
  - Bean Validation on the request bodies.

### 7. Mobile: data (`lib/features/order/`)
- [x] Entities: `PackingView`, `OrderProof` and `PackageSize`.
- [x] `PackingRepository` interface and its implementation, `parsePackingView`.
- [x] `ApiConstants`: `sellerOrderPacking(id)`, `packingProofs(id)`, `packingProof(id, proofId)` and `packingComplete(id)`.
- [x] Media upload: reuse the chat/listing upload (`/media/uploads` → PUT → `/media/{id}/complete`) with purpose `SELLER_PRE_SHIPMENT_EVIDENCE`, then attach.
- [x] Mock mode: extend `SELLER_ORDERS=mock` so the sample "Packing" order opens a mock packing view.

### 8. Mobile: presentation (`features/order/presentation/packing/`)
- [x] `PackAndUploadProofScreen`, route `/seller/orders/:id/packing`:
  - declared before `/seller/:sellerId`
  - added to the route guard's gated and signed-in-only sets
- [x] Layout as the Make design (G7):
  - header and subtitle
  - order card
  - "Steps to follow" card
  - Item Photos and Packaging Photos, with counters
  - "Packed size and weight" card (G11)
  - escrow note (G12)
  - "Submit Proof & Schedule Pickup" button with the red hint below it while photos are missing
- [x] Two sections, "Item Photos" (`ITEM_CONDITION`, camera Add tile) and "Packaging Photos" (`PACKAGE_SEALED`, upload Add tile), with the counts from G10. Each has:
  - "Take photo" (camera first) and "Choose from gallery", via `PhotoSource`
  - thumbnails with a remove button
  - upload progress and retry for each photo
- [x] Error mapping:
  - a failed upload: `ERROR_IMAGE_UPLOAD_FAILED`
  - a server refusal: `WARNING_IMAGE_QUALITY_LOW`
  - the limit: `ERROR_PROOF_LIMIT`
- [x] The add buttons are disabled at the maximum number of photos.
- [x] "Packed size and weight" fields:
  - prefilled and editable
  - decimal keyboard for weight
  - checked against the C.4.1 limits before sending
- [x] "Submit Proof & Schedule Pickup" (the LLD's "Done, schedule pickup"):
  - enabled when both sections meet their minimum (G10) and nothing is uploading
  - calls `complete`, then returns to Incoming Orders with the order in "Schedule Pickup"
  - opens Schedule Pickup once US-027 ships (G6)
- [x] Back keeps the drafts.
- [x] US-112 hand-off in `seller_incoming_orders_screen.dart`:
  - Start Packing opens the packing screen on success
  - Continue Packing opens it too
  - update the US-112 tests that assert "coming soon" for these two
- [x] Hindi and English ARB strings, then `flutter gen-l10n`.
- [x] Accessibility:
  - 48 dp targets
  - photo labels "Item condition photo 1 of 2"
  - progress announced
  - add the screen to the `all_screens_accessibility` and `screen_headings` tests

### 9. Documentation (CLAUDE.md §5.10)
- [x] Per-section photo counts (G10): update the US-026 validation rules in `user-stories.md`, and the settings and D.3 rules in LLD Part 0.
- [x] LLD Part D: add a D.7 "As built" section and the version and change-log row. Close G3 and G5 in M.4 if decided.
- [x] `Sprint-plan.md` row; the note in `user-stories.md`; the US-112 guide's "coming soon" rows for Start/Continue Packing.
- [x] `Manual Testing Guides/US-026-Testing-Guide.md`, with SQL to create a `SELLER_PACKING_PENDING` order and its shipment.

### 10. Quality gates (CLAUDE.md §5.7, §5.8)
- [x] Backend: `mvn clean verify`, Checkstyle, JaCoCo at least 90% on changed classes, Sonar with 0 new issues.
- [x] Mobile: `dart format`, `flutter analyze`, full suite, at least 90% coverage of `features/order/**/packing`.

## 5. Test Plan

**Backend unit (JUnit 5, Mockito, AssertJ):**
- `PackingServiceTest`, the rules table at each edge:
  - 1 and 2 item photos; 0 and 1 packaging photos
  - the 4th item photo allowed and the 5th refused; the 2nd packaging photo allowed and the 3rd refused
  - 479 and 480 px on the shorter side
  - the settings changed (for example item 1 to 8, packaging 1 to 4)
  - wrong state (409)
  - repeated `complete` (200, same card)
  - removing a submitted proof refused
  - re-attaching the same media is idempotent
  - package out of limits (each field, each edge: 0.04/0.05/30/30.01 kg, 0/1/150/151 cm)
  - kg to grams conversion
  - buyer proofs exclude drafts
- `PackingControllerTest` (MockMvc):
  - shapes of the 4 endpoints
  - validation 400
  - 404 for another seller's order
  - 403 for a non-`ACTIVE` seller
- `OrderEvidenceAdapterTest`: owner, purpose, `READY`, EXIF location removed, links.
- `ShipmentPackageAdapterTest`; `FulfilmentSettingTest` for the new settings.

**Backend integration (`SellerPackingIntegrationTest`, Testcontainers PostgreSQL; order and shipment inserted directly):**
- attach, remove, attach, then complete moves the order to `SELLER_PROOF_UPLOADED`, stores the package on the shipment and writes order history
- the US-112 list now shows the order in the Packing group with `SCHEDULE_PICKUP`
- the trigger refuses changing or deleting a submitted proof
- two concurrent `complete` calls give one transition and two 200 answers
- buyer proofs show only submitted photos

**Mobile (flutter_test, mocktail):**
- Repository: parsing, and error-code mapping.
- Controller:
  - attach with progress and retry after failure
  - remove
  - the complete button's enabled state
  - complete success and the 409 refresh
  - Continue Packing restores the drafts
- Screen and widget:
  - both sections, the limit, the low-quality message
  - package field validation
  - navigation from Start Packing and Continue Packing (updated US-112 tests)
  - Hindi strings
  - accessibility labels

## 6. Validation Checklist

- [x] Prompted to prepare: the new-order push (US-112) opens Incoming Orders, and Start Packing opens this screen
- [x] Item condition and sealed package photos are both required (`ERROR_IMAGE_REQUIRED`)
- [x] Pickup can be scheduled only after `complete`; `SCHEDULE_PICKUP` appears only in `SELLER_PROOF_UPLOADED`
- [x] Buyer can view the proof images: submitted only, as signed links (backend; screen with US-023, G1)
- [x] Item photos 2 to 4 and packaging photos 1 to 2 (settings, G10), with the counters and the hint matching; 480 px minimum (`WARNING_IMAGE_QUALITY_LOW`)
- [x] Photos timestamped by the server and stored privately; EXIF location removed; submitted photos can't be changed
- [x] Poor network: each photo retries on its own; drafts survive leaving the screen
- [x] Skipping the upload is impossible: no pickup action and no transition without `complete`
- [x] Fake images or the wrong item: kept as evidence, with no automatic check (G16), as documented
- [x] Error codes and messages match Part 0; English and Hindi; accessibility checks pass
- [x] US-112 "coming soon" removed for Start Packing and Continue Packing only

## 7. Open Gaps / Questions

| # | Gap | Recommendation |
|---|---|---|
| G1 | **US-023 is not built.** The "buyer can view proof images" part has no buyer screen or order-detail endpoint yet. US-021 isn't built either, so real orders don't exist. | Build the backend `sellerProofs` query now and test it. US-023 adds the field to its order detail and shows the photos (hand-off). Test with orders inserted by SQL, as for US-112. |
| G2 | **US-122 is not built.** Listings don't yet require packed weight and size, so the prefill is often empty. The C.4.1 limits are still Proposed (LLD G5). | Include the package fields now: prefill from `weight_kg` and `dimensions_cm` when the listing has them, otherwise leave them empty and required. Apply the C.4.1 limits as stated. |
| G3 | **The minimum-size rule exists twice.** Media already rejects evidence photos under 480 px with `ERROR_INVALID_PHOTO` when the upload completes, so `PROOF_MIN_PIXELS` (settable from 240 to 1080) and `WARNING_IMAGE_QUALITY_LOW` would never apply. | Media applies 1 px for evidence purposes, as for chat, and the order module applies `PROOF_MIN_PIXELS` with `WARNING_IMAGE_QUALITY_LOW`, as the LLD says. |
| G4 | **Retention date.** The LLD says "order completion + 2 years" (Proposed, LLD G16), but completion is unknown when the photo is attached. | Leave `retention_until` null while the order is open. Hand-off to US-031/US-024 (order completion) to set it to completion + 2 years. Removed drafts are deleted at once. |
| G5 | **Self-pickup orders.** Do they go through packing? Part A sends self-pickup straight from `SHIPPING_MODE_SELECTED` to hand-over. | Packing is for `DELIVERY` orders only. Self-pickup never reaches `SELLER_PACKING_PENDING`, so no extra rule is needed. |
| G6 | **After "Done, schedule pickup"** the LLD opens Schedule Pickup (US-027), which isn't built. | Return to Incoming Orders, where the card shows "Schedule Pickup" (still "coming soon" until US-027). |
| G7 | **Figma design.** ~~Unknown whether Make has the screen.~~ **Closed:** the Make file `tzrpUwfrR0SYeyKkv1p0co` has the Pack & Upload Proof screen (screenshot shared 2026-11-28). It is the visual source; the implementation reads its exact text, colours and icons with `get_design_context`. Make draws only the empty state. Thumbnails, upload progress, retry, the refusal messages and the loading and error states use existing design-system parts. The screen as drawn has: a header ("Pack & Upload Proof", "Required before pickup is scheduled"); an order card (item title, `Order #<ref>`); a static "Steps to follow" card with 4 steps; "Item Photos" (camera Add tile, counter `0/4`, "Min 2, max 4 photos required"); "Packaging Photos" (upload Add tile, counter `0/2`, "Show packed item clearly"); an escrow note; the button "Submit Proof & Schedule Pickup"; and the hint "Add at least 2 item photos + 1 packaging photo". | Build the screen as drawn, with the G10 to G12 decisions. |
| G8 | **Migration number.** `V47` is the next free number; US-091 (not started) may also need one. | Use `V47__order_proofs.sql`; whichever story merges second renumbers. |
| G9 | **Photo order and the 5-photo maximum.** Is the maximum per order or per section? | ~~Per order, across both sections (LLD D.3).~~ Replaced by G10. |
| G10 | **Photo counts: the design differs from the story and the LLD.** <br>• Story and LLD: 2 to 5 photos in total, with at least one of each kind. <br>• Make: Item Photos 2 to 4 and Packaging Photos 1 to 2, so 3 to 6 in total. | **Decided 2026-11-28: follow the design.** Replace the two settings with four, `PROOF_ITEM_MIN` 2, `PROOF_ITEM_MAX` 4, `PROOF_PACKAGE_MIN` 1 and `PROOF_PACKAGE_MAX` 2, and keep `PROOF_MIN_PIXELS`. `ERROR_PROOF_LIMIT` names the section ("You can add up to 4 item photos"). Update the story's validation rules and LLD Part 0 and D.3. |
| G11 | **Packed size and weight are not in the design**, but the LLD (D.3, D.5) and US-122 need the seller to confirm them here. | Add a "Packed size and weight" card between Packaging Photos and the escrow note, using the existing form-field parts (G2 prefill and limits). |
| G12 | **Escrow note** ("Payment of ₹55,000 is held in escrow…"). Escrow is US-091 and US-021, and neither is built yet. | Show the order's item amount from the packing view (US-112 amount format). The wording is true once US-021 ships, and packing is only for prepaid delivery orders (G5). |

## 8. Implementation Notes (as built, 2026-11-28)

The full list is in LLD D.7. Differences from this plan:

- **G2, package prefill:** the view prefills only a package already confirmed on the shipment.
  - US-122, in progress, stores the listing's packed size in new `listings.package_*` columns rather than as the `weight_kg` and `dimensions_cm` attributes, so prefilling from the listing is handed to US-122.
- **G8, migration number:** `V47__order_proofs.sql` as agreed. US-122's work in progress also uses `V47`; whichever story merges second renumbers.
- **G10, photo counts:** the four settings are `PROOF_ITEM_MIN` (2, from 1 to 4), `PROOF_ITEM_MAX` (4, from 1 to 8), `PROOF_PACKAGE_MIN` (1, from 1 to 2) and `PROOF_PACKAGE_MAX` (2, from 1 to 4). A maximum set below its minimum counts as the minimum.
- **G3, photo size:** media gives `SELLER_PRE_SHIPMENT_EVIDENCE` a 1 px minimum, and the order module checks `PROOF_MIN_PIXELS`. `BUYER_DELIVERY_EVIDENCE` is left for US-030.
- **Cleaning:** the clean-copy steps of `ChatImageService` moved into a shared `ImageCleaner`.
  - Chat's behaviour is unchanged; its 14 tests now run through the shared class.
  - Packing photos are kept at most 1600 px on the longest side, without metadata.
- **Packed size errors:** Bean Validation answers with the app-wide `VALIDATION_ERROR` code and field keys such as `packageSize.weightKg`. The LLD names this code `ERROR_VALIDATION`.
- **API details:** removing a draft that is already gone answers 204. Attaching the same photo again answers with the same draft.
- **Mobile:**
  - The packing calls were added to `SellerOrderRepository`, so the `SELLER_ORDERS=mock` sample orders can be packed end to end.
  - The header scrolls with the content, so the screen fits Hindi at 200% text.
  - The Add tiles have a solid tinted border instead of a dashed one, and Make's "MAIN" label and "Proof Uploaded!" page are left out (G6).
  - The app refuses a too-small photo, or one that would overfill a section, before uploading it.
  - The route guard treats `/seller/orders/*` as Incoming Orders.

**Hand-offs:**

| Story | Work |
|---|---|
| US-122 | Listing prefill; `V47` renumbering |
| US-023 | `sellerProofs` on the buyer's order details |
| US-027 | Schedule Pickup after packing (still "coming soon") |
| US-030 | Buyer receipt photos |
| US-031 / US-024 | Photo retention date |

US-112's "coming soon" for Start Packing and Continue Packing is removed. The US-112 testing guide (TC-004 and Not Testable Yet), `user-stories.md` and `Sprint-plan.md` are updated.

**Tests:**

- **Backend:**
  - 8 new classes:
    - `PackingServiceTest` (27 tests)
    - `PackingControllerTest` (4)
    - `PackageSizeTest` (14)
    - `OrderEvidenceAdapterTest` (7)
    - `ShipmentPackageAdapterTest` (3)
    - `SellerPackingIntegrationTest` (5, Testcontainers)
    - new cases in `FulfilmentSettingTest` and `MediaAssetServiceTest`
  - `ChatImageServiceTest` updated for `ImageCleaner`.
  - `mvn clean verify`: 4,122 tests, 0 failures, 9 skipped (LiveKit and libvips smoke tests).
  - Checkstyle: 0 violations.
  - JaCoCo line coverage of the new classes: 100%; `OrderEvidenceAdapter` 95%; `ImageCleaner` 87%, where the uncovered lines are clean-up error branches moved unchanged from chat.
  - Sonar: 0 issues and 0 hotspots in changed files; only the existing `JwtTokenProvider` S2143 remains.
- **Mobile:**
  - New test files:
    - `packing_repository_test.dart` (7 tests)
    - `packing_controller_test.dart` (8)
    - `pack_and_upload_proof_screen_test.dart` (8)
  - Updated tests:
    - Incoming Orders screen: Start Packing and Continue Packing open packing, with or without finishing (+2)
    - route guard (+1)
    - accessibility (+4) and headings (+1) for the packing screen
  - Full suite: 2,526 passed, 2 failed. The failures are `google_accessibility_test.dart`, which also fails on a clean main on this machine.
  - `flutter analyze` and `dart format`: clean.
  - Line coverage of the packing code: 97.3% (780 of 802 lines).

**Status:** Approved (2026-11-28) · Built (2026-11-28; all gaps closed. G1 to G6, G8, G9, G11 and G12 agreed; G7 closed with the Make screen; G10 decided, follow the design)
