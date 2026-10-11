# US-101 - Google Sign-In: Manual Testing Guide

**Sprint 1 - Identity & User Management**

Test the Flutter app on Android and iOS, and the three public Google authentication endpoints. Record results separately for mock and native Google sign-in. Passing the mock tests does not verify Google OAuth integration.

## References

- [Sprint 1 LLD, section 4](../LLD/Sprint-1-Identity-User-Management-LLD.md#4-us-101-google-sign-in)
- [Sprint 1 combined testing guide](../Sprint-1-Combined-Testing-Guide.md#us-101--google-sign-in-optional-convenience-login)
- [User story US-101](../user-stories.md#us-101-google-sign-in-optional-convenience-login)
- [Google OAuth setup guide](../google-signin-guide.html)
- Mobile repository README: Google sign-in configuration and platform setup.

## Prerequisites

1. Use a mobile build containing US-101 and a backend containing the corresponding status, account-standing and optional-consent changes. Returning-user responses must include `status`.
2. Start PostgreSQL, Redis and the backend. Default backend base URL: `http://localhost:8080/api/v1`; Swagger: `http://localhost:8080/swagger-ui.html`.
3. For mock tests, use the backend's mock Google verifier (`GOOGLE_OAUTH_PROVIDER=mock`) and mock OTP delivery. Do not send OTPs to arbitrary real numbers.
4. From the mobile repository, launch the app using the matching dev configuration:

```bash
flutter devices
flutter run -d <android-device-id> --dart-define-from-file=config/dev_android.json
flutter run -d <ios-device-id> --dart-define-from-file=config/dev_ios.json
```

The Android dev URL uses `10.0.2.2` (Android emulator only); the iOS simulator uses `localhost`. A physical device needs the backend's LAN address in a local configuration file.

5. Ensure the app is signed out, complete or skip onboarding, and open **Create Account**. The Google entry point is **Continue with Google** there, not on the mobile-number **Sign In** screen.
6. Use dedicated test accounts. Prepare these fixtures through normal registration rather than setting incomplete accounts to `ACTIVE` in SQL:

| Fixture | Example mobile | Preparation |
|---|---|---|
| New Google user | `9111000001` | No account yet; choose mock name `us101new` |
| Existing mobile-only account | `9111000002` | Complete registration including Sign Up; status `ACTIVE`; no Google link |
| Incomplete registration | `9111000003` | Stop at email verification; status `EMAIL_VERIFICATION_PENDING` |

Use unused numbers and names if these already exist. Choosing a different Google name does not make an already-registered mobile number new.

## Mock Versus Native

| Mode | Mobile configuration | Backend configuration | What it verifies |
|---|---|---|---|
| Mock | `GOOGLE_SIGN_IN=mock` | `GOOGLE_OAUTH_PROVIDER=mock` | ValueX screens, API flow, OTP, linking, routing and errors |
| Native | `GOOGLE_SIGN_IN=native`, real client IDs | `GOOGLE_OAUTH_PROVIDER=http`, matching accepted client IDs | Real account chooser, callback, ID token validation and ValueX flow |

Mock mode opens a development-only account-name dialog. Names are lowercased and stripped to letters/digits; `us101new` sends `mock-us101new` and maps to `us101new@gmail.com`. The same name represents the same Google account.

**Important:** the literal API token `invalid` triggers `ERROR_INVALID_GOOGLE_TOKEN`. `mock-invalid` is accepted by the mock backend. Other non-mock strings are mapped to a generic mock user. Use native mode for expiry, signature, audience and verified-email validation tests.

## Expected Flows

| Flow | Expected result |
|---|---|
| New Google account, new mobile | Mobile number, SMS code, Aadhaar, then Sign Up; no email OTP step |
| Already-linked Google account | Immediate ValueX sign-in; route by server `status` |
| New Google account, existing `ACTIVE` mobile | Verify that mobile by OTP, link Google to the existing user, then Home |

After new-user mobile verification, status is `IDENTITY_VERIFICATION_PENDING`. Skipping or completing Aadhaar moves registration to Sign Up. Terms and consent are collected at Sign Up, not silently accepted during Google mobile verification.

## Mobile Test Cases

Run each case on both target platforms where applicable. Unless stated otherwise, use mock mode.

| ID | Scenario and steps | Expected result |
|---|---|---|
| MG-01 | On Create Account, tap Continue with Google; cancel the dialog | Development-only banner shown; cancellation leaves the app signed out and sends no Google authentication request |
| MG-02 | Choose unused name `us101new` | Add your mobile number screen shows the Google email; no ValueX tokens issued yet |
| MG-03 | On the mobile step submit a short number or one starting with `1` | Inline validation; no OTP request |
| MG-04 | Submit an unused valid number; read its latest OTP from the backend log; enter it | Code screen masks the number; success opens Aadhaar with `IDENTITY_VERIFICATION_PENDING`; no email OTP step |
| MG-05 | After MG-04, skip Aadhaar and complete Sign Up | Terms must be opened and consent explicitly accepted; Sign Up completes and opens Home |
| MG-06 | Reset only the local session; choose the same Google name | No mobile/code prompt; an `ACTIVE` account opens Home; an unfinished account resumes its server-defined registration step |
| MG-07 | Choose a new Google name and verify the mobile of the existing `ACTIVE` fixture | Home opens for the existing user ID; no duplicate user; a Google link is added |
| MG-08 | Choose a different Google name and submit the incomplete-registration fixture | Inline unfinished-registration message; no link created; use mobile OTP Sign In to finish that account |
| MG-09 | Try linking a second Google name to an account that already has Google linked | Inline already-linked message; original link remains unchanged |
| MG-10 | Enter a wrong six-digit OTP | Invalid or expired OTP inline; no account or link created; code screen remains |
| MG-11 | Wait more than 5 minutes after sending the OTP, then verify | Expired OTP error; after cooldown Resend requests another code and restarts the timer |
| MG-12 | Resend after the 30-second cooldown, then verify with the latest code | One resend request; countdown resets; latest code completes the flow |
| MG-13 | Tap Change number on the code screen | Returns to the Google mobile step; send a code for the new number and complete it; never verify using the previous number's code |
| MG-14 | Wait over 10 minutes after the last successful social-session creation or OTP-send request, then send/verify | Google-session-expired message; go back to Create Account and restart Google sign-in |
| MG-15 | On a linked fixture, set status to `SUSPENDED`; reset local session and choose its Google name | Suspension message under Google button; no tokens or new session issued; app remains signed out |
| MG-16 | Repeat MG-15 with `BANNED` and `CLOSED` | Recovery-required message; no tokens; restore the fixture's original status afterwards |
| MG-17 | Disconnect network before confirming the chooser, then restore it and try again | Visible connection failure, no false success; retry can complete sign-in |
| MG-18 | Double-tap Continue with Google / Send OTP / Verify | No duplicate account or link; repeated submissions do not produce parallel successful operations |
| MG-19 | Kill and reopen the app during Google mobile verification | Pending social session is not restored from local storage; user must restart Google sign-in |
| MG-20 | Open `/google/mobile` or `/google/verify` without a pending social session | Returns to Create Account; no crash or usable verification form |
| MG-21 | Hindi, maximum text size, small viewport, keyboard open | Fields, errors and actions remain visible or scrollable; no clipping/overlap; record native-speaker review separately |
| MG-22 | VoiceOver / TalkBack: navigate chooser, mobile form and code form, including errors | Named controls, announced errors, sensible focus order and usable touch targets |

For OTP-limit checks, use a dedicated mobile: the backend shares send and failure buckets with registration and mobile login. The app limits sends to three and uses a 30-second resend cooldown. Test backend enforcement separately through Swagger; an app-disabled button is not proof of backend enforcement.

### Reading the Development OTP

Use the latest log entry for the exact test mobile, not the last OTP for any account:

```text
[DEV-MOCK] OTP ... mobile=<test-mobile> ... otp=<six-digit-code>
```

Do not include OTPs, Google ID tokens, social session tokens or ValueX tokens in screenshots, shared logs or defect reports.

## Backend API Checks

All three endpoints are public. Remove Swagger's Bearer authorization for these calls. Tokens are passed in JSON, not query parameters.

### API-01: Start Google Sign-In

`POST /auth/social/google`

```json
{ "idToken": "mock-us101new" }
```

For an unlinked Google account, expect `200` and:

```json
{
  "success": true,
  "data": {
    "requiresMobileVerification": true,
    "socialSessionToken": "<temporary-session>",
    "googleEmail": "us101new@gmail.com"
  }
}
```

For an already-linked Google account, expect `requiresMobileVerification=false`, `accessToken`, `refreshToken`, `userId`, `aadhaarVerified` and `status`. Confirm the status matches the database, including unfinished registration. Token issuance must be rejected for blocked accounts.

### API-02: Send Mobile OTP Without Consent Flags

`POST /auth/social/google/initiate-mobile`

```json
{ "socialSessionToken": "<temporary-session>", "mobile": "9111000001" }
```

Expect `200`, an OTP-sent message and `otpExpiresInSeconds=300`. Omitted consent flags must be accepted. Explicit `termsAccepted=false` or `consentGiven=false` must still be rejected.

### API-03: Verify Mobile

`POST /auth/social/google/verify-mobile`

```json
{
  "socialSessionToken": "<temporary-session>",
  "mobile": "9111000001",
  "otp": "<latest-code-for-this-mobile>"
}
```

Expect `200`, a token pair, user ID, `aadhaarVerified` and `status`. A new user has verified Google email and status `IDENTITY_VERIFICATION_PENDING`; an existing `ACTIVE` user keeps the same ID and status. The pending social session is consumed.

### API Negative Tests

| ID | Request/change | Expected |
|---|---|---|
| API-04 | Start with `idToken=invalid` | `400 ERROR_INVALID_GOOGLE_TOKEN` |
| API-05 | Missing/blank ID token, social session token, mobile or OTP | `400` validation error for the required field |
| API-06 | Unknown/expired social session token | `400 ERROR_SOCIAL_SESSION_EXPIRED` |
| API-07 | Verify a session before initiate-mobile | `400 ERROR_SOCIAL_SESSION_INVALID` |
| API-08 | Verify with a different mobile from initiate-mobile | `400 ERROR_MOBILE_MISMATCH` |
| API-09 | Wrong OTP / expired OTP | `400 ERROR_INVALID_OTP` / `ERROR_OTP_EXPIRED` |
| API-10 | Fourth send within 10 minutes | `400 ERROR_OTP_RATE_LIMIT` |
| API-11 | Exceed five verification attempts within 10 minutes | `400 ERROR_OTP_MAX_ATTEMPTS`; obtain a fresh session/code for subsequent tests |
| API-12 | Explicit refusal of terms or consent | `400 ERROR_TERMS_NOT_ACCEPTED` / `ERROR_CONSENT_REQUIRED` |
| API-13 | Link an unlinked Google identity to a non-`ACTIVE` mobile | Incomplete/restricted/suspended states currently return `ERROR_INVALID_STATE`; `BANNED`/`CLOSED` return `ERROR_ACCOUNT_RECOVERY_REQUIRED` |
| API-14 | Start with an already-linked Google identity whose user is suspended/banned/closed | `ERROR_ACCOUNT_SUSPENDED` / `ERROR_ACCOUNT_RECOVERY_REQUIRED`; no token pair |

## Database Evidence

Read-only queries for a dedicated fixture:

```sql
SELECT id, mobile, email, email_verified, status,
       terms_accepted_at, consent_given_at
FROM users WHERE mobile = '9111000001';

SELECT provider, provider_user_id, provider_email, user_id
FROM user_social_accounts
WHERE user_id IN (SELECT id FROM users WHERE mobile = '9111000001');
```

Before Sign Up, a new Google user must have both consent timestamps null. After completing Sign Up they must be populated. Existing accounts keep their previously recorded consent. Linking must not create a second user or silently replace the existing account's profile/email.

For blocked-account tests, save the original state first, mutate only a dedicated fixture, and restore it:

```sql
UPDATE users SET status = 'SUSPENDED' WHERE mobile = '9111000001';
-- After testing, restore the status recorded before the change.
UPDATE users SET status = 'IDENTITY_VERIFICATION_PENDING' WHERE mobile = '9111000001';
```

## Native Google Tests

These are blocked until real OAuth clients are configured. Never test real-token security against the mock backend.

1. Create a Web OAuth client; set its ID as mobile `GOOGLE_SERVER_CLIENT_ID` and include it in backend `GOOGLE_CLIENT_ID_WEB`.
2. Create an Android client for `com.valuex.valuex_mobile`, registering the SHA-1 for each tested signing key. A debug client does not prove the release signing setup works.
3. Create an iOS client for `com.valuex.valuexMobile`; set `GOOGLE_IOS_CLIENT_ID` and its reversed URL scheme in `ios/Runner/Info.plist`.
4. Use mobile `GOOGLE_SIGN_IN=native` and backend `GOOGLE_OAUTH_PROVIDER=http`. Configure the accepted client IDs. Client IDs are public configuration; never put client secrets in the app.

| ID | Native scenario | Expected |
|---|---|---|
| NG-01 | Tap Continue with Google on Android and iOS | Real account chooser appears; no development mock dialog |
| NG-02 | Cancel Google authentication | Remains signed out, no backend sign-in request or failure message |
| NG-03 | Choose an unlinked Google account | App returns from Google and follows the mobile verification flow |
| NG-04 | Choose an already-linked account | No mobile OTP; server status determines destination |
| NG-05 | Choose another Google account on a later attempt | Selected account's identity is used; no accidental reuse of the earlier account |
| NG-06 | Submit expired/tampered/wrong-audience ID tokens directly to the HTTP verifier | Authentication rejected; no ValueX session issued |
| NG-07 | Repeat NG-01 to NG-04 with release-signed Android and iOS builds | Native callbacks and server validation work with release configuration |
| NG-08 | Google unavailable or native configuration invalid | Visible unavailable/failure message; no ValueX session issued |
| NG-09 | Remove Google authorization and try signing in again | Record actual reauthorization behaviour; removing Google authorization must not be mistaken for revoking an already-issued ValueX session |

## Reset and Known Limitations

- There is no logout UI in this iteration. To repeat returning-user tests, use the same backend fixture and the debug-only `CLEAR_LOCAL_SESSION` flag in Appendix A.10. It clears only ValueX's login entries, preserving root certificates and other Keychain data.
- Do not delete shared users, flush Redis or clear unrelated Keychain data. Prefer fresh dedicated fixtures. Preserve user IDs and original statuses for cleanup through approved test-data procedures.
- Social-session TTL is 10 minutes; successful initiate-mobile resets it. OTP TTL is 5 minutes. Resending invalidates the earlier code.
- Mock/native mode does not prevent backend linking races or account-state changes between sending and verifying OTP. Test those as security edge cases; report any blocked account being issued usable tokens, rather than accepting it as intended behaviour.
- Native Google authentication and device screen-reader tests are not verified by host widget tests. Record them as not run until performed.
- Google on iOS requires an App Store guideline 4.8 equivalent-login assessment before release. This implementation alone is not evidence of store compliance.
- Restore any shortened TTLs after testing. Do not disable Flyway or schema validation to claim a normal deployment test passed; record startup/migration blockers separately.

## Result Record

| Field | Record |
|---|---|
| Mobile/backend commit or build | |
| Platform, OS and device | |
| Mock or native; debug or release | |
| Test ID and fixture | |
| Pass / fail / blocked / not run | |
| Actual result and sanitized evidence | |
| Defect reference and cleanup completed | |

Complete all applicable mobile and API cases, plus native cases on both platforms before declaring real Google sign-in verified.

## Appendix A - Native Google Sign-In Setup and End-to-End Testing

### A.1 What You Need

- Access to a Google Cloud project where you can configure OAuth clients and the consent screen.
- Two dedicated real Google test accounts, for example Google account A and Google account B.
- Android Studio, JDK 17, and a physical Android device or emulator with Google Play services and a Google account added. A plain AOSP emulator without Google services is not suitable.
- On macOS: Xcode, CocoaPods and an iOS simulator or physical device. A physical device requires an appropriate Apple signing team.
- PostgreSQL, Redis and the ValueX backend with the US-101 changes. Resolve migration blockers before claiming a normal startup passed.
- A new mobile fixture and an existing `ACTIVE` mobile-only fixture with no Google link. Use mock SMS delivery for local testing, not arbitrary real recipients.

This project authenticates through Google and then the ValueX backend. It does not use Firebase Authentication. Do not add Firebase packages, a Google Services Gradle plugin or Firebase configuration files solely for this setup: the app passes OAuth client IDs directly to `google_sign_in`.

### A.2 Create the Google Cloud Project and Consent Configuration

1. Open [Google Cloud Console](https://console.cloud.google.com/) and select or create the project that will own ValueX's OAuth clients. Keep the Web, Android and iOS clients in the same project.
2. Open **Google Auth Platform** (or **APIs & Services > OAuth consent screen**, depending on the console interface).
3. Configure **Branding**: app name, support email and developer contact email. For public distribution, supply the required homepage/privacy-policy information and verify domains where requested. Do not invent a domain for local testing.
4. Under **Audience**, choose **External** for consumer Google accounts. Choose Internal only for a Workspace-only application. Keep External in Testing for initial QA.
5. Add Google accounts A and B as test users if the console's audience configuration requires test users. Only permitted users should be used for these tests.
6. Review **Data Access**. This feature needs sign-in identity (OpenID, email and basic profile), not Drive, Contacts or other sensitive data. Do not request unrelated scopes or enable unrelated APIs.
7. Save the configuration. Production publication and any Google verification requirements are separate release tasks; a working test-user sign-in does not complete them.

The provider might show an account chooser or a previously-authorized flow rather than a fresh consent screen every time. Do not fail a test solely because Google did not display the same consent UI on a subsequent login.

### A.3 Create the Web OAuth Client (Required on Both Platforms)

1. Open **Clients > Create client** (or **Credentials > Create credentials > OAuth client ID**).
2. Select **Web application**, name it `ValueX Native Backend`, and create it.
3. Copy its **client ID**, which ends in `.apps.googleusercontent.com`.
4. Use this exact ID as mobile `GOOGLE_SERVER_CLIENT_ID` and backend `GOOGLE_CLIENT_ID_WEB`.

For this native ID-token exchange, the app does not use a browser redirect to the backend. No localhost redirect URI or JavaScript origin is required for this flow. Do not confuse this Web client with a future Flutter Web login integration.

Google may also display a client secret. This implementation does not use it. Never put a client secret, Google password, ID token or ValueX token in the app, a config JSON committed to Git, or a shared test report. OAuth client IDs themselves are public configuration.

### A.4 Register Android Package and Signing Certificates

The current Android application ID is `com.valuex.valuex_mobile`. Verify it in `android/app/build.gradle.kts`; use the actual application ID if a build flavor or suffix changes it.

From `valuex-mobile`, get the certificates used by your builds:

```bash
cd android
./gradlew signingReport
cd ..
```

Find the **debug** variant's `SHA1` and store path. A fallback for the standard local debug key is:

```bash
keytool -list -v \
  -keystore "$HOME/.android/debug.keystore" \
  -alias androiddebugkey
```

Use the keystore's password directly in the terminal if prompted. Do not send it through chat. Prefer the signing report because a custom signing configuration can use a different key.

1. In Google Cloud, create an OAuth client of type **Android**.
2. Enter package name `com.valuex.valuex_mobile` and the debug certificate's SHA-1 exactly.
3. Name it clearly, for example `ValueX Android - Local Debug`, and save its client ID for backend configuration/inventory.
4. Each developer or CI signing key can have a different SHA-1. Register each package/certificate pair that actually needs native authentication.
5. For a directly installed release APK, register the actual release signing certificate in an additional Android OAuth client.
6. For Google Play distribution, use the **App signing certificate** SHA-1 shown under Play Console's App Integrity / App Signing page. Play signs installed builds with that key, which may differ from your upload key.

The current repository still signs release builds with the debug key. A release-mode build using that key does not verify production signing. Configure real release signing separately before testing a distributable build.

Do not set the Android client ID as `GOOGLE_SERVER_CLIENT_ID`; that setting must remain the Web client ID. This app does not expose a `GOOGLE_ANDROID_CLIENT_ID` Dart setting: Android identity is matched using package name and signing certificate.

### A.5 Register iOS Client and Callback URL Scheme

1. In Google Cloud, create an OAuth client of type **iOS**.
2. Enter bundle ID `com.valuex.valuexMobile` (capitalization differs from the Android ID). Verify the actual Runner bundle ID in Xcode before creating it.
3. Copy the iOS client ID and set mobile `GOOGLE_IOS_CLIENT_ID` to it.
4. Copy the reversed client ID / iOS URL scheme displayed by Google. For example:

```text
iOS client ID:    1234567890-abcdef.apps.googleusercontent.com
Callback scheme: com.googleusercontent.apps.1234567890-abcdef
```

Add this entry **inside the existing top-level `<dict>`** in `ios/Runner/Info.plist`, using your real reversed iOS ID, not the example:

```xml
<key>CFBundleURLTypes</key>
<array>
    <dict>
        <key>CFBundleTypeRole</key>
        <string>Editor</string>
        <key>CFBundleURLSchemes</key>
        <array>
            <string>com.googleusercontent.apps.YOUR_REVERSED_IOS_CLIENT_ID</string>
        </array>
    </dict>
</array>
```

If `CFBundleURLTypes` already exists, add a dictionary to its array; do not duplicate the key or replace other callback schemes. The callback uses the **iOS** client, not the Web client.

The current app passes `clientId` and `serverClientId` from Dart configuration. Therefore `GIDClientID` and `GIDServerClientID` plist keys are not additionally required when those settings are supplied. The URL scheme is still mandatory. No manual AppDelegate callback implementation is required by this setup.

Validate the plist after editing:

```bash
plutil -lint ios/Runner/Info.plist
```

The plist is checked into Git; review and commit intended callback configuration separately. Never place a client secret in it.

### A.6 Create a Local Native Mobile Configuration

Use `config/dev_local.json`, which is already ignored by Git. Create/edit it locally and replace every example value with your actual IDs:

```json
{
  "ENV": "dev",
  "API_BASE_URL": "http://localhost:8080/api/v1",
  "AADHAAR_FLOW": "sandbox",
  "GOOGLE_SIGN_IN": "native",
  "GOOGLE_SERVER_CLIENT_ID": "YOUR_WEB_CLIENT_ID.apps.googleusercontent.com",
  "GOOGLE_IOS_CLIENT_ID": "YOUR_IOS_CLIENT_ID.apps.googleusercontent.com"
}
```

Select the API URL for the device being tested:

| Target | Backend URL on the development machine |
|---|---|
| iOS simulator | `http://localhost:8080/api/v1` |
| Android emulator | `http://10.0.2.2:8080/api/v1` |
| Physical Android/iOS device | `http://<development-machine-LAN-IP>:8080/api/v1` |

For physical devices, use the same reachable network, permit port 8080 through the development firewall, and allow local-network access on iOS if requested. HTTP is for development only; release environments must use HTTPS and appropriate platform transport settings.

Use a full app restart after changing Dart defines. Hot reload cannot change compile-time configuration. The checked-in dev files still specify mock mode: passing `config/dev_ios.json` would continue to show the mock chooser.

### A.7 Start the Backend with Real Google Verification

Start PostgreSQL and Redis with the settings in the backend README. On macOS, in a separate terminal:

```bash
cd valuex-backend
export JAVA_HOME=/opt/homebrew/opt/openjdk@21
export GOOGLE_OAUTH_PROVIDER=http
export GOOGLE_CLIENT_ID_WEB='YOUR_WEB_CLIENT_ID.apps.googleusercontent.com'
export GOOGLE_CLIENT_ID_ANDROID='YOUR_ANDROID_CLIENT_ID.apps.googleusercontent.com'
export GOOGLE_CLIENT_ID_IOS='YOUR_IOS_CLIENT_ID.apps.googleusercontent.com'

~/tools/apache-maven-3.9.9/bin/mvn spring-boot:run \
  -Dspring-boot.run.arguments=--spring.profiles.active=dev
```

Adjust JDK/Maven paths to your installation. If your network requires the macOS trust-store options used for this repository, retain those local `MAVEN_OPTS` as described in the backend setup; do not weaken TLS certificate verification.

The backend must have outbound HTTPS access to `oauth2.googleapis.com`. It currently verifies ID tokens using Google's `tokeninfo` endpoint and then checks the audience against its configured client-ID list and requires verified email. The native client requests the Web audience, so the Web ID must exactly match on both sides.

Confirm startup succeeded and open `http://localhost:8080/swagger-ui.html`. Do not use a pre-existing backend process without checking its provider configuration. If the backend has duplicate migrations or schema errors, resolve them or record the environment as blocked; disabling Flyway/schema checks does not establish normal deployment readiness.

Keep Google verification **HTTP** while OTP delivery stays **mock** for local QA. Real Google identity and real SMS delivery are independent concerns. Read the OTP for the exact test mobile from the backend terminal; never paste it or tokens into shared reports.

### A.8 Build and Launch Native Authentication

From `valuex-mobile`:

```bash
flutter pub get
flutter devices

# iOS simulator; dev_local.json must use localhost.
flutter run -d 34A402DC-E0C8-41D2-AD0A-E635F79BC8FE \
  --dart-define-from-file=config/dev_local.json

# Android; change dev_local.json to the emulator or physical-device URL first.
flutter run -d <android-device-id> \
  --dart-define-from-file=config/dev_local.json
```

Use the actual simulator ID if yours differs. If CocoaPods dependencies need installation, run `cd ios && pod install && cd ..`. Native plist/configuration edits need a rebuilt app, not just hot reload.

On Create Account, tap **Continue with Google**. A real Google account chooser / authentication sheet must appear, and the development mock-name dialog must not appear. Cancel once: the app should stay signed out. Then retry and select test Google account A.

### A.9 End-to-End Acceptance Walkthrough

**Test 1: Real Google account A + unused mobile (new-user flow)**

1. Ensure Google account A has no entry in `user_social_accounts` and use an unused dedicated mobile number.
2. Start signed out, choose Continue with Google, and select account A. Complete any Google prompts.
3. Expect return to ValueX's mobile step showing account A's email. There should be no ValueX access/refresh tokens yet.
4. Enter the dedicated mobile, tap Send OTP, and enter its latest mock SMS code from the backend log.
5. Expect Aadhaar, not email verification. Confirm database `email_verified=true`, `status=IDENTITY_VERIFICATION_PENDING`, and a `GOOGLE` link to this user.
6. Confirm both consent timestamps are null before Sign Up. Skip or complete Aadhaar, complete Sign Up and explicitly accept terms/consent.
7. Expect Home with `ACTIVE` status and populated consent timestamps. Record this fixture's user ID for later tests.

**Test 2: Account A returns without mobile OTP**

1. Clear only the local ValueX session using the reset guidance below; preserve the backend user and Google link.
2. Continue with Google and choose account A again.
3. Expect Home with no mobile/code step and the same ValueX user ID. If the fixture is intentionally incomplete, expect its current registration step instead.
4. Restart the app and confirm the normal persisted-session restore works. Removing Google authorization is not equivalent to logging out of ValueX.

**Test 3: Account B + existing active mobile-only account (link flow)**

1. Pick account B that is not linked anywhere in ValueX.
2. Verify the target mobile is `ACTIVE` and has **no Google link**. Use the read-only fixture query below.
3. Choose account B, enter that mobile and verify its OTP.
4. Expect Home for the original user ID; no duplicate user. The new link identifies account B. The original profile/contact email must not be silently overwritten.
5. Clear local session and choose B again: expect immediate sign-in for that same user.

```sql
SELECT u.id, u.mobile, u.status, s.provider_user_id
FROM users u
LEFT JOIN user_social_accounts s
  ON s.user_id = u.id AND s.provider = 'GOOGLE'
WHERE u.mobile = 'YOUR_TEST_MOBILE';
```

If `provider_user_id` is already populated, this is not a mobile-only linking fixture. The current design allows one Google identity per ValueX account. A different Google account targeting that mobile must be rejected; the current already-linked message is ambiguous about which side already has the link.

**Test 4: Refused linking and refused returning login**

1. With a fresh unlinked Google account, submit an incomplete-registration mobile. Expect the unfinished-registration message, not a new account or link.
2. Try a different Google account against the already-linked active mobile. Expect already-linked rejection; verify the original link remains.
3. For a dedicated already-linked fixture, save its status and set it to `SUSPENDED`. Clear local session and choose its Google account. Expect refusal and no new ValueX session.
4. Repeat with `BANNED`/`CLOSED`, then restore the original status. Use the SQL and safety guidance earlier in this guide.

**Test 5: Native cancellation, wrong OTP and expiry**

1. Cancel the native chooser before selecting an account. No Google backend sign-in request should be sent.
2. Start a new-user flow and submit a wrong OTP. Expect an inline error, no account/link creation, and a usable retry path.
3. Wait over 5 minutes after send to test expired OTP. Resend after cooldown and use the latest code.
4. Wait over 10 minutes after the last successful social-session creation/initiate request to test social-session expiry. Restart Google sign-in when prompted.
5. Turn off connectivity before authentication or the backend exchange. Record the visible failure and successful recovery after reconnecting.

### A.10 Reset Between Native Test Cases

Clearing local login does **not** delete the Google-to-ValueX link. Preserve it for returning-login tests; choose a different unlinked Google account and a suitable mobile fixture for linking tests.

For a dedicated Android emulator, this command clears **all local ValueX app data**, including login, onboarding and preferences, but not other apps or backend data:

```bash
adb -s <android-device-serial> shell am force-stop com.valuex.valuex_mobile
adb -s <android-device-serial> shell pm clear com.valuex.valuex_mobile
```

Then reopen ValueX and skip onboarding. Do not run this on a device where ValueX local data must be preserved.

For iPhone 17, use the debug-only local logout flag from `valuex-mobile`:

```bash
flutter run -d 34A402DC-E0C8-41D2-AD0A-E635F79BC8FE \
  --dart-define-from-file=config/dev_local.json \
  --dart-define=CLEAR_LOCAL_SESSION=true
```

This deletes only ValueX's access token, refresh token and user ID at startup. It preserves onboarding/preferences, the Zscaler root certificate and other apps' credentials. The flag is ignored outside debug builds. Omit it for normal launches; a build with the flag continues to clear login on every start or hot restart.

There is no mobile logout UI in this iteration. Local clearing does not revoke backend sessions or delete Google links. Backend `POST /auth/logout` revokes the ValueX session but does not by itself clear app-local storage; use it when intentionally testing server-session revocation. Do not reset the whole simulator Keychain for ordinary login testing.

### A.11 Troubleshooting

| Symptom | Check / next step |
|---|---|
| Mock account-name dialog still appears | Launch defines still set `GOOGLE_SIGN_IN=mock`; use the local native file and restart fully |
| Missing server client ID at startup | Supply the actual Web OAuth ID as `GOOGLE_SERVER_CLIENT_ID` |
| Android closes chooser after selecting an account, with no sign-in | Verify package/SHA-1/Web client ID first; the Android credential SDK can report configuration failures as cancellation |
| Android debug works but release/Play build fails | Register the actual installed build's signing certificate, including Play app-signing SHA-1 where applicable |
| iOS never returns to ValueX or fails native authentication | Check exact iOS client/bundle ID and reversed URL scheme; validate plist and rebuild |
| Google says access is blocked | Check audience, test users, project policy and consent configuration; use a permitted test account |
| Backend returns `ERROR_INVALID_GOOGLE_TOKEN` for genuine Google login | Confirm backend HTTP provider, matching Web audience, verified email, token freshness and outbound HTTPS |
| Backend cannot reach Google | The current adapter also maps HTTP/network failures to `ERROR_INVALID_GOOGLE_TOKEN`; do not assume every such code means an invalid token |
| Native works but mobile OTP/linking fails | Check Redis, fixture status, existing Google link, correct OTP mobile and TTL; native OAuth success does not prove ValueX linking passed |
| App opens Home directly | Local ValueX tokens remain; reset the local session before testing the Google entry point |
| iOS debugger says it lost connection | Reopen the app and check whether it is running; debugger disconnection alone does not prove authentication failed |

When debugging server token validation, do not enable full request/URL logging. The current HTTP adapter sends the ID token to Google's `tokeninfo` endpoint in a URL, and transport exception messages can contain that URL. Treat raw logs as sensitive, sanitize them before sharing, and record any token exposure as a security issue.

### A.12 Security and Release Verification

- Run NG-06 against the HTTP verifier with an authorized test harness that obtains genuine test ID tokens. Test expiry, tampering and an audience from an unrelated project not present in the allowlist. Do not paste tokens into chat or reports, or put them in command history. These checks are blocked if no secure token-capture/test harness is available; the app deliberately does not log ID tokens.
- Token payload decoding alone is not signature validation. Record backend rejection and absence of a new ValueX session as the security evidence.
- Requesting a new Google token does not invalidate a previous ValueX JWT; test ValueX refresh/logout independently with US-107/US-104.
- Repeat native login on release-signed Android and iOS builds. iOS simulator success does not verify physical-device signing or App Store review readiness.
- Resolve Apple guideline 4.8's equivalent-login requirement before iOS publication; update privacy disclosures for the Google email/profile identity actually collected.
- Record platform, signing certificate/client configuration (IDs may be recorded), commit/build, test IDs, sanitized results and cleanup in the Result Record above. Do not mark native integration complete while either platform or release configuration remains untested.