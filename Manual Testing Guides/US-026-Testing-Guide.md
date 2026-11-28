# US-026 — Seller Prepares Package and Uploads Proof: QA Testing Guide

**Sprint 6 · Shipping & Delivery**

Manual checks of Pack & Upload Proof (mobile) and its four endpoints (backend), using test orders inserted with SQL,
or the Figma Make sample orders in the app.

> **What this story ships:**
> - `GET /api/v1/seller/orders/{id}/packing`
> - `POST …/packing/proofs`
> - `DELETE …/packing/proofs/{proofId}`
> - `POST …/packing/complete`
> - the `order_proofs` table (migration `V47`)
> - the screen opened from **Start Packing** and **Continue Packing** on Incoming Orders (US-112)
>
> **Checkout (US-021) is not built, so no real order exists yet.** Create a packing order with the SQL below, or run
> the app with the sample orders. Pickup scheduling (US-027) still answers "This is coming soon".
>
> See `Documents/LLD/Sprint-6-Shipping-Delivery-LLD.md` Part D (D.7 for what was built), and read the
> **Not Testable Yet** section below before filing anything as a bug.

| Setting | Value |
|---|---|
| Backend | Branch `feature/US-026-pack-and-upload-proof`; migration `V47__order_proofs.sql` |
| App | Branch `feature/US-026-pack-and-upload-proof`. Sample orders: add `--dart-define=SELLER_ORDERS=mock` (dev configs only); "Sony A7III Camera Body" is already in Packing |
| Settings (`platform_settings`) | `PROOF_ITEM_MIN` 2, `PROOF_ITEM_MAX` 4, `PROOF_PACKAGE_MIN` 1, `PROOF_PACKAGE_MAX` 2, `PROOF_MIN_PIXELS` 480 |
| Packed size limits | 0.05 to 30 kg; each side 1 to 150 cm |
| Automated tests (backend) | `mvn test "-Dtest=PackingServiceTest,PackingControllerTest,PackageSizeTest,OrderEvidenceAdapterTest,ShipmentPackageAdapterTest,ChatImageServiceTest,SellerPackingIntegrationTest"` (with Docker running; on this machine, set `JAVA_TOOL_OPTIONS="-Duser.timezone=Asia/Kolkata"` first) |
| Automated tests (app) | `flutter test test/features/order --dart-define=SKIP_PIXEL_CONTRAST=true` |

---

## Test Scenarios Overview

| TC | Scenario | Expected Result |
|---|---|---|
| TC-001 | Open from Start Packing and Continue Packing | Pack & Upload Proof for that order, as in Make |
| TC-002 | Screen content | Order card, steps, two sections at 0/4 and 0/2, escrow note, disabled button, red hint |
| TC-003 | Add photos (camera and gallery) | Spinner, then the photo; counter turns green at the minimum |
| TC-004 | Section limits | Add tile disappears at 4 item and 2 packaging photos; API answers `ERROR_PROOF_LIMIT` |
| TC-005 | Low-quality and unusable photos | "Image quality low. Upload clearer photo"; nothing added |
| TC-006 | Poor network | Failed photo stays with a retry; retry attaches it; remove drops it |
| TC-007 | Remove and leave, then Continue Packing | Drafts come back; removed ones are gone |
| TC-008 | Packed size and weight | Prefilled when already confirmed; limits checked |
| TC-009 | Submit | Order moves to Packing Required with Schedule Pickup; "Proof uploaded…" message |
| TC-010 | Skipping the photos | Button disabled; API answers `ERROR_IMAGE_REQUIRED` |
| TC-011 | Two devices and stale screens | One move; the other device is sent back to the list |
| TC-012 | Evidence rules | Server time, private storage, no location data, submitted photos cannot change |
| TC-013 | Ownership and account | Another seller's order is "not found"; suspended seller refused |
| TC-014 | Hindi, 200% text, screen reader | No overflow; headings, labels, 48 dp targets |
| TC-015 | Automated tests | All pass |

---

## Setup — A Packing Order

Sign in to the app as the **seller** and note your user id (`SELECT id FROM users WHERE mobile = '+91…';`). You also
need a **buyer** user id (any other active user) and one of the seller's listing ids.

```sql
WITH o AS (
  INSERT INTO orders (order_number, checkout_id, buyer_id, seller_id, delivery_mode, payment_option, status,
                      item_amount, shipping_amount, total_amount, delivery_address, seller_display_name,
                      created_at, updated_at)
  VALUES ('VX-QA-' || nextval('order_number_seq'), gen_random_uuid(), '<buyer>', '<seller>', 'DELIVERY', 'PAY_NOW',
          'SELLER_PACKING_PENDING', 55000, 0, 55000,
          '{"line1": "12 MG Road", "city": "Bengaluru", "state": "Karnataka", "pincode": "560001"}',
          'QA Seller', now() - interval '2 hours', now())
  RETURNING id
), i AS (
  INSERT INTO order_items (order_id, listing_id, seller_id, price, title)
  SELECT id, '<listing>', '<seller>', 55000, 'iPhone 15 Pro Max' FROM o
)
INSERT INTO shipments (order_id, status) SELECT id, 'SHIPPING_REQUIRED' FROM o RETURNING order_id;
```

