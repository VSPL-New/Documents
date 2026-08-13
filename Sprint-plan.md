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

## Deferred Follow-ups

- **pgvector extension** — LLD §5.3 lists `CREATE EXTENSION vector` for visual
  search, but stock `postgres:16-alpine` doesn't bundle pgvector. Deferred out
  of S0-004 (not required for the "PostgreSQL accessible" exit criterion).
  Needs a `pgvector/pgvector:pg16` base image (or a custom Dockerfile layer)
  and should be scoped as its own story once a visual-search sprint is planned.

---

# Sprint 1 - Identity & User Management

## Goal

Allow users to register and login via multiple auth methods, verify identity, and manage profiles.

## Stories

| ID     | Story                                       | Repo            | SP | Dependency |
| ------ | ------------------------------------------- | --------------- | -- | ---------- |
| US-001 | User Registration via Mobile OTP            | backend, mobile | 8  | S0-001     |
| US-106 | Mobile OTP Login for Returning Users        | backend, mobile | 5  | US-001     |
| US-107 | Access Token Refresh                        | backend, mobile | 5  | US-106     |
| US-101 | Google Sign-In (Optional Convenience Login) | backend, mobile | 5  | US-001     |
| US-102 | Apple Sign-In (Optional Convenience Login)  | backend, mobile | 5  | US-001     |
| US-002 | One Account Per User Enforcement            | backend         | 3  | US-001     |
| US-003 | User Profile Management                     | backend, mobile | 5  | US-001     |
| US-103 | Profile Hub / Account Menu Navigation       | backend, mobile | 5  | US-003     |
| US-104 | Account Logout                              | backend, mobile | 2  | US-001     |
| US-105 | Account Security Settings                   | backend, mobile | 5  | US-003     |
| US-077 | Critical Event Notifications                | backend, mobile | 5  | US-001     |
| US-088 | Lifecycle State - User Account              | backend         | 3  | US-001     |

## Exit Criteria

* Mobile OTP registration and login operational
* Returning users can log back in via mobile OTP without re-registering (US-106)
* Access tokens can be silently refreshed via the refresh token, with rotation and type validation (US-107)
* Google Sign-In functional (optional)
* Apple Sign-In functional (optional)
* Aadhaar onboarding complete (skippable until first transaction)
* User profiles operational
* Profile hub navigation, logout, and account security settings operational (menu items to not-yet-built sections show empty/coming-soon states until their sprints land)

---

# Sprint 2 - Seller Listing Creation

## Goal

Allow sellers to create and publish listings.

## Stories

| ID     | Story                                 | Repo            | SP | Dependency |
| ------ | ------------------------------------- | --------------- | -- | ---------- |
| US-004 | Create Listing with Photo Capture     | mobile, backend | 8  | US-001     |
| US-005 | AI-Assisted Listing Creation          | backend, AI     | 8  | US-004     |
| US-006 | Multi-Category Tagging                | backend, mobile | 3  | US-004     |
| US-007 | Restricted Items Prevention           | backend, AI     | 5  | US-005     |
| US-089 | Lifecycle State - Listing             | backend         | 5  | US-004     |
| US-084 | Pre-Publication Trust & Safety Review | backend, AI     | 5  | US-007     |
| US-078 | Listing Plan Features and Pricing     | backend, mobile | 3  | US-004     |
| US-008 | Seller Chooses Listing Plan           | backend, mobile | 5  | US-078     |
| US-009 | Listing Publication After Payment     | backend         | 5  | US-008     |
| US-010 | Edit/Delete Listing                   | backend, mobile | 5  | US-009     |

## Exit Criteria

* Listings can be created and published
* AI-assisted metadata generation working
* Moderation workflow operational
* Payment integration for listing plans complete

---

# Sprint 3 - Discovery & Search

## Goal

Enable buyers to discover items.

## Stories

| ID     | Story                      | Repo            | SP | Dependency |
| ------ | -------------------------- | --------------- | -- | ---------- |
| US-011 | Browse and Search Listings | backend, mobile | 8  | US-009     |
| US-012 | View Listing Details       | backend, mobile | 5  | US-011     |
| US-073 | Save and Bookmark Listings | backend, mobile | 3  | US-012     |
| US-066 | Saved Searches and Alerts  | backend, mobile | 5  | US-011     |

## Exit Criteria

* Search operational with filters
* Listing detail view complete
* Saved items and search alerts working

---

