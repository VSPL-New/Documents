# Sprint Coverage Analysis

**Analysis Date:** 2026-06-05

## Summary

| Metric | Count | Percentage |
|--------|-------|------------|
| **Total User Stories** | 100 | 100% |
| **Covered in Sprints** | 44 | 44% |
| **Missing from Sprints** | 56 | 56% |

## Covered Stories (44 stories across 6 sprints)

### Sprint 0 - Foundation & Architecture (8 stories)
- S0-001: Backend Project Skeleton
- S0-002: Flutter Project Setup
- S0-003: Admin Web Setup
- S0-004: PostgreSQL Setup
- S0-005: Redis Setup
- S0-006: CI/CD Pipeline
- S0-007: OpenAPI Framework
- S0-008: Lifecycle State Framework

### Sprint 1 - Identity & User Management (5 stories)
- US-001: User Registration with Aadhaar Verification
- US-002: One Account Per User Enforcement
- US-003: User Profile Management
- US-077: Critical Event Notifications
- US-088: Lifecycle State - User Account

### Sprint 2 - Seller Listing Creation (9 stories)
- US-004: Create Listing with Photo Capture
- US-005: AI-Assisted Listing Creation
- US-006: Multi-Category Tagging
- US-007: Restricted Items Prevention
- US-008: Seller Chooses Listing Plan
- US-009: Listing Publication After Payment
- US-010: Edit/Delete Listing
- US-084: Pre-Publication Trust & Safety Review
- US-089: Lifecycle State - Listing

### Sprint 3 - Discovery & Search (4 stories)
- US-011: Browse and Search Listings
- US-012: View Listing Details
- US-066: Saved Searches and Alerts
- US-073: Save and Bookmark Listings

### Sprint 4 - Communication & Negotiation (9 stories)
- US-013: Chat with Seller
- US-014: Masked Voice Call
- US-015: Video Call with Recording
- US-016: Communication History Storage
- US-017: Price Negotiation
- US-018: Prevent Checkout Without Price Acceptance
- US-069: Buyer Initiates Contact from Listing
- US-076: Seller Negotiation Management
- US-080: Auto-Expire Inactive Negotiations

### Sprint 5 - Cart, Checkout & Payments (9 stories)
- US-019: Add to Cart (Multi-Item)
- US-020: Choose Delivery or Self-Pickup
- US-021: Buyer Makes Payment (Escrow)
- US-022: Self-Pickup Payment Options
- US-023: Order Creation and Tracking
- US-025: Platform Fee Deduction
- US-072: Seller Payout Bank/UPI Management
- US-090: Lifecycle State - Order
- US-091: Lifecycle State - Payment & Escrow

### Sprint 6 - Shipping & Delivery (8 stories)
- US-026: Seller Prepares Package and Uploads Proof
- US-027: Pickup Scheduling
- US-028: Item Pickup by Logistics Partner
- US-029: Shipment Tracking
- US-030: Buyer Receives Item and Uploads Proof
- US-031: Delivery Confirmation via In-App Button
- US-032: Failed Delivery and Rescheduling
- US-092: Lifecycle State - Shipping

---

## Missing Stories (56 stories)

### Payment & Escrow (1 story)
- **US-024**: Payment Release After Buyer Confirmation

### Returns (3 stories) - Sprint 7 planned
- **US-033**: Buyer Initiates Return
- **US-034**: Return Approval and Reverse Logistics
- **US-035**: Refund Processing

### Ratings & Reviews (2 stories) - Sprint 8 planned
- **US-036**: Buyer Rates Seller
- **US-037**: Seller Rates Buyer

### Premium Features (5 stories) - Sprint 10 & 11 planned
- **US-038**: Buyer Upgrades to Premium (Photo Search Access)
- **US-039**: Photo-Based Search (Premium Feature)
- **US-040**: Visual Search Results Ranking
- **US-041**: Search Refinement with Filters
- **US-042**: Subscription Management

### Support & Assistance (5 stories) - Sprint 12 planned
- **US-043**: On-Screen AI Bot Assistance
- **US-044**: Multi-Language Support
- **US-045**: Chat with Human Support
- **US-046**: Call Human Support
- **US-047**: Raise Dispute/Grievance

### Trust & Safety (5 stories) - Sprint 8 planned
- **US-048**: Fraud Listing Detection
- **US-049**: Image Proof Authenticity Validation
- **US-050**: Daily Listing Limit
- **US-051**: Progressive Penalties for Violations
- **US-052**: Fraud Score and Velocity Checks

