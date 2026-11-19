# US-131 - Push Notification Channel (FCM): QA Testing Guide

**Sprint 4 · Communication & Negotiation**

Manual test cases for push notifications: registering a phone, the generic pushes for chat messages and offers, the
permission prompt, sign-out, and the clean-up. The push itself needs **a real phone** and a Firebase project; the
registration API and the policy are also checked with `curl` and the database.

> **What ships:** `PUT` and `DELETE /api/v1/devices/push-token`; the table `device_tokens` (migration `V40`); the
> providers `noop` and `fcm`; chat messages and negotiation events pushed with generic text (English or Hindi);
> tokens revoked at sign-out, when an account stops being active, when Firebase says the token is dead, and by a daily
> clean-up. In the app: the install id, registration on start, token change and language change, the explanation sheet
> the first time a conversation is opened, the "Notifications are off" strip, taps that open the conversation or
> negotiation, and the Android channels.
> **Not in this story:** per-category preferences (US-087), WhatsApp (US-086), call pushes (US-014 and US-015 are on
> hold), marketing push, web push.
> **On hold:** **iOS** is built and left ready but not tested: it needs the Apple Developer account, the Push
> Notifications capability on the App ID and the APNs key uploaded in Firebase (`valuex-infra/docs/push.md`). Run
> section H when that exists.

| Setting | Value |
|---|---|
| Backend base URL | `http://localhost:8080` |
| Properties | `valuex.push.provider` (env `PUSH_PROVIDER`: `noop` default, `fcm`), `valuex.push.fcm.credentials-json` (env `FCM_SERVICE_ACCOUNT_JSON`, a secret) |
| Admin settings (`platform_settings`) | `DEVICE_TOKEN_CALLS_PER_HOUR` 30, `PUSH_TOKEN_REVOKED_RETENTION_DAYS` 30, `PUSH_TOKEN_STALE_DAYS` 60 |
| Error codes | 422 `ERROR_INVALID_PUSH_TOKEN`; 429 `RATE_LIMIT_EXCEEDED` |
| Firebase files (not committed) | `valuex-mobile/android/app/google-services.json`, `valuex-mobile/ios/Runner/GoogleService-Info.plist` |
| Known gaps | Real delivery is not covered by the automated tests; iOS is untested; offer pushes have no collapse key (each shows); the call policy rows are unused until calls exist |

---

## Prerequisites

1. Backend and PostgreSQL running. For sections A to D and G, `PUSH_PROVIDER=noop` is enough; for E, F and H use
   `PUSH_PROVIDER=fcm` and `FCM_SERVICE_ACCOUNT_JSON` set from the secret manager (one line; never paste it into a ticket).
2. A Firebase project with the Android app `com.valuex.valuex_mobile` registered, `google-services.json` copied to the path above,
   and the service account with the role Firebase Cloud Messaging API Admin.
3. Two `ACTIVE` accounts: `$ALICE` (seller) and `$BOB` (buyer); a live listing owned by Alice. One Android 13+ phone for Alice
   (a second phone or the emulator for Bob).
4. Build and install: `flutter run --dart-define-from-file=config/dev_local.json` (or the usual build) on the phone.
5. Variables:

```bash
B="localhost:8080/api/v1"
HA="Authorization: Bearer $ALICE"
```

---

## A. Registering a token (AC1, AC6)

| # | Steps | Expected |
|---|---|---|
| A1 | `curl -i -X PUT -H "$HA" -H 'Content-Type: application/json' $B/devices/push-token -d '{"deviceId":"d1","platform":"ANDROID","token":"tok-1","locale":"hi","appVersion":"0.1.0","permissionGranted":true}'` | 204, no body. `SELECT user_id, platform, locale, permission_granted, revoked_at FROM device_tokens WHERE fcm_token='tok-1'` shows Alice, ANDROID, hi, true, null. |
| A2 | Repeat A1 | 204; still one row; `last_seen_at` moved forward. |
| A3 | Same call with `"token":"tok-2"` (a refreshed token, same `deviceId`) | 204; `tok-1` now has `revoked_at` set and `tok-2` is active. |
| A4 | Register `tok-2` with Bob's token and `deviceId` `d1` | 204; the row of `tok-2` now belongs to Bob; Alice has no active token. |
| A5 | `"permissionGranted":false` | 204; stored as false. Nothing is pushed to that token (see D4). |
| A6 | `"platform":"WINDOWS"`, an empty `token`, a missing `deviceId`, a 513-character token | 422 `ERROR_INVALID_PUSH_TOKEN` each; no row. |
| A7 | Without a token | 401. |
| A8 | 31 calls within an hour (`DEVICE_TOKEN_CALLS_PER_HOUR` 30) | The 31st answers 429 `RATE_LIMIT_EXCEEDED`. |
| A9 | Search the log and every API response for a token value | Never present. |

