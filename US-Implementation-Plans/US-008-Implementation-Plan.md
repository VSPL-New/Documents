# US-008: Seller Chooses Listing Plan — Implementation Plan

> **Update (2026-10-25, category taxonomy):** Plans will vary by L1 category (US-119); until then all categories use the current plans and Real Estate listings use them too. US-006 adds a Dev-only banner "Plan is under revision until US-119" to the plan page. "Item details complete" means every required field of the category's listing schema (US-006), and the primary-category check becomes the L3-category check. The price maximum is ₹10,00,00,000. Migration numbers shift.

## 1. Header

| Field | Value |
|---|---|
| Story ID | US-008 |
| Title | Seller Chooses Listing Plan |
| Sprint | Sprint 2 — Seller Listing Creation |
| Story Points | 5 |
| Repos | valuex-backend, valuex-mobile |
| Dependency | US-078 (plan catalog, tax settings and the plan page); **US-117 (payment port, dummy gateway, `payments` tables, checkout wrapper)**; US-089 (`ListingLifecycleService`, states); US-007 (`RestrictedItemGate`); US-114 (complete item details); US-004 (Aadhaar check before plan selection). Must be built **before** US-009 and US-084, which are delivered together after it |

**Scope decisions (2026-10-16):**
1. Seller flow: Item Details (US-114) → restricted item check (US-007) → Aadhaar check if needed (US-004) → **plan selection and review page (this story)** → payment → webhook (US-009) → Trust & Safety review (US-084) → publication on approval.
2. This story owns plan selection, the plan price snapshot on the listing, the request for a payment and the Review page. It does **not** confirm a payment: only the signed gateway callback does that (US-117, then US-009 for the listing). The app shows "payment received" only after the server says so.
3. The payment itself is **US-117** (gateway-neutral): a payment port, a **dummy gateway** (its `mock` provider), `payments` and `payment_attempts` tables, the callback endpoint and the app checkout wrapper. The gateway is not decided and talks with a provider are in progress, so this story is built and tested only against the dummy gateway; it never names a real gateway. `valuex.payment.provider` is owned by US-117.
4. Upgrading a live listing is out of scope (US-064).
5. Plans are dynamic and managed by the admin console (US-116): this story never refers to a plan by name in logic. The plan is chosen by code from the catalog, the price and validity are copied onto the listing when the plan is selected, and a price of zero means no payment. Prices include GST for now (US-078 tax settings).

## 2. Story Recap

**As a** seller **I want to** choose a listing plan **so that** I can control visibility and reach.

**Acceptance Criteria** (`Documents/user-stories.md`):
- After I complete my draft and proceed, if I have not completed Aadhaar verification I am asked to do it first (US-004), then shown the plans.
- I see the plans configured by the platform (US-078); when I select one I see the price (shown as including GST); a plan with a price takes me to payment.
- When payment succeeds my listing goes to the Trust & Safety review and is published when approved (US-009, US-084).

**Edge Cases:** seller cancels payment · payment fails · seller closes the app before paying · plan upgrade on an existing listing (US-064) · plan validity ending.

**Validation Rules:** draft must be complete before plan selection · a plan priced at zero needs no payment · a priced plan needs a successful payment before review and publishing · plan duration starts at publication · the price and validity charged are the ones shown when the plan was selected · at most 50 active listings per seller.

**Error Scenarios:** `ERROR_PAYMENT_FAILED` · `ERROR_INCOMPLETE_LISTING` · `ERROR_MAX_LISTINGS_REACHED` · `ERROR_AADHAAR_VERIFICATION_REQUIRED` · `ERROR_RESTRICTED_ITEM` (from US-007).

## 3. Design Reference

