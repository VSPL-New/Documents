# US-130 - Realtime Gateway (WebSocket) and Live Chat: QA Testing Guide

**Sprint 4 · Communication & Negotiation**

Manual test cases for the live connection (US-130) and for chat becoming live on it (US-013 events). The gateway is
checked with `curl`, `wscat` and `redis-cli`; chat is checked on two phones (or one phone and `wscat` for the second
person).

> **What ships:** `POST /api/v1/realtime/tickets`, the WebSocket `GET /ws/v1?ticket=...`, Redis fan-out on the
> channel `rt:u:{userId}`, presence, the inbound frames `ping`, `app.state`, `chat.delivered`, `chat.read` and
> `chat.typing`, the events `chat.message.created`, `chat.message.delivered`, `chat.read`, `chat.typing` and
> `chat.thread.updated`; migration `V35` (settings only, no table); the nine `REALTIME_*` Admin settings. In the app:
> the live connection, the "Reconnecting…" strip, the typing line, and a Chats list, conversation and unread dot that
> no longer poll while the connection is open.
> **Not in this story:** push notifications (US-131), negotiation and call events (US-017, US-014), the Admin screen
> for the settings (US-116), the 10,000-session load test (script and targets are in LLD A.10; not run).

| Setting | Value |
|---|---|
| Backend base URL | `http://localhost:8080` (WebSocket `ws://localhost:8080/ws/v1`) |
| Properties | `valuex.realtime.enabled` (env `REALTIME_ENABLED`, default true), `valuex.realtime.allowed-origins` (env `REALTIME_ALLOWED_ORIGINS`, default empty) |
| Admin settings (`platform_settings`) | `REALTIME_MAX_SESSIONS_PER_USER` 3, `REALTIME_PING_INTERVAL_SECONDS` 25, `REALTIME_IDLE_TIMEOUT_SECONDS` 75, `REALTIME_TICKET_TTL_SECONDS` 30, `REALTIME_MAX_INBOUND_BYTES` 8192, `REALTIME_SEND_BUFFER_BYTES` 524288, `REALTIME_SEND_TIME_LIMIT_SECONDS` 5, `REALTIME_INBOUND_FRAMES_PER_SECOND` 20, `REALTIME_TICKET_REQUESTS_PER_MINUTE` 30 |
| Error codes | 503 `ERROR_REALTIME_UNAVAILABLE`; 403 `ERROR_ACCOUNT_NOT_ACTIVE`; 429 `RATE_LIMIT_EXCEEDED`; WebSocket events `error` with `ERROR_INVALID_FRAME` or `ERROR_FRAME_FAILED` |
| Close codes | 1001 going away or idle, 4401 token ended, 4403 account not active, 4408 slow consumer, 4409 session replaced, 4413 frame too large, 4429 too many frames |
| Known gaps | Hindi texts of the strip and the typing line need review; the settings change by SQL until US-116; a browser client also needs its origin in `valuex.cors.allowed-origins` |

---

## Prerequisites

1. Backend, PostgreSQL and Redis running (`docker compose up`); `REALTIME_ENABLED` not set to false.
2. Two `ACTIVE` accounts with tokens: `$ALICE` (seller) and `$BOB` (buyer); note `ALICE_ID` and `BOB_ID`. A live listing owned by Alice.
3. Tools: `curl`, `wscat` (`npm i -g wscat`), `redis-cli`.
4. Variables:

```bash
B="localhost:8080/api/v1"
HA="Authorization: Bearer $ALICE"
HB="Authorization: Bearer $BOB"
ticket() { curl -s -X POST -H "$1" $B/realtime/tickets | python -c "import sys,json;print(json.load(sys.stdin)['data']['ticket'])"; }
```

---

## A. Ticket and connection (AC1)

| # | Steps | Expected |
|---|---|---|
| A1 | `curl -s -X POST -H "$HA" $B/realtime/tickets` | 200 with `ticket` (43 characters), `expiresInSeconds` 30, `pingIntervalSeconds` 25 and `url` `ws://localhost:8080/ws/v1`. |
| A2 | Without a token | 401. |
| A3 | `wscat -c "ws://localhost:8080/ws/v1?ticket=$(ticket "$HA")"` | Connected; no frame arrives on its own. |
| A4 | Type `{"type":"ping"}` | An event `{"v":1,"type":"pong",...}` arrives. |
| A5 | Connect again with the same ticket (save it first) | Refused: HTTP 401. A made-up ticket and a ticket after 31 seconds: 401 as well. |
| A6 | `redis-cli KEYS 'rt:ticket:*'` right after a ticket is issued | One key, a hash (64 hex characters), not the ticket; it disappears within 30 seconds or when used. |
| A7 | Search the backend log for the ticket and for the access token | Neither appears; no frame text appears. |
| A8 | 31 ticket requests within a minute (`REALTIME_TICKET_REQUESTS_PER_MINUTE` is 30) | The 31st answers 429 `RATE_LIMIT_EXCEEDED`. |

