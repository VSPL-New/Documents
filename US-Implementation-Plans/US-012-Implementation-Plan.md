# US-012: View Listing Details — Implementation Plan

## 1. Header

| Field | Value |
|---|---|
| Story ID | US-012 |
| Title | View Listing Details |
| Sprint | Sprint 3 — Discovery & Search |
| Story Points | 5 |
| Repositories | valuex-backend, valuex-mobile |
| Dependency | US-011 (merged). Reuse the mobile US-123 preview presentation/projection where it matches. Sprint 3 LLD build order places US-012 before US-073 and US-118. Confirm the US-123 backend projection is available before implementation. |

**Planning status:** Approved by the user on 2026-11-12, including deferring save/heart UI and mutation to US-073.

## 2. Story Recap

**As a** buyer, **I want to** view complete listing details, **so that** I can make an informed decision.

**Acceptance Criteria** (from `Documents/user-stories.md`, updated by Sprint 3 LLD):
- Opening a listing shows all photos in a swipeable gallery, title, description, applicable condition, price, seller name/rating/location/joined date, listing age and communication options.
- Swiping photos allows full-resolution viewing.
- Opening the seller profile shows the seller's other listings and reviews.
- For Real Estate, show category path, attributes, intent and price for that intent; do not show cart or Buy Now. New Developments use "Starting from".
- Until their later stories are implemented, unavailable chat/call/video/cart actions are disabled with a "Coming soon" label. Seller reviews return unavailable/empty until Sprint 8.
- Listing unavailable or suspended-seller conditions show the documented error states.

**Edge cases:** listing deleted, expired, sold or hidden while open; seller suspended; photo failures; seller has no other listings or reviews.

**Validation rules:** photos are accessible; seller rating, when available, is 0–5; prices are INR; listing age uses server time so device clock differences do not alter it. The API exposes only the approved public fields.

**Error scenarios:** `ERROR_LISTING_NOT_AVAILABLE` (404), `ERROR_SELLER_SUSPENDED` (403), and the seller/listing not-found behavior defined by Part C.

## 3. Design Reference

