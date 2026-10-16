# US-006: Multi-Category Tagging — Implementation Plan

## 1. Header

| Field | Value |
|---|---|
| Story ID | US-006 |
| Title | Multi-Category Tagging |
| Sprint | Sprint 2 — Seller Listing Creation |
| Story Points | 3 (see Open Gaps item 1: the picker may need more) |
| Repos | valuex-backend, valuex-mobile |
| Dependency | US-004 (draft listing); **US-114** (it adds the single `category_slug` and the category chips that this story replaces); US-089 (states). Built after US-114 and, if US-007 is already built, together with the change to US-007's checker described below |

**Scope decisions (2026-10-16):**
1. A listing has one **primary** category (mandatory) and up to **3 additional** categories, all from a predefined taxonomy.
2. This story owns the **taxonomy tables** and the read endpoints for them. Home (US-111, Sprint 3) reuses the same top-level categories instead of its mock list.
3. The primary and additional categories are saved when the seller taps **Done** in the picker, so the "unrelated categories" warning appears while the seller can still change them. The Item Details page (US-114) then shows the chosen categories and no longer has its own category chips.
4. Search by category (any of the four) is Sprint 3; this story only stores and validates the set.
5. The unrelated-categories check is a warning, not a block, and sets a flag on the listing for the Trust & Safety review (US-084) to read.

## 2. Story Recap

**As a** seller **I want to** tag my item with multiple categories **so that** it appears in relevant search results.

**Acceptance Criteria** (`Documents/user-stories.md`): when I select a primary category I can add up to 3 additional related categories; a buyer searching any of those categories finds my listing (Sprint 3).

**Edge Cases:** duplicate categories · unrelated categories (spam attempt) · very deep category tree (6+ levels) · more than the allowed number of categories.

**Validation Rules:** primary category mandatory · at most 3 additional · categories from the predefined taxonomy only · suspicious combinations are flagged for review.

**Error Scenarios:** `ERROR_DUPLICATE_CATEGORY` · `ERROR_MAX_CATEGORIES` ("Maximum 4 categories allowed") · `WARNING_UNRELATED_CATEGORIES`. The LLD adds `ERROR_PRIMARY_CATEGORY_REQUIRED` and `CATEGORY_NOT_FOUND`.

**Flutter notes (story):** multi-select picker with a hierarchical taxonomy; the primary chip shown apart from the additional tags; a tappable category tree with search and filter.

## 3. Design Reference

