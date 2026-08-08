# Low Level Design - Sprint 1: Identity & User Management

**Document Version:** 1.4
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

**Reference Documents:**
- PRD v1.4
- HLD Parts 1-3
- Sprint Plan v2.0
- User Stories v3.3
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
13. [Database Schema](#13-database-schema)
14. [API Design](#14-api-design)
15. [Security Considerations](#15-security-considerations)
16. [Testing Strategy](#16-testing-strategy)

---

# 1. Sprint Overview

## 1.1 Goal

Allow users to register and log in via multiple auth methods (Mobile OTP, Google, Apple), verify identity, and manage profiles. Establish the authentication foundation for all subsequent sprints.

## 1.2 Stories

| ID     | Story                                       | Repo            | SP | Dependency |
|--------|---------------------------------------------|-----------------|----|------------|
| US-001 | User Registration via Mobile OTP            | backend, mobile | 8  | S0-001     |
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

- [ ] User can register via mobile OTP
- [ ] Email verification step works (OTP sent to email after mobile OTP)
- [ ] Google Sign-In working (returns JWT, new-user flow collects mobile)
- [ ] ~~Apple Sign-In~~ — **Dropped from scope**
- [ ] Aadhaar verification flow works (skip + complete)
- [ ] Aadhaar gate enforced on first transaction attempt
- [ ] Duplicate account prevention operational
- [ ] User profile view and edit working
- [ ] Profile hub summary endpoint returns badge counts (extensible provider SPI)
- [ ] Logout revokes current session (JWT `jti` blocklisted immediately)
- [ ] Mobile/email change via OTP working; active-sessions list and "log out of other devices" working
- [ ] Account state transitions tracked and audited
- [ ] Critical event notifications sent (in-app + push)
- [ ] All endpoints documented in Swagger UI

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
│   │   ├── EmailVerificationService.java   # Email OTP send + verify
│   │   ├── AadhaarVerificationService.java # Aadhaar initiate + verify
│   │   ├── GoogleSignInService.java        # Google 3-step sign-in flow
│   │   ├── UserProfileService.java         # Profile CRUD + avatar selection/catalog
│   │   ├── ProfileMenuService.java         # Profile hub badge aggregation (US-103)
│   │   ├── SessionService.java             # Session create/revoke/blocklist (US-104/US-105)
│   │   └── AccountSecurityService.java     # Mobile/email change, session listing (US-105)
│   └── dto/
│       ├── InitiateRegistrationRequest.java
│       ├── VerifyMobileOtpRequest.java
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
    ├── AuthController.java                 # All auth endpoints (registration + social + logout)
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
  → Return: AuthResponse { accessToken, refreshToken, aadhaarVerified=false, userId }

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
  → Return: AuthResponse { accessToken, refreshToken, aadhaarVerified=false, userId }
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
  → Return: AuthResponse { accessToken, refreshToken, aadhaarVerified=true, userId }
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
  → Return: AuthResponse { accessToken, refreshToken, aadhaarVerified=false, userId }
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
    int badgeCount(UUID userId);   // 0 if nothing pending
}
```

`ProfileMenuService` autowires `List<ProfileMenuBadgeProvider>` — Spring injects whatever providers exist at the time. In Sprint 1, only the notifications provider exists; every other menu key is simply absent from the response until its owning sprint registers a provider bean.

```java
package com.valuex.auth.application.service;

@Service
@RequiredArgsConstructor
public class ProfileMenuService {

    private final UserRepository userRepository;
    private final List<ProfileMenuBadgeProvider> badgeProviders;

    public ProfileMenuSummaryResponse getSummary(UUID userId) {
        User user = userRepository.findById(userId)
            .orElseThrow(() -> new NotFoundException("User not found"));

        Map<String, Integer> badges = badgeProviders.stream()
            .collect(Collectors.toMap(
                ProfileMenuBadgeProvider::menuKey,
                p -> p.badgeCount(userId)));

        return ProfileMenuSummaryResponse.builder()
            .displayName(user.getDisplayName())
            .avatarId(user.getAvatarId())
            .aadhaarVerified(user.isAadhaarVerified())
            .badges(badges)   // e.g. {"NOTIFICATIONS": 3}
            .build();
    }
}
```

Sprint 1's own notifications provider:

```java
package com.valuex.auth.adapter.menu;

@Component
@RequiredArgsConstructor
public class NotificationsBadgeProvider implements ProfileMenuBadgeProvider {

    private final NotificationRepository notificationRepository;

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

```java
package com.valuex.auth.application.dto;

public record ProfileMenuSummaryResponse(
    String displayName,
    String avatarId,
    boolean aadhaarVerified,
    Map<String, Integer> badges
) {}
```

---

# 9. US-104: Account Logout

## 9.1 Logout Flow

```
POST /api/v1/auth/logout
  Auth: Bearer token required
  → Extract jti + userId from access token claims
  → SessionService.revoke(jti, userId, reason="USER_LOGOUT")
      → user_sessions.revoked_at = now(), revoked_reason = "USER_LOGOUT"
      → Redis SETEX blocklist:{jti} <remaining-ttl-seconds> "1"
  → Return: { message: "Logged out successfully" }
```

## 9.2 SessionService

```java
package com.valuex.auth.application.service;

@Service
@RequiredArgsConstructor
public class SessionService {

    private final UserSessionRepository sessionRepository;
    private final StringRedisTemplate redisTemplate;

    public void createSession(UUID userId, String jti, String refreshToken,
                               String deviceInfo, String ipAddress) {
        UserSession session = UserSession.builder()
            .id(UUID.fromString(jti))
            .userId(userId)
            .refreshTokenHash(sha256(refreshToken))
            .deviceInfo(deviceInfo)
            .ipAddress(ipAddress)
            .createdAt(Instant.now())
            .lastActiveAt(Instant.now())
            .build();
        sessionRepository.save(session);
    }

    public void revoke(String jti, UUID userId, String reason) {
        UserSession session = sessionRepository.findByIdAndUserId(UUID.fromString(jti), userId)
            .orElseThrow(() -> new NotFoundException("Session not found"));
        session.setRevokedAt(Instant.now());
        session.setRevokedReason(reason);
        sessionRepository.save(session);

        long remainingTtl = extractRemainingTtlSeconds(jti);
        redisTemplate.opsForValue().set("blocklist:" + jti, "1",
            Duration.ofSeconds(Math.max(remainingTtl, 1)));
    }

    public boolean isBlocked(String jti) {
        return Boolean.TRUE.equals(redisTemplate.hasKey("blocklist:" + jti));
    }
}
```

`createSession` is called from every place a JWT is currently issued: `UserRegistrationService` (Steps 2/4a/5), `GoogleSignInService` (Flows A/B/C), and Aadhaar re-issue — each already has the `jti` available since it's generated at token-issuance time.

## 9.3 JwtAuthenticationFilter Extension

The existing filter (Sprint 0 Foundation LLD) adds one check after signature/expiry validation:

```java
if (sessionService.isBlocked(claims.getId())) {   // claims.getId() == jti
    throw new InvalidTokenException("Session has been logged out");
}
```

## 9.4 Edge Case: In-Flight Requests

Logout does not cancel requests already past the filter when it's called — only new requests bearing the blocklisted `jti` are rejected. The mobile client is responsible for warning the user and cancelling active uploads client-side before calling `/logout` (per user-stories.md US-104 edge cases).

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

# 13. Database Schema

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

# 14. API Design

## 14.1 Auth Endpoints

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
    "userId": "uuid"
  }
}
```
**Errors:** `ERROR_INVALID_OTP`, `ERROR_OTP_EXPIRED`

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
    "userId": "uuid"
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
    "verifiedName": "A**** K****"
  }
}
```

---

## 14.2 Social Login Endpoints

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
    "userId": "uuid"
  }
}
```
**Errors:** `ERROR_SOCIAL_SESSION_EXPIRED`, `ERROR_INVALID_OTP`, `ERROR_OTP_EXPIRED`

---

~~POST /api/v1/auth/social/apple~~ — **Dropped (US-102 removed from scope)**

---

## 14.3 User Profile Endpoints

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

## 14.4 Notifications Endpoints

### GET /api/v1/notifications
**Auth:** Bearer token required
**Query params:** `page=0&size=20&unreadOnly=false`
**Response header:** `X-Unread-Notifications: 3`

### PATCH /api/v1/notifications/{id}/read
**Auth:** Bearer token required

### PATCH /api/v1/notifications/read-all
**Auth:** Bearer token required

---

## 14.5 Profile Hub Endpoint

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
    "badges": { "NOTIFICATIONS": 3 }
  }
}
```
Note: badge keys for menu items whose owning sprint hasn't shipped yet are simply absent from `badges` (see Section 8.3).

