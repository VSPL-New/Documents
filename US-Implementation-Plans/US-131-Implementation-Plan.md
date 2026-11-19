# US-131: Push Notification Channel (FCM) - Implementation Plan

## 1. Header

| Field | Value |
|---|---|
| Story | US-131 - Push Notification Channel (**proposed story**, found missing while writing the Sprint 4 LLD; not yet in `user-stories.md`, and `Sprint-plan.md` only mentions it in the 2026-11-15 note under Sprint 4, see gap G1) |
| Sprint | Sprint 4 - Communication & Negotiation |
| Story points | 5 (proposed in LLD Part B) |
| Repos involved | valuex-backend (device tokens, `PushPort` with FCM and no-op adapters, push policy and copy, dispatcher change, chat hook, cleanup job), valuex-mobile (Firebase, `PushService`, permission timing, token registration, Android channels, deep links), valuex-infra (FCM secret, Firebase files in CI, APNs key: documentation). No `valuex-ai` or `valuex-web` change. |
| Dependencies | US-077 (notification dispatcher, done). Uses US-013 (chat events, built) and US-130 (`PresenceService`, built 2026-11-17 in backend PR #69 and mobile PR #78, both merged, G2). Serves US-017, US-076, US-080 (offer events, later) and US-014, US-015 (call pushes, on hold). |
| Date | 2026-11-17 |
| Design source | [Sprint 4 LLD](../LLD/Sprint-4-Communication-Negotiation-LLD.md) Part B (B.1 to B.10), section 1.5 (`valuex.push.*`), 1.8 (resilience), Part E (`ChatMessageListener`), decisions D15 and D18. |
| Branches (proposal) | `feature/US-131-push-notifications` in `valuex-backend`, `valuex-mobile` and `valuex-infra`, cut from `main` after #69 and #78 are merged, rebased before work starts (CLAUDE.md rule 5.1). Documents: `docs/US-131-push-notifications`. |
| Flyway number | `V40__device_tokens.sql` (V39 is Buy Now; re-check at branch time). |

## 2. Story Recap

The LLD gives a story statement and edge cases but no acceptance-criteria list. The criteria below are derived from LLD B.1 to B.9 only; nothing is added to them (gap G1).

**As a** user **I want** a notification on my phone when someone messages me, makes or answers an offer, or calls me **so that** I can respond without keeping the app open.

| ID | Behaviour (derived from LLD Part B) |
|---|---|
| AC1 | The app registers its push token after sign-in and whenever the token changes (`PUT /api/v1/devices/push-token` with install id, platform, token, language, app version and whether the permission was granted). A token belongs to one account at a time: registering it on another account moves it, and older tokens of the same account and install id are revoked. |
| AC2 | The app removes its token at sign-out (`DELETE /api/v1/devices/push-token`, idempotent) before the session is cleared; an account that is closed (or stops being active, G10) loses all its tokens. A signed-out phone never receives another person's notification. |
| AC3 | A chat message sends a push to every active token of the recipient that has the permission, unless the recipient is online in the foreground (their open app already got it over the socket). The in-app notification is unchanged. |
| AC4 | The push is generic: a title such as "New message from Asha" and the body "Open JustQlic to read it". It never holds message text, an offer amount or a phone number (decision D18). It is sent in English or Hindi according to the language stored with the token. |
| AC5 | A token FCM reports as `UNREGISTERED` or `INVALID_ARGUMENT` is revoked and skipped from then on. A temporary FCM failure is retried three times and then counted; the in-app notification and the socket are not affected. |
| AC6 | A phone whose user denied the permission is registered with `permission_granted = false`; nothing is pushed to it. |
| AC7 | The notification permission is asked the first time the user starts a chat (and later when offers exist), after a short explanation sheet, never at launch. A "no" is remembered, and Profile > Notifications offers a shortcut to the system settings. |
| AC8 | Tapping a notification opens its target (`/chats/{id}` now; offers and calls later) through the existing deep-link mapping; a push that arrives while the app is open does not duplicate what the socket showed (G9). |
| AC9 | Android has the channels `chat`, `offers`, `calls` and `general`; iOS is configured for remote notifications. |
| AC10 | Revoked tokens are deleted 30 days after revocation and tokens not seen for 60 days are deleted (daily job). |

**Edge cases (LLD B.1.1):** user looking at the app; stale token or uninstalled app; sign-out; the same user on two phones; permission denied; FCM down; lock-screen privacy; language.
**Validation rules:** unknown platform or empty token is `ERROR_INVALID_PUSH_TOKEN` (422); token calls are limited to 30 per hour per user (`RATE_LIMIT_EXCEEDED`, 429); a token is never logged and never returned by any API; the FCM credentials live only in the secret manager.
**Out of scope (LLD B.2):** per-category user preferences (US-087), WhatsApp (US-086), marketing push, native incoming-call screens (D15), web push. Call and offer pushes are designed in the policy table but are sent only when those stories exist.

## 3. Design Reference

LLD Part B: B.3 `device_tokens`, B.4 API and payload, B.5 backend design (`PushChannelSender`, `PushPolicy`, token lifecycle, `PushPort`, dedupe, metrics), B.6 sequence, B.7 mobile design, B.8 codes, B.9 security, B.10 tests; Part E (`ChatMessageListener` pushes with the collapse key `chat:{threadId}`).

### Key design decisions

- **Push is best effort.** PostgreSQL and the in-app notification stay the record; a failed push never fails the action that caused it.
- **One port.** `PushPort.send(token, message)` has `FcmPushAdapter` (Firebase Admin SDK) and `NoopPushAdapter` (default in dev and CI), chosen by `valuex.push.provider`.
- **One policy table.** `PushPolicy` maps an event type to its Android channel, priority and whether it is skipped for an online user; calls are never skipped and have no inbox row.
- **Generic content.** The server never puts text or amounts in a push; the app fetches detail over the authenticated API after the tap.
- **Tokens are credentials.** Hashing is not possible (FCM needs the value), so the value is stored, never logged, never returned, revoked at sign-out and cleaned up.

### Verified implementation anchors (checked 2026-11-17)

| Area | Finding and consequence |
|---|---|
| Channels | `notification/domain/NotificationChannelType` has `IN_APP`, `SMS`, `EMAIL`; its comment says push is absent. Add `PUSH`. |
| Dispatcher | `NotificationDispatcher.dispatch` is `@Transactional`, always saves the in-app row, honours `dedupeKey` (a repeat sends nothing), and sends SMS and email inside the transaction. FCM is a network call, so push must run **after commit and off the request thread** (G6). The dispatcher has no push-only mode: calls need one (no inbox row). |
| Chat hook | `communication/.../ChatMessageListener` dispatches `CHAT_MESSAGE` with channels `{IN_APP}`, coalesced by `chat:{thread}:{recipient}:{window}`. With the dedupe, a push through the dispatcher would go out once per window, while LLD E.5 says every message pushes with a collapse key (G4). |
| Presence | `realtime/application/PresenceService.isOnline(userId)` exists in backend PR #69. The notification module must not import the realtime package: use a small `UserPresencePort` in `notification/application/port` with an adapter in `realtime`. |
| Preferences | `NotificationPreferences.shouldSend(userId, eventType, channel)` always answers true; the push sender calls it so US-087 can switch categories off later. |
| Settings | `CommunicationSetting` registry (US-132, US-069, US-013, US-130) is where tunable numbers go; read through `PlatformSettingsService.communication()` (G11). |
| Retry | `pom.xml` has `resilience4j-circuitbreaker` only; `AiGatewayClient` implements its own retry loop and circuit breaker. No `resilience4j-retry` dependency (G5). |
| Firebase | Neither repo has Firebase: no `firebase-admin` in the backend, no `firebase_core` or `firebase_messaging` in `pubspec.yaml`, no `google-services` Gradle plugin, no `GoogleService-Info.plist`; Android `AndroidManifest.xml` has no `POST_NOTIFICATIONS`. |
| Install id | The LLD says the app has a device id "in secure storage". A search of `valuex-mobile/lib` finds none (G7). |
| Logout | `auth/.../LogoutService` revokes the session row and blocklists the jti; it knows no device. The app calls `DELETE` itself before logging out. `UserStateService.close(...)` and `UserStateChangedEvent` exist for the account side. |
| Mobile routing | `features/notifications/domain/notification_deep_links.dart` maps exact paths (`/profile`, `/saved-items`, saved searches, listing pages); `/chats/{id}` needs a pattern. Navigation on tap is in `notification_navigation.dart`. |
| Mobile packages | `permission_handler` (`openAppSettings`), `flutter_secure_storage`, `uuid`, `shared_preferences` are present. `AppConstants.appVersion` and `localeControllerProvider` give version and language. |

## 4. Implementation Steps

### Documents (first, small)
- [ ] Add US-131 to `Sprint-plan.md` Sprint 4 and `user-stories.md` using LLD B.1 as the story text and the criteria of section 2 (gap G1). Update the Sprint 4 story-count lines.

### Database
- [ ] `V40__device_tokens.sql`: `device_tokens` exactly as LLD B.3 (unique `fcm_token`, the two partial indexes, platform CHECK), plus seeds for the three settings of G11 (`INSERT ... ON CONFLICT (setting_key) DO NOTHING`, same style as `V34`/`V35`).

### Backend (`valuex-backend`)
- [ ] `pom.xml`: add `com.google.firebase:firebase-admin` (version pinned when built).
- [ ] `ValuexProperties`: `push.provider` (`noop` default, env `PUSH_PROVIDER`) and `push.fcm.credentials-json` (env `FCM_SERVICE_ACCOUNT_JSON`, empty); `application.yml` entries; the `fcm` adapter refuses to start with empty credentials.
- [ ] `CommunicationSetting` keys (G11): `DEVICE_TOKEN_CALLS_PER_HOUR` (30), `PUSH_TOKEN_REVOKED_RETENTION_DAYS` (30), `PUSH_TOKEN_STALE_DAYS` (60), each with a range; update `CommunicationSettingTest`.
- [ ] `notification/domain`: add `PUSH` to `NotificationChannelType` and fix its comment; `DeviceToken` entity, `DevicePlatform` enum.
- [ ] `notification/infrastructure/persistence/DeviceTokenRepository`: find active by user, find by `fcm_token`, revoke by user, by user and device, by token, delete for cleanup.
- [ ] `notification/application/service/DeviceTokenService`: `register` (validate platform and token, upsert by `fcm_token`, set `user_id` to the caller, clear `revoked_at`, revoke older tokens of the same user and device id, rate limit through `RedisCacheService.checkRateLimit` with the Admin number), `unregister(userId, deviceId)` (idempotent), `revokeForUser`, `revokeToken` (after FCM says invalid).
- [ ] `notification/api/DeviceTokenController`: `PUT` and `DELETE /api/v1/devices/push-token`, 204, request DTOs with validation; unknown platform or empty token answers `ERROR_INVALID_PUSH_TOKEN` through `UnprocessableException`; OpenAPI annotations.
- [ ] `notification/application/port`: `PushPort` (`send(PushMessage)` returning `PushResult`: `SENT`, `UNREGISTERED`, `INVALID`, `TRANSIENT`), `UserPresencePort` (`isOnline`).
- [ ] `notification/adapter`: `FcmPushAdapter` (`@ConditionalOnProperty` provider `fcm`; one `FirebaseMessaging` bean; builds the `notification` block, the `data` block (`eventType`, `deepLink`, `eventId`, `channel`), the Android `channelId` and priority, the APNs priority and the collapse key; maps `MessagingErrorCode` to `PushResult`), `NoopPushAdapter` (default; logs the count only). Add the `UserPresencePort` adapter in `realtime` (`PresenceAdapter` over `PresenceService`).
- [ ] `notification/application/service`: `PushPolicy` (the table of LLD B.5 in one place), `PushCopy` (English and Hindi, generic text), `PushChannelSender.send(...)` (policy, `NotificationPreferences`, online skip, active tokens with permission, payload in the token's locale, per-token send with three tries and a short backoff, revoke on `UNREGISTERED` or `INVALID`, metrics `push.sent{eventType}`, `push.failed{reason}`, `push.tokens.revoked`, `push.skipped{reason=online|no_token|permission}`; the token is never logged).
- [ ] `NotificationDispatcher`: when the channel set contains `PUSH`, register an after-commit action that hands the notification to `PushChannelSender` on a bounded executor (G6); when the set is only `PUSH` store no inbox row (calls); existing callers and tests keep their behaviour.
- [ ] `ChatMessageListener`: send the chat push for every message with the collapse key `chat:{threadId}` (G4, recommended option) in addition to the existing coalesced in-app notification; the push never fails the send.
- [ ] Token lifecycle on the account side: a listener on `UserStateChangedEvent` revokes all tokens of the user when the account is `CLOSED` (and, G10, when it stops being `ACTIVE`).
- [ ] `PushTokenCleanupJob` (daily, `@Scheduled`, style of `NotificationRetentionCleanupJob`): delete rows revoked more than the retention days ago and rows not seen for the stale days.
- [ ] Update `notification/package-info.java`.

### Mobile (`valuex-mobile`)
- [ ] `pubspec.yaml`: `firebase_core`, `firebase_messaging` (versions pinned when built).
- [ ] Android: Gradle `google-services` plugin applied **only when `google-services.json` exists** (G14), `POST_NOTIFICATIONS` in the manifest, a default notification channel meta-data; native Kotlin creates the channels `chat`, `offers`, `general` (default importance) and `calls` (high, with sound) at start, with names from `values` and `values-hi` string resources (G8). `google-services.json` and `GoogleService-Info.plist` are in `.gitignore`.
- [ ] iOS: `remote-notification` background mode, the Push Notifications capability (`aps-environment` entitlement) and foreground presentation options set to none (G9); document that it needs a real device and an APNs key in Firebase (G13).
- [ ] `core/push/install_id.dart`: a random install id kept in secure storage (G7).
- [ ] `core/push/push_service.dart`: `PushService` interface (`initialize`, `requestPermission`, `token`, `tokenChanges`, `permissionGranted`, `opened` tap stream, `initialMessage`) with `FirebasePushService` and `NoopPushService` (used when Firebase is not configured or in tests); initialisation errors are caught so the app starts without Firebase.
- [ ] `core/push/push_providers.dart`: `pushServiceProvider`, and `pushRegistrationProvider` (watched by `ValueXApp` like `realtimeConnectionProvider`): while the account is active, register after sign-in, on every token refresh and when the app language changes (G16); `PUT /devices/push-token` through a small `PushTokenRepository` (`ApiConstants.devicePushToken`).
- [ ] Sign-out: `SessionController.logOut` calls the `DELETE` before the session is cleared; a failure does not block sign-out (the server also revokes at account close).
- [ ] Permission timing: an explanation sheet then the system prompt the first time the user starts a chat (`ChatLauncher` / the Chat action of the listing page); the answer is remembered in preferences; a "no" registers the token with `permissionGranted: false`; Profile > Notifications gets a row that opens the system settings (`openAppSettings`). English and Hindi strings in `app_en.arb` and `app_hi.arb`.
- [ ] Deep links: `notification_deep_links.dart` maps `/chats/{id}` (pattern); a tap on a background notification and a cold start from a notification go through the existing `notification_navigation.dart` path (`onMessageOpenedApp`, `getInitialMessage`). Duplicate taps on the same `eventId` are ignored.
- [ ] Foreground: a push received while the app is open is not shown (G9).

### Infra (`valuex-infra`)
- [ ] `docs/push.md`: the FCM service account in the secret manager (role `firebase.messaging` only), env vars `PUSH_PROVIDER` and `FCM_SERVICE_ACCOUNT_JSON`, how CI injects `google-services.json` and `GoogleService-Info.plist`, the APNs key in Firebase, the per-environment Firebase projects, `dev-real.env.example` entries without values.

### Documents (at the end)
- [ ] Update LLD Part B with as-built notes (B.11) and the change log, `user-stories.md` and Sprint-plan status, the E.11 push rows, and write `Manual Testing Guides/US-131-Testing-Guide.md` (real Android 13+ and iOS devices, app killed, backgrounded, foreground; Hindi).

## 5. Test Plan

| Level | Cases | Covers |
|---|---|---|
| Unit | `PushPolicyTest`: every event type (channel set, Android channel, priority, skip when online, calls never skipped, unknown type sends nothing) | AC3, AC4 |
| Unit | `PushCopyTest`: English and Hindi for every event type; no text, amount or number can enter the copy (the builder takes none) | AC4 |
| Unit | `DeviceTokenServiceTest`: first register, refresh, move to another account, revoke older token of the same device, unknown platform and empty token (422), rate limit (429), unregister twice, `revokeForUser`, permission false is stored | AC1, AC2, AC6 |
| Unit | `PushChannelSenderTest`: online user skipped, two tokens both sent, permission false skipped, no token counted, `UNREGISTERED` and `INVALID` revoke, three tries then `push.failed`, a failing `PushPort` never throws, the token is not in the log output, `NotificationPreferences` false skips | AC3, AC5, AC6 |
| Unit | `FcmPushAdapterTest` with a mocked `FirebaseMessaging`: payload shape, error-code mapping, collapse key; `NoopPushAdapterTest` | B.4, AC5 |
| Unit | `NotificationDispatcherTest` additions: push after commit only, push-only set stores no row, dedupe sends no push, existing channel behaviour unchanged; `ChatMessageListenerTest` addition: a push per message with the collapse key and a failing push does not stop the in-app notification | AC3 |
| Unit | `PushTokenCleanupJobTest`; account-state listener test (closed and not-active revoke, active does not); `CommunicationSettingTest` for the three keys | AC2, AC10 |
| Controller | `DeviceTokenControllerTest`: 204 paths, 401, 422, 429, a token that belongs to another account moves | AC1 |
| Integration (Testcontainers PostgreSQL; run locally with the Docker workaround) | `V40` applies; register, refresh and move a token; sign-out `DELETE`; cleanup deletes the right rows; chat message creates a `PushPort` call for the recipient's tokens (no-op adapter spy) and none when the recipient has an open session | AC1 to AC3, AC10 |
| Mobile | `PushService` with a fake: permission sheet timing (first chat only, remembered, "no" registers `permissionGranted: false`), registration after sign-in, on token refresh and on language change, `DELETE` before sign-out and sign-out still works when it fails, no registration while the account is not active, duplicate tap ignored, foreground push not shown, app starts with the no-op service when Firebase is absent | AC1, AC2, AC6 to AC8 |
| Mobile | Deep link tests: `/chats/{id}` maps to the thread, unknown links do nothing, cold start and background tap route the same way | AC8 |
| Mobile widget | Explanation sheet and the Profile > Notifications row in English and Hindi, 320 px and 200 percent text, semantics | AC7 |
| Manual (real devices, not in CI) | Android 13+ and one iOS device, app killed, backgrounded and foreground; Hindi device language; two phones; sign-out; permission denied; FCM unreachable | AC3 to AC9 |

Target above 90 percent line coverage on new and changed code in both repos (CODING_STANDARDS 1.8). Local note: Testcontainers integration tests run with `JAVA_TOOL_OPTIONS='-Dapi.version=1.44 -Duser.timezone=UTC'`.

## 6. Validation Checklist

- [ ] AC1 to AC10 each have a passing test.
- [ ] A token is never logged, never returned by an API, and is revoked at sign-out and account close; a phone that signed out receives nothing.
- [ ] A token registered on a second account moves; older tokens of the same install id are revoked.
- [ ] A push holds no message text, offer amount or phone number, in English and Hindi.
- [ ] An online (foreground) recipient gets no push; a backgrounded or closed app does.
- [ ] `UNREGISTERED` and `INVALID_ARGUMENT` revoke the token; FCM being down changes nothing for the user who caused the event.
- [ ] A user who denied the permission is registered but never pushed.
- [ ] The permission is requested only after the explanation sheet and only on the first chat; nothing at launch.
- [ ] The app builds, starts and passes its tests without Firebase files; CI needs no secrets for unit tests.
- [ ] Android channels exist and are localised; iOS has the remote-notification mode.
- [ ] Every tunable push number is an Admin-managed `CommunicationSetting` with the LLD default.
- [ ] Checkstyle (120 characters, also in tests), SonarQube (quality gate, no new issues), `dart format` and `dart analyze --fatal-infos` clean; builds pass; coverage above 90 percent; only the one migration added.

## 7. Open Gaps / Questions

| ID | Gap | Proposal |
|---|---|---|
| G1 | US-131 is not in `user-stories.md` and `Sprint-plan.md` mentions it only in a note; the LLD has a story statement and edge cases but no acceptance criteria. | Approve the derived AC1 to AC10; the story is added to both documents as the first step (same as US-130 and US-132). |
| G2 | Resolved: backend #69 and mobile #78 (US-130) are merged. | Branches cut from current `main`; Flyway number is `V40` (V36 to V39 were taken by negotiation and Buy Now). |
| G3 | No Firebase project or credentials exist for this repository. Real push cannot be tested without them. | Code and automated tests run on the no-op adapter and a fake messaging plugin. **You (or infra) need to create a Firebase project per environment**, an FCM service account for the backend and the Android and iOS app registrations (plus an APNs key for iOS) before the manual device tests. |
| G4 | LLD E.5 says every chat message pushes (collapse key `chat:{threadId}`), but the in-app notification is coalesced to one per thread per `CHAT_NOTIFY_COALESCE_MINUTES`, and a repeated dedupe key sends nothing. | **Recommended:** push every message with the collapse key (the phone shows only the latest), the in-app notification stays coalesced. **Alternative:** one push per window like the in-app one (simpler, but a second message within 10 minutes would not ring). |
| G5 | LLD says retries use "the Resilience4j policy of 1.8", but only `resilience4j-circuitbreaker` is a dependency and `AiGatewayClient` has its own loop. | Three tries with a short backoff in `PushChannelSender`, same style as `AiGatewayClient`; no new library. A circuit breaker is not needed (one-way, best effort). |
| G6 | FCM is a network call and the dispatcher runs inside a transaction. | Hand the push to a bounded executor after commit (`TransactionSynchronization.afterCommit`); the 2-second target in B.9 is measured from commit. |
| G7 | The LLD assumes an install id already exists in secure storage; none exists. | Add `DeviceInstallId` (random UUID kept in secure storage, created on first use). |
| G8 | Android channels must exist before a push names them. The LLD says names are ARB strings, but native channel creation cannot read ARB files. | Create the channels natively in Kotlin at start, named from Android string resources in English and Hindi; no extra plugin. Alternative: `flutter_local_notifications` (a new dependency) with ARB names. |
| G9 | LLD B.7 says a foreground push is dropped when its `eventId` was already received over the socket, otherwise a banner is shown. Socket event ids and notification ids differ, so the match cannot work, and the server already skips push for an online user. | Never show a system push while the app is in the foreground (the socket and the notifications list cover it); `eventId` only prevents a double navigation on tap. |
| G10 | The LLD revokes tokens at sign-out and account close only. A suspended, restricted or banned account would still be pushed. | Also revoke tokens when the account stops being `ACTIVE`; the app registers again after the next successful active sign-in. |
| G11 | The 30 per hour limit and the cleanup ages (30 and 60 days) are constants in the LLD. | Make them Admin-managed `CommunicationSetting` keys with those defaults, like the chat and realtime numbers (screen in US-116). |
| G12 | Hindi push texts and the permission sheet copy are not in the LLD. | Draft English and Hindi in the PR; Hindi is reviewed together later (LLD O5). |
| G13 | iOS push cannot be tested in a simulator and needs a paid Apple developer account, the capability and an APNs key. | Implement and document; the iOS check is a manual real-device step in the testing guide. |
| G14 | The Android Gradle plugin and iOS build fail without Firebase files, which are not committed. | Apply the `google-services` plugin only when the file exists and make `FirebasePushService` initialisation optional, so developers and CI without the files still build and run (push is then off). |
| G15 | `NotificationPreferences.shouldSend` is always true until US-087. | The sender calls it for `PUSH` so the later story needs no change here. |
| G16 | The token stores the language at registration; a later language change would leave the push in the old language. | Register again when the app language changes (a small hook next to the token refresh). |

**Decided 2026-11-17 (user: "Agree" to every recommendation):** G4 push every chat message with the collapse key `chat:{threadId}`; G5 own three-try loop, no new library; G6 push after commit on a bounded executor; G7 new install id in secure storage; G8 native Kotlin channels with Android string resources; G9 never show a system push in the foreground; G10 also revoke tokens when the account stops being `ACTIVE`; G11 the three numbers are Admin-managed settings; G12 to G16 as proposed. **G3:** the product owner creates the Firebase projects and credentials (steps in `valuex-infra/docs/push.md`, written during the story); coding and tests do not wait for them.

**Update 2026-11-19 (user):** the Firebase project exists and the Android and iOS apps are registered. The Apple Developer account is not ready, so **iOS push is on hold: build it fully and leave it ready, not verified.** That means the iOS entitlement, background mode, `GoogleService-Info.plist` hook and foreground options are all written, `FcmPushAdapter` sets the APNs headers, and `docs/push.md` lists the APNs key upload as the one remaining step. The iOS real-device check stays unchecked in the testing guide. Android is the only platform verified end to end. The user told me to develop the feature on this basis, which I take as the go-ahead.

**Status: Approved** (2026-11-19, user: "develop the feature and keep ready")

## 8. As built (2026-11-19)

Built on `feature/US-131-push-notifications` (backend, mobile, infra) and `docs/US-131-push-notifications`. The detailed differences from the LLD are in LLD B.11; the ones that differ from this plan:

- **Offer pushes are included** (the plan left them for later): the events exist since US-017, so `NegotiationNotificationListener` adds `PUSH`. The policy also holds `OFFER_WITHDRAWN` and `NEGOTIATION_CANCELLED`.
- **No push-only dispatcher mode** for calls: calls are on hold, so it would be unused code.
- **Permission sheet** is shown when a conversation is first opened (covers the seller too), not from the chat launcher; offers do not ask on their own.
- **Registration on every app start** while the account is active, so `last_seen_at` stays fresh and the 60 day clean-up never removes a phone in use.
- **The app also deletes its Firebase token at sign-out and when the account stops being active**, so a session that ends without a chance to call the server still stops receiving.
- **`AccountStatePushListener` uses `REQUIRES_NEW`**: found by the integration test (a plain transaction after commit is not saved).
- **Migration is `V40`** (V36 to V39 were taken by negotiation and Buy Now), with an extra index on `revoked_at`.
- **Mobile `Profile > Notifications` shortcut** is a `PushOffBanner` on the Notifications page.
- **`FirebasePushService`** (platform glue, about 45 lines) has no unit test; everything around it uses a fake. The deprecated `getToken` is kept on purpose (see LLD B.11 row 16).

**Verification:** backend `mvn verify`: 3,252 tests, 0 failures; Sonar: no issue in this story's files, new-code coverage 94.3 percent; the gate shows ERROR only because of 4 issues in test files of earlier stories (US-076, US-018, US-017 tests), left alone. Mobile: 2,173 tests pass, the 2 known `google_accessibility_test` failures remain, coverage of the new files is 100 percent (except the Firebase glue), `dart analyze --fatal-infos` clean. **Not done:** a real push through Firebase, any iOS build.
