# US-005: AI-Assisted Listing Creation — Implementation Plan

> **Revised (2026-10-28, category taxonomy):** US-006 is implemented (`V16`, taxonomy module, `GET /categories/{code}/listing-schema`), so this plan now classifies to an enabled L3 category code in one stage, stores suggestions with category codes, and prefills only attributes the Metadata Dictionary marks AI-extractable, validated against the category's listing schema. The AI on/off switch stays `valuex.ai.enabled` until US-121. Photo retention and limits are defined in section 4 (Backend, AI boundary). The migration is `V17`. Price suggestion stays on hold; when it returns, comparables join on `listings.category_id`.

> **Added (2026-10-28, AI cost optimization):** vision models identify the item and capture category-specific metadata through a configurable cheapest-to-most-expensive model cascade with bounded retries; the seller uploads 2 to 10 photos of one object from different angles. See section 3 (AI cost optimization strategy) and LLD Part B §6.5. Decided the same day: `valuex-ai` is now built in this story, the whole call has a hard limit of 20 seconds, the story is 13 SP, the four tiers are chosen (section 3), and AI tries to fill every attribute it can determine for the detected L3 category, plus the subjective text fields.

> **Added (2026-10-28, image preparation):** the models do not receive every uploaded photo at camera resolution. `valuex-ai` first checks quality, removes near-duplicates, resizes, and selects the best 3 to 5 views; the original photos stay untouched in R2 for the listing. See section 3 (cost strategy, item 1) and LLD Part B §6.5.6.

## 1. Header

| Field | Value |
|---|---|
| Story ID | US-005 |
| Title | AI-Assisted Listing Creation |
| Sprint | Sprint 2 — Seller Listing Creation |
| Story Points | 13 (re-estimated from 8 on 2026-10-28 because `valuex-ai` and the internal endpoints joined the story; agreed by the product owner) |
| Repos | valuex-backend, valuex-mobile (only the Submit to AI wiring and unavailable message), valuex-ai (the listing suggestion endpoint and the model cascade; in scope since 2026-10-28) |
| Dependency | US-004 — Create Listing with Photo Capture; draft must be `DRAFT` with at least one READY listing media asset. US-089 (listing states), US-114 (Item Details page, `AiSuggestion` model, feedback call) and US-006 (taxonomy, listing schema) are already built |

Sprint 2 goal: allow sellers to create and publish listings. US-005 provides advisory metadata suggestions for the US-004 draft flow and must never prevent manual listing creation.

**Scope decisions (2026-10-15):**
1. ~~The AI service is developed separately and arrives later.~~ **Changed 2026-10-28: `valuex-ai` is built in this story.** This plan delivers the backend side of the boundary (persistence, the three seller endpoints, the AI Gateway client against the LLD §6.2 contract, fallback/resilience, feedback capture, and the internal endpoints the AI service calls) and the AI service itself (the `/ai/v1/listings/suggest` endpoint and the model cascade). Price estimation stays on hold. Until real provider keys are available the service is run and tested against a fake model server, and `valuex.ai.enabled` stays `false` by default.
2. **Every Sprint 2 story assumes AI is disabled or down and works manually.** A single configuration switch, `valuex.ai.enabled` (default `false`), turns AI assistance on or off. When off, nothing calls the AI service, nothing fails, and the seller fills in item details, category and description by hand. When on, the AI fills those fields and the seller reviews them.
3. **Price suggestion is on hold** (still in design discussion). It is removed from this story's implementation until the design is settled: no price range in the persisted suggestion, no price feedback field, no price re-validation, no price warnings.
4. **Unavailable message.** When the seller taps **Submit to AI** and AI is disabled, down, or its usage quota is exhausted, the app shows: "AI Service is not available at this moment or your usage quota has exhausted, please do manual entry". The backend sends the same text as the degraded response `message` (error code `ERROR_AI_SERVICE_UNAVAILABLE`); a quota-exhausted or HTTP 429 reply from the AI Gateway is treated like any other unavailable result.
5. **Cost strategy (2026-10-28).** The AI service uses 3 to 4 vision models in a cheapest-first cascade, driven only by configuration (see the AI cost optimization strategy below). The backend side of this story changes the contract, the gateway timeout and retry, persistence of the tier attempts, the 2 to 10 photo rule and adds the internal endpoints; `valuex-ai` implements the cascade.

## 2. Story Recap

**As a** seller **I want** AI to suggest item details from my photos **so that** I can create listings faster with accurate information.

**Acceptance Criteria** (`Documents/user-stories.md`):
- Given uploaded item photos, AI suggests the category (an enabled L3 code from the taxonomy) and then, for that category, tries to fill every field of its schema that can be determined from the photos, required and optional (including "More details"). It also writes the subjective fields: title, description, condition and condition notes. (Price range is on hold, see Scope decisions.)
- Seller can accept, edit, or reject each suggestion independently.
- Seller can manually enter any field.
- Added by scope decision: with AI disabled or unavailable, the seller completes every field manually and nothing fails.

**Edge Cases:** AI cannot identify item · wrong category · multiple items in photos · AI disabled · AI timeout/failure. (Unrealistic price and unique/rare item without comparables are deferred with price suggestion.)

