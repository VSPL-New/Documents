# ValueX User Stories

**Version:** 1.0  
**Based on:** PRD_ValueX_v1.1.md, ValueX_User_Flow_diagram_ver0.2.png  
**Date:** 2026-05-14

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

---

## User Management & Authentication

### US-001: User Registration with Aadhaar Verification
**As a** new user  
**I want to** register using my Aadhaar  
**So that** I can access the platform securely with verified identity

**Acceptance Criteria:**
- Given I am on the registration page
- When I enter my mobile number
- Then I receive an OTP for mobile verification
- And after OTP validation, I am prompted for Aadhaar verification
- When I complete Aadhaar verification via third-party service
- Then my account is created successfully
- And I am assigned a unique user ID
- And my verified identity is stored securely

**Edge Cases:**
- User already registered with same Aadhaar
- Aadhaar verification fails (invalid, expired, or API timeout)
- Mobile number already linked to another account
- User cancels Aadhaar verification mid-flow
- Network interruption during verification
- Third-party service downtime

**Validation Rules:**
- Mobile number must be 10 digits
- Mobile number must be unique per account
- Aadhaar must be valid 12-digit number
- One Aadhaar can link to only one account
- User must accept terms & conditions
- User must provide consent for data processing

**Error Scenarios:**
- `ERROR_MOBILE_ALREADY_REGISTERED`: "This mobile number is already registered"
- `ERROR_AADHAAR_ALREADY_USED`: "This Aadhaar is already linked to an account"
- `ERROR_AADHAAR_VERIFICATION_FAILED`: "Unable to verify Aadhaar. Please try again"
- `ERROR_AADHAAR_SERVICE_UNAVAILABLE`: "Verification service temporarily unavailable"
- `ERROR_INVALID_OTP`: "Invalid or expired OTP"

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

**Acceptance Criteria:**
- Given I am logged in
- When I navigate to my profile
- Then I can view my profile details (name, photo, location, ratings, joined date)
- When I update my profile photo, display name, or location
- Then changes are saved successfully
- And other users see updated information

**Edge Cases:**
- User uploads inappropriate profile image
- User tries to change verified Aadhaar name
- User leaves required fields empty
- Profile photo exceeds size limit
- User updates location outside India

**Validation Rules:**
- Profile photo max size: 5MB
- Allowed formats: JPG, PNG
- Display name: 3-50 characters, no special symbols
- Location must be valid Indian city/state
- Aadhaar-verified name cannot be edited

**Error Scenarios:**
- `ERROR_PHOTO_TOO_LARGE`: "Profile photo must be less than 5MB"
- `ERROR_INVALID_FORMAT`: "Only JPG and PNG formats allowed"
- `ERROR_INAPPROPRIATE_CONTENT`: "Content violates community guidelines"

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

---

### US-044: Multi-Language Support
**As a** user  
**I want to** use the app in my preferred language  
**So that** I can understand content easily

**Acceptance Criteria:**
- Given I am in app settings
- When I tap "Language"
- Then I see list of supported languages (e.g., English, Hindi, Tamil, Telugu, Bengali, etc.)
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

---

## End of User Stories Document

**Total User Stories:** 67 (57 MVP + 2 Critical + 8 Enhancement)  
**Coverage:** All functional requirements + identified gaps  
**Version:** 1.1 (Updated 2026-05-21)

**Next Steps:**  
1. Product team to prioritize stories into sprints (see sprint-plan.md)
2. Technical team to estimate story points
3. Design team to create UI/UX flows
4. QA team to derive test cases from acceptance criteria

---

**Story Categories:**
- **MVP (US-001 to US-057):** 57 stories - Core product functionality
- **Critical Additions (US-058 to US-059):** 2 stories - Order cancellation flows
- **Enhancement Backlog (US-060 to US-067):** 8 stories - Future improvements

**Notes:**
- Premium feature plan details (bundled features, pricing) are TBD - stories written generically
- Third-party service integrations (Aadhaar, payment gateway, logistics) are provider-agnostic
- Auto-release timeouts (7 days for payment, 1 month for video deletion) are configurable
- All monetary values to be confirmed by finance team
- API endpoint specifications to be detailed in technical design docs