## B. Refusals (AC2)

| # | Steps | Expected |
|---|---|---|
| B1 | Issue a ticket, then `UPDATE users SET status='SUSPENDED' WHERE id='<ALICE_ID>'`, then connect | HTTP 403. Restore the status. |
| B2 | Ticket request for a user in `OTP_PENDING` | 403 `ERROR_ACCOUNT_NOT_ACTIVE`. |
| B3 | `wscat -H "Origin: https://evil.example.com" -c ws://localhost:8080/ws/v1?ticket=...` | HTTP 403. With no Origin (the app) it connects. |
| B4 | Start the backend with `REALTIME_ENABLED=false` | The ticket call answers 503 `ERROR_REALTIME_UNAVAILABLE`; a handshake answers 503. Chat in the app still works (polling, see I9). Switch it back on. |

## C. Events reach the right person (AC3, AC8)

| # | Steps | Expected |
|---|---|---|
| C1 | Alice and Bob each connect with `wscat`. `redis-cli PUBLISH rt:u:<ALICE_ID> '{"v":1,"type":"badge.updated","id":"x1","ts":"2026-11-17T10:00:00Z","data":{"chatsUnread":2}}'` | Only Alice's socket receives it (this is what a second server instance does). |
| C2 | Publish the same text to `rt:u:<BOB_ID>` | Only Bob's socket receives it. There is no frame with which Bob can listen to Alice's channel. |
| C3 | Alice opens two sockets | A publish to Alice reaches both. |
| C4 | Stop Redis (`docker compose stop redis`) and send a chat message over REST | The REST call still answers 201; the sender's own open socket still receives the event; the log counts `realtime.publish.failures`. Start Redis again. |
| C5 | `GET /actuator/metrics/realtime.sessions.active`, `realtime.events.sent.total?tag=type:chat.read`, `realtime.connect.total?tag=outcome:accepted` | The metrics exist and move. |

## D. Limits and close codes (AC4, AC5)

| # | Steps | Expected |
|---|---|---|
| D1 | Alice connects four times | The first socket closes with 4409; the other three stay. |
| D2 | `UPDATE platform_settings SET setting_value='1' WHERE setting_key='REALTIME_MAX_SESSIONS_PER_USER'` and evict the cache (restart or wait 60 s) | A new connection closes the older one; sessions open before the change keep their old limit. Restore 3. |
| D3 | Send a text frame longer than 8192 bytes | The server closes with 4413. |
| D4 | Send 60 `{"type":"ping"}` frames in one second | The server closes with 4429. |
| D5 | A session for a ticket made with a token that expires in a minute (wait for the expiry) | The server closes with 4401 within about 10 seconds after the expiry. |
| D6 | With a socket open, move the account out of `ACTIVE` through the Admin account-state action (for example flag it for review) | The socket closes with 4403 on every server. |
| D7 | Stay silent for 76 seconds (no ping) | The server closes the session (1001, "Idle"). |
| D8 | Set `REALTIME_IDLE_TIMEOUT_SECONDS` to the same value as `REALTIME_PING_INTERVAL_SECONDS` | The backend logs a warning and uses 75 and 25. Restore the values. |
| D9 | Restart the backend with a socket open | The socket closes with 1001; the app reconnects (J3). |

## E. Frames and presence (AC6, AC7)

| # | Steps | Expected |
|---|---|---|
| E1 | `{"type":"nope"}` | Ignored; `realtime.events.received.total` with `type=unknown` grows; the socket stays open. |
| E2 | `not json` and `[1]` | An `error` event with `ERROR_INVALID_FRAME`; the socket stays open. |
| E3 | `{"type":"app.state","data":{"foreground":true}}`, then `redis-cli ZRANGE rt:presence:<ALICE_ID> 0 -1 WITHSCORES` | One member (the session id) with a score about 90 seconds ahead. |
| E4 | `{"type":"app.state","data":{"foreground":false}}` | The member is gone; the user counts as offline. |
| E5 | Wait 100 seconds with the foreground state and no ping | The member is dropped on the next read of presence. |

## F. Chat is live (AC10)

