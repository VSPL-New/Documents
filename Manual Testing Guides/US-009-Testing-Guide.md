# US-009 and US-084 — Listing Publication After Payment and Trust & Safety Review: QA Testing Guide

**Sprint 2 · Seller Listing Creation** (delivered together on one branch; this guide covers both stories)

Manual test cases for what happens to a listing after its plan is paid: the hand-over to the Trust & Safety review (US-084),
publication (US-009), the three review attempts, the refund flag, late payments, the recovery jobs, and the app's
"Your listing is submitted" page. The dummy gateway is used; no money is charged.

> **What ships:** migrations `V21` (`listing_trust_safety_reviews`, `listing_trust_safety_appeals`) and `V22`
> (`listings.published_at`); `ListingPaymentHandler` (replaces the US-008 logging default), `ListingPaymentResultListener`
> (payment succeeded, failed and late), `TrustSafetyReviewService`, `ListingPublicationService`, `ListingRefundDueListener`,
> `ListingRecoveryJob`; `POST /api/v1/listings/{id}/trust-safety-review` and `.../appeal`; the app page `/sell/submitted`.
> **Not in this story:** admin approve/reject endpoints (no admin role until Sprint 10, the decisions are services only),
> seller notifications (US-115), the listing preview page (US-123, the button says "Preview is coming soon"), search ranking
> for boosted and priority plans (Sprint 3), issuing the refund (finance approves it later with `approveAndExecute`).

| Setting | Value |
|---|---|
| Backend base URL | `http://localhost:8080` |
| Migrations | `V21`, `V22` (Flyway runs on start) |
| Gateway | `PAYMENT_PROVIDER=mock` (default in `dev`); see `US-117-Testing-Guide.md` |
| Review mode | `MODERATION_MANUAL_REVIEW_ENABLED=false` (default): a listing with no AI score is approved at once as `AUTO_APPROVED_NO_AI`. `true`: it waits in the queue |
| AI | `VALUEX_AI_ENABLED=false` (default). With `true` the fraud score comes from the AI service (`/ai/v1/listings/fraud-score`, not built yet) |
| Settings | `valuex.moderation.max-review-attempts` 3, `review-sla-hours` 24; `valuex.listing.recovery.*` every minute, retry after 5 minutes, 5 attempts, unpaid timeout 30 minutes |
| Errors | `ERROR_REVIEW_NOT_ALLOWED` · `ERROR_APPEAL_NOT_ALLOWED` · `ERROR_APPEAL_ALREADY_SUBMITTED` · `ERROR_REVIEW_REASON_REQUIRED` · `ERROR_NO_PENDING_REVIEW` · `LISTING_NOT_FOUND` (404) |

---

## Prerequisites

1. PostgreSQL and Redis from `valuex-backend/docker-compose.yml`; start the backend (`mvn spring-boot:run`).
2. Two `ACTIVE` sellers with Aadhaar verified and tokens: `$TOKEN` (seller A) and `$TOKEN_B` (seller B).
3. A complete draft of seller A with a cleared restricted check (`US-008-Testing-Guide.md`, prerequisite 3). Note its id as `$LISTING`.
4. Choose a plan (`BOOSTED`) and keep the `payment.paymentId` as `$PAYMENT`. Pay it with the dummy gateway:

```powershell
curl.exe -s -X POST "http://localhost:8080/api/v1/dev/payments/$PAYMENT/simulate" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{\"outcome\":\"SUCCESS\"}'
```

Useful queries:

```sql
SELECT status, plan_type, plan_validity_days, published_at, expires_at FROM listings WHERE id = '<id>';
SELECT action, from_status, to_status FROM listing_status_history WHERE listing_id = '<id>' ORDER BY changed_at;
SELECT attempt_number, review_reason, auto_decision, admin_decision, sla_deadline FROM listing_trust_safety_reviews WHERE listing_id = '<id>' ORDER BY created_at;
```

---

## Test cases: backend

