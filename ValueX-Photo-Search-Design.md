# ValueX Photo Search Design

**Document Type:** Architecture / Implementation Design Input\
**Status:** Approved for design update and implementation planning\
**Product:** ValueX\
**Feature:** AI Photo-Based Product Search\
**Mobile:** Flutter\
**Web:** React\
**Business Backend:** Java Spring Boot\
**AI Services:** Python / FastAPI\
**Object Storage:** Cloudflare R2 Standard\
**Transactional Database:** PostgreSQL\
**Vector Search (MVP):** PostgreSQL + pgvector\
**Keyword / Faceted Search:** OpenSearch\
**Cache:** Redis\
**Date:** 2026-09-01

------------------------------------------------------------------------

## 1. Purpose

This document defines the end-to-end technical design for ValueX
photo-based product search. It is intended as direct input to
architecture, backend, AI, mobile, web, infrastructure, QA, and
implementation agents.

The central product concept is: **Click a photo to sell. Click a photo
to buy.**

A buyer must be able to take a photograph using the mobile camera or
choose an existing photograph, submit it to ValueX, have AI understand
it, search eligible seller listings for the same or similar items,
receive strongest matches first, and refine results using marketplace
filters.

This design complements the ValueX Storage Design Decision.
**Cloudflare R2 stores image objects; pgvector stores numerical image
embeddings used for similarity search.**

## 2. Product Behavior

The implementation must support:

-   camera or gallery query image;
-   server-side buyer-plan entitlement and quota;
-   AI visual feature extraction;
-   search across eligible seller listing images;
-   highest-match-first results;
-   optional calibrated similarity presentation;
-   price, location, condition and seller-rating filters;
-   graceful handling of invalid, unclear, inappropriate and no-result
    images;
-   isolation so photo-search failure does not break normal keyword
    search.

## 3. Selected Architecture

``` text
Cloudflare R2        -> image object storage
PostgreSQL           -> authoritative listing/business/media metadata
pgvector             -> seller listing image embeddings
OpenSearch           -> keyword search, filters and facets
Redis                -> quotas, rate limits and short-lived caches
Python AI            -> preprocessing, embeddings, classification and ranking
Spring Boot          -> authentication, entitlement and business orchestration
Flutter / React      -> buyer experience
```

R2 does not replace a vector database. R2 stores JPEG/PNG/HEIC/AVIF/WebP
objects. pgvector stores vectors such as `[0.021, -0.117, 0.764, ...]`.

## 4. End-to-End Architecture

``` text
SELLER INDEXING

Seller Flutter/React
 -> Spring Boot Media API
 -> short-lived upload authorization
 -> Cloudflare R2
 -> Media Worker
    - validation
    - EXIF cleanup
    - AVIF/WebP derivatives
    - perceptual hash
 -> ListingMediaReady event
 -> Python Visual AI
    - preprocessing
    - category/attribute inference
    - embedding generation
 -> PostgreSQL + pgvector
 -> vector index ready


BUYER SEARCH

Buyer Flutter/React
 -> Spring Boot Photo Search API
    - authentication
    - account-state check
    - entitlement/quota
    - validation
 -> temporary private R2 query image
 -> Python Visual Search
    - preprocessing
    - query embedding
    - optional category/attribute inference
 -> pgvector ANN search
 -> top-K image candidates
 -> aggregate/deduplicate by listing
 -> authoritative listing eligibility validation
 -> OpenSearch filters/facets
 -> hybrid re-ranking
 -> ranked listing results
 -> Cloudflare CDN image variants
 -> buyer
```

## 5. Seller Visual Indexing

Generate embeddings only after mandatory media processing completes and:

``` text
MediaAsset.status = READY
```

Emit a lightweight event such as:

``` json
{
  "eventId": "uuid",
  "eventType": "ListingMediaReady",
  "listingId": "uuid",
  "mediaId": "uuid",
  "objectKey": "listings/.../original.jpg",
  "occurredAt": "2026-09-01T12:00:00Z"
}
```

Python then obtains authorized media access, preprocesses the image,
generates an embedding, optionally extracts category/brand/object
attributes, stores model/version metadata, and updates index status.

### Multiple listing images

