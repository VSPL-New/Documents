# US-080 - Auto-Expire Inactive Negotiations: QA Testing Guide

**Sprint 4 · Communication & Negotiation**

Manual test cases for the jobs that warn and expire negotiations nobody answers, the chat messages that extend the
deadline, the end of an unused price lock, and the notifications and live updates that go with them. This story is
backend only: the jobs, the SQL and the notifications are checked with `curl` and SQL; the app is used only to see
the result (the negotiation and Offers screens).

> **What ships:** `NegotiationExpiryJob` (a warning pass, then an expiry pass) and `AgreementExpiryJob` (ends price
> locks), both every 60 seconds (`valuex.negotiation.job.expiry-interval-ms`); a chat message counts as activity;
> migration `V38` (`idx_negotiations_warning`); notifications `NEGOTIATION_EXPIRING`, `NEGOTIATION_EXPIRED` and
> `AGREEMENT_EXPIRED`; a neutral card in the thread; the seller's Offers badge drops at expiry.
> **Not in this story:** Hindi and English app texts for the three new notifications and cards, and the "Make a new
> offer" button on an expired negotiation (mobile follow-up: the app shows the server's English text meanwhile);
> push notifications (US-131); search hiding of reserved items (US-068); an Admin screen for the settings (US-116).

| Setting | Value |
|---|---|
| Backend base URL | `http://localhost:8080` |
| Timing (Admin settings) | `NEGOTIATION_INACTIVITY_HOURS` 48, `NEGOTIATION_WARNING_BEFORE_HOURS` 24 (must stay below the inactivity time, else both return to their defaults), `NEGOTIATION_MAX_LIFETIME_DAYS` 14, `PRICE_LOCK_HOURS` 24 |
| Job tuning (`application.yml`) | `valuex.negotiation.job.expiry-interval-ms` 60000, `batch-size` 100, `max-batches-per-run` 20 |
| Notifications | `NEGOTIATION_EXPIRING` (only the person whose answer is awaited): "Negotiation will expire in 24 hours. Please respond"; `NEGOTIATION_EXPIRED` (both): "This negotiation has expired. Start a new offer"; `AGREEMENT_EXPIRED` (both): "Price acceptance expired. Please re-negotiate" |
| Error codes | 409 `ERROR_NEGOTIATION_EXPIRED` (buyer), `ERROR_OFFER_EXPIRED` (seller) on any answer after the deadline |
| Known gaps | App texts for the new notifications are English only (mobile follow-up) |

---

## Prerequisites

1. Backend, PostgreSQL and Redis running. To test quickly, set `valuex.negotiation.job.expiry-interval-ms` to
   `5000` (environment: `VALUEX_NEGOTIATION_JOB_EXPIRY_INTERVAL_MS=5000`) and restart; the default of 60 seconds also
   works, you just wait up to a minute after each SQL change.
2. A published, negotiable goods listing owned by `$SELLER` (id `LISTING`), and two `ACTIVE`, Aadhaar-verified buyers
   `$BUYER1` and `$BUYER2`.
3. Handy variables:

```bash
B="localhost:8080/api/v1"
HS="Authorization: Bearer $SELLER"
H1="Authorization: Bearer $BUYER1"
H2="Authorization: Bearer $BUYER2"
J="Content-Type: application/json"
```

4. Buyer 1 offers 12000 on `LISTING`; note `NEG` (the negotiation id) and `OFFER` (the offer id):

```bash
curl -s -X POST $B/listings/$LISTING/offers -H "$H1" -H "$J" -d '{"amount":"12000","clientRequestId":"'$(uuidgen)'"}'
```

---

## A. Migration and settings

| # | Steps | Expected |
|---|---|---|
| A1 | `SELECT version, success FROM flyway_schema_history WHERE version = '38';` and `SELECT indexname FROM pg_indexes WHERE indexname = 'idx_negotiations_warning';` | One successful row, one index. |
| A2 | `SELECT setting_key, setting_value FROM platform_settings WHERE setting_key LIKE 'NEGOTIATION_%';` | `NEGOTIATION_INACTIVITY_HOURS` 48, `NEGOTIATION_WARNING_BEFORE_HOURS` 24 and the other keys (no new seed in this story). |

## B. The 24 hour warning (validation rule, edge case "seller on vacation")

