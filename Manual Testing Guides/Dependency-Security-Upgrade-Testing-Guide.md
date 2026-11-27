# Dependency Security Upgrade (Spring Boot 4.1.3): QA Testing Guide

**Chore · valuex-backend · branch `chore/dependency-security-upgrade`**

Smoke checks for the backend after moving from Spring Boot 3.2.5 to 4.1.3 to close the open Dependabot alerts. No
feature, API, database or app screen changes. Anything that works differently from before is a bug in this upgrade.

> **What changed:** Spring Boot 4.1.3 (Spring Framework 7.0, Spring Security 7.1, Hibernate 7, Tomcat 11, Netty 4.2,
> Flyway 12, Testcontainers 2, springdoc 3.1). The app still uses **Jackson 2** for every JSON body
> (`spring.http.converters.preferred-json-mapper: jackson2` and `JacksonConfig`), so the JSON sent to the mobile app
> must be byte-for-byte the same shape as before. Guava and OpenTelemetry, which come in through `firebase-admin`, are
> pinned to patched versions. `.github/dependabot.yml` now points at the right folder.

| Setting | Value |
|---|---|
| Build | `mvn clean verify` (Docker must be running; on this machine set `JAVA_TOOL_OPTIONS="-Dapi.version=1.44 -Duser.timezone=Asia/Kolkata"` first) |
| Automated coverage | The whole suite (3,822 tests) runs unchanged apart from test-API renames |
| Dependabot | Open alerts on the default branch close by themselves after merge |

---

## Test Scenarios Overview

| TC | Scenario | Expected Result |
|---|---|---|
| TC-001 | The backend starts on an existing dev database | Starts with no errors; Flyway reports nothing new to apply |
| TC-002 | Health and API docs | `/actuator/health` is UP (OpenSearch may be DEGRADED if it is not running); Swagger UI opens |
| TC-003 | JSON shape is unchanged | Dates are ISO strings, null fields are left out, unknown request fields are ignored |
| TC-004 | Login and token refresh | OTP login, token refresh and a protected call work; no token gives 401 |
| TC-005 | Listings and search | Create, edit and publish a listing; search and Home return results |
| TC-006 | Chat in real time | Two users chat; messages, typing and read receipts arrive live over `/ws/v1` |
| TC-007 | Cart and delivery choice | Add from an accepted offer, choose delivery or pickup |
| TC-008 | Push notifications | A listing event still sends an FCM push (dev Firebase project) |
| TC-009 | Dependabot after merge | Security tab shows the backend alerts closed; Maven update PRs start arriving on Mondays |

---

## TC-001 — Backend Starts

1. Pull the branch and run `mvn spring-boot:run -Dspring-boot.run.profiles=dev` with PostgreSQL, Redis and OpenSearch up.
2. **Expected:** the log shows `Started ValuexApplication`; Flyway logs `Schema "public" is up to date`; no
   `ERROR` or `APPLICATION FAILED TO START`.

## TC-002 — Health and API Docs

1. `GET /actuator/health`.
2. Open `/swagger-ui.html`.
3. **Expected:** status `UP` (the `openSearch` part shows `DEGRADED`, not `DOWN`, if OpenSearch is stopped); Swagger
   lists every controller.

## TC-003 — JSON Shape Unchanged

Compare a few responses with the same calls on `main` (or with the mobile app's expectations):

1. `GET` a public listing and your profile.
2. **Expected:**
   - timestamps look like `"2026-11-27T10:15:30Z"`, not numbers
   - fields with no value are left out
   - `POST` a request with an extra, unknown field: it is accepted, not refused with 400
   - error bodies keep the same `code` and `message` fields

## TC-004 — Login and Tokens

1. Request an OTP, verify it and call `GET /api/v1/users/me` with the access token.
2. Refresh the token, then call again with no token.
3. **Expected:** 200, 200, then 401 with the usual error body.

## TC-005 — Listings and Search

1. Create a listing with photos, publish it, then search for its title and open Home.
2. **Expected:** the listing is created and published, appears in search, and Home shows its sections.

## TC-006 — Real-Time Chat

1. Sign in as two users on two devices and open a chat between them.
2. Send messages, type, and read them.
3. **Expected:** messages, typing and read state appear on the other device without refreshing. Only one Redis
   subscription container starts (log line from `RedisMessageListenerContainer` appears once).

## TC-007 — Cart and Delivery Choice

Follow the main path of the US-019 and US-020 guides. **Expected:** unchanged results.

## TC-008 — Push Notifications

Trigger a listing notification (for example, publish a listing someone has saved a search for). **Expected:** the
device receives the push, as in the US-131 guide.

## TC-009 — Dependabot After Merge

1. After the PR is merged to `main`, open the backend repo's **Security → Dependabot** tab.
2. **Expected:** the 148 Maven alerts move to closed within a few minutes. The next Monday, Dependabot opens grouped
   Maven PRs titled like `build(deps): bump ...`.

---

## Not Part of This Upgrade

- **Jackson 3:** Spring Boot 4 defaults to Jackson 3. We stay on Jackson 2 for now so the JSON sent to the apps
  does not change. Moving to Jackson 3 is a separate task, because its defaults for dates and unknown fields differ.
- **Spring Boot 4.2:** 4.2.0 came out on 2026-11-20. Dependabot will offer it once it has a patch release or two.
