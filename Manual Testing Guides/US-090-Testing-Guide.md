# US-090 — Lifecycle State - Order: QA Testing Guide

**Sprint 5 · Cart, Checkout & Payments**

Manual checks of the order tables, their database rules and the order state machine, using SQL against a local dev
database and the automated test suite.

> **What this story ships:** the `orders`, `order_items` and `order_status_history` tables (Flyway `V45__orders.sql`),
> the order state machine for the Sprint 5 states, and `OrderTransitionService`, the only code that changes an order's
> status. **There is no API and no app screen, and no order is created by the app yet.** Orders are created only after
> payment, by US-021 (checkout). The buyer's order screens are US-023 and US-070. See
> `Documents/LLD/Sprint-5-Cart-Checkout-Payments-LLD.md` Part C, and the **Not Testable Yet** section below before
> filing anything as a bug.

| Setting | Value |
|---|---|
| DB | PostgreSQL, `orders`, `order_items`, `order_status_history`, sequence `order_number_seq` |
| Migration | `V45__orders.sql` |
| Automated coverage | `OrderStateMachineTest`, `OrderTest`, `OrderTransitionServiceTest`, `OrderNumberGeneratorTest`, `OrderLifecycleIntegrationTest` |
| Run them | `mvn test "-Dtest=Order*Test,OrderLifecycleIntegrationTest"` (Docker must be running for the integration test; on this machine set `JAVA_TOOL_OPTIONS="-Dapi.version=1.44 -Duser.timezone=Asia/Kolkata"` first) |

---

## Test Scenarios Overview

| TC | Scenario | Expected Result |
|---|---|---|
| TC-001 | The backend starts on an existing dev database | Flyway applies V45; the app starts; nothing else changes |
| TC-002 | The three tables and their rules exist | Columns, CHECK constraints, unique keys and indexes as listed |
| TC-003 | One item per order | A second `order_items` row for the same order is rejected |
| TC-004 | Total must equal item plus shipping | An order with a wrong total is rejected |
| TC-005 | Only known statuses, delivery modes, payment options and actors | Unknown values are rejected |
| TC-006 | History is insert-only and in time order | Moves made by the automated test give rows with rising `changed_at` |
| TC-007 | The state machine allows only the designed moves | The automated tests pass in full: 74 tests |
| TC-008 | Regression: cart, delivery choice and listing flows | Unchanged (US-019, US-020 guides) |

---

## TC-001 — Migration Applies

1. Start the backend against your normal dev database (it already has V1 to V43, and V44 if the US-016 branch was run).
2. Check:
   ```sql
   SELECT version, description, success FROM flyway_schema_history WHERE version = '45';
   ```
   **Expect** one row, `orders`, `success = true`. The app log shows no Flyway error.

> If your dev database already has a V45 from another branch, Flyway refuses to start. Use a fresh database, or remove
> that branch's V45 row and its tables first.

## TC-002 — Tables and Rules

```sql
SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid IN ('orders'::regclass, 'order_items'::regclass, 'order_status_history'::regclass)
ORDER BY conname;
```
**Expect** among others: `chk_orders_total`, `chk_orders_amounts`, `chk_orders_delivery_mode`,
`chk_orders_payment_option`, `chk_orders_status` (24 states), `chk_osh_actor_type`, `chk_order_items_price`, the unique
keys on `orders.order_number` and `order_items.order_id`, and foreign keys to `users` and `listings`.
**There is no foreign key from `orders.checkout_id` yet**: US-021 adds it.

```sql
SELECT indexname FROM pg_indexes WHERE tablename IN ('orders', 'order_items', 'order_status_history') ORDER BY 1;
```
**Expect** `idx_order_buyer_created`, `idx_order_seller_status`, `idx_orders_checkout`, `idx_order_items_listing`,
`idx_order_items_seller` and `idx_osh_order`, besides the primary and unique keys.

## TC-003 to TC-005 — Database Rules