Initially create one embedding per useful listing image:

``` text
Listing L100
 |- M1 -> V1
 |- M2 -> V2
 |- M3 -> V3
 `- M4 -> V4
```

Retrieve at image level but return at listing level. MVP aggregation:

``` text
listingVisualScore = MAX(valid image similarity scores)
```

Keep this aggregation pluggable for later learned/top-N strategies.

## 6. Buyer Search Flow

Entry points:

``` text
Take Photo
Upload From Gallery
```

Before AI processing, Spring Boot validates:

1.  authenticated user;
2.  account state;
3.  photo-search entitlement;
4.  daily plan quota;
5.  rate limit;
6.  file metadata constraints.

Entitlement must be server-side.

### Temporary query media

Use dedicated private storage, for example:

``` text
valuex-prod-search-input
search/{requestId}/input.jpg
```

Buyer search photos must not automatically become permanent assets.
Configure short retention and automatic cleanup. Do not reuse them for
model training without an explicitly approved policy/consent basis.

## 7. Query Processing

``` text
Query Image
 -> decode
 -> normalize
 -> quality validation
 -> safety validation
 -> optional object detection/cropping
 -> optional category/attribute inference
 -> embedding
 -> Query Vector
```

Handle blur, low resolution, blank/corrupt images, multiple unrelated
objects, screenshots where relevant, and inappropriate/restricted
content.

Suggested errors:

``` text
ERROR_IMAGE_TOO_LARGE
ERROR_IMAGE_UNCLEAR
ERROR_INVALID_IMAGE
ERROR_INAPPROPRIATE_IMAGE
ERROR_PREMIUM_REQUIRED
ERROR_DAILY_LIMIT_REACHED
ERROR_PHOTO_SEARCH_UNAVAILABLE
```

## 8. Embedding Model Contract

Do not couple architecture to one named model.

``` python
class ImageEmbeddingProvider:
    def embed(self, image) -> EmbeddingResult:
        ...
```

`EmbeddingResult` should contain:

``` text
vector
model_name
model_version
embedding_version
dimensions
processing_time_ms
quality/confidence metadata
```

Never compare incompatible embedding spaces. Every vector must carry
model/version/dimension metadata.

## 9. Vector Data Model

Illustrative schema:

``` sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE listing_image_embeddings (
    id UUID PRIMARY KEY,
    listing_id UUID NOT NULL,
    media_id UUID NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(100) NOT NULL,
    embedding_version VARCHAR(100) NOT NULL,
    dimensions INTEGER NOT NULL,
    embedding VECTOR(<MODEL_DIMENSION>) NOT NULL,
    index_status VARCHAR(30) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    UNIQUE(media_id, embedding_version)
);
```

Select actual vector dimension only after the model is finalized.

Use an approximate-nearest-neighbor index. HNSW is the initial
candidate. Benchmark the similarity metric and index parameters against
representative ValueX data.

## 10. Candidate Retrieval

Do not retrieve only the final UI page size. Retrieve a configurable
larger pool, initially benchmark around:

``` text
topK = 200-500
```

Candidates may be removed because a listing is sold, expired, suspended,
outside location/price filters, wrong condition/category, or otherwise
ineligible.

`topK` must be configuration.

### Similarity score

Do not assume raw cosine similarity equals a user-facing percentage.

``` text
raw similarity
 -> calibration
 -> normalizedMatchScore [0..1]
```

The existing product concept of a minimum similarity threshold must be
validated/calibrated using a labeled ValueX evaluation dataset.

## 11. Hybrid Search

Pure vector similarity is insufficient. Combine:

``` text
Visual Similarity
+ AI-inferred metadata
+ Listing metadata
+ Buyer filters
```

Potential inferred attributes:

``` text
category
object type
brand
model
color
material
style
```

Use inferred attributes only above appropriate confidence.

## 12. OpenSearch Role

OpenSearch handles:

-   keyword/category search;
-   price/condition/location/seller-rating filters;
-   facets;
-   marketplace text ranking.

pgvector handles visual candidate retrieval.

PostgreSQL owns authoritative business state.

Do not duplicate authoritative listing/order lifecycle rules inside the
AI service.

## 13. Re-ranking

Use two stages.

**Stage 1:** pgvector top-K retrieval.

**Stage 2:** re-ranking using visual similarity,
category/brand/attribute match, availability, location, listing quality,
seller trust and other approved signals.

Illustrative formula only:

``` text
finalScore =
    visualSimilarity * 0.60
  + categoryMatch    * 0.15
  + brandModelMatch  * 0.10
  + conditionMatch   * 0.05
  + locationScore    * 0.05
  + listingQuality   * 0.03
  + sellerTrust      * 0.02
