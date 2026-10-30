# US-007 — Restricted Items Prevention: QA Testing Guide

**Sprint 2 · Seller Listing Creation**

Manual test cases for the restricted-items check that runs when a seller taps **Choose Listing Plan** on the
Item Details page: the backend API, the policy loader, the photo-based finding from `valuex-ai`, and the app's
compliance popup and blocked dialog. No AI key is needed for the text and category cases (AI is off by default).

> **What this story ships:** `POST /api/v1/listings/{listingId}/restricted-check`,
> `POST .../restricted-check/{checkId}/compliance-acceptance`, `POST .../restricted-check/{checkId}/appeal`,
> the start-up loader of the Restrictions policy (21 rows, English and Hindi), the `RestrictedItemGate` used by
> US-008 and US-009, an optional `restrictionPolicyCode` in the US-005 classification answer, and the app wiring.

| Setting | Value |
|---|---|
| Backend base URL | `http://localhost:8080` |
| Migration | `V18` (Flyway runs on start) |
| DB tables | `restriction_policies`, `restriction_terms`, `category_restriction_policies`, `listing_moderation_checks`, `listing_compliance_acceptances`, `listing_moderation_appeals` |
| Results | `SAFE` (200) · `COMPLIANCE_REQUIRED` (200) · `RESTRICTED` (400 `ERROR_RESTRICTED_ITEM`) · `SEVERE_VIOLATION` (403 `ERROR_ACCOUNT_SUSPENDED`) |
| Repeated-violation rule | 3 blocked checks in 30 days flag the account for review |

---

## Prerequisites

1. PostgreSQL and Redis from `valuex-backend/docker-compose.yml`; start the backend (`mvn spring-boot:run`). The
   log shows `Restrictions policy <version> loaded: 21 rows, <n> terms, 87 category mappings` on the first start
   and `... is already loaded` afterwards.
2. Two `ACTIVE` seller accounts with access tokens: `$TOKEN` (seller A) and `$TOKEN_B` (seller B).
3. A draft of seller A with at least 2 READY photos (`US-004-Testing-Guide.md`); note its id as `$LISTING`.
4. Category codes (`GET /api/v1/categories/search?q=...`): a plain one such as a chair (`$CLEAN`), a Real Estate
   one such as an apartment (`$REAL_ESTATE`), `CAT-0204` (Solar Panels) and `CAT-0742` (Forklifts).
5. For the app cases: the emulator build of `valuex-mobile` signed in as seller A.

Helper to set the text and category of the draft (the app does this through the Item Details page):

```sql
UPDATE listings SET title = '<title>', description = '<description>',
  category_id = (SELECT id FROM categories WHERE code = '<category code>') WHERE id = '<listing id>';
```

Call the check:

```powershell
curl.exe -s -X POST "http://localhost:8080/api/v1/listings/$LISTING/restricted-check" -H "Authorization: Bearer $TOKEN"
```

---

## Test cases

