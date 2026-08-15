# Low Level Design - Sprint 1: Identity & User Management

**Document Version:** 1.10
**Product:** ValueX
**Sprint:** Sprint 1 - Identity & User Management
**Sprint Duration:** 2 Weeks
**Date:** August 2026

**Change Log:**

| Version | Date | Change |
|---|---|---|
| 1.1 | Jul 2026 | Initial design |
| 1.2 | Aug 2026 | Updated to reflect actual implementation: email verification step added to US-001 flow; US-101 port/adapter architecture revised (GoogleTokenPort, MockGoogleTokenAdapter, multi-client-ID config); two new Google endpoints added (initiate-mobile, verify-mobile); Google link-to-existing-account flow documented; email_verified security check added; skip-aadhaar return type corrected; package structure corrected; JWT claims corrected; US-102 Apple Sign-In dropped |
| 1.3 | Aug 2026 | Added US-103 (Profile Hub / Account Menu Navigation), US-104 (Account Logout), US-105 (Account Security Settings) — gaps identified when auditing US-003 against user-stories.md v3.2. Introduces session tracking (`jti` claim + `user_sessions` table + Redis blocklist) as shared infrastructure for US-104/US-105. Design only — not yet implemented. |
| 1.4 | Aug 2026 | US-003 redesigned: avatar selection (fixed catalog, `avatar_id`) replaces free-form profile photo upload — removes `StoragePort`/S3 pipeline and image content-moderation dependency entirely. `users.profile_photo_url` (V2) superseded by `users.avatar_id` (V6). Future `user_sessions`/`contact_change_attempts` migration renumbered V6→V7 accordingly. Reflects actual implementation of US-003. |
| 1.5 | Aug 2026 | US-103 implemented: `ProfileMenuBadgeProvider` SPI, `ProfileMenuService`, `GET /api/v1/users/me/menu-summary` on the existing `UserProfileController`. Zero badge providers registered (confirmed no notification persistence exists yet — `com.valuex.notification` is still Sprint-0 scaffolding, US-077 not built) — extensibility proven by test (empty list + multi-provider aggregation), not by the LLD's example `NotificationsBadgeProvider`, which is deferred to whenever US-077 lands. `ProfileMenuSummaryResponse` implemented as `@Data @Builder class` (§8.4), not the originally-sketched `record`, to match every sibling DTO. |
| 1.6 | Aug 2026 | US-103 PR review + AC audit: `ProfileMenuService` hardened — constructor-time duplicate-`menuKey` validation (fail fast, not a live-request crash), per-provider failure/negative-count isolation (log + omit, doesn't break the whole response), `badges` map returned unmodifiable, `ProfileMenuBadgeProvider` SPI fully documented, plus a narrow Docker-free Spring-context test proving `List<ProfileMenuBadgeProvider>` autowiring actually works. Separately, an AC audit found `memberSince` ("joined date") was missing from the summary response despite being in the AC text — added. `rating` and a seller `hasActiveListings` signal remain genuinely unavailable (Ratings and Listings aren't built yet) — not fixable until those stories land. |
| 1.7 | Aug 2026 | Full doc-vs-code audit (not just the avatar change): §8.2's `ProfileMenuService`/`ProfileMenuBadgeProvider` snippets were stale (still showed `@RequiredArgsConstructor`, no constructor validation, no per-provider isolation) — rewritten to match real source, with the review-added behaviors called out explicitly instead of silently baked in. §16.4 JWT Claims (numbered §15.4 at the time) presented the design-only `jti` claim as if implemented — it is not; the real `JwtTokenProvider` has no `jti` claim, flagged clearly. §17.1's "ProfileMenuService Tests" list had three invented method names that don't match what was actually written — replaced with real method names for every US-003/US-103 test class, plus the previously-undocumented `ProfileMenuServiceWiringIntegrationTest`. §17.2's `UserRegistrationIntegrationTest` was always fictional (never built) — now labeled as such. §15.4/15.6/15.7 (Notifications/Logout/Account Security endpoints) now explicitly flagged "not implemented" rather than reading as live. Implementation Sequence table gained a Status column, corrected two stale class names (§3, §10: `SocialLoginPort`/`GoogleSocialLoginAdapter` → `GoogleTokenPort`/`GoogleSignInService`, a v1.2 rename this table never picked up), marked Apple as dropped, and added the PR-review hardening as its own row (19a). §1.3 Exit Criteria checkboxes now reflect actual status instead of being uniformly unchecked. |
| 1.8 | Aug 2026 | US-106 (Mobile OTP Login for Returning Users) implemented and documented: new §13 covers the login flow, the 10-state login-eligibility table, `UserLoginService` (reuses the long-dormant `OtpPurpose.LOGIN`, reuses the existing `ERROR_INVALID_STATE` convention rather than inventing a new error code — same pattern as `GoogleSignInService.initiateMobileForSocialLink`), and what login deliberately never touches (no state transition, no `User` row writes, no session/audit infrastructure — none of that exists yet). Old §13-16 renumbered to §14-17 (Database Schema, API Design, Security Considerations, Testing Strategy) to make room. §15.1 gained the two new `/auth/login/*` endpoint specs, §16.5 gained their rate-limit rows, §17.1 gained real `UserLoginServiceTest`/`AuthControllerTest` method names, §2.4 Package Structure updated with the new DTO/service classes, and Implementation Sequence gained row 23. |
| 1.9 | Aug 2026 | US-106 AC audit found a real gap: neither the JWT nor `AuthResponse` ever returned the account's `status`, so the client had no way to satisfy the AC's "route to the appropriate screen for my account's current state" without an extra API call. Fixed by adding `status` to `AuthResponse` — populated in all five places it's built (`UserLoginService.verifyLogin`, `UserRegistrationService.verifyMobileOtp`/`.skipAadhaar`, `AadhaarVerificationService.completeVerification`, `GoogleSignInService.verifySocialMobileOtp`), so registration, login, Aadhaar, and Google sign-in all return it consistently, not just login. All affected JSON response examples in §15.1/§15.2 and the flow diagrams in §3.1/§4/§13.2/§13.4 updated to show it. `SocialSignInResponse` (Google Flow B, already-linked immediate JWT) is a separate DTO and was not touched — out of scope of this fix. Also fixed two Sonar `S5778` code smells in `ProfileMenuServiceTest` (lambdas with multiple throw-possible invocations) found during the first Sonar scan of the US-106 branch. |
| 1.10 | Aug 2026 | US-107 (Access Token Refresh) implemented and documented: new §14 covers `POST /auth/refresh` (`TokenRefreshService`), the central stateless-vs-rotation scoping decision (session/`jti` tracking doesn't exist anywhere in the codebase, so single-use rotation and logout-invalidation are explicitly deferred to US-104/US-105 — matching the story's own documented fallback), and an explicit list of every AC/edge-case this leaves unmet (§14.5). Also closes a real pre-existing security gap the story's design note called out: `JwtAuthenticationFilter` now rejects refresh-type tokens used as bearer tokens (previously authenticated with `role=null`/`ROLE_null`) via new `JwtTokenProvider.isAccessToken`/`isRefreshToken`/`isTokenExpired` methods. Old §14-17 renumbered to §15-18 (Database Schema, API Design, Security Considerations, Testing Strategy). §16.1 gained the `/auth/refresh` endpoint spec, §17.4 JWT Claims updated to describe the new token-type-check behavior, §18.1 gained real `TokenRefreshServiceTest`/`AuthControllerTest`/`JwtTokenProviderTest`/`JwtAuthenticationFilterTest` method names, §2.4 Package Structure updated, and Implementation Sequence gained rows 24-24a. Two Sonar issues (one `S6068` redundant-matcher smell x2, seven `S5778` multi-throw-lambda smells) found and fixed in `TokenRefreshServiceTest` during the first scan of the US-107 branch. |

**Reference Documents:**
- PRD v1.4
- HLD Parts 1-3
- Sprint Plan v2.0
- User Stories v3.4
- Sprint-0-Foundation-Architecture-LLD v1.0

---

## Table of Contents