# Sprint 4 - Communication & Negotiation

## Goal

Enable buyer-seller interaction and price negotiation.

## Stories

| ID     | Story                                     | Repo            | SP | Dependency |
| ------ | ----------------------------------------- | --------------- | -- | ---------- |
| US-069 | Buyer Initiates Contact from Listing      | mobile, backend | 3  | US-012     |
| US-013 | Chat with Seller                          | backend, mobile | 8  | US-069     |
| US-014 | Masked Voice Call                         | backend, mobile | 8  | US-013     |
| US-015 | Video Call with Recording                 | backend, mobile | 8  | US-014     |
| US-016 | Communication History Storage             | backend         | 5  | US-015     |
| US-017 | Price Negotiation                         | backend, mobile | 8  | US-013     |
| US-076 | Seller Negotiation Management             | backend, mobile | 5  | US-017     |
| US-018 | Prevent Checkout Without Price Acceptance | backend         | 3  | US-017     |
| US-080 | Auto-Expire Inactive Negotiations         | backend         | 3  | US-017     |
| US-068 | Direct Buy Now Flow                       | backend, mobile | 5  | US-012     |

## Exit Criteria

* Chat, voice, and video communication working
* Price negotiation flow complete
* Direct buy now option available
* Auto-expiry mechanism functional

---

# Sprint 5 - Cart, Checkout & Payments

## Goal

Enable secure transactions and escrow.

## Stories

| ID     | Story                              | Repo            | SP | Dependency |
| ------ | ---------------------------------- | --------------- | -- | ---------- |
| US-019 | Add to Cart (Multi-Item)           | backend, mobile | 5  | US-018     |
| US-020 | Choose Delivery or Self-Pickup     | backend, mobile | 5  | US-019     |
| US-090 | Lifecycle State - Order            | backend         | 5  | US-020     |
| US-091 | Lifecycle State - Payment & Escrow | backend         | 5  | US-090     |
| US-021 | Buyer Makes Payment (Escrow)       | backend, mobile | 13 | US-091     |
| US-022 | Self-Pickup Payment Options        | backend, mobile | 5  | US-021     |
| US-075 | Retry Failed Payments              | backend, mobile | 3  | US-021     |
| US-023 | Order Creation and Tracking        | backend, mobile | 5  | US-021     |
| US-070 | View Order History                 | backend, mobile | 3  | US-023     |
| US-025 | Platform Fee Deduction             | backend         | 3  | US-021     |
| US-072 | Seller Payout Bank/UPI Management  | backend, mobile | 5  | US-025     |
| US-071 | View Payment and Transaction       | backend, mobile | 5  | US-021     |

## Exit Criteria

* Cart and checkout flow complete
* Payment gateway integration done
* Escrow system operational
* Order tracking working
* Fee calculation accurate

---

# Sprint 6 - Shipping & Delivery

## Goal

Enable fulfillment workflow.

## Stories

| ID     | Story                                     | Repo            | SP | Dependency |
| ------ | ----------------------------------------- | --------------- | -- | ---------- |
| US-092 | Lifecycle State - Shipping                | backend         | 3  | US-023     |
| US-026 | Seller Prepares Package and Uploads Proof | backend, mobile | 5  | US-023     |
| US-027 | Pickup Scheduling                         | backend, mobile | 5  | US-026     |
| US-028 | Item Pickup by Logistics Partner          | backend         | 5  | US-027     |
| US-029 | Shipment Tracking                         | backend, mobile | 5  | US-028     |
| US-030 | Buyer Receives Item and Uploads Proof     | backend, mobile | 5  | US-029     |
| US-031 | Delivery Confirmation via In-App Button   | backend, mobile | 3  | US-030     |
| US-032 | Failed Delivery and Rescheduling          | backend         | 5  | US-029     |
| US-024 | Payment Release After Buyer Confirmation  | backend         | 5  | US-031     |
| US-085 | Seller Payment Release Notification       | backend, mobile | 3  | US-024     |

## Exit Criteria

* End-to-end shipping operational
* Logistics partner integration complete
* Payment release mechanism working

---

# MVP RELEASE

Includes:

* User Registration & Profiles
* Listing Creation (AI-assisted)
* Search & Discovery
* Communication (Chat, Voice, Video)
* Negotiation & Direct Buy
* Cart & Checkout
* Escrow & Payments
* Shipping & Delivery
* Order Tracking

---

# Sprint 7 - Order Cancellation & Returns

