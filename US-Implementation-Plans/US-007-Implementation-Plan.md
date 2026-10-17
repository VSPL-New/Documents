# US-007: Restricted Items Prevention — Implementation Plan

## 1. Header

| Field | Value |
|---|---|
| Story ID | US-007 |
| Title | Restricted Items Prevention |
| Sprint | Sprint 2 — Seller Listing Creation |
| Story Points | 5 |
| Repos | valuex-backend, valuex-mobile (error display only). `valuex-ai` is out of scope (separate team, integrated later) |
| Dependency | US-089 (`ListingLifecycleService`, built first); US-005 (shared `valuex.ai.enabled` switch, `AiGatewayClient`, Resilience4j setup); US-004 draft listings; the new Item Details story (title/description entry, see Open Gaps); US-006 for category matching tests; US-088 `UserStateService` for account flagging |

**Scope decisions (2026-10-16):**
1. AI is assumed disabled or down. A **rule-based check** against a `restricted_items` database table of terms replaces the AI check in that case. It looks at the seller's **title, description and category**.
2. A match is treated exactly as if the AI had identified a restricted item: the check fails, the listing is blocked and the rest of the flow continues as for an AI `RESTRICTED` (or `SEVERE_VIOLATION`) result. No match is `SAFE`.
3. This replaces the LLD's fail-closed `ERROR_MODERATION_UNAVAILABLE` for the AI-off and AI-down cases. With AI enabled and the AI answering, the AI result is used.
4. The table is seeded with typical restricted items (wine, liquor, arms and so on) by the migration; each term has a severity.
5. Category matching is implemented now, but is only tested end to end once US-006 (category taxonomy) is available.

## 2. Story Recap

**As a** platform **I want to** prevent listing of restricted items **so that** the platform remains compliant and safe.

**Acceptance Criteria** (`Documents/user-stories.md`):
- When AI/system detects restricted items in photos or description, listing creation is blocked, the seller is shown which items are prohibited, and guidelines are displayed.
- When a seller tries to publish a restricted-item listing, the system prevents publication and flags the account for review.

**Restricted item categories:** weapons, explosives, ammunition · drugs, narcotics, tobacco, alcohol · adult content · counterfeit/pirated goods · live animals · human body parts/organs · hazardous materials · documents (passports, IDs, degrees).

**Edge Cases:** borderline item (toy weapon) · restricted keyword in a legitimate listing · coded language · item legal in some states only · seller appeals.

**Validation Rules:** text keyword scanning in title/description · photo analysis (AI only) · manual review for borderline cases · repeated violations lead to account suspension.

**Error Scenarios:** `ERROR_RESTRICTED_ITEM` · `ERROR_SUSPICIOUS_CONTENT` · `ERROR_ACCOUNT_SUSPENDED`.

## 3. Design Reference

