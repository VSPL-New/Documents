# ValueX User Stories

**Version:** 3.0  
**Based on:** PRD_ValueX_v1.3.docx + Flutter Plan Gap Analysis  
**Date:** 2026-07-05

---

## Table of Contents
1. [User Management & Authentication](#user-management--authentication)
2. [Seller - Listing Management](#seller---listing-management)
3. [Buyer - Discovery & Search](#buyer---discovery--search)
4. [Communication](#communication)
5. [Negotiation & Cart](#negotiation--cart)
6. [Orders & Payments](#orders--payments)
7. [Shipping & Logistics](#shipping--logistics)
8. [Returns](#returns)
9. [Ratings & Reviews](#ratings--reviews)
10. [Premium Features](#premium-features)
11. [Support & Assistance](#support--assistance)
12. [Trust & Safety](#trust--safety)
13. [Admin & Moderation](#admin--moderation)
14. [New Features - PRD v1.3 Alignment](#new-features---prd-v13-alignment)
15. [Lifecycle State Machines](#lifecycle-state-machines)
16. [Compliance & Accessibility](#compliance--accessibility)
17. [Profile Management Extensions](#profile-management-extensions)
18. [Authentication Extensions](#authentication-extensions)
19. [Address Management](#address-management)
20. [Mobile App Security](#mobile-app-security)
21. [UI Quality](#ui-quality)
22. [Home](#home)
23. [Seller Order Management](#seller-order-management)
24. [Listing Details](#listing-details)
25. [Listing Notifications](#listing-notifications)
26. [Plan Administration](#plan-administration)
27. [Payment Gateway](#payment-gateway)

---

## User Management & Authentication

### US-001: User Registration via Mobile OTP, Email Verification, and Aadhaar
**As a** new user  
**I want to** register by verifying my mobile number and email address  
**So that** I can access the platform with a trusted identity

**Related User Stories:**
- This story covers first-time registration only. Returning-user login: US-106
- Session renewal after the token issued here expires: US-107
- Avatar catalog and later profile edits: US-003
- Addresses are not collected at Sign Up. The first address is saved when the user buys with home delivery (US-020) or posts an item to sell (US-004); they are managed later under My Addresses (US-113); entry and verification follow US-108

**Registration Flow:**
1. Verify mobile (SMS OTP) → account: `EMAIL_VERIFICATION_PENDING`
2. Verify email (email OTP) → account: `IDENTITY_VERIFICATION_PENDING`
3a. Complete Aadhaar verification → account: `SIGNUP_PENDING` (`aadhaarVerified = true`)
3b. Skip Aadhaar → account: `SIGNUP_PENDING` (`aadhaarVerified = false`, limited until Aadhaar done)
4. Sign Up: provide profile details, accept terms and consent → account: `ACTIVE`

**Acceptance Criteria:**
- Given I am on the registration page
- When I enter my mobile number
- Then I receive a 6-digit OTP via SMS
- When I enter the correct OTP within 5 minutes
- Then my account moves to `EMAIL_VERIFICATION_PENDING` state
- And I am issued a JWT to continue registration
- When I provide my email address
- Then I receive a 6-digit OTP via email
- When I enter the correct email OTP within 5 minutes
- Then my email is verified and account moves to `IDENTITY_VERIFICATION_PENDING` state
- When I choose to complete Aadhaar verification immediately
- Then I am prompted to enter my Aadhaar number and consent
- And after successful Aadhaar OTP verification, my account transitions to `SIGNUP_PENDING` with `aadhaarVerified = true`
- When I choose to skip Aadhaar verification
- Then I receive a new JWT and my account transitions to `SIGNUP_PENDING`
- And I am told that Aadhaar verification is required before any transaction; for selling it is asked for after I submit my listing, for buying and contacting at that step
- Given my account is `SIGNUP_PENDING`
- When I am shown the Sign Up form
- Then I provide my name, gender (optional) and avatar (optional)
- And I am not asked for a date of birth or an address
- And my verified mobile number and email are shown and cannot be edited
- When I open the Terms and Conditions and then accept them with the single terms and consent toggle
- And I submit the form
- Then my profile is saved, I receive a new JWT and my account transitions to `ACTIVE`
- And I can browse and use most platform features
- But I must complete Aadhaar verification before my first buy transaction, and before I can choose a listing plan for my first listing
- When I close or lose the app at any point during registration and reopen it later
- Then I am taken to the registration step that matches my current account state, without repeating steps I already completed
- And I am never shown a step that my account state does not allow

**Edge Cases:**
- App is closed, killed or restarted mid-registration (resume from the server-side account state)
- Access token is missing or no longer valid when the app is reopened mid-registration
- User started registration but never verified the mobile OTP (no token yet; registration restarts at mobile entry)
- Mobile number already linked to another account
- Email address already linked to another account
- User enters email OTP before mobile OTP is verified
- User cancels Aadhaar verification mid-flow
- Aadhaar verification fails (invalid, expired, or API timeout)
- User already registered with same Aadhaar (from a different account)
- Network interruption during any OTP or Aadhaar verification step
- Third-party Aadhaar service downtime
- User requests OTP too many times on mobile or email (rate limiting applies)
- App is closed on the Sign Up step (resume at Sign Up; email and mobile stay verified)
- User tries to accept terms without having opened the Terms and Conditions page
- User leaves gender empty (neutral default avatar, no gender stored)

**Validation Rules:**
- Mobile number must be 10 digits, Indian format; unique per account
- Registration progress is resumed from the server-side account state, never from locally cached screen state alone
- Mobile OTP is 6 digits, expires after 5 minutes
- Email must be a valid format; unique per account
- Email OTP is 6 digits, expires after 5 minutes
- Maximum 3 OTP send requests per mobile or email per 10 minutes
- Maximum 5 failed OTP attempts per channel before 10-minute cooldown
- Email verification must be completed before Aadhaar verification can begin
- Aadhaar must be valid 12-digit number (when provided)
- One Aadhaar can link to only one account across all states
- Terms & conditions and data-processing consent are accepted on the Sign Up step with one toggle, enabled only after the user has opened the Terms and Conditions page; the accepted terms version is stored
- Name: 3-50 characters, letters, spaces and `. ' -`
- Gender: optional; `MALE`, `FEMALE` or `OTHERS` when given; choosing the selected option again clears it
- Date of birth is not collected anywhere in the app
- Avatar: optional, from the published catalog; otherwise a default avatar chosen by gender (male-looking, female-looking, or neutral for `OTHERS` or when no gender is given)
- Accounts in `SIGNUP_PENDING` can still complete Aadhaar verification

**Error Scenarios:**
- `ERROR_MOBILE_ALREADY_REGISTERED`: "This mobile number is already registered"
- `ERROR_EMAIL_ALREADY_REGISTERED`: "This email is already linked to another account"
- `ERROR_INVALID_OTP`: "Invalid or expired OTP"
- `ERROR_OTP_EXPIRED`: "OTP has expired. Please request a new one"
- `ERROR_OTP_RATE_LIMIT`: "Too many OTP requests. Please try again in 10 minutes"
- `ERROR_OTP_MAX_ATTEMPTS`: "Too many failed attempts. Please request a new OTP"
- `ERROR_INVALID_STATE`: "This step is not available in the current account state"
- `ERROR_AADHAAR_ALREADY_USED`: "This Aadhaar is already linked to an account"
- `ERROR_AADHAAR_VERIFICATION_FAILED`: "Unable to verify Aadhaar. Please try again"
- `ERROR_AADHAAR_SERVICE_UNAVAILABLE`: "Verification service temporarily unavailable"
- `ERROR_AADHAAR_VERIFICATION_REQUIRED`: "Please complete Aadhaar verification to proceed"
- `ERROR_TERMS_NOT_ACCEPTED`: "Please accept the terms and conditions to continue"
- `ERROR_CONSENT_REQUIRED`: "Consent for data processing is required"
- `ERROR_INVALID_AVATAR`: "Selected avatar is not available. Please choose another"

---

### US-002: One Account Per User Enforcement
**As a** platform administrator  
**I want to** enforce one account per user  
**So that** fraud and duplicate accounts are prevented

**Acceptance Criteria:**
- Given a user attempts to register
- When the system detects Aadhaar already linked to an existing account
- Then registration is blocked
- And user is shown appropriate error message
- When user attempts to verify again with same Aadhaar from different device
- Then system prevents duplicate account creation
- And logs the attempt for security monitoring

**Edge Cases:**
- User lost access to original account and wants to register again
- User claims Aadhaar was used by someone else fraudulently
- System detects partial match (similar but not exact Aadhaar)
- User changes mobile but wants to use same Aadhaar

**Validation Rules:**
- Aadhaar uniqueness check must happen before account creation
- Check must include soft-deleted/suspended accounts
- System must maintain audit log of all Aadhaar verification attempts

**Error Scenarios:**
- `ERROR_DUPLICATE_ACCOUNT`: "An account with this identity already exists"
- `ERROR_ACCOUNT_RECOVERY_REQUIRED`: "Please use account recovery if you've lost access"

---

### US-003: User Profile Management
**As a** registered user  
**I want to** manage my profile information  
**So that** buyers/sellers can view relevant details about me

**Related User Stories:**
- Profile fields here (avatar, display name, ratings) are surfaced from the Profile Hub: US-103
- Addresses (home, office, any name the user gives) are not part of the profile; they are managed under My Addresses: US-113
- Account security (mobile/email change, sessions, delete account): US-105
- Logout: US-104

**Design Note (v3.3):** Users do **not** upload a free-form profile photo. Instead they pick an **avatar** from a fixed catalog of avatar images the frontend app ships/renders — this removes the need for image content moderation entirely (no user-supplied image ever reaches the platform for a profile picture). The backend owns the canonical list of valid avatar IDs and only stores which one is selected.

**Acceptance Criteria:**
- Given I am logged in
- When I navigate to my profile
- Then I can view my profile details (avatar, display name, gender if given, ratings, joined date)
- When I open the avatar picker
- Then I see the full catalog of available avatars
- When I select an avatar and confirm
- Then my profile updates to show the selected avatar
- When I update my display name
- Then changes are saved successfully
- And other users see updated information
- Given I have never picked an avatar
- When I view my profile
- Then a default avatar is shown

**Edge Cases:**
- User selects an avatar ID that isn't in the current catalog (stale client-side list, tampered request)
- User tries to change verified Aadhaar name
- User submits an empty/blank display name on update
- Avatar catalog changes (avatar removed) after a user already selected it — existing selection remains valid until the user picks a new one

**Validation Rules:**
- Avatar selection must be one of the platform's published avatar catalog IDs
- Every account has a default avatar from account creation, before any explicit selection
- Display name: 3-50 characters, no special symbols
- Aadhaar-verified name cannot be edited

**Error Scenarios:**
- `ERROR_INVALID_AVATAR`: "Selected avatar is not available. Please choose another"
- `ERROR_INAPPROPRIATE_CONTENT`: retired — no longer applicable, since profile pictures are no longer user-uploaded images

---

## Seller - Listing Management

### US-004: Create Listing with Photo Capture
**As a** seller  
**I want to** create a listing by capturing photos of my item  
**So that** I can quickly list items for sale

**Acceptance Criteria:**
- Given I am logged in as a seller
- When I tap "Sell Item"
- Then camera opens for photo capture
- When I capture at least 2 photos (max 10 photos)
- Then photos are uploaded to the system
- And I can proceed to add item details
- When I post the listing and have no saved address
- Then I am asked to enter my pickup address (entry and verification: US-108)
- And it is saved as my default address for pickup and delivery
- When I post the listing and already have saved addresses
- Then my default address is preselected and I can choose another saved address or enter a new one
- And a new address can be given a name such as Home, Office or any custom name
- And the city of the chosen address is shown as the item's location
- When I submit my listing and I have not completed Aadhaar verification
- Then, before I am taken to listing plan selection (US-008), I am asked to complete Aadhaar verification
- And once it is complete I continue to plan selection with my listing kept as it was
- And tapping Sell, capturing photos and filling in the listing are never blocked by Aadhaar

**Edge Cases:**
- User denies camera permission
- Camera fails to open
- User tries to upload more than 10 photos
- Photo quality is very poor
- User uploads non-item photos (random images)
- Network failure during photo upload
- Seller has no saved address when posting (the address is requested at that point, not at Sign Up)
- Seller leaves the Aadhaar verification step half-way or closes the app (the draft stays; the check is asked again on the next submit)

**Validation Rules:**
- Minimum 2 photos required
- Maximum 10 photos allowed
- Photo format: JPG, PNG, HEIC
- Max size per photo: 10MB
- Minimum resolution: 480x480px
- A listing cannot be posted without a pickup address; a new listing draft has no location until the seller chooses the address

**Error Scenarios:**
- `ERROR_CAMERA_PERMISSION_DENIED`: "Camera access required to capture photos"
- `ERROR_MAX_PHOTOS_EXCEEDED`: "Maximum 10 photos allowed"
- `ERROR_PHOTO_UPLOAD_FAILED`: "Failed to upload photo. Check your connection"
- `ERROR_INVALID_PHOTO`: "Photo quality too low or invalid format"
- `ERROR_PICKUP_ADDRESS_REQUIRED`: "Please add your pickup address to post this item"
- `ERROR_AADHAAR_VERIFICATION_REQUIRED`: "Please complete Aadhaar verification to proceed" (shown when a seller submits a listing, before plan selection)

**Related User Stories:**
- US-108: pickup address entry and verification
- US-113: managing saved addresses afterwards

---

### US-005: AI-Assisted Listing Creation
**As a** seller  
**I want** AI to suggest item details from my photos  
**So that** I can create listings faster with accurate information

**Acceptance Criteria:**
- Given I have uploaded item photos
- When AI analyzes the images
- Then system suggests:
  - Category (e.g., "Electronics > Mobile Phones")
  - Item title
  - Condition (New/Like New/Good/Fair/Poor)
  - Price range
  - Description
- When I review suggestions
- Then I can accept, edit, or reject each suggestion
- And I can manually enter any field

**Edge Cases:**
- AI cannot identify item from photos
- AI suggests wrong category
- AI suggests unrealistic price
- Photos contain multiple items
- Item is unique/rare with no comparable listings
- AI service timeout or failure

**Validation Rules:**
- AI suggestions are optional; manual entry always allowed
- Price suggestion must be within 20% of similar listings
- Category must be from predefined list
- Title max length: 100 characters
- Description max length: 2000 characters

**Error Scenarios:**
- `ERROR_AI_SERVICE_UNAVAILABLE`: "Auto-suggestions unavailable. Please enter details manually"
- `WARNING_UNABLE_TO_IDENTIFY`: "Unable to identify item. Please select category manually"
- `WARNING_PRICE_OUT_OF_RANGE`: "Suggested price may be too high/low. Please verify"

---

### US-006: Multi-Category Tagging
**As a** seller  
**I want to** tag my item with multiple categories  
**So that** it appears in relevant search results

**Acceptance Criteria:**
- Given I am creating/editing a listing
- When I select a primary category
- Then I can add up to 3 additional related categories
- When a buyer searches any of those categories
- Then my listing appears in results

**Edge Cases:**
- Seller selects duplicate categories
- Seller selects unrelated categories (spam attempt)
- Category tree is very deep (6+ levels)
- Seller tries to add more than allowed categories

**Validation Rules:**
- Primary category is mandatory
- Maximum 3 additional categories
- Categories must be from predefined taxonomy
- System flags suspicious category combinations for review

**Error Scenarios:**
- `ERROR_DUPLICATE_CATEGORY`: "Category already selected"
- `ERROR_MAX_CATEGORIES`: "Maximum 4 categories allowed"
- `WARNING_UNRELATED_CATEGORIES`: "Selected categories seem unrelated. This may affect visibility"

**Flutter Implementation Notes:**
- Multi-select category picker widget with hierarchical taxonomy
- Primary category chip shown separately from additional tags
- Tappable category tree with search/filter capability

---

### US-007: Restricted Items Prevention
**As a** platform  
**I want to** prevent listing of restricted items  
**So that** platform remains compliant and safe

**Acceptance Criteria:**
- Given a seller is creating a listing
- When AI/system detects restricted items in photos or description
- Then listing creation is blocked
- And seller is shown which items are prohibited
- And guidelines are displayed
- When seller tries to publish restricted item listing
- Then system prevents publication
- And flags account for review

**Restricted Item Categories:**
- Weapons, explosives, ammunition
- Drugs, narcotics, tobacco, alcohol
- Adult content
- Counterfeit/pirated goods
- Live animals
- Human body parts, organs
- Hazardous materials
- Documents (passports, IDs, degrees)

**Edge Cases:**
- Item is borderline (e.g., toy weapon)
- Description contains restricted keywords but item is legitimate
- Seller tries to bypass using coded language
- Item legal in some states but not others
- Seller appeals restriction

**Validation Rules:**
- Photo analysis for restricted items
- Text keyword scanning in title/description
- Manual review required for borderline cases
- Repeated violations lead to account suspension

**Error Scenarios:**
- `ERROR_RESTRICTED_ITEM`: "This item cannot be listed. See prohibited items policy"
- `ERROR_SUSPICIOUS_CONTENT`: "Listing flagged for review. You'll be notified within 24 hours"
- `ERROR_ACCOUNT_SUSPENDED`: "Your account is suspended due to policy violations"

---

### US-008: Seller Chooses Listing Plan
**As a** seller  
**I want to** choose a listing plan (Basic/Boosted/Priority)  
**So that** I can control visibility and reach

**Acceptance Criteria:**
- Given I have completed my listing draft
- When I proceed to publish
- Then, if I have not completed Aadhaar verification, I am first asked to complete it (US-004) and only then shown the plan options
- Then I am shown the listing plans that are available (the plans, their features and prices are managed by the platform and can change; today Basic, Boosted and Priority, see US-078 and US-116)
- When I select a plan
- Then I see the price, shown as including GST, and the plan's features
- When I select a plan that has a price
- Then I am redirected to payment (US-117)
- When payment succeeds
- Then my listing goes to the Trust & Safety review (US-084) and is published when it is approved (US-009)

**Edge Cases:**
- Seller cancels payment
- Payment fails
- Seller selects plan but closes app before payment
- Seller wants to upgrade existing listing
- Plan duration expires while listing is active

**Validation Rules:**
- Draft must be complete before plan selection
- A plan priced at zero needs no payment (none is free today; management can set a price to zero in the admin console, US-116)
- Paid plans require successful payment before publishing
- Plan duration starts from publication of the listing
- The price and validity I am charged are the ones shown to me when I choose, even if the plan is changed later
- Seller can have max 50 active listings

**Error Scenarios:**
- `ERROR_PAYMENT_FAILED`: "Payment unsuccessful. Please try again"
- `ERROR_INCOMPLETE_LISTING`: "Complete all required fields before selecting plan"
- `ERROR_MAX_LISTINGS_REACHED`: "You've reached the maximum listing limit"

---

### US-009: Listing Publication After Payment
**As a** seller  
**I want** my listing to be published immediately after successful payment  
**So that** buyers can discover it right away

**Acceptance Criteria:**
- Given I have selected a listing plan
- When payment is successful (or my chosen plan is priced at zero)
- Then my listing goes to the Trust & Safety review (US-084)
- And I receive a notification that it is under review (usually within a few hours)
- When the review approves my listing
- Then listing is published instantly
- And listing appears in search results
- And plan features are activated (boosted/priority placement)
- And I receive confirmation notification
- When I view my listings
- Then I see the published listing with plan badge

**Edge Cases:**
- Payment succeeds but listing publish fails
- Listing published but features not activated
- Duplicate payment for same listing
- Network interruption after payment
- Listing is rejected after payment (the seller edits it and resubmits it for review without paying again, up to 3 review attempts in total; after the 3rd failed review the plan fee is refunded)

**Validation Rules:**
- Payment must be confirmed before the review and before publishing
- Listing status: Draft → Plan payment → Trust & Safety review → Approved → Published
- If publishing fails after approval, the listing stays approved and publishing is retried; a payment that cannot be turned into a published listing is refunded
- Plan duration starts from publication of the listing
- Plan activation within 5 minutes of approval

**Error Scenarios:**
- `ERROR_PUBLISH_FAILED`: "Payment successful but listing failed to publish. Refund initiated"
- `ERROR_DUPLICATE_PAYMENT`: "This listing is already paid and published"

---

### US-010: Edit/Delete Listing
**As a** seller  
**I want to** edit or delete my listings  
**So that** I can keep information accurate and remove sold items

**Acceptance Criteria:**
- Given I have published listings
- When I view my listings
- Then I can select "Edit" or "Delete"
- When I edit and save
- Then changes reflect immediately
- And active negotiations are notified of changes
- When I delete a listing with no active orders
- Then listing is removed from platform
- When I try to delete a listing with active orders
- Then system prevents deletion
- And shows error message

**Edge Cases:**
- Seller edits price during active negotiation
- Seller deletes listing while buyer is viewing
- Seller changes item drastically (different item)
- Seller tries to delete listing with pending payment
- Edit violates new platform policies

**Validation Rules:**
- Cannot delete listing with: active orders, pending payment, open disputes
- Major edits (category, price >20% change) require re-moderation
- Edit history maintained for audit
- Deleted listings retained for 90 days (soft delete)

**Error Scenarios:**
- `ERROR_CANNOT_DELETE_ACTIVE_ORDER`: "Cannot delete listing with active orders"
- `ERROR_PRICE_CHANGE_TOO_HIGH`: "Price change >20% requires admin approval"
- `WARNING_BUYERS_WILL_BE_NOTIFIED`: "Active viewers will be notified of changes"

**Flutter Implementation Notes:**
- Edit launches pre-filled CreateListingScreen with existing data
- Delete requires confirmation bottom sheet with warning
- Swipe-to-delete with undo option in MyListingsScreen (within 2s)

---

## Buyer - Discovery & Search

### US-011: Browse and Search Listings
**As a** buyer  
**I want to** browse and search for items  
**So that** I can find what I need

**Acceptance Criteria:**
- Given I am on the home page
- When I enter search keywords
- Then I see relevant listings ranked by relevance
- When I browse by category
- Then I see listings in that category
- When I apply filters (price, condition, location)
- Then results are filtered accordingly
- When I scroll down
- Then more results load (pagination)

**Edge Cases:**
- Search query with no results
- Search with special characters or very long text
- Multiple filters applied
- Location filter outside India
- Price range filters with min > max

**Validation Rules:**
- Search query max length: 200 characters
- Results show only published, non-expired listings
- Paid plan listings (Priority/Boosted) ranked higher
- Distance-based ranking if a location is chosen on Home (my current location or one of my saved locations); that location is used only for searching and is never saved or entered as an address
- Minimum relevance score for display

**Error Scenarios:**
- `NO_RESULTS_FOUND`: "No items found. Try different keywords"
- `ERROR_INVALID_FILTERS`: "Invalid filter combination"

---

### US-012: View Listing Details
**As a** buyer  
**I want to** view complete listing details  
**So that** I can make an informed decision

**Acceptance Criteria:**
- Given I click on a listing
- When listing details page loads
- Then I see:
  - All photos (swipeable gallery)
  - Title, description, condition
  - Price
  - Seller name, rating, location (city of the seller's pickup address), joined date
  - Listing age
  - Communication options (chat, call, video call)
  - Add to cart button
- When I swipe photos
- Then I can view all images in full resolution
- When I click on seller profile
- Then I see seller's other listings and reviews

**Edge Cases:**
- Listing deleted/expired while buyer is viewing
- Seller suspended while buyer views listing
- Photos fail to load
- Seller has no other listings or reviews

**Validation Rules:**
- All photos must be viewable
- Seller rating displayed as stars (0-5)
- Price displayed in INR with currency symbol
- Listing age displayed (e.g., "Posted 2 days ago")

**Error Scenarios:**
- `ERROR_LISTING_NOT_AVAILABLE`: "This listing is no longer available"
- `ERROR_SELLER_SUSPENDED`: "Seller account is suspended"

---

## Communication

### US-013: Chat with Seller
**As a** buyer  
**I want to** chat with the seller  
**So that** I can ask questions about the item

**Acceptance Criteria:**
- Given I am viewing a listing
- When I tap "Chat"
- Then chat window opens
- When I type and send a message
- Then seller receives notification
- When seller replies
- Then I receive notification and see message in chat
- And all messages are stored persistently
- When I open chat history
- Then I see all previous conversations with timestamps

**Edge Cases:**
- Seller doesn't respond
- Buyer sends spam/inappropriate messages
- Chat initiated but listing deleted
- Network interruption during chat
- User blocks seller

**Validation Rules:**
- Message max length: 2000 characters
- Image sharing allowed (max 5MB)
- Chat history retained for 6 months after transaction closure
- Profanity filter applied to messages
- System flags suspicious patterns (spam, harassment)

**Error Scenarios:**
- `ERROR_MESSAGE_TOO_LONG`: "Message exceeds 2000 characters"
- `ERROR_SELLER_UNAVAILABLE`: "Seller is currently unavailable"
- `WARNING_CONTENT_FLAGGED`: "Message contains inappropriate content"

---

### US-014: Masked Voice Call
**As a** buyer  
**I want to** call the seller without revealing my number  
**So that** I can discuss details while maintaining privacy

**Acceptance Criteria:**
- Given I am viewing a listing or in chat
- When I tap "Call"
- Then system initiates masked voice call
- And both parties' numbers remain hidden
- When call connects
- Then voice quality is clear
- And call duration is tracked
- When call ends
- Then call log is stored with duration

**Edge Cases:**
- Seller doesn't answer
- Call drops mid-conversation
- Poor network quality
- User denies microphone permission
- Call service unavailable

**Validation Rules:**
- Both parties must consent to call recording (if applicable)
- Call logs retained for 6 months
- Max call duration: 30 minutes per session
- Caller ID shows platform number, not actual user number

**Error Scenarios:**
- `ERROR_MICROPHONE_PERMISSION`: "Microphone access required for calls"
- `ERROR_CALL_FAILED`: "Unable to connect call. Please try again"
- `ERROR_NO_ANSWER`: "Seller didn't answer. Try again later"

**Flutter Implementation Notes:**
- Requires VoIP SDK integration (Agora / WebRTC via flutter_webrtc)
- `permission_handler` for microphone permission request
- In-call UI overlay with mute, speaker, end-call controls
- Call state managed via Riverpod CallNotifier

---

### US-015: Video Call with Recording
**As a** buyer  
**I want to** video call the seller to see the item  
**So that** I can verify condition before purchasing

**Acceptance Criteria:**
- Given I am viewing a listing or in chat
- When I tap "Video Call"
- Then I see consent notice: "This call will be recorded for safety"
- When I accept
- Then system prompts seller to join
- When seller accepts
- Then video call connects
- And recording starts
- When call ends
- Then video is stored securely
- And recording is deleted after 1 month of transaction closure

**Edge Cases:**
- User denies camera/microphone permission
- Seller rejects video call
- Poor network causes video lag
- Recording fails but call proceeds
- User wants to download recording

**Validation Rules:**
- Both parties must consent before recording
- Consent captured at call start
- Video stored encrypted
- Auto-delete 30 days after transaction closure
- User can report inappropriate behavior during call
- Max video call duration: 30 minutes

**Error Scenarios:**
- `ERROR_CAMERA_PERMISSION`: "Camera and microphone access required"
- `ERROR_SELLER_DECLINED`: "Seller declined video call"
- `ERROR_RECORDING_FAILED`: "Recording unavailable but call can proceed"
- `WARNING_LOW_BANDWIDTH`: "Poor connection. Video quality may be affected"

**Flutter Implementation Notes:**
- Same VoIP SDK as US-014 (Agora preferred for recording support)
- Consent dialog mandatory before initiating; cannot skip
- Camera preview + remote video in PiP layout
- Network quality indicator widget during call

---

### US-016: Communication History Storage
**As a** platform  
**I want to** store all communication history  
**So that** disputes can be resolved with evidence

**Acceptance Criteria:**
- Given users communicate via chat, call, or video
- When communication occurs
- Then all data is logged with timestamps
- And stored securely with encryption
- When a dispute is raised
- Then admins can access relevant communication logs
- When transaction closes
- Then video recordings are auto-deleted after 30 days
- And chat/call logs retained for 6 months

**Edge Cases:**
- Storage limit exceeded
- User requests data deletion (GDPR-like)
- Communication involves inappropriate content
- System needs to retrieve very old logs

**Validation Rules:**
- Chat messages: 6 months retention
- Call logs: 6 months retention
- Video recordings: Auto-delete 30 days post-transaction
- All communication encrypted at rest
- Access logs maintained for audit

**Error Scenarios:**
- `ERROR_STORAGE_FULL`: "Unable to store recording"
- `ERROR_RETRIEVAL_FAILED`: "Unable to load conversation history"

---

## Negotiation & Cart

### US-017: Price Negotiation
**As a** buyer  
**I want to** negotiate the price with the seller  
**So that** I can get a better deal

**Acceptance Criteria:**
- Given I am viewing a listing
- When I tap "Make Offer"
- Then I can enter my proposed price
- When I submit offer
- Then seller receives notification
- When seller accepts, counters, or rejects
- Then I receive notification
- When seller accepts my offer
- Then accepted price is locked
- And I can proceed to checkout
- When seller counters
- Then I can accept, counter again, or decline

**Edge Cases:**
- Buyer offers absurdly low price (e.g., 90% off)
- Multiple buyers negotiating simultaneously
- Seller changes mind after accepting
- Negotiation inactive for days
- Buyer makes offer then ghosts

**Validation Rules:**
- Offer must be > 0 and <= listed price
- Max 5 back-and-forth negotiations per buyer-seller pair
- Negotiation auto-expires after 48 hours of inactivity
- Accepted price cannot be changed unless both parties agree
- System logs all negotiation activity

**Error Scenarios:**
- `ERROR_INVALID_OFFER`: "Offer must be between ₹1 and ₹[listed_price]"
- `ERROR_MAX_NEGOTIATIONS`: "Maximum negotiation attempts reached"
- `ERROR_NEGOTIATION_EXPIRED`: "This negotiation has expired"
- `WARNING_LOW_OFFER`: "Your offer is significantly lower than asking price"

---

### US-018: Prevent Checkout Without Price Acceptance
**As a** platform  
**I want to** prevent buyers from checking out unless seller accepts price  
**So that** transactions are based on mutual agreement

**Acceptance Criteria:**
- Given a buyer wants to purchase an item
- When seller has not yet accepted the negotiated price
- Then "Proceed to Checkout" button is disabled
- And message displays: "Waiting for seller to accept your offer"
- When seller accepts price
- Then button becomes enabled
- And buyer can proceed to payment

**Edge Cases:**
- Buyer tries to bypass by direct URL access
- Seller accepts but buyer already left the page
- Price acceptance expires before buyer checks out
- Multiple items in cart with different acceptance states

**Validation Rules:**
- Backend validation required (not just frontend disable)
- Price acceptance valid for 24 hours
- After 24 hours, buyer must re-negotiate
- Cart items show acceptance status indicator

**Error Scenarios:**
- `ERROR_PRICE_NOT_ACCEPTED`: "Seller hasn't accepted your offer yet"
- `ERROR_ACCEPTANCE_EXPIRED`: "Price acceptance expired. Please re-negotiate"
- `ERROR_UNAUTHORIZED_CHECKOUT`: "Cannot proceed without seller acceptance"

**Flutter Implementation Notes:**
- Checkout button disabled state tied to negotiation state in Riverpod
- Status badge on each cart item (Pending / Accepted / Expired)
- Real-time state update via polling or WebSocket when seller accepts

---

### US-019: Add to Cart (Multi-Item)
**As a** buyer  
**I want to** add multiple items to my cart  
**So that** I can purchase them in one transaction

**Acceptance Criteria:**
- Given I am viewing listing(s) with accepted prices
- When I tap "Add to Cart"
- Then item is added to my cart
- When I navigate to cart
- Then I see all added items with:
  - Item image, title
  - Seller name
  - Accepted price
  - Delivery option selection
- When I have items from multiple sellers
- Then items are grouped by seller
- When I proceed to checkout
- Then I make one payment transaction
- And system creates one order per item, each with its own order number and its own escrow

**Edge Cases:**
- Item removed by seller after adding to cart
- Price changed by seller after cart addition
- Cart has mix of delivery and self-pickup items
- Cart abandoned for days
- Seller suspends listing while in buyer's cart

**Validation Rules:**
- Max 20 items in cart at once
- Cart items expire after 24 hours (need to re-add)
- Item must have accepted price to add to cart
- Stock check before checkout (if item sold)

**Error Scenarios:**
- `ERROR_ITEM_UNAVAILABLE`: "This item is no longer available"
- `ERROR_PRICE_CHANGED`: "Price has changed. Please review"
- `ERROR_MAX_CART_ITEMS`: "Cart limit reached (20 items)"
- `ERROR_CART_EXPIRED`: "Cart items expired. Please add again"

**Flutter Implementation Notes:**
- CartScreen groups items by seller using ListView with section headers
- 24hr expiry countdown shown per item as a subtle timer chip
- Cart persisted locally via `isar` / `drift`, synced to backend on open

---

### US-020: Choose Delivery or Self-Pickup
**As a** buyer  
**I want to** choose between delivery or self-pickup  
**So that** I have flexibility in receiving my item

**Acceptance Criteria:**
- Given I am checking out an item
- When I view delivery options
- Then I see:
  - **Delivery**: Address selection, estimated delivery date, shipping cost
  - **Self-Pickup**: Seller's pickup location, pickup hours
- When I select "Delivery"
- Then I can add/select delivery address
- And if I have no saved address I am asked to enter one (entry and verification: US-108) and it is saved as my default address
- And if I have saved addresses my default address is preselected, I can choose another, or enter a new address and give it a name such as Home, Office or any custom name
- And shipping cost is calculated
- When I select "Self-Pickup"
- Then I choose payment option:
  - "Pay Now" (escrow)
  - "Pay at Pickup" (direct to seller)
- And I see seller's pickup address and contact

**Edge Cases:**
- Seller doesn't offer delivery option
- Seller doesn't offer self-pickup option
- Buyer's address is outside delivery serviceable area
- Shipping cost exceeds item price
- Seller location too far for self-pickup

**Validation Rules:**
- At least one option must be available
- Delivery address must be complete with pincode
- Self-pickup address must be valid
- Shipping cost must be calculated before checkout
- Buyer must agree to terms for selected option

**Error Scenarios:**
- `ERROR_NO_DELIVERY_AVAILABLE`: "Seller doesn't offer delivery to your location"
- `ERROR_NO_SELF_PICKUP`: "Self-pickup not available for this item"
- `ERROR_INVALID_ADDRESS`: "Please enter complete delivery address"

**Flutter Implementation Notes:**
- Delivery option card with the reusable address component from US-108 (search, verification, name) and the list of saved addresses
- Shipping cost calculated via backend API on address selection
- Self-pickup shows seller location on embedded map widget

---

## Orders & Payments

### US-021: Buyer Makes Payment (Escrow)
**As a** buyer  
**I want to** pay securely via escrow  
**So that** my money is protected until I receive the item

**Acceptance Criteria:**
- Given I have items in cart with chosen delivery options
- When I proceed to checkout
- Then I see order summary:
  - Item(s) price
  - Shipping cost (if delivery)
  - Platform fees
  - Total amount
- When I confirm and pay
- Then payment is processed via payment gateway
- When payment succeeds
- Then funds are held in escrow (separate per item)
- And one order is created per item, each with its own order number
- And each seller is notified to ship their own items
- And I receive order confirmation

**Edge Cases:**
- Payment gateway timeout
- Payment fails after deduction
- Payment succeeds but creating the order for one of the items fails (the consolidated payment covers several item orders)
- User closes app during payment
- Duplicate payment attempt

**Validation Rules:**
- Payment amount must match the total of all the item orders in the checkout
- Escrow created per item (not combined); each item's amount is paid out only to that item's seller
- Every order covers exactly one item
- Payment confirmation required before order creation
- Buyer must complete payment within 15 minutes
- Failed payments auto-cancel order

**Error Scenarios:**
- `ERROR_PAYMENT_FAILED`: "Payment unsuccessful. Please try again"
- `ERROR_PAYMENT_TIMEOUT`: "Payment timed out. Your cart is still saved"
- `ERROR_GATEWAY_UNAVAILABLE`: "Payment service temporarily unavailable"
- `ERROR_INSUFFICIENT_BALANCE`: "Payment failed due to insufficient funds"

---

### US-022: Self-Pickup Payment Options
**As a** buyer using self-pickup  
**I want to** choose between advance payment or pay-at-pickup  
**So that** I have flexibility in payment

**Acceptance Criteria:**
- Given I selected "Self-Pickup"
- When I proceed to payment
- Then I see two options:
  - **Pay Now**: Amount held in escrow, released after in-app confirmation
  - **Pay at Pickup**: No online payment, buyer pays seller directly
- When I select "Pay Now"
- Then I complete payment via gateway
- And amount held in escrow
- And seller is notified item is sold
- When I select "Pay at Pickup"
- Then no payment is processed
- And seller is notified of pickup appointment
- And order status is "Pending Pickup Payment"

**Edge Cases:**
- Buyer selects "Pay at Pickup" but doesn't show up
- Seller refuses to hand over item despite "Pay at Pickup"
- Buyer pays at pickup but disputes quality
- Buyer changes mind and wants escrow after selecting direct payment

**Validation Rules:**
- "Pay at Pickup" requires buyer-seller agreement (seller must enable)
- "Pay Now" follows standard escrow rules
- Platform fees only charged on "Pay Now" transactions
- No refund mechanism for "Pay at Pickup" disputes

**Error Scenarios:**
- `ERROR_SELLER_DISABLED_PAY_AT_PICKUP`: "Seller requires advance payment"
- `WARNING_NO_PLATFORM_PROTECTION`: "Pay at Pickup is not protected by escrow"

**Flutter Implementation Notes:**
- Warning banner prominently shown for "Pay at Pickup" option
- "Pay at Pickup" option rendered only when seller has enabled it
- Seller enable/disable toggle in listing settings

---

### US-023: Order Creation and Tracking
**As a** buyer  
**I want to** track my order status  
**So that** I know when to expect delivery

**Acceptance Criteria:**
- Given I have placed an order
- When I view "My Orders"
- Then I see order with status:
  - Awaiting Pickup
  - Picked Up
  - In Transit
  - Out for Delivery
  - Delivered
- When I click on an order
- Then I see detailed timeline with timestamps
- And shipping partner details (if applicable)
- When order status changes
- Then I receive push notification

**Edge Cases:**
- Tracking not updated by logistics partner
- Order stuck in one status for days
- Several items bought together from the same seller are separate orders and are shipped separately
- Logistics partner returns item to seller

**Validation Rules:**
- Order status must progress sequentially
- Timestamps must be in correct order
- Status updates within SLA (e.g., pickup within 48 hours)
- Buyer can contact support if status stale >24 hours

**Error Scenarios:**
- `WARNING_TRACKING_DELAYED`: "Tracking information not yet available"
- `ERROR_SHIPMENT_EXCEPTION`: "Delivery delayed due to logistical issues"

---

### US-024: Payment Release After Buyer Confirmation
**As a** seller  
**I want** payment released after buyer confirms receipt  
**So that** I receive my money once transaction completes

**Acceptance Criteria:**
- Given buyer received the item
- When buyer taps "Item Received" in app (for delivery)
- Or buyer taps "Item Received" after self-pickup
- Then buyer is prompted to upload proof images (optional)
- And buyer confirms item quality
- When buyer confirms
- Then escrow releases payment to seller
- And platform deducts fees
- And seller receives net amount
- And both parties can rate each other

**Edge Cases:**
- Buyer doesn't confirm receipt (delayed/forgot)
- Buyer disputes item quality before confirming
- Item damaged in transit
- Buyer confirms by mistake
- Auto-release timeout triggers

**Validation Rules:**
- Manual confirmation within 7 days; auto-release after 7 days
- Buyer must be able to upload images as proof
- Seller cannot request early release
- Platform fee deducted before release
- Payment released within 24 hours of confirmation

**Error Scenarios:**
- `ERROR_DISPUTE_PENDING`: "Cannot release payment during active dispute"
- `ERROR_BANK_TRANSFER_FAILED`: "Payment release failed. Contact support"
- `AUTO_RELEASE_NOTIFICATION`: "Payment auto-released due to no response"

---

### US-025: Platform Fee Deduction
**As a** platform  
**I want to** deduct fees from transactions  
**So that** revenue is generated

**Acceptance Criteria:**
- Given a transaction is completed
- When payment is released from escrow
- Then platform calculates fee:
  - Percentage of item price (e.g., 5%)
  - Minimum fee threshold (e.g., ₹10)
- And deducts fee from seller's payout
- When seller views transaction details
- Then seller sees:
  - Item price
  - Platform fee
  - Net amount received

**Edge Cases:**
- Very low-value items (fee > reasonable %)
- Fee calculation error
- Seller disputes fee amount
- Promotional period with reduced fees

**Validation Rules:**
- Fee structure clearly stated in terms
- Fee calculated on accepted price, not listed price
- Fee deducted only on successful transactions
- Fee breakdown shown before seller accepts offer

**Error Scenarios:**
- `ERROR_FEE_CALCULATION`: "Unable to calculate fee. Transaction on hold"

---

## Shipping & Logistics

### US-026: Seller Prepares Package and Uploads Proof
**As a** seller  
**I want to** upload package photos before pickup  
**So that** there's proof of item condition at shipping

**Acceptance Criteria:**
- Given buyer has placed an order
- When I receive order notification
- Then I am prompted to prepare item for shipping
- When I package the item
- Then I must upload proof images:
  - Item condition (before packaging)
  - Packaged item (sealed)
- When I upload images
- Then I can schedule pickup
- And buyer can view proof images

**Edge Cases:**
- Seller uploads incorrect/fake images
- Seller skips image upload and schedules pickup
- Images fail to upload due to poor network
- Seller packages wrong item

**Validation Rules:**
- Minimum 2 images required (item + package)
- Max 5 images allowed
- Images must be clear (min resolution 480x480)
- Image upload required before pickup scheduling
- Images timestamped and stored

**Error Scenarios:**
- `ERROR_IMAGE_REQUIRED`: "Please upload package images before scheduling pickup"
- `ERROR_IMAGE_UPLOAD_FAILED`: "Failed to upload images. Try again"
- `WARNING_IMAGE_QUALITY_LOW`: "Image quality low. Upload clearer photo"

**Related User Stories:**
- US-112: this screen opens from "Start Packing" and "Continue Packing" on the seller's Incoming Orders page

---

### US-027: Pickup Scheduling
**As a** seller  
**I want to** schedule item pickup with logistics partner  
**So that** the item is collected and shipped

**Acceptance Criteria:**
- Given I have uploaded proof images
- When I tap "Schedule Pickup"
- Then I select:
  - Pickup date (today or next 7 days)
  - Pickup time slot
  - Pickup address (my default address preselected; I can choose another saved address or enter a new named one)
- When I confirm
- Then pickup request is sent to logistics partner
- And I receive confirmation with pickup details
- When logistics partner is assigned
- Then I see partner name and contact
- And tracking is initiated

**Edge Cases:**
- No logistics partner available in area
- Seller selects past date/time
- Seller address is incomplete
- Logistics partner doesn't arrive in time slot
- Seller wants to reschedule pickup

**Validation Rules:**
- Pickup scheduling within 48 hours of order
- Valid pickup address required
- Seller must be available at chosen time
- Rescheduling allowed up to 2 times
- Auto-escalation if pickup not completed in 48 hours

**Error Scenarios:**
- `ERROR_NO_LOGISTICS_AVAILABLE`: "No pickup service in your area. Contact support"
- `ERROR_INVALID_TIMESLOT`: "Selected time slot unavailable"
- `ERROR_PICKUP_DELAYED`: "Pickup delayed. We'll notify you when rescheduled"

**Related User Stories:**
- US-112: "Schedule Pickup" and "View Schedule" on the seller's Incoming Orders page open this flow

---

### US-028: Item Pickup by Logistics Partner
**As a** logistics partner  
**I want to** collect item from seller  
**So that** I can ship it to buyer

**Acceptance Criteria:**
- Given I have a pickup assignment
- When I arrive at seller location
- Then I verify item against order details
- When I collect item
- Then I mark "Picked Up" in system
- And update tracking status
- And provide receipt to seller
- When pickup fails (seller unavailable)
- Then I mark "Pickup Failed"
- And reschedule is initiated

**Edge Cases:**
- Seller not available at scheduled time
- Item doesn't match description
- Item too large/heavy for logistics vehicle
- Multiple pickups from same seller
- Seller refuses to hand over item

**Validation Rules:**
- Photo proof of pickup required
- Pickup within scheduled time slot (+/- 30 min grace)
- Seller signature/confirmation captured
- Failed pickup triggers auto-reschedule

**Error Scenarios:**
- `ERROR_SELLER_UNAVAILABLE`: "Seller not available. Rescheduling pickup"
- `ERROR_ITEM_MISMATCH`: "Item doesn't match order. Escalating to support"

---

### US-029: Shipment Tracking
**As a** buyer  
**I want to** track my shipment in real-time  
**So that** I know where my item is

**Acceptance Criteria:**
- Given item has been picked up
- When I view order details
- Then I see tracking updates:
  - Picked up from seller
  - At logistics hub
  - In transit to destination
  - Out for delivery
  - Delivered
- When tracking status changes
- Then I receive push notification
- When I tap on tracking
- Then I see estimated delivery date
- And logistics partner contact info

**Edge Cases:**
- Tracking not updated for >24 hours
- Item stuck at hub
- Delivery attempted but buyer unavailable
- Wrong delivery address
- Item lost in transit

**Validation Rules:**
- Tracking updates at each checkpoint
- ETA calculated based on distance and logistics SLA
- Buyer can contact logistics partner via platform
- Stale tracking auto-escalated to support

**Error Scenarios:**
- `WARNING_TRACKING_DELAYED`: "Tracking not updated. We're investigating"
- `ERROR_DELIVERY_FAILED`: "Delivery attempt failed. Contact logistics partner"
- `ERROR_ITEM_LOST`: "Item cannot be located. Dispute process initiated"

---

### US-030: Buyer Receives Item and Uploads Proof
**As a** buyer  
**I want to** upload proof images after receiving item  
**So that** delivery is documented

**Acceptance Criteria:**
- Given item is delivered
- When I receive the package
- Then I am prompted to upload images:
  - Package condition
  - Item received (after opening)
- When I upload images
- Then I can confirm "Item Received"
- And images are stored for dispute resolution
- When I confirm receipt
- Then payment is released to seller

**Edge Cases:**
- Buyer receives damaged package
- Item doesn't match listing
- Buyer forgets to upload images
- Buyer uploads images but disputes item
- Buyer confirms by mistake

**Validation Rules:**
- Image upload optional but recommended
- Buyer can dispute before confirming receipt
- Images timestamped
- Confirmation cannot be undone
- 7-day window to confirm or dispute

**Error Scenarios:**
- `ERROR_IMAGE_UPLOAD_FAILED`: "Failed to upload images. You can still confirm"
- `WARNING_ITEM_MISMATCH`: "Item doesn't match? File a dispute before confirming"

---

### US-031: Delivery Confirmation via In-App Button
**As a** buyer  
**I want to** confirm delivery via in-app button  
**So that** seller gets paid and transaction completes

**Acceptance Criteria:**
- Given I have received and inspected the item
- When I tap "Item Received" button
- Then I see confirmation prompt: "Confirm item received in good condition?"
- When I confirm
- Then order status changes to "Completed"
- And escrow releases payment to seller
- And I can now rate seller
- And seller can rate me

**Edge Cases:**
- Buyer taps by mistake
- Buyer confirms but item is damaged (late realization)
- Self-pickup buyer forgets to confirm
- Auto-release triggers before manual confirmation

**Validation Rules:**
- One-time action (cannot undo)
- Confirmation triggers payment release within 24 hours
- Auto-confirmation after 7 days if no action
- Confirmation disables dispute option for quality issues

**Error Scenarios:**
- `WARNING_CANNOT_UNDO`: "Once confirmed, you cannot dispute quality"
- `ERROR_ALREADY_CONFIRMED`: "Item already confirmed"

---

### US-032: Failed Delivery and Rescheduling
**As a** buyer  
**I want to** reschedule delivery if I'm unavailable  
**So that** I don't miss my delivery

**Acceptance Criteria:**
- Given delivery attempt fails (buyer unavailable)
- When logistics partner marks "Delivery Failed"
- Then I receive notification with reschedule options
- When I select new delivery date/time
- Then delivery is rescheduled
- And I receive updated ETA
- When maximum reschedule attempts (3) reached
- Then item is returned to seller
- And refund is initiated

**Edge Cases:**
- Buyer repeatedly unavailable
- Buyer doesn't respond to reschedule notification
- Buyer wants to change delivery address
- Logistics partner can't deliver due to address issue

**Validation Rules:**
- Max 3 delivery attempts
- Buyer must reschedule within 24 hours of failed attempt
- After 3 failures, auto-return to seller
- Refund processed within 5 business days

**Error Scenarios:**
- `ERROR_MAX_ATTEMPTS_REACHED`: "Item returned to seller. Refund initiated"
- `ERROR_INVALID_RESCHEDULE_TIME`: "Selected time unavailable"
- `WARNING_FINAL_ATTEMPT`: "This is your last delivery attempt"

**Flutter Implementation Notes:**
- Failed delivery triggers push notification with deep link to reschedule screen
- Date/time slot picker scoped to next 7 days
- Attempt counter displayed as progress indicator (e.g., "Attempt 2 of 3")

---

## Returns

### US-033: Buyer Initiates Return
**As a** buyer  
**I want to** return an item if it doesn't meet expectations  
**So that** I can get a refund

**Acceptance Criteria:**
- Given I have received an item
- When I tap "Return Item" within 7 days of delivery
- Then I select return reason:
  - Item not as described
  - Wrong item received
  - Damaged/defective
  - Changed mind
- When I submit return request with images
- Then seller is notified
- And return request is under review
- When return is approved
- Then I receive return shipping instructions
- And I must ship item back at my own cost

**Edge Cases:**
- Return requested after 7-day window
- Item used/damaged by buyer
- Original packaging not available
- Buyer wants partial refund
- Seller disputes return claim

**Validation Rules:**
- Return window: 7 days from delivery
- Item must be unused and in original condition
- Images required showing item condition
- Return shipping cost borne by buyer
- Seller can accept or dispute return

**Error Scenarios:**
- `ERROR_RETURN_WINDOW_EXPIRED`: "Return period has ended"
- `ERROR_ITEM_USED`: "Item appears used. Return may be denied"
- `ERROR_NO_ORIGINAL_PACKAGING`: "Original packaging required for return"
- `WARNING_SHIPPING_COST`: "You'll pay return shipping costs"

---

### US-034: Return Approval and Reverse Logistics
**As a** seller  
**I want to** review return requests  
**So that** I can accept valid returns

**Acceptance Criteria:**
- Given buyer has requested return
- When I view return request
- Then I see:
  - Return reason
  - Buyer's proof images
  - Item condition claim
- When I accept return
- Then buyer is notified to ship item back
- And reverse pickup is scheduled (buyer pays)
- When I receive returned item
- Then I verify condition
- When item is acceptable
- Then I confirm return acceptance
- And refund is processed
- When item is not acceptable (damaged by buyer)
- Then I can dispute return
- And admin reviews dispute

**Edge Cases:**
- Seller rejects all returns unfairly
- Buyer ships wrong/different item back
- Item damaged during return shipping
- Seller receives item but doesn't confirm
- Seller moves/unavailable for return delivery

**Validation Rules:**
- Seller must respond to return within 48 hours
- Auto-acceptance if seller doesn't respond in 72 hours
- Item must match original condition
- Refund processed within 5 business days of acceptance
- Seller can upload images of returned item

**Error Scenarios:**
- `ERROR_RETURN_EXPIRED`: "Return acceptance window expired"
- `ERROR_ITEM_MISMATCH`: "Returned item doesn't match original"
- `DISPUTE_ESCALATED`: "Dispute escalated to admin for review"

---

### US-035: Refund Processing
**As a** buyer  
**I want** my refund processed quickly after return acceptance  
**So that** I get my money back

**Acceptance Criteria:**
- Given seller has accepted return
- When seller confirms item received in good condition
- Then platform initiates refund
- And refund amount = item price + shipping cost (if delivery)
- And platform fee is refunded
- When refund is processed
- Then I receive notification
- And amount is credited to original payment method within 5-7 business days

**Edge Cases:**
- Payment method no longer valid
- Partial refund (item partially damaged)
- Refund fails due to bank issues
- Buyer wants refund to different account

**Validation Rules:**
- Refund to original payment method only
- Full refund includes item price + shipping
- Platform fee refunded
- Refund timeline: 5-7 business days
- Buyer notified at each refund stage

**Error Scenarios:**
- `ERROR_REFUND_FAILED`: "Refund failed. Contact your bank"
- `ERROR_INVALID_PAYMENT_METHOD`: "Original payment method unavailable"
- `PARTIAL_REFUND`: "Partial refund of ₹X applied due to item condition"

---

## Ratings & Reviews

### US-036: Buyer Rates Seller
**As a** buyer  
**I want to** rate the seller after transaction  
**So that** other buyers know about seller reliability

**Acceptance Criteria:**
- Given transaction is completed (item received & confirmed)
- When I am prompted to rate seller
- Then I provide:
  - Star rating (1-5)
  - Review text (optional)
  - Rating categories: Communication, Item Accuracy, Packaging
- When I submit rating
- Then seller's overall rating is updated
- And my review is visible on seller's profile

**Edge Cases:**
- Buyer skips rating
- Buyer gives unfair/malicious review
- Buyer rates after long delay
- Buyer wants to edit/delete review

**Validation Rules:**
- Rating allowed only after transaction completion
- One rating per transaction
- Review max length: 500 characters
- Profanity filter applied
- Seller can report inappropriate reviews

**Error Scenarios:**
- `ERROR_ALREADY_RATED`: "You've already rated this seller"
- `ERROR_TRANSACTION_INCOMPLETE`: "Complete transaction before rating"
- `WARNING_INAPPROPRIATE_CONTENT`: "Review contains inappropriate language"

---

### US-037: Seller Rates Buyer
**As a** seller  
**I want to** rate the buyer after transaction  
**So that** I can identify reliable buyers

**Acceptance Criteria:**
- Given transaction is completed
- When I am prompted to rate buyer
- Then I provide:
  - Star rating (1-5)
  - Review text (optional)
  - Rating categories: Communication, Payment Promptness, Professionalism
- When I submit rating
- Then buyer's overall rating is updated
- And rating is visible to other sellers

**Edge Cases:**
- Seller rates all buyers poorly unfairly
- Seller uses ratings to harass buyers
- Buyer has no prior ratings (new user)

**Validation Rules:**
- Rating allowed only after transaction completion
- One rating per transaction
- Review max length: 500 characters
- System flags sellers who consistently rate unfairly

**Error Scenarios:**
- `ERROR_ALREADY_RATED`: "You've already rated this buyer"
- `WARNING_PATTERN_DETECTED`: "Your rating pattern flagged for review"

---

## Premium Features

### US-038: Buyer Upgrades to Premium (Photo Search Access)
**As a** buyer  
**I want to** upgrade to premium subscription  
**So that** I can use photo-based search and other premium features

**Acceptance Criteria:**
- Given I am a free user
- When I attempt to use photo search
- Then I see paywall: "Upgrade to Premium"
- When I tap "Upgrade"
- Then I see subscription plans (details TBD):
  - Features included (photo search + others)
  - Pricing (monthly/annual)
- When I select a plan and pay
- Then my account is upgraded to premium
- And I receive confirmation
- And photo search is now accessible
- And other premium features are unlocked

**Edge Cases:**
- Payment fails during upgrade
- User already has active subscription
- User wants to change plan mid-subscription
- Subscription expires during active search

**Validation Rules:**
- Payment required before feature access
- Subscription auto-renews unless canceled
- Upgrade is immediate after successful payment
- User notified before auto-renewal

**Error Scenarios:**
- `ERROR_PAYMENT_FAILED`: "Upgrade unsuccessful. Try again"
- `ERROR_ALREADY_SUBSCRIBED`: "You already have an active subscription"
- `ERROR_PLAN_UNAVAILABLE`: "Selected plan temporarily unavailable"

---

### US-039: Photo-Based Search (Premium Feature)
**As a** premium buyer  
**I want to** search using photos  
**So that** I can find items visually without typing keywords

**Acceptance Criteria:**
- Given I have premium subscription
- When I tap "Photo Search"
- Then I see two options:
  - "Take Photo" (camera)
  - "Upload from Gallery"
- When I take/upload photo
- Then system analyzes image
- And extracts visual features
- And matches against existing listings
- When results are ready (< 2 seconds)
- Then I see listings ranked by similarity score
- And similarity % shown for each result
- And I can apply filters to refine results

**Edge Cases:**
- Non-premium user tries to access (paywall shown)
- Image is unclear/blurry
- Image contains multiple items
- No matching listings found
- Image is inappropriate content
- User uploads screenshot of listing (duplicate detection)

**Validation Rules:**
- Premium subscription required (verified server-side)
- Image size: max 10MB
- Formats: JPG, PNG, HEIC
- Min resolution: 480x480
- Results ranked by confidence score (0-100%)
- Min 60% similarity to display result
- Fallback suggestions if no exact match

**Error Scenarios:**
- `ERROR_PREMIUM_REQUIRED`: "Upgrade to Premium to use photo search"
- `ERROR_SUBSCRIPTION_EXPIRED`: "Your subscription has expired. Renew to continue"
- `ERROR_IMAGE_TOO_LARGE`: "Image size must be under 10MB"
- `ERROR_IMAGE_UNCLEAR`: "Image quality too low. Try a clearer photo"
- `NO_RESULTS_FOUND`: "No similar items found. Try different photo or browse manually"
- `ERROR_INAPPROPRIATE_IMAGE`: "Image violates content policy"

---

### US-040: Visual Search Results Ranking
**As a** premium buyer  
**I want** search results ranked by similarity  
**So that** most relevant items appear first

**Acceptance Criteria:**
- Given I performed photo search
- When results are displayed
- Then items are sorted by similarity score (highest first)
- And each result shows:
  - Item image
  - Similarity % (e.g., "85% match")
  - Title, price, location
- When I scroll down
- Then similarity % decreases
- When similarity < 60%
- Then results show "Partial Match" label
- When I tap on a result
- Then I see full item details

**Edge Cases:**
- Multiple items with same similarity score
- Very low similarity across all results
- User searches for item not typically listed (rare items)

**Validation Rules:**
- Minimum 60% similarity to display
- Max 50 results per search
- Results cached for 5 minutes
- Similarity score calculated by AI/ML model

**Error Scenarios:**
- `WARNING_LOW_CONFIDENCE`: "Results have low similarity. Refine your search"
- `NO_HIGH_MATCHES`: "No close matches found. Showing similar categories"

---

### US-041: Search Refinement with Filters
**As a** premium buyer  
**I want to** apply filters after photo search  
**So that** I can narrow down results

**Acceptance Criteria:**
- Given I have photo search results
- When I tap "Filters"
- Then I can apply:
  - Price range
  - Location/distance
  - Item condition
  - Seller rating
- When I apply filters
- Then results update instantly
- And similarity ranking is preserved within filtered set

**Edge Cases:**
- Filters eliminate all results
- User applies conflicting filters
- Filter options empty (no items in range)

**Validation Rules:**
- Filters apply on top of similarity results
- Similarity ranking maintained
- Min 60% similarity threshold still enforced

**Error Scenarios:**
- `NO_RESULTS_WITH_FILTERS`: "No items match your filters. Try adjusting"

---

### US-042: Subscription Management
**As a** premium buyer  
**I want to** manage my subscription  
**So that** I can renew, cancel, or change plans

**Acceptance Criteria:**
- Given I have active subscription
- When I navigate to "Subscription Settings"
- Then I see:
  - Current plan
  - Features included
  - Next billing date
  - Payment method
- When I tap "Change Plan"
- Then I can upgrade/downgrade
- When I tap "Cancel Subscription"
- Then I see confirmation prompt
- When I confirm cancellation
- Then subscription is canceled
- And I retain access until current period ends
- And auto-renewal is disabled

**Edge Cases:**
- User cancels then immediately re-subscribes
- User downgrades mid-period
- Payment method expires before renewal
- User wants refund for unused period

**Validation Rules:**
- Cancellation takes effect at period end (no immediate cutoff)
- Pro-rated refunds not offered (per policy)
- User notified 3 days before auto-renewal
- Failed renewal triggers grace period (3 days)

**Error Scenarios:**
- `ERROR_CANCELLATION_FAILED`: "Unable to cancel. Contact support"
- `ERROR_PAYMENT_METHOD_EXPIRED`: "Update payment method to continue subscription"
- `WARNING_RENEWAL_FAILED`: "Payment failed. Update payment method within 3 days"

**Flutter Implementation Notes:**
- Subscription card in ProfileScreen with current plan details
- Cancellation flow with "Access until [date]" confirmation
- 3-day pre-renewal push notification via FCM

---

## Support & Assistance

### US-043: On-Screen AI Bot Assistance
**As a** user  
**I want** AI bot to help me navigate the platform  
**So that** I can get instant answers

**Acceptance Criteria:**
- Given I am using the app
- When I tap "Help" icon
- Then AI bot chat opens
- When I type a question
- Then bot provides relevant answer
- And suggests related help articles
- When bot cannot answer
- Then bot offers to connect me with human support

**Edge Cases:**
- Bot misunderstands question
- User asks about specific order/dispute
- Bot response is incorrect
- User spams bot
- Bot service is down

**Validation Rules:**
- Bot available 24/7
- Response time < 5 seconds
- Bot can access user's order history (with permission)
- Bot cannot handle disputes (escalates to human)

**Error Scenarios:**
- `ERROR_BOT_UNAVAILABLE`: "AI assistant temporarily unavailable. Try again"
- `ESCALATE_TO_HUMAN`: "Let me connect you with a support agent"

**Flutter Implementation Notes:**
- Floating help FAB visible on all main screens
- Chat widget implemented as a modal bottom sheet with DraggableScrollableSheet
- Calls `valuex-ai` internal API; never exposed publicly

---

### US-044: Multi-Language Support
**As a** user  
**I want to** use the app in my preferred language  
**So that** I can understand content easily

**Acceptance Criteria:**
- Given I am in app settings
- When I tap "Language"
- Then I see list of supported languages (English, Hindi, Tamil, Telugu, Bengali, Marathi, Gujarati, Kannada, Malayalam, Punjabi)
- When I select a language
- Then entire app UI changes to that language
- And listings/messages remain in original language
- And I see translation option for user-generated content

**Edge Cases:**
- Language not fully translated (missing strings)
- User switches language mid-transaction
- Language detection based on region
- RTL language support (future)

**Validation Rules:**
- Minimum 10 Indian languages supported
- UI text translated
- User-generated content (listings, messages) not auto-translated
- Translation toggle available for listings

**Error Scenarios:**
- `WARNING_PARTIAL_TRANSLATION`: "Some content not available in this language"

**Flutter Implementation Notes:**
- `flutter_localizations` + `intl` package with ARB files per language
- Language selection persisted in `SharedPreferences`
- App restarts locale without full rebuild via `Locale` state in Riverpod
- LanguageScreen already scaffolded — needs localization wiring

---

### US-045: Chat with Human Support
**As a** user  
**I want to** chat with human support  
**So that** I can get help with complex issues

**Acceptance Criteria:**
- Given I need human assistance
- When I tap "Chat with Support"
- Then I am connected to available agent
- Or placed in queue if all agents busy
- When agent is available
- Then chat starts
- And agent has access to my profile and order history
- When issue is resolved
- Then agent can close ticket
- And I receive chat transcript via email

**Edge Cases:**
- No agents available (outside business hours)
- User disconnects mid-chat
- Agent needs to escalate to specialist
- Chat session timeout

**Validation Rules:**
- Support available 9 AM - 9 PM IST
- Max wait time: 5 minutes
- Agent can view user history with consent
- Chat transcripts stored for 6 months

**Error Scenarios:**
- `WARNING_HIGH_VOLUME`: "Wait time: ~5 minutes"
- `ERROR_SUPPORT_OFFLINE`: "Support available 9 AM - 9 PM. Leave a message"

---

### US-046: Call Human Support
**As a** user  
**I want to** call support for urgent issues  
**So that** I can get immediate assistance

**Acceptance Criteria:**
- Given I need urgent help
- When I tap "Call Support"
- Then I see support phone number
- Or app initiates direct call
- When I call during business hours
- Then I am connected to agent
- When I call outside business hours
- Then I hear message with alternative options

**Edge Cases:**
- Call drops mid-conversation
- Agent cannot resolve issue over phone
- User calls repeatedly for same issue
- Language barrier

**Validation Rules:**
- Phone support: 9 AM - 9 PM IST
- Calls routed based on user's language preference
- Call recording with user consent
- Callback option if wait time > 10 minutes

**Error Scenarios:**
- `OUTSIDE_HOURS`: "Support available 9 AM - 9 PM. Call back or leave message"
- `HIGH_CALL_VOLUME`: "Request callback or try chat support"

---

### US-047: Raise Dispute/Grievance
**As a** user  
**I want to** raise a dispute  
**So that** platform can help resolve issues

**Acceptance Criteria:**
- Given I have an issue with a transaction
- When I tap "Raise Dispute"
- Then I select dispute type:
  - Item not as described
  - Payment not released
  - Item not received
  - Seller/buyer harassment
  - Other
- When I provide details and evidence (chat logs, images)
- Then dispute is submitted
- And admin is notified
- And I receive dispute ID
- When admin reviews
- Then I receive updates
- And resolution is communicated

**Edge Cases:**
- User raises frivolous disputes repeatedly
- Dispute raised after transaction closed
- Insufficient evidence provided
- Both parties claim opposite things

**Validation Rules:**
- Disputes must be raised within 7 days of issue
- Evidence required (images, chat logs)
- Both parties notified of dispute
- Admin reviews within 48 hours
- Resolution binding on both parties

**Error Scenarios:**
- `ERROR_DISPUTE_WINDOW_CLOSED`: "Dispute window expired"
- `ERROR_INSUFFICIENT_EVIDENCE`: "Please provide more details"
- `DISPUTE_UNDER_REVIEW`: "Dispute submitted. Expect response in 48 hours"

**Flutter Implementation Notes:**
- DisputeScreen already scaffolded — needs dispute type picker, evidence upload (images + text), and submission API call
- Evidence images use same `image_picker` + upload flow as listing creation
- Dispute ID displayed in confirmation screen with copy-to-clipboard

---

## Trust & Safety

### US-048: Fraud Listing Detection
**As a** platform  
**I want to** detect and block fraudulent listings  
**So that** buyers are protected

**Acceptance Criteria:**
- Given a seller creates a listing
- When system analyzes listing content
- Then AI flags suspicious patterns:
  - Duplicate images (used in other listings)
  - Restricted keywords
  - Unrealistic pricing
  - Suspicious seller behavior (new account, multiple listings)
- When listing is flagged
- Then listing is held for manual review
- And seller is notified of review
- When admin approves
- Then listing is published
- When admin rejects
- Then listing is blocked
- And seller is warned

**Edge Cases:**
- False positive (legitimate listing flagged)
- Seller re-uploads same listing with minor changes
- Coordinated fraud (multiple accounts)

**Validation Rules:**
- AI fraud score threshold: >70% auto-flag
- Manual review within 24 hours
- Image watermarking to prevent reuse
- Repeated violations lead to account suspension

**Error Scenarios:**
- `LISTING_UNDER_REVIEW`: "Your listing is under review. You'll be notified within 24 hours"
- `LISTING_REJECTED`: "Listing violates platform policies. See details"

---

### US-049: Image Proof Authenticity Validation
**As a** platform  
**I want to** verify image authenticity  
**So that** sellers don't reuse images across listings

**Acceptance Criteria:**
- Given a seller uploads images for a listing
- When system analyzes images
- Then image hashing/fingerprinting is performed
- When image matches existing listing
- Then system flags duplicate
- And seller is warned
- When seller uploads watermarked images from other platforms
- Then system detects and rejects

**Edge Cases:**
- Seller slightly edits image (crop, filter) to bypass detection
- Seller legitimately re-lists same item
- Image similarity (same item, different angle)

**Validation Rules:**
- Perceptual hashing used (detects edits)
- Duplicate image across different sellers = fraud
- Same seller, same image = re-listing allowed
- Metadata analysis (EXIF data check)

**Error Scenarios:**
- `ERROR_DUPLICATE_IMAGE`: "This image is used in another listing. Upload original photos"
- `WARNING_WATERMARK_DETECTED`: "Remove watermarks from other platforms"

---

### US-050: Daily Listing Limit
**As a** platform  
**I want to** limit daily listings per user  
**So that** spam and fraud are reduced

**Acceptance Criteria:**
- Given a seller is creating listings
- When seller reaches daily limit (e.g., 10 listings/day for new users)
- Then system prevents further listing creation
- And shows error message
- When seller is verified and has good reputation
- Then limit is increased (e.g., 50 listings/day)

**Edge Cases:**
- Seller creates multiple accounts to bypass limit
- Seller needs to list more items urgently
- Limit resets at midnight (timezone handling)

**Validation Rules:**
- New users: 10 listings/day
- Verified users: 50 listings/day
- Limit resets daily at midnight IST
- Limit increase based on reputation score

**Error Scenarios:**
- `ERROR_DAILY_LIMIT_REACHED`: "Daily listing limit reached. Try tomorrow"
- `REQUEST_LIMIT_INCREASE`: "Need higher limit? Contact support"

---

### US-051: Progressive Penalties for Violations
**As a** platform  
**I want to** apply progressive penalties  
**So that** repeat offenders are deterred

**Acceptance Criteria:**
- Given a user violates platform policies
- When first violation occurs
- Then user receives warning
- When second violation occurs
- Then user receives temporary suspension (7 days)
- When third violation occurs
- Then user receives permanent ban
- And Aadhaar is blacklisted

**Violation Types:**
- Fraudulent listings
- Harassment
- Payment disputes (seller cancellations)
- Inappropriate content
- Spam

**Edge Cases:**
- User appeals penalty
- Different violation types (cumulative or separate?)
- User violates during suspension

**Validation Rules:**
- Violation history tracked per Aadhaar
- Appeals reviewed within 48 hours
- Permanent ban includes Aadhaar blacklist
- User notified at each penalty level

**Error Scenarios:**
- `WARNING_ISSUED`: "Policy violation detected. Further violations may result in suspension"
- `ACCOUNT_SUSPENDED`: "Your account is suspended for 7 days due to repeated violations"
- `ACCOUNT_BANNED`: "Your account has been permanently banned"

---

### US-052: Fraud Score and Velocity Checks
**As a** platform  
**I want to** monitor user activity patterns  
**So that** fraud is detected early

**Acceptance Criteria:**
- Given a user is active on platform
- When system tracks activity:
  - Listing velocity (listings/hour)
  - Message velocity (messages/hour)
  - Call velocity (calls/hour)
  - Login patterns (multiple devices)
- And calculates fraud score
- When fraud score exceeds threshold
- Then account is flagged for review
- And high-risk actions are blocked (listing, payment)
- And admin investigates

**Edge Cases:**
- Legitimate power user flagged incorrectly
- Coordinated fraud across multiple accounts
- Sudden spike in activity (e.g., bulk listing of items)

**Validation Rules:**
- Fraud score: 0-100 (>80 = high risk)
- Velocity thresholds:
  - Listings: max 5/hour
  - Messages: max 50/hour
  - Calls: max 20/hour
- Account frozen until admin review

**Error Scenarios:**
- `ACCOUNT_UNDER_REVIEW`: "Your account is under security review"
- `ACTION_BLOCKED`: "This action is temporarily blocked. Contact support"

---

## Admin & Moderation

### US-053: Admin Dashboard - User Management
**As an** admin  
**I want to** manage user accounts  
**So that** I can suspend/ban violators

**Acceptance Criteria:**
- Given I am logged in as admin
- When I search for a user
- Then I see user profile with:
  - Account details
  - Listing history
  - Transaction history
  - Violation history
  - Fraud score
- When I select an action (warn/suspend/ban)
- Then action is applied
- And user is notified
- And action is logged in audit trail

**Edge Cases:**
- Admin accidentally bans legitimate user
- User is mid-transaction during suspension
- Banned user tries to create new account

**Validation Rules:**
- Only admin/moderator roles can access
- All actions require reason
- Suspended users cannot transact
- Banned users cannot login
- Audit log immutable

**Error Scenarios:**
- `ERROR_UNAUTHORIZED`: "You don't have permission for this action"
- `ERROR_USER_NOT_FOUND`: "User account not found"

---

### US-054: Admin Dashboard - Listing Moderation
**As an** admin  
**I want to** moderate flagged listings  
**So that** platform remains safe

**Acceptance Criteria:**
- Given flagged listings exist
- When I view moderation queue
- Then I see listings with:
  - Flag reason (AI detection, user report)
  - Listing details
  - Seller info
- When I review listing
- Then I can approve or reject
- When I reject
- Then seller is notified with reason
- And violation is recorded

**Edge Cases:**
- Listing removed by seller before moderation
- Multiple flags on same listing
- Borderline listing (hard to decide)

**Validation Rules:**
- Moderation queue prioritized by risk score
- SLA: review within 24 hours
- Reject reason mandatory
- Appeals allowed within 7 days

**Error Scenarios:**
- `ERROR_LISTING_ALREADY_REMOVED`: "Listing no longer exists"

---

### US-055: Admin Dashboard - Dispute Resolution
**As an** admin  
**I want to** resolve disputes between buyers and sellers  
**So that** fair outcomes are achieved

**Acceptance Criteria:**
- Given disputes are raised
- When I view dispute queue
- Then I see:
  - Dispute type
  - Both parties' claims
  - Evidence (images, chat logs, call logs)
  - Order details
- When I review evidence
- Then I make decision:
  - Full refund to buyer
  - Partial refund
  - Release payment to seller
  - No action
- When I submit decision
- Then both parties are notified
- And action is executed (refund/payment release)
- And dispute is closed

**Edge Cases:**
- Insufficient evidence from either party
- Both parties provide conflicting evidence
- Dispute escalated to senior admin
- Decision appealed by one party

**Validation Rules:**
- SLA: resolve within 48 hours
- Decision requires detailed reasoning
- One appeal allowed per dispute
- Final decision is binding

**Error Scenarios:**
- `ERROR_INSUFFICIENT_EVIDENCE`: "Cannot resolve. Requesting more information"
- `DISPUTE_ESCALATED`: "Complex case. Escalated to senior team"

---

### US-056: Admin Dashboard - Transaction Monitoring
**As an** admin  
**I want to** monitor transactions in real-time  
**So that** anomalies are detected quickly

**Acceptance Criteria:**
- Given transactions are occurring
- When I view transaction dashboard
- Then I see metrics:
  - Total transactions today/week/month
  - GMV
  - Failed payments
  - Disputed transactions
  - Average order value
  - Top sellers/buyers
- When I filter by parameters
- Then I see detailed transaction list
- When I click on a transaction
- Then I see complete transaction flow

**Edge Cases:**
- Dashboard performance with high volume
- Real-time data lag
- Exporting large datasets

**Validation Rules:**
- Data refreshes every 5 minutes
- Historical data: last 12 months
- Export to CSV available
- Role-based access (only admins/analysts)

**Error Scenarios:**
- `ERROR_DATA_UNAVAILABLE`: "Unable to load dashboard data. Refresh"

---

### US-057: Admin Dashboard - Content Moderation (Chat/Video)
**As an** admin  
**I want to** review flagged chat/video content  
**So that** harassment and abuse are addressed

**Acceptance Criteria:**
- Given chat/video is flagged (by AI or user report)
- When I view moderation queue
- Then I see:
  - Flagged content (chat excerpt or video)
  - Participants
  - Flag reason
- When I review content
- Then I can:
  - Take no action
  - Warn user
  - Suspend user
  - Ban user
- And both parties are notified of outcome

**Edge Cases:**
- Video too long to review fully
- Chat context needed (full conversation)
- False positive flag
- Multiple reports on same user

**Validation Rules:**
- SLA: review within 24 hours
- Severe violations (threats, explicit content) = immediate ban
- Video reviews require timestamp of violation
- User identity protected during review

**Error Scenarios:**
- `ERROR_CONTENT_UNAVAILABLE`: "Flagged content no longer available"
- `IMMEDIATE_ACTION_TAKEN`: "Severe violation. User banned pending review"

---

### US-058: Order Cancellation by Buyer (Before Pickup)
**As a** buyer  
**I want to** cancel my order before the item is picked up  
**So that** I can get a refund if I change my mind

**Acceptance Criteria:**
- Given I have placed an order with payment in escrow
- When order status is "Awaiting Pickup"
- Then I see "Cancel Order" option
- When I tap "Cancel Order"
- Then I see confirmation prompt with refund details
- When I confirm cancellation
- Then order is canceled
- And full refund is initiated to my payment method
- And seller is notified of cancellation
- And listing is made available again
- When order status is "Picked Up" or later
- Then "Cancel Order" option is disabled

**Edge Cases:**
- Buyer cancels just as logistics partner is picking up
- Multiple cancellation attempts (duplicate requests)
- Buyer cancels one of several items bought together: only that item's order is cancelled and refunded, because each item is its own order
- Refund fails due to payment method issues
- Seller already shipped item before cancellation processed

**Validation Rules:**
- Cancellation allowed only before pickup
- Full refund = item price + shipping cost (if paid)
- No penalty for buyer cancellation
- Refund processed within 24 hours
- Seller notified immediately
- Order cannot be reinstated after cancellation
- Listing automatically re-published

**Error Scenarios:**
- `ERROR_CANCELLATION_NOT_ALLOWED`: "Order already picked up. Cannot cancel"
- `ERROR_REFUND_FAILED`: "Cancellation successful but refund failed. Contact support"
- `ERROR_ALREADY_CANCELLED`: "This order is already cancelled"
- `ERROR_PICKUP_IN_PROGRESS`: "Pickup in progress. Contact logistics partner"

**Flutter Implementation Notes:**
- "Cancel Order" button visible only when order state is `AWAITING_PICKUP`
- Confirmation bottom sheet shows itemised refund breakdown
- Optimistic UI update with rollback on API error

---

### US-059: Order Cancellation by Seller (With Penalty)
**As a** seller  
**I want to** cancel an order if the item is no longer available  
**So that** I can handle unexpected situations, accepting the penalty

**Acceptance Criteria:**
- Given I have an active order
- When order status is "Awaiting Pickup"
- Then I see "Cancel Order" option with penalty warning
- When I tap "Cancel Order"
- Then I see confirmation: "Cancelling will result in penalty of ₹X. Proceed?"
- When I confirm cancellation
- Then order is canceled
- And buyer gets full refund
- And penalty is deducted from my seller wallet (or future earnings)
- And violation is recorded in my account
- And buyer is notified with apology message
- When I have 3+ cancellations in 30 days
- Then my account is temporarily suspended for review

**Edge Cases:**
- Seller cancels multiple orders simultaneously
- Seller has insufficient balance for penalty
- Seller cancels after logistics pickup scheduled
- Buyer already on way for self-pickup
- Seller tries to cancel due to price dissatisfaction

**Validation Rules:**
- Cancellation allowed before pickup only
- Penalty: 10% of order value or ₹100 (whichever is higher)
- Violation recorded per cancellation
- 3 cancellations in 30 days = account review
- 5 cancellations in 30 days = permanent suspension
- Buyer receives full refund within 24 hours
- Seller cannot re-list same item for 48 hours (cooling period)

**Error Scenarios:**
- `ERROR_CANCELLATION_NOT_ALLOWED`: "Order already picked up. Cannot cancel"
- `ERROR_INSUFFICIENT_BALANCE`: "Insufficient balance for penalty. Contact support"
- `WARNING_PENALTY_APPLIED`: "Order cancelled. Penalty of ₹X deducted"
- `WARNING_ACCOUNT_AT_RISK`: "Multiple cancellations detected. Next violation may result in suspension"
- `ACCOUNT_SUSPENDED`: "Too many cancellations. Account suspended for review"

**Flutter Implementation Notes:**
- Penalty amount calculated and shown in confirmation dialog before seller confirms
- Cancellation count badge visible in seller dashboard header
- Cooling-period timer shown on the affected listing in MyListingsScreen
- "Reject" on a New order in Incoming Orders (US-112) opens this same cancellation flow, with the same penalty warning and confirmation

---

## Enhancement Stories (Backlog)

### US-060: Logistics Partner - View Assigned Tasks
**As a** logistics partner  
**I want to** view all my assigned pickups and deliveries  
**So that** I can plan my route efficiently

**Acceptance Criteria:**
- Given I am logged in as logistics partner
- When I view my dashboard
- Then I see:
  - Pending pickups (today)
  - Scheduled deliveries (today)
  - Completed tasks
- When I tap on a task
- Then I see details: address, contact, time slot, item details
- When I update status
- Then buyers/sellers are notified

**Edge Cases:**
- High volume of tasks
- Task address is incorrect
- Multiple tasks at same location

**Validation Rules:**
- Tasks sorted by time slot
- Map integration for route planning
- Status updates required at each checkpoint

**Error Scenarios:**
- `ERROR_NO_TASKS`: "No tasks assigned for today"
- `ERROR_ADDRESS_INVALID`: "Unable to locate address. Contact support"

---

### US-061: Screen Reader Compatibility
**As a** visually impaired user  
**I want** the app to be screen reader compatible  
**So that** I can use the platform independently

**Acceptance Criteria:**
- Given I have screen reader enabled
- When I navigate the app
- Then all UI elements are announced correctly
- And all buttons/actions are accessible
- And images have descriptive alt text
- When I perform actions
- Then confirmations are announced

**Edge Cases:**
- Complex forms with multiple fields
- Image galleries
- Real-time chat notifications

**Validation Rules:**
- WCAG 2.1 AA compliance
- All interactive elements keyboard navigable
- Focus indicators visible
- Alt text for all images

**Error Scenarios:**
- N/A (accessibility is always-on)

---

### US-062: Data Export Request
**As a** user  
**I want to** export all my data  
**So that** I have a copy of my information

**Acceptance Criteria:**
- Given I am logged in
- When I go to Privacy Settings
- Then I see "Download My Data"
- When I request data export
- Then system generates a downloadable file with:
  - Profile information
  - Listing history
  - Transaction history
  - Messages
  - Ratings/reviews
- And I receive email when ready (within 48 hours)

**Edge Cases:**
- Large data volumes
- Multiple export requests
- Deleted/archived data

**Validation Rules:**
- Export format: JSON or CSV
- Data includes last 2 years
- Email notification with secure download link
- Link expires in 7 days

**Error Scenarios:**
- `ERROR_EXPORT_FAILED`: "Unable to generate export. Try again"
- `ERROR_TOO_MANY_REQUESTS`: "Export already in progress"

---

### US-063: Data Deletion Request
**As a** user  
**I want to** delete my account and all data  
**So that** my information is removed from the platform

**Acceptance Criteria:**
- Given I have no active orders
- When I request account deletion
- Then I see warning: "This action is permanent"
- When I confirm
- Then account is scheduled for deletion
- And I receive confirmation email
- And all data is deleted within 30 days
- And I cannot log in after deletion

**Edge Cases:**
- User has active orders
- User has pending disputes
- User has outstanding payments

**Validation Rules:**
- Cannot delete with active orders
- 30-day grace period (can cancel deletion)
- Aadhaar mapping removed
- Legal retention: transaction records kept for 7 years (anonymized)

**Error Scenarios:**
- `ERROR_ACTIVE_ORDERS`: "Cannot delete account with active orders"
- `ERROR_PENDING_DISPUTES`: "Resolve disputes before deleting account"

---

### US-064: Upgrade Listing Plan
**As a** seller  
**I want to** upgrade my listing from Basic to Boosted/Priority  
**So that** I can increase visibility mid-flight

**Acceptance Criteria:**
- Given I have a published listing with Basic plan
- When I view listing details
- Then I see "Upgrade Plan" option
- When I select Boosted or Priority
- Then I see price difference
- When I pay
- Then listing is upgraded immediately
- And new plan features are activated

**Edge Cases:**
- Listing near expiry
- Downgrade not allowed
- Multiple upgrades

**Validation Rules:**
- Only upward upgrades allowed
- Price difference = new plan - remaining value of old plan
- Plan duration extends from upgrade date

**Error Scenarios:**
- `ERROR_PAYMENT_FAILED`: "Upgrade failed. Try again"
- `ERROR_DOWNGRADE_NOT_ALLOWED`: "Downgrade not supported. Create new listing"

**Flutter Implementation Notes:**
- "Upgrade Plan" CTA shown in MyListingsScreen item detail
- Price difference calculated and displayed before payment confirmation
- Reuses ListingPlanScreen with current plan pre-selected and lower options disabled

---

### US-065: Bulk Listing Upload
**As a** power seller  
**I want to** upload multiple listings via CSV  
**So that** I can list many items quickly

**Acceptance Criteria:**
- Given I am a verified seller
- When I select "Bulk Upload"
- Then I download CSV template
- When I fill template with item details
- And upload CSV
- Then system validates all rows
- When validation passes
- Then all listings are created as drafts
- And I can review and publish individually

**Edge Cases:**
- CSV format errors
- Duplicate entries
- Missing required fields
- Too many rows (limit 100 per upload)

**Validation Rules:**
- Verified sellers only
- Max 100 listings per CSV
- All validation rules apply per listing
- Bulk upload counts toward daily limit

**Error Scenarios:**
- `ERROR_INVALID_FORMAT`: "CSV format incorrect. Download template"
- `ERROR_VALIDATION_FAILED`: "Row X: [error details]"
- `ERROR_NOT_VERIFIED`: "Bulk upload requires verified account"

---

### US-066: Saved Searches and Alerts
**As a** buyer  
**I want to** save my search criteria and get alerts  
**So that** I'm notified when matching items are listed

**Acceptance Criteria:**
- Given I performed a search
- When I tap "Save Search"
- Then search criteria is saved
- When a new listing matches my criteria
- Then I receive push notification
- When I view "Saved Searches"
- Then I see all my saved searches
- And I can enable/disable alerts per search

**Edge Cases:**
- Too many saved searches (limit 10)
- High-frequency alerts (many matches)
- Search criteria becomes invalid (category deleted)

**Validation Rules:**
- Max 10 saved searches per user
- Alerts sent max once per day (digest)
- User can delete saved searches anytime

**Error Scenarios:**
- `ERROR_MAX_SAVED_SEARCHES`: "Maximum 10 saved searches allowed"
- `ERROR_INVALID_CRITERIA`: "Search criteria no longer valid"

**Flutter Implementation Notes:**
- Distinct from SavedItemsScreen (bookmarked listings); this is SavedSearchesScreen
- Save Search button in HomeScreen/search results header
- Toggle switch per saved search for alert on/off
- FCM topic subscription per saved search criteria

---

### US-067: Seller Performance Analytics
**As a** seller  
**I want to** view analytics on my listings  
**So that** I can optimize my selling strategy

**Acceptance Criteria:**
- Given I have published listings
- When I view "My Analytics"
- Then I see metrics:
  - Total views per listing
  - Inquiries (chat/call count)
  - Conversion rate
  - Average negotiation rounds
  - Average time to sell
- When I select a listing
- Then I see detailed analytics for that item
- When I apply date filters
- Then data updates accordingly

**Edge Cases:**
- New seller with no data
- Listing with no views
- Very old listings

**Validation Rules:**
- Data available for last 90 days
- Real-time view counts
- Analytics retained even after listing deleted

**Error Scenarios:**
- `NO_DATA_AVAILABLE`: "No analytics data yet"
- `ERROR_LOADING_ANALYTICS`: "Unable to load analytics. Refresh"

**Flutter Implementation Notes:**
- Analytics tab inside ProfileScreen or standalone SellerAnalyticsScreen
- Charts via `fl_chart` package (bar chart for views, line for conversion trend)
- Date range picker with 7d / 30d / 90d presets

---

## New Features - PRD v1.3 Alignment

### US-068: Direct Buy Now Flow
**As a** buyer  
**I want to** purchase an item immediately at listed price  
**So that** I can skip negotiation for items I want to buy quickly

**Acceptance Criteria:**
- Given I am viewing a listing with "Buy Now" option enabled
- When I tap "Buy Now"
- Then I skip negotiation step
- And item is added to cart at listed price
- And I proceed directly to checkout
- When seller has disabled "Buy Now"
- Then only "Make Offer" button is available
- And buyer must negotiate

**Edge Cases:**
- Item sold to another buyer while current buyer is checking out
- Seller changes price during checkout
- Buyer wants to negotiate after using Buy Now
- Multiple buyers click Buy Now simultaneously

**Validation Rules:**
- Buy Now price is the listed price (no negotiation)
- Seller can enable/disable Buy Now per listing
- Buy Now items follow same escrow flow
- Item reserved for 15 minutes during checkout

**Error Scenarios:**
- `ERROR_ITEM_SOLD`: "This item is no longer available"
- `ERROR_PRICE_CHANGED`: "Price has changed. Please review"
- `ERROR_BUY_NOW_DISABLED`: "Seller requires price negotiation for this item"

**Flutter Implementation Notes:**
- ListingDetailScreen shows "Buy Now" and "Make Offer" as two distinct CTAs
- 15-minute reservation timer shown in checkout header with countdown
- "Buy Now" toggle in seller's listing creation/edit settings

---

### US-069: Buyer Initiates Contact from Listing
**As a** buyer  
**I want to** easily contact seller from listing page  
**So that** I can inquire about item details

**Acceptance Criteria:**
- Given I am viewing a listing
- When I see communication options (Chat, Call, Video Call)
- Then I can tap any option to initiate contact
- When I tap "Chat"
- Then chat window opens with listing context pre-loaded
- When I tap "Call"
- Then masked voice call initiates
- When I tap "Video Call"
- Then video call request is sent to seller
- And I see "Waiting for seller to accept" message

**Edge Cases:**
- Seller is offline/unavailable
- Buyer hasn't verified account
- Seller has blocked buyer
- Multiple contact attempts in short time (spam prevention)

**Validation Rules:**
- Contact options visible only to logged-in users
- Listing context (title, price) auto-included in first chat message
- Call/video call requires both parties to be online
- System logs all contact attempts

**Error Scenarios:**
- `ERROR_LOGIN_REQUIRED`: "Please login to contact seller"
- `ERROR_SELLER_UNAVAILABLE`: "Seller is currently unavailable"
- `ERROR_BLOCKED`: "You cannot contact this seller"
- `WARNING_RATE_LIMIT`: "Too many contact attempts. Try again later"

---

### US-070: View Order History
**As a** user  
**I want to** view all my past and active orders  
**So that** I can track purchases and reference previous transactions

**Acceptance Criteria:**
- Given I am logged in
- When I navigate to "My Orders"
- Then I see list of all orders with:
  - Order ID, date
  - Item image and title
  - Seller/buyer name
  - Order status
  - Total amount
- When I filter by status (Active/Completed/Cancelled/Returned)
- Then only matching orders are displayed
- When I tap on an order
- Then I see complete order details page
- And I can access order actions (track, contact, return, dispute)

**Edge Cases:**
- User has hundreds of orders (pagination)
- Order deleted by admin
- Seller account suspended after order
- Items bought together in one checkout appear as separate orders, each with its own order number

**Validation Rules:**
- Orders sorted by date (newest first)
- Pagination: 20 orders per page
- Order history retained for 2 years
- Deleted orders marked but not removed from history

**Error Scenarios:**
- `ERROR_LOADING_ORDERS`: "Unable to load orders. Refresh"
- `NO_ORDERS_FOUND`: "You haven't placed any orders yet"

---

### US-071: View Payment and Transaction History
**As a** user  
**I want to** view my payment and transaction history  
**So that** I can track my spending and earnings

**Acceptance Criteria:**
- Given I am logged in
- When I navigate to "Transactions" or "Wallet"
- Then I see list of all financial transactions:
  - Date and time
  - Transaction type (Payment/Refund/Payout/Fee)
  - Amount (debit/credit)
  - Status (Success/Pending/Failed)
  - Order reference
  - Balance after transaction
- When I filter by date range or type
- Then results update accordingly
- When I tap on a transaction
- Then I see detailed breakdown including fees, taxes
- When I tap "Download Statement"
- Then PDF/CSV is generated

**Edge Cases:**
- Failed payment attempts
- Partial refunds
- Platform fee deductions
- Seller payout pending
- Very old transactions (2+ years)

**Validation Rules:**
- Transaction history retained for 7 years (compliance)
- All amounts in INR with 2 decimal places
- Running balance shown
- Export limited to last 2 years

**Error Scenarios:**
- `ERROR_LOADING_TRANSACTIONS`: "Unable to load transaction history"
- `ERROR_EXPORT_FAILED`: "Failed to generate statement. Try again"

---

### US-072: Seller Payout Bank/UPI Management
**As a** seller  
**I want to** manage my payout bank account or UPI details  
**So that** I receive payments from completed sales

**Acceptance Criteria:**
- Given I am logged in as seller
- When I navigate to "Payout Settings"
- Then I see options to add:
  - Bank account (Account number, IFSC, name)
  - UPI ID
- When I add bank account
- Then system validates account details
- And sends test deposit for verification
- When I verify test amount
- Then account is activated for payouts
- When I add UPI ID
- Then system validates UPI format
- And marks as primary payout method
- When I have multiple payout methods
- Then I can set one as primary
- And change primary method anytime

**Edge Cases:**
- Invalid bank account details
- UPI ID not found
- Seller tries to change payout method with pending payout
- Bank account belongs to different person than Aadhaar name

**Validation Rules:**
- Bank account name must match Aadhaar name
- IFSC code must be valid Indian bank
- UPI ID format: username@bankname
- Minimum one payout method required before first sale
- Payout method changes take effect after 24 hours

**Error Scenarios:**
- `ERROR_INVALID_ACCOUNT`: "Bank account details are invalid"
- `ERROR_NAME_MISMATCH`: "Account name must match your registered name"
- `ERROR_INVALID_UPI`: "UPI ID not found or invalid"
- `ERROR_PENDING_PAYOUT`: "Cannot change payout method with pending payouts"

---

### US-073: Save and Bookmark Listings
**As a** buyer  
**I want to** save listings I'm interested in  
**So that** I can review them later

**Acceptance Criteria:**
- Given I am viewing a listing
- When I tap "Save" or heart icon
- Then listing is added to my saved items
- And icon changes to "Saved" state
- When I navigate to "Saved Items"
- Then I see all bookmarked listings
- And I can view, remove, or purchase saved items
- When a saved listing is sold or removed
- Then I receive notification
- And item is marked as "No longer available" in saved list

**Edge Cases:**
- User saves hundreds of items
- Saved item price changes
- Saved item seller suspends account
- Saved item expires

**Validation Rules:**
- Maximum 200 saved items per user
- Saved items retained for 90 days
- Notifications for price drops on saved items (future enhancement)
- Can save from search results or listing page

**Error Scenarios:**
- `ERROR_MAX_SAVED`: "Maximum 200 saved items reached. Remove some to add more"
- `ERROR_ITEM_UNAVAILABLE`: "This listing is no longer available"

---

### US-074: Track Support Ticket Status
**As a** user  
**I want to** track status of my support tickets  
**So that** I know when my issues are resolved

**Acceptance Criteria:**
- Given I have raised support tickets
- When I navigate to "Support" or "Help"
- Then I see list of all my tickets with:
  - Ticket ID
  - Subject
  - Status (Open/In Progress/Waiting for You/Resolved/Closed)
  - Created date
  - Last updated date
- When I tap on a ticket
- Then I see complete conversation history
- And I can add new messages
- When ticket status changes
- Then I receive notification
- When agent responds
- Then I receive notification and can reply

**Edge Cases:**
- Ticket auto-closed after 7 days of inactivity
- User reopens closed ticket
- Multiple tickets for same issue
- Ticket escalated to senior support

**Validation Rules:**
- Ticket conversation history retained for 1 year
- User can reopen ticket within 30 days of closure
- Tickets auto-close after 7 days with no user response
- Priority tickets (payment, dispute) marked separately

**Error Scenarios:**
- `ERROR_LOADING_TICKETS`: "Unable to load support tickets"
- `ERROR_TICKET_CLOSED`: "This ticket is closed. Create new ticket for new issues"

---

### US-075: Retry Failed Payments
**As a** buyer  
**I want to** retry failed payments  
**So that** I can complete my purchase without creating new order

**Acceptance Criteria:**
- Given my payment failed during checkout
- When I see payment failed message
- Then I see "Retry Payment" button
- When I tap "Retry Payment"
- Then payment gateway reopens
- And I can try different payment method
- When payment succeeds on retry
- Then order is created normally
- And cart is cleared
- When I abandon retry
- Then order remains in "Payment Pending" state for 15 minutes
- And auto-cancels after timeout

**Edge Cases:**
- Multiple retry attempts fail
- Payment method temporarily blocked
- Item sold during retry window
- Network interruption during retry

**Validation Rules:**
- Maximum 3 retry attempts per order
- 15-minute window for retry after initial failure
- Retry must use same order details (price locked)
- After timeout, user must create new order

**Error Scenarios:**
- `ERROR_PAYMENT_FAILED`: "Payment failed. Please try different method"
- `ERROR_MAX_RETRIES`: "Maximum retry attempts reached. Please try again later"
- `ERROR_ITEM_UNAVAILABLE`: "Item no longer available. Order cancelled"
- `ERROR_RETRY_EXPIRED`: "Retry window expired. Please create new order"

**Flutter Implementation Notes:**
- Retry state tracked in PaymentNotifier (Riverpod)
- 15-minute countdown timer displayed on retry screen
- Attempt counter shown: "Attempt 2 of 3"
- On max retries or timeout, redirect to HomeScreen with toast

---

### US-076: Seller Negotiation Management
**As a** seller  
**I want to** manage buyer offers efficiently  
**So that** I can accept, reject, or counter offers quickly

**Acceptance Criteria:**
- Given I have received buyer offers
- When I navigate to "Offers" or receive notification
- Then I see list of pending offers with:
  - Buyer name and rating
  - Item details
  - Offered price vs listed price
  - Offer timestamp
- When I tap on an offer
- Then I see three options: Accept, Reject, Counter
- When I tap "Accept"
- Then buyer is notified immediately
- And price is locked for 24 hours
- And buyer can proceed to checkout
- When I tap "Reject"
- Then buyer is notified
- And negotiation ends
- When I tap "Counter"
- Then I enter my counter offer
- And buyer receives notification to review

**Edge Cases:**
- Multiple buyers making offers simultaneously
- Seller accepts one offer while others pending
- Offer expires while seller is reviewing
- Buyer cancels offer before seller responds

**Validation Rules:**
- Offers expire after 48 hours if no seller response
- Accepting one offer auto-rejects others for same item
- Counter offer must be between buyer offer and listed price
- Maximum 5 back-and-forth per buyer-seller pair
- Seller must respond within 48 hours or offer auto-expires

**Error Scenarios:**
- `ERROR_OFFER_EXPIRED`: "This offer has expired"
- `ERROR_ALREADY_ACCEPTED`: "You've already accepted another offer for this item"
- `ERROR_INVALID_COUNTER`: "Counter offer must be between ₹X and ₹Y"
- `WARNING_MAX_NEGOTIATIONS`: "Maximum negotiation rounds reached"

**Flutter Implementation Notes:**
- Offers tab in MessagesScreen or standalone OffersScreen accessible from ProfileScreen
- Offer cards sorted by expiry (soonest first) with countdown chips
- Counter offer uses a bottom sheet with price input slider between buyer offer and listed price

---

### US-077: Critical Event Notifications
**As a** user  
**I want to** receive notifications for critical events  
**So that** I stay informed about important account and transaction activities

**Acceptance Criteria:**
- Given I am a registered user
- When critical events occur, I receive notifications via:
  - In-app notifications
  - Push notifications
  - Email
  - SMS (for high-priority events)
- Critical events include:
  - Account created
  - Password changed
  - New login from unknown device
  - Item added/removed from cart
  - Order placed
  - Payment success/failure
  - Order status changes
  - Messages received
  - Offers received/accepted
  - Dispute raised/resolved
  - Account suspended/banned
- When I tap notification
- Then I am taken to relevant page in app
- When I navigate to "Notifications"
- Then I see history of all notifications

**Edge Cases:**
- Multiple notifications in short time (grouped)
- User has notifications disabled
- Network unavailable (queued for later)
- Email bounces or SMS fails

**Validation Rules:**
- High-priority events: SMS + Push + Email + In-app
- Medium-priority: Push + In-app
- Low-priority: In-app only
- Notification history retained for 90 days
- User can configure notification preferences
- Unread count shown on notifications icon

**Error Scenarios:**
- `ERROR_NOTIFICATION_FAILED`: Logged but user not aware
- Retry mechanism for failed notifications

---

### US-078: Listing Plan Features and Pricing
**As a** seller  
**I want to** understand differences between listing plans  
**So that** I can choose the right plan for my item

**Design Note (2026-10-16):** Listing plans, their features and their prices are dynamic: management changes them from the admin console (US-116) as business decisions change, so the app never hard-codes them and the values below are the current ones, not fixed rules. Basic is paid (₹49); there is no free plan today, and a plan whose price is set to zero is free. Prices include GST for now; the tax setting is also managed from the admin console. Until the admin console exists, plan changes are made through a database change.

**Acceptance Criteria:**
- Given I am creating a listing
- When I reach plan selection step
- Then I see the plan options configured by the platform with a clear comparison (the current plans are shown below):
  
**Basic Plan (₹49 after discount, originally ₹99):**
  - Listed in chronological order
  - 7 days validity
  - AI + Email support only
  
**Boosted Plan (₹149 after discount, originally ₹399):**
  - Listed on top when searched
  - 7 days validity
  - AI + Email + Human Chat support
  
**Priority Plan (₹249 after discount, originally ₹699):**
  - Boosted placement + Featured on landing page
  - "Featured" badge on listing
  - 1 month validity
  - AI + Email + Chat + On-call support

- When I select a plan
- Then I see payment breakdown before confirming, with the price shown as including GST
- When payment succeeds
- Then selected plan features activate immediately

**Edge Cases:**
- User wants to upgrade mid-validity (handled in US-064)
- Plan expires before item sells
- User wants refund for unused plan period
- Multiple items with different plans

**Validation Rules:**
- Validity starts from publication of the listing
- Plans, features and prices come from the platform's plan settings and can change; a listing keeps the price and validity that applied when the seller chose the plan
- Prices include GST (the tax setting is managed from the admin console, US-116)
- Plan features non-transferable
- Featured items shown max 20 on landing page (rotation basis)
- Support level determines response time SLA

**Error Scenarios:**
- `ERROR_PAYMENT_REQUIRED`: "Complete payment to activate plan"
- `PLAN_EXPIRED`: "Your listing plan has expired. Renew to continue visibility"

---

### US-079: Buyer Premium Plan Features
**As a** buyer  
**I want to** understand premium plan options  
**So that** I can choose the right subscription

**Acceptance Criteria:**
- Given I am a free user or want to upgrade
- When I view premium plans
- Then I see three tiers with features:

**Basic Plan (Free):**
  - 3 photo searches per day
  - Chat with sellers
  - AI + Email support
  - Unlimited validity

**Smart Plan (₹49/month after discount, originally ₹99):**
  - 10 photo searches per day
  - Chat + Voice calls with sellers
  - AI + Email + Human Chat support
  - 7-day validity

**Vision Plan (₹149/month after discount, originally ₹499):**
  - Unlimited photo searches
  - Chat + Voice + Video calls with sellers
  - AI + Email + Chat + On-call support
  - 1-month validity

- When I select a plan
- Then I see pricing and features summary
- When I complete payment
- Then plan activates immediately
- And I can use premium features

**Edge Cases:**
- User downgrades mid-subscription
- User exhausts daily photo search limit
- Plan expires mid-search
- User wants refund

**Validation Rules:**
- Daily limits reset at midnight IST
- Plan validity starts from payment date
- Auto-renewal unless cancelled
- Downgrade takes effect at next billing cycle
- No pro-rated refunds

**Error Scenarios:**
- `ERROR_DAILY_LIMIT_REACHED`: "Daily photo search limit reached. Upgrade for more"
- `ERROR_PREMIUM_REQUIRED`: "Upgrade to Smart or Vision plan to make voice calls"
- `SUBSCRIPTION_EXPIRED`: "Your subscription expired. Renew to continue"

---

### US-080: Auto-Expire Inactive Negotiations
**As a** platform  
**I want to** auto-expire inactive negotiations  
**So that** stale offers don't block transactions

**Acceptance Criteria:**
- Given a negotiation is in progress
- When 48 hours pass with no activity from either party
- Then negotiation status changes to "EXPIRED"
- And both parties receive notification
- And seller's item becomes available for other buyers
- And buyer can make new offer if interested
- When negotiation expires
- Then no party can accept/counter the last offer
- And negotiation history is retained for reference

**Edge Cases:**
- Buyer replies just before expiry
- Seller was on vacation/unavailable
- Multiple negotiations expire simultaneously
- User wants to restart expired negotiation

**Validation Rules:**
- Timeout: 48 hours from last message
- 24-hour warning notification sent before expiry
- Expired negotiations retained in history
- Users can create new negotiation after expiry
- No automatic price acceptance on expiry

**Error Scenarios:**
- `ERROR_NEGOTIATION_EXPIRED`: "This negotiation has expired. Start a new offer"
- `WARNING_EXPIRING_SOON`: "Negotiation will expire in 24 hours. Please respond"

---

### US-081: Block Transactions for Users Under Investigation
**As a** platform  
**I want to** block high-risk actions for flagged users  
**So that** fraud is prevented during investigation

**Acceptance Criteria:**
- Given a user is flagged for fraud investigation
- When user account status is "UNDER_REVIEW" or "RESTRICTED"
- Then the following actions are blocked:
  - Creating new listings
  - Making payments
  - Withdrawing funds
  - Accepting offers
  - Bulk actions
- When user attempts blocked action
- Then they see message: "Your account is under security review. Contact support"
- When investigation completes
- Then restrictions are lifted or account is banned
- And user is notified of outcome

**Edge Cases:**
- User has active orders during investigation
- User receives payment while under review
- False positive flagging
- User tries to create new account

**Validation Rules:**
- Active orders can complete but no new transactions
- Funds held in escrow remain safe
- Investigation SLA: 48-72 hours
- User can view account but cannot transact
- Support ticket automatically created

**Error Scenarios:**
- `ACCOUNT_UNDER_REVIEW`: "Your account is under security review. You'll be notified within 72 hours"
- `ACTION_BLOCKED`: "This action is temporarily blocked. Contact support for details"
- `ACCOUNT_RESTRICTED`: "Your account has limited access. Contact support"

---

### US-082: Image Watermark Detection
**As a** platform  
**I want to** detect images with watermarks from other platforms  
**So that** sellers use original photos

**Acceptance Criteria:**
- Given a seller uploads listing images
- When system analyzes images
- Then AI detects watermarks from known platforms (OLX, Quikr, Facebook Marketplace, etc.)
- When watermark is detected
- Then upload is rejected
- And seller sees error: "Remove watermarks and upload original photos"
- When seller uploads edited image to bypass detection
- Then perceptual hashing still detects manipulation
- And image is flagged for manual review

**Edge Cases:**
- Seller's own watermark/logo
- Very faint or partially cropped watermark
- Multiple images in batch upload
- Seller claims watermark is legitimate

**Validation Rules:**
- Check against database of known platform watermarks
- Perceptual hashing to detect edited images
- Allow user watermark if disclosed
- Manual review for borderline cases
- Flagged images cannot be published until cleared

**Error Scenarios:**
- `ERROR_WATERMARK_DETECTED`: "Image contains watermark from another platform. Upload original photos"
- `ERROR_IMAGE_MANIPULATION_DETECTED`: "Image appears edited. Upload unmodified photos"
- `WARNING_UNDER_REVIEW`: "Image flagged for review. You'll be notified within 24 hours"

---

### US-083: System Audit Trail
**As a** platform administrator  
**I want** comprehensive audit logs of critical actions  
**So that** I can investigate issues and ensure compliance

**Acceptance Criteria:**
- Given system is operational
- When users perform critical actions, system logs:
  - User ID, timestamp, IP address, device info
  - Action type (login, payment, order, listing, dispute)
  - Before/after state for data changes
  - Result (success/failure) and error codes
- Critical actions include:
  - User registration/login/logout
  - Password changes
  - Payment transactions
  - Order creation/cancellation
  - Listing creation/edit/delete
  - Dispute raised/resolved
  - Admin actions (ban, suspend, override)
  - Payout method changes
  - Account deletion requests
- When admin views audit logs
- Then logs are searchable by user, date, action type
- And logs are tamper-proof (write-only)
- When compliance audit occurs
- Then logs can be exported securely

**Edge Cases:**
- High-volume logging (millions of events/day)
- Log storage limits
- Sensitive data in logs (PII redaction)
- Log retention beyond 7 years

**Validation Rules:**
- Logs retained for 7 years minimum (compliance)
- Logs encrypted at rest
- PII redacted in exports
- Immutable once written
- Admin access logged separately

**Error Scenarios:**
- `ERROR_LOG_WRITE_FAILED`: Alerts sent to ops team
- Backup logging mechanism activated

---

### US-084: Pre-Publication Trust & Safety Review
**As a** platform  
**I want** all listings reviewed before publication  
**So that** prohibited items and fraud are prevented

**Acceptance Criteria:**
- Given a seller has paid for the listing plan (US-008, US-009)
- When payment succeeds
- Then listing enters "TRUST_SAFETY_REVIEW" state
- And AI performs automated checks:
  - Restricted item detection (weapons, drugs, etc.)
  - Image analysis (inappropriate content)
  - Text analysis (banned keywords)
  - Price reasonableness
  - Seller reputation score
- When AI fraud score < 70
- Then listing auto-approves and publishes
- When AI fraud score > 70
- Then listing queued for manual review
- And admin reviews within 24 hours
- When admin approves
- Then listing publishes
- When admin rejects
- Then seller is notified with reason
- And can revise and resubmit without paying again (3 review attempts in total)
- When the third review attempt also fails
- Then the listing is closed, the seller is notified, and the plan fee is refunded

**Edge Cases:**
- AI false positive on legitimate item
- Borderline prohibited item (toy weapon)
- Seller tries to bypass with coded language
- High volume causes review backlog
- Seller disputes rejection

**Validation Rules:**
- All listings must pass review before publication
- Auto-approval for trusted sellers (rating > 4.5, 50+ sales)
- Manual review SLA: 24 hours
- Rejection reason must be specific
- Seller can appeal rejection
- A seller has 3 review attempts per paid plan; after the third failed attempt the plan fee is refunded (automatic or manual refund is decided later)
- Appeals reviewed by senior moderator

**Error Scenarios:**
- `LISTING_UNDER_REVIEW`: "Your listing is under review. You'll be notified within 24 hours"
- `LISTING_REJECTED`: "Listing rejected: [specific reason]. Revise and resubmit"
- `LISTING_REJECTED_FINAL`: "Listing rejected after 3 review attempts. Your plan fee will be refunded"
- `APPEAL_SUBMITTED`: "Appeal submitted. Senior team will review within 48 hours"

---

### US-085: Seller Payment Release Notification
**As a** seller  
**I want** to be notified when payment is released  
**So that** I know funds are available

**Acceptance Criteria:**
- Given buyer has confirmed item receipt
- When escrow releases payment to seller
- Then seller receives notifications via:
  - Push notification
  - In-app notification
  - Email
  - SMS (for amounts > ₹5000)
- Notification includes:
  - Order ID
  - Item name
  - Gross amount
  - Platform fee deducted
  - Net amount received
  - Expected payout date (2-3 business days)
- When seller taps notification
- Then app opens to transaction details page
- When payout completes to bank/UPI
- Then seller receives confirmation notification

**Edge Cases:**
- Notification delivery fails
- Multiple payouts on same day
- Payout delayed due to bank issues
- Seller has no payout method set up

**Validation Rules:**
- Notification sent within 5 minutes of release
- Transaction details page shows complete breakdown
- Payout timeline: 2-3 business days to bank
- Seller can view pending payouts in wallet

**Error Scenarios:**
- `ERROR_NOTIFICATION_FAILED`: System retries, seller can check in-app
- `PAYOUT_DELAYED`: "Payout delayed. Expected by [date]"
- `ERROR_NO_PAYOUT_METHOD`: "Add payout method to receive funds"

---

### US-086: WhatsApp Notifications
**As a** user  
**I want** to receive important updates via WhatsApp  
**So that** I don't miss critical information

**Acceptance Criteria:**
- Given I have opted in for WhatsApp notifications
- When critical events occur, I receive WhatsApp messages:
  - Order placed/shipped/delivered
  - Payment received
  - Offers received
  - Disputes raised
  - Account alerts
- When I receive WhatsApp notification
- Then message includes:
  - Event summary
  - Order/transaction reference
  - Quick action button (Track Order, View Details)
- When I tap action button
- Then WhatsApp opens app deep link to relevant page
- When I don't have app installed
- Then web link opens

**Edge Cases:**
- User hasn't opted in for WhatsApp
- WhatsApp number different from registered mobile
- WhatsApp business account API rate limits
- User blocks WhatsApp notifications

**Validation Rules:**
- Opt-in required for WhatsApp notifications
- WhatsApp number must be verified
- Rate limit: Max 10 messages per day per user
- High-priority events always sent (order status)
- Low-priority batched into daily digest

**Error Scenarios:**
- `ERROR_WHATSAPP_NOT_ENABLED`: User doesn't see WhatsApp option
- `ERROR_DELIVERY_FAILED`: Falls back to SMS/Email
- `RATE_LIMIT_REACHED`: Next message queued for tomorrow

**Flutter Implementation Notes:**
- Opt-in toggle in NotificationsSettingsScreen (linked to US-087)
- Deep link scheme: `valuex://order/{orderId}` handled via `go_router` deep link config
- WhatsApp Business API integration is backend-side; mobile only manages opt-in preference

---

### US-087: Notification Preferences Management
**As a** user  
**I want to** manage my notification preferences  
**So that** I only receive notifications I care about

**Acceptance Criteria:**
- Given I am logged in
- When I navigate to "Settings > Notifications"
- Then I see notification categories:
  - Order Updates (placed, shipped, delivered)
  - Messages & Offers
  - Payment & Transactions
  - Account & Security
  - Marketing & Promotions
- For each category, I can toggle channels:
  - Push notifications
  - Email
  - SMS
  - WhatsApp
- When I disable a channel for a category
- Then I stop receiving those notifications
- Exception: Critical security notifications always sent
- When I tap "Test Notifications"
- Then I receive sample notification on enabled channels

**Edge Cases:**
- User disables all notifications
- Critical security event occurs (override user preference)
- User changes phone number (re-verify channels)
- User wants to temporarily mute all for vacation

**Validation Rules:**
- Security notifications cannot be fully disabled
- Changes take effect immediately
- User can set quiet hours (no notifications 10 PM - 8 AM)
- "Mute All" option available with expiry time

**Error Scenarios:**
- `WARNING_SECURITY_NOTIFICATIONS`: "Security notifications cannot be disabled"
- `SUCCESS_PREFERENCES_SAVED`: "Notification preferences updated"

**Flutter Implementation Notes:**
- NotificationsSettingsScreen accessible from ProfileScreen settings
- Category/channel matrix rendered as grouped `SwitchListTile` widgets
- Security category rows rendered non-interactive with a lock icon
- Preferences stored in `flutter_secure_storage` and synced to backend

---

## Lifecycle State Machines

### US-088: Lifecycle State - User Account
**As a** platform  
**I want** to track user account lifecycle states  
**So that** account status determines access permissions

**Acceptance Criteria:**
- Given a user interacts with platform
- Then account must be in one of these states:
  - NEW: Registration started, not completed
  - OTP_PENDING: Awaiting mobile verification
  - IDENTITY_VERIFICATION_PENDING: Aadhaar verification in progress
  - SIGNUP_PENDING: Aadhaar done or skipped, Sign Up form (profile, terms) not yet submitted
  - ACTIVE: Registration complete, can use the platform (transactions need Aadhaar)
  - UNDER_REVIEW: Flagged for investigation
  - RESTRICTED: Limited access during review
  - SUSPENDED: Temporarily banned (7 days)
  - BANNED: Permanently banned
  - CLOSED: User-requested account deletion
- State transitions:
  - NEW → OTP_PENDING → EMAIL_VERIFICATION_PENDING → IDENTITY_VERIFICATION_PENDING → SIGNUP_PENDING → ACTIVE
  - ACTIVE → UNDER_REVIEW → RESTRICTED → SUSPENDED → BANNED
  - ACTIVE → CLOSED
- Business rules:
  - Only ACTIVE users can transact
  - UNDER_REVIEW users can view but not create/pay
  - SUSPENDED users cannot login
  - BANNED users' Aadhaar is blacklisted
  - CLOSED accounts retained for 7 years (compliance) but inaccessible

**Edge Cases:**
- User tries to register while SUSPENDED
- Account auto-moves from SUSPENDED to ACTIVE after 7 days
- User appeals BANNED status
- CLOSED account has active orders

**Validation Rules:**
- State changes logged in audit trail
- User notified of all state changes
- Active orders must complete before account closure
- Appeals allowed for SUSPENDED/BANNED within 30 days

**Error Scenarios:**
- `ACCOUNT_SUSPENDED`: "Your account is suspended until [date]"
- `ACCOUNT_BANNED`: "Your account has been permanently banned"
- `ACCOUNT_UNDER_REVIEW`: "Account under review. Contact support"

---

### US-089: Lifecycle State - Listing
**As a** platform  
**I want** to track listing lifecycle states  
**So that** listing status determines visibility and actions

**Acceptance Criteria:**
- Given a seller creates a listing
- Then listing progresses through states:
  - DRAFT: Being created
  - PLAN_SELECTION_PENDING: Seller choosing plan
  - PLAN_PAYMENT_PENDING: Payment in progress
  - PLAN_PAYMENT_FAILED: Payment unsuccessful
  - PLAN_PAYMENT_SUCCESS: Payment successful
  - MEDIA_UPLOAD_PENDING: Photos being uploaded
  - AI_DETAILS_GENERATED: AI suggested metadata
  - PRICE_PENDING: Seller setting final price
  - TRUST_SAFETY_REVIEW: Under moderation
  - APPROVED: Cleared for publication
  - PUBLISHED: Live and visible
  - BUYER_INQUIRY_PENDING: Buyer viewing
  - NEGOTIATION_IN_PROGRESS: Price negotiation active
  - OFFER_ACCEPTED: Price agreed
  - ORDER_CREATED: Buyer ordered
  - SOLD: Transaction complete
  - EXPIRED: Listing plan validity ended
  - DEACTIVATED_BY_SELLER: Seller removed
  - REMOVED_BY_ADMIN: Moderation action
  - REJECTED: Failed trust & safety
  - REVISION_REQUIRED: Seller must fix issues

**Business Rules:**
- Cannot publish without successful plan payment
- Must pass TRUST_SAFETY_REVIEW before PUBLISHED
- PUBLISHED listings visible in search
- SOLD listings archived
- EXPIRED listings can be renewed

**Validation Rules:**
- State transitions logged
- Seller notified at key states
- Visibility controlled by state
- Expired listings auto-renewed not allowed (manual only)

---

### US-090: Lifecycle State - Order
**As a** platform  
**I want** to track order lifecycle states  
**So that** order status determines actions and payments

**Acceptance Criteria:**
- Given an order is created
- Then order progresses through states:
  - ORDER_INITIATED: Buyer started checkout
  - SELLER_PRICE_ACCEPTED: Negotiation complete
  - CHECKOUT_STARTED: Buyer at payment page
  - PAYMENT_PENDING: Payment processing
  - PAYMENT_FAILED: Payment unsuccessful
  - PAYMENT_SUCCESS: Payment received
  - ESCROW_HELD: Funds held securely
  - SHIPPING_MODE_SELECTED: Delivery/self-pickup chosen
  - SELLER_PACKING_PENDING: Seller preparing item
  - SELLER_PROOF_UPLOADED: Package photos uploaded
  - PICKUP_SCHEDULED: Logistics assigned
  - PICKED_UP: Item collected
  - IN_TRANSIT: Being shipped
  - OUT_FOR_DELIVERY: Final delivery attempt
  - DELIVERED: Buyer received
  - BUYER_PROOF_PENDING: Awaiting buyer photos
  - BUYER_CONFIRMATION_PENDING: Awaiting buyer confirmation
  - COMPLETED: Payment released, transaction done
  - RETURN_REQUESTED: Buyer wants return
  - DISPUTE_RAISED: Issue reported
  - SHIPMENT_LOST: Item lost in transit
  - DELIVERY_FAILED: Could not deliver
  - RETURN_TO_SELLER: Item being returned
  - CANCELLED: Order cancelled

**Business Rules:**
- Escrow held until COMPLETED or DISPUTE_RAISED
- Auto-complete after 7 days if no buyer action
- CANCELLED triggers refund
- SHIPMENT_LOST triggers investigation
- Each order covers exactly one item; a checkout with several items creates several orders (US-019, US-021)

**Validation Rules:**
- State transitions sequential
- Cannot skip states (except exceptions like CANCELLED)
- Both parties notified at key states
- Timestamps recorded for SLA tracking

**Related User Stories:**
- US-112: tapping "Start Packing" on Incoming Orders moves the order from `SHIPPING_MODE_SELECTED` to `SELLER_PACKING_PENDING`; the seller's Incoming Orders buckets (New, Packing, Scheduled, Shipped) are derived from these states

---

### US-091: Lifecycle State - Payment & Escrow
**As a** platform  
**I want** to track payment and escrow lifecycle  
**So that** funds are released correctly

**Acceptance Criteria:**
- Given a payment is initiated
- Then payment/escrow progresses through states:
  - PAYMENT_INITIATED: Buyer started payment
  - PAYMENT_PENDING: Gateway processing
  - PAYMENT_SUCCESS: Payment received
  - PAYMENT_FAILED: Payment unsuccessful
  - ESCROW_CREATED: Escrow account created
  - ESCROW_HELD: Funds locked
  - RELEASE_PENDING: Awaiting buyer confirmation
  - RELEASED_TO_SELLER: Payment released
  - REFUND_REVIEW: Refund request under review
  - REFUND_APPROVED: Refund authorized
  - REFUND_REJECTED: Refund denied
  - REFUND_PROCESSED: Money returned to buyer
  - PARTIAL_RELEASE: Split payment (partial refund scenario)
  - ADMIN_HOLD: Manual hold during dispute

**Business Rules:**
- ESCROW_HELD is default state after payment
- RELEASED_TO_SELLER only after buyer confirmation or 7-day auto-release
- ADMIN_HOLD during active disputes
- PARTIAL_RELEASE requires admin approval

**Validation Rules:**
- All state changes logged immutably
- Financial transactions auditable
- Refund timeline: 5-7 business days
- Seller payout timeline: 2-3 business days after release

---

### US-092: Lifecycle State - Shipping
**As a** platform  
**I want** to track shipping lifecycle states  
**So that** delivery is monitored end-to-end

**Acceptance Criteria:**
- Given an order requires shipping
- Then shipping progresses through states:
  - SHIPPING_NOT_REQUIRED: Self-pickup order
  - SHIPPING_REQUIRED: Delivery order
  - SHIPPING_PARTNER_SELECTION: Logistics being assigned
  - PICKUP_SLOT_SELECTED: Seller chose time
  - PICKUP_SCHEDULED: Logistics confirmed
  - PICKUP_ASSIGNED: Driver assigned
  - PICKED_UP: Item collected from seller
  - IN_TRANSIT: In logistics network
  - OUT_FOR_DELIVERY: Final mile delivery
  - DELIVERED: Handed to buyer
  - PICKUP_FAILED: Seller unavailable
  - PICKUP_RESCHEDULED: New pickup time set
  - DELIVERY_FAILED: Buyer unavailable
  - DELIVERY_RESCHEDULED: New delivery attempt
  - RETURN_TO_SELLER: Max attempts exceeded
  - SHIPMENT_DELAYED: Logistics delay
  - SHIPMENT_LOST: Cannot locate package
  - INVESTIGATION_OPENED: Lost shipment under review

**Business Rules:**
- Max 3 delivery attempts before RETURN_TO_SELLER
- SHIPMENT_LOST triggers refund process
- PICKUP_FAILED allows 2 reschedules
- Tracking updated at each checkpoint

**Validation Rules:**
- State transitions trigger notifications
- GPS tracking for IN_TRANSIT (future)
- ETA calculated dynamically
- Delivery proof (photo/signature) required

---

### US-093: Lifecycle State - Return
**As a** platform  
**I want** to track return lifecycle states  
**So that** returns are processed correctly

**Acceptance Criteria:**
- Given a buyer requests return
- Then return progresses through states:
  - RETURN_REQUESTED: Buyer initiated
  - RETURN_ELIGIBILITY_CHECK: System validates (within 7 days, item condition)
  - RETURN_APPROVED: Seller/admin approved
  - RETURN_REJECTED: Return denied
  - RETURN_SHIPPING_PENDING: Buyer to ship back
  - RETURN_IN_TRANSIT: Item being returned
  - RETURN_DELIVERED_TO_SELLER: Seller received
  - SELLER_RETURN_INSPECTION: Seller checking condition
  - RETURN_ACCEPTED: Item as described
  - RETURN_DISPUTED: Item damaged/wrong item returned
  - TRUST_SAFETY_REVIEW: Admin reviewing dispute
  - REFUND_INITIATED: Refund processing
  - REFUND_PROCESSED: Money returned
  - RETURN_CLOSED: Process complete

**Business Rules:**
- Returns allowed within 7 days of delivery
- Buyer pays return shipping
- RETURN_DISPUTED escalates to admin
- REFUND_PROCESSED includes item price + original shipping

**Validation Rules:**
- Seller must inspect within 48 hours
- Auto-accept if seller doesn't respond in 72 hours
- Admin resolves disputes within 48 hours
- Refund timeline: 5-7 business days

---

### US-094: Lifecycle State - Dispute
**As a** platform  
**I want** to track dispute lifecycle states  
**So that** disputes are resolved fairly

**Acceptance Criteria:**
- Given a dispute is raised
- Then dispute progresses through states:
  - DISPUTE_CREATED: User raised issue
  - EVIDENCE_PENDING: Awaiting evidence from parties
  - EVIDENCE_SUBMITTED: Both parties submitted proof
  - TRUST_SAFETY_REVIEW: Admin reviewing
  - MORE_INFO_REQUIRED: Admin needs more details
  - DECISION_PENDING: Admin finalizing decision
  - RESOLVED_BUYER_REFUND: Full refund to buyer
  - RESOLVED_SELLER_RELEASE: Payment to seller
  - RESOLVED_PARTIAL_REFUND: Split resolution
  - DISPUTE_CLOSED: Case closed

**Business Rules:**
- Escrow locked during dispute (ADMIN_HOLD)
- Evidence deadline: 48 hours
- Admin reviews within 48-72 hours
- Decision is final (one appeal allowed)
- Both parties notified at each state

**Validation Rules:**
- Evidence must include: images, chat logs, shipment proof
- Admin decision requires written justification
- Appeal window: 7 days from decision
- Senior admin handles appeals

---

### US-095: Lifecycle State - Support Ticket
**As a** platform  
**I want** to track support ticket lifecycle  
**So that** customer issues are resolved efficiently

**Acceptance Criteria:**
- Given a user raises a ticket
- Then ticket progresses through states:
  - TICKET_CREATED: User submitted issue
  - ASSIGNED: Agent assigned
  - IN_PROGRESS: Agent working on it
  - WAITING_FOR_USER: Agent needs user input
  - WAITING_FOR_INTERNAL_REVIEW: Escalated internally
  - RESOLVED: Issue fixed
  - CLOSED: Ticket closed
  - REOPENED: User reopened after closure

**Business Rules:**
- Auto-assign based on ticket type and agent availability
- WAITING_FOR_USER for >3 days → auto-close
- User can reopen within 30 days of CLOSED
- Priority tickets (payment, dispute) have faster SLA

**Validation Rules:**
- SLA tracking per ticket type
- Agent response time monitored
- User satisfaction survey after RESOLVED
- Ticket history retained for 1 year

---

### US-096: Lifecycle State - Premium Subscription
**As a** platform  
**I want** to track buyer premium subscription lifecycle  
**So that** feature access is controlled correctly

**Acceptance Criteria:**
- Given a buyer interacts with premium features
- Then subscription progresses through states:
  - PLAN_NOT_ACTIVE: Free user
  - UPGRADE_PROMPT_SHOWN: Paywall displayed
  - PLAN_SELECTED: User chose Smart/Vision plan
  - PAYMENT_PENDING: Payment processing
  - PAYMENT_SUCCESS: Payment received
  - PLAN_ACTIVE: Subscription active
  - PLAN_EXPIRED: Subscription ended
  - RENEWAL_PENDING: Auto-renewal due

**Business Rules:**
- PLAN_ACTIVE users access premium features per plan limits
- PLAN_EXPIRED reverts to free tier
- RENEWAL_PENDING triggers 3 days before expiry
- Failed renewal → 3-day grace period → PLAN_EXPIRED

**Validation Rules:**
- Daily photo search limits enforced
- Communication privileges per plan
- Support level based on plan
- Auto-renewal unless user cancels

---

## Compliance & Accessibility

### US-097: Data Export Request (GDPR Compliance)
**As a** user  
**I want** to export all my personal data  
**So that** I have a copy of my information

**Acceptance Criteria:**
- Given I am logged in
- When I navigate to "Privacy Settings > Download My Data"
- Then I see "Request Data Export" button
- When I tap "Request Data Export"
- Then system queues export job
- And I see message: "Export will be ready in 24-48 hours. We'll email you"
- When export is ready
- Then I receive email with secure download link
- And link expires in 7 days
- When I download export
- Then I receive ZIP file containing:
  - Profile information (JSON)
  - Listing history (CSV)
  - Order history (CSV)
  - Transaction history (CSV)
  - Messages (JSON)
  - Ratings and reviews (JSON)

**Edge Cases:**
- Multiple export requests in short time
- Very large data (>100 MB)
- Export generation fails
- User requests export then deletes account

**Validation Rules:**
- One export request per 30 days
- Data includes last 2 years only
- Email link valid for 7 days
- Download link single-use for security
- Data anonymizes other users' PII

**Error Scenarios:**
- `ERROR_RECENT_EXPORT`: "You requested an export recently. Try again after [date]"
- `ERROR_EXPORT_FAILED`: "Export failed. Please try again or contact support"
- `LINK_EXPIRED`: "Download link expired. Request new export"

---

### US-098: Data Deletion Request (Right to be Forgotten)
**As a** user  
**I want** to delete my account and all personal data  
**So that** my information is removed from the platform

**Acceptance Criteria:**
- Given I am logged in
- When I navigate to "Privacy Settings > Delete Account"
- Then I see warning: "This action is permanent. All data will be deleted"
- When I confirm deletion
- Then system checks for:
  - Active orders: Cannot delete
  - Pending disputes: Cannot delete
  - Outstanding payments: Cannot delete
- When no blockers exist
- Then account scheduled for deletion
- And I receive email: "Account will be deleted in 30 days. Login to cancel"
- When 30 days pass
- Then account and data permanently deleted:
  - Profile deleted
  - Listings removed
  - Messages deleted
  - Images deleted
  - Personal data anonymized in transaction records (7-year retention for compliance)
- When I try to login after deletion
- Then I see: "Account does not exist"

**Edge Cases:**
- User has active orders (must complete first)
- User has pending payouts (must be processed first)
- User requests deletion then tries to cancel on day 29
- User creates new account after deletion

**Validation Rules:**
- Cannot delete with active orders
- Cannot delete with pending payouts/refunds
- Cannot delete with open disputes
- 30-day grace period (can cancel deletion)
- Transaction records anonymized but retained for 7 years (tax compliance)
- Aadhaar mapping removed after 30 days

**Error Scenarios:**
- `ERROR_ACTIVE_ORDERS`: "Complete active orders before deleting account"
- `ERROR_PENDING_PAYMENTS`: "Resolve pending payments before deletion"
- `ERROR_OPEN_DISPUTES`: "Resolve disputes before deleting account"
- `DELETION_SCHEDULED`: "Account will be deleted on [date]. Login to cancel"

---

### US-099: Screen Reader and Accessibility Support
**As a** visually impaired user  
**I want** the app to be accessible via screen reader  
**So that** I can use the platform independently

**Acceptance Criteria:**
- Given I have a screen reader enabled (TalkBack, VoiceOver)
- When I navigate the app
- Then all UI elements are announced correctly:
  - Buttons announce action ("Add to cart button")
  - Images have descriptive alt text ("Red bicycle, good condition")
  - Form fields announce label and current value
  - Error messages announced immediately
  - Navigation structure clear (headings, landmarks)
- When I perform actions
- Then feedback is announced ("Item added to cart")
- When viewing listings
- Then essential info announced: title, price, condition, location
- When in checkout flow
- Then each step announced clearly
- All interactive elements keyboard/gesture navigable

**Edge Cases:**
- Complex forms with multiple fields
- Image galleries (swipeable)
- Real-time chat messages
- Video call interface
- Dynamic content updates

**Validation Rules:**
- WCAG 2.1 AA compliance minimum
- All interactive elements have accessible labels
- Focus order logical
- Color contrast ratios meet standards (4.5:1 for text)
- Touch targets minimum 44x44 pixels
- Text resizable up to 200% without loss of functionality

**Error Scenarios:**
- `N/A`: Accessibility is always-on, no error states
- Graceful degradation if screen reader not detected

---

### US-100: Admin Analytics Dashboard
**As an** admin  
**I want** a comprehensive analytics dashboard  
**So that** I can monitor platform health and business metrics

**Acceptance Criteria:**
- Given I am logged in as admin
- When I view analytics dashboard
- Then I see key metrics:

**Business Metrics:**
  - GMV (Gross Merchandise Value) - daily/weekly/monthly
  - Conversion rate (visitors → buyers)
  - Listing success rate (published → sold)
  - Average order value
  - Revenue (platform fees)
  - Active users (DAU/MAU)
  - User growth rate

**Operational Metrics:**
  - Delivery success rate
  - Average delivery time
  - Failed delivery rate
  - Return rate
  - Dispute rate and resolution time

**Trust & Safety Metrics:**
  - Fraud detection accuracy
  - Fraudulent listing blocked
  - User accounts banned
  - Average fraud investigation time

**Support Metrics:**
  - Support ticket volume
  - Average resolution time
  - Support SLA compliance
  - Customer satisfaction score

**Premium Features:**
  - Photo search usage rate
  - Conversion rate (free → paid users)
  - Premium revenue
  - Average photo searches per user

- When I select date range or filters
- Then data updates accordingly
- When I tap on a metric
- Then I see detailed breakdown and trend chart
- When I tap "Export Report"
- Then CSV/PDF is generated

**Edge Cases:**
- Data unavailable for certain periods
- Real-time vs batch processed metrics
- Very large date ranges (performance)

**Validation Rules:**
- Data refreshed every 15 minutes
- Historical data: last 24 months
- Role-based access (admin, analyst)
- Export includes metadata (date range, filters)

**Error Scenarios:**
- `ERROR_DATA_UNAVAILABLE`: "Unable to load metrics. Try again"
- `ERROR_EXPORT_FAILED`: "Export failed. Try again or contact support"

---

### US-101: Google Sign-In (Optional Convenience Login)
**As a** returning user  
**I want to** sign in using my Google account  
**So that** I can log in without entering my mobile number and OTP every time

**Acceptance Criteria:**
- Given I am on the login screen
- When I tap "Continue with Google"
- Then I am redirected to Google OAuth consent screen
- When I grant consent and Google returns an ID token
- Then the backend validates the Google ID token with Google's public keys
- If my Google email is already linked to a ValueX account:
  - Then I am logged in and issued a new JWT
- If this is a new Google account (first social login):
  - Then I am prompted to enter and verify my mobile number via OTP
  - After mobile OTP verification, my account is created (or linked if mobile already exists)
  - Then I can continue with or without Aadhaar verification
- When I am logged in via Google
- Then my session is identical to Mobile OTP login (same JWT, same permissions)

**Edge Cases:**
- Google token expired or invalid
- Google email already linked to another ValueX account (via different Google account)
- User revokes Google access from Google account settings
- Google OAuth service temporarily unavailable
- User's mobile number (entered after social login) already registered under a different account

**Validation Rules:**
- Google ID token must be validated server-side using Google's token verification endpoint
- Token audience must match ValueX's Google Client ID
- Email from Google token must be stored (not used as account key — mobile is the account key)
- Social login only permitted after account has a verified mobile number

**Error Scenarios:**
- `ERROR_INVALID_GOOGLE_TOKEN`: "Google sign-in failed. Please try again"
- `ERROR_GOOGLE_SERVICE_UNAVAILABLE`: "Google Sign-In is temporarily unavailable"
- `ERROR_MOBILE_ALREADY_REGISTERED`: "This mobile number is already registered with another account"
- `ERROR_SOCIAL_ACCOUNT_ALREADY_LINKED`: "This Google account is already linked to another ValueX account"

**Flutter Implementation Notes:**
- Use `google_sign_in` Flutter package (v7). The app sends only the `idToken`; the backend validates it and the app never trusts client-side verification. The app signs the Google account out locally right after reading the token
- The entry point is the existing "Continue with Google" button on Create Account; Sign In has none (its design has no Google button)
- Returning Google user: `status` in the response drives the same routing as Sign In (`ACTIVE` goes to Home, unfinished registration resumes at its step). A suspended or banned account is refused with the standard messages and the user stays signed out
- New Google account: a mobile-number step and an OTP step (the shared OTP view, `googleLink` channel) follow. Verifying creates the account at `IDENTITY_VERIFICATION_PENDING` (Aadhaar, then Sign Up), or links Google to an existing `ACTIVE` account (straight to Home)
- Terms and consent are not sent with the number: Sign Up collects and records them, as for mobile-OTP registration. The backend leaves them unset until then
- Build configuration: `GOOGLE_SIGN_IN=mock` (development; a dev-only account chooser sends `mock-<name>` to a backend running the mock verifier, rejected in prod) or `native` with `GOOGLE_SERVER_CLIENT_ID` (the web client ID the backend accepts) and optional `GOOGLE_IOS_CLIENT_ID`
- Not done yet: real Google OAuth clients (Web, Android with SHA-1s, iOS with URL scheme), and Apple guideline 4.8 (an equivalent privacy-preserving login is needed once Google is offered on iOS; Sign in with Apple is out of scope)

---

### US-102: Apple Sign-In (Optional Convenience Login)
**As a** returning user on an Apple device  
**I want to** sign in using my Apple ID  
**So that** I can log in quickly with Face ID / Touch ID without entering credentials

**Acceptance Criteria:**
- Given I am on the login screen on an iOS device
- When I tap "Sign in with Apple"
- Then the native Apple Sign-In sheet is presented
- When I authenticate (Face ID / Touch ID / password)
- Then Apple returns an identity token and optionally an email
- Then the backend validates the Apple identity token using Apple's public keys
- If my Apple account is already linked to a ValueX account:
  - Then I am logged in and issued a new JWT
- If this is a new Apple account (first Apple login):
  - Then I am prompted to enter and verify my mobile number via OTP
  - After mobile OTP verification, my account is created (or linked if mobile already exists)
  - Then I can continue with or without Aadhaar verification
- When I am logged in via Apple
- Then my session is identical to Mobile OTP login (same JWT, same permissions)

**Edge Cases:**
- Apple hides user email (Hide My Email feature) — system must use `sub` claim as the stable Apple user identifier, not email
- Apple only returns email on first sign-in — must be stored on first use
- User removes app from "Sign in with Apple" in Apple ID settings
- Apple Sign-In is not available on Android (must be iOS/macOS only)
- Apple identity token expired or signature invalid

**Validation Rules:**
- Apple identity token must be validated server-side using Apple's public keys (JWK endpoint)
- Token `iss` must be `https://appleid.apple.com`
- Token `aud` must match ValueX's Apple Service ID
- Apple `sub` (stable user identifier) stored as the social account key — NOT email
- Apple Sign-In is mandatory on iOS if any other third-party login is offered (App Store guideline 4.8)
- Social login only permitted after account has a verified mobile number

**Error Scenarios:**
- `ERROR_INVALID_APPLE_TOKEN`: "Apple Sign-In failed. Please try again"
- `ERROR_APPLE_SERVICE_UNAVAILABLE`: "Apple Sign-In is temporarily unavailable"
- `ERROR_MOBILE_ALREADY_REGISTERED`: "This mobile number is already registered with another account"
- `ERROR_SOCIAL_ACCOUNT_ALREADY_LINKED`: "This Apple ID is already linked to another ValueX account"

**Flutter Implementation Notes:**
- Use `sign_in_with_apple` Flutter package
- Apple Sign-In is required on iOS if Google Sign-In is shown (App Store Rule 4.8)
- Send `identityToken` to backend — backend validates, never trust client-side
- Store `userIdentifier` (the `sub` claim) as the Apple account key, not email
- On Android, show Google Sign-In only (Apple Sign-In not available)

---

## Profile Management Extensions

### US-103: Profile Hub / Account Menu Navigation
**As a** registered user  
**I want to** access all my account-related sections from a single Profile hub  
**So that** I can quickly navigate to my orders, listings, payments, and settings without hunting for them

**Acceptance Criteria:**
- Given I am logged in
- When I tap the "Profile" tab
- Then I see my profile summary (photo, display name, rating, joined date) at the top
- And below it, a menu of sections grouped by category:
  - **Activity**: My Orders, Incoming Orders (seller orders to pack and ship), My Listings, Saved Items, Offers/Negotiations
  - **Payments**: Payment & Transaction History, Payout Settings (sellers only)
  - **Preferences**: Notification Preferences, Language
  - **Support**: Help & Support, Raise Dispute, My Support Tickets
  - **Account**: Edit Profile, My Addresses, Account Security, Privacy Settings, Logout
- When I tap any menu item
- Then I am navigated to the corresponding screen
- When a section has actionable items (e.g., pending orders, unread offers)
- Then a badge/count indicator is shown next to that menu item

**Edge Cases:**
- New user with no orders/listings/saved items (empty states shown, not hidden)
- Seller-only sections shown to buyers who haven't listed anything yet
- Menu item destination temporarily unavailable (service down)
- User has pending items in multiple sections simultaneously (multiple badges)

**Validation Rules:**
- Sections requiring seller status remain visible to all users but stay empty until first listing
- Badge counts refresh on profile view and on relevant push notification receipt
- The Incoming Orders badge is the number of orders in the New state (US-112)
- Logout requires confirmation dialog (see US-104)

**Error Scenarios:**
- `ERROR_SECTION_UNAVAILABLE`: "This section is temporarily unavailable"

**Related User Stories:**
- Profile summary fields: US-003
- Activity: My Orders → US-023, US-070; Incoming Orders → US-112; My Listings → US-010, US-067, US-064; Saved Items → US-073; Offers → US-076
- Payments: US-071 (transaction history), US-072 (payout settings)
- Preferences: US-087 (notifications), US-044 (language)
- Support: US-043, US-045, US-046 (help & support), US-047 (raise dispute), US-074 (ticket status)
- Account: US-105 (account security), US-113 (my addresses; the row shows the coming soon message until US-113 is built), US-063 / US-098 (delete account), US-104 (logout)

**Flutter Implementation Notes:**
- ProfileScreen acts as the navigation shell; each menu row uses `ListTile` with leading icon, trailing badge/chevron
- Badge counts sourced from a single `ProfileSummaryProvider` (Riverpod) aggregating unread/pending counts per section
- Seller-only rows (Payout Settings, Seller Analytics) conditionally rendered based on `hasActiveListings` flag

---

### US-104: Account Logout
**As a** registered user  
**I want to** log out of my account  
**So that** I can secure my session, especially on shared devices

**Acceptance Criteria:**
- Given I am logged in
- When I tap "Logout" from the Profile menu
- Then I see a confirmation dialog: "Are you sure you want to log out?"
- When I confirm
- Then my session token is invalidated on the server
- And locally stored session data is cleared
- And I am redirected to the login screen
- When I cancel
- Then I remain on the current screen with no change

**Edge Cases:**
- User logs out while a listing/message is being uploaded (in-flight request)
- User logs out on a device with no network (local logout only, server invalidation queued)
- User has multiple active sessions on other devices
- Logout triggered automatically after password/PIN change (force re-login)

**Validation Rules:**
- Server-side JWT/session invalidation required, not just client-side token deletion
- Locally cached sensitive data cleared on logout (draft listings excluded)
- In-flight uploads allowed to complete or are cancelled with a warning before logout proceeds

**Error Scenarios:**
- `ERROR_LOGOUT_FAILED`: "Unable to log out. Please try again"
- `WARNING_UPLOAD_IN_PROGRESS`: "An upload is in progress. Logging out will cancel it"

**Related User Stories:**
- Accessed from Profile Hub: US-103
- Related to session creation: US-001 (registration/JWT issuance), US-101 / US-102 (social login sessions)
- Logging out of all other devices: US-105

**Flutter Implementation Notes:**
- Logout clears `flutter_secure_storage` tokens and resets Riverpod auth state
- Confirmation via standard `AlertDialog`; destructive action styled red
- Navigates to login screen via `go_router` and clears navigation stack

---

### US-105: Account Security Settings
**As a** registered user  
**I want to** manage my account security settings  
**So that** I can protect my account from unauthorized access

**Acceptance Criteria:**
- Given I am logged in
- When I navigate to "Profile > Account Security"
- Then I see:
  - Registered mobile number (masked, with "Change" option requiring OTP re-verification)
  - Registered email (masked, with "Change" option requiring OTP re-verification)
  - Aadhaar verification status (read-only badge; prompts to complete if pending)
  - Active sessions/devices list with last active time
  - "Log out of all other devices" action
  - "Delete My Account" entry point
- When I change my mobile or email
- Then I must verify the new value via OTP before it takes effect
- When I tap "Log out of all other devices"
- Then all sessions except the current one are invalidated
- When I tap "Delete My Account"
- Then I am taken to the account deletion flow

**Edge Cases:**
- User tries to change mobile to a number already registered to another account
- User has no other active sessions to log out
- User loses access to old mobile/email before completing change verification
- Aadhaar verification status shown as pending for a long time

**Validation Rules:**
- Mobile/email change requires OTP verification on the new value (same rules as US-001: 6-digit OTP, 5-minute expiry)
- Old mobile/email remains active until new one is verified
- Session list limited to last 10 active sessions, sorted by most recent
- Account deletion entry point only enabled if no active orders/disputes (per US-063 / US-098 rules)

**Error Scenarios:**
- `ERROR_MOBILE_ALREADY_REGISTERED`: "This mobile number is already registered with another account"
- `ERROR_EMAIL_ALREADY_REGISTERED`: "This email is already linked to another account"
- `ERROR_INVALID_OTP`: "Invalid or expired OTP"
- `ERROR_NO_OTHER_SESSIONS`: "No other active sessions found"

**Related User Stories:**
- Accessed from Profile Hub: US-103
- OTP verification rules shared with: US-001 (registration)
- Account deletion: US-063, US-098
- Single-session logout: US-104

**Flutter Implementation Notes:**
- AccountSecurityScreen with masked mobile/email fields (e.g. `•••• •••210`) and "Change" CTA reusing the OTP flow from US-001
- Active sessions list backed by backend session table; "This device" tag on current session
- Delete Account CTA styled as destructive, routes to existing deletion confirmation flow (US-063 / US-098)

---

## Authentication Extensions

### US-106: Mobile OTP Login for Returning Users
**As a** registered user who signed up via mobile OTP  
**I want to** log back into my account using my mobile number and OTP  
**So that** I can access my account again after my session expires, without registering a second time

**Design Note:** Identified as a gap when auditing the backend API flow for returning users — US-001 only covers first-time registration and explicitly *rejects* an already-registered mobile (`ERROR_MOBILE_ALREADY_REGISTERED`) with no alternate path. US-101/US-102 (Google/Apple Sign-In) are written as *"Optional Convenience Login"* — a shortcut around mobile-OTP login — but the primary mobile-OTP login path they're a shortcut *around* was never itself specced. This story fills that gap.

**Acceptance Criteria:**
- Given I already have an account (any state other than mid-registration OTP steps)
- When I enter my registered mobile number on the login screen
- Then I receive a 6-digit OTP via SMS
- When I enter the correct OTP within 5 minutes
- Then I am issued a new access token and refresh token
- And I am taken to the appropriate screen for my account's current state — `ACTIVE` accounts go to the home screen; accounts that never finished registration (e.g. `EMAIL_VERIFICATION_PENDING`) resume at that exact step
- Given my account is `SUSPENDED`
- Then login is blocked with a suspension message
- Given my account is `BANNED` or `CLOSED`
- Then login is blocked with a recovery-required message

**Edge Cases:**
- Mobile number entered has no account at all — must not silently create one; point the user to registration instead
- Account is mid-registration (never reached `ACTIVE`) — login must resume it, not treat it as an error
- Account state changes (suspended/banned) between OTP send and OTP verify
- Repeated login OTP requests — same abuse-prevention rules as registration OTP

**Validation Rules:**
- Login requires an existing account — the mobile number must already be registered (opposite check from US-001's registration)
- Same OTP mechanics as US-001: 6-digit, 5-minute expiry, max 3 sends / 10 min, max 5 failed verifies / 10 min
- The issued JWT reflects the account's *current* `status` and `aadhaarVerified` values, read fresh from the database — never a cached/stale value from a previous session
- Login must not be usable to bypass Aadhaar-gated actions any differently than a freshly registered session would

**Error Scenarios:**
- `ERROR_MOBILE_NOT_REGISTERED`: "No account found with this mobile number. Please register"
- `ERROR_ACCOUNT_SUSPENDED`: "Your account is suspended. Please contact support"
- `ERROR_ACCOUNT_RECOVERY_REQUIRED`: "Your account requires recovery. Please contact support"
- `ERROR_INVALID_OTP`, `ERROR_OTP_EXPIRED`, `ERROR_OTP_RATE_LIMIT`, `ERROR_OTP_MAX_ATTEMPTS` (same as US-001)

**Related User Stories:**
- Shares OTP send/verify mechanics with US-001 (registration)
- US-101 (Google Sign-In) and US-102 (Apple Sign-In) are convenience alternatives to this story, not replacements for it
- Token issued here expires per US-107 (Access Token Refresh) rules
- Logout: US-104

**Flutter Implementation Notes:**
- Login screen offers mobile-number entry as the primary action (route `/sign-in`, code step `/sign-in/verify`). The "Continue with Google"/"Continue with Apple" secondary buttons are **not** part of the first implementation; they arrive with US-101/US-102
- Reuses the OTP-entry widget already built for registration (US-001) through a `login` channel, with login-specific error text. Sign In has its own entry controller so it never shares state with the Sign Up mobile step
- On success, route based on the returned `status` claim rather than assuming `ACTIVE` — anything short of `ACTIVE` re-enters the registration flow at that step
- Unknown mobile number (`ERROR_MOBILE_NOT_REGISTERED`): inline error plus a "Create an account" link; the footer "Don't have an account? Sign up" carries a valid entered number to the Sign Up mobile step, and Sign Up's "Already have an account? Sign In" footer does the reverse
- Entry points: Create Account "Sign In", the account-unavailable screen ("Back to Sign In") and session expiry all route to Sign In
- `SUSPENDED` and `BANNED`/`CLOSED` show the backend's generic messages; the suspension end date is only inside the message text, so it is not shown as a separate value
- English and Hindi strings; the Hindi text needs native-speaker review

---

### US-107: Access Token Refresh
**As a** logged-in user  
**I want** my session to renew automatically using my refresh token  
**So that** I don't have to re-enter my mobile OTP every time my short-lived access token expires

**Design Note:** Every current auth flow (US-001, US-101, US-102, and the new US-106) already issues a `refreshToken` in its response — but no endpoint anywhere accepts one. It's a dead value today. Separately, the JWT validation filter checks only signature and expiry, not the token's `type` claim — meaning a refresh token can currently be used directly as a bearer access token, which this story's validation rules close.

**Acceptance Criteria:**
- Given I hold a valid, unexpired refresh token
- When my access token expires and the app submits the refresh token
- Then I receive a new access token and a new refresh token
- Given my refresh token has expired or was already used once (rotated out)
- Then the refresh attempt fails and I must log in again (US-106 or social sign-in)
- Given I log out (US-104)
- Then my refresh token is invalidated immediately and cannot be used again
- Given my account was suspended/banned after the refresh token was issued
- Then the refresh attempt fails even though the token itself hasn't expired

**Edge Cases:**
- A previously-used (rotated-out) refresh token is presented again — treat as possible theft, invalidate the whole token family if session tracking exists
- An access token is submitted to the refresh endpoint instead of a refresh token
- Two refresh calls fire concurrently from the same client (e.g. two open tabs) near expiry
- Clock skew right at the expiry boundary

**Validation Rules:**
- The refresh endpoint must reject any token whose `type` claim is not `refresh`
- Refresh tokens are single-use: each successful refresh issues a new refresh token and invalidates the one just used (rotation)
- The new access token's `status`/`aadhaarVerified` claims are re-read from the database at refresh time, not copied from the old token — so state changes from another session (e.g. Aadhaar verified elsewhere) propagate on next refresh
- A refresh must fail closed if the account is no longer in good standing at refresh time, regardless of token expiry

**Error Scenarios:**
- `ERROR_INVALID_REFRESH_TOKEN`: "Session expired. Please log in again"
- `ERROR_REFRESH_TOKEN_EXPIRED`: "Session expired. Please log in again"
- `ERROR_WRONG_TOKEN_TYPE`: "Invalid token for this operation"
- `ERROR_ACCOUNT_RECOVERY_REQUIRED` / `ERROR_ACCOUNT_SUSPENDED`: account state changed since the token was issued

**Related User Stories:**
- Consumes tokens issued by US-001, US-101, US-102, US-106
- If session tracking ships for US-104/US-105 (the `jti`/`user_sessions` design), refresh rotation should mark the old session revoked and create a new one; if not, refresh operates statelessly (signature + expiry + type check only)
- Logout: US-104 (must invalidate the refresh token, not just the access token)

**Flutter Implementation Notes:**
- HTTP client interceptor catches `401`, calls the refresh endpoint with the stored refresh token, retries the original request once. Concurrent `401`s share one refresh call, and a request that failed with a token another call has already replaced is retried with the new token instead of triggering a second refresh
- The refresh call itself, and public endpoints, never go through the refresh interceptor
- On refresh failure the stored tokens are cleared and the app returns to Sign In (US-106) with a "Session expired" notice. Network, timeout and 5xx failures during refresh keep the tokens so the user is not signed out by a bad connection
- `ERROR_ACCOUNT_SUSPENDED` and `ERROR_ACCOUNT_RECOVERY_REQUIRED` at refresh time open the account-unavailable screen instead of the generic notice ("fail closed" for accounts no longer in good standing)
- The `status` and `aadhaarVerified` returned by each refresh update the app's account state, so a change made elsewhere (for example Aadhaar verified on another device) routes the user on the next refresh
- Refresh token stored in secure storage only, never in plain shared preferences; token values are never logged

---

## Address Management

### US-108: Address Entry with Google Places Autocomplete and Address Verification
**As a** user entering an address (when I buy with home delivery or post an item to sell)  
**I want to** search for my address with suggestions and have it verified  
**So that** my address is accurate and deliveries and pickups can be completed

**Design Change (2026-10-15):** Addresses are no longer collected at Sign Up or on Home. The first address is saved when the user checks out an item for home delivery (US-020) or posts an item to sell (US-004), and becomes their default address for delivery and pickup. A user can add more addresses and give each a name (Home, Office or any custom name). Home only uses the current or a saved location for searching and never calls address search or verification (US-111).

**Related User Stories:**
- US-001: Sign Up no longer collects an address; this story is not used there
- US-004: posting a listing asks for the pickup address; US-020: delivery address selection; US-027: pickup address; all reuse this story's component and verification
- US-111: Home does not use address search or verification
- US-113: My Addresses (placeholder) manages the saved addresses

**Acceptance Criteria:**
- Given I am entering an address
- When I type at least 3 characters in the address search field
- Then I see address suggestions from Google Places Autocomplete, restricted to India
- When I select a suggestion
- Then State, City, Pincode and the address line are filled in from the selected place
- And I can still edit the details (house or flat number, landmark)
- When I submit the address
- Then the backend verifies it through the address verification API
- And I see whether the address is verified
- Given verification fails
- Then I can correct the address and try again
- Given location permission is denied, Places is unavailable, or I am offline
- Then I can still enter the address manually using the same fields

**Edge Cases:**
- Google Places quota exceeded or service down
- Address outside India or outside the serviceable area
- Pincode does not match the selected city or state
- User edits fields after selecting a suggestion (verify the edited result, not the suggestion)
- Ambiguous or partial results; PO box; very long addresses
- Address typed in Hindi or another Indian language
- Offline or slow network while typing (debounce, show last results, fall back to manual)
- Verification provider downtime

**Validation Rules:**
- Pincode is 6 digits; state must be one of the supported Indian states or union territories
- Address line is 10 to 255 characters
- The verification result (verified or not) and the verified timestamp are stored with the address
- A saved address has an optional name (up to 50 characters) and one address per user is the default; the first address a user saves becomes the default
- The user's saved addresses are listed for the app, default first, with name and full address (used by the Home saved-location pop-up, US-111)
- The verification provider is behind a port with a sandbox adapter for development, the same pattern as the OTP and Aadhaar providers
- Full addresses are never written to logs

**Error Scenarios:**
- `ERROR_ADDRESS_INVALID`: "Please enter a complete address"
- `ERROR_ADDRESS_NOT_VERIFIED`: "We could not verify this address. Please check and try again"
- `ERROR_ADDRESS_SERVICE_UNAVAILABLE`: "Address verification is temporarily unavailable"
- `ERROR_PINCODE_MISMATCH`: "The pincode does not match the selected city or state"

**Flutter Implementation Notes:**
- Google Places Autocomplete with a 300 ms debounce, India-only restriction and session tokens to control billing
- API keys restricted per platform (Android package and SHA-1, iOS bundle ID); keys supplied through the environment config, never committed
- One reusable address component used by checkout (delivery), posting a listing (pickup) and My Addresses
- Manual-entry fallback always available; accessible labels on suggestions

**Backend Notes:**
- Dedicated address verification API (provider-agnostic port) and storage of structured address components, place ID and verification status; design to be written in the LLD
- `GET /users/me/addresses` returns the user's saved addresses (name, full address, default flag), default first; saving addresses is added by the stories that collect them (US-004, US-020, US-113)

---

### US-113: My Addresses (placeholder)
**As a** user  
**I want to** see and manage the addresses I have saved  
**So that** I can reuse them for delivery, pickup and finding items near me

**Status:** Placeholder. The product owner will detail this story later; the acceptance criteria below are only a starting point.

**Design Note:** Addresses are not collected at Sign Up. The first address is saved when the user buys an item with home delivery (US-020) or posts an item to sell (US-004), and becomes the default for delivery and pickup. A user can enter new addresses and give each a name such as Home, Office or any custom name. The Profile tab shows a "My Addresses" row under Account that shows the coming soon message until this story is built.

**Related User Stories:**
- US-103: the "My Addresses" row under Account in the Profile tab
- US-108: address entry and verification component
- US-004, US-020, US-027: where addresses are first saved and chosen
- US-111: Home offers the saved addresses as "Use my saved location"

**Acceptance Criteria (to be detailed):**
- Given I am logged in
- When I tap "My Addresses" under Account in the Profile tab
- Then I see my saved addresses with their names and full addresses, my default first
- And I can add, edit, rename, delete and choose my default address (to be detailed)

**Edge Cases:** To be detailed

**Validation Rules:** To be detailed

**Error Scenarios:** To be detailed

**Open:**
- Story points are not estimated yet
- Rules for deleting the default address or an address used by an open order

---

## Mobile App Security

### US-109: Mobile App Security Hardening
**As a** user of the ValueX mobile app  
**I want** the app to protect my session, my traffic and my sensitive screens  
**So that** my account and personal data are safe even on a compromised network or device

**Design Note:** CODING_STANDARDS section 3.7 requires SSL pinning for production builds, root and jailbreak detection, and a device ID kept in secure storage. These are app-wide controls, not part of any single feature story. Secure token storage, log redaction and screenshot protection for the Aadhaar screens are delivered with US-001; this story covers the remaining items. Later Payment, Escrow and Bank Details screens enable the screenshot protection service in their own stories.

**Related User Stories:**
- US-001: delivers secure token storage, log redaction and the screenshot protection service (Aadhaar screens)
- US-104, US-105: sessions and logout can use the device ID
- US-021, US-072: Payment and Bank Details screens must enable screenshot protection

**Acceptance Criteria:**
- Given a production build
- When the app connects to the ValueX API
- Then the connection is accepted only if the server certificate matches the pinned certificates or public keys
- And a mismatch fails the request with a "Connection not secure" message and no data is sent
- Given a production build runs on a rooted or jailbroken device
- Then the user sees a security warning
- And Aadhaar, payment and bank detail flows are blocked
- Given the app starts for the first time
- Then a random device ID is generated and stored in secure storage
- And it is sent with API requests so sessions can be tied to a device
- Given the user logs out or reinstalls the app
- Then the device ID behaviour is consistent with the platform's secure-storage rules
- Given a development or staging build
- Then pinning and root detection can be disabled by the environment config without code changes

**Edge Cases:**
- Certificate rotation (pins must include a backup pin; app update path when pins change)
- Corporate proxy or antivirus intercepting TLS on the user's network
- Emulators and simulators in development builds
- False positives of root detection on custom ROMs
- Device ID retained across reinstall on iOS Keychain
- Secure storage unavailable or corrupted

**Validation Rules:**
- Pinning applies to production builds only and is configured per environment
- The device ID is a random UUID and contains no hardware identifiers
- No security check result or device ID is written to logs or analytics
- Behaviour on a rooted or jailbroken device (warn and block sensitive flows, or block the app) is a product decision to be confirmed before implementation

**Error Scenarios:**
- `ERROR_CONNECTION_NOT_SECURE`: "Connection not secure. Please check your network and try again"
- `ERROR_DEVICE_NOT_SUPPORTED`: "This feature is not available on this device for security reasons"

**Flutter Implementation Notes:**
- Pinning through the Dio HTTP client adapter, pins supplied by environment config
- Root and jailbreak detection through a maintained package or native checks, chosen in the implementation plan
- Device ID service in `core/security` backed by `FlutterSecureStorage`

---

## UI Quality

### US-110: Registration UI Accessibility and Readability Review
**As a** user of the ValueX mobile app, including users with low vision, motor difficulty or a screen reader, or who read in bright light or at a large text size  
**I want** every registration screen to be easy to see, read, understand and tap  
**So that** I can create my account without help

**Design Note:** An audit of the screens delivered by US-001 (onboarding, create account, mobile and email entry and OTP, Aadhaar, Sign Up, Terms, blocked, Home placeholder) found 20 gaps against WCAG 2.2 AA and Material and Apple touch guidance. The gaps, measurements and proposed fixes are in `valuex-mobile/docs/App UI review findings.md`. This story fixes them screen by screen. For each screen the before and after design is reviewed and approved by the product owner before the code changes. The result is written into `valuex-mobile/docs/Flutter-Design-System.md` so later screens are compliant from the start.

**Related User Stories:**
- US-001: delivers the screens reviewed here
- US-099: app-wide accessibility story; this story applies the same standard to the registration screens first and raises the touch target minimum to 48
- US-108: the address entry component must follow the same standards when it is used at checkout and when posting a listing

**Acceptance Criteria:**
- Given any text on a registration screen
- Then its contrast against its background is at least 4.5:1
- And borders and edges of inputs, selectors and cards are at least 3:1 against their surroundings
- Given any tappable control
- Then its tap area is at least 48 by 48 dp, without changing how it looks where the design is smaller
- Given a screen reader (TalkBack, VoiceOver) is on
- Then every tappable control has a label, screen titles are announced as headings, loading states are announced, and onboarding can be completed
- Given the system text size is set to 200%
- Then no registration screen clips or overlaps text, in English and Hindi
- Given an input is invalid
- Then the error is shown under the field in text that stays on screen until it is fixed
- And a disabled primary button shows why it is disabled
- Given the system "reduce motion" setting is on
- Then animated elements are replaced by static ones
- Given a new screen is added
- Then automated checks for tap target size, labels and text contrast run on it and must pass
- And the design system document lists the colour, type, spacing and touch rules the screen must follow

**Edge Cases:**
- Hindi text, which needs more line height than English
- Text size at 200% on a small phone
- Colours defined in Figma that fail contrast (onboarding): the design owner approves a compliant replacement
- Controls that look smaller than 48 dp but have a larger tap area
- Bright sunlight on a low-contrast display

**Validation Rules:**
- WCAG 2.2 AA: text 4.5:1, non-text 3:1
- Touch target minimum 48 dp (Material); this also satisfies the 44 pt iOS minimum
- Body and helper text at least 14 px; 12 px only for non-essential captions
- Every change is shown as a before and after design and approved before implementation
- Colour and type values come from design tokens only, never literals in widgets

**Error Scenarios:**
- `N/A`: No new error codes; this story changes how existing errors are shown

**Flutter Implementation Notes:**
- Colour, type and size changes go through the tokens in `lib/core/theme`
- Flutter's accessibility guideline checks (`androidTapTargetGuideline`, `iOSTapTargetGuideline`, `labeledTapTargetGuideline`, `textContrastGuideline`) run in widget tests on every screen
- Large text is tested at 1.5x and 2x in English and Hindi with the real brand fonts

---

## Home

### US-111: Home Page
**As a** logged-in buyer  
**I want** a home page that shows items near me, lets me search, browse categories and reach the main areas of the app  
**So that** I can find something to buy quickly and start from one familiar place

**Design Note:** Built from the Figma design file frame "Home Page" (node `2017:635`), the "Location & Notification Row" (`2019:2022`) and the bottom navigation (`2021:2850`). Where the Figma frame differs from `valuex-mobile/docs/Flutter-Design-System.md`, the design system wins (colours, type sizes, 48 dp tap targets, the single brand gradient, the 428 px base frame). The promo card and the listing cards in Figma are sample content.

**Related User Stories:**
- US-011: search, category browsing and filters; the Home search bar, category tiles and "See All" open its results
- US-012: tapping a listing card opens listing details
- US-038, US-039: the camera icon in the search bar starts photo search; non-premium users see the paywall
- US-008, US-078: Boosted and Priority listings are ranked first and carry the "BOOSTED" or "Featured" badge
- US-019: cart; US-077: notifications; US-004: Sell; US-013: Chats; US-103: Profile
- US-108: address entry and verification are not used on Home; Home offers only my current location or one of my saved locations
- US-113: My Addresses manages the saved addresses that Home offers
- US-110, US-099: accessibility and design system rules the screen must meet

**Acceptance Criteria:**
- Given my account is `ACTIVE`
- When I open the app or tap the Home tab
- Then I see, from top to bottom: a gradient header, a promo card, a "Browse" category row, "Featured Deals Near You", and the bottom navigation
- And the header shows my current area and city, a cart icon and a notifications bell, with a search bar and a camera icon below
- Given I have allowed location access
- When Home loads
- Then the area and city are taken from my live location and the listings near me are shown
- Given I have not allowed location access or it is unavailable
- Then I am offered "Use my current location" and "Use my saved location"
- When I tap the location in the header
- Then I can choose "Use my current location" or "Use my saved location", and Home refreshes for the new place
- And there is no way to type an address on Home
- When I choose "Use my saved location"
- Then a pop-up asks me to select one of my saved addresses, each shown with its name (Home, Office or a custom name) and its full address
- And when I select one, listings near that address (its city, state and pincode) are shown
- Given I have no saved address
- Then the pop-up tells me an address is saved when I buy or sell an item, and I can close it or use my current location
- And the place chosen on Home is used only to find listings near it; it is not saved as an address and is never sent to the server
- When I tap the bell
- Then I open my notifications (US-077), and an unread badge shows when there are unread items
- When I tap the cart
- Then I open my cart (US-019), and a badge shows when the cart has items
- When I tap the search bar
- Then I go to search (US-011)
- When I tap the camera icon
- Then photo search starts if I am a premium buyer, otherwise I see the upgrade paywall (US-038)
- When a promo is active
- Then I see a promo card with its title, short text and a call-to-action button, and tapping it opens the promo's target
- And when there is no active promo, the promo section is not shown
- When I look at "Browse"
- Then I see the first five categories from the backend, each with its image and name, and a "More" tile
- When I tap a category
- Then I see listings in that category (US-011)
- When I tap "More"
- Then I see a category selection page that lists all categories from the backend, and tapping one opens its listings
- When I look at "Featured Deals Near You"
- Then I see listing cards in two columns, each with an image, title, price in INR, city, seller rating and condition
- And Boosted and Priority listings come first and show their badge
- When I tap a listing card
- Then I open its details (US-012)
- When I tap "See All"
- Then I see the full list of listings near me in the same order, with pagination (US-011)
- When I pull down on Home
- Then the page refreshes
- When I tap a bottom navigation item
- Then I go to Home, Search, Sell (US-004), Chats (US-013) or Profile (US-103), and the current item is marked
- Given I skipped Aadhaar verification
- When I tap Sell
- Then the Sell flow opens as for any other user; Aadhaar verification is asked for only after I submit my listing (US-004)
- Given the network is down
- When I open Home
- Then I see the last loaded content with a message and a Retry button, or an error state with Retry when nothing was loaded before

**Edge Cases:**
- Location permission denied once, denied permanently, or turned off in the device settings
- Location takes long to resolve or is outside India
- No saved location chosen and no location permission
- User has no saved addresses, or the list of saved addresses fails to load
- No listings near the chosen place
- Fewer than five categories returned by the backend
- Promo expired or removed while the user is on Home
- A listing image fails to load (a placeholder is shown)
- A listing is sold or removed while it is on screen
- Very long listing titles or city names; Hindi text; text size at 200%
- Cart or notification counts above 99
- Slow network, partial responses (promo loads but listings fail, or the reverse)
- User changes location while a refresh is in progress

**Validation Rules:**
- Only published, non-expired listings are shown
- Featured Deals shows at most 20 listings, Boosted and Priority first, then newest or nearest (US-078, US-011 ranking)
- Listing prices are shown in INR with Indian digit grouping (for example ₹1,85,000)
- Seller rating is shown with one decimal on a 0 to 5 scale; a seller with no rating shows no rating
- Condition is one of the listing condition values (for example Good, Like New, Excellent)
- Categories, their order, names and images come from the backend and are not hard-coded in the app
- Promo content (text, image, target, start and end date) comes from the backend; the app shows at most the active promos
- Location permission is requested on Home with a short explanation of why, not at app start
- Only the area and city (or the city, state and pincode of a saved address) are used for listings; exact coordinates are not logged, and are not stored without consent
- The chosen place is kept on the device only so it survives an app restart; it is never saved as an address and no Google Places or address verification call is made from Home
- Every control has a tap area of at least 48 by 48 dp, every control has a label, titles are headings, text is at least 14 px for anything important and passes 4.5:1 contrast (US-110)
- The screen is added to the automated accessibility and heading tests

**Error Scenarios:**
- `ERROR_LOCATION_PERMISSION_DENIED`: "Location access is off. Use a saved location to see items near you"
- `ERROR_LOCATION_UNAVAILABLE`: "Unable to detect your location. Use a saved location instead"
- `ERROR_HOME_LOAD_FAILED`: "Unable to load Home. Pull down or tap Retry"
- `NO_LISTINGS_NEAR_YOU`: "No items near you yet. Try another location"
- `NO_SAVED_LOCATIONS`: "You have no saved locations yet. An address is saved when you buy or sell an item."
- `ERROR_SAVED_LOCATIONS_FAILED`: "Unable to load your saved locations. Try again"
- `ERROR_CATEGORIES_UNAVAILABLE`: "Unable to load categories. Try again"

**Flutter Implementation Notes:**
- Page built from Figma node `2017:635` with the design system tokens only; the header uses `AppGradients.brand`; Figma values that conflict with the design system are resolved to the design system (decision A)
- Reuses existing components where they fit (`BrandGradientButton` for the promo button, `FieldError` and the loading and error views); new shared pieces: listing card, category tile, promo card, bottom navigation with a raised Sell button, location header
- Bell and cart are separate icon buttons with 48 dp tap areas and count badges
- Location through the device location and permission packages; reverse geocoding gives the area and city; the saved-location pop-up lists the user's saved addresses from `GET /users/me/addresses` and uses the chosen address's city, state and pincode (no address search, no Places)
- Data comes through repository interfaces; until the backend endpoints exist, a mock repository supplies listings, categories and a sample promo
- The category selection page is its own route reached from the "More" tile
- Pull to refresh, loading skeletons, empty and error states; all strings in the English and Hindi ARB files

**Backend Notes:**
- Needs endpoints for the categories list, the home feed (featured and nearby listings by area or coordinates, ranked by plan) and active promos; none exist yet
- Promo content is managed by the product team and loaded before launch
- Scheduling: the mobile page is already built on a mock repository; the backend endpoints are delivered in Sprint 3 (Discovery & Search), after US-011, and the app then switches to them

---

## Seller Order Management

### US-112: Seller Incoming Orders
**As a** seller  
**I want** one list of every order buyers have placed on my items, grouped by what I need to do next  
**So that** I can pack, schedule pickup and follow each order without searching through chats and notifications

**Design Note:** Built from the Figma Make app screen `SellerIncomingOrdersScreen` (Profile > Selling > Incoming Orders). Make shows four sample orders, one per status, with sample buyers, items and prices; that content is a sample, not data. Where the Make screen differs from `valuex-mobile/docs/Flutter-Design-System.md`, the design system wins (colours, type sizes, 48 dp tap targets, the single brand gradient). Make's "Reject" button has no action defined; this story defines it (see Acceptance Criteria and Open Questions).

**Related User Stories:**
- US-103: Profile hub entry ("Incoming Orders") and its New-order badge
- US-023: the order, its reference number and the order details page
- US-090: order lifecycle states from which the four buckets are derived
- US-020, US-022: delivery or self-pickup choice and the self-pickup payment options
- US-031: the buyer confirms collection of a self-pickup order, which completes it
- US-026: "Start Packing" and "Continue Packing" open Pack & Upload Proof
- US-027: "Schedule Pickup" and "View Schedule" open pickup scheduling
- US-059: "Reject" opens seller cancellation with penalty
- US-058: a buyer cancelling removes the order from this list
- US-029: tracking after pickup (the Shipped bucket)
- US-070: completed, cancelled and returned orders are found in order history
- US-077: new-order push notification
- US-110, US-099: accessibility and design system rules the screen must meet

**Acceptance Criteria:**
- Given my account is `ACTIVE` and buyers have paid for orders on my items
- When I open Profile and tap "Incoming Orders" under Selling
- Then I see the Incoming Orders page with a back button, the title "Incoming Orders" and the line "{n} orders · {x} new"
- And when {x} is more than zero, a "{x} New" badge is shown beside the title
- And I see four count tiles: New, Packing, Scheduled and Shipped
- And I see my orders as cards, ordered New first, then Packing, Scheduled and Shipped, newest first inside each group
- And each card shows: the order reference, an "URGENT" tag when it applies, a status chip (icon and text), the item photo, title and price in INR, "Buyer: {name}" with the buyer's initials, and how long ago the order was placed
- And each card has an action area and a button that opens the order details
- Given an order is **New Order** (paid, delivery chosen, I have not started packing)
- Then the card offers "Start Packing" and "Reject"
- When I tap "Start Packing"
- Then the order moves to Packing and I open Pack & Upload Proof for it (US-026)
- When I tap "Reject"
- Then I see the seller cancellation confirmation with the penalty warning (US-059), and only after I confirm is the order cancelled and the buyer refunded in full
- And the penalty always applies once a buyer has booked the order and paid into escrow, whenever I reject it; a Pay at Pickup order has no escrow payment, so no penalty applies (buyer and seller agree it between themselves)
- Given an order is **Packing Required** (packing started, proof not yet uploaded)
- Then the card offers "Continue Packing", which reopens Pack & Upload Proof with the photos I already added kept
- Given I uploaded proof but have not scheduled pickup
- Then the order stays in Packing and the card offers "Schedule Pickup" (US-027)
- Given an order is **Pickup Scheduled**
- Then the card offers "View Schedule", which shows the pickup date, time slot and address (US-027)
- Given an order is **Shipped** (picked up, in transit, out for delivery, delivered or waiting for buyer confirmation)
- Then the card shows "Order Shipped" as a status and has no action button; I follow progress on the order details (US-029)
- Given an order is a **self-pickup order** (the buyer collects the item from me, US-020)
- Then it is treated like any other New Order: it is in the New group with the "New Order" chip and the extra tag "Self Pickup by Buyer"
- And there is no shipping for it: no packing proof and no pickup scheduling
- And the card offers "View Pickup Details" (my pickup address and hours as the buyer sees them) and "Reject"
- And it is never marked URGENT, because there is no logistics pickup deadline
- When the buyer collects the item and confirms in the app (US-031)
- Then the order is completed and leaves the list
- When I tap the order details button on any card
- Then I open the order details with its timeline, buyer, item and the amount held in escrow (US-023)
- When a buyer pays for one of my items
- Then I get a push notification (US-077), the Profile "Incoming Orders" badge increases, and opening the notification takes me to this page
- When I pull down
- Then the page refreshes the list and the counts
- When I come back from packing or pickup scheduling
- Then the card shows the new status without a manual refresh
- When there are more than 20 orders
- Then more are loaded as I scroll
- And when all are loaded I see "Showing all {n} incoming orders" at the bottom
- Given I have no incoming orders
- Then I see an empty state: "No incoming orders yet. Orders for your listings will appear here", and the counts show 0
- Given an order is completed, cancelled, returned or in dispute
- Then it is no longer in this list and is found in order history (US-070)
- Given the network is down
- When I open the page
- Then I see the last loaded list with a message and a Retry button, or an error state with Retry when nothing was loaded before

**Status Mapping (from US-090 order states):**

| Bucket (chip text) | Order states | Seller actions |
|---|---|---|
| New ("New Order") | `SHIPPING_MODE_SELECTED`, delivery orders | Start Packing, Reject |
| New ("New Order", tag "Self Pickup by Buyer") | `SHIPPING_MODE_SELECTED`, self-pickup orders (paid into escrow, or Pay at Pickup, US-022) | View Pickup Details, Reject |
| Packing ("Packing Required") | `SELLER_PACKING_PENDING`; `SELLER_PROOF_UPLOADED` | Continue Packing; Schedule Pickup |
| Scheduled ("Pickup Scheduled") | `PICKUP_SCHEDULED` | View Schedule |
| Shipped ("Shipped") | `PICKED_UP`, `IN_TRANSIT`, `OUT_FOR_DELIVERY`, `DELIVERED`, `BUYER_PROOF_PENDING`, `BUYER_CONFIRMATION_PENDING`, `DELIVERY_FAILED`, `SHIPMENT_LOST` | none |

Not listed: orders before `SHIPPING_MODE_SELECTED` (not yet paid), and `COMPLETED`, `CANCELLED`, `RETURN_REQUESTED`, `RETURN_TO_SELLER`, `DISPUTE_RAISED`.

**Edge Cases:**
- A buyer cancels (US-058) or the order changes state while the seller has the page open: the seller taps an action on a stale card and is told the order has moved on, then the card refreshes
- The seller taps "Start Packing" twice, or on two devices: the second request does nothing harmful and opens the same packing screen
- The seller leaves Pack & Upload Proof without finishing: the order stays in Packing and the entered photos are kept where possible
- The seller uploads proof but does not schedule pickup: the order stays in Packing with "Schedule Pickup"
- Several orders for the same item or the same buyer
- A cart with several items from several sellers becomes one order per item, each with its own order number, escrow, delivery and refund, so each item is its own card
- Buyer name is very long, has no Latin letters, or is a single word (initials from the first letters of the first two words)
- Item photo fails to load or the item has since been removed (a placeholder is shown; the order stays)
- A delivery exception (`DELIVERY_FAILED`, `SHIPMENT_LOST`) is shown in Shipped with its status text so the seller can see it
- Hundreds of orders (pagination); counts above 99
- Hindi text; text size at 200%; item titles that wrap
- Seller account suspended or banned: the page is not available (US-088)
- Self-pickup orders (US-020, US-022) are New orders with the tag "Self Pickup by Buyer" and no shipping; a Pay at Pickup order has no escrow payment, and the buyer may never collect it

**Validation Rules:**
- Only the seller's own orders are returned; another user's order is never visible
- The buyer is shown by display name and initials only; no mobile number, email or address (contact goes through the masked channels of Sprint 4)
- Prices are shown in INR with Indian digit grouping (for example ₹1,85,000); the amount is the order amount (each order is one item)
- The order reference is the same reference the buyer sees (US-023). While the page runs on mock data it shows the sample numbers from the Figma Make screen (for example ORD-S-1001); with real data it shows the actual order number from the backend
- "Urgent" is decided by the server, not the app: a New order whose seller deadline (pickup within 48 hours of the order, US-027) is within 24 hours; self-pickup orders are never urgent
- Which buttons a card shows is decided by the server from the order state, so the app does not hold the state machine
- "Start Packing" is allowed only from the New state; "Continue Packing" and "Schedule Pickup" only from Packing; the server rejects any other request
- "Reject" is offered on New orders and on self-pickup orders; once packing has started the seller cancels from the order details through US-059. In both cases the US-059 penalty applies in full, except on Pay at Pickup orders, which have no escrow payment and no penalty
- Counts and list come from the same data and agree after a refresh
- Every control has a tap area of at least 48 by 48 dp and a label; the page title is a heading; text is at least 14 px for anything important and passes 4.5:1 contrast; a status is told by its icon and text, never by colour alone (US-110)
- The screen is added to the automated accessibility and heading tests

**Error Scenarios:**
- `ERROR_INCOMING_ORDERS_LOAD_FAILED`: "Unable to load your incoming orders. Pull down or tap Retry"
- `ERROR_ORDER_ACTION_NOT_ALLOWED`: "This order has already moved to the next step. Refreshing"
- `ERROR_ORDER_NOT_FOUND`: "This order is no longer available"
- `ERROR_SECTION_UNAVAILABLE`: "This section is temporarily unavailable" (US-103)

**Flutter Implementation Notes:**
- Page `SellerIncomingOrdersScreen` under `lib/features/order/`, route `/seller/orders`, opened from the Profile "Incoming Orders" row; it has a back button (it is not a bottom-navigation tab)
- Layout from Make: header (back, title, count line, New badge) over a tint-to-background fade, a four-tile summary row, then order cards; the card has a header row (reference, URGENT, status chip), an item row (photo, title, price, buyer avatar and name, time) and an action row (primary button, secondary button, details button)
- Design system mapping: Poppins title and DM Sans text; the status chip uses brand colours with an icon and text; "Start Packing" is `BrandGradientButton`, "Reject" is a destructive secondary using `brandError`, other actions use `SingleToneButton`; tiles and cards use the existing card tokens; details button is a 48 dp icon button
- Providers: an incoming-orders list provider (paged) and a summary provider; the summary also feeds the Profile badge; both are refreshed after any action and when a new-order push arrives
- Mobile talks to the backend through a repository interface; until the endpoints exist a mock repository supplies the four sample orders from Make so the screen can be built first, and is replaced by the real repository without a screen change
- Actions navigate to the existing packing and pickup screens of US-026 and US-027; the buttons shown come from the server's `actions` list; the self-pickup tag "Self Pickup by Buyer" is shown from `deliveryMode`
- While running on mock data the repository returns the four sample orders from Make with their order numbers (ORD-S-1001 and so on); the real repository shows the backend order number
- All strings in the English and Hindi ARB files; relative time uses a localized formatter

**Backend Notes:**
- Needs `GET /api/v1/seller/orders`, `GET /api/v1/seller/orders/summary` and `POST /api/v1/seller/orders/{orderId}/start-packing` (see LLD Sprint 6, Part A)
- Adds an `INCOMING_ORDERS` badge provider to the Profile menu summary (US-103)
- Uses the order data and lifecycle of US-023 and US-090; no new table is needed

**Decisions (product owner, 2026-10-12):**
- Urgent: a New delivery order whose pickup deadline (48 hours from the order) is within 24 hours
- Reject: the penalty always applies after a buyer has booked the order and paid into escrow; Pay at Pickup orders have no escrow payment and no penalty
- Self-pickup orders are treated like any New order, with the extra tag "Self Pickup by Buyer" and no shipping
- One order per item: one consolidated payment for any number of items from any number of sellers creates one order per item, each with its own order number, escrow, chat, negotiation, delivery and refund; each seller is paid for their own items
- Order reference: mock data shows the sample numbers from Make; real data shows the actual order number from the backend

**Open:**
- US-090 has no states for the self-pickup hand-over; the owner will update US-090 when needed. Until then a self-pickup order stays New until it completes or is cancelled

---

## Listing Details

### US-114: Listing Item Details Entry
**As a** seller  
**I want** to enter or review my item's title, category, condition, description, location and price on one screen  
**So that** my listing is complete and I can move on to choose a listing plan

**Design Note:** Built from the Figma Make `CreateListingScreen` "Item Details" step (Make file `tzrpUwfrR0SYeyKkv1p0co`), with the content of Make's "Set Your Price" step added to the same page (product owner decision, 2026-10-16). The page has two variants. When AI is disabled or unavailable (the default), the fields start empty and the subtitle reads "Fill in the details". When AI has filled the fields (US-005), they are prefilled, the subtitle reads "AI filled these from your photos" and a banner says "AI filled these from your photos. Review and edit as needed." Make's AI price suggestion card is not part of this story because price suggestion is on hold. Where Make differs from `valuex-mobile/docs/Flutter-Design-System.md`, the design system wins. Order of the seller flow: Photos, Item Details (this story), Listing Plan, Review and Pay, then the Trust and Safety review after payment (US-084), then publication.

**Related User Stories:**
- US-004: delivers the photo step; its minimum is raised to 2 photos by this decision
- US-005: fills this page when AI is enabled; when it is not, the seller types everything
- US-006: later extends the single category to a primary plus up to 3 additional categories from the taxonomy
- US-007: the restricted item check runs on the entered title, description and category when the seller continues
- US-008: the next step, Listing Plan
- US-089, US-084: listing states and the review after payment
- US-108, US-113: when addresses are delivered, the pickup address replaces the temporary location below
- US-111: Home's location is reused here
- US-010: edit uses the same page for published listings

**Acceptance Criteria:**
- Given I have uploaded at least 2 photos and tapped Submit to AI (US-004, US-005)
- When AI is disabled, unavailable or out of quota
- Then I see the message from US-005 and the Item Details page opens with empty fields
- When AI is available
- Then the page opens with the title, category, condition and description filled in, the AI banner shown, and every field editable
- Given I am on the Item Details page
- Then I can enter or change the title, choose one category, choose a condition, write a description and enter my price
- And the condition options are Brand New, Like New, Good, Fair and Poor
- And my price is entered in rupees with a ₹ prefix, with the note "Buyers can negotiate. You can accept, counter, or reject any offer."
- And the location shows the area and city of my current location, taken from Home (US-111), with an action to use my current location if it is not known yet
- When the title, category, condition, description or price is missing
- Then the "Choose Listing Plan" button is disabled and the missing fields are shown under the field
- When I tap "Choose Listing Plan" with the required fields filled
- Then my details are saved to the draft
- And the restricted item check (US-007) runs on them
- And if it passes I continue to listing plan selection (US-008, after the Aadhaar check of US-004 where it applies)
- When I leave the page and come back to the draft
- Then my saved details are shown again
- Given my listing was sent back for revision (US-084)
- Then I can change the same fields, and I resubmit the listing without paying the plan again

**Edge Cases:**
- AI fills a field with text over the allowed length (it is shortened before it is shown)
- Seller clears a field that AI filled
- Seller changes details after returning from the plan screen (allowed while the listing is a draft or in revision)
- Location permission denied, location service off or location unavailable (the same prompts as Home)
- Seller has fewer than 2 photos when continuing (blocked, with a message)
- Price has more than 2 decimals, is zero or negative, or is extremely large
- Network failure when saving (the typed values stay on screen so nothing is lost)
- Text 200% size and Hindi text (US-110 rules apply)
- Title or description contains a restricted word (blocked by the US-007 check, with the same message as AI would give)

**Validation Rules:**
- Title: required, up to 100 characters, spaces trimmed
- Category: required, one category until US-006; chosen from the same category list Home shows
- Condition: required, one of NEW, LIKE_NEW, GOOD, FAIR, POOR (shown as Brand New, Like New, Good, Fair, Poor)
- Description: required, up to 2000 characters
- Price: required, greater than zero, at most 2 decimal places, in rupees, up to ₹1,00,00,000
- Location: the city of the Home location; the device coordinates are never sent to the server or stored
- At least 2 photos must be on the listing to continue (the server checks this too)
- Details can be changed only while the listing is a draft or needs revision

**Error Scenarios:**
- `ERROR_MIN_PHOTOS_REQUIRED`: "At least 2 photos required"
- `ERROR_TITLE_REQUIRED`: "Enter a title for your item"
- `ERROR_CATEGORY_REQUIRED`: "Choose a category"
- `ERROR_CONDITION_REQUIRED`: "Choose the condition of your item"
- `ERROR_DESCRIPTION_REQUIRED`: "Describe your item"
- `ERROR_PRICE_INVALID`: "Enter a valid price"
- `ERROR_LISTING_NOT_EDITABLE`: "This listing can no longer be edited"
- `ERROR_RESTRICTED_ITEM`: shown from US-007 when the check fails

**Flutter Implementation Notes:**
- Page `ItemDetailsScreen` under `lib/features/listing/`, opened after Submit to AI on the photo page; the progress bar has 4 steps (Photos, Details, Plan, Review) because Make's separate Price step is merged into this page
- Layout from Make: header with back and progress bar over the page background, a scrolling form (title input, category chips, condition chips, description box, location field, then the price block), and a bottom button "Choose Listing Plan"
- Design system mapping: Poppins title and DM Sans text; inputs use the theme input style; chips follow the existing chip style with the brand blue for category and the success green for condition; the bottom button is `BrandGradientButton`; the AI banner and the negotiation note use the existing info-card style; tap targets at least 48 dp
- Location reuses the Home location controller and its prompts; it shows the area and city and never shows or sends coordinates
- Photos: the minimum on `ListingPhotoRules` changes from 1 to 2 and the Submit to AI button follows it
- All strings in the English and Hindi ARB files

**Backend Notes:**
- Needs a draft update endpoint (`PATCH /api/v1/listings/{listingId}`) that saves title, category, condition, description, price and location city for the owner while the listing is a draft or in revision, and returns them with the draft
- Uses the existing `listings` columns `title`, `description`, `condition`, `price` and `seller_location`; adds a temporary `category_slug` column until US-006 replaces it with the taxonomy tables
- The server rejects continuing with fewer than 2 photos

**Decisions (product owner, 2026-10-16):**
- The Trust and Safety review runs after payment and before publication; the restricted item check (US-007) runs before plan selection so a seller does not pay for a listing that cannot be published
- Condition values are NEW, LIKE_NEW, GOOD, FAIR, POOR
- One category for now, extended by US-006
- Make's "Set Your Price" content is part of this page; manual price entry is part of this story
- Location is the user's current location, as on Home, until the address stories are delivered
- Minimum 2 photos; the review time shown to sellers is "a few hours"
- Title, category, condition, description and price are all required; the highest price is ₹1,00,00,000; the progress bar has 4 steps
- A listing rejected in review: the seller is notified to modify it and resubmits it for review without paying again, up to 3 review attempts in total; after the third failed review the plan fee is refunded (automatic or manual refund to be decided)

**Open:**
- None

---

## Listing Notifications

### US-115: Listing Lifecycle Notifications
**As a** seller  
**I want** to be told, in the app and by email where it matters, what happens to my listing after I pay for a plan  
**So that** I know what to do next without checking the app

**Design Note:** US-077 covers account, cart, order, payment, offer and dispute events but not the listing lifecycle. This story adds the notifications for the Sprint 2 listing flow (payment, Trust and Safety review, publication, revision, final rejection, refund, expiry and removal) so the messages, channels and wording are defined in one place. The stories that cause these events (US-008, US-009, US-084, US-089) only publish events; this story turns them into notifications. The existing notification module has in-app, SMS and email channels and no push channel yet; push is added to these messages when push infrastructure exists (US-077).

**Related User Stories:**
- US-077: the notification centre, channels, priorities and 90-day history this story reuses
- US-087: the seller's notification preferences
- US-089: the listing status change events that trigger most messages
- US-008, US-009: payment events (payment received, payment failed, refund due)
- US-084: review outcomes (revision required, final rejection)
- US-114: the Item Details page that the revision message opens
- US-044: language; Hindi wording needs native-speaker review

**Acceptance Criteria:**
- Given I paid for a listing plan (or chose the free plan)
- When the payment succeeds
- Then I get "under review" in the app, saying it will be checked within a few hours
- Given my listing is approved and published
- Then I get "your listing is live" in the app, and tapping it opens the listing
- Given a review does not approve my listing (review 1 or 2)
- Then I get "needs changes" in the app and by email, with the reason and how many reviews I have used out of 3
- And it says I can update the listing and resubmit without paying again
- And tapping it opens the Item Details page of that listing (US-114)
- Given my third review fails
- Then I get "not approved after 3 reviews" in the app, by email and by SMS
- And when I paid, it says the plan fee will be refunded, with the amount
- And when I used the free plan, it says nothing about a refund
- Given my plan fee is being refunded
- Then I get "refund is being processed" in the app and by email, with the amount; when the refund is issued, I get "refund issued" (added when the refund step is built)
- Given my payment fails
- Then I get "payment unsuccessful" in the app, and tapping it opens plan selection
- Given my listing expires or an admin removes it
- Then I get "listing expired" (with a renew action) or "listing removed" (with a link to support) in the app, and the removal also by email
- When I open Notifications (US-077)
- Then these messages appear in my history with the listing title, newest first, and unread ones are marked
- And one event never creates more than one notification, even if the event is received twice

**Messages (English text is the source; Hindi is a draft for native-speaker review):**

| Event (`eventType`) | Channels | English | Hindi (draft) |
|---|---|---|---|
| `LISTING_UNDER_REVIEW` | in-app | "Payment received. Your listing is under review and will be checked within a few hours." | "भुगतान प्राप्त हुआ। आपकी लिस्टिंग की समीक्षा चल रही है, कुछ घंटों में जाँच हो जाएगी।" |
| `LISTING_PUBLISHED` | in-app | "Your listing \"{title}\" is now live. Buyers can find it." | "आपकी लिस्टिंग \"{title}\" अब लाइव है। खरीदार इसे देख सकते हैं।" |
| `LISTING_REVISION_REQUIRED` | in-app, email | "Your listing \"{title}\" needs changes: {reason}. Update it and resubmit (review {n} of 3). You will not be charged again." | "आपकी लिस्टिंग \"{title}\" में बदलाव ज़रूरी हैं: {reason}। इसे सुधारकर दोबारा भेजें (समीक्षा {n}/3)। दोबारा भुगतान नहीं करना होगा।" |
| `LISTING_REJECTED_FINAL` | in-app, email, SMS | "Your listing \"{title}\" was not approved after 3 reviews. Your plan fee of ₹{amount} will be refunded." (free plan: no refund sentence) | "आपकी लिस्टिंग \"{title}\" 3 समीक्षाओं के बाद भी स्वीकृत नहीं हुई। आपके प्लान शुल्क ₹{amount} की वापसी की जाएगी।" |
| `LISTING_REFUND_DUE` | in-app, email | "Your refund of ₹{amount} for the listing plan is being processed." | "लिस्टिंग प्लान के ₹{amount} की वापसी प्रक्रिया में है।" |
| `LISTING_PAYMENT_FAILED` | in-app | "Your payment was unsuccessful. Please try again or choose another plan." | "आपका भुगतान सफल नहीं हुआ। कृपया दोबारा कोशिश करें या दूसरा प्लान चुनें।" |
| `LISTING_EXPIRED` | in-app | "Your listing \"{title}\" has expired. Renew it to make it visible again." | "आपकी लिस्टिंग \"{title}\" की अवधि समाप्त हो गई है। फिर से दिखाने के लिए इसे रिन्यू करें।" |
| `LISTING_REMOVED_BY_ADMIN` | in-app, email | "Your listing \"{title}\" was removed by ValueX. Contact support for details." | "आपकी लिस्टिंग \"{title}\" को ValueX ने हटा दिया है। विवरण के लिए सहायता से संपर्क करें।" |

**Edge Cases:**
- The same event is delivered twice (retry, webhook repeat, job re-run): only one notification
- Listing title is very long, contains quotes or non-Latin text (shortened for display)
- Review reason is long (shown in full in the app and email, shortened in a push or SMS)
- Seller has turned off email or in-app notifications (US-087): the preference is followed; the messages that tell the seller to act (needs changes, final rejection, refund, removal) are always kept in the in-app history
- Seller's email is missing or bounces (the in-app message is still created)
- A seller whose listing was approved while the app was closed (the message waits in history)
- Notification arrives after the listing was already deleted

**Validation Rules:**
- Channels and priority follow US-077: high priority (needs changes, final rejection, refund, removal) uses in-app and email, plus SMS for the final rejection; medium (under review, published, payment failed, expired) is in-app only until push exists
- One notification per event, identified by listing, event type and review attempt
- No card, bank or Aadhaar data in any message
- The title and reason are plain text; HTML is not allowed
- Messages carry the event type and its values (title, reason, attempt, amount) so the app can show them in the user's language; email and SMS are sent in English until a language preference is stored on the server
- Each message opens the right screen through a deep link (listing, Item Details, plan selection, support)
- Notification history is kept for 90 days (US-077)

**Error Scenarios:**
- `ERROR_NOTIFICATION_FAILED`: logged, not shown to the user; email and SMS failures never block the listing flow (US-077)

**Flutter Implementation Notes:**
- Notifications page (US-077) renders these types from the event type and values with English and Hindi strings in the ARB files; deep links open `valuex://listing/{listingId}`, the Item Details page, plan selection or support
- Unread badge and grouping follow US-077
- Hindi strings need native-speaker review before release

**Backend Notes:**
- A listener in the notification module (same pattern as `AccountEventNotificationListener`) subscribes to the listing status change event (US-089), the payment events (US-009) and the refund-due event (US-084), and dispatches through `NotificationDispatcher`
- The notification record gets an optional `params` value (title, reason, attempt, amount) so the app can localize; this needs a small migration
- The existing account notification copy still says "JustQlic"; it is changed to "ValueX" when this listener is added, as the product name is ValueX
- Duplicate protection: a unique key of listing, event type and attempt

**Decisions (product owner, 2026-10-16):**
- Listing lifecycle notifications are a separate story from US-077
- Review-attempt rule behind the messages: 3 reviews in total, then a refund (US-084)

**Open:**
- Push notifications for these messages once push infrastructure exists
- Whether email and SMS should be in the seller's language (needs a language preference stored on the server)
- Whether the final-rejection SMS is wanted or in-app and email are enough
- Hindi wording to be reviewed by a native speaker

---

## Plan Administration

### US-116: Admin - Manage Seller Listing Plans and Tax Settings
**As an** admin with plan management permission  
**I want to** create, change and switch off seller listing plans, and set how GST is applied, from the admin console  
**So that** management decisions on plans, features and prices take effect without an app or server release

**Design Note (2026-10-16):** Management changes listing plans, their features and their prices as business decisions change. The plan catalog (US-078) is therefore data, edited here. Today Basic is ₹49 and no plan is free; if management decides a plan should be free, its price is set to zero here and the plan then needs no payment (US-008). Prices include GST for now; the GST setting is also configured here. Until this story is built, plans and the GST setting are changed by a database change.

**Related User Stories:**
- US-078: the plan catalog this console edits
- US-008, US-009: use the plan's price and validity when a seller chooses it
- US-053, US-054: the admin console, admin login and roles this story is part of
- US-083: every change is written to the audit trail
- US-064: plan upgrades use the plan prices

**Acceptance Criteria:**
- Given I am an admin with plan management permission
- When I open Plan Management
- Then I see all seller plans, active and inactive, with name, price, original price, validity, support level, badge, display order and features
- When I change a plan's price, original price, validity, features, support level, badge, name or order and save
- Then new listing purchases use the new values after the change is saved
- And listings that already chose or paid for the plan keep the price and validity that applied at the time
- When I set a plan's price to zero
- Then that plan is free and sellers who choose it are not asked to pay
- When I add a new plan
- Then it appears for sellers once I mark it active
- When I switch a plan off
- Then sellers no longer see it, and listings that already have it are unaffected
- And at least one plan always stays active
- When I open Tax Settings
- Then I can set whether prices include GST or GST is added on top, and the GST rate
- And sellers see the price breakdown according to that setting
- When another admin saved a change to the same plan after I opened it
- Then my save is refused with a message to reload
- When a change is saved
- Then it is written to the audit trail with who changed what, the old value and the new value

**Edge Cases:**
- A seller is in the middle of choosing or paying for a plan when its price changes (the order keeps the amount shown when the order was created)
- A price is set to zero while unpaid orders for that plan exist
- An admin tries to switch off the last active plan
- Original price lower than the price, or a negative price
- Very long or empty feature lines; feature text in Hindi
- A plan is renamed after listings used it
- Two admins editing at once
- The plan catalog is cached (a change must show to sellers within a few minutes at most, and the cache is cleared on save)

**Validation Rules:**
- Price is zero or more with 2 decimal places; original price is not lower than the price; validity is at least 1 day
- Plan code is unique and cannot be changed after it is created; plans cannot be deleted, only switched off
- At least one plan stays active at all times
- GST rate is between 0 and 28 percent; the tax mode is "prices include GST" or "GST added on top"
- Only admins with plan management permission can read or change plans (US-053 roles)
- Every change is audited (US-083)
- A change never alters amounts of orders already created or of listings already purchased

**Error Scenarios:**
- `ERROR_UNAUTHORIZED`: "You don't have permission for this action"
- `ERROR_PLAN_NOT_FOUND`: "Plan not found"
- `ERROR_PLAN_INVALID_PRICE`: "Enter a valid price"
- `ERROR_LAST_ACTIVE_PLAN`: "At least one plan must stay active"
- `ERROR_PLAN_CODE_EXISTS`: "A plan with this code already exists"
- `ERROR_CONCURRENT_EDIT`: "This plan was changed by someone else. Reload and try again"

**Backend Notes:**
- Admin endpoints under `/api/v1/admin/plans` and `/api/v1/admin/settings/tax`, protected by the admin roles of US-053; the seller catalog endpoint of US-078 reads the same data and its cache is cleared on every save
- Uses the `plans` table and the platform settings table created for US-078; plan changes use a version number to detect concurrent edits

**Web Notes:**
- Pages in the admin console (`valuex-web`): plans list, plan edit form with feature lines, tax settings page

**Open:**
- Plan and feature text in Hindi (whether the console stores translations)
- Scheduled price changes (an effective date) and time-limited promotional prices
- Whether tax settings are global or per plan

---

## Payment Gateway

### US-117: Payment Gateway Integration
**As a** platform  
**I want** one payment integration that creates payment orders, takes the payment in the app, confirms it from the gateway's signed callback, refunds, and reconciles  
**So that** listing plan payments, checkout and subscriptions all use one tested integration, and the gateway can be chosen or changed by configuration

**Design Note (2026-10-16):** The payment gateway has not been chosen yet (Razorpay is assumed in the architecture documents but is not decided). This story delivers a gateway-neutral integration: a payment port, a sandbox adapter for development and tests, the callback and refund handling, and the app's checkout wrapper. The real gateway adapter is added as soon as the gateway is chosen, without changing the stories that use payments. US-008 (listing plans) is the first user; US-021, US-022, US-035 and US-038 follow.

**Related User Stories:**
- US-008, US-009: listing plan payment, confirmation and refund after failed reviews
- US-021, US-022, US-075: buyer payment, retry
- US-035: refunds; US-038, US-042: subscriptions
- US-071: payment and transaction history
- US-091: payment lifecycle states
- US-083: audit trail
- US-109: screenshot protection on payment screens

**Acceptance Criteria:**
- Given a feature needs a payment (for example a listing plan)
- When it asks for one
- Then a payment record is created in the state `PAYMENT_INITIATED` with a gateway order, and the app receives what its checkout needs (order ID, amount, currency, the gateway's public key)
- When the user completes or cancels the checkout in the app
- Then the app reports only what the user did; it never marks a payment as successful
- When the gateway sends its signed callback
- Then the server verifies the signature, checks the amount, and moves the payment to success or failure
- And a repeated or late callback changes nothing
- And the callback is always acknowledged so the gateway does not keep retrying
- Given a callback never arrives
- Then a scheduled check asks the gateway about payments that are still pending and settles them
- Given a captured payment must be refunded (US-009, US-035)
- When a refund is requested, in full or in part
- Then the refund is sent to the gateway, tracked through the refund states, and its result is recorded
- Given the gateway is not configured or is a sandbox
- Then the sandbox adapter is used and no real money moves
- And with a real gateway, keys come from the environment and are never stored in the code or logs

**Edge Cases:**
- Callback arrives before the app returns from checkout
- The app reports success but no callback ever arrives (the scheduled check settles it)
- Callback amount differs from the order amount (rejected and flagged)
- Duplicate callbacks and replayed callbacks
- Gateway timeout or outage while creating an order (the feature gets a clear error and can retry)
- User closes the app during payment (the payment is settled by the callback)
- Gateway order expires unpaid
- Partial refund, refund failure, refund callback arriving twice
- Two payments for the same reference (listing plan) at once

**Validation Rules:**
- All amounts are decided by the server, in rupees with 2 decimals, and sent to the gateway in the smallest currency unit; the app can never set an amount
- Callbacks are trusted only after their signature check passes, using a constant-time comparison
- Card, UPI and bank details never reach ValueX servers or logs
- Secrets (keys, webhook secret) are read from the environment or secret store
- Payment records and attempts are never deleted and are kept for 7 years (US-071)
- Payment and refund states follow US-091
- The provider is selected by configuration; with no provider set, the sandbox adapter is used only in non-production profiles

**Error Scenarios:**
- `ERROR_GATEWAY_UNAVAILABLE`: "Payment service temporarily unavailable"
- `ERROR_PAYMENT_FAILED`: "Payment unsuccessful. Please try again"
- `ERROR_PAYMENT_TIMEOUT`: "Payment timed out. Please try again"
- `ERROR_DUPLICATE_PAYMENT`: absorbed silently for repeated callbacks
- `ERROR_REFUND_FAILED`: "Refund failed. Our team has been notified"

**Flutter Implementation Notes:**
- A payment checkout interface in the app with a sandbox implementation for development and a gateway implementation added when the gateway is chosen; features call the interface and do not know which gateway is used
- The interface returns completed, cancelled or failed as reported by the checkout; the app then asks the server for the real status
- Payment screens enable screenshot protection (US-109)

**Backend Notes:**
- A payment port (create order, fetch payment status, refund, verify and parse callbacks) with a sandbox adapter, in the existing `payment` module with its payment state machine
- Tables `payments` and `payment_attempts`, with idempotency columns for callbacks; one generic callback endpoint, with the signature header and format handled by the adapter
- Scheduled reconciliation of pending payments; the refund methods are used by US-009 and US-035

**Decisions (product owner, 2026-10-16):**
- The gateway is not decided; the integration is gateway-neutral and starts with the sandbox adapter

**Open:**
- Which gateway to use, its fees and its refund and settlement rules
- Payouts to sellers (US-072) are separate from this story
- Whether refunds for failed listing reviews are automatic or manual (US-084)

---

## End of User Stories Document

**Total User Stories:** 117  
**Coverage:** Full PRD_ValueX_v1.4 alignment + Flutter Implementation Notes  
**Version:** 3.16 (Updated 2026-10-16) — Added US-116 (Admin - Manage Seller Listing Plans and Tax Settings) and US-117 (Payment Gateway Integration); listing plans, features and prices are dynamic (US-008, US-078, US-009): Basic is paid at ₹49 with no free plan, prices include GST, and a plan set to zero is free. Version 3.15 (Updated 2026-10-16) — Added US-115 (Listing Lifecycle Notifications); plan validity starts at publication and a seller gets 3 review attempts, then a refund (US-008, US-009, US-078, US-084). Version 3.14 (Updated 2026-10-16) — Added US-114 (Listing Item Details Entry) from the Figma Make Item Details and Set Your Price screens; US-004 minimum raised to 2 photos; the Trust and Safety review (US-084) runs after plan payment and before publication. Version 3.13 (Updated 2026-10-15) — Design change: Sign Up no longer asks for an address or date of birth and gender is optional (US-001, US-003, US-088); an address is first saved when the user buys with home delivery (US-020) or posts an item to sell (US-004), with an optional name (Home, Office, custom); Home offers only "Use my current location" and "Use my saved location" and never enters or verifies an address (US-111, US-011, US-108); added the My Addresses placeholder (US-113) and the Account row in the Profile hub (US-103); US-012 and US-027 cross-reference the pickup address. Version 3.12 (Updated 2026-10-12) — Added US-112 (Seller Incoming Orders) from the Figma Make Profile > Incoming Orders screen; US-103, US-026, US-027, US-059 and US-090 cross-reference it. Product owner decisions on urgent, reject penalty, self-pickup and order reference recorded in US-112; US-111 scheduled in Sprint 3. Version 3.11 (2026-10-11) — US-101 Flutter Implementation Notes updated to the delivered Google sign-in, and the returning-user flow now applies the account-standing check. Version 3.10 (2026-10-10): US-107 Flutter Implementation Notes updated to the delivered mobile refresh behaviour. Version 3.9 (2026-10-09): US-106 Flutter Implementation Notes updated to the delivered mobile Sign In. Version 3.8 (2026-10-08): Added US-111 (Home Page). Version 3.7 (2026-10-07): Added US-110 (Registration UI Accessibility and Readability Review). Version 3.6 (2026-10-05): Added US-109 (Mobile App Security Hardening); US-001 amended (terms and consent at Sign Up, `SIGNUP_PENDING` state, Sign Up step with profile and address). Version 3.5 (2026-10-05): Added US-108 (Address Entry with Google Places Autocomplete and Address Verification). Version 3.4 (2026-08-12): Added US-106 (Mobile OTP Login for Returning Users) and US-107 (Access Token Refresh), gaps identified when tracing the backend's actual returning-user API flow

**Next Steps:**  
1. Product team to prioritize stories into sprints (see sprint-plan.md)
2. Technical team to estimate story points
3. Design team to create UI/UX flows
4. QA team to derive test cases from acceptance criteria
5. Review lifecycle state machine stories for implementation sequence

---

**Story Categories:**
- **MVP Core (US-001 to US-057):** 57 stories - Original core product functionality
- **Critical Additions (US-058 to US-059):** 2 stories - Order cancellation flows
- **Enhancement Backlog (US-060 to US-067):** 8 stories - Future improvements
- **PRD v1.3 New Features (US-068 to US-087):** 20 stories - Missing functional requirements
  - Direct buy flow, notifications, history views, preferences
  - Premium plan details with pricing
  - Admin features and monitoring
- **Lifecycle State Machines (US-088 to US-096):** 9 stories - State management
  - User, Listing, Order, Payment, Shipping, Return, Dispute, Ticket, Subscription
- **Compliance & Accessibility (US-097 to US-100):** 4 stories - GDPR, accessibility, analytics
- **Social Login (US-101 to US-102):** 2 stories - Google & Apple Sign-In
- **Profile Management Extensions (US-103 to US-105):** 3 stories - Gap-fill identified when auditing US-003: Profile Hub navigation tying together My Orders/Listings/Payments/Payouts/Notifications/Language/Support/Dispute, plus Logout and Account Security (mobile/email change, sessions, delete account entry point)
- **Authentication Extensions (US-106 to US-107):** 2 stories - Gap-fill identified when tracing the backend's returning-user API flow: mobile-OTP login (US-001 only covers first-time registration and blocks already-registered mobiles) and access-token refresh (refresh tokens are issued by every auth flow but no endpoint ever consumes one)
- **Address Management (US-108, US-113):** 2 stories - US-108: address entry with Google Places Autocomplete and a dedicated address verification API, used at checkout and when posting a listing (Sign Up and Home do not ask for an address); US-113: My Addresses placeholder to be detailed by the product owner
- **Mobile App Security (US-109):** 1 story - SSL pinning, root and jailbreak detection, device ID (CODING_STANDARDS 3.7)
- **UI Quality (US-110):** 1 story - Contrast, touch target, text size and screen reader fixes for the registration screens, and the design system rules for later screens
- **Home (US-111):** 1 story - Home page: location header, search with photo search, promo card, category browsing, featured deals near you and bottom navigation
- **Seller Order Management (US-112):** 1 story - Seller's Incoming Orders list reached from the Profile hub: orders grouped as New, Packing, Scheduled and Shipped, with Start Packing, Reject, Continue Packing, Schedule Pickup and View Schedule
- **Listing Details (US-114):** 1 story - One Item Details page for title, category, condition, description, location and price, filled by AI when it is enabled and by the seller otherwise
- **Listing Notifications (US-115):** 1 story - Notifications for the listing lifecycle after payment: under review, published, needs changes, final rejection, refund, payment failed, expired and removed, in English and Hindi
- **Plan Administration (US-116):** 1 story - Admin console pages to create, change and switch off seller listing plans (prices, features, validity) and to set the GST setting
- **Payment Gateway (US-117):** 1 story - Gateway-neutral payment integration: payment orders, signed callbacks, refunds, reconciliation and the app checkout wrapper, with a sandbox adapter until the gateway is chosen

---

**PRD v1.3 Coverage Summary:**
- ✅ All 59 Functional Requirements (FR-1 to FR-59) now have corresponding user stories
- ✅ All Lifecycle State Machines from Section 18 covered
- ✅ Premium Plans pricing and features from Section 17 detailed
- ✅ Admin Analytics from Section 15 addressed
- ✅ WhatsApp notifications from Section 13 included
- ✅ Non-functional requirements (accessibility, compliance) covered

**Notes:**
- Premium plan pricing: Basic (Free), Smart (₹49/mo), Vision (₹149/mo) - discounted rates
- Listing plan pricing: Basic (₹49), Boosted (₹149), Priority (₹249) - discounted rates
- Third-party service integrations (Aadhaar, payment gateway, logistics) are provider-agnostic
- Auto-release timeouts: 7 days for payment, 30 days for video deletion, 48 hours for negotiations
- All monetary values aligned with PRD v1.3
- State machine transitions require careful implementation to maintain data consistency
- Lifecycle states should be implemented with audit logging for compliance
- API endpoint specifications to be detailed in technical design docs
