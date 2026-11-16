# US-132: Block and Report User - Implementation Plan

## 1. Header

| Field | Value |
|---|---|
| Story | US-132 - Block and Report User (**proposed story**, found missing while writing the Sprint 4 LLD; not yet in `Sprint-plan.md` or `user-stories.md`, see gap G1) |
| Sprint | Sprint 4 - Communication & Negotiation |
| Story points | 3 (proposed in LLD Part C; Sprint 4 total becomes 69 SP, 53 SP active) |
| Repos involved | valuex-backend (tables, block and report endpoints, `BlockService`, `ReportService`, `CommunicationSetting` registry) and valuex-mobile (Blocked Users screen, shared Block and Report widgets). No `valuex-ai`, infra or `valuex-web` change. |
| Dependencies | US-003 (profile, `users.display_name`; merged). Verified 2026-11-15: `main` has no `communication` code yet (the package holds only `package-info.java`). US-132 itself blocks US-069, US-013, US-017 and the other contact entry points. |
| Date | 2026-11-15 |
| Design source | [Sprint 4 LLD](../LLD/Sprint-4-Communication-Negotiation-LLD.md) Part C (C.1 to C.9), section 1.3 (package layout), 1.6 (`CommunicationSetting`), 1.7 (migrations), 8.2 (error codes) and decisions D3 and D17. |
| Branches (proposal) | `feature/US-132-block-and-report-user` in `valuex-backend` and `valuex-mobile`, cut from current `main` and rebased before work starts (CLAUDE.md rule 5.1). |
| Flyway number | The LLD says V33 (provisional). `main` is at V31, so use the next free number when the branch is cut (V32 unless US-131 lands first). |

## 2. Story Recap

The LLD gives a story statement but no acceptance-criteria list. The criteria below are derived from LLD C.1 to C.7 only; nothing is added to them.

**As a** user **I want** to block someone who bothers me and report abusive behaviour **so that** I feel safe using chat, calls and offers.

| ID | Behaviour (derived from LLD Part C) |
|---|---|
| AC1 | I can block another user and unblock them; both are idempotent. A blocked user is never told. |
| AC2 | Where either side has blocked the other, contact is refused with `ERROR_BLOCKED` ("You cannot contact this seller"). The message does not say who blocked whom. The check is `BlockService.isBlockedEitherWay`, used by Parts D to M. |
| AC3 | I can see the users I blocked ("Blocked users") and unblock them from there. |
| AC4 | I can report a user, thread, message or call with a reason and optional details (max 500 characters). One open report per reporter and target; a repeat is accepted without creating a duplicate. |
| AC5 | Every report keeps the evidence: the containing thread (and, for a call, that call) is put on hold so retention cannot delete it before an Admin reviews the report. |
| AC6 | Blocking while a chat is open makes the thread read-only for both people (`ERROR_BLOCKED` on send, banner and disabled composer in the app); unblocking restores it. History stays visible. |
| AC7 | Blocking does not cancel an active price agreement or an order; it only stops new contact. |

**Edge cases (LLD C.1.1):** blocking oneself (`ERROR_INVALID_BLOCK`, 422); blocking or unblocking twice; report of a target the reporter was not part of (404, so ids cannot be probed); false or abusive reporting (rate limit plus counter; Admin review is Sprint 10); report during a call (on hold with calls).
**Validation rules:** `details` at most 500 characters and plain text; unknown reason is rejected; at most `REPORTS_PER_DAY` (default 10, range 1 to 50) reports per user per day.
**Errors:** `ERROR_BLOCKED` (403), `ERROR_INVALID_BLOCK` (422), `ERROR_INVALID_REPORT_REASON` (422), not found (404), `RATE_LIMIT_EXCEEDED` (429, existing code).
**Out of scope (LLD C.2):** Admin review UI and actions (US-057, US-055), penalties (US-051), hiding listings from blocked buyers in search.

## 3. Design Reference

