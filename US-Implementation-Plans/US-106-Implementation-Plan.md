# US-106: Mobile OTP Login for Returning Users — Implementation Plan

## Context

Traced earlier this session: the backend has no way for a returning mobile-OTP user to log back in. `POST /api/v1/auth/register/initiate` explicitly rejects an already-registered mobile with `ERROR_MOBILE_ALREADY_REGISTERED`, and no other endpoint fills the gap — Google/Apple Sign-In are documented as *"Optional Convenience Login"*, i.e. a shortcut around a primary mobile-OTP login path that was never itself built. US-106 (`Documents/user-stories.md`) was written to close this gap. This plan implements it.

A design validation pass (using the actual current source of `UserRegistrationService`, `GoogleSignInService`, `AuthController`, `SecurityConfig`, and the two closest existing test files) confirmed the approach below and surfaced one real precedent conflict, resolved below.

## Recommended Approach

### 1. New: `UserLoginService`
`valuex-backend/src/main/java/com/valuex/auth/application/service/UserLoginService.java`

A separate service from `UserRegistrationService` — matches this codebase's established one-service-per-concern split (`EmailVerificationService`, `AadhaarVerificationService`, `GoogleSignInService` are all separate despite sharing OTP mechanics). Registration and login have opposite existence-check semantics, so bolting login onto `UserRegistrationService` would blur that.

Dependencies: `UserRepository`, `OtpPort`, `RedisCacheService`, `JwtTokenProvider`, `ValuexProperties`, plus an inline `SecureRandom` — deliberately **no** `UserAccountStateMachine` and **no** `JdbcTemplate`, because login never transitions state (see point 4).

```java
@Service
@RequiredArgsConstructor
@Slf4j
public class UserLoginService {

    public MessageResponse initiateLogin(InitiateLoginRequest request) {
        User user = userRepository.findByMobile(request.getMobile())
            .orElseThrow(() -> new BusinessException("ERROR_MOBILE_NOT_REGISTERED",
                "No account found with this mobile number. Please register"));
        assertLoginEligible(user);
        // rate-limit check on otp_rate:{mobile} -> ERROR_OTP_RATE_LIMIT
        // generate OTP, hash, redisCache.set("otp:" + mobile + ":" + OtpPurpose.LOGIN, hash, ttl)
        // otpPort.sendOtp(mobile, otp, OtpPurpose.LOGIN)
    }

    public AuthResponse verifyLogin(VerifyLoginOtpRequest request) {
        // rate-limit check on otp_fail:{mobile} first -> ERROR_OTP_MAX_ATTEMPTS (mirrors verifyMobileOtp's exact ordering)
        User user = userRepository.findByMobile(request.getMobile())
            .orElseThrow(() -> new BusinessException("ERROR_MOBILE_NOT_REGISTERED", "..."));
        assertLoginEligible(user);   // re-checked here -- this IS the fix for "state changed between send and verify"
        // fetch+compare OTP hash from otp:{mobile}:LOGIN -> ERROR_OTP_EXPIRED / ERROR_INVALID_OTP
        // delete both Redis keys
        String accessToken = jwtTokenProvider.generateAccessToken(
            user.getId(), "USER", user.isAadhaarVerified(), "MOBILE_OTP");   // read fresh from `user`, not cached
        String refreshToken = jwtTokenProvider.generateRefreshToken(user.getId());
        return AuthResponse.builder()
            .accessToken(accessToken).refreshToken(refreshToken)
            .aadhaarVerified(user.isAadhaarVerified()).userId(user.getId().toString())
            .build();
    }

    private void assertLoginEligible(User user) {
        switch (user.getStatus()) {
            case NEW, OTP_PENDING -> throw new BusinessException("ERROR_INVALID_STATE",
                "Please complete your mobile number verification before logging in");
            case SUSPENDED -> throw new BusinessException("ERROR_ACCOUNT_SUSPENDED",
                "Your account is suspended. Please contact support");
            case BANNED, CLOSED -> throw new BusinessException("ERROR_ACCOUNT_RECOVERY_REQUIRED",
                "Your account requires recovery. Please contact support");
            default -> { /* EMAIL_VERIFICATION_PENDING, IDENTITY_VERIFICATION_PENDING, ACTIVE, UNDER_REVIEW, RESTRICTED -- allowed */ }
        }
    }
}
```

