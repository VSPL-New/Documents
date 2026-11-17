# US-130: Realtime Gateway (WebSocket) - Implementation Plan

## 1. Header

| Field | Value |
|---|---|
| Story | US-130 - Realtime Gateway (WebSocket) (**proposed story**, found missing while writing the Sprint 4 LLD; not yet in `user-stories.md`, and `Sprint-plan.md` only mentions it in the 2026-11-15 note under Sprint 4, see gap G1) |
| Sprint | Sprint 4 - Communication & Negotiation |
| Story points | 5 (proposed in LLD Part A) |
| Repos involved | valuex-backend (WebSocket endpoint, ticket service, Redis fan-out, presence), valuex-mobile (`RealtimeClient`, lifecycle, polling fallback, banner), valuex-infra (ingress and TLS notes only). No `valuex-ai` or `valuex-web` change. |
| Dependencies | S0-001 (backend skeleton, done), US-107 (access token refresh, done: testing guide exists) and US-013 (chat, built 2026-11-17, PRs backend #68 and mobile #77 must be merged first because this story wires chat into the gateway). US-130 no longer blocks US-013: chat shipped on REST plus 15 s polling and this story upgrades it. It still blocks US-014/015 (on hold), US-017, US-018 and US-076. |
| Date | 2026-11-16; reviewed against the code on 2026-11-17 (changes are marked "2026-11-17" in the text and in gaps G2, G7, G8 and G11 to G14) |
| Design source | [Sprint 4 LLD](../LLD/Sprint-4-Communication-Negotiation-LLD.md) Part A (A.1 to A.10), section 1.1 (principles 1 and 2), 1.3 (package layout `com.valuex.realtime`), 1.5 (deployment configuration) and decision D2. |
| Branches (proposal) | `feature/US-130-realtime-gateway` in `valuex-backend`, `valuex-mobile` and `valuex-infra` (if its docs change), cut from `main` after backend #68 and mobile #77 (US-069 and US-013) are merged, and rebased before work starts (CLAUDE.md rule 5.1). US-132 is already on `main`. Local checkouts are currently on `feature/US-069-US-013-contact-and-chat`, so switch to `main` and pull first (G8). |
| Flyway number | No PostgreSQL table (A.3); state lives in Redis with TTLs. One seed-only migration for the Admin-managed realtime settings: **`V35__realtime_settings.sql`** (V33 and V34 are taken by US-069 and US-013; the LLD's provisional V35 belongs to on-hold calls and will move). Re-check the number at branch time. |

## 2. Story Recap

The LLD gives a story statement and edge cases but no acceptance-criteria list. The criteria below are derived from LLD A.1 to A.9 only; nothing is added to them (gap G1).

**As a** signed-in user **I want** new messages, offers and incoming calls to reach me immediately **so that** a conversation feels live.

| ID | Behaviour (derived from LLD Part A) |
|---|---|
| AC1 | A signed-in user gets a single-use ticket (`POST /api/v1/realtime/tickets`, 30 s lifetime, bound to the user) and opens `wss://.../ws/v1?ticket=...`. The access token never appears in a URL. A missing, unknown, reused or expired ticket is refused with 401. |
| AC2 | The handshake is refused with 403 when the account is not `ACTIVE` or a present `Origin` is not in `valuex.realtime.allowed-origins`. |
| AC3 | A service publishes an event with `RealtimePublisher.publishToUser(userId, type, data)` after commit, and every open session of that user, on any backend instance, receives the envelope. A user only ever receives events for their own id. |
| AC4 | A user can hold several sessions (up to `max-sessions-per-user`); a further session closes the oldest with 4409. |
| AC5 | The server closes a session with 4401 before the access token expires; with 4403 when the account stops being `ACTIVE`; with 4408 for a slow consumer; with 4413 for an oversized frame; with 4429 above 20 inbound frames per second; with 1001 on shutdown. |
| AC6 | Client signals work: `ping` is answered by `pong`, `app.state` sets foreground or background for presence, and typed frames are forwarded to their services. Unknown types are ignored and counted. |
| AC7 | `PresenceService.isOnline(userId)` is true only while at least one foreground session was heard from in the last 90 s. |
| AC8 | If Redis is unavailable, events reach sessions on the same instance, the failure is counted, and REST writes are unaffected. |
| AC9 | The mobile `RealtimeClient` connects, pings, reconnects with backoff, handles the close codes, re-syncs after every reconnect, applies events idempotently, and falls back to 15 s polling when realtime is unavailable. |
| AC10 | **Chat goes live (added 2026-11-17, gap G11).** A message sent in a thread reaches the other person's open app without polling (`chat.message.created`, also to the sender's other devices); delivered and read cursors, typing (`chat.typing`, never stored) and read-only changes after a block (`chat.thread.updated`) arrive as events; the client sends `chat.delivered`, `chat.read` and `chat.typing` over the socket. While the socket is connected the chat list and thread do not poll; when it is down they poll every 15 s as today. Chat behaviour over REST is unchanged. |

**Edge cases (LLD A.1.1):** network switch, app backgrounded or killed, token expiry while connected, same account on two phones, suspended or banned account, backend restart during a deploy, slow or stalled client, Redis down, replayed or stolen ticket.
**Validation rules:** ticket 43 characters, 32 random bytes, stored as SHA-256 with a 30 s TTL and consumed with an atomic get-and-delete; ticket endpoint limited to 30 calls per minute per user; inbound frames capped at `max-inbound-message-bytes`; token bucket of 20 frames per second per session.
**Errors:** `ERROR_REALTIME_UNAVAILABLE` (503), `ERROR_ACCOUNT_NOT_ACTIVE` (403), standard 401, `RATE_LIMIT_EXCEEDED` (429, existing code); close codes 1001, 4401, 4403, 4408, 4409, 4413, 4429.
**Out of scope (LLD A.2):** the content of call and negotiation events (Parts F to L), a web client, push (Part B, US-131), message persistence (built in US-013). Chat events are now in scope (AC10, gap G11).

## 3. Design Reference

LLD Part A: A.3 Redis keys, A.4 contract (ticket, connection, event types, client frames, close codes), A.5 backend design, A.6 sequence diagram, A.7 mobile design, A.8 rules and codes, A.9 security and NFR, A.10 tests; section 1.1 principles 1 and 2 (PostgreSQL is the source of truth, realtime is a hint; writes go over REST).

### Key design decisions

- **Realtime is a hint.** After any gap the app re-reads over REST with sequence cursors, so no event is needed for correctness. This lets Redis loss and reconnects degrade gracefully (A.1.1, A.7).
- **Ticket, not token.** `POST /realtime/tickets` (Bearer) returns a single-use 30 s ticket; the WebSocket handshake carries only that ticket. It is hashed in Redis and consumed with `GETDEL`.
- **No PostgreSQL.** Three Redis keys: `rt:ticket:{sha256}`, `rt:presence:{userId}` (sorted set) and the `rt:u:{userId}` pub/sub channel (A.3).
- **Fan-out through Redis pub/sub** with a pattern subscription `rt:u:*` on each instance, so no sticky sessions are needed. `RealtimePublisher` is called only from `AFTER_COMMIT` listeners.
- **Per-session protection:** `ConcurrentWebSocketSessionDecorator` with a send time limit and buffer limit, a token bucket, a frame size cap and an idle sweep.
- **Mobile owns one `RealtimeClient`** behind a Riverpod provider; features read typed providers and never the raw socket.

### Verified implementation anchors (checked 2026-11-16)

| Area | Finding and consequence |
|---|---|
| WebSocket dependency | `valuex-backend/pom.xml` has no `spring-boot-starter-websocket`; it has `spring-boot-starter-data-redis`. `valuex-mobile/pubspec.yaml` has no `web_socket_channel`. Both are added. |
| `realtime` package | Does not exist. Create `com.valuex.realtime` (LLD 1.3). |
| Redis helper | `common/cache/RedisCacheService` offers `checkRateLimit`, `set`, `get`, `setIfAbsent`, `delete` but no `GETDEL`, sorted set or pub/sub. The realtime classes use `StringRedisTemplate` and `RedisMessageListenerContainer` directly (gap G4). The ticket endpoint rate limit reuses `checkRateLimit`. |
| Token expiry | `common/security/JwtTokenProvider.getExpirationFromToken(token)` returns the `Instant` needed for `tokenExp` and `sessionDeadline`. Access tokens last 3,600,000 ms (`valuex.jwt.access-token-expiry`). |
| Account state | `auth/domain/UserStateChangedEvent` (a `DomainEvent`; carries `userId`, `fromState`, `toState`, `action`, `actorId`, `reason`) exists; a listener can close sessions when `toState` is not `ACTIVE`. `communication/application/port/ParticipantDirectoryPort` has `activeAmong(Collection<UUID>)` (extended by US-013, on the US-069/013 branch until #68 merges); the handshake uses `activeAmong(List.of(userId))`. |
| Security config | `common/config/SecurityConfig` uses `requestMatchers(...).permitAll()` lists and `hasAnyRole` for admin; `/ws/v1` is added to the permitted list, the ticket endpoint stays authenticated. |
| Settings | `application.yml` has a `valuex:` block (jwt, cors, api, otp, and `calls.enabled` from US-069). Only `valuex.realtime.enabled` and `allowed-origins` stay deployment configuration (LLD 1.5). All tunable numbers become Admin-managed `CommunicationSetting` keys (G3, decided). `CommunicationSetting` now holds 12 keys (`REPORTS_PER_DAY` plus the contact and chat keys of US-069 and US-013), each `(default, min, max)`, read through `PlatformSettingsService.communication()`; `CommunicationSettings.of(...)` applies the range per key only, so the cross-field rule (idle timeout greater than ping interval) is a check in the realtime code, not in the registry (G12). |
| Error codes | `ERROR_ACCOUNT_NOT_ACTIVE` exists as a constant in `communication/.../ContactGuard`; `common/exception/ErrorCodes` (shared codes) exists since US-069. Move the constant to `ErrorCodes` and reuse it (G7, resolved). |
| Chat hooks (new) | `communication/domain/ChatMessageCreatedEvent(threadId, messageId, seq, senderId, recipientId)` is published inside the send transaction and consumed by `ChatMessageListener` (AFTER_COMMIT, REQUIRES_NEW, in-app notification only). `ChatMessageService.markDelivered` and `markRead` move the cursors and publish nothing. `UserBlockedEvent` and `UserUnblockedEvent` exist (US-132) but nothing turns them into a thread update, because `canSend` is computed on every read. `ChatMessageMapper.map(callerId, thread, rows)` builds the REST message shape per viewer (it signs image links), so the realtime payload reuses it. `ChatAccessPolicy` gives `canSend` and the read-only reason. |
| Mobile | `core/network` (`api_client.dart`, `token_refresher.dart`, `session_event.dart`) holds Dio, token refresh and session events; `core/realtime/` does not exist. Routing is in `core/routing`. The sign-out hook is the existing session event. Chat already polls: `features/chat/presentation/providers/chat_polling.dart` exposes `chatPollIntervalProvider` (15 s, null turns it off), used by `ChatThreadController.build` (`_poll` re-reads the thread and `afterSeq = lastSeq`) and `ChatListController`. The `_poll` method is the re-sync this story reuses. |

## 4. Implementation Steps

### Documents (first, small)
- [ ] Add US-130 to `Sprint-plan.md` Sprint 4 and `user-stories.md` using LLD A.1 as the story text and the approved criteria of section 2 (AC1 to AC10), as the LLD hand-off list (8.7 items 7 and 8) asks (gap G1). Update the Sprint 4 story-count lines and the US-013 row, which says "realtime and push with US-130, US-131".

### Database
- [ ] No realtime table (LLD A.3). Only the settings-seed migration (see Backend, Admin-managed settings).

### Backend (`valuex-backend`)
- [ ] `pom.xml`: add `spring-boot-starter-websocket`.
- [ ] `application.yml`: add only `valuex.realtime.enabled` (default `true`) and `valuex.realtime.allowed-origins` (default empty); bind in `ValuexProperties`.
- [ ] Admin-managed settings (G3): add to `CommunicationSetting` the keys `REALTIME_MAX_SESSIONS_PER_USER` (3), `REALTIME_PING_INTERVAL_SECONDS` (25), `REALTIME_IDLE_TIMEOUT_SECONDS` (75), `REALTIME_TICKET_TTL_SECONDS` (30), `REALTIME_MAX_INBOUND_BYTES` (8192), `REALTIME_SEND_BUFFER_BYTES` (524288), `REALTIME_SEND_TIME_LIMIT_SECONDS` (5), `REALTIME_INBOUND_FRAMES_PER_SECOND` (20) and `REALTIME_TICKET_REQUESTS_PER_MINUTE` (30), each with a minimum and maximum; seed them in `V35__realtime_settings.sql` with `INSERT ... ON CONFLICT (setting_key) DO NOTHING` (same style as `V34__chat.sql`). Services read them through `PlatformSettingsService.communication()`, so a change applies without a restart (new sessions use new values; open sessions keep the limits they started with). Cross-field rule (G12): the registry only checks ranges per key, so a small `RealtimeLimits` reader in `com.valuex.realtime` falls back to the two defaults (idle 75 s, ping 25 s) and logs a warning when idle timeout is not greater than the ping interval. Defaults are the LLD 1.5 and A.4 values.
- [ ] `realtime/config/WebSocketConfig`: register `RealtimeWebSocketHandler` on `/ws/v1` with `RealtimeHandshakeInterceptor`; `SecurityConfig` permits `/ws/v1` at the filter level (the ticket is the credential).
- [ ] `realtime/application/RealtimeTicketService`: `issue(userId, tokenExp)` (32 random bytes, base64url, store `rt:ticket:{sha256}` for 30 s) and `consume(ticket)` (`GETDEL`, empty when unknown or used).
- [ ] `realtime/api/RealtimeTicketController`: `POST /api/v1/realtime/tickets`, returns `{ticket, expiresInSeconds, url, pingIntervalSeconds}`; `ERROR_REALTIME_UNAVAILABLE` (503) when `valuex.realtime.enabled=false`; account state check (`ERROR_ACCOUNT_NOT_ACTIVE`, constant moved from `ContactGuard` to `common/exception/ErrorCodes`, G7); rate limit `REALTIME_TICKET_REQUESTS_PER_MINUTE` (30) per user (`RATE_LIMIT_EXCEEDED`); OpenAPI annotations. Pass the access token expiry from the request into `issue`.
- [ ] `realtime/infrastructure/RealtimeHandshakeInterceptor`: check `Origin` when present against `allowed-origins`, consume the ticket (401 when missing, unknown or used), require `ACTIVE` through `ParticipantDirectoryPort` (403), store `userId` and `sessionDeadline` in session attributes.
- [ ] `realtime/infrastructure/LocalSessionRegistry`: `ConcurrentHashMap<UUID, Set<Session>>`, each session wrapped in `ConcurrentWebSocketSessionDecorator`; `deliver(userId, json)`; per-user session cap (oldest closed with 4409); scheduled sweep closing sessions past `sessionDeadline` (4401) and idle sessions; close of all sessions of a user (4403); slow consumer closed with 4408 on a send timeout or buffer overflow; shutdown closes with 1001.
- [ ] `realtime/application/RealtimePublisher`: `publishToUser(userId, type, data)` builds the envelope and `PUBLISH rt:u:{userId}`; on Redis failure fall back to local delivery and count `realtime.publish.failures`. Document and test that it is meant for `AFTER_COMMIT` listeners only.
- [ ] `realtime/infrastructure/RedisRealtimeBus`: subscribe to the pattern `rt:u:*` on every instance and call `LocalSessionRegistry.deliver`.
- [ ] `realtime/application/PresenceService`: `touch(userId, sessionId, foreground)`, `remove`, `isOnline(userId)` on the sorted set `rt:presence:{userId}` (score = expiry epoch seconds, key TTL 120 s, 90 s liveness window).
- [ ] `realtime/application/AccountStateRealtimeListener`: on `UserStateChangedEvent` with `toState` not `ACTIVE`, close all sessions of that user through the bus so every instance acts.
- [ ] `realtime/infrastructure/RealtimeWebSocketHandler`: parse JSON frames, token bucket of `REALTIME_INBOUND_FRAMES_PER_SECOND` (20) per session (4429), frame size cap (4413), handle `ping`/`pong`, `app.state`; ignore and count unknown types; a handler failure answers an `error` event without closing the session except for protocol violations. `chat.typing`, `chat.delivered`, `chat.read` and `call.heartbeat` are routed through a small `InboundFrameHandler` registry so stories register their handlers without changing the gateway. This story registers the three chat handlers itself (see Chat wiring below); `call.heartbeat` stays unknown until US-014 (gap G2).

#### Chat wiring (AC10, gap G11)
- [ ] `communication/application/service/ChatRealtimeListener` (new, AFTER_COMMIT, no transaction needed): on `ChatMessageCreatedEvent` loads the message, maps it with `ChatMessageMapper` for each viewer (recipient: `fromMe=false`; sender's other devices: `fromMe=true`) and calls `RealtimePublisher.publishToUser(..., "chat.message.created", message)`; failures are logged and counted, never reach the sender (same rule as `ChatMessageListener`). Payload above about 3 KB (LLD A.4) is replaced by a `chat.thread.updated`-style hint so the client re-reads over REST.
- [ ] `ChatMessageService.markDelivered` and `markRead` publish a new `ChatCursorMovedEvent(threadId, userId, kind, upToSeq)` only when the cursor actually moved; a second AFTER_COMMIT listener sends `chat.message.delivered` or `chat.read` to the other participant.
- [ ] `UserBlockedEvent` and `UserUnblockedEvent` (US-132): a listener finds the pair's threads (`ChatThreadRepository`, one indexed query) and publishes `chat.thread.updated {threadId, canSend, readOnlyReason, lastSeq}` to both people, using `ChatAccessPolicy` for the values. The same event is published when a listing is removed (existing reasons only; no new reason added).
- [ ] Inbound handlers registered in the `InboundFrameHandler` registry: `chat.delivered` and `chat.read` call the same `ChatMessageService` methods as the REST endpoints (so the same clamping and 404 for non-participants apply); `chat.typing` checks the caller is a participant and the thread is writable, then relays `chat.typing {threadId, userId, typing}` to the other person; rate-limited by the per-session token bucket, never stored, never logged.
- [ ] Settings: no new key for chat; typing is relayed at most once per second per thread on the client.
- [ ] `realtime/domain/RealtimeEnvelope` and the event type constants of LLD A.4.3 and A.4.4; error code constants (`ERROR_REALTIME_UNAVAILABLE`).
- [ ] Metrics (A.5): `realtime.sessions.active`, `realtime.events.sent.total{type}`, `realtime.events.received.total{type}`, `realtime.send.failures{reason}`, `realtime.connect.total{outcome}`, `realtime.publish.failures`. Log type, session id and user id only, never the payload.
- [ ] Update the `realtime` `package-info.java`.

### Infra (`valuex-infra`)
- [ ] Document the ingress needs (WebSocket upgrade, idle timeout of at least 75 s, no sticky sessions, `wss` with TLS 1.3 per HLD 06) and the `valuex.realtime.*` environment variables, in the infra docs; `docker-compose.yml` needs no change (A.5). Where those docs live in `valuex-infra` is to be confirmed (gap G5).

### Mobile (`valuex-mobile`)
- [ ] `pubspec.yaml`: add `web_socket_channel` (version pinned when built, A.7).
- [ ] `core/realtime/realtime_client.dart`: interface `RealtimeClient` (`Stream<RealtimeEvent> events`, `connect()`, `disconnect()`, `send(type, data)`, `ConnectionState state`) and `WebSocketRealtimeClient`; `RealtimeEvent` envelope model; endpoint and event type constants in `api_constants.dart`.
- [ ] Connect flow: `POST /realtime/tickets`, open the socket, send `app.state {foreground:true}`, ping every `pingIntervalSeconds`; backoff 1, 2, 4, 8, 16, 30 s with jitter, reset after a stable minute; 4403 stops reconnecting (account state screen), 4401 refreshes the token first through `token_refresher.dart`, 4409 reconnects only on user action, 4408 and 4413 reconnect, 4429 backs off 30 s.
- [ ] Riverpod provider owns the client for the signed-in session; sign-out disconnects it (existing session event).
- [ ] Lifecycle: a `WidgetsBindingObserver` sends `app.state {foreground:false}` on pause and closes after 30 s; on resume reconnects and triggers a re-sync.
- [ ] Re-sync contract: a `realtimeResyncProvider` that features subscribe to; this story provides the trigger and idempotent apply helpers (by `id` and `seq`). Chat plugs in now (below); US-017 and later stories plug in their own re-reads (gap G2).
- [ ] Typed providers `chatEventsProvider`, `negotiationEventsProvider`, `callEventsProvider` that filter the stream.
- [ ] Polling fallback: when the ticket call returns `ERROR_REALTIME_UNAVAILABLE`, or the socket cannot open for 60 s, expose a "realtime degraded" state so features poll every 15 s while visible. `chatPollIntervalProvider` (existing, `chat_polling.dart`) becomes derived from that state: 15 s while degraded or disconnected, null while connected; tests that override it with null keep working.
- [ ] "Reconnecting..." banner widget (`realtimeReconnecting`) with a live-region role, shown only while a chat thread is open; English and Hindi strings in `app_en.arb` and `app_hi.arb`, regenerate l10n. It is placed in `ChatThreadScreen` (built in US-013).

#### Chat wiring (mobile, AC10, gap G11)
- [ ] `ChatThreadController`: apply `chat.message.created` (insert by `seq`, ignore duplicates and messages already shown from an optimistic send via `clientMessageId`), `chat.message.delivered` and `chat.read` (update the cursors and the sent/delivered/read status), `chat.thread.updated` (composer and read-only banner), `chat.typing` (indicator hidden after 4 seconds). On a reconnect or app resume call the existing `_poll` logic (`afterSeq = lastSeq`) once.
- [ ] Send `chat.delivered` and `chat.read` over the socket when connected (REST `_markSeen` stays as the fallback) and `chat.typing` from the composer (at most once per second, stop frame after a pause or send).
- [ ] `ChatListController`: refresh quietly on `chat.message.created` and `chat.thread.updated`; `chatUnreadCountProvider` is invalidated on the same events so the unread dot is live without polling.
- [ ] Typing indicator widget in the thread (English and Hindi strings, announced politely to screen readers, hidden at 200 percent text only if it would overflow).

### Documents (at the end)
- [ ] Update LLD Part A (and Part E for the chat wiring) with as-built notes and the change log (Sprint 3 and Part C.10, D.11, E.11 style), `user-stories.md` and Sprint-plan status, and write `Manual Testing Guides/US-130-Testing-Guide.md` (including the shared realtime setup notes the LLD promises, 8.7). Fix the 8.7 migration table: V35 is now the realtime settings and the calls migration moves.

## 5. Test Plan

| Level | Cases | Covers |
|---|---|---|
| Unit | `CommunicationSettingTest` and `PlatformSettingsServiceTest` additions: the new realtime keys (range, default on invalid value, idle timeout greater than ping interval) and a changed value read after cache eviction | G3 |
| Unit | `RealtimeTicketServiceTest`: issue stores a hash only, 43 character ticket, consume returns the user once, second consume empty, expired ticket empty | AC1 |
| Unit | `RealtimePublisherTest` and `RedisRealtimeBusTest`: envelope serialisation, publish to channel, Redis failure falls back to local delivery and counts a failure | AC3, AC8 |
| Unit | `PresenceServiceTest`: touch, foreground and background, expiry of old members after 90 s, `isOnline` true and false, remove | AC7 |
| Unit | `LocalSessionRegistryTest`: deliver to all sessions of a user only, session cap closes the oldest with 4409, deadline sweep 4401, idle sweep, close-all 4403, slow consumer 4408 | AC3, AC4, AC5 |
| Unit | `RealtimeHandshakeInterceptorTest`: missing, unknown and reused ticket (401), inactive account (403), bad `Origin` (403), no `Origin` allowed, valid handshake stores attributes | AC1, AC2 |
| Unit | `RealtimeWebSocketHandlerTest`: ping and pong, `app.state`, unknown type counted, oversize frame 4413, token bucket 4429, handler failure answers `error` without closing, inbound handler registry routing | AC5, AC6 |
| Unit | `RealtimeLimitsTest`: idle timeout not greater than ping interval falls back to the defaults with a warning | G12 |
| Unit | `ChatRealtimeListenerTest`: message published to the recipient (`fromMe=false`) and to the sender's other devices (`fromMe=true`), oversize payload becomes a re-read hint, publisher failure is swallowed and counted, no message text in logs; cursor-moved listener sends `chat.message.delivered` and `chat.read` only when the cursor moved; block, unblock and listing-removal listener sends `chat.thread.updated` with the right `canSend` and reason to both people; inbound `chat.delivered`, `chat.read` and `chat.typing` handlers (participant check, writable check, stranger refused, typing never stored) | AC10 |
| Unit | `AccountStateRealtimeListenerTest`: non-`ACTIVE` state closes sessions, `ACTIVE` does not | AC5 |
| Controller | `RealtimeTicketControllerTest`: 200 shape, 401, 403 inactive, 503 when disabled, 429 on the 31st call in a minute | AC1, AC2 |
| Integration (Testcontainers Redis, embedded server) | Connect with a ticket and receive a published event; ticket reuse refused; token expiry closes with 4401; suspension closes with 4403; fourth session closes the first with 4409; slow consumer closes with 4408; an event published through a second `RedisRealtimeBus` reaches a session on the first "instance"; a user never receives another user's event | AC1 to AC5, AC8 |
| Integration (chat, same setup) | Two users with a thread: a message sent over REST arrives as `chat.message.created` on the recipient's socket and the sender's second socket; `chat.read` sent over the socket moves the cursor and the sender gets `chat.read`; a block sends `chat.thread.updated` with `canSend=false`; a stranger's `chat.typing` frame is ignored | AC10 |
| Mobile (fake socket) | `RealtimeClient`: connect flow and ping, backoff sequence with reset, close-code handling (4401 refresh, 4403 stop, 4409 no auto reconnect, 4408, 4429), resume re-sync, idempotent event apply, polling fallback state, sign-out disconnects, typed provider filtering | AC9 |
| Mobile (chat) | `ChatThreadController` and `ChatListController` with a fake client: event inserts by `seq` and ignores a duplicate and an optimistic echo, cursors and statuses update, read-only update disables the composer, typing shows and hides after 4 s, polling stops while connected and resumes when degraded, one re-sync on reconnect; thread screen shows the typing indicator and the reconnecting banner; existing chat tests still pass unchanged | AC10 |
| Mobile widget | Reconnecting banner shown only while down with a thread open, live-region semantics, Hindi strings, 200 percent text | AC9 |
| Load (manual, not in CI) | Script opens 10,000 sessions and measures publish-to-receive latency against the A.9 targets (p95 under 200 ms, p99 under 500 ms) | NFR |

Target above 90 percent line coverage on new and changed code (CODING_STANDARDS 1.8). Local note: Testcontainers integration tests run locally with `JAVA_TOOL_OPTIONS='-Dapi.version=1.44 -Duser.timezone=UTC'` (Docker Engine 29 and the machine time zone otherwise break them); they ran that way for US-069 and US-013.

## 6. Validation Checklist

- [ ] AC1 to AC9 each have a passing test.
- [ ] The access token never appears in a URL, log line or the ticket value; only the hash of the ticket is stored.
- [ ] A ticket works once; a second use, an expired ticket and a ticket of a non-active account are refused.
- [ ] A user receives only events published to their own id; there is no subscribe-by-id message.
- [ ] Every close code in A.4.5 is produced and handled by the client as specified.
- [ ] Two sessions of one account both receive events; the cap closes the oldest.
- [ ] With Redis down, same-instance delivery works, `realtime.publish.failures` increments and REST writes still succeed.
- [ ] `RealtimePublisher` is documented as `AFTER_COMMIT` only and no caller publishes inside a transaction.
- [ ] No event payload is logged; metrics of A.5 exist and are exposed.
- [ ] Every tunable realtime number is a `CommunicationSetting` seeded with the LLD default, changeable by database update now and by the Admin settings screen once US-116 adds the fields.
- [ ] `valuex.realtime.enabled=false` answers 503 `ERROR_REALTIME_UNAVAILABLE` and the app falls back to polling.
- [ ] English and Hindi strings exist for the banner; Hindi marked for native-speaker review.
- [ ] Checkstyle (120 characters per line, also in tests), SonarQube (quality gate and no new issues; self-invocation of `@Transactional` methods, constant SQL strings and lambdas with several throwing calls were the issues of the last story), `dart format` and `flutter analyze --fatal-infos` clean; build passes; coverage above 90 percent; only the settings-seed migration added.
- [ ] AC10: a message, a read receipt, typing and a block show up live between two phones with no polling while connected; with the gateway disabled (`valuex.realtime.enabled=false`) chat still works over 15 s polling exactly as before; no event payload or typed text is logged.

## 7. Open Gaps / Questions

| ID | Gap | Proposal |
|---|---|---|
| G1 | US-130 is not in `user-stories.md` and `Sprint-plan.md` only mentions it in a note; the LLD has a story statement and edge cases but no acceptance criteria. Section 2 derives AC1 to AC9 from LLD Part A only. | Approve the derived criteria; the story is added to both documents as the first step (same as US-132 G1). |
| G2 | Several hooks referred to things that did not exist: `ChatService`/`CallService` for the inbound frames, the per-feature re-sync and polling, and the thread screen for the banner. **Updated 2026-11-17:** chat now exists, so this story registers the three chat handlers and wires chat itself (G11). The registry, re-sync trigger, polling state and banner stay generic. Only `call.heartbeat` (US-014, on hold) and the negotiation re-reads (US-017) are left to later stories; until then `call.heartbeat` is counted as unknown. | Build the stable contracts as planned; chat plugs in here, US-017 and US-014 later. |
| G3 | The LLD (1.5) lists these numbers as deployment configuration, but the user wants them configurable from the Admin UI. | **Decided (2026-11-16):** they become Admin-managed `CommunicationSetting` keys (see Backend steps) with the LLD 1.5 and A.4 defaults (3 sessions, ping 25 s, idle 75 s, 8192 bytes inbound, 524288 bytes buffer, 5 s send limit, ticket TTL 30 s). The defaults I first proposed were wrong and are dropped. Only `enabled` and `allowed-origins` stay in configuration. **Caveat:** the Admin settings screen is US-116 (Sprint 10), so until then values change by database update; US-130 builds no Admin screen or endpoint. Add these fields to the US-116 scope and LLD 8.7 item 9. |
| G4 | `RedisCacheService` has no `GETDEL`, sorted-set or pub/sub support; the LLD does not say whether to extend it. | Use `StringRedisTemplate` and `RedisMessageListenerContainer` inside `com.valuex.realtime`; keep `RedisCacheService` unchanged (surgical change). Reuse `checkRateLimit` for the ticket endpoint. |
| G5 | The LLD says the infra repository "documents" the ingress and TLS rule but does not name a file; `valuex-infra` contents were not inspected here beyond its existence. | Find the right file when the branch is cut; if there is none, add a short `realtime.md` note. No manifest change is assumed. |
| G6 | How the ticket endpoint learns the access token's `exp` (needed for `tokenExp`) is not specified. | Read it from the request's Bearer token with `JwtTokenProvider.getExpirationFromToken`. |
| G7 | Whether `ERROR_ACCOUNT_NOT_ACTIVE` already exists. | **Resolved 2026-11-17:** it exists as a constant in `ContactGuard` (403 `ForbiddenException`). Move it to the shared `ErrorCodes` and use it from both places. |
| G8 | Local checkouts and the base branch. | **Updated 2026-11-17:** US-132 is on `main`; US-069 and US-013 are in open PRs backend #68 and mobile #77. Start this story after both are merged (cut from `main`). If you want to start earlier, the branch can be cut from `feature/US-069-US-013-contact-and-chat` and rebased after the merge; say so and I will plan for it. |
| G9 | Banner copy and Hindi text are not in the LLD. | Draft English and Hindi in the PR; Hindi marked for native-speaker review (LLD O5). |
| G10 | The 10,000-session load test is manual and may need a load generator tool that is not set up. | Provide a small script and run it once per release; results go in the testing guide. Not a merge gate. |

G1, G2 (as originally proposed), G4, G5, G6, G7, G9 and G10: proposals agreed by the user on 2026-11-16.

**Decided 2026-11-17 (user: "agree" to the recommendations):**

| ID | Decision |
|---|---|
| G11 | Include the chat wiring (AC10) in this story. Story is about 7 SP; Sprint 4 total moves from 53 to about 55 SP. |
| G12 | `RealtimeLimits` reader checks idle timeout against ping interval and falls back to the defaults with a warning; the registry is not changed. |
| G13 | An expired signed image link in an event is handled by re-reading over REST. |
| G14 | Push stays with US-131; the in-app notification stays meanwhile. |

**Status: Approved** (user, 2026-11-17; G11 to G14 decided)

## 8. As built (2026-11-17)

Built on `feature/US-130-realtime-gateway` in `valuex-backend`, `valuex-mobile` and `valuex-infra` (a new `docs/realtime.md`; G5: the repository held only a README). The deviations from the LLD are in LLD A.11 (14 rows) and E.11 (rows 3 and 13 updated). The ones that change behaviour:

- Migration is `V35__realtime_settings.sql` (settings only). The nine `REALTIME_*` numbers are Admin-managed `CommunicationSetting` keys; only `enabled` and `allowed-origins` are properties (G3). `RealtimeLimits` applies the idle-versus-ping rule (G12).
- All users of the gateway close sessions with a `session.close` control message on `rt:u:{userId}` (no fourth Redis key). `ERROR_ACCOUNT_NOT_ACTIVE` moved to the shared `ErrorCodes` (G7).
- Chat wiring (G11): `chat.message.created` carries `{threadId, message}` per viewer; a message over about 3 KB sends a `chat.thread.updated` hint; `chat.message.delivered`, `chat.read`, `chat.typing` and `chat.thread.updated` (block, unblock, Admin removal or rejection of the listing) are built; the inbound frames `chat.delivered`, `chat.read` and `chat.typing` are registered through the `InboundFrameHandler` registry. A change of account state does not send `chat.thread.updated`.
- Mobile: the controllers listen to events, `chatPollIntervalProvider` is 15 seconds only while the socket is not connected, every reconnect and every return to the foreground re-reads the open thread, the list and the unread count. The "Reconnecting…" strip uses a static icon (a spinner stopped `pumpAndSettle` in tests and adds motion). A separate polling helper was not needed.
- A browser origin must be in both `valuex.realtime.allowed-origins` and `valuex.cors.allowed-origins`, because the CORS filter answers 403 first (found by the integration test).
- The slow-consumer close (4408) is covered by a unit test only; the load test is not run (G10, not a merge gate).
- `ChatIntegrationTest` now builds its listing through the new shared test fixture `LiveListingFixture` (the same code moved out, used by both integration tests).

Results: backend 2,690 tests green (18 in `RealtimeIntegrationTest` with real PostgreSQL and Redis), checkstyle clean, SonarQube quality gate on new code and coverage in the story summary; mobile 1,913 tests green apart from the two Google pixel-contrast tests that already failed, `dart format` clean, `dart analyze --fatal-infos` clean (the analyzer plugins could not reach pub.dev from this machine and said so; no diagnostics were reported), coverage of the new and changed mobile code about 96 percent.
