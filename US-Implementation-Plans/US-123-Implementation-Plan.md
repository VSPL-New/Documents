# US-123: Preview Listing - Implementation Plan

## 1. Header

| Field | Value |
|---|---|
| Story | US-123 - Preview Listing |
| Sprint | Sprint 2 - Seller Listing Creation |
| Story points | TBD; do not change sprint totals until estimated and approved |
| Repos involved | valuex-backend, valuex-mobile; Documents for delivery records |
| Dependencies | US-004/US-114 (saved listing and photos), US-006 (category schema), US-089 (states), US-009/US-084 (submitted page and review result), US-010 (My Listings entry) |
| Date | 2026-11-08 |
| Handoff gate | Approved by the user on 2026-11-08, including G1-G4 as recommended. Implemented on local branches, not committed (section 8) |

This file is the canonical plan. It follows the repository's existing `US-Implementation-Plans/` location, even though the US-Implementor agent's generic instructions mention the older `Documents/<US-ID>-Implementation-Plan.md` path. Pass this exact file to the implementor. Do not duplicate it at the old location.

## 2. Story Recap

As a seller, I want to preview my saved listing the way buyers will see it, so that I can check it before and after publication.

### Acceptance Criteria

| ID | Required behavior |
|---|---|
| AC1 | An authenticated owner can open the saved listing preview from US-009 and the approved US-010 entry points. Another user, a missing listing or a soft-deleted listing receives `LISTING_NOT_FOUND`; no content flashes before authorization succeeds. |
| AC2 | Show ordered photos, title, asking/derived price, category path, applicable condition, description, category-specific details, saved location and eligible plan badge. Never manufacture sample values or trust a navigation payload as the source of truth. |
| AC3 | Show the current seller-only status; revision required includes the stored review reason. Support existing non-editable states without enabling mutations. Paused is a future state dependency, not a lifecycle implementation in this story. |
| AC4 | Overview contains all applicable mandatory fields for the selected category, including conditionally required fields. Fields represented in the shared summary are not repeated. |
| AC5 | Details contains every remaining populated applicable field, including optional fields. Hide empty optional fields; preserve meaningful `0`, `false`, lists and structured values. |
| AC6 | Both tabs use the latest persisted values regardless of AI or manual origin, including seller corrections. Do not generate AI suggestions, refile the category, save, validate-for-submission or resubmit on preview load. |
| AC7 | Revised C layout: Overview and Details only; location stays above the tabs; condition is right-aligned on the item-title row. Long titles and translated text wrap without covering the badge. |
| AC8 | Fixed safe-area footer: Chat, Call and Video in row one; Make an Offer and Buy Now in row two. Save remains in the header. All six buyer controls are visibly and semantically disabled, with the preview explanation. |
| AC9 | Owner-authorized, short-lived photo links only; tolerate missing, failed, removed and expired images independently of the rest of the listing. |
| AC10 | One reusable read-only content widget, English/Hindi UI, existing JustQlic tokens/components, accessible scrolling and 200% text scaling. Allow future reuse by US-126/US-012 without implementing those stories. |

### Confirmed Design Decisions

- The user selected C, then removed its Location tab and added Call, Video and Make an Offer to the existing buyer actions.
- The user confirmed the mandatory-versus-remaining-populated split, independent of AI/manual provenance.
- Title, price, condition and location remain above the tabs without duplication. The condition badge is aligned at the right of the title row, not on a separate row below the price.
- The supplied buyer screenshot is a reference for button arrangement and condition placement only. Seller profiles, ratings, view counts, sharing, escrow/shipping/returns claims and verification badges were not requested and are not in scope.
- The preview is read-only. Edit, delete, pause/resume, relist, appeal, resubmit, calling/video sessions, negotiations, checkout and favourites are not implemented here.

## 3. Design Reference

