# US-005: AI-Assisted Listing Creation — Implementation Plan

## 1. Header

| Field | Value |
|---|---|
| Story ID | US-005 |
| Title | AI-Assisted Listing Creation |
| Sprint | Sprint 2 — Seller Listing Creation |
| Story Points | 8 |
| Repos | valuex-backend, valuex-ai; `valuex-mobile` excluded per `CLAUDE.md` §6 |
| Dependency | US-004 — Create Listing with Photo Capture; draft must be `DRAFT` with at least one READY listing media asset |

Sprint 2 goal: allow sellers to create and publish listings. US-005 provides advisory metadata suggestions for the US-004 draft flow and must never prevent manual listing creation.

## 2. Story Recap

**As a** seller **I want** AI to suggest item details from my photos **so that** I can create listings faster with accurate information.

**Acceptance Criteria** (`Documents/user-stories.md`):
- Given uploaded item photos, AI suggests category, title, condition, price range, and description.
- Seller can accept, edit, or reject each suggestion independently.
- Seller can manually enter any field.

**Edge Cases:** AI cannot identify item · wrong category · unrealistic price · multiple items in photos · unique/rare item without comparables · AI timeout/failure.

**Validation Rules:** suggestions optional/manual entry always allowed · price suggestion within 20% of similar listings · category from predefined list · title max 100 characters · description max 2000 characters.

**Error Scenarios:** `ERROR_AI_SERVICE_UNAVAILABLE` · `WARNING_UNABLE_TO_IDENTIFY` · `WARNING_PRICE_OUT_OF_RANGE`.

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
- Backend independently checks AI price range against comparable listings and appends `WARNING_PRICE_OUT_OF_RANGE` when needed.
- AI suggestions and per-field feedback are append-oriented records for later quality/retraining analysis.

## 4. Implementation Steps

### Database Migration — `valuex-backend`
- [ ] Identify the next Flyway version after the current migrations; add the US-005 migration (the LLD uses `V{N}` as a placeholder).
- [ ] Add `listing_ai_suggestions` with status (`PENDING`, `COMPLETED`, `FAILED`, `TIMEOUT`), category JSON, title, condition, description, price range/currency, warnings, confidence, model name/version, inference ID, latency, fallback flag, and timestamp.
- [ ] Add `listing_ai_suggestion_feedback` with suggestion ID, field (`CATEGORY`, `TITLE`, `CONDITION`, `DESCRIPTION`, `PRICE`), action (`ACCEPTED`, `EDITED`, `REJECTED`), original/final values, and timestamp.
- [ ] Add `listings.ai_assisted BOOLEAN NOT NULL DEFAULT FALSE` if not already present from US-004.
- [ ] Add indexes on suggestion listing/status and feedback suggestion ID.
- [ ] Keep the migration compatible with the US-004 `listings` and media-ID model; do not introduce raw image URL columns.

### Backend — Domain, Persistence, DTOs
- [ ] Add `ListingAiSuggestion`, `ListingAiSuggestionFeedback`, `ListingAiSuggestionStatus`, `ListingAiFeedbackField`, and `ListingAiFeedbackAction` under the existing listing module conventions.
- [ ] Add repositories for latest suggestion lookup, per-listing hourly trigger count, and feedback persistence.
- [ ] Add response DTOs: `ListingAiSuggestionResponse`, `CategorySuggestionDto`, `PriceRangeDto`, and `SuggestionFeedbackRequest`.
- [ ] Add internal AI transport models using `mediaIds`, listing ID, seller ID, seller location, and optional text hint; map AI response model/version/inference metadata without exposing provider internals.

### Backend — AI Gateway Integration
- [ ] Add `AiGatewayClient` under shared infrastructure, using the existing HTTP-client conventions and internal `X-Internal-Api-Key` configuration.
- [ ] Call `POST /ai/v1/listings/suggest` with the listing’s READY media IDs and optional `textHint` (max 500 characters).
- [ ] Configure Resilience4j circuit breaker `aiGateway` and 5-second time limiter per the LLD; do not add blind retries.
- [ ] Implement `ListingSuggestResponse.unavailable()` fallback and persist a `FAILED`/fallback suggestion while returning manual-entry guidance.
- [ ] Propagate request/inference identifiers in structured logs without logging signed URLs, image bytes, credentials, or PII.

### Backend — `ListingAiService`
- [ ] Validate authenticated seller ownership, listing status `DRAFT`, and at least one listing media ID before calling AI.
- [ ] Enforce the LLD trigger limit of 5 generations per listing per hour with `AI_SUGGESTION_RATE_LIMITED`.
- [ ] Persist completed suggestions with warnings, confidence, model/version, inference ID, latency, and `ai_assisted=true`.
- [ ] Independently validate the AI price range against comparable active listings using the ±20% band and append `WARNING_PRICE_OUT_OF_RANGE` when applicable.
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
- [ ] Keep AI unavailable, unable-to-identify, multiple-item, and price-warning cases in successful advisory payloads.

### AI Service — `valuex-ai`
- [ ] Add the internal FastAPI listing router at `/ai/v1/listings/suggest`, protected by the internal API-key dependency.
- [ ] Add Pydantic request/response models with `mediaIds`, category suggestions, title, condition, description, price range, warnings, confidence, model name/version, and inference ID.
- [ ] Implement provider-neutral Listing Intelligence Service orchestration: authorized media retrieval → image analysis → category classification → comparable price estimation → title/description generation.
- [ ] Add warnings for low confidence, unclear images, and multiple detected items; skip title/description generation when identification confidence is below the configured threshold.
- [ ] Return low-comparable results with low-confidence handling instead of fabricating a precise price.
- [ ] Add AI configuration for vision timeout, minimum identification confidence, minimum comparables, Media API URL, and internal credentials through environment variables.
- [ ] Never write backend-owned listing state directly from Python.

