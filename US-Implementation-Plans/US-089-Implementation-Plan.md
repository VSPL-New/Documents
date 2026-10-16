# US-089: Lifecycle State - Listing — Implementation Plan

## 1. Header

| Field | Value |
|---|---|
| Story ID | US-089 |
| Title | Lifecycle State - Listing |
| Sprint | Sprint 2 — Seller Listing Creation |
| Story Points | 5 |
| Repos | valuex-backend only |
| Dependency | US-004 (listings and `listing_status_history` exist). Must be built **before** US-005, US-007, US-008, and US-009 with US-084 (delivered together), which all change listing status through it |

**Build order decision (2026-10-16):** US-089 is implemented first. US-084 (trust and safety review) and the later plan/publish stories depend on its transition guard.

## 2. Story Recap

**As a** platform **I want** to track listing lifecycle states **so that** listing status determines visibility and actions.

**Acceptance Criteria** (`Documents/user-stories.md`): a listing progresses through `DRAFT`, `PLAN_SELECTION_PENDING`, `PLAN_PAYMENT_PENDING`, `PLAN_PAYMENT_FAILED`, `PLAN_PAYMENT_SUCCESS`, `MEDIA_UPLOAD_PENDING`, `AI_DETAILS_GENERATED`, `PRICE_PENDING`, `TRUST_SAFETY_REVIEW`, `APPROVED`, `PUBLISHED`, `BUYER_INQUIRY_PENDING`, `NEGOTIATION_IN_PROGRESS`, `OFFER_ACCEPTED`, `ORDER_CREATED`, `SOLD`, `EXPIRED`, `DEACTIVATED_BY_SELLER`, `REMOVED_BY_ADMIN`, `REJECTED`, `REVISION_REQUIRED`.

**Business Rules:** cannot publish without successful plan payment · must pass `TRUST_SAFETY_REVIEW` before `PUBLISHED` · `PUBLISHED` listings are visible in search · `SOLD` listings are archived · `EXPIRED` listings can be renewed.

**Validation Rules:** state transitions are logged · seller notified at key states · visibility controlled by state · expired listings are never auto-renewed (manual only).

**Error Scenarios:** none defined in the story; the LLD adds an invalid-transition error and `LISTING_NOT_FOUND`.

## 3. Design Reference

