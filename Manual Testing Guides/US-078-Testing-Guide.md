# US-078: Listing Plan Features and Pricing: Manual Testing Guide

**Scope:** the plan catalog (`GET /api/v1/plans/seller`) and the Choose Listing Plan page. Selecting and paying for a plan is US-008, so **Review Listing** only shows "Reviewing your listing is coming soon."

## Setup
- Backend running with Flyway applied (`V15__seller_plans.sql`); signed-in seller.
- A draft with 2 or more ready photos and valid item details (US-004, US-114).

## A. Opening the page
| ID | Step | Expected |
|---|---|---|
| A-01 | On Item Details fill every field and tap **Choose Listing Plan** | The plan page opens (step 3 of 4) with the title "Choose Listing Plan" and "Boost your visibility and sell faster" |
| A-02 | Tap back | Item Details is shown with your values |
| A-03 | Turn off the network and open the page | An error with **Retry**; Retry loads the plans once the network is back |

## B. Plan cards (starting data)
| ID | Step | Expected |
|---|---|---|
| B-01 | Look at the cards | Basic ₹49 (₹99 struck through), Boosted ₹149 (₹399), Priority ₹249 (₹699), in that order |
| B-02 | Badges | Boosted shows POPULAR; Priority shows BEST VALUE; Basic has none |
| B-03 | Feature lines | Basic: Listed in chronological order, 7 days validity, AI + Email support. Boosted: Listed on top when searched, 7 days validity, AI + Email + Chat (Human) support. Priority: Boosted placement, Featured on landing page, Featured badge, 1 month validity, AI + Email + Chat + On-call support |
| B-04 | Default selection | Boosted is selected (blue/magenta border, "Selected" mark) |
| B-05 | Tap Priority, then Basic | Only the tapped card is selected; the breakdown changes with it |

## C. Payment breakdown
| ID | Step | Expected |
|---|---|---|
| C-01 | Boosted selected | Original price ₹399; Discount (63% off) −₹250; GST included ₹22.73; Total to pay ₹149; "Inclusive of GST" |
| C-02 | Basic selected | Discount (51% off) −₹50; GST included ₹7.47; Total ₹49 |
| C-03 | Priority selected | Discount (64% off) −₹450; Total ₹249 |

## D. Plans are data (use SQL, then evict the cache by restarting or waiting an hour)
| ID | Step | Expected |
|---|---|---|
| D-01 | `UPDATE plans SET discounted_price = 0 WHERE code = 'BASIC'` | Basic shows "Free"; breakdown says "Free" and "No payment is needed for this plan."; no GST line |
| D-02 | `UPDATE plans SET is_active = FALSE WHERE code = 'BASIC'` | Two plans are shown |
| D-03 | `UPDATE platform_settings SET setting_value = 'EXCLUSIVE' WHERE setting_key = 'GST_MODE'` | Breakdown shows "GST (18%)" added and a total larger than the price; no "Inclusive of GST" |
| D-04 | Insert a fourth seller plan | A fourth card appears in `display_order` |
| D-05 | Mark no plan as recommended | The first plan is selected by default |
| D-06 | All plans inactive | "No plans are available right now."; Review Listing does nothing |

## E. Other
| ID | Step | Expected |
|---|---|---|
| E-01 | Tap **Review Listing** | "Reviewing your listing is coming soon." |
| E-02 | Text size 200% | No clipping or overflow; cards and breakdown grow |
| E-03 | Screen reader | Each card is read as one choice with its name, price, lines and selected state; the struck-through price is read as "Original price ₹399" |
| E-04 | Hindi | Labels translated (needs native-speaker review); plan names and feature lines come from the server in English |
| E-05 | Call `GET /api/v1/plans/seller` without a token | 401 |

## Acceptance criteria tally
| Criterion | Covered by |
|---|---|
| Three plans side by side with the stated prices, validity and support | B-01, B-03 |
| Payment breakdown before confirming | C-01 to C-03 |
| Plan features activate after payment | Not here; US-008 and US-009 |
