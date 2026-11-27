# US-092 — Lifecycle State - Shipping: QA Testing Guide

**Sprint 6 · Shipping & Delivery**

Manual checks of the shipment tables, their database rules and the shipment state machine, using SQL against a local
dev database and the automated test suite.

> **What this story ships:** the `shipments` and `shipment_status_history` tables (Flyway `V46__shipments.sql`), the
> shipment state machine with the 18 states of the story, and `ShipmentTransitionService`, the only code that changes a
> shipment's status. Each shipment change also moves the order (for example "picked up" moves the order to
> `PICKED_UP`). **There is no API and no app screen.** Shipments are created with the order by US-021 (checkout);
> pickup scheduling is US-027, the courier integration US-122, and the tracking screen US-029. See
> `Documents/LLD/Sprint-6-Shipping-Delivery-LLD.md` Part B (B.7 for what was built), and the **Not Testable Yet**
> section below before filing anything as a bug.

| Setting | Value |
|---|---|
| DB | PostgreSQL, `shipments`, `shipment_status_history`; `order_status_history.chk_osh_actor_type` changed |
| Migration | `V46__shipments.sql` |
| Settings | `PICKUP_MAX_RESCHEDULES` (default 2), `DELIVERY_MAX_ATTEMPTS` (default 3) in `platform_settings` |
| Automated coverage | `ShipmentStateMachineTest`, `ShipmentTest`, `ShipmentTransitionServiceTest`, `ShipmentCreationAdapterTest`, `OrderFulfilmentAdapterTest`, `FulfilmentSettingTest`, `ShipmentLifecycleIntegrationTest` |
| Run them | `mvn test "-Dtest=Shipment*Test,OrderFulfilmentAdapterTest,FulfilmentSettingTest"` (Docker must be running for the integration test; on this machine set `JAVA_TOOL_OPTIONS="-Duser.timezone=Asia/Kolkata"` first) |

---

## Test Scenarios Overview

| TC | Scenario | Expected Result |
|---|---|---|
| TC-001 | The backend starts on an existing dev database | Flyway applies V46; every existing order gets one shipment row |
| TC-002 | The tables and their rules exist | Columns, CHECK constraints, unique keys, indexes and the history trigger as listed |
| TC-003 | Only known statuses, actors and non-negative counters | Unknown values are rejected |
| TC-004 | One shipment per order, one order per AWB | A second row is rejected |
| TC-005 | Shipment history is insert-only | `UPDATE` and `DELETE` are refused |
| TC-006 | The courier can be an actor on the order timeline | `LOGISTICS` is accepted in `order_status_history` |
| TC-007 | Moves, business rules and order sync | The automated tests pass in full: 133 tests |
| TC-008 | Regression: order lifecycle, cart and delivery choice | Unchanged |

---

## TC-001 — Migration Applies

1. Start the backend against your normal dev database (it already has V1 to V45).
2. Check:
   ```sql
   SELECT version, description, success FROM flyway_schema_history WHERE version = '46';
   ```
   **Expect** one row, `shipments`, `success = true`. The app log shows no Flyway error.
3. Check the back-fill:
   ```sql
   SELECT o.delivery_mode, s.status, COUNT(*)
   FROM orders o JOIN shipments s ON s.order_id = o.id
   GROUP BY 1, 2;
   SELECT COUNT(*) FROM orders o WHERE NOT EXISTS (SELECT 1 FROM shipments s WHERE s.order_id = o.id);
   ```
   **Expect** `DELIVERY` orders in `SHIPPING_REQUIRED`, `SELF_PICKUP` orders in `SHIPPING_NOT_REQUIRED`, and `0` orders
   without a shipment. (On a database with no orders both queries return nothing or `0`.)

> If your dev database already has a V46 from another branch, Flyway refuses to start. Use a fresh database, or remove
> that branch's V46 row and its tables first.

## TC-002 — Tables and Rules

```sql
SELECT conrelid::regclass, conname, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid IN ('shipments'::regclass, 'shipment_status_history'::regclass, 'order_status_history'::regclass)
ORDER BY 1, 2;
```
**Expect** among others: `chk_shipments_status` (the 18 states), `chk_shipments_counters`, the unique keys on
`shipments.order_id` and `shipments.awb`, foreign keys to `orders` and `addresses`, `chk_ssh_actor_type` (`BUYER`,
`SELLER`, `SYSTEM`, `ADMIN`, `LOGISTICS`), and `chk_osh_actor_type` now ending in `'GATEWAY', 'LOGISTICS'`.

```sql
SELECT indexname FROM pg_indexes WHERE tablename IN ('shipments', 'shipment_status_history') ORDER BY 1;
SELECT tgname FROM pg_trigger WHERE tgrelid = 'shipment_status_history'::regclass AND NOT tgisinternal;
```
**Expect** `idx_shipments_booking_due`, `idx_shipments_active` and `idx_ssh_shipment` besides the primary and unique
keys, and the trigger `trg_ssh_immutable`.

## TC-003 to TC-006 — Database Rules