| # | Steps | Expected |
|---|---|---|
| B1 | `UPDATE negotiations SET expires_at = now() + interval '20 hours' WHERE id = '<NEG>';` Wait for one job run. | `warning_sent_at` is set. The **seller** (whose turn it is) has one in-app notification `NEGOTIATION_EXPIRING`: "Negotiation will expire in 24 hours. Please respond"; the buyer has none. `params.hours` is 24. |
| B2 | Wait for two more job runs. | No second warning (still one notification). |
| B3 | The seller counters 14000 (the turn passes to the buyer), then `UPDATE negotiations SET expires_at = now() + interval '20 hours', warning_sent_at = NULL WHERE id = '<NEG>';` and wait. | The **buyer** (whose turn it is) gets `NEGOTIATION_EXPIRING`; the seller gets none. |
| B4 | `UPDATE platform_settings SET setting_value = '12' WHERE setting_key = 'NEGOTIATION_WARNING_BEFORE_HOURS';` (wait about a minute for the settings cache or restart), then set `expires_at = now() + interval '20 hours', warning_sent_at = NULL`. | No warning (20 hours is outside the 12 hour window); at `expires_at = now() + interval '10 hours'` the warning arrives and says "in 12 hours". Restore the value 24 afterwards. |
| B4a | Set the warning hours to 60 (above the 48 hour inactivity time). | Both values return to the defaults 24 and 48 (`settings.invalid` is counted); a warning is sent only inside 24 hours. |
| B5 | `UPDATE negotiations SET expires_at = now() - interval '1 minute', warning_sent_at = NULL WHERE id = '<NEG>';` | No warning for a negotiation already past its end; the expiry pass takes it (section C). |

## C. Expiry (AC1, AC2, AC5, edge case "many at once")

| # | Steps | Expected |
|---|---|---|
| C1 | Make a fresh offer. `UPDATE negotiations SET expires_at = now() - interval '1 minute' WHERE id = '<NEG>';` Wait for a job run. | `state = NEGOTIATION_EXPIRED`, `closed_reason = EXPIRED`, `closed_at` set. The pending offer is `EXPIRED` (`SELECT status FROM offers ...`). A history row has `action = EXPIRE` and `actor_id` NULL. |
| C2 | Check notifications of both people. | Each has one `NEGOTIATION_EXPIRED`: "This negotiation has expired. Start a new offer"; neither text shows a price. |
| C3 | Open the thread (app or `GET /chats/{thread}/messages`). | A neutral card `OFFER_EVENT` with `kind = NEGOTIATION_EXPIRED` (negotiation id and round only). |
| C4 | `GET /negotiations/{NEG}` as buyer and as seller. | `state = NEGOTIATION_EXPIRED`; history (offers) still readable; no actions available. |
| C5 | Seller `POST $B/offers/$OFFER/accept` and `.../counter`; buyer `POST .../accept` on a seller counter. | 409: `ERROR_OFFER_EXPIRED` for the seller, `ERROR_NEGOTIATION_EXPIRED` for the buyer. Nothing is created; no price agreement exists (no automatic acceptance). |
| C6 | Seller, app: Offers badge and Offers > Pending. | The badge dropped; the offer left Pending and shows under Closed. |
| C7 | Several buyers each hold an open offer; set all their `expires_at` to a minute ago; wait one run. | Every one of them is expired in the same run; check `SELECT count(*) FROM negotiation_status_history WHERE action = 'EXPIRE';` (up to 100 per batch and 20 batches per run; the rest in the next run). |
| C8 | Run two backend instances (or call the job from two processes) while 20 negotiations are due. | Each negotiation expires exactly once: 20 history rows, 40 notifications (two people each), no errors in the log. |
| C9 | `UPDATE negotiations SET max_lifetime_at = now() - interval '1 minute' WHERE id = '<open NEG>';` | It expires although `expires_at` is still in the future (the 14 day lifetime). |

## D. Edge: a reply close to the deadline

| # | Steps | Expected |
|---|---|---|
| D1 | `UPDATE negotiations SET expires_at = now() + interval '30 seconds' WHERE id = '<NEG>';` Seller counters at once. | 200: the counter works and the end moves out to about now plus 48 hours (`expires_at` check). |
| D2 | `UPDATE negotiations SET expires_at = now() - interval '1 second' ...` and answer before the job runs (use a long job interval). | 409 as in C5; the row is still `BUYER_REVIEWING` until the job runs, then `NEGOTIATION_EXPIRED` (nobody can slip a reply through). |

## E. Chat counts as activity (decision D21)

