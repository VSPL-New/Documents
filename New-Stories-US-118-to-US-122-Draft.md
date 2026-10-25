# New User Stories US-118 to US-122 (Draft for review)

**Status:** Added to `user-stories.md` and `Sprint-plan.md` on 2026-10-25 (this draft is kept for reference). Sprint placement and story points are proposals: US-118 and US-120 in Sprint 3, US-122 in Sprint 6, US-119 and US-121 in Sprint 10.

| ID | Title | Repos | SP (proposal) | Depends on |
|---|---|---|---|---|
| US-118 | Real Estate Listing Specifics | backend, mobile | 5 | US-006 |
| US-119 | Category-wise Listing Plans | backend, mobile, web | 5 | US-078, US-116 |
| US-120 | OpenSearch Setup and Listing Indexing | backend, infra | 8 | US-006, US-089 (before US-011) |
| US-121 | Admin: Categories, Attributes, Options and AI Settings | backend, web | 8 | US-006, US-053 |
| US-122 | Shiprocket Delivery Integration | backend, mobile | 13 | US-006, US-021, US-023 |

---

### US-118: Real Estate Listing Specifics
> **Scope note (2026-10-25):** the seller-side transaction intent and the `listing_price_inr` derivation are built in US-006 (Real Estate is enabled from day one). This story covers the buyer side (intent prompt and mandatory intent filter, "Starting from" display), the negotiation-only flow, and marking a property Sold or Rented. The first acceptance criteria below describe behaviour that US-006 delivers.

**As a** seller **I want** to list a property for sale, rent or lease **so that** interested buyers can find it and negotiate a price with me

**Acceptance Criteria:**
- Given I choose a Real Estate category on Item Details
- Then I am asked for the transaction intent (Sale, Rent or Lease), limited to the intents the property family supports (Homes: Sale, Rent; New Developments: Sale; Land: Sale, Lease; Commercial: Sale, Rent, Lease; Shared and Managed Living: Rent)
- And the property's own city, locality and pincode are asked (not my seller location)
- And the price fields shown depend on the intent, and one normalized `listing_price_inr` is derived: Sale uses `sale_price` (`price_min` for New Developments, shown as "Starting from"), Rent and Lease use `monthly_rent`
- And `asking_price_inr`, condition, quantity and delivery options are not shown
- When a buyer searches Real Estate
- Then results are always within one transaction intent, and price range and sorting apply only after an intent is chosen
- When a buyer opens a property
- Then they can chat, call or video call me and negotiate the price, and there is no cart, escrow, payment or delivery
- When I agree a deal
- Then I mark the property Sold or Rented

**Edge Cases:** intent not supported by the family; changing intent after entering prices; New Development with `price_min` above `price_max`; commercial Lease without `lease_amount` (optional); buyer searches with no intent chosen.

**Validation Rules:** intent is required and must be allowed for the profile; the price for the intent is required and above 0; `listing_price_inr` is system-derived and not editable; the intent filter is mandatory in every Real Estate search; the Real Estate compliance popup (US-007) is accepted before posting.

**Error Scenarios:** `ERROR_INTENT_NOT_SUPPORTED`, `ERROR_PRICE_REQUIRED_FOR_INTENT`, `ERROR_INVALID_PRICE_RANGE`.

**Decided:** a Real Estate search without an intent prompts the buyer to choose Buy, Rent or Lease; the maximum price is ₹10,00,00,000; the compliance popup applies to all Real Estate L3 categories.

---

### US-119: Category-wise Listing Plans
**As a** platform owner **I want** listing plans and prices to vary by L1 category **so that** property and goods can be priced and featured differently

**Acceptance Criteria:**
- Given an Admin defines plans for an L1 category (US-116 screens extended)
- When a seller reaches plan selection (US-008) for a listing in that L1
- Then they see that L1's plans, features, price and tax
- Until this story is built, all categories use the current plans and a banner "Plan is under revision until US-119" shows in Dev builds only

**Edge Cases:** an L1 with no plan configured; a plan retired while a seller is on the page; a listing whose L1 changes after a plan was chosen (a category change re-runs plan selection per US-010).

**Validation Rules:** every enabled L1 has at least one active plan; GST rules follow US-078 and US-116.

