# US-008 — Seller Chooses Listing Plan: QA Testing Guide

**Sprint 2 · Seller Listing Creation**

Manual test cases for choosing a listing plan on a finished draft: `POST /api/v1/listings/{listingId}/plan-selection`, the
plan snapshot on the listing, the payment request through US-117 (dummy gateway), and the app's plan page, review page
and test checkout. No money is charged.

> **What this story ships:** `PlanSelectionService` and the plan-selection endpoint; migration `V20`
> (`plan_price`, `plan_validity_days`, `plan_price_includes_gst` on `listings`); `planCode` on the draft response;
> `ListingPaymentCompletedHandler` (no-op until US-009); the app's Review & Publish page and its error messages.
> **Not in this story:** moving the listing to `PLAN_PAYMENT_SUCCESS` after a paid callback, review and publication (US-009,
> US-084). Until they exist a paid listing stays in `PLAN_PAYMENT_PENDING`.

| Setting | Value |
|---|---|
| Backend base URL | `http://localhost:8080` |
| Migration | `V20` (Flyway runs on start) |
| Gateway | `PAYMENT_PROVIDER=mock` (default in `dev`); see `US-117-Testing-Guide.md` |
| Plans (seed) | BASIC ₹49 (7 days), BOOSTED ₹149 (7 days), PRIORITY ₹249 (30 days); prices include GST |
| Errors | `ERROR_INCOMPLETE_LISTING` · `ERROR_MIN_PHOTOS_REQUIRED` · `ERROR_MAX_LISTINGS_REACHED` · `ERROR_PLAN_SELECTION_NOT_ALLOWED` · `PLAN_NOT_FOUND` (404) · `AADHAAR_VERIFICATION_REQUIRED` (403) · `ERROR_GATEWAY_UNAVAILABLE` (503) · the US-007 errors |

---

## Prerequisites

1. PostgreSQL and Redis from `valuex-backend/docker-compose.yml`; start the backend (`mvn spring-boot:run`).
2. Two `ACTIVE` sellers with Aadhaar verified and access tokens: `$TOKEN` (seller A) and `$TOKEN_B` (seller B).
3. A complete draft of seller A with a cleared restricted check: at least 2 READY photos (`US-004-Testing-Guide.md`),
   a category, title, description and price saved through `PATCH /api/v1/listings/{id}` (`US-114`, `US-006`), then
   `POST /api/v1/listings/{id}/restricted-check` returns `SAFE` (`US-007-Testing-Guide.md`). Note its id as `$LISTING`.

Choose a plan:

```powershell
curl.exe -s -X POST "http://localhost:8080/api/v1/listings/$LISTING/plan-selection" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{\"planCode\":\"BOOSTED\"}'
```

---

## Test cases

| ID | Acceptance criterion / edge case | Steps | Expected |
|---|---|---|---|
| TC-001 | Migration | Start the backend; `SELECT version FROM flyway_schema_history WHERE version = '20';` | One successful row; `listings` has `plan_price`, `plan_validity_days`, `plan_price_includes_gst` |
| TC-002 | A paid plan returns the checkout details | Choose `BOOSTED` | 200, `paymentRequired` true, `listingStatus` `PLAN_PAYMENT_PENDING`, `amount` 149, `payment.orderId` `mock_order_...`, `payment.publicKey` `mock_public_key`, `payment.expiresAt` 30 minutes ahead; no secret in the body |
| TC-003 | Listing and payment state | After TC-002: `SELECT status, plan_type, plan_price, plan_validity_days, plan_price_includes_gst FROM listings WHERE id = '<id>'`; `SELECT status, amount FROM payments WHERE reference_id = '<id>'` | Listing `PLAN_PAYMENT_PENDING`, `BOOSTED`, 149, 7, true; one payment `PAYMENT_PENDING` for 149; `listing_status_history` has CREATE, `SUBMIT_FOR_PLAN`, `SELECT_PLAN` |
| TC-004 | Amount comes from the server | Send `{"planCode":"BOOSTED","amount":1}` | Same answer as TC-002; the extra field is ignored |
| TC-005 | Same plan again returns the same order | Repeat TC-002 | Same `payment.paymentId` and `orderId`; still one payment row |
| TC-006 | Another plan replaces the unpaid one | Choose `PRIORITY` after TC-002 | `amount` 249; the first payment is `PAYMENT_FAILED` with `failure_reason` `SUPERSEDED`; one `PAYMENT_PENDING` payment for 249; the listing's `plan_type` is `PRIORITY`; history shows `RESELECT_PLAN` and `SELECT_PLAN` |
| TC-007 | The snapshot does not change later | After TC-002: `UPDATE plans SET discounted_price = 199 WHERE code = 'BOOSTED';` | The listing still has `plan_price` 149 and the open payment 149 |
| TC-008 | Plan priced at zero needs no payment | `UPDATE plans SET discounted_price = 0 WHERE code = 'BASIC';` choose `BASIC` on a fresh complete draft | 200, `paymentRequired` false, `payment` null, `listingStatus` `PLAN_PAYMENT_SUCCESS`; no `payments` row; the log says the plan is paid and no publication step is installed. Restore the price afterwards |
| TC-009 | Incomplete draft | Choose a plan for a draft without a title or price | 400 `ERROR_INCOMPLETE_LISTING` |
| TC-010 | Photos | Draft with one photo | 400 `ERROR_MIN_PHOTOS_REQUIRED` |
| TC-011 | Restricted check required | Edit the title after the check, or never check, then choose a plan | 400 `ERROR_RESTRICTED_CHECK_REQUIRED`; a blocked item gives its US-007 error |
| TC-012 | Aadhaar | Call with a token of a seller whose Aadhaar is not verified | 403 `AADHAAR_VERIFICATION_REQUIRED` |
| TC-013 | Unknown or inactive plan | `{"planCode":"NOPE"}`; `UPDATE plans SET is_active = FALSE WHERE code = 'BOOSTED'` then choose it | 404 `PLAN_NOT_FOUND` both times; restore afterwards |
| TC-014 | Missing code | `{}` | 400 `VALIDATION_ERROR` |
| TC-015 | Ownership | Seller B chooses a plan for seller A's draft; no token | 404 `LISTING_NOT_FOUND`; 401 |
| TC-016 | Too late to choose | Choose a plan for a listing in `PLAN_PAYMENT_SUCCESS` or later | 400 `ERROR_PLAN_SELECTION_NOT_ALLOWED` |
| TC-017 | Active listing cap | Start with `VALUEX_LISTING_MAX_ACTIVE_LISTINGS=1` (or create 50 listings); seller A has another active listing | 400 `ERROR_MAX_LISTINGS_REACHED`; sold, expired, deactivated, removed and rejected listings do not count |
| TC-018 | Gateway not configured | Start with `SPRING_PROFILE=staging` and no `PAYMENT_PROVIDER`; choose a paid plan | 503 `ERROR_GATEWAY_UNAVAILABLE`; the listing stays in its old status and no payment row is left |
| TC-019 | Payment fails, then another try | After TC-002 simulate failure (`US-117-Testing-Guide.md`, `simulate` with `FAILURE`), then choose the same plan again | A new payment (new `orderId`) is created for the same amount; the old one stays `PAYMENT_FAILED` |
| TC-020 | The app can resume | `GET /api/v1/listings/$LISTING` after TC-002 | `planCode` `BOOSTED`, `status` `PLAN_PAYMENT_PENDING` |

