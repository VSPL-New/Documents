# US-006: Category Taxonomy and Category-driven Item Details: Manual Testing Guide

**Scope:** the category taxonomy import, the category browse/search/schema APIs, `PUT /api/v1/listings/{listingId}/category`, the extended `PATCH /api/v1/listings/{listingId}`, the category picker and the category-driven Item Details page on mobile, the new maximum price (₹10,00,00,000) and the Dev-only banner on the Choose Listing Plan page. AI category suggestion (US-005), the restricted item popup (US-007), Real Estate buyer-side specifics (US-118), category-wise plans (US-119) and Admin editing (US-121) are not part of this story.

## Setup
- Backend running on PostgreSQL with Flyway applied up to `V16__taxonomy_and_listing_attributes.sql`. The taxonomy is imported on startup (`valuex.taxonomy.import-on-startup=true`, the default).
- A signed-in seller with Aadhaar verified and a draft with at least 2 ready photos (US-004).
- Mobile built with `ENV=dev` for the banner check (G-01); a staging or prod build for G-02.
- A tool to call the API (all calls need the seller's bearer token). Examples below use `{{base}}` for `/api/v1`.

## A. Taxonomy import
| ID | Step | Expected |
|---|---|---|
| A-01 | Start the backend on an empty database | Log line "Taxonomy imported" with counts `l1=39, l2=157, l3=907, attributes=492, profiles=51` |
| A-02 | `SELECT level, count(*) FROM categories GROUP BY level` | 39, 157 and 907 rows; all L3 codes start with `CAT-` |
| A-03 | Restart the backend | "Taxonomy unchanged, import skipped"; no category id changes |
| A-04 | Edit one CSV under `resources/taxonomy`, rebuild, start | Import runs again; ids of existing categories are unchanged; `taxonomy_import_log` has a new `SUCCESS` row |
| A-05 | Break a CSV (unknown profile on one row), start | Start-up fails with every problem listed; nothing is written; a `FAILED` log row exists |
| A-06 | Start with `TAXONOMY_IMPORT_DRY_RUN=true` | `DRY_RUN` log row; tables unchanged |
| A-07 | Start with `TAXONOMY_IMPORT_ON_STARTUP=false` | "Taxonomy import on startup is disabled"; nothing imported |

## B. Browse and search APIs
| ID | Step | Expected |
|---|---|---|
| B-01 | `GET {{base}}/categories/children?scope=POPULAR` | 15 L1 categories in rank order, each `popular: true` |
| B-02 | Same with `scope=OTHERS` | The other 24 L1 categories, A to Z |
| B-03 | `GET .../children?parentCode=<an L1 code>&scope=POPULAR` | At most 10 popular L2 categories |
| B-04 | `GET .../children?parentCode=<an L2 code>&scope=ALL` | Every enabled L3 under it, `hasChildren: false` |
| B-05 | `parentCode=<an L3 code>` | 400 `ERROR_CATEGORY_LEAF` |
| B-06 | `parentCode=L1-NOPE` | 404 `CATEGORY_NOT_FOUND` |
| B-07 | `GET .../search?q=smartphone` | Up to 20 L3 results, each with its L1 > L2 > L3 path |
| B-08 | `q=a` or `q=%%` | Empty list |
| B-09 | Disable an L1 (`UPDATE categories SET admin_enabled = false WHERE code = ...`) | It and its descendants disappear from browse and search; re-enable to restore |
| B-10 | Call without a token | 401 |

## C. Category forms (`GET {{base}}/categories/{code}/listing-schema`)
| ID | Step | Expected |
|---|---|---|
| C-01 | A Smartphones leaf | `group: GOODS`; common flags show condition, quantity and negotiable; required fields (brand, model, storage) come first; optional fields next; "More details" fields (age, purchase year, warranty and similar) last with `section: MORE` |
| C-02 | A Cars leaf | `group: WHOLE_VEHICLE`; no quantity; `ownership_count` not listed (the profile has `owner_count`); registration state has 36 options |
| C-03 | An Apartment leaf | `group: REAL_ESTATE`; no condition, quantity or More details; `transactionIntents: [SALE, RENT]`; `sale_price` required when intent is SALE, `monthly_rent` when RENT; `property_type` has `prefillOption` |
| C-04 | A New Developments leaf | Intent `[SALE]` only; `price_min` required; negotiable not shown |
| C-05 | A Land leaf / Commercial leaf / Shared Accommodation leaf | Intents `[SALE, LEASE]` / `[SALE, RENT, LEASE]` / `[RENT]`; commercial has `lease_amount`, land has `monthly_rent`; shared has `monthly_rent` required and intent prefilled |
| C-06 | An "Other" leaf | Only `item_type_free_text` is required; `special_attributes_json` is a key/value field |
| C-07 | Any leaf | None of title, description, condition, price, quantity, delivery or location keys appear as category fields |
| C-08 | `code` of an L2 or an unknown code | 400 `ERROR_CATEGORY_NOT_LEAF` / 404 `CATEGORY_NOT_FOUND` |

## D. Choosing a category (`PUT {{base}}/listings/{id}/category` `{"categoryCode": "..."}`)
| ID | Step | Expected |
|---|---|---|
| D-01 | Set a valid leaf on a `DRAFT` | 200; draft shows `category` with its path |
| D-02 | Set the same leaf again | 200; nothing changes |
| D-03 | Save some details, then set a different leaf | Values the new form does not ask are removed; shared ones (for example brand, model, age) stay |
| D-04 | An L1 or L2 code | 400 `ERROR_CATEGORY_NOT_LEAF` |
| D-05 | A disabled leaf | 400 `ERROR_CATEGORY_DISABLED` |
| D-06 | Unknown code | 404 `CATEGORY_NOT_FOUND` |
| D-07 | A listing that is not `DRAFT` or `REVISION_REQUIRED` | 400 `ERROR_LISTING_NOT_EDITABLE` |
| D-08 | Another seller's listing | 404 `LISTING_NOT_FOUND` |

## E. Saving details (`PATCH {{base}}/listings/{id}`)
| ID | Step | Expected |
|---|---|---|
| E-01 | Save before choosing a category | 400 `ERROR_CATEGORY_REQUIRED` |
| E-02 | Complete goods body (title, condition, conditionNotes, description, price, negotiable, quantity, attributes) | 200; the draft returns every value; attribute options come back as codes, dates as ISO text |
| E-03 | Leave out a required category field | 400 `ERROR_ATTRIBUTE_REQUIRED`; `error.details.field` names the key |
| E-04 | Send a key the form does not ask | 400 `ERROR_ATTRIBUTE_NOT_ALLOWED` |
| E-05 | Wrong type or out of range (pincode `012345`, percent `120`, year `1800`, text over its length) | 400 `ERROR_ATTRIBUTE_INVALID` |
| E-06 | Related fields (`price_min` > `price_max`, `floor_number` > `total_floors`, built-up area < carpet area) | 400 `ERROR_ATTRIBUTE_INVALID` on the second field |
| E-07 | Option sent by code, by label, or in other case | Accepted; stored as the option code |
| E-08 | Multi-select with a repeated option | Stored once |
| E-09 | Missing condition notes, condition, negotiable or quantity (goods) | `ERROR_CONDITION_NOTES_REQUIRED`, `ERROR_CONDITION_REQUIRED`, `ERROR_NEGOTIABLE_REQUIRED`, `ERROR_QUANTITY_INVALID` |
| E-10 | Quantity `0`, `1001` | `ERROR_QUANTITY_INVALID` |
| E-11 | Price `0`, `-5`, `10.123`, `100000000.01` | `ERROR_PRICE_INVALID` |
| E-12 | Price `100000000` | Accepted (new maximum ₹10,00,00,000) |
| E-13 | Whole vehicle with `quantity: 7` | Saved quantity is 1 |
| E-14 | Real Estate, intent `RENT`, `monthly_rent: 25000`, any `price` in the body | Listing price is 25000; condition and quantity are empty |
| E-15 | Real Estate, intent `SALE`, `sale_price` missing | 400 `ERROR_ATTRIBUTE_REQUIRED` |
| E-16 | "Other" leaf with `special_attributes_json` of 21 pairs | 400 `ERROR_ATTRIBUTE_INVALID` |
| E-17 | Dimensions `{"length": 0}` or an unknown key | 400 `ERROR_ATTRIBUTE_INVALID` |
| E-18 | Less than 2 photos | 400 `ERROR_MIN_PHOTOS_REQUIRED` |
| E-19 | Title `<b>x</b>`, description with control characters | Stored as plain text; control characters removed |
| E-20 | Save again with fewer attributes | Earlier values are replaced, not merged |
| E-21 | `GET {{base}}/listings/{id}` | Same values as E-02, with category path |

## F. Mobile: Item Details
| ID | Step | Expected |
|---|---|---|
| F-01 | Open Item Details on a new draft | Title field and a **Choose a category** button; no condition, description or price yet; "Fill in the required fields to continue"; Choose Listing Plan is off |
| F-02 | Tap Choose a category | Picker opens with the popular categories; **More categories** shows the rest |
| F-03 | Tap an L1, then an L2 | Each level lists its popular children first; **More categories** shows the rest; leaves (L3) are listed in full |
| F-04 | Back in the picker | Goes up one level; at the top it closes without a choice |
| F-05 | Type 1 letter, then 2 or more | "Type at least 2 letters to search", then results after a short pause, each with its parents shown |
| F-06 | Search for text with no match | "No categories match" |
| F-07 | Choose a leaf | Page shows the category with its path and **Change**; the form for it appears |
| F-08 | Smartphones form | Condition chips and notes, description, About this item (required fields marked *), **More details** (collapsed), location, price, "Price is negotiable", quantity |
| F-09 | Tap More details | Optional and "More details" fields appear; tap again hides them |
| F-10 | Fill a required field wrongly (percent 120, pincode 12345) and leave it | Hint under the field "Enter a valid ..." |
| F-11 | Clear a required field you touched | "... is required" |
| F-12 | Field types | Chips for up to 8 options; a searchable sheet for longer lists (state, RAM); multi-select; yes/no; date picker; numbers accept digits only; comma separated lists; length, width, height boxes; add/remove name-value rows (Other items) |
| F-13 | Real Estate leaf | No condition, price or quantity; type chips show Sale/Rent; the type of property is already selected; choosing Rent asks for monthly rent, choosing Sale asks for sale price |
| F-14 | Change the category | The form reloads; values the new category does not ask are gone; type fields that repeat the category are refilled |
| F-15 | Choose a category the server refuses (disable it first) | "This category is not available. Choose another one."; Retry or choose another |
| F-16 | Turn off the network while a form loads | "Unable to load the details for this category. Try again" with Retry |
| F-17 | Complete the form, tap Choose Listing Plan | Details saved with only the visible fields; the plan page opens |
| F-18 | Server rejects the save | A snack bar with a localized message; typed values kept |
| F-19 | Max price | `100000000` accepted; `100000001` shows "Enter a valid price" |
| F-20 | Quantity `0`, `1001`, blank | "Enter a quantity from 1 to 1000" |

## G. Dev banner on the plan page
| ID | Step | Expected |
|---|---|---|
| G-01 | Dev build, open Choose Listing Plan | A banner under the header: "Plan is under revision until US-119" |
| G-02 | Staging or prod build | No banner |

## H. Accessibility and language
| ID | Step | Expected |
|---|---|---|
| H-01 | Text size 200% | No clipping or overflow; chips wrap |
| H-02 | Screen reader | Category button, each field label, each chip (selected state), More details (expanded state) and picker rows have names |
| H-03 | Hindi | All new labels, hints and errors translated (native-speaker review needed); field labels from the server stay in English until Admin adds translations |

## Automated tests
| Area | Command |
|---|---|
| Backend, all (unit, integration, checkstyle, coverage) | `mvn verify "-Dapi.version=1.44" "-Duser.timezone=Asia/Kolkata"` in `valuex-backend` (needs Docker) |
| Backend, taxonomy only | `mvn test "-Dtest=TaxonomyIntegrationTest,TaxonomySourceLoaderTest,AttributeValidatorTest,ListingDetailsIntegrationTest" "-Dapi.version=1.44"` |
| SonarQube | `mvn clean verify sonar:sonar` (token from `~/.m2/settings.xml`) |
| Mobile, listing | `flutter test test/features/listing` in `valuex-mobile` |
| Mobile, everything | `flutter analyze` and `flutter test` |

## Acceptance criteria tally
| Criterion | Covered by |
|---|---|
| Taxonomy loaded from the approved sheets (39 / 157 / 907 / 492) | A-01 to A-07 |
| Popular-first browsing, "Others", search from 2 characters | B-01 to B-10, F-02 to F-06 |
| One enabled leaf category per listing; L1 and L2 derived | D-01 to D-08, F-07 |
| Item Details driven by the category (required first, optional and More details) | C-01 to C-08, F-08 to F-14 |
| Type, range and related-field validation on the server and the app | E-03 to E-08, E-16, E-17, F-10 to F-12 |
| Real Estate transaction intent drives the listing price | C-03 to C-05, E-14, E-15, F-13 |
| Whole vehicles have no quantity; Real Estate has no condition | C-02, E-13, E-14 |
| Maximum price ₹10,00,00,000 | E-11, E-12, F-19 |
| Changing the category keeps only matching values | D-03, F-14 |
| Dev-only plan banner | G-01, G-02 |
