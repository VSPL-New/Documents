# MSG91 Integration Guide — SMS & Email OTP

## Design Review: Plug-and-Play Assessment

The current architecture uses the **Hexagonal (Port/Adapter) pattern** for OTP providers. Here is the verdict on each aspect:

| Aspect | Status | Detail |
|---|---|---|
| Service layer isolation | ✅ Pass | `UserRegistrationService` and `EmailVerificationService` depend only on `OtpPort` / `EmailOtpPort` interfaces — they have zero knowledge of MSG91 or Mock |
| Adding a new provider | ✅ Pass | Create one new adapter file; nothing in domain or application layer changes |
| Switching providers at runtime | ✅ Pass | Change one env var (`OTP_SMS_PROVIDER` / `OTP_EMAIL_PROVIDER`), restart — no code change |
| Independent SMS and email providers | ❌ Gap | `valuex.otp.provider` is a single key controlling both `OtpPort` and `EmailOtpPort` beans simultaneously. You cannot use MSG91 for SMS and SendGrid for email without code changes |

### Gap Fix (Required Before Adding MSG91)

Split `valuex.otp.provider` into two independent keys:

```
valuex.otp.sms-provider   = mock | msg91
valuex.otp.email-provider = mock | msg91
```

This is the **only structural change** needed. Services, ports, and domain code are untouched.

---

## Required Changes

### 1. `ValuexProperties.java` — split provider + add Msg91 block

```java
@Data
public static class Otp {
    private String smsProvider   = "mock";    // replaces: provider
    private String emailProvider = "mock";    // new
    private int expirySeconds = 300;
    private int length = 6;
    private int maxSendAttemptsPerWindow = 3;
    private int maxVerifyAttemptsPerWindow = 5;
    private int rateLimitWindowMinutes = 10;
}

@Data
public static class Msg91 {
    private String authKey;
    private String senderId;          // DLT-registered 6-char sender ID
    private String smsFlowId;         // MSG91 Flow ID for OTP SMS template
    private String emailFromAddress;
    private String emailFromName;
    private String emailTemplateId;   // MSG91 email template ID
}
```

Add `private Msg91 msg91 = new Msg91();` alongside the other fields.

> **Why a separate `Msg91` block?** OTP behaviour config (expiry, length, rate limits) belongs to the application layer. Provider credentials belong to the adapter layer. Mixing them in `Otp` would couple the two.

---

### 2. `application.yml` — split provider keys + add msg91 block

```yaml
valuex:
  otp:
    sms-provider:   ${OTP_SMS_PROVIDER:mock}    # was: provider
    email-provider: ${OTP_EMAIL_PROVIDER:mock}  # new
    expiry-seconds: 300
    # ... rest unchanged

  msg91:
    auth-key:           ${MSG91_AUTH_KEY:}
    sender-id:          ${MSG91_SENDER_ID:}
    sms-flow-id:        ${MSG91_SMS_FLOW_ID:}
    email-from-address: ${MSG91_EMAIL_FROM_ADDRESS:}
    email-from-name:    ${MSG91_EMAIL_FROM_NAME:ValueX}
    email-template-id:  ${MSG91_EMAIL_TEMPLATE_ID:}
```

---

### 3. `.env.example` — add MSG91 keys

```
# OTP provider: mock (dev) | msg91 (staging/prod)
OTP_SMS_PROVIDER=mock
OTP_EMAIL_PROVIDER=mock

# MSG91 — leave blank for mock provider
MSG91_AUTH_KEY=
MSG91_SENDER_ID=
MSG91_SMS_FLOW_ID=
MSG91_EMAIL_FROM_ADDRESS=
MSG91_EMAIL_FROM_NAME=ValueX
MSG91_EMAIL_TEMPLATE_ID=
```

---

### 4. `OtpProviderConfig.java` — split conditionals + add MSG91 beans

