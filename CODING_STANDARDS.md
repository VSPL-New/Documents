# ValueX Coding Standards

**Version:** 1.0  
**Product:** ValueX – AI-Enabled C2C Recommerce Marketplace  
**Company:** ValueQuo Solutions Pvt. Ltd.  
**Date:** June 2026  
**Applies To:** All repositories — valuex-backend, valuex-mobile, valuex-web, valuex-ai, valuex-infra

---

## Table of Contents

1. [Universal Standards](#1-universal-standards)
2. [valuex-backend — Java Spring Boot](#2-valuex-backend--java-spring-boot)
3. [valuex-mobile — Flutter / Dart](#3-valuex-mobile--flutter--dart)
4. [valuex-web — React / TypeScript](#4-valuex-web--react--typescript)
5. [valuex-ai — Python FastAPI](#5-valuex-ai--python-fastapi)
6. [valuex-infra — GitHub Actions & Terraform](#6-valuex-infra--github-actions--terraform)

---

# 1. Universal Standards

These rules apply to every repository without exception.

---

## 1.1 Branching Strategy

| Branch | Purpose | Protection |
|--------|---------|-----------|
| `main` | Production-ready code | Protected — requires PR + approval |
| `develop` | Integration branch | Protected — requires PR |
| `feature/*` | Feature development | e.g. `feature/user-registration` |
| `fix/*` | Bug fixes | e.g. `fix/otp-expiry-bug` |
| `hotfix/*` | Production hotfixes | e.g. `hotfix/payment-webhook-crash` |
| `chore/*` | Dependency / config updates | e.g. `chore/upgrade-spring-boot` |

**Rules:**
- Never commit directly to `main` or `develop`.
- Feature branches must be rebased on `develop` before PR.
- Branch names use lowercase kebab-case.

---

## 1.2 Commit Message Format

Follow Conventional Commits:

```
<type>(<scope>): <short summary>

[optional body]
[optional footer]
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`, `ci`

**Scope:** module or feature name in lowercase (e.g. `auth`, `listing`, `payment`, `ci`)

**Examples:**
```
feat(auth): add Aadhaar OTP verification flow
fix(payment): handle webhook duplicate events
chore(deps): upgrade Spring Boot to 3.2.6
test(listing): add unit tests for listing state machine
```

**Rules:**
- Summary in present tense, lowercase, no period at end.
- Max 72 characters in the summary line.
- Reference story ID in footer when applicable: `Refs: US-001`

---

## 1.3 Pull Request Rules

- Every PR requires at least one reviewer approval.
- PR must pass all CI checks before merge.
- PR title follows the same Conventional Commits format.
- PR body must include: What changed, Why, How to test.
- Delete branch after merge.
- No `console.log`, `System.out.println`, or `print()` debug statements in PRs.

---

## 1.4 Secret Management

- **Never commit secrets** (API keys, passwords, tokens, private keys) to any repository.
- Use environment variables for all configuration that differs per environment.
- GitHub Secrets for CI/CD pipeline values.
- `.env` files are `.gitignore`d in every repo.
- Sensitive fields (Aadhaar hash, bank account, UPI, refresh tokens) are encrypted at rest using AES-256.
- Never log raw Aadhaar numbers, bank account numbers, or UPI IDs.

---

## 1.5 Security Mandates (All Repos)

- All inter-service traffic over TLS 1.3.
- JWT access token validity: 1 hour. Refresh token validity: 7 days.
- RBAC enforced server-side — never trust client-side role claims.
- Rate limits are enforced at the API Gateway level and additionally at service level.
- Account status (ACTIVE, UNDER_REVIEW, RESTRICTED, SUSPENDED, BANNED) must be validated on every protected API call.
- All file uploads (images) must validate MIME type, extension, and content — not just the filename.
- AI APIs are internal-only. They must never be exposed publicly.

---

## 1.6 API Contract Standards

All REST APIs follow:

**Base path:** `/api/v1`

**Success response:**
```json
{
  "success": true,
  "data": {},
  "metadata": {
    "requestId": "uuid",
    "timestamp": "ISO-8601"
  }
}
```

**Error response:**
```json
{
  "success": false,
  "error": {
    "code": "SCREAMING_SNAKE_CASE_ERROR_CODE",
    "message": "Human-readable message"
  },
  "metadata": {
    "requestId": "uuid",
    "timestamp": "ISO-8601"
  }
}
```

**Rules:**
- Error codes are `SCREAMING_SNAKE_CASE` (e.g. `INVALID_OTP`, `LISTING_NOT_FOUND`).
- No breaking changes within a version (`/api/v1`). Additive changes only.
- Pagination: use `page`, `size`, `totalElements`, `totalPages` in `metadata`.
- All list responses are paginated — never return unbounded lists.
- Every request carries `X-Correlation-Id` header for distributed tracing.

---

## 1.7 Logging Standards

Structured JSON logs only. Every log entry must include:

```json
{
  "timestamp": "ISO-8601",
  "level": "INFO|WARN|ERROR|DEBUG",
  "requestId": "uuid",
  "userId": "uuid or SYSTEM",
  "service": "valuex-backend",
  "module": "auth",
  "action": "OTP_VERIFIED",
  "message": "Human readable"
}
```

**Rules:**
- Use `ERROR` for exceptions and failures.
- Use `WARN` for degraded conditions (AI fallback used, retry triggered).
- Use `INFO` for significant business events (order created, payment succeeded).
- Use `DEBUG` for diagnostic details — disabled in production.
- Mask PII in logs: `98XXXX1234`, `ab***@gmail.com`.
- Never log: raw Aadhaar, bank account numbers, UPI IDs, JWT tokens, passwords.

---

## 1.8 Test Coverage Minimums

| Repo | Minimum Coverage |
|------|-----------------|
| valuex-backend | 80% |
| valuex-mobile | 70% |
| valuex-web | 70% |
| valuex-ai | 70% |
| valuex-infra | Terraform `plan` validates all PRs |

Coverage gate is enforced in CI — PRs below threshold are blocked.

---

## 1.9 Code Review Checklist

Before approving any PR, verify:

- [ ] No secrets or credentials in code
- [ ] No debug logging or commented-out code
- [ ] Error codes follow the standard format
- [ ] Sensitive data is masked in logs
- [ ] Account status validation is present on new protected endpoints
- [ ] New DB columns have appropriate indexes
- [ ] New API endpoints have OpenAPI annotations (backend)
- [ ] State transitions go through the state machine (not direct status assignment)
- [ ] Financial records are append-only (no UPDATE on escrow_ledger, payment_events)
- [ ] AI calls have fallback handling

---

# 2. valuex-backend — Java Spring Boot

**Stack:** Java 21, Spring Boot 3.2.x, Maven, Lombok, JPA, Flyway, PostgreSQL 16, Redis 7, JWT  
**Architecture:** Modular Monolith — clean package boundaries per business domain

---

## 2.1 Code Style

- Follow **Google Java Style Guide**.
- Enforced via **Checkstyle** plugin in Maven (configured in `checkstyle.xml`).
- Indentation: 4 spaces. No tabs.
- Max line length: 120 characters.
- All source files have the standard copyright header.

**Naming conventions:**

| Element | Convention | Example |
|---------|-----------|---------|
| Classes | PascalCase | `ListingService`, `OrderController` |
| Interfaces | PascalCase | `ListingRepository`, `DomainEvent` |
| Methods | camelCase | `createListing()`, `validateOtp()` |
| Variables | camelCase | `userId`, `listingStatus` |
| Constants | UPPER_SNAKE_CASE | `MAX_LISTING_IMAGES`, `OTP_EXPIRY_MINUTES` |
| Packages | lowercase dot-separated | `com.valuex.listing.service` |
| DB columns | snake_case | `created_at`, `seller_id` |
| Error codes | SCREAMING_SNAKE_CASE | `LISTING_NOT_FOUND` |

---

## 2.2 Package Structure

Each domain module follows this internal layout:

```
com.valuex.<module>/
├── controller/       # HTTP layer — request/response only
├── service/          # Application layer — use case orchestration
├── domain/           # Business rules, state machines, enums
├── repository/       # JPA repositories — data access only
├── dto/              # Request/Response DTOs
├── event/            # Domain events for this module
└── exception/        # Module-specific exceptions
```

`com.valuex.common/` contains shared infrastructure:

```
com.valuex.common/
├── config/           # Spring configs (Security, Redis, OpenAPI, etc.)
├── security/         # JWT, SecurityContext
├── audit/            # Audit interceptor and logger
├── events/           # DomainEvent base class and publisher
├── exception/        # GlobalExceptionHandler, BusinessException, etc.
├── dto/              # ApiResponse<T>, PagedResponse<T>
├── statemachine/     # Generic StateMachine<S>
└── utils/            # DateUtils, StringUtils, etc.
```

---

## 2.3 Layer Responsibilities

**Controller layer:**
- Receives HTTP requests, validates input via `@Valid`.
- Maps DTOs, calls the service layer.
- Returns `ResponseEntity<ApiResponse<T>>`.
- **No business logic.** No direct repository calls.

**Service (Application) layer:**
- Orchestrates use cases.
- Owns `@Transactional` boundaries.
- Publishes domain events after successful state changes.
- Validates account status before any state-mutating operation.

**Domain layer:**
- Contains business rules, enums, state machine definitions.
- No Spring dependencies — pure Java.
- All state transitions must go through `StateMachine.transition()`.

**Repository layer:**
- Spring Data JPA repositories only.
- Named queries for complex reads; native SQL via `@Query` for reporting.
- No business logic.

**Infrastructure layer:**
- External service adapters (Aadhaar, Razorpay, Shiprocket, AI service).
- Redis cache service.
- S3/object storage service.

---

## 2.4 State Machine Rules

Every entity with a lifecycle (`User`, `Listing`, `Order`, `Payment`, `Escrow`, `Shipment`, `Return`, `Dispute`, `Subscription`, `SupportTicket`) must:

1. Use `StateMachine<S>` from `com.valuex.common.statemachine`.
2. Reject invalid transitions with `ValidationException("INVALID_STATE_TRANSITION", ...)`.
3. Write a `*_status_history` record on every successful transition.
4. Publish a domain event after every transition.
5. **Never** update status directly (`entity.setStatus(...)`) — always go through the state machine.

---

## 2.5 API and OpenAPI Standards

Every `@RestController` must:

- Be annotated with `@Tag(name = "...", description = "...")`.
- Have `@Operation(summary = "...", description = "...")` on each endpoint.
- Declare `@ApiResponses` for at least 200 and 4xx cases.
- Map to `/api/v1/<module>/<resource>`.

OpenAPI is auto-generated via Springdoc. Accessible at `/swagger-ui.html` in non-prod environments.

---

## 2.6 Security Rules

- All endpoints except public auth and actuator health require JWT.
- Role enforcement via `@PreAuthorize("hasRole('ADMIN')")` or `@PreAuthorize("hasAnyRole('BUYER','SELLER')")`.
- Account status checked in the service layer before any transactional operation.
- `SecurityContext.getCurrentUserId()` is the only acceptable way to get the authenticated user's ID — never trust a userId from the request body for ownership operations.
- Aadhaar: store only `SHA-256(aadhaar + salt)` — never the raw number.
- Bank account / UPI fields: encrypt with AES-256 before persist.

---

## 2.7 Database and Migration Rules

- Schema changes managed exclusively through **Flyway migrations**.
- Migration files named: `V{N}__{description}.sql` (e.g. `V2__add_listing_plan_type.sql`).
- Never alter a migration file after it has been applied to any environment.
- New columns on existing tables must be `NULLABLE` initially (backward compatible).
- All foreign key columns have an index.
- **Immutable financial records:** `escrow_ledger`, `payment_events`, `refund_events`, `audit_logs` — no UPDATE or DELETE ever. Append-only.

---

## 2.8 Redis Usage Rules

Redis is a cache — **not the source of truth**.

Allowed uses:
- Sessions: `session:{userId}` TTL 7 days
- OTP: `otp:{mobile}` TTL 5 minutes
- Rate limiting: `rate:otp:{mobile}`, `rate:login:{user}` TTL 1 hour
- Cart lock: `cart-lock:{listingId}` TTL 15 minutes
- Short-lived entity caches

Rules:
- Always set TTL. No keys without expiry.
- Invalidate cache on entity update.
- Cache miss must fall back to PostgreSQL — never fail the request.

---

## 2.9 Event-Driven Rules (MVP)

- Use `DomainEventPublisher` from `com.valuex.common.events` for all internal events.
- Events are published **after** the transaction commits (use `@TransactionalEventListener(phase = AFTER_COMMIT)`).
- Event handlers for notifications, search indexing, and analytics run asynchronously via `@Async`.
- Transactional outbox pattern for reliability on critical events (order, payment, escrow).

---

## 2.10 Exception Handling

- Throw domain-specific exceptions: `NotFoundException`, `ValidationException`, `BusinessException`.
- `GlobalExceptionHandler` in `common.exception` maps all exceptions to standard `ApiResponse<Void>` error responses.
- Never let unhandled exceptions propagate to the HTTP layer.
- Log at `ERROR` level with full stack trace for unexpected exceptions.
- Log at `WARN` level for expected business exceptions (invalid OTP, listing not found).

---

## 2.11 Testing Standards

- Use **JUnit 5** + **AssertJ** + **Mockito**.
- Test method naming: `should<ExpectedResult>When<Condition>()`.
- Structure: `// Given`, `// When`, `// Then` comments in every test.
- Unit tests mock the repository layer.
- Integration tests use `@SpringBootTest` with real PostgreSQL (TestContainers or a CI service container) — no H2 for integration tests.
- Every new service method has a corresponding unit test.
- Every new API endpoint has an integration test covering happy path and at least one error case.

---

## 2.12 Lombok Usage

Allowed: `@Data`, `@Builder`, `@NoArgsConstructor`, `@AllArgsConstructor`, `@RequiredArgsConstructor`, `@Slf4j`, `@Getter`, `@Setter`.

Rules:
- Prefer `@RequiredArgsConstructor` for constructor injection over `@Autowired`.
- Do not use `@Data` on JPA entity classes (use `@Getter`/`@Setter` + explicit `equals`/`hashCode` on ID only).
- All loggers via `@Slf4j` — no `Logger logger = LoggerFactory.getLogger(...)`.

---

# 3. valuex-mobile — Flutter / Dart

**Stack:** Flutter 3.22+, Dart 3.4+, Riverpod 2.5+, GoRouter 14+, Dio 5.4+  
**Architecture:** Clean Architecture + Feature-Based Modular Structure

---

## 3.1 Code Style

- Follow **Dart official style guide** (enforced via `flutter_lints` + `riverpod_lint`).
- Indentation: 2 spaces.
- Max line length: 100 characters.
- Run `dart format` before every commit.

**Naming conventions:**

| Element | Convention | Example |
|---------|-----------|---------|
| Classes, Widgets | PascalCase | `ListingCard`, `AuthProvider` |
| Files | snake_case | `listing_card.dart`, `auth_provider.dart` |
| Variables, functions | camelCase | `userId`, `fetchListing()` |
| Constants | lowerCamelCase | `kPrimaryColor`, `kBaseUrl` |
| Providers | camelCase + `Provider` | `authProvider`, `cartProvider` |
| Enums | PascalCase | `ListingStatus`, `UserAccountState` |
| Folders | snake_case | `core/`, `features/auth/` |

---

## 3.2 Folder Structure

Every feature follows this internal layout:

```
features/<feature_name>/
├── data/
│   ├── repositories/       # Implements domain repository interface
│   ├── datasources/        # API calls via Dio
│   └── models/             # JSON DTOs (fromJson / toJson)
├── domain/
│   ├── entities/           # Pure Dart business objects
│   ├── repositories/       # Abstract interfaces
│   └── usecases/           # Single-responsibility use cases
└── presentation/
    ├── screens/            # Full-page widgets
    ├── widgets/            # Feature-specific reusable widgets
    └── providers/          # Riverpod providers for this feature
```

`core/` contains shared infrastructure only:

```
core/
├── config/                 # Environment config
├── constants/              # API constants, storage keys, app constants
├── network/                # Dio client, interceptors, ApiResponse model
├── security/               # Secure storage service
├── theme/                  # AppTheme, colors, text styles
├── utils/                  # Validators, formatters, date utils
├── routing/                # GoRouter config, route names
└── widgets/                # Shared widgets (AppButton, AppTextField, etc.)
```

---

## 3.3 State Management Rules (Riverpod)

- All state via **Riverpod providers**. No `StatefulWidget` state for business data.
- Use `AsyncNotifierProvider` for async data with loading/error/data states.
- Use `StateNotifierProvider` for mutable local state.
- Use `Provider` for pure dependency injection.
- Use `FutureProvider` for simple read-only async data.
- Use code generation (`riverpod_generator` + `@riverpod` annotation) for all new providers.
- Providers are co-located with their feature (`features/<name>/presentation/providers/`).
- Always handle all three `AsyncValue` states in widgets: `.when(data:, loading:, error:)` — never ignore loading or error.

---

## 3.4 Widget Rules

- All widgets are `const` where possible.
- Screens (`*Screen`) receive no business logic — they read from providers and pass callbacks.
- No direct API calls or repository calls inside widgets — always go through a provider.
- Reusable UI components live in `core/widgets/` or `features/<name>/presentation/widgets/`.
- Every `Text` widget displaying user-facing content must use a localization key — no hardcoded strings.
- Touch targets: minimum 44×44 logical pixels for all interactive elements.
- Color contrast must meet WCAG 2.1 AA (4.5:1 for text).

---

## 3.5 Navigation Rules

- All navigation via **GoRouter** — no direct `Navigator.push`.
- Route names defined in `core/routing/route_names.dart` as `static const String`.
- Deep links must be registered in `app_router.dart`.
- Guard authenticated routes with a `redirect` callback that checks auth state.

---

## 3.6 API and Error Handling Rules

- All HTTP via **Dio** through `ApiClient` in `core/network/`.
- `ApiInterceptor` injects `Authorization: Bearer <token>` on every request.
- On 401 response: attempt token refresh once, then redirect to login.
- Standardized `ApiError` model mirrors the backend error response structure.
- Show standardized error UI on network failure: "Unable to connect — Retry".
- Show standardized error UI on server failure: "Something went wrong — Try Again".
- Show session expiry UI on 401 (after refresh failure): "Session expired — Login again".

---

## 3.7 Security Rules

- JWT and refresh tokens stored **only** in `FlutterSecureStorage` — never in `SharedPreferences`.
- Device ID stored in `FlutterSecureStorage`.
- SSL Pinning configured for production builds.
- Root/jailbreak detection enabled.
- Screenshot protection enabled on: Payment, Escrow, Bank Details, Aadhaar screens.
- No sensitive data in analytics events.

---

## 3.8 Localization Rules

- All user-facing strings must have entries in `lib/l10n/app_en.arb` (and other language ARB files).
- No hardcoded strings in widgets — use `AppLocalizations.of(context).keyName`.
- Supported languages for MVP: English, Hindi. Additional regional languages in later sprints.

---

## 3.9 Testing Standards

- **Unit tests** for use cases and repositories (mock the data source).
- **Widget tests** for all screens — test golden path and key error states.
- **Integration tests** for critical user flows (registration, listing creation, checkout).
- Test files co-located: `test/features/<feature>/...` mirroring `lib/features/<feature>/...`.
- Use `mocktail` for mocking.

---

# 4. valuex-web — React / TypeScript

**Stack:** React 18+, TypeScript 5+, Vite 5+, Redux Toolkit 2.0+, React Query, Material-UI 5+, Axios  
**Architecture:** Feature-Based Architecture

---

## 4.1 Code Style

- **Prettier** for formatting. **ESLint** with `@typescript-eslint` for linting.
- Both enforced as CI checks and pre-commit hooks.
- Indentation: 2 spaces.
- Max line length: 100 characters.
- Semicolons: yes.
- Single quotes for strings.

**Naming conventions:**

| Element | Convention | Example |
|---------|-----------|---------|
| Components | PascalCase | `ListingCard`, `OrderDetail` |
| Component files | PascalCase `.tsx` | `ListingCard.tsx` |
| Non-component files | camelCase `.ts` | `authSlice.ts`, `useListings.ts` |
| Folders | camelCase | `features/listings/`, `hooks/` |
| Type/Interface | PascalCase | `ListingDto`, `ApiResponse<T>` |
| Enums | PascalCase | `UserStatus`, `ListingCondition` |
| Custom hooks | `use` prefix | `useListings()`, `useAuth()` |
| Redux slices | camelCase + `Slice` | `authSlice`, `cartSlice` |
| Constants | UPPER_SNAKE_CASE | `API_BASE_URL`, `MAX_FILE_SIZE` |

---

## 4.2 Folder Structure

```
src/
├── api/
│   ├── client.ts           # Axios instance + interceptors
│   └── endpoints/          # API function per domain (authApi.ts, listingApi.ts)
├── app/
│   └── App.tsx             # Root component
├── components/
│   └── shared/             # Cross-feature reusable components
├── layouts/
│   └── AdminLayout.tsx     # Layout wrappers
├── pages/                  # Route-level page components
├── features/
│   ├── auth/
│   │   ├── components/     # Auth-specific UI components
│   │   ├── hooks/          # Auth-specific custom hooks
│   │   └── types.ts        # Auth-specific TypeScript types
│   ├── listings/
│   ├── orders/
│   ├── cart/
│   ├── search/
│   └── ...
├── store/
│   ├── index.ts            # Redux store setup
│   └── slices/             # Redux Toolkit slices
├── hooks/                  # Shared custom hooks
├── utils/                  # Shared utilities
├── types/                  # Global TypeScript types and interfaces
└── routes/                 # Route definitions
```

---

## 4.3 Component Rules

- **Functional components only** — no class components.
- Components export as **named exports** (except page-level components which may use default export).
- One component per file.
- Props type defined as `interface <ComponentName>Props` in the same file.
- No inline styles — use MUI's `sx` prop or `styled` from `@emotion/styled`.
- All interactive elements must have `aria-label` or visible label for accessibility.
- Keyboard navigation must work on all interactive elements.

---

## 4.4 State Management Rules

**Redux Toolkit** manages global client state:
- `authSlice` — authentication state (user, token)
- `cartSlice` — cart items
- `notificationSlice` — notification count / list
- `uiSlice` — global UI state (loading, modals)

**React Query (TanStack Query)** manages server state:
- All API data (listings, orders, search results, subscriptions) via `useQuery` / `useMutation`.
- Cache invalidation on mutations.
- No manual loading state management for server data — use React Query's `isLoading`, `isError`, `data`.

**Rule:** Do not store server-fetched data in Redux. Redux is for client-side state only.

---

## 4.5 TypeScript Rules

- `strict: true` in `tsconfig.json` — no exceptions.
- No `any` type — use `unknown` and narrow, or define a proper type.
- All API response shapes defined as TypeScript interfaces in `src/types/`.
- All API function return types explicitly declared.
- Enums for finite value sets (e.g. `ListingStatus`, `UserRole`).

---

## 4.6 API and Error Handling Rules

- All HTTP via the **Axios client** in `src/api/client.ts`.
- Request interceptor injects `Authorization: Bearer <token>`.
- Response interceptor handles 401 (token refresh → retry, else redirect to login).
- API functions in `src/api/endpoints/<domain>Api.ts` (e.g. `listingApi.ts`).
- Always use React Query's `onError` to show toast/snackbar on mutation failures.
- Map backend error codes to user-friendly messages in a central `errorMessages.ts` map.

---

## 4.7 Security Rules

- Access token stored in **memory only** (React state or Zustand) — never `localStorage`.
- Refresh token as **HttpOnly secure cookie** — not accessible to JavaScript.
- Admin portal must implement CSRF protection via `SameSite=Strict` cookies.
- CSP headers configured on the server/CDN.
- No user-controlled content rendered as HTML (no `dangerouslySetInnerHTML`).
- Route-level auth guards: unauthenticated users redirected to login.

---

## 4.8 Accessibility Rules (WCAG 2.1 AA)

- All images have `alt` text.
- Form fields have associated `<label>` elements or `aria-label`.
- Color is never the sole indicator of state.
- Focus is managed on modal open/close.
- All functionality accessible via keyboard.

---

## 4.9 Testing Standards

- **Vitest** + **React Testing Library** for unit and component tests.
- Test files: `<ComponentName>.test.tsx` co-located with component.
- Test every component for: render without error, key user interactions, error states.
- Mock API calls via `msw` (Mock Service Worker) — never mock Axios directly.
- E2E tests via **Playwright** for critical flows (login, create listing, checkout).

---

# 5. valuex-ai — Python FastAPI

**Stack:** Python 3.11+, FastAPI, Pydantic v2, Uvicorn/Gunicorn  
**Architecture:** Domain-organized routers, AI service isolation

---

## 5.1 Code Style

- Follow **PEP 8**.
- Enforced via **Ruff** (linting + formatting) — replaces Black + Flake8.
- Indentation: 4 spaces.
- Max line length: 100 characters.
- Run `ruff check . && ruff format .` before every commit.
- **Type hints are mandatory** on all function signatures and class attributes.

**Naming conventions:**

| Element | Convention | Example |
|---------|-----------|---------|
| Modules / files | snake_case | `listing_service.py`, `fraud_router.py` |
| Classes | PascalCase | `ListingRequest`, `FraudScoreResponse` |
| Functions / methods | snake_case | `generate_embedding()`, `score_fraud()` |
| Variables | snake_case | `listing_id`, `fraud_score` |
| Constants | UPPER_SNAKE_CASE | `MAX_EMBEDDING_BATCH`, `SIMILARITY_THRESHOLD` |
| Pydantic models | PascalCase + `Request`/`Response` | `ListingSuggestRequest`, `FraudScoreResponse` |

---

## 5.2 Project Structure

```
valuex-ai/
├── app/
│   ├── main.py                 # FastAPI app entry point
│   ├── routers/
│   │   ├── listing.py          # /ai/v1/listings/*
│   │   ├── visual_search.py    # /ai/v1/search/*
│   │   ├── fraud.py            # /ai/v1/fraud/*
│   │   ├── moderation.py       # /ai/v1/moderation/*
│   │   └── support.py          # /ai/v1/support/*
│   ├── services/
│   │   ├── listing_service.py
│   │   ├── visual_search_service.py
│   │   ├── fraud_service.py
│   │   ├── moderation_service.py
│   │   └── support_service.py
│   ├── models/
│   │   ├── requests.py         # Pydantic input models
│   │   └── responses.py        # Pydantic output models
│   ├── core/
│   │   ├── config.py           # Settings via pydantic-settings
│   │   ├── security.py         # Internal API key auth
│   │   ├── logging.py          # Structured JSON logger
│   │   └── exceptions.py       # Custom exception handlers
│   └── workers/
│       └── embedding_worker.py # Background embedding generation
├── tests/
├── Dockerfile
├── requirements.txt
└── pyproject.toml
```

---

## 5.3 Pydantic Rules

- All request and response shapes are **Pydantic v2 models** — no raw dicts in function signatures.
- Pydantic models use `model_validator` and `field_validator` for input validation.
- Response models always include `model_name: str`, `model_version: str`, `inference_id: str` (UUID).
- Use `model_config = ConfigDict(str_strip_whitespace=True)` on all request models.

---

## 5.4 API Design Rules

- All AI endpoints under `/ai/v1/`.
- **Internal-only** — authenticated via internal API key (`X-Internal-Api-Key` header). Never exposed to the public internet.
- All endpoints return the standard AI response envelope:

```json
{
  "inferenceId": "uuid",
  "modelName": "visual-search-clip",
  "modelVersion": "1.0.0",
  "result": {},
  "confidenceScore": 0.89,
  "warnings": []
}
```

- Every response must include `modelName` and `modelVersion` for auditability and rollback capability.

---

## 5.5 AI Service Principles

- **AI is advisory**: suggestions for title, category, price, description can be overridden by the user.
- **AI is blocking** only for safety decisions: restricted item detection, watermark detection.
- **AI never owns transactions**: Spring Boot backend owns all state mutations.
- Every AI service must have a fallback:
  - Listing AI failure → allow manual entry.
  - Photo search failure → return keyword search suggestion.
  - Fraud AI failure → fall back to rules engine.
  - Moderation AI failure → route to manual review queue.
- Timeouts: set per-service; never block indefinitely.
- Quota enforcement for photo search is server-side (validated in Spring Boot, not just AI service).

---

## 5.6 Data Privacy Rules

- Never log raw Aadhaar, bank account, UPI, or private message content.
- Access media only via signed S3 URLs — never store URLs with permanent access.
- Temporary query images (photo search uploads) deleted after the retention window.
- For LLM-based features: system prompts are centrally controlled. Validate all LLM output before returning to client. No user-controlled prompt injection.

---

## 5.7 Async and Performance Rules

- FastAPI endpoints must be `async def` for I/O-bound work (DB calls, S3, external models).
- CPU-bound work (embedding generation, model inference) runs in a thread pool via `asyncio.run_in_executor`.
- Embedding generation for listing images is done by the `embedding_worker` background task — not inline in the request path.
- Target latencies:
  - Listing AI: < 5 seconds
  - Photo search: < 2 seconds (p95)
  - Fraud score: < 500ms (p95)
  - Moderation: < 3 seconds

---

## 5.8 Logging Rules

Every AI inference must log:

```json
{
  "inference_id": "uuid",
  "model_name": "fraud-detector",
  "model_version": "1.2.0",
  "request_id": "uuid from caller",
  "entity_type": "LISTING",
  "entity_id": "uuid",
  "latency_ms": 142,
  "decision": "MANUAL_REVIEW",
  "confidence": 0.76,
  "fallback_used": false
}
```

Never log: input images as base64, Aadhaar data, bank details.

---

## 5.9 Testing Standards

- **pytest** for all tests.
- Unit tests mock external model calls and DB calls.
- Integration tests use a test database and mock model inference.
- Every router has tests for: successful response, invalid input (Pydantic validation), internal service error (fallback path).
- Model evaluation tests run on a scheduled pipeline (not in unit tests).

---

# 6. valuex-infra — GitHub Actions & Terraform

**Stack:** GitHub Actions (CI/CD), Terraform (IaC), Docker, Kubernetes

---

## 6.1 Terraform Standards

**File layout per module:**

```
valuex-infra/
├── environments/
│   ├── dev/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── terraform.tfvars
│   ├── staging/
│   └── prod/
├── modules/
│   ├── vpc/
│   ├── kubernetes/
│   ├── postgresql/
│   ├── redis/
│   ├── s3/
│   ├── load_balancer/
│   └── monitoring/
└── README.md
```

**Naming convention:** `valuex-{env}-{resource}` (e.g. `valuex-prod-postgres`, `valuex-staging-redis`)

**Rules:**
- One module per resource type. Never duplicate logic across modules.
- Each environment (`dev`, `staging`, `prod`) has its own state file in remote backend (S3 + DynamoDB lock).
- No hardcoded values in `.tf` files — all environment-specific values in `terraform.tfvars` (which is `.gitignore`d).
- Sensitive values (passwords, API keys) come from the secret manager (AWS Secrets Manager or equivalent) — never from `tfvars` in the repo.
- `terraform plan` output must be reviewed and approved before `terraform apply` on staging and prod.
- Every `module` block has a `source` pinned to a specific version/tag — no floating references.
- All resources have tags: `env`, `product`, `managed_by = terraform`.

---

## 6.2 GitHub Actions Standards

**Workflow file naming:**

```
.github/workflows/
├── backend-ci.yml
├── mobile-ci.yml
├── web-ci.yml
├── ai-ci.yml
├── infra-validate.yml
└── deploy-staging.yml
```

**Reusable workflows** in `.github/workflows/shared/` for common steps (checkout, setup Java, setup Flutter, Docker build).

**Rules:**
- All secrets via GitHub Secrets — never hardcoded in YAML.
- Workflows triggered by `pull_request` (CI) and `push` to `develop`/`main` (CD).
- Use `paths:` filter so workflows only run when relevant files change.
- Pin all action versions to a specific SHA or version tag (e.g. `actions/checkout@v4`) — no `@main` or `@latest`.
- Every CI pipeline runs in this order: lint/format check → compile → unit tests → security scan → build artifact.
- Security scan (SAST + dependency vulnerability) is mandatory on every PR.
- Docker image builds only happen on merge to `develop` or `main` (not on every PR).

---

## 6.3 CI Pipeline Structure (Per Repo)

**Backend CI (`backend-ci.yml`):**
```
Checkout → Setup JDK 21 → Cache Maven → Checkstyle → Run tests (with PostgreSQL + Redis services) → Build JAR → Upload artifact → [if main] Build Docker image
```

Quality gates: tests must pass, coverage ≥ 80%.

**Mobile CI (`mobile-ci.yml`):**
```
Checkout → Setup Flutter 3.22 → flutter pub get → dart format --check → flutter analyze → flutter test (with coverage) → flutter build apk (release) → [if main] flutter build ios
```

Quality gates: analyzer zero warnings, coverage ≥ 70%.

**Web CI (`web-ci.yml`):**
```
Checkout → Setup Node 20 → npm ci → ESLint → Prettier check → Vitest (coverage) → tsc --noEmit → Vite build
```

Quality gates: no lint errors, coverage ≥ 70%, TypeScript zero errors.

**AI CI (`ai-ci.yml`):**
```
Checkout → Setup Python 3.11 → pip install → Ruff check → Ruff format check → pytest (coverage) → Docker build
```

Quality gates: ruff zero errors, coverage ≥ 70%.

**Infra Validate (`infra-validate.yml`):**
```
Checkout → Setup Terraform → terraform fmt --check → terraform validate → tflint → terraform plan (output only, no apply)
```

---

## 6.4 Deployment Pipeline Structure

**Staging (auto on `develop` merge):**
```
Download artifact → Run smoke tests → Build Docker image → Push to registry → kubectl rollout (rolling update) → Health check
```

**Production (on `main` merge, requires manual approval):**
```
Download artifact → Manual approval gate → Build Docker image → Push to registry → Blue/Green or Canary deploy → Health check → Smoke tests → Promote or rollback
```

---

## 6.5 Docker Standards

- Use **multi-stage builds** for all images to minimize final image size.
- Base images: `eclipse-temurin:21-jre-alpine` (backend), `python:3.11-slim` (AI), `node:20-alpine` (web build).
- Run containers as **non-root users** — add a service user in the Dockerfile.
- Set `HEALTHCHECK` in every Dockerfile.
- Image tags: `{repo}:{git-sha}` for traceability; `latest` tag only on `main` builds.
- All images are scanned for vulnerabilities before push to registry (via Trivy or equivalent).

---

## 6.6 Kubernetes Standards

- All manifests in `valuex-infra/k8s/{env}/{service}/`.
- Naming: `valuex-{service}` (e.g. `valuex-backend`, `valuex-ai`).
- Every deployment has:
  - `resources.requests` and `resources.limits` set.
  - `livenessProbe` and `readinessProbe` configured.
  - `minReplicas` and `maxReplicas` in HPA.
  - `PodDisruptionBudget` to maintain availability during rolling updates.
- Secrets in Kubernetes come from the secret manager via the secrets-store CSI driver — never plain `Secret` manifests in the repo.
- ConfigMaps for non-sensitive environment configuration.

---

## 6.7 Environment Configuration Rules

| Environment | Deploy Trigger | Approval Required |
|-------------|---------------|-------------------|
| dev | On PR merge to `develop` | No |
| staging | On PR merge to `develop` | No |
| prod | On PR merge to `main` | Yes — senior engineer |

- `dev` may use cheaper instance sizes and single replicas.
- `staging` must be a production replica (same config, scaled down).
- `prod` never receives untested code — all changes pass through staging first.

---

*End of ValueX Coding Standards v1.0*
