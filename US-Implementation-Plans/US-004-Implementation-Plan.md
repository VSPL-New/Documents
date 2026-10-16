# US-004: Create Listing with Photo Capture — Implementation Plan

## 1. Header

| Field | Value |
|---|---|
| Story ID | US-004 |
| Title | Create Listing with Photo Capture |
| Sprint | Sprint 2 — Seller Listing Creation |
| Story Points | 8 |
| Repos | valuex-backend, valuex-mobile (Flutter) |
| Dependency | US-001 (User Registration via Mobile OTP) — caller must be an authenticated, `ACTIVE`, Aadhaar-verified seller |

**Scope (updated 2026-10-14):** `valuex-mobile` is now the real Flutter app (Flutter/Riverpod/go_router, see `CLAUDE.md` §6). The first pass of this story was backend-only; the gap-fix pass adds the Flutter capture screen wired to the backend and closes the backend gaps listed in §8.

Sprint 2 goal: "Allow sellers to create and publish listings." US-004 is the entry point of that sprint — every later Sprint 2 story (US-005 AI suggestions, US-006 tagging, US-007 restricted-item check, US-089 lifecycle, US-084 trust & safety, US-078/US-008/US-009 plan & publish, US-010 edit/delete) builds on the `listings`/`listing_images` rows this story creates.

## 2. Story Recap

**As a** seller **I want to** create a listing by capturing photos of my item **so that** I can quickly list items for sale.

**Acceptance Criteria** (`Documents/user-stories.md`):
- Given I am logged in as a seller, when I tap "Sell Item", then camera opens for photo capture.
- When I capture at least 1 photo (max 10 photos), then photos are uploaded to the system.
- And I can proceed to add item details.

**Edge Cases:** camera permission denied · camera fails to open · >10 photos attempted · poor photo quality · non-item/random photos uploaded · network failure during upload.

**Validation Rules:** min 1 photo required · max 10 photos · format JPG/PNG/HEIC · max 10MB per photo · min resolution 480×480px.

**Error Scenarios:** `ERROR_CAMERA_PERMISSION_DENIED` · `ERROR_MAX_PHOTOS_EXCEEDED` · `ERROR_PHOTO_UPLOAD_FAILED` · `ERROR_INVALID_PHOTO`.

## 3. Design Reference

