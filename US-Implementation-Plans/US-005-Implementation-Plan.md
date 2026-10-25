# US-005: AI-Assisted Listing Creation — Implementation Plan

> **Update (2026-10-25, category taxonomy):** US-006 is built first, so this plan must be revised before it is built: classify to an L1/L2/L3 category code from the taxonomy in one stage and store suggestions with category codes; prefill only attributes the Metadata Dictionary marks AI-extractable, validated against the category's listing schema; the AI on/off switch and thresholds come from US-121 (until then `valuex.ai.enabled`); define retention and limits for seller photos sent to the Vision service; price comparables join on `listings.category_id`. The open gap about validating categories against the taxonomy is closed by US-006. Migration numbers shift (US-006 takes `V16`).

## 1. Header

| Field | Value |
|---|---|
| Story ID | US-005 |
| Title | AI-Assisted Listing Creation |
| Sprint | Sprint 2 — Seller Listing Creation |
| Story Points | 8 |
| Repos | valuex-backend, valuex-mobile (only the Submit to AI wiring and unavailable message). `valuex-ai` is out of scope (built separately by another team, integrated later) |
| Dependency | US-004 — Create Listing with Photo Capture; draft must be `DRAFT` with at least one READY listing media asset. US-089 is built first (listing states); US-114 (Listing Item Details Entry) provides the Item Details page |

Sprint 2 goal: allow sellers to create and publish listings. US-005 provides advisory metadata suggestions for the US-004 draft flow and must never prevent manual listing creation.

**Scope decisions (2026-10-15):**
1. The AI service (image analysis, categorization, text generation) is developed separately and arrives later. This plan delivers only the backend side of the boundary: persistence, the three seller endpoints, the AI Gateway client against the LLD §6.2 contract, fallback/resilience and feedback capture.
2. **Every Sprint 2 story assumes AI is disabled or down and works manually.** A single configuration switch, `valuex.ai.enabled` (default `false`), turns AI assistance on or off. When off, nothing calls the AI service, nothing fails, and the seller fills in item details, category and description by hand. When on, the AI fills those fields and the seller reviews them.
3. **Price suggestion is on hold** (still in design discussion). It is removed from this story's implementation until the design is settled: no price range in the persisted suggestion, no price feedback field, no price re-validation, no price warnings.
4. **Unavailable message.** When the seller taps **Submit to AI** and AI is disabled, down, or its usage quota is exhausted, the app shows: "AI Service is not available at this moment or your usage quota has exhausted, please do manual entry". The backend sends the same text as the degraded response `message` (error code `ERROR_AI_SERVICE_UNAVAILABLE`); a quota-exhausted or HTTP 429 reply from the AI Gateway is treated like any other unavailable result.

## 2. Story Recap

**As a** seller **I want** AI to suggest item details from my photos **so that** I can create listings faster with accurate information.

**Acceptance Criteria** (`Documents/user-stories.md`):
- Given uploaded item photos, AI suggests category, title, condition, and description. (Price range is on hold, see Scope decisions.)
- Seller can accept, edit, or reject each suggestion independently.
- Seller can manually enter any field.
- Added by scope decision: with AI disabled or unavailable, the seller completes every field manually and nothing fails.

**Edge Cases:** AI cannot identify item · wrong category · multiple items in photos · AI disabled · AI timeout/failure. (Unrealistic price and unique/rare item without comparables are deferred with price suggestion.)

**Validation Rules:** suggestions optional/manual entry always allowed · category from predefined list · title max 100 characters · description max 2000 characters. (The 20% price rule is deferred with price suggestion.)

**Error Scenarios:** `ERROR_AI_SERVICE_UNAVAILABLE` · `WARNING_UNABLE_TO_IDENTIFY`. (`WARNING_PRICE_OUT_OF_RANGE` is deferred.)

## 3. Design Reference

