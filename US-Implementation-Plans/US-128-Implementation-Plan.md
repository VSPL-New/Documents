# US-128: Listing Photo Variants - Implementation Plan

## 1. Header

| Field | Value |
|---|---|
| Story | US-128 - Listing Photo Variants (thumbnail, card, detail, zoom); a new story added by the Sprint 3 LLD |
| Sprint | Sprint 3 - Discovery & Search |
| Story points | 5 (proposed) |
| Repos involved | valuex-backend (code, `Dockerfile`, `docker-compose.yml`, README). No mobile change: the apps consume the new URLs in US-011, US-012, US-073 and US-111. |
| Dependencies | US-004 (media upload, tables and CDN mapping, built). Soft dependency on [US-120](US-120-Implementation-Plan.md) section 4.4 (Admin settings foundation) for one setting; see gap G3. Built in parallel with US-120. |
| Date | 2026-11-09 |
| Design source | [Sprint 3 LLD](../LLD/Sprint-3-Discovery-Search-LLD.md), Part H and section 1.4 (final, approved 2026-11-09); [object storage design](../Valuex-Object-Storage-Design-Decision.md) sections 6 to 8 |
| Branch (proposal) | `feature/US-128-listing-photo-variants` from the latest `main` in `valuex-backend` |
| Flyway number | The LLD says `V30`, provisional. Take the next free number when the branch is cut. |

## 2. Story Recap

**As a** buyer **I want** listing photos to load quickly in lists and galleries **so that** browsing is smooth on mobile networks.

### Acceptance Criteria (user-stories.md US-128)

| ID | Behaviour |
|---|---|
| AC1 | A ready listing photo gets four copies: thumbnail (about 300 px), card (about 600 px), detail (about 1200 px), zoom (about 1600 px); aspect ratio kept; never enlarged. |
| AC2 | The copies are rotation-corrected and carry no location or other camera data. |
| AC3 | Cards show the card variant; compact lists the thumbnail; the gallery the detail variant; full-screen zoom the zoom variant. Buyers never receive the original once variants exist. |
| AC4 | While variants are not ready, the original is shown through a short-lived signed link. |
| AC5 | Deleting a listing photo deletes its variants. Photos uploaded before this story are processed in the background. |

**Edge cases:** HEIC photos; very large or corrupt images; one size failing; backlog after a mass upload; CDN not configured in development.
**Validation:** only listing photos are processed; a failed photo is retried a limited number of times, then marked failed and keeps using the fallback; variant sizes and quality are deployment configuration.
**Errors:** none user-facing; failures raise an operations alert.

## 3. Design Reference

LLD Part H (H.3 data, H.4 targets, H.5 design, H.7 NFR, H.8 tests) and LLD section 1.4 (photo URL rules and the variant used per surface).

### Verified Implementation Anchors (checked in the code on 2026-11-09)

