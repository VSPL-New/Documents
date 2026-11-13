# US-118 — Real Estate Listing Specifics: QA Testing Guide

**Sprint 3 · Discovery & Search**

Manual test cases for the property flow: the Buy, Rent or Lease choice before property prices, the intent rules per
property type, the price the seller must enter for the chosen intent, and the owner's **Mark as Sold, Rented or Leased**
action, including a deal made outside JustQlic and a property that is still in review. The backend is checked with
`curl` and SQL; the app is checked in Search and My Listings.

> **What ships:** `POST /api/v1/listings/{id}/close`; `closeOutcome` and `closedOutcome` on My Listings cards; the check
> of a Buy, Rent or Lease choice at category level (L1 and L2) in search; `ERROR_PRICE_REQUIRED_FOR_INTENT` when a
> seller saves a property without the price for the chosen intent; migration `V28` (backend). In the app: the Mark as
> action on My Listings, the Rented and Leased labels, a price range cleared when the intent changes, and an intent
> chooser that stops offering an option the server refused (mobile).
> **Already built before this story and only re-checked here:** the Buy, Rent or Lease prompt, "Starting from" for New
> Developments, no cart or Buy Now on a property (US-006, US-011, US-012).
> **Not in this story:** chat, call, video call and price negotiation (Sprint 4); saved listings and their
> notifications (US-073: a saved property is not marked unavailable and its savers are not told yet); the Admin review
> queue screen (US-054).

| Setting | Value |
|---|---|
| Backend base URL | `http://localhost:8080` |
| Close endpoint | `POST /api/v1/listings/{listingId}/close` with `{"outcome": "SOLD" \| "RENTED" \| "LEASED"}`; the owner only |
| Closable stages | published, inquiry pending, negotiation in progress, offer accepted, expired, in Trust & Safety review, revision required |
| Error codes | `ERROR_NOT_A_PROPERTY_LISTING`, `ERROR_LISTING_NOT_CLOSABLE`, `ERROR_INTENT_NOT_SUPPORTED`, `ERROR_PRICE_REQUIRED_FOR_INTENT` (all 400); `LISTING_NOT_FOUND` (404) |
| Known gaps | Nothing creates the inquiry and negotiation stages yet (Sprint 4); use SQL to put a listing in one (case C). Saved listings are US-073 |

---

## Prerequisites

1. Backend, PostgreSQL, Redis and OpenSearch running (see the US-011 guide); the app running against it.
2. Two `ACTIVE` accounts: a seller (`$SELLER`) and a buyer (`$BUYER`), each with an access token.
3. As the seller publish these listings (the free Basic plan is enough):

| # | Category | Intent | Price | Notes |
|---|---|---|---|---|
| P1 | Homes | Sale | sale price 5000000 | |
| P2 | Homes | Rent | monthly rent 25000 | |
| P3 | Land | Lease | monthly rent 40000 | |
| P4 | New Developments | Sale | minimum price 7500000 | shows "Starting from" |
| P5 | Commercial | Lease | monthly rent 90000 | leave the optional total lease amount empty |
| G1 | any goods category (for example Smartphones) | | 4500 | a goods listing |

4. Handy variables:

```bash
B="localhost:8080/api/v1"
HS="Authorization: Bearer $SELLER"
HB="Authorization: Bearer $BUYER"
close() { curl -s -X POST -H "$HS" -H "Content-Type: application/json" -d "{\"outcome\":\"$2\"}" "$B/listings/$1/close"; }
```

---

## A. Buy, Rent or Lease in search (buyer)

