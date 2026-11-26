# US-090: Lifecycle State - Order — Implementation Plan

## 1. Header

| Field | Value |
|---|---|
| Story ID | US-090 |
| Title | Lifecycle State - Order |
| Sprint | Sprint 5 — Cart, Checkout & Payments |
| Story Points | 5 |
| Repos | valuex-backend only |
| Dependency | US-020 (built, merged). Must come **before** US-091 (escrow), US-021 (checkout, payment and order creation) and US-023 (order tracking), which all read or move orders through this story's service |
| Branch | `feature/US-090-order-lifecycle` in `valuex-backend`, from `main` |

**Scope decisions (2026-11-26):**
- **US-090 only.** The LLD suggests building US-090 together with US-091; they will be separate branches. US-091 (escrow tables, ledger, escrow state wiring) gets its own plan next.
- **`orders.checkout_id` without a foreign key for now.** The `checkouts` table belongs to US-021. US-090 creates `checkout_id UUID NOT NULL` with no constraint, and the US-021 checkouts migration adds `fk_orders_checkout`. This is a deviation from LLD C.2 and gets recorded in the LLD.

## 2. Story Recap

**As a** platform **I want** to track order lifecycle states **so that** order status determines actions and payments.

**Acceptance Criteria** (`Documents/user-stories.md`): once an order is created it progresses through `ORDER_INITIATED`, `SELLER_PRICE_ACCEPTED`, `CHECKOUT_STARTED`, `PAYMENT_PENDING`, `PAYMENT_FAILED`, `PAYMENT_SUCCESS`, `ESCROW_HELD`, `SHIPPING_MODE_SELECTED`, `SELLER_PACKING_PENDING`, `SELLER_PROOF_UPLOADED`, `PICKUP_SCHEDULED`, `PICKED_UP`, `IN_TRANSIT`, `OUT_FOR_DELIVERY`, `DELIVERED`, `BUYER_PROOF_PENDING`, `BUYER_CONFIRMATION_PENDING`, `COMPLETED`, `RETURN_REQUESTED`, `DISPUTE_RAISED`, `SHIPMENT_LOST`, `DELIVERY_FAILED`, `RETURN_TO_SELLER`, `CANCELLED`.

**Business Rules:** escrow held until `COMPLETED` or `DISPUTE_RAISED` · auto-complete after 7 days if no buyer action · `CANCELLED` triggers refund · `SHIPMENT_LOST` triggers investigation · each order covers exactly one item; a checkout with several items creates several orders.

**Validation Rules:** state transitions sequential · cannot skip states (except exceptions like `CANCELLED`) · both parties notified at key states · timestamps recorded for SLA tracking.

**Related:** US-112 moves `SHIPPING_MODE_SELECTED → SELLER_PACKING_PENDING` ("Start Packing"); its seller buckets are derived from these states.

**Error Scenarios:** none in the story. From the LLD: `ERROR_ORDER_NOT_FOUND` (404, "This order was not found", LLD 0.5) and the existing `INVALID_STATE_TRANSITION` from `common.statemachine.StateMachine`.

## 3. Design Reference