For TC-001, also create a New order: use `'SHIPPING_MODE_SELECTED'` as the status.

**Checking the result:**

```sql
SELECT kind, width, height, uploaded_at, submitted_at FROM order_proofs WHERE order_id = '<order>' ORDER BY uploaded_at;
SELECT weight_grams, length_cm, breadth_cm, height_cm FROM shipments WHERE order_id = '<order>';
SELECT action, actor_type FROM order_status_history WHERE order_id = '<order>' ORDER BY changed_at;
```

`order_status_history` is insert-only and submitted proofs cannot be deleted, so use a throw-away database for heavy
testing.

---

## TC-001 — Open the Screen

1. Profile > Selling > **Incoming Orders**.
2. On a New delivery order, tap **Start Packing**.

**Expect:** The order moves to Packing and Pack & Upload Proof opens for it.

3. Go back, then tap **Continue Packing** on the same order.

**Expect:** The same screen opens.

## TC-002 — Screen Content (Make)

**Expect:**
- **Header:** the back button, "Pack & Upload Proof" and "Required before pickup is scheduled".
- **Order card:** the item title and "Order #VX-QA-…".
- **"STEPS TO FOLLOW:"** with the four numbered steps.
- **Item Photos:**
  - "Min 2, max 4 photos required"
  - a red `0/4` chip
  - a blue Add tile with a camera
- **Packaging Photos:**
  - "Show packed item clearly"
  - a red `0/2` chip
  - a fuchsia Add tile with an upload arrow
- **Packed size and weight:** four fields. This card is not in Make; see plan gap G11.
- **Escrow note:** "Payment of ₹55,000 is held in escrow…", with the amount in bold green.
- **Bottom:**
  - "Submit Proof & Schedule Pickup" is dimmed
  - "Add at least 2 item photos + 1 packaging photo" in red below it

## TC-003 — Add Photos

1. Tap the item Add tile, then **Take a photo**, and take a clear photo.

**Expect:**
- A thumbnail with a spinner, then the photo.
- The chip shows `1/4`.

2. Add a second item photo with **Choose from gallery**.

**Expect:** The chip shows `2/4` and turns green.

3. Add one packaging photo.

**Expect:** The packaging chip shows `1/2` in green, and the red hint disappears.

## TC-004 — Section Limits

1. Add item photos until there are 4.

**Expect:** The item Add tile disappears.

2. Add packaging photos until there are 2.

**Expect:** The packaging Add tile disappears.

3. **API:** attach a fifth item photo directly (`POST …/packing/proofs` with a new packing upload).

**Expect:** `422 ERROR_PROOF_LIMIT`, "You can add up to 4 item photos".

4. Set `PROOF_ITEM_MAX` to 6 and reopen the screen once the settings cache has expired.

**Expect:**
- "Min 2, max 6 photos required".
- Two more photos can be added.

## TC-005 — Low-Quality and Unusable Photos

1. Choose a photo smaller than 480 px on one side (for example, a 300 × 800 screenshot).

**Expect:**
- "Image quality low. Upload clearer photo".
- Nothing is added and the counter is unchanged.

2. **API:** attach a packing upload smaller than 480 px.

**Expect:** `422 WARNING_IMAGE_QUALITY_LOW`.

3. With `PROOF_MIN_PIXELS` set to 240, try the same photo again.

**Expect:** It is accepted.

4. **API:** attach a chat picture's media id, or another user's packing upload.

**Expect:** `400 ERROR_VALIDATION`.

## TC-006 — Poor Network

1. Turn on airplane mode, then add a photo.

**Expect:**
- "Failed to upload images. Try again".
- The photo stays, tinted red with a retry arrow.
- The button stays disabled.

2. Turn airplane mode off and tap the failed photo (not its corner).

**Expect:** It uploads and becomes a normal photo.

3. Repeat step 1, then tap the **×** on the failed photo.

**Expect:** It is removed.

## TC-007 — Remove, Leave and Continue Packing

1. Add 3 item photos, then remove one with **×**.

**Expect:** The chip shows `2/4`, and the row is gone from `order_proofs`.

2. Go back to Incoming Orders, then tap **Continue Packing**.

**Expect:** The two remaining photos are shown again; they are drafts, with `submitted_at` empty.

