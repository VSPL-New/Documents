# US-014 + US-015 - Voice and Video Calls with the Seller: QA Testing Guide

**Sprint 4 · Communication & Negotiation**

Manual test cases for the in-app voice call (US-014) and video call (US-015) between a buyer and the seller of a listing,
on LiveKit. The backend is checked with `curl` and SQL; the app is checked on two phones (or one phone and a second
participant joined from the LiveKit web client, see section B).

> **What ships:** `POST /api/v1/calls/voice` and `/video`, `GET /api/v1/calls/{id}`, `POST /api/v1/calls/{id}/accept`,
> `/decline`, `/cancel`, `/join`, `/connected`, `/heartbeat`, `/end`, `GET /api/v1/calls?threadId=`, the provider
> webhook `POST /api/v1/webhooks/rtc` (public, signed by LiveKit); migration `V43` (`call_sessions`, `call_events`, seven
> `CALL_*` settings); the call watchdog job; call summary cards and missed-call notifications; the ringing push
> (`CALL_INCOMING`, `VIDEO_CALL_REQUEST`); in the app: the Call and Video buttons on the listing page and in the
> conversation header, the call screen (ringing, voice, video with picture-in-picture, ended), the incoming call screen,
> Android foreground service and permissions.
> **Not in this story:** recording and transcription of any call (decision D24: the MVP records and transcribes
> nothing); the call-log retention job, the Admin evidence endpoint and the legal hold (US-016: no call row is deleted
> until then); CallKit and a VoIP push (heads-up push only); iOS keep-awake (see Known gaps).

| Setting | Value |
|---|---|
| Backend base URL | `http://localhost:8080` |
| Settings (Admin-managed, `platform_settings`) | `CALL_RING_SECONDS` 45, `CALL_MAX_MINUTES` 30, `CALL_JOIN_SECONDS` 30, `CALL_HEARTBEAT_TIMEOUT_SECONDS` 45, `CALL_LOG_RETENTION_DAYS` 180 (stored, not enforced yet), `CALL_VIDEO_MAX_HEIGHT` 720, `CALL_VIDEO_MAX_FPS` 24, and the existing `CALL_ATTEMPTS_PER_PAIR_PER_HOUR` 3 |
| Properties and environment | `CALLS_ENABLED` (default false), `RTC_PROVIDER` (`mock` or `livekit`, default `mock`), `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` (the last three are required when the provider is `livekit`; the backend refuses to start and names the missing one) |
| Error codes | 503 `ERROR_CALLS_UNAVAILABLE`, `ERROR_CALL_FAILED`; 403 `ERROR_BLOCKED`; 404 `ERROR_CALL_NOT_FOUND` (also for another person's call); 409 `ERROR_CALL_IN_PROGRESS`, `ERROR_USER_BUSY`, `ERROR_SELLER_UNAVAILABLE`, `ERROR_CALL_NOT_ACTIVE`, `ERROR_OWN_LISTING`; 429 `WARNING_RATE_LIMIT`; client side: `ERROR_MICROPHONE_PERMISSION`, `ERROR_CAMERA_PERMISSION` |
| Known gaps | All Hindi texts need native review; iOS is not tested (no device) and has no keep-awake; the Android 14 background behaviour needs a physical check (section H); the LiveKit project has no region pinning (decision) |

---

## Prerequisites

1. PostgreSQL, Redis and the backend running with `CALLS_ENABLED=true`. For a real call, also `RTC_PROVIDER=livekit` and
   the three LiveKit variables. Local values live in `scripts\dev-real.env` (`LIVEKIT_URL` is the `wss://...livekit.cloud`
   address; never commit the key or the secret). `scripts\start-dev-real.ps1` passes them to the backend.
2. Two `ACTIVE` accounts with display names: `$SELLER` (Asha K) and `$BUYER` (Ravi S); a third, `$THIRD` (Eve).
3. A live listing `LISTING` owned by `$SELLER`. The seller's phone has the app installed and has signed in once (a push
   token is stored), or is connected (online): otherwise the call is refused as `ERROR_SELLER_UNAVAILABLE`.
4. Variables:

```bash
B="localhost:8080/api/v1"
HS="Authorization: Bearer $SELLER"
HB="Authorization: Bearer $BUYER"
HT="Authorization: Bearer $THIRD"
```

---