## Goal

Enable order cancellation and return workflows.

## Stories

| ID     | Story                                  | Repo            | SP | Dependency |
| ------ | -------------------------------------- | --------------- | -- | ---------- |
| US-058 | Order Cancellation by Buyer            | backend, mobile | 5  | US-023     |
| US-059 | Order Cancellation by Seller (Penalty) | backend, mobile | 5  | US-023     |
| US-093 | Lifecycle State - Return               | backend         | 3  | US-031     |
| US-033 | Buyer Initiates Return                 | backend, mobile | 8  | US-031     |
| US-034 | Return Approval and Reverse Logistics  | backend, mobile | 8  | US-033     |
| US-035 | Refund Processing                      | backend         | 5  | US-034     |

## Exit Criteria

* Order cancellation working with penalties
* Return flow complete
* Refund processing operational

---

# Sprint 8 - Ratings & Disputes

## Goal

Enable ratings, reviews, and dispute resolution.

## Stories

| ID     | Story                         | Repo            | SP | Dependency |
| ------ | ----------------------------- | --------------- | -- | ---------- |
| US-036 | Buyer Rates Seller            | backend, mobile | 5  | US-031     |
| US-037 | Seller Rates Buyer            | backend, mobile | 3  | US-031     |
| US-094 | Lifecycle State - Dispute     | backend         | 3  | US-031     |
| US-047 | Raise Dispute/Grievance       | backend, mobile | 8  | US-031     |
| US-055 | Admin Dispute Resolution      | backend, web    | 8  | US-047     |

## Exit Criteria

* Rating system working
* Dispute mechanism functional
* Admin dispute resolution tools ready

---

# Sprint 9 - Trust & Safety

## Goal

Implement fraud detection and safety measures.

## Stories

| ID     | Story                                          | Repo        | SP | Dependency |
| ------ | ---------------------------------------------- | ----------- | -- | ---------- |
| US-048 | Fraud Listing Detection                        | backend, AI | 8  | US-009     |
| US-049 | Image Proof Authenticity Validation            | backend, AI | 5  | US-048     |
| US-082 | Image Watermark Detection                      | backend, AI | 5  | US-049     |
| US-050 | Daily Listing Limit                            | backend     | 3  | US-009     |
| US-052 | Fraud Score and Velocity Checks                | backend     | 8  | US-048     |
| US-081 | Block Transactions for Users Under Invest      | backend     | 5  | US-052     |
| US-051 | Progressive Penalties for Violations           | backend     | 5  | US-052     |

## Exit Criteria

* Fraud detection system operational
* Image validation working
* Velocity checks implemented
* Penalty system functional

---

# Sprint 10 - Admin Operations

## Goal

Build admin dashboard and moderation tools.

## Stories

| ID     | Story                            | Repo        | SP | Dependency |
| ------ | -------------------------------- | ----------- | -- | ---------- |
| US-083 | System Audit Trail               | backend     | 8  | S0-001     |
| US-053 | Admin User Management            | backend,web | 8  | US-001     |
| US-054 | Admin Listing Moderation         | backend,web | 5  | US-084     |
| US-057 | Admin Content Moderation         | backend,web | 5  | US-016     |
| US-056 | Admin Transaction Monitoring     | backend,web | 5  | US-023     |
| US-100 | Admin Analytics Dashboard        | backend,web | 8  | US-056     |

## Exit Criteria

* Admin dashboard operational
* Moderation queues working
* Analytics and monitoring in place
* Audit trail complete

---

# Sprint 11 - Support & Notifications

## Goal

Build support system and notification infrastructure.

## Stories

| ID     | Story                                | Repo            | SP | Dependency |
| ------ | ------------------------------------ | --------------- | -- | ---------- |
| US-095 | Lifecycle State - Support Ticket     | backend         | 3  | None       |
| US-043 | On-Screen AI Bot Assistance          | backend, mobile | 8  | None       |
| US-045 | Chat with Human Support              | backend, mobile | 5  | US-095     |
| US-046 | Call Human Support                   | backend, mobile | 5  | US-095     |
| US-074 | Track Support Ticket Status          | backend, mobile | 3  | US-095     |
| US-086 | WhatsApp Notifications               | backend         | 5  | US-077     |
| US-087 | Notification Preferences Management  | backend, mobile | 3  | US-077     |

## Exit Criteria

* AI bot working
* Human support system operational
* Notification infrastructure complete
* WhatsApp integration done

