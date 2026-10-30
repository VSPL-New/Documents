# US-007: Restricted Items Prevention — Implementation Plan

> **Revised (2026-10-29):** US-006 (taxonomy), US-089, US-114, US-005 and US-088 are built, so this plan now applies the 2026-10-25 category-taxonomy update. A listing ends a check as **pass**, **blocked** (Prohibited row of the Restrictions sheet) or **compliance required** (Conditional category, or a Conditional item found by keyword or AI): the seller sees the sheet's popup and continues only on "Agree & Continue", and the acceptance is stored with the listing, category, policy version and time. Detection is rule/keyword based now and AI-assisted when `valuex.ai.enabled=true`. The Restrictions sheet replaces the earlier hand-written restricted list. Migration numbers: the latest is `V17` (US-005), so this story takes `V18`.

## 1. Header

| Field | Value |
|---|---|
| Story ID | US-007 |
| Title | Restricted Items Prevention |
| Sprint | Sprint 2 — Seller Listing Creation |
| Story Points | 5 |
| Repos | valuex-backend, valuex-mobile (the check call, the compliance popup and the blocked message), valuex-ai (a small change to the classification prompt and answer, Open Gap 14) |
| Dependency | Built: US-089 (`ListingLifecycleService`), US-005 (`valuex.ai.enabled`, `AiGatewayClient`, programmatic Resilience4j), US-114 (Item Details page and draft update), US-006 (`CategoryService`, `listings.category_id`, `marketplaceStatus`), US-088 (`UserStateService.flagForReview`). Built **before** US-008 (which calls the gate) and US-084 |

**Scope decisions (2026-10-16, revised 2026-10-29):**
1. AI is assumed disabled or down. A **rule-based check** against database tables replaces the AI check in that case. It looks at the seller's **title, description and category**.
2. Three outcomes. **Blocked**: a Prohibited item is found; the listing cannot continue and the seller sees the matching rows of the Restrictions sheet. **Compliance required**: the category is Conditional, or a Conditional item is found by keyword or AI; the seller sees the sheet's popup and continues only on "Agree & Continue". **Pass**: nothing found. A rule match is treated exactly as if the AI had found it.
3. This replaces the LLD's fail-closed `ERROR_MODERATION_UNAVAILABLE` for the AI-off and AI-down cases. With AI enabled and the AI answering, the AI result is used.
4. The Restrictions sheet (`Documents/Category_Taxonomy_CSVs/ValueX_JustQlic_Master_Restrictions.csv`, 12 Prohibited and 9 Conditional rows) is the source of the policy text, loaded into the database with a version. The keyword table is seeded from it; each term points at one sheet row.
5. Which categories are Conditional follows `Documents/Category_Taxonomy_Review_Drafts.md` section 7 (decisions D25 and D29): all 37 Real Estate L3 categories; Solar Panels (CAT-0204) and Forklifts (CAT-0742) have no popup.
6. The check result is bound to the content that was checked (title, description, category and photos). Changing any of them makes the earlier result stale, so the gate asks for a new check.
7. **Category first (decided 2026-10-29).** The AI vision model finds the item's category from the seller's photos (the US-005 classification); once the category is known, the JustQlic Restrictions policy is applied to it. No separate moderation model call is added. A Prohibited item shown in the photos is recognised by the same classification call (Open Gap 14, decided).
8. **Hindi is required (decided 2026-10-29).** Every policy title, popup message and button is shown in English and Hindi; the Hindi texts in section 8 were reviewed and approved.

## 2. Story Recap

**As a** platform **I want to** prevent listing of restricted items **so that** the platform remains compliant and safe.

**Acceptance Criteria** (`Documents/user-stories.md`):
- Given a seller is creating a listing
- When AI/system detects restricted items in photos or description
- Then listing creation is blocked
- And seller is shown which items are prohibited
- And guidelines are displayed
- When seller tries to publish restricted item listing
- Then system prevents publication
- And flags account for review
- When the category is Conditional, or a Conditional item is detected
- Then a compliance popup with the Restrictions sheet text is shown and the seller continues only by choosing "Agree & Continue"; the acceptance is stored with the listing, category, policy version and time

**Restricted item categories:** the Restrictions sheet replaces the list in the story: 12 Prohibited rows (blocked) and 9 Conditional rows (popup), see the CSV.

**Edge Cases:** borderline item (toy weapon) · restricted keyword in a legitimate listing · coded language · item legal in some states only · seller appeals.

**Validation Rules:** text keyword scanning in title/description · photo analysis (AI only) · manual review for borderline cases · repeated violations lead to account suspension.

**Error Scenarios:** `ERROR_RESTRICTED_ITEM` · `ERROR_SUSPICIOUS_CONTENT` · `ERROR_ACCOUNT_SUSPENDED`.

## 3. Design Reference

