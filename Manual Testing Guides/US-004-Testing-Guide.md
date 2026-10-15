# US-004: Create Listing with Photo Capture — Testing Guide

## 1. Purpose

This guide covers manual and automated verification of the backend implementation for US-004. The implementation is backend-only. `valuex-mobile` is a React trial prototype and is intentionally not used; the future Flutter client will consume the APIs documented here.

## 2. Prerequisites

- Java 21 and Maven 3.9+.
- PostgreSQL 16 with the existing ValueX schema, or Docker Desktop for Testcontainers integration tests.
- A configured S3-compatible object store for end-to-end upload testing. Cloudflare R2 is the default provider; use `OBJECT_STORAGE_PROVIDER=r2` and the environment-specific endpoint/credentials.
- A valid authenticated seller access token for API tests. The seller must have account status `ACTIVE`.
- Optional: an HTTP client such as Swagger UI, Postman, or curl.

## 3. Backend Configuration

Configure these environment variables without committing secrets:

```text
OBJECT_STORAGE_PROVIDER=r2
OBJECT_STORAGE_ENDPOINT=https://<account-id>.r2.cloudflarestorage.com
OBJECT_STORAGE_REGION=auto
OBJECT_STORAGE_ACCESS_KEY_ID=<secret>
OBJECT_STORAGE_SECRET_ACCESS_KEY=<secret>
OBJECT_STORAGE_BUCKET_PREFIX=valuex-dev
MEDIA_CDN_BASE_URL=https://media-dev.valuex.com
```

The backend uses the provider-neutral `ObjectStoragePort`. Do not place provider credentials in a client or call R2/AWS SDKs directly from listing code.

Start the backend from `valuex-backend/`:

```powershell
mvn spring-boot:run
```

Swagger UI is available at `http://localhost:8080/swagger-ui.html` when enabled.

## 4. Automated Tests

Run the focused US-004 tests:

```powershell
mvn test "-Dtest=MediaAssetServiceTest,ListingDraftServiceTest,ListingControllerTest,MediaControllerTest"
```

Run the complete backend verification:

```powershell
mvn verify
```

Expected result: all executable tests pass, Checkstyle reports zero violations, and the JaCoCo coverage gate passes. The application-context integration test requires Docker/Testcontainers; if Docker is unavailable, it is skipped by the existing project test configuration.

## 5. API Test Flow

### 5.1 Create a draft

Request:

```http
POST /api/v1/listings
Authorization: Bearer <seller-access-token>
```

Expected result: HTTP `201`, `success=true`, a new `listingId`, and `status=DRAFT`.

### 5.2 Request media upload authorization

Request:

```http
POST /api/v1/media/uploads
Authorization: Bearer <seller-access-token>
Content-Type: application/json

{
  "purpose": "LISTING_IMAGE",
  "ownerType": "LISTING",
  "ownerId": "<listingId>",
  "fileName": "item.jpg",
  "contentType": "image/jpeg",
  "sizeBytes": 2500000
}
```

Expected result: HTTP `200`, a `mediaId`, and a short-lived `uploadUrl`. The media record is `PENDING_UPLOAD`.

### 5.3 Upload and complete media

Use the returned URL for a direct `PUT` of the image bytes. Then call:

```http
POST /api/v1/media/<mediaId>/complete
Authorization: Bearer <seller-access-token>
Content-Type: application/json

{
  "contentType": "image/jpeg",
  "sizeBytes": 2500000,
  "width": 1200,
  "height": 1200,
  "checksum": "optional-checksum",
  "perceptualHash": "optional-phash"
}
```

Expected result: HTTP `200`, `status=READY`, and stored dimensions/content metadata.

### 5.4 Attach the media to the listing

```http
POST /api/v1/listings/<listingId>/images
Authorization: Bearer <seller-access-token>
Content-Type: application/json

{
  "mediaId": "<mediaId>"
}
```

Expected result: HTTP `200` with an `imageId`, the same `mediaId`, and `sortOrder=0`.

Repeat steps 5.2–5.4 for up to 10 images.

### 5.5 Resume the draft

```http
GET /api/v1/listings/<listingId>
Authorization: Bearer <seller-access-token>
```

Expected result: HTTP `200`, `status=DRAFT`, and the attached images ordered by `sortOrder`.

## 6. Manual Test Cases

