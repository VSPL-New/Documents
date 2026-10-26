# US-006: Category Taxonomy and Category-driven Item Details — Implementation Plan

> Rewritten 2026-10-25. The earlier "Multi-Category Tagging" plan is superseded (multi-category was dropped). All decisions referenced as D1 to D29 are in [Category_Taxonomy_Review_Drafts.md](../Category_Taxonomy_Review_Drafts.md), which also holds the required-fields table, option lists, type corrections, validation ranges and the Conditional mapping used here.

## 1. Header

| Field | Value |
|---|---|
| Story ID | US-006 (rewritten; was "Multi-Category Tagging") |
| Title | Category Taxonomy and Category-driven Item Details |
| Sprint | Sprint 2 — Seller Listing Creation |
| Story Points | 13 (approved 2026-10-25; the old 3 SP no longer fits. Breakdown: taxonomy tables and importer 5, schema API and listing integration 3, mobile picker and dynamic form 5) |
| Repos | valuex-backend, valuex-mobile |
| Dependency | US-004, US-114, US-089 (all merged to `main`). Built before US-005 and US-007 (D1) |
| Related, not in this story | US-007 (compliance popup), US-118 (Real Estate specifics), US-119 (plans by L1), US-120 (OpenSearch), US-121 (Admin categories and AI settings), US-122 (delivery and Shiprocket), US-108 update (location) |

**Scope (agreed, Q27):** taxonomy and metadata tables, the importer, category and listing-schema APIs, a 3-level category picker, the dynamic Item Details form, and replacing `category_slug`.

**Not in this story:** photo search; delivery policy, `delivery_modes`, packed weight and size (US-122); the Conditional-category popup (US-007); buyer-side Real Estate intent prompt, intent filter and the negotiation-only flow (US-118); Admin screens (US-121); OpenSearch (US-120); AI prefill itself (US-005); item location and its public precision (US-108 update).

## 2. Story Recap

**As a** seller **I want to** choose my item's category from the marketplace taxonomy and fill in the details that category needs **so that** buyers can find my item and see accurate information.

**Acceptance Criteria (proposed; to be written into `user-stories.md` after approval):**
- Given I am on Item Details for a draft listing
- When I open the category picker
- Then I see up to 15 popular L1 categories followed by an "Others" control for the remaining enabled ones; inside an L1, up to 10 popular L2 categories followed by "Others"; then all enabled L3 categories; and I can search by name
- And only enabled categories are shown (a disabled parent hides its whole branch)
- When I choose an L3 category
- Then the page shows the common fields and that category's required fields, with its optional fields under "More details", labelled with the dictionary display names
- When I change the category after entering details
- Then I am warned and the details that do not apply are cleared
- When nothing fits, or AI cannot categorize the item, or the category is missing or disabled
- Then I pick the matching "Other ..." category and all non-common details are stored as special attributes
- When I choose a Real Estate category
- Then I choose a transaction intent allowed for that property family and enter the price for that intent, and the listing price is derived from it
- And Choose Listing Plan is enabled only when every required field is valid

**Edge Cases:** category disabled while the seller is on the page; category changed after details were entered; very long option lists; search with no results; unit-based numbers; out-of-range values; an option removed after being chosen; duplicate display names inside one profile.

**Validation Rules:** the listing's category must be an enabled L3; attributes must belong to the category's schema; required fields present; types, ranges, options and cross-field rules from the drafts file; price above 0 and at most ₹10,00,00,000; title at most 100 and description at most 2000 characters (existing).

**Error Scenarios:** `ERROR_CATEGORY_REQUIRED` (existing) · `CATEGORY_NOT_FOUND` (404) · `ERROR_CATEGORY_DISABLED` · `ERROR_CATEGORY_NOT_LEAF` · `ERROR_ATTRIBUTE_NOT_ALLOWED` · `ERROR_ATTRIBUTE_REQUIRED` · `ERROR_ATTRIBUTE_INVALID`.

## 3. Design Reference

