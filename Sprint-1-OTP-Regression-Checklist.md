# Sprint 1 Auth OTP Regression Checklist

## Scope
This checklist validates the mobile OTP re-initiation fix and email OTP verify-time conflict handling.

## Test Cases

| ID | Scenario | Steps | Expected Result | Pass/Fail |
|---|---|---|---|---|
| TC-01 | Mobile registration initiate | Call register/initiate with valid mobile + terms + consent | OTP sent success response | ☐ |
| TC-02 | Mobile OTP expiry | Wait past OTP TTL, then verify with old OTP | ERROR_OTP_EXPIRED | ☐ |
| TC-03 | Mobile re-initiate after expiry | Call register/initiate again with same mobile | OTP sent again, no mobile already registered error | ☐ |
| TC-04 | Mobile verify after re-initiate | Verify using fresh OTP | Access + refresh token returned, status becomes EMAIL_VERIFICATION_PENDING | ☐ |
| TC-05 | Existing real account re-register blocked | Try register/initiate on mobile already in ACTIVE account | ERROR_MOBILE_ALREADY_REGISTERED | ☐ |
| TC-06 | Email OTP send (pending state) | With JWT in EMAIL_VERIFICATION_PENDING, call email/send-otp | OTP sent success response | ☐ |
| TC-07 | Email OTP expiry | Wait past TTL, then verify with old OTP | ERROR_OTP_EXPIRED | ☐ |
| TC-08 | Email resend after expiry | Call email/send-otp again with same email | OTP sent again | ☐ |
| TC-09 | Email verify success after resend | Verify using fresh OTP | Email verified success, status becomes IDENTITY_VERIFICATION_PENDING | ☐ |
| TC-10 | Email already linked to another account | Use email owned by different user | ERROR_EMAIL_ALREADY_REGISTERED | ☐ |
| TC-11 | Concurrent same-email claim race | Two pending users send/verify same email in close sequence | One succeeds, other gets clean ERROR_EMAIL_ALREADY_REGISTERED | ☐ |
| TC-12 | No raw DB error leak | Force race/conflict case | API returns business error, not SQL/DataIntegrity stack error | ☐ |
| TC-13 | Mobile OTP rate limit | Repeated initiate beyond window | ERROR_OTP_RATE_LIMIT | ☐ |
| TC-14 | Mobile OTP max verify attempts | Repeated wrong OTP beyond limit | ERROR_OTP_MAX_ATTEMPTS | ☐ |
| TC-15 | Email OTP rate limit | Repeated email send beyond window | ERROR_OTP_RATE_LIMIT | ☐ |
| TC-16 | Email OTP max verify attempts | Repeated wrong email OTP beyond limit | ERROR_OTP_MAX_ATTEMPTS | ☐ |

## Execution Notes

1. Run with mock OTP adapters so OTP values are visible in logs.
2. Capture response body for each failure case and confirm exact error code, not just message.
3. Re-run TC-03 and TC-09 twice to confirm behavior is stable across repeated retries.

## Evidence Checklist

- API request payload captured
- HTTP status code captured
- API response body captured
- Server log snippet captured for OTP/evidence
- Tester signoff and timestamp