LLD Part C: C.3 data model, C.4 API, C.5 backend design, C.6 mobile, C.7 rules and codes, C.8 security, C.9 tests; section 1.3 (module layout `com.valuex.communication`), 1.6 (settings mechanism), 1.7 (migration table), 8.2 (error catalogue), 9.1 D3 and D17.

### Key design decisions

- Two tables, `user_blocks (blocker_id, blocked_id)` with a primary key on the pair and a self-block CHECK, and `communication_reports` (target type, reason and status CHECK constraints, a partial unique index so a reporter has one `OPEN` report per target). Both in one migration.
- `BlockService.isBlockedEitherWay(a, b)` is one indexed query over both directions, cached for the duration of a request. It is the single guard every later contact path calls.
- `ReportService.report` resolves the reported user from the target, refuses targets the reporter was not part of with the not-found error, cleans `details` with `PlainText`, applies `REPORTS_PER_DAY`, and puts the evidence on hold through `CommunicationHoldPort`.
- The report limit is a `CommunicationSetting` (Admin-managed, decision D17), read through `PlatformSettingsService`, so an Admin change applies without a restart.
- Privacy: users can write reports but never read them back; the block list is only readable by the blocker; a blocked person is never told.

### Verified implementation anchors (checked against `origin/main` on 2026-11-15)

| Area | Finding and consequence |
|---|---|
| `communication` package | Contains only `package-info.java` (its javadoc still says "voice calls, video sessions"; update it). Parts C to H all live here (LLD 1.3): `api/BlockController`, `ReportController`, `application/service/BlockService`, `ReportService`, `application/port/CommunicationHoldPort`, `domain/UserBlock`, `CommunicationReport`, `infrastructure/persistence`. |
| Settings registry | `PlatformSettingsService` exposes only `discovery()` and caches one `DiscoverySettings` snapshot. `CommunicationSetting` and `communication()` do not exist (LLD 1.6 says "same shape as `DiscoverySetting`"). US-132 is the first story to need them, so it creates the registry and a second cached snapshot (gap G3). |
| Rate limiting | The pattern is `RedisCacheService.checkRateLimit(key, max, window)` and `throw new RateLimitedException("RATE_LIMIT_EXCEEDED", ...)`, as in `SavedListingService` and `AccountSecurityService`. |
| Exceptions | `NotFoundException`, `ConflictException`, `ForbiddenException` (for `ERROR_BLOCKED`, 403), `ValidationException` (422 codes), `RateLimitedException` and `BusinessException` exist in `common/exception`. |
| Plain text | `common/util/PlainText` exists for `details`. |
| User identity | `auth.domain.User` has `display_name` (nullable, 50). The block list needs a display name and a fallback when it is null. The other modules reach users through ports (LLD 1.3 names `ParticipantDirectoryPort`, implemented in `auth`). |
| Events | `UserStateChangedEvent` exists in `auth`; `ThreadReadOnlyChangedEvent` does not (it belongs to the chat design, gap G2). |
| Mobile | Profile screen already has an Account section (`profile_screen.dart`, rows such as `accountSecurity`); routes are in `core/routing/app_router.dart` (`RouteNames`); a `seller_profile_screen.dart` exists in `features/listing_view`; strings are in `app_en.arb` and `app_hi.arb`; saved searches and saved items features show the repository, controller and screen pattern to copy. |

## 4. Implementation Steps

### Documents (first, small)
- [ ] Add US-132 (and, when planned, US-130 and US-131) to `Sprint-plan.md` Sprint 4 and `user-stories.md` using LLD C.1 as the story text and the approved acceptance criteria of section 2 above, as the LLD hand-off list (8.7 items 7 and 8) asks (gap G1, approved).

### Database
- [ ] Migration `V<next>__user_blocks_and_reports.sql`: `user_blocks` (PK, self-block CHECK, `idx_user_blocks_blocked`), `communication_reports` (CHECKs, `uq_reports_open_per_target`, `idx_reports_status`) exactly as LLD C.3.
- [ ] Seed `REPORTS_PER_DAY` = 10 in `platform_settings` with `INSERT ... ON CONFLICT (setting_key) DO NOTHING`.