Use any order that has a shipment (from TC-001, or insert one as in the US-090 guide TC-003). Run each step in a
transaction and roll it back at the end so nothing stays behind:

```sql
BEGIN;
-- TC-003: each of these fails with a check constraint error
UPDATE shipments SET status = 'TELEPORTED' WHERE order_id = '<order id>';
ROLLBACK; BEGIN;
UPDATE shipments SET delivery_attempts = -1 WHERE order_id = '<order id>';
ROLLBACK; BEGIN;
INSERT INTO shipment_status_history (shipment_id, to_status, action, actor_type, changed_at)
SELECT id, 'PICKED_UP', 'TEST', 'ROBOT', NOW() FROM shipments WHERE order_id = '<order id>';
ROLLBACK; BEGIN;
-- TC-004: fails with a unique violation
INSERT INTO shipments (order_id, status) VALUES ('<order id>', 'SHIPPING_REQUIRED');
ROLLBACK; BEGIN;
-- TC-005: the insert works; the update and the delete fail with "shipment_status_history is insert-only"
INSERT INTO shipment_status_history (shipment_id, to_status, action, actor_type, changed_at)
SELECT id, 'PICKUP_SLOT_SELECTED', 'TEST', 'SYSTEM', NOW() FROM shipments WHERE order_id = '<order id>';
UPDATE shipment_status_history SET note = 'changed' WHERE action = 'TEST';
ROLLBACK; BEGIN;
-- TC-006: succeeds
INSERT INTO order_status_history (order_id, from_status, to_status, action, actor_type)
VALUES ('<order id>', 'PICKUP_SCHEDULED', 'PICKED_UP', 'TEST', 'LOGISTICS');
ROLLBACK;
```

To check the unique AWB, set `awb = 'AWB-TEST'` on one shipment and then on another inside one transaction: the second
update fails. Roll back.

## TC-007 — Moves, Business Rules and Order Sync

Shipment moves have no endpoint (US-027, US-122 and later stories call `ShipmentTransitionService`), so they are checked
by the automated suite:

```
mvn test "-Dtest=Shipment*Test,OrderFulfilmentAdapterTest,FulfilmentSettingTest"
```
**Expect** 133 tests, 0 failures, 0 skipped (`ShipmentLifecycleIntegrationTest` is skipped only when Docker is not
running, so check that it actually ran). These tests cover:

- every allowed move of LLD B.3, all 18 states reachable, and every other move refused with `INVALID_STATE_TRANSITION`
  and nothing written; delivered, returned and self-pickup shipments have no way out
- the seller picks the pickup slot before the courier is booked: `SHIPPING_REQUIRED → PICKUP_SLOT_SELECTED →
  SHIPPING_PARTNER_SELECTION → PICKUP_SCHEDULED`
- **3 delivery attempts:** the third failed delivery moves the shipment and the order to `RETURN_TO_SELLER` at once,
  by the system; with `DELIVERY_MAX_ATTEMPTS = 1` the first failure does
- **2 pickup reschedules:** seller reschedules and reschedules after a failed pickup count together; the third is
  refused with `ERROR_MAX_PICKUP_RESCHEDULES`; with `PICKUP_MAX_RESCHEDULES = 0` the first is
- **lost shipment:** from any moving state it goes to `INVESTIGATION_OPENED`, the order to `SHIPMENT_LOST`, and one
  refund request event is published
- **tracking at each checkpoint:** one history row and one `SHIPMENT_STATUS_CHANGED` event (with buyer and seller ids)
  per move; when the courier skips scans (for example booked straight to delivered), the missing steps are written with
  the note `inferred`, the order moves step by step to `BUYER_PROOF_PENDING`, and the times keep their order
- an old or repeated courier event is ignored; a "delivered" scan after a failed attempt is applied
- the order is moved in the same transaction: if the order is not in the expected state, nothing is saved
- two courier events arriving at once: exactly one wins
- the service refuses to run outside a transaction

## TC-008 — Regression

Run the US-090 automated tests (`mvn test "-Dtest=Order*Test,OrderLifecycleIntegrationTest"`) and the US-019 and
US-020 guides' main paths (add to cart, choose delivery or pickup). **Expect** no change, apart from the order machine
now also allowing `REPORT_LOST` from `PICKED_UP`, `OUT_FOR_DELIVERY` and `DELIVERY_FAILED`.

---

## Not Testable Yet

| Item | Comes with |
|---|---|
| A shipment created when a real order is paid | US-021 |
| Choosing a pickup slot and booking the courier | US-027, US-122 |
| Courier events from Shiprocket (webhook, polling) | US-122 |
| Notifications and status texts for shipment changes (English and Hindi) | US-023, Sprint 6 Parts E to J |
| The tracking timeline and ETA on screen | US-029 |
| The refund after a lost shipment or a return to the seller | US-032 (needs escrow, US-091) |
| Delivery proof (photo or signature) | US-030 (buyer photos); partner proof to be checked with US-122 |
| GPS tracking in transit | Future (story) |
| Self-pickup "Mark as handed over" | US-112 revision |
