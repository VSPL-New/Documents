# US-113 - My Addresses: QA Testing Guide

**Sprint 5 · Cart, Checkout & Payments**

Manual test cases for the My Addresses screen and its three new endpoints: list, add, edit, rename, set as default and
delete saved addresses; the delete refusal while a cart line or a listing uses an address; the cap of ten; the new
`offline` address checks (no verification API) and the optional Google place check that is switched off by default.
Backend and mobile.

> **What ships:** `PUT /api/v1/users/me/addresses/{id}` (edit or rename), `PUT /api/v1/users/me/addresses/{id}/default`
> and `DELETE /api/v1/users/me/addresses/{id}`; the limit of 10 addresses on `POST /api/v1/users/me/addresses`;
> `ADDRESS_PROVIDER=offline` (own checks, saved `verified=false`); the optional place check
> (`ADDRESS_PLACE_CHECK_ENABLED`, off); the app's My Addresses screen (Profile > Account > My Addresses,
> `/profile/addresses`) and the edit mode of the address form. **No database migration.**
> **Not in this story:** the seller's pickup address on a listing (no screen until US-004 and US-027), geocoding, any
> address verification API, a Verified mark for addresses saved without a provider.

| Setting | Value |
|---|---|
| Backend base URL | `http://localhost:8080` |
| Address provider | `ADDRESS_PROVIDER=sandbox` (default, local) or `offline` (staging and production) |
| Place check | `ADDRESS_PLACE_CHECK_ENABLED=false` (default); on needs `ADDRESS_PROVIDER=offline` and `GOOGLE_PLACES_SERVER_API_KEY` |
| App search | `ADDRESS_SEARCH=mock` (local) or `google` with `GOOGLE_PLACES_API_KEY` (never paste or commit a key) |
| Error codes | 404 `ERROR_ADDRESS_NOT_FOUND`, 409 `ERROR_ADDRESS_IN_USE`, 400 `ERROR_ADDRESS_LIMIT_REACHED`, and for a changed address `ERROR_PINCODE_MISMATCH`, `ERROR_ADDRESS_INVALID`, `ERROR_INVALID_ADDRESS_STATE`, `ERROR_ADDRESS_NOT_VERIFIED` (sandbox/google only), `ERROR_ADDRESS_SERVICE_UNAVAILABLE` (sandbox/google only), `ERROR_ADDRESS_RATE_LIMIT` |
| Known gaps | Hindi texts need native review; the seller pickup address cannot be set until US-004 and US-027 |

> **Where to set these:** `scripts/dev-real.env` (copy `scripts/dev-real.env.example`); `scripts/start-dev-real.ps1` passes them to the backend and the app. Without a Places key the launcher uses `ADDRESS_PROVIDER=sandbox` and the mock search; with one it uses `offline` and Google search. `ADDRESS_PROVIDER`, `ADDRESS_PLACE_CHECK_ENABLED`, `GOOGLE_PLACES_SERVER_API_KEY` and `CHECKOUT_ENABLED` (default true in the launcher) can be set there to override. The backend example is `valuex-backend/.env.example`.

---

## Prerequisites

1. Backend, PostgreSQL and Redis running with `CHECKOUT_ENABLED=true` (a cart line is needed for section D) and the
   provider on `sandbox` (pincode 560038 fits Karnataka, 411045 fits Maharashtra; a street line containing "unverified"
   is refused and one containing "unavailable" behaves like an outage).
2. A seller `$SELLER` with a published goods listing `$L1`, an Aadhaar-verified buyer `$BUYER`, a second user `$OTHER`.
3. `$BUYER` has `$L1` in the cart with a delivery choice (see US-019 and US-020 testing guides) for section D.
4. Handy variables:

