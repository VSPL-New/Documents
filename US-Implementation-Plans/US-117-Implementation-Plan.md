# US-117: Payment Gateway Integration — Implementation Plan

## 1. Header

| Field | Value |
|---|---|
| Story ID | US-117 |
| Title | Payment Gateway Integration |
| Sprint | Sprint 2 — Seller Listing Creation |
| Story Points | 5 (proposed) |
| Repos | valuex-backend, valuex-mobile |
| Dependency | S0-001 (backend skeleton). Built **before** US-008, which is its first user; no other Sprint 2 story is needed first |

**Scope decisions (2026-10-16):**
1. The payment gateway is **not decided**. This story is gateway-neutral: a payment port, a mock adapter, the callback and refund handling, reconciliation and the app checkout wrapper. No gateway name, SDK, key or signature format appears in the shared code. The real adapter (and the app's gateway checkout implementation) is a small follow-up when the gateway is chosen.
   **Update (2026-10-30, decided): the dummy gateway is the only adapter delivered now.** Talks with a payment gateway provider are still in progress, so this story ships a **dummy gateway** (the `mock` provider below) that behaves like a real one end to end: orders, a test checkout where the tester chooses Pay, Fail or Cancel, a signed callback through the same endpoint a real gateway will use, reconciliation and refunds. No money moves and no real gateway account is needed. Everything else in the story is built for real, so switching to a real gateway later is one adapter plus the app's checkout implementation, with no change in US-008, US-009 or any feature.
2. The first user is the listing plan payment (US-008, US-009). Buyer payments and escrow (US-021, US-022, US-075), refunds for returns (US-035), and subscriptions (US-038, US-042) use the same service later.
3. Amounts are always decided by the server. The app never sends or changes an amount, and never marks a payment successful.
4. This story builds the refund call and the refund tracking. It does **not** decide when a refund is issued: US-009 only flags `REFUND_REVIEW`, and whether a refund is automatic or manual stays an open product decision.
5. Seller payouts (US-072) and escrow release (US-024) are out of scope.

## 2. Story Recap

**As a** platform **I want** one payment integration that creates payment orders, takes the payment in the app, confirms it from the gateway's signed callback, refunds, and reconciles **so that** all payments use one tested integration and the gateway can be chosen or changed by configuration.

**Acceptance Criteria** (`Documents/user-stories.md`):
- A feature asks for a payment: a payment is created in `PAYMENT_INITIATED` with a gateway order, and the app gets what its checkout needs (order ID, amount, currency, public key).
- The app reports only what the user did (completed, cancelled, failed); it never marks a payment successful.
- The gateway's signed callback is verified (signature and amount) and settles the payment; repeated or late callbacks change nothing; the callback is always acknowledged.
- A scheduled check settles payments still pending when no callback arrives.
- A captured payment can be refunded (full or partial); the refund is tracked through the refund states.
- Without a configured gateway the mock adapter is used and no money moves; real keys come from the environment and are never stored in code or logs.

**Edge Cases:** callback before the app returns · success reported but no callback · amount mismatch · duplicate or replayed callbacks · gateway timeout or outage on create · app closed during payment · gateway order expires unpaid · partial refund, refund failure, duplicate refund callback · two payments for one reference at once.

**Validation Rules:** server-decided amounts (rupees, 2 decimals; smallest unit to the gateway) · constant-time signature check before any processing · no card, UPI or bank details in ValueX servers or logs · secrets from environment · payment records and attempts never deleted, kept 7 years · states follow US-091 · provider chosen by configuration, mock only in the `dev` and `test` profiles (decided 2026-10-30).

**Error Scenarios:** `ERROR_GATEWAY_UNAVAILABLE` · `ERROR_PAYMENT_FAILED` · `ERROR_PAYMENT_TIMEOUT` · `ERROR_DUPLICATE_PAYMENT` (absorbed) · `ERROR_REFUND_FAILED`.

## 3. Design Reference

- Primary source: [Sprint-2-Seller Listing Creation-LLD.md — Part H](../LLD/Sprint-2-Seller%20Listing%20Creation-LLD.md#part-h---us-008-seller-chooses-listing-plan) §H.3 (tables) and [Part I](../LLD/Sprint-2-Seller%20Listing%20Creation-LLD.md#part-i---us-009-listing-publication-after-payment) §I.3–I.4 (callback), read with the 2026-10-16 gateway-neutral notes. HLD Part 7 §10 (Payment APIs) and §21 (gateway integration). The LLD's `razorpay*` names are read as the neutral names below.
- Design reference for the app: there is no Figma screen for the gateway's own checkout (the gateway draws it). The mock checkout is a developer-only bottom sheet using the existing design system, shown when the app is configured for the dummy gateway (Open Gap 9).

**What already exists in the code:**
- `payment` module with only `PaymentState` and `PaymentStateMachine` (`PAYMENT_INITIATED → PAYMENT_PENDING → PAYMENT_SUCCESS / PAYMENT_FAILED`, escrow, `REFUND_REVIEW → REFUND_APPROVED → REFUND_PROCESSED`). There is **no** `PAYMENT_SUCCESS → REFUND_REVIEW` transition and no way back from `PAYMENT_FAILED` to success.
- Provider-adapter pattern with `@ConditionalOnProperty` (`OtpProviderConfig`, `AddressProviderConfig`), `ValuexProperties`, `DomainEventPublisher`, `BusinessException`, `NotFoundException`, `GlobalExceptionHandler`, `ApiResponse`.
- `SecurityConfig` with a `permitAll` list (the callback route is added there) and `/api/v1/admin/**` for admin roles.
- `@EnableScheduling` and Redis are in place; scheduled jobs exist (`SuspendedAccountAutoLiftJob`).
- Mobile: `ScreenProtectionService` (its comment already names payment screens), `ApiClient`, feature folders with `data/domain/presentation`, Riverpod.

**Key design decisions:**
- **Port.** `PaymentGatewayPort` has four operations: `createOrder`, `fetchOrderStatus`, `refund`, `parseCallback` (verifies the signature and returns a neutral `GatewayEvent`). Adapters own everything provider-specific: request format, signature header, event names. The generic callback endpoint passes the raw body and headers to `parseCallback`.
- **Neutral event.** `GatewayEvent` has `eventId`, `type` (`PAYMENT_CAPTURED`, `PAYMENT_FAILED`, `REFUND_PROCESSED`, `REFUND_FAILED`), `gatewayOrderId`, `gatewayPaymentId`, `gatewayRefundId`, `amountMinor`, `failureReason`.
- **One service for features.** `PaymentService.createOrReuse(command)` (in process, never an HTTP endpoint, because the amount must come from the server) and `PaymentService.supersedeOpenPayment(referenceType, referenceId)` (used by US-008 when the seller changes plan).
- **Results leave as events.** `PaymentSucceededEvent` and `PaymentFailedEvent` carry `paymentId`, `referenceType`, `referenceId`, `amount`, and for failures a `reason` (`FAILED`, `EXPIRED`, `SUPERSEDED`); the success event carries `late` (true when the payment was captured after it had been failed or expired). Features listen with `@TransactionalEventListener(AFTER_COMMIT)`; this story never calls a feature.
- **Idempotency.** Every callback is stored in `payment_gateway_events` with a unique `gateway_event_id`; a duplicate is acknowledged and ignored. `gateway_payment_id` is unique on `payments`. Settling uses optimistic locking and the state machine, so a callback and a reconciliation run cannot both settle one payment.
- **One open payment per reference.** A partial unique index allows only one `PAYMENT_INITIATED`/`PAYMENT_PENDING` payment for a (reference type, reference ID).
- **Orders are not cancelled at the gateway** (decided here): `supersedeOpenPayment` fails the payment locally with reason `SUPERSEDED` and lets the gateway order expire. If the user pays that old order anyway, the callback takes the late-success path below.
- **Late success (money taken for a failed, expired or superseded payment).** `PAYMENT_FAILED → PAYMENT_SUCCESS` is added with action `LATE_SUCCESS`; the success event has `late = true` and the feature decides (see Open Gaps and the US-009 plan). Money is never silently kept.
- **Reconciliation** is a scheduled job, plus an immediate status fetch when the app reports checkout completed.
- **Mock adapter** keeps orders in the database only (no network). It signs its own callbacks with a mock secret, and a developer-only simulate endpoint pushes a mock callback through the **same** callback service the real gateway uses, so the real path is exercised in development and tests.
- **Production safety.** The dummy (`mock`) provider is allowed only in the `dev` profile (and `test` for automated tests). Any other profile, `prod` included, refuses to start with `valuex.payment.provider=mock`, and the simulate endpoint exists only with the mock provider.

## 4. Implementation Steps

### Database Migration — `valuex-backend`
- [ ] `V19__payments.sql` (US-007 took `V18`; renumber to the next free version at implementation time):
  - `payments`: `id`, `reference_type` (`LISTING_PLAN` now; `ORDER`, `SUBSCRIPTION` later), `reference_id`, `payer_user_id`, `amount NUMERIC(12,2)`, `currency` (default `INR`), `status` (existing `PaymentState` names, default `PAYMENT_INITIATED`), `gateway_provider`, `gateway_order_id`, `gateway_payment_id`, `failure_reason`, `expires_at`, `version` (optimistic lock), `created_at`, `updated_at`. Indexes: `(reference_type, reference_id)`; unique `gateway_order_id` where not null; unique `gateway_payment_id` where not null; **unique open payment** on `(reference_type, reference_id)` where `status IN ('PAYMENT_INITIATED','PAYMENT_PENDING')`; `(status, created_at)` for the reconciliation job.
  - `payment_attempts`: `id`, `payment_id`, `kind` (`CREATE_ORDER`, `CHECKOUT_RESULT`, `CALLBACK`, `STATUS_FETCH`), `status`, `gateway_transaction_id`, `failure_reason`, `attempted_at`.
  - `payment_gateway_events`: `id`, `gateway_event_id` (unique), `event_type`, `payment_id` (nullable), `outcome` (`SETTLED`, `IGNORED_DUPLICATE`, `IGNORED_UNKNOWN_ORDER`, `AMOUNT_MISMATCH`, `IGNORED_STATE`), `received_at`. Stores no raw body and no card or personal data.
  - `payment_refunds`: `id`, `payment_id`, `amount`, `status` (`REQUESTED`, `PROCESSED`, `FAILED`), `reason`, `gateway_refund_id` (unique when not null), `requested_by`, `created_at`, `processed_at`.
  - No `DELETE` is ever issued on these tables; record the 7-year retention in the migration comment (US-071).

### Backend — Port, Mock Adapter, Configuration
- [ ] `PaymentGatewayPort` and its value types (`CreateOrderRequest`, `GatewayOrder`, `GatewayOrderStatus`, `GatewayRefund`, `GatewayEvent`) in `payment/domain` (pure Java, no provider names). A single `GatewayException` with a kind (`UNAVAILABLE`, `REJECTED`, `INVALID_SIGNATURE`).
- [ ] `MockPaymentGatewayAdapter` in `payment/adapter`: creates a fake order ID, answers status and refund calls from the database state, signs and verifies mock callbacks with `valuex.payment.mock.webhook-secret` (HMAC-SHA256, constant-time compare).
- [ ] `PaymentProviderConfig` selecting the adapter with `@ConditionalOnProperty("valuex.payment.provider")`; `mock` is the default only in the `dev` and `test` profiles; every other profile must set the provider explicitly. Properties in `ValuexProperties` and `application.yml`: `provider`, `currency`, `order-expiry-minutes` (30), `reconciliation.interval` and `reconciliation.min-age`, `mock.webhook-secret`. Real gateway keys are added with the real adapter, read from the environment.
- [ ] `PaymentProviderStartupCheck`: fails startup when the provider is `mock` in any profile other than `dev` or `test`, and fails when no provider is set outside those profiles.

### Backend — State Machine and Domain
- [ ] `PaymentStateMachine` additions: `PAYMENT_SUCCESS → REFUND_REVIEW` (`REVIEW_REFUND`) and `PAYMENT_FAILED → PAYMENT_SUCCESS` (`LATE_SUCCESS`). Keep all existing transitions. Add the new transitions to the US-091 documentation when that story lands.
- [ ] `Payment`, `PaymentAttempt`, `PaymentGatewayEvent`, `PaymentRefund` entities and repositories; `Money` helper converting rupees to the smallest unit exactly (rejects more than 2 decimals, zero or negative).
- [ ] `PaymentSucceededEvent`, `PaymentFailedEvent` (with `reason`, `late`) as `DomainEvent`s.

### Backend — `PaymentService`
- [ ] `createOrReuse(CreatePaymentCommand)` (reference type, reference ID, payer, amount): amount above zero (a zero amount is a caller bug: features skip payment for zero); an open payment with the same amount is returned as is; an open payment with a different amount is superseded; then create the `payments` row, call `createOrder` (5 s timeout inside the adapter), save `gateway_order_id`, `expires_at`, move `PAYMENT_INITIATED → PAYMENT_PENDING` (`SUBMIT`), write a `CREATE_ORDER` attempt. A gateway failure rolls the row back to nothing left pending and raises `ERROR_GATEWAY_UNAVAILABLE` (503).
- [ ] Return a `PaymentCheckoutDetails` (payment ID, order ID, amount, currency, public key from the adapter, expiry); no secret is ever included.
- [ ] `supersedeOpenPayment(referenceType, referenceId)`: open payment `PAYMENT_PENDING → PAYMENT_FAILED` (`FAIL`, reason `SUPERSEDED`), publish `PaymentFailedEvent(SUPERSEDED)`; no gateway call.
- [ ] `PaymentSettlementService.settleCaptured(gatewayOrderId, gatewayPaymentId, amountMinor)` used by the callback, the reconciliation job and the status fetch: load by order ID with a lock; amount mismatch → record `AMOUNT_MISMATCH`, no state change, error log and metric; `PAYMENT_PENDING → PAYMENT_SUCCESS` (`SUCCESS`) or `PAYMENT_FAILED → PAYMENT_SUCCESS` (`LATE_SUCCESS`, event `late = true`); already success → no-op; other states → record `IGNORED_STATE`. Save `gateway_payment_id`; publish `PaymentSucceededEvent` after the commit.
- [ ] `settleFailed(...)`: `PAYMENT_PENDING → PAYMENT_FAILED` (`FAIL`) with the gateway's reason, publish `PaymentFailedEvent(FAILED)`.
- [ ] `expire(...)`: used by reconciliation: `PAYMENT_PENDING → PAYMENT_FAILED`, reason `EXPIRED`, event `PaymentFailedEvent(EXPIRED)`.

### Backend — Callback and Status Endpoints
- [ ] `PaymentCallbackController`: `POST /api/v1/webhooks/payment`, added to the `permitAll` list in `SecurityConfig` (no user token). Reads the **raw** body; calls `adapter.parseCallback`; invalid signature → 401 with no processing; anything else → 200 always, including unknown orders and business rejections, so the gateway never retries on business outcomes. A processing error is caught, logged without the body, and answered 200 only when the event was stored for the reconciliation job to finish; otherwise 500 so the gateway retries.
- [ ] `PaymentCallbackService.handle(GatewayEvent)`: insert into `payment_gateway_events` first (unique event ID; a conflict means duplicate → return); then call the settlement service or the refund update by event type; record the outcome.
- [ ] `GET /api/v1/payments/{paymentId}` (authenticated payer only; others get not found): status and amount for the app to poll. `ApiResponse` envelope.
- [ ] `POST /api/v1/payments/{paymentId}/checkout-result` body `{ "result": "COMPLETED" | "CANCELLED" | "FAILED", "gatewayPaymentId": "..." }` (payer only): writes a `CHECKOUT_RESULT` attempt; on `COMPLETED` fetches the order status from the gateway and settles if it is paid (same service, idempotent). It never changes a payment because the app says so. Rate limit per payment (5 per minute).
- [ ] Standard error mapping in `GlobalExceptionHandler`; no payment secrets or bodies in logs.

### Backend — Reconciliation
- [ ] `PaymentReconciliationJob` (`@Scheduled`, `fixedDelay` from properties, default every 5 minutes; with a lock so two instances do not run it together): payments `PAYMENT_PENDING` older than `min-age` (default 5 minutes) → `fetchOrderStatus`: paid → `settleCaptured`; failed → `settleFailed`; not paid and `expires_at` passed → `expire`. Writes a `STATUS_FETCH` attempt per call; a gateway error skips that payment until the next run. Batch size limit (100) per run.
- [ ] Metrics: `payment_created_total`, `payment_settled_total{outcome}`, `payment_callback_rejected_total`, `payment_amount_mismatch_total`, `payment_reconciled_total`, `payment_late_success_total`; alert on any amount mismatch or late success.

### Backend — Refunds
- [ ] `PaymentRefundService.requestRefund(paymentId, amount, reason, requestedBy)`: payment must be `PAYMENT_SUCCESS` or `REFUND_REVIEW`; amount above zero and not above the amount still refundable; creates a `payment_refunds` row (`REQUESTED`); for a full refund moves `PAYMENT_SUCCESS → REFUND_REVIEW` when needed. **Does not call the gateway.** This is what a flag becomes when someone decides to refund.
- [ ] `PaymentRefundService.approveAndExecute(refundId)`: `REFUND_REVIEW → REFUND_APPROVED` (`APPROVE_REFUND`) for a full refund, call `adapter.refund` with the receipt equal to the refund ID (so a retry cannot refund twice), save `gateway_refund_id`; a synchronous `processed` answer or the refund callback sets the refund `PROCESSED` and the payment `REFUND_APPROVED → REFUND_PROCESSED` (`PROCESS_REFUND`) once the whole amount is refunded; a failure sets the refund `FAILED`, logs `ERROR_REFUND_FAILED` and alerts (the payment stays `REFUND_APPROVED` for a retry). Partial refunds update `payment_refunds` only; the payment state moves only when the total refunded equals the amount.
- [ ] Not exposed over HTTP in this story: US-009 (the flag), US-035 (returns) and the admin console (US-054/US-056) call the service when they are built. Until then it is exercised by tests only.

### Backend — Dev-only Simulation
- [ ] With `valuex.payment.provider=mock` only (`@ConditionalOnProperty`): `POST /api/v1/dev/payments/{paymentId}/simulate` body `{ "outcome": "SUCCESS" | "FAILURE" }`, authenticated payer. Builds a mock-signed callback for the payment and sends it through `PaymentCallbackService` exactly like a real callback. The bean does not exist with another provider (covered by a test).

### Mobile (Flutter)
There is no Figma screen for this story (the gateway draws its own checkout); the mock checkout sheet is developer-only, uses existing design system tokens and components, and needs no Figma-to-code mapping entry.
- [ ] `lib/features/payment/domain/`: `PaymentCheckout` interface `Future<CheckoutOutcome> open(CheckoutRequest request)` with `CheckoutOutcome` = `completed(gatewayPaymentId)`, `cancelled`, `failed(reason)`; `CheckoutRequest` (payment ID, order ID, amount, currency, public key); `PaymentStatus` model.
- [ ] `lib/features/payment/data/`: `PaymentRepository` (`getStatus`, `reportCheckoutResult`) using `ApiClient`; `MockPaymentCheckout` (opens the mock sheet, calls the simulate endpoint for "Pay" or "Fail", returns the outcome); Riverpod `paymentCheckoutProvider` returning `MockPaymentCheckout` today. The gateway implementation is added here when the gateway is chosen; no feature code changes.
- [ ] `lib/features/payment/presentation/`: `MockCheckoutSheet` bottom sheet ("Test payment": amount, Pay, Fail, Cancel), shown only when the app is configured for the dummy gateway (`PAYMENT_PROVIDER=mock` in the dev configs only; decided 2026-10-30); localized, 48 dp tap targets, labels for screen readers.
- [ ] `PaymentFlowController` (Riverpod): `start(CheckoutRequest)` → enables screen protection (US-109) → `paymentCheckout.open` → `reportCheckoutResult` → polls `getStatus` (every 2 s, up to 60 s) until `PAYMENT_SUCCESS` or a failed state → disables screen protection → returns `PaymentResult` (`confirmed`, `failed`, `pending`). `pending` means the server has not settled it yet: the calling feature shows "We're confirming your payment" and keeps checking when the app resumes. The controller never treats the SDK's "completed" as success.
- [ ] Hold the screen protection from the existing reference-counted `ScreenProtectionService` for the whole flow.
- [ ] Error messages for `ERROR_GATEWAY_UNAVAILABLE`, `ERROR_PAYMENT_FAILED`, `ERROR_PAYMENT_TIMEOUT` in the existing API error mapping, in English and Hindi (Hindi to be reviewed).
- [ ] No gateway package is added to `pubspec.yaml` in this story.

### Documentation/Quality
- [ ] OpenAPI for the two payer endpoints and the callback (headers described generically, always-200 behaviour, 401 on a bad signature); the dev simulate endpoint tagged "dev only".
- [ ] Update LLD Part H §H.3 (tables, neutral names), Part I §I.3–I.4 (callback owned here, event-based hand-over), and HLD Part 7 §21 (provider-neutral, adapter list) where the implementation differs.
- [ ] Add a short "Adding a payment gateway" section to the backend README: implement `PaymentGatewayPort`, register in `PaymentProviderConfig`, add keys and the webhook secret to the environment, add the SDK implementation of `PaymentCheckout` in the app.
- [ ] After implementation, create `Documents/Manual Testing Guides/US-117-Testing-Guide.md` (mock provider: create, pay, fail, cancel, duplicate callback, late success, reconciliation, refund through the service).

## 5. Test Plan

Target >90% coverage for new code (`CLAUDE.md`).

### Backend Unit Tests
- [ ] `Money`: 49.00 → 4900, 0.1 + 0.2 style inputs, more than 2 decimals rejected, zero and negative rejected.
- [ ] `createOrReuse`: creates `PAYMENT_PENDING` with order ID and expiry; same open amount returns the same payment; different amount supersedes the old one and creates a new one; zero amount rejected; gateway error leaves no open payment and raises `ERROR_GATEWAY_UNAVAILABLE`; the response never contains a secret.
- [ ] `supersedeOpenPayment`: moves to failed with `SUPERSEDED`, event published once, no gateway call, nothing happens when there is no open payment.
- [ ] Settlement: captured moves `PAYMENT_PENDING → PAYMENT_SUCCESS` and publishes one event after commit; amount mismatch changes nothing and counts; already success is a no-op; unknown order is recorded and ignored; `PAYMENT_FAILED → PAYMENT_SUCCESS` sets `late = true`; refunded states are ignored; a second concurrent settlement loses on the version check and does nothing.
- [ ] `settleFailed` and `expire` publish `PaymentFailedEvent` with the right `reason`.
- [ ] Callback: valid signature accepted; missing, wrong or altered body rejected with 401 and no processing; the comparison is constant-time; duplicate event ID acknowledged and ignored; an unknown event type is stored and ignored; a processing error that stored the event answers 200.
- [ ] Checkout result: `COMPLETED` triggers a status fetch and settles when paid, does nothing when not paid; `CANCELLED` and `FAILED` write an attempt only; another user's payment is not found; the rate limit applies.
- [ ] Reconciliation: pending and paid at the gateway settles; pending, unpaid and expired fails with `EXPIRED`; younger than `min-age` is skipped; a gateway error skips one payment and continues; idempotent on a second run.
- [ ] Refunds: full refund walks `PAYMENT_SUCCESS → REFUND_REVIEW → REFUND_APPROVED → REFUND_PROCESSED`; partial refunds keep the payment state until the total matches; refunding more than the amount rejected; a retry uses the same receipt and cannot refund twice; gateway failure leaves `REFUND_APPROVED` and alerts; duplicate refund callback is ignored.
- [ ] `PaymentStateMachine`: the two new transitions work; every previous transition still works; an invalid transition is rejected.
- [ ] Mock adapter: order creation, status, refund and signing; the startup check fails in any profile other than `dev` or `test` with `mock`, and passes with `mock` in `dev` and `test`; the simulate controller bean exists only with the mock provider.

### Backend Integration Tests (Testcontainers PostgreSQL)
- [ ] `V19` applies on top of the previous versions; the open-payment unique index blocks a second open payment for one reference, and allows a new one after the old one is failed.
- [ ] End to end with the mock provider: create → simulate success through the callback endpoint → payment `PAYMENT_SUCCESS`, one `PaymentSucceededEvent`; the same callback again changes nothing.
- [ ] The callback endpoint works without a user token; `GET /payments/{id}` requires one and enforces ownership (IDOR).
- [ ] Late success: expire a payment, then send the captured callback: payment `PAYMENT_SUCCESS`, event with `late = true`.
- [ ] Reconciliation settles a pending payment with no callback.
- [ ] No test or log line contains a raw callback body.

### Mobile Tests (Flutter)
- [ ] `PaymentFlowController` with fakes: completed + server confirms → `confirmed`; completed but the server stays pending → `pending` after the poll limit (never `confirmed`); cancelled → `cancelled` and no polling; failed → `failed`; screen protection is enabled before and disabled after in every path, including errors.
- [ ] `PaymentRepository`: request and response parsing, error mapping for the three error codes.
- [ ] `MockCheckoutSheet`: Pay, Fail and Cancel buttons; shown only when the app is configured for the dummy gateway (`PAYMENT_PROVIDER=mock`, see Open Gap 9) and never when it is not; accessibility guideline tests (tap target, labels) in English and Hindi.

## 6. Validation Checklist

- [ ] The amount always comes from the server; the app has no way to set or change it.
- [ ] A payment becomes successful only through a verified callback, a gateway status fetch, or reconciliation, never through the app's report.
- [ ] Duplicate, replayed and out-of-order callbacks are harmless; late success is never lost.
- [ ] No gateway name, SDK or provider-specific field appears outside an adapter.
- [ ] The callback is always acknowledged except for an invalid signature (and a store failure, so the gateway retries).
- [ ] No card, UPI, bank detail or raw callback body is stored or logged; secrets only from the environment.
- [ ] Payment records are never deleted.
- [ ] The mock provider can run only in `dev` and `test` (never in `prod` or any other profile), and the simulate endpoint cannot exist without it.
- [ ] The app shows the dummy checkout only when its config has `PAYMENT_PROVIDER=mock`; `staging.json` and `prod.json` do not contain it.
- [ ] Every payment state change goes through `PaymentStateMachine`.
- [ ] Switching the provider needs no change in US-008, US-009 or any feature.
- [ ] Checkstyle, full tests, coverage, SonarQube (backend) and Flutter analyze and tests (mobile) pass before push.

## 7. Open Gaps / Questions

1. **Gateway choice (open, product owner).** Which gateway, its fees, settlement and refund rules, and the account, keys and webhook secret needed for staging. The HLD assumes Razorpay with Cashfree as a possible later option. Until it is chosen only the mock adapter exists, and a `prod` deployment will not start (see item 6); the real adapter and the app's gateway checkout are a follow-up story or a task on this one, to be sized once the gateway is known.
2. **Refund execution (open).** The service can issue refunds, but nothing calls it yet: US-009 flags `REFUND_REVIEW` only. Decide whether a refund after the third failed review is automatic or approved by finance, and who approves (admin console, US-054/US-056).
3. **Late success handling (proposed default).** When money arrives for a failed, expired or superseded payment, the payment goes to `PAYMENT_SUCCESS` and the event is marked `late`. Proposed default for a listing plan: if the listing is still waiting for that plan, continue as a normal success; otherwise flag the payment for refund review. This needs a small addition to the US-009 plan, which is noted there; please confirm the default.
4. **Cancelling gateway orders (decided here).** Orders are never cancelled at the gateway; superseded orders expire there.
5. **Partial refunds and escrow.** Partial refund amounts are tracked, but the escrow and return rules are US-021 and US-035; this story only provides the call.
6. **Environments without a gateway (decided 2026-10-30).** The dummy gateway runs in `dev` only (`PAYMENT_PROVIDER=mock` in the dev app configs `config/dev_*.json`); never in prod. In other environments (staging, prod) the backend refuses to start with `mock`; until the real gateway exists, paying there is not possible. If a staging or production deployment is needed before then, the choice is to allow it with the payment endpoints answering `ERROR_GATEWAY_UNAVAILABLE`; the plan assumes there is no such release before the gateway is chosen.
7. **Invoices and GST on payments.** Prices include GST (US-078); invoice generation and GST reporting are not in this story and need a finance decision.
8. **Payments table owner.** `payments` now belongs to US-117; US-008's migration only adds plan snapshot columns on `listings`.
9. **Where the dummy gateway may run (decided 2026-10-30).** `PAYMENT_PROVIDER=mock` in **dev only**, never in prod (and not in staging). The app shows the dummy checkout only when `config/dev_*.json` sets `PAYMENT_PROVIDER=mock` (a `--dart-define`), independent of debug or release build; `staging.json` and `prod.json` do not contain it. The backend allows the dummy provider in `dev` (and `test` for automated tests) and refuses to start with it anywhere else. Consequence: in staging and prod the payment endpoints are unusable until the real gateway adapter exists (item 6).
10. **Dummy gateway behaviour (decided 2026-10-30).** The tester decides the outcome in the test sheet (Pay or Fail) and nothing is charged. The dummy callback goes through the same endpoint and signature check as a real one, so the real path is tested from day one. Extra simulated cases (delayed callback, no callback) are available through the dev simulate endpoint and the reconciliation job, not through extra app screens.

---

**Status:** Approved (2026-10-30; the user approved the plan with the dummy `mock` gateway in dev only, never in prod; migration `V19`).

## 8. Implementation Notes (deviations from the plan as built)

1. **No provider configured does not stop the start.** The plan said a `prod` deployment would not start without a gateway. As built, only `PAYMENT_PROVIDER=mock` outside `dev` and `test` refuses to start; with no provider the `UnconfiguredPaymentGateway` is used, so `createOrder`, status and refund calls answer `ERROR_GATEWAY_UNAVAILABLE` (503) and every callback is rejected as unsigned (401). This is the choice open gap 6 offered, and it keeps staging and prod deployable before the gateway is chosen. An unknown provider name fails the start. The check lives in `PaymentProviderConfig` instead of a separate `PaymentProviderStartupCheck` class.
2. **The dummy gateway keeps its orders in memory,** not in the database. After a restart an unknown order reads as "not paid" and reconciliation expires it at `expires_at`. Refunds are idempotent per receipt in memory. Simulated callbacks go through `parseCallback` and `PaymentCallbackService` exactly like real ones.
3. **Callback processing error.** The event insert and the processing share one transaction, so a failure rolls both back and the controller answers 500; the gateway's retry is processed from scratch. (The plan's "200 when the event was stored" case cannot happen.)
4. **No reconciliation lock.** Two instances may run the job together; settlement locks the payment row and is idempotent, so the second run changes nothing.
5. **Duplicate create race.** Two simultaneous `createOrReuse` calls for one reference: the loser hits the unique index and gets `400 ERROR_DUPLICATE_PAYMENT` ("try again"); the retry reuses the winner's payment.
6. **Metrics** are Micrometer counters named `payment.created`, `payment.settled{outcome}`, `payment.callback.rejected`, `payment.amount.mismatch`, `payment.reconciled`, `payment.late.success` and `payment.refund.failed`. Alert rules are part of the DevOps work (US-072), not this story.
7. **New 503 type.** `ServiceUnavailableException` and its handler were added to `GlobalExceptionHandler` for `ERROR_GATEWAY_UNAVAILABLE`.
8. **Refund rules as built.** A refund request that brings the total of requested and processed refunds up to the payment amount moves `PAYMENT_SUCCESS → REFUND_REVIEW`; `approveAndExecute` accepts a `REQUESTED` or `FAILED` refund (the retry) and `REFUND_PROCESSED` is reached when the processed refunds equal the amount. Payment rows are locked (`findByIdForUpdate`) for these calls so two refunds cannot over-refund.
9. **Mobile.** `PaymentCheckout.open` takes a `BuildContext` (the dummy sheet needs it). `PaymentFlow` is a plain Riverpod-provided class (`paymentFlowProvider`) rather than a notifier, and `PaymentResult` has a fourth value, `cancelled`, for a payer who backs out. `AppConfig` rejects `PAYMENT_PROVIDER=mock` outside dev. The dummy checkout is added to `config/dev_android.json`, `dev_ios.json`, `dev_device.json` and `dev_local.json` only.
10. **Sonar and JaCoCo.** `payment` was removed from the Sonar and JaCoCo exclusions in `pom.xml`, so the module is measured.
