# US-014 and US-015: In-App Voice Call and In-App Video Call (LiveKit, no recording or transcript in the MVP) - Implementation Plan

## 1. Header

| Item | Value |
|---|---|
| Stories | **US-014** In-App Voice Call and **US-015** In-App Video Call, planned and built together (product owner, 2026-11-22). **The MVP records and transcribes nothing** (decision D24, 2026-11-22): no consent step, no speech-to-text, no stored call text; a call keeps its call log only |
| Sprint | Sprint 4 - Communication & Negotiation (both stories were put on hold on 2026-11-15 until a call provider was chosen) |
| Story points | 8 + 8 = 16 (from Sprint-plan.md; **not re-estimated** although the transcript left US-015). Voice and video share one call model, so the split below is by layer, not by story |
| Repos | `valuex-backend`, `valuex-mobile`, `valuex-infra` (secrets, webhook route; Part 4, Infra) |
| Dependency | US-013 chat, US-069 contact guard, US-130 realtime, US-131 push, US-132 block and report: all built. **Call provider: LiveKit** (decision of 2026-11-22, closes open item O1 of the Sprint 4 LLD); the LiveKit account is created (product owner, 2026-11-22) |
| Not in this plan | US-016 (call-log retention job, Admin evidence endpoint, real `CommunicationHoldPort`); **call transcripts, consent and on-device speech-to-text (deferred, D24)**; US-109 app integrity; US-116 settings screen; a native incoming-call screen (CallKit, ConnectionService; decision D15) |
| Source documents | [Sprint 4 LLD](../LLD/Sprint-4-Communication-Negotiation-LLD.md) v0.13 Part F (US-014) and Part G (US-015, MVP part G.1 to G.2a); [user-stories.md](../user-stories.md) US-014, US-015; LiveKit documentation read on 2026-11-22 (Part 3) |

## 2. Story Recap

**US-014 (voice).** *As a* buyer *I want to* call the seller without revealing my number *so that* I can discuss details while keeping my privacy.
- Tap "Call" on a listing or in chat: an in-app call (app to app, over the internet) starts. No phone number of either person is used or shown.
- The call connects with clear voice, its duration is tracked, and when it ends a call log is stored with the duration.
- Edge cases: seller does not answer; call drops; poor network; microphone permission denied; call service unavailable.
- Rules: the call is not recorded or transcribed (the screens say so); call logs kept 6 months (the LLD makes this `CALL_LOG_RETENTION_DAYS`, 180, owned by US-016); at most 30 minutes per call.
- Errors: `ERROR_MICROPHONE_PERMISSION`, `ERROR_CALL_FAILED`, `ERROR_NO_ANSWER`.

**US-015 (video).** *As a* buyer *I want to* video call the seller to see the item *so that* I can check its condition before buying.
- Tap "Video Call": the app asks for camera and microphone permission if needed; the seller is asked to join; when the seller accepts the video call connects; at the end a call log is stored with the duration. Nothing of the call is recorded or transcribed.
- Edge cases: camera or microphone permission denied; seller rejects; poor network causes lag.
- Rules: the user can report abuse during a call; at most 30 minutes; no audio, video or text of the call is stored.
- Errors: `ERROR_CAMERA_PERMISSION`, `ERROR_SELLER_DECLINED`, `WARNING_LOW_BANDWIDTH`.
- **Deferred beyond the MVP (user-stories.md US-015):** the consent notice, the on-device transcript, its storage and deletion, `ERROR_TRANSCRIPT_FAILED`, the copy-of-transcript edge case.

## 3. Design Reference

### 3.1 What the LLD already settles (not repeated here)

[Part F](../LLD/Sprint-4-Communication-Negotiation-LLD.md) (call lifecycle, `call_sessions` without consent or transcript columns, `call_events`, state machine, API, watchdog, heartbeat in Redis, mobile screens, error codes) and the MVP part of [Part G](../LLD/Sprint-4-Communication-Negotiation-LLD.md) (G.1 to G.2a: what video adds to voice) are built as written, except where section 3.3 says otherwise. The Sprint 4 LLD was updated to v0.13 on 2026-11-22 for decisions D24 (no recording or transcript in the MVP) and the LiveKit choice; G.3 to G.11 remain only as the deferred transcript design. The LLD already isolates the provider behind `RtcProviderPort` (backend) and `RtcClient` (mobile). This plan adds the LiveKit adapter for both and the changes LiveKit makes to the design.

### 3.2 What the LiveKit documentation says (and where it is not enough)

Read on 2026-11-22: docs.livekit.io (tokens and grants, room and participant management, webhooks, Flutter quickstart, Flutter audio guide, server API, regions, quotas, billing, firewall, self-hosting), livekit.com/pricing, the `livekit_client` and `livekit_ffi` entries on pub.dev, and the LiveKit Kotlin/Java server SDK source on GitHub. Local copies are in the session folder `files/livekit/`.

