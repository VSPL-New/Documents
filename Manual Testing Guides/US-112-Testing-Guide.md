# US-112 — Seller Incoming Orders: QA Testing Guide

**Sprint 6 · Shipping & Delivery**

Manual checks of the seller's Incoming Orders page (mobile) and its four endpoints (backend), using test orders inserted
with SQL, or the Figma Make sample orders in the app.

> **What this story ships:** `GET /api/v1/seller/orders`, `GET /api/v1/seller/orders/summary`,
> `POST /api/v1/seller/orders/{id}/start-packing`, `POST /api/v1/seller/orders/{id}/mark-handed-over`, the Profile
> "Incoming Orders" badge, the `NEW_ORDER` push setting, and the Incoming Orders page reached from Profile > Selling.
> **Checkout (US-021) is not built, so no real order exists yet:** create test orders with the SQL below, or run the app
> with the sample orders. Buttons that open screens of later stories answer "This is coming soon". See
> `Documents/LLD/Sprint-6-Shipping-Delivery-LLD.md` Part A (A.12 for what was built), and the **Not Testable Yet**
> section below before filing anything as a bug.

| Setting | Value |
|---|---|
| Backend | Branch `feature/US-112-seller-incoming-orders`; no migration (uses V45 orders and V46 shipments) |
| App | Branch `feature/US-112-seller-incoming-orders`; sample orders: add `--dart-define=SELLER_ORDERS=mock` (dev configs only) |
| Settings | `PICKUP_SLA_HOURS` (default 48) and `PICKUP_MAX_RESCHEDULES` (default 2) in `platform_settings`; `valuex.seller-orders.urgent-window` (PT24H) |
| Automated tests (backend) | `mvn test "-Dtest=FulfilmentBucket*Test,SellerOrder*Test,IncomingOrdersBadgeProviderTest,OrderPartyDirectoryAdapterTest,OrderItemPhotoAdapterTest,SellerIncomingOrdersIntegrationTest"` (Docker running; on this machine set `JAVA_TOOL_OPTIONS="-Duser.timezone=Asia/Kolkata"` first) |
| Automated tests (app) | `flutter test test/features/order --dart-define=SKIP_PIXEL_CONTRAST=true` |

---

## Test Scenarios Overview

| TC | Scenario | Expected Result |
|---|---|---|
| TC-001 | Open Incoming Orders from Profile | Page with back button, title, count line, New badge, four tiles |
| TC-002 | Groups, order and card content | New, Packing, Scheduled, Shipped; newest first in each; card fields as listed |
| TC-003 | URGENT | Only on New delivery orders within 24 hours of the pickup deadline |
| TC-004 | Start Packing | Order moves to Packing; repeat is harmless; a stale card is refused and refreshed |
| TC-005 | Self-pickup order | Tag, View Pickup Details, Mark as handed over, Reject; never URGENT |
| TC-006 | Packing, Scheduled and Shipped variants | Schedule Pickup, Arranging pickup, booking error, Pickup failed, Reschedule limit, Returning, Handed over |
| TC-007 | Orders that are not listed | Before payment, completed, cancelled, return requested, disputed, returned to seller |
| TC-008 | Privacy and ownership | Only own orders; another seller's order is "not found"; buyer by name only |
| TC-009 | Empty, error, offline and paging | Empty text; error with Retry; last list kept; more on scroll; footer |
| TC-010 | Profile badge and push | Badge = New orders; push deep link opens the page |
| TC-011 | Suspended account | 403 from the API; the app shows the blocked screen |
| TC-012 | Hindi, 200% text, screen reader | No overflow; headings, labels and 48 dp targets |
| TC-013 | Automated tests | All pass |

---

## Setup — Test Orders

Sign in to the app as the **seller** and note your user id (`SELECT id FROM users WHERE mobile = '+91…';`). You also
need a **buyer** user id (any other active user) and one of the seller's listing ids
(`SELECT id FROM listings WHERE seller_id = '<seller>' LIMIT 1;`).

Run this block once per order, changing the values marked `<…>`:

```sql
WITH o AS (
  INSERT INTO orders (order_number, checkout_id, buyer_id, seller_id, delivery_mode, payment_option, status,
                      item_amount, shipping_amount, total_amount, pickup_address, seller_display_name, created_at,
                      updated_at)
  VALUES ('VX-QA-' || nextval('order_number_seq'), gen_random_uuid(), '<buyer>', '<seller>',
          '<DELIVERY or SELF_PICKUP>', 'PAY_NOW', '<order state, e.g. SHIPPING_MODE_SELECTED>',
          42000, 0, 42000,
          '{"line1": "4 Park Street", "city": "Kolkata", "state": "West Bengal", "pincode": "700016"}',
          'QA Seller', now() - interval '<hours> hours', now())
  RETURNING id, delivery_mode
), i AS (
  INSERT INTO order_items (order_id, listing_id, seller_id, price, title)
  SELECT id, '<listing>', '<seller>', 42000, 'Vintage Leica M6 Film Camera' FROM o
)
INSERT INTO shipments (order_id, status)
SELECT id, CASE WHEN delivery_mode = 'SELF_PICKUP' THEN 'SHIPPING_NOT_REQUIRED' ELSE '<shipment state, e.g. SHIPPING_REQUIRED>' END
FROM o;
```

