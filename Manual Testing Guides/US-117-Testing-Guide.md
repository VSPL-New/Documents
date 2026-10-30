# US-117 — Payment Gateway Integration: QA Testing Guide

**Sprint 2 · Seller Listing Creation (shared payment infrastructure)**

Manual test cases for the gateway-neutral payment module and its **dummy gateway** (`PAYMENT_PROVIDER=mock`): payment
creation, the signed callback, settlement, reconciliation, the payer's status and checkout-result endpoints, refunds
(service only), and the app's test checkout. No money is ever charged. No feature calls the payment module yet
(US-008 is the first caller), so payments are created here through a small dev helper or the automated tests.

> **What this story ships:** `PaymentGatewayPort` and the `MockPaymentGatewayAdapter`; `PaymentService`,
> `PaymentSettlementService`, `PaymentCallbackService`, `PaymentReconciliationJob`, `PaymentRefundService`;
> `GET /api/v1/payments/{id}`, `POST /api/v1/payments/{id}/checkout-result`, `POST /api/v1/webhooks/payment`,
> and (mock only) `POST /api/v1/dev/payments/{id}/simulate`; migration `V19`; the app's `PaymentFlow` and test checkout.

| Setting | Value |
|---|---|
| Backend base URL | `http://localhost:8080` |
| Migration | `V19` (Flyway runs on start) |
| DB tables | `payments`, `payment_attempts`, `payment_gateway_events`, `payment_refunds` |
| Provider | `PAYMENT_PROVIDER=mock` (default in the `dev` profile); secret `PAYMENT_MOCK_WEBHOOK_SECRET` (default `dev-only-mock-payment-secret`) |
| Callback header | `X-Mock-Signature` = hex HMAC-SHA256 of the raw body with the secret |
| Order expiry | 30 minutes; reconciliation every 5 minutes for payments older than 5 minutes |
| Error codes | `ERROR_GATEWAY_UNAVAILABLE` (503) · `ERROR_DUPLICATE_PAYMENT` (400) · `ERROR_INVALID_PAYMENT_AMOUNT` (400) · `PAYMENT_NOT_FOUND` (404) · `PAYMENT_CHECKOUT_RESULT_RATE_LIMITED` (429) |

---

## Prerequisites

1. PostgreSQL and Redis from `valuex-backend/docker-compose.yml`; start the backend (`mvn spring-boot:run`). The log
   shows `Payment gateway: the DUMMY gateway is active; no money moves`.
2. Two `ACTIVE` users with access tokens: `$TOKEN` (payer) and `$TOKEN_B` (another user); note the payer's id as `$PAYER`.
3. Create a payment for the payer (no endpoint creates one yet; US-008 will). Either run the automated tests, or
   insert one with SQL for a manual run:

```sql
-- a pending payment with an order the dummy gateway does not know (it reads as "not paid")
INSERT INTO payments (id, reference_type, reference_id, payer_user_id, amount, status, gateway_provider,
                      gateway_order_id, expires_at)
VALUES ('11111111-1111-4111-8111-111111111111', 'LISTING_PLAN', uuid_generate_v4(), '<$PAYER>', 49,
        'PAYMENT_PENDING', 'mock', 'mock_order_manual1', NOW() + INTERVAL '30 minutes');
```

   Set `$PAY` to `11111111-1111-4111-8111-111111111111`. The dummy gateway keeps orders in memory, so after a backend
   restart a `mock_order_...` order is unknown to it and reads as not paid.
4. For the app cases: the emulator build of `valuex-mobile` with `config/dev_android.json` (it contains
   `"PAYMENT_PROVIDER": "mock"`), signed in as the payer.

Read a payment:

```powershell
curl.exe -s "http://localhost:8080/api/v1/payments/$PAY" -H "Authorization: Bearer $TOKEN"
```

---

## Test cases

