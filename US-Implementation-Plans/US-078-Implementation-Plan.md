# US-078: Listing Plan Features and Pricing — Implementation Plan

## 1. Header

| Field | Value |
|---|---|
| Story ID | US-078 |
| Title | Listing Plan Features and Pricing |
| Sprint | Sprint 2 — Seller Listing Creation |
| Story Points | 3 |
| Repos | valuex-backend, valuex-mobile |
| Dependency | US-004 (listings exist). Built before US-008, which selects and pays for a plan from this catalog |

**Scope:** the read-only plan catalog and the pricing comparison. It does not select or pay for a plan (US-008), publish (US-009), upgrade a live listing (US-064), or edit plans (admin console, US-116).

**Plans are dynamic (decided 2026-10-16).** Plans, features and prices are data managed from the admin console (US-116) and change with management decisions. Nothing about a plan is hard-coded in code or in the app. The three plans below are only the starting rows. There is no free plan today; if management sets a price to zero it is free, and the rest of the flow (US-008, US-009) must already handle a zero price. Prices include GST for now, and the GST setting is configurable.

## 2. Story Recap

**As a** seller **I want to** understand differences between listing plans **so that** I can choose the right plan for my item.

**Acceptance Criteria** (`Documents/user-stories.md`):
- At plan selection I see three plans side by side:
  - **Basic** ₹49 (originally ₹99): listed in chronological order, 7 days validity, AI + email support.
  - **Boosted** ₹149 (originally ₹399): listed on top when searched, 7 days validity, AI + email + human chat support.
  - **Priority** ₹249 (originally ₹699): boosted placement, featured on the landing page, "Featured" badge, 1 month validity, AI + email + chat + on-call support.
- When I select a plan I see the payment breakdown before confirming.
- When payment succeeds, the selected plan's features activate (US-008, US-009).

**Validation Rules:** plan validity starts at publication (updated 2026-10-16) · plan features are not transferable · at most 20 featured listings on the landing page (rotation) · support level sets the support response time.

**Error Scenarios:** `ERROR_PAYMENT_REQUIRED` · `PLAN_EXPIRED`.

## 3. Design Reference