For a variant that needs shipment details, update the shipment afterwards, for example
`UPDATE shipments SET booking_error = 'ERROR_SHIPMENT_CREATION_FAILED' WHERE order_id = '<order>';`.
Remove test orders when done (`order_status_history` and `shipment_status_history` rows are insert-only, so use a
throw-away database for heavy testing).

---

## TC-001 — Open the Page

1. Profile > Selling > **Incoming Orders**.

**Expect:**
- The page opens with the back button, "Incoming Orders" and "{n} orders · {x} new".
- A "{x} New" badge beside the title when x > 0, and none when x = 0.
- Four tiles, New, Packing, Scheduled and Shipped, each with an icon and its count.

Back returns to Profile.

## TC-002 — Groups, Order and Card Content

Create one order in each of `SHIPPING_MODE_SELECTED`, `SELLER_PACKING_PENDING`, `PICKUP_SCHEDULED`, `IN_TRANSIT`
(delivery), with different `<hours>`. Add a second New order.

**Expect:**
- **Order:** New first, then Packing, Scheduled and Shipped; within New, the newest first.
- **Tiles:** the counts match the cards.
- **Each card:**
  - `#<order number>`
  - a status chip with icon and text: New Order, Packing Required, Pickup Scheduled or Shipped
  - a photo, or a grey placeholder when the listing has none
  - the title, on two lines at most
  - the price as "₹42,000"
  - the initials and "Buyer: <name>"
  - "<n> hours ago"
  - the details button (it answers "This is coming soon")
- **Buttons:**
  - New: **Start Packing** and **Reject**
  - Packing: **Continue Packing**
  - Scheduled: **View Schedule** and **Reschedule Pickup**
  - Shipped: "Order Shipped" with no button

Sample orders: run the app with `SELLER_ORDERS=mock`. **Expect** the four Make orders, ORD-S-1001 (URGENT) to
ORD-S-0998, with placeholders for photos.

## TC-003 — URGENT

Create New delivery orders placed 23, 24 and 30 hours ago, and a self-pickup order placed 30 hours ago.

**Expect:**
- URGENT on the 24- and 30-hour delivery orders, not on the 23-hour one.
- Never on the self-pickup order.
- With `PICKUP_SLA_HOURS` set to 12 (and the settings cache expired), every New delivery order is URGENT.

## TC-004 — Start Packing

1. Tap **Start Packing** on a New delivery order.

**Expect:**
- "This is coming soon" (packing is US-026).
- The card moves to Packing with **Continue Packing**, and the New tile and the badge go down by one.
- `order_status_history` gets one row, `CONFIRM_SHIPPING`, actor `SELLER`.