### Admin & Moderation (7 stories) - Sprint 9 planned
- **US-053**: Admin Dashboard - User Management
- **US-054**: Admin Dashboard - Listing Moderation
- **US-055**: Admin Dashboard - Dispute Resolution
- **US-056**: Admin Dashboard - Transaction Monitoring
- **US-057**: Admin Dashboard - Content Moderation (Chat/Video)
- **US-058**: Order Cancellation by Buyer (Before Pickup)
- **US-059**: Order Cancellation by Seller (With Penalty)

### Enhancement Backlog (7 stories)
- **US-060**: Logistics Partner - View Assigned Tasks
- **US-061**: Screen Reader Compatibility
- **US-062**: Data Export Request
- **US-063**: Data Deletion Request
- **US-064**: Upgrade Listing Plan
- **US-065**: Bulk Listing Upload
- **US-067**: Seller Performance Analytics

### New Features - PRD v1.3 (13 stories)
- **US-068**: Direct Buy Now Flow
- **US-070**: View Order History
- **US-071**: View Payment and Transaction History
- **US-074**: Track Support Ticket Status
- **US-075**: Retry Failed Payments
- **US-078**: Listing Plan Features and Pricing
- **US-079**: Buyer Premium Plan Features
- **US-081**: Block Transactions for Users Under Investigation
- **US-082**: Image Watermark Detection
- **US-083**: System Audit Trail
- **US-085**: Seller Payment Release Notification
- **US-086**: WhatsApp Notifications
- **US-087**: Notification Preferences Management

### Lifecycle States (4 stories)
- **US-093**: Lifecycle State - Return
- **US-094**: Lifecycle State - Dispute
- **US-095**: Lifecycle State - Support Ticket
- **US-096**: Lifecycle State - Premium Subscription

### Compliance & Accessibility (4 stories) - Sprint 12 planned
- **US-097**: Data Export Request (GDPR Compliance)
- **US-098**: Data Deletion Request (Right to be Forgotten)
- **US-099**: Screen Reader and Accessibility Support
- **US-100**: Admin Analytics Dashboard

---

## Analysis

### Current Sprint Plan Coverage (Sprint 0-6)
The current Sprint-plan.md covers the **MVP Release** scope:
- ✅ User registration and authentication
- ✅ Listing creation and management
- ✅ Search and discovery
- ✅ Communication and negotiation
- ✅ Cart, checkout, and payments
- ✅ Shipping and delivery

### Missing High-Priority Features
Several **critical features** mentioned in Sprint-plan.md (Sprint 7-12) are defined but stories not detailed:

1. **Sprint 7 - Returns & Disputes**: Stories US-033 to US-035, US-047, US-094
2. **Sprint 8 - Ratings & Trust**: Stories US-036, US-037, US-048 to US-052, US-081, US-082
3. **Sprint 9 - Admin Operations**: Stories US-053 to US-057, US-074, US-083, US-100
4. **Sprint 10 - Premium Plans**: Stories US-038, US-042, US-078, US-079, US-096
5. **Sprint 11 - AI Photo Search**: Stories US-039 to US-041
6. **Sprint 12 - Support & Compliance**: Stories US-043 to US-046, US-061, US-062, US-063, US-086, US-087, US-095, US-097 to US-099

### Recommendations

1. **For MVP (Sprint 0-6)**: Add US-024 (Payment Release) to Sprint 5
2. **For Post-MVP**: Expand Sprint 7-12 sections in Sprint-plan.md with full story tables
3. **For v1.3 Features**: Many new features (US-068 to US-087) need sprint assignment
4. **For Lifecycle States**: US-093 to US-096 should be distributed across relevant sprints

---

## Next Steps

### Option 1: Import MVP Only (44 stories)
```bash
# Use Sprint-plan.md to import stories sprint-by-sprint
python import_user_stories_to_github.py --sprint 0 --dry-run
python import_user_stories_to_github.py --sprint 1 --dry-run
# ... etc
```

### Option 2: Import All 100 Stories
```bash
# Use user-stories.md to import all stories with full details
python import_user_stories_to_github.py --dry-run
```

### Option 3: Hybrid Approach
1. Import MVP stories (Sprint 0-6) using Sprint-plan.md
2. Import remaining 56 stories using user-stories.md with `--skip-existing`
3. Manually assign sprint labels to post-MVP stories in GitHub

---

**Document Generated:** 2026-06-05  
**Tool Used:** sprint-coverage-analysis script
