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

---

## User Management & Authentication

### US-001: User Registration via Mobile OTP, Email Verification, and Aadhaar
**As a** new user  
**I want to** register by verifying my mobile number and email address  
**So that** I can access the platform with a trusted identity

**Registration Flow:**
1. Verify mobile (SMS OTP) → account: `EMAIL_VERIFICATION_PENDING`
2. Verify email (email OTP) → account: `IDENTITY_VERIFICATION_PENDING`
3a. Complete Aadhaar verification → account: `ACTIVE` (`aadhaarVerified = true`)
3b. Skip Aadhaar → account: `ACTIVE` (`aadhaarVerified = false`, limited until Aadhaar done)

**Acceptance Criteria:**
- Given I am on the registration page
- When I enter my mobile number and accept terms & conditions
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
- And after successful Aadhaar OTP verification, my account transitions to `ACTIVE` with `aadhaarVerified = true`
- When I choose to skip Aadhaar verification
- Then I receive a new JWT and my account transitions to `ACTIVE`
- And I can browse and use most platform features
- But I must complete Aadhaar verification before my first buy or sell transaction

**Edge Cases:**
- Mobile number already linked to another account
- Email address already linked to another account
- User enters email OTP before mobile OTP is verified
- User cancels Aadhaar verification mid-flow
- Aadhaar verification fails (invalid, expired, or API timeout)
- User already registered with same Aadhaar (from a different account)
- Network interruption during any OTP or Aadhaar verification step
- Third-party Aadhaar service downtime
- User requests OTP too many times on mobile or email (rate limiting applies)

**Validation Rules:**
- Mobile number must be 10 digits, Indian format; unique per account
- Mobile OTP is 6 digits, expires after 5 minutes
- Email must be a valid format; unique per account
- Email OTP is 6 digits, expires after 5 minutes
- Maximum 3 OTP send requests per mobile or email per 10 minutes
- Maximum 5 failed OTP attempts per channel before 10-minute cooldown
- Email verification must be completed before Aadhaar verification can begin
- Aadhaar must be valid 12-digit number (when provided)
- One Aadhaar can link to only one account across all states
- User must accept terms & conditions and provide consent for data processing

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
- Profile fields here (avatar, display name, location) are surfaced from the Profile Hub: US-103
- Account security (mobile/email change, sessions, delete account): US-105
- Logout: US-104

**Design Note (v3.3):** Users do **not** upload a free-form profile photo. Instead they pick an **avatar** from a fixed catalog of avatar images the frontend app ships/renders — this removes the need for image content moderation entirely (no user-supplied image ever reaches the platform for a profile picture). The backend owns the canonical list of valid avatar IDs and only stores which one is selected.

**Acceptance Criteria:**
- Given I am logged in
- When I navigate to my profile
- Then I can view my profile details (avatar, display name, location, ratings, joined date)
- When I open the avatar picker
- Then I see the full catalog of available avatars
- When I select an avatar and confirm
- Then my profile updates to show the selected avatar
- When I update my display name or location
- Then changes are saved successfully
- And other users see updated information
- Given I have never picked an avatar
- When I view my profile
- Then a default avatar is shown

**Edge Cases:**
- User selects an avatar ID that isn't in the current catalog (stale client-side list, tampered request)
- User tries to change verified Aadhaar name
- User submits an empty/blank display name or city on update
- User updates location outside India
- Avatar catalog changes (avatar removed) after a user already selected it — existing selection remains valid until the user picks a new one

**Validation Rules:**
- Avatar selection must be one of the platform's published avatar catalog IDs
- Every account has a default avatar from account creation, before any explicit selection
- Display name: 3-50 characters, no special symbols
- Location must be valid Indian city/state
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
- When I capture at least 1 photo (max 10 photos)
- Then photos are uploaded to the system
- And I can proceed to add item details

**Edge Cases:**
- User denies camera permission
- Camera fails to open
- User tries to upload more than 10 photos
- Photo quality is very poor
- User uploads non-item photos (random images)
- Network failure during photo upload

**Validation Rules:**
- Minimum 1 photo required
- Maximum 10 photos allowed
- Photo format: JPG, PNG, HEIC
- Max size per photo: 10MB
- Minimum resolution: 480x480px

**Error Scenarios:**
- `ERROR_CAMERA_PERMISSION_DENIED`: "Camera access required to capture photos"
- `ERROR_MAX_PHOTOS_EXCEEDED`: "Maximum 10 photos allowed"
- `ERROR_PHOTO_UPLOAD_FAILED`: "Failed to upload photo. Check your connection"
- `ERROR_INVALID_PHOTO`: "Photo quality too low or invalid format"

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
- Then I am shown 3 listing plan options with features:
  - **Basic** (Free): Standard visibility, limited inquiries
  - **Boosted** (Paid): Higher ranking for 7 days, increased visibility
  - **Priority** (Paid): Top placement for 30 days, "Featured" badge, verified