- [Sprint-3-Discovery-Search-LLD.md — Part C, US-012](../LLD/Sprint-3-Discovery-Search-LLD.md#part-c---us-012-view-listing-details): source of truth for API, field allow-list, photo variants, capabilities, UI states, security and tests.
- [Sprint-3-Discovery-Search-LLD.md — Part A, US-120](../LLD/Sprint-3-Discovery-Search-LLD.md#part-a---us-120-opensearch-setup-and-listing-indexing): search card/photo variants and listing eligibility.
- [Sprint-2-Seller Listing Creation-LLD.md — Part C, US-006](../LLD/Sprint-2-Seller%20Listing%20Creation-LLD.md#part-c---us-006-category-taxonomy-and-category-driven-item-details): category schema, attributes and normalized property price.
- [US-123 Implementation Plan](US-123-Implementation-Plan.md), plus the merged mobile implementation: `lib/features/listing/presentation/widgets/listing_preview.dart`, `lib/features/listing/domain/listing_preview_fields.dart`, and `lib/features/listing/presentation/widgets/preview_gallery.dart`.
- [Figma Make — Mobile App UI Design](https://www.figma.com/make/tzrpUwfrR0SYeyKkv1p0co/Mobile-App-UI-Design?p=f&t=Y5u9K0QqLyfIIw41-0): the `ListingDetailScreen.tsx` screen is visual inspiration only. Adapt its gallery, hierarchy, seller summary and action-area ideas to the approved LLD and Flutter design system; do not port React/shadcn code or mock data.

**Reuse boundary:** US-123 `ListingPreview` and `projectPreviewFields` are seller-owned, read-only presentation. Reuse the shared field formatting, gallery or content widgets where they fit, but do not reuse the owner-only status/review banner, plan badge, My Listings route, or seller preview data contract as the buyer API/model. The US-012 LLD specifies a distinct `listing_view` feature and public response.

**Figma exclusions:** the Make screen contains sample seller/rating/view values and escrow, shipping and returns claims. Do not ship those unless returned by the approved API and in story scope. Follow Part C for disabled action capabilities; hide Real Estate cart/Buy Now as `NOT_APPLICABLE`, rather than treating the Make mock's Buy Now control as a requirement.

## 4. Implementation Steps

### Backend — `valuex-backend`
- [ ] Add `PublicListingController` and `PublicListingService` for authenticated `GET /api/v1/listings/{listingId}/public`, `GET /api/v1/sellers/{sellerId}/listings?page=&size=`, and `GET /api/v1/sellers/{sellerId}/reviews?page=&size=` using the standard API envelope.
- [ ] Add a dedicated `PublicListingFieldProjector` that reads persisted values through the stored category's `ListingSchemaResponse` and returns only populated fields defined by the schema, with schema labels and units. Omit unknown/unmapped values and `AttributeRules.EXCLUDED_KEYS`.
- [ ] Keep this public projector separate from US-123's owner-only `ListingPreviewAssembler`/`ListingDraftResponse`; do not expose status, review reason, plan data, owner media IDs or other owner-preview context. Share schema metadata only, not the owner response contract.
- [ ] Apply `ListingEligibilityFilter` before constructing the response or requesting photo links; reject non-live listings with `ERROR_LISTING_NOT_AVAILABLE` and inactive sellers with `ERROR_SELLER_SUSPENDED`.
- [ ] Build public fields from the allow-list: display name only; public city; category path and permitted attributes; `publishedAt` and `serverTime`; rating and count nullable/zero until Sprint 8; saved/own-listing flags. Never expose pincode, coordinates, seller phone/email, Aadhaar state, full name, serial number or excluded system attributes.
- [ ] Return all READY photos in sort order via `ListingPhotoLinkPort`, with thumbnail/detail/zoom variant URLs and signed-link expiry only for fallback links. Set `Cache-Control: no-store` on API responses.
- [ ] Return server-computed capabilities. Real Estate cart/Buy Now are `NOT_APPLICABLE`; own-listing actions are `OWN_LISTING`; not-yet-built buyer actions are `COMING_SOON`. Add seller listings through Part B query with a seller filter, newest first; return the Part C empty/unavailable reviews response until Sprint 8.
- [ ] Add OpenAPI examples and tests for authorization, eligibility, seller state and field redaction.

### Mobile — `valuex-mobile`
- [ ] Add `lib/features/listing_view` as a buyer-facing feature, separate from seller `lib/features/listing`. Add the API model/repository/provider for the public response; do not read seller-owned `GET /listings/{id}` or trust a navigation payload for detail data.
- [ ] Add `/listing/:id` routing; open it from search cards and use the same route for supported saved-item/notification deep links. Handle authentication, loading, retry and back-to-list behavior.
- [ ] Reuse US-123 `projectPreviewFields`, gallery and read-only content widgets where their inputs/semantics match. Factor a shared presentation component only where necessary; keep seller status/review banner and owner preview actions out of the buyer view.
- [ ] Build the detail layout from Flutter design-system tokens: swipeable gallery using `detailUrl`, thumbnail strip and on-demand `zoomUrl`; category path, title, applicable condition, price/qualifier, seller summary, city, posted age, description and schema-projected attributes.
- [ ] Compute listing age from API `publishedAt` and `serverTime`. Format INR with Indian digit grouping and show the correct transaction intent/price; show "Starting from" for `STARTING_FROM`.
- [ ] Render Chat, Call and Video disabled with the LLD's "Coming soon" state while unavailable. Hide Add to Cart and Buy Now when capabilities are `NOT_APPLICABLE`; never infer availability from client-side category logic.
- [ ] Add seller profile navigation and seller listings/reviews screens using the Part C APIs; represent unavailable/empty reviews accurately. Do not show a save/heart control or add bookmarking mutations; return `saved: false` until US-073 supplies real saved state.
- [ ] Localize app-owned strings in English/Hindi, use API-provided category/attribute labels, and cover gallery retry/expired-link handling, screen-reader semantics, text scaling and responsive layouts.

### Tests and Delivery
- [ ] Add backend unit/integration and Flutter widget/integration tests mapped to the acceptance criteria and edge cases; target greater than 90% coverage for new story code per `CLAUDE.md`.
- [ ] Create `Documents/Manual Testing Guides/US-012-Testing-Guide.md` covering live/unavailable/suspended cases, gallery and retry, seller navigation, Real Estate capability behavior and Coming Soon actions.
- [ ] Follow `CLAUDE.md`: create a feature branch from `main`, rebase with `main`, build, run backend Checkstyle/tests and mobile format/analyze/tests/coverage, run SonarQube, fix findings, and verify all acceptance criteria before pushing. Seek separate approval before commit/push and PR creation.

## 5. Test Plan

### Backend
- [ ] Public detail returns the exact approved field projection for a live listing and does not expose private/internal fields.
- [ ] Public projector tests cover known schema attributes, labels/units, empty optional values, unknown keys and excluded keys; owner-only US-123 context never appears in the public DTO.
- [ ] Deleted, expired, sold or hidden listing returns `ERROR_LISTING_NOT_AVAILABLE`; inactive seller returns `ERROR_SELLER_SUSPENDED`; seller listings enforce active/unknown seller behavior.
- [ ] Photo links are ordered and include the right variants; no photo URLs are returned before eligibility checks; signed fallback expiry is only present when applicable.
- [ ] Seller listings are paginated and newest-first; reviews return `{ reviewsAvailable: false, items: [] }` until the Rating module exists.
- [ ] Capability tests cover Real Estate `cart`/`buyNow` as `NOT_APPLICABLE`, own listing as `OWN_LISTING`, unavailable actions as `COMING_SOON`, and `saved: false` before US-073.
- [ ] Assert API response `Cache-Control: no-store`; verify no view counter/event is written.

### Mobile
- [ ] Deep route loads by listing ID; owner-only US-123 data is not used as the buyer source of truth; loading, retry, back, unavailable and suspended states work.
- [ ] Gallery covers 0/1/many images, ordering, swipe, zoom, broken/removed images and expired signed-link retry without blocking the rest of the page.
- [ ] Preview field projection/reused formatting handles options, booleans, numbers, dates, lists, objects, missing required values and hidden fields without duplicate summary values or exposing excluded keys.
- [ ] Posted age uses server time; price, city, category path and attributes render correctly; Real Estate intent/price and `STARTING_FROM` are correct.
- [ ] Capability-driven actions are disabled or hidden as designed; no button launches unbuilt chat/call/video/cart/buy flows.
- [ ] Seller profile navigation, empty reviews and seller listing pagination work; no save/heart control is displayed before US-073.
- [ ] Test English/Hindi, long text, 200% text scaling, 320px width, semantic labels/focus order and action-area safe-area layout.

## 6. Validation Checklist

- [ ] Public detail and seller APIs enforce authentication, live eligibility and active seller status before returning data or media links.
- [ ] Only Part C's public allow-list is returned; private identifiers, addresses, contact data and excluded attributes remain hidden.
- [ ] The public detail UI reads from the US-012 API, not the US-123 owner endpoint/model or navigation-payload snapshots.
- [ ] US-123 preview presentation/projection is reused where it fits, with seller-only status/review/plan UI kept out of the buyer screen.
- [ ] Photos use the correct variants and recover from per-image failures/expired fallback links.
- [ ] Price, qualifier, transaction intent, seller summary and listing age match the server response; `STARTING_FROM` is rendered correctly.
- [ ] Unavailable actions follow server capabilities; Real Estate never displays cart or Buy Now; no disabled action has an active side effect.
- [ ] US-012 displays no save/heart control or mutation before US-073; the public response uses `saved: false` until US-073 provides real state.
- [ ] Checkstyle, tests, coverage, SonarQube, manual guide and all acceptance criteria are complete before marking the story done.

## 7. Open Gaps / Questions

1. **Figma Make is illustrative only.** The source is a React prototype with mock seller values, view counts and commerce/trust claims. The plan follows Part C and the existing Flutter design system where these differ.

## 8. Implementation Deviations (2026-11-12)

Recorded after implementation; the LLD Part C.11 has the same table.

- Mobile does not reuse US-123 `projectPreviewFields` or `PreviewGallery`. The buyer API already returns schema-labelled attributes (`PublicListingFieldProjector`) and per-photo variant URLs, while those widgets read the owner response and owner-only photo links. Only generic building blocks are shared.
- `GET /sellers/{id}/reviews` takes no `page`/`size` (always empty until Sprint 8).
- The seller profile lists all of the seller's live listings, including the one being viewed; `otherListingsCount` counts only the others.
- Seller profile title is generic; the seller name is not passed in the navigation payload.
- Home cards and listing promos open the listing page too (added in a follow-up: US-111 deferred this to US-012 and this plan missed it).
- Backend scope check: the changes to `ListingCondition` (label), `ListingSearchQuery`/`SearchRequestValidator`/`ListingSearchService`/`OpenSearchQueryBuilder` (seller filter) and `ListingPricing` support the public response and the seller-listings step of this plan.

**Status:** Approved