**Validation Rules:** suggestions optional/manual entry always allowed · category must be an enabled L3 in the taxonomy · attribute keys must belong to that category's schema and be AI-extractable · title max 100 characters · description max 2000 characters · condition notes max 1000 characters. (The 20% price rule is deferred with price suggestion.)

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
- **Taxonomy-aware (US-006, [LLD Part B update](../LLD/Sprint-2-Seller%20Listing%20Creation-LLD.md#part-b---us-005-ai-assisted-listing-creation)).** The AI returns `categoryCode` values, never free text. The backend checks each code with `CategoryService` (enabled L3 only) and drops the rest with `WARNING_UNABLE_TO_IDENTIFY`. Attribute suggestions cover every field of the category's schema that the Metadata Dictionary marks AI-extractable (`YES`, or `LIMITED` with a "please verify" flag), required and optional alike, including the "More details" fields; a model returns nothing for a field it cannot see rather than guessing. Fields marked `NO` are not attempted: they are facts only the seller knows (for example purchase date, ownership, invoice, IMEI, legal status, repair history). Where a `NO` field is in fact visible in a photo, the dictionary is corrected through a reviewed override (see Backend — Taxonomy: AI-extractable Corrections) and the AI then attempts it with a "please verify" flag. Facts that are not visible in a photo are never attempted. The backend keeps only keys that are in `ListingSchemaService.schemaForCode(code)` and valid for `AttributeValidator`. The subjective fields (title, description, condition, condition notes, and `item_type_free_text` for "Other ..." categories) are written by the AI from what it sees. Low confidence, AI off, down or no valid category means manual entry including the category (the seller picks an "Other ..." category when nothing fits).
- **Seller photos and the Vision service.** The seller uploads 2 to 10 photos (existing US-004 rule), all of the same object from different angles. Only READY media IDs cross the boundary, all of them in display order, each as a short-lived read authorization. The AI service then selects the best 3 to 5 views and sends only resized copies to the models; the originals stay in R2. the AI side must not keep or train on them (contract term with each provider). The backend persists no image bytes or URLs.
- AI service endpoint is internal-only: `POST /ai/v1/listings/suggest` through the AI Gateway.
- Listing images are passed across the AI boundary as `mediaIds`; the Media Module issues short-lived authorized reads. No provider URLs or signed URLs are persisted as business data.
- AI failures return an HTTP 200 degraded advisory payload with manual entry available; the circuit breaker, a 20-second hard time limit (the cascade makes several model calls) and a small bounded retry protect the backend.
- AI suggestions and per-field feedback are append-oriented records for later quality/retraining analysis.
- **Master AI switch.** `valuex.ai.enabled` (env `VALUEX_AI_ENABLED`, default `false`) is checked by `ListingAiService` before any AI call. Disabled: no gateway call, no suggestion row persisted, the rate limit is not consumed, and the endpoint returns the same HTTP 200 degraded payload (`fallback: true`, manual-entry message). Enabled but the service is down, slow or its circuit is open: the call falls back the same way and a `FAILED` row is persisted. The switch is a shared `AiProperties` in `common.infrastructure.ai` so later Sprint 2 stories reuse it. The LLD §6.2 request/response JSON (minus price) is the contract between the backend and `valuex-ai`.
- **Manual fallbacks for the other AI-using Sprint 2 stories (decided 2026-10-15/16; implemented in their own plans, see [US-007](US-007-Implementation-Plan.md) and [US-084](US-084-Implementation-Plan.md); this story only provides the shared `valuex.ai.enabled` switch):**
  - **US-007 Restricted Items:** when AI is disabled or unavailable, a rule-based check against a `restricted_items` table of terms runs on title, description and category, and a match is treated as an AI `RESTRICTED` result.
  - **US-084 Trust & Safety Review:** when AI is disabled or unavailable, no fraud score is computed. Until the admin console arrives the listing is auto-approved (recorded as such); manual moderation is switched on later by configuration.

**AI cost optimization strategy (model cascade).** Detailed design: [LLD Part B §6.5](../LLD/Sprint-2-Seller%20Listing%20Creation-LLD.md#65-model-cascade-cost-optimization). Specified here and built in `valuex-ai` by this story; the backend only consumes the result.
1. **Photos.** 2 to 10 photos of the same object from different angles are prepared once per request, and only a few resized views reach the models (never one call per photo). Steps: (a) quality check, where images that are too blurry, too dark or too bright are set aside; (b) near-duplicate removal by perceptual hash, keeping the sharpest of each group; (c) resize to a long side of 1024 px as JPEG without metadata (never enlarged); (d) selection and ranking of the best 3 to 5 views, with the cover photo first when it passes the quality check and then the views most different from those already chosen. Tier 1 receives the top 3 views, tier 2 the top 4 and tiers 3 and 4 the top 5 of the same ranking, so escalation needs no new preparation. The original photos stay untouched in object storage (R2) for the listing; the AI service only reads them through short-lived links and keeps the resized copies in memory for the request. Each model attempt is one call that returns the category, condition and a draft title and description. A second call (item 4) then fills the category's attributes and writes the final title, description and condition notes. Photos that show different objects raise `MULTIPLE_ITEMS_DETECTED`.
2. **Tiers.** An ordered list of 3 to 4 tiers, cheapest first. Each tier names a provider, a model id, an accept-confidence threshold, an image cap, a timeout and a max output size, plus optional unit prices for cost metrics. Chosen on 2026-10-28:

   | Tier | Provider | Model |
   |---|---|---|
   | 1 | OpenAI | GPT-6 Luna |
   | 2 | Google | Gemini 3.1 Flash-Lite |
   | 3 | OpenAI | GPT-6.1 Sol |
   | 4 | Google (confirmed) | Gemini 3.1 Pro |

   The exact API model ids and the Google connection path are confirmed in Open Gap 22.
3. **Escalation.** Run tier 1. Accept its result when the output is valid, the category is an enabled L3 and the category confidence is at least the tier's threshold. Otherwise run the next tier on the same photos. The last tier's result is returned whatever its confidence, with `WARNING_UNABLE_TO_IDENTIFY` when it is below the minimum identification confidence. A tier whose retries are exhausted also escalates, so a provider outage on one tier does not fail the request. A tier is only started when enough time is left for its own timeout plus the attribute call.
4. **Attributes and subjective fields.** After a category is accepted, one more call by the accepting tier's model receives the photos and every AI-extractable field of that category (required and optional, from the internal `ai-fields` endpoint). It returns a value and a confidence for each field it can determine, nothing for the rest, and writes the final title (built from the key attributes such as brand and model where known, at most 100 characters), description (at most 2000), condition and condition notes (at most 1000). Values below the per-field confidence are dropped. There is no further escalation for this call. If too little time remains, it is skipped and the draft title and description from the first call are returned without attributes.
5. **Configurable providers.** Providers and tiers live in configuration (provider type, base URL, secret name, model id per tier). Swapping a model, a provider, the order or the thresholds is a configuration change and a restart, not a code change. A provider that speaks the OpenAI-compatible protocol needs configuration only; a provider with a different protocol needs one adapter class once, then configuration. The service refuses to start on an invalid tier list.
6. **Retry.** Per model call: up to 3 attempts, exponential backoff with jitter (300 ms start, doubling, capped at 2 s), on timeout, connection error, HTTP 429 (honouring `Retry-After`, capped), HTTP 5xx and an unparseable structured answer (once). No retry on HTTP 400, 401, 403 or a content-policy refusal. When attempts run out the cascade moves to the next tier. An overall deadline (default 17 s, which includes the attribute call) stops new attempts and tiers from starting, so the backend's 20 s hard limit is never reached by a running cascade. The backend retries the gateway call at most once, and only when the connection failed or the gateway answered 502 or 503 before doing any work; never after a read timeout, so one seller action cannot pay for two cascades.
7. **Other cost controls.** The taxonomy list is a cacheable prompt prefix; output size is capped per tier; the existing limit of 5 generations per listing per hour stays; metrics track tokens and estimated cost per tier, the share of requests accepted at each tier, escalation rate and retry count.
8. **Persisted record.** Each suggestion stores `tier_attempts` (tier, model, outcome, confidence, attempts, images sent, latency, tokens) for cost and quality analysis. Provider and model names are not returned to the mobile app.
9. **Tuning from real data (after go-live).** Thresholds start strict (accept 0.85 / 0.80 / 0.75) and are loosened from evidence. Evidence comes from two sources: (a) the persisted `tier_attempts` joined with the seller feedback rows, which show how often sellers keep each tier's answer by confidence band; and (b) an optional shadow comparison, off by default, where a small share of requests also runs a stronger reference tier in the background after the seller has already received the answer, and only agreement counts are recorded as metrics (no seller impact, no stored photos or answers). The queries are documented in LLD §11.1 and in the testing guide.

## 4. Implementation Steps

### Database Migration — `valuex-backend`
- [ ] Add the US-005 migration as `V17__listing_ai_suggestions.sql` (the highest on `main` is `V16__taxonomy_and_listing_attributes.sql`; recheck `db/migration` at implementation time).
- [ ] Add `listing_ai_suggestions` with status (`PENDING`, `COMPLETED`, `FAILED`, `TIMEOUT`), `category_suggestions` JSONB (`[{categoryCode, categoryPath, confidence}]`), `attribute_suggestions` JSONB (`[{key, value, confidence, verify}]`), title, condition, description, `condition_notes_suggestion` text, warnings, confidence, model name/version (of the accepting tier), `tier_attempts` JSONB (see the cost strategy), inference ID, latency, fallback flag, and timestamp. No price columns; they are added by a later migration once the price design is agreed.
- [ ] Add `listing_ai_suggestion_feedback` with suggestion ID, field (`CATEGORY`, `TITLE`, `CONDITION`, `CONDITION_NOTES`, `DESCRIPTION`, `ATTRIBUTE`), nullable `attribute_key` (required when field is `ATTRIBUTE`), action (`ACCEPTED`, `EDITED`, `REJECTED`), original/final values, and timestamp.
- [ ] Do not add `listings.ai_assisted`; it already exists (`V10__listing_media_schema.sql`, `Listing.aiAssisted`).
- [ ] Add indexes on suggestion listing/status and feedback suggestion ID.
- [ ] Keep the migration compatible with the US-004 `listings` and media-ID model; do not introduce raw image URL columns.

### Backend — Domain, Persistence, DTOs
- [ ] Add `ListingAiSuggestion`, `ListingAiSuggestionFeedback`, `ListingAiSuggestionStatus`, `ListingAiFeedbackField`, and `ListingAiFeedbackAction` under the existing listing module layers (`domain`, `application`, `api`, `infrastructure/persistence`).
- [ ] Add repositories for latest suggestion lookup, per-listing hourly trigger count, and feedback persistence.
- [ ] Add response DTOs: `ListingAiSuggestionResponse` (including `conditionNotesSuggestion`), `CategorySuggestionDto` (`categoryCode`, `categoryPath`, `confidence`), `AttributeSuggestionDto` (`key`, `value`, `confidence`, `verify`), and `SuggestionFeedbackRequest` (item has optional `attributeKey`).
- [ ] Add internal AI transport models using `mediaIds`, listing ID, seller ID, seller location, and optional text hint; map AI response model/version/inference metadata without exposing provider internals.

### Backend — AI Switch and Gateway Client (no AI logic)
- [ ] Add `AiProperties` (`valuex.ai.enabled` default `false`, `min-confidence` (see Open Gap 10), `gateway.base-url`, `gateway.api-key` from environment, `gateway.timeout-seconds` default 20, `gateway.retry.max-attempts` default 2, `gateway.retry.backoff-millis` default 500) in `common.infrastructure.ai`, bound through `ValuexProperties` (new `ai` section next to `listing` and `taxonomy`); add the keys to `application.yml`. Base URL and API key are not required while `enabled=false`. The provider and tier configuration belongs to the AI service, not the backend. US-121 later replaces the switch and threshold with Admin settings.
- [ ] Add `AiGatewayClient` in `common.infrastructure.ai` using `RestClient` (as in `GoogleAddressVerificationAdapter`) to call `POST /ai/v1/listings/suggest` with `X-Internal-Api-Key`, READY media IDs and optional `textHint` (max 500 characters). `ListingSuggestRequest` / `ListingSuggestResponse` records follow LLD §6.2 (the standard AI response envelope with the suggestions inside `result`, decided 2026-10-28; without the price range; the envelope also carries `tierAttempts`), plus `ListingSuggestResponse.unavailable()`.
- [ ] Add `io.github.resilience4j:resilience4j-spring-boot3` (plus `spring-boot-starter-aop`, which its annotations need) to `pom.xml`, and configure the `aiGateway` circuit breaker per the LLD (sliding window 20, failure threshold 50%, 30s open) with a 20-second read timeout and a 2-second connect timeout on the `RestClient` (the cascade may call several models). Wrap `AiGatewayClient.suggestListing` with `@CircuitBreaker(name = "aiGateway")` and a fallback returning `unavailable()`.
- [ ] Add a `@Retry(name = "aiGateway")` outside the circuit breaker: 2 attempts, 500 ms backoff, retrying only connection failures and HTTP 502 or 503; never a read timeout or a 4xx.
- [ ] Map timeout, HTTP error, malformed body and open circuit to `unavailable()`.
- [ ] Verify the client with a mocked HTTP server, and run one local end-to-end check against `valuex-ai` using the fake model server (no vendor keys).
- [ ] Log inference IDs and listing ID in structured logs without signed URLs, image bytes, credentials, or PII.

### Backend — Internal Endpoints for the AI Service
The AI service must not touch backend tables or the public API, so it reads what it needs through internal-only endpoints (decided 2026-10-28).
- [ ] Add `InternalApiKeyFilter` and a separate `SecurityFilterChain` for `/internal/v1/**`, ordered before the JWT chain: no JWT, requires `X-Internal-Api-Key` (constant-time comparison; key from env `VALUEX_INTERNAL_API_KEY`, a different key from the one the backend sends to the gateway). A missing or wrong key gives 401. The path is also blocked at the public ingress.
- [ ] `GET /internal/v1/taxonomy/snapshot`: enabled L3 categories (code, name, L1 and L2 path, marketplace status) with `version` set to the checksum of the last successful `taxonomy_import_log` row; supports `ETag` / `If-None-Match` (304).
- [ ] `GET /internal/v1/taxonomy/categories/{code}/ai-fields`: the category's fields that are AI-extractable, required and optional alike (key, label, type, unit, option codes, validation, `aiExtractable` YES or LIMITED), read through a small lookup of `attribute_definitions.ai_extractable` in the taxonomy module. The public listing-schema API is unchanged. This closes Open Gap 11.
- [ ] `POST /internal/v1/media/read-access` with `listingId` and `mediaIds`: checks that every ID is a READY photo attached to that listing and returns short-lived download URLs from `ObjectStoragePort.createDownloadAuthorization`; nothing is stored.
- [ ] Tests: key required; the snapshot leaves out disabled and Prohibited categories; ETag returns 304; `ai-fields` returns only AI-prefill fields with LIMITED marked; read-access refuses media of another listing or not READY.

### Backend — Taxonomy: AI-extractable Corrections
The dictionary flag `ai_extractable` (YES, LIMITED, NO) is the single control for what the AI attempts. Fields marked `NO` stay manual because only the seller knows them (decided 2026-10-28), but a field that is visible in a photo and wrongly marked `NO` should be attempted.
- [ ] Review every attribute marked `NO` in `ValueX_JustQlic_Master_Metadata_Dictionary.csv` (column "AI Extractable (MVP)") and list those whose value can be read from the photos, for example colour, material, visible damage, size or model markings, and visible accessories. The product owner approves the list. Knowledge-only facts stay `NO`: purchase date or year, purchase price, ownership count, invoice, warranty dates, serial number and IMEI, repair history, battery health unless shown, and legal status.
- [ ] Add `taxonomy/overrides/ai-extractable-overrides.csv` (`attribute_key`, `ai_extractable`, `reason`) with the approved changes, set to `LIMITED` so values carry "please verify" (`YES` only if the owner decides so). The master CSV stays as supplied.
- [ ] Extend the importer to read this file like the other override files: check that each key exists and the value is `YES`, `LIMITED` or `NO`, apply it to `attribute_definitions.ai_extractable`, include it in the checksum, keep the import idempotent and all-or-nothing, and record the decision in `Category_Taxonomy_Review_Drafts.md`.
- [ ] The internal `ai-fields` endpoint and `valuex-ai` pick up corrected flags with no further change. A later correction is an edit of the override file; US-121 can move it to Admin.
- [ ] Tests: the override is applied and shows in `ai-fields` as `LIMITED`; an unknown key or an invalid value fails the whole import; a second run changes nothing; the checksum changes when the file changes; a knowledge-only `NO` field stays excluded.

### Backend — `ListingAiService`
- [ ] Validate authenticated seller ownership, listing status `DRAFT`, and at least 2 READY listing photos (`ERROR_MIN_PHOTOS_REQUIRED`, the existing US-004 code).
- [ ] If `valuex.ai.enabled=false`, return the degraded manual-entry response immediately: no gateway call, no row persisted, no rate-limit consumption, `ai_assisted` stays false.
- [ ] Enforce the LLD trigger limit of 5 generations per listing per hour with `AI_SUGGESTION_RATE_LIMITED`.
- [ ] If the call fails, times out or the circuit is open, persist a `FAILED`/fallback suggestion and return the same degraded response.
- [ ] Persist completed suggestions with warnings, confidence, model/version, `tier_attempts`, inference ID, latency, and `ai_assisted=true`; persist `tier_attempts` on `FAILED` rows too when the gateway returned them.
- [ ] Truncate title to 100, description to 2000 and condition notes to 1000 characters, and accept only valid condition values, before persistence.
- [ ] Validate suggested categories with `CategoryService` (enabled L3 only; invalid ones dropped, `WARNING_UNABLE_TO_IDENTIFY` when none remain) and treat a top category below `min-confidence` as no category.
- [ ] Filter suggested attributes against `ListingSchemaService.schemaForCode(topCategory)`: keep only schema keys that are AI-extractable (required and optional, any section), validate each value with the existing `AttributeValidator` (a value that fails is dropped on its own, the others stay), mark `LIMITED` ones `verify=true`, and drop the rest. Attribute suggestions are returned only with a valid category.
- [ ] Ensure low-confidence/unclear and multiple-item cases remain successful advisory responses, not hard failures.
- [ ] Record accept/edit/reject feedback per field and verify the suggestion belongs to the requested listing and authenticated seller.
- [ ] Keep suggestion feedback separate from applying final values; final seller values continue through the existing listing update flow (`PATCH /api/v1/listings/{listingId}` and `PUT .../category`).
- [ ] Source the media IDs from `listing_images` (READY assets only, all 2 to 10, in display order); the AI service prepares them and sends only the best 3 to 5 resized views.

### Backend — API
- [ ] Add `ListingAiController` with seller authorization and ownership checks:
  - `POST /api/v1/listings/{listingId}/ai-suggestions`
  - `GET /api/v1/listings/{listingId}/ai-suggestions`
  - `PATCH /api/v1/listings/{listingId}/ai-suggestions/{suggestionId}/feedback`
- [ ] Use the standard `ApiResponse` envelope and existing centralized exception handling.
- [ ] Return `LISTING_NOT_FOUND`, `ERROR_MIN_PHOTOS_REQUIRED`, `LISTING_NOT_IN_DRAFT`, `AI_SUGGESTION_RATE_LIMITED`, and `AI_SUGGESTION_NOT_FOUND` according to the LLD (`ERROR_MIN_PHOTOS_REQUIRED` replaces `LISTING_HAS_NO_IMAGES` now that 2 photos are the minimum).
- [ ] Keep AI disabled, AI unavailable, unable-to-identify and multiple-item cases in successful advisory payloads.

### AI Service — `valuex-ai` (IN SCOPE since 2026-10-28)
The repository holds only a README today. Build only what this story needs, following CODING_STANDARDS §5; design in LLD Part B §6 and §6.5. Price estimation is on hold.
- [ ] Project skeleton: `pyproject.toml` (Ruff, pytest), `requirements.txt`, `Dockerfile`, `tests/`, `app/main.py`, `app/routers/listing.py`, `app/services/listing_service.py`, `app/models/`, `app/core/` (`config.py`, `security.py`, `logging.py`, `exceptions.py`), a `config/ai.example.yaml` with placeholder providers and tiers, and the README updated with how to run and configure it.
- [ ] `POST /ai/v1/listings/suggest` (internal API key, Pydantic v2 request with 2 to 10 `mediaIds`, optional `textHint` max 500 characters) returning the LLD §6.2 response (standard envelope: `inferenceId`, `modelName`, `modelVersion`, `result`, `confidenceScore`, `warnings`, plus `tierAttempts`); type hints everywhere; async I/O.
- [ ] Settings: provider and tier configuration loaded from configuration and validated at startup (1 to 4 tiers, known providers, secrets present, thresholds and image caps in range); the service refuses to start on an invalid list.
- [ ] Backend client (`app/clients/backend_client.py`): taxonomy snapshot (cached by version, refreshed with `If-None-Match`), `ai-fields` per category (cached by code and version), media read-access, all with the internal API key.
- [ ] `app/services/vision/`: `VisionModelProvider` protocol and error types, the `openai_compatible` adapter, the provider registry, `call_with_retry` (backoff with jitter, `Retry-After` cap, transient or permanent errors), `images/` (fetch from the signed URLs in parallel, decode JPEG, PNG and HEIC, quality check, near-duplicate removal by perceptual hash, resize to JPEG without metadata, ranked selection of the best 3 to 5 views; all CPU work runs off the event loop and counts against the deadline), `run_cascade` and the accept rule (including the time reserve for the attribute call), and the attribute and text call.
- [ ] Image preparation settings in the configuration (fetch and preparation timeouts, `max_side_px`, JPEG quality, sharpness and brightness limits, duplicate distance, minimum and maximum views) with the starting values in LLD §6.5.2. Proposed libraries: Pillow, NumPy and `pillow-heif` (US-004 accepts HEIC photos, which Pillow cannot read alone); no OpenCV. The service never modifies, copies or deletes the originals and never writes the resized copies to disk or object storage. If every image fails the quality check the best two are still sent with `WARNING_IMAGE_UNCLEAR`; an image that cannot be fetched or decoded is skipped, and if none is usable the service returns unavailable.
- [ ] Initial configuration in `config/ai.example.yaml` with the four tiers from section 3 (provider connections `openai` and `google`, secrets from environment variables, no keys in the repository). OpenAI uses the `openai_compatible` adapter. Google uses it too if Google's OpenAI-compatible endpoint supports image input and structured JSON output for the chosen models; if not, add one `google_genai` adapter (Open Gap 22).
- [ ] Prompts: system prompt kept in the service; the taxonomy list as a stable prefix; for the attribute and text call, the category's field list with types, units and option codes, an instruction to return nothing for a field that is not visible (no guessing), and the response JSON schema; the seller's `textHint` passed only as quoted, length-capped data; the model's JSON answer validated (category must be in the snapshot, title at most 100, description at most 2000 and condition notes at most 1000 characters, condition in the allowed set, attribute values typed per `ai-fields` and options by code); no seller-controlled instructions reach the system prompt.
- [ ] Warnings `MULTIPLE_ITEMS_DETECTED`, `WARNING_UNABLE_TO_IDENTIFY` and `WARNING_IMAGE_UNCLEAR`; attribute suggestions only for the accepted category and only above `field_min_confidence`; fields marked `NO` in the dictionary and non-visible or legal facts are never requested.
- [ ] Optional shadow comparison (LLD §6.5.8), off by default: for a configured share of requests served by a tier below the reference tier, run the reference tier in the background after the response is sent, compare the category code and the attribute values, and emit only metrics and structured log counts (`ai_listing_shadow_*`). It never changes the seller's response, is capped per hour, uses the same prepared in-memory views, stores nothing, and counts its tokens in the cost metrics.
- [ ] Structured logs per CODING_STANDARDS §5.8 and the tier metrics in LLD §11; never log images, signed URLs, keys or prompts with seller text.
- [ ] Model access is real HTTP to the configured providers; in tests and local runs a fake OpenAI-compatible server stands in. Choosing the real providers and models is Open Gap 16.
- [ ] Set `VALUEX_AI_ENABLED=true` in a local environment, point the backend at the service and run one end-to-end check against the fake model server.

### Mobile (Flutter)
Only the **Submit to AI** wiring in `valuex-mobile/lib/features/listing`. US-114 already built the Item Details page, `AiSuggestion` (`asDraft`), `ItemDetailsArgs.suggestion`, `suggestionFeedback()` and `sendSuggestionFeedback`; this story feeds them.
- [ ] Add a `ListingRepository` method for `POST /api/v1/listings/{listingId}/ai-suggestions` and call it from `_submit` in `create_listing_screen.dart` after `submitDraft` succeeds, before opening Item Details.
- [ ] When the response is the degraded one (`fallback: true`) or the call fails, show the message "AI Service is not available at this moment or your usage quota has exhausted, please do manual entry" and continue to manual entry.
- [ ] Add the message as an l10n string in `app_en.arb` and `app_hi.arb` (Hindi translation to be confirmed) and map `ERROR_AI_SERVICE_UNAVAILABLE` in `listing_error_messages.dart`.
- [ ] The call can take up to the backend's 20 s limit: raise the receive timeout for this one request to 25 s, show a busy state with an "Analysing your photos" message (English and Hindi) while waiting, and keep the button disabled so a second tap cannot start a second cascade.
- [ ] When a real suggestion comes back, parse it into `AiSuggestion` (category code, title, condition, condition notes, description; attribute suggestions with `verify` flags) and pass it as `ItemDetailsArgs.suggestion` so the existing page prefills. Extend `AiSuggestion.asDraft` to carry condition notes and the attribute values (required and optional, including "More details", which should open when AI filled something there), and extend `suggestionFeedback()` with `CONDITION_NOTES` and `ATTRIBUTE` (with key).
- [ ] Mark fields the AI flagged `verify` with a small "Please verify" hint (English and Hindi, tokens only, not colour alone), and keep the existing "AI filled these from your photos" banner. The seller can edit or clear any filled field.
- [ ] Follow `Documents/CODING_STANDARDS.md` and the design system (`valuex-mobile/docs/Flutter-Design-System.md`): tokens only, 48 dp tap targets, labelled controls.

### Documentation/Quality
- [ ] Add/update OpenAPI examples for the three backend endpoints.
- [ ] Document the tuning queries (LLD §11.1: seller keep-rate by tier and confidence band, escalation and cost by tier, correction rate per field) and run each against the test database to confirm they work with the real column and JSON key names.
- [ ] Update the Sprint 2 LLD Part B for the cost strategy (done 2026-10-28: §6.5 and the sections it touches); after implementation, update it again if the build deviates (e.g. the `valuex.ai.enabled` switch, price suggestion removed, RestClient instead of WebClient, package layout).
- [ ] After implementation, create `Documents/Manual Testing Guides/US-005-Testing-Guide.md` with manual/API test steps and a "Tuning from real data" section holding the queries from LLD §11.1.

## 5. Test Plan

Target >90% coverage for new backend/AI service logic, consistent with `CLAUDE.md`.

### Backend Unit Tests

- [ ] Happy path (AI enabled, mocked client) returns category, title, condition, description, confidence, model/version, and persists the suggestion.
- [ ] AI disabled: no gateway call, no row persisted, rate limit untouched, degraded manual-entry response returned, `ai_assisted` unchanged.
- [ ] Rejects missing listing, non-owner listing, non-`DRAFT` listing, and a listing with fewer than 2 READY photos (also when AI is disabled).
- [ ] All READY photos (2 to 10, display order) are sent; a listing with 10 photos sends 10.
- [ ] Gateway retry: a connection failure or 503 is retried once and succeeds; a second failure falls back; a read timeout and a 4xx are not retried; the cascade is never started twice.
- [ ] `tier_attempts` from the response are persisted on `COMPLETED` rows (and on `FAILED` rows when returned).
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

Built in this story with `pytest` (CODING_STANDARDS §5.9; model calls and the backend client are mocked). Every router test covers success, invalid input (fewer than 2 or more than 10 `mediaIds`, over-long `textHint`) and the internal-error fallback. These are also the acceptance tests for the cascade (LLD §13.3), and the backend tests below cover how the backend handles each AI outcome:
- [ ] Cascade: tier 1 accepted at or above its threshold (tiers 2 to 4 not called); below it escalates; the last tier's result is returned with `WARNING_UNABLE_TO_IDENTIFY` when still low; at most one pass per tier.
- [ ] Retry: timeout, connection error, 429 (with `Retry-After`), 5xx and one unparseable answer are retried with backoff up to 3 attempts; 400, 401, 403 and a content-policy refusal are not; exhausted attempts escalate to the next tier; the overall deadline stops new attempts.
- [ ] Configuration: swapping a model, provider, order or threshold changes behaviour with no code change; an invalid tier list (none, more than 4, unknown provider, missing secret) stops startup.
- [ ] Image preparation: a blurry, a dark and a bright image are set aside; near-duplicates collapse to the sharpest one; the cover photo is ranked first when it passes the quality check; selection is diverse and capped at 5; fewer than 3 usable views are topped up from the set-aside ones, and 2 uploaded photos send 2; tier 1 receives 3, tier 2 4 and tiers 3 and 4 5 of the same ranking; resized images have a long side of at most 1024 px, are never enlarged and carry no EXIF or GPS data; HEIC, PNG and JPEG decode; an undecodable or unfetchable image is skipped; all images failing the quality check gives `WARNING_IMAGE_UNCLEAR` with the best two sent; the originals are never modified; preparation honours its timeout.
- [ ] Photos: 2 to 10 accepted, fewer or more rejected; photos of different objects raise `MULTIPLE_ITEMS_DETECTED`.
- [ ] Attribute call: all AI-extractable fields of the category (required, optional and "More details") are requested and none marked `NO`; a field the model leaves empty is not returned; values below `field_min_confidence` are dropped; a tier is not started when its timeout plus the attribute call do not fit, and the attribute call is skipped (draft title and description returned) when too little time remains.
- [ ] Subjective fields: title, description, condition and condition notes are returned within their limits; "Other ..." categories get `item_type_free_text`.
- [ ] Response uses the standard envelope with the suggestions in `result`.
- [ ] Shadow comparison: off by default; when on, only the configured share is sampled and never more than the hourly cap; it runs after the response is sent and a failure or timeout in it does not affect the response; no shadow call when the served tier is already the reference tier; agreement metrics are correct for matching and differing category codes and attributes; nothing from it is stored.
- [ ] Per-tier cost metrics and `tierAttempts` are emitted.
- [ ] AI response with `WARNING_UNABLE_TO_IDENTIFY` and empty category suggestions persists as `COMPLETED`, not `FAILED`.
- [ ] Category codes that are unknown, disabled, not L3 or Prohibited are dropped; with none left the warning is added and attribute suggestions are discarded.
- [ ] Top category below `min-confidence` is treated as no category.
- [ ] Attribute suggestions: keys outside the schema and invalid values are dropped one by one; `LIMITED` ones get `verify=true`; required, optional and "More details" fields are all accepted; condition notes over 1000 characters are truncated.
- [ ] AI response with `MULTIPLE_ITEMS_DETECTED` persists and is returned unchanged.
- [ ] Over-long title (>100) and description (>2000) from the AI are truncated before persistence; unknown condition values are rejected or dropped.
- [ ] Model name/version and inference ID are stored with every completed suggestion.

### Mobile Tests (Flutter)

- [ ] Widget test: tapping **Submit to AI** with a degraded/failed response shows the unavailable message and does not crash or lose the uploaded photos.
- [ ] Repository test: the endpoint call parses both a normal and a degraded response.
- [ ] Widget test: while the request runs the busy message shows and a second tap does nothing; the 25 s receive timeout is set for this call.
- [ ] Widget test: a suggestion with attributes, condition notes and a `verify` flag prefills the form (including "More details"), shows the hint on the flagged field, and the seller can edit or clear each value; feedback includes `CONDITION_NOTES` and `ATTRIBUTE` rows.
- [ ] Message exists in English and Hindi and passes the accessibility guideline checks (tap target, label, contrast).

## 6. Validation Checklist

- [ ] Every stored category suggestion is an enabled L3 code; attribute suggestions exist only for AI-extractable keys of that category's schema (required and optional), with `LIMITED` ones flagged "please verify" and `NO` fields never attempted.
- [ ] Title, description, condition and condition notes are filled by the AI within their limits and can be edited or cleared by the seller.
- [ ] Every attribute marked `NO` has been reviewed; the visible ones are in `ai-extractable-overrides.csv` as `LIMITED`, and knowledge-only facts such as purchase date stay manual.
- [ ] All 2 to 10 READY photo IDs reach the AI service (fewer than 2 gives `ERROR_MIN_PHOTOS_REQUIRED`); the models receive only the best 3 to 5 resized views (long side at most 1024 px, no metadata); the original photos in R2 are unchanged; no image bytes or URLs are persisted.
- [ ] Cascade, retry and provider settings live only in configuration; changing a model or provider needs no code change; tiers are ordered cheapest first and capped at 4.
- [ ] A low-confidence cheap tier escalates, and an exhausted retry also escalates; the whole call stays within the overall deadline.
- [ ] The gateway call is retried at most once and never after a read timeout.
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
- [ ] `valuex-ai` runs from its README instructions, passes `ruff check`, `ruff format --check` and `pytest`, has no vendor key in the repository, and the internal endpoints reject a missing or wrong key.
- [ ] A request never runs longer than 20 s end to end: AI deadline 17 s, backend limit 20 s, app timeout 25 s.
- [ ] Tier thresholds, image preparation limits and the shadow settings are configuration only; the shadow comparison is off by default and cannot change or delay a seller's response; the tuning queries return correct results on test data.
- [ ] Checkstyle, full tests, coverage, and SonarQube checks pass before push.

## 7. Open Gaps / Questions

1. **AI service contract ownership (decided 2026-10-28).** This story builds both sides, so the LLD §6.2 contract is owned here; any change updates the Part B LLD, the gateway client and `valuex-ai` together.
2. **Circuit breaker mechanism (decided).** Add `resilience4j-spring-boot3` and wrap `AiGatewayClient`, as in the Implementation Steps. The same dependency is reused by later AI-calling stories (each with its own breaker instance).
3. ~~**Category data.**~~ **Closed by US-006:** the taxonomy and `listings.category_id` exist; suggestions are validated against enabled L3 categories.
4. **Price suggestion (on hold).** When the design is settled: add price columns, a `PRICE` feedback field, comparable-listings access for the AI team (credentials, or via a backend endpoint) and the ±20% re-validation (LLD §5.7.1, §6.3.1). Not built now.
5. **US-007 and US-084 manual fallbacks (decided).** Details are in their own plans. Nothing further is needed for US-005.
6. **How the app learns AI is off (decided).** The app always shows **Submit to AI** and learns the state from the response and the message above, so no `aiSuggestionsAvailable` flag is added.
7. **Manual entry screen (decided).** [US-114](US-114-Implementation-Plan.md) "Listing Item Details Entry" builds the Flutter Item Details page from the Figma Make screen in the brand theme. After the unavailable message the app opens it with empty fields; with AI on it opens prefilled. This story only needs to hand the suggestion (or none) to that page.
8. **Media completion/derivative timing.** US-004 currently exposes media lifecycle/API foundations; asynchronous AVIF/WebP worker processing is a documented follow-up. US-005 must consume only media assets that the Media Module reports as READY.
9. **Listing update endpoint (decided).** [US-114](US-114-Implementation-Plan.md) adds `PATCH /api/v1/listings/{listingId}` (title, category, condition, description, price, location city) for drafts and listings in revision, and applies the seller's final values; US-010 later extends it to published listings. US-006 extended it with `attributes`, and added `PUT .../category`.
10. **Confidence threshold (decided 2026-10-28).** `valuex.ai.min-confidence` default `0.60` for the category (below it, manual category), until US-121 makes it an Admin setting.
11. ~~**`ai_extractable` LIMITED vs YES.**~~ **Decided:** the internal `ai-fields` endpoint returns the YES or LIMITED value, so the backend can flag "please verify" without changing the public schema API.
12. **Photo limits and retention (updated 2026-10-28).** The count is settled: 2 to 10 photos of one object from different angles, all sent. Still open: the retention term (no retention or training use by the Vision providers) is a contract term with each provider that the code cannot enforce; confirm it is part of provider selection (Open Gap 16).
13. **`ATTRIBUTE` feedback field.** Added so per-attribute accept/edit/reject is captured (an extension of LLD §5.2.3). Confirm, or restrict feedback to the four common fields.
14. **Stale LLD text.** LLD Part B still shows `WebClient`, `categoryId` and price in places; the 2026-10-28 banner and §6.5 mark what they replace, and the rest is cleaned up after implementation.
15. ~~**Who builds the cascade / story points.**~~ **Decided 2026-10-28:** `valuex-ai` is built in this story and the estimate is 13 SP (agreed). Still to do after you approve this plan: update `Sprint-plan.md` and `user-stories.md` to 13 SP.
16. **Tier values (partly decided 2026-10-28).** Providers and models are chosen (section 3). Still open: accept-confidence thresholds, image caps, tier timeouts, output sizes and unit prices. Proposed starting numbers: accept thresholds 0.85 / 0.80 / 0.75 on the first three tiers (stricter than the likely final values, to be loosened from real data), 3 / 4 / 5 / 5 views per tier, tier timeouts 5 / 6 / 7 / 9 s, an attribute call timeout of 6 s, inside the 17 s deadline. They need tuning on a labelled photo set, and unit prices come from the providers' price lists. Photo set: proposed owner is product or QA, who would photograph and label about 100 items with the team (to be confirmed); after go-live the thresholds are tuned from real usage (Open Gap 28). Still needed: confirmation that each provider's terms exclude retention or training on the photos.
17. **Confidence quality (decided 2026-10-28).** The accept rule also requires valid structured output and an enabled L3 code, and thresholds are checked against the labelled photo set before go-live.
18. **Latency target (decided 2026-10-28).** Under 5 s when tier 1 accepts and a hard limit of 20 s (backend limit 20 s, AI deadline 17 s, app timeout 25 s). With 17 s, a request usually reaches at most tier 2 or 3 plus the attribute call, unless earlier tiers fail fast; tier timeouts are sized for that. HLD §12.1 is updated to say so.
19. **Taxonomy and media access for the AI service (decided 2026-10-28).** Internal-only endpoints on the backend (see Backend — Internal Endpoints), protected by the internal API key and cached by the import checksum. The media read-access endpoint is an addition needed for the same reason; it is not in the earlier LLD.
20. ~~**Response shape.**~~ **Decided 2026-10-28:** `valuex-ai` follows the standard AI envelope of CODING_STANDARDS §5.4 (`inferenceId`, `modelName`, `modelVersion`, `result`, `confidenceScore`, `warnings`), with the suggestions inside `result` and one extra top-level field, `tierAttempts`. LLD §6.2 is updated.
21. ~~**Tier 4 provider.**~~ **Confirmed 2026-10-28:** Google (Gemini 3.1 Pro).
22. **Model ids and Google connection.** The model names are used as written (GPT-6 Luna, Gemini 3.1 Flash-Lite, GPT-6.1 Sol, Gemini 3.1 Pro); the exact API model ids must be taken from each provider's documentation and set in configuration. Each model must accept several images and return structured JSON. For Google, the plan assumes its OpenAI-compatible endpoint can do both; if not, one `google_genai` adapter is added (a small amount of extra work inside this story).
23. **How many tiers fit in 20 s.** Each tier must leave time for the attribute call (6 s), so with a 17 s deadline a request normally reaches tier 2 and reaches tiers 3 and 4 only when earlier tiers fail fast or answer quickly. The cost saving comes from tiers 1 and 2; tiers 3 and 4 mainly add resilience. Real latencies will show whether the timeouts or the 20 s limit need to change.
24. ~~**Fields marked `NO` and non-visible facts.**~~ **Decided 2026-10-28:** fields marked `NO` are facts only the seller knows (such as purchase date) and stay manual. A field that is visible in a photo but wrongly marked `NO` is corrected through a reviewed override file (flipped to `LIMITED`) and the AI then attempts it. The review of the `NO` list and the product owner's approval of the flips are part of this story (see Backend — Taxonomy: AI-extractable Corrections).
25. **Recording AI-filled values (optional).** `listing_attribute_values` already has `value_source` and `ai_confidence`. Not planned here: marking values the seller kept as AI-sourced when the details are saved. Add it if you want it for analytics.
26. **Image preparation thresholds.** Starting values (LLD §6.5.2): sharpness at least 100 (variance of the Laplacian on a 512 px copy), mean brightness between 35 and 225, duplicates within a Hamming distance of 6 on a 64-bit difference hash, 3 to 5 views, long side 1024 px, JPEG quality 80. They are guesses and must be tuned on the labelled photo set, together with the tier thresholds.
27. **Downloading originals.** To filter photos, the AI service downloads up to 10 originals (each up to 10 MB). This adds time and bandwidth inside the 17 s deadline. Once the media module produces smaller derivatives (a documented follow-up of US-004), the service should fetch those instead. Not planned now; the preparation timeout (4 s) bounds the cost.
28. **Tuning after go-live (decided 2026-10-28).** (a) Seller feedback joined with `tier_attempts` gives keep-rates by tier and confidence band; sellers may keep wrong values, so treat the numbers as a trend. (b) The optional shadow comparison (off by default, sample rate and hourly cap in configuration) measures a cheap tier against the strongest tier without seller bias, at the cost of the extra calls; turn it on only with a budget in mind and only if the providers' terms allow it. (c) Changing a threshold needs a configuration change and a restart until US-121 adds Admin settings. (d) Go-live defaults: AI off by default, internal users first, strict thresholds. The tuning queries and the shadow comparison are included in the 13 SP; no new storage is added.
---

**Status:** Approved (2026-10-28; the user approved the plan including `valuex-ai`, 13 SP, the model cascade with the four chosen tiers (tier 4 Google), image preparation, tuning from real data, and the review of `NO`-marked attributes with the AI-extractable override file).


---

## 8. Implementation Notes (2026-10-28)

Deviations from the plan above, found while implementing. The LLD describes the behaviour; these notes record where the code differs from the plan wording.

**Backend**
- No separate `AiProperties` class: the settings are the nested `ValuexProperties.AiSettings` (`valuex.ai.*`, with `Gateway` and `Internal` parts). Behaviour is the same (`valuex.ai.enabled` default `false`).
- Circuit breaker: `resilience4j-circuitbreaker` is used programmatically in `AiGatewayClient` (window 20, 50%, 30 s open, 5 half-open calls). `resilience4j-spring-boot3`, `spring-boot-starter-aop` and annotations were not needed. There is no TimeLimiter: the `RestClient` read timeout (20 s) is the hard limit.
- The retry is a small manual loop (once, on connect failure, 502 or 503 only); a read timeout is never retried because the cascade may still be running.
- `RateLimitedException` (new, mapped to HTTP 429 `AI_SUGGESTION_RATE_LIMITED`) was added because `BusinessException` maps to 400.
- The internal chain `/internal/v1/**` has its own `SecurityFilterChain` (`InternalSecurityConfig`) and `InternalApiKeyFilter` is created inside it (not a bean, so it is not applied to every request).
- The AI fields endpoint also returns the "More details" fields (`section = MORE`), because the AI tries to fill those too.
- `tier_attempts` are kept on `FAILED` rows when the gateway answered without a result (`AiGatewayClient` returns the answer, `ListingAiService.recordFailed` stores it and the inference id).
- `ai-extractable-overrides.csv` is header-only: no `NO` attribute was approved by the product owner yet, so nothing is overridden. The candidate list is in the testing guide's "Open items".
- The mobile response omits provider and model names (as planned).

**valuex-ai**
- Photo preparation uses Pillow, pillow-heif, NumPy: Laplacian sharpness, brightness, 64-bit difference hash. HEIC is decoded; the encoded views carry no metadata.
- The attribute call of the accepting tier is recorded as an extra tier attempt named `<tier>:attributes`.
- Shadow comparison is implemented and off by default.
- Ruff line length is 100 (CODING_STANDARDS §5); the coverage gate is 90% for `app/` (99% reached).

**Mobile**
- `ApiClient.post` got an optional `receiveTimeout`. The default is already 30 s, so the AI call uses a shorter, explicit 25 s (`ApiConstants.aiSuggestionTimeout`), not a longer one.
- `sendSuggestionFeedback` now sends the body as `{"feedback": [...]}` (the backend contract); the earlier US-114 code sent `fields`, which the backend does not accept.
- A third notice was added: when AI answers but recognises nothing, the seller sees "We could not recognise the item from your photos. Please fill in the details yourself." (English and Hindi) instead of an empty AI-filled page.
- The Hindi texts need confirmation by the product owner.

**Results**
- Backend: `mvn verify` green, 910 tests, JaCoCo gate met, Checkstyle clean. Integration tests need Docker with `-Dtestcontainers.version=1.21.4` on this machine (Docker 29).
- valuex-ai: 138 tests, 99% coverage, `ruff check` and `ruff format` clean.
- Mobile: `flutter analyze` clean; the new and the existing listing tests pass. 18 accessibility tests (text contrast and similar guidelines on sign-in, sign-up, Aadhaar, profile and account-security screens) fail, none in listing code; they are not caused by this story.
- SonarQube: not run (no server or token available in this environment).