- When I select a plan
- Then I see the pricing
- When I select a paid plan
- Then I am redirected to payment
- When payment succeeds
- Then listing is published with selected plan features

**Edge Cases:**
- Seller cancels payment
- Payment fails
- Seller selects plan but closes app before payment
- Seller wants to upgrade existing listing
- Plan duration expires while listing is active

**Validation Rules:**
- Draft must be complete before plan selection
- Free plan has no payment requirement
- Paid plans require successful payment before publishing
- Plan duration starts from successful payment
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
- Given I have selected a paid listing plan
- When payment is successful
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

**Validation Rules:**
- Payment must be confirmed before publishing
- Listing status: Draft → Processing → Published
- Rollback to draft if publish fails after payment (with refund)
- Plan activation within 5 minutes of payment

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
- Distance-based ranking if location enabled
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
  - Seller name, rating, location, joined date
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
- And system creates separate escrows per item

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
- Delivery option card with Google Maps address picker
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
- And order is created
- And seller is notified to ship
- And I receive order confirmation

**Edge Cases:**
- Payment gateway timeout
- Payment fails after deduction
- Partial payment success (multi-item cart)
- User closes app during payment
- Duplicate payment attempt

**Validation Rules:**
- Payment amount must match order total
- Escrow created per item (not combined)
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
- Multiple items from same seller shipped separately
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
  - Pickup address
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
- Buyer cancels multi-item order (partial vs. full cancellation)
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
- Multi-item orders display

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

**Acceptance Criteria:**
- Given I am creating a listing
- When I reach plan selection step
- Then I see three plan options with clear comparison:
  
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
- Then I see payment breakdown before confirming
- When payment succeeds
- Then selected plan features activate immediately

**Edge Cases:**
- User wants to upgrade mid-validity (handled in US-064)
- Plan expires before item sells
- User wants refund for unused plan period
- Multiple items with different plans

**Validation Rules:**
- Validity starts from successful payment
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
- Given a seller completes listing creation
- When seller submits for publication
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
- And can revise and resubmit

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
- Appeals reviewed by senior moderator

**Error Scenarios:**
- `LISTING_UNDER_REVIEW`: "Your listing is under review. You'll be notified within 24 hours"
- `LISTING_REJECTED`: "Listing rejected: [specific reason]. Revise and resubmit"
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
  - ACTIVE: Fully verified, can transact
  - UNDER_REVIEW: Flagged for investigation
  - RESTRICTED: Limited access during review
  - SUSPENDED: Temporarily banned (7 days)
  - BANNED: Permanently banned
  - CLOSED: User-requested account deletion
- State transitions:
  - NEW → OTP_PENDING → IDENTITY_VERIFICATION_PENDING → ACTIVE
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

**Validation Rules:**
- State transitions sequential
- Cannot skip states (except exceptions like CANCELLED)
- Both parties notified at key states
- Timestamps recorded for SLA tracking

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
- Use `google_sign_in` Flutter package
- Send `idToken` from Google to backend — backend validates, never trust client-side verification
- On success show standard home screen; on new account show mobile verification screen

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
  - **Activity**: My Orders, My Listings, Saved Items, Offers/Negotiations
  - **Payments**: Payment & Transaction History, Payout Settings (sellers only)
  - **Preferences**: Notification Preferences, Language
  - **Support**: Help & Support, Raise Dispute, My Support Tickets
  - **Account**: Edit Profile, Account Security, Privacy Settings, Logout
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
- Logout requires confirmation dialog (see US-104)

**Error Scenarios:**
- `ERROR_SECTION_UNAVAILABLE`: "This section is temporarily unavailable"

**Related User Stories:**
- Profile summary fields: US-003
- Activity: My Orders → US-023, US-070; My Listings → US-010, US-067, US-064; Saved Items → US-073; Offers → US-076
- Payments: US-071 (transaction history), US-072 (payout settings)
- Preferences: US-087 (notifications), US-044 (language)
- Support: US-043, US-045, US-046 (help & support), US-047 (raise dispute), US-074 (ticket status)
- Account: US-105 (account security), US-063 / US-098 (delete account), US-104 (logout)

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

## End of User Stories Document

**Total User Stories:** 105  
**Coverage:** Full PRD_ValueX_v1.4 alignment + Flutter Implementation Notes  
**Version:** 3.3 (Updated 2026-08-07) — US-003 redesigned: avatar selection replaces free-form profile photo upload

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
