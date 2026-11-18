# US-080: Auto-Expire Inactive Negotiations - Implementation Plan

## 1. Header

| Field | Value |
|---|---|
| Story | US-080 - Auto-Expire Inactive Negotiations |
| Sprint | Sprint 4 - Communication & Negotiation |
| Story points | 3 |
| Repos involved | valuex-backend only (two scheduled jobs, chat activity listener, notification and card texts, one index). No `valuex-mobile`, `valuex-ai`, `valuex-web` or infra change in this story (see G6 for the mobile follow-up). |
| Dependencies | US-017 (built, merged). **US-076 (backend PR #71, now merged, confirmed 2026-11-18)**: it adds `NEGOTIATION_WARNING_BEFORE_HOURS`, its cross-field rule, `warnAt`, migration V37 and the listing-then-row lock order that the agreement job must follow (confirmed by the user 2026-11-18). |
| Date | 2026-11-18 |
| Design source | [Sprint 4 LLD](../LLD/Sprint-4-Communication-Negotiation-LLD.md) Part L (L.1 to L.10), I.5 (state machine), I.11 and J.11 (what US-017 and US-076 already built), decisions D8 and D21. |
| Branch (proposal) | `feature/US-080-auto-expire-negotiations` in `valuex-backend`, cut from `main` after PR #71 is merged, rebased before work starts (CLAUDE.md rule 5.1). |
| Flyway number | Next free number at branch time (V38 if nothing else lands first; the LLD's provisional V38 for US-068 will move). |

## 2. Story Recap

**As a** platform **I want to** auto-expire inactive negotiations **so that** stale offers don't block transactions.

> Update (2026-10-25, category taxonomy): applies to Real Estate negotiations as well (US-118).

**Acceptance criteria (from `user-stories.md`):**

| ID | Criterion |
|---|---|
| AC1 | When 48 hours pass with no activity from either party in a negotiation in progress, its state becomes EXPIRED. |
| AC2 | Both parties receive a notification. |
| AC3 | The seller's item becomes available for other buyers. |
| AC4 | The buyer can make a new offer if interested. |
| AC5 | After expiry nobody can accept or counter the last offer, and the history is kept. |

**Edge cases (story):** buyer replies just before expiry; seller on vacation; many negotiations expire at once; user wants to restart an expired negotiation.
**Validation rules (story):** timeout 48 hours from the last message; a 24-hour warning before expiry; expired negotiations stay in history; a new negotiation is allowed after expiry; no automatic price acceptance.
**Error scenarios (story):** `ERROR_NEGOTIATION_EXPIRED` ("This negotiation has expired. Start a new offer"); `WARNING_EXPIRING_SOON` ("Negotiation will expire in 24 hours. Please respond").

## 3. Design Reference

LLD Part L, with these points that matter for the build:

- **State machine** already has `EXPIRE` (from `SELLER_REVIEWING` and `BUYER_REVIEWING`) and `EXPIRE_ACCEPTANCE`; `ClosedReason.EXPIRED` / `ACCEPTANCE_EXPIRED` and `OfferStatus.EXPIRED` exist. `NegotiationTransitions.expireAcceptance` exists; a plain `expire` does not.
- **Deadline checks on actions already exist** (`NegotiationRow.isPastDeadline`, `NegotiationService.requireTurn`): a late reply gets `ERROR_NEGOTIATION_EXPIRED` (buyer) or `ERROR_OFFER_EXPIRED` (seller, US-076) before any job runs. The jobs only make the stored state true and tell people.
- **Two jobs, one schedule** (`valuex.negotiation.job.expiry-interval` 60 s, `batch-size`), in the style of `ListingExpiryJob`: `NegotiationExpiryJob` (warning pass, then expiry pass) and `AgreementExpiryJob` (price lock ended). Each row is its own small transaction; a failed row is logged by id and skipped; re-running changes nothing already closed.
- **Locks:** rows are picked with `FOR UPDATE SKIP LOCKED`, then re-checked (state and deadline) after the row lock, because a person may have acted in between. For an agreement the **listing advisory lock is taken before the negotiation row lock**, the same order as US-076's accept, so the job cannot deadlock with it (`PriceAgreementService.lockListing`).
- **Activity bump** (D21): a chat message counts as activity, but never beyond `max_lifetime_at`.
- **Settings** (`NegotiationSettings`) are read on every pass, so an Admin change applies at the next run; invalid values already fall back to defaults (US-076).
- **Events:** the existing `NegotiationUpdatedEvent` (ids and kind only) drives realtime (`negotiation.updated`, and the `badge.updated` that US-076 added, so the seller's Offers badge drops at expiry) and in-app notifications. System actions have `actorId = null`, which `NegotiationNotificationListener` already treats as "tell both".

## 4. Implementation Steps

### Database
- [ ] `V38__negotiation_warning_index.sql` (number at branch time): `idx_negotiations_warning ON negotiations (expires_at) WHERE warning_sent_at IS NULL AND state IN ('SELLER_REVIEWING','BUYER_REVIEWING')` exactly as L.3. The expiry pass uses the existing `idx_negotiations_expiry`, the agreement pass the existing `idx_price_agreements_expiry`. No new columns or settings.

### Backend (`com.valuex.negotiation`)
- [ ] `NegotiationEventKind`: add `NEGOTIATION_EXPIRING`, `NEGOTIATION_EXPIRED`, `AGREEMENT_EXPIRED`.
- [ ] `ValuexProperties`: add a `negotiation.job` section (`expiryInterval` 60 s, `batchSize`), documented like the listing expiry one.
- [ ] `NegotiationRepository`: `findWarnDue(now, windowHours, limit)` and `findExpiryDue(now, limit)` (both `FOR UPDATE SKIP LOCKED`, return ids), `markWarned(id, now)`. `PriceAgreementRepository`: `findDue(now, limit)` returning agreement id, listing id and negotiation id.
- [ ] `NegotiationTransitions.expire(negotiation, now)`: `offers.closePending(..., EXPIRED, now)`, then `move(EXPIRE, Change(NEGOTIATION_EXPIRED, closedReason EXPIRED), actor null)`. Same shape as `cancel`.
- [ ] `NegotiationExpiryService` (transactional unit per row, called by the job):
  - `warn(id)`: lock, re-check still awaiting, `warning_sent_at` null and inside the window; set `warning_sent_at`; publish `NEGOTIATION_EXPIRING` (event actor null).
  - `expire(id)`: lock, re-check awaiting and past `expires_at` or `max_lifetime_at`; `transitions.expire`; post a neutral `OFFER_EVENT` card to the thread (kind and round only, as US-076's supersede card); publish `NEGOTIATION_EXPIRED`; metric `negotiation.expired{reason=INACTIVITY|MAX_LIFETIME}`.
  - `expireAgreement(id)`: take the listing lock, then lock the negotiation; end the agreement (`EXPIRED`, `ended_reason EXPIRED`); for source `OFFER` move the negotiation with `transitions.expireAcceptance`, post the card, publish `AGREEMENT_EXPIRED`; for `BUY_NOW` only end the row, no notification (L.5); metric `agreement.expired{source}`. Reuse the existing `PriceAgreementService.expireDue` logic instead of a second copy.
- [ ] `NegotiationExpiryJob` (`@Scheduled(fixedDelayString = "${valuex.negotiation.job.expiry-interval:60s}")`): warning pass then expiry pass, each batch loop until fewer rows than `batchSize` or a cap per run; catches and logs per row; `negotiation.job.duration` timer. `AgreementExpiryJob`: same for agreements.
- [ ] `NegotiationActivityListener` (negotiation module, `BEFORE_COMMIT` on `ChatMessageCreatedEvent`): `UPDATE negotiations SET last_activity_at = now(), expires_at = LEAST(now() + inactivity, max_lifetime_at), warning_sent_at = NULL WHERE thread_id = ? AND state IN ('SELLER_REVIEWING','BUYER_REVIEWING') AND expires_at > now() AND max_lifetime_at > now()`. The two `> now()` guards keep a chat message from reviving a negotiation that is already past its deadline (G3). Repository method `bumpActivity(threadId, now, inactivity)`.
- [ ] `NegotiationNotificationCopy` and `NegotiationNotificationListener`: texts for the three new kinds (`NEGOTIATION_EXPIRING` "Negotiation will expire in N hours. Please respond", `NEGOTIATION_EXPIRED` "This negotiation has expired. Start a new offer", `AGREEMENT_EXPIRED` "Price acceptance expired. Please re-negotiate"); no price in any of them (`NO_AMOUNT`); `NEGOTIATION_EXPIRING` goes only to the party whose turn it is (change `recipients`); its dedupe key includes the `expires_at` epoch so a warning after an activity bump is not swallowed by the round-based key (G2).
- [ ] `NegotiationRealtimeListener`: no change expected (publishes `negotiation.updated` and `badge.updated` for every event); `NEGOTIATION_EXPIRING` should not trigger a badge change, only `negotiation.updated`; verify and keep the existing tests green.
- [ ] Metrics: `negotiation.warned`, `negotiation.expired{reason}`, `agreement.expired{source}`, `negotiation.job.duration`.

### Mobile / Web / AI
- Not in scope (G6).

## 5. Test Plan (target above 90% on new and changed classes)

**Unit (fake clock, mocks)**
- `NegotiationExpiryServiceTest`: warn only inside the window and only once; warn skipped if state changed or `warning_sent_at` already set after the lock; recipient is the party whose turn it is; expire closes pending offer as `EXPIRED`, history row with null actor, card posted, event published; expire skipped when the deadline moved after the lock (reply just before expiry); lifetime cap expires even when `expires_at` is later; agreement expiry for `OFFER` and `BUY_NOW`; failure on one row does not stop the batch.
- `NegotiationExpiryJobTest` / `AgreementExpiryJobTest`: batch loop and the per-run cap, exception per row logged and skipped, metrics, empty run.
- `NegotiationActivityListenerTest`: bumps awaiting negotiations of the thread, clears `warning_sent_at`, never past `max_lifetime_at`, ignores closed or accepted negotiations and past-deadline ones.
- `NegotiationNotificationCopyTest` / `ListenerTest`: three new kinds, no amount param, warning only to the awaiting party, dedupe key differs after a bump.
- `NegotiationTransitionsTest`: `expire` (state machine, history, offer status).

**Integration (PostgreSQL Testcontainers, extend `NegotiationIntegrationTest` or a new `NegotiationExpiryIntegrationTest`)**
- Warn then expire a negotiation with a controllable clock; both people get the expiry notification, the thread has the card, the history keeps both offers; AC1, AC2, AC5.
- Action just before the deadline succeeds and moves the deadline; action just after fails with the expiry error even before the job runs (AC5, edge 1).
- Two job instances run together: no double processing (`SKIP LOCKED`).
- Many (for example 120) negotiations expire in one pass across several batches (edge 3).
- Chat message extends the deadline but not past the lifetime; a message after the deadline does not revive it (G3).
- Agreement expiry: lock ends, negotiation `NEGOTIATION_EXPIRED` (`ACCEPTANCE_EXPIRED`), the seller can accept another buyer's offer, no deadlock with a concurrent accept (the US-076 lock order) (AC3).
- Restart after expiry: new offer allowed at once, no cooldown (AC4); property negotiation expires on the same timers; an accepted property negotiation is not touched by the job.
- Setting change (`NEGOTIATION_INACTIVITY_HOURS`, warning hours) applies at the next pass; a broken pair falls back to defaults.
- Update the US-076 test(s) that assert "an expired offer stays listed until US-080" so they expect it to move to the closed list after the job.

## 6. Validation Checklist

- [ ] AC1: 48 hours of inactivity (setting) closes the negotiation as `NEGOTIATION_EXPIRED`, `closed_reason EXPIRED`.
- [ ] AC2: both people get the in-app notification and see the card; realtime `negotiation.updated` and the seller badge update.
- [ ] AC3: expired offers hold nothing; an expired price lock frees the listing for another accept.
- [ ] AC4: a new offer is allowed immediately after expiry (no cooldown).
- [ ] AC5: no accept or counter after the deadline, with or without the job having run; history rows and offers are kept.
- [ ] Edge: reply just before and just after the deadline; seller away (warning to the party whose turn it is); many at once; restart.
- [ ] Validation: warning once per quiet period (not repeated), reset by activity; timeout never beyond the 14-day lifetime; no automatic acceptance; warning hours stay below the timeout.
- [ ] Error texts: `ERROR_NEGOTIATION_EXPIRED` and the warning text match the story.
- [ ] Jobs are idempotent, per-row transactions, safe on several instances; listing lock before row lock.
- [ ] Real Estate: same timers, no price lock effects.
- [ ] Checkstyle, tests above 90% coverage on new code, SonarQube gate, LLD Part L / I.11 / J.11 reconciled, testing guide `US-080-Testing-Guide.md`.

## 7. Open Gaps / Questions

| # | Gap | Proposed answer |
|---|---|---|
| G1 | US-076 (PR #71) was not merged; this story needs its setting, `warnAt` and lock order. | **Resolved 2026-11-18:** the user merged US-076; cut the branch from the updated `main`. |
| G2 | The LLD dedupe key is round-based (`neg:{id}:{type}:{round}:{recipient}`), so a second warning in the same round after a chat bump would be dropped. | Add the `expires_at` epoch to the key of `NEGOTIATION_EXPIRING` only. |
| G3 | Activity bump after the deadline but before the job runs would revive the negotiation, which contradicts L.1.1 and AC5; the LLD query has no guard. | Add `expires_at > now()` and `max_lifetime_at > now()` to the bump (included in the steps). |
| G4 | The warning text says "24 hours", but the window is an Admin setting. | The text uses the configured hours; with the default it equals the story text. Confirm. |
| G5 | An accepted Real Estate negotiation has no price lock and `expires_at` equal to the lifetime end; L.1.1 says it is kept until the listing closes. | The job never touches accepted negotiations without an agreement; confirm that the 14-day lifetime does not apply to an accepted property price. |
| G6 | L.7 expects mobile strings (Hindi and English) for the expiring, expired and price-expired texts and a "Make a new offer" action; the Sprint plan lists this story as backend only. Today mobile shows the server's English title for unknown notification types. | Keep US-080 backend only; add a small mobile follow-up (strings, system card kinds, "Make a new offer" on an expired negotiation) as a separate story or an addition you choose. |
| G7 | Search hiding of reserved listings (LLD M.5) belongs to US-068 and is not built. | Nothing to do here; the listing is free as soon as the agreement row ends. |
| G8 | Flyway number and the LLD's provisional V38 for US-068 will collide. | Use the next free number at branch time and update LLD Part M. |

**Answers (user, 2026-11-18):** G1 US-076 is merged. G2 to G5, G7 and G8 agreed as proposed (G4 and G5 confirmed: the warning text uses the configured hours; the job never expires an accepted Real Estate negotiation). G6 agreed: US-080 stays backend only and the mobile strings and "Make a new offer" action are a separate follow-up.

**Status: Approved (2026-11-18); implemented 2026-11-18 (see section 8)**

## 8. Deviations from the plan (as built, 2026-11-18)

| # | Plan | As built | Why |
|---|---|---|---|
| D1 | Pick rows with `FOR UPDATE SKIP LOCKED`. | Ids are read without a lock; each row is then locked in its own transaction together with the "still due" condition (`lockWarnDue`, `lockExpiryDue`, `FOR UPDATE SKIP LOCKED`). | Locks taken by a batch select end with that transaction, so they would not keep two instances apart; the per-row lock does, and a person who just answered wins. |
| D2 | `findWarnDueIds` and friends. | Also added `max-batches-per-run` (20) and the helper `ExpiryBatches.drain` (stops at a short batch, a batch with no progress or the cap; a failing row is logged and skipped). | One run must end even when many rows are due or one keeps failing. |
| D3 | Reuse `PriceAgreementService.expireDue`. | Reused and extended: it now announces (card and event) for every negotiation it moves, so the lazy clean-up on accept and the job behave the same; `expireDueOnListing` (listing lock first) and `dueListingIds` are new; `PriceAgreementRepository.expireDue` returns the sources of the ended rows for the metric. | One code path and one announcement (the buyer would otherwise not be told when the lock was cleared by an accept). |
| D4 | `NegotiationExpiryService` does warn, expire and agreement expiry. | The agreement step lives in `PriceAgreementService` (it owns the listing lock and agreements); a small `NegotiationExpiryAnnouncer` writes the card and publishes the event for all three cases. | Avoids a second copy of the agreement logic and a dependency cycle. |
| D5 | Warn when `expires_at - window <= now`. | Also `expires_at > now`. | A negotiation past its end is expired, not warned. |
| D6 | Realtime listener unchanged. | `badge.updated` is skipped for the warning (no count changes); `negotiation.updated` is still sent. | Avoids a useless event. |
| D7 | Job interval property `expiry-interval`. | `valuex.negotiation.job.expiry-interval-ms` (60000), like the other interval properties; the test profile sets one hour so a background run cannot change integration test data. | Convention and test stability. |
| D8 | G2 to G5 and G6 as agreed. | Built as agreed: the dedupe key of the warning uses the end time; the bump has the two "not yet past" guards; the text uses the configured hours; accepted property negotiations are not touched; no mobile change (follow-up). | Plan answers of 2026-11-18. |

Open items for the product owner: the mobile follow-up (Hindi and English texts for `NEGOTIATION_EXPIRING`, `NEGOTIATION_EXPIRED` and `AGREEMENT_EXPIRED`, the matching system card kinds, the "Make a new offer" button on an expired negotiation); push for the three notifications (US-131); search hiding of reserved listings (US-068).