### App cases (emulator, `dev_android.json`)

| ID | Steps | Expected |
|---|---|---|
| TC-A01 | Finish Item Details for a clean item, tap **Choose Listing Plan**, pick a plan, tap **Review Listing** | The button shows a spinner, then the Review & Publish page opens |
| TC-A02 | Read the review page | Title, category path, price and description of the item; the plan name and "Valid for N days"; the breakdown with "Inclusive of GST"; the note about the Trust & Safety team; the button "Pay ₹149 & Publish" |
| TC-A03 | Tap **Pay**, then **Pay** in the test sheet | The sheet closes, a message says "Payment received, your listing is under review", the app goes to Home. The listing stays `PLAN_PAYMENT_PENDING` until US-009 |
| TC-A04 | Tap **Pay**, then **Fail** | "Your payment did not go through. You have not been charged."; stay on the page; tapping Pay again opens a new test checkout (a new order) |
| TC-A05 | Tap **Pay**, then **Cancel** | Stay on the page; tapping Pay again opens the checkout for the same order |
| TC-A06 | Stop the backend after tapping Pay in the sheet | After about 60 seconds: "We're confirming your payment"; nothing says the payment succeeded |
| TC-A07 | Plan page with a plan priced at zero | The review page shows **Publish** with no amount; tapping it says "Your listing is under review" and goes Home; no checkout opens |
| TC-A08 | Seller without Aadhaar taps **Review Listing** | "Please complete Aadhaar verification to proceed" and the Aadhaar page opens |
| TC-A09 | Draft with 50 other active listings | "You've reached the maximum listing limit"; stay on the plan page |
| TC-A10 | Staging config (no `PAYMENT_PROVIDER`) and a backend without a gateway | "Payments are not available at this moment, please try again later" |
| TC-A11 | Switch to Hindi; set the largest system text size | The page is in Hindi and shows without overflow; the pay button stays reachable above the message bar |

---

## Running the automated tests

Backend (Docker must be running for the integration tests):

```powershell
cd valuex-backend
$env:JAVA_TOOL_OPTIONS='-Duser.timezone=Asia/Kolkata'
mvn verify '-Dtestcontainers.version=1.21.4'
mvn checkstyle:check
```

Only this story:

```powershell
mvn test '-Dtest=PlanSelectionServiceTest,ListingPlanControllerTest,PlanSelectionIntegrationTest,ListingControllerTest'
```

Mobile:

```powershell
cd valuex-mobile
flutter gen-l10n
flutter analyze
flutter test test/features/listing
```

(The 18 accessibility contrast tests that fail on `main` are not part of this story.)

Results at hand-over: backend `mvn clean verify` 1137 tests, 0 failures (this story: 18 `PlanSelectionServiceTest`, 1 controller test and
10 Testcontainers integration tests in `PlanSelectionIntegrationTest`); Checkstyle and the JaCoCo gate pass; SonarQube gate OK
(0 new issues, 93.7 % coverage on new code). Mobile: `flutter analyze` no issues; all 191 tests in `test/features/listing` pass; changed
files 98 to 100 % line covered (`review_listing_screen` 99/100, `plan_selection_controller` and `plan_selection` 100 %); the full suite shows
only the 18 accessibility contrast failures that also fail on `main`.