---

# Sprint 12 - Premium Features (Buyer)

## Goal

Launch premium buyer subscription plans.

## Stories

| ID     | Story                                | Repo            | SP | Dependency |
| ------ | ------------------------------------ | --------------- | -- | ---------- |
| US-096 | Lifecycle State - Premium Subscript  | backend         | 3  | None       |
| US-079 | Buyer Premium Plan Features          | backend, mobile | 3  | None       |
| US-038 | Buyer Upgrades to Premium            | backend, mobile | 8  | US-079     |
| US-042 | Subscription Management              | backend, mobile | 5  | US-038     |

## Exit Criteria

* Premium subscription plans launched
* Payment and auto-renewal working
* Feature gating by plan operational

---

# Sprint 13 - AI Photo Search (Premium Feature)

## Goal

Enable visual search for premium users.

## Stories

| ID     | Story                             | Repo            | SP | Dependency |
| ------ | --------------------------------- | --------------- | -- | ---------- |
| US-039 | Photo-Based Search                | backend,AI      | 13 | US-038     |
| US-040 | Visual Search Results Ranking     | backend, AI     | 8  | US-039     |
| US-041 | Search Refinement with Filters    | backend, mobile | 5  | US-040     |

## Exit Criteria

* Photo search working for premium users
* Visual similarity ranking accurate
* Search refinement filters functional

---

# Sprint 14 - Localization & Compliance

## Goal

Add multi-language support and compliance features.

## Stories

| ID     | Story                                    | Repo            | SP | Dependency |
| ------ | ---------------------------------------- | --------------- | -- | ---------- |
| US-044 | Multi-Language Support                   | mobile, web     | 8  | None       |
| US-097 | Data Export Request (GDPR Compliance)    | backend, mobile | 5  | US-001     |
| US-098 | Data Deletion Request (Right to Forget)  | backend, mobile | 5  | US-097     |
| US-099 | Screen Reader and Accessibility Support  | mobile, web     | 8  | None       |

## Exit Criteria

* 10+ Indian languages supported
* GDPR compliance features working
* Accessibility WCAG 2.1 AA compliant

---

# Sprint 15 - Enhancement & Optimization

## Goal

Add advanced features and optimize platform.

## Stories

| ID     | Story                        | Repo            | SP | Dependency |
| ------ | ---------------------------- | --------------- | -- | ---------- |
| US-064 | Upgrade Listing Plan         | backend, mobile | 5  | US-009     |
| US-065 | Bulk Listing Upload          | backend, web    | 8  | US-009     |
| US-067 | Seller Performance Analytics | backend, mobile | 5  | US-023     |
| US-060 | Logistics Partner Tasks View | backend         | 5  | US-028     |

## Exit Criteria

* Listing upgrades working
* Bulk upload for power sellers
* Analytics dashboards complete
* Logistics partner app features ready

---

# Summary

## Sprint Statistics

| Sprint | Focus Area                          | Stories | SP  | Duration |
| ------ | ----------------------------------- | ------- | --- | -------- |
| S0     | Foundation & Architecture           | 8       | 41  | 2 weeks  |
| S1     | Identity & User Management          | 10      | 46  | 2 weeks  |
| S2     | Seller Listing Creation             | 10      | 52  | 2 weeks  |
| S3     | Discovery & Search                  | 4       | 21  | 2 weeks  |
| S4     | Communication & Negotiation         | 10      | 56  | 2 weeks  |
| S5     | Cart, Checkout & Payments           | 12      | 62  | 2 weeks  |
| S6     | Shipping & Delivery                 | 10      | 44  | 2 weeks  |
| S7     | Order Cancellation & Returns        | 6       | 34  | 2 weeks  |
| S8     | Ratings & Disputes                  | 5       | 27  | 2 weeks  |
| S9     | Trust & Safety                      | 7       | 39  | 2 weeks  |
| S10    | Admin Operations                    | 6       | 39  | 2 weeks  |
| S11    | Support & Notifications             | 7       | 32  | 2 weeks  |
| S12    | Premium Features (Buyer)            | 4       | 19  | 2 weeks  |
| S13    | AI Photo Search                     | 3       | 26  | 2 weeks  |
| S14    | Localization & Compliance           | 4       | 26  | 2 weeks  |
| S15    | Enhancement & Optimization          | 4       | 23  | 2 weeks  |
| **Total** | **16 Sprints (32 weeks / 8 months)** | **110** | **587** | **32 weeks** |