Primary source: [Sprint-2-Seller Listing Creation-LLD.md — Part E](../LLD/Sprint-2-Seller%20Listing%20Creation-LLD.md#part-e---us-089-lifecycle-state---listing), §E.1–E.8.

**What already exists in the code (so this story is mostly reconciliation plus one service):**
- `ListingState` enum with all 21 states.
- `ListingStateMachine` (in-code, built on `common.statemachine.StateMachine`) — its main path already matches the order decided on 2026-10-16 (plan and payment first, then review), but it still routes through the unused AI-era states (see below).
- `listing_status_history` table and `ListingStatusHistory` entity (VARCHAR statuses, `changed_by`, `reason`), written today only for the initial `DRAFT` in `ListingDraftService.createDraft`.
- The same pattern is used for user accounts: `UserAccountStateMachine` plus `UserStateService.applyTransition` (check transition, save, write history, publish event).

**Key design decisions:**
- **Follow the existing code pattern, not the LLD's database objects.** The LLD proposes a Postgres `listing_status` enum and a `listing_status_transitions` table. The code already uses `VARCHAR` statuses and an in-code `StateMachine`, so this story keeps that and does not add the table. The LLD will be updated to match.
- **Sprint 2 seller flow (product owner decision, 2026-10-16: review after payment and before publishing):**
  `DRAFT → PLAN_SELECTION_PENDING → PLAN_PAYMENT_PENDING → {PLAN_PAYMENT_FAILED | PLAN_PAYMENT_SUCCESS} → TRUST_SAFETY_REVIEW → {APPROVED | REJECTED | REVISION_REQUIRED}`, then `APPROVED → PUBLISHED`. A listing can reach `PUBLISHED` only from `APPROVED`, and can reach `TRUST_SAFETY_REVIEW` only after a successful payment, so both business rules hold. The restricted item check (US-007) is not a state change; it runs while the listing is still `DRAFT`, before plan selection. This **replaces the order in LLD Part E §E.2/E.3** (review before plan), which will be updated.
- A listing that fails review is revised in place and resubmitted straight to `TRUST_SAFETY_REVIEW` (`RESUBMIT`) without paying again; the details are editable in `REVISION_REQUIRED` (US-114) and US-007 runs again before resubmission. A seller gets 3 review attempts per paid plan (2026-10-16): failed attempts 1 and 2 give `REVISION_REQUIRED`, the 3rd gives `REJECTED`, which is **final** (no outgoing transitions) and starts the plan-fee refund (US-084, US-009). The attempt count is kept by US-084, not by the state machine.
- The AI-era states `MEDIA_UPLOAD_PENDING`, `AI_DETAILS_GENERATED` and `PRICE_PENDING` stay in the enum (they are in the acceptance criteria) but are **not reachable** in Sprint 2: photos, details and price are all entered while the listing is a draft. This also suits the AI-off and price-on-hold decisions.
- `ListingLifecycleService` is the only code allowed to change `listings.status` after creation; every other module (review, plan, payment) calls it.

**Reconciled transitions** (action name in brackets; the current machine is replaced by this set):

| From | To | Action |
|---|---|---|
| `DRAFT` | `PLAN_SELECTION_PENDING` | `SUBMIT_FOR_PLAN` |
| `PLAN_SELECTION_PENDING` | `PLAN_PAYMENT_PENDING` | `SELECT_PLAN` |
| `PLAN_PAYMENT_PENDING` | `PLAN_PAYMENT_SUCCESS` / `PLAN_PAYMENT_FAILED` | `PAYMENT_SUCCESS` / `PAYMENT_FAIL` |
| `PLAN_PAYMENT_PENDING` | `PLAN_SELECTION_PENDING` | `PAYMENT_TIMEOUT` (unpaid for 30 minutes, LLD §H.8; run by the US-009 job) / `RESELECT_PLAN` (seller picks another plan before paying, US-008) |
| `PLAN_PAYMENT_FAILED` | `PLAN_PAYMENT_PENDING` / `PLAN_SELECTION_PENDING` | `RETRY_PAYMENT` / `RESELECT_PLAN` |
| `PLAN_PAYMENT_SUCCESS` | `TRUST_SAFETY_REVIEW` | `SUBMIT_FOR_REVIEW` |
| `TRUST_SAFETY_REVIEW` | `APPROVED` / `REVISION_REQUIRED` / `REJECTED` (final, third failed attempt) | `APPROVE` / `REQUEST_REVISION` / `REJECT` |
| `REVISION_REQUIRED` | `TRUST_SAFETY_REVIEW` | `RESUBMIT` |
| `APPROVED` | `PUBLISHED` | `PUBLISH` |
| `PUBLISHED` | `BUYER_INQUIRY_PENDING` → `NEGOTIATION_IN_PROGRESS` → `OFFER_ACCEPTED` → `ORDER_CREATED` → `SOLD` | unchanged from current code |
| `PUBLISHED` | `EXPIRED` / `DEACTIVATED_BY_SELLER` / `REMOVED_BY_ADMIN` | `EXPIRE` / `DEACTIVATE` / `REMOVE` |
| `EXPIRED` | `PLAN_SELECTION_PENDING` | `RENEW` (manual only) |
| `PUBLISHED` | `TRUST_SAFETY_REVIEW` | `EDIT_FOR_REVIEW` (major edit by the seller, US-010) |
| `DRAFT` / `PLAN_SELECTION_PENDING` / `PLAN_PAYMENT_FAILED` / `REVISION_REQUIRED` / `EXPIRED` | `DEACTIVATED_BY_SELLER` | `DELETE` (seller deletes the listing, US-010) |

Removed from the current machine: `PLAN_PAYMENT_SUCCESS → MEDIA_UPLOAD_PENDING`, `MEDIA_UPLOAD_PENDING → AI_DETAILS_GENERATED`, `AI_DETAILS_GENERATED → PRICE_PENDING` and `PRICE_PENDING → TRUST_SAFETY_REVIEW` (replaced by `PLAN_PAYMENT_SUCCESS → TRUST_SAFETY_REVIEW`). Also removed: `REJECTED → REVISION_REQUIRED` (`REJECTED` is now final). Added: `RESELECT_PLAN`, `PAYMENT_TIMEOUT` and `RENEW`. Everything else is as in the current code, so the change is small.

## 4. Implementation Steps

### Database Migration — `valuex-backend`
- [ ] `V13__listing_status_history_action.sql`: add nullable `action VARCHAR(50)` to `listing_status_history` so history records the action as well as the states (as `account_status_history` does). No new tables.

### Backend — State Machine
- [ ] Replace the transitions in `ListingStateMachine` with the reconciled set above, keeping the enum unchanged.
- [ ] Add small helpers on `ListingState` for the business rules: `isTerminal()` (`SOLD`, `DEACTIVATED_BY_SELLER`, `REMOVED_BY_ADMIN`, `REJECTED`) and `isLiveForBuyers()` (`PUBLISHED` only for now, see Open Gaps).

### Backend — `ListingLifecycleService`
- [ ] Add `findByIdForUpdate(UUID)` (pessimistic write lock) to `ListingRepository`, next to the existing `findByIdAndSellerIdForUpdate`.
- [ ] `ListingLifecycleService.transition(listingId, targetState, action, changedBy, reason)` in `listing/application/service`, modelled on `UserStateService.applyTransition`: lock the listing, `stateMachine.transition(from, to, action)`, set the status, save, write a `ListingStatusHistory` row (with `from`, `to`, `action`, `changedBy`, `reason` trimmed to 255), publish the event, log.
- [ ] `ListingNotFound` as `NotFoundException("LISTING_NOT_FOUND", ...)`; invalid transitions surface the existing `ValidationException` (`INVALID_STATE_TRANSITION`, HTTP 400).
- [ ] Add `ListingStatusChangedEvent extends DomainEvent` (listing ID, from, to, action, changedBy, reason) and publish it through `DomainEventPublisher`, as the user state change does.
- [ ] Convenience methods for the callers in later stories (`submitForPlan`, `submitForReview`, `approve`, `reject`, `requestRevision`, `resubmit`, `publish`, and so on) are thin wrappers over `transition`; add only the ones the Sprint 2 stories use, when those stories are built.
- [ ] Keep `ListingDraftService.createDraft` writing the first `DRAFT` history row (no `from`), and add the `action` value there (`CREATE`).

### Backend — Seller Notifications at Key States
- [ ] This story only publishes `ListingStatusChangedEvent` (listing ID, from, to, action, actor, reason). The notifications for the key states (`APPROVED`, `REJECTED`, `REVISION_REQUIRED`, `PUBLISHED`, `EXPIRED`, `REMOVED_BY_ADMIN`) are built by US-115 (Listing Lifecycle Notifications), which subscribes to this event and owns the copy and channels.

### Backend — Visibility
- [ ] Expose the state rule through `ListingState.isLiveForBuyers()`; no search or read API exists yet, so nothing else is wired. Sprint 3 uses it to index only live listings and to de-index on any exit from `PUBLISHED`.

### Documentation/Quality
- [ ] Update LLD Part E (and the dependent parts, see Open Gaps 7): payment-first order, in-code state machine instead of a transitions table, `action` column, reachable/unreachable states, 400 `INVALID_STATE_TRANSITION`.
- [ ] After implementation, create `Documents/Manual Testing Guides/US-089-Testing-Guide.md` (there is no seller endpoint for this story, so the guide is based on API calls from the stories that use it plus database checks).

## 5. Test Plan

Target >90% coverage for new code (`CLAUDE.md`).

### Unit Tests
- [ ] `ListingStateMachine`: every allowed transition in the table passes; a representative set of disallowed ones fails (for example `DRAFT → PUBLISHED`, `DRAFT → TRUST_SAFETY_REVIEW`, `PLAN_PAYMENT_SUCCESS → PUBLISHED`, `PLAN_SELECTION_PENDING → PUBLISHED`, `SOLD → PUBLISHED`, `EXPIRED → PUBLISHED`); wrong action name for a valid pair fails.
- [ ] Every one of the 21 states is reachable or explicitly accounted for (the three AI-era states are documented as unreachable in Sprint 2).
- [ ] `ListingLifecycleService`: valid transition updates the status, writes one history row with `from`, `to`, `action`, `changedBy`, `reason`, and publishes one event; invalid transition changes nothing and publishes nothing; unknown listing throws `LISTING_NOT_FOUND`; reason longer than 255 is trimmed.
- [ ] Full Sprint 2 path, step by step, from `DRAFT` to `PUBLISHED` (`DRAFT → PLAN_SELECTION_PENDING → PLAN_PAYMENT_PENDING → PLAN_PAYMENT_SUCCESS → TRUST_SAFETY_REVIEW → APPROVED → PUBLISHED`), the payment-failure loops, and the reject/revise loop (`TRUST_SAFETY_REVIEW → REVISION_REQUIRED → TRUST_SAFETY_REVIEW`, twice) with no second payment, then `TRUST_SAFETY_REVIEW → REJECTED`, after which no transition is allowed.
- [ ] `EXPIRED → PLAN_SELECTION_PENDING` works only through `RENEW`; nothing moves `EXPIRED` straight to `PUBLISHED`.
- [ ] The status change event carries every value US-115 needs (listing ID, from, to, action, actor, reason), is published once per transition, and is not published when the transition is rejected.
- [ ] `ListingState` helper methods.

### Integration Tests (Testcontainers PostgreSQL)
- [ ] Transition writes the status and history in one transaction; a failure after the status change rolls both back.
- [ ] Two concurrent transitions on the same listing are serialised by the row lock (the second sees the new state and is rejected if no longer valid).
- [ ] `V13` migration applies on top of `V12` and existing history rows keep working (`action` null).

## 6. Validation Checklist

- [ ] A listing cannot be published without a paid plan and without passing review (payment comes first, then review, then publish).
- [ ] A revision-required listing is revised and resubmitted to review without paying again; a `REJECTED` listing is final.
- [ ] Expired listings are never renewed automatically.
- [ ] Every status change after creation goes through `ListingLifecycleService`; no other code sets `listings.status`.
- [ ] Every transition leaves exactly one history row and one event.
- [ ] Every transition publishes the status change event that US-115 turns into seller notifications.
- [ ] Visibility rule for buyers is defined in one place.
- [ ] Existing listing and media tests still pass.
- [ ] Checkstyle, full tests, coverage and SonarQube pass before push.

## 7. Open Gaps / Questions

1. **LLD deviation (decided 2026-10-16).** Keep the in-code state machine and `VARCHAR` statuses; the LLD's `listing_status_transitions` table and Postgres enum are dropped, because the code already works that way. The LLD is updated to match.
2. **Invalid-transition error (decided 2026-10-16).** Keep the shared behaviour: HTTP 400 `INVALID_STATE_TRANSITION`. The LLD's 409 `INVALID_LISTING_STATE_TRANSITION` is dropped. The LLD is updated to match.
3. **Buyer visibility (decided 2026-10-16).** A listing is visible in search only once it is `PUBLISHED`, never before. `ListingState.isLiveForBuyers()` returns true for `PUBLISHED` only; what happens in the inquiry and negotiation states is decided in Sprint 3/4.
4. **LLD shortcut `PUBLISHED → SOLD` (decided 2026-10-16).** Not built. The code's path through the inquiry, negotiation, offer and order states is kept.
5. **Notification copy (decided).** Owned by US-115 (Listing Lifecycle Notifications), including the Hindi text.
6. **Existing data (decided 2026-10-16).** The project is in development and has no real listings. Any mock or test listing in a state the new machine removes is discarded or recreated with the new state machine; no data migration is written.
7. **Other documents that assume review first (done).** LLD Parts D, E, F, H and I and the story map were updated to the payment-first order on 2026-10-16, and the US-008, US-009 and US-084 stories and the sprint plan dependencies were updated too. US-009's implementation plan, when written, covers payment success handing the listing to review and publication on approval.
8. **Refund after 3 failed reviews (decided 2026-10-16).** After the third failed review the listing is `REJECTED` (final) and the plan fee is refunded; automatic or manual refund is decided later (US-084, US-009). Plan validity now starts at publication, so `expires_at` is set when the listing is published.

---

**Status:** Implemented on branch `feature/US-089-lifecycle-state-listing` (valuex-backend); unit tests, checkstyle and coverage pass. Pending: Docker integration tests and the SonarQube scan (neither could run locally), then commit approval. No deviation from this plan; LLD Part E and the testing guide are updated.