| # | Steps | Expected |
|---|---|---|
| E1 | `UPDATE negotiations SET expires_at = now() + interval '2 hours', warning_sent_at = now() WHERE id = '<NEG>';` Buyer sends a text in the thread. | `expires_at` is now about 48 hours ahead, `last_activity_at` is now and `warning_sent_at` is NULL. |
| E2 | The same with `max_lifetime_at = now() + interval '10 hours'`. | `expires_at` equals `max_lifetime_at` (never beyond the lifetime). |
| E3 | `expires_at = now() - interval '1 minute'` (past the deadline, job not run yet) and a chat message. | `expires_at` does not move: a negotiation past its end is not revived. |
| E4 | After E1, set `expires_at = now() + interval '19 hours'` again. | A second `NEGOTIATION_EXPIRING` notification is sent (the first one does not block it). |
| E5 | A message in a thread whose negotiation is closed. | Nothing changes in the negotiation. |

## F. Restart after expiry (AC4)

| # | Steps | Expected |
|---|---|---|
| F1 | After C1, buyer 1 offers again on the same listing. | 201 at once (no cooldown after an expiry; the cooldown only follows a rejection); a new negotiation is `SELLER_REVIEWING`. The old one stays `NEGOTIATION_EXPIRED`. |
| F2 | App, buyer: open the expired negotiation. | It shows as expired. (The "Make a new offer" button is the mobile follow-up; the listing page's Make Offer works.) |

## G. Unused price lock (AC3)

| # | Steps | Expected |
|---|---|---|
| G1 | Seller accepts buyer 1's offer. `UPDATE price_agreements SET valid_until = now() - interval '1 minute' WHERE listing_id = '<LISTING>';` Wait for a job run. | The agreement is `EXPIRED` (`ended_reason = EXPIRED`); the negotiation is `NEGOTIATION_EXPIRED` with `closed_reason = ACCEPTANCE_EXPIRED`; history `EXPIRE_ACCEPTANCE`. |
| G2 | Notifications and thread. | Both people have `AGREEMENT_EXPIRED`: "Price acceptance expired. Please re-negotiate"; the thread has a card with `kind = AGREEMENT_EXPIRED`. |
| G3 | Buyer 2 offers on the listing and the seller accepts. | Accepted; exactly one `ACTIVE` agreement exists (the item is free for others again). |
| G4 | Repeat G1 and, in the same second, accept another buyer's offer (two `curl` calls in parallel, or lower the interval). | Both calls finish (no deadlock); one `ACTIVE` agreement; the first negotiation expired once, with one `AGREEMENT_EXPIRED` per person. |
| G5 | A property listing: accept an offer (no price lock), wait past `max_lifetime_at`... | The accepted property negotiation is left alone by the jobs (state stays `OFFER_ACCEPTED`); awaiting property negotiations expire on the same timers as goods. |

## H. Metrics and resilience

| # | Steps | Expected |
|---|---|---|
| H1 | `GET /actuator/metrics/negotiation.expired`, `negotiation.warned`, `agreement.expired`, `negotiation.job.duration` (with the tags `reason`, `source`, `job`). | Counters rise with the tests above; the timer has a count per run for `job=negotiation` and `job=agreement`. |
| H2 | Break one row (for example make a notification insert fail) or stop PostgreSQL for a moment. | The job logs the id (or the failure) and goes on or ends the run; the next run continues; nothing escapes to the scheduler and the application keeps running. |
| H3 | Look at the log after a normal run. | "Negotiations warned: n, expired: m" and "Price locks ended: k" only when something was done. |

## I. Live updates

| # | Steps | Expected |
|---|---|---|
| I1 | Seller has the Offers screen open; an offer expires. | The list updates within seconds (`negotiation.updated`), the Offers badge changes (`badge.updated`). |
| I2 | A warning is sent. | `negotiation.updated` is sent; `badge.updated` is **not** (no count changed). |

---

## How to run the automated tests

```bash
# backend (from valuex-backend; Docker running for the integration tests)
export JAVA_TOOL_OPTIONS="-Dapi.version=1.44 -Duser.timezone=Asia/Kolkata"
mvn -o test -Dtest='NegotiationExpiryServiceTest,NegotiationExpiryJobTest,AgreementExpiryJobTest,ExpiryBatchesTest,NegotiationExpiryAnnouncerTest,NegotiationActivityListenerTest,NegotiationTransitionsTest,PriceAgreementServiceTest,NegotiationNotificationListenerTest,NegotiationRealtimeListenerTest'
mvn -o test -Dtest='NegotiationExpiryIntegrationTest,NegotiationIntegrationTest'
```