- [Story](../user-stories.md#us-123-preview-listing) and [Sprint 2](../Sprint-plan.md#sprint-2---seller-listing-creation).
- [Sprint 2 LLD, Part L](../LLD/Sprint-2-Seller%20Listing%20Creation-LLD.md#part-l---us-123-preview-listing): this story's design and contract gaps. Existing foundations: Parts A (owner/media reads), C (schema and derived price), E (state vocabulary), F (review decisions), G/H (plans), I (submitted page), J (My Listings) and K (notification routes).
- [Revised C interactive mockup](US-123-preview-options.html). Figma writes were blocked by the account's MCP quota; there is no newly created US-123 Figma frame to implement or map. The local artifact is the layout reference.
- [Flutter design system](../../valuex-mobile/docs/Flutter-Design-System.md) and [coding standards](../CODING_STANDARDS.md) control production tokens, components, accessibility, localization and quality gates.

**Mockup limitation:** the watch, price, category path, one-photo counter, review reason and Boosted badge are fictional sample data. The current HTML puts the description in Overview and sample attributes in Details; it does not demonstrate schema-driven grouping. AC4/AC5, not that static grouping, govern production. The real gallery handles the saved photo count and ordering. The sample neighbourhood is not a reason to expose an address: the current saved API value is a city.

### Verified Implementation Anchors

| Area | Existing implementation and implication |
|---|---|
| Owner listing read | `ListingController.getDraft` -> `ListingDraftService.getDraft` -> `ListingDraftAssembler`; `GET /api/v1/listings/{listingId}` already returns status, common values, attributes, category path, plan code and image/media IDs. Ownership is checked before assembly. |
| Deleted records | `ListingRepository.findByIdAndSellerId` filters `deletedAt is null`. Preserve this and identical not-found responses for another owner. |
| Missing preview context | `ListingDraftResponse` has no review reason, plan display name, publication date or inline schema. This is contract gap G1, not a currently available API. |
| Photo read | `ListingRepository.photoUrl` already calls `POST /api/v1/media/{mediaId}/access`; `MediaAssetService.createAccess` verifies media ownership/READY and returns `accessUrl` plus `expiresAt`. The mobile helper currently drops expiry. Reuse this flow, not a new public URL or a listing-review POST. |
| Requiredness | `listing_schema.dart`: `ListingSchema.isRequired(field, attributes)` handles `required` and `requiredWhen`; `isBlankValue` preserves `0`/`false`. `categoryFields` and `moreFields` represent form sections, not the requested preview split. |
| Disabled taxonomy | `ListingSchemaService.schemaForCode` requires a selectable leaf. `ListingDraftAssembler` already finds the stored category by ID; implement owner-scoped read-only schema access under approved G1. Do not relax taxonomy selection/write validation. |
| Saved values | `ExistingListing`/`ListingDetailsDraft` serve edit flows. The parser defaults absent quantity to 1: a preview must preserve absence rather than accidentally display this editing default as a saved fact. |
| Review source | `ListingTrustSafetyReviewRepository` stores the latest review, including rejection reason. `TrustSafetyReviewController` exposes a POST that can start/resubmit a review. Never call it to populate a read-only screen. |
| Plan display | `MyListingsService` resolves `planType` through `PlanRepository`; `Listing` stores `publishedAt`. Reuse these sources subject to G3 rather than calling a plan-selection API. |
| Entry points | `ListingSubmittedScreen._preview` is a snackbar stub. `MyListingsScreen._open` routes editable items to edit, plan-pending/failed items to plan selection, other unsold items to a status sheet, and sold items to a coming-soon message. G2 governs the additions. |

## 4. Implementation Steps

### 4.1 Approval and Scope

- [x] G1-G4 and the implementation plan approved explicitly by the user on 2026-11-08; approval recorded in this plan and LLD Part L. Estimate points separately; no estimate was approved.
- [x] Recheck the named files against the implementation branch. If the code/contract has changed, stop to reconcile the plan rather than silently broaden it.
- [x] No database migration or AI-service change is expected. Any new persisted schema/snapshot/history requirement needs a revised plan.

### 4.2 Backend Read Contract

- [x] Implement the approved G1 read projection on the existing owner GET. Preserve existing response fields and mutation consumers; add the approved nullable preview context. Reuse listing, taxonomy, plan and review application abstractions within module boundaries.
- [x] Resolve the owner/non-deleted listing first. Do not query or return review, schema or media context for an unauthorized caller. Keep the read transactional and free of listing/history/payment/review writes and events.
- [x] Derive the review reason from the latest relevant review only when the current state is `REVISION_REQUIRED` or `REJECTED`; never show an older failure on a subsequently approved/published/re-reviewing listing. Null means no recorded reason, not a fabricated message.
- [x] Resolve the schema for the listing's stored category under G1/G4, including disabled categories that still have definitions. Preserve the selectable-category checks on creation, edits and the public category-selector endpoint.
- [x] Return only approved saved common values and attributes, no raw moderation payload, reviewer identity, storage keys or private address/contact data. Never make an AI call.
- [x] Reuse media access authorization and TTL. Add expiry-aware parsing in mobile without breaking callers that currently expect `photoUrl` to return a string. Avoid a new photo endpoint unless the plan is revised.
- [x] Extend existing owner-read/controller/service tests and update any record-constructor fixtures affected by additive response fields. Do not turn edit endpoints into a new preview workflow.

### 4.3 Mobile Data and Field Projection

- [x] Reuse `ListingRepository.getListing` and the agreed response parser/provider pattern. Preserve raw nullable saved values for preview; do not run `ListingDetailsDraft.toJson`, form defaults, `saveDetails`, `setCategory` or AI generation during reads.
- [x] Keep presentation grouping in a pure, testable listing-domain helper. Read the current saved attribute map and the approved schema together. Use `ListingSchema.isRequired`, schema common-field visibility and server field order; do not use `isMore` or `aiPrefill` as requiredness.
- [x] Summary owns title, price, category path, applicable condition and saved city. Negotiability can stay beside the price when applicable. Overview owns remaining required common/category values (for example visible quantity and required condition notes); Details owns remaining populated values. Follow the US-114 description rule; the selected layout keeps the saved description in Overview.
- [x] For Real Estate, keep the already derived listing price in the summary, retain transaction intent in Overview and suppress only the same active price attribute represented by that summary. Do not hide distinct amounts such as a deposit or maintenance charge merely because they are prices. Respect category rules hiding condition/quantity/negotiability.
- [x] Translate option codes to schema labels; retain free text for `OPTION_OR_TEXT`. Format numbers/currency/units, dates without unintended timezone shifts, booleans, multi-options, text lists and nested object/JSON values without Dart/JSON debug dumps. Treat values as plain text, never executable markup.
- [x] Handle missing required values, empty Details, unknown fields/options and missing schema according to G4. Do not erase saved values or infer a new category. Do not expose excluded system attributes (coordinates/internal fields) as a fallback.
- [ ] (Partly done: each photo has its own link and a Retry that fetches a new one; there is no automatic refresh when a link expires, see delivery note 5.) Load photos in `sortOrder`, scope state/cache to the authenticated owner and listing, and clear private state on account/session change. Use signed URLs only while valid; handle refresh once after expiry/image failure, then show a per-image fallback/retry, not an infinite refresh loop. Opening or retrying images never changes a listing.
- [x] Use existing request/error/session-expiry handling. Prevent stale requests for another listing/account from replacing the current preview. Reopen/refresh reads current saved data; no full offline private-listing persistence is introduced.

### 4.4 Mobile Screen and Navigation

- [x] Add a reusable `ListingPreview` content widget under the listing feature, with a thin screen/provider for owner data, loading, errors, retry and navigation. Use existing file organization and shared widgets; a dedicated preview provider must not reuse mutable editor state.
- [x] Add a listing-ID-based route in `route_names.dart`, `app_router.dart` and the appropriate `route_guard.dart` allowlist. It must load by ID on fresh navigation and never treat client routing as ownership enforcement. Do not repurpose `/listing/{id}`, the future buyer/notification destination, without a separate approved scope change.
- [x] Replace the submitted-page snackbar with preview navigation using its existing `listingId`. Implement G2 in `my_listings_screen.dart`/`my_listing_card.dart`; preserve Edit/Delete permissions and plan recovery. Back returns to the originating screen; a direct route has a safe My Listings fallback.
- [x] Build revised C using Poppins/DM Sans and existing brand tokens: gallery with correct count and accessible enlarged photo, category path, title and right-aligned condition, price, city, and exactly two tabs. No Location tab or duplicate location section.
- [ ] (Partly done: Overview is selected first and the page scrolls at 200% text, but above 1.3x text the banner and buyer actions scroll with the content instead of staying fixed, see delivery note 2.) Keep Overview selected initially. Tabs and vertical content must remain usable with long values and 200% English/Hindi text. Keep the action area outside content scrolling; account for safe-area insets and growing labels without covering the last field.
- [x] Add the two footer rows and disabled Save control. Disable handlers and accessibility actions; no dialler launch, microphone/camera permission, call/video SDK, offer API, checkout, favourites mutation or haptic side effect. Keep the explanation visible for the disabled state.
- [x] Reuse `BrandGradientButton` for Buy Now, `SingleToneButton`/existing supported icon-button composition for secondary actions, and `SquareBackButton`/`AppImage`. Do not copy literal HTML colours, opacity/spacing numbers or hand-drawn icons into Flutter.
- [x] Map real `ListingState` values to localized status copy. `DRAFT` is not automatically "Details complete"; never claim completion from status alone. `TRUST_SAFETY_REVIEW`, revision required, published, sold, expired and other existing states must not be conflated. `DEACTIVATED_BY_SELLER` is not a substitute for future `PAUSED`.
- [x] Add English/Hindi ARB keys, error/status mapping and accessibility coverage. Schema labels currently come from the API; do not invent translations of user content or silently promise bilingual taxonomy labels not supplied by that API.

### 4.5 Delivery Workflow

- [x] Work on dedicated lowercase story branches from `main` in the affected repos; inspect and preserve existing uncommitted changes. This planning task does not create branches or commit files.
- [x] Run focused tests first, then the required repository checks: backend tests/verify and Checkstyle; mobile generated-code checks where applicable, `dart format`, `flutter analyze --fatal-infos`, tests and coverage. Meet repo floors (backend 80%, mobile 85%) and the implementor's >=90% new/changed-code target.
- [ ] (Blocked, not run: no SonarQube server on localhost:9000, no token, and the setup guide is not in the repository.) Run applicable SonarQube quality gates through the configured environment. Do not paste secrets into chat or commands recorded in the plan. Missing configuration is a reported blocker, not a passed scan. `CLAUDE.md` was not present in the workspace search; do not claim it was read.
- [x] Verify desktop/mobile mockup decisions in Flutter at narrow phone sizes and 200% text. Ask before running/installing tests on the user's emulator or device. Add a critical owner-preview flow integration test; document execution constraints honestly.
- [x] Write `Documents/Manual Testing Guides/US-123-Testing-Guide.md`, map cases to AC1-AC10, and reconcile LLD Part L with the as-built contract. Update the US-009/US-010 testing guides' placeholder notes only when implementation replaces those stubs.
- [ ] Ask separately before commit/push and before PR creation. Use Conventional Commits/PR titles such as `feat(US-123): add owner listing preview` and `docs(US-123): document listing preview`. Plan approval does not grant commit, push or PR approval; recording it does not start implementation.

## 5. Test Plan

Prefer existing fixtures and suites. Existing anchors: backend `ListingControllerTest`, `ListingDraftServiceTest`, `ListingDetailsIntegrationTest`, `ListingEditDeleteIntegrationTest`, `MediaAssetServiceTest`/`MediaControllerTest`; mobile `listing_fixtures.dart`, `listing_schema_test.dart`, `listing_submitted_test.dart`, `my_listings_test.dart`. Add only focused preview projection/widget tests where those suites are not a suitable home.

| Test group | Cases and assertions | AC |
|---|---|---|
| Owner read | Owner succeeds in supported states; guest rejected; other owner/missing/deleted IDs return not found; no metadata leakage or transient cached content on account switch | AC1, AC3 |
| No mutations | Preview load, tab changes, gallery, refresh and every disabled action produce zero listing saves, state transitions, review requests, AI calls, payment or favourite operations; media access POST is authorization only | AC6, AC8, AC9 |
| Requiredness | Required=true; requiredWhen matches/does not match; optional CATEGORY field; required MORE field; missing mandatory field; schema order; invisible common fields; each visible value appears once | AC2, AC4, AC5 |
| Saved values | Equivalent saved manual/AI values render identically; seller correction wins; missing quantity does not become 1; valid zero/false retained; blank optional string/list/map omitted | AC4-AC6 |
| Field types | Option labels and unknown-code fallback; OPTION_OR_TEXT; decimal/unit/date/boolean; lists and nested JSON; no raw HTML execution or private system-key exposure | AC2, AC5 |
| Real Estate/vehicles | Sale/rent/lease conditional fields; derived price without duplicate active amount; other monetary fields retained; common condition/quantity visibility; no mock watch assumptions | AC2, AC4, AC5 |
| Review/plan | Latest applicable reason only; null reason; re-review clears stale reason; no badge before publication; correct saved plan name/no hard-coded Boosted; unknown plan omitted | AC2, AC3 |
| Media | Zero/one/many photos; ordering; unauthorized media access; removed/non-READY image; broken bytes; short-lived link expires and bounded refresh; gallery remaining usable | AC9 |
| Navigation | Submitted-page ID; G2 card/Preview entry rules; Edit/Delete and plan recovery unchanged; sold item content without sale data; back/direct route/not-found/retry; old notification flows unaffected | AC1, AC3, AC10 |
| Layout/accessibility | Exactly Overview/Details; single location; title/condition no overlap at 320/390/428 widths and long Hindi text; both footer rows visible; scroll reaches last field; disabled semantics and logical focus; 200% text | AC7, AC8, AC10 |
| Resilience | Loading, offline/retry, 401/session refresh, 404, server error, disabled/missing schema, empty Details, unknown lifecycle string; no false success or infinite retry | AC1-AC5, AC9, AC10 |

## 6. Validation Checklist

- [ ] AC1-AC10 have automated coverage and manual-test cases; quality gates and coverage results are recorded rather than assumed.
- [x] Confirmed design C and the schema-based tab grouping are both implemented; static mockup field placement is not copied as business logic.
- [x] Plan/publication/review metadata comes from the approved read contract, not dummy content, stale My Listings data or a mutating POST.
- [x] The city is shown once; no saved address, precise coordinates, seller phone/email, fabricated ratings or commerce assurances are exposed.
- [x] All five footer controls and Save are inactive; no new permissions/SDKs or buyer workflows are installed.
- [ ] Owner reads and image reads are authorized; not-found, deletion, stale URL, expired session and account-switch behavior is tested.
- [ ] Conditional requiredness and all supported value types work for at least goods, vehicles, Real Estate and OTHER profiles.
- [x] No PAUSED lifecycle transition, order/payout section, notifications redesign, category-editor rewrite, database migration or AI-service change slipped into scope.
- [x] Manual guide, LLD and story describe the implementation accurately; unresolved gates are not marked passed.
- [x] User explicitly approved this plan on 2026-11-08; US-Implementor has not started coding.

## 7. Open Gaps / Questions

The user explicitly approved this plan and the recommended G1-G4 decisions on 2026-11-08. Part L records the same approved design, not an as-built implementation. G5 remains an estimation item only and does not block handoff.

| ID | Decision / remaining planning item | Approval |
|---|---|---|
| G1 | Reuse owner `GET /api/v1/listings/{listingId}` and existing media-access POST. Add nullable `listingSchema` (existing `ListingSchemaResponse` shape), `reviewReason`, `planName`, `publishedAt` to `ListingDraftResponse`; no new preview endpoint. Assemble the schema from the listing's stored category after ownership, allowing read-only disabled categories without relaxing edit/selector checks. Additive fields must not break existing GET/PATCH/submit/category callers. Review reason is plain text from the latest matching review only in revision/rejected states. | Approved 2026-11-08 |
| G2 | Preserve existing editable-card/plan-recovery card taps from US-010. Add a separately labelled Preview action on each My Listings card, including published/draft/revision/sold cards; it opens read-only C. Replace the non-editable unsold status-sheet destination with C. Keep sold-card tap reserved for US-126 until that story, but allow its separate Preview action to show item content now. Keep Edit/Delete rules unchanged. The alternative of changing all card taps to preview was not selected. | Approved 2026-11-08 |
| G3 | Use saved city only. Display the resolved plan name as a badge only when `publishedAt` is non-null and the plan name is known, including a previously published sold/expired listing; it describes the selected plan, not currently active benefits. No hard-coded Boosted or shipping/escrow claims. | Approved 2026-11-08 |
| G4 | Missing required field: localized "Not provided" in Overview, with no default invention. Empty Details: keep the tab and show "No additional details". Unknown saved non-system attribute: show in Details with its key as a fallback label; unknown option: show the saved code. If the category/profile no longer yields a schema, show a localized unavailable/retry state and known common values, without guessing requiredness or exposing raw system attributes. Admin-removed but non-deleted owner listings retain the existing owner's read visibility with a Removed status; deleted rows are not found. Future PAUSED can render a read-only label when supplied, but no new state/transition is added by US-123. | Approved 2026-11-08 |
| G5 | Story-point estimate is not yet agreed. Keep TBD and existing sprint totals; estimate separately without changing the approved scope. | Planning only; non-blocking |

**Risk notes:** inline schema expands an existing shared response; constructor fixtures and all consumer parsers need regression tests. The category schema is current, not a historical snapshot, so saved listings may gain missing mandatory fields after taxonomy changes; G4 is essential. The two-row footer reduces visible content height and needs text-scale tests. A future sale page must not accidentally enable buyer controls on the owner's read-only component. The review-result/appeal/resubmit UI mentioned as deferred in the US-084 plan is not blanket authorization for mutation controls on this screen.

**Handoff instruction:** give US-Implementor `Documents/US-Implementation-Plans/US-123-Implementation-Plan.md` and story ID US-123. The user approved the full plan, including G1-G4, on 2026-11-08. Follow the approved scope and normal implementation/commit/push/PR gates; seek clarification for any new deviation. No implementation was performed while recording approval.

## 8. Delivery Notes (2026-11-08)

Built on branches `feature/us-123-listing-preview` in `valuex-backend` and `valuex-mobile` (both from `main`). Nothing is committed or pushed.

**Deviations from this plan, and why**

1. **Footer buttons have no icons.** The approved mockup showed icons on Chat, Call and Video. The design system forbids new button variants and `SingleToneButton` has no icon slot, so all four secondary buttons are label-only. Adding an icon slot is a design-system change (conflict protocol 6.1) and needs the owner's decision.
2. **Banner and buyer actions scroll at large text.** Above 1.3x text size they scroll with the content instead of staying pinned: pinned, they overflowed a 320x640 phone at 200% text (74 px in English, 248 px in Hindi). At normal size they stay fixed as designed.
3. **The route is top level**, `/profile/listings/:listingId/preview`, not nested under My Listings. Nested, the router also built Profile and My Listings under the preview and started their loads. The route guard treats the prefix like My Listings, so a signed-out user is sent to sign in.
4. **The date formatter is passed in** (`PreviewLabels.formatDate`) so the field projection stays pure Dart with no intl locale setup.
5. **Photo links are not refreshed automatically.** Each photo fetches its own link when shown; Retry fetches a new one. There is no timer or on-expiry refresh, so a link that expires while the screen stays open is replaced only on Retry or when the screen is reopened. Left open in section 4.3.
6. **The status sheet is gone.** `listing_status_sheet.dart`, `listingStatusExplanation` and their five strings are removed, along with `submittedPreviewSoon`, because nothing uses them now.
7. **Admin-removed and unknown states read "Unavailable"** (the existing My Listings badge), not "Removed". There is no `PAUSED` state yet; an unknown state falls back to "This listing is not available to buyers".
8. **The app-wide accessibility and heading test maps were not extended.** They cover data-free screens. The preview has its own tap-target, label, contrast and 2x-text tests instead.
9. **Hindi strings are drafts** for native-speaker review, as for the rest of the app.

**Results**

| Check | Result |
|---|---|
| Backend `mvn -o test` (includes Checkstyle) | 1,484 tests, 0 failures; 127 Docker-backed integration tests skipped on this machine |
| Backend coverage, changed classes | `ListingPreviewAssembler` and `ListingDraftResponse` 100% of lines; `ListingDraftService` 100% of lines |
| Mobile `dart format`, `flutter analyze --fatal-infos` | clean |
| Mobile `flutter test --coverage` | 1,097 passed, 1 failed. The failure is `item_details_live_test.dart` "passes the tap target and label guidelines" (condition-chip contrast). It fails the same way on a clean `origin/main`, so it is not caused by this story and is not fixed here |
| Mobile coverage | new preview files 96.1% of lines; whole app 91.6% |
| Preview tests | 35 in `listing_preview_test.dart` (model, projection, repository, route guard, screen, accessibility, 2x text in English and Hindi) plus updated My Listings and submitted-page tests |
| Integration flow `integration_test/listing_preview_flow_test.dart` | passes when run headlessly as a temporary copy under `test/`. **Not run on the emulator**, as agreed |
| SonarQube | **Not run**: no server on localhost:9000, no token, setup guide missing |

**Not covered**

- No backend integration test of the owner GET JSON: `ListingDetailsIntegrationTest` and the other Docker-backed tests are skipped here. The response additions are covered by unit tests only.
- Stale-link expiry, session expiry and account switch while the preview is open are not tested; the provider is auto-disposed and the router guard handles sign-out.
- Vehicle and OTHER category profiles are not exercised in the projection tests (goods and Real Estate are).

**Status:** Approved - user approval recorded on 2026-11-08 for the implementation plan and G1-G4. Implemented locally on the branches above; not committed, pushed or reviewed. Story points remain TBD. Open: SonarQube scan, deviation 1 (icons), deviation 5 (automatic link refresh).