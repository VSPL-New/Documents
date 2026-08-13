# US-103 — Profile Hub / Account Menu Navigation: QA Testing Guide

**Sprint 1 · Identity & User Management**

Manual test cases for the profile-hub summary endpoint, using Swagger UI against a local dev environment.

> **What this story actually ships (backend):** US-103 is primarily a **mobile navigation shell** (the "Profile" tab with its grouped menu). The backend's only Sprint-1 deliverable is one summary endpoint plus an extensibility mechanism (`ProfileMenuBadgeProvider` SPI) so later sprints can contribute badge counts (unread orders, pending offers, etc.) without this endpoint ever changing again. **No badge provider is registered yet** — `badges` in the response is always `{}` today. That's the correct, designed state, not a bug — see `Documents/LLD/Sprint-1-Identity-User-Management-LLD.md` §8 for why.

| Setting | Value |
|---|---|
| Base URL | `http://localhost:8080` |
| Swagger UI | `http://localhost:8080/swagger-ui.html` (tag: **User Profile**) |
| Endpoint under test | `GET /api/v1/users/me/menu-summary` |
| Expected `badges` today | `{}` (empty — zero providers registered) |
| Default avatar | `avatar-01` |

---

## Prerequisites — Get an Authenticated User

Same as US-003: this endpoint only requires a valid JWT, not email/Aadhaar verification. Fastest path (see `US-001-Testing-Guide.md` for full detail):

1. `POST /api/v1/auth/register/initiate`
   ```json
   { "mobile": "9000000020", "termsAccepted": true, "consentGiven": true }
   ```
2. Read the OTP from the console log, then `POST /api/v1/auth/register/verify-mobile`
   ```json
   { "mobile": "9000000020", "otp": "XXXXXX" }
   ```
3. Copy `data.accessToken` and **Authorize** in Swagger UI (🔒 button, paste token, no `Bearer ` prefix).

---

## Test Scenarios Overview

| TC | Scenario | Expected Result |
|---|---|---|
| TC-001 | Get menu summary — fresh account defaults | `200`, default avatar, `memberSince` set, empty `badges` |
| TC-002 | Summary reflects a display-name update | `200`, `displayName` matches latest `PATCH /users/me` |
| TC-003 | Summary reflects an avatar change | `200`, `avatarId` matches latest `PUT /users/me/avatar` |
| TC-004 | Summary reflects Aadhaar verification | `200`, `aadhaarVerified: true` after US-001 Aadhaar flow |
| TC-005 | `badges` is always empty today | `200`, `badges: {}` regardless of account activity |
| TC-006 | Unauthenticated request rejected | `401 UNAUTHORIZED` |
| TC-007 | `memberSince` matches `GET /users/me` | `200`, both endpoints report the identical timestamp |

---

## TC-001 — Get Menu Summary (Fresh Account Defaults)

**Goal:** A freshly registered user gets a sane summary with no prior profile edits.

**Endpoint:** `GET /api/v1/users/me/menu-summary` *(requires JWT)*

No request body.

**Expected response (200 OK):**
```json
{
  "success": true,
  "data": {
    "avatarId": "avatar-01",
    "aadhaarVerified": false,
    "memberSince": "2026-08-12T10:30:00Z",
    "badges": {}
  }
}
```

> `displayName` is omitted entirely (not `null`) — same `non_null` JSON inclusion rule as `GET /api/v1/users/me` (see US-003 guide). Don't file this as a bug.
>
> `memberSince` is the account's `created_at` timestamp — set the moment `POST /register/initiate` first creates the user row (Step 1 of registration), **not** when this endpoint is first called. It should already be a few minutes old by the time you reach this test, not "now."

---

## TC-002 — Summary Reflects a Display-Name Update

**Goal:** The summary endpoint reads live data, not a cached/stale copy.

**Steps:**
1. `PATCH /api/v1/users/me`
   ```json
   { "displayName": "Abhay Kumar" }
   ```
2. `GET /api/v1/users/me/menu-summary`

**Expected:** `data.displayName` is `"Abhay Kumar"`.

---

## TC-003 — Summary Reflects an Avatar Change

