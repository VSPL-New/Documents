# US-084: Pre-Publication Trust & Safety Review — Implementation Plan

> **Update (2026-10-25, category taxonomy):** the review also covers Conditional-category and Real Estate listings, including the seller's compliance acceptance (US-007). The `categories_unrelated` signal no longer exists because multi-category tagging was dropped.

## 1. Header

| Field | Value |
|---|---|
| Story ID | US-084 |
| Title | Pre-Publication Trust & Safety Review |
| Sprint | Sprint 2 — Seller Listing Creation |
| Story Points | 5 |
| Repos | valuex-backend, valuex-mobile (status display only). `valuex-ai` is out of scope (separate team, integrated later) |
| Dependency | US-007 (restricted-item gate); **US-009, developed and delivered together with this story** ([plan](US-009-Implementation-Plan.md): one branch, one pull request); US-089 ([plan](US-089-Implementation-Plan.md), built first: `ListingLifecycleService`, reconciled listing states, key-state notifications); US-005 (shared `valuex.ai.enabled` switch, `AiGatewayClient`, Resilience4j) |

**Combined delivery (2026-10-16):** US-009 and US-084 are built together because payment success hands the listing to this review and approval triggers publication. See "Combined delivery" in the US-009 plan for the build order and the shared end-to-end tests. Review attempts are 3 in total per paid plan (the first review is attempt 1).

**Scope decisions (2026-10-16):**
1. AI is assumed disabled or down, so **no fraud score is computed**.
2. **Until the admin console UI arrives, the review auto-approves.** Every listing that reaches the review without an AI score moves to `APPROVED` and the decision is recorded as `AUTO_APPROVED_NO_AI` so these listings can be identified and re-reviewed later.
3. The **trusted-seller bypass still applies** when AI is off (rating above 4.5 and 50+ sales), because it does not need AI.
4. Switching to real human moderation later is a configuration change, `valuex.moderation.manual-review-enabled=true` (default `false`): AI-off listings then go to `QUEUED_FOR_REVIEW` instead of auto-approving.
5. Admin approve/reject **endpoints are not exposed** in this story. There is no admin authentication or role model yet (Sprint 10), and exposing them ahead of that would be unsafe. The decision logic is built as services, in the same way as `UserStateService`, and the controllers are added with the admin console (US-054).
6. **Three review attempts per paid plan (2026-10-16).** Every review that does not approve the listing is a failed attempt. After attempt 1 or 2 the listing becomes `REVISION_REQUIRED` and the seller is notified to modify it; the seller resubmits without paying again. After the 3rd failed attempt the listing becomes `REJECTED` (final), the seller is notified and the plan fee is refunded: the payment is moved to `REFUND_REVIEW` (an existing payment state). Whether the refund is then issued automatically or by finance is decided later, so no gateway refund call is built here.

## 2. Story Recap

**As a** platform **I want** all listings reviewed before publication **so that** prohibited items and fraud are prevented.

**Acceptance Criteria** (`Documents/user-stories.md`):
- When the seller's plan payment succeeds (US-008, US-009), the listing enters `TRUST_SAFETY_REVIEW`.
- AI checks: restricted item detection, image analysis, text analysis, price reasonableness, seller reputation.
- Fraud score below 70 auto-approves; above 70 queues for manual review, and an admin reviews within 24 hours.
- Admin approves → listing proceeds; admin rejects → seller notified with reason and can revise and resubmit without paying again (3 review attempts in total); after the third failed review the listing is closed and the plan fee is refunded.

**Edge Cases:** AI false positive · borderline item (toy weapon) · coded language · review backlog · seller disputes rejection.

**Validation Rules:** every listing must pass review before publication · trusted sellers auto-approve · 24-hour manual review SLA · specific rejection reason · seller can appeal · appeals reviewed by a senior moderator.

**Error Scenarios:** `LISTING_UNDER_REVIEW` · `LISTING_REJECTED` · `LISTING_REJECTED_FINAL` (new, third failed attempt) · `APPEAL_SUBMITTED`.

## 3. Design Reference