| Area | Finding and consequence |
|---|---|
| Tables and types | `media_variants` (V10: `variant_type`, `object_key`, `content_type`, `size_bytes`, `width`, `height`) and `MediaVariantType` (`THUMBNAIL`, `CARD`, `DETAIL`, `ZOOM`) exist. No code writes them. `MediaVariantRepository` only has `findByMediaAssetId`. |
| Delivery mapping | `MediaAssetResponse.from` already maps variants to `cdnBaseUrl + objectKey`; `MediaAssetService.toResponse` does this for `PUBLIC_DERIVATIVE` assets; `visibilityFor(LISTING_IMAGE)` is `PUBLIC_DERIVATIVE`. `valuex.media.storage.cdn-base-url` defaults to `https://media-dev.valuex.com`. |
| Storage port | `ObjectStoragePort` has `readHead`, presigned upload and download links, `delete`, `copy`. It has **no full read and no write of an object**, so this story adds both. The only implementation is `CloudflareR2ObjectStorageAdapter` (AWS SDK `S3Client`). |
| Download links | `createDownloadAuthorization` signs for devices (`public-endpoint`); `createServerDownloadAuthorization` signs for the server. The LLD names the server one for the fallback; a phone needs the device one (gap G4). |
| Original keys and buckets | `objectKeyFor` gives `listing_image/{ownerId}/{uuid}{ext}`; `bucketFor(LISTING_IMAGE)` is `<prefix>-listing-media`. Variants go to a separate public bucket (decision G1, section 4.5). |
| Upload validation | `ImageInspector` reads only the first 512 KB; HEIC is accepted with no dimensions (`MediaAssetService` allows an unreadable HEIC and trusts the client's width and height). Nothing caps pixel count before a full decode. |
| Deletion | `MediaAssetService.delete` sets `DELETED` or `DELETION_PENDING` and deletes the original only; variants are untouched. `ListingDeletionService` is a soft delete that does not touch media. |
| Media status | `MediaStatus.READY` is set at upload completion, before any derivative exists; this story does not change that (variants arrive later, delivery falls back). |
| Runtime image | `valuex-backend/Dockerfile` is `eclipse-temurin:21-jre-alpine`, runs as a non-root user. |
| Tests | No fake `ObjectStoragePort` exists; tests mock it. Fixture images do not exist under `src/test/resources`. |

## 4. Implementation Steps

### 4.1 Branch and spike
- [ ] Cut the branch; run the media tests for a green baseline.
- [ ] Spike (half a day, before coding the processor): on the target image, confirm the Alpine packages for libvips with HEIC support (`vips`, `vips-tools`, `vips-heif` or equivalent), the exact `vipsthumbnail` flags for "fit inside, never enlarge, auto-rotate, strip metadata, JPEG quality 82", and `vipsheader` output for width and height. Record the result in the pull request. Decision G2 (2026-11-09): if the spike shows Alpine cannot decode HEIC, switch the runtime image to a Debian-based Temurin image instead of shipping without HEIC variants.

### 4.2 Configuration (`MediaVariantProperties`, prefix `valuex.media.variant`, deployment values)
- [ ] `processor` (`imageio` default, `vips` in production), `jpeg-quality` 82, `sizes` (thumbnail 300, card 600, detail 1200, zoom 1600 px longest side), `poll-interval` 10s, `batch-size` 10, `concurrency` 2, `max-attempts` 5, `max-pixels` 50,000,000, `vips-path`, `process-timeout` 30s, `temp-dir`.
- [ ] `MediaStorageProperties`: `variantBucketSuffix` (default `-listing-variants`); the variants bucket is `<bucket-prefix>-listing-variants` (decision G1).
- [ ] Defaults in `application.yml`; test profile uses `imageio`.

### 4.3 Database migration `V30__listing_photo_variants.sql` (number provisional)
- [ ] `media_assets.variant_status` (`PENDING` default, check `PENDING`, `READY`, `FAILED`), `variant_attempts`, `variant_error`.
- [ ] Unique index `uq_media_variants_asset_type (media_asset_id, variant_type)` and the partial pending index of LLD H.3.
- [ ] Existing `READY` listing photos start `PENDING`, which is the backfill; other purposes are ignored by the job.
- [ ] `MediaAsset` entity gets the three fields; `MediaVariantRepository` gets `findByMediaAssetIdIn` and `deleteByMediaAssetId`.

### 4.4 Storage port
- [ ] `ObjectStoragePort`: `download(StorageObjectKey, Path)` and `upload(StorageObjectKey, Path, contentType, cacheControl)`; implement in `CloudflareR2ObjectStorageAdapter` with `ResponseTransformer.toFile` and `RequestBody.fromFile`; unit tests with a mocked `S3Client`, same style as the existing adapter tests.
- [ ] Test support: an in-memory `ObjectStoragePort` fake in `src/test`.

### 4.5 Generation
- [ ] `ImageVariantProcessor` port: input file path and content type, list of `VariantSpec(type, maxSide)`, output files with width, height and size; a typed failure with a reason.
- [ ] `ImageIoVariantProcessor` (JPEG and PNG): decode once, apply the EXIF orientation (small parser of the APP1 orientation tag, no new dependency), scale with high-quality interpolation, never enlarge, write JPEG without metadata. A HEIC input returns the failure `HEIC_NEEDS_VIPS` at once, so it is not retried.
- [ ] `VipsVariantProcessor`: runs `vipsheader` first and refuses an image above `max-pixels`; then `vipsthumbnail` per size, using `ProcessBuilder` with an argument list (no shell), a private temp directory, generated file names only, `process-timeout` with forced kill, and a truncated stderr in the error.
- [ ] `MediaVariantService.generate(mediaId)`: loads the asset, downloads the original to a temp file, runs the processor, uploads each variant to `listing_image_variants/{mediaId}/{thumb|card|detail|zoom}.jpg` in the separate variants bucket with `Cache-Control: public, max-age=31536000, immutable`, then inserts the four `media_variants` rows in one transaction (rows already present are reused, so a retry is idempotent); always removes the temp files.
- [ ] `MediaVariantJob` (`@Scheduled`): claims pending `LISTING_IMAGE` assets in status `READY` with `FOR UPDATE SKIP LOCKED`, limits concurrency, marks `READY` on success or increments attempts with the error, and `FAILED` after `max-attempts`. A failure never stops the batch.
- [ ] Metrics: `media.variant.generated.total{type}`, `media.variant.failed.total`, `media.variant.pending` (gauge), generation timer. Alert when pending is above 500 for 30 minutes or any asset is `FAILED`.

### 4.6 Delivery port and deletion
- [ ] `ListingPhotoLinkPort.urls(listingId, mediaIds)` and `ListingPhotoLinkAdapter`: confirms the media ids belong to the listing (`listing_images`) and are `READY`; one query for variants of the page; returns `thumbnailUrl`, `cardUrl`, `detailUrl`, `zoomUrl`; CDN URLs (no expiry) when all four variants exist and `cdn-base-url` is set, otherwise one signed link to the original in all four fields with `expiresAt` (device-reachable authorization, gap G4); the original is never returned once variants exist.
- [ ] Fallback lifetime is the Admin setting `PHOTO_FALLBACK_LINK_MINUTES` (default 15) through `PlatformSettingsService` (gap G3).
- [ ] `MediaAssetService.delete` also deletes the variant objects and rows; a storage failure leaves the asset `DELETION_PENDING` as the original does today.

### 4.7 Dockerfile, compose and docs
- [ ] `Dockerfile`: install libvips (per the spike) before switching to the non-root user; if the spike requires it (decision G2), change the base image to a Debian-based `eclipse-temurin:21-jre` and install libvips with HEIF support through `apt`; keep the non-root user and the health check; set `MEDIA_VARIANT_PROCESSOR=vips` for the production profile.
- [ ] `docker-compose.yml`: create the separate variants bucket next to the existing media buckets for local use (check how the existing buckets are created).
- [ ] Infra hand-off (not code): create `<prefix>-listing-variants` in each environment and expose only that bucket through the CDN at `valuex.media.storage.cdn-base-url`; the originals bucket `<prefix>-listing-media` stays private. Record this in the pull request and the README.
- [ ] README: how to run locally with and without libvips (`brew install vips`), how to backfill and how to read the metrics.
- [ ] LLD Part H: "As built" note for any deviation (at least the device-reachable authorization).
- [ ] After implementation, `Documents/Manual Testing Guides/US-128-Testing-Guide.md`.
- [ ] Checkstyle, full backend tests, coverage above 90% for new code, SonarQube before any push. Never push or open a pull request without asking.

## 5. Test Plan

Fixtures under `src/test/resources/media/`: JPEG, PNG, a rotated JPEG (EXIF orientation 6) with GPS data, a small image below the smallest size, a HEIC file, a corrupt file, and a PNG whose header declares huge dimensions.

### 5.1 Unit tests
- [ ] `ImageIoVariantProcessorTest`: four sizes and their dimensions; aspect ratio kept; a small image is not enlarged; EXIF orientation applied; output has no EXIF or GPS segment; corrupt input fails with a reason; HEIC returns `HEIC_NEEDS_VIPS`.
- [ ] `VipsVariantProcessorTest` (skipped when `vips` is not installed): same cases plus HEIC; the pixel cap refuses the large PNG before decoding; timeout kills a hung process; arguments are never built from user text.
- [ ] `MediaVariantServiceTest`: upload keys, cache header, rows inserted once; a retry after a partial upload is idempotent; temp files always removed.
- [ ] `MediaVariantJobTest`: claim, attempts, `FAILED` after the maximum, one failure does not stop the batch, other purposes ignored.
- [ ] `ListingPhotoLinkAdapterTest`: CDN URLs when four variants exist; fallback when fewer than four, when `cdn-base-url` is blank, and when variants are missing for some photos only; media not attached to the listing or not `READY` is not returned; the original is never in a CDN response.
- [ ] `MediaAssetServiceTest`: delete removes variants; storage failure leaves `DELETION_PENDING`.
- [ ] `CloudflareR2ObjectStorageAdapter` upload and download tests.

### 5.2 Integration tests (Testcontainers PostgreSQL, in-memory storage fake)
- [ ] Upload a photo, run the job: four variants and rows exist, status `READY`, URLs resolve to the CDN form.
- [ ] A backlog of existing `READY` photos is processed in the background.
- [ ] A corrupt photo ends `FAILED` after the attempts without blocking the others; its URLs fall back to the signed original.
- [ ] Two job instances never process one asset twice (`SKIP LOCKED`).
- [ ] Migration test: `V30` applies to a database that already has `READY` listing photos and leaves them `PENDING`.

## 6. Validation Checklist

- [ ] AC1: four sizes with the right dimensions, no enlarging, aspect kept.
- [ ] AC2: orientation corrected; no EXIF or GPS in any variant (checked on a fixture that has GPS).
- [ ] AC3: the URL port returns the four variant URLs; the original is not returned when variants exist.
- [ ] AC4: before variants exist, a signed link to the original is returned and works on a device.
- [ ] AC5: removing a photo deletes its variants; old photos are processed in the background.
- [ ] Edge cases: HEIC, oversized and corrupt images, partial failure, backlog, CDN not configured.
- [ ] Only listing photos are processed; failed photos stop after `max-attempts` and raise the alert.
- [ ] Variant sizes and quality are configuration, not Admin settings.
- [ ] Checkstyle, tests, coverage above 90%, SonarQube pass; testing guide written.

## 7. Open Gaps / Questions

1. **G1 Public exposure of derivatives (decided 2026-11-09).** Variants live in a separate bucket `<prefix>-listing-variants`, exposed through the CDN; the originals bucket stays private. Infra creates the bucket and the CDN route (section 4.7).
2. **G2 libvips on Alpine and HEIC (decided 2026-11-09).** The spike in 4.1 confirms. If Alpine cannot decode HEIC, the runtime image becomes Debian-based; HEIC photos are not left on the fallback.
3. **G3 Settings dependency.** `PHOTO_FALLBACK_LINK_MINUTES` is read through `PlatformSettingsService`, which US-120 section 4.4 builds. Preferred order: merge that small foundation first. If US-128 must land first, use `MediaStorageProperties.downloadUrlTtl` (10 minutes) and switch in a one-line follow-up.
4. **G4 LLD correction.** The LLD names `createServerDownloadAuthorization` for the fallback; that link is for the server and may use an address a phone cannot reach. The plan uses the device-reachable `createDownloadAuthorization`; the LLD gets an "As built" note.
5. **G5 Soft-deleted listings.** A soft delete keeps photos for the 90-day retention (US-010), so public variant URLs of a deleted listing stay reachable by anyone who has the URL until the purge story (US-127), which must also delete variants. Keys are unguessable. Accept, or add variant removal to the delete path (cost: regeneration if the seller undoes the delete).
6. **G6 Pixel limit.** `max-pixels` 50 MP is a proposal; confirm against the largest phone photos you expect.
7. **G7 HEIC dimensions.** For HEIC the client's declared width and height are trusted at upload; the variant job reads real dimensions (`vipsheader`) and could update the asset row. Decide whether to correct `media_assets.width` and `height` after generation (recommended, small).
8. **G8 Sequencing for US-011.** US-011 needs `ListingPhotoLinkPort`. If it starts before this story finishes, merge section 4.6 first (it works with the fallback alone).

---

**Status:** Approved (2026-11-09). The user approved this plan and asked for implementation to start.

## 8. As Built (2026-11-09)

Deviations from this plan; the full table is LLD Sprint 3, section H.9.

- Flyway number is `V26`. `media_assets` also got `variant_lease_until` (a claim lease); the queue is `MediaVariantQueue` (one `UPDATE ... RETURNING` with `SKIP LOCKED` inside), not a `SELECT ... FOR UPDATE` held during processing.
- A picture that cannot be read as an image, HEIC without libvips and an oversized picture stop at once as `FAILED`; other faults retry up to `max-attempts`, waiting `attempts` minutes between tries.
- The fallback link is the device-reachable `createDownloadAuthorization` (gap G4); its lifetime is `PHOTO_FALLBACK_LINK_MINUTES` through `PlatformSettingsService` (gap G3, US-120 foundation, so this story is built on the US-120 branch).
- Gap G7 taken: the real, rotated size is written back to `media_assets.width` and `height` when it differs.
- libvips spike (8.18.7, macOS): `vipsthumbnail in -s 'WxH>' -o '/abs/out.jpg[Q=82,strip]'`; auto-rotate is the default; HEIC reads. The Linux image was not built (no Docker here): `Dockerfile` now uses Debian-based `eclipse-temurin:21-jre` with `libvips-tools` (decision G2).
- `ListingPhotoLinkPort` is in `media/port`, its adapter in `media/infrastructure`.
- No mobile change, as planned. Nothing consumes `ListingPhotoLinkPort` yet (US-011, US-012, US-073, US-111).
- Not run: Docker image build, real R2 and CDN, HEIC on Linux, SonarQube.
- Infra hand-off still open: create `<prefix>-listing-variants` in each environment and expose only that bucket through the CDN at `valuex.media.storage.cdn-base-url`; set `MEDIA_VARIANT_PROCESSOR=vips` in production.