| ID | Acceptance criterion / edge case | Steps | Expected |
|---|---|---|---|
| TC-001 | Policy loaded at start | Start the backend; `SELECT status, count(*) FROM restriction_policies WHERE active GROUP BY status;` | `PROHIBITED` 12, `CONDITIONAL` 9; every row has `title_hi`, `popup_message_hi` and one `policy_version` |
| TC-002 | Clean item passes | Title "Wooden study chair", category `$CLEAN`, call the check | 200, `result` `SAFE`, no `policies`; one row in `listing_moderation_checks` with `source` `RULES` |
| TC-003 | Prohibited keyword blocks | Title "Red wine bottles", call the check | 400, `error.code` `ERROR_RESTRICTED_ITEM`, message "This item cannot be listed. See prohibited items policy", `data.policies[0].code` `ALCOHOL_TOBACCO` with English and Hindi text; the check is stored with `result` `RESTRICTED` |
| TC-004 | Keyword in the description only | Title "Glass set", description "empty wine bottles", call | Blocked as in TC-003 |
| TC-005 | Whole words only | Title "Farm toys and charms" | `SAFE` (no match inside "farms" or "charms") |
| TC-006 | Plural / phrase variants | Titles "Antique pistols", "Air rifle", "Pure cocaine" | Each blocked; "cocaine" is a severe term (TC-009) |
| TC-007 | Known false positive | Title "Crystal wine glass set" | Blocked (accepted for this version); TC-012 shows the appeal |
| TC-008 | Conditional category asks to agree | Category `$REAL_ESTATE`, clean text | 200, `COMPLIANCE_REQUIRED`, message "Please read and agree to continue", `policies[0].code` `REAL_ESTATE` with the sheet text |
| TC-009 | Severe violation | Title "Pure cocaine", call as seller A | 403 `ERROR_ACCOUNT_SUSPENDED`; `SELECT status FROM users WHERE id = '<seller A>'` is `UNDER_REVIEW`; the check is stored with `result` `SEVERE_VIOLATION`. Set the account back to `ACTIVE` before continuing |
| TC-010 | Conditional keyword in another category | Title "Camera drone", category `$CLEAN` | 200 `COMPLIANCE_REQUIRED`, `policies[0].code` `DRONES` |
| TC-011 | Exempt Conditional categories | Category `CAT-0204`, then `CAT-0742`, clean text | `SAFE` for both |
| TC-012 | Appeal | After TC-003: `POST .../restricted-check/{checkId}/appeal` with `{"reason": "Empty decorative bottles"}` | 201, `status` `PENDING`; a second appeal gives 400 `ERROR_APPEAL_ALREADY_SUBMITTED`; an empty reason gives 400 `VALIDATION_ERROR`; appealing a `SAFE` check gives 400 `ERROR_APPEAL_NOT_ALLOWED` |
| TC-013 | Accept the compliance text | After TC-008: `POST .../{checkId}/compliance-acceptance` with `{"policyCodes": ["REAL_ESTATE"]}` | 200 `accepted` 1; a row in `listing_compliance_acceptances` with listing, category, `policy_code`, `policy_version`, `accepted_at`; repeating it gives 400 `ERROR_COMPLIANCE_ALREADY_ACCEPTED`; a wrong code list gives 400 `ERROR_COMPLIANCE_POLICIES_MISMATCH`; an empty list gives 400 `VALIDATION_ERROR` |
| TC-014 | Edit after the check | After TC-013 change the title in the DB (SQL helper), then call the check again | A new check is made and the earlier agreement does not carry over (`COMPLIANCE_REQUIRED` with a new `checkId`); accepting the old `checkId` gives 400 `ERROR_COMPLIANCE_NOT_APPLICABLE` |
| TC-015 | Ownership | Seller B calls the check, acceptance and appeal for seller A's listing | 404 `LISTING_NOT_FOUND` each time; no token gives 401 |
| TC-016 | Draft rules | Call the check for a listing with fewer than 2 photos; for one without a category; for one that is no longer a draft | 400 `ERROR_MIN_PHOTOS_REQUIRED`; 400 `ERROR_CATEGORY_REQUIRED`; 400 `LISTING_NOT_IN_DRAFT` |
| TC-017 | Repeated violations | As a fresh seller make 3 blocked checks (TC-003) within 30 days | After the third the account is `UNDER_REVIEW`; the first two did not flag it. Compliance results do not count |
| TC-018 | Photo-based finding | Enable AI (`US-005-Testing-Guide.md`, fake model server). Change `CLASSIFY` in `fake_model.py` to include `"restrictionPolicyCode": "WEAPONS"`; generate suggestions for `$LISTING`; keep clean text; call the check | 400 `ERROR_RESTRICTED_ITEM` with `WEAPONS`; the check has `source` `AI`. Add or remove a photo and call again: the finding is ignored (`source` `RULES`, `SAFE`) |
| TC-019 | Unknown code from the model | Same as TC-018 with `"restrictionPolicyCode": "MADE_UP"` and then `"DRONES"` | `valuex-ai` drops it; the check is `SAFE` |
| TC-020 | Policy reload | Edit a Hindi text in `restriction-policies.csv`, restart the backend | Log says the policy loaded; `restriction_policies.policy_version` changed on all rows; an acceptance made before the change is no longer enough for the gate |
| TC-021 | Gate (used by US-008 and US-009) | No endpoint calls it yet; run `RestrictedItemGateTest` and `RestrictedItemIntegrationTest` | A listing never checked, edited after its check, blocked, or with an unaccepted conditional check is refused; `SAFE`, an accepted conditional check and an overturned appeal pass |

### App cases (emulator)

| ID | Steps | Expected |
|---|---|---|
| TC-A01 | Fill Item Details for a clean item, tap **Choose Listing Plan** | The plan page opens |
| TC-A02 | Choose a Real Estate category, fill the form, tap **Choose Listing Plan** | One dialog "Before you continue" lists the Real Estate text. **Cancel** closes it and stays on the page; **Agree & Continue** records it and opens the plan page |
| TC-A03 | Enter a title with "wine", tap **Choose Listing Plan** | Dialog "This item cannot be listed" with the matched row's title and message; **Go Back** closes it; the plan page does not open |
| TC-A04 | From TC-A03 tap **Appeal**, enter a reason, **Send appeal** | The button is off until a reason is typed; a snackbar says "Appeal sent. We will review it."; appealing again shows "You have already appealed this item" and keeps the dialog open |
| TC-A05 | Enter a title with "cocaine" | The dialog also says "Your account is suspended due to policy violations" |
| TC-A06 | Switch the app language to Hindi and repeat TC-A02 and TC-A03 | Titles, messages, buttons and the appeal text are in Hindi |
| TC-A07 | Turn the network off, tap **Choose Listing Plan** | A snackbar error; the plan page does not open |
| TC-A08 | Set the system text size to the largest | The dialogs show without overflow and the buttons stay reachable |

---

## Running the automated tests

Backend (Docker must be running for the integration test):

```powershell
cd valuex-backend
$env:JAVA_TOOL_OPTIONS='-Duser.timezone=Asia/Kolkata'
mvn verify '-Dtestcontainers.version=1.21.4'
mvn checkstyle:check
```

Only this story:

```powershell
mvn test '-Dtest=TextNormalizerTest,RuleBasedRestrictedItemCheckerTest,RestrictedItemCheckServiceTest,RestrictedItemGateTest,ListingModerationAppealServiceTest,ContentFingerprintTest,RestrictionPolicyLoaderTest,RestrictedItemControllerTest,ListingAiServiceTest,RestrictedItemIntegrationTest'
```

`valuex-ai`:

```powershell
cd valuex-ai
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m pytest --cov
```

Mobile:

```powershell
cd valuex-mobile
flutter gen-l10n
flutter analyze
flutter test test/features/listing
```

(The 18 accessibility contrast tests in `all_screens_accessibility_test.dart` and the other screens fail on `main`
too; they are not part of this story.)

Results at hand-over: backend unit tests for this story 86 passed (line coverage of the new classes 86 to 100 %,
most above 97 %; the Testcontainers test `RestrictedItemIntegrationTest` needs a running Docker engine);
`valuex-ai` 99.05 % coverage; mobile changed files 98 to 100 % covered.