Primary source: [Sprint-5-Cart-Checkout-Payments-LLD.md — Part C](../LLD/Sprint-5-Cart-Checkout-Payments-LLD.md#part-c---us-090-lifecycle-state-order) (C.1 to C.4). Also read: 0.5 (error codes), 0.6 (events), 0.7 D2 (no order before payment), D10 (money type), Part E.5 (how US-021 will create orders) and Part H (what US-023 reads). HLD: `03-Data-Architecture.md` (one item and one seller per order).

**What already exists in the code:**
- `order.domain.OrderState`: all 24 states, with display names.
- `order.domain.OrderStateMachine`: a Sprint 0 skeleton built on `common.statemachine.StateMachine`. Its trigger names and first steps differ from LLD C.3 (see below). Nothing calls it yet.
- The pattern to copy is US-089's `ListingLifecycleService.transition`: lock the row with `findByIdForUpdate`, check the machine, save, write one history row and publish one event through `DomainEventPublisher`.

**Key design decisions (from LLD Part C unless noted):**
- **No order exists before payment (D2).** US-090 builds no API and creates no orders. It provides the tables, the entities, the state machine and the only service allowed to change `orders.status`. US-021's `OrderCreationService` inserts orders and replays the checkout's pre-payment history (C.3). US-023 and US-070 read them.
- **One item per order:** `order_items.order_id` is `UNIQUE`, and `seller_id` sits on `orders` as a plain column.
- **Insert-only history:** `order_status_history` rows are never updated or deleted. Each row stores `actor_type` (`BUYER`, `SELLER`, `SYSTEM`, `ADMIN`, `GATEWAY`), `actor_id` and `changed_at`, which gives the SLA timestamps.
- **Every transition goes through `OrderTransitionService.move(orderId, trigger, actor, note)`.** It locks the order row (`SELECT ... FOR UPDATE`), checks `OrderStateMachine`, writes the history row and publishes `OrderStatusChangedEvent`. `orders.version` (`@Version`) guards concurrent updates.
- **Sprint 5 transitions use the LLD C.3 trigger names**: `START_CHECKOUT`, `PAYMENT_INITIATED`, `PAYMENT_FAILED`, `PAYMENT_CONFIRMED`, `ESCROW_HELD`, `MODE_SELECTED`, `CANCEL`. The skeleton's Sprint 5 names are replaced. Transitions after `SHIPPING_MODE_SELECTED` keep their current names, since Sprint 6 to 8 own them.
- **Money** is `NUMERIC(12,2)` and `BigDecimal` with scale 2, HALF_UP (D10). `chk_orders_total` enforces `total_amount = item_amount + shipping_amount`.

**Reconciled Sprint 5 transitions** (C.3; replaces the skeleton's first section):

| From | To | Trigger | Note |
|---|---|---|---|
| `SELLER_PRICE_ACCEPTED` | `ORDER_INITIATED` | `START_CHECKOUT` | Both replayed rows are written when the checkout is created (C.3). Order and trigger name: **G1** |
| `ORDER_INITIATED` | `CHECKOUT_STARTED` | `START_CHECKOUT` | |
| `CHECKOUT_STARTED` | `PAYMENT_PENDING` | `PAYMENT_INITIATED` | |
| `PAYMENT_PENDING` | `PAYMENT_FAILED` | `PAYMENT_FAILED` | |
| `PAYMENT_FAILED` | `PAYMENT_PENDING` | `PAYMENT_INITIATED` | A retry is a new payment attempt (US-075) |
| `PAYMENT_PENDING` | `PAYMENT_SUCCESS` | `PAYMENT_CONFIRMED` | |
| `PAYMENT_SUCCESS` | `ESCROW_HELD` | `ESCROW_HELD` | |
| `ESCROW_HELD` | `SHIPPING_MODE_SELECTED` | `MODE_SELECTED` | |
| `CHECKOUT_STARTED` | `SHIPPING_MODE_SELECTED` | `MODE_SELECTED` | **New:** Pay at Pickup skips payment (C.3) |
| `ORDER_INITIATED`, `PAYMENT_PENDING`, `PAYMENT_FAILED` | `CANCELLED` | `CANCEL` | Unchanged from the skeleton. Cancelling after payment is Sprint 7: **G4** |

Removed from the skeleton: `ORDER_INITIATED → SELLER_PRICE_ACCEPTED` (`ACCEPT_PRICE`), and the old names `PROCEED_PAYMENT`, `PAYMENT_SUCCESS`, `PAYMENT_FAIL`, `RETRY_PAYMENT`, `HOLD_ESCROW`, `SELECT_SHIPPING`. Everything from `SHIPPING_MODE_SELECTED → SELLER_PACKING_PENDING` onwards stays unchanged.

**Out of scope (owner in brackets):** creating orders and replaying checkout history (US-021) · escrow tables and ledger (US-091) · the 7-day auto-complete (US-024, Sprint 6) · refund on `CANCELLED` (Sprint 7) · `SHIPMENT_LOST` investigation (not designed, **G5**) · notification texts and the `order.updated` realtime topic (US-023, Part H) · any API or mobile screen.

## 4. Implementation Steps

### 0. Workflow (CLAUDE.md §5)
- [ ] `valuex-backend` is currently on `feature/US-016-communication-history` with uncommitted changes, including an untracked `V44__communication_access_log.sql`. Leave that work alone: either finish US-016 first, or create the US-090 branch from an up-to-date `main` without touching the US-016 changes.
- [ ] `git checkout main && git pull`, then `git checkout -b feature/US-090-order-lifecycle` and rebase on `main`.

### 1. Database Migration — `valuex-backend`
- [ ] `V{N}__orders.sql`, where `{N}` is the next free number on `main` when the branch is cut. `V44` is already used by US-016 on its branch, so check both and pick a number neither uses (**G6**). The file contains LLD C.2 as written, except that `checkout_id` gets **no** `REFERENCES checkouts (id)` (scope decision). Add a SQL comment saying US-021 adds the constraint.
  - `order_number_seq`, `orders` (with `chk_orders_total`, `idx_order_buyer_created`, `idx_order_seller_status`), `order_items` (`order_id UNIQUE`), `order_status_history` with `idx_osh_order`.
  - Add `CHECK` constraints on `delivery_mode IN ('DELIVERY','SELF_PICKUP')`, `payment_option IN ('PAY_NOW','PAY_AT_PICKUP')` and `actor_type`. This follows the `payments.status` CHECK of V19 (LLD D.1). The `status` CHECK lists the 24 `OrderState` names.

### 2. Domain — `com.valuex.order.domain`
- [ ] `OrderStateMachine`: replace the Sprint 5 section with the reconciled table above. Leave the rest unchanged.
- [ ] `Order` entity (`orders`): `@Version version`, `status` as `@Enumerated(STRING) OrderState`, `deliveryMode` and `paymentOption` as enums, `deliveryAddress` and `pickupAddress` as JSONB snapshots (use the same JSONB mapping as `cart_items`/US-020), and `deletedAt`. No public setter for `status`: only `OrderTransitionService` changes it, through a package-private `applyStatus(OrderState)` or the existing convention, whichever `Listing` uses.
- [ ] `OrderItem` entity (`order_items`) with title and image snapshot.
- [ ] `OrderStatusHistory` entity (`order_status_history`), immutable: `@Immutable`, no setters.
- [ ] Enums `DeliveryMode` and `PaymentOption`. Reuse the US-020 cart enums if they exist with the same values, rather than duplicating them. Add `OrderActorType` (`BUYER`, `SELLER`, `SYSTEM`, `ADMIN`, `GATEWAY`).
- [ ] `OrderActor` record (`type`, `id`, with `id` null for `SYSTEM`) so callers pass one value.
- [ ] `OrderStatusChangedEvent` (domain event, same base class as `ListingStatusChangedEvent`): `orderId`, `orderNumber`, `buyerId`, `sellerId`, `from`, `to`, `trigger`, `actorType`, `actorId`, `changedAt`. It carries both party ids so US-023 and later listeners can notify both parties (validation rule).

### 3. Persistence — `com.valuex.order.infrastructure.persistence`
- [ ] `OrderRepository` with `findByIdForUpdate(UUID)` (`@Lock(PESSIMISTIC_WRITE)`, as in `ListingRepository`) and `nextOrderNumberValue()` (native `SELECT nextval('order_number_seq')`).
- [ ] `OrderItemRepository` and `OrderStatusHistoryRepository`. The latter gets `findByOrderIdOrderByChangedAtAscIdAsc` for the timeline (US-023) and only insert methods are used.

### 4. Application — `com.valuex.order.application.service`
- [ ] `OrderTransitionService.move(UUID orderId, String trigger, OrderActor actor, String note)` with `@Transactional`:
  1. Lock the order, or throw `NotFoundException("ERROR_ORDER_NOT_FOUND", …)`.
  2. Resolve the target state from `(current status, trigger)`. `StateMachine` today needs the target passed in, so add a small lookup. Either add `resolveTarget(from, action)` to `OrderStateMachine`, or have `move` take the target as `ListingLifecycleService.transition` does. Pick one and keep it consistent. Unknown pairs raise `INVALID_STATE_TRANSITION`.
  3. Set the status and save, so `@Version` increments.
  4. Insert the history row (`from_status`, `to_status`, actor, note trimmed to 255, `changed_at = now`).
  5. Publish `OrderStatusChangedEvent`. Log the order id, the states and the trigger (no personal data).
- [ ] `OrderNumberGenerator.next()`: `VX-` + `yyMMdd` (IST, using the platform `Clock` bean) + `-` + the 6-digit zero-padded sequence value, for example `VX-261126-000123`. US-021 uses it when it inserts orders. Format source: LLD C.2 comment (**G7** covers the time zone and what happens past 999999).
- [ ] Error code `ERROR_ORDER_NOT_FOUND` added to the error-code catalogue and the message bundles (English and Hindi) used for the LLD 0.5 codes.

### 5. Documentation (CLAUDE.md §5.10)
- [ ] LLD Part C: record the deferred FK, the final trigger names and order (G1), the Pay at Pickup transition, and the `CHECK` constraints.
- [ ] LLD Part E.2: note that US-021's migration adds `fk_orders_checkout`.
- [ ] `Sprint-plan.md`: link this plan from the US-090 row and mark it built when done.
- [ ] `Documents/Manual Testing Guides/US-090-Testing-Guide.md`: backend-only checks using SQL (migration applied, constraints, a scripted run of transitions through a test endpoint or test, history rows).

### 6. Quality gates (CLAUDE.md §5.7 and §5.8)
- [ ] `./gradlew build` (or the Maven equivalent used by the repo), checkstyle, JaCoCo, then the SonarQube scan. Fix every issue before pushing.

## 5. Test Plan

Target is above 90% line and branch coverage for `com.valuex.order`. Integration tests use Testcontainers PostgreSQL (see the local Docker workaround in project memory).

**Unit — `OrderStateMachineTest`**
- Parameterized: every allowed Sprint 5 transition in the table succeeds (AC: states progress).
- The full replay path `SELLER_PRICE_ACCEPTED → … → SHIPPING_MODE_SELECTED` succeeds step by step, with and without one `PAYMENT_FAILED → PAYMENT_PENDING` retry.
- The Pay at Pickup path `CHECKOUT_STARTED → SHIPPING_MODE_SELECTED` succeeds.
- Skipping is rejected: `CHECKOUT_STARTED → PAYMENT_SUCCESS`, `PAYMENT_PENDING → ESCROW_HELD`, `SHIPPING_MODE_SELECTED → DELIVERED` all throw `INVALID_STATE_TRANSITION` (validation rule "cannot skip states").
- A right target with the wrong trigger is rejected.
- `CANCEL` is accepted from the three listed states and rejected from `COMPLETED`.
- Regression: the post-Sprint-5 transitions in the skeleton are unchanged. A table-driven test asserts the full transition list.
- The removed old triggers (`PROCEED_PAYMENT`, `HOLD_ESCROW`, …) are rejected.

**Unit — `OrderTransitionServiceTest` (Mockito)**
- Order not found → `ERROR_ORDER_NOT_FOUND`, no history row, no event.
- Invalid trigger → exception, status unchanged, no history row, no event.
- Valid move → status saved, one history row with the right from, to, actor type, actor id and note, one event with buyer and seller ids.
- A note over 255 characters is trimmed. A null note is allowed. A `SYSTEM` actor has a null actor id.

**Unit — `OrderNumberGeneratorTest`**
- Uses a fixed `Clock`: the format is `VX-yyMMdd-NNNNNN`, the value is zero-padded, and the date uses IST near midnight UTC.

**Integration — `OrderLifecycleIntegrationTest` (Testcontainers)**
- The migration applies on a clean database and on top of the current `main` schema.
- Insert an order with its item and move it along the whole Sprint 5 path. The history rows have rising `changed_at`, and the timeline query returns them in order (validation rule "timestamps recorded").
- `chk_orders_total` rejects a wrong total. A second `order_items` row for the same order is rejected (one item per order). An unknown `status`, `delivery_mode` or `actor_type` is rejected.
- `order_number` is unique.
- Concurrency: two threads move the same order from `PAYMENT_PENDING`, one with `PAYMENT_CONFIRMED` and one with `PAYMENT_FAILED`. Exactly one wins, the other gets `INVALID_STATE_TRANSITION` after the lock, and there is exactly one history row for that step.
- `OrderStatusChangedEvent` is published once per committed move (captured with `@RecordApplicationEvents`), and none is published on rollback.

## 6. Validation Checklist

**Acceptance criteria**
- [ ] All 24 states exist in `OrderState` and the `status` CHECK.
- [ ] Every Sprint 5 state can be reached through `OrderTransitionService` along the C.3 path, including Pay at Pickup.
- [ ] States from Sprint 6 onwards remain reachable through the unchanged skeleton transitions.

**Business rules**
- [ ] One item per order is enforced by the database (`order_items.order_id UNIQUE`).
- [ ] Escrow until `COMPLETED`/`DISPUTE_RAISED`, auto-complete after 7 days, refund on `CANCELLED` and `SHIPMENT_LOST` investigation are recorded as handed to their stories (US-091, US-024, Sprint 7, G5). None are built here.

**Validation rules**
- [ ] Transitions are sequential and skipping is refused, except `CANCEL`.
- [ ] Every transition writes one insert-only history row with actor and timestamp (SLA).
- [ ] `OrderStatusChangedEvent` carries both buyer and seller ids, for the notifications built in US-023 (G3).

**Errors and edge cases**
- [ ] `ERROR_ORDER_NOT_FOUND` (404) is returned for an unknown order, with English and Hindi text.
- [ ] Invalid transitions raise `INVALID_STATE_TRANSITION` and leave no partial writes.
- [ ] Concurrent moves are safe (row lock plus `@Version`).
- [ ] Nothing reads or writes `orders.status` except `OrderTransitionService` (and US-021's insert).

**Process**
- [ ] Coverage above 90% for `com.valuex.order`. Checkstyle and Sonar are clean.
- [ ] LLD, Sprint plan and testing guide are updated.

## 7. Open Gaps / Questions

All gaps were resolved by the user on 2026-11-26: G1 confirmed, G2 to G8 agreed as proposed.

| # | Gap | Decision |
|---|---|---|
| G1 | **Order of the first two states.** The story lists `ORDER_INITIATED` then `SELLER_PRICE_ACCEPTED`, and so does the skeleton. LLD C.3 records `SELLER_PRICE_ACCEPTED` first (when the cart line is added) and `ORDER_INITIATED` at checkout. LLD C.3 also names no trigger for `SELLER_PRICE_ACCEPTED → ORDER_INITIATED`. | Follow LLD C.3, the newer design and the one US-021 will replay, and use `START_CHECKOUT` for both steps written at checkout. **Confirmed.** |
| G2 | **Deferred FK.** `orders.checkout_id` has no constraint until US-021 (decision 2026-11-26). Orders inserted before then (tests, manual seeding) may use any UUID. | US-021's migration adds `fk_orders_checkout`. It fails if orphan rows exist, so dev seed data must use real checkouts or be cleared. Note this in the US-021 plan. |
| G3 | **"Both parties notified at key states."** LLD 0.6 defines only buyer-side `ORDER_STATUS_CHANGED` (US-023) and `NEW_ORDER` for the seller (US-021). Which states are "key" for the seller is not defined. | US-090 publishes the event with both ids. US-023 builds the buyer listener. A product decision on seller notification states goes into the US-023 or US-112 plan. |
| G4 | **Cancelling after payment.** The skeleton's `CANCEL` only covers pre-payment states, which never live on an order row (D2). Buyer and seller cancellation of a paid order is Sprint 7 (US-058, US-059). | Keep it as is. Sprint 7 adds `CANCEL` from post-payment states together with the refund. |
| G5 | **`SHIPMENT_LOST` triggers investigation.** No LLD design exists. | Out of scope. Raise it for the Sprint 6 LLD (US-029 or US-032). |
| G6 | **Migration number clash.** US-016 holds `V44` on an unmerged branch. | Check both branches at branch time and take the next free number. If US-016 merges first, rebase and renumber. |
| G7 | **Order number details.** `VX-yyMMdd-NNNNNN` comes from an LLD comment only. The time zone and what happens past 999,999 orders are not stated. | Use IST, and let the number grow past six digits (the `VARCHAR(30)` column fits it). **Agreed.** |
| G8 | **History replay.** LLD C.3 replays checkout states into a new order's history. The writer belongs to US-021, but it must use the same state machine. | US-090 exposes the machine. US-021 validates each replayed step with `OrderStateMachine` before inserting rows, to keep "cannot skip states" true for replayed rows too. Note this in the US-021 plan. |

## 8. Implementation Notes (as built, 2026-11-26)

Built on `feature/US-090-order-lifecycle` (worktree `wt/US-090-backend`, so the uncommitted US-016 work stayed untouched). Migration `V45__orders.sql`. Deviations from the plan text, all recorded in LLD Part C "(as built)":

- **Target resolution:** `move` takes a trigger. A generic `StateMachine.resolveTarget(from, action)` was added to `common.statemachine`, and `Order.applyTrigger` uses it. `Order` has no status setter (CODING_STANDARDS 2.4 and 2.12: no `@Data` on entities, never set the status directly).
- **Extra schema:** `order_status_history.action` (the trigger, as in the listing history), `chk_orders_amounts`, `chk_order_items_price`, and indexes on `orders.checkout_id`, `order_items.listing_id` and `order_items.seller_id` (CODING_STANDARDS 2.7: every foreign key column has an index).
- **Timestamps:** `changed_at` comes from the `Clock` at microsecond precision, kept strictly after the previous change, so two moves in one transaction never tie.
- **Error text:** the backend has no message bundles, so the English and Hindi texts for `ERROR_ORDER_NOT_FOUND` move to the US-023 app work. The code and HTTP 404 are built here.
- **Enums reused:** `cart.domain.DeliveryMode` and `PaymentOption`.

**Forward notes:** the Sprint 6 LLD (Part A, US-112) calls the enum `OrderStatus`; the code name is `OrderState`. Self-pickup hand-over states are still for the product owner to add (Sprint 6 LLD open item 2), and are not part of this story.

---

**Status:** Approved (2026-11-26)