## A. The listing page and the conversation (US-014 AC1, US-015 AC1)

| # | Steps | Expected |
|---|---|---|
| A1 | `CALLS_ENABLED=false`; read `GET $B/listings/$LISTING/public` as the buyer | `call` and `video` are `COMING_SOON`; tapping Call or Video in the app says "Coming soon". |
| A2 | `CALLS_ENABLED=true`, restart; read the listing | `call` and `video` `available:true`. |
| A3 | As the seller | Every option `OWN_LISTING`; Call and Video are dimmed. |
| A4 | App: open the conversation as the buyer | Call and Video in the header are enabled; as the seller they are dimmed. |
| A5 | App: a conversation that is read-only (blocked, listing removed) | Call and Video in the header are dimmed. |
| A6 | `CALLS_ENABLED=false`, then `curl -X POST -H "$HB" -H "Content-Type: application/json" -d '{"listingId":"'$LISTING'"}' $B/calls/voice` | 503 `ERROR_CALLS_UNAVAILABLE`; nothing stored. |

## B. A voice call from ringing to hang-up (US-014 AC2 to AC6)

| # | Steps | Expected |
|---|---|---|
| B1 | App (buyer): tap Call on the listing. Allow the microphone | The call screen shows "Calling...", the seller's name, "About <listing>" and "This call is not recorded"; one Cancel button. `SELECT state FROM call_sessions ORDER BY requested_at DESC LIMIT 1` is `RINGING`. |
| B2 | App (seller): the phone rings | The incoming call screen opens at once when the app is open (`call.incoming` event); when the app is closed a high-priority push "Incoming call" arrives and a tap opens `/call/<id>`. Accept and Decline are shown. |
| B3 | Seller taps Accept and allows the microphone | State `ACCEPTED`, then both phones say "Connecting...", join the room and the state becomes `ACTIVE`; both show the timer from 0:00; the call is audible both ways. |
| B4 | During the call: Mute, Speaker | The other person stops hearing you while muted; the label changes to Unmute; Speaker toggles to Earpiece and back. |
| B5 | `SELECT event_type FROM call_events WHERE call_id='<id>' ORDER BY occurred_at` | `REQUESTED, ACCEPTED, JOINED, JOINED, CONNECTED` (and later `ENDED`). |
| B6 | While active, Redis `GET call:hb:<call>:<user>` | A recent epoch value for each person, refreshed every 15 seconds; **no** `UPDATE call_sessions` per beat. |
| B7 | Buyer taps End call | Both phones show "Call ended" and the duration; `end_reason` `COMPLETED`, `duration_seconds` right (within 2 s of the timer); `room_closed_at` is set. |
| B8 | The conversation | A card "voice call · 1:05" for both people; the seller also has no extra notification. |
| B9 | Repeat `POST /calls/<id>/end` | 200 with the call as it was left; nothing changes. |
| B10 | Two-party test without a second phone: as the seller, `curl -X POST -H "$HS" $B/calls/<id>/accept` then `POST $B/calls/<id>/join` | The answer holds `credentials.url` and `credentials.token`. Open `https://meet.livekit.io/?tab=custom`, paste them, and join: the buyer's phone shows both people connected. |

## C. A video call (US-015)

| # | Steps | Expected |
|---|---|---|
| C1 | App (buyer): tap Video and allow camera and microphone | "Calling..."; `call_type` `VIDEO`. |
| C2 | App (seller): the incoming screen says "Incoming video call"; Accept | Both join; each sees the other full screen and a small own picture. |
| C3 | Drag the small picture | It follows the finger and stays on screen. |
| C4 | Turn camera off, then on; Flip camera | The small picture disappears and returns; the other person sees the picture stop and restart; Flip changes front and back. |
| C5 | The join answer (`POST /calls/<id>/join`) | `media` `VIDEO` and `video` `{maxHeight:720,maxFps:24}`. Set `CALL_VIDEO_MAX_HEIGHT` to 360 and `CALL_VIDEO_MAX_FPS` to 15 in `platform_settings`, wait for the cache (about a minute), make a new video call: the join answer carries 360 and 15 and the picture is smaller. Restore. |
| C6 | Weak line: switch the phone to a very slow network | The chip says "Weak connection", a banner "Your connection is weak." with Turn off video appears above the controls; tapping it turns the camera off and keeps the sound. |
| C7 | Refuse the camera at the first prompt | Nothing is created; "Camera and microphone access are required for video calls" with Open settings. A voice call is still possible. |
| C8 | Check the LiveKit project's egress and recording pages | No recording or egress was started (decision D24). |

