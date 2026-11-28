# US-112: Seller Incoming Orders — Implementation Plan

## 1. Header

| Field | Value |
|---|---|
| Story ID | US-112 |
| Title | Seller Incoming Orders |
| Sprint | Sprint 6 — Shipping & Delivery |
| Story Points | 5 |
| Repos | valuex-backend, valuex-mobile |
| Dependency | US-023, US-103 (`Sprint-plan.md`). US-103 is built (the Profile row and the `INCOMING_ORDERS` key exist). **US-023 is not built**, nor is US-021, which creates orders. Like US-090 and US-092, the backend is built and tested by inserting orders directly. The screens that the card buttons open (US-023, US-026, US-027, US-059) do not exist yet (G2). The backend also needs US-092 (the `shipments` table and `FulfilmentSetting`), which is merged to `main` (PR #95, 2026-11-27) (G3) |
| Branches | `feature/US-112-seller-incoming-orders` in `valuex-backend` (worktree `wt/US-112-backend`) and in `valuex-mobile` (worktree `wt/US-112-mobile`), each from an up-to-date `origin/main` |

**Scope (user decision 2026-11-27): all of LLD Part A.** This covers:
- the four endpoints
- the `INCOMING_ORDERS` badge provider
- the `NEW_ORDER` push row
- the mobile page with its real repository, plus a mock repository of the Make sample orders

## 2. Story Recap

**As a** seller **I want** one list of every order buyers have placed on my items, grouped by what I need to do next **so that** I can pack, schedule pickup and follow each order without searching through chats and notifications.

**Acceptance Criteria** (`user-stories.md`, summarised):
- **The page.** An `ACTIVE` seller opens Profile > Selling > "Incoming Orders". The page has a back button, the title "Incoming Orders" and the line "{n} orders · {x} new". When x > 0, a "{x} New" badge sits beside the title.
- **Tiles and cards.** Four count tiles: New, Packing, Scheduled and Shipped. Below them, cards ordered New → Packing → Scheduled → Shipped, newest first within each group.
- **A card shows:**
  - the order reference, the URGENT tag and a status chip (icon and text)
  - the item photo, title and price in INR
  - "Buyer: {name}" with initials, and the time since the order
  - an action area and an order-details button
- **New (delivery).** "Start Packing" moves the order to Packing and opens Pack & Upload Proof (US-026). "Reject" opens the US-059 confirmation, which always shows the penalty, except for Pay at Pickup orders.
- **Packing Required.** "Continue Packing" reopens Pack & Upload Proof with the photos kept. After the proof is uploaded, the order stays in Packing with "Schedule Pickup" (US-027).
- **Pickup Scheduled.** "View Schedule" shows the date, slot and address (US-027).
- **Shipped.** Covers picked up through to waiting for buyer confirmation. The card shows "Order Shipped" and has no action.
- **Self-pickup.** In New with the "New Order" chip and the tag "Self Pickup by Buyer". There is no packing or pickup scheduling. The card offers "View Pickup Details" and "Reject", and is never URGENT. The order completes and leaves the list when the buyer confirms (US-031).
- **Details.** The details button opens the order details (US-023).
- **Push.** A new paid order sends a push (US-077) and raises the Profile badge. The push opens this page.
- **Refresh.** Pull to refresh reloads the list and counts. Coming back from packing or scheduling shows the new status without a manual refresh.
- **Paging.** 20 orders per page, more loaded on scroll, and "Showing all {n} incoming orders" at the end.
- **Empty and done.**
  - Empty state: "No incoming orders yet. Orders for your listings will appear here", with counts of 0.
  - Completed, cancelled, returned and disputed orders leave the list (US-070).
- **Offline.** Show the last loaded list with a message and Retry, or an error state with Retry.

**Validation Rules:**
- The list shows only the seller's own orders. The buyer appears by display name and initials only.
- Prices are in INR with Indian grouping (₹1,85,000).
- The order reference is the backend `order_number` (mock data: ORD-S-1001…).
- The server decides URGENT, which buttons are shown, and which actions are allowed.
- Counts and list agree.
- Tap targets are 48 dp with labels. The title is a heading. Important text is at least 14 px at 4.5:1 contrast. Status is never shown by colour alone.
- The screen is added to the accessibility and heading tests.

**Error Scenarios:** `ERROR_INCOMING_ORDERS_LOAD_FAILED`, `ERROR_ORDER_ACTION_NOT_ALLOWED` ("This order has already moved to the next step. Refreshing"), `ERROR_ORDER_NOT_FOUND` ("This order is no longer available"), `ERROR_SECTION_UNAVAILABLE` (US-103).

**Edge Cases:**
- A stale card's action is refused, then the card refreshes.
- Start Packing tapped twice or on two devices does no harm.
- Packing left unfinished, or proof uploaded without a pickup scheduled.
- Several orders for the same item or buyer.
- Long, single-word or non-Latin buyer names.
- The photo is missing or the listing was removed.
- A delivery exception appears in Shipped.
- Hundreds of orders, or counts above 99.
- Hindi at 200% text.
- A suspended or banned account.
- Pay at Pickup self-pickup orders.

## 3. Design Reference

**Primary source:** [Sprint-6-Shipping-Delivery-LLD.md — Part A](../LLD/Sprint-6-Shipping-Delivery-LLD.md#part-a---us-112-seller-incoming-orders), **revision 0.4** (Part A unchanged in 0.5), on `main` since Documents PR #307 merged on 2026-11-27 (G1).

**Also read:**
- LLD sections:
  - 0.1: module ownership
  - 0.2: order vs shipment state
  - 0.3: `PICKUP_SLA_HOURS`
  - 0.4: error codes
  - 0.5: the `NEW_ORDER` push row on the `orders` channel
  - 0.6 S1: one shipment per order
  - 0.6 S10: self-pickup hand-over
- HLD 02 "Seller Fulfilment APIs (US-112)" and HLD 07 "Seller Incoming Orders (US-112)"
- LLD Sprint 1 §8.3: the `INCOMING_ORDERS` badge key
- Figma Make file `tzrpUwfrR0SYeyKkv1p0co`, `src/app/components/SellerIncomingOrdersScreen.tsx` (the version the prototype opens; the root `SellerIncomingOrdersScreen.tsx` is an older draft that nothing opens). Make draws only the four basic states. Self-pickup, "Schedule Pickup", "Arranging pickup", the exception tags, Reschedule, and the empty, loading and error states have no Make design and use existing design-system parts.

**What already exists on `main`:**
- **Backend `order` module (US-090):**
  - `Order`, `OrderItem`, `OrderState` (24 states), `OrderStateMachine` (`CONFIRM_SHIPPING` and `REQUEST_BUYER_PROOF` exist; `HANDED_OVER` does not)
  - `OrderTransitionService.move(orderId, trigger, OrderActor, note)`, which locks the row, writes history and publishes `OrderStatusChangedEvent`
  - `OrderRepository`, and `OrderErrors.ORDER_NOT_FOUND` (only)
- **`V45__orders.sql`:** has `seller_id`, `order_number`, `delivery_mode`, `payment_option`, `pickup_address` (JSONB), `deleted_at`, the index `idx_order_seller_status (seller_id, status, created_at DESC)`, and `order_items` (one per order, with `title`, `price`, `image_url`, `listing_id`). **No migration is needed** (A.3).
- **US-092 (PR #95, merged to `main` 2026-11-27):**
  - `shipments` (`status`, `booking_error`, `pickup_reschedules`, `rto_delivered_at`, one row per order)
  - `FulfilmentSetting` (`PICKUP_MAX_RESCHEDULES`, `DELIVERY_MAX_ATTEMPTS`)
  - `ShipmentState`
- **Profile hub (US-103):** `auth.application.port.ProfileMenuBadgeProvider` (`menuKey()`, `badgeCount(userId)`). `ProfileMenuService` isolates failures.
- **Push:** `notification.application.service.PushPolicy` is one map of event → `Rule(channel, highPriority, skipWhenOnline)`. Its channels are `chat`, `offers` and `calls`; there is **no `orders` channel** yet.
- **Ports to copy:**
  - `communication.application.port.ParticipantDirectoryPort` (`displayNames`, `activeAmong`) ← `auth.infrastructure.communication.ParticipantDirectoryAdapter`
  - `media.port.ListingPhotoLinkPort` (signed `thumbnailUrl` per listing photo)
  - Account gating is done per service with `ForbiddenException(ErrorCodes.ACCOUNT_NOT_ACTIVE)`. There is no global filter.
- **Mobile:**
  - `lib/features/profile/presentation/profile_screen.dart`: the "Incoming Orders" row calls `item(Icons.assignment_outlined, l10n.profileIncomingOrders, ProfileMenuKeys.incomingOrders)` with no `onTap`, so it shows "coming soon".
  - `ProfileMenuKeys.incomingOrders = 'INCOMING_ORDERS'`
  - `BrandGradientButton` and `SingleToneButton` exist
  - `test/all_screens_accessibility_test.dart` and `test/screen_headings_test.dart` exist
  - The mock-mode pattern is in `AppConfig` (`useMockPayment`, `useMockAddressSearch`)
  - Android channels are created in `MainActivity.kt` (`chat`, `offers`, `calls`)
  - **No `lib/features/order/`** and no `order.updated` realtime event (both come with US-023)

**Key design decisions (LLD Part A):**
- **Buckets are derived, not stored.** `FulfilmentBucketResolver` maps (order state, delivery mode, shipment state) to a bucket, tags and actions, per the table in A.3.1. The shipment state only changes chips and actions. The single exception is `RETURN_TO_SELLER` with `rto_delivered_at` set, which leaves the list (G7).
- **The server owns the actions.** The app renders `actions` and `tags` and holds no state machine.
- **Start Packing** is `CONFIRM_SHIPPING` (`SHIPPING_MODE_SELECTED → SELLER_PACKING_PENDING`), actor SELLER. It applies only to delivery orders, and a repeat succeeds.
- **Mark handed over (S10)** applies only to self-pickup orders. It runs `HANDED_OVER` (`SHIPPING_MODE_SELECTED → DELIVERED`, new trigger), then `REQUEST_BUYER_PROOF` (system), and a repeat succeeds (G4).
- **Ownership.** `findByIdAndSellerId` returns 404 for both an unknown order and another seller's order. Concurrent changes return 409 `ERROR_ORDER_ACTION_NOT_ALLOWED`.
- **URGENT.** Shown on a New delivery order when `placedAt + PICKUP_SLA_HOURS` falls within `urgent-window` (PT24H). It is never shown on self-pickup orders.
- **Paging.** 20 per page, capped at 50, sorted by bucket rank and then `created_at DESC`.

**Out of scope (owner):**
- packing proof (US-026)
- pickup scheduling and the schedule view (US-027)
- Reject and its penalty (US-059, Sprint 7)
- order details content and `order.updated` (US-023)
- tracking (US-029)
- order history (US-070)
- creating the `NEW_ORDER` notification (US-021)
- the buyer's confirmation and the auto-confirmation after hand-over (US-031, Part J)

## 4. Implementation Steps

### 0. Workflow (CLAUDE.md §5)
- [x] Do not touch the main `valuex-backend`, `valuex-mobile` or `Documents` checkouts. They have their own branches and untracked files. Create the worktrees `wt/US-112-backend` and `wt/US-112-mobile` from an up-to-date `origin/main`.
- [x] Backend: US-092 is on `main` (G3), so branch straight from `origin/main`. Check the latest migration number when the branch is cut; this story adds none.

### 1. Backend: domain (`com.valuex.order.domain`)
- [x] `OrderStateMachine`: add `HANDED_OVER` (`SHIPPING_MODE_SELECTED → DELIVERED`) and update `TRANSITION_COUNT` in `OrderStateMachineTest`.
- [x] `OrderErrors`: add `ORDER_ACTION_NOT_ALLOWED = "ERROR_ORDER_ACTION_NOT_ALLOWED"` (G5).
- [x] `FulfilmentBucket` (`NEW, PACKING, SCHEDULED, SHIPPED`), with a rank and the (state, mode) pairs of each bucket (`pairsOf`).
- [x] `SellerOrderAction`: `START_PACKING, REJECT, CONTINUE_PACKING, SCHEDULE_PICKUP, VIEW_SCHEDULE, RESCHEDULE_PICKUP, VIEW_PICKUP_DETAILS, MARK_HANDED_OVER`.
- [x] `OrderTag`: `URGENT, SELF_PICKUP, PICKUP_FAILED, ARRANGING_PICKUP, RETURNING, HANDED_OVER`.

### 2. Backend: settings (`com.valuex.plans.domain`)
- [x] `FulfilmentSetting`: add `PICKUP_SLA_HOURS` (default 48, range 12–120, LLD 0.3), and expose it in `FulfilmentSettings` (G8).
- [x] `application.yml`: add `valuex.seller-orders.urgent-window: PT24H` and `max-page-size: 50` through a `@ConfigurationProperties` record `SellerOrdersProperties`.

### 3. Backend: ports
- [x] `order/application/port/OrderPartyDirectoryPort`, with `displayNames(Collection<UUID>)` and `isActive(UUID)`, and its adapter `auth/infrastructure/order/OrderPartyDirectoryAdapter`. This follows `ParticipantDirectoryAdapter` (G6, G9).
- [x] Thumbnails: an `order/application/port/OrderItemPhotoPort` that returns `thumbnailUrls(Collection<UUID> listingIds)`, backed by `ListingPhotoLinkPort` and called once per page. The adapter lives in `listing` or `media`; G6 says which. A null result means the app shows a placeholder.

### 4. Backend: persistence (`order/infrastructure/persistence`)
- [x] `OrderRepository.findByIdAndSellerId(id, sellerId)`, excluding rows where `deleted_at` is set.
- [x] `SellerOrderQueryRepository`, a native projection into `IncomingOrderRow` (G7):
  - joins `orders`, its single `order_items` row, and `shipments` (inner join, S1)
  - filters on `seller_id`, `deleted_at IS NULL`, the bucket's (status, delivery_mode) pairs, and `NOT (status = 'RETURN_TO_SELLER' AND s.rto_delivered_at IS NOT NULL)`
  - orders by `CASE` bucket rank, then `created_at DESC`
  - takes a `Pageable`, with a count query
- [x] Summary: one grouped count with the same `WHERE`, folded into the four buckets in Java, so counts and list always agree.

### 5. Backend: application (`order/application`)
- [x] DTOs `IncomingOrderResponse` (the A.4.1 shape), `IncomingOrdersSummaryResponse` and `IncomingOrderRow`. Amounts are JSON strings. Self-pickup orders carry `pickupAddress` (G10).
- [x] `FulfilmentBucketResolver`: the A.5.2 switch. `RESCHEDULE_PICKUP` is offered only while `pickupReschedules < PICKUP_MAX_RESCHEDULES`. The URGENT rule uses an injected `Clock`.
- [x] `SellerOrderQueueService`:
  - `list(sellerId, bucket, pageable)`: caps the size at 50, batches names and thumbnails, and resolves each row
  - `summary(sellerId)`
  - `startPacking(sellerId, orderId)`: wrong state or self-pickup gives 409. On `INVALID_STATE_TRANSITION` it re-reads the order and returns 200 if it is already `SELLER_PACKING_PENDING`, otherwise 409 (G11).
  - `markHandedOver(sellerId, orderId)`: runs two moves in one transaction. A delivery order or the wrong state gives 409, and a repeat from `BUYER_PROOF_PENDING` returns 200.
  - every method first checks `isActive(sellerId)` and refuses with 403 `ERROR_ACCOUNT_NOT_ACTIVE`
- [x] Metrics: `seller_orders_start_packing_total{result}` and `seller_orders_handed_over_total{result}`. Logs carry ids only.

### 6. Backend: API (`order/api/SellerOrderController`)
- [x] `GET /api/v1/seller/orders?bucket=&page=&size=`: `@PageableDefault(size = 20)`. An invalid `bucket` gives 400 `ERROR_VALIDATION`. Returns `PagedResponse`.
- [x] `GET /api/v1/seller/orders/summary`.
- [x] `POST /api/v1/seller/orders/{orderId}/start-packing` and `POST /api/v1/seller/orders/{orderId}/mark-handed-over`.
- [x] OpenAPI tag "Seller Orders", with the refusals documented as other controllers do.

### 7. Backend: badge and push
- [x] `order/adapter/menu/IncomingOrdersBadgeProvider implements ProfileMenuBadgeProvider` (key `INCOMING_ORDERS`). Its count is orders with `status = SHIPPING_MODE_SELECTED`, both delivery modes, using one indexed count.
- [x] `PushPolicy`:
  - add `ORDERS = "orders"`
  - add `Map.entry("NEW_ORDER", new Rule(ORDERS, true, false))`
  - document the deep link `{type: NEW_ORDER, route: /seller/orders}` for US-021

### 8. Mobile: domain and data (`lib/features/order/`)
- [x] `domain/entities/incoming_order.dart`: `IncomingOrder`, `FulfilmentBucket`, `SellerOrderAction`, `OrderTag`, `OrdersSummary` (`fromJson`; unknown actions and tags are ignored).
- [x] `domain/repositories/seller_order_repository.dart`, the interface.
- [x] `data/seller_order_repository_impl.dart` for the four endpoints, with new paths in `ApiConstants`.
- [x] `data/mock_seller_order_repository.dart`: the four Make sample orders (ORD-S-1001 Ananya Sharma / Leica M6 / ₹42,000 / URGENT, ORD-S-1000, ORD-S-0999, ORD-S-0998), chosen by an `AppConfig` mock mode (G12). Make loads its sample photos from Unsplash, so the mock uses no remote photos: `imageUrl` is null (the placeholder is shown) or a bundled asset.

### 9. Mobile: presentation
- [x] `presentation/providers/seller_order_providers.dart`:
  - a paged list provider and a summary provider, loaded in parallel
  - pull to refresh invalidates both
  - after any action, and on return from a pushed route, both are invalidated
  - a 409 shows the message, then invalidates both
- [x] `seller_incoming_orders_screen.dart`, with the widgets `incoming_orders_header`, `order_count_tile`, `incoming_order_card`, `order_status_chip` and `buyer_initials_avatar`. Follow the A.8.3 mapping to the design system.
- [x] States: skeleton while loading; empty; error with Retry; the last loaded list with a message; and the "Showing all {n} incoming orders" footer.
- [x] Action mapping per A.8.2:
  - `START_PACKING`: call the endpoint, then open packing
  - `MARK_HANDED_OVER`: confirm "Has the buyer collected the item?", call, then reload
  - `VIEW_PICKUP_DETAILS`: a read-only sheet
  - `CONTINUE_PACKING`, `SCHEDULE_PICKUP`, `VIEW_SCHEDULE`, `RESCHEDULE_PICKUP`, `REJECT` and the details button: the coming-soon message until US-026, US-027, US-059 and US-023 ship (G2)
- [x] Initials come from the first letters of the first two words, and work for non-Latin names. Relative time is localized.
- [x] Icons, taken from the Make screen and drawn from Material:
  - status chips and tiles: New `Icons.error_outline`, Packing `Icons.inventory_2_outlined`, Scheduled `Icons.schedule`, Shipped `Icons.local_shipping_outlined`
  - Continue Packing and Schedule Pickup: the package icon; View Schedule and Reschedule Pickup: the clock icon; the "Order Shipped" row: `Icons.check_circle_outline`
  - each bucket keeps its own icon, so status never depends on colour (A.8.3)
- [x] Price is shown as text, "₹" followed by the amount with Indian grouping (₹42,000, ₹1,85,000), in `AppTextStyles.cardPrice`. Make's separate rupee icon is not used, so screen readers announce the amount as one value.
- [x] Item titles wrap to at most two lines and then end with an ellipsis. Make cuts them to one line, but the story lists "item titles that wrap" as an edge case, including Hindi at 200% text.
- [x] Routing: `RouteNames.sellerOrders = '/seller/orders'` for signed-in `ACTIVE` users. The Profile "Incoming Orders" row gets `onTap: () => context.push(RouteNames.sellerOrders)` and keeps the `INCOMING_ORDERS` badge.
- [x] Push:
  - `notification_deep_links.dart` maps `NEW_ORDER` to `/seller/orders`, and the arriving push invalidates both providers
  - `MainActivity.kt` gets the `orders` channel, with `push_channel_orders` added in English and Hindi
- [x] Strings (A.8.4) in `app_en.arb` and `app_hi.arb`, with plurals. Badge and tile counts above 99 show "99+" (G17).
- [x] Accessibility: add the screen to `all_screens_accessibility_test.dart` and `screen_headings_test.dart`.

### 10. Documentation (CLAUDE.md §5.10)
- [x] LLD Part A: an "As built" section (A.12) with any deviations, the version line and a change-log row.
- [x] `Sprint-plan.md`: link the plan from the US-112 row and mark it built.
- [x] `user-stories.md`: a built note.
- [x] Record the hand-offs to US-021, US-023, US-026, US-027, US-031 and US-059 (G2).
- [x] `Manual Testing Guides/US-112-Testing-Guide.md`.

### 11. Quality gates (CLAUDE.md §5.7, §5.8)
- [x] Backend: `mvn clean verify` (on this machine, `JAVA_TOOL_OPTIONS="-Duser.timezone=Asia/Kolkata"`), then Checkstyle, then the Sonar scan. Fix every issue in changed files.
- [x] Mobile:
  - `dart format lib test` must leave a clean diff
  - `flutter analyze`
  - `flutter test --coverage`
  - the Sonar scan
- [x] Coverage of new and changed code: 90% or more in both repos.

## 5. Test Plan

**Backend unit (JUnit 5, Mockito, AssertJ):**

| Test | Covers |
|---|---|
| `FulfilmentBucketResolverTest` (parameterized) | Every row of A.3.1:<br>• all 24 order states × both modes<br>• the shipment sub-states (`SHIPPING_REQUIRED` vs `PICKUP_SLOT_SELECTED` / `SHIPPING_PARTNER_SELECTION`; `PICKUP_FAILED`)<br>• `RETURN_TO_SELLER` with and without `rto_delivered_at`<br>• `RESCHEDULE_PICKUP` present below the limit and absent at it<br>• URGENT at the window edges (just inside, exactly on, just outside), never for self-pickup or outside New |
| `SellerOrderQueueServiceTest` | `list`:<br>• size capped at 50, batched names and thumbnails, missing thumbnail gives null<br>`summary`: folds rows into buckets<br>`startPacking`:<br>• success (`CONFIRM_SHIPPING`, actor SELLER), repeat gives 200 with no move<br>• wrong state gives 409, self-pickup gives 409, foreign or unknown order gives 404<br>• a race (`INVALID_STATE_TRANSITION` then re-read `SELLER_PACKING_PENDING`) gives 200, otherwise 409<br>`markHandedOver`:<br>• two moves in order, repeat gives 200, delivery order gives 409, wrong state gives 409, foreign order gives 404<br>Inactive seller: 403 on every method |
| `SellerOrderControllerTest` (`@WebMvcTest`) | Envelope and paging metadata, an invalid `bucket` gives 400, 401 without a token, error codes mapped to their HTTP statuses |
| `IncomingOrdersBadgeProviderTest` | Key `INCOMING_ORDERS`; counts New orders of both modes |
| `OrderPartyDirectoryAdapterTest`, photo port adapter test | Batch names, active check, empty input |
| `OrderStateMachineTest` (updated) | `HANDED_OVER` allowed only from `SHIPPING_MODE_SELECTED`; new `TRANSITION_COUNT` |
| `FulfilmentSettingTest`, `PlatformSettingsServiceTest` (updated) | `PICKUP_SLA_HOURS` default, range and fallback |
| `PushPolicyTest` (updated) | `NEW_ORDER` → `orders`, high priority, not skipped when online |

**Backend integration (`SellerIncomingOrdersIntegrationTest`, `@SpringBootTest` + Testcontainers PostgreSQL; orders and shipments inserted directly):**
- a seller sees only their own orders, and another seller's id gives 404
- order across buckets and newest first within each; pagination metadata and the second page
- `RETURN_TO_SELLER` delivered back and `COMPLETED` orders are not listed
- summary equals the list totals
- `start-packing` and `mark-handed-over` write `order_status_history` (actor SELLER, then SYSTEM)
- two concurrent `start-packing` calls give one transition and two 200s
- the badge count appears in `GET /users/me/menu-summary`
- an inactive account gets 403

**Mobile (flutter_test, mocktail):**
- repository: payload parsing, query parameters, error mapping, unknown action and tag ignored
- mock repository: the four Make samples, with no remote image URLs
- providers: parallel load, refresh, invalidation after an action, a 409 shows the message and reloads
- card per bucket: the buttons and tags match `actions` and `tags`; URGENT; self-pickup tag; "Order Shipped" row with no button; placeholder image
- Start Packing calls the endpoint, then shows coming soon
- Mark as handed over: confirm, call, reload; cancelling does nothing
- header line and New badge with plurals; tiles; "99+"
- empty, skeleton, error with Retry, stale list with message; footer after the last page
- back button; Profile row navigates; `NEW_ORDER` deep link; initials edge cases
- price text "₹42,000" and "₹1,85,000" (one semantics label, no rupee icon)
- each bucket's chip and tile shows its own icon; the action rows show their icons
- a long title wraps to two lines and ends with an ellipsis, with no overflow at 200% text
- Hindi at 200% text; accessibility guidelines; heading test

## 6. Validation Checklist

- [ ] Page, back button, title, "{n} orders · {x} new", "{x} New" badge only when x > 0
- [ ] Four tiles, and the counts agree with the list
- [ ] Card order: buckets, then newest first; 20 per page with more on scroll; footer text
- [ ] Card fields: reference, URGENT, chip with icon and text, photo or placeholder, title, ₹ price with Indian grouping, buyer name and initials, relative time, details button
- [ ] New delivery: Start Packing moves to Packing (idempotent; 409 on a stale card); Reject is shown (coming soon until US-059)
- [ ] Packing: Continue Packing; Schedule Pickup after proof; "Arranging pickup" with no action while booking
- [ ] Scheduled: View Schedule, plus Reschedule while allowed; the "Pickup failed" tag
- [ ] Shipped: "Order Shipped", no action; the exception states included; "Returning to you"; "Handed over"
- [ ] Self-pickup: New, tag, View Pickup Details, Mark as handed over (G4), Reject; never URGENT
- [ ] Completed, cancelled, return requested, disputed and returned-to-seller-delivered orders are not listed
- [ ] Only the seller's own orders; foreign and unknown orders give the same 404; only the buyer's display name is exposed
- [ ] Account not `ACTIVE` gives 403; the app shows the blocked screen
- [ ] Invalid `bucket` gives 400; size capped at 50
- [ ] `INCOMING_ORDERS` badge = New count; `NEW_ORDER` push row and deep link; `orders` Android channel
- [ ] Pull to refresh; refresh on return from actions; refresh on push
- [ ] Error texts: `ERROR_INCOMING_ORDERS_LOAD_FAILED`, `ERROR_ORDER_ACTION_NOT_ALLOWED`, `ERROR_ORDER_NOT_FOUND`, `ERROR_SECTION_UNAVAILABLE`
- [ ] English and Hindi strings; 200% text; 48 dp targets; status not by colour alone; in both accessibility tests
- [ ] Coverage of 90% or more; Checkstyle, `flutter analyze` and Sonar clean; LLD, Sprint-plan, user-stories and testing guide updated

## 7. Open Gaps / Questions

**All gaps closed (user decisions, 2026-11-28):**
- **G1:** closed. PR #307 is merged, so LLD 0.4/0.5 is on `main`.
- **G3:** closed. US-092 (PR #95) is merged.
- **G4:** build "Mark as handed over" as in LLD 0.4 (S10). This closes the US-092 G6 hand-off (`HANDED_OVER`).
- **G2, G5 to G17:** the proposals below are agreed as written.

| # | Gap | Proposal |
|---|---|---|
| G1 | **The LLD on `main` is version 0.3.** The revised Part A (0.4: shipment sub-states, `mark-handed-over`, `NEW_ORDER` from US-021) exists only in Documents PR #307. This plan follows 0.4. | Merge #307 before or with this plan's PR. The plan's link resolves once it merges. |
| G2 | **Screens and data from unbuilt stories:**<br>• no order is ever created (US-021)<br>• no order details or `order.updated` (US-023)<br>• no packing (US-026), scheduling (US-027), Reject (US-059) or buyer confirmation after hand-over (US-031, Part J) | • Those buttons show the existing coming-soon message.<br>• Refresh comes from pull, return-from-action and push only. The `order.updated` listener is a hand-off to US-023.<br>• Each hand-off is recorded in the LLD as-built notes. |
| G3 | **The backend needs US-092** (`shipments`, `FulfilmentSetting`, `ShipmentState`), which is PR #95 and still open. | Cut the backend branch after #95 merges. If it has not merged, stack on `feature/US-092-shipping-lifecycle` and retarget the PR. |
| G4 | **Mark as handed over (S10)** is "Proposed" in LLD 0.4 and needs product-owner confirmation (M.4 G21). After a hand-over, nothing moves the order out of `BUYER_PROOF_PENDING` until US-031 or Part J, so the card stays in Shipped "Handed over". The story itself says "until then a self-pickup order stays New". | Build it as in 0.4, which also closes the US-092 G6 hand-off (`HANDED_OVER`). Alternative: leave `HANDED_OVER` and `MARK_HANDED_OVER` out until Part J. |
| G5 | `ERROR_ORDER_ACTION_NOT_ALLOWED` is listed in LLD 0.4 as an existing code, but it is **not in the code**. | Add it to `OrderErrors`. |
| G6 | **Cross-module reads.** The LLD joins `users` in SQL for the buyer name and calls a `MediaUrlResolver`, which does not exist. `order_items.image_url` is a snapshot, and a signed link in it would expire. | • Names: an order-side port `OrderPartyDirectoryPort` with its adapter in `auth`, as `ParticipantDirectoryPort` does.<br>• Thumbnails: `OrderItemPhotoPort`, backed by `ListingPhotoLinkPort` with one batch per page; null when the listing or photo is gone.<br>• No SQL against another module's tables. |
| G7 | **Shipment data.** LLD A.1 names a `ShipmentQueryPort`, but A.5.3 joins `shipments` in the query. A.5.2 says "the count needs no join", but that is wrong for `RETURN_TO_SELLER` once delivered back, which must leave both list and counts. | One read-only native query in `order` that joins `shipments` (inner, S1), with the same `WHERE` for list and summary. No `ShipmentQueryPort`. Correct A.5.2 in the as-built notes. |
| G8 | `PICKUP_SLA_HOURS` (LLD 0.3) is not yet in `FulfilmentSetting`; US-092 added only two keys. | Add it here (48, range 12–120). The 24-hour urgent window stays a property, as A.5.7 says. |
| G9 | **`ACTIVE` gating.** The LLD says 403 for a non-active account, but there is no global filter. | Check `OrderPartyDirectoryPort.isActive` in the service and return `ForbiddenException(ACCOUNT_NOT_ACTIVE)`, as `ContactGuard` does. |
| G10 | **View Pickup Details.** It needs "my pickup address and hours as the buyer sees them", and no response field carries this. | Add `pickupAddress` (the `orders.pickup_address` snapshot) to the list item for self-pickup orders only. Show hours only if the snapshot holds them; otherwise show the address alone and note it as a gap for US-020. |
| G11 | **Concurrent "Start Packing".** `move` locks the row, so the second caller gets `INVALID_STATE_TRANSITION`, but the story says a second tap "does nothing harmful and opens the same packing screen". | On that error, re-read the order. Return 200 if it is now `SELLER_PACKING_PENDING`, otherwise 409. |
| G12 | **Mock repository.** The story says mock data is used until the backend ships, and the backend ships in this story. Without US-021 a real seller has no orders, so the page would always be empty. | Use the real repository by default. Add an `AppConfig` mock mode (like `useMockPayment`) that serves the Make samples, for demos and QA until US-021. |
| G13 | **Rate limit** (60 per minute per seller) is marked "proposed" in A.9. There is no shared rate limiter. | Out of scope here. Leave it as an LLD open item. |
| G14 | **Seller notification states** (US-090 G3: which order changes notify the seller) were deferred to "US-023 or US-112". | US-112 adds only the `NEW_ORDER` push row. Seller status notifications stay with US-023 and Parts E–J. |
| G15 | **Error text.** The story says "…next step. Refreshing"; LLD A.7 omits "Refreshing". | The server sends the LLD text, and the app shows the story text, which includes "Refreshing". |
| G16 | **Hindi and the Android channel.** The `orders` channel name needs a Hindi string. | Add `push_channel_orders` to `values` and `values-hi` alongside `chat` and `offers`. |
| G17 | **Counts above 99.** The story edge case has no rule. | The "{x} New" badge and the Profile badge show "99+". The tiles and the count line show the full number. |

## 8. Implementation Notes (as built, 2026-11-28)

Branches: `feature/US-112-seller-incoming-orders` in `valuex-backend` and in `valuex-mobile`, both cut from `origin/main` after US-092 (PR #95) merged. The design differences are recorded in [LLD A.12](../LLD/Sprint-6-Shipping-Delivery-LLD.md#a12-as-built-us-112-2026-11-28). In short:

- **G7, as proposed:** one read query joins `shipments`, and the group is computed in SQL, so the list, the counts and the single card agree. The resolver turns a row into tags and actions only.
- **G6, G9, as proposed:** `OrderPartyDirectoryPort` (auth adapter) and `OrderItemPhotoPort` (listing adapter over `ListingPhotoLinkPort`).
- **G10:** `pickupAddress` added to self-pickup cards. **Also added:** `bookingError`, because LLD A.1.1 needs the booking error on the card, which A.4.1 had no field for.
- **G11, done differently:** instead of catching `INVALID_STATE_TRANSITION` and re-reading, the order is read with a row lock (`findByIdAndSellerIdForUpdate`), so two calls run one after the other and the second returns the same 200. The move commits before the card is read: the first build ran both in one transaction, and a photo link that failed marked it rollback-only (found by the integration test).
- **Push:** a `PushCopy` text for `NEW_ORDER` was needed besides the `PushPolicy` row; a push without text is not sent.
- **Mobile route:** `/seller/orders` matched the existing `/seller/:sellerId` profile route. The Incoming Orders route is declared first, and the route guard treats it as its own page (active accounts only).
- **Mobile refresh:** no refresh when a push arrives while the app is open, because the app has no foreground push stream; a tapped push opens the page fresh. No `order.updated` listener (US-023).
- **G13:** the rate limit was not built.

**Hand-offs** (LLD A.12): US-021 (`NEW_ORDER` notification with `/seller/orders`, shipment per order), US-023 (order details, `order.updated`), US-026 and US-027 (packing and pickup screens), US-059 (Reject), US-031 / Part J (buyer confirmation after hand-over). The US-092 hand-off G6 (`HANDED_OVER`) is closed, and the US-090 and US-092 testing guides now point their US-112 rows here.

**Tests:**
- Backend: 8 new test classes with 67 tests, including `SellerIncomingOrdersIntegrationTest` with 7 tests on Testcontainers. 4 test classes updated: `OrderStateMachineTest`, `FulfilmentSettingTest`, `PushPolicyTest` and `PushCopyTest`.
- Mobile: 3 new test files (41 tests); the config, deep-link, route-guard, Profile, accessibility and heading tests were extended.

---

**Status:** Approved (2026-11-28) · Built (2026-11-28)