| ID | Acceptance criterion / edge case | Steps | Expected |
|---|---|---|---|
| TC-001 | Migration | Start the backend; `SELECT version FROM flyway_schema_history WHERE version = '19';` | One successful row; the four tables exist |
| TC-002 | One open payment per reference | Insert a second `PAYMENT_PENDING` payment with the same `reference_type` and `reference_id` | The database rejects it (`uq_payments_open_reference`) |
| TC-003 | Simulate success | `POST /api/v1/dev/payments/$PAY/simulate` with `{"outcome":"SUCCESS"}` as the payer | 200, `data.status` `PAYMENT_SUCCESS`; `payments.gateway_payment_id` set; one `payment_gateway_events` row with `outcome` `SETTLED` and the payment id |
| TC-004 | Simulate failure | New pending payment, `{"outcome":"FAILURE"}` | 200, `PAYMENT_FAILED`, `failureReason` `MOCK_PAYMENT_DECLINED`; event `outcome` `FAILED_SETTLED` |
| TC-005 | Callback needs no token but a signature | `POST /api/v1/webhooks/payment` with a body and no `Authorization` header and a wrong `X-Mock-Signature` | 401; nothing is stored in `payment_gateway_events`; a missing header gives 401 too |
| TC-006 | Valid callback | Build a body (see the automated test `PaymentIntegrationTest` for the shape) signed with the secret and post it without a token | 200 and the payment settles |
| TC-007 | Duplicate callback | Post the same signed body twice | Both 200; one event row; the payment settled once (`SELECT count(*) FROM payment_gateway_events WHERE gateway_event_id = '<id>'` is 1) |
| TC-008 | Amount mismatch | Signed capture event with another `amountMinor` than the payment | 200; the payment stays `PAYMENT_PENDING`; event `outcome` `AMOUNT_MISMATCH`; an `ERROR` log line "Payment amount mismatch" |
| TC-009 | Unknown order | Signed capture event for an order that does not exist | 200; event `outcome` `IGNORED_UNKNOWN_ORDER` |
| TC-010 | Late success | Set a pending payment to `PAYMENT_FAILED` (`failure_reason` `EXPIRED`), then post a signed capture for its order | `PAYMENT_SUCCESS`; log "Late payment success"; the `PaymentSucceededEvent` has `late = true` (covered by the integration test) |
| TC-011 | Reconciliation settles a paid order | Make the order paid at the gateway without a callback (simulate, then set the payment back to `PAYMENT_PENDING` with an old `created_at`), run the job (wait 5 minutes or call `PaymentReconciliationJob` from a test) | The payment becomes `PAYMENT_SUCCESS`; a `STATUS_FETCH` attempt is stored |
| TC-012 | Reconciliation expires an unpaid order | Pending payment with `created_at` 40 minutes ago and `expires_at` in the past, run the job | `PAYMENT_FAILED`, `failure_reason` `EXPIRED` |
| TC-013 | Only the payer sees a payment | `GET /api/v1/payments/$PAY` as `$TOKEN_B`; and without a token | 404 `PAYMENT_NOT_FOUND`; 401 |
| TC-014 | Checkout result never settles by itself | `POST .../checkout-result` with `{"result":"COMPLETED","gatewayPaymentId":"liar"}` while the gateway has not paid | 200; `data.status` still `PAYMENT_PENDING`; a `CHECKOUT_RESULT` attempt is stored |
| TC-015 | Checkout result after a real payment | Make the order paid at the gateway (simulate success, then set the payment back to `PAYMENT_PENDING` in SQL), then post `COMPLETED` | `PAYMENT_SUCCESS` (the server asked the gateway) |
| TC-016 | Rate limit | Post six checkout results for one payment within a minute | The first five give 200; the sixth gives 429 `PAYMENT_CHECKOUT_RESULT_RATE_LIMITED` |
| TC-017 | Validation | `checkout-result` with `{}` or `{"result":"MAYBE"}` | 400 `VALIDATION_ERROR` |
| TC-018 | Simulate is payer-only and mock-only | `simulate` as `$TOKEN_B`; then start the backend with `PAYMENT_PROVIDER=` empty | 404 `PAYMENT_NOT_FOUND`; with no provider the simulate route does not exist (the controller bean is not created; covered by `PaymentProviderConfigTest`) |
| TC-019 | Dummy gateway refused outside dev | Start with `SPRING_PROFILE=prod PAYMENT_PROVIDER=mock` | The backend refuses to start: "valuex.payment.provider=mock is allowed only in the dev and test profiles" |
| TC-020 | No gateway configured | Start with `SPRING_PROFILE=staging` and no `PAYMENT_PROVIDER` | The backend starts; creating a payment answers 503 `ERROR_GATEWAY_UNAVAILABLE`; the callback endpoint answers 401 |
| TC-021 | Unknown provider | `PAYMENT_PROVIDER=razorpay` | The backend refuses to start: "Unknown payment provider: razorpay" |
| TC-022 | Create, reuse, supersede (service) | Run `PaymentServiceTest` and `PaymentIntegrationTest` | Same amount reuses the open payment; a different amount supersedes it (`PAYMENT_FAILED`, `SUPERSEDED`) and creates a new one; zero or fractional amounts are rejected; a gateway error leaves nothing pending |
| TC-023 | Refunds (service only) | Run `PaymentRefundServiceTest` | Full refund `PAYMENT_SUCCESS → REFUND_REVIEW → REFUND_APPROVED → REFUND_PROCESSED`; partial refunds keep the state until the total matches; more than the amount is refused; a retry uses the same receipt (refund id); a gateway failure leaves the refund `FAILED` and the payment `REFUND_APPROVED` |
| TC-024 | No secrets or bodies in logs | Run TC-003 to TC-009 and read the backend log | No signature, secret or callback body appears; only ids, states and outcomes |