| ID | Steps | Expected |
|---|---|---|
| TC-001 | In the app open Search, choose the Real Estate category | The "Choose Buy, Rent or Lease" sheet opens before any result or price is shown |
| TC-002 | Close the sheet without choosing | A prompt "Choose Buy, Rent or Lease to see properties" with a Choose button; no results |
| TC-003 | Choose Rent | Rent listings only (P2); a chip "Rent. Change" is shown; goods are never in the list |
| TC-004 | `curl -s -H "$HB" "$B/search/listings?category=<Real Estate L1 code>"` (no intent) | 400, `ERROR_INTENT_REQUIRED` |
| TC-005 | Same with `&transactionIntent=SALE`, then `RENT`, then `LEASE` | 200 each; every listing in the answer has that intent; a Sale and a Rent listing are never in one answer |
| TC-006 | Land category (L2), `transactionIntent=RENT` | 400, `ERROR_INTENT_NOT_SUPPORTED` (Land has Sale and Lease only) |
| TC-007 | Land category (L2), `transactionIntent=SALE`, then `LEASE` | 200 each |
| TC-008 | New Developments category with `transactionIntent=RENT` or `LEASE` | 400, `ERROR_INTENT_NOT_SUPPORTED` (Sale only) |
| TC-009 | Shared and Managed Living category, `SALE` and `LEASE` | 400, `ERROR_INTENT_NOT_SUPPORTED`; `RENT` gives 200 |
| TC-010 | Commercial category, each of `SALE`, `RENT`, `LEASE` | 200 each |
| TC-011 | A goods category with `transactionIntent=SALE` | 400, `ERROR_INTENT_NOT_SUPPORTED` |
| TC-012 | With Rent chosen in the app, open Filters and enter a price range (for example 10000 to 30000), apply, then choose Lease through the chip | The price range is cleared (the filter badge goes away); the Lease results load without it |
| TC-013 | Choose the same intent again from the chip | The price range is kept |
| TC-014 | In the app open the Land category (L2) and choose Rent | The server refuses it; the chooser opens again with the message "This option is not available for this property type" and without a Rent option; choosing Buy or Lease then searches |
| TC-015 | `...&priceMin=30000&priceMax=10000&transactionIntent=RENT` | 400, `ERROR_INVALID_PRICE_RANGE` |
| TC-016 | Look at P4 in the Sale results | The card says "Starting from" with the minimum price; the details page agrees |
| TC-017 | Open P1 as the buyer | Details show the sale price; there is no cart, Add to cart or Buy Now |

---

## B. Price for the chosen intent (seller)

The seller saves the Item Details of a property (`PATCH /api/v1/listings/{id}` with the attributes) or uses the
app's Item Details screen.

| ID | Steps | Expected |
|---|---|---|
| TC-020 | Homes, intent Sale, no sale price | 400, `ERROR_PRICE_REQUIRED_FOR_INTENT`, "Enter the price for your option", `details.field` = `sale_price`; the app shows the same text |
| TC-021 | Homes, intent Rent, no monthly rent | 400, `ERROR_PRICE_REQUIRED_FOR_INTENT`, field `monthly_rent` |
| TC-022 | New Developments, Sale, no minimum price | 400, `ERROR_PRICE_REQUIRED_FOR_INTENT`, field `price_min` |
| TC-023 | Land, Lease, no monthly rent | 400, `ERROR_PRICE_REQUIRED_FOR_INTENT`, field `monthly_rent` |
| TC-024 | Commercial, Lease, monthly rent present, total lease amount empty | Saved; the lease amount stays optional |
| TC-025 | Shared and Managed Living, Rent, no monthly rent | 400, `ERROR_PRICE_REQUIRED_FOR_INTENT` |
| TC-026 | Homes, Sale, sale price above 100000000 | 400, `ERROR_ATTRIBUTE_INVALID` for `sale_price` (the ₹10 crore maximum) |
| TC-027 | Homes with a missing city (any other required field) | 400, `ERROR_ATTRIBUTE_REQUIRED` (not the price code) |
| TC-028 | Homes with Sale chosen and the monthly rent filled but no sale price | 400, `ERROR_PRICE_REQUIRED_FOR_INTENT` for `sale_price`; the listing price is the sale price, never the rent |

---

## C. Mark as Sold, Rented or Leased (owner)

