# US-113: My Addresses - Implementation Plan

## 1. Header

| Field | Value |
|---|---|
| Story | US-113 - My Addresses (a placeholder in `user-stories.md`; this plan proposes the detail, marked **Proposed** below) |
| Sprint | Sprint 5 - Cart, Checkout & Payments |
| Story points | **Not agreed.** Proposed 5 SP: Part 1 (manage addresses) about 3, Part 2 (Google auto-complete set-up and offline checks, option A) about 1, Part 3 (optional Place Details check, option B, switched off by default) about 1. See G1 |
| Repos involved | `valuex-backend` (`user` module: edit, set default and delete endpoints; an offline verification adapter; an optional Place Details check). `valuex-mobile` (My Addresses screen, edit mode of the address form, "Verified" mark hidden for unverified addresses, Google Places config). No `valuex-ai` or `valuex-web` change. **No database migration.** Infra: Google Cloud keys (section 3.2) |
| Dependencies | US-020 (adds `POST /users/me/addresses`, `label`, the cart's use of `addresses`; **built and merged**), US-108 (address component and verification; built) |
| Blocks | Nothing in Sprint 5. US-004 and US-027 reuse the same component and endpoints |
| Design source | [Sprint 5 LLD](../LLD/Sprint-5-Cart-Checkout-Payments-LLD.md) Part M (placeholder), B.4 and B.6 (as-built US-020), G7 and G18 of N.4. No Part M2 exists yet; this plan lists what it needs |
| Branches | `feature/US-113-my-addresses` in `valuex-backend` and `valuex-mobile`, `docs/US-113-my-addresses` in `Documents`; cut from updated `main` (confirm with `git log` that the US-020 commits are on it). The in-use check reads `cart_items.delivery_address_id` (V41/V42) |

## 2. Story Recap

**As a** user **I want to** see and manage the addresses I have saved **so that** I can reuse them for delivery, pickup and finding items near me.

Status in the story file: *placeholder; the acceptance criteria are only a starting point.* Open there: story points, and the rules for deleting the default address or an address used by an open order.

**Acceptance criteria (as written, to be detailed):**
- Given I am logged in, when I tap "My Addresses" under Account in the Profile tab, then I see my saved addresses with their names and full addresses, my default first.
- And I can add, edit, rename, delete and choose my default address.

**Edge cases, validation rules, error scenarios:** "To be detailed" in the story. Section 3 proposes them; none is agreed yet.

**Direction history:** 2026-11-22 the plan used MapmyIndia (auto-complete, validation, geocoding). 2026-11-23 MapmyIndia pricing was too high, so the plan **falls back to Google** for auto-complete and **drops geocoding** (nothing uses coordinates yet). The Google Address Validation API is **not** used: you chose (2026-11-23) to plan **option A** (offline checks only) as the working mode and **option B** (check the chosen place with Google Place Details) as built but **configurable, off by default**, to be switched on only if A alone proves not enough in use.

## 3. Design Reference and Key Decisions

### 3.1 What exists today (read from the code)

| Piece | State |
|---|---|
| `addresses` table (V11) | `address_line1`, `address_line2` (house, landmark), `city`, `state`, `pincode`, `place_id`, `verified`, `verified_at`, `is_default`, `label` (US-020), one default per user by a partial unique index |
| `AddressController` | `GET /users/me/addresses` (default first), `POST /users/me/addresses` (verifies, then saves), `POST /addresses/verify`. **No update, delete or set-default endpoint** |
| `AddressService` / `AddressCreationService` | Verification (rate limited; errors `ERROR_ADDRESS_INVALID`, `ERROR_INVALID_ADDRESS_STATE`, `ERROR_PINCODE_MISMATCH`, `ERROR_ADDRESS_NOT_VERIFIED`, `ERROR_ADDRESS_SERVICE_UNAVAILABLE`, `ERROR_ADDRESS_RATE_LIMIT`); create under a per-user advisory lock, provider call outside the transaction; always stores `verified=true` today |
| Provider | `AddressVerificationPort.verify(AddressInput)` returning `AddressVerificationResult(Outcome, AddressInput)` with `Outcome` = `VERIFIED`, `NOT_VERIFIED`, `PINCODE_MISMATCH`. Adapters `sandbox` (uses `PincodeZones.matches(pincode, state)`; markers "unverified" and "unavailable" for tests) and `google` (Address Validation API), chosen by `valuex.address.provider` in `AddressProviderConfig` (default `sandbox`) |
| Auto-complete | Already in the app: `GooglePlacesService` (Places API New, India only, session tokens, field mask) or a mock, chosen by `ADDRESS_SEARCH` (`mock` / `google`) and `GOOGLE_PLACES_API_KEY` in `AppConfig`; the mock is refused in prod. **Not on the backend** |
| Who points at an address | `cart_items.delivery_address_id` and `listings.pickup_address_id` (foreign keys, no `ON DELETE`). Orders keep their own JSON snapshot (LLD Part M) |
| Mobile | `features/address`: `AddressRepository` (list, verify, create), `savedAddressesProvider`, `AddressFormSheet` (add only), `AddressSearchField`, `AddressVerificationStatus`. The Profile row "My Addresses" (`profile_screen.dart`) has no action yet |
| LLD G18 | Says a guard `ERROR_ADDRESS_IN_USE` is "a one-line check in `AddressService`". **There is no delete to guard yet**, so US-113 adds delete and the guard together |

### 3.2 Google, what this story needs

| API | Used for | Where | Cost note |
|---|---|---|---|
| Places API (New) **Autocomplete** + **Place Details** | Search as the user types, then fetch the chosen place's address parts | Mobile app (already built) | With a session token, the autocomplete requests and the closing Place Details are billed once, by the Place Details field mask. **Ask only for `formattedAddress` and `addressComponents`**: any other field (hours, ratings, and also `displayName`) moves the call to a higher-priced tier. The app's mask today includes an unused `displayName`; this story removes it |
| Places API (New) **Place Details**, server side | Option B only: re-read the chosen place and compare | Backend | One call per save of a place-based address; off by default. Mask is `addressComponents` only |
| Address Validation API | **Not used** (option C). The existing `google` adapter stays in the code, unchanged, as an unused choice | - | - |
| Geocoding API | **Not used** (skipped by you) | - | - |

Keys (never committed, never pasted in chat):
- **App key** `GOOGLE_PLACES_API_KEY`: Places API (New) only; restricted by Android package name and SHA-1 and by iOS bundle id. It is inside the app, so quota alerts matter.
- **Server key** (option B only, `GOOGLE_PLACES_SERVER_API_KEY`): Places API (New) only; restricted to the server IP addresses. Not needed while B is off.
- A Google Cloud project with billing enabled, and a budget alert (G3).

### 3.3 Proposed design (needs your confirmation; see section 7)

**Part 1 - manage addresses (no provider dependency).** New in the `user` module, in a new `AddressManagementService` so `AddressService` (verify, list) and `AddressCreationService` stay small:

| Action | Endpoint | Rule |
|---|---|---|
| Edit / rename | `PUT /users/me/addresses/{id}` | Only `label` changed: saved without any verification call. Any address field changed: verified again through the verification port (outside the transaction, as create). Not the caller's address: 404 `ERROR_ADDRESS_NOT_FOUND` |
| Set default | `PUT /users/me/addresses/{id}/default` | Under the same per-user advisory lock as create; clears the old default first; already default is a no-op 200 |
| Delete | `DELETE /users/me/addresses/{id}` | 409 `ERROR_ADDRESS_IN_USE` if a cart line or a listing points at it (open orders hold a snapshot, so they do not block). Deleting the default promotes the oldest remaining address; deleting the last address is allowed |

Also: at most 10 saved addresses per user (`ERROR_ADDRESS_LIMIT_REACHED`, applied to create too); editing an in-use address is allowed, and a changed address field clears that cart line's delivery choice so the buyer chooses again and gets a new quote. Labels: up to 50 characters, trimmed, blank becomes none (rules of US-108). Full addresses never go to logs; a metric `address.managed{action}` counts the three actions.

**Part 2 - option A: offline checks, no verification API (the working mode).**
- New `OfflineAddressVerificationAdapter` behind the existing `AddressVerificationPort`, chosen by `valuex.address.provider=offline`. It makes **no network call**. After the existing request validation (line length, 6-digit pincode, supported state) it applies `PincodeZones.matches(pincode, state)`: a mismatch gives `PINCODE_MISMATCH` (the existing pincode message); otherwise it gives a new outcome `ACCEPTED_UNVERIFIED`.
- `Outcome.ACCEPTED_UNVERIFIED` is added; `AddressService.assertAccepted` accepts it; `VerifiedAddressResponse.verified` and the create and update paths store `verified` and `verified_at` **from the outcome** instead of always true (so `VERIFIED` stays `true`, as `sandbox` and `google` keep working). Offline addresses are saved `verified=false`, `verified_at` null.
- The default of `valuex.address.provider` is **not** changed in this story (`sandbox` stays the dev default); production and staging set `ADDRESS_PROVIDER=offline` (G4).
- Auto-complete needs no backend work: `ADDRESS_SEARCH=google` and `GOOGLE_PLACES_API_KEY` in the app's production build, plus the key set-up of 3.2. The app keeps its 300 ms debounce, 3-character minimum, session tokens and manual entry.
- Consequences (G5): the "Verified" mark is hidden in the app for `verified:false` (a quiet line is not shown for A, to avoid scaring the user); `ERROR_ADDRESS_NOT_VERIFIED` and the "provider down" error stay in the code but cannot be reached in `offline` mode; US-108's acceptance criteria and the LLD text that name a provider check are updated.

**Part 3 - option B: Place Details check, built but off by default.**
- Setting `valuex.address.place-check.enabled` (env `ADDRESS_PLACE_CHECK_ENABLED`, default **false**) with `timeout-seconds` and the server key (3.2). With the switch off nothing is called and no server key is required; startup fails clearly only if the switch is on and the key is blank.
- New `PlaceDetailsPort` (`Optional<PlaceAddress> fetch(placeId)`; `PlaceAddress` = state, city, pincode) with `GooglePlaceDetailsAdapter` (Place Details (New), `X-Goog-FieldMask: addressComponents`, key in the header, never logged) and a `NoPlaceDetailsAdapter` (always empty) used when the switch is off. `OfflineAddressVerificationAdapter` receives the port.
- Rule, only when the switch is on **and** the request carries a `placeId` **and** the offline checks passed: fetch the place; if its state, city and pincode equal the submitted ones (compared case-insensitively, state through the existing state normaliser) the outcome is `VERIFIED` (`verified=true`); a difference, an unknown place, a provider error or a timeout gives `ACCEPTED_UNVERIFIED`. **B never refuses a save and never raises the provider-down error**: it can only upgrade an address to verified. A manual address (no `placeId`) stays unverified.
- Metric `address.placecheck{result}` (`match`, `mismatch`, `not_found`, `error`, `skipped`).
- Cost: one Place Details call per save of a place-based address; the create path verifies again on the server, so a short cache of the place by `placeId` (10 minutes, Redis, key is the place id, never the address) is proposed to avoid a second call (G6).

**Where the `verified` meaning ends up:** `true` = confirmed against a Google place (only with B on, or `sandbox`/`google` modes); `false` = passed our offline checks only. Nothing else reads `verified` (checked earlier: only the address module and the app status line).

### 3.4 Mobile (Flutter, Riverpod, go_router)

`MyAddressesScreen` at `/profile/addresses`, opened from the Profile row; a card per address (name or "Address", full address, Default chip, and a Verified chip only when `verified: true`), a menu with Edit, Rename, Set as default and Delete (confirm dialog; the in-use refusal explains why), an empty state with "Add address", and "Add address" using `AddressFormSheet`, which gets an edit mode. Re-read the list after every action (`savedAddressesProvider`, shared with `DeliveryScreen` and the Home saved-location pop-up). Texts in `app_en.arb` and `app_hi.arb`.

## 4. Implementation Steps

### Backend, Part 1 (`valuex-backend`)
- [ ] Branch from updated `main`; confirm the US-020 commits are on it.
- [ ] `UpdateAddressRequest` (label, address, landmark, city, state, pincode, placeId; validation as `CreateAddressRequest`) and the error constants `ERROR_ADDRESS_NOT_FOUND`, `ERROR_ADDRESS_IN_USE`, `ERROR_ADDRESS_LIMIT_REACHED` in the module's existing error class.
- [ ] `AddressRepository`: `findByIdAndUserId`, `countByUserId`, `oldestOtherThan(userId, id)` (promotion), delete through the repository.
- [ ] `AddressUsagePort` in `user/application/port` with `isInUse(addressId)`; adapters read `cart_items.delivery_address_id` (cart module) and `listings.pickup_address_id` (listing module), the same way as `CartAddressAdapter` and `CartPickupAdapter`, so `user` does not import them. A second port method clears the cart line's delivery choice when an in-use address changes.
- [ ] `AddressManagementService`: `update`, `setDefault`, `delete` (lock `address:<userId>`, verification outside the transaction on a changed address field, promotion on deleting the default); the 10-address cap also in `AddressCreationService`.
- [ ] `AddressController`: three endpoints with OpenAPI notes and the error list.
- [ ] Metric `address.managed{action}`.

### Backend, Part 2 (option A)
- [ ] `Outcome.ACCEPTED_UNVERIFIED`; `AddressService.assertAccepted` accepts it; `VerifiedAddressResponse.verified`, the create and the update paths store `verified` and `verified_at` from the outcome.
- [ ] `OfflineAddressVerificationAdapter` (no network, the offline rules of 3.3, no address text in logs); wiring `valuex.address.provider=offline` in `AddressProviderConfig`; `ADDRESS_PROVIDER` documented with the new value.
- [ ] Existing `sandbox` and `google` adapters and their tests untouched and still green.

### Backend, Part 3 (option B, off by default)
- [ ] `ValuexProperties.AddressSettings.PlaceCheck` (`enabled`, `serverApiKey`, `timeoutSeconds`); `application.yml` keys `ADDRESS_PLACE_CHECK_ENABLED` (default false), `GOOGLE_PLACES_SERVER_API_KEY`; startup check only when enabled.
- [ ] `PlaceDetailsPort`, `PlaceAddress`, `GooglePlaceDetailsAdapter` (RestClient with timeouts; field mask `addressComponents`; mapping `administrative_area_level_1` to state, `locality` to city, `postal_code` to pincode), `NoPlaceDetailsAdapter`; conditional wiring on the switch.
- [ ] The comparison in one small pure method (`PlaceMatcher`) so it is easy to test; the place-check call inside `OfflineAddressVerificationAdapter` after the offline checks, fail-soft to `ACCEPTED_UNVERIFIED`.
- [ ] Metric `address.placecheck{result}`; the optional 10-minute place cache (G6).

### Mobile (`valuex-mobile`)
- [ ] `AddressRepository`: `update`, `setDefault`, `delete`; `ApiConstants` entries.
- [ ] `MyAddressesScreen`, address card widget, delete-confirm dialog, route in `route_names.dart` and `app_router.dart`, Profile row action in `profile_screen.dart` (replaces the no-action row).
- [ ] `AddressFormSheet` edit mode (starts from a `SavedAddress`, rename-only path without re-verification).
- [ ] `AddressVerificationStatus` and the card show "Verified" only for `verified: true`; nothing is shown for `false`.
- [ ] **Cost fix in `GooglePlacesService.details`:** the field mask is `id,displayName,formattedAddress,addressComponents`, and `displayName` is read nowhere in `parseDetails`. Change it to `formattedAddress,addressComponents` (address fields only) and add a test that fails if the mask gains another field. Debounce (300 ms), 3-character minimum and session tokens are already in place (`address_providers.dart`), so no change there.
- [ ] Production build config uses `ADDRESS_SEARCH=google` and `GOOGLE_PLACES_API_KEY` (key never committed).
- [ ] `app_en.arb` and `app_hi.arb` texts; run `flutter gen-l10n`, `dart format lib test`, `flutter analyze`.

### Docs (`Documents`)
- [ ] LLD: new Part M2 (replace the Part M placeholder), as-built section, close G18 and G7; update the US-108 text that names a provider check and its "verified" rule; `user-stories.md` detail for US-113 and `Sprint-plan.md` with the agreed points; deployment notes for `ADDRESS_PROVIDER=offline`, `ADDRESS_SEARCH=google`, the two Google keys and `ADDRESS_PLACE_CHECK_ENABLED`; testing guide.

## 5. Test Plan (target above 90% on new and changed code)

| Area | Cases |
|---|---|
| `AddressManagementService` unit | Rename only: no verification call, `updatedAt` moves. Address change: verification called; `PINCODE_MISMATCH` and the other refusals map to the existing codes and nothing is saved. Someone else's id: `ERROR_ADDRESS_NOT_FOUND`. Set default: old default cleared, already default is a no-op. Delete: in use 409; unused deleted; default deleted promotes the oldest; last address deleted. Eleventh address refused. Editing an in-use address clears the cart line's choice |
| Integration (Testcontainers) | Two parallel set-default calls leave exactly one default (partial unique index plus lock). Delete refused for an address on a cart line and on a listing's `pickup_address_id`; allowed once the line is removed |
| Controller | 401 without a token, 400 on blank or too-long label and bad pincode, 404, 409, 200/204 shapes |
| Option A adapter | Matching pincode and state gives `ACCEPTED_UNVERIFIED` and the address is saved with `verified=false`, `verified_at` null; mismatch gives `PINCODE_MISMATCH`; no network call is made (no HTTP client in the adapter); `sandbox` and `google` modes still give `verified=true` (existing tests stay green); the address text is never logged |
| Option B | Switch off: `NoPlaceDetailsAdapter`, no call, no key needed. Switch on with a fake HTTP server: equal state, city and pincode gives `VERIFIED`; one field different gives `ACCEPTED_UNVERIFIED`; place not found, 4xx, 5xx, timeout and garbage give `ACCEPTED_UNVERIFIED` and never an error; manual address (no `placeId`) makes no call; offline refusal (pincode mismatch) makes no call; the key is sent in the header and never logged; startup fails with the switch on and a blank key; the cache avoids a second call for the same place; `PlaceMatcher` cases (case, spacing, state alias) |
| Mobile cost guard | `GooglePlacesService.details` sends the field mask `formattedAddress,addressComponents` and nothing else (test on the request header) |
| Mobile | Repository calls; screen: list default first, empty state, set default refreshes, delete confirm, in-use message, error state with retry; form sheet edit mode (rename-only skips verification); no "Verified" mark for `verified:false`, mark shown for `true`; Hindi and English strings present |

## 6. Validation Checklist

- [ ] AC: My Addresses shows names and full addresses, default first.
- [ ] AC: add, edit, rename, delete and set default each work and the list refreshes.
- [ ] Exactly one default after every action (tested under parallel calls).
- [ ] An address on a cart line or listing cannot be deleted; the message says why.
- [ ] An edited address is checked again; a rename is not.
- [ ] Only the owner can read or change an address (404 otherwise, no leak).
- [ ] Label up to 50 characters; pincode 6 digits; state supported; pincode matches state; line 10 to 255 characters; at most 10 addresses.
- [ ] Option A: no external call on save; address saved `verified=false`; the app shows no "Verified" mark.
- [ ] Option B: switch off by default; with it on, a matching place gives `verified=true`, anything else saves as unverified, and it never blocks a save.
- [ ] No full address in logs; no key or secret in any file; the server key lives only in the backend environment; the app key is restricted by package and bundle id.
- [ ] Auto-complete fills the form; the user can still edit and enter by hand.
- [ ] `DeliveryScreen` and the Home saved-location pop-up still work with the new list.
- [ ] English and Hindi texts for every new string; Hindi flagged for native review.
- [ ] Build, checkstyle (120 chars), SonarQube clean for new code; mobile `dart format`, `flutter analyze`.

## 7. Open Gaps / Questions

### 7.1 Your answers (recorded)

| # | Decision |
|---|---|
| D1 | Both parts (manage addresses and auto-complete) are in US-113 |
| D2 | **Changed 2026-11-23:** Google replaces MapmyIndia for auto-complete (pricing). Auto-complete stays in the app as built (Places API New) |
| D3 | **Changed 2026-11-23:** geocoding is skipped; no coordinates, no migration |
| D4 | **Changed 2026-11-23:** address validation by an API is not used. Plan **A** (offline checks) as the working mode and **B** (Place Details check) built, **configurable and off by default**; enable B only if A alone proves not enough |
| D5 | Delete blocked while a cart line or listing uses the address; deleting the default promotes the oldest remaining; the last address can be deleted |
| D6 | Editing an in-use address is allowed; a changed address field clears that cart line's delivery choice |
| D7 | At most 10 saved addresses per user, `ERROR_ADDRESS_LIMIT_REACHED` |
| D8 | Provider-style failure while editing: with A there is no provider; with B failures never block (fail soft). A rename always works |
| D9 | The seller pickup address has no writer until US-004 and US-027; out of scope |
| D10 | US-020 PRs are merged |
| D11 | Story points are re-estimated (see D12) |
| D12 | G1: 5 SP (Part 1 about 3, option A about 1, option B about 1); the sprint plan row and the story file are updated in the docs step |
| D13 | G2: auto-complete stays in the app (restricted key, quota alert); no backend proxy |
| D14 | G3: a Google Cloud project with billing exists; the app key (and the server key when B is enabled) is created outside the chat; budget alert and daily quota cap on Places API (New) |
| D15 | G4: `ADDRESS_PROVIDER=offline` only in staging and production; the dev default stays `sandbox` |
| D16 | G5: no address is `verified=true` while B is off; the "Verified" mark is hidden; US-108 and the LLD are updated |
| D17 | G6: 10-minute Redis cache of the place by `placeId` (used only when B is on) |
| D18 | G7: the second Place Details call for B is an accepted cost; check the SKU and price before enabling B |
| D19 | G8: a missing postal code or city counts as a mismatch and the address is saved unverified |
| D20 | G9: English first, Hindi in `app_hi.arb`, flagged for native review |
| D21 | G10: Places UI Kit is not used anywhere for now; revisit only if the bill is high, as its own story |

### 7.2 Open gaps
None. All gaps G1 to G10 were answered on 2026-11-23 (D12 to D21).

## 8. As built (2026-11-23)

All steps of section 4 are built. Deviations from the plan:

- **Field mask in the app:** `GooglePlacesService.details` asks for `id,formattedAddress,addressComponents`, not `formattedAddress,addressComponents`. The form reads the place id from the answer's `id`, which is a free field; `displayName` (unused) was dropped. The server-side place check asks for `addressComponents` only, as planned.
- **`AddressCreationService`** takes the new `AddressLock` bean instead of a `JdbcTemplate` (so create, edit, set default and delete share one lock); its test was updated.
- **Option B wiring:** the switch is read in `AddressProviderConfig.placeCheck`, which exists only when `ADDRESS_PROVIDER=offline`; with the switch off it returns `NoPlaceCheck` and no server key is needed.
- **Mobile:** `AddressRepository.verify` now returns the `verified` flag (was void) and the verification controller has a new status `accepted` (no text shown). The existing tests that stub `verify` were updated to return a bool.
- **Docs:** the story detail is in `user-stories.md` (US-113 and a note in US-108), the Sprint plan row has 5 SP (the Sprint 5 and grand totals in the plan table were not changed), and the LLD has Part M rewritten as built (version 0.5) and G18 done. Testing guide: `Manual Testing Guides/US-113-Testing-Guide.md`.

**Status: Approved and built** (2026-11-23; all gaps answered; pending the push and pull request approvals)