### App cases (emulator, `dev_android.json`)

These need a feature that starts a payment (US-008). Until then, start the flow from a widget test or a temporary
debug button calling `ref.read(paymentFlowProvider).start(context, CheckoutRequest(...))`.

| ID | Steps | Expected |
|---|---|---|
| TC-A01 | Start a payment | The bottom sheet "Test payment" shows the note "This is a test checkout. No money is charged.", the amount and the buttons Pay, Fail, Cancel |
| TC-A02 | Tap **Pay** | The sheet closes; the app reports the result and the server settles; the flow returns `confirmed` after the server says `PAYMENT_SUCCESS` |
| TC-A03 | Tap **Fail** | The flow returns `failed`; the payment is `PAYMENT_FAILED` |
| TC-A04 | Tap **Cancel** or swipe the sheet down | The flow returns `cancelled`; the payment stays `PAYMENT_PENDING` |
| TC-A05 | Stop the backend after tapping Pay | After 60 seconds the flow returns `pending` (the feature shows "We're confirming your payment"); nothing says success |
| TC-A06 | Screenshots | While the sheet is open a screenshot is blocked (Android); protection is released after the flow ends |
| TC-A07 | Staging or prod config | Run with `config/staging.json`: it has no `PAYMENT_PROVIDER`; paying fails with "Payments are not available at this moment, please try again later" |
| TC-A08 | Hindi and large text | Switch to Hindi, then set the largest system text size | Sheet text is in Hindi and shows without overflow; buttons stay reachable |

---

## Running the automated tests

Backend (Docker must be running for the integration test):

```powershell
cd valuex-backend
$env:JAVA_TOOL_OPTIONS='-Duser.timezone=Asia/Kolkata'
mvn verify '-Dtestcontainers.version=1.21.4'
mvn checkstyle:check
```

Only this story:

```powershell
mvn test '-Dtest=MoneyTest,MockPaymentGatewayAdapterTest,PaymentProviderConfigTest,UnconfiguredPaymentGatewayTest,PaymentSettlementServiceTest,PaymentServiceTest,PaymentReconciliationServiceTest,PaymentReconciliationJobTest,PaymentCallbackServiceTest,PaymentRefundServiceTest,PaymentControllersTest,PaymentSimulationServiceTest,PaymentStateMachineTest,PaymentIntegrationTest'
```

Mobile:

```powershell
cd valuex-mobile
flutter gen-l10n
flutter analyze
flutter test test/features/payment test/core/config
```

(The 18 accessibility contrast tests that fail on `main` are not part of this story.)

Results at hand-over: backend `mvn clean verify` 1108 tests, 0 failures (this story: 100 unit tests and the 19-case
`PaymentIntegrationTest` on Testcontainers PostgreSQL), Checkstyle and the JaCoCo gate pass; payment classes are 96 to
100 % line covered; SonarQube quality gate OK (0 new issues, 93.6 % coverage on new code). Mobile: `flutter analyze`
no issues; 52 tests in `test/features/payment` and `test/core/config` pass; the payment files are 94 to 100 % line
covered; the full suite shows only the 18 accessibility contrast failures that also fail on `main`.