Take P1 to P5 to the stages below with SQL where the app cannot (the inquiry and negotiation stages arrive in Sprint 4):

```sql
UPDATE listings SET status = 'NEGOTIATION_IN_PROGRESS' WHERE id = '<P1 id>';
```

| ID | Steps | Expected |
|---|---|---|
| TC-030 | Seller opens My Listings | P1 to P5 show a "Mark as Sold", "Mark as Rented" or "Mark as Leased" link that follows their intent (P1 Sold, P2 Rented, P3 and P5 Leased, P4 Sold); G1 has no such link |
| TC-031 | Tap "Mark as Rented" on P2 | A sheet "Mark this property as Rented?" says the deal can be inside or outside JustQlic and cannot be undone |
| TC-032 | Cancel | Nothing is sent; the link is still there |
| TC-033 | Confirm | "Property marked as Rented"; the card now reads **Rented** (not Sold), loses the link, and the Sold tab and count include it |
| TC-034 | `curl -s -H "$HB" "$B/listings/<P2 id>/public"` as the buyer | 404, `ERROR_LISTING_NOT_AVAILABLE`; P2 is gone from search |
| TC-035 | `close <P1 id> SOLD` | 200, `data` = `{listingId, status: "SOLD", outcome: "SOLD"}` |
| TC-036 | `close <P3 id> LEASED` | 200; the card reads Leased |
| TC-037 | In SQL: `SELECT status, closed_outcome, price FROM listings WHERE id = '<P1 id>'` | `SOLD`, `SOLD`, and the price is still 5000000 |
| TC-038 | In SQL: `SELECT action, reason FROM listing_status_history WHERE listing_id = '<P1 id>' ORDER BY changed_at DESC LIMIT 1` | `MARK_PROPERTY_CLOSED`, `SOLD`; there is no buyer and no deal price anywhere in the row |
| TC-039 | `close <P4 id> RENTED` (New Development is Sale) | 400, `ERROR_INTENT_NOT_SUPPORTED`; the listing stays published |
| TC-040 | `close <P5 id> SOLD` (Commercial listed for Lease) | 400, `ERROR_INTENT_NOT_SUPPORTED` |
| TC-041 | `close <P2 id> RENTED` again | 400, `ERROR_LISTING_NOT_CLOSABLE` (double tap or second request) |
| TC-042 | `close <G1 id> SOLD` | 400, `ERROR_NOT_A_PROPERTY_LISTING`; goods reach Sold only through an order |
| TC-043 | A property still in draft | 400, `ERROR_NOT_A_PROPERTY_LISTING` (never published) |
| TC-044 | As the buyer, `curl -X POST -H "$HB" ... "$B/listings/<P4 id>/close"` | 404, `LISTING_NOT_FOUND`; only the owner can close |
| TC-045 | Body `{"outcome":"GONE"}`, then `{}` | 400 each; the listing is unchanged |
| TC-046 | No token | 401 |

### Each stage (outside deal, no negotiation record)

Create a few more published properties for the seller (Homes, Rent). For each stage set it with SQL, then `close`
with `RENTED`.

| ID | Stage set in SQL | Expected |
|---|---|---|
| TC-050 | `PUBLISHED` | 200, becomes `SOLD`, outcome `RENTED` (a deal outside JustQlic: nothing was ever started in chat) |
| TC-051 | `BUYER_INQUIRY_PENDING` | 200 |
| TC-052 | `NEGOTIATION_IN_PROGRESS` | 200 |
| TC-053 | `OFFER_ACCEPTED` | 200 |
| TC-054 | `EXPIRED` | 200 (the deal was made after the listing lapsed) |
| TC-055 | `TRUST_SAFETY_REVIEW` | 200 (see D) |
| TC-056 | `REVISION_REQUIRED` | 200 |
| TC-057 | `ORDER_CREATED`, `SOLD`, `DEACTIVATED_BY_SELLER`, `REMOVED_BY_ADMIN`, `REJECTED`, `APPROVED`, `PLAN_SELECTION_PENDING` | 400, `ERROR_LISTING_NOT_CLOSABLE` each; the stage does not change |