**Steps:**
1. `PUT /api/v1/users/me/avatar`
   ```json
   { "avatarId": "avatar-07" }
   ```
2. `GET /api/v1/users/me/menu-summary`

**Expected:** `data.avatarId` is `"avatar-07"`.

---

## TC-004 — Summary Reflects Aadhaar Verification

**Prerequisites:** Complete the full US-001 flow through Aadhaar verification for this user (email OTP, then `POST /aadhaar/initiate` + `POST /aadhaar/verify` with the sandbox provider — see `US-001-Testing-Guide.md` Steps 3–6).

**Steps:** `GET /api/v1/users/me/menu-summary`

**Expected:** `data.aadhaarVerified` is `true`.

---

## TC-005 — `badges` Is Always Empty Today

**Goal:** Confirm the current, correct state of the extensibility mechanism — no badge provider is wired up yet in Sprint 1.

**Steps:** Regardless of what you've done with this account (updated profile, changed avatar, verified Aadhaar, made multiple API calls), call `GET /api/v1/users/me/menu-summary`.

**Expected:** `data.badges` is always `{}` — an empty JSON object, present in the response (not omitted, since it's a non-null empty map), but with no keys.

> **Do not** file "no badges for my orders/offers/notifications" as a bug. Those badge keys (`MY_ORDERS`, `OFFERS`, `NOTIFICATIONS`, etc. — see LLD §8.3 for the full list) only appear once their owning story registers a `ProfileMenuBadgeProvider` bean, starting with Notifications in Sprint 11 at the earliest. Re-run this TC after any story that's supposed to contribute a badge ships, to confirm the new key appears with a correct count.

---

## TC-006 — Unauthenticated Request Rejected

**Steps:** In Swagger UI, click **Authorize 🔒** → **Logout** (or call without an `Authorization` header), then `GET /api/v1/users/me/menu-summary`.

**Expected response (401 Unauthorized):**
```json
{
  "success": false,
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Authentication required"
  }
}
```

---

## TC-007 — `memberSince` Matches `GET /users/me`

**Goal:** The summary endpoint's `memberSince` is the same underlying value as the one already shown on the full profile — not a separately (and possibly differently) computed timestamp.

**Steps:**
1. `GET /api/v1/users/me` → note `data.memberSince`
2. `GET /api/v1/users/me/menu-summary` → note `data.memberSince`

**Expected:** Both values are identical, character-for-character.

> This field was added after an AC audit found the original US-103 acceptance criteria call for a "joined date" in the profile summary, which the first implementation omitted — see LLD changelog v1.6.

---

## Not Testable Yet (Don't File as Bugs)

- **The actual "Profile" menu/tab UI** (grouped sections, empty/"coming soon" states for unshipped destinations, seller-only rows) — that's mobile-side work per the LLD; this guide only covers the backend summary endpoint.
- **Any badge count** (`MY_ORDERS`, `SAVED_ITEMS`, `OFFERS`, `TRANSACTIONS`, `PAYOUTS`, `NOTIFICATIONS`, `SUPPORT_TICKETS`, `DISPUTES`) — see TC-005. None exist until their owning story ships.
- **`ERROR_SECTION_UNAVAILABLE`** — this error is defined in `user-stories.md` for when an individual menu *destination* screen is down, not for this summary endpoint itself. Not reachable via any current API call.
- **Resilience against a broken badge provider** — the backend was hardened during PR review so that (a) one provider throwing an exception or returning a negative count doesn't break the whole response, just omits that one badge, and (b) two providers registering the same key fails app startup with a clear error rather than crashing a live request. Neither is exercisable via this API today since zero providers are registered — there's nothing that *can* misbehave yet. Once the first real provider (Notifications, earliest Sprint 11) ships, these become worth re-testing directly.

---

## Reset Between Tests

Same as US-003 — see `US-003-Testing-Guide.md` → **Reset Between Tests** (reset `display_name`/`city`/`avatar_id` via SQL, or just register a fresh mobile number per TC).

---

## Error Reference

| HTTP | Error Code | Cause |
|---|---|---|
| 401 | `UNAUTHORIZED` | Missing or expired JWT (TC-006) |
| 404 | `NOT_FOUND` | JWT references a user that no longer exists — not reachable via normal API use |