---

## 14.6 Logout Endpoint

### POST /api/v1/auth/logout
**Auth:** Bearer token required
**Response 200:**
```json
{
  "success": true,
  "data": { "message": "Logged out successfully" }
}
```
Idempotent — calling it again on an already-revoked session still returns 200.
**Errors:** `ERROR_LOGOUT_FAILED`

---

## 14.7 Account Security Endpoints

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

# 15. Security Considerations

## 15.1 Social Login Token Security

| Rule | Detail |
|---|---|
| Server-side validation only | Google and Apple tokens are NEVER trusted from the client — always re-validated server-side |
| Google token validation | Call `https://oauth2.googleapis.com/tokeninfo?id_token={token}` — verify `email_verified == true`, `aud` in configured client-IDs list (web, Android, iOS) |
| `email_verified` enforcement | `HttpGoogleTokenAdapter` rejects tokens where `email_verified != "true"`. Unverified Google emails are never accepted. |
| Multiple client IDs | `valuex.oauth.google.client-ids` holds three IDs (web, Android, iOS). The `aud` claim must match one of them. |
| No client-side shortcut | Flutter plugins return validated tokens — but backend must re-validate independently |
| ~~Apple token validation~~ | ~~US-102 dropped~~ |

## 15.2 Aadhaar Data Handling

