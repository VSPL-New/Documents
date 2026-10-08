# US-004: Create Listing with Photo Capture — Implementation Plan

## 1. Header

| Field | Value |
|---|---|
| Story ID | US-004 |
| Title | Create Listing with Photo Capture |
| Sprint | Sprint 2 — Seller Listing Creation |
| Story Points | 8 |
| Repos | valuex-backend only for this pass (see decision below) — LLD/user story scope is valuex-mobile, valuex-backend |
| Dependency | US-001 (User Registration via Mobile OTP) — caller must be an authenticated, `ACTIVE` seller |

**Scope decision (per `CLAUDE.md` §6):** `valuex-mobile` currently contains a trial/prototype React app, not the real mobile platform — the real client will be Flutter, built separately by the UI dev team, not yet available. This implementation pass is **backend-only**; no changes are made to `valuex-mobile`. Mobile wiring is deferred to when the Flutter app exists and is out of scope here, not merely postponed within this plan.

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
- `valuex-mobile` is, in its current state, a Figma-exported **React + Vite** prototype (`CreateListingScreen.tsx` already exists with hardcoded mock photo URLs and a fake AI-progress timer), not the Flutter app assumed by `Documents/CODING_STANDARDS.md` §3 and the HLD. Per the confirmed decision in `CLAUDE.md` §6, this prototype is ignored entirely — no mobile implementation steps are included in this plan.

## 4. Implementation Steps

### DB Migration (valuex-backend)
- [x] Add Flyway migration `V9__listing_media_schema.sql`:
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
  - `createDraft(sellerId)` → `Listing` in `DRAFT` (initial value, no `ListingStateMachine.transition()` call needed — `DRAFT` is the entity's default/initial state, not a transition target in the existing state machine).
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

### Mobile — out of scope for this pass
Per `CLAUDE.md` §6, `valuex-mobile` (React/Vite trial prototype) is intentionally left untouched. No mobile steps are planned until the Flutter app exists. The backend API contract (§3) is designed to be client-agnostic so the future Flutter client can integrate against it without backend rework.

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

Non-item/random-photo detection and camera-permission-denied are explicitly **not** backend-testable here (per LLD §A.1.1: non-item detection is AI's advisory concern in US-005; camera permission is OS/client-only) — these, along with all other client-side UX behavior, are deferred to the future Flutter client and its own test suite, not covered by this backend-only pass.

## 6. Validation Checklist

- [ ] Min 1 photo required before proceeding past capture step (client-gated; confirm backend intentionally allows a 0-image `DRAFT` to persist so a seller can resume later).
- [ ] Max 10 photos enforced both client- and server-side.
- [ ] Format restricted to JPG/PNG/HEIC (content-type validated server-side, not just filename extension, per `CODING_STANDARDS.md` §1.5).
- [ ] Max 10MB per photo enforced server-side.
- [ ] Min resolution 480×480px enforced server-side.
- [ ] `ERROR_CAMERA_PERMISSION_DENIED` handled client-only (no backend involvement).
- [ ] `ERROR_MAX_PHOTOS_EXCEEDED`, `ERROR_PHOTO_UPLOAD_FAILED`, `ERROR_INVALID_PHOTO` all return the exact codes/messages from `user-stories.md`.
- [ ] Ownership check prevents any cross-seller access to another seller's draft/images.
- [ ] `listing_images` stores `media_asset_id`, not provider URLs; client responses expose media resources/variants, not bucket internals.
- [ ] Object storage provider is selected through external config, not business-code changes; `CloudflareR2ObjectStorageAdapter` is the MVP adapter behind `ObjectStoragePort`.
- [ ] Signed upload/access URLs are short-lived and never persisted as canonical database values.
- [ ] Only an `ACTIVE` seller (per US-001/US-088 account state) can create a listing — confirm against current account-status gating used elsewhere (e.g. `AadhaarGatingInterceptor`/`assertLoginEligible`-style checks), since this LLD doesn't specify the exact status guard.
- [ ] `com/valuex/listing/**` removed from both Sonar and JaCoCo exclusion lists in `pom.xml`.

## 7. Open Gaps / Questions

1. ~~No object storage backend exists yet~~ — **Resolved by architecture decision:** implement the shared Media Module with `ObjectStoragePort`; default provider is Cloudflare R2 Standard + Cloudflare CDN, selected with `OBJECT_STORAGE_PROVIDER=r2` and related external config. AWS S3 and Backblaze B2 remain plug-in provider adapters once implemented; business modules must continue to depend only on `ObjectStoragePort`.
2. ~~`valuex-mobile` is a React/Vite prototype, not the Flutter app~~ — **Resolved:** confirmed by the user this is a trial prototype only; the real Flutter app is being built separately by the UI dev team and isn't available yet. This plan is backend-only; mobile wiring is deferred until the Flutter app exists (see `CLAUDE.md` §6).
3. **Seller account-status gating for listing creation** isn't specified in US-004's own acceptance criteria or the LLD — only "logged in as a seller." Confirm which `UserAccountState` values are allowed to create a listing (presumably `ACTIVE` only, mirroring US-081's later "block transactions for users under investigation" rule), so `ListingDraftService.createDraft` can enforce it now rather than retrofitting in Sprint 9.
4. **Migration version number** (`V{N}`) must be set to the actual next available Flyway version at implementation time, not the LLD's placeholder.

---

## 8. Implementation Reconciliation

- [x] Backend-only scope applied; `valuex-mobile` was not modified.
- [x] Added Flyway migration `V9__listing_media_schema.sql` with listings, media assets/variants, listing-image associations, and status history.
- [x] Added Listing and Media domain models, repositories, `ListingDraftService`, `MediaAssetService`, REST controllers, `ObjectStoragePort`, and the Cloudflare R2 S3-compatible adapter.
- [x] Added service/controller tests and verified focused tests pass.
- [x] Added [US-004-Testing-Guide.md](US-004-Testing-Guide.md).
- [ ] Asynchronous media-worker validation, AVIF/WebP derivative generation, and production R2/IaC provisioning remain deployment follow-ups; the backend lifecycle and provider abstraction are implemented for this story.

**Status:** Implemented — awaiting user approval to commit and push