---

## D. A property in review leaves the review queue

```sql
-- a review waiting for a person
UPDATE listings SET status = 'TRUST_SAFETY_REVIEW' WHERE id = '<id>';
INSERT INTO listing_trust_safety_reviews (listing_id, attempt_number, review_reason, auto_decision)
VALUES ('<id>', 1, 'EDIT', 'QUEUED_FOR_REVIEW') RETURNING id;
```

| ID | Steps | Expected |
|---|---|---|
| TC-060 | Before closing, `SELECT count(*) FROM listing_trust_safety_reviews WHERE listing_id = '<id>' AND auto_decision = 'QUEUED_FOR_REVIEW' AND admin_decision IS NULL` | 1 (pending) |
| TC-061 | `close <id> RENTED` | 200 |
| TC-062 | Repeat the count of TC-060 | 0: the review is no longer pending |
| TC-063 | `SELECT admin_decision, admin_id, reviewed_at FROM listing_trust_safety_reviews WHERE listing_id = '<id>'` | `CLOSED_BY_OWNER`, null, a time |
| TC-064 | Try an admin approve, reject or revision request on the listing (the review service has no endpoint yet: use the integration test `ListingClosureIntegrationTest`) | Fails with `ERROR_REVIEW_NOT_ALLOWED`; the listing cannot be published again |
| TC-065 | A listing in `REVISION_REQUIRED` whose last review was decided (`REVISION_REQUESTED`) and that has a pending appeal: close it | 200; the review keeps `REVISION_REQUESTED`; the appeal status is `MOOT` |
| TC-066 | Try to appeal the closed listing | 400, `ERROR_APPEAL_NOT_ALLOWED` |
| TC-067 | A property in `TRUST_SAFETY_REVIEW` that has no review row | 200 |

---

## E. Failure handling in the app

| ID | Steps | Expected |
|---|---|---|
| TC-070 | Turn the network off, confirm a close | A message that the connection failed; the link is still there and can be tried again |
| TC-071 | Close a property from the app while the same property was closed on another device | The message "This property can't be marked as sold, rented or leased right now"; pull to refresh shows it as closed |
| TC-072 | Switch the app to Hindi, repeat TC-031 to TC-033 | All texts are in Hindi, including the outcome names and the confirmation |
| TC-073 | Large text (200%) and TalkBack/VoiceOver on the card | The link reads "Mark <title> as Rented"; nothing is cut off; the tap target is at least 48 dp |

---

## F. Regression

| ID | Steps | Expected |
|---|---|---|
| TC-080 | Delete a goods listing and a property listing from My Listings | Works as before (US-010) |
| TC-081 | Order a goods listing to completion (when orders exist) | It still reaches Sold only through the order; the property close endpoint refuses goods |
| TC-082 | Goods search, goods details, plan selection and listing edits | Unchanged |

---

## Running the automated tests

```bash
# backend (PostgreSQL through Testcontainers needs Docker)
cd valuex-backend
mvn -o test -Dtest='ListingClosureServiceTest,TrustSafetyReviewCloserTest,ListingClosedOutcomeTest,ListingStateMachineTest,SearchRequestValidatorTest,AttributeValidatorTest,MyListingsServiceTest,ListingControllerTest,ListingClosureIntegrationTest'

# mobile
cd valuex-mobile
flutter test test/features/listing/my_listings_test.dart test/features/search/search_results_controller_test.dart test/features/search/search_screen_test.dart --dart-define=SKIP_PIXEL_CONTRAST=true
```

On a machine where Testcontainers cannot reach Docker set
`JAVA_TOOL_OPTIONS="-Dapi.version=1.44 -Duser.timezone=Asia/Kolkata"` first.