Primary source: [Sprint-2-Seller Listing Creation-LLD.md — Part D](../LLD/Sprint-2-Seller%20Listing%20Creation-LLD.md#part-d---us-007-restricted-items-prevention), §D.1–D.10. Also [HLD Part 4 §8](../HLD/04-AI-Architecture.md#8-restricted-item--content-moderation-ai) and [US-005 plan](US-005-Implementation-Plan.md) for the shared AI switch.

**Key design decisions:**
- One entry point, `POST /api/v1/listings/{listingId}/restricted-check`, runs `RestrictedItemCheckService`. It uses the AI Gateway when `valuex.ai.enabled=true` and the AI answers; otherwise (disabled, timeout, error, open circuit) it uses the rule-based `RuleBasedRestrictedItemChecker`. Both return the same result type, so everything after the check is common code. Results: `SAFE`, `COMPLIANCE_REQUIRED`, `RESTRICTED`, `SEVERE_VIOLATION`, and `UNCLEAR` (AI only).
- Result handling (LLD §D.5, extended): `SAFE` proceeds; `COMPLIANCE_REQUIRED` returns the popup rows and the seller must accept before the gate opens; `UNCLEAR` (AI only) is queued for manual review; `RESTRICTED` blocks with `ERROR_RESTRICTED_ITEM`; `SEVERE_VIOLATION` blocks and flags the account through `UserStateService.flagForReview`.
- Every check is saved to `listing_moderation_checks` with `source` (`AI` or `RULES`), `model_version` (`rules-v1` for the rule check), the matched policy codes and a `content_hash` of what was checked. Acceptances are saved to `listing_compliance_acceptances`.
- Every Sprint 2 listing must pass this gate before plan selection. The story exposes `RestrictedItemGate.requireCleared(listingId)`; US-008 and US-009 call it. The gate passes only for a check on the listing's **current** content hash that is `SAFE`, or `COMPLIANCE_REQUIRED` with every returned policy accepted at the current policy version (an admin-approved `UNCLEAR` or an overturned appeal also passes).
- Category rule: the listing's L3 code (`listings.category_id`, resolved with `CategoryService`) is looked up in the conditional-category map; a hit gives `COMPLIANCE_REQUIRED` with that row. A Prohibited category cannot be enabled (US-006), so category matching never blocks.

**Term matching (recommended and adopted):**
- Normalise title and description: Unicode NFKC, lower case, strip accents, replace punctuation and symbols with spaces, collapse whitespace.
- Match **whole words or whole phrases** on token boundaries, never raw substrings, so "arms" does not hit "farms", "charms" or "alarms".
- No stemming or fuzzy matching in the first version. Plurals and common variants are seeded as separate terms ("gun", "guns"). False positives are handled by the appeal flow (blocked results) and by "Agree & Continue" (conditional results); coded language is left to the AI later.
- Each term points at one Restrictions-sheet row (`policy_code`). A Prohibited row gives `RESTRICTED` (or `SEVERE_VIOLATION` for the severe ones); a Conditional row gives `COMPLIANCE_REQUIRED` even when the listing's category is not Conditional.
- The highest outcome wins: `SEVERE_VIOLATION` over `RESTRICTED` over `COMPLIANCE_REQUIRED` over `SAFE`; all matched rows are returned.

## 4. Implementation Steps

### Database Migration — `valuex-backend`
- [ ] `V18__restrictions_and_moderation_checks.sql` (the latest is `V17`; if another story lands first, renumber to the next free version at implementation time).
- [ ] `restriction_policies`: `code` (primary key, the stable codes of section 8, for example `WEAPONS`, `DRONES`), `status` (`PROHIBITED`, `CONDITIONAL`), `title` and `title_hi`, `popup_message` and `popup_message_hi`, `cta_label` and `cta_label_hi`, `policy_version`, `active`. English comes from the copied sheet and Hindi from a reviewed file `restrictions/restriction-policies-hi.csv` (section 8); both are loaded by a loader like `TaxonomySourceLoader` (idempotent, version = checksum of both files), not hand-written in SQL. The API returns both languages and the app shows the one for the seller's language.
- [ ] `restriction_terms`: `id`, `term` (stored normalised, unique among active rows), `policy_code` (foreign key to `restriction_policies`), `severity` (`RESTRICTED`, `SEVERE_VIOLATION`; only Prohibited rows can be severe), `active`, `created_at`. Seeded by the migration with typical English terms for every Prohibited row that can be matched by text (alcohol and tobacco, weapons and ammunition, explosives, drugs, counterfeit and replica, IDs and documents, human organs, live animals, hazardous chemicals, adult content) and for the Conditional rows that keywords can reveal (drone, helmet, car seat, lithium battery, perfume, seeds). `SEVERE_VIOLATION` stays for explosives, narcotics and human organs as approved on 2026-10-16.
- [ ] `category_restriction_policies`: `category_code` (L3 code), `policy_code`. Source: `taxonomy/restrictions/conditional-categories.csv`, generated once from `Category_Taxonomy_Review_Drafts.md` section 7 and the taxonomy CSV (L3 codes, all 37 Real Estate L3 included, CAT-0204 and CAT-0742 absent) and reviewed by the product owner; loaded with the sheet.
- [ ] `listing_moderation_checks` per LLD §D.3 with changes: `result` as `VARCHAR` with a check constraint (`SAFE`, `COMPLIANCE_REQUIRED`, `UNCLEAR`, `RESTRICTED`, `SEVERE_VIOLATION`) instead of a Postgres enum type (same approach as `listings.status`); extra columns `source` (`AI`, `RULES`), `matched_policy_codes` (JSONB), `content_hash`, `policy_version`; `matched_keywords` JSONB is kept.
- [ ] `listing_compliance_acceptances`: `id`, `listing_id`, `check_id`, `seller_id`, `category_id`, `policy_code`, `policy_version`, `accepted_at`; unique per (`check_id`, `policy_code`).
- [ ] `listing_moderation_appeals` per LLD §D.3.

### Backend — Domain and Persistence
- [ ] Entities and repositories for `RestrictionPolicy`, `RestrictionTerm`, `CategoryRestrictionPolicy`, `ListingModerationCheck`, `ListingComplianceAcceptance`, `ListingModerationAppeal` in the listing module (the sheet loader sits beside the taxonomy loader).
- [ ] `ModerationResult`, `RestrictionStatus` and `RestrictionSeverity` enums.
- [ ] `RestrictionPolicyLoader` (startup, idempotent, validates that every conditional-category code exists and is enabled, that every Conditional-marked L3 in the taxonomy is mapped or explicitly exempt, and that every term points at an active policy).
- [ ] `ContentHasher`: SHA-256 over title, description, L3 category code and the sorted READY media IDs.

### Backend — Rule-Based Checker
- [ ] `TextNormalizer` (NFKC, lower case, accent strip, punctuation to spaces).
- [ ] `RuleBasedRestrictedItemChecker`: builds token n-grams from normalised title and description up to the longest active term and matches them against the active terms (cached, refreshed when the sheet version changes); adds the policy of the listing's L3 category from `category_restriction_policies`. Returns the highest outcome with all matched policy codes and terms.
- [ ] The category comes from `CategoryService` using `listings.category_id`; no separate provider port is needed now that US-006 is built.
- [ ] Matched terms are stored but redacted (`***`) in application logs (LLD §D.10).

### Backend — AI Path (category first, no new model call)
- [ ] With `valuex.ai.enabled=true`, the category comes from the AI vision classification already built in US-005 (stored on the latest `listing_ai_suggestions` row, or the seller's own choice on Item Details, which always wins). The check then applies the policy of that category from `category_restriction_policies`; there is no `POST /ai/v1/moderation/restricted-item-check` and no change to `valuex-ai` for conditional categories.
- [ ] Recognising a Prohibited item from photos (decided): the classification prompt in `valuex-ai` also lists the 12 Prohibited rows (code and title) and the model may return an optional `restrictionPolicyCode` in the same call; the answer schema, the `ListingSuggestResponse` envelope and the backend `ListingSuggestResponse.Result` carry it, and `V18` adds `restriction_policy_code` to `listing_ai_suggestions`. The check reads it from the latest stored suggestion while the photo set is unchanged (same `content_hash` photo part); a code that is not a Prohibited row is ignored. If the photos changed since the suggestion, or AI is off, only text keywords can give a Prohibited result. The value is advisory input to the check, never shown to the seller as a model answer.
- [ ] With AI off, down or unanswered, the rule-based checker runs on the seller's text and the seller's chosen category, so an unchecked listing never passes.

### Backend — `RestrictedItemCheckService`
- [ ] Verify ownership and `DRAFT` status, at least 2 photos and a chosen category; run the AI path when `valuex.ai.enabled=true`, else the rule-based checker.
- [ ] Persist the check (with `content_hash` and `policy_version`), then handle the result: `SAFE` proceeds; `COMPLIANCE_REQUIRED` returns the popup rows (title, message, CTA labels) and leaves the gate closed until accepted; `UNCLEAR` queues for manual review and returns the `LISTING_UNDER_REVIEW` advisory; `RESTRICTED` throws `ERROR_RESTRICTED_ITEM` with the matched rows; `SEVERE_VIOLATION` calls `UserStateService.flagForReview` (actor `null`, as the auto-lift job does, reason `SEVERE_RESTRICTED_ITEM_VIOLATION`) and throws `ERROR_ACCOUNT_SUSPENDED`.
- [ ] `acceptCompliance(listingId, sellerId, checkId, policyCodes)`: the check belongs to the listing, is the latest for the current content hash and is `COMPLIANCE_REQUIRED`; every returned policy must be accepted; stores one row per policy with the listing, category, policy version and time.
- [ ] Expose `RestrictedItemGate.requireCleared(listingId)`: passes only for the latest check on the current content hash that is `SAFE`, `COMPLIANCE_REQUIRED` fully accepted at the current policy version, an admin-approved `UNCLEAR`, or blocked but overturned on appeal; otherwise `ERROR_RESTRICTED_CHECK_REQUIRED` (stale or missing) or the blocking error.
- [ ] A listing whose latest check is `RESTRICTED` or `SEVERE_VIOLATION` stays blocked until its content changes (new hash, new check) or an appeal is overturned.
- [ ] Repeated violations: count prior `RESTRICTED` and `SEVERE_VIOLATION` checks per seller and flag the account for review after 3 blocked checks in 30 days (approved 2026-10-16; configurable through `ValuexProperties`). Compliance results are not counted.

### Backend — API
- [ ] `POST /api/v1/listings/{listingId}/restricted-check` returning the LLD §D.4 payloads; the blocking result includes the matched rows (`title`, `message`) and a guidelines link; the compliance result includes `checkId`, the rows to show and `policyVersion`.
- [ ] `POST /api/v1/listings/{listingId}/restricted-check/{checkId}/compliance-acceptance` with `{ "policyCodes": [...] }` ("Agree & Continue"); "Cancel" needs no call.
- [ ] `POST /api/v1/listings/{listingId}/restricted-check/{checkId}/appeal` (seller, one appeal per check, only for `RESTRICTED`/`SEVERE_VIOLATION`); appeals are stored `PENDING` with no review endpoint until the admin console (Sprint 10).
- [ ] Standard `ApiResponse` envelope and central exception handling; seller ID from the security context only.

### Mobile (Flutter)
- [ ] `ListingRepository` calls for the check, the acceptance and the appeal; parse the three outcomes.
- [ ] Call the check from the Item Details **Choose Listing Plan** action after the details are saved (`_continue` in `item_details_screen.dart`) and before opening the plan page (US-114).
- [ ] **Compliance popup** (design-system dialog, decided): all matched rows in one dialog with the messages in the seller's language, one "Agree & Continue" (records every row) and "Cancel"; continuing sends the acceptance and opens the plan page; Cancel stays on the page.
- [ ] **Blocked state**: `ERROR_RESTRICTED_ITEM` with the matched rows' titles and messages, a link to the prohibited items guidelines and a "Go Back" button; `ERROR_ACCOUNT_SUSPENDED` and the `LISTING_UNDER_REVIEW` advisory through `listing_error_messages.dart`; an appeal action for blocked results.
- [ ] Strings in English and Hindi: the popup titles, messages and buttons come from the server in both languages (section 8) and the app picks the seller's language; the app's own labels go in `app_en.arb` and `app_hi.arb`; tokens only; 48 dp tap targets; labelled controls; accessibility guideline tests.

### Documentation/Quality
- [ ] OpenAPI examples for the three endpoints; update LLD Part D (rule-based fallback, `source`, the new outcome and acceptance table, `VARCHAR` results, the sheet tables).
- [ ] After implementation, create `Documents/Manual Testing Guides/US-007-Testing-Guide.md`.

## 5. Test Plan

Target >90% coverage for new code (`CLAUDE.md`).

### Unit Tests
- [ ] `TextNormalizer`: case, accents, punctuation, repeated spaces, Devanagari text unchanged.
- [ ] Checker: "wine" matches; "wine glass" matches (known false positive, covered by appeal); "farms" does not match "arms"; plural variants; multi-word phrases; term at start/end of text; match in title only, in description only, in both.
- [ ] Highest outcome wins (`SEVERE_VIOLATION` over `RESTRICTED` over `COMPLIANCE_REQUIRED`); all matched rows are returned.
- [ ] A Conditional keyword on a non-Conditional category gives `COMPLIANCE_REQUIRED`; a Conditional category with clean text also does; CAT-0204 and CAT-0742 give `SAFE`; every Real Estate L3 gives `COMPLIANCE_REQUIRED`.
- [ ] Inactive terms are ignored; empty title/description is `SAFE`.
- [ ] Loader: the sheet's 12 Prohibited and 9 Conditional rows load with a version; a conditional-category code that is unknown or disabled, an unmapped Conditional L3, or a term pointing at no policy fails the load.
- [ ] Service: `SAFE`, `COMPLIANCE_REQUIRED`, `RESTRICTED`, `SEVERE_VIOLATION` (account flagged, actor null), `UNCLEAR` (AI only), AI disabled, AI timeout/open circuit falls back to rules, check persisted with correct `source`, `model_version`, `content_hash` and `policy_version`.
- [ ] Acceptance: stored per policy with listing, category, policy version and time; a policy not in the check, a stale check, another seller's listing and a repeated acceptance are rejected.
- [ ] Gate: passes for `SAFE`, for an accepted `COMPLIANCE_REQUIRED` and for an overturned appeal; refuses a missing, stale (title, description, category or photos changed), blocked or unaccepted check; a new policy version invalidates earlier acceptances.
- [ ] Not owner / not `DRAFT` / fewer than 2 photos / no category rejected; appeal allowed only once and only for blocking results.
- [ ] Photo-based Prohibited result: a stored suggestion with a Prohibited `restrictionPolicyCode` and unchanged photos gives `RESTRICTED` (or `SEVERE_VIOLATION` for the severe rows); changed photos, an unknown code or a Conditional code are ignored.
- [ ] Repeated-violation threshold flags the account; compliance results are not counted.

### Integration Tests (Testcontainers PostgreSQL)
- [ ] Migration applies; the loader fills the policies, the seeded terms and the conditional-category map.
- [ ] `POST /restricted-check` end to end with AI disabled: clean listing, Conditional category (accept, then the gate opens), restricted listing, severe listing (account moves to `UNDER_REVIEW`).
- [ ] Mocked AI Gateway success, 5xx and timeout paths.
- [ ] IDOR: another seller cannot check, accept or appeal.

### Mobile Tests (Flutter)
- [ ] Item Details to plan flow with fakes: pass, compliance popup (Agree & Continue and Cancel), blocked screen, unavailable service.
- [ ] Strings and accessibility checks in English and Hindi.

### `valuex-ai` Tests
- [ ] The classification prompt lists the 12 Prohibited rows; the schema accepts an optional `restrictionPolicyCode`; an unknown code is dropped; existing cascade tests still pass; coverage stays above 90%.

## 6. Validation Checklist

- [ ] With `valuex.ai.enabled=false` (default) the check runs from the database tables and never calls the AI.
- [ ] A match blocks the listing exactly like an AI `RESTRICTED` result (same error, same stored check, same appeal path).
- [ ] A Conditional category, or a Conditional keyword or AI finding, always shows the popup with the sheet's text, and the seller cannot continue without "Agree & Continue"; the acceptance holds listing, category, policy version and time.
- [ ] Every Real Estate L3 shows the popup; CAT-0204 and CAT-0742 do not.
- [ ] Matching is whole word/phrase; substring false positives such as "farms" are avoided.
- [ ] Terms exist for every Prohibited row that text can reveal.
- [ ] Severe matches flag the account through the existing US-088 state service, not by direct SQL.
- [ ] AI failure never lets an unchecked listing through (it falls back to the rule check).
- [ ] No path to plan selection or publication accepts a listing without a cleared check on its current content.
- [ ] Matched terms are redacted in logs; ownership comes from the security context.
- [ ] Checkstyle, full tests, coverage and SonarQube pass before push.

## 7. Open Gaps / Questions

1. **Seed list and severities (decided).** Approved as proposed on 2026-10-16, now linked to the sheet's rows. Hindi and regional-language terms are not seeded; add later through the table.
2. **Repeated-violation threshold (decided).** 3 blocked checks in 30 days flags the account for review.
3. **Title and description entry (resolved).** US-114 is built; `listings.category_id` and `CategoryService` (US-006) give the category. The temporary `category_slug` of the old plan is no longer needed.
4. **Where the app calls the check (decided).** From the Item Details page's **Choose Listing Plan** button, after the details are saved and before plan selection. It runs again before a revised listing is resubmitted to review (US-089 `RESUBMIT`).
5. **Admin handling of `UNCLEAR` and appeals.** There is no admin console or RBAC until Sprint 10, so `UNCLEAR` results and appeals sit `PENDING` with no reviewer. Accepted for now; confirm.
6. **System actor for flagging (resolved).** `UserStateService` writes `actor_id` as null for platform actions (as the auto-lift job does), so `flagForReview(sellerId, null, reason)` is used.
7. **False positives** ("wine glass", "toy gun") are blocked until appeal; acceptable for the first version?
8. **`valuex-ai` moderation endpoint (decided 2026-10-29).** Not added. The AI vision model finds the category (US-005) and the Restrictions policy is applied to that category (scope decision 7).
9. **Several rows in one popup (decided: agreed).** One dialog lists all rows with a single "Agree & Continue" that records every row.
10. **Popup language (decided: Hindi required).** English and Hindi are both shipped; the Hindi texts in section 8 were reviewed and approved.
11. **Design (decided).** Build with the design system's dialog; no Figma frame exists for it.
12. **Conditional-category map (decided).** Generated from section 7 of the taxonomy review and loaded with the sheet; you review the generated file before go-live.
13. **Order of work.** This story is built before US-117 and US-008: its migration is `V18`, so US-117 becomes `V19` and US-008 `V20`.
14. **Prohibited items from photos (decided 2026-10-29: extend the vision call).** The taxonomy has no Prohibited category, so the category alone cannot block a firearm photo. The US-005 classification call also returns an optional `restrictionPolicyCode` from the 12 Prohibited rows (no extra model call). This touches `valuex-ai` (prompt, schema, tests) and the US-005 backend code (DTO, one column), and adds roughly 1 SP to this story; to be confirmed when the story is sized. With AI off, text keywords are the only Prohibited signal.

---

## 8. Hindi Texts (reviewed and approved 2026-10-29)

Translations of the Restrictions sheet; codes are the stable `restriction_policies.code` values. Reviewed by the product owner on 2026-10-29. Buttons: **Go Back** = वापस जाएँ · **I Understand** = ठीक है · **Agree & Continue** = सहमत हों और आगे बढ़ें · **Cancel** = रद्द करें.

### 8.1 Prohibited (shown only when an item is detected and blocked)

| Code | Title (Hindi) | Popup message (Hindi) |
|---|---|---|
| `WEAPONS` | आग्नेयास्त्र, गोला-बारूद, विस्फोटक और हथियारों के पुर्ज़े | ValueX पर हथियार और उनसे जुड़ी वस्तुओं की अनुमति नहीं है। आगे बढ़कर आप पुष्टि करते हैं कि इस लिस्टिंग में आग्नेयास्त्र, गोला-बारूद, विस्फोटक, हथियारों के पुर्ज़े या इसी तरह की विनियमित वस्तुएँ शामिल नहीं हैं। |
| `DRUGS` | अवैध नशीले पदार्थ, मादक पदार्थ, नियंत्रित पदार्थ | ValueX पर अवैध नशीले पदार्थ, मादक पदार्थ और नियंत्रित पदार्थों की अनुमति नहीं है। आगे बढ़कर आप पुष्टि करते हैं कि इस लिस्टिंग में ऐसा कोई पदार्थ न तो है और न ही उसकी पेशकश की जा रही है। |
| `PRESCRIPTION_MEDICINES` | डॉक्टर के पर्चे वाली दवाएँ और केवल पर्चे पर मिलने वाले चिकित्सा उत्पाद | डॉक्टर के पर्चे वाली दवाएँ और केवल पर्चे पर मिलने वाले चिकित्सा उत्पाद तब तक लिस्ट नहीं किए जा सकते जब तक ValueX कोई मंज़ूर विनियमित-कॉमर्स व्यवस्था स्पष्ट रूप से शुरू न करे। आगे बढ़कर आप पुष्टि करते हैं कि यह वस्तु केवल पर्चे पर मिलने वाली या अन्यथा प्रतिबंधित नहीं है। |
| `ALCOHOL_TOBACCO` | शराब और निकोटिन/तंबाकू/वेपिंग उत्पाद | ValueX पर शराब, तंबाकू, निकोटिन और वेपिंग उत्पादों की अनुमति नहीं है। आगे बढ़कर आप पुष्टि करते हैं कि इस लिस्टिंग में आयु-प्रतिबंधित ऐसे कोई उत्पाद शामिल नहीं हैं। |
| `LIVE_ANIMALS` | जीवित जानवर और वन्यजीव उत्पाद | ValueX पर जीवित जानवरों और संरक्षित या वन्यजीव-आधारित उत्पादों की अनुमति नहीं है। आगे बढ़कर आप पुष्टि करते हैं कि यह लिस्टिंग किसी जीवित जानवर की नहीं है और इसमें प्रतिबंधित वन्यजीव सामग्री शामिल नहीं है। |
| `COUNTERFEIT` | नकली, ब्रांड की प्रतिकृति और पायरेटेड मीडिया | केवल असली और कानूनी रूप से बेचने योग्य सामान ही लिस्ट किया जा सकता है। आगे बढ़कर आप पुष्टि करते हैं कि यह वस्तु असली है, नकली या ब्रांड की प्रतिकृति नहीं है और इसमें पायरेटेड मीडिया शामिल नहीं है। |
| `STOLEN_GOODS` | चोरी का सामान या हटाए/बदले गए पहचान चिह्न वाला सामान | आप केवल वही वस्तुएँ लिस्ट कर सकते हैं जिनके आप कानूनी रूप से मालिक हैं या जिन्हें बेचने के लिए आप अधिकृत हैं। आगे बढ़कर आप पुष्टि करते हैं कि यह वस्तु चोरी की नहीं है और सीरियल नंबर, IMEI, चेसिस नंबर या अन्य पहचान चिह्न अवैध रूप से हटाए या बदले नहीं गए हैं। |
| `ADULT` | अश्लील सामग्री और स्पष्ट रूप से वयस्क उत्पाद | अश्लील सामग्री और स्पष्ट रूप से वयस्क उत्पादों की ValueX पर अनुमति नहीं है। आगे बढ़कर आप पुष्टि करते हैं कि इस लिस्टिंग में प्रतिबंधित वयस्क सामग्री या उत्पाद शामिल नहीं हैं। |
| `HUMAN_ORGANS` | मानव शरीर के अंग, शारीरिक द्रव, ऑर्गन | ValueX पर मानव शरीर के अंग, ऑर्गन और शारीरिक द्रव की अनुमति नहीं है। आगे बढ़कर आप पुष्टि करते हैं कि इस लिस्टिंग में ऐसी कोई सामग्री शामिल नहीं है। |
| `HAZARDOUS` | ख़तरनाक रसायन, ज़हर, रेडियोधर्मी पदार्थ | ValueX पर ख़तरनाक रसायन, ज़हर और रेडियोधर्मी पदार्थों की अनुमति नहीं है। आगे बढ़कर आप पुष्टि करते हैं कि इस वस्तु में कोई प्रतिबंधित ख़तरनाक या रेडियोधर्मी पदार्थ नहीं है। |
| `IDS_CREDENTIALS` | सरकारी पहचान पत्र, बैंक खाते, SIM पहचान, क्रेडेंशियल, पहचान-हस्तांतरण प्रतिबंध वाले टिकट | सरकारी पहचान पत्र, बैंक खाते, SIM पहचान, लॉगिन क्रेडेंशियल और ऐसे टिकट या अधिकार जिन्हें कानूनी रूप से हस्तांतरित नहीं किया जा सकता, की अनुमति नहीं है। आगे बढ़कर आप पुष्टि करते हैं कि इस लिस्टिंग में ऐसी कोई वस्तु या पहुँच का अधिकार शामिल नहीं है। |
| `DIGITAL_ACCOUNTS` | डिजिटल खाते, गेम अकाउंट, सॉफ़्टवेयर कीज़ जहाँ कानूनी रूप से हस्तांतरण अनुमत नहीं | डिजिटल खाते, गेम अकाउंट और सॉफ़्टवेयर कीज़ केवल तभी बेचे जा सकते हैं जब उनका हस्तांतरण कानूनी और अनुबंध के अनुसार अनुमत हो। आगे बढ़कर आप पुष्टि करते हैं कि आपको इस वस्तु को हस्तांतरित करने का अधिकार है और यह लिस्टिंग लागू लाइसेंस या सेवा की शर्तों का पालन करती है। |

### 8.2 Conditional (shown with "Agree & Continue")

| Code | Title (Hindi) | Popup message (Hindi) |
|---|---|---|
| `COSMETICS` | खुले हुए कॉस्मेटिक्स, स्किनकेयर, परफ़्यूम और निजी स्वच्छता उत्पाद | स्वच्छता और सुरक्षा के लिए केवल फ़ैक्टरी-सील्ड और अनखुले कॉस्मेटिक्स, स्किनकेयर, परफ़्यूम और निजी स्वच्छता उत्पाद ही लिस्ट किए जाने चाहिए। आगे बढ़कर आप पुष्टि करते हैं कि वस्तु अनयूज़्ड और सील्ड है तथा उसका विवरण सही है। |
| `FOOD` | खाद्य पदार्थ, पालतू जानवरों का भोजन और घरेलू उपभोग की वस्तुएँ | आगे बढ़कर आप पुष्टि करते हैं कि यह उत्पाद सील्ड है, एक्सपायर नहीं हुआ है, मूल लेबल वाली पैकिंग में है, उपयोग के लिए सुरक्षित है और दोबारा बेचने के लिए कानूनी रूप से अनुमत है। जो वस्तुएँ इन शर्तों को पूरा नहीं करतीं, उन्हें ValueX अस्वीकार कर सकता है। |
| `JEWELLERY_COLLECTIBLES` | महँगे आभूषण, लग्ज़री घड़ियाँ और संग्रहणीय वस्तुएँ | आगे बढ़कर आप पुष्टि करते हैं कि आप इस वस्तु के कानूनी मालिक हैं या इसे बेचने के लिए अधिकृत हैं, लिस्टिंग असली और सही है, और माँगे जाने पर आप प्रामाणिकता, मूल्यांकन या स्वामित्व का प्रमाण दे सकते हैं। |
| `MEDICAL_EQUIPMENT` | चिकित्सा उपकरण | आगे बढ़कर आप पुष्टि करते हैं कि यह दोबारा बेचने के लिए अनुमत उपकरण है, यह पर्चे पर मिलने वाला या पेशेवर उपयोग तक सीमित प्रतिबंधित उत्पाद नहीं है, और इसकी स्थिति, स्वच्छता और ज्ञात सीमाओं की पूरी जानकारी दी गई है। |
| `DRONES` | ड्रोन | आगे बढ़कर आप पुष्टि करते हैं कि ड्रोन रखना और बेचना कानूनी है, जहाँ लागू हो वहाँ आवश्यक पंजीकरण या पहचान का विवरण दिया जाएगा, और बैटरी या शिपिंग से जुड़े प्रतिबंधों का पालन किया जाएगा। |
| `SAFETY_EQUIPMENT` | इस्तेमाल किए हुए हेलमेट, बच्चों की कार सीट और सुरक्षा उपकरण | सुरक्षा से जुड़े इस्तेमाल किए हुए उपकरण में अतिरिक्त सावधानी ज़रूरी है। आगे बढ़कर आप पुष्टि करते हैं कि दुर्घटना, टक्कर, क्षति, उम्र और एक्सपायरी की सारी ज्ञात जानकारी दी गई है और जहाँ सुरक्षा का इतिहास अज्ञात है वहाँ वस्तु को सुरक्षित नहीं बताया जा रहा है। |
| `LARGE_BATTERIES` | बड़ी बैटरियाँ / लिथियम पावर पैक | आगे बढ़कर आप पुष्टि करते हैं कि बैटरी या पावर पैक का विवरण सही है, वह क्षतिग्रस्त, फूला हुआ या लीक करता हुआ नहीं है, और परिवहन व कूरियर के सभी लागू प्रतिबंधों का पालन किया जाएगा। डिलीवरी के विकल्प सीमित हो सकते हैं या उपलब्ध नहीं हो सकते। |
| `PLANTS_SEEDS` | पौधे और बीज | आगे बढ़कर आप पुष्टि करते हैं कि पौधे या बीज की प्रजाति को बेचना और ले जाना कानूनी है और वह संरक्षित, प्रतिबंधित या अन्यथा नियंत्रित नहीं है। स्थानीय, प्रजाति-विशेष या शिपिंग के नियम फिर भी लागू हो सकते हैं। |
| `REAL_ESTATE` | रियल एस्टेट / संपत्ति की लिस्टिंग | आगे बढ़कर आप पुष्टि करते हैं कि आप इस संपत्ति के मालिक हैं या इसका विज्ञापन करने के लिए अधिकृत हैं, संपत्ति और पोस्ट करने वाले का सारा विवरण सही है, और जहाँ लागू हो वहाँ आवश्यक प्रोजेक्ट या RERA जानकारी दी जाएगी। संपत्ति की ड्यू डिलिजेंस तथा हस्तांतरण या पट्टे की औपचारिकताएँ सामान्य सामान-डिलीवरी प्रक्रिया से बाहर रहती हैं। |

Points to check when reviewing: "ऑर्गन", "लग्ज़री", "ड्यू डिलिजेंस" and "रेडियोधर्मी" are kept in familiar or transliterated form; "ठीक है" is used for "I Understand" to keep the button gender-neutral; "RERA", "IMEI" and "SIM" stay in Latin letters.

---

**Status:** Approved (2026-10-29; the product owner reviewed the Hindi texts in section 8 and approved the plan, including the vision-based Prohibited detection)

---

## 9. Implementation Notes (what was built, and where it differs from this plan)

Branch `feature/US-007-restricted-items-prevention` in `valuex-backend`, `valuex-ai` and `valuex-mobile`. Migration `V18`.

| # | Plan said | Built | Why |
|---|---|---|---|
| 1 | Seed the policy rows and terms in the migration | `V18` only creates the tables and columns. A new `RestrictionPolicyLoader` (`ApplicationRunner`, order 2, after the taxonomy import) reads four files from `src/main/resources/restrictions/` and writes the rows. Rows and terms that left the files are deactivated | The Hindi texts, the sheet text and the 50 category rows belong in reviewable files, not in SQL; the policy version stays tied to the exact text |
| 2 | Policy version | SHA-256 of the four source files; the load is skipped when the database already holds that version; a bad file stops the start with every problem listed | An acceptance is tied to the exact text the seller agreed to |
| 3 | Extra file | `restriction-policies.csv` holds the code, default severity and Hindi texts per sheet row; the sheet itself is copied unchanged as `ValueX_JustQlic_Master_Restrictions.csv` | One place for the codes and translations |
| 4 | Seed terms | 182 reviewed terms. Left out as too likely to hit innocent text: bare "gun", "arms", "passport", "sim card", "fake", and the singular "puppy" and "kitten" | Whole-word matching has no context; the appeal path covers the rest |
| 5 | Blocked result throws `ERROR_RESTRICTED_ITEM` | `RestrictedItemCheckService.runCheck` returns the stored check; the controller turns `RESTRICTED` into 400 and `SEVERE_VIOLATION` into 403, with `data` and `error` in the same body | A thrown exception would roll back the stored check and hide the matched rows from the app |
| 6 | AI path runs at check time | No model call at check time. The check uses the `restrictionPolicyCode` stored with the latest completed US-005 suggestion, only while its `media_hash` equals the draft's current photos (stored in `listing_ai_suggestions.restriction_policy_code` and `media_hash`) | Photos already went through the vision call; no second call, no latency, nothing can fail at this step. `UNCLEAR` is therefore never produced by this build; it stays valid for the admin flow |
| 7 | Mocked AI Gateway success, 5xx, timeout integration tests | Not applicable (see 6); the US-005 gateway tests still cover those paths | |
| 8 | Guidelines link in the blocked answer | Not included. There is no guidelines page or URL yet; the blocked dialog shows the server's "See prohibited items policy" message and the matched rows | Add the link when the page exists |
| 9 | Content hash | SHA-256 over title, description, category code and a hash of the sorted photo ids. `ContentFingerprint` | A change to any of them makes an earlier check stale |
| 10 | `valuex-ai` | The classification schema has a required `restrictionPolicyCode` (one of the 12 Prohibited codes or null); the prompt lists the codes; an unknown code is dropped; the result is returned also when the item has no category | OpenAI strict schemas need every property required |
| 11 | Mobile error body | `ApiError` now carries the envelope's `data`; `ListingRepository.checkRestrictedItems` turns the 400/403 blocked bodies into a result | The blocked answer needs the matched rows |

Quality results: see the testing guide section "Running the automated tests".

Open items for the product owner: the extra ~1 SP for the `valuex-ai` change (open gap 14), the missing guidelines link (row 8), and that `UNCLEAR` and appeals sit `PENDING` until the admin console (open gap 5).