### Mobile/Web
- [ ] No mobile implementation in this pass. `valuex-mobile` is a React trial/prototype; the real client will be Flutter and is being developed separately. Future Flutter work will render the suggestions, allow per-field accept/edit/reject, and use the backend’s manual-entry path.

### Documentation/Quality
- [ ] Add/update OpenAPI examples for the three backend endpoints and internal AI contract.
- [ ] Update the Sprint 2 LLD if implementation deviates from the Part B design.
- [ ] After implementation, create `Documents/US-Implementation-Plans/US-005-Testing-Guide.md` with manual/API test steps.

## 5. Test Plan

Target >90% coverage for new backend/AI service logic, consistent with `CLAUDE.md`.

### Backend Unit Tests

- [ ] Happy path returns category, title, condition, price range, description, confidence, model/version, and persists the suggestion.
- [ ] Rejects missing listing, non-owner listing, non-`DRAFT` listing, and listing with no READY images.
- [ ] Enforces the 5-per-hour per-listing trigger limit.
- [ ] Appends `WARNING_PRICE_OUT_OF_RANGE` when AI range falls outside the comparable ±20% band.
- [ ] Does not add a price warning when no comparable listings exist.
- [ ] Returns fallback/manual-entry payload for AI timeout, gateway error, and open circuit.
- [ ] Persists `ai_assisted=true` only after a completed AI response.
- [ ] Persists one feedback row for each accepted/edited/rejected field.
- [ ] Rejects feedback for a suggestion belonging to another listing or seller.
- [ ] Preserves listing state when recording suggestion feedback.

### Backend Integration/Contract Tests

- [ ] `POST /ai-suggestions` happy path with a mocked AI Gateway and Testcontainers PostgreSQL.
- [ ] AI Gateway 5xx/timeout returns HTTP 200 degraded advisory response and persists fallback status.
- [ ] `GET /ai-suggestions` returns the latest attempt and returns `AI_SUGGESTION_NOT_FOUND` when none exists.
- [ ] Feedback endpoint validates field/action values and standard error envelope.
- [ ] Internal AI request/response JSON contract matches the Python Pydantic models, including `mediaIds` and model metadata.
- [ ] Seller ownership prevents IDOR access to another seller’s listing/suggestion.

### AI Service Tests (`pytest`)

- [ ] Internal API key is required.
- [ ] Valid media IDs produce the expected response contract.
- [ ] Low identification confidence produces `WARNING_UNABLE_TO_IDENTIFY` and no title/description.
- [ ] Multiple items produce `MULTIPLE_ITEMS_DETECTED`.
- [ ] Insufficient comparables produce low-confidence/no precise range behavior.
- [ ] Text hint is bounded at 500 characters.
- [ ] Model name/version and inference ID are present in every successful response.
- [ ] Image/media access failure and model timeout produce the contract expected by the backend fallback path.

## 6. Validation Checklist

- [ ] Category suggestion comes from the predefined category taxonomy.
- [ ] Title is never persisted above 100 characters.
- [ ] Description is never persisted above 2,000 characters.
- [ ] Condition is constrained to `NEW`, `LIKE_NEW`, `GOOD`, `FAIR`, or `POOR`.
- [ ] Price range is checked against similar listings using the 20% rule.
- [ ] AI remains advisory; manual entry works without a successful AI response.
- [ ] Seller can independently accept, edit, or reject every suggested field through feedback records and the existing listing update path.
- [ ] Low-confidence, multiple-item, unique-item, and wrong-category cases remain recoverable without blocking draft creation.
- [ ] AI timeout/failure returns `ERROR_AI_SERVICE_UNAVAILABLE` guidance and leaves the draft manually editable.
- [ ] AI Gateway is internal-only and authenticated.
- [ ] Media access uses `mediaIds` and short-lived authorization; no raw provider URL or signed URL is persisted/logged.
- [ ] Listing ownership is derived from the authenticated security context.
- [ ] Suggestion and feedback records retain model/version/inference/latency metadata for observability.
- [ ] No direct Python write path exists to `listings`.
- [ ] `valuex-mobile` remains unchanged.
- [ ] Checkstyle, full tests, coverage, and SonarQube checks pass before push.

## 7. Open Gaps / Questions

1. **AI repository is not implemented yet.** `valuex-ai` currently contains only `README.md`; the exact provider SDK, media client, model hosting, and Python package layout are not established in the repository. Implement against the LLD’s endpoint/schema boundary and record the selected provider/layout in the LLD.
2. **Exact AI model/provider is intentionally unspecified.** The LLD permits a managed multimodal API or self-hosted/provider-neutral implementation. This decision must be made during implementation without changing the internal contract.
3. **Comparable-listing access from Python is not operationally specified.** The LLD describes a read-only PostgreSQL query, but connection ownership/credentials and whether the query should instead be exposed through a backend service are not defined. Do not grant broader database access without a security decision.
4. **Media completion/derivative timing.** US-004 currently exposes media lifecycle/API foundations; asynchronous AVIF/WebP worker processing is a documented follow-up. US-005 must consume only media assets that the Media Module reports as READY.
5. **Listing update endpoint implementation.** The LLD references the existing `PATCH /api/v1/listings/{id}` path for applying final seller values, but the US-004 backend slice does not implement full listing metadata editing. Confirm whether US-005 should add the minimum draft-field update path or defer final-value application to US-010.
6. **Flyway version.** Replace `V{N}` with the next available migration version at implementation time.

---

**Status:** Draft