1. [Sprint Overview](#1-sprint-overview)
2. [Architecture Decisions](#2-architecture-decisions)
3. [US-001: User Registration via Mobile OTP](#3-us-001-user-registration-via-mobile-otp)
4. [US-101: Google Sign-In](#4-us-101-google-sign-in)
5. [US-102: Apple Sign-In](#5-us-102-apple-sign-in)
6. [US-002: One Account Per User Enforcement](#6-us-002-one-account-per-user-enforcement)
7. [US-003: User Profile Management](#7-us-003-user-profile-management)
8. [US-103: Profile Hub / Account Menu Navigation](#8-us-103-profile-hub--account-menu-navigation)
9. [US-104: Account Logout](#9-us-104-account-logout)
10. [US-105: Account Security Settings](#10-us-105-account-security-settings)
11. [US-077: Critical Event Notifications](#11-us-077-critical-event-notifications)
12. [US-088: Lifecycle State - User Account](#12-us-088-lifecycle-state---user-account)
13. [US-106: Mobile OTP Login for Returning Users](#13-us-106-mobile-otp-login-for-returning-users)
14. [US-107: Access Token Refresh](#14-us-107-access-token-refresh)
15. [Database Schema](#15-database-schema)
16. [API Design](#16-api-design)
17. [Security Considerations](#17-security-considerations)
18. [Testing Strategy](#18-testing-strategy)

---

# 1. Sprint Overview

## 1.1 Goal

Allow users to register and log in via multiple auth methods (Mobile OTP, Google, Apple), verify identity, and manage profiles. Establish the authentication foundation for all subsequent sprints.

## 1.2 Stories

| ID     | Story                                       | Repo            | SP | Dependency |
|--------|---------------------------------------------|-----------------|----|------------|
| US-001 | User Registration via Mobile OTP            | backend, mobile | 8  | S0-001     |
| US-106 | Mobile OTP Login for Returning Users        | backend, mobile | 5  | US-001     |
| US-107 | Access Token Refresh                        | backend, mobile | 5  | US-106     |
| US-101 | Google Sign-In (Optional Convenience Login) | backend, mobile | 5  | US-001     |
| ~~US-102~~ | ~~Apple Sign-In (Optional Convenience Login)~~ | ~~backend, mobile~~ | ~~5~~ | — **Dropped** |
| US-002 | One Account Per User Enforcement            | backend         | 3  | US-001     |
| US-003 | User Profile Management                     | backend, mobile | 5  | US-001     |
| US-103 | Profile Hub / Account Menu Navigation       | backend, mobile | 5  | US-003     |
| US-104 | Account Logout                              | backend, mobile | 2  | US-001     |
| US-105 | Account Security Settings                   | backend, mobile | 5  | US-003     |
| US-077 | Critical Event Notifications                | backend, mobile | 5  | US-001     |
| US-088 | Lifecycle State - User Account              | backend         | 3  | US-001     |

## 1.3 Exit Criteria

Status as of v1.10 — checked items are actually implemented and covered by passing tests, not just designed:

- [x] User can register via mobile OTP
- [x] Returning users can log back in via mobile OTP without re-registering (US-106 — see §13)
- [x] Access tokens can be refreshed via the refresh token — **stateless only**, single-use rotation and logout-invalidation deferred to US-104/US-105 (US-107 — see §14)
- [x] Email verification step works (OTP sent to email after mobile OTP)
- [x] Google Sign-In working (returns JWT, new-user flow collects mobile)
- [ ] ~~Apple Sign-In~~ — **Dropped from scope**
- [x] Aadhaar verification flow works (skip + complete)
- [x] Aadhaar gate enforced on first transaction attempt
- [x] Duplicate account prevention operational
- [x] User profile view and edit working (avatar selection, not photo upload — see §7)
- [x] Profile hub summary endpoint returns badge counts (extensible provider SPI, hardened per PR review — see §8)
- [ ] Logout revokes current session (JWT `jti` blocklisted immediately) — **design only, not implemented** (US-104; the real `JwtTokenProvider` has no `jti` claim yet — see §17.4)
- [ ] Mobile/email change via OTP working; active-sessions list and "log out of other devices" working — **design only, not implemented** (US-105)
- [x] Account state transitions tracked and audited (`UserAccountStateMachine` + `account_status_history`, exercised by every registration/Aadhaar test)
- [ ] Critical event notifications sent (in-app + push) — **design only, not implemented** (US-077; `com.valuex.notification` is still the Sprint-0 state-machine scaffold, no entity/table/dispatcher)
- [x] All *implemented* endpoints documented in Swagger UI (`@Operation`/`@Tag` on every real controller method)

---

# 2. Architecture Decisions

## 2.1 Plug-and-Play OTP Provider

**Problem:** The SMS OTP provider has not been decided yet (Twilio, AWS SNS, MSG91, Kaleyra, etc.).

**Decision:** Define an `OtpPort` interface. Each provider is an adapter implementing this interface. The active adapter is selected via a single config property. No code change required to switch providers.

```
valuex.otp.provider=mock        # dev
valuex.otp.provider=msg91       # staging / prod
```

**Interface contract:**

```java
public interface OtpPort {
    void sendOtp(String mobile, String otp, OtpPurpose purpose);
}
```

**Adapters:**

| Adapter | When Used |
|---|---|
| `MockOtpAdapter` | Local dev — logs OTP to console/Redis |
| `Msg91OtpAdapter` | Production candidate |
| `TwilioOtpAdapter` | Alternative candidate |

Spring selects active adapter using `@ConditionalOnProperty`:

```java
@Bean
@ConditionalOnProperty(name = "valuex.otp.provider", havingValue = "mock")
public OtpPort mockOtpAdapter() { return new MockOtpAdapter(); }

@Bean
@ConditionalOnProperty(name = "valuex.otp.provider", havingValue = "msg91")
public OtpPort msg91OtpAdapter(Msg91Properties props) { return new Msg91OtpAdapter(props); }
```

---

## 2.2 Plug-and-Play Aadhaar Provider

**Problem:** The Aadhaar verification provider has not been decided yet (AuthBridge, DigiLocker, UIDAI Sandbox, etc.).

**Decision:** Define an `AadhaarVerificationPort` interface. Adapters implement provider-specific HTTP calls. Provider switched via config. Zero code change to switch.

```
valuex.aadhaar.provider=sandbox        # dev
valuex.aadhaar.provider=authbridge     # staging / prod
```

**Interface contract:**

```java
public interface AadhaarVerificationPort {
    AadhaarOtpResponse initiateVerification(String aadhaarNumber, String consentToken);
    AadhaarVerifyResponse completeVerification(String transactionId, String otp);
}
```

**Adapters:**

| Adapter | When Used |
|---|---|
| `SandboxAadhaarAdapter` | Local dev — simulates success/failure |
| `AuthBridgeAadhaarAdapter` | Production candidate |
| `DigiLockerAadhaarAdapter` | Alternative candidate |

---

## 2.3 Aadhaar Verification is Skippable Until First Transaction

**Problem:** Forcing Aadhaar upfront creates friction and drop-offs. PRD allows deferred verification.

**Decision:**

- After mobile OTP, account state = `IDENTITY_VERIFICATION_PENDING`
- A JWT is issued with `aadhaarVerified: false` claim
- User can browse, view listings, and use the app freely
- `@RequiresIdentityVerification` annotation on listing creation and buy endpoints
- When an unverified user hits a gated endpoint → HTTP 403 with `AADHAAR_VERIFICATION_REQUIRED` and deep link hint to the verification flow

```
Transaction Gating Flow:
User hits POST /api/v1/listings
  → AadhaarGatingInterceptor checks JWT claim
  → aadhaarVerified=false → 403 AADHAAR_VERIFICATION_REQUIRED
  → Client shows "Complete Aadhaar verification to continue"
```

---

## 2.4 Package Structure

All new code lives under `com.valuex.auth`:

```
com.valuex.auth/
├── domain/
│   ├── User.java                            # JPA entity
│   ├── UserAccountState.java               # (created in S0-008)
│   ├── SocialProvider.java                 # Enum: GOOGLE
│   ├── UserSocialAccount.java              # JPA entity for social links
│   └── UserSession.java                    # JPA entity — one row per login (US-104/US-105)
│
├── application/
│   ├── port/
│   │   ├── OtpPort.java                    # OTP provider interface
│   │   ├── AadhaarVerificationPort.java    # Aadhaar provider interface
│   │   ├── GoogleTokenPort.java            # Google token validation interface
│   │   ├── GoogleUserInfo.java             # Record: sub, email, name
│   │   └── ProfileMenuBadgeProvider.java   # SPI — each domain module contributes a badge count (US-103)
│   ├── service/
│   │   ├── UserRegistrationService.java    # Registration + mobile OTP flow
│   │   ├── UserLoginService.java           # Login for returning users (US-106)
│   │   ├── EmailVerificationService.java   # Email OTP send + verify
│   │   ├── AadhaarVerificationService.java # Aadhaar initiate + verify
│   │   ├── GoogleSignInService.java        # Google 3-step sign-in flow
│   │   ├── TokenRefreshService.java        # Stateless access-token refresh (US-107)
│   │   ├── UserProfileService.java         # Profile CRUD + avatar selection/catalog
│   │   ├── ProfileMenuService.java         # Profile hub badge aggregation (US-103)
│   │   ├── SessionService.java             # Session create/revoke/blocklist (US-104/US-105)
│   │   └── AccountSecurityService.java     # Mobile/email change, session listing (US-105)
│   └── dto/
│       ├── InitiateRegistrationRequest.java
│       ├── VerifyMobileOtpRequest.java
│       ├── InitiateLoginRequest.java       # { mobile } — US-106
│       ├── VerifyLoginOtpRequest.java      # { mobile, otp } — US-106
│       ├── RefreshTokenRequest.java        # { refreshToken } — US-107
│       ├── SendEmailOtpRequest.java
│       ├── VerifyEmailOtpRequest.java
│       ├── InitiateAadhaarRequest.java
│       ├── VerifyAadhaarOtpRequest.java
│       ├── GoogleSignInRequest.java
│       ├── SocialLinkMobileRequest.java
│       ├── SocialVerifyMobileRequest.java
│       ├── SocialSignInResponse.java
│       ├── UpdateProfileRequest.java
│       ├── SelectAvatarRequest.java        # { avatarId } — US-003 avatar picker
│       ├── AuthResponse.java
│       ├── MessageResponse.java
│       ├── ProfileMenuSummaryResponse.java # US-103
│       ├── ChangeMobileRequest.java        # US-105
│       ├── VerifyMobileChangeRequest.java  # US-105
│       ├── ChangeEmailRequest.java         # US-105
│       ├── VerifyEmailChangeRequest.java   # US-105
│       └── SessionSummaryResponse.java     # US-105
│
├── adapter/
│   ├── otp/
│   │   ├── MockOtpAdapter.java             # Dev stub
│   │   ├── Msg91OtpAdapter.java            # Production candidate
│   │   └── OtpProviderConfig.java          # @ConditionalOnProperty wiring
│   ├── aadhaar/
│   │   ├── SandboxAadhaarAdapter.java      # Dev stub
│   │   ├── AuthBridgeAadhaarAdapter.java   # Production candidate
│   │   └── AadhaarProviderConfig.java      # @ConditionalOnProperty wiring
│   ├── oauth/
│   │   ├── MockGoogleTokenAdapter.java     # Dev stub — accepts mock-<suffix> tokens
│   │   ├── HttpGoogleTokenAdapter.java     # Prod — calls Google tokeninfo endpoint
│   │   └── GoogleTokenAdapterConfig.java   # @ConditionalOnProperty wiring
│   └── menu/
│       └── NotificationsBadgeProvider.java # Sprint 1's only ProfileMenuBadgeProvider impl (US-103)
│
├── infrastructure/
│   └── persistence/
│       ├── UserRepository.java             # Domain-facing interface
│       ├── UserJpaRepository.java          # Spring Data JPA
│       ├── UserSocialAccountRepository.java # Social account lookups
│       └── UserSessionRepository.java      # Session lookups (US-104/US-105)
│
├── security/
│   └── AadhaarGatingInterceptor.java       # Enforces identity gate
│
└── api/
    ├── AuthController.java                 # All auth endpoints (registration + login + refresh + social + logout)
    ├── UserProfileController.java          # Profile endpoints + menu-summary (US-103)
    ├── AvatarController.java               # GET /api/v1/avatars — avatar catalog (US-003)
    └── AccountSecurityController.java      # Mobile/email change, sessions (US-105)
```

Note: there is no `StoragePort`/adapter and no file-upload pipeline in this module. Profile pictures are
never user-uploaded — see Section 7 (US-003 redesign, v1.4) for why.

---

## 2.5 Session Tracking for Logout & Multi-Device Management

**Problem:** JWTs are stateless — the design in Sections 3-6 has no server-side way to revoke a specific access token before its `exp`, and no way to enumerate a user's active devices. US-104 (Logout) and US-105 (Account Security) both need this.

**Decision:**
- Every JWT (access + refresh) gets a `jti` (JWT ID, UUID) claim, generated at issuance.
- A `user_sessions` table records one row per login — from *any* auth flow (mobile OTP, Google, Aadhaar re-issue) — keyed by `jti`, storing a hash of the refresh token plus device metadata and timestamps.
- **Logout** (US-104) marks the session `revoked_at` and adds its `jti` to a Redis blocklist (`blocklist:{jti}`) with TTL = the access token's remaining lifetime, so the still-valid access token is rejected on the very next request instead of waiting out its `exp`.
- **"Log out of all other devices"** (US-105) revokes every session for the user except the caller's own `jti`.
- `JwtAuthenticationFilter` (already defined in the Sprint 0 Foundation LLD) gets one additional check after signature/expiry validation: reject if `jti` is present in the blocklist.

This keeps normal request handling stateless (no DB hit per request — just a Redis key lookup) while making revocation immediate.

---

# 3. US-001: User Registration via Mobile OTP

## 3.1 Registration Flow

```
Step 1: Initiate Registration
  POST /api/v1/auth/register/initiate
  Body: { mobile, termsAccepted, consentGiven }
  → Validate mobile format (10 digits, starts with 6-9)
  → Check mobile not already registered
  → Create user record (state = NEW)
  → Generate OTP (6 digits)
  → Store SHA-256(OTP) in Redis: otp:{mobile}:{purpose}  TTL=300s
  → Call OtpPort.sendOtp(mobile, otp, MOBILE_VERIFY)
  → Transition state: NEW → OTP_PENDING
  → Return: { message: "OTP sent", otpExpiresInSeconds: 300 }

Step 2: Verify Mobile OTP
  POST /api/v1/auth/register/verify-mobile
  Body: { mobile, otp }
  → Fetch OTP hash from Redis
  → Validate OTP (hash match, rate-limit check)
  → Delete OTP + counters from Redis
  → Transition state: OTP_PENDING → EMAIL_VERIFICATION_PENDING  ← actual state
  → Generate JWT (aadhaarVerified=false, userId, role=USER)
  → Return: AuthResponse { accessToken, refreshToken, aadhaarVerified=false, userId,
                            status=EMAIL_VERIFICATION_PENDING }

Step 3: Email Verification  ← added during development
  POST /api/v1/auth/email/send-otp
  Body: { email }
  → Validate email format
  → Generate OTP (6 digits), store SHA-256(OTP) in Redis  TTL=300s
  → Send OTP to email via EmailOtpPort
  → Return: { message, otpExpiresInSeconds: 300 }

  POST /api/v1/auth/email/verify-otp
  Body: { email, otp }
  → Validate OTP hash from Redis
  → Transition state: EMAIL_VERIFICATION_PENDING → IDENTITY_VERIFICATION_PENDING
  → Return: { message: "Email verified successfully" }

Step 4a: Skip Aadhaar (User chooses to skip)
  POST /api/v1/auth/register/skip-aadhaar
  → Transition state: IDENTITY_VERIFICATION_PENDING → ACTIVE  ← actual behaviour
  → Reissue JWT
  → Return: AuthResponse { accessToken, refreshToken, aadhaarVerified=false, userId, status=ACTIVE }
  Note: aadhaarVerified stays false; Aadhaar gate blocks first transaction

Step 4b: Initiate Aadhaar Verification
  POST /api/v1/auth/aadhaar/initiate
  Body: { aadhaarNumber, consentToken }
  → Validate Aadhaar format (12 digits)
  → Check Aadhaar hash not already linked to another user (US-002)
  → Call AadhaarVerificationPort.initiateVerification(aadhaarNumber, consentToken)
  → Store transactionId in Redis: aadhaar_txn:{userId}  TTL=600s
  → Log attempt in aadhaar_verification_attempts table
  → Return: { transactionId, message: "OTP sent to Aadhaar-linked mobile" }

Step 5: Complete Aadhaar Verification
  POST /api/v1/auth/aadhaar/verify
  Body: { transactionId, otp }
  → Fetch transactionId from Redis
  → Call AadhaarVerificationPort.completeVerification(transactionId, otp)
  → On success: store SHA-256(aadhaarNumber) on user record
  → Set aadhaarVerified=true, store masked name from Aadhaar
  → Update attempt log: status=SUCCESS
  → Transition state: IDENTITY_VERIFICATION_PENDING → ACTIVE
  → Reissue JWT (aadhaarVerified=true)
  → Return: AuthResponse { accessToken, refreshToken, aadhaarVerified=true, userId, status=ACTIVE }
```

## 3.2 User Entity

```java
package com.valuex.auth.domain;

@Entity
@Table(name = "users")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class User {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(nullable = false, unique = true, length = 15)
    private String mobile;

    @Column(nullable = false)
    @Enumerated(EnumType.STRING)
    private UserAccountState status;

    @Column(name = "aadhaar_hash", unique = true, length = 64)
    private String aadhaarHash;         // SHA-256, never plain Aadhaar

    @Column(name = "aadhaar_name")
    private String aadhaarName;         // Masked name from Aadhaar API

    @Column(name = "aadhaar_verified", nullable = false)
    private boolean aadhaarVerified = false;

    @Column(name = "display_name", length = 50)
    private String displayName;

    @Column(name = "avatar_id", length = 50)
    private String avatarId;            // ID from the platform's avatar catalog — never a user-uploaded URL

    @Column(length = 255)
    private String city;

    @Column(name = "terms_accepted_at")
    private Instant termsAcceptedAt;

    @Column(name = "consent_given_at")
    private Instant consentGivenAt;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    @PrePersist
    void onCreate() {
        createdAt = Instant.now();
        updatedAt = Instant.now();
        if (status == null) {
            status = UserAccountState.NEW;
        }
        if (avatarId == null) {
            avatarId = "avatar-01";   // default until the user picks one
        }
    }

    @PreUpdate
    void onUpdate() {
        updatedAt = Instant.now();
    }
}
```

## 3.3 OTP Port Interface

```java
package com.valuex.auth.application.port;

public interface OtpPort {
    void sendOtp(String mobile, String otp, OtpPurpose purpose);
}

public enum OtpPurpose {
    MOBILE_VERIFY,
    LOGIN
}
```

## 3.4 Mock OTP Adapter (Dev)

```java
package com.valuex.auth.adapter.otp;

@Slf4j
public class MockOtpAdapter implements OtpPort {

    @Override
    public void sendOtp(String mobile, String otp, OtpPurpose purpose) {
        // In dev, OTP is visible in logs and also stored in Redis for easy retrieval
        log.info("[DEV-MOCK] OTP for mobile={} purpose={} otp={}", mobile, purpose, otp);
    }
}
```

## 3.5 Aadhaar Port Interface

```java
package com.valuex.auth.application.port;

public interface AadhaarVerificationPort {
    AadhaarOtpResponse initiateVerification(String aadhaarNumber, String consentToken);
    AadhaarVerifyResponse completeVerification(String transactionId, String otp);
}

public record AadhaarOtpResponse(String transactionId, String message) {}

public record AadhaarVerifyResponse(
    boolean success,
    String maskedName,
    String failureReason
) {}
```

## 3.6 Sandbox Aadhaar Adapter (Dev)

```java
package com.valuex.auth.adapter.aadhaar;

@Slf4j
public class SandboxAadhaarAdapter implements AadhaarVerificationPort {

    // Test Aadhaar that always fails: 999999999999
    private static final String ALWAYS_FAIL_AADHAAR = "999999999999";

    @Override
    public AadhaarOtpResponse initiateVerification(String aadhaarNumber, String consentToken) {
        log.info("[DEV-SANDBOX] Aadhaar OTP initiated for aadhaar ending in {}",
            aadhaarNumber.substring(8));
        return new AadhaarOtpResponse("sandbox-txn-" + UUID.randomUUID(), "OTP sent");
    }

    @Override
    public AadhaarVerifyResponse completeVerification(String transactionId, String otp) {
        // In sandbox: OTP "000000" always fails, anything else succeeds
        if ("000000".equals(otp)) {
            return new AadhaarVerifyResponse(false, null, "Invalid OTP");
        }
        return new AadhaarVerifyResponse(true, "Test User", null);
    }
}
```

## 3.7 Provider Configuration

```java
package com.valuex.auth.adapter.otp;

@Configuration
public class OtpProviderConfig {

    @Bean
    @ConditionalOnProperty(name = "valuex.otp.provider", havingValue = "mock",
        matchIfMissing = true)
    public OtpPort mockOtpAdapter() {
        return new MockOtpAdapter();
    }

    @Bean
    @ConditionalOnProperty(name = "valuex.otp.provider", havingValue = "msg91")
    public OtpPort msg91OtpAdapter(Msg91Properties properties) {
        return new Msg91OtpAdapter(properties);
    }
}
```

```java
package com.valuex.auth.adapter.aadhaar;

@Configuration
public class AadhaarProviderConfig {

    @Bean
    @ConditionalOnProperty(name = "valuex.aadhaar.provider", havingValue = "sandbox",
        matchIfMissing = true)
    public AadhaarVerificationPort sandboxAadhaarAdapter() {
        return new SandboxAadhaarAdapter();
    }

    @Bean
    @ConditionalOnProperty(name = "valuex.aadhaar.provider", havingValue = "authbridge")
    public AadhaarVerificationPort authBridgeAadhaarAdapter(AuthBridgeProperties properties) {
        return new AuthBridgeAadhaarAdapter(properties);
    }
}
```

## 3.8 application.yml additions

```yaml
valuex:
  otp:
    provider: ${OTP_PROVIDER:mock}
    expiry-seconds: 300
    length: 6
  aadhaar:
    provider: ${AADHAAR_PROVIDER:sandbox}
```

## 3.9 OTP Redis Key Pattern

```
Key:   otp:{mobile}:{purpose}
Value: SHA-256(otp)
TTL:   300 seconds (5 minutes)

Key:   aadhaar_txn:{userId}
Value: {transactionId}
TTL:   600 seconds (10 minutes)
```

---

# 4. US-101: Google Sign-In

## 4.1 Three Supported Flows

### Flow A — New Google user (not yet in ValueX)
```
POST /api/v1/auth/social/google  { idToken }
  → Validate token (mock or HTTP adapter)
  → Google sub not found in user_social_accounts
  → Store social session in Redis (10-min TTL)
  → Return: { requiresMobileVerification: true, socialSessionToken, googleEmail }

POST /api/v1/auth/social/google/initiate-mobile
  { socialSessionToken, mobile, termsAccepted, consentGiven }
  → Validate social session exists in Redis
  → Check mobile not already ACTIVE with Google already linked
  → Send mobile OTP
  → Return: { message: "OTP sent", otpExpiresInSeconds: 300 }

POST /api/v1/auth/social/google/verify-mobile
  { socialSessionToken, mobile, otp }
  → Validate OTP
  → Create new User (state = IDENTITY_VERIFICATION_PENDING)
  → Write UserSocialAccount row linking Google sub → new userId
  → Clear session + OTP from Redis
  → Issue JWT
  → Return: AuthResponse { accessToken, refreshToken, aadhaarVerified=false, userId,
                            status=IDENTITY_VERIFICATION_PENDING }
```

### Flow B — Returning Google user (already linked)
```
POST /api/v1/auth/social/google  { idToken }
  → Validate token
  → Google sub found in user_social_accounts → look up User
  → Issue JWT immediately
  → Return: { requiresMobileVerification: false, accessToken, refreshToken, ... }
```

### Flow C — Link Google to an existing mobile-OTP account
```
POST /api/v1/auth/social/google  { idToken }
  → Google sub not found → create social session (same as Flow A Step 1)

POST /api/v1/auth/social/google/initiate-mobile
  { socialSessionToken, mobile: "<existing user's mobile>", ... }
  → Mobile belongs to an existing ACTIVE user
  → Confirm that user does not already have Google linked
  → Send OTP to that mobile
  → Session updated with existingUserId

POST /api/v1/auth/social/google/verify-mobile
  → Validate OTP
  → Write UserSocialAccount row linking Google sub → existingUserId
  → No state change (account stays ACTIVE)
  → Issue JWT
```

> **Constraint:** The existing account must be in `ACTIVE` state.
> Accounts in `EMAIL_VERIFICATION_PENDING` or `IDENTITY_VERIFICATION_PENDING`
> return `ERROR_INVALID_STATE`.

## 4.2 GoogleTokenPort (Plug-and-Play)

The design uses a **Google-specific port** rather than a generic `SocialLoginPort`,
because Google and Apple token validation differ enough to warrant separate interfaces.

```java
package com.valuex.auth.application.port;

public interface GoogleTokenPort {
    GoogleUserInfo verifyIdToken(String idToken);
}

public record GoogleUserInfo(String sub, String email, String name) {}
```

**MockGoogleTokenAdapter (dev):**
```java
package com.valuex.auth.adapter.oauth;

// Accepts tokens of form "mock-<suffix>"
// Maps suffix to stable Google sub: "google-sub-<suffix>"
// "invalid" suffix throws ERROR_INVALID_GOOGLE_TOKEN
@Slf4j
public class MockGoogleTokenAdapter implements GoogleTokenPort {
    @Override
    public GoogleUserInfo verifyIdToken(String idToken) {
        if (!idToken.startsWith("mock-") || idToken.equals("mock-invalid")) {
            throw new BusinessException("ERROR_INVALID_GOOGLE_TOKEN", "...");
        }
        String suffix = idToken.substring(5);
        return new GoogleUserInfo("google-sub-" + suffix, suffix + "@gmail.com", suffix);
    }
}
```

**HttpGoogleTokenAdapter (prod):**
```java
package com.valuex.auth.adapter.oauth;

// Calls https://oauth2.googleapis.com/tokeninfo?id_token={idToken}
// Validates: email_verified == "true", aud in configured client-ids list
// Throws ERROR_INVALID_GOOGLE_TOKEN on any failure
@Slf4j
@RequiredArgsConstructor
public class HttpGoogleTokenAdapter implements GoogleTokenPort {
    private static final String TOKENINFO_URL =
        "https://oauth2.googleapis.com/tokeninfo?id_token=";

    private final RestClient restClient;
    private final ValuexProperties valuexProperties;

    @Override
    public GoogleUserInfo verifyIdToken(String idToken) {
        // 1. GET tokeninfo
        // 2. Check email_verified == "true"  ← security requirement
        // 3. Check aud in acceptedClientIds
        // 4. Return GoogleUserInfo(sub, email, name)
    }
}
```

**GoogleTokenAdapterConfig:**
```java
package com.valuex.auth.adapter.oauth;

@Configuration
public class GoogleTokenAdapterConfig {

    @Bean
    @ConditionalOnProperty(name = "valuex.oauth.google.provider",
        havingValue = "mock", matchIfMissing = true)
    public GoogleTokenPort mockGoogleTokenAdapter() {
        return new MockGoogleTokenAdapter();
    }

    @Bean
    @ConditionalOnProperty(name = "valuex.oauth.google.provider", havingValue = "http")
    public GoogleTokenPort httpGoogleTokenAdapter(
            RestClient restClient, ValuexProperties properties) {
        return new HttpGoogleTokenAdapter(restClient, properties);
    }
}
```

## 4.3 Redis Social Session Key Pattern

```
Key:   social:pending:{socialSessionToken}        (UUID)
Value: GOOGLE|{sub}|{email}                       (Steps 1-2)
       GOOGLE|{sub}|{email}|{mobile}|{existingUserId or "new"}  (after initiate-mobile)
TTL:   600 seconds (10 minutes)

Key:   otp:{mobile}:MOBILE_VERIFY
Value: SHA-256(otp)
TTL:   300 seconds
```

Session is deleted from Redis on successful OTP verification.

## 4.4 user_social_accounts Table (V5 migration)

```sql
CREATE TABLE user_social_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(20) NOT NULL,           -- 'GOOGLE'
    provider_user_id VARCHAR(255) NOT NULL,  -- sub from token
    provider_email VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_social_provider UNIQUE (provider, provider_user_id)
);

CREATE INDEX idx_social_accounts_user ON user_social_accounts(user_id);
```

## 4.5 application.yml additions

```yaml
valuex:
  oauth:
    google:
      provider: ${GOOGLE_OAUTH_PROVIDER:mock}   # mock (dev) | http (prod)
      client-ids:
        - ${GOOGLE_CLIENT_ID_WEB:}
        - ${GOOGLE_CLIENT_ID_ANDROID:}
        - ${GOOGLE_CLIENT_ID_IOS:}
```

Production env vars required when `provider=http`:

| Variable | Description |
|---|---|
| `GOOGLE_OAUTH_PROVIDER` | Set to `http` in prod |
| `GOOGLE_CLIENT_ID_WEB` | Web OAuth client ID |
| `GOOGLE_CLIENT_ID_ANDROID` | Android OAuth client ID (SHA-1 fingerprint registered) |
| `GOOGLE_CLIENT_ID_IOS` | iOS OAuth client ID |

---

# 5. US-102: Apple Sign-In — ~~DROPPED~~

> **Decision (Aug 2026):** Apple Sign-In has been removed from scope.
> The `SocialProvider` enum retains only `GOOGLE`.
> The `user_social_accounts` table schema (`provider VARCHAR(20)`) is future-compatible
> if Apple Sign-In is re-introduced in a later sprint.
>
> The Apple-specific rules below are retained for reference if the story is revisited:
>
> - Use `sub` claim as stable identifier — **not** email
> - Email only sent by Apple on first sign-in; must be cached immediately
> - Apple may return a `@privaterelay.appleid.com` relay address — store as-is
> - Apple Sign-In is not available on Android
> - App Store guideline 4.8: if any OAuth login is shown on iOS, Apple Sign-In must also be offered

---

# 6. US-002: One Account Per User Enforcement

## 4.1 Design

Duplicate account prevention is enforced at two checkpoints:

**Checkpoint 1 — Mobile uniqueness** (during Step 1 of registration):
```
SELECT COUNT(*) FROM users WHERE mobile = ?
→ If exists → ERROR_MOBILE_ALREADY_REGISTERED
```
Includes soft-deleted, suspended, and banned accounts.

**Checkpoint 2 — Aadhaar uniqueness** (during Step 3b):
```
SELECT COUNT(*) FROM users WHERE aadhaar_hash = SHA256(?)
→ If exists → ERROR_AADHAAR_ALREADY_USED
```
Includes all account states. If found on a BANNED account → log security event.

## 4.2 Audit Logging

Every Aadhaar verification attempt (success or failure) is written to `aadhaar_verification_attempts`:

```
actor_id     → userId
aadhaar_hash → SHA-256(aadhaarNumber)  — never plain text
provider     → valuex.aadhaar.provider
transaction_id, status, failure_reason, ip_address, created_at
```

This provides the audit trail required by compliance without storing raw Aadhaar numbers.

---

# 7. US-003: User Profile Management

## 5.0 Design Change (v1.4) — Avatar Selection Replaces Photo Upload

**Original design (v1.1-1.3):** free-form profile photo upload to S3, with content moderation "queued async" and no actual moderation pipeline behind it (Trust & Safety/US-048/049 don't exist until Sprint 9).

**Revised decision:** users never upload a profile picture. They pick an **avatar** from a fixed catalog the frontend renders. The backend's only job is to own the canonical list of valid avatar IDs and store which one each user selected.

**Why:** this eliminates image content moderation from Sprint 1's scope entirely — no user-supplied image ever reaches the platform for a profile picture, so `ERROR_INAPPROPRIATE_CONTENT`, file-type/size validation, and the `StoragePort`/S3 upload pipeline this story would otherwise need are all unnecessary. It also removes a real Sprint-9-dependency gap: the old design's moderation note was aspirational and had nothing behind it yet.

**Impact:** `users.profile_photo_url` → `users.avatar_id`. No `StoragePort`, no storage adapters, no multipart upload endpoint in this module.

## 5.1 Profile Fields

| Field | Editable | Source | Validation |
|---|---|---|---|
| `displayName` | Yes | User input | 3-50 chars, no special symbols |
| `avatarId` | Yes | Avatar catalog selection | Must be a published catalog ID |
| `city` | Yes | User input | Valid Indian city |
| `aadhaarName` | No | Aadhaar API | Read-only, shown as "Verified Name" |
| `mobile` | No | Registration | Identity anchor, not changeable |

## 5.2 Avatar Catalog & Selection Flow

The catalog is a small, backend-owned, config-driven list of IDs (`valuex.avatar.available-ids`) that the frontend maps to its own bundled avatar images — the backend never stores or serves avatar image bytes, only the ID.

```
GET /api/v1/avatars
  Auth: Bearer token required
  → Return the current catalog: { avatarIds: [...], defaultAvatarId: "avatar-01" }

PUT /api/v1/users/me/avatar
  Auth: Bearer token required
  Body: { avatarId }
  → Validate avatarId is one of valuex.avatar.available-ids
  → user.avatarId = avatarId; save
  → Return: updated UserProfileResponse

Every account gets avatarId = "avatar-01" at creation time (User.onCreate()),
so profile view never has to handle a null avatar.
```

## 5.3 UserProfileService

```java
package com.valuex.auth.application.service;

@Service
@RequiredArgsConstructor
public class UserProfileService {

    private final UserRepository userRepository;
    private final ValuexProperties valuexProperties;

    public UserProfileResponse getProfile(UUID userId) {
        return UserProfileResponse.from(findUser(userId));
    }

    @Transactional
    public UserProfileResponse updateProfile(UUID userId, UpdateProfileRequest request) {
        User user = findUser(userId);

        if (request.getDisplayName() != null) {
            user.setDisplayName(request.getDisplayName());
        }
        if (request.getCity() != null) {
            user.setCity(request.getCity());
        }

        return UserProfileResponse.from(userRepository.save(user));
    }

    public List<String> getAvatarCatalog() {
        return valuexProperties.getAvatar().getAvailableIds();
    }

    @Transactional
    public UserProfileResponse selectAvatar(UUID userId, String avatarId) {
        User user = findUser(userId);

        if (!valuexProperties.getAvatar().getAvailableIds().contains(avatarId)) {
            throw new BusinessException("ERROR_INVALID_AVATAR",
                "Selected avatar is not available. Please choose another");
        }

        user.setAvatarId(avatarId);
        return UserProfileResponse.from(userRepository.save(user));
    }

    private User findUser(UUID userId) {
        return userRepository.findById(userId)
            .orElseThrow(() -> new NotFoundException("User not found"));
    }
}
```

---

# 8. US-103: Profile Hub / Account Menu Navigation

## 8.1 Design Approach

The Profile Hub is primarily a **mobile navigation shell** (`ProfileScreen`) — a static, grouped menu (Activity / Payments / Preferences / Support / Account) that deep-links to each feature's own screen (My Orders, Saved Items, Payout Settings, ...), most of which don't exist until later sprints (see Sprint Plan v2.0). Sprint 1 delivers:

- The backend summary endpoint the shell calls to badge menu items with live counts.
- An extensible mechanism so later sprints (Orders in Sprint 5, Support in Sprint 11, ...) can contribute their own badge count **without modifying this service**.

## 8.2 Badge Aggregation via Provider SPI

Rather than `ProfileMenuService` querying every other domain's tables directly (tight coupling to modules that don't exist yet), it depends on a small SPI that each domain module implements once it lands:

```java
package com.valuex.auth.application.port;

public interface ProfileMenuBadgeProvider {
    String menuKey();              // e.g. "MY_ORDERS", "OFFERS", "SUPPORT_TICKETS"
    int badgeCount(UUID userId);   // must be non-negative; must be fast/non-blocking
}
```

Deliberately a plain `String` key, not a shared enum — an enum would have to live somewhere (this module or another shared one), forcing every future implementing module to depend on it just to plug in, which defeats the point of the SPI. Each implementation defines its own `menuKey()` as a local constant. The real interface (`ProfileMenuBadgeProvider.java`) carries full Javadoc on both methods covering this, plus the uniqueness and non-blocking contracts — added during PR review, not shown in full here to avoid the doc and the source drifting on the next wording tweak.

`ProfileMenuService` autowires `List<ProfileMenuBadgeProvider>` — Spring injects whatever providers exist at the time (an empty list is valid, not an error). As of Sprint 1, **zero providers are registered** — `com.valuex.notification` has no persisted entity yet (only the Sprint-0 state-machine scaffold), so even the notifications example below has never actually been built. Every menu key is simply absent from the response until its owning sprint registers a provider bean.

The snippet below is the *shape* of the real implementation, trimmed for readability — see `ProfileMenuService.java` for the exact, current source. Three things were added during PR review that aren't obvious from a trimmed snippet, so don't reproduce this verbatim without them:

1. **No `@RequiredArgsConstructor`.** The constructor is written by hand so it can validate `badgeProviders` before the object exists — see point 3.
2. **Per-provider try/catch**, not `Collectors.toMap`. A provider that throws, or returns a negative count, has its key logged and omitted — it does not fail the whole response for every other provider.
3. **Constructor-time uniqueness check.** Two providers registering the same `menuKey()` throws `IllegalStateException` at app startup (or test object construction), not on a live user's request via a cryptic `Collectors.toMap` crash.

```java
package com.valuex.auth.application.service;

@Slf4j
@Service
public class ProfileMenuService {

    private final UserRepository userRepository;
    private final List<ProfileMenuBadgeProvider> badgeProviders;

    public ProfileMenuService(UserRepository userRepository, List<ProfileMenuBadgeProvider> badgeProviders) {
        this.userRepository = userRepository;
        this.badgeProviders = badgeProviders;
        validateUniqueMenuKeys(badgeProviders);   // point 3 — throws IllegalStateException on collision
    }

    public ProfileMenuSummaryResponse getSummary(UUID userId) {
        User user = userRepository.findById(userId)
            .orElseThrow(() -> new NotFoundException("User not found"));

        Map<String, Integer> badges = new LinkedHashMap<>();
        for (ProfileMenuBadgeProvider provider : badgeProviders) {
            try {
                int count = provider.badgeCount(userId);
                if (count >= 0) {
                    badges.put(provider.menuKey(), count);
                } else {
                    log.warn("negative count from {} — omitting", provider.getClass().getSimpleName());
                }
            } catch (RuntimeException e) {
                log.warn("provider {} failed — omitting", provider.getClass().getSimpleName(), e);   // point 2
            }
        }

        return ProfileMenuSummaryResponse.builder()
            .displayName(user.getDisplayName())
            .avatarId(user.getAvatarId())
            .aadhaarVerified(user.isAadhaarVerified())
            .memberSince(user.getCreatedAt())   // AC audit fix — US-103's AC calls for "joined date" in the summary
            .badges(Collections.unmodifiableMap(badges))   // e.g. {"NOTIFICATIONS": 3}
            .build();
    }

    private static void validateUniqueMenuKeys(List<ProfileMenuBadgeProvider> providers) { /* see source */ }
}
```

Sprint 1's own notifications provider — **hypothetical, not built.** `NotificationRepository` doesn't exist (US-077 hasn't shipped), so this class has never actually been created; it's shown only to illustrate what registering a provider looks like once one exists:

```java
package com.valuex.auth.adapter.menu;

@Component
@RequiredArgsConstructor
public class NotificationsBadgeProvider implements ProfileMenuBadgeProvider {

    private final NotificationRepository notificationRepository;   // does not exist yet

    @Override
    public String menuKey() { return "NOTIFICATIONS"; }

    @Override
    public int badgeCount(UUID userId) {
        return notificationRepository.countByUserIdAndReadFalse(userId);
    }
}
```

## 8.3 Menu Structure (Client Reference)

The backend does not enforce menu structure — it's a mobile-side constant — but the groupings below are the contract the mobile team builds against, so badge keys must line up:

| Group | Menu Item | Badge Key | Destination Story | Sprint |
|---|---|---|---|---|
| Activity | My Orders | `MY_ORDERS` | US-023 / US-070 | 5 |
| Activity | My Listings | `MY_LISTINGS` | US-010 / US-067 | 2 / 15 |
| Activity | Saved Items | `SAVED_ITEMS` | US-073 | 3 |
| Activity | Offers | `OFFERS` | US-076 | 4 |
| Payments | Transaction History | `TRANSACTIONS` | US-071 | 5 |
| Payments | Payout Settings | `PAYOUTS` | US-072 | 5 |
| Preferences | Notifications | `NOTIFICATIONS` | US-087 | 11 |
| Preferences | Language | — (no badge) | US-044 | 14 |
| Support | Help & Support | `SUPPORT_TICKETS` | US-043/045/046/074 | 11 |
| Support | Raise Dispute | `DISPUTES` | US-047 | 8 |
| Account | Edit Profile | — | US-003 | 1 |
| Account | Account Security | — | US-105 | 1 |
| Account | Logout | — | US-104 | 1 |

Menu items whose destination story hasn't shipped yet have no matching key in the `badges` map — the mobile client shows an empty/"coming soon" state for that row rather than hiding it (per US-103 edge cases in user-stories.md).

## 8.4 ProfileMenuSummaryResponse DTO

Implemented as `@Data @Builder class`, not a `record` — every sibling DTO in this package
(`UserProfileResponse`, `AuthResponse`, `AvatarCatalogResponse`, ...) is a plain `@Data @Builder`
class, and matching that keeps accessor style (`.getDisplayName()`, not `.displayName()`)
consistent across the whole test suite for zero functional difference.

```java
package com.valuex.auth.application.dto;

@Data
@Builder
public class ProfileMenuSummaryResponse {
    private String displayName;
    private String avatarId;
    private boolean aadhaarVerified;
    private Instant memberSince;
    private Map<String, Integer> badges;
}
```

---

# 9. US-104: Account Logout

**Implemented.** The design below (§9.1–§9.4) was written before this story was built and
proposed a `user_sessions` Postgres table + `SessionService` shared with US-105. The actual
implementation intentionally narrowed that scope: pure logout correctness needs nothing beyond a
`jti` claim and a Redis blocklist entry — no persisted session row. `user_sessions` is deferred to
whenever US-105 actually needs to *enumerate* sessions/devices, which this story does not. See
the corrected design below.

## 9.1 Logout Flow (as built)

```
POST /api/v1/auth/logout
  Auth: Bearer token required
  → LogoutService.logout(accessToken)
      → jti = JwtTokenProvider.getJtiFromToken(accessToken)
      → expiry = JwtTokenProvider.getExpirationFromToken(accessToken)
      → redisCache.set("blocklist:" + jti, "1", ttl = max(1s, expiry - now))
  → Return: { message: "Logged out successfully" }
```

Every token-issuing flow (`UserRegistrationService`, `UserLoginService`, `GoogleSignInService`,
`AadhaarVerificationService`, `TokenRefreshService`) now mints one shared `jti` per access+refresh
pair, so a single blocklist entry invalidates both tokens from that login/registration event, not
just the access token used to call `/logout`. `TokenRefreshService` reuses the *incoming* refresh
token's `jti` in its reissued pair (rather than minting a new one) and checks the blocklist before
honoring a refresh — so the session stays revocable by its original `jti` across any number of
refreshes, and a refresh attempted after logout fails with `ERROR_REFRESH_TOKEN_EXPIRED`.

## 9.2 LogoutService (as built)

```java
package com.valuex.auth.application.service;

@Service
@RequiredArgsConstructor
@Slf4j
public class LogoutService {

    private final RedisCacheService redisCache;
    private final JwtTokenProvider jwtTokenProvider;

    public MessageResponse logout(String accessToken) {
        String jti = jwtTokenProvider.getJtiFromToken(accessToken);
        Instant expiry = jwtTokenProvider.getExpirationFromToken(accessToken);
        long remainingSeconds = Math.max(1, Duration.between(Instant.now(), expiry).getSeconds());
        redisCache.set(JwtTokenProvider.BLOCKLIST_PREFIX + jti, "1", Duration.ofSeconds(remainingSeconds));
        return MessageResponse.of("Logged out successfully");
    }
}
```

No `UserSessionRepository`, no `user_sessions` table, no `createSession` call wired into the
issuing services — those remain genuinely US-105 territory (device listing needs persisted rows;
pure revocation does not).

## 9.3 JwtAuthenticationFilter Extension (as built)

`JwtAuthenticationFilter` now depends on `RedisCacheService` directly (no `SessionService`
indirection) and adds one check after the existing signature/access-type validation:

```java
} else if (redisCache.exists(JwtTokenProvider.BLOCKLIST_PREFIX + jwtTokenProvider.getJtiFromToken(token))) {
    log.warn("Rejected blocklisted (logged-out) token");
} else {
    // existing SecurityContext setup
}
```

One Redis `EXISTS` per authenticated request — no added DB round-trip, matching the original
performance goal in §2.5.

## 9.4 Edge Case: In-Flight Requests

Logout does not cancel requests already past the filter when it's called — only new requests
bearing the blocklisted `jti` are rejected. The mobile client is responsible for warning the user
and cancelling active uploads client-side before calling `/logout` (per user-stories.md US-104
edge cases).

## 9.5 Idempotency Boundary (corrected from the original design)

A retried `/logout` call using the same still-valid token (e.g. a client retry after a network
blip, before the first call's Redis write is visible) succeeds both times — overwriting the same
blocklist key is a safe no-op. But a **later** call using the same, now-blocklisted token is
rejected by `JwtAuthenticationFilter` before it ever reaches the controller → `401 UNAUTHORIZED`,
not `200`, because there is no valid session left to authenticate the request with. This is
correct, security-relevant behavior — the original §9 draft's blanket "always 200" framing did not
anticipate this, since it assumed a session-row lookup (which can't itself expire mid-flow) rather
than filter-level jti authentication (which can).

## 9.6 `ERROR_LOGOUT_FAILED` — Defined but Not Reachable

`user-stories.md` defines this code, but nothing in the as-built design has a real failure path
that should surface it — the only external call is a Redis write; an actual Redis outage
propagates as a `500`, not a caught business error.

---

# 10. US-105: Account Security Settings

## 10.1 Mobile / Email Change Flow

Reuses the exact OTP mechanics from US-001 (`OtpPort`, `EmailVerificationService`) against the **new** value, not the existing one:

```
POST /api/v1/users/me/mobile/change/initiate
  Auth: Bearer token required
  Body: { newMobile }
  → Validate format; check newMobile not already ACTIVE for another user
  → Generate OTP, store SHA-256(otp) in Redis: otp:{newMobile}:MOBILE_CHANGE  TTL=300s
  → OtpPort.sendOtp(newMobile, otp, MOBILE_CHANGE)
  → Return: { message, otpExpiresInSeconds: 300 }

POST /api/v1/users/me/mobile/change/verify
  Body: { newMobile, otp }
  → Validate OTP
  → user.mobile = newMobile; save
  → Publish MobileNumberChangedEvent → US-077 notifies old + new mobile
  → Return: { message: "Mobile number updated" }
```

Email change mirrors this exactly against `POST /api/v1/users/me/email/change/initiate|verify`, reusing `EmailVerificationService` with a new `EmailOtpPurpose.EMAIL_CHANGE`.

**The old value stays active until the new one is verified** — if the user abandons the flow mid-way, nothing changes (matches user-stories.md US-105 validation rule).

## 10.2 Active Sessions

```
GET /api/v1/users/me/sessions
  Auth: Bearer token required
  → List up to 10 most-recent non-revoked user_sessions rows for this user
  → Mark the row matching the caller's own jti as "isCurrent": true
  → Return: [{ sessionId, deviceInfo, ipAddress, createdAt, lastActiveAt, isCurrent }, ...]

POST /api/v1/users/me/sessions/revoke-others
  Auth: Bearer token required
  → SessionService.revokeAllExcept(userId, callerJti, reason="REVOKE_OTHER_DEVICES")
  → Return: { message: "Logged out of N other device(s)" }
```

```java
public void revokeAllExcept(UUID userId, String keepJti, String reason) {
    List<UserSession> active = sessionRepository.findByUserIdAndRevokedAtIsNull(userId);
    for (UserSession session : active) {
        if (session.getId().equals(UUID.fromString(keepJti))) continue;
        revoke(session.getId().toString(), userId, reason);
    }
}
```

## 10.3 Delete Account Entry Point — Out of Scope for Sprint 1

`GET /api/v1/users/me/account-security` includes a `deleteAccountUrl` pointing at the deletion flow, but the deletion flow itself (eligibility checks against active orders/disputes, 30-day grace period) is **US-063 / US-098, built in Sprint 14** — those domains (orders, disputes) don't exist yet in Sprint 1. The mobile Account Security screen renders the "Delete My Account" row from day one; tapping it before Sprint 14 ships shows "This feature is coming soon."

## 10.4 AccountSecurityController

```java
package com.valuex.auth.api;

@RestController
@RequestMapping("/api/v1/users/me")
@RequiredArgsConstructor
public class AccountSecurityController {

    private final AccountSecurityService accountSecurityService;
    private final SessionService sessionService;

    @GetMapping("/account-security")
    public ResponseEntity<?> getAccountSecurity(@AuthenticationPrincipal UUID userId) { ... }

    @PostMapping("/mobile/change/initiate")
    public ResponseEntity<?> initiateMobileChange(@AuthenticationPrincipal UUID userId,
            @Valid @RequestBody ChangeMobileRequest request) { ... }

    @PostMapping("/mobile/change/verify")
    public ResponseEntity<?> verifyMobileChange(@AuthenticationPrincipal UUID userId,
            @Valid @RequestBody VerifyMobileChangeRequest request) { ... }

    @PostMapping("/email/change/initiate")
    public ResponseEntity<?> initiateEmailChange(@AuthenticationPrincipal UUID userId,
            @Valid @RequestBody ChangeEmailRequest request) { ... }

    @PostMapping("/email/change/verify")
    public ResponseEntity<?> verifyEmailChange(@AuthenticationPrincipal UUID userId,
            @Valid @RequestBody VerifyEmailChangeRequest request) { ... }

    @GetMapping("/sessions")
    public ResponseEntity<?> listSessions(@AuthenticationPrincipal UUID userId) { ... }

    @PostMapping("/sessions/revoke-others")
    public ResponseEntity<?> revokeOtherSessions(@AuthenticationPrincipal UUID userId) { ... }
}
```

---

# 11. US-077: Critical Event Notifications

## 6.1 Sprint 1 Scope

Sprint 1 covers notifications for **account lifecycle events only**:
- Account created (registration complete)
- Account state changes (UNDER_REVIEW, SUSPENDED, BANNED, CLOSED)
- Unknown device login (future sprint — noted here for architecture alignment)

Order, payment, and listing notifications are implemented in their respective sprints.

## 6.2 Notification Architecture

**Pattern:** Domain events → Spring event publisher → Notification dispatcher → Channel adapters

```
UserRegistrationService.completeRegistration()
  → publisher.publish(new AccountCreatedEvent(userId, mobile))
      → NotificationEventListener.onAccountCreated(event)
          → NotificationDispatcher.dispatch(userId, ACCOUNT_CREATED, priority=HIGH)
              → InAppChannel.send(...)
              → PushChannel.send(...)
              → SmsChannel.send(...)   ← uses OtpPort's SMS capability or separate SMS port
```

## 6.3 Notification Priority Rules (Sprint 1 Events)

| Event | Channels | Priority |
|---|---|---|
| Account created | In-app + SMS | HIGH |
| Aadhaar verified | In-app | MEDIUM |
| State → UNDER_REVIEW | In-app + SMS | HIGH |
| State → SUSPENDED | In-app + SMS + Email | HIGH |
| State → BANNED | In-app + SMS + Email | HIGH |

## 6.4 Notification Entity

```java
@Entity
@Table(name = "notifications")
public class Notification {
    private UUID id;
    private UUID userId;

    @Enumerated(EnumType.STRING)
    private NotificationState status;         // from S0-008 NotificationState

    private String eventType;                 // ACCOUNT_CREATED, STATE_CHANGED, etc.
    private String title;
    private String body;
    private String deepLink;

    @Enumerated(EnumType.STRING)
    private NotificationPriority priority;    // HIGH, MEDIUM, LOW

    private boolean read;
    private Instant createdAt;
    private Instant readAt;
}
```

## 6.5 Notification Retention and Pagination

- Notification history retained for 90 days
- `GET /api/v1/notifications` returns paginated list (default page size: 20)
- Unread count returned in response header: `X-Unread-Notifications: 3`

---

# 12. US-088: Lifecycle State - User Account

## 7.1 State Machine Integration

`UserAccountStateMachine` (already created in S0-008) is injected into `UserRegistrationService` and `UserStateService`.

All state transitions go through the state machine — **direct status field updates are forbidden**.

```java
// CORRECT — always via state machine
stateMachine.transition(user.getStatus(), UserAccountState.OTP_PENDING, "REQUEST_OTP");
user.setStatus(UserAccountState.OTP_PENDING);
userRepository.save(user);
auditLogger.log(userId, "STATE_CHANGE", "NEW → OTP_PENDING");

// FORBIDDEN — never do this
user.setStatus(UserAccountState.OTP_PENDING);   // no validation, no audit
```

## 7.2 Access Control by State

| State | Can Login | Can Browse | Can List/Buy |
|---|---|---|---|
| NEW | No | No | No |
| OTP_PENDING | No | No | No |
| IDENTITY_VERIFICATION_PENDING | Yes | Yes | No (Aadhaar gate) |
| ACTIVE | Yes | Yes | Yes |
| UNDER_REVIEW | Yes | Yes | No |
| RESTRICTED | Yes | Yes (limited) | No |
| SUSPENDED | No | No | No |
| BANNED | No | No | No |
| CLOSED | No | No | No |

## 7.3 Aadhaar Gating Interceptor

```java
package com.valuex.auth.security;

@Component
public class AadhaarGatingInterceptor implements HandlerInterceptor {

    @Override
    public boolean preHandle(HttpServletRequest request,
                             HttpServletResponse response,
                             Object handler) throws Exception {

        if (!(handler instanceof HandlerMethod method)) {
            return true;
        }

        if (!method.hasMethodAnnotation(RequiresIdentityVerification.class)) {
            return true;
        }

        SecurityContext context = SecurityContextHolder.getContext();
        boolean aadhaarVerified = extractAadhaarVerifiedClaim(context);

        if (!aadhaarVerified) {
            response.setStatus(HttpServletResponse.SC_FORBIDDEN);
            response.setContentType("application/json");
            response.getWriter().write("""
                {
                  "success": false,
                  "error": {
                    "code": "AADHAAR_VERIFICATION_REQUIRED",
                    "message": "Please complete Aadhaar verification to continue",
                    "action": "/api/v1/auth/aadhaar/initiate"
                  }
                }
                """);
            return false;
        }
        return true;
    }
}
```

## 7.4 Annotation

```java
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface RequiresIdentityVerification {}
```

Usage on downstream controllers (Sprint 2+):
```java
@RequiresIdentityVerification
@PostMapping("/listings")
public ResponseEntity<?> createListing(...) { ... }
```

## 7.5 Suspended Account Auto-Lift

Per US-088: suspended accounts auto-lift to ACTIVE after 7 days.

Implemented as a scheduled job (Sprint 1 backend):
```java
@Scheduled(cron = "0 0 * * * *")   // every hour
public void liftExpiredSuspensions() {
    // Find users in SUSPENDED state where suspension_lifted_at <= now()
    // Transition to ACTIVE via state machine
    // Publish STATE_CHANGED event
}
```

---

# 13. US-106: Mobile OTP Login for Returning Users

## 13.1 Why This Story Exists

Traced while auditing the backend's actual API flow for returning users: there was no way for a mobile-OTP user to log back in. `POST /register/initiate` explicitly rejects an already-registered mobile with `ERROR_MOBILE_ALREADY_REGISTERED`, and US-101/US-102 (Google/Apple Sign-In) are documented as *"Optional Convenience Login"* — a shortcut around a primary mobile-OTP login path that had never itself been built. US-106 closes that gap.

## 13.2 Login Flow

```
Step 1: Initiate Login
  POST /api/v1/auth/login/initiate
  Body: { mobile }
  → Look up user by mobile — not found → ERROR_MOBILE_NOT_REGISTERED
  → assertLoginEligible(user) — see §13.3
  → Rate limit (shared otp_rate:{mobile} bucket with registration — see §13.4)
  → Generate OTP (6 digits), store SHA-256(OTP) in Redis: otp:{mobile}:LOGIN  TTL=300s
  → Call OtpPort.sendOtp(mobile, otp, LOGIN)
  → Return: { message: "OTP sent", otpExpiresInSeconds: 300 }

Step 2: Verify Login OTP
  POST /api/v1/auth/login/verify-mobile
  Body: { mobile, otp }
  → Fail-rate-limit check first (otp_fail:{mobile}), mirroring US-001's verify-mobile ordering
  → Re-fetch user by mobile, re-run assertLoginEligible(user)
    — this second check is what actually satisfies "account state changes between send and verify"
  → Validate OTP hash from Redis
  → Delete OTP + fail-counter keys
  → Issue JWT reflecting the account's CURRENT status/aadhaarVerified, read fresh from `user`
  → Return: AuthResponse { accessToken, refreshToken, aadhaarVerified, userId, status }
    -- `status` is what lets the client route correctly post-login (§1.3 exit criterion,
       previously a gap: neither the JWT nor AuthResponse carried it — see v1.9 changelog)

No state transition occurs anywhere in this flow — login only reads state, it never writes it.
Unlike registration's verify-mobile step (OTP_PENDING → EMAIL_VERIFICATION_PENDING), there is no
stateMachine.transition() call, no account_status_history row, and neither method is @Transactional.
```

## 13.3 State Eligibility — Who Can Log Back In

Cross-checked against the actual `UserAccountState` enum and §12.2's Access Control table:

| State | Login? | Result |
|---|---|---|
| NEW, OTP_PENDING | No | `ERROR_INVALID_STATE` — mobile was never verified, nothing to log into yet |
| EMAIL_VERIFICATION_PENDING | **Yes** | resumes at the email step |
| IDENTITY_VERIFICATION_PENDING | **Yes** | resumes at the Aadhaar step |
| ACTIVE | **Yes** | home |
| UNDER_REVIEW, RESTRICTED | **Yes** | per §12.2 — these states can log in, just can't list/buy |
| SUSPENDED | No | `ERROR_ACCOUNT_SUSPENDED` |
| BANNED, CLOSED | No | `ERROR_ACCOUNT_RECOVERY_REQUIRED` |

`assertLoginEligible` is called at **both** initiate and verify — calling it twice, not once, is what actually handles the "suspended/banned between send and verify" edge case from `user-stories.md`.

**Error code decision:** NEW/OTP_PENDING reuses `ERROR_INVALID_STATE` rather than a new code — `GoogleSignInService.initiateMobileForSocialLink` already throws this exact code for the analogous "account exists, registration incomplete" situation. Every other error code is either specified directly in the AC (`ERROR_MOBILE_NOT_REGISTERED`, `ERROR_ACCOUNT_SUSPENDED`) or reused verbatim from existing strings (`ERROR_ACCOUNT_RECOVERY_REQUIRED` copied from `GoogleSignInService`; `ERROR_INVALID_OTP`/`ERROR_OTP_EXPIRED`/`ERROR_OTP_RATE_LIMIT`/`ERROR_OTP_MAX_ATTEMPTS` copied from `UserRegistrationService`).

## 13.4 UserLoginService

A separate service from `UserRegistrationService` — matches this module's one-service-per-concern
split (`EmailVerificationService`, `AadhaarVerificationService`, `GoogleSignInService` are all
separate despite sharing OTP mechanics). Registration requires a mobile that does **not** exist;
login requires the opposite — bolting them together would blur that. No `UserAccountStateMachine`
or `JdbcTemplate` dependency, since login never transitions state or writes audit history.

```java
package com.valuex.auth.application.service;

@Service
@RequiredArgsConstructor
@Slf4j
public class UserLoginService {

    private final UserRepository userRepository;
    private final OtpPort otpPort;
    private final RedisCacheService redisCache;
    private final JwtTokenProvider jwtTokenProvider;
    private final ValuexProperties valuexProperties;
    private final SecureRandom secureRandom = new SecureRandom();

    public MessageResponse initiateLogin(InitiateLoginRequest request) {
        User user = findRegisteredUser(request.getMobile());
        assertLoginEligible(user);
        // rate-limit check on otp_rate:{mobile} -> ERROR_OTP_RATE_LIMIT
        // generate OTP, hash, redisCache.set("otp:" + mobile + ":" + OtpPurpose.LOGIN, hash, ttl)
        // otpPort.sendOtp(mobile, otp, OtpPurpose.LOGIN)
    }

    public AuthResponse verifyLogin(VerifyLoginOtpRequest request) {
        // rate-limit check on otp_fail:{mobile} first, mirrors verifyMobileOtp's exact ordering
        User user = findRegisteredUser(request.getMobile());
        assertLoginEligible(user);   // re-checked -- covers "state changed between send and verify"
        // fetch+compare OTP hash from otp:{mobile}:LOGIN -> ERROR_OTP_EXPIRED / ERROR_INVALID_OTP
        // delete both Redis keys
        return AuthResponse.builder()
            .accessToken(jwtTokenProvider.generateAccessToken(
                user.getId(), "USER", user.isAadhaarVerified(), "MOBILE_OTP"))
            .refreshToken(jwtTokenProvider.generateRefreshToken(user.getId()))
            .aadhaarVerified(user.isAadhaarVerified())   // read fresh from `user`, never cached
            .userId(user.getId().toString())
            .status(user.getStatus().name())             // lets the client route post-login (§13.2)
            .build();
    }

    private User findRegisteredUser(String mobile) {
        return userRepository.findByMobile(mobile)
            .orElseThrow(() -> new BusinessException("ERROR_MOBILE_NOT_REGISTERED",
                "No account found with this mobile number. Please register"));
    }

    private void assertLoginEligible(User user) {
        switch (user.getStatus()) {
            case NEW, OTP_PENDING -> throw new BusinessException("ERROR_INVALID_STATE",
                "Please complete your mobile number verification before logging in");
            case SUSPENDED -> throw new BusinessException("ERROR_ACCOUNT_SUSPENDED",
                "Your account is suspended. Please contact support");
            case BANNED, CLOSED -> throw new BusinessException("ERROR_ACCOUNT_RECOVERY_REQUIRED",
                "Your account requires recovery. Please contact support");
            default -> { /* EMAIL_VERIFICATION_PENDING, IDENTITY_VERIFICATION_PENDING,
                            ACTIVE, UNDER_REVIEW, RESTRICTED -- all allowed */ }
        }
    }
}
```

Trimmed for readability (full OTP generation/rate-limit code omitted) — see `UserLoginService.java`
for the exact current source.

## 13.5 `OtpPurpose.LOGIN` — Finally Used

`OtpPurpose` has carried an unused `LOGIN` value since US-001. Login OTPs use Redis key
`otp:{mobile}:LOGIN`, distinct from registration's `otp:{mobile}:MOBILE_VERIFY`. Rate-limit buckets
(`otp_rate:{mobile}`, `otp_fail:{mobile}`) are **shared** with registration's identical prefixes,
not purpose-scoped — safe because a mobile can never be simultaneously eligible for both
registration (requires `!existsByMobile`) and login (requires `existsByMobile`).

## 13.6 What Login Deliberately Does Not Touch

- **`account_status_history`** — an audit trail of state *transitions* only; login causes none.
- **Session/`jti` tracking** — the `user_sessions` design (§2.5, US-104/US-105) doesn't exist in
  real code yet. Login correctly does not add one; that's US-107/US-104 territory.
- **Aadhaar gating** — already uniformly enforced by `AadhaarGatingInterceptor` reading the
  `aadhaarVerified` JWT claim regardless of which flow issued the token. Since login reads
  `user.isAadhaarVerified()` fresh from the DB into that claim exactly like every other flow, no
  new gating logic is needed.

---

# 14. US-107: Access Token Refresh

## 14.1 Why This Story Exists

Every auth flow (US-001, US-101, US-106) already issues a `refreshToken` in its `AuthResponse` —
but until now, no endpoint anywhere accepted one. It was a dead value. Separately,
`JwtAuthenticationFilter` only checked signature + expiry, not the token's `type` claim, so a
refresh token could authenticate as a bearer access token today (with `role=null`, since refresh
tokens carry no role claim — a latent `ROLE_null` authority bug this story also closes).

## 14.2 The Stateless-vs-Rotation Decision

The story's AC asks for true single-use rotation (invalidate the old refresh token on use) and
logout-invalidation. Both require session/`jti` tracking infrastructure that **does not exist
anywhere in this codebase** — no `jti` claim, no `user_sessions` table, no Redis blocklist. That's
100% design-only, scoped to US-104/US-105 (§2.5), neither implemented. Logout (US-104) doesn't
exist at all — zero "logout" references anywhere in `src/main/java`.

The story's own "Related User Stories" text pre-authorizes exactly this fallback: *"if session
tracking doesn't exist, refresh operates statelessly (signature + expiry + type check only)."*
Building `jti`/Redis tracking now means designing infrastructure that US-104/US-105 will need to
define anyway (revocation-on-logout semantics, TTL alignment, theft-family invalidation) — likely
redone once those stories land with their own opinions. **Decision: implemented stateless.** See
§14.5 for exactly which ACs/edge cases this leaves unmet.

## 14.3 Refresh Flow

```
POST /api/v1/auth/refresh
Body: { refreshToken }
  → validateToken(token) — signature + expiry
    → invalid: isTokenExpired(token) ? ERROR_REFRESH_TOKEN_EXPIRED : ERROR_INVALID_REFRESH_TOKEN
  → isRefreshToken(token) — must be a refresh-type token, not access
    → false: ERROR_WRONG_TOKEN_TYPE
  → userRepository.findById(sub claim) — not found: ERROR_INVALID_REFRESH_TOKEN
  → assertAccountInGoodStanding(user) — same switch as UserLoginService.assertLoginEligible
    (§13.3), duplicated rather than extracted (see §14.4)
  → Issue a NEW access token + NEW refresh token, both re-reading status/aadhaarVerified fresh
    from `user` — never copied from the old token's claims
  → Return: AuthResponse { accessToken, refreshToken, aadhaarVerified, userId, status }

No state transition, no account_status_history row, not @Transactional — refresh only reads.
```

`JwtTokenProvider` gained three boolean-getter methods for this (matching the existing
`isAadhaarVerified(token)` convention): `isAccessToken`, `isRefreshToken`, `isTokenExpired`
(catches `ExpiredJwtException` specifically, so a merely-tampered token isn't misreported as
expired).

**Validation order constraint:** every `JwtTokenProvider` claim getter goes through the private
`parseClaims()`, which throws on bad signature/expiry — so the `type` claim cannot be read before
signature+expiry is already implicitly checked. The achievable order is `validateToken` →
`isRefreshToken` → user lookup → good-standing, not "type first."

## 14.4 Good-Standing Check: Duplicated, Not Extracted

`UserLoginService.assertLoginEligible` (§13.3/§13.4) is directly exercised by ~4 parameterized
tests via `@InjectMocks`-over-mocks. Extracting it to a shared component would force those tests
to add a new non-mocked collaborator — real churn to a passing file, for a 4-branch switch that
isn't worth a new abstraction. `TokenRefreshService.assertAccountInGoodStanding` duplicates the
same ~12 lines instead, matching this module's existing style (small duplication across
sibling services is already the house pattern — see `UserLoginService`'s own header comment on
why it isn't folded into `UserRegistrationService`). Same codes/messages: `NEW`/`OTP_PENDING` →
`ERROR_INVALID_STATE`, `SUSPENDED` → `ERROR_ACCOUNT_SUSPENDED`, `BANNED`/`CLOSED` →
`ERROR_ACCOUNT_RECOVERY_REQUIRED`, everything else allowed.

## 14.5 ACs and Edge Cases NOT Satisfied by This Scope

Documented explicitly, not silently dropped:

1. **Old refresh token is not invalidated on use** — stays valid until its own 7-day expiry. The
   single biggest gap from going stateless.
2. **"Already used once (rotated out)" cannot be detected** — a still-unexpired refresh token can
   be replayed indefinitely.
3. **"Logout invalidates the refresh token" is unmeetable regardless of design choice** — US-104
   (logout) doesn't exist in the codebase yet.
4. **"Replayed rotated-out token → theft, invalidate token family"** — explicitly conditional in
   the story text on session tracking existing; N/A here by the story's own qualification.
5. **Two concurrent refresh calls near expiry both succeed independently** — no mutual exclusion,
   a direct consequence of no rotation-invalidation.
6. **Clock skew at the expiry boundary** — pre-existing, systemic JJWT default-tolerance property
   of `JwtTokenProvider`, not newly introduced or newly fixed here.
7. **An *expired* access token submitted to `/refresh`** surfaces as
   `ERROR_INVALID_REFRESH_TOKEN`/`ERROR_REFRESH_TOKEN_EXPIRED` rather than `ERROR_WRONG_TOKEN_TYPE`
   (type can only be read after a successful parse). Same end-user outcome either way (log in
   again).
8. **`authProvider` claim resets to `MOBILE_OTP` on every refresh**, regardless of the original
   login method — currently inert, since nothing reads this claim downstream today.

---

# 15. Database Schema

## 8.1 Flyway Migration: V2__auth_schema.sql

```sql
-- Extend users table from V1
ALTER TABLE users ADD COLUMN aadhaar_hash VARCHAR(64) UNIQUE;
ALTER TABLE users ADD COLUMN aadhaar_name VARCHAR(255);
ALTER TABLE users ADD COLUMN aadhaar_verified BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE users ADD COLUMN display_name VARCHAR(50);
ALTER TABLE users ADD COLUMN profile_photo_url VARCHAR(500);
ALTER TABLE users ADD COLUMN city VARCHAR(255);
ALTER TABLE users ADD COLUMN terms_accepted_at TIMESTAMP;
ALTER TABLE users ADD COLUMN consent_given_at TIMESTAMP;
ALTER TABLE users ADD COLUMN suspension_lifted_at TIMESTAMP;

CREATE INDEX idx_users_aadhaar_hash ON users(aadhaar_hash);

-- Aadhaar verification audit trail
CREATE TABLE aadhaar_verification_attempts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    aadhaar_hash VARCHAR(64) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    transaction_id VARCHAR(255),
    status VARCHAR(50) NOT NULL,     -- INITIATED, SUCCESS, FAILED, TIMEOUT
    failure_reason VARCHAR(500),
    ip_address VARCHAR(50),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_aadhaar_attempts_user ON aadhaar_verification_attempts(user_id);
CREATE INDEX idx_aadhaar_attempts_hash ON aadhaar_verification_attempts(aadhaar_hash);

-- Account state history
CREATE TABLE user_state_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    from_state VARCHAR(50),
    to_state VARCHAR(50) NOT NULL,
    action VARCHAR(100) NOT NULL,
    actor_id UUID,        -- null = system, set = admin user
    reason VARCHAR(500),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_state_history_user ON user_state_history(user_id);
CREATE INDEX idx_state_history_created ON user_state_history(created_at);

-- Notifications
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    status VARCHAR(50) NOT NULL DEFAULT 'EVENT_TRIGGERED',
    event_type VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    body TEXT,
    deep_link VARCHAR(500),
    priority VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
    read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP,
    expires_at TIMESTAMP
);

CREATE INDEX idx_notifications_user ON notifications(user_id, read, created_at DESC);

-- Social login accounts (Google, Apple)
-- (See US-101/US-102 sections for full DDL)
-- user_social_accounts table defined in Section 4.3
```

## 8.2 Flyway Migration: V6__replace_profile_photo_with_avatar.sql

```sql
-- US-003 redesign (v1.4): avatar selection replaces free-form photo upload.
-- profile_photo_url (added in V2) is superseded — the upload endpoint that
-- populated it has been removed; no code path writes to it anymore.
ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_id VARCHAR(50);
UPDATE users SET avatar_id = 'avatar-01' WHERE avatar_id IS NULL;
ALTER TABLE users ALTER COLUMN avatar_id SET DEFAULT 'avatar-01';
ALTER TABLE users ALTER COLUMN avatar_id SET NOT NULL;
ALTER TABLE users DROP COLUMN IF EXISTS profile_photo_url;
```

## 8.3 Flyway Migration: V7__session_and_security_schema.sql

```sql
-- Session tracking for logout / multi-device management (US-104, US-105)
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY,                      -- == JWT jti
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    refresh_token_hash VARCHAR(64) NOT NULL,  -- SHA-256, never plain
    device_info VARCHAR(255),
    ip_address VARCHAR(50),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_active_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP,
    revoked_reason VARCHAR(100)
);

CREATE INDEX idx_user_sessions_user ON user_sessions(user_id, revoked_at);

-- Mobile/email change audit trail (mirrors aadhaar_verification_attempts pattern) (US-105)
CREATE TABLE contact_change_attempts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    change_type VARCHAR(20) NOT NULL,   -- MOBILE, EMAIL
    old_value VARCHAR(255),
    new_value VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,        -- INITIATED, SUCCESS, FAILED
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_contact_change_user ON contact_change_attempts(user_id);
```

---

# 16. API Design

## 16.1 Auth Endpoints

### POST /api/v1/auth/register/initiate
**Request:**
```json
{
  "mobile": "9876543210",
  "termsAccepted": true,
  "consentGiven": true
}
```
**Response 200:**
```json
{
  "success": true,
  "data": {
    "message": "OTP sent to your mobile number",
    "otpExpiresInSeconds": 300
  }
}
```
**Errors:** `ERROR_MOBILE_ALREADY_REGISTERED`, `ERROR_INVALID_MOBILE`

---

### POST /api/v1/auth/register/verify-mobile
**Request:**
```json
{
  "mobile": "9876543210",
  "otp": "123456"
}
```
**Response 200:**
```json
{
  "success": true,
  "data": {
    "accessToken": "eyJ...",
    "refreshToken": "eyJ...",
    "aadhaarVerified": false,
    "userId": "uuid",
    "status": "EMAIL_VERIFICATION_PENDING"
  }
}
```
**Errors:** `ERROR_INVALID_OTP`, `ERROR_OTP_EXPIRED`

---

### POST /api/v1/auth/login/initiate
See §13 (US-106) for the full login flow.
**Request:**
```json
{ "mobile": "9876543210" }
```
**Response 200:**
```json
{
  "success": true,
  "data": {
    "message": "OTP sent to your mobile number",
    "otpExpiresInSeconds": 300
  }
}
```
**Errors:** `ERROR_MOBILE_NOT_REGISTERED`, `ERROR_OTP_RATE_LIMIT`, `ERROR_INVALID_STATE`
(mobile never verified), `ERROR_ACCOUNT_SUSPENDED`, `ERROR_ACCOUNT_RECOVERY_REQUIRED`

---

### POST /api/v1/auth/login/verify-mobile
**Request:**
```json
{ "mobile": "9876543210", "otp": "123456" }
```
**Response 200:**
```json
{
  "success": true,
  "data": {
    "accessToken": "eyJ...",
    "refreshToken": "eyJ...",
    "aadhaarVerified": true,
    "userId": "uuid",
    "status": "ACTIVE"
  }
}
```
Note: `aadhaarVerified` and `status` both reflect the account's **current** DB state at login
time (e.g. a user who finished Aadhaar verification since their last login gets
`aadhaarVerified: true` immediately). The client routes on `status` — `ACTIVE` goes to the
home screen; anything short of `ACTIVE` (e.g. `EMAIL_VERIFICATION_PENDING`,
`IDENTITY_VERIFICATION_PENDING`) resumes registration at that exact step. See §13.4.
**Errors:** `ERROR_MOBILE_NOT_REGISTERED`, `ERROR_OTP_MAX_ATTEMPTS`, `ERROR_OTP_EXPIRED`,
`ERROR_INVALID_OTP`, `ERROR_INVALID_STATE`, `ERROR_ACCOUNT_SUSPENDED`, `ERROR_ACCOUNT_RECOVERY_REQUIRED`

---

### POST /api/v1/auth/refresh
See §14 (US-107) for the full design, including which ACs this scope does **not** satisfy.
**Request:**
```json
{ "refreshToken": "eyJ..." }
```
**Response 200:**
```json
{
  "success": true,
  "data": {
    "accessToken": "eyJ...",
    "refreshToken": "eyJ...",
    "aadhaarVerified": true,
    "userId": "uuid",
    "status": "ACTIVE"
  }
}
```
Note: a NEW refresh token is issued on every call, but the **old one is not invalidated** — it
remains valid until its own natural expiry (no single-use rotation; stateless design, §14.2).
`aadhaarVerified` and `status` are re-read fresh from the database, never copied from the
submitted token's claims.
**Errors:** `ERROR_INVALID_REFRESH_TOKEN`, `ERROR_REFRESH_TOKEN_EXPIRED`, `ERROR_WRONG_TOKEN_TYPE`,
`ERROR_INVALID_STATE`, `ERROR_ACCOUNT_SUSPENDED`, `ERROR_ACCOUNT_RECOVERY_REQUIRED`

---

### POST /api/v1/auth/email/send-otp
**Auth:** Bearer token required
**Request:**
```json
{ "email": "user@example.com" }
```
**Response 200:**
```json
{
  "success": true,
  "data": { "message": "OTP sent to user@example.com", "otpExpiresInSeconds": 300 }
}
```
**Errors:** `ERROR_INVALID_EMAIL`, `ERROR_OTP_RATE_LIMIT_EXCEEDED`

---

### POST /api/v1/auth/email/verify-otp
**Auth:** Bearer token required
**Request:**
```json
{ "email": "user@example.com", "otp": "483920" }
```
**Response 200:**
```json
{
  "success": true,
  "data": { "message": "Email verified successfully" }
}
```
**Errors:** `ERROR_INVALID_OTP`, `ERROR_OTP_EXPIRED`

---

### POST /api/v1/auth/register/skip-aadhaar
**Auth:** Bearer token required
**Response 200:**
```json
{
  "success": true,
  "data": {
    "accessToken": "eyJ...",
    "refreshToken": "eyJ...",
    "aadhaarVerified": false,
    "userId": "uuid",
    "status": "ACTIVE"
  }
}
```
Note: Account transitions to `ACTIVE`. `aadhaarVerified` remains `false` — Aadhaar gate
blocks first transaction attempt.

---

### POST /api/v1/auth/aadhaar/initiate
**Auth:** Bearer token required
**Request:**
```json
{
  "aadhaarNumber": "123456789012",
  "consentToken": "user-provided-consent-timestamp"
}
```
**Response 200:**
```json
{
  "success": true,
  "data": {
    "transactionId": "txn-abc123",
    "message": "OTP sent to Aadhaar-linked mobile"
  }
}
```
**Errors:** `ERROR_AADHAAR_ALREADY_USED`, `ERROR_INVALID_AADHAAR`, `ERROR_AADHAAR_SERVICE_UNAVAILABLE`

---

### POST /api/v1/auth/aadhaar/verify
**Auth:** Bearer token required
**Request:**
```json
{
  "transactionId": "txn-abc123",
  "otp": "123456"
}
```
**Response 200:**
```json
{
  "success": true,
  "data": {
    "accessToken": "eyJ...",
    "refreshToken": "eyJ...",
    "aadhaarVerified": true,
    "verifiedName": "A**** K****",
    "status": "ACTIVE"
  }
}
```

---

## 16.2 Social Login Endpoints

All three Google endpoints are **public** (no Bearer token required).

### POST /api/v1/auth/social/google
**Request:**
```json
{ "idToken": "<Google ID token from client>" }
```
**Response 200 — returning user (already linked):**
```json
{
  "success": true,
  "data": {
    "requiresMobileVerification": false,
    "accessToken": "eyJ...",
    "refreshToken": "eyJ...",
    "aadhaarVerified": false,
    "userId": "uuid"
  }
}
```
**Response 200 — new user (mobile verification required):**
```json
{
  "success": true,
  "data": {
    "requiresMobileVerification": true,
    "socialSessionToken": "3f8a1c2d-e5f6-...",
    "googleEmail": "alice@gmail.com"
  }
}
```
**Errors:** `ERROR_INVALID_GOOGLE_TOKEN`

---

### POST /api/v1/auth/social/google/initiate-mobile
**Request:**
```json
{
  "socialSessionToken": "3f8a1c2d-e5f6-...",
  "mobile": "9876543210",
  "termsAccepted": true,
  "consentGiven": true
}
```
**Response 200:**
```json
{
  "success": true,
  "data": { "message": "OTP sent", "otpExpiresInSeconds": 300 }
}
```
**Errors:** `ERROR_SOCIAL_SESSION_EXPIRED`, `ERROR_INVALID_STATE`, `ERROR_OTP_RATE_LIMIT_EXCEEDED`

---

### POST /api/v1/auth/social/google/verify-mobile
**Request:**
```json
{
  "socialSessionToken": "3f8a1c2d-e5f6-...",
  "mobile": "9876543210",
  "otp": "483920"
}
```
**Response 200:**
```json
{
  "success": true,
  "data": {
    "accessToken": "eyJ...",
    "refreshToken": "eyJ...",
    "aadhaarVerified": false,
    "userId": "uuid",
    "status": "IDENTITY_VERIFICATION_PENDING"
  }
}
```
Note: `status` is `IDENTITY_VERIFICATION_PENDING` for a newly created Google user (email
already verified by Google, so registration's email-OTP step is skipped — see
`GoogleSignInService.createNewSocialUser`) or the linked account's existing `status` when
linking Google to an already-registered mobile number.
**Errors:** `ERROR_SOCIAL_SESSION_EXPIRED`, `ERROR_INVALID_OTP`, `ERROR_OTP_EXPIRED`

---

~~POST /api/v1/auth/social/apple~~ — **Dropped (US-102 removed from scope)**

---

## 16.3 User Profile Endpoints

### GET /api/v1/users/me
**Auth:** Bearer token required
**Response 200:**
```json
{
  "success": true,
  "data": {
    "userId": "uuid",
    "mobile": "98*****210",
    "displayName": "Abhay",
    "aadhaarName": "A**** K****",
    "aadhaarVerified": true,
    "avatarId": "avatar-01",
    "city": "Bengaluru",
    "status": "ACTIVE",
    "memberSince": "2026-07-09T00:00:00Z"
  }
}
```

---

### PATCH /api/v1/users/me
**Auth:** Bearer token required
**Request:**
```json
{
  "displayName": "Abhay Kumar",
  "city": "Bengaluru"
}
```

---

### GET /api/v1/avatars
**Auth:** Bearer token required
**Response 200:**
```json
{
  "success": true,
  "data": {
    "avatarIds": ["avatar-01", "avatar-02", "avatar-03", "..."],
    "defaultAvatarId": "avatar-01"
  }
}
```

---

### PUT /api/v1/users/me/avatar
**Auth:** Bearer token required
**Request:**
```json
{ "avatarId": "avatar-07" }
```
**Response 200:** same shape as `GET /api/v1/users/me`, with `avatarId` updated.
**Errors:** `ERROR_INVALID_AVATAR`

---

## 16.4 Notifications Endpoints

> **Not implemented.** US-077 hasn't been built — no `Notification` entity, table, or controller exists.
> These endpoints are design only.

### GET /api/v1/notifications
**Auth:** Bearer token required
**Query params:** `page=0&size=20&unreadOnly=false`
**Response header:** `X-Unread-Notifications: 3`

### PATCH /api/v1/notifications/{id}/read
**Auth:** Bearer token required

### PATCH /api/v1/notifications/read-all
**Auth:** Bearer token required

---

## 16.5 Profile Hub Endpoint

### GET /api/v1/users/me/menu-summary
**Auth:** Bearer token required
**Response 200:**
```json
{
  "success": true,
  "data": {
    "displayName": "Abhay",
    "avatarId": "avatar-01",
    "aadhaarVerified": true,
    "memberSince": "2026-07-09T00:00:00Z",
    "badges": { "NOTIFICATIONS": 3 }
  }
}
```
Note: badge keys for menu items whose owning sprint hasn't shipped yet are simply absent from `badges` (see Section 8.3).

---

## 16.6 Logout Endpoint

**Implemented (US-104).** Blocklists the calling access token's `jti` (and, since access+refresh
now share a `jti` per issuance, the paired refresh token too) — see §9.

### POST /api/v1/auth/logout
**Auth:** Bearer token required
**Response 200:**
```json
{
  "success": true,
  "data": { "message": "Logged out successfully" }
}
```
Idempotent only within the token's validity — see §9.5 for why a later call with the same,
now-blocklisted token returns `401` rather than a second `200`.
**Errors:** `ERROR_LOGOUT_FAILED` (defined, not reachable in this design — see §9.6)

---

## 16.7 Account Security Endpoints

> **Not implemented.** US-105 hasn't been built — no `AccountSecurityController`/`AccountSecurityService`
> exists. Mobile/email change, session listing, and "log out of other devices" are all design only.

### GET /api/v1/users/me/account-security
**Auth:** Bearer token required
**Response 200:**
```json
{
  "success": true,
  "data": {
    "mobile": "98*****210",
    "email": "a****@example.com",
    "aadhaarVerified": true,
    "deleteAccountUrl": "/api/v1/users/me/deletion-request"
  }
}
```

### POST /api/v1/users/me/mobile/change/initiate
**Auth:** Bearer token required
**Request:** `{ "newMobile": "9123456780" }`
**Response 200:** `{ "message": "OTP sent", "otpExpiresInSeconds": 300 }`
**Errors:** `ERROR_MOBILE_ALREADY_REGISTERED`, `ERROR_OTP_RATE_LIMIT_EXCEEDED`

### POST /api/v1/users/me/mobile/change/verify
**Auth:** Bearer token required
**Request:** `{ "newMobile": "9123456780", "otp": "123456" }`
**Response 200:** `{ "message": "Mobile number updated" }`
**Errors:** `ERROR_INVALID_OTP`, `ERROR_OTP_EXPIRED`

### POST /api/v1/users/me/email/change/initiate
### POST /api/v1/users/me/email/change/verify
Same contract as mobile change, against `newEmail`.
**Errors:** `ERROR_EMAIL_ALREADY_REGISTERED`, `ERROR_INVALID_OTP`, `ERROR_OTP_EXPIRED`

### GET /api/v1/users/me/sessions
**Auth:** Bearer token required
**Response 200:**
```json
{
  "success": true,
  "data": [
    { "sessionId": "uuid", "deviceInfo": "iPhone 14 / iOS 18", "ipAddress": "49.x.x.x",
      "createdAt": "2026-08-01T10:00:00Z", "lastActiveAt": "2026-08-06T09:00:00Z", "isCurrent": true },
    { "sessionId": "uuid", "deviceInfo": "Chrome / Windows", "ipAddress": "103.x.x.x",
      "createdAt": "2026-07-28T18:00:00Z", "lastActiveAt": "2026-07-30T12:00:00Z", "isCurrent": false }
  ]
}
```

### POST /api/v1/users/me/sessions/revoke-others
**Auth:** Bearer token required
**Response 200:** `{ "message": "Logged out of 1 other device(s)" }`
**Errors:** `ERROR_NO_OTHER_SESSIONS`

---

# 17. Security Considerations

## 17.1 Social Login Token Security

| Rule | Detail |
|---|---|
| Server-side validation only | Google and Apple tokens are NEVER trusted from the client — always re-validated server-side |
| Google token validation | Call `https://oauth2.googleapis.com/tokeninfo?id_token={token}` — verify `email_verified == true`, `aud` in configured client-IDs list (web, Android, iOS) |
| `email_verified` enforcement | `HttpGoogleTokenAdapter` rejects tokens where `email_verified != "true"`. Unverified Google emails are never accepted. |
| Multiple client IDs | `valuex.oauth.google.client-ids` holds three IDs (web, Android, iOS). The `aud` claim must match one of them. |
| No client-side shortcut | Flutter plugins return validated tokens — but backend must re-validate independently |
| ~~Apple token validation~~ | ~~US-102 dropped~~ |

## 17.2 Aadhaar Data Handling

| Data | Storage | Notes |
|---|---|---|
| Raw Aadhaar number | **Never stored** | Sent to provider API only, in-memory only |
| Aadhaar hash | `users.aadhaar_hash` | SHA-256 only, for uniqueness check |
| Aadhaar name | `users.aadhaar_name` | Masked (A**** K****) from provider |
| Verification attempt | `aadhaar_verification_attempts` | Audit trail with hash, not plain number |

## 17.3 OTP Security

- OTP is 6 digits, alphanumeric entropy optional (config)
- Stored as `SHA-256(otp)` in Redis — never plain text
- Rate limit: max 3 OTP send requests per mobile per 10 minutes (Redis counter)
- OTP invalidated immediately after successful use
- Max 5 failed OTP attempts before lockout (10-minute cooldown)

## 17.4 JWT Claims

**As actually implemented today** (`JwtTokenProvider.java`):

```json
{
  "sub": "user-uuid",
  "type": "access",
  "role": "USER",
  "aadhaarVerified": false,
  "authProvider": "MOBILE_OTP",
  "iat": 1720483200,
  "exp": 1720486800
}
```

`authProvider` values: `MOBILE_OTP`, `GOOGLE`

Note: `accountStatus` is **not** included in the JWT — state is always read from the database.
The `type` claim distinguishes access tokens from refresh tokens (`"access"` | `"refresh"`).

**US-107 update:** `JwtTokenProvider` gained `isAccessToken(token)`, `isRefreshToken(token)`, and
`isTokenExpired(token)` boolean getters (matching the existing `isAadhaarVerified(token)`
convention). `JwtAuthenticationFilter` now calls `isAccessToken(token)` before setting a
`SecurityContext` authentication — a refresh token presented as a bearer token is rejected
(logged as a warning, request still proceeds unauthenticated) instead of silently authenticating
with a `role=null` / `ROLE_null` authority as it did before. See §14.3.

**US-104 update:** `jti` is now real. Every access and refresh token carries a `jti` (JWT ID) claim,
shared between an access token and its paired refresh token when minted together, and reused
across refreshes by `TokenRefreshService` rather than rotated. `JwtTokenProvider` gained
`getJtiFromToken(token)` and `getExpirationFromToken(token)`. This still does **not** make refresh
tokens single-use — the old one stays valid until its own expiry (§14.2) — `jti` is used only for
logout revocation (§9), not rotation. Don't assume single-use rotation exists anywhere in the real
token flow until that's separately built.

## 17.5 Rate Limiting (via Redis)

| Endpoint | Limit | Window |
|---|---|---|
| `/register/initiate` | 3 requests | per mobile per 10 min |
| `/login/initiate` | 3 requests | per mobile per 10 min (shared `otp.max-send-attempts-per-window` config) |
| `/login/verify-mobile` (fail) | 5 attempts | per mobile per 10 min (shared `otp.max-verify-attempts-per-window` config) |
| `/email/send-otp` | 3 requests | per user per 10 min |
| `/email/verify-otp` (fail) | 5 attempts | per user per 10 min |
| `/aadhaar/initiate` | 3 requests | per user per 10 min |
| `/aadhaar/verify` (fail) | 5 attempts | per user per 10 min |
| `/social/google/initiate-mobile` | 3 requests | per social session per 10 min |
| `/users/me/mobile/change/initiate` | 3 requests | per user per 10 min |
| `/users/me/email/change/initiate` | 3 requests | per user per 10 min |
| `/auth/logout` | Not implemented | this row was a speculative abuse guard in the original design; not in US-104's AC/edge cases, and repeated logout calls are self-limiting (each blocklists the token used, so an attacker gains nothing by calling it repeatedly) — skipped as unneeded scope, not an oversight |

## 17.6 Session & Token Revocation (US-104 / US-105)

| Rule | Detail |
|---|---|
| Refresh token storage | `user_sessions` (and therefore this row) does not exist in the US-104 implementation — there is nothing to store. Will apply once US-105 adds persisted sessions. |
| Revocation propagation | **Implemented as designed.** `blocklist:{jti}` TTL is set to the access token's *remaining* lifetime — never longer, so Redis never accumulates stale keys |
| Blocklist check cost | **Implemented as designed.** One Redis `EXISTS` per authenticated request, added to the existing `JwtAuthenticationFilter` — no additional DB round-trip |
| Mobile/email change security | US-105 territory — not implemented yet |
| Session enumeration | US-105 territory — not implemented yet; `GET /users/me/sessions` doesn't exist |

---

# 18. Testing Strategy

## 18.1 Unit Tests

### UserRegistrationService Tests
- `shouldSendOtpAndTransitionStateToOtpPending`
- `shouldRejectAlreadyRegisteredMobile`
- `shouldVerifyOtpAndIssueJwt`
- `shouldRejectInvalidOtp`
- `shouldRejectExpiredOtp`
- `shouldIncrementFailedOtpCount`

### AadhaarVerificationService Tests
- `shouldInitiateVerificationAndStoreTransactionId`
- `shouldRejectDuplicateAadhaarHash`
- `shouldCompleteVerificationAndTransitionToActive`
- `shouldHandleProviderTimeout`
- `shouldHandleProviderUnavailable`

### UserAccountStateMachine Tests (US-088)
- `shouldAllowValidTransitions`
- `shouldRejectInvalidTransition`
- `shouldAllowSkipAadhaarTransition`

### AadhaarGatingInterceptor Tests
- `shouldAllowRequestWhenAadhaarVerified`
- `shouldBlockRequestWhenAadhaarNotVerified`
- `shouldPassThroughEndpointsWithoutAnnotation`

### EmailVerificationService Tests
- `shouldSendEmailOtpSuccessfully`
- `shouldRejectInvalidEmailFormat`
- `shouldVerifyEmailOtpAndTransitionState`
- `shouldRejectInvalidEmailOtp`
- `shouldRejectExpiredEmailOtp`
- `shouldEnforceEmailOtpRateLimit`

### GoogleSignInService Tests (US-101)
- `shouldReturnJwtForReturningGoogleUser` (Flow B)
- `shouldReturnSocialSessionTokenForNewGoogleUser` (Flow A)
- `shouldSendMobileOtpForNewGoogleUser`
- `shouldVerifyOtpAndCreateNewUserForGoogle`
- `shouldLinkGoogleToExistingActiveAccount` (Flow C)
- `shouldRejectLinkWhenExistingAccountNotActive`
- `shouldRejectLinkWhenGoogleAlreadyLinked`
- `shouldRejectExpiredSocialSession`
- `shouldRejectInvalidGoogleToken`
- `shouldRejectOtpMismatchInSocialFlow`
- `shouldEnforceOtpRateLimitInSocialFlow`
- `shouldDeleteSocialSessionAfterSuccessfulVerification`
- `shouldRejectInvalidGoogleToken` (HttpGoogleTokenAdapter)
- `shouldRejectUnverifiedEmailGoogleToken` (HttpGoogleTokenAdapter)

### AuthController Tests (Google endpoints)
- `shouldReturnJwtWhenGoogleUserAlreadyLinked`
- `shouldReturnSessionTokenWhenGoogleUserIsNew`
- `shouldReturnOkWhenSocialMobileInitiated`
- `shouldReturnJwtWhenSocialMobileOtpVerified`

~~Apple tests~~ — dropped with US-102

### UserLoginService Tests (US-106) — implemented, real method names

`UserLoginServiceTest`:
- `shouldSendOtpWhenAccountIsActive`
- `shouldRejectInitiateWhenMobileNotRegistered`
- `shouldRejectInitiateWhenRateLimitExceeded`
- `shouldRejectInitiateWhenMobileNeverVerified` — `@ParameterizedTest @EnumSource(names={"NEW","OTP_PENDING"})`
- `shouldRejectInitiateWhenAccountSuspended`
- `shouldRejectInitiateWhenAccountBannedOrClosed` — `@ParameterizedTest @EnumSource(names={"BANNED","CLOSED"})`
- `shouldAllowInitiateForEveryOtherEligibleState` — `@ParameterizedTest @EnumSource(names={"EMAIL_VERIFICATION_PENDING","IDENTITY_VERIFICATION_PENDING","UNDER_REVIEW","RESTRICTED"})`
- `shouldVerifyOtpAndReturnJwtReflectingCurrentDbState`
- `shouldReturnStatusReflectingAccountsCurrentStateNotAHardcodedValue` — `@ParameterizedTest @EnumSource(names={"EMAIL_VERIFICATION_PENDING","IDENTITY_VERIFICATION_PENDING","ACTIVE","UNDER_REVIEW","RESTRICTED"})`; added in v1.9 alongside the `AuthResponse.status` fix
- `shouldRejectVerifyWhenMobileNotRegistered`
- `shouldRejectVerifyWhenAccountBecameSuspendedBetweenSendAndVerify`
- `shouldRejectVerifyWhenOtpExpired`
- `shouldRejectVerifyWhenOtpIsWrong`
- `shouldRejectVerifyWhenMaxFailAttemptsExceeded`
- `shouldNeverMutateUserDuringLogin` — asserts `verify(userRepository, never()).save(...)`/`saveAndFlush(...)`; login never writes state

`AuthControllerTest`:
- `shouldReturnOkWhenLoginInitiated`
- `shouldReturnJwtWhenLoginOtpVerified`

### TokenRefreshService Tests (US-107) — implemented, real method names

`TokenRefreshServiceTest`:
- `shouldIssueNewTokenPairForValidRefreshToken`
- `shouldBuildNewAccessTokenFromFreshDbStateNotOldTokenClaims` — verifies `generateAccessToken` is
  called with the DB user's live `aadhaarVerified`/role, not anything copied from the old token
- `shouldRejectExpiredRefreshToken`
- `shouldRejectTamperedRefreshTokenThatIsNotExpired`
- `shouldRejectAccessTokenSubmittedToRefreshEndpoint`
- `shouldRejectWhenNoUserMatchesTheTokenSubject`
- `shouldRejectWhenAccountNeverCompletedMobileVerification` — `@ParameterizedTest @EnumSource(names={"NEW","OTP_PENDING"})`
- `shouldRejectWhenAccountSuspended`
- `shouldRejectWhenAccountBannedOrClosed` — `@ParameterizedTest @EnumSource(names={"BANNED","CLOSED"})`
- `shouldAllowRefreshForEveryOtherEligibleState` — `@ParameterizedTest @EnumSource(names={"EMAIL_VERIFICATION_PENDING","IDENTITY_VERIFICATION_PENDING","ACTIVE","UNDER_REVIEW","RESTRICTED"})`

`AuthControllerTest`:
- `shouldReturnNewTokensWhenRefreshSucceeds`

`JwtTokenProviderTest` — additions for the new boolean getters:
- `isAccessTokenDistinguishesTokenType`
- `isRefreshTokenDistinguishesTokenType`
- `isTokenExpiredTrueForExpiredToken`, `isTokenExpiredFalseForValidToken`, `isTokenExpiredFalseForGarbageString`

`JwtAuthenticationFilterTest` — additions for the bearer-token type-check fix:
- `shouldNotSetAuthenticationWhenTokenIsRefreshType` (new)
- `shouldSetAuthenticationWhenTokenIsValid` and `shouldStillCallFilterChainWhenTokenExtractionFails` both updated to stub `isAccessToken(token)` → `true` — required once the filter started checking it, otherwise the unstubbed boolean mock defaults to `false` and silently breaks authentication under strict-stubs Mockito

### US-003 Tests — implemented, real method names

`UserProfileServiceTest`:
- `shouldReturnProfileForExistingUser`
- `shouldThrowNotFoundWhenGettingMissingUser`
- `shouldUpdateDisplayNameAndCity`
- `shouldLeaveFieldsUnchangedWhenNotProvided`
- `shouldNeverExposeAadhaarNameAsEditable`
- `shouldReturnAvatarCatalogFromConfig`
- `shouldSelectAvatarWhenIdIsInCatalog`
- `shouldRejectAvatarIdNotInCatalog`

`UserProfileControllerTest`:
- `shouldReturnProfileForAuthenticatedUser`
- `shouldReturnUpdatedProfileOnPatch`
- `shouldReturnUpdatedProfileWhenAvatarSelected`
- `shouldReturnMenuSummaryForAuthenticatedUser`

`AvatarControllerTest`:
- `shouldReturnAvatarCatalog`

### ProfileMenuService Tests (US-103) — implemented, real method names

The three names below (`shouldAggregateBadgesFromAllRegisteredProviders`, `shouldOmitBadgeKeyWhenNoProviderRegistered`, `shouldReturnZeroCountWhenNoUnreadNotifications`) were this section's original *design-time guess* and don't match what was actually written — corrected here:

`ProfileMenuServiceTest`:
- `shouldReturnSummaryWithEmptyBadgesWhenNoProvidersRegistered`
- `shouldAggregateBadgeCountsFromAllRegisteredProviders`
- `shouldReturnUnmodifiableBadgesMap` — added during PR review (§8.4/§16)
- `shouldOmitBadgeAndContinueWhenAProviderThrows` — added during PR review (per-provider isolation)
- `shouldOmitBadgeWhenProviderReturnsNegativeCount` — added during PR review
- `shouldThrowWhenTwoProvidersShareTheSameMenuKey` — added during PR review (constructor validation)
- `shouldThrowNotFoundWhenUserMissing`

`ProfileMenuServiceWiringIntegrationTest` — added during PR review, a distinct kind of test from the rest of this list:
- `shouldAutowireEveryRegisteredBadgeProviderBean` — a narrow, Docker-free Spring context test (own `@Configuration` registering two stub `ProfileMenuBadgeProvider` beans + a `@MockBean UserRepository`) proving Spring's `List<ProfileMenuBadgeProvider>` collection actually works end-to-end. Every other test in this document's "Unit Tests" section constructs its service directly with a hand-built `List.of(...)` or Mockito mocks — none of them touch the real Spring container, so none of them could have caught a wiring bug. This is the one test in the whole module that does.

### LogoutService Tests (US-104) — implemented, real method names

There is no `SessionService` in the as-built design (§9) — no persisted session row to create,
revoke, or scope by owning user, since there's no `user_sessions` table. `LogoutService` only
blocklists a jti; the names below replace this section's original `SessionService`-shaped guess.

`LogoutServiceTest`:
- `shouldBlocklistTheTokensJtiForItsRemainingLifetime`
- `shouldFloorTtlAtOneSecondForAnAlmostExpiredToken`

`TokenRefreshServiceTest` gained the US-104-relevant cases:
- `shouldRejectRefreshWhenSessionHasBeenLoggedOut`
- `shouldReuseIncomingTokensJtiInTheReissuedPair`

### JwtAuthenticationFilter Tests (US-104) — implemented, real method names
`JwtAuthenticationFilterTest`:
- `shouldNotSetAuthenticationWhenTokenIsBlocklisted`
- `shouldSetAuthenticationWhenTokenIsValid` — extended to also cover the non-blocklisted path
  through the new check

### AccountSecurityService Tests (US-105) — design only, not written (story not implemented)
- `shouldInitiateMobileChangeAndSendOtpToNewNumber`
- `shouldRejectMobileChangeWhenNewNumberAlreadyRegistered`
- `shouldVerifyMobileChangeAndUpdateUser`
- `shouldKeepOldMobileActiveUntilNewOneVerified`
- `shouldMirrorFlowForEmailChange`
- `shouldListActiveSessionsWithCurrentSessionFlagged`
- `shouldRevokeAllSessionsExceptCaller`
- `shouldRejectRevokeOthersWhenNoOtherSessionsExist`

## 18.2 Integration Tests

**Illustrative — `UserRegistrationIntegrationTest` below does not exist.** No `@AutoConfigureMockMvc`
request-level integration test has been written for any flow yet (see Implementation Sequence, Step 22).
The only integration-style tests that actually exist are `ValuexApplicationTests` (full app boot via
Testcontainers, needs Docker) and `ProfileMenuServiceWiringIntegrationTest` (§18.1, Docker-free). This
snippet documents the intended shape for when request-level tests are eventually added.

```java
@SpringBootTest
@AutoConfigureMockMvc
class UserRegistrationIntegrationTest {

    @Test
    void shouldCompleteFullRegistrationFlow() throws Exception {
        // Step 1: Initiate
        mockMvc.perform(post("/api/v1/auth/register/initiate")
            .content("{\"mobile\":\"9876543210\",\"termsAccepted\":true,\"consentGiven\":true}")
            .contentType(MediaType.APPLICATION_JSON))
            .andExpect(status().isOk());

        // Step 2: Verify OTP (MockOtpAdapter logs OTP, test reads from Redis)
        mockMvc.perform(post("/api/v1/auth/register/verify-mobile")
            .content("{\"mobile\":\"9876543210\",\"otp\":\"123456\"}")
            .contentType(MediaType.APPLICATION_JSON))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.data.aadhaarVerified").value(false));

        // Step 3: Aadhaar
        mockMvc.perform(post("/api/v1/auth/aadhaar/initiate")
            .header("Authorization", "Bearer " + token)
            .content("{\"aadhaarNumber\":\"123456789012\",\"consentToken\":\"ts-123\"}")
            .contentType(MediaType.APPLICATION_JSON))
            .andExpect(status().isOk());

        // Step 4: Complete
        mockMvc.perform(post("/api/v1/auth/aadhaar/verify")
            .header("Authorization", "Bearer " + token)
            .content("{\"transactionId\":\"sandbox-txn-xxx\",\"otp\":\"123456\"}")
            .contentType(MediaType.APPLICATION_JSON))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.data.aadhaarVerified").value(true));
    }

    @Test
    void shouldBlockListingCreationWithoutAadhaar() throws Exception {
        // Register without Aadhaar
        String token = registerAndGetToken();

        mockMvc.perform(post("/api/v1/listings")
            .header("Authorization", "Bearer " + token))
            .andExpect(status().isForbidden())
            .andExpect(jsonPath("$.error.code").value("AADHAAR_VERIFICATION_REQUIRED"));
    }
}
```

## 18.3 Provider Switching Test

A test profile (`application-providertest.yml`) verifies that swapping `valuex.aadhaar.provider` or `valuex.otp.provider` loads the correct adapter bean without any code changes. Same applies for `valuex.social.google.enabled` and `valuex.social.apple.enabled`.

---

# Implementation Sequence

Status as of v1.10. Task names in rows 3 and 10 were corrected in v1.7 — the original names
(`SocialLoginPort`, `GoogleSocialLoginAdapter`) were superseded by the real `GoogleTokenPort`/
`GoogleSignInService` design back in v1.2, but this table was never updated to match at the time.
Row 23 (US-106) added in v1.8; row 23a (AuthResponse `status` field) added in v1.9; rows 24-24a
(US-107) added in v1.10.

| # | Task | Story | Depends On | Status |
|---|---|---|---|---|
| 1 | `V2__auth_schema.sql` Flyway migration (incl. `user_social_accounts`) | US-001 | S0-004 | ✅ Done |
| 2 | `User.java` entity + `UserRepository` | US-001 | Step 1 | ✅ Done |
| 3 | `OtpPort` + `AadhaarVerificationPort` + `GoogleTokenPort` interfaces | US-001 | — | ✅ Done |
| 4 | `MockOtpAdapter` + `SandboxAadhaarAdapter` + config | US-001 | Step 3 | ✅ Done |
| 5 | `UserRegistrationService` (initiate + verify OTP) | US-001 | Steps 2, 3, 4 | ✅ Done |
| 6 | `AadhaarVerificationService` (initiate + verify + skip) | US-001 | Step 5 | ✅ Done |
| 7 | `AuthController` — all registration endpoints | US-001 | Step 6 | ✅ Done |
| 8 | `AadhaarGatingInterceptor` + `@RequiresIdentityVerification` | US-001, US-088 | Step 6 | ✅ Done |
| 9 | Duplicate enforcement in registration flow | US-002 | Step 5 | ✅ Done |
| 10 | `GoogleTokenPort` adapters + `GoogleSignInService` + `/auth/social/google*` | US-101 | Step 5 | ✅ Done |
| 11 | ~~Apple Sign-In adapter + `/auth/social/apple`~~ | US-102 | Step 10 | ❌ Dropped from scope |
| 12 | `V6__replace_profile_photo_with_avatar.sql` migration | US-003 | Step 1 | ✅ Done |
| 12a | `UserProfileService` (profile CRUD + avatar catalog/selection) + `UserProfileController` + `AvatarController` | US-003 | Steps 2, 12 | ✅ Done |
| 13 | Notification entity + dispatcher + event listeners | US-077 | Step 5 | ⬜ Not started — `com.valuex.notification` is still the Sprint-0 state-machine scaffold only |
| 14 | Suspended account auto-lift scheduled job | US-088 | Step 5 | ⬜ Not started — no `@Scheduled` job exists anywhere in the codebase |
| 15 | `user_sessions` + `contact_change_attempts` migration (V7) | US-105 | Step 1 | ⬜ Not started — turned out to be US-105-only; US-104 needed no persisted table, see §9 |
| 16 | Add `jti` claim to token issuance, shared per access+refresh pair; `LogoutService` (blocklist, no `SessionService`/table) | US-104 | Steps 5, 10 | ✅ Done — see §9 for the as-built design, narrower than this row's original plan |
| 17 | Extend `JwtAuthenticationFilter` with blocklist check | US-104 | Step 16 | ✅ Done |
| 18 | `AuthController` logout endpoint | US-104 | Step 16 | ✅ Done |
| 19 | `ProfileMenuBadgeProvider` SPI + `ProfileMenuService` + menu-summary endpoint | US-103 | Step 13 | ✅ Done — **except** `NotificationsBadgeProvider`, correctly deferred until Step 13 lands (zero providers registered today, by design, not a bug) |
| 19a | `ProfileMenuService` hardening: constructor-time duplicate-key validation, per-provider failure/negative-count isolation, unmodifiable `badges` map, full SPI Javadoc, Spring-wiring integration test | US-103 | Step 19 | ✅ Done — added during PR review, not part of the original plan |
| 20 | `AccountSecurityService` + `AccountSecurityController` (mobile/email change, sessions) | US-105 | Steps 12, 16 | ⬜ Not started |
| 21 | Unit tests | US-001, US-002, US-003, US-101, US-103, US-106, US-107 | Steps 5-9, 12a, 19-19a, 23, 24-24a | ✅ Done for every implemented story |
| 22 | Integration tests | All | Steps 7-14, 17-20 | 🟡 Partial — `ValuexApplicationTests` (Testcontainers/Docker, boots the whole app) plus the narrow `ProfileMenuServiceWiringIntegrationTest` (Docker-free, proves `List<ProfileMenuBadgeProvider>` autowiring). No dedicated request-level `MockMvc` integration tests exist yet for any flow — everything implemented is verified at the unit level only. |
| 23 | `InitiateLoginRequest`/`VerifyLoginOtpRequest` DTOs + `UserLoginService` (initiate + verify login OTP, reuses `OtpPurpose.LOGIN`) + `/auth/login/*` endpoints on `AuthController` + `SecurityConfig` `permitAll()` entries | US-106 | Steps 2, 5 | ✅ Done — see §13 |
| 23a | `AuthResponse.status` field, populated in all 5 builder call sites (`UserLoginService`, `UserRegistrationService` x2, `AadhaarVerificationService`, `GoogleSignInService`) — closes the AC gap where the client couldn't tell which screen to route to after auth | US-106 | Step 23 | ✅ Done — added during US-106 AC audit, not part of the original plan |
| 24 | `RefreshTokenRequest` DTO + `TokenRefreshService` (stateless refresh — signature/expiry/type/good-standing, reissues both tokens) + `/auth/refresh` on `AuthController` + `SecurityConfig` `permitAll()` entry | US-107 | Steps 2, 23 | ✅ Done — see §14. Single-use rotation and logout-invalidation explicitly deferred to US-104/US-105 (§14.5) |
| 24a | `JwtTokenProvider.isAccessToken`/`isRefreshToken`/`isTokenExpired` + `JwtAuthenticationFilter` type-check fix (rejects refresh tokens used as bearer tokens, closing the `role=null` gap) | US-107 | Step 24 | ✅ Done — closes the design-note gap called out in US-107's `user-stories.md` entry |

---

**End of Sprint 1 Low Level Design**