```

These are not production constants. Tune using offline relevance
evaluation and production behavior.

Paid listing promotion must not cause a weak visual result to masquerade
as the strongest organic match.

## 14. Same Item vs Similar Item

Use semantic embeddings for similar-item search.

Use perceptual hashing plus embedding similarity for near-identical
image detection.

Store both:

``` text
semantic embedding
perceptual hash
```

Perceptual hashing also supports duplicate-image/fraud detection.

## 15. Trust & Safety Reuse

The visual pipeline can provide fraud signals:

``` text
duplicate/near-duplicate image
cross-account image reuse
watermark detection
restricted object detection
repeated relisting after enforcement
```

Vector similarity alone must never automatically ban a user.

## 16. Python AI Structure

``` text
valuex-ai/
  src/
    visual/
      embedding/
        provider.py
        preprocessing.py
        inference.py
        versioning.py
      search/
        vector_repository.py
        candidate_retrieval.py
        aggregation.py
        reranking.py
        calibration.py
      classification/
        category.py
        attributes.py
      quality/
        blur.py
        validation.py
      safety/
        restricted_content.py
        watermark.py
      fraud/
        perceptual_hash.py
        duplicate_detection.py
    api/
      photo_search.py
      internal_embedding.py
    common/
      config.py
      telemetry.py
      errors.py
```

Entitlement, payments, account state and lifecycle remain Spring Boot
responsibilities.

## 17. Service Boundaries

Clients communicate with Spring Boot, never directly with pgvector.

Seller indexing is asynchronous:

``` text
Spring/Media Pipeline -> outbox/event -> Python worker -> pgvector
```

Buyer search is synchronous where the latency SLO permits:

``` text
Spring Boot -> Python visual search -> candidates -> business filtering -> results
```

Internal AI endpoints must be authenticated and not publicly routable.

## 18. Candidate APIs

Exact contracts must be captured in OpenAPI.

Buyer-facing:

``` http
POST /api/v1/search/photo
GET  /api/v1/search/photo/{searchId}
```

Internal:

``` http
POST /internal/v1/visual-search
POST /internal/v1/embeddings/images
POST /internal/v1/visual-index/reindex
```

Example request:

``` json
{
  "searchId": "uuid",
  "mediaId": "uuid",
  "filters": {
    "priceMin": 1000,
    "priceMax": 10000,
    "condition": ["GOOD", "LIKE_NEW"],
    "location": {
      "pincode": "411014",
      "radiusKm": 50
    }
  },
  "topK": 300
}
```

Never expose raw embeddings to clients.

## 19. Buyer Result Contract

``` json
{
  "searchId": "uuid",
  "results": [
    {
      "listingId": "uuid",
      "title": "Apple iPhone 14 128GB",
      "price": 42000,
      "condition": "GOOD",
      "location": "Pune",
      "matchScore": 0.91,
      "matchLabel": "Best Match",
      "image": {
        "thumbnail": "https://media.valuex.com/...",
        "card": "https://media.valuex.com/..."
      }
    }
  ],
  "pagination": {
    "page": 1,
    "pageSize": 20,
    "hasMore": true
  }
}
```

Keep API score separate from presentation formatting.

## 20. Filters

Support product-defined filters such as:

``` text
price
location/distance
condition
seller rating
```

Apply them while preserving meaningful visual ranking.

If filters eliminate results, provide clear recovery actions such as
Clear Filters, Expand Location, Broaden Price, Try Another Photo, or
Browse Related Category.

## 21. Search Session Model

``` text
PhotoSearchRequest
------------------
id
user_id
query_media_id
plan_id
embedding_version
status
filters_json
candidate_count
result_count
latency_ms
created_at
expires_at
```

States:

``` text
CREATED
UPLOAD_PENDING
PROCESSING
SEARCHING
RERANKING
COMPLETED
NO_RESULTS
FAILED
EXPIRED
```

## 22. Redis

Use Redis for:

-   daily plan quota;
-   rate limiting;
-   short-lived search state;
-   result caching;
-   repeated-query cache.

Possible keys:

``` text
photoquota:{userId}:{date}
photosearch:rate:{userId}
photosearch:result:{searchHash}:{filterHash}:{indexVersion}
```

Redis is not the vector source of truth.

## 23. Listing Lifecycle Integration

Only eligible listings appear in active photo search.

At minimum:

``` text
PUBLISHED -> searchable
```

Exclude states such as:

``` text
SOLD
EXPIRED
REJECTED
REMOVED_BY_ADMIN
DEACTIVATED_BY_SELLER
```

Vectors may remain temporarily where retention permits, but
authoritative listing state controls visibility.

## 24. Media Change / Re-index

``` text
Image added:
READY -> embedding job -> vector inserted