- Primary source: [Sprint-2-Seller Listing Creation-LLD.md — Part H](../LLD/Sprint-2-Seller%20Listing%20Creation-LLD.md#part-h---us-008-seller-chooses-listing-plan) (updated 2026-10-16), with Part G (plans), Part E (states), Part I (webhook).
- HLD Part 7 §21 payment gateway integration; HLD Part 3 §4.7 payments tables. The LLD's Razorpay names (`razorpayOrderId`, `X-Razorpay-Signature`) are read as the gateway-neutral names of US-117.
- Figma Make (`tzrpUwfrR0SYeyKkv1p0co`): `ListingPlanScreen.tsx` (plan cards, built in US-078) and the **Review & Publish** step in `CreateListingScreen.tsx` (photo strip, details summary, plan summary, "Trust & Safety Review" note, "Pay ₹X & Publish" button).

**What already exists in the code:**
- `PaymentState` and `PaymentStateMachine` (`PAYMENT_INITIATED → PAYMENT_PENDING → PAYMENT_SUCCESS / PAYMENT_FAILED`, plus escrow and refund states). No `payments` table, entity, gateway client or controller yet.
- `ListingDraftService`, `ListingController`, `Listing.planType`; Aadhaar verification and `aadhaarVerified` on the account; RestClient provider-adapter pattern with `@ConditionalOnProperty` (`AddressProviderConfig`).
- Spring scheduling and Redis cache are enabled.

**Key design decisions:**
- `PlanSelectionService.selectPlan(listingId, sellerId, planCode)` follows LLD §H.5 with the updated entry rule: the listing must be a `DRAFT` (or in plan selection or payment failed, when re-selecting), complete, with a cleared US-007 check, and the seller's Aadhaar verified.
- One open payment per listing: selecting the same plan again returns the existing order; selecting another plan cancels the unpaid order and creates a new one.
- Amounts are computed on the server from the plan catalog, never taken from the app. Because prices include GST, the plan price is the amount charged; the amount is sent to the gateway in paise by US-117.
- The plan price and validity days are copied onto the listing when the plan is selected (`plan_price`, `plan_validity_days`, `gst_inclusive`). US-009 uses the copied validity for `expires_at`, so an admin change after selection never alters an existing listing or an open payment.
- A plan with a zero price (none today; Basic is ₹49) skips the gateway and calls US-009's `ListingPaymentCompletedHandler`. This path has no plan-code check; it is decided only by the price being zero.

## 4. Implementation Steps

### Database Migration — `valuex-backend`
- [ ] `V20__listing_plan_snapshot.sql` (US-007 took `V18` and US-117 is planned as `V19`, which holds the `payments` and `payment_attempts` tables; renumber at implementation time if the order changes): add nullable `plan_price NUMERIC(10,2)`, `plan_validity_days INT` and `plan_price_includes_gst BOOLEAN` to `listings`. The `payments` tables are not created here.

### Backend — Payments (from US-117)
- [ ] Use US-117's payment service to create a payment for the listing (reference type `LISTING_PLAN`, reference ID the listing ID, amount from the plan snapshot); it returns what the app checkout needs. This story adds no gateway adapter, no tables and no callback handling.
- [ ] Until US-117 is merged, develop against its port interface; US-117 is built first (see Open Gaps).

### Backend — Domain
- [ ] Add the transition `PLAN_PAYMENT_PENDING → PLAN_SELECTION_PENDING` with action `RESELECT_PLAN` (US-089 table), so a seller can pick another plan before paying.

### Backend — `PlanSelectionService` and API
- [ ] `POST /api/v1/listings/{listingId}/plan-selection` with `{ "planCode": "BOOSTED" }`; seller from the security context only.
- [ ] Checks in order: owner and status; item details complete (including a primary category, from US-006) and at least 2 photos (`ERROR_INCOMPLETE_LISTING`); `RestrictedItemGate.requireCleared`; Aadhaar verified (`ERROR_AADHAAR_VERIFICATION_REQUIRED`); active-listing cap of 50 (`ERROR_MAX_LISTINGS_REACHED`, counting every status except `SOLD`, `EXPIRED`, `DEACTIVATED_BY_SELLER`, `REMOVED_BY_ADMIN`, `REJECTED`); plan exists and is active.
- [ ] Transitions through `ListingLifecycleService`: `DRAFT → PLAN_SELECTION_PENDING → PLAN_PAYMENT_PENDING` (price above zero), copy the plan price, validity days and tax mode onto the listing, set `listings.plan_type`; create the payment through US-117 (`PAYMENT_INITIATED`); return the order ID, amount, currency and the public key the app needs.
- [ ] Zero-price plan: no payment and no gateway call; call `ListingPaymentCompletedHandler.onPaymentSuccess` (US-009).
- [ ] Standard `ApiResponse` envelope and central exception handling; no payment secrets in logs.
- [ ] Extend the draft response with `planCode` so the app can resume after the app was closed during payment.
- [ ] The scheduled job that returns unpaid listings to plan selection after 30 minutes belongs to US-009.

### Mobile (Flutter)
Follow `nova-figma-to-code` for the Review & Publish step (call the Figma MCP for the Make file, check drift, reuse components, record the mapping).
- [ ] Wire the plan page from US-078: **Review Listing** calls `plan-selection` and opens the Review page; an Aadhaar-not-verified response routes to the existing Aadhaar verification and comes back to the plan page.
- [ ] `ReviewListingScreen` (Review & Publish): photo strip, details summary (title, category, condition, location, description, price), plan summary (name, validity, amount), the Trust & Safety note with "usually within a few hours", and the button "Pay ₹{amount} & Publish".
- [ ] Plan page from US-078 shows prices as inclusive of GST; the Review page shows the plan price once with "Inclusive of GST"; a zero price shows "Publish" with no amount and goes straight to the review message.
- [ ] Payment checkout: call the app's payment checkout interface from US-117 with the order details; this story does not depend on any gateway SDK; the app never marks a payment as successful itself.
- [ ] After checkout returns, poll the listing status (with a limit) until it shows payment received (`PLAN_PAYMENT_SUCCESS` or later), then show "Payment received, your listing is under review" and go to My Listings; if it does not confirm in time, show a message that the payment is being confirmed and keep checking on resume.
- [ ] Handle: checkout cancelled (stay on the Review page, order kept, can retry or change plan), payment failed (message `ERROR_PAYMENT_FAILED`, retry or another plan), app killed mid-payment (on reopen, the draft shows its plan state and offers to continue or change plan).
- [ ] Errors mapped in `listing_error_messages.dart`; strings in English and Hindi; tokens only; 48 dp tap targets; accessibility guideline tests.
- [ ] With the dummy gateway (US-117) the whole flow works in development and testing: **Pay ₹{amount} & Publish** opens the test checkout (Pay, Fail, Cancel); Pay settles through the same signed callback a real gateway will use, then the listing moves on; Fail shows `ERROR_PAYMENT_FAILED` with retry or change plan; Cancel stays on the Review page. No money moves.

### Documentation/Quality
- [ ] OpenAPI example for `plan-selection`; update LLD Part H where the implementation differs.
- [ ] After implementation, create `Documents/Manual Testing Guides/US-008-Testing-Guide.md`.

## 5. Test Plan

Target >90% coverage for new code (`CLAUDE.md`).

### Backend Unit Tests
- [ ] Paid plan: transitions `DRAFT → PLAN_SELECTION_PENDING → PLAN_PAYMENT_PENDING`, `plan_type` and the price, validity and tax snapshot set, US-117's payment service called once with the catalog price, response has order ID and amount.
- [ ] Snapshot: changing the plan's price or validity after selection does not change the listing's snapshot or the open payment amount.
- [ ] Same plan selected twice returns the same order; another plan cancels the unpaid payment and creates a new order.
- [ ] Rejections: not owner, wrong status, incomplete details, fewer than 2 photos, restricted gate not cleared, Aadhaar not verified, 50 active listings, unknown or inactive plan.
- [ ] Amount comes from the server catalog; a price sent by the client is ignored.
- [ ] Zero-price plan (a catalog row with price 0, any code) calls the payment-completed handler and never US-117's payment service.
- [ ] Payment service error (gateway unavailable): listing returns to plan selection, no stray payment row left pending, `ERROR_GATEWAY_UNAVAILABLE`.

### Backend Integration Tests (Testcontainers PostgreSQL)
- [ ] `V20` applies; `POST /plan-selection` end to end with the dummy gateway; IDOR (another seller gets not found).
- [ ] Re-selecting a plan from `PLAN_PAYMENT_PENDING` works through `RESELECT_PLAN`.

### Mobile Tests (Flutter)
- [ ] Plan page to Review page flow with fakes; Aadhaar-required response routes and returns.
- [ ] Review page shows the right summary and amount; checkout cancelled, failed and succeeded paths; polling stops at the limit.
- [ ] Resume after app restart with a pending payment.
- [ ] Accessibility checks in English and Hindi.

## 6. Validation Checklist

- [ ] No listing can reach plan selection without a cleared restricted check, verified Aadhaar and complete details.
- [ ] The charged amount always comes from the server plan catalog and the listing snapshot.
- [ ] No code path depends on a plan's name or code, or on there being a free plan.
- [ ] The app never treats a payment as successful before the server confirms it.
- [ ] A seller can change plan before paying and can retry after a failure; no double charge for one listing.
- [ ] No gateway name, SDK, key or secret appears in this story's code.
- [ ] All status changes go through `ListingLifecycleService`; payment status through `PaymentStateMachine`.
- [ ] Checkstyle, full tests, coverage, SonarQube (backend) and Flutter analyze and tests (mobile) pass before push.

## 7. Open Gaps / Questions

1. **Basic price (decided 2026-10-16).** Basic is ₹49 and there is no free plan; a plan set to zero by management is free and uses the zero-price path. The story text of US-008 is updated.
2. **Payment gateway (decided 2026-10-16: not chosen yet).** Gateway choice, account, keys and the app SDK are US-117's open items; this story is independent of them.
3. **Taxes (decided 2026-10-16).** Prices include GST and the tax mode and rate are configurable (US-078, US-116). The GST amount shown on the Review page is informational; invoice generation is not in this story and needs a finance decision.
4. **Order of work.** US-117 must be built before this story. If it is not ready, only the port interface and the dummy gateway of US-117 are needed here.
5. **Changing plan after payment** is out of scope (US-064).
6. **Cancelled orders at the gateway (decided in US-117).** An unpaid order is not cancelled at the gateway when the seller picks another plan: the old payment is failed locally (`supersedeOpenPayment`, reason `SUPERSEDED`) and the gateway order expires. If it is paid anyway, US-117 reports a late success and US-009 flags it for refund review.
7. **Dependency order.** US-008 comes before the US-009 + US-084 pair; it calls `ListingPaymentCompletedHandler`, which that pair provides, so for development the handler is introduced as an interface with a no-op default that the pair replaces.
8. **Readiness check (2026-10-29).** Built: US-078 (`PlanCatalogService`, plan page), US-089 (`ListingLifecycleService`), US-114, US-006 and US-005. Not built: **US-007** (`RestrictedItemGate`) and **US-117** (payment port, `payments` tables). The latest migration is `V17` (US-005). Build order chosen on 2026-10-29: US-007 first (`V18`), then US-117 (`V19`), then this story (`V20`); the `V18`/`V19` numbers above shift accordingly. This story cannot be implemented end to end until US-117 (at least its port and sandbox adapter) and US-007 exist.
9. **Readiness check (2026-10-30).** US-007 is now built: `RestrictedItemGate.requireCleared(listingId)` exists on the `feature/US-007-restricted-items-prevention` branches (pull requests: backend #42, valuex-ai #3, valuex-mobile #46, open, not yet merged); the latest migration is `V18`. **US-117 is still not built**, so this story is blocked until at least its payment port, dummy gateway and `payments` tables are on `main`. Order: US-117 first (`V19`), then this story (`V20`).
10. **Dummy gateway (decided 2026-10-30).** Because talks with a payment gateway provider are still in progress, US-117 delivers a dummy gateway first and this story builds on it. Nothing in this story changes when a real gateway replaces it. Where the dummy checkout may run is decided in US-117 Open Gap 9: `dev` only, never prod.
11. **Zero-price path and the dummy gateway.** The zero-price path never reaches the gateway, so it behaves the same with the dummy or a real gateway.

---

**Status:** Approved (2026-10-30; the user approved the plan, built on the dummy gateway of US-117; migration `V20`; implement after US-117).

## 8. Implementation Notes (deviations from the plan as built, 2026-10-31)

1. **Readiness.** US-007 (#42, #46) and US-117 (#43, #48) were merged to `main` first; this story is built on them, migration `V20`.
2. **State machine.** `PLAN_PAYMENT_PENDING → PLAN_SELECTION_PENDING` (`RESELECT_PLAN`) and `PLAN_PAYMENT_FAILED → PLAN_PAYMENT_PENDING` (`RETRY_PAYMENT`) already existed from US-089, so no state machine change was needed.
3. **Aadhaar check.** Done by the existing `@RequiresIdentityVerification` interceptor, so the error code is `AADHAAR_VERIFICATION_REQUIRED` (which the app already maps), not `ERROR_AADHAAR_VERIFICATION_REQUIRED`.
4. **Gateway failure.** `ERROR_GATEWAY_UNAVAILABLE` rolls back the whole selection, so the listing stays where it was (for example `DRAFT`), rather than moving to plan selection. Nothing is left pending.
5. **Charged amount.** The amount is `TaxSettings.totalAmount(plan price)`: the plan price in inclusive mode, price plus GST in exclusive mode. The snapshot stores the plan's listed price and the GST mode.
6. **Same plan again.** In `PLAN_PAYMENT_PENDING` with the same plan the listing is not moved; the snapshot is refreshed and `PaymentService.createOrReuse` returns the same order when the amount is unchanged, or replaces it when the catalog price changed. After a failed payment the same plan uses `RETRY_PAYMENT`; another plan uses `RESELECT_PLAN` then `SELECT_PLAN`.
7. **Handler.** `ListingPaymentCompletedHandler` (interface) has a logging default from `ListingPaymentHandlerConfig`; US-009 replaces it. Until US-009 listens to `PaymentSucceededEvent` and `PaymentFailedEvent`, a paid listing stays in `PLAN_PAYMENT_PENDING` after the gateway confirms the payment.
8. **Completeness check.** "Complete" means title, description, category and price are set (the details save already validates the rest per category) and at least 2 photos.
9. **Review page, mobile.** The summary shows title, category path, price and description; the photo strip, condition and location are not shown because the draft carries no photo read URLs and the plan page is only given the fields above. The Figma Make file was not re-read (no Figma tool was available); the page reuses existing components and tokens, so a design pass is still open.
10. **After payment.** The app returns to Home with a message ("Payment received, your listing is under review" or "We're confirming your payment"); My Listings does not exist yet. It does not poll the listing status: it uses the payment status of US-117's `PaymentFlow`, which only trusts the server.
11. **Resume and Aadhaar.** There is no draft-resume entry point in the app yet, so "reopen and continue" is not built (the draft response now carries `planCode` for it). After an Aadhaar-required answer the app opens the Aadhaar page; where it returns afterwards is the existing Aadhaar flow's behaviour.
12. **Active cap.** `valuex.listing.max-active-listings` (default 50).