## D. Calls that do not connect (US-014 AC7 to AC9)

| # | Steps | Expected |
|---|---|---|
| D1 | Buyer calls; nobody answers for 45 s (or set `CALL_RING_SECONDS` to 10) | Within 15 s of the limit both phones show: buyer "Asha K did not answer", seller "Missed call from Ravi S"; `end_reason` `NO_ANSWER`; the seller has an in-app notification "Missed call from Ravi S" and a push; the conversation card says "No answer" for the buyer and "Missed voice call" for the seller. |
| D2 | Seller taps Decline | The seller's screen closes; the buyer sees "Asha K declined the call"; `DECLINED`; the card says "Declined". |
| D3 | Buyer taps Cancel while ringing | The buyer's screen closes; the seller's incoming screen shows "Missed call from Ravi S"; `CANCELLED`. |
| D4 | Seller accepts, but turn the buyer's network off before the buyer joins; wait 30 s (`CALL_JOIN_SECONDS`) | The call ends with `JOIN_FAILED`; both phones say "The call could not be connected". |
| D5 | During an active call, put one phone in airplane mode | After about 45 s (`CALL_HEARTBEAT_TIMEOUT_SECONDS`) plus up to 15 s, the call ends `DROPPED`; the duration ends at the **older** of the two last beats (`SELECT duration_seconds`). The other phone says "The call ended because the connection was lost". |
| D6 | Kill the app of one person during a call | The same as D5. |
| D7 | Set `CALL_MAX_MINUTES` to 3 and call | At 1:00 a banner "This call ends in 2:00" appears and counts down; at 3:00 the call ends `MAX_DURATION`; both phones say "The call reached its time limit". Restore. |
| D8 | Stop the backend for 1 minute during a call, then start it | The call continues on the media service; heartbeats resume; if the outage was longer than the timeout the call is ended `DROPPED` on the first watchdog run. |

## E. Rules and errors (US-014 AC10, edge cases)

| # | Steps | Expected |
|---|---|---|
| E1 | The seller calls their own listing | 409 `ERROR_OWN_LISTING`. |
| E2 | Buyer starts a call, then starts a second one (voice or video) | 409 `ERROR_CALL_IN_PROGRESS`. |
| E3 | `$THIRD` calls the seller while the seller is on a call | 409 `ERROR_USER_BUSY` ("The seller is on another call"). |
| E4 | Seller with no push token and not connected | 409 `ERROR_SELLER_UNAVAILABLE`. |
| E5 | Block the buyer during an active call (`PUT /users/<BUYER_ID>/block` as the seller) | The call ends at once, `BLOCKED`; both phones say "This call could not continue"; a new call is 403 `ERROR_BLOCKED`. |
| E6 | `UPDATE platform_settings SET setting_value='1' WHERE setting_key='CALL_ATTEMPTS_PER_PAIR_PER_HOUR'`, make two calls, wait for the cache | The second attempt after one ended is 429 `WARNING_RATE_LIMIT`. Restore to 3. |
| E7 | `GET /calls/<id>`, `/accept`, `/join` as `$THIRD` | 404 `ERROR_CALL_NOT_FOUND`. |
| E8 | Buyer calls `/accept`; seller calls `/cancel` | 409 (only the person called accepts; only the caller cancels). |
| E9 | `/accept` after the ringing time is over | 409 `ERROR_CALL_NOT_ACTIVE`. |
| E10 | `/heartbeat` for an ended call | 409 `ERROR_CALL_NOT_ACTIVE` (the app reads the call and shows the ended screen). |
| E11 | `/join` while the call is still `RINGING` | 409 `ERROR_CALL_NOT_ACTIVE`. |
| E12 | Two simultaneous `POST /calls/voice` from the buyer (two terminals) | One 201 and one 409; one `call_sessions` row. |
| E13 | Use a wrong `LIVEKIT_API_SECRET`, start a call and accept | The join answers 503 `ERROR_CALL_FAILED`; the app says "We could not connect the call"; the call ends. |
| E14 | Report the call from the call screen (Report) and file it as the seller | The report is accepted; `SELECT flagged FROM call_sessions` is true. A report by `$THIRD` is refused (404). |