Primary source: [Sprint-2-Seller Listing Creation-LLD.md — Part D](../LLD/Sprint-2-Seller%20Listing%20Creation-LLD.md#part-d---us-007-restricted-items-prevention), §D.1–D.10. Also [HLD Part 4 §8](../HLD/04-AI-Architecture.md#8-restricted-item--content-moderation-ai) and [US-005 plan](US-005-Implementation-Plan.md) for the shared AI switch.

**Key design decisions:**
- One entry point, `POST /api/v1/listings/{listingId}/restricted-check`, runs `RestrictedItemCheckService`. It uses the AI Gateway when `valuex.ai.enabled=true` and the AI answers; otherwise (disabled, timeout, error, open circuit) it uses the rule-based `RuleBasedRestrictedItemChecker`. Both return the same result type (`SAFE`, `RESTRICTED`, `SEVERE_VIOLATION`; `UNCLEAR` only from AI), so everything after the check is common code.
- Result handling follows LLD §D.5: `SAFE` proceeds; `UNCLEAR` (AI only) is queued for manual review; `RESTRICTED` blocks with `ERROR_RESTRICTED_ITEM`; `SEVERE_VIOLATION` blocks and flags the account via `UserStateService.flagForReview`.
- Every check is saved to `listing_moderation_checks` with `source` (`AI` or `RULES`) and `model_version` (`rules-v1` for the rule check), so rule results stay auditable and can be re-run once AI arrives.
- Every Sprint 2 listing must pass this gate before plan selection. This story exposes the gate; US-008/US-009 call it.

**Term matching (recommended and adopted):**
- Normalise title and description: Unicode NFKC, lower case, strip accents, replace punctuation and symbols with spaces, collapse whitespace.
- Match **whole words or whole phrases** on token boundaries, never raw substrings, so "arms" does not hit "farms", "charms" or "alarms".
- No stemming or fuzzy matching in the first version. Plurals and common variants are seeded as separate terms ("gun", "guns"). This keeps results predictable; false positives are handled by the appeal flow, and coded language is left to the AI later.
- A term may carry a `category_slug`. When the listing's category (primary or additional, from US-006) matches an active term's `category_slug`, that is also a match.
- Every term has a severity: `RESTRICTED` (block) or `SEVERE_VIOLATION` (block and flag the account).

## 4. Implementation Steps

### Database Migration — `valuex-backend`
- [ ] `V17__restricted_items_and_moderation_checks.sql` (after US-089's `V13`, US-114's `V14`, US-078's `V15` and US-005's `V16`; renumber to the next free version at implementation time).
- [ ] `restricted_items`: `id`, `term` (stored normalised, unique among active rows), `restriction_category` (`WEAPONS`, `EXPLOSIVES`, `AMMUNITION`, `DRUGS`, `TOBACCO`, `ALCOHOL`, `ADULT`, `COUNTERFEIT`, `LIVE_ANIMALS`, `HUMAN_ORGANS`, `HAZARDOUS`, `DOCUMENTS`), `severity` (`RESTRICTED`, `SEVERE_VIOLATION`), `category_slug` (nullable), `active`, `created_at`. Index on `term`.
- [ ] Seed rows in the same migration for typical items, for example: alcohol (wine, liquor, whisky, vodka, rum, beer), tobacco (cigarette, cigar, hookah tobacco), weapons (arms, gun, pistol, rifle, firearm, revolver), ammunition (bullet, cartridge, ammunition), explosives (explosive, dynamite, detonator), drugs (cocaine, heroin, marijuana, narcotics), counterfeit ("replica", "first copy" luxury items), documents (passport, aadhaar card, degree certificate), human organs, live animals. Seed terms and severities were approved as proposed on 2026-10-16: `SEVERE_VIOLATION` for explosives, narcotics and human organs, `RESTRICTED` for the rest; terms are English only for now.
- [ ] `listing_moderation_checks` per LLD §D.3 plus `source` (`AI`, `RULES`); `result` as `VARCHAR` with a check constraint instead of a Postgres enum type (same approach as `listings.status`).
- [ ] `listing_moderation_appeals` per LLD §D.3.

### Backend — Domain and Persistence
- [ ] Entities and repositories for `RestrictedItem`, `ListingModerationCheck`, `ListingModerationAppeal` under the listing module layers.
- [ ] `ModerationResult`, `RestrictionCategory`, `RestrictionSeverity` enums.
- [ ] Repository method returning active terms (and active terms with a `category_slug`).

### Backend — Rule-Based Checker
- [ ] `TextNormalizer` (NFKC, lower case, accent strip, punctuation to spaces).
- [ ] `RuleBasedRestrictedItemChecker`: builds token n-grams from normalised title and description up to the longest active term, matches them against the active terms, and also matches the listing's categories against `category_slug`. Returns the highest severity found with the matched categories and terms.
- [ ] `ListingCategoryProvider` port returning the listing's category slugs; until US-006 lands the adapter returns an empty set, and the US-006 adapter is wired in when it arrives.
- [ ] Matched terms are stored but redacted (`***`) in application logs (LLD §D.10).

### Backend — AI Path (no AI logic)
- [ ] Add `checkRestrictedItem` to `AiGatewayClient` for `POST /ai/v1/moderation/restricted-item-check` (`mediaIds`, title, description) with its own Resilience4j instance `moderationGateway`, 8s timeout, no retries (LLD §D.9).
- [ ] On disabled, timeout, error or open circuit, fall back to `RuleBasedRestrictedItemChecker` instead of failing closed. Verified with a mocked server only.

### Backend — `RestrictedItemCheckService`
- [ ] Verify ownership and `DRAFT` status; run the AI path when `valuex.ai.enabled=true`, else the rule-based checker.
- [ ] Persist the check, then handle the result: `SAFE` proceeds; `UNCLEAR` queues for manual review and returns the `LISTING_UNDER_REVIEW` advisory; `RESTRICTED` throws `ERROR_RESTRICTED_ITEM`; `SEVERE_VIOLATION` calls `UserStateService.flagForReview` and throws `ERROR_ACCOUNT_SUSPENDED`.
- [ ] A listing that already has a `RESTRICTED` or `SEVERE_VIOLATION` check cannot pass again until its title, description or category changes (re-check) or an appeal is overturned.
- [ ] Expose `RestrictedItemGate.requireCleared(listingId)` so US-008 (plan selection) and US-009 (publication) can refuse a listing without a current `SAFE` or admin-approved check.
- [ ] Repeated violations: count prior `RESTRICTED` checks per seller and flag the account for review after 3 blocked checks in 30 days, as the story requires (threshold approved 2026-10-16; configurable through `ValuexProperties`).

### Backend — API
- [ ] `POST /api/v1/listings/{listingId}/restricted-check` returning the LLD §D.4 payloads (blocking result includes `matchedCategories` and the guidelines text).
- [ ] `POST /api/v1/listings/{listingId}/restricted-check/{checkId}/appeal` (seller, one appeal per check, only for `RESTRICTED`/`SEVERE_VIOLATION`); appeals are stored `PENDING` with no review endpoint until the admin console (Sprint 10).
- [ ] Standard `ApiResponse` envelope and central exception handling; seller ID from the security context only.

### Mobile (Flutter)
- [ ] Show `ERROR_RESTRICTED_ITEM` (with the matched categories and a link to the prohibited items guidelines), `ERROR_ACCOUNT_SUSPENDED` and the `LISTING_UNDER_REVIEW` advisory using `listing_error_messages.dart` and l10n (English and Hindi).
- [ ] Call the check from the Item Details page's **Choose Listing Plan** action (US-114).

### Documentation/Quality
- [ ] OpenAPI examples for the two endpoints; update the Part D LLD for the rule-based fallback, `source` column and severity.
- [ ] After implementation, create `Documents/Manual Testing Guides/US-007-Testing-Guide.md`.

## 5. Test Plan

Target >90% coverage for new code (`CLAUDE.md`).

### Unit Tests
- [ ] `TextNormalizer`: case, accents, punctuation, repeated spaces, Devanagari text unchanged.
- [ ] Checker: "wine" matches; "wine glass" matches (known false positive, covered by appeal); "farms" does not match "arms"; plural variants; multi-word phrases; term at start/end of text; match in title only, in description only, in both.
- [ ] Highest severity wins when `RESTRICTED` and `SEVERE_VIOLATION` terms both match.
- [ ] Inactive terms are ignored; empty title/description is `SAFE`.
- [ ] Category matching with a fake `ListingCategoryProvider` (primary and additional categories).
- [ ] Service: `SAFE`, `RESTRICTED`, `SEVERE_VIOLATION` (account flagged), `UNCLEAR` (AI only), AI disabled, AI timeout/open circuit falls back to rules, check persisted with correct `source` and `model_version`.
- [ ] Not owner / not `DRAFT` rejected; appeal allowed only once and only for blocking results.
- [ ] Gate refuses a listing without a current cleared check.
- [ ] Repeated-violation threshold flags the account.

### Integration Tests (Testcontainers PostgreSQL)
- [ ] Migration applies; seeded terms present with valid severities.
- [ ] `POST /restricted-check` end to end with AI disabled for a clean listing, a restricted listing and a severe listing (account moves to `UNDER_REVIEW`).
- [ ] Mocked AI Gateway success, 5xx and timeout paths.
- [ ] IDOR: another seller cannot check or appeal a listing.

### Deferred Until US-006 Is Available
- [ ] End-to-end check that a listing tagged with a restricted category (for example alcohol) is blocked through the real `ListingCategoryProvider`.
- [ ] Mobile category flow with the check.

## 6. Validation Checklist

- [ ] With `valuex.ai.enabled=false` (default) the check runs from the database table and never calls the AI.
- [ ] A match blocks the listing exactly like an AI `RESTRICTED` result (same error, same stored check, same appeal path).
- [ ] Matching is whole word/phrase; substring false positives such as "farms" are avoided.
- [ ] Seed data covers every restricted category in the story that can be matched by text.
- [ ] Severe matches flag the account through the existing US-088 state service, not by direct SQL.
- [ ] AI failure never lets an unchecked listing through (it falls back to the rule check).
- [ ] No publication path accepts a listing without a cleared check.
- [ ] Matched terms are redacted in logs; ownership comes from the security context.
- [ ] Category matching is implemented and awaiting US-006 for end-to-end validation.
- [ ] Checkstyle, full tests, coverage and SonarQube pass before push.

## 7. Open Gaps / Questions

1. **Seed list and severities (decided).** Approved as proposed. Hindi and regional-language terms are not seeded; add later through the table.
2. **Repeated-violation threshold (decided).** 3 blocked checks in 30 days flags the account for review.
3. **Title and description entry (decided).** US-114 "Listing Item Details Entry" adds the Flutter Item Details page and the draft-update endpoint that saves title, description, condition, category and price. It is built before this story so the check has seller text to scan. It also adds a temporary `listings.category_slug`, so `ListingCategoryProvider` can read the listing's category now; restricted categories in the table still need real taxonomy slugs from US-006 to match.
4. **Where the app calls the check (decided).** From the Item Details page's **Choose Listing Plan** button, after the details are saved and before plan selection (so a seller does not pay for a listing that cannot be published). It runs again before a revised listing is resubmitted to review (US-089 `RESUBMIT`).
5. **Admin handling of `UNCLEAR` and appeals.** There is no admin console or RBAC until Sprint 10, so `UNCLEAR` results and appeals sit `PENDING` with no reviewer. Accepted for now; confirm.
6. **System actor ID** for `UserStateService.flagForReview` calls made by the platform rather than a person.
7. **False positives** ("wine glass", "toy gun") are blocked until appeal; acceptable for the first version?

---

**Status:** Draft