Use a test buyer, a test seller and one of the seller's listings (any status). Run each step in a transaction and roll
it back at the end so nothing stays behind:

```sql
BEGIN;
INSERT INTO orders (order_number, checkout_id, buyer_id, seller_id, delivery_mode, payment_option, status,
                    item_amount, shipping_amount, total_amount, seller_display_name)
VALUES ('VX-TEST-000001', gen_random_uuid(), '<buyer id>', '<seller id>', 'DELIVERY', 'PAY_NOW', 'PAYMENT_SUCCESS',
        1500.00, 80.00, 1580.00, 'Test seller')
RETURNING id;                                                         -- succeeds

INSERT INTO order_items (order_id, listing_id, seller_id, price, title)
VALUES ('<order id>', '<listing id>', '<seller id>', 1500.00, 'Chair'); -- succeeds
INSERT INTO order_items (order_id, listing_id, seller_id, price, title)
VALUES ('<order id>', '<listing id>', '<seller id>', 10.00, 'Second'); -- TC-003: fails, unique order_id
ROLLBACK;
```

| Step (in a new `BEGIN … ROLLBACK`) | Expected |
|---|---|
| Insert the order above with `total_amount = 999.00` | TC-004: fails, `chk_orders_total` |
| Insert with `status = 'SHIPPED'` | TC-005: fails, `chk_orders_status` |
| Insert with `delivery_mode = 'DRONE'` or `payment_option = 'CASH'` | TC-005: fails, the matching CHECK |
| Insert a history row with `actor_type = 'ROBOT'` | TC-005: fails, `chk_osh_actor_type` |

## TC-006 and TC-007 — Moves and History

Status moves have no endpoint (US-021 and later stories call `OrderTransitionService`), so they are checked by the
automated suite:

```
mvn test "-Dtest=Order*Test,OrderLifecycleIntegrationTest"
```
**Expect** 74 tests, 0 failures, 0 skipped (`OrderLifecycleIntegrationTest` is skipped only when Docker is not
running, so check that it actually ran). These tests cover:

- the full Sprint 5 path `SELLER_PRICE_ACCEPTED → ORDER_INITIATED → CHECKOUT_STARTED → PAYMENT_PENDING → PAYMENT_FAILED
  → PAYMENT_PENDING → PAYMENT_SUCCESS → ESCROW_HELD → SHIPPING_MODE_SELECTED`, with rising `changed_at` even for the
  two moves made in one transaction, and one `ORDER_STATUS_CHANGED` event per move
- Pay at Pickup: `CHECKOUT_STARTED → SHIPPING_MODE_SELECTED`
- skipped states (for example `CHECKOUT_STARTED → PAYMENT_SUCCESS`) and the removed Sprint 0 trigger names are
  refused with `INVALID_STATE_TRANSITION`, with no history row written
- an unknown order gives `ERROR_ORDER_NOT_FOUND`
- two payment results arriving at once: exactly one wins
- a failure after the move rolls back both the status and the history row
- order numbers look like `VX-261126-000123` and use the date in India

## TC-008 — Regression

Run the US-019 and US-020 guides' main paths (add to cart, choose delivery or pickup). **Expect** no change: US-090
does not touch the cart, the listing flow or any API.

---

## Not Testable Yet

| Item | Comes with |
|---|---|
| Creating a real order (pay for a cart) and its history replay | US-021 |
| The buyer's order details, timeline, status texts and notifications (English and Hindi) | US-023 |
| Order history list | US-070 |
| Escrow held until completed or disputed | US-091, US-024 |
| Auto-complete after 7 days | US-024 (Sprint 6) |
| Refund on cancellation; cancelling a paid order | Sprint 7 (US-058, US-059) |
| `SHIPMENT_LOST` investigation | Not designed yet (Sprint 6 LLD) |
| Seller Start Packing (`SHIPPING_MODE_SELECTED → SELLER_PACKING_PENDING`) | US-112 |
