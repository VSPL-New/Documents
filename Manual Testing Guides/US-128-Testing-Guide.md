# US-128 — Listing Photo Variants: QA Testing Guide

**Sprint 3 · Discovery & Search**

Manual test cases for the four copies made of every listing photo (thumbnail, card, detail, zoom): when they appear,
what they look like, what the app receives before they exist, what happens when making them fails, and what happens
when a photo is deleted. No screen uses the new addresses yet (US-011, US-012, US-073, US-111 will), so this guide
checks the files, the database rows and the delivery port through SQL and the object store.

> **What ships:** migration `V26`; `MediaVariantJob` (every 10 s, batches of 10); the processors (`imageio` for JPEG
> and PNG, `vips` for everything including HEIC); `ListingPhotoLinkPort` (the addresses per photo); removal of copies
> with their photo; the separate public bucket `<prefix>-listing-variants`; a Debian-based Docker image with libvips.
> **Not in this story:** any app or API screen that shows the copies, the Admin screens, the purge of soft-deleted
> listings (US-127).

| Setting | Value |
|---|---|
| Migration | `V26__listing_photo_variants.sql` |
| Sizes (longest side) | thumbnail 300, card 600, detail 1200, zoom 1600; JPEG quality 82; never enlarged |
| Copy keys | `listing_image_variants/{mediaId}/{thumbnail\|card\|detail\|zoom}.jpg` in `<prefix>-listing-variants` |
| Processor | `MEDIA_VARIANT_PROCESSOR=imageio` (default) or `vips` |
| Retries | up to 5 tries, waiting 1, 2, 3, 4 minutes; then `variant_status = FAILED` |
| Known gaps | The Docker image build, the real R2 bucket and CDN, and HEIC on Linux were not run; Sonar not run |

---

## Prerequisites

1. `docker compose up -d postgres redis object-storage object-storage-init` (the init step creates the variants
   bucket), then start the backend. For HEIC cases install libvips (`brew install vips`) and start with
   `MEDIA_VARIANT_PROCESSOR=vips`.
2. A seller with a draft listing and the photo upload steps of `US-004-Testing-Guide.md`. Photo fixtures:
   a large JPEG (about 4000 x 3000), a small JPEG (about 500 x 400), a portrait phone photo with EXIF rotation and GPS
   (take one with a phone and location on), a PNG, a HEIC photo from an iPhone, and a text file renamed `broken.jpg`.
3. Handy queries:

```sql
SELECT id, status, variant_status, variant_attempts, variant_error, width, height
FROM media_assets WHERE owner_id = '<listing id>' ORDER BY created_at;
SELECT variant_type, width, height, size_bytes, object_key FROM media_variants WHERE media_asset_id = '<media id>' ORDER BY 1;
SELECT variant_status, count(*) FROM media_assets WHERE media_purpose = 'LISTING_IMAGE' GROUP BY 1;
```

Open the object store console (or `aws --endpoint-url http://localhost:9300 s3 ls s3://valuex-dev-listing-variants/ --recursive`).

---

## Test cases: making the copies (AC1, AC2)

| ID | Criterion / edge case | Steps | Expected |
|---|---|---|---|
| TC-001 | AC1 four copies | Upload the large JPEG to a draft, wait up to 30 s | `variant_status` becomes `READY`; four rows; sizes 300x225, 600x450, 1200x900, 1600x1200; four objects in the variants bucket |
| TC-002 | AC1 never enlarged | Upload the small JPEG (500x400) | The thumbnail is 300x240; card, detail and zoom are 500x400 (the original size), not larger |
| TC-003 | AC1 aspect ratio | Check each row of TC-001 | width / height is 4 : 3 within one pixel |
| TC-004 | AC2 rotation | Upload the portrait phone photo | Open the zoom copy: it is upright (not on its side); the dimensions are portrait |
| TC-005 | AC2 metadata | Download a copy, run `exiftool` on it (or open its properties) | No GPS, camera, date or software fields |
| TC-006 | PNG | Upload a PNG with transparency | Copies are JPEG; transparent areas are white |
| TC-007 | Cache headers | `curl -sI` a copy through the object store or CDN | `Content-Type: image/jpeg`, `Cache-Control: public, max-age=31536000, immutable` |
| TC-008 | Quality | Compare the zoom copy to the original | Looks the same on a phone screen; the file is much smaller |
| TC-009 | HEIC with libvips | With `MEDIA_VARIANT_PROCESSOR=vips`, upload an iPhone HEIC | Four JPEG copies, upright; `media_assets.width/height` hold the real size |
| TC-010 | HEIC without libvips | With the default processor, upload a HEIC | `variant_status` `FAILED` at once, `variant_error` `HEIC_NEEDS_VIPS`; the fallback (TC-014) is used |
| TC-011 | Only listing photos | Upload a profile photo | Its `variant_status` stays `PENDING` and no copies appear (the job only handles listing photos) |