- Primary source: [Sprint-2-Seller Listing Creation-LLD.md — Part C](../LLD/Sprint-2-Seller%20Listing%20Creation-LLD.md#part-c---us-006-multi-category-tagging) §C.1–C.8, with the changes below. HLD Part 3 §4.3 (`categories`, `listing_categories`).
- **No Figma frame is known for the picker.** The Make file used for the listing flow has the category chips of the Item Details step only. Build the picker from the design system (see Open Gaps item 2).
- Existing code to reuse: `ListingController`, `ListingDraftService`, the US-114 details service and its editable-state check (`DRAFT` or `REVISION_REQUIRED`, `ERROR_LISTING_NOT_EDITABLE`), `ListingDraftResponse`, Spring Cache with Redis, the `ApiResponse` envelope; mobile `ItemDetailsScreen` (US-114), `ListingRepository`, `listing_error_messages.dart`, theme chips and inputs, `BrandGradientButton`.

**What differs from LLD Part C:**
- The LLD allows any category to be assigned. This plan allows **any active category** (not only leaves), but a deactivated category cannot be newly assigned.
- The LLD returns the tree only by parent. This plan adds a **name search** endpoint, because the story asks for search and filter in the picker.
- The LLD deletes and re-inserts the rows. This plan does the same inside one transaction, after taking the same row lock the draft code uses.
- A `slug` column is added to `categories` because US-114 stored a slug and the Home list identifies categories by id strings.

**Key design decisions:**
- **Taxonomy as data.** `categories` is a tree (`parent_id`, `depth`, `slug` unique, `sort_order`, `is_active`). The seed matches the Home list (electronics, laptops, mobiles, cameras, vehicles, furniture, fashion, appliances, books, sports, toys, music), using the same ids as slugs so that US-114's stored slugs map straight across. Deeper levels are product content (Open Gaps item 3); the code supports at least 8 levels and is tested with 7.
- **Relatedness rule (deterministic, no AI).** An additional category is related to the primary when (a) both share a common ancestor and each is no more than 2 levels below it (an ancestor or descendant counts), or (b) the two appear as a pair in `category_related_pairs` (an allow-list for cross-sell, for example Mobiles and Electronics). Top-level categories share no ancestor, so they relate only through the allow-list. The result is a warning list, never an error.
- **Flag for review.** `listings.categories_unrelated` (boolean) is set on every save from the checker result. US-084 reads it as one of its review signals; this story only sets it.
- **Temporary slug column replaced.** The migration copies `listings.category_slug` into `listing_categories` as the primary category and drops the column.

## 4. Implementation Steps

### Database Migration — `valuex-backend`
- [ ] `V22__listing_categories.sql` (next free version after US-009's `V21`, but before it if this story is built first; renumber at implementation time):
  - `categories` (`id`, `parent_id`, `slug` unique, `name`, `depth` with a check of 0 to 8, `sort_order`, `is_active`); indexes on `parent_id` and `slug`.
  - `listing_categories` (`listing_id`, `category_id`, `is_primary`, `created_at`, primary key `(listing_id, category_id)`) with the unique partial index `uq_listing_categories_primary` (one primary per listing) and an index on `category_id` for Sprint 3 search.
  - `category_related_pairs` (`category_a_id`, `category_b_id`, primary key on the pair; stored once, checked in both directions).
  - `listings.categories_unrelated BOOLEAN NOT NULL DEFAULT FALSE`.
  - Seed the 12 top-level categories and the electronics-family allow-list pairs.
  - Copy each `listings.category_slug` that matches a category into `listing_categories` as primary, then drop `category_slug`. Listings whose slug matches nothing keep no category and must pick one again (the integration test covers this).

### Backend — Taxonomy and Assignment
- [ ] `Category`, `ListingCategory`, `CategoryRelatedPair` entities and repositories (`findByParentIdAndActiveTrueOrderBySortOrder`, `findAllByIdIn`, a name search query, a recursive query for the path of a set of ids).
- [ ] `CategoryService`: `children(parentId)` (top level when null), `search(query)`, `pathsFor(ids)`. Responses are cached in Redis for 1 hour and the cache is evicted on deploy (the taxonomy changes only by migration in this story).
- [ ] `CategoryRelatednessChecker` implementing the rule above. Input: the primary and the additional categories with their ancestors; output: `true`/`false`.
- [ ] `ListingCategoryService.setCategories(listingId, sellerId, request)`:
  1. lock the listing for the owner (same call the draft code uses; another seller gets not found);
  2. require an editable status (the US-114 check; US-010 widens it to `PUBLISHED`);
  3. require a primary (`ERROR_PRIMARY_CATEGORY_REQUIRED`), at most 3 additional (`ERROR_MAX_CATEGORIES`), no duplicates among all ids (`ERROR_DUPLICATE_CATEGORY`);
  4. every id must exist and be active (`CATEGORY_NOT_FOUND`, 404);
  5. replace the rows in one transaction and flush so the primary unique index surfaces a clash at once;
  6. set `categories_unrelated` from the checker and return the categories with their paths and a `warnings` list that has `WARNING_UNRELATED_CATEGORIES` when the flag is set.
- [ ] Remove `categorySlug` from the US-114 `PATCH /api/v1/listings/{id}` request. Its "category required" check (`ERROR_CATEGORY_REQUIRED`) now looks for a primary row in `listing_categories`. `ListingDraftResponse` gets `categories` (primary and additional with paths) in place of the slug.
- [ ] US-008's "complete details" rule uses the same primary-category check (note added to its plan).
- [ ] Update US-007's `RuleBasedRestrictedItemChecker`: match restricted category terms against the slugs of **all** assigned categories (primary and additional), not the removed `category_slug`. Add a test: a restricted category added as an additional tag blocks the listing.

### Backend — API
- [ ] `GET /api/v1/categories/tree?parentId=` returns the active children of a node (top level without `parentId`); each item has `id`, `slug`, `name`, `depth`, `hasChildren`. The tree is loaded lazily by level, never as one payload, which handles trees of 6 or more levels.
- [ ] `GET /api/v1/categories/search?q=` returns up to 20 active categories whose name matches (case-insensitive, at least 2 characters), each with its full path, for the picker's search box.
- [ ] `PUT /api/v1/listings/{listingId}/categories` with `{ "primaryCategoryId": "...", "additionalCategoryIds": ["..."] }`; the seller comes from the security context only; standard envelope; response `{ categories: [{categoryId, categoryPath, isPrimary}], warnings: [] }`. The call is idempotent (full replace).
- [ ] All three endpoints require authentication. No admin taxonomy endpoints (the taxonomy is seeded; admin management is not in any sprint story).

### Mobile (Flutter)
There is no Figma frame for this picker (Open Gaps item 2). If the designer provides one, follow `nova-figma-to-code` (get the design context, check the mapping file for drift, reuse components, record the mapping); otherwise build from `valuex-mobile/docs/Flutter-Design-System.md`.
- [ ] Models under `lib/features/listing/domain/`: `CategoryNode` (id, slug, name, depth, hasChildren), `CategoryPath`, `ListingCategories` (primary plus additional). Do not reuse Home's `ListingCategory`; Home moves to the backend list in US-111.
- [ ] `ListingRepository` methods: `categoryChildren(parentId)`, `searchCategories(query)`, `saveCategories(listingId, primaryId, additionalIds)` with error mapping for the five error codes; Riverpod providers for each, with loading, error and retry states.
- [ ] `CategoryPickerScreen` (full screen from Item Details): a search field at the top; a breadcrumb row for the current level; a list of the level's categories with a chevron for those that have children and a selection control for each; a chip area at the top of the list showing the **primary** chip (separate style, with a clear action) and up to 3 **additional** chips, each removable; the first selection becomes the primary, the next ones additional; tapping a selected category removes it; a counter ("2 of 4 selected"); a **Done** button, disabled until a primary exists.
- [ ] Limits and errors in the UI: trying to select a 5th category shows `ERROR_MAX_CATEGORIES` and changes nothing; selecting an already chosen category is not possible (it unselects), so `ERROR_DUPLICATE_CATEGORY` only appears if the server disagrees; a server rejection leaves the picker open with the message.
- [ ] **Done** calls `saveCategories`. On success with warnings, show a non-blocking banner in the picker with `WARNING_UNRELATED_CATEGORIES` and two actions, "Keep" (return to Item Details) and "Change" (stay); without warnings, return at once.
- [ ] `ItemDetailsScreen` (US-114): replace the single-select category chips with a "Categories" section that shows the primary chip and the additional chips and an **Edit categories** button opening the picker; a required-field error for a missing primary uses `ERROR_PRIMARY_CATEGORY_REQUIRED`. **Choose Listing Plan** is enabled only when a primary category is saved. The details `PATCH` no longer carries a category.
- [ ] Prefill: when AI (US-005) suggests a category slug, the app looks it up in the taxonomy and offers it as the primary in the picker; an unknown slug is ignored.
- [ ] Strings in English and Hindi (Hindi to be reviewed); category names come from the server; tokens only; 48 dp tap targets; every chip, row and selection control has a semantic label and selected state; works at 200% text and with a screen reader; accessibility guideline tests.

### Documentation/Quality
- [ ] OpenAPI examples for the three endpoints; update LLD Part C (slug column, search endpoint, the `categories_unrelated` flag, any-active-category rule); update the US-114 plan note that US-006 replaces the chips; add this story's note to the US-084 plan (reads `categories_unrelated`).
- [ ] After implementation, create `Documents/Manual Testing Guides/US-006-Testing-Guide.md`.

## 5. Test Plan

Target >90% coverage for new code (`CLAUDE.md`).

### Backend Unit Tests
- [ ] `setCategories`: valid primary plus 0 to 3 additional saves and returns paths; primary missing rejected; 4 additional rejected (`ERROR_MAX_CATEGORIES`); a duplicate (including the primary repeated as additional) rejected; unknown or inactive id gives `CATEGORY_NOT_FOUND`; non-owner gets not found; a non-editable status gives `ERROR_LISTING_NOT_EDITABLE`.
- [ ] Replace semantics: a second call replaces the first set; the primary can change; the listing always has exactly one primary.
- [ ] Relatedness checker: parent and child related; siblings under one parent related; cousins more than 2 levels from the common ancestor not related; two top-level categories not related unless on the allow-list; allow-list works in both directions; a tree of 7 levels works.
- [ ] `categories_unrelated` set and cleared correctly across saves; warning present in the response only when set.
- [ ] US-007 integration point: restricted category assigned as an additional tag is detected.
- [ ] `CategoryService.search`: matches, case-insensitive, minimum length, limit of 20, inactive excluded.

### Backend Integration Tests (Testcontainers PostgreSQL)
- [ ] Migration applies on top of the previous versions; seed present; a listing with a known `category_slug` ends with a primary row and no slug column; an unknown slug leaves no category and does not fail the migration.
- [ ] The unique partial index rejects two primaries for one listing.
- [ ] `GET /categories/tree` (top level and a child level, `hasChildren` correct), `GET /categories/search`, `PUT /listings/{id}/categories`; authentication required; IDOR checked.
- [ ] Redis cache: second call served from cache.

### Mobile Tests (Flutter)
- [ ] Picker: first selection is primary, next ones additional, the 5th is refused with the message, tapping a selected category removes it, search results show paths, lazy level loading and breadcrumb, Done disabled without a primary, warning banner with Keep and Change, server error shown, loading and retry states.
- [ ] Item Details: the categories section shows the chips and opens the picker; Choose Listing Plan is blocked without a primary; the details save sends no category.
- [ ] Accessibility guideline tests (tap target, labels, selected state) in English and Hindi, and 200% text.

## 6. Validation Checklist

- [ ] Every listing has at most one primary and at most 3 additional categories, all active taxonomy nodes.
- [ ] The category set is replaced atomically; a failed save leaves the previous set.
- [ ] The relatedness result is only a warning and a flag; it never blocks the seller.
- [ ] Restricted-item checks look at all assigned categories.
- [ ] No category is accepted from free text; only ids from the taxonomy.
- [ ] No other seller's listing can be read or changed.
- [ ] The Home screen is not changed by this story.
- [ ] Brand theme and design system rules followed.
- [ ] Checkstyle, full tests, coverage, SonarQube (backend) and Flutter analyze and tests (mobile) pass before push.

## 7. Open Gaps / Questions

1. **Story points.** The story is estimated at 3 SP, but this plan covers the taxonomy tables, three endpoints, relatedness rules, a hierarchical searchable picker and the migration of US-114's slug. Proposed: 5 SP. Please confirm.
2. **Design.** There is no Figma frame for the category picker. Is there one, or should it be built from the design system alone?
3. **Taxonomy content.** The seed has the 12 top-level categories from Home only, so deeper levels and the cross-sell pairs are not defined. Product needs to supply the full tree (names, levels, which categories relate). Until then every seller picks from the top level, and "6+ levels" is covered by tests only. Is the full taxonomy available?
4. **Hindi category names.** Category names are stored in English only. Hindi names need a `name_hi` column or translation file (Sprint 14 localization, US-044). Accepted for now?
5. **Ancestor and descendant together.** Selecting a category and its own parent is allowed and counts as related. It is redundant for search. Is that acceptable, or should it be refused?
6. **Flag consumption.** `categories_unrelated` is only set here. US-084's plan needs one line to read it as a review signal (added in its plan); with auto-approval and no AI it has no effect until manual review is switched on.
7. **Editing categories after publication** is US-010 (a change of the primary category is a major edit that goes back to review).

---

**Status:** Draft