- Sources: the Category_Taxonomy_CSVs (Taxonomy, Common Metadata, Metadata Profiles, Metadata Dictionary, Restrictions), [Category_Taxonomy_Review_Drafts.md](../Category_Taxonomy_Review_Drafts.md), and `ValueX_Category_Taxonomy_MVP_Design.md` (ideas for tables and endpoints only; our existing design wins). LLD Part C is rewritten after approval.
- **No Figma frame for the picker or the dynamic form: build from the brand design system** (`valuex-mobile/docs/Flutter-Design-System.md`).
- Existing code to evolve: `ListingController`, `ListingDetailsService`, `UpdateListingDetailsRequest`, `ListingDraftResponse`, `Listing`, `ListingDraftService`, the editable-state check (`DRAFT` or `REVISION_REQUIRED`, `ERROR_LISTING_NOT_EDITABLE`), Redis cache, the `ApiResponse` envelope; mobile `ItemDetailsScreen`, `item_details_controller.dart`, `listing_details.dart`, `listing_repository.dart`, `listing_error_messages.dart`.

**Key design decisions:**
- **Evolve in place (D2).** Migration `V16` adds the taxonomy and attribute tables and changes `listings`; `category_slug` is replaced by `category_id` (L3). Dev data is discarded (D21). The existing `price` column (NUMERIC(12,2), already large enough for ₹10 crore) keeps its name and holds the normalized listing price; this story derives it for property (Sale gives `sale_price`, or `price_min` for New Developments; Rent and Lease give `monthly_rent`).
- **Tables (plural names, as elsewhere):** `categories`, `attribute_definitions`, `attribute_options`, `metadata_profiles`, `metadata_profile_attributes`, `category_metadata_profiles`, `category_attribute_overrides`, `listing_attribute_values`, `listing_attribute_option_values`, `taxonomy_import_log`.
- **Common fields** stay as `listings` columns (`title`, `description`, `condition`, `price`) plus new `condition_notes`, `negotiable`, `quantity`. Everything else is a typed attribute value. Condition keeps NEW, LIKE_NEW, GOOD, FAIR, POOR (D7).
- **Schema-driven form.** `GET /categories/{code}/listing-schema` returns the fields for the category (key, display name, type, unit, UI control, required, options, validation, AI-prefill flag, order). Common-field applicability follows the drafts file (section 2). The server validates saves against the same schema.
- **Importer (D21).** CSVs and an overrides file are committed under `valuex-backend/src/main/resources/taxonomy/`. An idempotent, all-or-nothing importer upserts by category code and fails on: duplicate L3 code with a different path, L3 without a profile, profile key missing from the dictionary, more than 15 popular L1 or 10 popular L2 per L1, duplicate popular ranks among siblings, an enabled Prohibited category, inconsistent levels, or duplicate display names inside one profile. It records a version and checksum in `taxonomy_import_log` and runs on deploy (admin trigger comes with US-121).
- **Effective enabled.** An L3 is selectable when its L1, L2 and L3 are all `admin_enabled` and its status is not Prohibited. Real Estate and Conditional categories are enabled from day one (D30).
- **"Others" (D15).** The OTHER profile has only common fields plus `item_type_free_text`; its non-common entries are stored in one JSON attribute (`special_attributes_json`).
- **Out of reach on purpose:** AI prefill (the schema carries `aiPrefillEnabled`; US-005 fills values; until then, and whenever AI is off, the seller types everything, D4), delivery fields (US-122), buyer-side property flow (US-118).

## 4. Implementation Steps

