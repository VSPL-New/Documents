# US-092: Lifecycle State - Shipping — Implementation Plan

## 1. Header

| Field | Value |
|---|---|
| Story ID | US-092 |
| Title | Lifecycle State - Shipping |
| Sprint | Sprint 6 — Shipping & Delivery |
| Story Points | 3 |
| Repos | valuex-backend only |
| Dependency | US-023 in `Sprint-plan.md`, **not blocking** (LLD Part B header): the story needs only `orders` and `OrderTransitionService` from US-090 (built, merged). Tests insert orders directly, as US-090's did. Must come **before** US-122 (Shiprocket), US-027 (pickup), US-028, US-029, US-032, which all move shipments through this story's service |
| Branch | `feature/US-092-shipping-lifecycle` in `valuex-backend`, from `main` |

**Scope:** domain, persistence and the transition service only. No REST API, no partner calls, no notification texts, no refund money movement (owners listed in §3).

## 2. Story Recap

**As a** platform **I want** to track shipping lifecycle states **so that** delivery is monitored end-to-end.

**Acceptance Criteria** (`user-stories.md`): given an order requires shipping, shipping progresses through `SHIPPING_NOT_REQUIRED` (self-pickup), `SHIPPING_REQUIRED` (delivery), `SHIPPING_PARTNER_SELECTION`, `PICKUP_SLOT_SELECTED`, `PICKUP_SCHEDULED`, `PICKUP_ASSIGNED`, `PICKED_UP`, `IN_TRANSIT`, `OUT_FOR_DELIVERY`, `DELIVERED`, `PICKUP_FAILED`, `PICKUP_RESCHEDULED`, `DELIVERY_FAILED`, `DELIVERY_RESCHEDULED`, `RETURN_TO_SELLER`, `SHIPMENT_DELAYED`, `SHIPMENT_LOST`, `INVESTIGATION_OPENED`.

**Business Rules:** max 3 delivery attempts before `RETURN_TO_SELLER` · `SHIPMENT_LOST` triggers refund process · `PICKUP_FAILED` allows 2 reschedules · tracking updated at each checkpoint.

**Validation Rules:** state transitions trigger notifications · GPS tracking for `IN_TRANSIT` (future) · ETA calculated dynamically · delivery proof (photo/signature) required.

**Error Scenarios:** none in the story. From the LLD: `ERROR_MAX_PICKUP_RESCHEDULES` (409, "Pickup can be rescheduled only twice. Contact support", LLD 0.4), the existing `INVALID_STATE_TRANSITION` and `ERROR_ORDER_NOT_FOUND`.

## 3. Design Reference