```bash
B="localhost:8080/api/v1"
HB="Authorization: Bearer $BUYER"
HO="Authorization: Bearer $OTHER"
J="Content-Type: application/json"
add()  { curl -s -X POST $B/users/me/addresses -H "$HB" -H "$J" -d "$1"; }
list() { curl -s $B/users/me/addresses -H "$HB" | jq '.data[] | {id,label,city,pincode,verified,defaultAddress}'; }
put()  { curl -s -i -X PUT $B/users/me/addresses/$1$2 -H "${4:-$HB}" -H "$J" -d "$3"; }
HOME='{"address":"12 MG Road, Indiranagar","landmark":"Flat 4","city":"Bengaluru","state":"Karnataka","pincode":"560038","label":"Home"}'
OFFICE='{"address":"4 Residency Road, Shanti Nagar","city":"Bengaluru","state":"Karnataka","pincode":"560025","label":"Office"}'
```

---

## A. The list (acceptance criterion 1)

| # | Steps | Expected |
|---|---|---|
| A1 | App: Profile > Account > My Addresses with no saved address | Empty state "You have no saved addresses" and an Add address button. |
| A2 | `add "$HOME"`, `add "$OFFICE"` then open My Addresses | Two cards, Home first with a Default chip, then Office. Each shows name and full address (landmark, line, city, state pincode). |
| A3 | An address saved without a name | The card is called "Address". |
| A4 | `ADDRESS_PROVIDER=sandbox`: cards show a Verified chip. `ADDRESS_PROVIDER=offline`: no card shows Verified. | Chip only when `verified` is true. |
| A5 | Pull down to refresh; turn the backend off and open the screen | Refresh reloads; with the backend off an error with Retry; Retry works when it is back. |

## B. Add and edit (acceptance criterion 2)

| # | Steps | Expected |
|---|---|---|
| B1 | Tap Add address, search a place (mock mode: type three letters), pick the suggestion, choose the Office name, Save | The form fills in; "Address saved"; the list shows the new card. The first address is the default. |
| B2 | Menu > Edit on Office | Form titled "Edit address", fields filled, Office chip selected, no "make default" switch. |
| B3 | Edit: change only the name to Studio (custom "Other") and Save | "Address updated". No address check is made (`POST /addresses/verify` is not called; in the backend log no verification). |
| B4 | Edit: change the pincode to 411001 (Karnataka) | The form shows "The pincode does not match the selected city or state"; nothing is saved. |
| B5 | Edit: change the street line to a new valid one and Save | "Address updated"; the card shows the new text. With `offline` the card has no Verified chip. |
| B6 | `put <office-id> "" "$OFFICE"` (no label) | The name is removed (the card reads "Address"). A label of 51 characters answers 400. |
| B7 | `put <id> "" "$OFFICE" "$HO"` as `$OTHER` | 404 `ERROR_ADDRESS_NOT_FOUND`; nothing changes. |

## C. Set as default and delete

| # | Steps | Expected |
|---|---|---|
| C1 | Menu on the default address | No "Set as default" item. |
| C2 | Menu > Set as default on Office | "Default address changed"; Office first with the Default chip, Home without. `SELECT count(*) FROM addresses WHERE user_id=... AND is_default;` is 1. |
| C3 | `put <id> "/default" ""` on the default | 200, unchanged. |
| C4 | Run C2 for five addresses at once (five parallel `put .../default`) | All 200; exactly one default afterwards. |
| C5 | Menu > Delete on a non-default address, Cancel | Nothing is deleted. |
| C6 | Delete again and confirm | "Address deleted"; the card is gone. |
| C7 | Delete the default address while others exist | The oldest remaining address becomes the default. |
| C8 | Delete the last address | Allowed; the empty state shows. |
| C9 | `curl -X DELETE $B/users/me/addresses/<id> -H "$HO"` as another user | 404 `ERROR_ADDRESS_NOT_FOUND`. |

## D. An address that is in use