Primary source: [Sprint-2-Seller Listing Creation-LLD.md — Part A](../LLD/Sprint-2-Seller%20Listing%20Creation-LLD.md#part-a---us-004-create-listing-with-photo-capture) (§A.1–A.8): draft-listing creation, Media API upload authorization/completion, `media_assets`/`media_variants`, `listing_images.media_asset_id`, `listing_status_history`, `requireOwnedDraft` ownership+status guard, validation/error table.

**Key design decisions carried over from the LLD:**
- Listing creation uses a Media API pattern: `POST /api/v1/listings` creates an empty `DRAFT` shell, `POST /api/v1/media/uploads` creates `PENDING_UPLOAD` media and returns a short-lived direct upload URL, `POST /api/v1/media/{mediaId}/complete` validates/processes the media, and `POST /api/v1/listings/{id}/images` associates the READY `mediaId` with the listing. Raw image bytes never pass through the Spring Boot heap.
- Server-side re-validation of resolution/size/count is mandatory even though the client also gates these — never trust client-reported values.
- `perceptual_hash` is computed by media processing at upload time and stored in `media_assets` even though nothing consumes it until US-082 (Sprint 9 watermark detection) — avoids a backfill migration later.

**Corrections found by grounding this plan against the actual codebase** (the LLD was written before this cross-check; per the `US-Implementor` workflow, the LLD's Part E should be reconciled with these findings after implementation):
- `com.valuex.listing.domain.ListingState` and `ListingStateMachine` **already exist** (built under S0-008's generic `com.valuex.common.statemachine.StateMachine<S>` framework, same pattern as `auth`'s `UserAccountStateMachine`). The LLD's Part E proposed a separate DB-backed `listing_status_transitions` whitelist table and a bespoke `INVALID_LISTING_STATE_TRANSITION` error code — this plan instead **reuses the existing in-code state machine**, whose real error code is `INVALID_STATE_TRANSITION` (from `ValidationException`, thrown by `StateMachine.transition()`). No `listing_status_transitions` table will be created.
- `listings.status` will be persisted as the existing `ListingState` enum, not a newly-defined Postgres enum type — avoids two competing sources of truth for the same state set.
- `com/valuex/listing/**` is currently in **both** the JaCoCo and SonarQube exclusion lists in `pom.xml` (as a not-yet-implemented future-sprint stub, per `Documents/SonarQube-Setup-Guide.md`). This story must remove those two exclusion lines so the new code is actually measured for coverage and scanned.
- Object storage is now an approved configurable-provider design: Cloudflare R2 Standard + Cloudflare CDN for MVP, accessed only through `ObjectStoragePort` and selected by external configuration (`OBJECT_STORAGE_PROVIDER`, endpoint, credentials, bucket prefix, CDN URL). AWS S3/Backblaze B2 remain plug-in adapter options after their adapters exist; business code must not change for provider switching.
- `valuex-mobile` is the Flutter app. The Figma Make `CreateListingScreen` (React) is used only as the **visual reference** for the photo step; the Flutter screen adds the "Let AI do the work for you" card and "Photo tips for best results" section, and the bottom button reads **Submit to AI** (replacing "Add at least 2 photos"). The story's rule of min 1 / max 10 photos wins over the prototype's min 2 / max 8.

## 4. Implementation Steps

### DB Migration (valuex-backend)
- [x] Add Flyway migration `V10__listing_media_schema.sql` (originally `V9`; renumbered after a version clash with another V9 on main):
  - `listings` table: `id, seller_id, title, description, condition, price, status, plan_type, ai_assisted, seller_location, expires_at, created_at, updated_at` (status stored as `VARCHAR`, mapped via `@Enumerated(EnumType.STRING)` to `ListingState` — no new Postgres `ENUM` type, per §3 correction).
  - `media_assets` table: shared media metadata (`owner_type`, `owner_id`, `media_purpose`, provider/bucket/object reference, detected content type, size, dimensions, checksum, `perceptual_hash`, status, visibility, retention/delete timestamps).
  - `media_variants` table: generated derivative metadata (`thumbnail`, `card`, `detail`, `zoom`) with object key, content type, size, and dimensions.
  - `listing_images` table: `id, listing_id, media_asset_id, sort_order, created_at` — listing-specific association/order only; no raw URLs or provider-specific fields.
  - `listing_status_history` table: `id, listing_id, from_status, to_status, changed_by, reason, changed_at` (write-only audit log, caller's responsibility per `StateMachine`'s doc comment).
  - Indexes: `idx_listings_seller_status(seller_id, status)`, `idx_listing_images_listing(listing_id)`, unique `(listing_id, sort_order)`.

### Backend — Domain
- [x] `com.valuex.listing.domain.Listing` — JPA entity, `@Enumerated(EnumType.STRING)` status field typed `ListingState` (reuse existing enum, do not add a new one).
- [x] `com.valuex.listing.domain.ListingImage` — JPA entity.
- [x] `com.valuex.listing.domain.ListingStatusHistory` — JPA entity.
- [x] `com.valuex.listing.domain.ListingCreatedEvent` — domain event, published on successful draft creation (mirrors `auth`'s `AccountCreatedEvent` pattern).

### Backend — Media Module / Ports & Adapters
- [x] `com.valuex.media.port.ObjectStoragePort` — provider-neutral interface: `createUploadAuthorization`, `getMetadata`, `createDownloadAuthorization`, `delete`, `copy`.
- [x] `com.valuex.media.infrastructure.CloudflareR2ObjectStorageAdapter` — MVP/default adapter, selected by `OBJECT_STORAGE_PROVIDER=r2`.
- [x] Configuration properties for `valuex.media.storage.*`: provider, endpoint, region, access key, secret key, bucket prefix, CDN base URL, upload URL TTL, download URL TTL.
- [x] Provider-neutral plug-in point documented for future `AwsS3ObjectStorageAdapter` and `BackblazeB2ObjectStorageAdapter`; only the R2 adapter is implemented in this story.
- [x] `MediaAssetService` to create upload authorization, complete upload, verify metadata, enforce media lifecycle (`PENDING_UPLOAD` → `READY`/`REJECTED`), and expose `requireReadyAsset(mediaId, ownerId, purpose)` to Listing.

### Backend — Application
- [x] `com.valuex.listing.application.dto`: `CreateListingResponse`, `AttachListingImageRequest`, `AttachListingImageResponse`, `ListingDraftResponse`.
- [x] `com.valuex.listing.application.service.ListingDraftService`:
  - `createDraft(sellerId)` → `Listing` in `DRAFT` (initial value, no `ListingStateMachine.transition()` call needed — `DRAFT` is the entity's default/initial state, not a transition target in the existing state machine). A new draft has `seller_location` NULL (design change, Oct 2026): it is no longer copied from the user's city, because the profile has no city. The seller chooses the pickup address in the listing flow (US-004 post step) and the city of that address becomes the item's location.
  - `attachListingImage(listingId, sellerId, AttachListingImageRequest)` → ownership/status guard, `count < 10`, calls `MediaAssetService.requireReadyAsset(mediaId, sellerId, LISTING_IMAGE)`, re-validates `width/height >= 480` and `sizeBytes <= 10MB`, else `BusinessException` with the exact codes from §2 Error Scenarios.
  - `deleteImage(listingId, sellerId, imageId)`.
  - `getDraft(listingId, sellerId)`.
  - Shared `requireOwnedDraft(listingId, sellerId)` helper (per LLD §A.5) — reused as-is by US-005/US-006/US-010 when those stories land.

### Backend — API
- [x] `com.valuex.listing.api.ListingController`:
  - `POST /api/v1/listings`
  - `POST /api/v1/listings/{id}/images`
  - `DELETE /api/v1/listings/{id}/images/{imageId}`
  - `GET /api/v1/listings/{id}`
  - `POST /api/v1/listings/{id}/submit`
  - `@PreAuthorize` role check + `SecurityContext.getCurrentUserId()` for ownership (never a client-supplied `sellerId`), consistent with the rest of the codebase.
- [x] `com.valuex.media.api.MediaController`:
  - `POST /api/v1/media/uploads`
  - `POST /api/v1/media/{mediaId}/complete`
  - `GET /api/v1/media/{mediaId}`
  - `DELETE /api/v1/media/{mediaId}`
  - `POST /api/v1/media/{mediaId}/access`
  - Signed URLs are short-lived and returned only after authorization; signed URLs are never stored as canonical database values.

### Backend — Build Config
- [x] `pom.xml`: remove `**/com/valuex/listing/**` from `sonar.exclusions` and from the JaCoCo `<excludes>` list — this module is no longer a future-sprint stub.
- [x] `pom.xml`: add the S3-compatible storage client dependency used by the provider adapter.

### Mobile (valuex-mobile, Flutter)
- [x] `features/listing/domain/listing_photo.dart` — photo rules (max 10, 10 MB, 480×480), magic-byte type detection, upload status per photo.
- [x] `features/listing/data/photo_source.dart` — camera/gallery via `image_picker` (scaled to ≤2560 px), real dimensions via `ui.ImageDescriptor`, permission-denied mapping.
- [x] `features/listing/data/listing_repository.dart` — `POST /listings`, `POST /media/uploads`, direct `PUT` to the signed URL with a plain Dio (no bearer token), `POST /media/{id}/complete`, `POST/DELETE /listings/{id}/images`.
- [x] `CreateListingController` — creates the draft on the first valid photo, validates on device, uploads photos concurrently, retry/remove, `canSubmit` when ≥1 photo is ready and nothing is in flight.
- [x] `CreateListingScreen` (`/sell`, opened from the bottom-nav **Sell** tab; signed-in + Aadhaar-verified only) — opens the camera on entry, Figma photo-step layout, AI intro card, photo tips, **Submit to AI**.
- [x] English + Hindi strings; iOS `NSCameraUsageDescription` / `NSPhotoLibraryUsageDescription`.
- [ ] "Submit to AI" currently confirms the photos are saved; wiring it to AI analysis is US-005.
- [ ] Resuming an unfinished draft (`GET /listings/{id}`) from the app is not built; each Sell session starts a new draft.

## 5. Test Plan

Target ≥90% line coverage on new `listing` package classes (now that it's out of the JaCoCo exclusion list).

| Test | Maps To |
|---|---|
| `createDraft` returns listing in `DRAFT` for an `ACTIVE` seller | AC: tap "Sell Item" → capture opens |
| `createUploadAuthorization` persists `media_assets.status=PENDING_UPLOAD` and returns a short-lived upload URL | AC: photos are uploaded to the system |
| `completeUpload` validates uploaded metadata and moves media to `READY` after processing succeeds | Validation: real upload completion path |
| `attachListingImage` succeeds for image 1–10 when the media asset is READY and purpose is `LISTING_IMAGE` | AC: capture up to 10 photos |
| `attachListingImage` rejects the 11th image with `ERROR_MAX_PHOTOS_EXCEEDED` | Edge case: >10 photos attempted |
| `attachListingImage` rejects width/height < 480 with `ERROR_INVALID_PHOTO` | Validation: min resolution |
| `attachListingImage` rejects size > 10MB with `ERROR_INVALID_PHOTO` | Validation: max size |
| `attachListingImage` rejects non-READY media with `ERROR_PHOTO_UPLOAD_FAILED` or `ERROR_INVALID_PHOTO` | Edge case: failed/incomplete upload |
| `attachListingImage` throws 404 `LISTING_NOT_FOUND` for a listing owned by another seller | Security: ownership/IDOR |
| `attachListingImage` throws 400 when listing not in `DRAFT` (e.g. already `PUBLISHED`) | State guard |
| `deleteImage` removes an image and re-sequences `sort_order` | Basic CRUD correctness |
| `getDraft` returns persisted images to resume an in-progress draft | Resume-draft flow |
| Integration: full `POST /listings` → `POST /media/uploads` → direct `PUT` (mocked `ObjectStoragePort`) → `POST /media/{mediaId}/complete` → `POST /listings/{id}/images` round trip via `@SpringBootTest` + Testcontainers Postgres | End-to-end happy path |
| Integration: complete/attach flow when object metadata is missing or invalid | Edge case: network failure / corrupted upload |
| Configuration test: `OBJECT_STORAGE_PROVIDER=r2` wires `CloudflareR2ObjectStorageAdapter` behind `ObjectStoragePort`; listing services never depend on provider classes | Plug-and-play storage requirement |

Non-item/random-photo detection is **not** testable here (LLD §A.1.1: AI's advisory concern in US-005). Camera-permission denial and the client-side rules are covered by Flutter tests in `test/features/listing/create_listing_test.dart`.

## 6. Validation Checklist

- [x] Min 1 photo required before proceeding past capture step (client-gated; confirm backend intentionally allows a 0-image `DRAFT` to persist so a seller can resume later).
- [x] Max 10 photos enforced both client- and server-side.
- [x] Format restricted to JPG/PNG/HEIC (content-type validated server-side, not just filename extension, per `CODING_STANDARDS.md` §1.5).
- [x] Max 10MB per photo enforced server-side.
- [x] Min resolution 480×480px enforced server-side.
- [x] `ERROR_CAMERA_PERMISSION_DENIED` handled client-only (no backend involvement).
- [x] `ERROR_MAX_PHOTOS_EXCEEDED`, `ERROR_PHOTO_UPLOAD_FAILED`, `ERROR_INVALID_PHOTO` all return the exact codes/messages from `user-stories.md`.
- [x] Ownership check prevents any cross-seller access to another seller's draft/images.
- [x] `listing_images` stores `media_asset_id`, not provider URLs; client responses expose media resources/variants, not bucket internals.
- [x] Object storage provider is selected through external config, not business-code changes; `CloudflareR2ObjectStorageAdapter` is the MVP adapter behind `ObjectStoragePort`.
- [x] Signed upload/access URLs are short-lived and never persisted as canonical database values.
- [x] Only an `ACTIVE` seller (per US-001/US-088 account state) can create a listing — confirm against current account-status gating used elsewhere (e.g. `AadhaarGatingInterceptor`/`assertLoginEligible`-style checks), since this LLD doesn't specify the exact status guard.
- [x] `com/valuex/listing/**` removed from both Sonar and JaCoCo exclusion lists in `pom.xml`.

## 7. Open Gaps / Questions

1. ~~No object storage backend exists yet~~ — **Resolved:** shared Media Module with `ObjectStoragePort`; Cloudflare R2 by default. Local development uses a RustFS S3-compatible container from `docker-compose.yml` (host port 9300, because SonarQube uses 9000).
2. ~~`valuex-mobile` is a React/Vite prototype~~ — **Resolved:** `valuex-mobile` is the Flutter app; mobile wiring is implemented in this story.
3. ~~Seller account-status gating~~ — **Resolved:** `createDraft` requires `ACTIVE` (`ACCOUNT_NOT_ACTIVE`) and is not Aadhaar-gated; `POST /listings/{id}/submit` is annotated `@RequiresIdentityVerification` (`AADHAAR_VERIFICATION_REQUIRED`). The app lets Sell open and asks for Aadhaar only after the seller submits, then returns to Sell with the photos kept.
4. ~~Migration version number~~ — **Resolved:** `V10`.

---

## 8. Implementation Reconciliation

- [x] Backend first pass (commit f906746, merged to main): listing/media modules, R2 adapter, tests.
- [x] Migration renumbered to `V10__listing_media_schema.sql`.
- [x] Added [US-004-Testing-Guide.md](../scripts/US-004-Testing-Guide.md).
- [ ] Asynchronous media-worker validation, AVIF/WebP derivative generation, EXIF stripping and production R2/IaC provisioning remain deployment follow-ups.

### 8.1 Gap-fix pass (branch `feature/us-004-gap-fixes`, 2026-10-14)

Gaps found in review and fixed:

| # | Gap | Fix |
|---|---|---|
| 1 | `completeUpload` trusted client-reported width/height and content type | Reads the first 512 KB of the stored object (`ObjectStoragePort.readHead`), detects JPEG/PNG/HEIC by magic bytes, reads JPEG/PNG dimensions from the bytes (`ImageInspector`) |
| 2 | `REJECTED` status was rolled back with the exception, leaving media `PENDING_UPLOAD` | `@Transactional(noRollbackFor = BusinessException.class)`; rejected objects are also deleted from storage |
| 3 | Missing object / storage outage surfaced as HTTP 500 | Adapter wraps SDK errors in `StorageException`; complete returns `ERROR_PHOTO_UPLOAD_FAILED` and keeps the asset retryable |
| 4 | Any status could be completed (e.g. `REJECTED`/`DELETED` revived) | Only `PENDING_UPLOAD` completes; `READY` is idempotent |
| 5 | Concurrent attaches could exceed 10 photos or collide on `sort_order` | Pessimistic row lock on the listing for attach/delete; explicit `MEDIA_ALREADY_ATTACHED` / `LISTING_IMAGE_ORDER_CONFLICT` |
| 6 | Deleting an image re-sequenced in one pass and hit the unique `(listing_id, sort_order)` index (found by the new integration test) | Two flushed passes via negative positions |
| 7 | Deleting attached media orphaned `listing_images`; deleting twice called storage again | `MEDIA_IN_USE`, no-op for already deleted, `DELETION_PENDING` when storage is down; removing a listing image now deletes its media |
| 8 | Signed download URL issued for non-READY media | `MEDIA_NOT_READY` |
| 9 | No `listing_status_history` row for draft creation | `null → DRAFT` row with `DRAFT_CREATED` |
| 10 | Aadhaar gate not applied to listing creation | `@RequiresIdentityVerification` on `POST /listings/{id}/submit` (not on draft creation) |
| 11 | Object key extension came from the client file name; file name unbounded | Extension from validated content type; file name sanitised/truncated; `@Size` on request fields; HEIF normalised to HEIC |
| 12 | Max-10 only checked at attach, so unlimited uploads were possible | Upload authorization refuses once 10 READY photos exist; listing photos must be owned by a `LISTING` |
| 13 | Variant map exposed raw bucket object keys | CDN URLs for public media only |
| 14 | A new S3 client/presigner was built per call; presigned URLs used the internal endpoint | One cached client/presigner; `public-endpoint` + `path-style-access` settings |
| 15 | No integration test | `ListingPhotoFlowIntegrationTest` (Testcontainers PostgreSQL) |
| 16 | No mobile client | Flutter Sell flow (§4 Mobile) |

Validation: `mvn verify` 418 tests green, checkstyle clean, listing+media line coverage 97.5%; SonarQube shows no open issues in listing/media (remaining quality-gate failures are pre-existing in `auth`/`common`). Flutter: see the testing guide.

**Status:** Gap fixes implemented — awaiting user approval to commit, push and open the PR.