```java
@Configuration
@RequiredArgsConstructor
public class OtpProviderConfig {

    private final ValuexProperties properties;

    // ── Mock ─────────────────────────────────────────────────────

    @Bean
    @ConditionalOnProperty(name = "valuex.otp.sms-provider", havingValue = "mock", matchIfMissing = true)
    public OtpPort mockOtpAdapter() {
        return new MockOtpAdapter();
    }

    @Bean
    @ConditionalOnProperty(name = "valuex.otp.email-provider", havingValue = "mock", matchIfMissing = true)
    public EmailOtpPort mockEmailOtpAdapter() {
        return new MockEmailOtpAdapter();
    }

    // ── MSG91 ────────────────────────────────────────────────────

    @Bean
    @ConditionalOnProperty(name = "valuex.otp.sms-provider", havingValue = "msg91")
    public OtpPort msg91SmsOtpAdapter(RestClient restClient) {
        return new Msg91SmsOtpAdapter(restClient, properties.getMsg91());
    }

    @Bean
    @ConditionalOnProperty(name = "valuex.otp.email-provider", havingValue = "msg91")
    public EmailOtpPort msg91EmailOtpAdapter(RestClient restClient) {
        return new Msg91EmailOtpAdapter(restClient, properties.getMsg91());
    }

    @Bean
    @ConditionalOnProperty(
        name = {"valuex.otp.sms-provider", "valuex.otp.email-provider"},
        havingValue = "msg91"
    )
    public RestClient msg91RestClient() {
        return RestClient.builder()
            .baseUrl("https://api.msg91.com")
            .defaultHeader("Content-Type", "application/json")
            .build();
    }
}
```

> **Note:** `@ConditionalOnProperty` with multiple `name` values uses OR logic in Spring Boot — the bean registers if any of the listed properties has the given value. This means one `RestClient` bean is created if either provider is set to msg91.

---

### 5. `Msg91SmsOtpAdapter.java` — new file

**Package:** `com.valuex.auth.adapter.otp`

```java
@Slf4j
@RequiredArgsConstructor
public class Msg91SmsOtpAdapter implements OtpPort {

    private static final String FLOW_API_PATH = "/api/v5/flow/";

    private final RestClient restClient;
    private final ValuexProperties.Msg91 config;

    @Override
    public void sendOtp(String mobile, String otp, OtpPurpose purpose) {
        String internationalMobile = "91" + mobile;   // prepend India country code

        Map<String, String> body = Map.of(
            "flow_id", config.getSmsFlowId(),
            "sender",  config.getSenderId(),
            "mobiles", internationalMobile,
            "otp",     otp                            // must match template variable name
        );

        try {
            restClient.post()
                .uri(FLOW_API_PATH)
                .header("authkey", config.getAuthKey())
                .body(body)
                .retrieve()
                .toBodilessEntity();

            log.info("[MSG91-SMS] OTP sent to mobile={} purpose={}", mobile, purpose);
        } catch (Exception ex) {
            log.error("[MSG91-SMS] Failed to send OTP to mobile={}: {}", mobile, ex.getMessage());
            throw new BusinessException("ERROR_OTP_SEND_FAILED",
                "Failed to send OTP. Please try again");
        }
    }
}
```

**MSG91 SMS Flow API reference:**

```
POST https://api.msg91.com/api/v5/flow/
Header: authkey: <AUTH_KEY>
Header: Content-Type: application/json

{
  "flow_id": "<your-flow-id>",
  "sender":  "<SENDER>",
  "mobiles": "91XXXXXXXXXX",
  "otp":     "123456"
}
```

The field name `"otp"` must match the variable name you defined in the MSG91 Flow template. If your template uses `{{otp}}`, no change needed. If it uses a different name (e.g., `{{code}}`), update the key in the body accordingly — or make it configurable via `valuex.msg91.sms-otp-var-name`.

---

### 6. `Msg91EmailOtpAdapter.java` — new file

**Package:** `com.valuex.auth.adapter.otp`

```java
@Slf4j
@RequiredArgsConstructor
public class Msg91EmailOtpAdapter implements EmailOtpPort {

    private static final String EMAIL_API_PATH = "/api/v5/email/send";

    private final RestClient restClient;
    private final ValuexProperties.Msg91 config;

    @Override
    public void sendEmailOtp(String email, String otp, OtpPurpose purpose) {
        Map<String, Object> body = Map.of(
            "to",          List.of(Map.of("email", email)),
            "from",        Map.of(
                               "name",  config.getEmailFromName(),
                               "email", config.getEmailFromAddress()),
            "template_id", config.getEmailTemplateId(),
            "variables",   Map.of("otp", otp)       // matches {{otp}} in MSG91 email template
        );

        try {
            restClient.post()
                .uri(EMAIL_API_PATH)
                .header("authkey", config.getAuthKey())
                .body(body)
                .retrieve()
                .toBodilessEntity();

            log.info("[MSG91-EMAIL] OTP sent to email={} purpose={}", email, purpose);
        } catch (Exception ex) {
            log.error("[MSG91-EMAIL] Failed to send OTP to email={}: {}", email, ex.getMessage());
            throw new BusinessException("ERROR_OTP_SEND_FAILED",
                "Failed to send OTP. Please try again");
        }
    }
}
```