| ID | Scenario | Steps | Expected Result |
|---|---|---|---|
| TC-01 | Create draft as active seller | Call `POST /api/v1/listings` with an active seller token | `201`; draft is created in `DRAFT` state |
| TC-02 | Upload supported JPEG | Create an upload authorization, direct-upload a valid JPEG, complete it | Media reaches `READY` |
| TC-03 | Supported PNG/HEIC | Repeat with valid PNG and HEIC content | Each valid image is accepted |
| TC-04 | Attach ready image | Attach a READY `LISTING_IMAGE` media ID to its owning draft | Image is associated with `sortOrder` assigned |
| TC-05 | Minimum one photo | Complete one valid upload and attach it | Seller can proceed to details; backend has one listing image |
| TC-06 | Maximum ten photos | Attach ten valid images to one draft | All ten succeed |
| TC-07 | Eleventh photo | Attempt to attach an eleventh image | `ERROR_MAX_PHOTOS_EXCEEDED`, HTTP `400` |
| TC-08 | Oversized photo | Request upload/complete with size greater than 10 MB | `ERROR_INVALID_PHOTO`; no READY media is created |
| TC-09 | Small resolution | Complete with width or height below 480 pixels | `ERROR_INVALID_PHOTO`; media becomes `REJECTED` |
| TC-10 | Unsupported format | Request upload with GIF or non-image content type | `ERROR_INVALID_PHOTO`, HTTP `400` |
| TC-11 | Incomplete upload | Do not complete the direct upload, then attempt listing attachment | Attachment is rejected because media is not `READY` |
| TC-12 | Wrong seller listing access | Use seller B's token with seller A's listing ID | `LISTING_NOT_FOUND`; no upload URL or image association is issued |
| TC-13 | Wrong listing media | Use a READY media asset owned by another listing | `MEDIA_NOT_FOUND`; asset is not attached |
| TC-14 | Non-draft listing | Change the listing state outside this flow, then attempt attachment | `LISTING_NOT_IN_DRAFT` / business error; no image is attached |
| TC-15 | Remove image | Delete an attached image from the draft | Image is removed and remaining images are resequenced |
| TC-16 | Signed access | Call `POST /api/v1/media/{mediaId}/access` as the owner | Short-lived access URL returned; URL is not persisted as canonical metadata |
| TC-17 | Unauthorized media access | Call media GET/access/delete with another seller's token | `MEDIA_NOT_FOUND` or equivalent authorization failure |
| TC-18 | Storage provider abstraction | Set `OBJECT_STORAGE_PROVIDER=r2` and inspect startup/integration wiring | R2 adapter is selected; listing services depend only on `ObjectStoragePort` |
| TC-19 | Network/upload failure | Simulate failed direct upload or unavailable object store | Client can retry; media does not become `READY`; no listing image is attached |
| TC-20 | Camera permission | Deny camera permission in the future Flutter client | Client shows `ERROR_CAMERA_PERMISSION_DENIED`; backend remains unaffected |
| TC-21 | Camera failure fallback | Make camera unavailable in the future Flutter client | Client offers gallery fallback; no backend regression |
| TC-22 | Non-item image | Submit a random/non-item image | Accepted by US-004 media validation; AI/moderation handling belongs to US-005/US-007 |

## 7. Acceptance Criteria Traceability

- Camera opens after the seller selects Sell Item: future Flutter-client responsibility; no React prototype testing is included.
- At least one photo can be uploaded: TC-02 through TC-05.
- Maximum 10 photos: TC-06 and TC-07.
- Photos are uploaded and persisted through R2-compatible direct upload: TC-02, TC-04, TC-18, TC-19.
- Seller can proceed to item details after photo capture: backend returns a valid draft with attached READY media; future Flutter flow consumes TC-05 response.

## 8. Known Scope Boundaries

- Camera permission, camera startup failure, gallery UI, upload progress, and client retry UX belong to the future Flutter app.
- Non-item/random-photo classification belongs to AI/moderation stories.
- AVIF/WebP derivative generation and asynchronous media-worker processing are not yet implemented in this US-004 backend slice; the media lifecycle and storage abstraction are ready for that follow-up.
- Docker/Testcontainers is required for the full application-context integration test. Without Docker, unit/controller tests still provide local validation and the existing context test may be skipped.