| Data | Storage | Notes |
|---|---|---|
| Raw Aadhaar number | **Never stored** | Sent to provider API only, in-memory only |
| Aadhaar hash | `users.aadhaar_hash` | SHA-256 only, for uniqueness check |
| Aadhaar name | `users.aadhaar_name` | Masked (A**** K****) from provider |
| Verification attempt | `aadhaar_verification_attempts` | Audit trail with hash, not plain number |

## 15.3 OTP Security

- OTP is 6 digits, alphanumeric entropy optional (config)
- Stored as `SHA-256(otp)` in Redis — never plain text
- Rate limit: max 3 OTP send requests per mobile per 10 minutes (Redis counter)
- OTP invalidated immediately after successful use
- Max 5 failed OTP attempts before lockout (10-minute cooldown)

## 15.4 JWT Claims

```json
{
  "sub": "user-uuid",
  "jti": "3f8a1c2d-e5f6-4a9b-8c1d-2e3f4a5b6c7d",
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
The `jti` claim (added in v1.3) identifies the `user_sessions` row this token belongs to — see Section 2.5 and Section 15.6.

## 15.5 Rate Limiting (via Redis)

| Endpoint | Limit | Window |
|---|---|---|
| `/register/initiate` | 3 requests | per mobile per 10 min |
| `/email/send-otp` | 3 requests | per user per 10 min |
| `/email/verify-otp` (fail) | 5 attempts | per user per 10 min |
| `/aadhaar/initiate` | 3 requests | per user per 10 min |
| `/aadhaar/verify` (fail) | 5 attempts | per user per 10 min |
| `/social/google/initiate-mobile` | 3 requests | per social session per 10 min |
| `/users/me/mobile/change/initiate` | 3 requests | per user per 10 min |
| `/users/me/email/change/initiate` | 3 requests | per user per 10 min |
| `/auth/logout` | 10 requests | per user per 10 min (abuse guard) |

## 15.6 Session & Token Revocation (US-104 / US-105)

| Rule | Detail |
|---|---|
| Refresh token storage | Only `SHA-256(refreshToken)` is stored in `user_sessions` — never plain text, same pattern as OTPs |
| Revocation propagation | `blocklist:{jti}` TTL is set to the access token's *remaining* lifetime — never longer, so Redis never accumulates stale keys |
| Blocklist check cost | One Redis `EXISTS` per authenticated request, added to the existing `JwtAuthenticationFilter` — no additional DB round-trip |
| Mobile/email change security | New value must pass OTP verification before it replaces the old one; old value remains valid for login until then, preventing account lockout mid-change |
| Session enumeration | `GET /users/me/sessions` never exposes another user's sessions — scoped by `userId` from the JWT, not a client-supplied ID |

---

# 16. Testing Strategy

## 16.1 Unit Tests

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

### ProfileMenuService Tests (US-103)
- `shouldAggregateBadgesFromAllRegisteredProviders`
- `shouldOmitBadgeKeyWhenNoProviderRegistered`
- `shouldReturnZeroCountWhenNoUnreadNotifications`

### SessionService Tests (US-104)
- `shouldCreateSessionOnSuccessfulLogin`
- `shouldRevokeSessionAndBlocklistJti`
- `shouldSetBlocklistTtlToRemainingTokenLifetime`
- `shouldRejectRevokeForSessionBelongingToAnotherUser`
- `shouldBeIdempotentWhenRevokingAlreadyRevokedSession`

### JwtAuthenticationFilter Tests (US-104)
- `shouldRejectRequestWithBlocklistedJti`
- `shouldAllowRequestWithNonBlocklistedJti`

### AccountSecurityService Tests (US-105)
- `shouldInitiateMobileChangeAndSendOtpToNewNumber`
- `shouldRejectMobileChangeWhenNewNumberAlreadyRegistered`
- `shouldVerifyMobileChangeAndUpdateUser`
- `shouldKeepOldMobileActiveUntilNewOneVerified`
- `shouldMirrorFlowForEmailChange`
- `shouldListActiveSessionsWithCurrentSessionFlagged`
- `shouldRevokeAllSessionsExceptCaller`
- `shouldRejectRevokeOthersWhenNoOtherSessionsExist`

## 16.2 Integration Tests

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

## 16.3 Provider Switching Test

A test profile (`application-providertest.yml`) verifies that swapping `valuex.aadhaar.provider` or `valuex.otp.provider` loads the correct adapter bean without any code changes. Same applies for `valuex.social.google.enabled` and `valuex.social.apple.enabled`.

---

# Implementation Sequence

| # | Task | Story | Depends On |
|---|---|---|---|
| 1 | `V2__auth_schema.sql` Flyway migration (incl. `user_social_accounts`) | US-001 | S0-004 |
| 2 | `User.java` entity + `UserRepository` | US-001 | Step 1 |
| 3 | `OtpPort` + `AadhaarVerificationPort` + `SocialLoginPort` interfaces | US-001 | — |
| 4 | `MockOtpAdapter` + `SandboxAadhaarAdapter` + config | US-001 | Step 3 |
| 5 | `UserRegistrationService` (initiate + verify OTP) | US-001 | Steps 2, 3, 4 |
| 6 | `AadhaarVerificationService` (initiate + verify + skip) | US-001 | Step 5 |
| 7 | `AuthController` — all registration endpoints | US-001 | Step 6 |
| 8 | `AadhaarGatingInterceptor` + `@RequiresIdentityVerification` | US-001, US-088 | Step 6 |
| 9 | Duplicate enforcement in registration flow | US-002 | Step 5 |
| 10 | `GoogleSocialLoginAdapter` + `SocialLoginService` + `/auth/social/google` | US-101 | Step 5 |
| 11 | `AppleSocialLoginAdapter` + `/auth/social/apple` | US-102 | Step 10 |
| 12 | `V6__replace_profile_photo_with_avatar.sql` migration | US-003 | Step 1 |
| 12a | `UserProfileService` (profile CRUD + avatar catalog/selection) + `UserProfileController` + `AvatarController` | US-003 | Steps 2, 12 |
| 13 | Notification entity + dispatcher + event listeners | US-077 | Step 5 |
| 14 | Suspended account auto-lift scheduled job | US-088 | Step 5 |
| 15 | `user_sessions` + `contact_change_attempts` migration (V7) | US-104, US-105 | Step 1 |
| 16 | Add `jti` claim to token issuance; `SessionService` (create/revoke/blocklist) | US-104 | Steps 5, 10, 15 |
| 17 | Extend `JwtAuthenticationFilter` with blocklist check | US-104 | Step 16 |
| 18 | `AuthController` logout endpoint | US-104 | Step 16 |
| 19 | `ProfileMenuBadgeProvider` SPI + `ProfileMenuService` + `NotificationsBadgeProvider` + menu-summary endpoint | US-103 | Step 13 |
| 20 | `AccountSecurityService` + `AccountSecurityController` (mobile/email change, sessions) | US-105 | Steps 12, 16 |
| 21 | Unit tests | All | Steps 5-14, 16-20 |
| 22 | Integration tests | All | Steps 7-14, 17-20 |

---

**End of Sprint 1 Low Level Design**