| # | Topic | What LiveKit says | Effect on the design |
|---|---|---|---|
| L1 | Concepts | A **room** holds **participants** who publish audio, video or data **tracks**. A room is created by the server API or automatically when the first participant joins, and closes shortly after the last one leaves. Clients connect to the SFU with an **access token**. | One call = one room, named by `rtc_channel` (`c_` plus 32 random hex, as in LLD F.3). |
| L2 | Access token | A JWT signed with the **API secret** (HS256): `iss` = API key, `sub` = participant identity, `exp`, `nbf`, optional `name`, `metadata`, `attributes`, and a `video` grant (`roomJoin`, `room`, `canPublish`, `canSubscribe`, `canPublishData`, `canPublishSources`, `roomAdmin`, `roomRecord`, ...). **Omitted permissions are granted** (an unset `canPublishData` follows `canPublish`). Default lifetime 6 hours. Expiry only affects the first connect; LiveKit refreshes a connected client's token itself (10 minutes or the rest of the original lifetime, whichever is longer). | The backend builds tokens itself. Every grant is set explicitly. Lifetime = call limit + grace (LLD F.9). |
| L3 | No PII | "Participant identity and room name are recorded in logs and traces throughout LiveKit ... Don't put real names, phone numbers or email addresses in these fields. Use an opaque identifier." | Room name is already random. Identity is the **role**, `caller` or `callee`, and `name` is not set. The app shows the display name from our own API. This replaces the integer `uid` 1 and 2 of LLD F.4 (LiveKit identities are strings). |
| L4 | Room settings | `RoomConfiguration` can ride inside the token and applies only when the room is first created: `empty_timeout` (default 300 s), `departure_timeout` (default 20 s), `max_participants`. | Token carries `maxParticipants` 2, `emptyTimeout` = `CALL_JOIN_SECONDS` plus a small grace, and a short `departureTimeout`. No separate CreateRoom call. |
| L5 | Ending a call | `DeleteRoom` disconnects everyone (client reason `ROOM_DELETED`). `RemoveParticipant` disconnects one person (`PARTICIPANT_REMOVED`) and, **on LiveKit Cloud only**, revokes that token; pass `revoke_token_ts` (within 60 s of now) to make the revocation strict. A token can otherwise re-create a deleted room until it expires. Self-hosted servers do not revoke tokens. | On every end (hang up, timeout, limit, drop, block, error) the server calls `DeleteRoom`, then `RemoveParticipant` with `revoke_token_ts` for both identities (best effort, retried by the watchdog). Token lifetime is the call limit, so a stale token is useless soon after. |
| L6 | Server API | Twirp over HTTPS: `POST {host}/twirp/livekit.RoomService/<Method>` with a JSON body and `Authorization: Bearer <JWT with the matching grant>` (`roomAdmin` for remove and delete, `roomList` for list). Keys may be `snake_case` or `camelCase`. | Three calls are needed: `DeleteRoom`, `RemoveParticipant`, `ListParticipants` (reconciliation). Plain `RestClient` calls are enough. |
| L7 | Webhooks | HTTP POST, `Content-Type: application/webhook+json`, body = one event (`id`, `createdAt`, `event`, `room`, `participant`). The `Authorization` header holds a JWT signed with the API secret whose `sha256` claim is the base64 SHA-256 of the **raw body** (confirmed in the Kotlin SDK `WebhookReceiver`: issuer check, `exp` required, 60 s leeway). Events used: `participant_joined` (media connection is up), `participant_left`, `participant_connection_aborted`, `room_started`, `room_finished`. **No delivery guarantee**; several retries; events are sent in order. Configured in the Cloud dashboard (name, URL, signing key). | Matches LLD F.5 (`RtcWebhookController`: signature, stale time, de-duplication by event id). Webhooks refine join and leave times; they never decide the call alone (they can be lost). The heartbeat and watchdog stay. |
| L8 | Connection quality and reliability | The client SDKs report connection quality per participant; LiveKit tries ICE/UDP, then TURN/UDP 3478, TURN/TLS 443 and ICE/TCP 7881, and resumes or fully reconnects after a drop (`Reconnecting` event). Disconnect reasons include `DUPLICATE_IDENTITY`, `ROOM_DELETED`, `PARTICIPANT_REMOVED`, `JOIN_FAILURE`, `ROOM_CLOSED`. | Feeds the network chip and `WARNING_LOW_BANDWIDTH`. A second join with the same identity kicks the first (`DUPLICATE_IDENTITY`), which is what LLD F.5 wants for "joining twice returns fresh credentials". |
| L9 | Flutter SDK | `livekit_client` **2.14.0** (2026-11-19): `Room`, `connect(url, token, roomOptions)`, `localParticipant.setMicrophoneEnabled/setCameraEnabled`, `VideoTrackRenderer`, `EventsListener<RoomEvent>`. Needs **Dart >= 3.10 and Flutter >= 3.38** (2.11.0 and older: Flutter >= 3.27). Depends on `livekit_ffi` ^0.15.0, "a prebuilt native library via Native Assets". The SDK owns the platform audio session (`AudioManager`, automatic `communication` mode, echo cancellation, noise suppression and gain on by default; speaker routing with `setSpeakerOutputPreferred`). iOS needs `NSCameraUsageDescription`, `NSMicrophoneUsageDescription` and the `audio` background mode; Android needs camera, record-audio, modify-audio-settings, network-state and Bluetooth permissions. | The project's Flutter 3.47.5 (CI and local) satisfies it, but `pubspec.yaml` declares `flutter >=3.22.0` and `sdk >=3.4.0`: both must be raised. Native Assets must be proven in CI (spike S1). |
| L10 | Cost and limits (livekit.com/pricing, quotas page) | **Build** $0: 5,000 WebRTC minutes, 50 GB, **100 concurrent connections**, a hard cap (nothing is billed past it; new connections fail). **Ship** $50/month: 150,000 minutes then $0.0005 per minute, 250 GB then $0.12 per GB, 1,000 connections. **Scale** $500/month: 1.5 M minutes then $0.0004, 3 TB, 5,000 connections, **region pinning**. WebRTC minutes are "time an end user spends connected", min 10 s per session. | Assuming two participants per call: Build covers about 250 ten-minute calls a month and 50 calls at once; Ship about 7,500 ten-minute calls. Fine for development and a pilot; production needs Ship (G1). |
| L11 | Regions and residency | Cloud has an `india` region group (one location, so no in-region redundancy). Pinning a project to a region is a Scale feature; other plans use the global edge network (each user connects to the nearest edge). | **No region pinning (product owner, 2026-11-22).** Recorded as a risk in the privacy review (G8). |
| L12 | Recording and media access | Recording exists only through **Egress** (needs `roomRecord` or the egress API) and is never used. The SFU forwards media (DTLS-SRTP to the SFU); LiveKit also offers optional end-to-end encryption. | Tokens never carry `roomRecord`; nothing calls the Egress API; webhook `egress_*` events are ignored. This is what "no recording" means in the build (D24). Whether to add E2EE is still open (G8). |
| L13 | Local development | `livekit-server --dev` runs a local server with key `devkey` and secret `secret` on port 7880 (bind `0.0.0.0` to reach it from a phone); self-hosted webhooks are set in the config file. | Developers and optional integration tests need no Cloud account (the `mock` provider still covers CI). |