| ID | Acceptance criterion / edge case | Steps | Expected |
|---|---|---|---|
| TC-001 | Migrations | `SELECT version FROM flyway_schema_history WHERE version IN ('21','22');` | Two successful rows; `listings.published_at` and both review tables exist |
| TC-002 | Paid listing is reviewed and published | Prerequisite 4 (pay `BOOSTED`) | Listing ends `PUBLISHED`; history: `PAYMENT_SUCCESS`, `SUBMIT_FOR_REVIEW`, `APPROVE`, `PUBLISH`; one review row `AUTO_APPROVED_NO_AI`, attempt 1; the payment is `PAYMENT_SUCCESS` |
| TC-003 | Validity starts at publication | After TC-002 | `published_at` is set, `expires_at` = `published_at` + 7 days (the plan's validity days when the plan was chosen), not counted from payment |
| TC-004 | A listing is never published without payment | Call `POST /trust-safety-review` for a listing in `PLAN_PAYMENT_PENDING` | 400 `ERROR_REVIEW_NOT_ALLOWED`; status unchanged |
| TC-005 | Plan priced at zero | `UPDATE plans SET discounted_price = 0 WHERE code = 'BASIC';` choose `BASIC` on a fresh draft; restore the price | Listing goes straight through to `PUBLISHED` with no `payments` row and one review row |
| TC-006 | Manual review switched on | Start with `MODERATION_MANUAL_REVIEW_ENABLED=true`; pay | Listing stays `TRUST_SAFETY_REVIEW`; review row `QUEUED_FOR_REVIEW` with `sla_deadline` about 24 hours ahead and no `fraud_score`; `POST /trust-safety-review` returns `code` `LISTING_UNDER_REVIEW` |
| TC-007 | Idempotent status call | Call `POST /trust-safety-review` twice in TC-006 | Same answer both times, still one review row |
| TC-008 | Approval publishes | Approve the queued review (a developer calls `TrustSafetyReviewService.approve` from a test or a debugger; there is no endpoint) | Listing `PUBLISHED`; `admin_decision` `APPROVED` |
| TC-009 | First or second rejection | Reject the queued review (service `reject` with a reason) | Listing `REVISION_REQUIRED`; `rejection_reason` saved; the payment is untouched; no refund row |
| TC-010 | Resubmit without paying again | After TC-009 `POST /trust-safety-review` as seller A | 200, `attemptNumber` 2, `maxAttempts` 3; history `RESUBMIT`; still one payment row |
| TC-011 | Third attempt approved | Reject twice, resubmit twice, approve | Listing `PUBLISHED`; review rows 1, 2, 3 |
| TC-012 | Third failure closes the listing | Reject three times | Listing `REJECTED`; payment `REFUND_REVIEW`; one `payment_refunds` row `REQUESTED`; no gateway call; `POST /trust-safety-review` then returns `code` `LISTING_REJECTED_FINAL` and cannot resubmit |
| TC-013 | A revision request counts like a rejection | Use `requestRevision` instead of `reject` in TC-012 | Same outcome |
| TC-014 | Free plan, third failure | TC-005 with manual review on, three rejections | `REJECTED`; no refund row |
| TC-015 | Reason is required | Service `reject` with a blank or 501-character reason | `ERROR_REVIEW_REASON_REQUIRED` or `ERROR_REVIEW_REASON_TOO_LONG`; nothing changes |
| TC-016 | Appeal | After TC-009 `POST /trust-safety-review/appeal` with `{"reason":"..."}` | 201, status `PENDING`; a second appeal gives 400 `ERROR_APPEAL_ALREADY_SUBMITTED`; an appeal when the latest review did not fail gives 400 `ERROR_APPEAL_NOT_ALLOWED` |
| TC-017 | Ownership | Seller B calls the review and the appeal endpoints for seller A's listing; call with no token | 404 `LISTING_NOT_FOUND`; 401 |
| TC-018 | No admin routes | `GET /api/v1/admin/listings/review` | Not mapped (403 or 404 for a seller token); no admin endpoint is exposed |
| TC-019 | Payment fails | Choose a plan, simulate `FAILURE` | Listing `PLAN_PAYMENT_FAILED`; choosing the plan again works (US-008) |
| TC-020 | Payment expires | Choose a plan, age the payment (`US-117-Testing-Guide.md`) and run reconciliation | Listing returns to `PLAN_SELECTION_PENDING` |
| TC-021 | Late payment, same plan | Choose `BASIC`, expire its payment, then send the signed capture for it (`US-117-Testing-Guide.md`, late success) | The listing continues: `PLAN_PAYMENT_SUCCESS` then review then `PUBLISHED`; the payment is `PAYMENT_SUCCESS`; no refund row |
| TC-022 | Late payment, other plan or amount | Choose `BASIC`, choose `BOOSTED` (the BASIC payment is superseded), then capture the BASIC order | The BASIC payment becomes `REFUND_REVIEW` with a `REQUESTED` refund; the listing stays `PLAN_PAYMENT_PENDING` for BOOSTED; log line "flagged for refund review"; metric `payment.late.refund.review` |
| TC-023 | Second payment for a paid listing | Same as TC-022 but pay BOOSTED first, then capture the BASIC order | BASIC payment `REFUND_REVIEW`; the listing stays `PUBLISHED` |
| TC-024 | Review fails after payment | Make the review fail once (stop the app after the payment commits, or break the restricted check) | Payment `PAYMENT_SUCCESS`, listing `PLAN_PAYMENT_SUCCESS`; the next recovery run after 5 minutes completes it; metric `listing.review.handover.failure` |
| TC-025 | Publish fails after approval | `UPDATE listings SET plan_validity_days = NULL` before paying | Listing stays `APPROVED`, metric `listing.publish.failure`; restore the value and wait 5 minutes: the job publishes it |
| TC-026 | Retries are limited | Keep TC-025 broken | After 5 attempts the log shows `ALERT listing stuck in APPROVED` once and metric `listing.recovery.exhausted` rises; finance refunds by hand |
| TC-027 | Unpaid listing timeout | Choose a plan, delete the open payment's chance (mark it failed), wait 30 minutes | Listing returns to `PLAN_SELECTION_PENDING` (`PAYMENT_TIMEOUT`); with a successful payment present the job continues the listing instead |
| TC-028 | Plan changes do not move the expiry | Change the plan's validity in the catalog after payment, before publication | `expires_at` uses the days taken when the plan was chosen |
| TC-029 | Notifications | Pay and publish | Since US-115 the seller receives "under review" and then "your listing is live" (see `US-115-Testing-Guide.md`); the domain events `ListingReviewDecidedEvent` and the status change event are still published |

---

## Test cases: app (emulator, `dev_android.json`)

| ID | Steps | Expected |
|---|---|---|
| TC-A01 | Pay a plan in the test sheet (**Pay**) | The sheet closes and the page "Your listing is submitted" opens; no snackbar; it never says the listing is live; it says "We will notify you if any action is required" (US-115) |
| TC-A02 | Read the page | Title, the message about the Trust & Safety compliance review, the buttons **Preview your listing** and **Back to Home** |
| TC-A03 | Tap **Preview your listing** | "Preview is coming soon"; stay on the page |
| TC-A04 | Tap **Back to Home**; or press the system back button | Home opens; the app does not close and the review page is not shown again |
| TC-A05 | Plan priced at zero, tap **Publish** | The same submitted page opens; no checkout |
| TC-A06 | Payment not settled yet (stop the backend after **Pay**) | "We're confirming your payment" and Home (not the submitted page) |
| TC-A07 | Failed payment, cancelled checkout | As in US-008: stay on the review page |
| TC-A08 | Hindi and the largest system text size | The page is in Hindi, without overflow; both buttons reachable |

---

## Running the automated tests

Backend (Docker must be running for the integration tests):

```powershell
cd valuex-backend
$env:JAVA_TOOL_OPTIONS='-Duser.timezone=Asia/Kolkata'
mvn verify '-Dtestcontainers.version=1.21.4'
mvn checkstyle:check
```

Only these stories:

```powershell
mvn test '-Dtest=ListingReviewRouterTest,TrustSafetyReviewServiceTest,TrustSafetyAppealServiceTest,TrustSafetyReviewControllerTest,ListingPaymentHandlerTest,ListingPaymentResultListenerTest,ListingPublicationServiceTest,ListingRefundDueListenerTest,ListingRecoveryJobTest,AiGatewayClientTest,ListingPublicationIntegrationTest'
```

Mobile:

```powershell
cd valuex-mobile
flutter gen-l10n
dart format lib test
flutter analyze
flutter test test/features/listing
```

(The 18 accessibility contrast tests that fail on `main` are not part of this story.)

Results at hand-over: backend `mvn clean verify` 1246 tests, 0 failures (this delivery: 16 Testcontainers integration tests in
`ListingPublicationIntegrationTest` plus unit tests for the router, review, appeal, handler, result listener, publication,
refund listener, recovery job, AI client and controller); Checkstyle and the JaCoCo gate pass; SonarQube gate OK (0 new issues,
94.2 % coverage on new code; the one open issue, `S2143` in `JwtTokenProvider`, is old). Mobile: `flutter analyze` no issues,
`dart format` no diff, all tests in `test/features/listing` pass; `listing_submitted_screen` 32/32 and `review_listing_screen`
101/102 lines covered; the full suite shows only the 18 accessibility contrast failures that also fail on `main`.
