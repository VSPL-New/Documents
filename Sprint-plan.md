# ValueX Sprint Plan

Version: 2.0

Sprint Duration: 2 Weeks

---

# Sprint 0 - Foundation & Architecture

## Goal

Establish engineering foundation, repositories, CI/CD, environments, architecture skeletons.

## Repository Ownership

* Backend
* Mobile
* Web
* Infra
* AI

## Stories

| ID     | Story                     | Repo    | SP | Dependency |
| ------ | ------------------------- | ------- | -- | ---------- |
| S0-001 | Backend Project Skeleton  | backend | 5  | None       |
| S0-002 | Flutter Project Setup     | mobile  | 5  | None       |
| S0-003 | Admin Web Setup           | web     | 3  | None       |
| S0-004 | PostgreSQL Setup          | infra   | 3  | None       |
| S0-005 | Redis Setup               | infra   | 2  | None       |
| S0-006 | CI/CD Pipeline            | infra   | 8  | None       |
| S0-007 | OpenAPI Framework         | backend | 5  | S0-001     |
| S0-008 | Lifecycle State Framework | backend | 5  | S0-001     |

---

# Sprint 1 - Identity & User Management

## Goal

Allow users to register, verify identity and manage profiles.

## Stories

| ID     | User Story                                  | Repo                 |
| ------ | ------------------------------------------- | -------------------- |
| US-001 | User Registration with Aadhaar Verification | backend, mobile      |
| US-002 | One Account Per User Enforcement            | backend              |
| US-003 | User Profile Management                     | backend, mobile, web |
| US-077 | Critical Event Notifications                | backend, mobile      |
| US-088 | Lifecycle State - User Account              | backend              |

## Exit Criteria

* Aadhaar onboarding complete
* Login operational
* User profiles operational

---

# Sprint 2 - Seller Listing Creation

## Goal

Allow sellers to create and publish listings.

## Stories

| ID     | User Story                            | Repo                 |
| ------ | ------------------------------------- | -------------------- |
| US-004 | Create Listing with Photo Capture     | mobile, backend      |
| US-005 | AI-Assisted Listing Creation          | backend, AI          |
| US-006 | Multi-Category Tagging                | backend, mobile      |
| US-007 | Restricted Items Prevention           | backend, AI          |
| US-008 | Seller Chooses Listing Plan           | backend, mobile      |
| US-009 | Listing Publication After Payment     | backend              |
| US-010 | Edit/Delete Listing                   | backend, mobile, web |
| US-084 | Pre-Publication Trust & Safety Review | backend, AI          |
| US-089 | Lifecycle State - Listing             | backend              |

## Exit Criteria

* Listings can be created and published
* Moderation workflow operational

---

# Sprint 3 - Discovery & Search

## Goal

Enable buyers to discover items.

## Stories

| ID     | User Story                 | Repo                 |
| ------ | -------------------------- | -------------------- |
| US-011 | Browse and Search Listings | backend, mobile, web |
| US-012 | View Listing Details       | backend, mobile, web |
| US-066 | Saved Searches and Alerts  | backend, mobile      |
| US-073 | Save and Bookmark Listings | backend, mobile      |

## Exit Criteria

* Search operational
* Saved items operational

---

# Sprint 4 - Communication & Negotiation

## Goal

Enable buyer-seller interaction.

## Stories

| ID     | User Story                                | Repo            |
| ------ | ----------------------------------------- | --------------- |
| US-013 | Chat with Seller                          | backend, mobile |
| US-014 | Masked Voice Call                         | backend, mobile |
| US-015 | Video Call with Recording                 | backend, mobile |
| US-016 | Communication History Storage             | backend         |
| US-017 | Price Negotiation                         | backend, mobile |
| US-018 | Prevent Checkout Without Price Acceptance | backend         |
| US-069 | Buyer Initiates Contact from Listing      | mobile, backend |
| US-076 | Seller Negotiation Management             | backend, mobile |
| US-080 | Auto-Expire Inactive Negotiations         | backend         |

## Exit Criteria