Primary source: [Sprint-2-Seller Listing Creation-LLD.md — Part B](../LLD/Sprint-2-Seller%20Listing%20Creation-LLD.md#part-b---us-005-ai-assisted-listing-creation), sections 1–15.

Supporting references:
- [HLD Part 2 — Backend Architecture](../HLD/02-Backend-Architecture.md#43-listing-module): Listing module ownership and package boundaries.
- [HLD Part 3 — Data Architecture](../HLD/03-Data-Architecture.md#43-listing-domain): listing/category persistence.
- [HLD Part 4 — AI Architecture](../HLD/04-AI-Architecture.md#31-ai-must-be-advisory-unless-business-rule-requires-blocking): advisory AI boundary, internal gateway, model/version metadata, resilience.
- [HLD Part 4 — Visual/media access](../HLD/04-AI-Architecture.md#5-visual-search-architecture): shared media-ID and authorized media-access boundary; US-005 does not implement visual-search embeddings.
- [HLD Part 6 — Security/Deployment](../HLD/06-Security-Deployment-DevOps.md): internal service networking and secret handling.
- [HLD Part 7 — API/Integration](../HLD/07-API-Integrations-Release-Risk.md#27-ai-service-integration): internal AI integration conventions.
- [CODING_STANDARDS.md](../CODING_STANDARDS.md): Java/Python structure, API envelopes, security, testing, and secret-management rules.

**Key design decisions:**
- Spring Boot remains the source of truth and the only writer of `listings`; AI returns predictions only.
- Backend endpoints are `POST /api/v1/listings/{listingId}/ai-suggestions`, `GET .../ai-suggestions`, and `PATCH .../ai-suggestions/{suggestionId}/feedback`.
- AI service endpoint is internal-only: `POST /ai/v1/listings/suggest` through the AI Gateway.
- Listing images are passed across the AI boundary as `mediaIds`; the Media Module issues short-lived authorized reads. No provider URLs or signed URLs are persisted as business data.
- AI failures return an HTTP 200 degraded advisory payload with manual entry available; circuit breaker and 5-second time limiter protect the backend.
- AI suggestions and per-field feedback are append-oriented records for later quality/retraining analysis.
- **Master AI switch.** `valuex.ai.enabled` (env `VALUEX_AI_ENABLED`, default `false`) is checked by `ListingAiService` before any AI call. Disabled: no gateway call, no suggestion row persisted, the rate limit is not consumed, and the endpoint returns the same HTTP 200 degraded payload (`fallback: true`, manual-entry message). Enabled but the service is down, slow or its circuit is open: the call falls back the same way and a `FAILED` row is persisted. The switch is a shared `AiProperties` in `common.infrastructure.ai` so later Sprint 2 stories reuse it. The LLD §6.2 request/response JSON (minus price) is the contract handed to the AI team.
- **Manual fallbacks for the other AI-using Sprint 2 stories (decided 2026-10-15/16; implemented in their own plans, see [US-007](US-007-Implementation-Plan.md) and [US-084](US-084-Implementation-Plan.md); this story only provides the shared `valuex.ai.enabled` switch):**
  - **US-007 Restricted Items:** when AI is disabled or unavailable, a rule-based check against a `restricted_items` table of terms runs on title, description and category, and a match is treated as an AI `RESTRICTED` result.
  - **US-084 Trust & Safety Review:** when AI is disabled or unavailable, no fraud score is computed. Until the admin console arrives the listing is auto-approved (recorded as such); manual moderation is switched on later by configuration.
## 4. Implementation Steps

### Database Migration — `valuex-backend`
- [ ] Add the US-005 migration as `V16__listing_ai_suggestions.sql` (after US-089's `V13`, US-114's `V14` and US-078's `V15`; renumber to the next free version at implementation time).
- [ ] Add `listing_ai_suggestions` with status (`PENDING`, `COMPLETED`, `FAILED`, `TIMEOUT`), category JSON, title, condition, description, warnings, confidence, model name/version, inference ID, latency, fallback flag, and timestamp. No price columns; they are added by a later migration once the price design is agreed.
- [ ] Add `listing_ai_suggestion_feedback` with suggestion ID, field (`CATEGORY`, `TITLE`, `CONDITION`, `DESCRIPTION`), action (`ACCEPTED`, `EDITED`, `REJECTED`), original/final values, and timestamp.
- [ ] Do not add `listings.ai_assisted`; it already exists (`V10__listing_media_schema.sql`, `Listing.aiAssisted`).
- [ ] Add indexes on suggestion listing/status and feedback suggestion ID.
- [ ] Keep the migration compatible with the US-004 `listings` and media-ID model; do not introduce raw image URL columns.

### Backend — Domain, Persistence, DTOs
- [ ] Add `ListingAiSuggestion`, `ListingAiSuggestionFeedback`, `ListingAiSuggestionStatus`, `ListingAiFeedbackField`, and `ListingAiFeedbackAction` under the existing listing module layers (`domain`, `application`, `api`, `infrastructure/persistence`).
- [ ] Add repositories for latest suggestion lookup, per-listing hourly trigger count, and feedback persistence.
- [ ] Add response DTOs: `ListingAiSuggestionResponse`, `CategorySuggestionDto`, and `SuggestionFeedbackRequest`.
- [ ] Add internal AI transport models using `mediaIds`, listing ID, seller ID, seller location, and optional text hint; map AI response model/version/inference metadata without exposing provider internals.

### Backend — AI Switch and Gateway Client (no AI logic)
- [ ] Add `AiProperties` (`valuex.ai.enabled` default `false`, `gateway.base-url`, `gateway.api-key` from environment, `gateway.timeout-seconds` default 5) in `common.infrastructure.ai`, bound through `ValuexProperties`; add the keys to `application.yml`. Base URL and API key are not required while `enabled=false`.
- [ ] Add `AiGatewayClient` in `common.infrastructure.ai` using `RestClient` (as in `GoogleAddressVerificationAdapter`) to call `POST /ai/v1/listings/suggest` with `X-Internal-Api-Key`, READY media IDs and optional `textHint` (max 500 characters). `ListingSuggestRequest` / `ListingSuggestResponse` records follow LLD §6.2 without the price range, plus `ListingSuggestResponse.unavailable()`.
- [ ] Add `io.github.resilience4j:resilience4j-spring-boot3` (plus `spring-boot-starter-aop`, which its annotations need) to `pom.xml`, and configure the `aiGateway` circuit breaker per the LLD (sliding window 20, failure threshold 50%, 30s open) with the 5-second timeout on the `RestClient`; no blind retries. Wrap `AiGatewayClient.suggestListing` with `@CircuitBreaker(name = "aiGateway")` and a fallback returning `unavailable()`.
- [ ] Map timeout, HTTP error, malformed body and open circuit to `unavailable()`.
- [ ] Verify the client with a mocked HTTP server only; it is not run against a real AI service in this story.
- [ ] Log inference IDs and listing ID in structured logs without signed URLs, image bytes, credentials, or PII.

### Backend — `ListingAiService`
- [ ] Validate authenticated seller ownership, listing status `DRAFT`, and at least one listing media ID.
- [ ] If `valuex.ai.enabled=false`, return the degraded manual-entry response immediately: no gateway call, no row persisted, no rate-limit consumption, `ai_assisted` stays false.
- [ ] Enforce the LLD trigger limit of 5 generations per listing per hour with `AI_SUGGESTION_RATE_LIMITED`.
- [ ] If the call fails, times out or the circuit is open, persist a `FAILED`/fallback suggestion and return the same degraded response.
- [ ] Persist completed suggestions with warnings, confidence, model/version, inference ID, latency, and `ai_assisted=true`.
- [ ] Truncate title to 100 and description to 2000 characters, and accept only valid condition values, before persistence.
- [ ] Ensure low-confidence/unclear and multiple-item cases remain successful advisory responses, not hard failures.
- [ ] Record accept/edit/reject feedback per field and verify the suggestion belongs to the requested listing and authenticated seller.
- [ ] Keep suggestion feedback separate from applying final values; final seller values continue through the existing listing update flow.

### Backend — API
- [ ] Add `ListingAiController` with seller authorization and ownership checks:
  - `POST /api/v1/listings/{listingId}/ai-suggestions`
  - `GET /api/v1/listings/{listingId}/ai-suggestions`
  - `PATCH /api/v1/listings/{listingId}/ai-suggestions/{suggestionId}/feedback`
- [ ] Use the standard `ApiResponse` envelope and existing centralized exception handling.
- [ ] Return `LISTING_NOT_FOUND`, `LISTING_HAS_NO_IMAGES`, `LISTING_NOT_IN_DRAFT`, `AI_SUGGESTION_RATE_LIMITED`, and `AI_SUGGESTION_NOT_FOUND` according to the LLD.
- [ ] Keep AI disabled, AI unavailable, unable-to-identify and multiple-item cases in successful advisory payloads.

### AI Service — `valuex-ai` (OUT OF SCOPE, separate team)
Not implemented in this story. Image identification, categorization, text generation, the FastAPI router, Pydantic models, media retrieval and AI configuration (LLD Part B §6) belong to the AI team. Price estimation is on hold.
- [ ] Hand the AI team the contract: LLD §6.2 request/response models (without price), the `X-Internal-Api-Key` header, the 5s backend timeout, and the warning codes (`MULTIPLE_ITEMS_DETECTED`, `WARNING_UNABLE_TO_IDENTIFY`, `WARNING_IMAGE_UNCLEAR`).
- [ ] Integration (later, separate task): set `VALUEX_AI_ENABLED=true`, point to the AI Gateway, run an end-to-end check with the real service.

### Mobile (Flutter)
Only the **Submit to AI** wiring in `valuex-mobile/lib/features/listing`; per-field accept/edit/reject UI for real AI suggestions is built when the AI service is integrated.
- [ ] Add a `ListingRepository` method for `POST /api/v1/listings/{listingId}/ai-suggestions` and call it from `_submit` in `create_listing_screen.dart` after photos are uploaded.
- [ ] When the response is the degraded one (`fallback: true`) or the call fails, show the message "AI Service is not available at this moment or your usage quota has exhausted, please do manual entry" and continue to manual entry.
- [ ] Add the message as an l10n string in `app_en.arb` and `app_hi.arb` (Hindi translation to be confirmed) and map `ERROR_AI_SERVICE_UNAVAILABLE` in `listing_error_messages.dart`.
- [ ] When a real suggestion comes back, hold it for the later review UI; no suggestion UI in this story.
- [ ] Follow `Documents/CODING_STANDARDS.md` and the design system (`valuex-mobile/docs/Flutter-Design-System.md`): tokens only, 48 dp tap targets, labelled controls.

### Documentation/Quality
- [ ] Add/update OpenAPI examples for the three backend endpoints.
- [ ] Update the Sprint 2 LLD if implementation deviates from the Part B design (e.g. the `valuex.ai.enabled` switch, price suggestion removed, RestClient instead of WebClient, package layout).
- [ ] After implementation, create `Documents/Manual Testing Guides/US-005-Testing-Guide.md` with manual/API test steps.

## 5. Test Plan

Target >90% coverage for new backend/AI service logic, consistent with `CLAUDE.md`.

### Backend Unit Tests

- [ ] Happy path (AI enabled, mocked client) returns category, title, condition, description, confidence, model/version, and persists the suggestion.
- [ ] AI disabled: no gateway call, no row persisted, rate limit untouched, degraded manual-entry response returned, `ai_assisted` unchanged.
- [ ] Rejects missing listing, non-owner listing, non-`DRAFT` listing, and listing with no READY images (also when AI is disabled).
- [ ] Enforces the 5-per-hour per-listing trigger limit.
- [ ] Returns fallback/manual-entry payload and persists `FAILED` for AI timeout, gateway error, gateway quota/429 reply, and open circuit.
- [ ] Persists `ai_assisted=true` only after a completed AI response.
- [ ] Persists one feedback row for each accepted/edited/rejected field.
- [ ] Rejects feedback for a suggestion belonging to another listing or seller.
- [ ] Preserves listing state when recording suggestion feedback.

### Backend Integration/Contract Tests

- [ ] `POST /ai-suggestions` happy path with `valuex.ai.enabled=true`, a mocked AI Gateway server and Testcontainers PostgreSQL.
- [ ] AI Gateway 5xx/timeout returns HTTP 200 degraded advisory response and persists fallback status.
- [ ] Default configuration (`valuex.ai.enabled=false`, no gateway URL or key set) starts the app, and `POST /ai-suggestions` returns the degraded response while the draft stays manually editable.
- [ ] `GET /ai-suggestions` returns the latest attempt and returns `AI_SUGGESTION_NOT_FOUND` when none exists.
- [ ] Feedback endpoint validates field/action values and standard error envelope.
- [ ] `AiGatewayClient` request/response JSON matches the LLD §6.2 contract (camelCase `mediaIds`, model metadata), verified against a mocked HTTP server, including the `X-Internal-Api-Key` header, timeout and malformed-body handling.
- [ ] Seller ownership prevents IDOR access to another seller’s listing/suggestion.

### AI Service Tests

Out of scope; the AI team owns the `pytest` suite. Backend tests cover how the backend handles each AI outcome:
- [ ] AI response with `WARNING_UNABLE_TO_IDENTIFY` and empty category suggestions persists as `COMPLETED`, not `FAILED`.
- [ ] AI response with `MULTIPLE_ITEMS_DETECTED` persists and is returned unchanged.
- [ ] Over-long title (>100) and description (>2000) from the AI are truncated before persistence; unknown condition values are rejected or dropped.
- [ ] Model name/version and inference ID are stored with every completed suggestion.

### Mobile Tests (Flutter)

- [ ] Widget test: tapping **Submit to AI** with a degraded/failed response shows the unavailable message and does not crash or lose the uploaded photos.
- [ ] Repository test: the endpoint call parses both a normal and a degraded response.
- [ ] Message exists in English and Hindi and passes the accessibility guideline checks (tap target, label, contrast).

## 6. Validation Checklist

- [ ] Category suggestion is stored as returned by the AI; validating it against the predefined taxonomy depends on US-006 (Open Gap 3) and the AI team's classifier.
- [ ] Title is never persisted above 100 characters.
- [ ] Description is never persisted above 2,000 characters.
- [ ] Condition is constrained to `NEW`, `LIKE_NEW`, `GOOD`, `FAIR`, or `POOR`.
- [ ] No price suggestion, price column, price feedback or price warning exists (on hold).
- [ ] AI remains advisory; manual entry works without a successful AI response.
- [ ] Seller can independently accept, edit, or reject every suggested field through feedback records and the existing listing update path.
- [ ] Low-confidence, multiple-item, unique-item, and wrong-category cases remain recoverable without blocking draft creation.
- [ ] AI timeout/failure returns `ERROR_AI_SERVICE_UNAVAILABLE` guidance and leaves the draft manually editable.
- [ ] AI Gateway calls are internal-only and authenticated; the API key comes from environment configuration.
- [ ] Only `mediaIds` cross the boundary; no raw provider URL or signed URL is persisted/logged.
- [ ] Listing ownership is derived from the authenticated security context.
- [ ] Suggestion and feedback records retain model/version/inference/latency metadata for observability.
- [ ] With `valuex.ai.enabled=false` (default) the app starts and works end to end without any AI configuration, and every suggestion request degrades to manual entry.
- [ ] Switching `valuex.ai.enabled` needs no code change.
- [ ] Tapping **Submit to AI** with AI off or down shows exactly: "AI Service is not available at this moment or your usage quota has exhausted, please do manual entry".
- [ ] `valuex-ai` remains unchanged.
- [ ] Checkstyle, full tests, coverage, and SonarQube checks pass before push.

## 7. Open Gaps / Questions

1. **AI service contract ownership.** The AI team must agree to the LLD §6.2 contract (or propose changes) before integration. Any contract change updates the Part B LLD and the gateway client.
2. **Circuit breaker mechanism (decided).** Add `resilience4j-spring-boot3` and wrap `AiGatewayClient`, as in the Implementation Steps. The same dependency is reused by later AI-calling stories (each with its own breaker instance).
3. **Category data.** `listings` has no category column and there is no taxonomy table (US-006 owns them), so suggested categories are stored as returned and cannot yet be validated against a predefined list.
4. **Price suggestion (on hold).** When the design is settled: add price columns, a `PRICE` feedback field, comparable-listings access for the AI team (credentials, or via a backend endpoint) and the ±20% re-validation (LLD §5.7.1, §6.3.1). Not built now.
5. **US-007 and US-084 manual fallbacks (decided).** Details are in their own plans. Nothing further is needed for US-005.
6. **How the app learns AI is off (decided).** The app always shows **Submit to AI** and learns the state from the response and the message above, so no `aiSuggestionsAvailable` flag is added.
7. **Manual entry screen (decided).** [US-114](US-114-Implementation-Plan.md) "Listing Item Details Entry" builds the Flutter Item Details page from the Figma Make screen in the brand theme. After the unavailable message the app opens it with empty fields; with AI on it opens prefilled. This story only needs to hand the suggestion (or none) to that page.
8. **Media completion/derivative timing.** US-004 currently exposes media lifecycle/API foundations; asynchronous AVIF/WebP worker processing is a documented follow-up. US-005 must consume only media assets that the Media Module reports as READY.
9. **Listing update endpoint (decided).** [US-114](US-114-Implementation-Plan.md) adds `PATCH /api/v1/listings/{listingId}` (title, category, condition, description, price, location city) for drafts and listings in revision, and applies the seller's final values; US-010 later extends it to published listings.
---

**Status:** Revised