| # | Steps | Expected |
|---|---|---|
| D1 | `$BUYER` chose home delivery to Home for a cart line; delete Home | 409 `ERROR_ADDRESS_IN_USE`; the app says "This address is used by an item in your cart or a listing. Remove it there first"; the address stays. |
| D2 | Remove the line from the cart; delete Home again | Deleted. |
| D3 | `UPDATE listings SET pickup_address_id = '<seller-address-id>' WHERE id = '<L1>';` then the seller deletes that address | 409 `ERROR_ADDRESS_IN_USE`. Clear the column and delete again: deleted. |
| D4 | The buyer chose delivery to Home; edit Home's street line | The cart line has no delivery choice any more (`delivery_mode` is null); Choose delivery shows again and a new shipping cost is quoted. |
| D5 | Same line; only rename Home | The delivery choice stays. |
| D6 | An address that only an old order snapshot used | Deleting it works (orders keep their own copy). |

## E. The cap of ten

| # | Steps | Expected |
|---|---|---|
| E1 | Save ten addresses, then add an eleventh (app or `add "$OFFICE"`) | 400 `ERROR_ADDRESS_LIMIT_REACHED`; the app says "You can save up to 10 addresses. Delete one to add another". Delete one, add again: works. |

## F. Address checks without a verification API

Run the backend with `ADDRESS_PROVIDER=offline`, `ADDRESS_PLACE_CHECK_ENABLED` unset.

| # | Steps | Expected |
|---|---|---|
| F1 | `add "$HOME"` | 201 with `"verified": false`; `verified_at` is null in the database. No call leaves the server (check the network, no Google traffic). |
| F2 | `add` with pincode 110001 and state Karnataka | 400 `ERROR_PINCODE_MISMATCH`. |
| F3 | `curl -s -X POST $B/addresses/verify -H "$HB" -H "$J" -d "$HOME"` | 200 with `"verified": false`. In the app's form, no "Address verified" line appears and no error. |
| F4 | A line shorter than 10 characters, an unknown state | 400 `ERROR_ADDRESS_INVALID` / `ERROR_INVALID_ADDRESS_STATE`. |
| F5 | Start with `ADDRESS_PLACE_CHECK_ENABLED=true` and no key | The backend refuses to start with "GOOGLE_PLACES_SERVER_API_KEY is required". |

## G. The optional place check (only when you want to try it)

Needs `ADDRESS_PLACE_CHECK_ENABLED=true`, `GOOGLE_PLACES_SERVER_API_KEY` (set in the environment, never in a file) and a
real `placeId` from the app's Google search. Skip this section while the switch stays off.

| # | Steps | Expected |
|---|---|---|
| G1 | Save an address picked from a suggestion without editing it | `verified` is true; the card shows Verified. |
| G2 | Pick a suggestion and edit the pincode (still valid for the state) | Saved with `verified` false. |
| G3 | Type the address by hand (no place id) | Saved with `verified` false; no Google call. |
| G4 | Block outbound access to Google and save a picked address | Saved with `verified` false; the save is not refused. |
| G5 | Save the same picked place twice within 10 minutes | One Place Details call (metric `address.placecheck` and the Google usage page). |

## H. Cost guard in the app

| # | Steps | Expected |
|---|---|---|
| H1 | With a Google key, pick a suggestion and inspect the Place Details request | Header `X-Goog-FieldMask: id,formattedAddress,addressComponents`, nothing else. |
| H2 | Type quickly in the search box | One search request about 300 ms after you stop typing, and none under 3 characters. |

---

## Automated tests

```bash
# backend (Docker running; on this machine set JAVA_TOOL_OPTIONS="-Dapi.version=1.44 -Duser.timezone=Asia/Kolkata")
mvn test -Dtest='AddressManagementServiceTest,AddressManagementIntegrationTest,AddressOfflineIntegrationTest,OfflineAddressVerificationAdapterTest,PlaceCheckTest,PlaceMatcherTest,GooglePlaceDetailsAdapterTest,AddressProviderConfigTest,CartAddressUsageAdapterTest,ListingAddressUsageAdapterTest,AddressServiceTest,AddressCreationServiceTest,AddressControllerTest'

# mobile
flutter test test/features/address test/features/cart/address_form_sheet_test.dart --dart-define=SKIP_PIXEL_CONTRAST=true
```