### Database Migration — `valuex-backend`
- [ ] `V16__taxonomy_and_listing_attributes.sql` (the highest migration on `main` is `V15__seller_plans.sql`; recheck `db/migration` at implementation time. Other plans' numbers shift up by one when they are built). Use `uuid_generate_v4()` like the existing migrations.
  - `categories` (`id`, `parent_id`, `code` unique, `name`, `slug`, `level` 1 to 3 with a check against the parent, `marketplace_status` ALLOWED or CONDITIONAL, `admin_enabled`, `ui_popular`, `ui_rank`, `display_order`, `policy_notes`, timestamps); unique `(parent_id, slug)`; indexes on `parent_id`, `(level, admin_enabled)` and `(level, ui_popular, ui_rank)`.
  - `attribute_definitions` (`attribute_key` unique, `display_name`, `data_type`, `unit`, `ui_control`, `searchable`, `filterable`, `ai_extractable` YES, LIMITED or NO, `validation_json`, `help_text`, `admin_enabled`).
  - `attribute_options` (`attribute_id`, `code`, `display_value`, `display_order`, `admin_enabled`), unique `(attribute_id, code)`.
  - `metadata_profiles` (`code` unique, `name`, `version`, `admin_enabled`); `metadata_profile_attributes` (`required`, `display_order`, `ai_prefill_enabled`, `seller_editable`, `searchable`, `filterable`, primary key `(profile_id, attribute_id)`); `profile_attribute_options` (restricts a profile to a subset of an attribute's options, for example `transaction_intent`); `category_metadata_profiles` (`category_id` primary key); `category_attribute_overrides` (per-L3 differences).
  - `listing_attribute_values` (`listing_id`, `attribute_id`, typed columns `value_text`, `value_integer`, `value_decimal`, `value_boolean`, `value_date`, `value_option_id`, `value_json`, `value_source` SELLER, AI, ADMIN or IMPORT, `ai_confidence`, `seller_confirmed`, timestamps, primary key `(listing_id, attribute_id)`) and `listing_attribute_option_values` for multi-select (one row per option; never comma-separated text).
  - `taxonomy_import_log` (version, checksum, counts, status, run time).
  - `listings`: add `category_id` (FK to an L3), `condition_notes` TEXT, `negotiable` BOOLEAN, `quantity` INTEGER; drop `category_slug` (dev data is discarded, D21). `price` is unchanged (it already holds up to ₹10,00,00,000).

### Backend — Taxonomy and Importer (new module `com.valuex.taxonomy`, same layering as `plans`)
- [ ] Copy the sheets from `Documents/Category_Taxonomy_CSVs` (Taxonomy, Common Metadata, Metadata Profiles, Metadata Dictionary) into `src/main/resources/taxonomy/` with the v1.0 names. Add an overrides file carrying the decisions from the drafts file: required-field matrix per profile, per-profile option subsets, starter option lists, data-type corrections, validation ranges, and the two profile changes (`lease_amount` on `PROP_COMMERCIAL`, `monthly_rent` on `PROP_LAND`).
- [ ] `TaxonomyCsvReader`, `TaxonomyImportService` (dry run and apply, one transaction, upsert by code, immutable codes, deterministic generated codes for L1 and L2 such as `L1-MOBILES_TABLETS`), and the validations listed in section 3. Log every run in `taxonomy_import_log`.
- [ ] Trigger: an `ApplicationRunner` guarded by `valuex.taxonomy.import-on-startup` (and `valuex.taxonomy.import-dry-run`). An admin-triggered import comes with US-121.
- [ ] `CategoryService`: `children(parentCode, scope)` with scope POPULAR, OTHERS or ALL, `search(query)` over L3 names with the full path, `pathFor(code)`, and the effective-enabled rule (L1, L2 and L3 enabled; not Prohibited; plus the two feature flags). Cache the results in Redis and evict on import.

### Backend — Listing Schema, Validation and Listing Integration
- [ ] `ListingSchemaService`: builds the field list for an L3 from its profile, overrides and the Common-field applicability rules (Real Estate: no condition, quantity or delivery fields; whole vehicles (Cars, Motorcycles and Scooters, Commercial and Agricultural Vehicles): no quantity; delivery fields are left out until US-122). Uses the dictionary `Display Name` for labels. Cache by `(categoryCode, profileVersion)`.
- [ ] `AttributeValidator`: type, unit, range, option membership, required, and cross-field rules (`price_min` at most `price_max`, `floor_number` at most `total_floors`, `pieces_missing` at most `pieces_total`, and so on) from the drafts file. Rejects keys outside the schema (`ERROR_ATTRIBUTE_NOT_ALLOWED`).
- [ ] `ListingCategoryService.setCategory(listingId, sellerId, categoryCode)`: lock the listing for the owner (same call as the draft code), require an editable status, require an enabled L3 (`CATEGORY_NOT_FOUND`, `ERROR_CATEGORY_DISABLED`, `ERROR_CATEGORY_NOT_LEAF`), set `category_id`, and delete stored attribute values that are not in the new schema, in one transaction.
- [ ] `ListingDetailsService` / `UpdateListingDetailsRequest`: remove `categorySlug`; add `conditionNotes`, `negotiable`, `quantity` and `attributes` (key and value pairs). Replace the "complete details" check with the schema check (`ERROR_CATEGORY_REQUIRED` when there is no L3; `ERROR_ATTRIBUTE_REQUIRED` and `ERROR_ATTRIBUTE_INVALID` otherwise). Raise `valuex.listing.max-price` to 10,00,00,000. For "Others" listings, store the non-common entries in the single `special_attributes_json` attribute.
- [ ] `ListingDraftResponse`: replace `categorySlug` with `category` (code, name, path), and add the stored `attributes` and the new common fields.
- [ ] US-008's "complete details" rule uses the same schema check (note added to its plan).
- [ ] `ListingPriceResolver` (D11): `price` comes from `asking_price_inr` for goods and vehicles. For Real Estate it is derived from the intent: Sale gives `sale_price` (`price_min` for PROP_NEW_DEV), Rent and Lease give `monthly_rent`. The schema offers only the intents allowed for the profile (`profile_attribute_options` on `transaction_intent`) and requires the matching price field. The overrides file adds optional `lease_amount` to PROP_COMMERCIAL and `monthly_rent` to PROP_LAND.

### Backend — API
- [ ] `GET /api/v1/categories/children?parentCode=&scope=POPULAR|OTHERS|ALL` returns enabled children (top level without `parentCode`); each item has `code`, `name`, `level`, `hasChildren`.
- [ ] `GET /api/v1/categories/search?q=` returns up to 20 enabled L3 categories whose name matches (case-insensitive, at least 2 characters), each with its path.
- [ ] `GET /api/v1/categories/{code}/listing-schema` returns the form definition (key, label, type, unit, UI control, required, options, validation, `aiPrefillEnabled`, order, group).
- [ ] `PUT /api/v1/listings/{listingId}/category` with `{ "categoryCode": "CAT-0001" }`; the seller comes from the security context only.
- [ ] `PATCH /api/v1/listings/{listingId}` extended as above. All endpoints need authentication and use the standard envelope.
- [ ] Config: `valuex.taxonomy.import-on-startup`, `valuex.listing.max-price`.

### Mobile (Flutter)
- [ ] Models under `lib/features/listing/domain/`: `CategoryNode`, `CategoryPath`, `ListingSchema`, `SchemaField` (type, unit, UI control, required, options, validation), `AttributeValue`. Do not reuse Home's `ListingCategory`.
- [ ] Rework `listing_details.dart`: `ListingDetailsDraft.categorySlug` becomes the L3 category code, add `conditionNotes`, `negotiable`, `quantity` and an attribute map; required fields come from the schema; `DetailsField.category` is valid only with an L3; the `CATEGORY` entry of `suggestionFeedback` compares AI codes. Raise `maxPriceRupees` to 100000000. Update `item_details_controller.dart` and `listing_repository.dart` (the details save sends the new fields and no slug).
- [ ] `CategoryPickerScreen`: L1 grid with up to 15 popular tiles and an Others tile; an L2 list with up to 10 popular rows and Others; an L3 list; a search field with results showing the path; a breadcrumb; selecting an L3 calls `PUT .../category`; "Other ..." nodes are offered when nothing fits. Loading, error and retry states.
- [ ] Dynamic form widget built from the design system, one widget per UI control (text, long text, number with unit suffix, yes/no toggle, dropdown or searchable select, multi-select, date picker, autocomplete for option-or-text, composite dimensions). Required fields first; optional fields under a collapsed "More details"; labels from the dictionary display names; inline errors from the schema and server.
- [ ] `ItemDetailsScreen`: a Category row (path and a Change action) in place of the old chips; common fields (title, condition, condition notes, description, price, negotiable, quantity where applicable); the category fields; all optional Common fields (`age_months`, `purchase_year`, `original_price_inr`, `invoice_available`, `warranty_status`, `warranty_end_date`, `repair_history`, `ownership_count`, `serial_number_present`, `authenticity_proof`) under "More details" for goods and vehicles; `video_available` stays hidden until video upload exists; for Real Estate, the intent selector and the price field for that intent replace condition, quantity and the asking price; the existing negotiation note and location field are kept. Changing the category shows a warning and clears fields that no longer apply. **Choose Listing Plan** is enabled only when all required fields are valid. Remove `category_chips.dart` and `_CategoryChips`.
- [ ] Dev-only banner "Plan is under revision until US-119" on the Choose Listing Plan page, shown when `ENV=dev` (D14).
- [ ] Strings in English and Hindi for UI text (Hindi to be reviewed); category and attribute names come from the server in English (D23); tokens only; 48 dp tap targets; semantic labels and selected states; works at 200% text and with a screen reader.

### Documentation/Quality
- [x] Documents updated on 2026-10-25: LLD Part C rewritten; `user-stories.md` (US-006 rewritten, US-118 to US-122 added, update notes on affected stories); Sprint-plan; PRD; HLD parts 1 to 7; Sprint 1 and Sprint 6 LLD change logs; update notes on the US-005, US-007, US-008, US-010, US-084 and US-114 plans.
- [ ] OpenAPI examples for the new endpoints.
- [ ] After implementation, create `Documents/Manual Testing Guides/US-006-Testing-Guide.md`.

## 5. Test Plan

Target >90% coverage for new code (`CLAUDE.md`).

### Backend Unit Tests
- [ ] Importer validations, one test each: duplicate L3 code with a different path; L3 without a profile; profile key missing from the dictionary; more than 15 popular L1; more than 10 popular L2 under one L1; duplicate popular rank among siblings; an enabled Prohibited category; inconsistent level; duplicate display name inside one profile; a failed file applies nothing; a second run changes nothing (idempotent); codes of existing categories are never changed.
- [ ] Effective-enabled rule: disabled L1 or L2 hides the branch without rewriting child flags; re-enabling restores it; Prohibited excluded; the Real Estate and Conditional feature flags.
- [ ] `ListingSchemaService`: required and optional split for each profile family (phone, car, apparel, OTHER); Common-field applicability (Real Estate, whole vehicles, goods); delivery fields absent; per-profile option subsets; display names used as labels.
- [ ] `AttributeValidator`: each data type; unit and range rules; option membership; required; cross-field rules; a key outside the schema is rejected; multi-select stored as rows.
- [ ] `setCategory`: valid L3 saves; L1 or L2 rejected (`ERROR_CATEGORY_NOT_LEAF`); unknown code `CATEGORY_NOT_FOUND`; disabled branch `ERROR_CATEGORY_DISABLED`; non-owner gets not found; non-editable status `ERROR_LISTING_NOT_EDITABLE`; a category change deletes attributes outside the new schema and keeps the shared ones.
- [ ] Details save: price above 0 and at most ₹10,00,00,000 (exactly the maximum accepted, one paisa above rejected); title and description limits; "Others" listings store non-common entries in `special_attributes_json`.
- [ ] `ListingPriceResolver`: goods use `asking_price_inr`; Real Estate Sale gives `sale_price`, New Developments give `price_min`, Rent and Lease give `monthly_rent`; an intent not allowed for the profile is rejected; the matching price field is required.
- [ ] `CategoryService`: POPULAR and OTHERS scopes together equal ALL; search is case-insensitive, needs 2 characters, is limited to 20 and excludes disabled branches.

### Backend Integration Tests (Testcontainers PostgreSQL)
- [ ] `V16` applies on top of the previous versions; `listings.category_slug` is gone; the importer loads the real CSVs: 39 L1, 157 L2, 907 L3, 492 attribute keys, the popular limits hold, and a second run is a no-op.
- [ ] `GET /categories/children`, `GET /categories/search`, `GET /categories/{code}/listing-schema`, `PUT /listings/{id}/category`, extended `PATCH`: authentication required; IDOR checked; error codes and envelopes.
- [ ] Redis cache: second call served from cache; cache evicted after an import.

### Mobile Tests (Flutter)
- [ ] Picker: popular L1 then Others, popular L2 then Others, L3 list, search with paths, breadcrumb, "Other ..." fallback, loading, error and retry, disabled category removed after a refresh.
- [ ] Dynamic form: one test per UI control; required fields first and optional ones under "More details"; unit suffix; inline schema errors and server errors; dictionary labels used.
- [ ] Item Details: changing the category warns and clears fields that no longer apply; Choose Listing Plan blocked until all required fields are valid; price at the new maximum accepted; dev-only banner shown only when `ENV=dev`.
- [ ] Accessibility guideline tests (tap target, labels, selected state) in English and Hindi, and 200% text.

## 6. Validation Checklist

- [ ] Every listing points to an enabled L3 category; L1 and L2 are derived.
- [ ] Only attributes in the category's schema are stored; required fields are enforced on the server as well as in the app.
- [ ] Multi-select values are stored as rows, never as comma-separated text.
- [ ] Importer is idempotent, all-or-nothing, and never changes an existing category code.
- [ ] A disabled parent hides its whole branch and keeps child flags.
- [ ] Real Estate listings have an allowed intent and a derived price; Conditional categories are listable (their popup arrives with US-007).
- [ ] No delivery, weight, size or location changes sneak in (US-122 and the US-108 update).
- [ ] Condition values and photo limits are unchanged (D7); price maximum is ₹10,00,00,000.
- [ ] No other seller's listing can be read or changed.
- [ ] Brand theme and design system rules followed.
- [ ] Checkstyle, full tests, coverage, SonarQube (backend) and Flutter analyze and tests (mobile) pass before push.

## 7. Open Gaps / Questions (for your approval)

1. ~~**Story points.**~~ **Decided:** 13 SP.
2. ~~**Hidden categories.**~~ **Decided:** Real Estate and Conditional categories are enabled from day one (project in development). Seller-side intent and price derivation therefore move into this story.
3. ~~**Option lists batch 2.**~~ **Decided (2026-10-25):** reviewed and approved; see section 8 of [Category_Taxonomy_Review_Drafts.md](../Category_Taxonomy_Review_Drafts.md). An attribute without options shows as a text field until Admin loads them.
4. ~~**Optional Common fields in "More details".**~~ **Decided (2026-10-25):** `purchase_year`, `original_price_inr`, `invoice_available`, `warranty_status`, `warranty_end_date` and `repair_history` for goods. Left out: `age_months` (derived), `ownership_count`, `serial_number_present`, `video_available` and `authenticity_proof` (profile-level). Required fields are my selection from each profile plus the applicable Common Required fields; optional fields are the rest of the profile plus those optional Common fields; system fields are hidden.
5. ~~**Price column.**~~ **Decided:** the existing `price` column and API field keep their names and hold the normalized listing price.
6. **Admin switch and AI:** AI stays controlled by the existing `valuex.ai.enabled` setting until US-121 adds the Admin switch; this story only carries `aiPrefillEnabled` in the schema.
7. **Category change after publication** belongs to US-010 (an L3 change is a major edit).
8. **Dev banner:** shown on the Choose Listing Plan page only when `ENV=dev`; it is removed when US-119 ships.
9. ~~**`video_available`.**~~ **Decided:** hidden until the listing flow supports video upload.

---

## 8. Implementation notes (deviations from the plan, recorded 2026-10-26)

- **No `category_attribute_overrides` table.** Nothing used it. The differences it was meant to hold (required fields, type corrections, option lists, profile additions) are in the importer's override files under `taxonomy/overrides/` and are applied to the profile when it is loaded. The LLD and HLD table lists were updated.
- **No schema cache.** The listing schema is built on each request from indexed tables; the Redis cache with eviction on import is deferred until it is needed.
- **"More details" fields follow D31**, not item 4 of section 7 (written before D31): all optional Common fields for goods and whole vehicles (`age_months`, `purchase_year`, `original_price_inr`, `invoice_available`, `warranty_status`, `warranty_end_date`, `repair_history`, `ownership_count`, `serial_number_present`, `authenticity_proof`). `video_available` stays hidden. `ownership_count` is not offered for whole vehicles because their profiles already have `owner_count`. Fields already in the profile (for example `warranty_status`) appear once, in the profile.
- **Hidden from the form:** latitude and longitude (no way to capture them yet), and the other system or common-column keys listed in `AttributeRules.EXCLUDED_KEYS`.
- **Attribute payload** is an object by key (`{ "brand": "Apple" }`), not a list of key/value pairs; field-level errors carry `error.details.field` (a small extension of `BusinessException` and the exception handler).
- **Condition notes** are required wherever condition is shown (new error `ERROR_CONDITION_NOTES_REQUIRED`); new errors `ERROR_NEGOTIABLE_REQUIRED` and `ERROR_QUANTITY_INVALID`.
- **Option codes** are the upper-case display value with `+` written as `PLUS` (so `HDR10` and `HDR10+` differ). The importer skips an import when the files' checksum equals the last successful one, and `valuex.taxonomy.import-dry-run` runs the whole import and rolls it back.
- **`PlainText`** moved from the listing module to `com.valuex.common.util` because the taxonomy validator also uses it.
- **Mobile:** the category picker is a full-screen route opened with the navigator (not a new go_router route) and returns the chosen leaf code; "More details" is a small collapsible section (an expansion tile did not work inside the card background); Continue stays off while a category's form is loading; the old chip widget and its tests were removed.
- **Checks run:** backend `mvn verify` (817 tests, checkstyle clean, coverage checks met, new-code coverage 92.7%), SonarQube (no open issue left in files changed by this story; the quality gate still reports 5 pre-existing test-code smells in `OtpVerifierTest` and `TaxSettingsTest` and 1 in `JwtTokenProvider`, files this story does not touch), `flutter analyze` clean, all 115 listing tests pass. 18 accessibility and contrast tests on unrelated screens (sign-in, sign-up, Aadhaar, OTP, terms, splash, profile, account security) fail in the full mobile run; see the final report.

---

**Status:** Approved (2026-10-25; the user reviewed the option-list batch 2 and approved this plan). Implemented 2026-10-26; see section 8.