### Backend (`valuex-backend`)
- [ ] `plans/domain`: new `CommunicationSetting` enum (same shape as `DiscoverySetting`: kind, default, minimum, maximum, `parse`) with `REPORTS_PER_DAY` (1 to 50, default 10) only; new `CommunicationSettings` snapshot; `PlatformSettingsService.communication()` with its own cache, evicted with the existing `evict()`. Later stories add their keys (LLD 1.6 list).
- [ ] `communication/domain`: `UserBlock` (composite id), `CommunicationReport`, enums `ReportTargetType`, `ReportReason`, `ReportSource`, `ReportStatus`.
- [ ] `communication/infrastructure/persistence`: `UserBlockRepository` (`existsEitherWay` as one query on both directions, paged list by blocker), `CommunicationReportRepository`.
- [ ] `BlockService`: `block` (idempotent insert; `ERROR_INVALID_BLOCK` for self; 404 for an unknown user), `unblock` (idempotent), `isBlockedEitherWay(a, b)` with a per-request cache, `list` (user id, display name, `blockedAt`, paged). After block and unblock, publish `UserBlockedEvent` and `UserUnblockedEvent` (the chat story listens to make threads read-only, gap G2).
- [ ] `ReportService.report(reporterId, request)`: validate reason (`ERROR_INVALID_REPORT_REASON`); `REPORTS_PER_DAY` through `checkRateLimit` with a 24 hour window (gap G5); resolve `reported_user_id` and refuse a target the reporter was not part of with `NotFoundException`; clean `details` with `PlainText`; insert, treating the partial unique index as "already reported" and returning the existing report id; call `CommunicationHoldPort.hold(...)` (gap G2). Reports are write-only for users.
- [ ] `ReportTargetResolver` port with one implementation per target type, so `USER` works now and `THREAD`, `MESSAGE` and `CALL` are added by US-013 and US-014 without changing `ReportService` (gap G2).
- [ ] `CommunicationHoldPort` interface (LLD Part H) with a no-op default bean until US-016 provides the real one (gap G2).
- [ ] `BlockController` (`PUT` and `DELETE /api/v1/users/{userId}/block`, `GET /api/v1/users/me/blocks?page=0&size=20`) and `ReportController` (`POST /api/v1/reports`, 201 `{reportId}`), request records with Bean Validation, OpenAPI annotations, authenticated users only (`SecurityConfig` needs no public path).
- [ ] Error handling: `ERROR_BLOCKED` is defined here as the shared code (`ForbiddenException`, 403) for the later contact paths; `ERROR_INVALID_BLOCK` and `ERROR_INVALID_REPORT_REASON` through `ValidationException` (422).
- [ ] Metrics: `communication.block{action}`, `communication.report{target,reason}`, `retention.held{source=report}` placeholder left to US-016. Log ids only, never `details`.
- [ ] Update `communication/package-info.java` to the Part C module description.

### Mobile (`valuex-mobile`)
- [ ] `features/communication_safety/` (name to confirm, gap G6): `data/block_repository.dart`, `data/report_repository.dart`, `domain` models (`BlockedUser`, `ReportReason`), Riverpod controllers; endpoints in `api_constants.dart`.
- [ ] `BlockedUsersScreen` at `/blocked-users` (route in `app_router.dart`): paged list with name and unblock action, empty and error states with Retry, confirmation not needed for unblock.
- [ ] Profile > Account: add the "Blocked users" row to `profile_screen.dart`.
- [ ] Shared widgets reused by later stories: `BlockConfirmationDialog` (explains what changes), `ReportSheet` (reason list from the LLD, optional details field with a 500 character counter, error states including 429), and snackbars for `ERROR_BLOCKED`.
- [ ] Entry points available now: Block and Report on the seller profile screen (gap G6). The chat overflow menu, the read-only banner and the disabled composer ship with US-013; call-screen Report ships with US-014 (on hold).
- [ ] English and Hindi strings (`app_en.arb`, `app_hi.arb`, regenerate l10n), 48 dp targets, semantic labels.