## F. The provider webhook (public path)

| # | Steps | Expected |
|---|---|---|
| F1 | `curl -i -X POST $B/webhooks/rtc -d '{}'` (no signature) | 401. |
| F2 | A body signed with another secret, an expired token, or a changed body | 401 for each; `rtc.webhook.rejected` increases (`/actuator/metrics/rtc.webhook.rejected`). |
| F3 | During a real call, watch the LiveKit dashboard's webhook log | 200 for `participant_joined` and `participant_left`; a leave **does not** end the call. |
| F4 | The same event id delivered twice | The second is answered 200 and ignored (one `JOINED` row). |
| F5 | `room_started`, `egress_*`, any other event | 200, ignored. |

## G. Closing the media room

| # | Steps | Expected |
|---|---|---|
| G1 | After B7, `SELECT room_closed_at FROM call_sessions` | Set. The LiveKit dashboard shows no open room for the call. |
| G2 | Use a wrong secret for the end (or stop network access to LiveKit), end a call, then restore | `room_closed_at` is null; within 30 s of the next watchdog run it is set. |

## H. Phone behaviour (Android)

| # | Steps | Expected |
|---|---|---|
| H1 | During a call press Home and use another app for 2 minutes (Android 13 and 14) | The microphone (and for video the camera) keep working; the notification "JustQlic call in progress" is shown; tapping it returns to the call. |
| H2 | During a call let the phone sit for 2 minutes | The screen does not turn off. |
| H3 | The call ends | The notification disappears; the screen can sleep again. |
| H4 | Refuse the microphone ("Don't ask again") and tap Call | "Microphone access is required for calls" with Open settings, which opens the app's settings page. |
| H5 | An incoming call while the app is in the background | The heads-up push rings on the "Calls" channel; it expires after 60 s (a push delivered late is not shown). |
| H6 | A system call or an audio route change (Bluetooth) during a call | The audio follows the route; a phone call interrupts and the call recovers or ends by the rules in D5. |

## I. Layout, accessibility and language

| # | Steps | Expected |
|---|---|---|
| I1 | The ringing, voice, video and ended screens at 320 px width and 200 percent text | No overflow; the controls wrap; the video controls scroll if too tall. |
| I2 | TalkBack | Every control has its name (Accept, Decline, Mute, Unmute, Speaker, Earpiece, Camera, Flip camera, Report, End call); the timer is read as "Duration 5:00"; the weak-line and two-minute banners are announced. |
| I3 | Switch the app to Hindi | All call texts are in Hindi (needs native review). |
| I4 | Back button during a live call | Nothing happens (End, Cancel and Decline are the ways out); after the call ended it closes the screen. |

## J. Privacy (decision D24)

| # | Steps | Expected |
|---|---|---|
| J1 | `\d call_sessions` and `\d call_events` | No column or table about recording, consent or a transcript; no `transcript_*` table exists. |
| J2 | Search the backend logs of a call | No token, URL, key or secret, and no media. |
| J3 | The ringing and call screens | The line "This call is not recorded" is shown (information only; no tick box). |

---

## Automated tests

```bash
# Backend: unit tests and the integration test on Testcontainers PostgreSQL
cd valuex-backend
mvn -o test -Dtest="Call*Test,RtcWebhookServiceTest,LiveKit*Test,RtcProviderConfigTest,CommunicationSettingTest,FcmPushAdapterTest"
mvn -o verify                                   # everything, with checkstyle

# The live check of the LiveKit token and API client (skipped unless the three LIVEKIT_* variables are set)
LIVEKIT_URL=... LIVEKIT_API_KEY=... LIVEKIT_API_SECRET=... mvn -o test -Dtest=LiveKitLiveSmokeTest

# Mobile
cd valuex-mobile
flutter test --dart-define=SKIP_PIXEL_CONTRAST=true test/features/calls test/features/chat test/features/listing_view
dart format --output=none --set-exit-if-changed lib test integration_test && flutter analyze
```

`CallIntegrationTest` covers a voice and a video call from ring to hang-up, no answer, decline, cancel, a join that never
happens, a silent person, the longest time, a retry of the room close, a block in mid-call, another person's call, a busy
seller, an unreachable seller, two parallel calls, a signed and an unsigned webhook on the public path, a report that
flags the call, and the schema check of J1.