**MSG91 Email API reference:**

```
POST https://api.msg91.com/api/v5/email/send
Header: authkey: <AUTH_KEY>
Header: Content-Type: application/json

{
  "to":          [{ "email": "user@example.com" }],
  "from":        { "name": "ValueX", "email": "noreply@valuex.com" },
  "template_id": "<your-template-id>",
  "variables":   { "otp": "123456" }
}
```

---

### 7. `Msg91SmsOtpAdapterTest.java` — new file

**Package:** `com.valuex.auth.adapter.otp`

Test scenarios:
- `shouldCallMsg91FlowApiWithCorrectPayload` — mock `RestClient`, capture request body, verify `flow_id`, `sender`, `mobiles` (with `91` prefix), `otp`
- `shouldPrependCountryCodeToMobile` — assert `mobiles = "91" + mobile`
- `shouldThrowBusinessExceptionWhenMsg91Returns4xx` — mock `RestClient` to throw `HttpClientErrorException`, verify `BusinessException("ERROR_OTP_SEND_FAILED")` is thrown

---

### 8. `Msg91EmailOtpAdapterTest.java` — new file

**Package:** `com.valuex.auth.adapter.otp`

Test scenarios:
- `shouldCallMsg91EmailApiWithCorrectPayload` — verify `template_id`, `to[0].email`, `from.email`, `variables.otp`
- `shouldThrowBusinessExceptionWhenMsg91Returns4xx` — same error handling verification

---

## MSG91 Setup Prerequisites

Before setting the env vars, complete these steps in the MSG91 dashboard:

1. **DLT Registration** (mandatory for India SMS)
   - Register your entity on the TRAI DLT portal
   - Register the OTP SMS template with DLT
   - Get the DLT Template ID (needed during MSG91 template creation)

2. **Create SMS Flow in MSG91**
   - Go to MSG91 → Flow → Create New Flow
   - Select the DLT-registered template
   - Add variable `{{otp}}` where the OTP should appear
   - Save and copy the **Flow ID** → `MSG91_SMS_FLOW_ID`

3. **Register Sender ID**
   - 6-character alphanumeric sender ID (e.g., `VALUEX`)
   - Must be DLT-registered
   - Copy → `MSG91_SENDER_ID`

4. **Create Email Template in MSG91**
   - Go to MSG91 → Email → Templates
   - Add `{{otp}}` as the OTP placeholder in the template body
   - Save and copy the **Template ID** → `MSG91_EMAIL_TEMPLATE_ID`

5. **Verify sender email domain** in MSG91 email settings → `MSG91_EMAIL_FROM_ADDRESS`

---

## Switching Between Providers

To move from mock to MSG91 (no code change required):

**.env (local dev):**
```
OTP_SMS_PROVIDER=mock
OTP_EMAIL_PROVIDER=mock
```

**.env (staging/prod):**
```
OTP_SMS_PROVIDER=msg91
OTP_EMAIL_PROVIDER=msg91
MSG91_AUTH_KEY=xxxxxxxxxxxxxx
MSG91_SENDER_ID=VALUEX
MSG91_SMS_FLOW_ID=xxxxxxxxxx
MSG91_EMAIL_FROM_ADDRESS=noreply@valuex.com
MSG91_EMAIL_FROM_NAME=ValueX
MSG91_EMAIL_TEMPLATE_ID=xxxxxxxxxx
```

Mixed (SMS via MSG91, email via a different future provider):
```
OTP_SMS_PROVIDER=msg91
OTP_EMAIL_PROVIDER=sendgrid   ← once SendGrid adapter is added
```

---

## File Summary

| Action | File |
|---|---|
| Modify | `ValuexProperties.java` — split `provider`, add `Msg91` inner class |
| Modify | `application.yml` — split provider keys, add `msg91:` block |
| Modify | `.env.example` — add MSG91 vars |
| Modify | `OtpProviderConfig.java` — split conditionals, add MSG91 beans + `RestClient` bean |
| Create | `Msg91SmsOtpAdapter.java` |
| Create | `Msg91EmailOtpAdapter.java` |
| Create | `Msg91SmsOtpAdapterTest.java` |
| Create | `Msg91EmailOtpAdapterTest.java` |

Zero changes to: `OtpPort`, `EmailOtpPort`, `OtpPurpose`, `UserRegistrationService`, `EmailVerificationService`, `AuthController`, or any domain class.