### Documents (at the end)
- [ ] Update LLD Part C with as-built notes and the changelog (Sprint 3 style), `user-stories.md` and Sprint-plan status, and write `Manual Testing Guides/US-132-Testing-Guide.md`.

## 5. Test Plan

| Level | Cases | Covers |
|---|---|---|
| Unit | `BlockServiceTest`: block, repeat block, unblock, repeat unblock, self-block, unknown user, either-way check in both directions, request-level cache, list mapping with a null display name | AC1, AC2, AC3 |
| Unit | `ReportServiceTest`: resolution of the reported user, not-part-of-target is 404, unknown reason, duplicate open report returns the same id, a closed report allows a new one, `details` cleaned and capped at 500, daily limit and the 24 hour window, hold requested on every report, hold failure does not lose the report | AC4, AC5 |
| Unit | `CommunicationSettingTest` (range, parse, default on invalid) and `PlatformSettingsServiceTest` for `communication()` and cache eviction | settings |
| Integration (Testcontainers PostgreSQL, Redis) | Migration applies; self-block CHECK and open-report unique index enforced by the database; concurrent duplicate reports create one row; user A cannot read user B's block list; blocked user receives the same 403 body whoever blocked; unblock restores | AC1 to AC4 |
| Controller | 204 and 201, 401, 403, 404, 422 and 429 envelopes for each endpoint; paging | API |
| Contract test (shared, reused by later stories) | A helper that asserts a contact entry point answers `ERROR_BLOCKED` for a blocked pair; run against the first real entry point when US-069 lands | AC2 |
| Mobile | Blocked Users loading, empty, error, unblock; Report sheet validation, counter, failure and 429; Block confirmation; seller-profile entry; Hindi and 200 percent text; accessibility labels | AC1, AC3, AC4 |

Target above 90 percent line coverage on new and changed code (CODING_STANDARDS 1.8). AC6 and AC7 (read-only thread, price agreement and orders untouched) are verified by US-013 and US-017 tests against the events defined here.

## 6. Validation Checklist

- [ ] AC1 to AC5 each have a passing test; AC6 and AC7 hooks exist and are documented for US-013 and US-017.
- [ ] Block, unblock, repeat of each, self-block and unknown user behave as specified.
- [ ] `ERROR_BLOCKED` text is exactly "You cannot contact this seller" and never reveals who blocked whom.
- [ ] A report of a target the reporter was not part of returns 404, so ids cannot be probed.
- [ ] One open report per reporter and target; the 11th report in a day returns `RATE_LIMIT_EXCEEDED`; changing `REPORTS_PER_DAY` applies without a restart.
- [ ] `details` is plain text, limited to 500 characters, and never logged.
- [ ] No endpoint reads reports back; the block list is not visible to the blocked person.
- [ ] The block check uses indexed queries only (primary key plus `idx_user_blocks_blocked`).
- [ ] Checkstyle, SonarQube, `dart format` and `flutter analyze` clean; build passes; coverage above 90 percent.

## 7. Open Gaps / Questions

