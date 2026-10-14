# US-004: Create Listing with Photo Capture — Testing Guide

## 1. Purpose

Manual and automated verification of US-004 across `valuex-backend` (listing + media modules) and `valuex-mobile` (Flutter Sell flow). Updated for the gap-fix pass on branch `feature/us-004-gap-fixes`.

## 2. Prerequisites

- Java 21, Maven 3.9+, Docker Desktop (PostgreSQL, Redis, local object storage, Testcontainers).
- Flutter SDK and the Android emulator `ValueX_API_36` (see the project README for the emulator command).
- A seller account that is `ACTIVE` **and Aadhaar-verified** (sandbox Aadhaar is fine). Unverified accounts get `AADHAAR_VERIFICATION_REQUIRED`.
- Test images: a normal JPEG photo, a PNG, a HEIC from an iPhone (optional), an image smaller than 480×480, a file larger than 10 MB, and a non-image file renamed to `.jpg`.

## 3. Local Environment

### 3.1 Object storage

Local development uses a RustFS container as an S3-compatible stand-in for Cloudflare R2. Host port is **9300** (9000 is SonarQube, 9100 is used by Dart/Flutter tooling).

```powershell
cd C:\ValueX-Code\valuex-backend
docker compose up -d postgres redis object-storage object-storage-init
```

`object-storage-init` creates the buckets `valuex-dev-listing-media`, `-profile-media`, `-search-input`, `-support-media` and `-evidence`, then exits.

### 3.2 Backend

The `dev` profile already points at the local store:

| Setting | Dev default | Meaning |
|---|---|---|
| `OBJECT_STORAGE_ENDPOINT` | `http://localhost:9300` | Used by the backend to read/delete objects |
| `OBJECT_STORAGE_PUBLIC_ENDPOINT` | `http://10.0.2.2:9300` | Host written into signed upload/download URLs (the emulator's view of the PC) |
| `OBJECT_STORAGE_ACCESS_KEY_ID` / `OBJECT_STORAGE_SECRET_ACCESS_KEY` | `valuex-minio` / `valuex-minio-secret` | Local-only credentials |
| `OBJECT_STORAGE_PATH_STYLE` | `true` | Required for local S3-compatible stores |

For a physical phone, set `OBJECT_STORAGE_PUBLIC_ENDPOINT=http://<PC-LAN-IP>:9300`. For R2, set the real endpoint/credentials and leave `OBJECT_STORAGE_PUBLIC_ENDPOINT` empty. Never commit real credentials.

```powershell
cd C:\ValueX-Code\valuex-backend
mvn spring-boot:run
```

### 3.3 Mobile

```powershell
cd C:\ValueX-Code\valuex-mobile
flutter run -d emulator-5554 --dart-define-from-file=config/dev_android.json
```

## 4. Automated Tests

### 4.1 Backend

```powershell
cd C:\ValueX-Code\valuex-backend
mvn verify "-Dapi.version=1.44" "-Duser.timezone=Asia/Kolkata"
```

The two system properties are needed on this Windows machine only: Docker Engine 29 rejects the Testcontainers default API version, and PostgreSQL rejects the JVM's legacy `Asia/Calcutta` zone name.

| Suite | Tests | Covers |
|---|---|---|
| `MediaAssetServiceTest` | 39 | upload authorization, byte-level validation, REJECTED persistence, idempotent complete, storage failures, delete guards, access guard, CDN variants |
| `ListingDraftServiceTest` | 20 | draft + status history, attach rules (max 10, duplicates, sort order, ownership, state), delete + resequence, `requireOwnedDraft` |
| `CloudflareR2ObjectStorageAdapterTest` | 5 | presigned URL host/path style, SDK error translation, conditional wiring |
| `ListingPhotoFlowIntegrationTest` | 4 | real PostgreSQL: full flow, unique indexes, row lock, REJECTED persisted, missing object |
| `ListingControllerTest` / `MediaControllerTest` | 5 / 5 | controller wiring, Aadhaar gate annotation |

Expected: all tests pass, Checkstyle 0 violations, JaCoCo gate met (listing + media ≈ 97% lines). Then run SonarQube (`mvn sonar:sonar -DskipTests`) and confirm no open issues under `listing`/`media`.

### 4.2 Mobile

```powershell
cd C:\ValueX-Code\valuex-mobile
flutter analyze
flutter test test/features/listing
flutter test
```

`test/features/listing/create_listing_test.dart` covers photo rules, the repository's request bodies and storage PUT, the controller (draft creation, max 10, invalid/oversized photos, permission denial, retry, remove) and the screen (camera on entry, AI card, tips, Submit to AI, retry, remove, Back).

## 5. API Test Flow (Swagger or curl)

1. `POST /api/v1/listings` → `201`, `listingId`, `status=DRAFT`. A `listing_status_history` row `null → DRAFT` exists.
2. `POST /api/v1/media/uploads` with `purpose=LISTING_IMAGE`, `ownerType=LISTING`, `ownerId=<listingId>`, `fileName`, `contentType`, `sizeBytes` → `mediaId`, `uploadUrl`. The object key ends in an extension derived from `contentType`.
3. `PUT <uploadUrl>` with the exact `Content-Type` and `Content-Length` that were declared.
4. `POST /api/v1/media/{mediaId}/complete` → `READY`. Width/height in the response are the real image dimensions, not the values sent.
5. `POST /api/v1/listings/{listingId}/images` `{ "mediaId": "<mediaId>" }` → `imageId`, `sortOrder`.
6. `GET /api/v1/listings/{listingId}` → images in `sortOrder`.

## 6. Manual Test Cases

### 6.1 Mobile (emulator)

| ID | Scenario | Steps | Expected |
|---|---|---|---|
| M-01 | Sell opens the camera | Sign in (Aadhaar verified) → tap **Sell** | Camera opens immediately; after cancelling, the Add Photos screen shows the AI card, empty photo area and photo tips |
| M-02 | Screen matches design | Inspect the photo step | Back button, 5-step progress (first filled), "Add Photos", "Let AI do the work for you" card, "Photo tips for best results" with 4 ticked tiles, bottom button **Submit to AI** (no "Add at least 2 photos") |
| M-03 | Capture one photo | Take a photo | Tile shows a spinner, then the photo with **MAIN**; subtitle "1/10 photos added"; Submit to AI becomes enabled |
| M-04 | Gallery multi-select | Add → Choose from gallery → pick 3 | 3 tiles upload in parallel; header shows the total |
| M-05 | Max 10 | Add photos until 10, then pick more | Only 10 kept; "Maximum 10 photos allowed"; the Add tile disappears |
| M-06 | Low resolution | Pick an image under 480×480 | "Photo quality too low or invalid format"; nothing uploaded |
| M-07 | Over 10 MB | Pick a > 10 MB file that the picker does not shrink (e.g. a large PNG) | "Photo exceeds 10MB limit" |
| M-08 | Not an image | Pick a renamed non-image | "Photo quality too low or invalid format" |
| M-09 | Network failure | Stop the `object-storage` container, add a photo | Tile turns red with a retry icon; message reads "Failed to upload photo. Check your connection". Start the container, tap retry → photo becomes ready |
| M-10 | Remove | Tap the × on a ready photo | Photo disappears; server image deleted; remaining photos keep order; MAIN moves to the new first photo |
| M-11 | Submit to AI | With ≥1 ready photo, tap Submit to AI | "Photos saved. AI suggestions are coming soon." (AI analysis is US-005) |
| M-12 | Submit disabled | No photos, or a photo still uploading | Submit to AI is dimmed and does nothing |
| M-13 | Camera permission denied (iOS / devices that ask) | Deny camera access | "Camera access required to capture photos"; gallery still works |
| M-14 | Aadhaar not verified | Use an account that skipped Aadhaar → tap Sell | "Please complete Aadhaar verification to proceed"; Sell screen not opened |
| M-15 | Signed out | Browse as guest → tap Sell | Sent to Create Account |
| M-16 | Hindi | Switch app language to Hindi | All Sell strings are translated |

### 6.2 Backend

| ID | Scenario | Expected |
|---|---|---|
| B-01 | Create draft, active + verified seller | `201`, `DRAFT`, history row written |
| B-02 | Create draft, Aadhaar not verified | `403 AADHAAR_VERIFICATION_REQUIRED` |
| B-03 | Create draft, account not `ACTIVE` | `400 ACCOUNT_NOT_ACTIVE` |
| B-04 | JPEG / PNG / HEIC upload + complete | `READY`; JPEG/PNG dimensions read from bytes |
| B-05 | Declared `image/jpeg`, uploaded PNG bytes | `ERROR_INVALID_PHOTO`; media `REJECTED`; object deleted |
| B-06 | Image smaller than 480×480 (whatever width/height the client sends) | `ERROR_INVALID_PHOTO`; media stays `REJECTED` after the request |
| B-07 | Complete without uploading | `ERROR_PHOTO_UPLOAD_FAILED`; media stays `PENDING_UPLOAD`; upload then complete again succeeds |
| B-08 | Complete a `REJECTED` media | `ERROR_PHOTO_UPLOAD_FAILED` |
| B-09 | Complete a `READY` media again | `200`, unchanged |
| B-10 | 11th photo | Upload authorization: `ERROR_MAX_PHOTOS_EXCEEDED` (and attach also refuses) |
| B-11 | Attach the same media twice | `MEDIA_ALREADY_ATTACHED` |
| B-12 | Attach with a `sortOrder` already used | `LISTING_IMAGE_ORDER_CONFLICT` |
| B-13 | Delete image 1 of 3 | Remaining images re-sequenced to 0,1; deleted image's media `DELETED` |
| B-14 | `DELETE /media/{id}` for attached media | `MEDIA_IN_USE` |
| B-15 | `POST /media/{id}/access` for non-READY media | `MEDIA_NOT_READY` |
| B-16 | `GET /media/{id}` | `variants` contain CDN URLs only (never bucket keys); empty for private media |
| B-17 | Another seller's listing/media | `LISTING_NOT_FOUND` / `MEDIA_NOT_FOUND` |
| B-18 | Listing photo with `ownerType=USER` | `ERROR_INVALID_PHOTO` ("Listing photos must belong to a listing") |
| B-19 | Object store down during delete | Media `DELETION_PENDING`, request succeeds |

## 7. Acceptance Criteria Traceability

| Acceptance criterion | Evidence |
|---|---|
| Tapping Sell opens the camera | M-01; screen test "Sell opens the camera…" |
| At least 1 photo (max 10) is uploaded to the system | M-03–M-05, B-04, B-10; controller and integration tests |
| Seller can proceed to item details | M-11 (Submit to AI enabled after ≥1 ready photo; details/AI screen is US-005) |
| Edge cases: permission denied, camera failure, > 10 photos, poor quality, non-item photos, network failure | M-13, M-04 (gallery fallback), M-05, M-06–M-08, M-09; non-item detection is US-005/US-007 |
| Error codes `ERROR_CAMERA_PERMISSION_DENIED`, `ERROR_MAX_PHOTOS_EXCEEDED`, `ERROR_PHOTO_UPLOAD_FAILED`, `ERROR_INVALID_PHOTO` | M-13, M-05/B-10, M-09/B-07, M-06/B-05/B-06 |

## 8. Known Scope Boundaries

- **Submit to AI** confirms the photos are saved; AI analysis and the item-details step arrive with US-005.
- Resuming an unfinished draft in the app is not built; each Sell session creates a new draft (backend `GET /listings/{id}` is ready).
- HEIC dimensions cannot be decoded by the JDK; the server accepts client-reported dimensions for HEIC only (the app reads them from the file on the device).
- AVIF/WebP variants, EXIF stripping and server-side perceptual hashes are follow-ups; `variants` stays empty until the media worker exists.
- The photo-tip tiles use icons; swap in the designer's photos once they are delivered as assets.