## B. Sign-out and account state (AC2)

| # | Steps | Expected |
|---|---|---|
| B1 | `curl -i -X DELETE -H "$HA" -H 'Content-Type: application/json' $B/devices/push-token -d '{"deviceId":"d1"}'` | 204; the active token of that device has `revoked_at`. Repeat: 204 again. An unknown `deviceId`: 204. |
| B2 | Bob calls DELETE with Alice's `deviceId` | 204 and Alice's token is untouched (a person removes only their own). |
| B3 | In the app signed in as Alice, tap Sign out | Sign-out works at once, also with no network (within about 3 seconds); the row has `revoked_at`; signing in again registers a new token. |
| B4 | Close or suspend Alice's account (Admin or SQL through the app's state service) | All her tokens have `revoked_at`. Making her ACTIVE again does not bring them back (the app registers again on its next start). |

## C. Permission prompt (AC7)

| # | Steps | Expected |
|---|---|---|
| C1 | Fresh install, sign in as Alice. Nothing asks for notifications at launch or on Home. | No prompt. |
| C2 | Open any conversation | A sheet explains notifications ("Hear about messages and offers"), then the system prompt follows only after "Turn on notifications". |
| C3 | Allow | The phone is registered with `permission_granted = true`. |
| C4 | Repeat on a fresh install, tap "Not now" | No system prompt; the phone is registered with `permission_granted = false`; opening another conversation does not ask again. |
| C5 | Profile > Notifications while off | A strip says notifications are off with "Open Settings"; the button opens the app's system settings. Turn them on, return: the strip is gone and the row shows `permission_granted = true`. |
| C6 | Hindi app language | The sheet and strip read in Hindi; both fit at 200 percent text and 320 px width, buttons at least 48 dp. |
| C7 | Android 12 or older (no runtime permission) | No sheet; the phone registers as allowed. |

## D. What is pushed (AC3, AC4, AC6)

Use `PUSH_PROVIDER=noop` and read the backend log (`Push not sent (provider noop): event=... channel=...`), or
`fcm` with a real phone (section E).

| # | Steps | Expected |
|---|---|---|
| D1 | Alice's phone is registered; the app is closed. Bob sends a chat message | One push for each message: log line `event=CHAT_MESSAGE channel=chat`. The in-app notification is unchanged (one per thread per window). |
| D2 | Bob sends 5 messages quickly | 5 push attempts (each replaces the previous on the phone, see E3); one in-app notification. |
| D3 | Alice has the app open in the foreground (chat list visible) when Bob writes | No push (`push.skipped{reason=online}`); the message arrives over the live connection. |
| D4 | Alice's token has `permission_granted = false` | No push (`reason=permission`). A user with no token: `reason=no_token`. |
| D5 | Alice's phone language Hindi (token `locale` hi) | The text is in Hindi (see E2). |
| D6 | Bob makes an offer on Alice's listing, Alice answers | A push for each event for the other person: `OFFER_RECEIVED`, `OFFER_COUNTERED`, `OFFER_ACCEPTED`, `OFFER_REJECTED` (channel offers). |
| D7 | Search every push for text | Never holds the message text, an amount, an item title or a phone number: the title names the sender only for chat; the body only asks to open the app. |
| D8 | Block Bob (US-132), then Bob writes | No message is delivered and no push. |

## E. On a real phone with Firebase (AC3, AC5, AC8, AC9)

Set `PUSH_PROVIDER=fcm` and restart the backend.