| ID | Gap | Proposal |
|---|---|---|
| G1 | US-132 is not in `Sprint-plan.md` or `user-stories.md`, and the LLD has a story statement but no acceptance criteria. Section 2 derives them from LLD C only. | **Decided (2026-11-15):** derived criteria AC1 to AC7 approved; the story is added to both documents as the first step. |
| G2 | The LLD wires reports and blocks to things that do not exist yet: `chat_threads`, `chat_messages` and `call_sessions` (US-013, US-014), `CommunicationHoldPort` (Part H, US-016) and `ThreadReadOnlyChangedEvent` / `chat.thread.updated` (Parts A and E). A report on a message, thread or call and the read-only thread cannot be completed in this story. | **Decided (2026-11-15):** build the stable contracts now: `ReportTargetResolver` (only `USER` implemented), `CommunicationHoldPort` with a no-op bean, and `UserBlockedEvent` / `UserUnblockedEvent`. US-013 adds the thread and message resolvers, the read-only handling and the real hold; US-014 adds the call resolver. Until then a non-`USER` report target answers the not-found error. |
| G3 | `CommunicationSetting` and `PlatformSettingsService.communication()` do not exist, and the service is typed to discovery settings. | **Decided (2026-11-15):** US-132 creates the registry with only `REPORTS_PER_DAY`; later stories add their keys, each seeding with `ON CONFLICT DO NOTHING`. The Admin screen is US-116 (Sprint 10); until then a value changes by database update. |
| G4 | The LLD migration number (V33) is stale; `main` is at V31. | Use the next free number at branch time (V32 if US-131 is not merged first) and update the LLD, as in Sprint 3. |
| G5 | "10 reports per day" does not say rolling 24 hours or calendar day. | Rolling 24 hours through `checkRateLimit`, as other limits do. Redis-failure behaviour follows the existing helper. |
| G6 | With no chat yet, the LLD's menu entry points (chat thread overflow, call screen) do not exist, and the LLD names no entry point on the seller profile. | **Decided (2026-11-15):** ship the Blocked Users screen and the shared Block and Report widgets, and add Block and Report on the existing seller profile screen so the feature is testable now. Chat and call entry points follow with their stories. |
| G7 | The LLD does not say whether a user can block a suspended or deleted account, or what an unknown id returns. | Unknown or deleted id returns 404; any existing account can be blocked. |
| G8 | The blocked-person view: C.5 says `ERROR_BLOCKED` is "the same response whether the pair is blocked or the seller is simply unavailable, apart from the code". | Use the same message and status; only later stories' unavailable codes differ. No extra work here. |
| G9 | Report reason labels and block-confirmation copy are not in the LLD. | English and Hindi texts drafted in the PR; Hindi marked for native-speaker review (O5). |

**Status: Approved** (user, 2026-11-16)

---

## 8. As built: deviations (2026-11-16)

The full account is in LLD Part C.10. Where the built story differs from this plan:

| # | Plan | As built | Why |
|---|---|---|---|
| D1 | Next free Flyway number (V32). | `V32__user_blocks_and_reports.sql`; also CHECKs on `source` and `status`. | As planned. |
| D2 | `ERROR_INVALID_BLOCK` and `ERROR_INVALID_REPORT_REASON` answer 422 (validation "422 codes"). | 400 through `ValidationException`. | The backend has no 422 handler; all validation errors are 400. |
| D3 | `isBlockedEitherWay` with a per-request cache. | One indexed query per call, no cache. | No caller yet; add the cache when chat makes it a hot path. |
| D4 | `ParticipantDirectoryPort` implemented in auth. | `auth/infrastructure/communication/ParticipantDirectoryAdapter`; a `CLOSED` account counts as not found. | Matches the existing adapter pattern and decision G7. |
| D5 | `ReportTargetResolver`, no-op hold port, events (G2). | Built as planned: `UserReportTargetResolver`, a `@ConditionalOnMissingBean` no-op `CommunicationHoldPort`, `UserBlockedEvent` and `UserUnblockedEvent` (published only when the block changed). The hold is requested only for a newly stored report. | A repeat report keeps the same evidence. |
| D6 | Settings registry with `REPORTS_PER_DAY` (G3). | Built; the parse logic is shared through a small `SettingValue` helper that `DiscoverySetting` also uses. | Avoids duplicating the parser. |
| D7 | Rolling 24 hour limit (G5). | A fixed 24 hour window from the first report through `checkRateLimit`; Redis failure allows the request with a warning. | Same behaviour as the other limits. |
| D8 | Block and Report on the seller profile (G6). | Built, hidden on the user's own profile; also Profile > Account > Blocked users. | As planned. |
| D9 | Reporting yourself is not described. | Answers 404. | A person is not a party to themselves. |
| D10 | Integration test only for the database behaviour. | `BlockAndReportIntegrationTest` (Testcontainers) is written but could not be run locally because the Docker engine was not responding; unit tests cover every service and repository. | Run it in CI or after restarting Docker. |

Open item carried over: Hindi texts need native-speaker review (G9, O5).