Primary source: [Sprint-2-Seller Listing Creation-LLD.md — Part F](../LLD/Sprint-2-Seller%20Listing%20Creation-LLD.md#part-f---us-084-pre-publication-trust--safety-review), §F.1–F.9, and Part E (US-089) for the transition guard.

**Key design decisions:**
- `TrustSafetyReviewService.review(listingId)` moves the listing to `TRUST_SAFETY_REVIEW` through `ListingLifecycleService`, then decides:

| Situation | Decision (`auto_decision`) | Result |
|---|---|---|
| Trusted seller (rating above 4.5, 50+ sales) | `TRUSTED_SELLER_BYPASS` | `APPROVED` |
| AI on, score below 70 | `AUTO_APPROVED` | `APPROVED` |
| AI on, score 70 or above | `QUEUED_FOR_REVIEW` | stays in review, 24h SLA |
| AI off or down, manual review switched off (default) | `AUTO_APPROVED_NO_AI` | `APPROVED` |
| AI off or down, manual review switched on | `QUEUED_FOR_REVIEW` (`score_breakdown` null) | stays in review, 24h SLA |

- AI is never a reason to reject: an AI outage never blocks a listing and never raises an error to the seller.
- Failed attempts are counted per paid plan from the `listing_trust_safety_reviews` rows (`attempt_number`). The third failed attempt moves the listing `TRUST_SAFETY_REVIEW → REJECTED` (final, no outgoing transitions) and publishes a `ListingRefundDueEvent`; the payment side (US-009) moves the payment to `REFUND_REVIEW`. A renewal (new plan purchase) starts a fresh count.
- Approve and reject decisions (for the later console) go through the same lifecycle guard, so the audit trail in `listing_status_history` is identical for automatic and manual decisions.
- The US-007 restricted-item check always runs before this review, so with AI off the rule-based restricted-item check is still the real safeguard. The review auto-approving is an accepted product trade-off until moderators exist.

## 4. Implementation Steps

### Database Migration — `valuex-backend`
- [ ] `listing_trust_safety_reviews` per LLD §F.3 with these changes: `fraud_score` nullable (no score without AI), and `auto_decision` allows `AUTO_APPROVED_NO_AI` in addition to `AUTO_APPROVED`, `QUEUED_FOR_REVIEW`, `TRUSTED_SELLER_BYPASS`. Add `attempt_number`, `sla_deadline`, `rejection_reason`, `admin_id`, `admin_decision`, `reviewed_at`, `score_breakdown` (JSONB, nullable). Use the next free Flyway version after US-007's.
- [ ] Indexes on `listing_id` and a partial index for pending queue rows (`QUEUED_FOR_REVIEW` with no `admin_decision`).
- [ ] `listing_trust_safety_appeals` (review ID, seller ID, reason, status `PENDING`/`UPHELD`/`OVERTURNED`, resolver, timestamps), following the US-007 appeal table.

### Backend — Configuration
- [ ] `valuex.moderation.manual-review-enabled` (default `false`), `valuex.moderation.review-sla-hours` (default 24) and `valuex.moderation.max-review-attempts` (default 3), added to `ValuexProperties` and `application.yml`.

### Backend — AI Path (no AI logic)
- [ ] Add `computeFraudScore` to `AiGatewayClient` (LLD §F.5 contract: score 0–100 and a breakdown of image, text, price and reputation scores) with its own Resilience4j instance, used only when `valuex.ai.enabled=true`. Price reasonableness in the score depends on the price-suggestion design, which is on hold; the request simply omits price until then.
- [ ] Any failure or open circuit is treated as "AI unavailable", never as an error.

### Backend — Review Service
- [ ] `TrustSafetyReviewService.review` implementing the table above, using `ListingLifecycleService.transition` for every status change.
- [ ] `SellerReputationPort` returning rating and completed sales. Ratings (Sprint 8) and orders do not exist yet, so the first adapter returns "no reputation data", which means no seller is trusted until real data exists.
- [ ] Persist a `listing_trust_safety_reviews` row for every decision, including bypass and auto-approvals.
- [ ] Reject a review request unless the listing is in the state that precedes review and has a current cleared US-007 check (`RestrictedItemGate.requireCleared`).
- [ ] Decision methods for the later console: `approve(listingId, adminId)`, `reject(listingId, adminId, reason)` (reason mandatory and specific), `requestRevision(listingId, adminId, reason)`. A review that does not approve counts as a failed attempt whether it was a reject or a revision request: attempts 1 and 2 move the listing to `REVISION_REQUIRED`, attempt 3 moves it to `REJECTED`. A revision-required listing is revised in place (US-114) and sent back to review through US-089's `RESUBMIT`, without paying again; US-007 runs again before resubmission. They are plain services with no controller in this story.
- [ ] Seller notifications for approval, rejection and revision are built by US-115 (Listing Lifecycle Notifications) from US-089's `ListingStatusChangedEvent`. So that the message can say "review {n} of 3" and show the reason, this story publishes a `ListingReviewDecidedEvent` (listing ID, attempt number, decision, reason) with every decision. It also provides the `LISTING_UNDER_REVIEW` advisory for queued listings. The rejection reason is kept in full (500 characters) in the review row; the status history stores it trimmed to 255.
- [ ] `ListingRefundDueEvent` (listing ID, payment reference) published on the third failed attempt; the US-009 payment side listens and moves the payment to `REFUND_REVIEW`. No refund is called on the gateway in this story.
- [ ] Appeal submission by the seller for a rejection (`APPEAL_SUBMITTED`); stored `PENDING` for a senior moderator later.
- [ ] **Edit reviews (US-010).** A listing that already has `published_at` and is sent back to review after a major edit gets an edit review: add nullable `review_reason` (`INITIAL`, `EDIT`) to the review row. Edit reviews are never counted in the attempts per plan, never produce `REJECTED` or `ListingRefundDueEvent`, and a failed edit review gives `REVISION_REQUIRED` (resubmission goes through `RESUBMIT` and is again an edit review); approval moves `APPROVED → PUBLISHED` through US-009 without restarting the plan validity.
- [ ] **Category signal (US-006).** Read `listings.categories_unrelated` as one review signal (recorded in `score_breakdown` and shown to the future reviewer); with auto-approval it has no effect on the decision.

### Backend — API
- [ ] `POST /api/v1/listings/{listingId}/trust-safety-review` (called by the plan payment-success handler, and available to the seller to check status), returning the decision and the advisory message for queued listings.
- [ ] `POST /api/v1/listings/{listingId}/trust-safety-review/appeal`.
- [ ] No `/api/v1/admin/...` endpoints in this story (see Scope decision 5).

### Mobile (Flutter)
- [ ] Show the review result: approved (continue), `LISTING_UNDER_REVIEW` message when queued, `LISTING_REJECTED` with the specific reason, a revise/resubmit action and the attempts used (for example "attempt 1 of 3"), `LISTING_REJECTED_FINAL` after the third failure (listing closed, refund coming), and appeal. Messages via l10n (English and Hindi) and `listing_error_messages.dart`.

### Documentation/Quality
- [ ] OpenAPI examples; update LLD Part F for `AUTO_APPROVED_NO_AI`, the config switch and the deferred admin endpoints.
- [ ] After implementation, create `Documents/Manual Testing Guides/US-084-Testing-Guide.md`.

## 5. Test Plan

Target >90% coverage for new code (`CLAUDE.md`).

### Unit Tests
- [ ] AI off, manual review off: listing approved with `AUTO_APPROVED_NO_AI`, no gateway call, status history written.
- [ ] AI off, manual review on: listing queued with SLA deadline 24h ahead and null score.
- [ ] AI on, score 69.99 approves; 70 and above queues (boundary at 70 matches LLD).
- [ ] AI call fails, times out or circuit is open: treated like AI off; no exception reaches the seller.
- [ ] Trusted seller bypass approves with `TRUSTED_SELLER_BYPASS`, with and without AI; seller with rating 4.5 exactly or 49 sales is not trusted.
- [ ] No reputation data means not trusted.
- [ ] Review refused when the US-007 gate is not cleared, or the listing is in the wrong state.
- [ ] `reject` requires a reason; `approve`/`reject` use the lifecycle guard; invalid transitions fail with `INVALID_STATE_TRANSITION` (HTTP 400).
- [ ] Resubmit after a failed attempt goes through `RESUBMIT` (no second payment), after US-007 has been run again.
- [ ] Attempt counting: failed attempt 1 and 2 give `REVISION_REQUIRED`; failed attempt 3 gives `REJECTED` and one `ListingRefundDueEvent`; a request-revision decision counts like a reject; an approval on attempt 2 or 3 publishes normally; no resubmission is possible from `REJECTED`; a new plan purchase restarts the count.
- [ ] Appeal allowed once per rejection, only by the owner.

### Integration Tests (Testcontainers PostgreSQL)
- [ ] `POST /trust-safety-review` end to end with AI disabled (default configuration): listing ends `APPROVED`, review row and `listing_status_history` row exist.
- [ ] Same with `manual-review-enabled=true`: listing stays in `TRUST_SAFETY_REVIEW` and appears in the pending index.
- [ ] Mocked AI Gateway with scores below and above 70, and a 5xx.
- [ ] IDOR: another seller cannot trigger a review or appeal.
- [ ] No admin routes exist (404).

## 6. Validation Checklist

- [ ] With AI off the platform keeps working: every listing reaches `APPROVED` through the review with no errors.
- [ ] Every auto-approval without a score is recorded as `AUTO_APPROVED_NO_AI` so it can be audited or re-reviewed.
- [ ] Turning on `valuex.moderation.manual-review-enabled` routes AI-off listings to the queue without a code change.
- [ ] Trusted-seller bypass works with AI off; with no reputation data nobody is bypassed.
- [ ] Status changes only happen through `ListingLifecycleService`.
- [ ] Rejection always carries a specific reason, and the seller is notified.
- [ ] A seller gets exactly 3 review attempts per paid plan; the third failure closes the listing and flags the refund.
- [ ] No unauthenticated or admin-only endpoint is exposed.
- [ ] The US-007 restricted-item check is always a prerequisite.
- [ ] Checkstyle, full tests, coverage and SonarQube pass before push.

## 7. Open Gaps / Questions

1. **`ListingLifecycleService` (resolved).** Planned in [US-089](US-089-Implementation-Plan.md) and built first.
2. **Transition path to review (decided 2026-10-16).** The review runs **after payment**: `PLAN_PAYMENT_SUCCESS → TRUST_SAFETY_REVIEW` (`SUBMIT_FOR_REVIEW`), triggered when the plan payment succeeds, and before publication (`APPROVED → PUBLISHED`). The `PRICE_PENDING` and AI-detail states are not on the path. LLD §F.5/F.6 (review from `DRAFT`) is updated accordingly.
2a. **Payment trigger.** Sprint 2 payment for listing plans comes from US-008, so the review starts from its `PLAN_PAYMENT_SUCCESS` event or call; confirm how US-008 will hand over (the plan assumes a call to `TrustSafetyReviewService.review` from the payment-success handler).
2b. **Rejected after payment (decided 2026-10-16).** The seller is notified, edits the listing and resubmits it for review without paying again, up to 3 review attempts in total. After the third failed attempt the plan fee is refunded; the payment moves to `REFUND_REVIEW`. Whether the refund is automatic or manual is decided later.
2c. **Meaning of "3 attempts" (decided).** 3 reviews in total: the first review is attempt 1, so a seller sees at most 3 rejection notifications and 2 resubmissions. The limit stays configurable (`valuex.moderation.max-review-attempts`, default 3).
3. **Reputation data.** Seller rating and completed-sales counts will not exist until Sprint 8 and the order sprints, so the trusted-seller bypass has no effect for now. Accepted?
4. **Auto-approval risk.** Auto-approving with no AI and no moderator means the US-007 rule check is the only safeguard on a published listing. This follows the decision made; flag it for the later switch to manual review and consider a backlog re-review of `AUTO_APPROVED_NO_AI` listings.
5. **Notification copy (decided).** Owned by US-115, including the Hindi text.
6. **Appeals.** There is no senior-moderator role or console until Sprint 10; appeals are stored `PENDING`.
7. **Edit reviews and stuck reviews (from US-010).** One sweep job should find listings in `TRUST_SAFETY_REVIEW` with no open review row (a failed hand-over after payment or after an edit) and start the review; US-009's hand-over recovery job and this one should be the same job.

---

**Status:** Draft