Image replaced:
new READY -> new embedding -> activate -> retire old vector

Image permanently deleted:
remove active vector -> invalidate caches

Metadata changed:
update PostgreSQL/OpenSearch -> invalidate affected cache
```

Normal text/price edits do not require image re-embedding.

## 25. Model Versioning and Re-index

Design model replacement from day one.

``` text
visual-v1
 -> existing active index

visual-v2
 -> re-embed R2 media
 -> separate vector table/index/version
 -> offline evaluation
 -> shadow/canary
 -> activate v2
 -> rollback window
 -> retire v1
```

Never overwrite the only production index during major migration.

Maintain controlled `active_embedding_version` and
`candidate_embedding_version`.

## 26. Vector Database Evolution

MVP:

``` text
PostgreSQL + pgvector
```

Re-evaluate dedicated vector infrastructure when vector count, QPS,
p95/p99 latency, ANN memory/maintenance, or re-index time requires
independent scaling.

Potential future candidates:

``` text
Qdrant
Milvus
Pinecone
Weaviate
```

Benchmark before migration.

## 27. Capacity Planning

Track:

``` text
active listings
indexed images/listing
total vectors
embedding dimensions
bytes/vector
ANN index size
QPS
topK
p50/p95/p99 latency
```

Example:

``` text
20M listings x 5 indexed images = 100M vectors
```

## 28. Performance

Existing product expectation is photo-search results in under
approximately 2 seconds. Treat this as an end-to-end SLO and benchmark
representative infrastructure.

Illustrative latency budget:

  Stage                             Initial engineering target
  ------------------------------- ----------------------------
  Auth/entitlement                                    \<100 ms
  Query image access                                  \<150 ms
  Preprocessing + embedding                           \<500 ms
  Vector retrieval                                    \<300 ms
  Business/OpenSearch filtering                       \<300 ms
  Re-ranking                                          \<300 ms

Measure p50, p95 and p99, not averages alone.

## 29. Graceful Degradation

If AI or pgvector is unavailable, photo search must report temporary
unavailability while keyword/category search remains operational.

If R2 upload fails, provide retry.

Never silently label ordinary keyword results as photo-search matches.

## 30. Privacy

Buyer query photos may contain people, documents, addresses, homes,
possessions, or location metadata.

Mandatory:

-   private temporary storage;
-   short configurable retention;
-   automatic deletion;
-   EXIF/geolocation sanitization;
-   encryption;
-   no public query-image URL;
-   no training reuse without approved basis/consent;
-   privacy-policy disclosure.

## 31. Security

-   no vector DB credentials in clients;
-   pgvector only on trusted network paths;
-   authenticated internal AI endpoints;
-   private R2 query objects;
-   short-lived signed access;
-   rate limiting;
-   actual-content validation;
-   malicious/corrupt image rejection;
-   sensitive-log redaction;
-   audit entitlement/admin overrides.

## 32. Observability

Technical:

``` text
photo_search_requests_total
photo_search_failures_total
photo_search_latency_ms
embedding_latency_ms
vector_query_latency_ms
rerank_latency_ms
query_image_latency_ms
candidate_count
filtered_candidate_count
result_count
no_result_rate
```

Relevance/business:

``` text
top-1/top-5 click-through
search-to-listing-view
search-to-contact
search-to-cart
search-to-purchase
retry/reformulation rate
photo searches by plan
quota exhaustion
free-to-paid conversion
cost per photo search
```

Alert on latency SLO breach, vector/embedding errors, no-result
anomalies, indexing backlog, stale index and quota failures.

## 33. Offline Relevance Evaluation

Create a representative labeled ValueX dataset with query images and
graded relevant/non-relevant listings across categories, angles,
lighting, clutter, partial objects and low-quality phone photos.

Track:

``` text
Recall@K
Precision@K
MRR
NDCG@K
```

Use it to calibrate thresholds, compare models and approve ranking
changes.

## 34. AI Guardrails

-   never claim identity solely from embedding similarity;
-   never ban users solely from similarity;
-   calibrate match scores;
-   record model version;
-   support model/index rollback;
-   use explicit no-result behavior.

A UI percentage must be calibrated, not raw cosine similarity multiplied
by 100.

## 35. Testing

**Unit:** preprocessing, provider contract, normalization, aggregation,
re-ranking, filters, versions, quotas.

**Integration:** seller READY image -\> embedding -\> searchable vector;
buyer R2 query -\> Python -\> pgvector -\> ranked candidates.

**Contract:** Spring Boot \<-\> Python schemas.

**Security:** unauthorized search, expired plan, exhausted quota, direct
AI access, malicious/oversized/unsupported images.

**Relevance:** labeled offline dataset.

**Load:** concurrent searches, vector QPS, seller indexing, re-indexing,
p95/p99.

**Failure:** R2, Python, pgvector, OpenSearch timeouts; stale listings;
model mismatch.

## 36. Implementation Work Packages

### Spring Boot

-   entitlement integration;
-   quota/rate limit;
-   photo-search API;
-   temporary media;
-   Python client;
-   authoritative eligibility filtering;
-   OpenSearch filter integration;
-   result assembly;
-   errors/analytics.

### Python AI

-   preprocessing;
-   embedding abstraction;
-   active model/version config;
-   seller indexing worker;
-   query embedding;
-   pgvector repository;
-   ANN retrieval;
-   listing aggregation;
-   calibration;
-   category/attribute inference;
-   re-ranking;
-   telemetry/evaluation.

### PostgreSQL/pgvector

-   extension;
-   embedding schema;
-   ANN index;
-   migrations;
-   maintenance/reindex;
-   recovery validation.

### OpenSearch

-   filterable listing metadata;
-   state synchronization;
-   hybrid filtering.

### Redis

-   quotas;
-   rate limits;
-   result cache;
-   version-aware invalidation.

### R2

-   private search-input storage;
-   short retention;
-   signed access;
-   cleanup.

### Flutter

-   camera/gallery;
-   permissions;
-   preview/retake;
-   upload progress;
-   paywall/quota;
-   progress state;
-   ranked results;
-   filters;
-   errors/no-results/retry.

### React

Implement equivalent web flows where in product scope.

### Infra

-   private AI networking;
-   pgvector;
-   R2;
-   workers/events;
-   secrets;
-   dashboards/alerts;
-   scaling.

## 37. Design Updates Required

Update HLD Part 3 with pgvector schema/index and temporary search media.

Update HLD Part 4 with the complete visual-search pipeline, model
abstraction, re-index strategy, evaluation and calibration.

Update HLD Part 5 with camera/gallery flow, entitlement/paywall,
progress/error states, results and filters.

Update HLD Part 6 with pgvector/AI security, observability and
model/index deployment.

Update HLD Part 7 with photo-search and internal AI contracts.

Update the Storage Design Decision to explicitly state:

``` text
R2 stores photo-search media.
pgvector stores embeddings.
This Photo Search Design defines indexing and retrieval.
```

## 38. Suggested Technical Stories

AI:

``` text
AI-PS-001 Image preprocessing
AI-PS-002 Embedding provider abstraction
AI-PS-003 Seller image embedding/indexing
AI-PS-004 pgvector ANN retrieval
AI-PS-005 Listing candidate aggregation
AI-PS-006 Match-score calibration
AI-PS-007 Hybrid re-ranking
AI-PS-008 Offline relevance evaluation
AI-PS-009 Model-version/reindex pipeline
```

Backend:

``` text
BE-PS-001 Entitlement
BE-PS-002 Quota/rate limiting
BE-PS-003 Photo-search API
BE-PS-004 Temporary query storage
BE-PS-005 Python integration
BE-PS-006 Listing eligibility filtering
BE-PS-007 OpenSearch filters
BE-PS-008 Ranked response/analytics
```

Mobile:

``` text
MOB-PS-001 Photo Search screen
MOB-PS-002 Camera capture
MOB-PS-003 Gallery selection
MOB-PS-004 Preview/retake/upload
MOB-PS-005 Paywall/quota UX
MOB-PS-006 Ranked results
MOB-PS-007 Filters
MOB-PS-008 Error/no-result/retry
```

Infra:

``` text
INF-PS-001 Provision pgvector
INF-PS-002 Private photo-search R2
INF-PS-003 AI runtime/network
INF-PS-004 Indexing worker/event path
INF-PS-005 Dashboards/alerts
INF-PS-006 Vector maintenance/recovery
```

## 39. Acceptance Criteria

-   [ ] Camera/gallery query supported.
-   [ ] Server-side entitlement and quota enforced.
-   [ ] Query images private, temporary and automatically cleaned.
-   [ ] READY seller images asynchronously generate embeddings.
-   [ ] Embeddings carry model/version metadata.
-   [ ] Multiple images can represent one listing.
-   [ ] pgvector ANN returns configurable top-K candidates.
-   [ ] Image candidates aggregate to listing results.
-   [ ] Ineligible listings never appear.
-   [ ] OpenSearch filters refine vector candidates.
-   [ ] Similarity order remains meaningful after filtering.
-   [ ] User-facing percentage, if used, is calibrated.
-   [ ] Highest match appears first.
-   [ ] Perceptual hashing supports near-duplicate detection.
-   [ ] AI/vector failure does not break keyword search.
-   [ ] Model re-index/rollback supported.
-   [ ] Raw embeddings never exposed to clients.
-   [ ] Vector DB is private.
-   [ ] p50/p95/p99 observable.
-   [ ] Offline relevance evaluation exists.
-   [ ] Security, contract, integration, relevance and load tests pass.
-   [ ] HLD/LLD/OpenAPI updated.

## 40. Definition of Done

Done only when:

1.  HLD/LLD changes are merged;
2.  OpenAPI contracts approved;
3.  seller indexing works end-to-end;
4.  pgvector schema/index deployed;
5.  Python embedding/search deployed;
6.  Spring entitlement/orchestration deployed;
7.  Flutter camera/gallery integrated;
8.  OpenSearch filtering integrated;
9.  calibration validated;
10. relevance tests meet agreed threshold;
11. performance meets SLO or approved exception;
12. privacy/retention verified;
13. dashboards/alerts live;
14. rollback/reindex documented and tested;
15. staging proves
    `buyer photo -> AI -> vector search -> filtered ranked listings`;
16. security/privacy review complete.

## 41. Final Decision

For ValueX MVP, implement photo search using:

``` text
Cloudflare R2 Standard
+ Python visual AI
+ PostgreSQL / pgvector
+ OpenSearch
+ Redis
+ Spring Boot orchestration
+ Flutter / React clients
```

**R2 stores the images; pgvector stores their embeddings.**

Index each useful seller listing image. For each buyer query, retrieve a
larger top-K vector candidate set, consolidate image matches into
listing-level candidates, enforce authoritative marketplace state and
filters, and re-rank so the most relevant available listings appear
first.

Use pgvector for MVP to minimize infrastructure complexity and cost.
Re-evaluate a dedicated vector database only when measured vector
volume, QPS, index-maintenance cost, or p95/p99 latency demonstrates
that pgvector is insufficient.

The design must remain model-versioned, provider-portable,
privacy-aware, observable, and independently degradable from ValueX
normal keyword-search experience.