No `@Transactional` on either method — login never calls `save`/`saveAndFlush` (no state transition occurs), unlike registration's verify step which transitions `OTP_PENDING → EMAIL_VERIFICATION_PENDING`.

### 2. State-eligibility table (who can log in)

Cross-checked against the actual `UserAccountState` enum (10 values) and the LLD's §7.2 Access Control table:

| State | Login? | Result |
|---|---|---|
| NEW, OTP_PENDING | No | `ERROR_INVALID_STATE` — mobile never verified |
| EMAIL_VERIFICATION_PENDING | **Yes** | resumes at email step (AC's own explicit example) |
| IDENTITY_VERIFICATION_PENDING | **Yes** | resumes at Aadhaar step |
| ACTIVE | **Yes** | home |
| UNDER_REVIEW, RESTRICTED | **Yes** | per §7.2 — these states *can* log in, just can't list/buy |
| SUSPENDED | No | `ERROR_ACCOUNT_SUSPENDED` |
| BANNED, CLOSED | No | `ERROR_ACCOUNT_RECOVERY_REQUIRED` |

`assertLoginEligible` is called at **both** `initiateLogin` and `verifyLogin` — calling it twice (not just once at initiate) is what actually satisfies the AC's "account state changes between OTP send and verify" edge case.

### 3. Error code decision: reuse `ERROR_INVALID_STATE`, not a new code

For the NEW/OTP_PENDING case, `GoogleSignInService.initiateMobileForSocialLink` already hits the identical situation (existing user, registration incomplete) and throws `ERROR_INVALID_STATE` with *"Please complete your existing registration before linking Google Sign-In"*. This is the established codebase convention for "account exists but its status doesn't permit this action" — reused across `EmailVerificationService`, `AadhaarVerificationService`, `UserRegistrationService.skipAadhaar`, and `GoogleSignInService`. Login reuses the same code with its own message rather than inventing a new one, consistent with the principle (set earlier this session) of reusing existing error codes for situations that already have one, not creating near-duplicates.

Every other error code is either AC-specified (`ERROR_MOBILE_NOT_REGISTERED`, `ERROR_ACCOUNT_SUSPENDED`) or reused verbatim from existing code (`ERROR_ACCOUNT_RECOVERY_REQUIRED` — exact string copied from `GoogleSignInService`; `ERROR_INVALID_OTP`/`ERROR_OTP_EXPIRED`/`ERROR_OTP_RATE_LIMIT`/`ERROR_OTP_MAX_ATTEMPTS` — exact strings copied from `UserRegistrationService`).

### 4. `OtpPurpose.LOGIN` — finally used

The enum already has an unused `LOGIN` value. Login OTPs use Redis key `otp:{mobile}:LOGIN`, distinct from registration's `otp:{mobile}:MOBILE_VERIFY`. Verified zero blast radius: no adapter in the codebase branches on `OtpPurpose` (the only real adapter, `MockOtpAdapter`, just logs it).

Rate-limit buckets (`otp_rate:{mobile}`, `otp_fail:{mobile}`) are **shared** with registration's identical prefixes, not purpose-scoped — safe because a mobile can never be simultaneously eligible for both registration (requires `!existsByMobile`) and login (requires `existsByMobile`).

### 5. What login deliberately does NOT touch
- **`account_status_history` / `writeStateHistory`** — audit trail of state *transitions* only; login causes none, so writes none. (Every existing service only calls this alongside an actual `stateMachine.transition()` — confirmed by inspection, always travel together.)
- **Session/`jti` tracking** — the LLD's US-104/105 session design (`user_sessions` table) doesn't exist in real code yet (confirmed: no `UserSession.java` anywhere). Login correctly does not add one — that's US-107/US-104 territory, not this story.
- **Aadhaar gating** — already uniformly enforced by `AadhaarGatingInterceptor` reading the `aadhaarVerified` JWT claim regardless of which flow issued the token. Since login reads `user.isAadhaarVerified()` fresh from the DB into that claim exactly like every other flow, the AC's "must not bypass Aadhaar gating differently" is satisfied with zero new gating logic.

### 6. New DTOs
- `InitiateLoginRequest` (`application/dto/`) — single `mobile` field, same `@NotBlank @Pattern(regexp = "^[6-9]\\d{9}$", ...)` as `InitiateRegistrationRequest`. No `termsAccepted`/`consentGiven` — already captured at registration.
- `VerifyLoginOtpRequest` — `mobile` + `otp`, identical validation shape to `VerifyMobileOtpRequest`. Kept as its own DTO rather than reusing `VerifyMobileOtpRequest`, matching this codebase's existing pattern of one DTO per endpoint even where shapes coincide (e.g. `VerifyMobileOtpRequest` vs `SocialVerifyMobileRequest`).

No new response DTO — reuses existing `MessageResponse` (initiate) and `AuthResponse` (verify), exactly like registration.

### 7. Controller + Security
`AuthController.java`: add `private final UserLoginService loginService;` and two 2-line passthrough methods:
```java
@Operation(summary = "Login Step 1: Initiate login — sends OTP to a registered mobile number")
@PostMapping("/login/initiate")
public ResponseEntity<ApiResponse<MessageResponse>> initiateLogin(@Valid @RequestBody InitiateLoginRequest request) { ... }

@Operation(summary = "Login Step 2: Verify OTP — issues JWT reflecting the account's current status")
@PostMapping("/login/verify-mobile")
public ResponseEntity<ApiResponse<AuthResponse>> verifyLogin(@Valid @RequestBody VerifyLoginOtpRequest request) { ... }
```
Naming follows the existing `"Step N: ..."` / `"Social Step N: ..."` Swagger summary convention.

`SecurityConfig.java`: add `/api/v1/auth/login/initiate` and `/api/v1/auth/login/verify-mobile` to the `permitAll()` list, next to the `register/*` entries (public — no JWT exists yet at this point in the flow).

### 8. Tests

**New:** `UserLoginServiceTest.java` — same conventions as `UserRegistrationServiceTest`/`GoogleSignInServiceTest` (`MockitoExtension`, `LENIENT`, AssertJ). Follows `GoogleSignInServiceTest`'s more recent convention of calling `HashUtils.sha256Hex(...)` directly in test setup rather than duplicating the digest logic.

`initiateLogin`: happy path (ACTIVE) · mobile not registered · rate limit exceeded · NEW/OTP_PENDING rejected · SUSPENDED rejected · BANNED rejected · CLOSED rejected · **one test per additionally-eligible state** (EMAIL_VERIFICATION_PENDING, IDENTITY_VERIFICATION_PENDING, UNDER_REVIEW, RESTRICTED all send OTP successfully) — this last group is the crux of the story and directly locks in the §7.2 table.

`verifyLogin`: happy path returns JWT with `aadhaarVerified` matching the stubbed `User` (not hardcoded `false`, proving "fresh from DB") · invalid OTP · expired OTP · max fail attempts · mobile not found at verify time · **account became SUSPENDED between send and verify** (stub `findByMobile` returning SUSPENDED, assert rejection and `verify(jwtTokenProvider, never()).generateAccessToken(...)`) · `verify(userRepository, never()).save(any())`/`saveAndFlush(any())` somewhere to lock in "login never mutates the user."

**Edit:** `AuthControllerTest.java` — add `@Mock UserLoginService loginService`, plus `shouldReturnOkWhenLoginInitiated` and `shouldReturnJwtWhenLoginOtpVerified`, mirroring the existing registration test pair exactly.

### 9. Doc follow-up
US-106 currently only exists as a story entry (`user-stories.md`) and a Sprint-plan row — it has no LLD design section yet (unlike US-103, which had one *before* implementation). After code is green, add a new LLD section following the existing per-story format (matching §3 US-001 / §6 US-002's style — flow diagram, error table, state-eligibility table from point 2 above), inserted after §12 (US-088) and before §13 (Database Schema), renumbering §13-16 → §14-17 the same way prior sections were renumbered this session.

## Verification

1. `mvn verify` from `valuex-backend/` — checkstyle, full test suite, JaCoCo 65% gate.
2. Fast iteration: `mvn test -Dtest=UserLoginServiceTest,AuthControllerTest`.
3. Manual check via Swagger UI: register a fresh user, let them sit at `EMAIL_VERIFICATION_PENDING` (don't complete email step), then call `POST /auth/login/initiate` with that mobile — confirm OTP is sent and `POST /auth/login/verify-mobile` returns a JWT with `aadhaarVerified: false`. Then complete Aadhaar verification via the existing flow, log out (no real logout yet — just discard the token), and log back in via `/auth/login/*` — confirm the new JWT has `aadhaarVerified: true`, proving it's read fresh and not stuck at whatever it was during registration.