- Primary source: [Sprint-2-Seller Listing Creation-LLD.md — Part G](../LLD/Sprint-2-Seller%20Listing%20Creation-LLD.md#part-g---us-078-listing-plan-features-and-pricing) §G.1–G.7, and HLD Part 2 §4.5 (Plan & Entitlement module).
- PRD v1.3 §17 plan table (Basic ₹99 → ₹49, Boosted ₹399 → ₹149, Priority ₹699 → ₹249).
- Figma Make: `ListingPlanScreen.tsx` (the plan cards, "Choose Listing Plan" header) and the plan step in `CreateListingScreen.tsx`, in Make file `tzrpUwfrR0SYeyKkv1p0co`.
- Existing code to reuse: Spring Cache with Redis (`RedisConfig`, `@EnableCaching`), the `ApiResponse` envelope, the listing feature in `valuex-mobile/lib/features/listing`, brand components (`BrandGradientButton`, card tokens).

**Key design decisions:**
- Prices, validity, support level and feature lines live in the database (`plans` table seeded by migration), not in the app, so a price change needs no app release.
- Mobile shows the plan lines as: the catalog features, then the validity, then a support label built from `support_level` (localized). The marketing claims in Make that are not in the story (for example "3× more visibility") are not shown unless product adds them to the catalog.
- The page is the same one US-008 uses to select a plan: this story builds the display and the price breakdown; US-008 adds the action behind the button.

## 4. Implementation Steps

### Database Migration — `valuex-backend`
- [x] `V15__seller_plans.sql` (built as `V15` on top of US-114's `V14`, ahead of US-005 and US-007, which take the next free versions): `plans` table and the starting seller plan rows from LLD §G.3 with Basic changed to the decided value (`BASIC` ₹49, original ₹99, 7 days; `BOOSTED` ₹149, original ₹399, 7 days; `PRIORITY` ₹249, original ₹699, 30 days), with `audience`, `support_level`, `features` (JSONB), `display_order`, `badge`, `is_recommended` (the plan the page selects first), `is_active` and a `version` column for concurrent edit checks (US-116). Price columns allow zero (a zero price means free); no code treats a plan code as special. Buyer plans (US-079) are not seeded here.
- [ ] Same migration: a small `platform_settings` table (key, value, updated_at, updated_by) seeded with `GST_MODE = INCLUSIVE` and `GST_RATE_PERCENT = 18` (rate to be confirmed). Admin edits come with US-116; until then the values change by a database change.

### Backend — Catalog API
- [ ] `Plan` entity and `PlanRepository` (`findByCodeAndAudience`, `findByAudienceAndActiveTrueOrderByDiscountedPrice`).
- [ ] `PlanCatalogService.sellerPlans()` returning the active seller plans, ordered by `display_order`, with computed `discountAmount` and `discountPercent` (zero when there is no original price) and the tax information (`priceIncludesGst`, `gstRatePercent`, and the GST part of the price when the price includes GST); cached with `@Cacheable` (Redis, 1 hour) and evicted when a plan or the tax setting changes (US-116 calls the eviction).
- [ ] A `TaxSettings` reader over `platform_settings`, used here for display and by US-008 for the amount to charge; the price is the amount charged when the mode is `INCLUSIVE`.
- [ ] `GET /api/v1/plans/seller` (authenticated seller) returning the LLD §G.4 shape plus the computed discount values and the tax information; standard `ApiResponse` envelope. A plan with a zero price is returned like any other, with `price` 0.
- [ ] Prices are returned in rupees with 2 decimals; the gateway amount in paise is computed by US-008, not here.
- [ ] Not built in this story: `FeaturedListingRotationService` (LLD §G.5) and the `PLAN_EXPIRED` read-path check. Both need `listings.published_at` (added by US-009) and the landing-page and listing read endpoints of Sprint 3; they move there (see Open Gaps).

### Mobile (Flutter)
Follow `nova-figma-to-code`: call the Figma MCP `get_design_context` for the Make file, check the mapping file for drift, reuse existing components, record the mapping entry.
- [ ] `ListingPlanScreen` under `lib/features/listing/presentation/` (route in the Sell flow after Item Details): header "Choose Listing Plan" and subtitle, three plan cards (name, price, original price struck through, validity, feature lines, badge for Boosted and Priority, selected state), default selection Boosted as in Make.
- [ ] Plans from a repository method for `GET /plans/seller`; loading, error with Retry, and empty states; no prices or features hard-coded in the app.
- [ ] Price breakdown for the selected plan shown before confirming: original price, discount, total to pay, with the label "Inclusive of GST" (and the GST amount when the rate is set). A zero price shows "Free" and no payment wording. The number of plans, their names, order and features all come from the server, so one plan, two or five must render correctly.
- [ ] The bottom button label shows the amount ("Review Listing" in the 4-step flow; the action itself is added by US-008).
- [ ] Support level label and the badge texts localized (English and Hindi); validity shown as "7 days" and "1 month".
- [ ] Use design-system tokens only; 48 dp tap targets; every card has a label and a selected state announced to screen readers; works at 200% text.
- [ ] Update `valuex-mobile/docs/Flutter-Design-System.md` with the new card pattern if it is new.

### Documentation/Quality
- [ ] OpenAPI example for `GET /api/v1/plans/seller`.
- [ ] Update LLD Part G where the implementation differs (validity from publication, featured rotation moved to Sprint 3).
- [ ] After implementation, create `Documents/Manual Testing Guides/US-078-Testing-Guide.md`.

## 5. Test Plan

Target >90% coverage for new code (`CLAUDE.md`).

### Backend
- [ ] Catalog returns the active seller plans in display order, with the seeded prices, validity and features; inactive plans are not returned; buyer plans are not returned; changing the seeded data changes the result with no code change (for example a plan with price 0, a fourth plan, only one plan).
- [ ] Discount amount and percent are computed correctly (49 of 99, 149 of 399, 249 of 699) and are zero when there is no original price.
- [ ] GST: inclusive mode returns the GST part of the price (for example 49 at 18 percent); exclusive mode returns the added GST; a zero price has no GST.
- [ ] Caching: a second call hits the cache; changing a plan or the tax setting evicts it.
- [ ] Endpoint requires authentication; envelope matches the contract.
- [ ] Migration applies on top of the previous versions and the seed rows are correct.

### Mobile
- [ ] Widget tests: cards from a fake repository (three, one and a zero-price plan), default selection is the plan the server marks as recommended or otherwise the first, selection change updates the breakdown, badge shown only when the server sends one, loading/error/empty states, "Inclusive of GST" label.
- [ ] Prices use the Indian rupee format; Hindi strings render; text at 200% does not clip.
- [ ] Accessibility guideline tests (tap target, label, contrast).

## 6. Validation Checklist

- [ ] Prices and features come from the server; the app has no copies; no code branch depends on a plan code or on a plan being free or paid.
- [ ] The starting plans match the PRD and the story (Basic ₹49).
- [ ] The breakdown is shown before the seller confirms.
- [ ] Brand theme and design system rules followed; Figma-to-code mapping recorded.
- [ ] Checkstyle, full tests, coverage, SonarQube (backend) and Flutter analyze and tests (mobile) pass before push.

## 7. Open Gaps / Questions

1. **Basic price (decided 2026-10-16).** Basic is ₹49 and there is no free plan. If management makes a plan free, they set its price to zero in the admin console; the user story text of US-008 is updated accordingly.
2. **Taxes (decided 2026-10-16).** Prices are GST inclusive for now, and the GST mode and rate are configurable from the admin console (US-116). The GST rate (18 percent assumed) and the invoice requirements are to be confirmed by finance.
3. **Feature lines.** Make's lines differ from the story (for example "Standard search ranking", "3× more visibility", "Top search placement + homepage"). The catalog follows the story and the PRD; product to confirm the final wording.
4. **Featured rotation and expiry check (moved).** `FeaturedListingRotationService` and the `PLAN_EXPIRED` check move to Sprint 3 with the landing page and listing reads, because they need `published_at` from US-009.
5. **Admin management of plans** is US-116 (Sprint 10, needs the admin console and roles). Until then the catalog and the tax setting change by a database change. A price snapshot is taken when the seller selects a plan (US-008), so later price changes never alter existing listings or open payments.

---

**Status:** Implemented on `feature/US-078-listing-plan-pricing` (backend and mobile), awaiting review (2026-10-17). Approved 2026-10-17. Not done here, by design: the Figma-to-code mapping file entry, and the plan name and feature lines are English only because they come from the server (Hindi covers the labels, validity, support and badges).