Alice (seller) and Bob (buyer) each have the app open on the same listing, or Alice uses `wscat`.

| # | Steps | Expected |
|---|---|---|
| F1 | Bob opens the chat and sends "Is the box included?" | Alice's open conversation (or her list) shows it within a second with no pull to refresh; Alice's `wscat` shows `chat.message.created` with `data.threadId` and `data.message` (`fromMe` false). |
| F2 | Bob's second phone (or a second socket for Bob) | It also receives the message, with `fromMe` true. |
| F3 | Alice reads it | Bob's message changes to Delivered, then Read (`chat.message.delivered`, `chat.read`); the unread dot on Alice's Chats tab clears within a second. |
| F4 | Alice types in the field | Bob sees "Alice K is typing…" for about 4 seconds; it stops when Alice empties the field, sends, or pauses 3 seconds; typing frames go at most once a second. |
| F5 | Alice sends a frame `{"type":"chat.typing","data":{"threadId":"<thread>","typing":true}}` as a third person (Eve's socket) | Eve gets an `error` event `ERROR_FRAME_FAILED`; nothing reaches Alice or Bob. |
| F6 | Alice blocks Bob while both screens are open | Both conversations turn read-only at once (`chat.thread.updated`, `canSend` false, `BLOCKED`); typing is not relayed; unblocking opens them again. |
| F7 | An Admin removes the listing | Both conversations become read-only (`LISTING_REMOVED`). |
| F8 | Send a 2000-character Hindi message | It is not pushed in full (over about 3 KB); the other phone shows it after a moment by re-reading (`chat.thread.updated` hint). |
| F9 | `chat.read` over the socket as Bob for a thread that is not his | An `error` event; no change. |
| F10 | Read the backend log | No message text, typed text or event payload. |

## G. The app and the connection (AC9)

| # | Steps | Expected |
|---|---|---|
| G1 | Sign in; open a conversation | The backend shows one session for the user; no 15-second polling requests appear in the log while connected. |
| G2 | Turn on airplane mode while a conversation is open | After a moment the "Reconnecting…" strip appears (announced by a screen reader); the app polls every 15 seconds; turn it off: the strip goes away, the thread is re-read from its last message and the missed message appears. |
| G3 | Kill the backend and start it again | The app reconnects within about 30 seconds, with growing pauses (1, 2, 4, 8, 16, 30 s); no duplicate messages. |
| G4 | Send the app to the background for 10 seconds and return | Same connection (no new ticket); the screens are re-read once. |
| G5 | Background for 40 seconds | The socket closes after 30 seconds; on return it reconnects and re-reads. |
| G6 | Open the app on a fourth phone with the same account | The oldest phone stops (4409) and reconnects when the user returns to the app, not before. |
| G7 | Suspend the account while the app is open | The socket closes with 4403 and the app shows the account screen; it does not keep reconnecting. |
| G8 | Switch the backend to `REALTIME_ENABLED=false` | The app shows the strip and polls; sending and reading still work. |
| G9 | The same at 320 px and 200 percent text, and in Hindi | The strip and the typing line do not overflow; Hindi texts show. |
| G10 | Sign out | The connection closes; no events arrive for the next user who signs in on the phone. |

---

## Automated tests

```bash
# backend (needs Docker for PostgreSQL and Redis containers; on Docker Engine 29 and a machine time zone Postgres rejects:)
$env:JAVA_TOOL_OPTIONS='-Dapi.version=1.44 -Duser.timezone=UTC'
mvn test -Dtest='com.valuex.realtime.**.*Test,ChatRealtimeListenerTest,ChatFrameHandlersTest'

# mobile
flutter test test/core/realtime test/core/widgets/realtime_reconnecting_banner_test.dart test/features/chat
```

The integration test `RealtimeIntegrationTest` opens real sockets against the running server, PostgreSQL and Redis
containers and covers the ticket, the refusals, delivery to the right user only, delivery from "another instance",
the close codes 4401, 4403, 4409, 4413 and 4429, presence, the Admin ticket limit, and live chat between two people.

## Setup notes for environments

- **Ingress and load balancer:** allow the WebSocket upgrade on `/ws/v1`, an idle timeout of at least 75 seconds, no
  sticky sessions, and `wss` over TLS 1.3. See `valuex-infra/docs/realtime.md`.
- **Redis:** the gateway needs Redis 6.2 or newer (`GETDEL`) and pub/sub. A Redis that blocks pub/sub makes events
  stay on the instance that published them.
- **Browsers (later):** an origin must be in both `valuex.realtime.allowed-origins` and `valuex.cors.allowed-origins`.