**Error Scenarios:** `ERROR_NO_PLAN_FOR_CATEGORY`.

---

### US-120: OpenSearch Setup and Listing Indexing
**As a** platform **I want** a managed listing search index **so that** buyers get fast keyword, filter and facet search

**Acceptance Criteria:**
- Given a listing reaches `PUBLISHED`
- Then it is indexed (via an outbox with retries) and removed when it leaves `PUBLISHED`
- And the index document carries category (L1, L2, L3 codes and names), `listing_price_inr`, transaction intent, condition, location (city, pincode level only; no street address), plan type, seller rating, recency and typed attributes
- And ranking follows the HLD (exact match, category relevance, seller rating, plan boost, recency) with distance when a location is chosen
- And a disabled category (or any disabled parent) is excluded from results
- And OpenSearch downtime never blocks listing publication

**Edge Cases:** reindex after taxonomy changes; mapping changes (versioned index behind an alias); attribute explosion (typed nested attributes); missing seller rating.

**Validation Rules:** only published, non-expired listings are searchable; address and phone numbers are never indexed.

**Open items:** hosting (self-hosted or managed), dev setup, sizing, backups and alerting.

---

### US-121: Admin: Categories, Attributes, Options and AI Settings
**As an** Admin **I want** to manage the taxonomy, attributes, options and AI settings **so that** the marketplace can change without a release

**Acceptance Criteria:**
- Given I am an authorized Admin
- When I enable or disable a category
- Then all its descendants are runtime-disabled without rewriting their own flags
- When I set a category popular and give it a rank
- Then at most 15 L1 and 10 L2 per L1 are accepted
- When I edit an attribute or its options, or bulk upload options from a file
- Then the change applies to the dynamic Item Details form and to search facets
- When I switch AI on or off (and set confidence thresholds)
- Then the seller flow follows it: off, unavailable or low confidence means manual entry
- And every change is recorded in an audit trail (US-083)

**Edge Cases:** disabling a category with live listings (they stay stored but leave search and navigation); duplicate option codes in a bulk file; invalid file rows (the whole file is rejected with row errors); two Admins editing at once.

**Validation Rules:** `uiPopular` requires the category to be enabled; popular ranks are unique among siblings; L3 popularity is ignored; prohibited categories cannot be enabled for listing.

**Error Scenarios:** `ERROR_POPULAR_LIMIT_EXCEEDED`, `ERROR_DUPLICATE_RANK`, `ERROR_INVALID_OPTION_FILE`.

---

### US-122: Shiprocket Delivery Integration
**As a** buyer and seller **I want** delivery to be offered only where it can actually be shipped **so that** orders are picked up and delivered reliably

**Acceptance Criteria:**
- Given an L3 category is delivery-eligible (database policy, not hard-coded)
- When the seller lists an item
- Then packed weight and size are captured on Item Details
- When a buyer enters a delivery PIN
- Then delivery options are shown only if Shiprocket serviceability returns a valid courier for the seller's pickup PIN, package and PIN
- When an order is confirmed
- Then a shipment is created, the seller pickup is arranged (pickup locations reused per address), and tracking updates persist locally
- And whole vehicles and real estate are never delivery-eligible

**Open items (to be decided inside this story):**
1. Which delivery-eligibility states show delivery at launch (provisional or only partner-confirmed); `UNKNOWN` hidden or not.
2. Prepaid only (no COD).
3. Who pays shipping, any markup, and who absorbs quote versus actual differences (platform fee US-025, payout US-024).
4. Courier choice (cheapest, fastest or buyer-picked).
5. Pickup address (saved US-108 or US-113 address, at listing time or order time) and consent for sharing seller phone and email.
6. Shiprocket account (owner, plan, sandbox, pickup-location limits, webhooks).
7. Impact on US-027 to US-032, US-034 and US-060 (reverse pickup, NDR, RTO; proof photos and in-app confirmation).

**Edge Cases:** PIN not serviceable; courier changes between quote and booking; partial failure creating a shipment (reconcile before retry); duplicate webhook events; weight or dimensions changed after listing.

**Error Scenarios:** `ERROR_DELIVERY_NOT_AVAILABLE`, `ERROR_PIN_NOT_SERVICEABLE`, `ERROR_SHIPMENT_CREATION_FAILED`.
