# US-114: Listing Item Details Entry: Manual Testing Guide

**Scope:** the Item Details page (Sell step 2) and `PATCH /api/v1/listings/{listingId}`. AI is off by default, so the page opens empty. The restricted item check (US-007) and plan selection (US-008) are not built yet.

## Setup
- Backend running with Flyway applied (`V14__listing_category_slug.sql`), signed-in seller with Aadhaar verified.
- A draft with at least 2 ready photos (US-004).
- Home location chosen (device or saved) for the location checks.

## A. Photo page (change from US-004)
| ID | Step | Expected |
|---|---|---|
| A-01 | Open Sell, add 1 photo | "Add at least 2 photos to continue" shows; Submit to AI does nothing |
| A-02 | Add a second photo, tap Submit to AI | Item Details opens; progress shows step 2 of 4 |
| A-03 | Tap back on Item Details | Photos are still there |

## B. Item Details (manual entry)
| ID | Step | Expected |
|---|---|---|
| B-01 | Open the page | Fields empty; subtitle "Fill in the details"; no AI banner; "Fill in the required fields to continue"; Choose Listing Plan is off |
| B-02 | Type spaces in Title | "Enter a title for your item" |
| B-03 | Title over 100 characters | Field stops at 100; counter shown |
| B-04 | Pick a category, a condition | One chip is selected in each group (category blue, condition green, each with a tick); the other chips clear |
| B-04a | Look at the categories | At most 3 rows; the last chip is **Others** when the list does not fit |
| B-04b | Tap Others | A pop-up lists the remaining categories; tapping one closes it and shows that category selected on the page; **Close** dismisses it |
| B-05 | Description over 2000 characters | Field stops at 2000 |
| B-06 | Price `0`, `abc`, `1.234`, `10000001` | "Enter a valid price"; button stays off |
| B-07 | Price `1,299.50` | Accepted; button turns on once every field is valid |
| B-08 | Location row | Shows the Home area and city; no coordinates anywhere |
| B-09 | No Home location chosen | Same prompt and actions as Home (use current location, use saved location) |
| B-10 | Tap Choose Listing Plan | "Details saved. Choosing a plan is coming soon." |
| B-11 | Reopen the draft (GET listing) | Saved title, category, condition, description, price and city are returned |
| B-12 | Edit a field and save again | New value saved; status unchanged (`DRAFT`) |

## C. Errors
| ID | Step | Expected |
|---|---|---|
| C-01 | Turn off the network, tap Choose Listing Plan | Offline message; typed values kept; try again works |
| C-02 | Listing with fewer than 2 photos (call API directly) | `ERROR_MIN_PHOTOS_REQUIRED`, "At least 2 photos required" |
| C-03 | Listing not in `DRAFT` or `REVISION_REQUIRED` | `ERROR_LISTING_NOT_EDITABLE` |
| C-04 | Another seller's listing id | Not found |
| C-05 | `REVISION_REQUIRED` listing | Details can be edited and saved |
| C-06 | Title `<b>x</b>` | Stored and shown as plain text |

## D. AI-filled variant (only once US-005 is on)
| ID | Step | Expected |
|---|---|---|
| D-01 | Open with a suggestion | Banner; subtitle "AI filled these from your photos"; fields prefilled and editable |
| D-02 | Leave, edit or clear a suggested field, save | Feedback sent as accepted, edited or rejected; a feedback failure does not block saving |

## E. Accessibility
| ID | Step | Expected |
|---|---|---|
| E-01 | Text size 200% | No clipping or overflow; chips wrap |
| E-02 | Screen reader | Every field and chip has a name; selected chip announced; section titles are headings |
| E-03 | Hindi | Labels and hints translated (needs native-speaker review) |

## Acceptance criteria tally
| Criterion | Covered by |
|---|---|
| Empty fields when AI is off; prefilled with banner when AI is on | B-01, D-01 |
| Required title, category, condition, description, price | B-02 to B-07, C-02 |
| Location from Home, city only sent | B-08, B-09 |
| Choose Listing Plan saves | B-10 to B-12 |
| Editable in `DRAFT` and `REVISION_REQUIRED` only | C-03, C-05 |
| Restricted item check (US-007) then plan page (US-008) | Not yet; added with those stories |
