# Product Requirements Document (PRD)

**Product:** ValueX  
**Company:** ValueQuo Solutions Pvt. Ltd.  
**Author:** Abhay Kumar  
**Date:** April 21, 2026  
**Version:** 1.4

---

## Revisions

| Sl. | Changes | Version | Author | Reviewer |
|-----|---------|---------|--------|----------|
| 1 | Initial Draft | 0.1 | ChatGPT | Abhay |
| 2 | Added missing requirements | 1.0 | Abhay | - |
| 3 | Added more details | 1.1 | MS Copilot | Abhay |
| 4 | Added Premium Plans | 1.2 | Abhay | - |
| 5 | Added Lifecycle State | 1.3 | Abhay | - |
| 6 | Added Social Login Options (Google Sign-In, Apple Sign-In) | 1.4 | Abhay | - |

---

## Table of Contents

1. [Product Overview](#1-product-overview)
2. [Goals & Non-Goals](#2-goals--non-goals)
3. [Target Users & Personas](#3-target-users--personas)
4. [Key Use Cases / User Journeys](#4-key-use-cases--user-journeys)
5. [Feature Breakdown (by Domain)](#5-feature-breakdown-by-domain)
6. [Functional Requirements](#6-functional-requirements)
7. [Non-Functional Requirements](#7-non-functional-requirements)
8. [Trust & Safety Requirements](#8-trust--safety-requirements)
9. [Payment & Transaction Flow](#9-payment--transaction-flow)
10. [Shipping & Logistics Flow](#10-shipping--logistics-flow)
11. [Data Model Overview](#11-data-model-overview)
12. [API Expectations](#12-api-expectations)
13. [External Integrations](#13-external-integrations)
14. [Admin & Moderation Capabilities](#14-admin--moderation-capabilities)
15. [Analytics & Metrics (KPIs)](#15-analytics--metrics-kpis)
16. [Risks & Open Questions](#16-risks--open-questions)
17. [Premium Plans](#17-premium-plans)
18. [Lifecycle State Machines](#18-lifecycle-state-machines)
19. [Suggested Future Enhancements](#19-suggested-future-enhancements)

---

## 1. Product Overview

A pan-India **C2C (consumer-to-consumer) marketplace platform** enabling users to buy and sell used items via mobile apps (Android/iOS) and web, with integrated payments, shipping, AI assistance, and strong trust & safety mechanisms.

The platform aims to combine the **simplicity of OLX** with the **transaction reliability of Amazon**, including:

- Escrow-based payments
- Shipping integration (forward + reverse logistics)
- Aadhaar-based identity verification
- AI-powered listing and search including premium photo-based smart search for upgraded buyers
- Communication tools (chat, voice, video)

**ValueX** aims to balance ease of use with enterprise-grade transaction reliability, targeting trust gaps prevalent in informal resale platforms.

---

## 2. Goals & Non-Goals

### Goals

- Enable secure buying/selling of used goods across India
- Provide end-to-end transaction flow (listing → negotiation → payment → delivery → confirmation)
- Minimize fraud using identity verification, escrow, and activity monitoring
- Enable AI-assisted listing creation and discovery
- Provide multi-language accessibility
- Support scalable and reliable infrastructure
- Enable AI-powered visual search to improve product discovery
- Introduce premium buyer features to generate additional revenue streams

### Non-Goals

- Inventory ownership by platform (not first-party commerce)
- Warehousing or fulfillment by platform
- Real-time auction system
- International marketplace (initial phase limited to India)

### Success Criteria

**Success Metrics (First 12 Months):**
- ≥ 90% transactions completed without dispute
- Fraud rate < 1% of total orders
- ≥ 25% of searches using AI/visual search
- ≥ 60% DAU/MAU retention for active buyers

---

## 3. Target Users & Personas

### Seller Persona
**Individuals selling used items**

**Needs:**
- Easy listing creation
- Fair pricing guidance
- Protection from fake buyers
- Guaranteed payment

### Buyer Persona
**Individuals looking for affordable used items**

**Needs:**
- Trustworthy sellers
- Item authenticity
- Delivery assurance
- Return capability

### Admin / Operations Persona
- User moderation
- Dispute resolution
- Fraud monitoring
- Platform health monitoring

### Logistics Partner Persona
- Item pickup & delivery
- Status updates
- Reverse logistics execution

### Customer Support Agent Persona
- Ticket handling
- Call/chat support
- Dispute facilitation

### High-Risk Users (System Concern)
- Fraud sellers (fake listings, wrong items)
- Fraud buyers (fake interest, harassment, returns abuse)

---

## 4. Key Use Cases / User Journeys

### Seller Journey

1. Register via Mobile OTP (primary), Google Sign-In, or Apple Sign-In
2. Capture item photos via app
3. Create listing (AI-assisted)
4. Choose listing plan – Basic, Boosted, Priority
5. Pay as per selected plan
6. Receive buyer messages/calls/video calls
7. Negotiate price
8. Accept final price
9. Buyer places order
10. Seller prepares package, uploads proof images
11. Item picked up by logistics partner
12. Payment released after buyer confirmation

### Buyer Journey

1. Search using photo (number of search limits applies to free plan users)
2. Browse/search listings
3. View item details
4. Chat/call/video call seller
5. Negotiate price
6. Add to cart (multiple items possible)
7. Choose delivery or self-pickup
8. Make payment (escrow)
9. Track shipment
10. Receive item and upload proof images
11. Confirm receipt and quality → triggers payment release

### Return Flow

1. Buyer initiates return
2. Buyer ships item back at own cost
3. Seller receives item
4. Refund processed (conditions dependent)

### Failed Delivery Journey

1. Logistics attempts delivery
2. Buyer unavailable → reschedule
3. Failure threshold reached → return to seller

### Order Cancellation

- **Buyer cancels before pickup** → escrow refunded
- **Seller cancels** → seller penalty applied

### Dispute Journey

1. Buyer/seller raises dispute
2. Evidence submission (images, chat logs)
3. Admin review
4. Resolution: refund / partial refund / release

---

## 5. Feature Breakdown (by Domain)

### User Management
- Multi-method authentication for user registration and login:
  - **Mobile OTP** (primary — always required on first registration)
  - **Google Sign-In** (optional convenience login after account creation)
  - **Apple Sign-In** (optional convenience login after account creation)
- Aadhaar-based identity verification (skippable until first transaction)
- One-user-one-account enforcement
- Profile management

### Listings
- Photo-based listing creation
- Multi-category tagging
- AI-assisted metadata generation

### Communication
- Chat (stored)
- Masked voice calls
- Video calls (stored)

### Transactions
- Price negotiation system
- Cart (multi-item)
- Order management

### Payments
- Escrow system
- Buyer's confirmation based release
- Platform fees

### Logistics
- Pickup scheduling
- Delivery tracking
- Reverse pickup (returns)

### Ratings & Reviews
- Seller ratings
- Buyer ratings

### AI Features
- Price suggestions
- Auto listing creation
- Search optimization
- **Photo-based search**
  - Visual similarity matching for listings
  - Ranked results based on match confidence score
- Fraud detection

### Buyer Premium Features
- Photo-based smart search (camera + gallery upload)
- Subscription for photo search and support

### Notifications
- In-app
- Email
- SMS
- WhatsApp

### Support & Assistance
- On-screen bot assistant
- Multi-language UI
- Chat with human support person
- Call with human support person

---

## 6. Functional Requirements

### User & Authentication
- **FR-1:** Users must register using Mobile OTP as the primary authentication method
- **FR-1.1:** System must support Google Sign-In as an optional convenience login for returning users
- **FR-1.2:** System must support Apple Sign-In as an optional convenience login for returning users
- **FR-1.3:** Social login (Google/Apple) on first use must still collect and verify mobile number via OTP before completing registration
- **FR-1.4:** Aadhaar-based identity verification is required before a user's first buy or sell transaction; it may be skipped at registration
- **FR-2:** System must enforce one account per user
- **FR-3:** Users must have unique identity mapping

### Listing
- **FR-4:** Seller must capture item images via mobile camera
- **FR-5:** System must allow multiple category tagging
- **FR-6:** AI must suggest category, description, condition, price
- **FR-6.1:** System must stop listing of restricted items
- **FR-6.2:** Seller must purchase one listing plan out of 3
- **FR-6.3:** System must allow listing as per purchased listing plan after successful payment

### Communication
- **FR-7:** Platform must support chat between buyer and seller
- **FR-8:** Platform must provide masked voice calling
- **FR-9:** Platform must support video calling
- **FR-10:** Chat and video history must be stored

### Negotiation & Orders
- **FR-11:** Buyers must negotiate price via system
- **FR-12:** Seller must explicitly accept negotiated price
- **FR-13:** Buyer must add items to cart
- **FR-14:** Buyer must choose delivery or self-pickup
- **FR-14.1:** Buyer must be able to initiate seller contact from listing page
- **FR-14.2:** Buyer must be able to directly purchase item using Buy Now flow

### Payments
- **FR-15:** Payment must be collected and held in escrow
- **FR-16:** Payment must be released only after OTP confirmation
- **FR-17:** Platform must deduct applicable fees
- **FR-17.1:** Seller must receive notification when payment is released

### Shipping
- **FR-18:** System must support pickup scheduling
- **FR-19:** System must track shipment status
- **FR-20:** Reverse logistics must be supported

### Proof & Verification
- **FR-21:** Seller must upload item & packaging images before pickup
- **FR-22:** Buyer must upload package & item images after delivery

### Returns
- **FR-23:** Buyer must be able to return item at own shipping cost
- **FR-23.1:** System must track return shipment when buyer returns the item to seller
- **FR-23.2:** Seller must confirm returned item receipt and quality before refund closure

### Ratings
- **FR-24:** Buyers must rate sellers
- **FR-25:** Sellers must rate buyers

### Support & Assistance
- **FR-26:** System must provide on-screen AI bot to assist users
- **FR-27:** System must provide option to change language of application as per user's preference
- **FR-28:** System must provide option to chat with human support personnel
- **FR-29:** System must provide option to call human support personnel
- **FR-30:** System must provide option to raise dispute and grievance

### Photo-Based Search
- **FR-31:** Buyer must be able to search items using mobile camera (only if upgraded)
- **FR-32:** Buyer must be able to upload image from gallery for search (only if upgraded)
- **FR-33:** System must analyze image and extract visual features
- **FR-34:** System must match uploaded image against existing listings
- **FR-35:** Search results must be ranked based on similarity score (highest match first)
- **FR-36:** System must support partial matches (similar items, not exact)
- **FR-37:** System must allow user to refine search using filters after visual search
- **FR-38:** System must handle low-quality images gracefully
- **FR-39:** System must provide fallback suggestions if no exact match found
- **FR-40:** System must allow to use photo-based search to user who upgraded

### Premium Access Control
- **FR-41:** System must restrict photo-based search to upgraded buyers only
- **FR-42:** System must prompt non-upgraded users to purchase access before using feature
- **FR-43:** System must verify user entitlement before executing image search
- **FR-44:** System must support subscription or one-time purchase model for feature access

### Additional Requirements
- **FR-45:** System must prevent buyer payment unless seller has accepted price
- **FR-46:** System must auto-expire inactive negotiations after configurable time
- **FR-47:** System must block users under investigation from transacting
- **FR-48:** System must validate image authenticity (no reuse across listings)
- **FR-49:** System must log all critical user actions for audit
- **FR-50:** User must be notified on every critical event like user creation, password change, cart item changes etc.
- **FR-51:** User must be able to view all active and historical orders
- **FR-52:** User must be able to view payment and transaction history
- **FR-53:** User must be able to save/bookmark listings
- **FR-54:** Seller must be able to manage payout bank/UPI details
- **FR-55:** User must be able to track support ticket status
- **FR-56:** User must be able to cancel/abort transaction before payment confirmation
- **FR-57:** User must be able to retry failed payments
- **FR-58:** Seller must be able to accept/reject/counter buyer offers
- **FR-59:** Listings must pass trust & safety review before publishing
- **FR-60:** System must automatically screen listings for policy violations before publishing

---

## 7. Non-Functional Requirements

### Performance
- API latency < 300 ms (95th percentile)
- Real-time chat latency < 1 second
- Image search response time < 2 seconds (95th percentile)

### Scalability
- Support millions of users
- Horizontal scaling of services
- System must support large-scale image indexing and retrieval

### Reliability
- 99.9% uptime
- Fault-tolerant services

### Security
- Encrypted communication (TLS)
- Secure payment processing
- Identity validation

### Storage
- Persistent storage for chat/video history
- Scalable media storage for images/videos

### Compliance
- GDPR-like consent management
- Indian IT Act compliance
- Aadhaar data handling compliance

### Accessibility
- Screen reader support
- WCAG 2.1 AA compliance
- Language fallback support

---

## 8. Trust & Safety Requirements

- Aadhaar-based identity verification
- One-account-per-user enforcement
- Fraud listing detection
- Monitoring of chat/call behaviour
- Image proof before and after shipment
- Escrow-based payment protection
- Buyer confirmation for delivery
- Rating-based reputation system
- Detection of fake buyers (spam calls/messages)
- Limit daily number of items listing
- Stop listing of restricted items
- Progressive penalties (warning → suspension → ban)
- Automated fraud score thresholds
- Velocity checks (listing, messaging, calls)

---

## 9. Payment & Transaction Flow

1. Buyer selects item(s)
2. Negotiated price finalized
3. Buyer makes payment
4. Payment held in escrow
5. Seller ships item
6. Buyer receives item
7. Buyer confirms receipt of item
8. Payment released to seller
9. Platform deducts fees

### Premium Feature Payment Flow

1. Buyer selects premium feature (photo search)
2. Buyer makes payment
3. System activates premium feature access
4. Buyer can use photo-based search feature

### Additional Rules
- Refund initiation ≤ 24 hours post-approval
- Escrow hold timeout auto-release rule

---

## 10. Shipping & Logistics Flow

1. Seller prepares item
2. Seller uploads proof images
3. Pickup scheduled
4. Logistics partner collects item
5. Shipment tracking enabled
6. Item delivered to buyer
7. Buyer uploads proof images
8. Buyer confirms delivery
9. Reverse pickup initiated if return requested
10. Pickup within 48 hours
11. Delivery ETA confidence score

---

## 11. Data Model Overview

### Key Entities

- **User**
- **IdentityVerification**
- **Listing**
- **Category**
- **Order**
- **Cart**
- **Payment**
- **Escrow**
- **Shipment**
- **ReturnRequest**
- **ChatMessage**
- **CallLog**
- **VideoSession**
- **Rating**
- **FraudFlag**
- **ImageEmbedding**
- **SearchQuery**
- **SearchResult**
- **SimilarityScore**

---

## 12. API Expectations

### REST/GraphQL APIs for:
- User management
- Listing management
- Order processing
- Payment handling
- Shipment tracking
- Access control validation API (check entitlement of premium feature)
- Image search (list of matching items with similarity score)
- Search refinement (apply filters on visual search results)

### Real-time APIs:
- Chat (WebSockets)
- Call/video signaling

### Security
- Secure APIs with authentication tokens

### API Error Standards
- Standardized error codes
- Retry & idempotency support

---

## 13. External Integrations

- **Aadhaar authentication service**
- **Google OAuth 2.0** (Google Sign-In)
- **Apple Sign-In** (Sign in with Apple)
- **SMS OTP provider** (mobile number verification)
- **Payment gateways** (for escrow)
- **Logistics providers** (pickup, delivery, reverse pickup)
- **Communication services** (voice/video)
- **WhatsApp** for notification to users
- **AI/ML services** for:
  - Pricing
  - Image recognition
  - Fraud detection
- **Image embedding / vector search service**
- **Visual similarity search engine**

---

## 14. Admin & Moderation Capabilities

- User management (ban/suspend)
- Listing moderation (remove/approve)
- Fraud monitoring dashboard
- Dispute handling
- Transaction monitoring
- Content moderation (chat/video)
- Return processing
- Backend exception handling
- Role-based access control (Admin, Moderator, Support)
- Action audit logs
- Manual override controls

---

## 15. Analytics & Metrics (KPIs)

### Business Metrics
- GMV (Gross Merchandise Value)
- Conversion rate
- Listing success rate
- Fraud rate
- Return rate
- Delivery success rate
- User growth
- Active users
- Average order value
- Daily, weekly and monthly transaction report

### Photo Search Metrics
- Photo search usage rate
- Conversion rate from photo search
- Search accuracy (click-through on top results)
- Average similarity score of selected items

### Premium Feature Metrics
- Premium feature adoption rate
- Conversion rate (free → paid users)
- Revenue from photo search feature
- Usage frequency per paid user

### Operational Metrics
- Dispute resolution SLA
- Average delivery delay
- Fraud detection accuracy
- Support ticket resolution time

---

## 16. Risks & Open Questions

### Risks
- Fraudulent sellers sending incorrect items
- Fake buyers causing harassment
- Aadhaar integration complexity
- Logistics failures/delays
- Payment disputes
- High storage cost (video/chat history)
- Incorrect matches leading to poor user experience
- High compute cost for image processing
- Performance issues with large dataset
- Low adoption if pricing is not optimized
- User drop-off due to paywall
- Competitors offering free image search

### Mitigations
- Seller score-based visibility control
- Image watermarking
- Progressive escrow release for high-value items

### Open Questions
- Dispute resolution policy details
- Refund processing rules
- Handling damaged goods in transit
- Limits on return eligibility
- Legal compliance for Aadhaar usage
- Acceptable similarity threshold for matching
- Handling duplicate listings
- Strategy for improving model accuracy over time
- Should pricing be subscription-based or pay-per-use?
- Should trial access be provided?
- Should feature be bundled with other premium features?

---

## 17. Premium Plans

### Listing Plan (Seller)

| Feature | Basic | Boosted | Priority |
|---------|-------|---------|----------|
| **Price** | ₹99 (After discount: ₹49) | ₹399 (After discount: ₹149) | ₹699 (After discount: ₹249) |
| **Listing** | In order of date of listing | Listed on top when searched | Boosted + Listed on landing page, marked as featured item |
| **Validity** | 7 days | 7 days | 1 month |
| **Support** | AI + Email | Basic + Chat (Human) | Boosted + On Call |

### Buyer Plan

| Feature | Basic | Smart | Vision |
|---------|-------|-------|--------|
| **Price** | ₹0 | ₹99 (After discount: ₹49) | ₹499 (After discount: ₹149) |
| **Photo Search** | 3/day | 10/day | Unlimited |
| **Seller Contact** | Chat | Basic + Voice call | Smart + Video Call |
| **Validity** | Unlimited | 7 days | 1 month |
| **Support** | AI + Email | Basic + Chat (Human) | Smart + On Call |

---

## 18. Lifecycle State Machines

This section defines the lifecycle states, transitions, and business rules governing the major entities and workflows within the ValueX platform. These lifecycle definitions serve as the operational source of truth for frontend behavior, backend processing, payment handling, logistics orchestration, dispute resolution, moderation, and analytics.

### User Account Lifecycle

**States:**
- NEW
- OTP_PENDING
- IDENTITY_VERIFICATION_PENDING
- ACTIVE
- UNDER_REVIEW
- RESTRICTED
- SUSPENDED
- BANNED
- CLOSED

**Transition Flow:**
```
→ NEW 
→ OTP_PENDING 
→ IDENTITY_VERIFICATION_PENDING 
→ ACTIVE 
→ UNDER_REVIEW 
→ RESTRICTED 
→ SUSPENDED 
→ BANNED 
→ CLOSED
```

**Business Rules:**
- User cannot transact unless account status is ACTIVE
- Users under fraud investigation may be moved to UNDER_REVIEW or RESTRICTED
- Fraud-confirmed users must be BANNED
- One verified identity must map to only one ACTIVE account

---

### Seller Listing Lifecycle

**States:**
- DRAFT
- PLAN_SELECTION_PENDING
- PLAN_PAYMENT_PENDING
- PLAN_PAYMENT_FAILED
- PLAN_PAYMENT_SUCCESS
- MEDIA_UPLOAD_PENDING
- AI_DETAILS_GENERATED
- PRICE_PENDING
- TRUST_SAFETY_REVIEW
- APPROVED
- PUBLISHED
- BUYER_INQUIRY_PENDING
- NEGOTIATION_IN_PROGRESS
- OFFER_ACCEPTED
- ORDER_CREATED
- SOLD
- EXPIRED
- DEACTIVATED_BY_SELLER
- REMOVED_BY_ADMIN
- REJECTED
- REVISION_REQUIRED

**Transition Flow:**
```
→ DRAFT 
→ PLAN_SELECTION_PENDING 
→ PLAN_PAYMENT_PENDING 
→ PLAN_PAYMENT_SUCCESS 
→ MEDIA_UPLOAD_PENDING 
→ AI_DETAILS_GENERATED 
→ PRICE_PENDING 
→ TRUST_SAFETY_REVIEW 
→ APPROVED 
→ PUBLISHED 
→ BUYER_INQUIRY_PENDING 
→ NEGOTIATION_IN_PROGRESS 
→ OFFER_ACCEPTED 
→ ORDER_CREATED 
→ SOLD
```

**Exception Flow:**
```
TRUST_SAFETY_REVIEW → REJECTED
REJECTED → REVISION_REQUIRED
REVISION_REQUIRED → TRUST_SAFETY_REVIEW
PUBLISHED → EXPIRED
PUBLISHED → DEACTIVATED_BY_SELLER
PUBLISHED → REMOVED_BY_ADMIN
```

**Business Rules:**
- Listing cannot be published without successful listing-plan payment
- All listings must pass trust & safety review before publication
- Restricted/prohibited items must move to REJECTED state
- Listing visibility and validity depend on purchased seller plan

---

### Buyer Search Lifecycle

**Standard Search States:**
- SEARCH_STARTED
- FILTER_APPLIED
- RESULTS_DISPLAYED
- ITEM_VIEWED
- ITEM_SAVED
- SELLER_CONTACTED

**Photo Search States:**
- PHOTO_SEARCH_REQUESTED
- ENTITLEMENT_CHECK
- UPGRADE_REQUIRED
- PREMIUM_PAYMENT_PENDING
- PREMIUM_ACTIVE
- IMAGE_CAPTURED_OR_UPLOADED
- IMAGE_ANALYSIS_IN_PROGRESS
- SIMILARITY_MATCHING
- RESULTS_RANKED
- RESULTS_DISPLAYED

**Business Rules:**
- Photo-based search is available only to entitled buyers as per plan limits
- Results must be ranked by similarity score
- System must support exact and partial visual matches

---

### Negotiation Lifecycle

**States:**
- NEGOTIATION_STARTED
- BUYER_OFFER_SENT
- SELLER_REVIEWING
- SELLER_COUNTERED
- BUYER_REVIEWING
- OFFER_ACCEPTED
- OFFER_REJECTED
- NEGOTIATION_EXPIRED
- NEGOTIATION_CANCELLED

**Business Rules:**
- Buyer cannot proceed to payment until seller accepts final offer
- Inactive negotiations must auto-expire after configurable duration
- Accepted offers lock final transaction price temporarily

---

### Cart Lifecycle

**States:**
- EMPTY
- ITEM_ADDED
- CART_ACTIVE
- ITEM_REMOVED
- CHECKOUT_STARTED
- CHECKOUT_ABANDONED
- PAYMENT_PENDING
- ORDER_CREATED

**Business Rules:**
- Cart may contain multiple listings
- Item availability must be revalidated during checkout
- Sold or expired listings must be automatically removed from cart, and buyer must be notified the reason of removal

---

### Order Lifecycle

**States:**
- ORDER_INITIATED
- SELLER_PRICE_ACCEPTED
- CHECKOUT_STARTED
- PAYMENT_PENDING
- PAYMENT_FAILED
- PAYMENT_SUCCESS
- ESCROW_HELD
- SHIPPING_MODE_SELECTED
- SELLER_PACKING_PENDING
- SELLER_PROOF_UPLOADED
- PICKUP_SCHEDULED
- PICKED_UP
- IN_TRANSIT
- OUT_FOR_DELIVERY
- DELIVERED
- BUYER_PROOF_PENDING
- BUYER_CONFIRMATION_PENDING
- COMPLETED
- RETURN_REQUESTED
- DISPUTE_RAISED
- SHIPMENT_LOST
- DELIVERY_FAILED
- RETURN_TO_SELLER
- CANCELLED

**Business Rules:**
- Payment must remain in escrow until buyer confirmation or dispute resolution
- Buyer proof upload is mandatory before confirmation
- Lost shipment must trigger investigation workflow
- Order cannot move to COMPLETED unless escrow is released

---

### Payment & Escrow Lifecycle

**States:**
- PAYMENT_INITIATED
- PAYMENT_PENDING
- PAYMENT_SUCCESS
- PAYMENT_FAILED
- ESCROW_CREATED
- ESCROW_HELD
- RELEASE_PENDING
- RELEASED_TO_SELLER
- REFUND_REVIEW
- REFUND_APPROVED
- REFUND_REJECTED
- REFUND_PROCESSED
- PARTIAL_RELEASE
- ADMIN_HOLD

**Business Rules:**
- Escrow release requires buyer confirmation or admin decision
- Refunds may be partial or full
- Failed payments must support retry mechanism
- Seller must receive notification on escrow release

---

### Shipping Lifecycle

**States:**
- SHIPPING_NOT_REQUIRED
- SHIPPING_REQUIRED
- SHIPPING_PARTNER_SELECTION
- PICKUP_SLOT_SELECTED
- PICKUP_SCHEDULED
- PICKUP_ASSIGNED
- PICKED_UP
- IN_TRANSIT
- OUT_FOR_DELIVERY
- DELIVERED
- PICKUP_FAILED
- PICKUP_RESCHEDULED
- DELIVERY_FAILED
- DELIVERY_RESCHEDULED
- RETURN_TO_SELLER
- SHIPMENT_DELAYED
- SHIPMENT_LOST
- INVESTIGATION_OPENED

**Business Rules:**
- Platform must support integrated and self-arranged shipping modes
- Shipment tracking must be visible to both buyer and seller
- Delivery exceptions must trigger notifications and operational review

---

### Return Lifecycle

**States:**
- RETURN_REQUESTED
- RETURN_ELIGIBILITY_CHECK
- RETURN_APPROVED
- RETURN_REJECTED
- RETURN_SHIPPING_PENDING
- RETURN_IN_TRANSIT
- RETURN_DELIVERED_TO_SELLER
- SELLER_RETURN_INSPECTION
- RETURN_ACCEPTED
- RETURN_DISPUTED
- TRUST_SAFETY_REVIEW
- REFUND_INITIATED
- REFUND_PROCESSED
- RETURN_CLOSED

**Business Rules:**
- Buyer bears return shipping cost unless overridden by admin resolution
- Seller must verify returned item condition
- Disputed returns must move to trust & safety review

---

### Dispute Lifecycle

**States:**
- DISPUTE_CREATED
- EVIDENCE_PENDING
- EVIDENCE_SUBMITTED
- TRUST_SAFETY_REVIEW
- MORE_INFO_REQUIRED
- DECISION_PENDING
- RESOLVED_BUYER_REFUND
- RESOLVED_SELLER_RELEASE
- RESOLVED_PARTIAL_REFUND
- DISPUTE_CLOSED

**Business Rules:**
- Escrow remains locked during active dispute
- Evidence may include images, shipment proof, chat logs, and call/video records
- Admin must have manual override capability

---

### Buyer Premium Plan Lifecycle

**States:**
- PLAN_NOT_ACTIVE
- UPGRADE_PROMPT_SHOWN
- PLAN_SELECTED
- PAYMENT_PENDING
- PAYMENT_SUCCESS
- PLAN_ACTIVE
- PLAN_EXPIRED
- RENEWAL_PENDING

**Business Rules:**
- Buyer plans control:
  - Photo search quota
  - Communication privileges
  - Support level
- System must validate entitlement before premium feature access

---

### Seller Listing Plan Lifecycle

**States:**
- NO_PLAN
- PLAN_SELECTED
- PLAN_PAYMENT_PENDING
- PLAN_PAYMENT_SUCCESS
- PLAN_ACTIVE
- PLAN_EXPIRED
- RENEWAL_REQUIRED

**Business Rules:**
- Listing plans control visibility, support level, and listing validity
- Listings must not remain active after plan expiry

---

### Support Ticket Lifecycle

**States:**
- TICKET_CREATED
- ASSIGNED
- IN_PROGRESS
- WAITING_FOR_USER
- WAITING_FOR_INTERNAL_REVIEW
- RESOLVED
- CLOSED
- REOPENED

**Business Rules:**
- Tickets may be linked to listings, orders, disputes, payments, or accounts
- Support SLA must be monitored and measurable

---

### Notification Lifecycle

**States:**
- EVENT_TRIGGERED
- NOTIFICATION_QUEUED
- CHANNEL_SELECTED
- SENT
- DELIVERED
- READ
- FAILED
- RETRY_PENDING

**Notification Channels:**
- In-app
- Email
- SMS
- WhatsApp

**Business Rules:**
- Critical events must trigger user notifications
- Failed notifications must support retry mechanism
- Notification preference settings must be configurable by user

---

## 19. Suggested Future Enhancements

- AI-based fraud scoring system
- Automated dispute resolution
- Smart recommendations engine
- Voice-based search
- Seller performance analytics dashboard
- Insurance for high-value items
- Dynamic pricing optimization
- Real-time camera scanning with AR guidance
- Object detection to auto-crop item from background
- Personalized visual search based on user behavior
- Freemium model with limited free photo searches
- Bundled premium plans (photo search + priority support + advanced filters)

---

**End of Document**