### 3.3 Design decisions specific to LiveKit (proposed; each is open to your review)

1. **No LiveKit server SDK in the backend (recommended).** `io.livekit:livekit-server` 0.17.1 exists for Java and Kotlin, but it brings Kotlin stdlib 2.3.0, Retrofit 3.0.0, `protobuf-java` 4.29.4 and Jackson 2.22.2. The backend is on Spring Boot 3.2.5, which manages Jackson 2.15.4 and Kotlin 1.9.x; `firebase-admin` already supplies `protobuf-java` 4.33.6. The only things needed are a signed token, three JSON calls and one signature check, all easy with the `jjwt` 0.12.5 and `RestClient` the backend already has. Cost: we own about 150 lines of code and cross-check them against the official SDK once (spike S2). Fallback if the spike shows a problem: adopt the SDK and force compatible versions.
2. **Adapter shape.** `RtcProviderPort` gains `createCredentials(call, role)` (token + URL), `endCall(call)` (delete room, remove participants) and `listParticipants(call)`; `valuex.rtc.provider` = `livekit` or `mock` (default `mock`, so CI and development need no account). The join response keeps the neutral shape of LLD F.4, with `provider: "livekit"`, `channel`, `identity`, `credentials: { url, token }`, `expiresAt`, `media`.
3. **Grants per role.** Voice: `roomJoin`, `room`, `canSubscribe` true, `canPublish` true, `canPublishSources` [`microphone`], `canPublishData` false. Video adds `camera`. Never `roomAdmin`, `roomRecord`, `roomCreate`, `hidden`. The server API key used for admin calls is the same key but a separate short-lived admin token (`roomAdmin` for one room, 60 s).
4. **Token lifetime** = `max_ends_at + valuex.rtc.token-grace` minus now (LLD F.5). Refreshed tokens last at least 10 minutes, so the call limit is enforced by the server ending the room, not by token expiry alone.
5. **Webhooks refine, heartbeat decides.** `participant_joined` sets `caller_joined_at` or `callee_joined_at` (and wins over the client's `connected` when they differ by more than 5 s, LLD F.5); `participant_left` and `participant_connection_aborted` are written as `LEFT` events. Ending a call on `participant_left` is **not** done: LiveKit reconnects clients, so a short drop would end calls that would have recovered. The 45 s heartbeat rule of LLD F.5 stays (G3, G9).
6. **Client SDK behind our own interface.** `RtcClient` (LLD F.7) is implemented by `LiveKitRtcClient` over a thin `LiveKitRoomGateway` that wraps `Room`, so controllers and tests never import `livekit_client`. `adaptiveStream` and `dynacast` stay on (the SDK's own advice); the camera is capped at 720p and 24 frames per second, kept as settings (agreed by the product owner, 2026-11-22).
7. **Audio session ownership.** LiveKit's automatic `communication` session is used as is. Nothing else listens to the microphone: there is no speech recogniser (D24), which also removes the microphone-sharing risk that the transcript design carried.
8. **Nothing is recorded or transcribed (D24).** No recording, no server-side or on-device speech recognition, no stored text of a call, no consent step. The ringing and in-call screens show one information line, "This call is not recorded", with no tick box (G15).

## 4. Implementation Steps

### Phase 0 - Prerequisites and spikes (before any production code; results are written into section 7)

- [ ] **S0 Account and keys.** The LiveKit Cloud account is created (product owner, 2026-11-22). Still needed: a project for development (Build plan is enough), its URL, API key and API secret, put into the secret manager and `scripts\dev-real.env` by you (never pasted into chat or the repository), and the webhook created in the dashboard once the "Webhook route" step below exists.
- [ ] **S1 Flutter SDK spike (half a day, two phones).** Add `livekit_client` 2.14.0 on a throw-away branch; raise the `pubspec.yaml` constraints; build debug and release APKs locally and in `mobile-ci.yml` (Native Assets, `livekit_ffi`); join one room from two phones with a hand-made token; check audio route, speaker, Bluetooth headset, background audio and Android 14 foreground-service rules; iOS build if a Mac is available (G12). Go/no-go: build size, CI time, minimum Android and iOS versions.
- [ ] **S2 Token and webhook cross-check.** Produce a token with our code and with the official CLI or Kotlin SDK (same inputs) and join with both; sign a sample webhook body with the official receiver and verify it with ours. This proves decision 3.3.1 or sends us to the SDK.
- [ ] **S3 Timing measurements.** With airplane mode and with Wi-Fi to mobile data switches, record how long `participant_left` takes to reach the webhook and how long a client takes to reconnect; this fixes the heartbeat and ring/join values (they are settings, so no release is needed to change them).
- The transcription spike of the earlier draft is **cancelled** with the transcript (D24).

### Infra (`valuex-infra`)

- [ ] Secret entries `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` for each environment (the API secret is also the webhook signing key).
- [ ] A public HTTPS route to `POST /api/v1/webhooks/rtc` (LiveKit Cloud calls it from the internet); outbound HTTPS from the backend to the LiveKit URL; no inbound media port is needed on our side. Development uses a tunnel or the local LiveKit server (L13).
- [ ] Document the client firewall facts (L8: `*.livekit.cloud` 443, TURN/TLS 443, UDP 50000-60000, TCP 7881) for the support runbook.

### Database

- [ ] `V43__call_sessions.sql` (the next free number on `main`; V42 is the latest; confirm at branch time, G13) exactly as LLD F.3: `call_sessions` and `call_events` with their indexes and the state and end checks. **No consent or transcript columns and no `call_transcript_segments` (D24).** `rtc_channel` stays `VARCHAR(64)`; no column holds a LiveKit identity (it is derived from the role).
- [ ] Seed the `CALL_*` settings of the LLD table (`CALL_ATTEMPTS_PER_PAIR_PER_HOUR` 3, `CALL_RING_SECONDS` 45, `CALL_MAX_MINUTES` 30, `CALL_JOIN_SECONDS` 30, `CALL_LOG_RETENTION_DAYS` 180, plus the heartbeat limits and the camera caps) and register them in `plans.domain.CommunicationSetting` the way the chat settings are. **No transcript settings** (`CALL_TRANSCRIPT_RETENTION_DAYS` and the `valuex.transcription.*` keys are not seeded).

### Backend (`com.valuex.communication`, `valuex.rtc.*` properties)

Configuration and provider
- [ ] `ValuexProperties`: `Rtc` (`provider`, `livekit.url`, `livekit.api-key`, `livekit.api-secret`, `token-grace`, `webhook-leeway`); `valuex.calls.enabled` stays the master switch (already read by `ContactEligibilityService`).
- [ ] `application/port/RtcProviderPort` (extended as in 3.3.2) and `RtcCredentials`.
- [ ] `infrastructure/rtc/MockRtcAdapter` (fixed values, records `endCall`), `LiveKitTokenFactory` (jjwt HS256, claims of L2, explicit grants, `roomConfig`), `LiveKitApiClient` (`RestClient`, Twirp JSON, admin token per call, timeouts, one retry, errors mapped to `ERROR_CALL_FAILED`), `LiveKitRtcAdapter`, `LiveKitWebhookVerifier` (JWT signature and `exp`, `sha256` of the raw body, constant-time compare, leeway).
- [ ] The API secret and tokens are never logged; metrics `rtc.token.issued{type}`, `rtc.api.call{method,outcome}`, `rtc.webhook.received{event}`, `rtc.webhook.rejected`.

Call lifecycle (LLD F.3 to F.5)
- [ ] `domain/CallState`, `CallEndReason`, `CallType`, `CallStateMachine extends StateMachine<CallState>`, `CallStateChangedEvent`.
- [ ] `infrastructure/persistence/` rows and repositories for the two tables (`FOR UPDATE` loads, `FOR UPDATE SKIP LOCKED` batches for the watchdog).
- [ ] `application/service/CallService`: create (guard, `valuex.calls.enabled`, advisory lock on the two user ids, busy and in-progress checks, reachability D.5, find or create thread, insert `RINGING`, event, after commit `call.incoming` over the socket and the high-priority push), accept, decline, cancel, join (credentials), connected, heartbeat (Redis `call:hb:{callId}:{userId}`), end (idempotent, `CALL_SUMMARY` message, `RtcProviderPort.endCall`), history.
- [ ] `CallWatchdogJob` (ringing timeout, join timeout, heartbeat drop, max duration, retry of `endCall` for calls ended but not cleaned up) and `CallRoomReconcileJob` (optional, uses `listParticipants` for `ACTIVE` calls older than a few minutes; off by default).
- [ ] `application/service/CallBlockListener` (on `UserBlockedEvent` ends the pair's live call with `BLOCKED`).
- [ ] `ContactEligibilityService`: `call` and `video` become `available` per caller (reasons as LLD D.5) when `valuex.calls.enabled`; the `COMING_SOON` path stays when it is off. `ContactChannel.CALL` and `VIDEO` and `ContactGuard` are already there; add the call-specific limit and reachability.
- [ ] Missed call: `CALL_MISSED` notification and chat summary; copy in `CommunicationNotificationCopy` (English and Hindi, display name only).
- [ ] **Push, high priority:** `PushRequest` has no priority or time-to-live field; add them (`CALL_INCOMING` and `VIDEO_CALL_REQUEST` use high priority and a short TTL equal to the ringing window), keeping the existing rules in `PushPolicy` and `PushCopy`. Add the push-only dispatch mode that LLD B.11 row 6 left unbuilt.
- [ ] Controllers: `CallController` (all endpoints of LLD F.4; `POST /calls/video` takes `{listingId, threadId?}`), `RtcWebhookController` (public path added to `SecurityConfig`; 401 on a bad signature; de-duplication by event id in Redis; unknown events acknowledged), the 503 `ERROR_CALLS_UNAVAILABLE` while calls are off. There is no consent-notice endpoint and no transcript endpoint (D24).

Reporting a call
- [ ] `CallReportTargetResolver` so `POST /reports` with `targetType: CALL` works (`ReportTargetType.CALL` exists, no resolver yet), and a call-aware part of `CommunicationHoldPort.holdForReport` that sets `flagged` and `legal_hold` on the call (the chat part stays with US-016, G10).
- [ ] Not built here, handed to US-016: the call-log retention job (`purge_after`), the Admin evidence endpoint for calls.

### Mobile (`valuex-mobile`, `features/calls/`)

- [ ] `pubspec.yaml`: `livekit_client: ^2.14.0`, `sdk: '>=3.10.0 <4.0.0'`, `flutter: '>=3.38.0'`; confirm `permission_handler` ^11.3.1 is enough for camera and microphone (it is already used).
- [ ] Android manifest: camera, `ACCESS_NETWORK_STATE`, `CHANGE_NETWORK_STATE`, `MODIFY_AUDIO_SETTINGS`, Bluetooth (`BLUETOOTH_CONNECT`, and the older ones with `maxSdkVersion` 30), foreground-service permissions of types `microphone` and `camera`, plus the foreground service declaration (the package that provides the ongoing-call service is chosen in S1, G5). `RECORD_AUDIO` and `POST_NOTIFICATIONS` are already declared. iOS `Info.plist`: camera and microphone usage texts (English and Hindi) and `UIBackgroundModes` `audio`. No speech-recognition permission (D24).
- [ ] `domain/` (`Call`, `CallState`, `CallEndReason`, `RtcCredentials`), `data/call_repository.dart` (every endpoint of LLD F.4), `data/rtc/rtc_client.dart` (interface), `data/rtc/livekit_rtc_client.dart`, `data/rtc/livekit_room_gateway.dart`, `data/rtc/fake_rtc_client.dart`.
- [ ] `presentation/`: `call_controller.dart` (Riverpod: `idle`, `requesting`, `outgoingRinging`, `incomingRinging`, `joining`, `active`, `ended`), `incoming_call_screen.dart`, `in_call_screen.dart` (voice and video, picture-in-picture, mute, camera, flip, speaker, end, report, network chip, two-minute warning, the "This call is not recorded" line), `call_ended_sheet.dart`, `call_overlay_listener.dart` (global, listens to `call.incoming`), route `/call/:callId`. No consent sheet.
- [ ] Wire the Call and Video buttons in `listing_actions.dart` and the chat screen (today `onUnbuilt` and `COMING_SOON`), the call list per thread, and the `CALL_SUMMARY` and missed-call system cards in chat.
- [ ] Heartbeat every 15 s over the socket with REST fallback; map LiveKit disconnect reasons and connection quality to our end reasons and chips; end the call locally only after telling the server.
- [ ] English and Hindi ARB strings; all targets 48 dp with semantic labels; 320 px and 200 percent text.

### Docs (with the code)

- [ ] LLD Sprint 4: **already updated to v0.13 on 2026-11-22** for D24 and LiveKit (change log, D24, O1 closed, F.3 to F.8, Part G, Part H, Part N). At build time add the "As built" notes (new F.11 and G.12) for anything that differs.
- [ ] `Sprint-plan.md` and `user-stories.md` built notes for US-014, US-015 and the call-log part of US-016.
- [ ] `Manual Testing Guides/US-014-US-015-Testing-Guide.md` (two phones, different networks).
- [ ] Update the `valuex-infra` notes and the local-dev scripts (`scripts/`) for the new settings and the local LiveKit server.

## 5. Test Plan (target above 90 percent on new and changed code)

**Backend unit**
- `CallStateMachine`: every allowed transition and a sample of forbidden ones (AC: end states, `ERROR_CALL_NOT_ACTIVE`).
- `LiveKitTokenFactory`: decode with the same secret and check `iss`, `sub` (`caller` or `callee`), `exp` equals the call limit plus grace, `nbf`, no `name`, the `video` grant per call type (voice cannot publish `camera`; `canPublishData` false; no admin or record grants), `roomConfig`.
- `LiveKitWebhookVerifier`: valid body; body changed by one byte; wrong secret; expired `exp`; missing `sha256`; header with a `Bearer ` prefix (rejected); replay of the same event id.
- `LiveKitApiClient` (HTTP stub): the exact path and JSON of `DeleteRoom`, `RemoveParticipant` (with `revoke_token_ts`) and `ListParticipants`; admin token grant; timeout and 5xx mapped to a retryable error; a 404 on a room that is already gone is success.
- `CallService`: busy callee, caller already in a call, two simultaneous requests create one call, reachability, own listing, blocked, rate limit, accept after timeout, idempotent end, duration maths (never connected, dropped, completed, limit), end always calls `endCall`.
- `CallWatchdogJob`: ringing, join, heartbeat and limit cases with a fake clock; two instances do not double process; `endCall` retried after a failure.
- `ContactEligibilityService`: `call` and `video` for every reason with calls on, and `COMING_SOON` with calls off.
- **No recording or transcript (D24):** an architecture-style test that nothing in the `communication` module references the LiveKit Egress API, a `roomRecord` grant or a transcript class; the migration test that `call_sessions` has no consent or transcript column.

**Backend integration (PostgreSQL, Redis, `MockRtcAdapter`, fake clock)**: happy path voice and video; no answer; decline; cancel; join timeout; drop by missed heartbeat (`ended_at` equals the older last heartbeat); limit reached; block ends the call; participant isolation (404); webhook with and without a valid signature on the public path; call report sets the hold; `valuex.calls.enabled=false` answers 503.
**Opt-in (not in CI):** one test against a local `livekit-server --dev` that joins two clients with our tokens, ends the room and sees both disconnected. Run before each release and when the adapter changes.

**Mobile**: `CallController` states with `FakeRtcClient` and a fake realtime stream (permission refused, ring timeout, cancel, accept, hang up, drop, two-minute warning, incoming call from another screen); the "This call is not recorded" line on the ringing and in-call screens; `LiveKitRtcClient` mapping of disconnect reasons and connection quality through the gateway fake; camera permission refused and "Turn off video"; repository calls; routes and guards; Hindi, 320 px and 200 percent text; semantic labels.
**Manual (two real phones, different networks):** audio and video quality, speaker, Bluetooth, Wi-Fi to mobile data, screen off, app killed on the callee (push), 30-minute limit, deny each permission, block during a call, report during a call. Checklist in the testing guide.

## 6. Validation Checklist

**US-014 acceptance criteria**
- [ ] Tapping Call starts an in-app call; no phone number of either person appears in any response, push, log, token, room name or identity.
- [ ] The callee rings; accept connects; voice is clear; duration is tracked from the server `connected_at`; a call log (`call_sessions` and `call_events`) is stored with the duration when it ends.
- [ ] Seller does not answer: `NO_ANSWER` after 45 s, `ERROR_NO_ANSWER`, missed-call notification and chat summary.
- [ ] Call drops: ended as `DROPPED` after 45 s without a heartbeat, duration kept to the last heartbeat.
- [ ] Poor network: quality chip shown, call not ended for quality alone.
- [ ] Microphone denied: `ERROR_MICROPHONE_PERMISSION` before any request, with an Open settings action.
- [ ] Service unavailable: `ERROR_CALL_FAILED` (token, join or API failure) and `JOIN_FAILED`.
- [ ] Not recorded or transcribed (the screens say so); 30-minute limit enforced by the server (room deleted, token short-lived); logs kept by the retention rule (US-016).

**US-015 acceptance criteria**
- [ ] Video Call asks for camera and microphone permission if needed, prompts the seller, and the call connects when the seller accepts; the call log is stored with the duration.
- [ ] Camera or microphone denied: `ERROR_CAMERA_PERMISSION`. Seller declines: `ERROR_SELLER_DECLINED`. Poor bandwidth: `WARNING_LOW_BANDWIDTH` with "Turn off video".
- [ ] No audio, video or text of the call is stored anywhere: no Egress call, no `roomRecord` grant, no `egress_*` webhook handling, no media, consent or transcript column or table.
- [ ] Report during a call sets `flagged` and `legal_hold` on the call; call-log deletion after the retention period is delivered by US-016 (hand-off recorded).
- [ ] The deferred transcript items (consent notice, on-device speech-to-text, `ERROR_TRANSCRIPT_FAILED`, copy of transcript) are **not** built, and the recorded hand-off to a later story exists in user-stories.md.

**Edge cases and rules from the LLD**
- [ ] Busy callee, caller already in a call, both call each other, caller cancels while ringing, callee app closed (push), block during the call, call longer than 30 minutes (warning at two minutes, then end).
- [ ] Joining twice returns fresh credentials and the first connection is dropped (`DUPLICATE_IDENTITY`).
- [ ] A third person cannot join (`maxParticipants` 2 and no token).
- [ ] After a call ends, its room is deleted and both tokens are unusable (Cloud revocation, short lifetime).
- [ ] Webhooks with a bad signature or stale time are rejected and counted; a lost webhook changes nothing that the heartbeat and watchdog cannot fix.
- [ ] `valuex.calls.enabled=false`: buttons stay `COMING_SOON`, endpoints answer 503, nothing calls LiveKit.
- [ ] Hindi and English texts, 48 dp targets, 320 px and 200 percent text, semantic labels, no secret in logs, Checkstyle, Sonar and coverage above 90 percent, `dart format` and `flutter analyze` clean.

## 7. Open Gaps / Questions

### 7.1 Decisions already made (product owner, 2026-11-22)

| # | Decision | Effect |
|---|---|---|
| G1 | LiveKit account created. | Still needed from you: a project, its URL, API key and secret in the secret manager (S0), and which plan (Build for development; Ship before real users, L10). |
| G8 (part) | **No region pinning.** | Global edge network on Build and Ship; recorded as a risk for the legal review (O7). End-to-end encryption was not decided: see G8 below. |
| G10, G4, G14 | **No recording and no transcription in the MVP** (D24). | The transcript, consent step, speech-to-text, microphone-sharing spike, transcript retention and consent-text review are all out of this plan and deferred in the LLD, user stories, Sprint plan, PRD and HLD. |
| G11 | Video quality: 720p at 24 frames per second, kept as settings. | Agreed. |
| G7 | Public webhook route and the `valuex-infra` change are part of this story. | Agreed. |
| S2 (old) | The transcription spike is cancelled. | The Flutter SDK spike S1 stays. |
| G15 | Keep one "This call is not recorded" line on the ringing and in-call screens (no tick box, nothing stored). | Agreed (2026-11-22, recommendation accepted). |
| G16 | Keep 16 SP for now; re-estimate after spike S1. | Agreed. |
| G8 (E2EE) | No end-to-end encryption for the MVP; recorded as a risk for the legal review (O7, DPDP Act 2023). | Agreed. |
| G9 | A call ends on the heartbeat rule only, not when LiveKit reports the person left (decision 3.3.5). | Agreed. |
| G2 | Direct token, webhook and HTTP code with no LiveKit server SDK (decision 3.3.1), proven by spike S2. | Agreed. |
| G10 | Call-log retention job, Admin evidence endpoint for calls and the real `CommunicationHoldPort` stay with US-016, planned next. Until then no call log is deleted. | Agreed. |
| G6 | Ringing with the app closed is a high-priority heads-up push; no CallKit, ConnectionService or lock-screen screen in this story (D15). | Agreed. |

### 7.2 Not found in the LiveKit documentation (you asked me to say)

| # | What I could not find | Why it matters | Proposed way forward |
|---|---|---|---|
| G3 | **How long LiveKit takes to notice a dropped participant** (server ping or timeout values) and the exact retry count of webhooks. The docs describe resume and full reconnect but give no times for LiveKit Cloud. | Sets the 45 s drop rule and whether `participant_left` can ever end a call. | Keep our own 15 s heartbeat and 45 s rule (works whatever LiveKit does); measure in spike S3 and revisit. |
| G5 | **How to keep a call alive in the background on Android** (foreground service for microphone and camera). The Flutter docs show a foreground service only for screen share. | Android 14 stops a call when the app is backgrounded without one; LLD F.7 requires it. | Choose the plugin in S1 (for example a foreground-task package) and test on Android 13 and 14. |
| G6 | **Incoming-call behaviour with the app closed or the screen locked.** LiveKit has no push or ringing of its own; its docs do not cover CallKit or Android ConnectionService. | The callee must be rung by our push (US-131). | Decided (7.1): high-priority heads-up push, no CallKit or lock-screen UI in this story (D15). |
| G12 | **Minimum Android and iOS versions** of `livekit_client` 2.14.0 and whether `livekit_ffi` Native Assets build in our CI. The docs say Flutter >= 3.38 and Dart >= 3.10 only. | Could exclude older phones or break the build. | Spike S1 (also needs a Mac or an iOS device to prove iOS; do we have one?). |
| (closed) | Access to the local microphone audio frames in the Flutter SDK is not documented. | It was the fallback of the transcript design only. | No longer needed (D24). It matters again only if a transcript story is ever planned. |

### 7.3 Still open

| # | Item | Plan |
|---|---|---|
| G13 | **Migration number** `V43` is the next free one today; another open pull request may take it. | Confirm at branch time. |
| G12 | Minimum Android and iOS versions and the CI build of `livekit_client` (7.2). | Answered by spike S1; iOS proof needs a Mac or an iOS device (do we have one?). |
| G5, G3 | Android background service package and drop-detection timing (7.2). | Answered by spikes S1 and S3. |

### 7.4 Changes this plan makes to the LLD

Already written into the Sprint 4 LLD v0.13 on 2026-11-22: D24, O1 closed, no consent or transcript columns or endpoints, `V43`, LiveKit adapter and webhook rules, "This call is not recorded" line. To be added at build time as "As built": `identity` values `caller` and `callee` instead of `uid` 1 and 2 (already in F.4), tokens carrying `roomConfig`, the room deleted and tokens revoked at every end, `PushRequest` gaining a priority and a time-to-live, and the results of spikes S1 to S3.

## 8. As built (2026-11-22)

The deviations from this plan, each recorded in the LLD section F.11:

| # | Plan said | Built | Reason |
|---|---|---|---|
| 1 | `ERROR_CALL_FAILED` 502 | 503 | The existing exception types make an unreachable provider a 503. |
| 2 | Create takes `listingId` and `threadId` | `listingId` only | The server finds or opens the buyer's thread; one source of truth. |
| 3 | `DeleteRoom` with `roomAdmin` | The `roomCreate` grant (`deleteRoomToken`) | Found in spike S2: `roomAdmin` answers 401. `RemoveParticipant` uses `roomAdmin` plus `room` and `revoke_token_ts`. |
| 4 | Heartbeat over the socket with REST fallback | REST only, every 15 seconds, stored in Redis | The socket has no frame for it and the REST call is cheap; Redis keeps the database free of per-beat writes. |
| 5 | `CallRoomReconcileJob`, `listParticipants` | Not built | Nothing used them; the room close is retried by the watchdog. |
| 6 | `PushRequest` gains a time-to-live | The FCM adapter applies 60 seconds to every high-priority push | A ringing call is the only high-priority push; no new field needed. |
| 7 | Camera limits "from settings" | Sent in the join answer and applied when the camera turns on | Resolved the open question of section 7.2. |
| 8 | A foreground-service package chosen in S1 | A small native service and keep-screen-on flag in `MainActivity`, no new plugin | A plugin risked the Built-in Kotlin build of the app; about 80 lines of Kotlin do the job. iOS keep-awake is not done (no Mac to test). |
| 9 | SDK constraint of the app raised | Not raised: `flutter_secure_storage` 9 to 11.2 was enough | A higher Dart floor would have changed the formatter style of the whole repository. |

**Spike results.** S1: the app builds for Android arm64 with `livekit_client` 2.14 (about 85 seconds, debug); on this machine Dart's TLS fails, so the native library of the build hook was placed locally (CI downloads it). `device_info_plus` 12 breaks the app's Built-in Kotlin setup; 13 needs `win32` 6, which `flutter_secure_storage` 11.2 allows. S2: our hand-written HS256 tokens work against the real project; the grants above. S3 (how quickly LiveKit notices a dropped person) was not measured: the drop rule uses the heartbeat only, so it does not matter for correctness.

**Tests.** Backend: 117 new unit tests (state machine, service, ender, watchdog, listeners, room closer, webhook service, assembler, heartbeats, LiveKit token, verifier, adapter, configuration, FCM time-to-live), 19 integration tests on PostgreSQL, and a live LiveKit smoke test that only runs when the three `LIVEKIT_*` variables are set. Mobile: about 200 new tests (domain, repository, RTC mapping, controller with fake time, screens at 320 px and 200 percent text, Hindi, launcher, incoming listener, deep link, route guard, chat cards). Results of the quality gates are in the pull request description.

**Hand-offs closed.** The Call and Video buttons (listing page and conversation header) are live; the "Calls are coming soon" message and its string are removed; the `CALL_SUMMARY` card has its own text. **Open gaps:** the call-log retention job, the Admin evidence endpoint and the real legal hold stay with US-016; iOS keep-awake and iOS device proof; Hindi review; the on-device checks of testing guide sections B to D and H (no phone was connected at the end of the build).

**Status: Implemented (not yet merged).** Approved 2026-11-22. Manual testing guide: `Manual Testing Guides/US-014-US-015-Testing-Guide.md`.