## Test cases: delivery (AC3, AC4)

The delivery port has no HTTP endpoint yet. Check it in a unit or integration test run (`ListingPhotoLinkAdapterTest`,
`ListingPhotoVariantsIntegrationTest`), or from a Spring shell / debugger by calling
`ListingPhotoLinkPort.urls(listingId, mediaIds)`.

| ID | Criterion / edge case | Steps | Expected |
|---|---|---|---|
| TC-012 | AC3 CDN addresses | Call the port for a photo with four copies and `MEDIA_CDN_BASE_URL` set | `thumbnailUrl`, `cardUrl`, `detailUrl`, `zoomUrl` are `<cdn>/listing_image_variants/<mediaId>/<size>.jpg`; `expiresAt` is null |
| TC-013 | AC3 no original | Same call | No address contains the originals bucket, a signature or `listing_image/` |
| TC-014 | AC4 fallback | Stop the job (`MEDIA_VARIANT_ENABLED=false`), upload a photo, call the port | All four fields hold one signed link to the original; `expiresAt` about 15 minutes ahead; the link opens on a phone or emulator (the host is the device-reachable one) |
| TC-015 | AC4 lifetime | `UPDATE platform_settings SET setting_value = '30' WHERE setting_key = 'PHOTO_FALLBACK_LINK_MINUTES'`, wait 60 s, call again | `expiresAt` about 30 minutes ahead |
| TC-016 | AC4 CDN not configured | Start with `MEDIA_CDN_BASE_URL=` (empty) | The fallback link is returned even when four copies exist |
| TC-017 | Mixed page | A listing with one finished photo and one waiting photo | The first has CDN addresses, the second the signed link |
| TC-018 | Scope | Ask for a media id of another listing, a photo not `READY`, a profile photo | Nothing is returned for it |

## Test cases: failures, backlog, deletion (AC5)

| ID | Criterion / edge case | Steps | Expected |
|---|---|---|---|
| TC-019 | Broken file | Upload `broken.jpg` (the upload may be refused earlier by the content check; if it is accepted, or after replacing the stored object with junk) | `variant_status` `FAILED`, `variant_error` `UNSUPPORTED_FORMAT`; other photos are unaffected |
| TC-020 | Huge picture | Lower `valuex.media.variant.max-pixels` to 1000 and upload any photo | `FAILED` with `IMAGE_TOO_LARGE`; no decoding was attempted (the log shows no out-of-memory) |
| TC-021 | Storage outage | Upload a photo, then stop the object store before the next 10 s tick | `variant_attempts` rises, `variant_status` stays `PENDING` with `variant_error` `STORAGE_FAILED`; after the store is back the next try succeeds |
| TC-022 | Gives up | Keep the store down for 5 tries (set `max-attempts=2` to shorten) | `FAILED`; the log has one error line per photo and `media.variant.failed` is above 0 |
| TC-023 | Retry by hand | Run the reset query from the README for a `FAILED` photo after the cause is fixed | It is processed again and becomes `READY` |
| TC-024 | Backlog | Insert or upload 25 photos at once | About 10 are processed per 10 s tick; `media.variant.pending` falls to 0; none is processed twice (check `variant_attempts` is 1 for every photo) |
| TC-025 | Old photos | On a database that had photos before `V26`, start the backend | They show `PENDING` after migration and become `READY` in the background |
| TC-026 | Two instances | Start two backend instances and upload 20 photos | Every photo has exactly four rows; no duplicate-key errors; `variant_attempts` is 1 for all |
| TC-027 | AC5 delete | Remove a photo from a draft listing and delete its media | The four rows and four objects are gone, then the original |
| TC-028 | AC5 delete with outage | Stop the store, delete a photo with copies | The asset is `DELETION_PENDING`, the copy rows remain (nothing is orphaned) |
| TC-029 | Idempotent | Run the job twice on one photo (reset the status) | Still four rows; the objects are overwritten with the same keys |
| TC-030 | Working files | Check the temp folder (`MEDIA_VARIANT_TEMP_DIR` or `java.io.tmpdir`) after several runs, including failures | No `valuex-variants-*` folders are left |

---

## Automated tests

```bash
cd valuex-backend
mvn verify
mvn -Dtest='ExifOrientationTest,ImageIoVariantProcessorTest,VipsVariantProcessorTest,MediaVariantServiceTest,MediaVariantJobTest,ListingPhotoLinkAdapterTest,MediaAssetServiceTest,CloudflareR2ObjectStorageAdapterTest' test
```

`VipsVariantProcessorTest` runs the real libvips programs and is skipped when `vipsthumbnail` is not installed.
`ListingPhotoVariantsIntegrationTest` (PostgreSQL through Testcontainers, an in-memory object store) needs Docker and is
skipped without it; it covers the migration, the queue and its leases, the job end to end, retries and giving up,
the backlog, the delivery addresses and the deletion.