* Full negotiation workflow operational

---

# Sprint 5 - Cart, Checkout & Payments

## Goal

Enable secure transactions and escrow.

## Stories

| ID     | User Story                         | Repo            |
| ------ | ---------------------------------- | --------------- |
| US-019 | Add to Cart (Multi-Item)           | backend, mobile |
| US-020 | Choose Delivery or Self-Pickup     | backend, mobile |
| US-021 | Buyer Makes Payment (Escrow)       | backend, mobile |
| US-022 | Self-Pickup Payment Options        | backend, mobile |
| US-023 | Order Creation and Tracking        | backend, mobile |
| US-025 | Platform Fee Deduction             | backend         |
| US-072 | Seller Payout Bank/UPI Management  | backend, mobile |
| US-090 | Lifecycle State - Order            | backend         |
| US-091 | Lifecycle State - Payment & Escrow | backend         |

## Exit Criteria

* Orders operational
* Escrow operational

---

# Sprint 6 - Shipping & Delivery

## Goal

Enable fulfillment workflow.

## Stories

| ID     | User Story                                | Repo            |
| ------ | ----------------------------------------- | --------------- |
| US-026 | Seller Prepares Package and Uploads Proof | backend, mobile |
| US-027 | Pickup Scheduling                         | backend, mobile |
| US-028 | Item Pickup by Logistics Partner          | backend         |
| US-029 | Shipment Tracking                         | backend, mobile |
| US-030 | Buyer Receives Item and Uploads Proof     | backend, mobile |
| US-031 | Delivery Confirmation via In-App Button   | backend, mobile |
| US-032 | Failed Delivery and Rescheduling          | backend         |
| US-092 | Lifecycle State - Shipping                | backend         |

## Exit Criteria

* End-to-end shipping operational

---

# MVP RELEASE

Includes:

* User Registration
* Listings
* Search
* Communication
* Negotiation
* Cart
* Checkout
* Escrow
* Shipping
* Delivery

---

# Sprint 7 - Returns & Disputes

Stories:

* US-033 Return Request
* US-034 Return Approval
* US-035 Refund Processing
* US-047 Raise Dispute
* US-094 Lifecycle State - Dispute

---

# Sprint 8 - Ratings, Trust & Safety

Stories:

* US-036 Buyer Rates Seller
* US-037 Seller Rates Buyer
* US-048 Fraud Listing Detection
* US-049 Image Proof Authenticity Validation
* US-050 Daily Listing Limit
* US-051 Progressive Penalties
* US-052 Fraud Score and Velocity Checks
* US-081 Block Transactions for Users Under Investigation
* US-082 Image Watermark Detection

---

# Sprint 9 - Admin Operations

Stories:

* US-053 Admin User Management
* US-054 Listing Moderation
* US-055 Dispute Resolution
* US-056 Transaction Monitoring
* US-057 Content Moderation
* US-074 Track Support Ticket Status
* US-083 System Audit Trail
* US-100 Admin Analytics Dashboard

---

# Sprint 10 - Premium Plans

Stories:

* US-038 Buyer Upgrades to Premium
* US-042 Subscription Management
* US-078 Listing Plan Features and Pricing
* US-079 Buyer Premium Plan Features
* US-096 Lifecycle State - Premium Subscription

---

# Sprint 11 - AI Photo Search

Stories:

* US-039 Photo-Based Search
* US-040 Visual Search Results Ranking
* US-041 Search Refinement with Filters

---

# Sprint 12 - Support, Accessibility & Compliance

Stories:

* US-043 On-Screen AI Bot Assistance
* US-044 Multi-Language Support
* US-045 Chat with Human Support
* US-046 Call Human Support
* US-061 Screen Reader Compatibility
* US-062 Data Export Request
* US-063 Data Deletion Request
* US-086 WhatsApp Notifications
* US-087 Notification Preferences Management
* US-095 Lifecycle State - Support Ticket
* US-097 Data Export Request (Compliance)
* US-098 Data Deletion Request (Compliance)
* US-099 Accessibility Support