3. **API:** `DELETE …/packing/proofs/<id>` twice.

**Expect:** `204` both times.

## TC-008 — Packed Size and Weight

1. Leave a field empty, or enter 0.04 or 31 kg, or a side of 0.5 or 151 cm, then submit.

**Expect:**
- The field shows "Enter a packed weight between 0.05 and 30 kg" or "Enter each side between 1 and 150 cm".
- The order does not move.

2. **API:** `POST …/packing/complete` with `{"package":{"weightKg":"31",…}}`.

**Expect:** `400 VALIDATION_ERROR`, with `details["packageSize.weightKg"]`.

3. After TC-009, call `GET …/packing`.

**Expect:** `packageSize` holds the values entered. The listing's own values are prefilled only after US-122.

## TC-009 — Submit

1. With 2 item photos, 1 packaging photo and a valid size (for example 1.2 kg, 30 × 20 × 15 cm), tap **Submit Proof & Schedule Pickup**.

**Expect:**
- **App:**
  - back on Incoming Orders with "Proof uploaded. Schedule the pickup next"
  - the card shows "Packing Required" with **Schedule Pickup** ("coming soon" until US-027)
- **Database:**
  - every photo has `submitted_at` set
  - the shipment has `weight_grams` 1200 and the three sides
  - `order_status_history` has `UPLOAD_PROOF` with actor `SELLER`

2. **API:** call `POST …/packing/complete` again.

**Expect:** `200` with the same card, and no second history row.

## TC-010 — Skipping the Photos

1. In the app, with 1 item photo and 0 packaging photos:

**Expect:** The button is dimmed, and the red hint is shown.

2. **API:** call `POST …/packing/complete` with too few photos.

**Expect:** `422 ERROR_IMAGE_REQUIRED`, "Please upload package images before scheduling pickup", with `details.itemMissing` and `details.packageMissing`.

3. **API:** call `POST …/packing/proofs` on an order in `SHIPPING_MODE_SELECTED`.

**Expect:** `409 ERROR_ORDER_ACTION_NOT_ALLOWED`.

## TC-011 — Two Devices and Stale Screens

1. Open the same order's packing screen on two devices, and submit on one.
2. On the other device, add a photo.

**Expect:** "This order has already moved to the next step. Refreshing", and the screen goes back to the list.

3. **API:** send two `complete` calls at the same time.

**Expect:** Both answer `200`, and there is one `UPLOAD_PROOF` row.

## TC-012 — Evidence Rules

1. Upload a phone photo that has a GPS location.

**Expect:**
- The stored object under `seller_pre_shipment_evidence/<seller>/…` is a JPEG of at most 1600 px with no EXIF/GPS data. Download it with a signed link and check with an EXIF viewer.
- `uploaded_at` is the server time.

2. Open a photo's `url` from `GET …/packing`.

**Expect:** It works for 10 minutes, then expires. The bucket is private.

3. In SQL, after TC-009:
   - `UPDATE order_proofs SET kind = 'PACKAGE_SEALED' WHERE order_id = '<order>';`
   - `DELETE FROM order_proofs WHERE order_id = '<order>';`

**Expect:** Both fail with "order proof … is submitted and cannot change".

## TC-013 — Ownership and Account

1. As another seller, call `GET /api/v1/seller/orders/<order>/packing`.

**Expect:** `404 ERROR_ORDER_NOT_FOUND`.

2. Suspend the seller, then call any packing endpoint.

**Expect:** `403 ERROR_ACCOUNT_NOT_ACTIVE`.

## TC-014 — Hindi, 200% Text, Screen Reader

1. Switch the app to Hindi and set the text size to 200%.

**Expect:**
- No overflow.
- The header scrolls away, and the button stays at the bottom.

2. With TalkBack or VoiceOver on:

**Expect:**
- The title and section titles are headings.
- The chips read "0 of 4 photos added".
- Photos read "Item photo 1 of 2".
- The Add tiles read "Add item photo" and "Add packaging photo".
- **×** reads "Remove photo".
- Every target is at least 48 dp.

## TC-015 — Automated Tests

Run the commands in the table at the top.

**Expect:** All pass. On this machine, `google_accessibility_test.dart` (2 tests) also fails on a clean main.

---

## Not Testable Yet

| Item | Comes with |
|---|---|
| Real orders created by payment, and the new-order push | US-021 |
| Buyer sees the submitted packing photos in order details (`sellerProofs`) | US-023 |
| Schedule Pickup after packing | US-027 |
| Packed size prefilled from the listing; courier booking with the confirmed size | US-122 |
| Retention date (order completion + 2 years) on the photos | US-031 / US-024 |
| Automatic check for fake photos or a wrong item | Later AI story (LLD G16) |