| # | Steps | Expected |
|---|---|---|
| E1 | Alice's app in the background. Bob writes "hello" | A notification arrives within a few seconds on the channel Messages: "New message from Bob" / "Open JustQlic to read it". The lock screen shows no message text. |
| E2 | Same with Alice's app language Hindi | "Bob का नया संदेश" / "पढ़ने के लिए JustQlic खोलें". |
| E3 | Bob sends 3 messages while the phone is locked | One notification of that thread remains on the phone (they replace each other). |
| E4 | Kill the app (swipe away) and send a message | The notification still arrives. Tap it: the app opens that conversation. |
| E5 | App in the background, tap the notification | The conversation opens; tapping a second notification of the same event does nothing extra. |
| E6 | App open in the foreground on another screen | No system notification appears (the live connection shows the message). |
| E7 | Phone settings > Apps > JustQlic > Notifications | Four channels: Messages, Offers, Calls, General (in Hindi on a Hindi phone). |
| E8 | Uninstall the app on the phone, then send a message | The backend log has no error; the token gets `revoked_at` after Firebase answers "unregistered" (the first push fails, the token is revoked). |
| E9 | Stop the network of the backend towards Firebase, send a message | The send still succeeds for Bob; the log shows a warning after 3 tries; `push.failed{reason=transient}` goes up; the in-app notification exists. |
| E10 | Sign out on Alice's phone, then Bob writes | No notification arrives on that phone. Sign in as Charlie on the same phone: pushes meant for Alice do not arrive; Charlie's own do. |
| E11 | Backend with `PUSH_PROVIDER=fcm` and an empty `FCM_SERVICE_ACCOUNT_JSON` | The backend refuses to start with a message naming the variable. |
| E12 | Firebase console > Messaging > Send test message to the token from the table | A test message arrives on the phone. |

## F. Without Firebase (AC, G14)

| # | Steps | Expected |
|---|---|---|
| F1 | Build the app with no `google-services.json` | The build succeeds; the app starts; no prompt, no strip, no registration (push is off). |
| F2 | Backend with `PUSH_PROVIDER=noop` | Everything works; the log shows only the event and channel for each push. |

## G. Clean-up (AC10)

| # | Steps | Expected |
|---|---|---|
| G1 | Insert a token revoked 40 days ago, one revoked 5 days ago, one active not seen for 70 days and one seen today; run the job (or wait for 03:30) | The first and third are deleted; the others stay. |
| G2 | Change `PUSH_TOKEN_REVOKED_RETENTION_DAYS` to 3 in `platform_settings` and run again | The 5 day old revoked token goes too. |
| G3 | Use the app daily for a week | Its token's `last_seen_at` is refreshed at every app start. |

## H. iOS (on hold: run when the Apple account and APNs key exist)

| # | Steps | Expected |
|---|---|---|
| H1 | Enable Push Notifications on the App ID, create the APNs key, upload it to Firebase, add `GoogleService-Info.plist`, build on a Mac with signing | The build succeeds; `Runner.entitlements` has `aps-environment`; Background Modes shows Remote notifications. |
| H2 | On a real iPhone, open a conversation | The explanation sheet, then the iOS prompt; after Allow the phone registers (`platform = IOS`). |
| H3 | Repeat E1 to E6 | The same results; a push in the foreground shows no banner. |

## Run the automated tests

```bash
# Backend
cd valuex-backend
mvn test -Dtest="Push*Test,DeviceToken*Test,FcmPushAdapterTest,NoopPushAdapterTest,AccountStatePushListenerTest,ChatMessageListenerTest,NotificationDispatcherTest,CommunicationSettingTest"
# Integration (needs Docker; on this machine set JAVA_TOOL_OPTIONS='-Dapi.version=1.44 -Duser.timezone=UTC')
mvn test -Dtest=DeviceTokenIntegrationTest

# Mobile
cd valuex-mobile
flutter test --no-pub test/core/push test/features/notifications test/features/auth/presentation/session_controller_test.dart
```

## Acceptance coverage

| Criterion | Section |
|---|---|
| AC1 register and refresh | A, E10 |
| AC2 sign-out and account state | B, E10 |
| AC3 chat push, online skip | D1 to D4, E1, E6 |
| AC4 generic text, language | D5, D7, E1, E2 |
| AC5 dead token and retries | E8, E9 |
| AC6 permission refused | A5, C4, D4 |
| AC7 permission timing | C |
| AC8 tap opens target | E4, E5 |
| AC9 channels and iOS setup | E7, H |
| AC10 clean-up | G |