## Coverage

### Stories Planned: 110 / 107 total user stories

**Planned in Sprints:**
- All MVP core stories (US-001 to US-059): ✅ 59 stories
- Enhancement backlog (US-060, US-064, US-065, US-067): ✅ 4 stories
- New features (US-068 to US-087): ✅ 20 stories
- Lifecycle states (US-088 to US-096): ✅ 9 stories
- Compliance (US-097 to US-100): ✅ 4 stories
- Social Login (US-101 to US-102): ✅ 2 stories
- Profile Management Extensions (US-103 to US-105): ✅ 3 stories
- Authentication Extensions (US-106 to US-107): ✅ 2 stories

**Not Yet Planned (Future Backlog):**
- US-061: Screen Reader Compatibility (merged into US-099)
- US-062: Data Export Request (merged into US-097)
- US-063: Data Deletion Request (merged into US-098)
- US-066: Saved Searches and Alerts (included in Sprint 3)

All 107 user stories from the user-stories.md file are now covered in the sprint plan.

## Key Milestones

### MVP Release (End of Sprint 6 - Week 16)
**Core Features:**
- User registration with Aadhaar verification
- AI-assisted listing creation
- Search and discovery
- Multi-channel communication (chat, voice, video)
- Price negotiation
- Cart and checkout
- Escrow payments
- End-to-end shipping and delivery
- Order tracking

### Production Release (End of Sprint 8 - Week 20)
**Added Features:**
- Order cancellation
- Returns and refunds
- Ratings and reviews
- Dispute resolution

### Full Platform (End of Sprint 15 - Week 32)
**Complete Feature Set:**
- Fraud detection and safety
- Admin operations
- Support system
- Premium subscriptions
- AI photo search
- Multi-language support
- Compliance (GDPR)
- Accessibility
- Analytics and optimization

## Dependencies & Critical Path

**Critical Path Stories:**
1. S0-001 (Backend Skeleton) → Foundation for all backend work
2. US-001 (User Registration) → Required for all user-facing features
3. US-004 (Create Listing) → Required for marketplace functionality
4. US-009 (Listing Publication) → Required for buyers to see items
5. US-021 (Payment & Escrow) → Required for transactions
6. US-031 (Delivery Confirmation) → Required for payment release

**Parallel Tracks:**
- Infrastructure (CI/CD, databases) - Sprint 0
- Mobile + Backend + Web development teams can work in parallel
- AI features (US-005, US-039-041) - Can be developed alongside core features
- Admin tools (Sprint 10) - Can be built after core features are stable

## Repo Distribution

| Repo    | Primary Sprints                                      | Story Count |
| ------- | ---------------------------------------------------- | ----------- |
| backend | All sprints (S0-S15)                                 | ~80 stories |
| mobile  | S1-S9, S11-S14                                       | ~65 stories |
| web     | S0, S1, S2, S10, S14, S15                            | ~20 stories |
| AI      | S2, S9, S13                                          | ~10 stories |
| infra   | S0                                                   | ~5 stories  |

## Risk Areas

**High Complexity:**
- Escrow payment system (US-021, US-091) - 13 SP
- AI photo search (US-039) - 13 SP
- Video calls with recording (US-015) - 8 SP
- Fraud detection (US-048, US-052) - 8 SP each

**External Dependencies:**
- Aadhaar verification API (US-001)
- Payment gateway integration (US-021)
- Logistics partner APIs (US-027, US-028)
- WhatsApp Business API (US-086)

**Performance Critical:**
- Search with filters (US-011) - Must scale to millions of listings
- Real-time notifications (US-077) - Must handle high throughput
- Image processing (US-005, US-039) - Must be fast (<2 seconds)

## Recommendations

1. **Start with Sprint 0** - Critical foundation work
2. **MVP Focus** - Prioritize Sprints 1-6 for fastest time to market (16 weeks)
3. **Parallel Development** - Mobile, backend, and web teams work concurrently
4. **CI/CD Early** - S0-006 enables continuous delivery
5. **API-First** - S0-007 OpenAPI framework ensures consistency
6. **State Machines** - Lifecycle states (US-088 to US-096) are architectural - implement early
7. **Incremental AI** - Start with basic AI (US-005) before advanced features (US-039)
8. **Admin Tools** - Can be deprioritized if needed (Sprint 10)
9. **Premium Features** - Launch after MVP is stable (Sprints 12-13)