Primary source: [Sprint-6-Shipping-Delivery-LLD.md — Part B](../LLD/Sprint-6-Shipping-Delivery-LLD.md#part-b---us-092-lifecycle-state---shipping) (B.1 to B.6). Also read: 0.1 (module ownership, ports), 0.2 (order vs shipment state), 0.3 (`PICKUP_MAX_RESCHEDULES`, `DELIVERY_MAX_ATTEMPTS`), 0.4 (error codes), 0.5 (events), 0.6 decisions S1, S2, S8, S9.

**What already exists on `main`:**
- `shipping.domain.ShippingState`: all 18 states with display names. Kept as is.
- `shipping.domain.ShippingStateMachine`: a Sprint 0 skeleton. Nothing calls it. It is replaced by `ShipmentStateMachine` (B.3), as US-090 replaced the order skeleton.
- `order.application.service.OrderTransitionService.move(orderId, trigger, OrderActor, note)`, `@Transactional`, locks the order, writes history, publishes `OrderStatusChangedEvent`. The pattern to copy for shipments.
- `order.domain.OrderStateMachine` already has every order trigger in the B.4 mapping except the new `REPORT_LOST` sources.
- `order.domain.OrderActorType` = `BUYER, SELLER, SYSTEM, ADMIN, GATEWAY`; `chk_osh_actor_type` in `V45__orders.sql` matches.
- `forbid_ledger_change()` does **not** exist yet (US-091 not built) — see G1.
- Settings registries follow `plans.domain.CheckoutSetting` / `CheckoutSettings` over `platform_settings`.
- Cross-module port pattern: the port lives in the calling module, the adapter in the owning module (`shipping/application/port/DeliveryEligibilityPort` ← `listing/infrastructure/shipping/DeliveryEligibilityAdapter`).
- Latest migration on `main` and on the open US-016 branch is `V45`, so this story takes `V46` (re-check when the branch is cut).

**Key design decisions (LLD Part B):**
- **One shipment per order (S1).** `shipments.order_id UNIQUE`. Delivery orders start `SHIPPING_REQUIRED`, self-pickup orders `SHIPPING_NOT_REQUIRED` (terminal). The migration back-fills a row for every existing order.
- **`ShipmentTransitionService` is the only writer of `shipments.status`.** `move` (one trigger) and `advanceTo` (shortest forward path, missing steps written with note `inferred`, older targets ignored — S8). Both run inside the caller's transaction (`Propagation.MANDATORY`).
- **Lock order:** shipment row `FOR UPDATE` first, then the order row (inside `OrderTransitionService.move`), always, to avoid deadlocks.
- **The shipment drives the order** through `OrderFulfilmentPort` → `OrderTransitionService.move`, in the same transaction, per the B.4 mapping table. Partner-driven moves use the new actor `LOGISTICS`.
- **Slot before partner (S2):** `SHIPPING_REQUIRED → PICKUP_SLOT_SELECTED → SHIPPING_PARTNER_SELECTION → PICKUP_SCHEDULED`.
- **Counters:** `pickup_reschedules` (+1 on every `RESCHEDULE_PICKUP`, seller or automatic; refused at `PICKUP_MAX_RESCHEDULES`), `delivery_attempts` (+1 on every `FAIL_DELIVERY`; at `DELIVERY_MAX_ATTEMPTS` `RETURN` is applied in the same call).
- **Lost:** `REPORT_LOST` publishes `ShipmentRefundRequestedEvent(reason=LOST)` after commit, and `OPEN_INVESTIGATION` follows immediately in the same call.
- **History is insert-only** (`@Immutable` entity plus a DB trigger) with `actor_type` incl. `LOGISTICS`, `note`, `location`, `changed_at` (partner event time for `LOGISTICS` rows).

**Out of scope (owner):** partner adapters, webhook, polling and RTO request to the partner (US-122 / Part C, H.4); pickup scheduling API (US-027); notification listeners and texts (Parts E–J, US-023); the refund itself (`EscrowRefundService`, US-032 / H.5); support escalation at the reschedule limit (F.3); GPS (future); cancellation (Sprint 7, LLD G12); `HANDED_OVER` order trigger (S10, built with the US-112 revision — G6).

## 4. Implementation Steps

### 0. Workflow (CLAUDE.md §5)
- [x] `valuex-backend` main checkout is on a Dependabot branch and `wt/US-016-backend` holds US-016 (PR #82). Leave both alone: create a new worktree `wt/US-092-backend` from an up-to-date `origin/main` on branch `feature/US-092-shipping-lifecycle`.

### 1. Database Migration — `V46__shipments.sql`
- [x] `CREATE OR REPLACE FUNCTION forbid_ledger_change()` (raises an exception on UPDATE/DELETE) — G1.
- [x] `shipments` exactly as LLD B.2 (all columns, `chk_shipments_status` with the 18 names, `chk_shipments_counters`, `awb UNIQUE`, `idx_shipments_booking_due`, `idx_shipments_active`). `pickup_location_id` without FK (Part C adds it).
- [x] `shipment_status_history` with `chk_ssh_actor_type`, `idx_ssh_shipment`, and `trg_ssh_immutable`.
- [x] Replace `chk_osh_actor_type` on `order_status_history` to add `LOGISTICS`.
- [x] Back-fill: `INSERT INTO shipments (order_id, status) SELECT id, CASE delivery_mode WHEN 'DELIVERY' THEN 'SHIPPING_REQUIRED' ELSE 'SHIPPING_NOT_REQUIRED' END FROM orders WHERE NOT EXISTS (...)`.

### 2. Domain — `com.valuex.shipping.domain`
- [x] Delete `ShippingStateMachine`; add `ShipmentStateMachine extends StateMachine<ShippingState>` (`@Component`) with the B.3 table and public trigger constants (`SELECT_SLOT`, `START_BOOKING`, `BOOKED`, `BOOKING_FAILED`, `ASSIGN`, `CONFIRM_PICKUP`, `FAIL_PICKUP`, `RESCHEDULE_PICKUP`, `IN_TRANSIT`, `DELAY`, `RESUME`, `OUT_FOR_DELIVERY`, `DELIVER`, `FAIL_DELIVERY`, `RESCHEDULE_DELIVERY`, `RETRY_DELIVERY`, `RETURN`, `REPORT_LOST`, `OPEN_INVESTIGATION`, `FOUND`), plus the forward-trigger set used by `advanceTo`.
- [x] `Shipment` entity: `@Version`, `status` as `@Enumerated(STRING) ShippingState`, no status setter; `applyTrigger(machine, trigger, changedAt)` updates status and the timestamps/counters (`picked_up_at`, `delivered_at`, `rto_initiated_at`, `last_event_at`, `pickup_reschedules`, `delivery_attempts`); `pickup_address` JSONB via the existing `AddressSnapshot` mapping. Factory methods `forDelivery(...)` and `notRequired(orderId)`.
- [x] `ShipmentStatusHistory` (`@Immutable`, builder, no setters).
- [x] `ShipmentActorType` (`BUYER, SELLER, SYSTEM, ADMIN, LOGISTICS`) and `ShipmentActor` record with `system()` / `logistics()` helpers (G5).
- [x] `ShipmentEventContext` record (`note`, `location`, `occurredAt`, `eta`) — G5.
- [x] `ShipmentStatusChangedEvent` (fields per B.4) and `ShipmentRefundRequestedEvent(shipmentId, orderId, reason)` with `RefundReason.LOST` (`RTO` added by US-032).
- [x] `ShipmentErrors`: `SHIPMENT_NOT_FOUND` (internal, G7), `MAX_PICKUP_RESCHEDULES = "ERROR_MAX_PICKUP_RESCHEDULES"`.

### 3. Domain — `com.valuex.order.domain` (small changes)
- [x] `OrderActorType`: add `LOGISTICS`.
- [x] `OrderStateMachine`: add `REPORT_LOST` from `PICKED_UP`, `OUT_FOR_DELIVERY`, `DELIVERY_FAILED` (B.4). Nothing else.

### 4. Settings — `com.valuex.plans.domain`
- [x] `FulfilmentSetting` / `FulfilmentSettings` following `CheckoutSetting`, with only the two keys US-092 reads: `PICKUP_MAX_RESCHEDULES` (2, 0–5) and `DELIVERY_MAX_ATTEMPTS` (3, 1–5). Later stories add their keys (G2).

### 5. Persistence — `com.valuex.shipping.infrastructure.persistence`
- [x] `ShipmentRepository`: `findByIdForUpdate`, `findByOrderId`.
- [x] `ShipmentStatusHistoryRepository`: `findByShipmentIdOrderByChangedAtAscIdAsc`.

### 6. Ports and adapters
- [x] `shipping.application.port.OrderFulfilmentPort.move(orderId, trigger, ShipmentActor, note)` ← `order.infrastructure.shipping.OrderFulfilmentAdapter` mapping `ShipmentActor` to `OrderActor` and calling `OrderTransitionService.move`.
- [x] `order.application.port.ShipmentCreationPort.createFor(ShipmentCreationRequest)` (order id, delivery mode, quoted cost, eta, declared value, package) ← `shipping.infrastructure.order.ShipmentCreationAdapter`. No caller until US-021 (B.5); unit and integration tests call it directly.

### 7. Application — `com.valuex.shipping.application.service.ShipmentTransitionService`
- [x] `move(shipmentId, trigger, actor, ctx)`, `@Transactional(propagation = MANDATORY)`:
  1. Lock the shipment (`findByIdForUpdate`) or throw `NotFoundException`.
  2. For `RESCHEDULE_PICKUP`: refuse with `ConflictException(ERROR_MAX_PICKUP_RESCHEDULES)` when `pickup_reschedules >= PICKUP_MAX_RESCHEDULES`.
  3. `applyTrigger` (machine refuses invalid pairs with `INVALID_STATE_TRANSITION`); `changed_at` = `ctx.occurredAt` for `LOGISTICS`, else the clock kept strictly after the previous change (same rule as `OrderTransitionService.nextChangeTime`).
  4. Insert the history row; fire the mapped order trigger(s) through `OrderFulfilmentPort` (B.4 table, incl. `CONFIRM_DELIVERY` then `REQUEST_BUYER_PROOF`, and `REDELIVER` vs `OUT_FOR_DELIVERY` by previous state); publish `ShipmentStatusChangedEvent`.
  5. Follow-ups in the same call: `FAIL_DELIVERY` reaching `DELIVERY_MAX_ATTEMPTS` → `RETURN`; `REPORT_LOST` → publish `ShipmentRefundRequestedEvent(LOST)`, then `OPEN_INVESTIGATION`.
- [x] `advanceTo(shipmentId, target, actor, ctx)`: BFS over forward triggers only; returns `false` (no writes) when the target is unreachable forward (older/repeated event); otherwise applies each step through the same internal path, inferred steps with note `inferred` and the same event time.
- [x] Keep the B.4 mapping as one table-like private structure (e.g. `ShipmentOrderMapping`), not scattered `if`s.

### 8. Error catalogue
- [x] `ERROR_MAX_PICKUP_RESCHEDULES` in the error-code catalogue and message bundles (English and Hindi), like `ERROR_ORDER_NOT_FOUND` in US-090.

### 9. Documentation (CLAUDE.md §5.10)
- [x] LLD Part B: record any deviation (G1, G2, G5, G6, port placement) as built.
- [x] Sprint-5 LLD E.5 / US-021 plan: hand-off — `OrderCreationService.createForLine` must call `ShipmentCreationPort.createFor`.
- [x] `Sprint-plan.md`: link this plan from the US-092 row; mark built when done.
- [x] `Manual Testing Guides/US-092-Testing-Guide.md`: SQL-level checks (migration, back-fill, constraints, immutability) and how to run the test subset.

### 10. Quality gates (CLAUDE.md §5.7, §5.8)
- [ ] `mvn clean verify`, checkstyle, JaCoCo, then the SonarQube scan; fix every issue before pushing.

## 5. Test Plan

Target above 90% line and branch coverage for `com.valuex.shipping` and the changed `order` classes. Integration tests use Testcontainers PostgreSQL (see the local Docker workaround in project memory).

**Unit — `ShipmentStateMachineTest`**
- Parameterized: every B.3 row is allowed (AC: all 18 states reachable).
- Every other (state, trigger) pair is refused with `INVALID_STATE_TRANSITION`; `resolveTarget` is unique per pair.
- `SHIPPING_NOT_REQUIRED` and `DELIVERED` have no outgoing triggers; `RETURN_TO_SELLER` has none.
- Skeleton regressions: `SELECT_PARTNER`, `SCHEDULE`, `REASSIGN` no longer exist; `PICKUP_RESCHEDULED → PICKUP_SCHEDULED` via `BOOKED`.

**Unit — `ShipmentTransitionServiceTest` (Mockito)**
- Not found → exception, no writes. Invalid trigger → no history, no order move, no event.
- Valid move → one history row (from, to, action, actor, note, location, changed_at) and one `ShipmentStatusChangedEvent`.
- Order mapping: one test per B.4 row, including "no order trigger" rows (`PICKUP_ASSIGNED`, `PICKUP_FAILED`, `SHIPMENT_DELAYED`, `RESUME`, `DELIVERY_RESCHEDULED`, `FOUND`), `REDELIVER` after a failed attempt, and `DELIVER` → two order triggers.
- Pickup reschedule: 1st and 2nd allowed (seller and system each count), 3rd refused with `ERROR_MAX_PICKUP_RESCHEDULES`, counter unchanged (BR "2 reschedules").
- Delivery attempts: 1st and 2nd `FAIL_DELIVERY` stay `DELIVERY_FAILED`; 3rd ends in `RETURN_TO_SELLER` with two history rows and order `RETURN_TO_SELLER` (BR "max 3 attempts").
- Lost: `REPORT_LOST` from each of the six source states → `INVESTIGATION_OPENED`, refund event published once, order `SHIPMENT_LOST` (BR "lost triggers refund").
- `advanceTo`: `PICKUP_SCHEDULED → DELIVERED` writes `PICKED_UP`, `IN_TRANSIT`, `OUT_FOR_DELIVERY`, `DELIVERED` with note `inferred` on the gaps and moves the order step by step; a target behind the current state returns `false` with no writes; `advanceTo` never enters an exception state.
- `LOGISTICS` rows use the partner time; `SYSTEM` rows are strictly increasing on the same timestamp; timestamps/`eta`/`last_event_at` set.
- Settings read through `FulfilmentSettings` (values changed in the test take effect).

**Unit — `OrderStateMachineTest`, `OrderFulfilmentAdapterTest`, `ShipmentCreationAdapterTest`, `FulfilmentSettingTest`**
- New `REPORT_LOST` sources allowed; full previous transition list unchanged.
- Actor mapping `LOGISTICS` → `OrderActorType.LOGISTICS`, ids carried.
- Delivery → `SHIPPING_REQUIRED` with quoted cost, eta, declared value; self-pickup → `SHIPPING_NOT_REQUIRED`; a second shipment for the same order is refused.
- Defaults and ranges of the two keys.

**Integration — `ShipmentLifecycleIntegrationTest` (Testcontainers)**
- Migration applies on a clean DB and on the `V45` schema with existing orders; back-fill creates one correct row per order.
- Constraints: unknown status / actor type rejected; negative counters rejected; second shipment per order rejected; duplicate `awb` rejected; `LOGISTICS` accepted in `order_status_history`.
- `UPDATE` and `DELETE` on `shipment_status_history` are refused by the trigger.
- Happy path end to end: order at `SELLER_PROOF_UPLOADED` + shipment `SHIPPING_REQUIRED` → … → `DELIVERED`; order ends `BUYER_PROOF_PENDING`; timeline query returns rows in order (BR "tracking updated at each checkpoint").
- Rollback: a shipment move whose order move is invalid rolls back both (G4); no events published.
- Concurrency: two threads apply `DELIVER` and `FAIL_DELIVERY` to the same `OUT_FOR_DELIVERY` shipment; exactly one wins, the other gets `INVALID_STATE_TRANSITION`, no deadlock, one history row per step.
- Events published once per committed move (`@RecordApplicationEvents`), none on rollback.

## 6. Validation Checklist

**Acceptance criteria**
- [ ] All 18 states exist in `ShippingState` and `chk_shipments_status`.
- [ ] Every state is reachable through `ShipmentTransitionService` along the B.3 table.
- [ ] Self-pickup orders get `SHIPPING_NOT_REQUIRED`, delivery orders `SHIPPING_REQUIRED` (creation port and back-fill).

**Business rules**
- [ ] 3rd failed delivery → `RETURN_TO_SELLER` automatically.
- [ ] `SHIPMENT_LOST` publishes the refund request and opens the investigation (refund itself handed to US-032, G3).
- [ ] 3rd pickup reschedule refused with `ERROR_MAX_PICKUP_RESCHEDULES`.
- [ ] Every checkpoint writes one insert-only history row.

**Validation rules**
- [ ] Every move publishes `ShipmentStatusChangedEvent` (notification listeners handed to later parts, G4 in §7).
- [ ] GPS not built (future) — recorded.
- [ ] `eta` column set from context; dynamic ETA handed to US-122/US-029.
- [ ] Delivery proof handed to Part I / LLD G9.

**Errors and edge cases**
- [ ] Invalid transitions leave no partial writes (shipment and order roll back together).
- [ ] Old/repeated partner events are ignored by `advanceTo`.
- [ ] Lock order shipment → order; concurrent moves safe (lock + `@Version`).
- [ ] Nothing writes `shipments.status` except `ShipmentTransitionService` (and the creation adapter's insert).

**Process**
- [ ] Coverage above 90%; checkstyle and Sonar clean.
- [ ] LLD, Sprint-plan, testing guide updated; US-021 hand-off recorded.

## 7. Open Gaps / Questions

All gaps were resolved by the user on 2026-11-27: G1 to G9 agreed as proposed.

| # | Gap | Decision |
|---|---|---|
| G1 | **`forbid_ledger_change()` does not exist** — LLD B.2 assumes US-091 created it; US-091 is not built. | Create it in `V46` with `CREATE OR REPLACE FUNCTION`; US-091's migration must also use `CREATE OR REPLACE` (note in the US-091 plan). |
| G2 | **`FulfilmentSetting` registry** (LLD 0.3) has 15 keys; US-092 reads only two. | Create the registry with `PICKUP_MAX_RESCHEDULES` and `DELIVERY_MAX_ATTEMPTS` only; each later story adds its own keys (no speculative settings). |
| G3 | **"SHIPMENT_LOST triggers refund"** — `EscrowRefundService` (US-032, H.5) and escrow (US-091) are not built. | US-092 publishes `ShipmentRefundRequestedEvent(LOST)` with no listener; the rule is complete only when US-032 lands. Record it in Sprint-plan as a hand-off. |
| G4 | **Order not in the expected state** (e.g. booking completes while the order is still `SELLER_PACKING_PENDING`, because US-026 is not built). | Fail the whole transaction with `INVALID_STATE_TRANSITION` (shipment and order stay consistent). Tests insert orders in the matching state. |
| G5 | **`ShipmentActor` and `ShipmentEventContext`** are named in LLD B.4 but not defined. | `ShipmentActor(ShipmentActorType type, UUID id)` in `shipping.domain` (no dependency on `order.domain`); `ShipmentEventContext(note, location, occurredAt, eta)`. Mapped to `OrderActor` in the adapter. |
| G6 | **`HANDED_OVER` order trigger** (S10) is listed in B.4 but belongs to the self-pickup hand-over action (US-112 revision, Part A). | Not in US-092; add it with US-112's `mark-handed-over`. |
| G7 | **Shipment not found** has no user-facing error code (no API in this story). | Internal `NotFoundException("SHIPMENT_NOT_FOUND")`; Part C/E add user codes if needed. |
| G8 | **Port placement:** LLD B.5 names `ShipmentCreationPort` without a module. | Follow the existing pattern: port in the caller (`order.application.port`), adapter in `shipping.infrastructure.order`. |
| G9 | **Story's "PICKUP_FAILED allows 2 reschedules" vs LLD** counting seller reschedules and failed-pickup reschedules together. | Follow LLD 0.3/B.3.1 (combined counter). **Agreed.** |

## 8. Implementation Notes (as built, 2026-11-27)

Branch `feature/US-092-shipping-lifecycle` in `valuex-backend`. All steps of §4 are done; the LLD records the differences in [Part B.7](../LLD/Sprint-6-Shipping-Delivery-LLD.md#b7-as-built-us-092-2026-11-27).

**Deviations from this plan:**
- **`advanceTo` forward triggers** include `RESUME` and `RETRY_DELIVERY` besides the LLD's five (user decision 2026-11-27). Without them a "delivered" scan after a failed attempt, or a transit scan after a delay, would be ignored as old and the order would never reach `DELIVERED`.
- **Inferred-step times** are 1 microsecond apart instead of identical, so the timeline order does not depend on row ids. A late courier event is placed 1 microsecond after the last change.
- **`ShipmentCreationRequest`** has no package size, and `partner` is left empty: the listing has no packed weight or size and there is no provider property until US-122.
- **`OrderFulfilmentPort.parties(orderId)`** was added so the shipment events carry the buyer and seller ids (LLD B.4 event fields).
- **`PlatformSettingsService`:** the repeated invalid-setting log text and metric name became constants, because adding a fifth registry made Sonar flag the duplicates.

**Hand-offs (open, owned by other stories):**
- US-021: `OrderCreationService.createForLine` must call `ShipmentCreationPort.createFor` (Sprint 5 LLD E.5 note).
- US-032: listener for `ShipmentRefundRequestedEvent` (`EscrowRefundService`); until then the "lost triggers refund" rule stops at the event (G3).
- US-112 revision: `HANDED_OVER` order trigger (G6).
- US-023 and Parts E to J: notification listeners for `ShipmentStatusChangedEvent`.
- US-091: its ledger migration must use `CREATE OR REPLACE FUNCTION forbid_ledger_change()` (G1).

**Closed:** US-090 plan gap G5 (lost shipment opens an investigation).

---

**Status:** Approved (2026-11-27)