2. **Repeat:** call `POST /api/v1/seller/orders/<id>/start-packing` again (Swagger or curl with the seller's token).
   **Expect** 200 with the same card and no new history row.
3. **Stale card:** with the page open, change the order to `PICKUP_SCHEDULED` in SQL, then tap **Start Packing** on the
   old card. **Expect** "This order has already moved to the next step. Refreshing" and the card refreshes into
   Scheduled. The API answers 409 `ERROR_ORDER_ACTION_NOT_ALLOWED`.
4. **Self-pickup:** the API refuses Start Packing on a self-pickup order (409).

## TC-005 — Self-Pickup Order

Create a `SELF_PICKUP` order in `SHIPPING_MODE_SELECTED`.

**Expect:**
- The card is in New with "New Order" and the tag "Self Pickup by Buyer".
- Buttons: **View Pickup Details**, **Mark as handed over**, **Reject**. No URGENT.

1. **View Pickup Details** shows "Pickup details" with the address lines (4 Park Street / Kolkata, West Bengal 700016).
2. **Mark as handed over** asks "Has the buyer collected the item?":
   - **Cancel** changes nothing.
   - **Yes, handed over** moves the card to Shipped with the chip "Handed over" and no button.
   - The history gets `HANDED_OVER` (SELLER), then `REQUEST_BUYER_PROOF` (SYSTEM).
   - The order is `BUYER_PROOF_PENDING`.
3. Repeating the API call returns 200 and adds nothing. On a delivery order the API answers 409.

## TC-006 — Variants

Use delivery orders, setting the order and shipment states listed:

| Order state | Shipment (SQL) | Expect |
|---|---|---|
| `SELLER_PROOF_UPLOADED` | `SHIPPING_REQUIRED` | Packing, "Packing Required", **Schedule Pickup** |
| `SELLER_PROOF_UPLOADED` | `PICKUP_SLOT_SELECTED` | Packing, chip "Arranging pickup", details button only |
| `SELLER_PROOF_UPLOADED` | `SHIPPING_REQUIRED`, `booking_error = 'ERROR_SHIPMENT_CREATION_FAILED'` | **Schedule Pickup** and the red line "We could not arrange the shipment. Please try again" |
| same, `booking_error = 'ERROR_NO_LOGISTICS_AVAILABLE'` | | "No pickup service in your area. Contact support" |
| `PICKUP_SCHEDULED` | `PICKUP_FAILED` | Scheduled, tag "Pickup failed", **View Schedule** and **Reschedule Pickup** |
| `PICKUP_SCHEDULED` | `PICKUP_SCHEDULED`, `pickup_reschedules = 2` | **View Schedule** only |
| `DELIVERY_FAILED` or `SHIPMENT_LOST` | any | Shipped, "Order Shipped" |
| `RETURN_TO_SELLER` | `rto_delivered_at` empty | Shipped, chip "Returning to you" |

## TC-007 — Not Listed

Orders in `PAYMENT_PENDING`, `COMPLETED`, `CANCELLED`, `RETURN_REQUESTED`, `DISPUTE_RAISED`, and `RETURN_TO_SELLER` with
`rto_delivered_at` set. **Expect** none on the page and none in the counts.

## TC-008 — Privacy and Ownership

1. Sign in as another seller. **Expect** none of the first seller's orders.
2. As the second seller, call `start-packing` on the first seller's order id. **Expect** 404 `ERROR_ORDER_NOT_FOUND`,
   the same as for a random id; the order is unchanged.
3. Inspect a list response. **Expect** only `buyer.displayName`: no mobile, email or address. The pickup address
   appears only on self-pickup orders.

## TC-009 — Empty, Error, Offline and Paging

| Step | Expect |
|---|---|
| Seller with no orders | "No incoming orders yet. Orders for your listings will appear here", "0 orders · 0 new", tiles 0, no badge |
| Stop the backend, open the page | "Unable to load your incoming orders. Pull down or tap Retry" with **Retry**; start the backend, tap Retry: the list loads |
| Page loaded, then backend stopped, pull down | The cards stay; a banner with the same message and **Retry** |
| 25 orders | 20 first; scrolling loads the rest; "Showing all 25 incoming orders" at the end |
| `GET /seller/orders?size=500` | `metadata.size` is 50 |
| `GET /seller/orders?bucket=DONE` | 400 `ERROR_VALIDATION` |
| `GET /seller/orders?bucket=packing` | Only Packing orders |

## TC-010 — Profile Badge and Push

1. With 2 New orders (one delivery, one self-pickup), open Profile. **Expect** the Incoming Orders badge 2. Start
   packing one, go back. **Expect** 1.
2. The `NEW_ORDER` notification is created by checkout (US-021, not built). To check the link, insert a notification for
   the seller with deep link `/seller/orders` (as in the US-077 guide) and tap it in Notifications. **Expect** Incoming
   Orders opens.
3. Android: Settings > Apps > JustQlic > Notifications lists an **Orders** channel.

## TC-011 — Suspended Account

Set the seller to `SUSPENDED`. **Expect** the API answers 403 `ERROR_ACCOUNT_NOT_ACTIVE` and the app shows the blocked
screen (US-088).

## TC-012 — Hindi, Large Text and Screen Reader

- Switch to Hindi. **Expect** "आने वाले ऑर्डर", the tiles, chips, tags and buttons in Hindi.
- With text size at 200%, **expect** no overflow and titles wrapping to two lines.
- With TalkBack:
  - the title is read as a heading
  - each tile is read as one phrase ("1, New")
  - the details button is read as "Order details"
  - the photo is read as "Item photo"
  - every button is at least 48 dp

## TC-013 — Automated Tests

Run the two commands in the table at the top. **Expect** all to pass, and check that `SellerIncomingOrdersIntegrationTest`
ran rather than being skipped (it is skipped when Docker is not running).

---

## Not Testable Yet

| Item | Comes with |
|---|---|
| Real orders created by payment, and the `NEW_ORDER` push sent | US-021 |
| Order details from the card's details button; live refresh (`order.updated`) | US-023 |
| Pack & Upload Proof (after Start Packing, Continue Packing) | US-026 |
| Schedule Pickup, View Schedule, Reschedule Pickup | US-027 |
| Reject with the cancellation penalty | US-059 (Sprint 7) |
| Buyer confirmation and auto-confirmation after a self-pickup hand-over | US-031 (Part J) |
| Refresh when a push arrives while the app is open | Foreground push handling (not planned yet) |
| Rate limit of 60 requests per minute | Not built (LLD A.9, proposed) |
