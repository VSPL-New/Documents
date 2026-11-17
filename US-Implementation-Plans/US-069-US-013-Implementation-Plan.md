# US-069 + US-013: Buyer Contact and Chat with Seller - Implementation Plan

Planned as **one story** (user decision G1, 2026-11-16): US-069 (contact entry point, 3 SP) and US-013 (chat, 8 SP).

## 1. Header

| Field | Value |
|---|---|
| Stories | US-069 - Buyer Initiates Contact from Listing; US-013 - Chat with Seller |
| Sprint | Sprint 4 - Communication & Negotiation |
| Story points | 11 (3 + 8; Sprint plan and LLD Parts D and E) |
| Repos involved | valuex-backend (contact guard, attempt log, eligibility, capabilities, chat module, screening, notifications) and valuex-mobile (action bar, Chats tab, chat list and thread screens). No `valuex-ai`, infra or `valuex-web` change. |
| Dependencies | Met: US-012 (listing details and `capabilities`), US-132 (block and report; merged 2026-11-16, PRs #66, #76, #286), US-077 (notification dispatcher). **Not built:** US-130 (realtime gateway) and US-131 (push). Chat ships without them, see decision G10. Make Offer waits for US-017. |
| Date | 2026-11-16 |
| Design source | [Sprint 4 LLD](../LLD/Sprint-4-Communication-Negotiation-LLD.md) Part D (D.1 to D.10), Part E (E.1 to E.10), A.7 (polling fallback), sections 1.3, 1.5, 1.6, 1.7, 8.2, decisions D4, D9, D13, D15, D16 and conflict C14. |
| Branches (proposal) | `feature/US-069-US-013-contact-and-chat` in `valuex-backend` and `valuex-mobile`, cut from current `main`. Documents on `docs/US-069-US-013-contact-and-chat` (already cut). |
| Flyway numbers | `main` is at V32. `V33__contact_attempts.sql` (contact log and settings seeds) and `V34__chat.sql` (chat tables). The LLD's single provisional `V34__chat_and_contact.sql` is split in two (G3). |

## 2. Story Recap

### US-069 - Buyer Initiates Contact from Listing

**As a** buyer **I want to** easily contact the seller from the listing page **so that** I can inquire about the item.

| ID | Behaviour (user-stories.md, with the 2026-11-15 update) |
|---|---|
| AC1 | On a listing I see the communication options (Chat, Call, Video Call; Make Offer per LLD D.7) and can tap one to initiate contact. |
| AC2 | Tapping **Chat** opens the chat window with the listing context pre-loaded. |
| AC3 | **Call** and **Video Call** are app-to-app calls and stay "Coming soon" (disabled) until a call provider is chosen and `valuex.calls.enabled` is turned on (decision D4). |

**Edge cases:** seller offline or unavailable; buyer not verified or not active; seller has blocked the buyer; many contact attempts in a short time.
**Validation rules:** contact options only for signed-in users; listing context auto-included in the first chat message; the system logs all contact attempts.
**Errors:** `ERROR_SELLER_UNAVAILABLE`, `ERROR_BLOCKED` ("You cannot contact this seller"), `WARNING_RATE_LIMIT` ("Too many contact attempts. Try again later"); `ERROR_LOGIN_REQUIRED` is the standard 401 (conflict C14). The LLD adds `ERROR_ACCOUNT_NOT_ACTIVE` (403), `ERROR_OWN_LISTING` (409) and the existing `ERROR_LISTING_NOT_AVAILABLE` (404).

### US-013 - Chat with Seller

**As a** buyer **I want to** chat with the seller **so that** I can ask questions about the item.

| ID | Behaviour |
|---|---|
| AC4 | Tap "Chat" on a listing: the chat window opens. |
| AC5 | I type and send a message: the seller receives a notification. |
| AC6 | The seller replies: I receive a notification and see the message in the chat. |
| AC7 | All messages are stored persistently. |
| AC8 | Opening the chat history shows all previous conversations with timestamps. |

**Edge cases:** seller does not respond; spam or inappropriate messages; listing deleted after the chat started; network interruption during chat; user blocks the seller.
**Validation rules:** message at most 2000 characters; image sharing up to 5 MB; history kept 6 months after closure; profanity filter; suspicious patterns (spam, harassment) flagged.
**Errors:** `ERROR_MESSAGE_TOO_LONG` ("Message exceeds 2000 characters"), `ERROR_SELLER_UNAVAILABLE`, `WARNING_CONTENT_FLAGGED` with the D13 block, "Deliver message" and policy-agreement flow (a message with restricted terms is not delivered unless the sender agrees; an overridden message is flagged and reported at once).

## 3. Design Reference

LLD Part D (contact: D.3 to D.9) and Part E (chat: E.3 data model, E.4 API, E.5 backend design, E.7 mobile, E.8 rules and codes, E.9 NFR, E.10 tests); A.7 (polling fallback); 1.5 (properties), 1.6 (`CommunicationSetting`), 1.7 (migrations), 8.2 (errors).

### Key design decisions

- **One guard for every contact path.** `ContactGuard.require(channel, callerId, listingId)` checks in order: caller `ACTIVE`, listing live, caller is not the owner, seller `ACTIVE`, not blocked either way (`BlockService.requireNotBlocked`, US-132), then the rate limits. `ChatService.openThread` is its first caller; call and offer services will reuse it.
- **Every attempt is logged.** `ContactAttemptService.record` runs in `REQUIRES_NEW`; the table holds ids, channel and outcome only, never text.
- **Capabilities become per caller.** `ContactEligibilityService` applies the D.4 rule table. A block and a suspended seller both give `UNAVAILABLE`, so a block is never revealed. **Chat is now real** (`available` for an eligible buyer); **Make Offer stays `COMING_SOON` until US-017**; **Call and Video stay `COMING_SOON`** while `valuex.calls.enabled=false`.
- **Threads and messages.** One thread per `(listing, buyer)`, a snapshot of title and price, a per-thread `seq` assigned under a row lock, delivered and read as cursors (no row per message), unread counts stored on the thread. `clientMessageId` makes a retry idempotent.
- **Restricted terms (D13).** Blocked-term hit: `422 WARNING_CONTENT_FLAGGED` with the matched ranges and `agreementVersion`, nothing stored. Retry with `policyAgreement` delivers it flagged `BLOCKED_TERM_OVERRIDE`, creates a SYSTEM report at once, and is limited by `CHAT_POLICY_OVERRIDES_PER_DAY`. Contact details, links, off-platform payment words and repeats are flagged but delivered; `CHAT_AUTO_REPORT_FLAGS` flags in 24 hours raise a SYSTEM report.
- **Images.** Media API with purpose `CHAT_IMAGE`, then a sanitised JPEG copy (no EXIF) through `ImageVariantProcessor`; only the copy is delivered, through 10-minute signed links.
- **Plain text everywhere.** Message text is cleaned with `PlainText`, never logged, never in a notification, push or metric label.
- **Delivery without US-130 and US-131 (G10).** The app polls every 15 seconds while a chat screen is visible (the A.7 fallback), marks delivered and read through REST, and the seller gets an in-app notification through the existing `NotificationDispatcher` (coalesced). No WebSocket, typing indicator or push until those stories land; their hooks (`ChatMessageCreatedEvent`) are published so they plug in without changing chat.
- **Settings are Admin-managed** through the `CommunicationSetting` registry started in US-132.

### Design source (chat screens, supplied 2026-11-17)

Two screenshots (Messages list, chat thread) are the **visual reference only**; they are built in Flutter within `Flutter-Design-System.md`, with tokens mapped from the design system, not measured from the images. They show: a bold "Messages" title and rounded search field; list rows with a rounded-square gradient initial avatar, name, relative time, listing title, last-message preview and a blue unread count; a thread header (back, circular avatar, name, listing title as subtitle, round phone and video buttons); an info pill; white received bubbles and blue-to-purple gradient sent bubbles with the time inside; a rounded composer and gradient send button (disabled look while empty).

Decisions on the differences from LLD E.7 (user, 2026-11-17):

| # | Decision |
|---|---|
| 1 | Call and Video buttons in the thread header are shown **disabled with a "Coming soon" message** (calls on hold, D4); they follow `valuex.calls.enabled`. |
| 2 | The info pill uses the design's style with the plan's safety wording (keep chats and payments on JustQlic; do not share OTPs or bank details), **not** the "escrow-protected on ValueX" text; the escrow claim is not backed by the current scope (D10) and would need product and legal sign-off. |
| 3 | **No online dot** on the list until presence exists (US-130). |
| 4 | A **client-side search** on the chats list filters the loaded threads by counterpart name and listing title only; message text is never searched or indexed. |
| 5 | The All, Buying and Selling chips stay, in a compact row under the search field (the design has none; sellers need them). |
| 6 | The listing title is the header subtitle and opens the listing on tap; the separate `listing_header` card is dropped and the `LISTING_CONTEXT` card stays as the first message. |
| 7 | Sent, Delivered and Read status is drawn small in the time row of own bubbles. |
| 8 | An attach icon sits inside the composer field (the design has none; image sharing is required). |
| 9 | The existing bottom navigation is kept; only the Chats unread dot changes. |
| 10 | Own bubbles use the design-system gradient if one exists; the time text on it must pass the contrast test (more opaque white than in the screenshot). |

Not in the designs and built from the design system: blocked-message sheet, agreement dialog, read-only banner, image bubbles, retry state, date separators, empty and error states, avatar initials only (no photo is returned by the API).

### Verified implementation anchors (checked against `origin/main` on 2026-11-16)

| Area | Finding and consequence |
|---|---|
| Capabilities today | `PublicListingService.capabilities(realEstate, own)` is static: `OWN_LISTING` for the owner, otherwise chat, call and video `COMING_SOON`. The `Capabilities` record has no `offer` member and no `contact` block; `Capability.reason` is a free string. D.4's additive change is needed. |
| `communication` module | Holds `BlockService`, `ReportService`, `ReportTargetResolver` (USER only), a no-op `CommunicationHoldPort`, `ParticipantDirectoryPort` (adapter in `auth.infrastructure.communication`) and the repositories. Guard, eligibility, attempt log and chat services go in `communication/application/service`. |
| Settings | `CommunicationSetting` has only `REPORTS_PER_DAY`; this story adds the keys of section 4. |
| Rate limit pattern | `RedisCacheService.checkRateLimit(key, max, window)` and `RateLimitedException`, as in `ReportService`; a Redis failure allows the request with a warning. |
| Errors | `ForbiddenException` 403, `ConflictException` 409, `NotFoundException` 404, `RateLimitedException` 429; `ValidationException` and `BusinessException` map to 400 and **there is no 422 handler**, so the 422 codes of E.8 need a small exception (G11). `ERROR_LISTING_NOT_AVAILABLE` is package-private in `PublicListingService` and must be shared. New codes: `ERROR_ACCOUNT_NOT_ACTIVE`, `ERROR_OWN_LISTING`, `ERROR_SELLER_UNAVAILABLE`, `WARNING_RATE_LIMIT`, chat codes of E.8. |
| Notifications | `NotificationDispatcher.dispatch(NotificationDispatchRequest)` supports `dedupeKey` (duplicate ignored). Channels are IN_APP, SMS, EMAIL only (push is US-131). |
| Media | `MediaPurpose` has no `CHAT_IMAGE`; `MediaAssetService` special-cases `LISTING_IMAGE` (lines ~234, ~305), `media_purpose` is a plain `VARCHAR(50)` (no CHECK). `ImageVariantProcessor.process(input, contentType, specs, outputDir)` takes `VariantSpec(MediaVariantType, maxSide)`; variants are THUMBNAIL, CARD, DETAIL (1200 px by config) and ZOOM; the processing job is limited to `LISTING_IMAGE`. The 1600 px sanitised copy of E.4 needs its own spec (G12). |
| Listing helpers | `ListingPhotoLinkPort` (thumbnails) and `ListingEligibilityFilter.liveAmong` exist for the thread list. `ListingEngagement.chats()` returns 0 and can now read the thread count. |
| Mobile | `ListingActions` draws Chat, Call, Video, Add to Cart and Buy Now from `Capabilities`; an available action only calls `onUnbuilt`. `BottomNavItem.chats` is in `core/widgets/brand_bottom_nav.dart` with `chatsHasUnread`, still hard-coded `true` in `home_screen.dart` (line ~74) and `search_screen.dart` (line ~177); `main_nav.dart` (line ~41) handles the Chats tab. `image_picker` ^1.2.4 is already in `pubspec.yaml`; there is no `features/chat/`, no realtime client and no `web_socket_channel`. |
| Reusable safety UI | `features/communication_safety/` (`confirmBlockUser`, `showReportSheet`, `UserSafetyMenu`) from US-132 backs the thread's overflow menu. |

## 4. Implementation Steps

### Database
- [ ] `V33__contact_attempts.sql`: `contact_attempts` with the CHECKs and three indexes of LLD D.3, plus seeds (`ON CONFLICT DO NOTHING`) for `CONTACT_ATTEMPTS_PER_PAIR_PER_HOUR` 10, `CALL_ATTEMPTS_PER_PAIR_PER_HOUR` 3, `CHAT_NEW_THREADS_PER_DAY` 20, `CONTACT_ATTEMPT_RETENTION_DAYS` 180.
- [ ] `V34__chat.sql`: `chat_threads` and `chat_messages` exactly as LLD E.3 (unique `(listing_id, buyer_id)`, `uq_chat_messages_seq`, `uq_chat_messages_client`, the CHECKs, the indexes), plus seeds for `CHAT_MESSAGE_MAX_CHARS` 2000, `CHAT_IMAGE_MAX_MB` 5, `CHAT_MESSAGES_PER_MIN` 30, `CHAT_POLICY_OVERRIDES_PER_DAY` 5, `CHAT_NOTIFY_COALESCE_MINUTES` 10, `CHAT_AUTO_REPORT_FLAGS` 3, `CHAT_PAGE_SIZE` 30 (ranges per LLD 1.6). The retention columns (`closed_at`, `purge_after`, `legal_hold`) are created but unused until US-016.

### Backend - contact (US-069)
- [ ] `CommunicationSetting`: add the four contact keys and the seven chat keys; extend `CommunicationSettingTest`.
- [ ] `communication/domain`: `ContactChannel` (CHAT, CALL, VIDEO, OFFER, BUY_NOW), `ContactOutcome` (ALLOWED, BLOCKED, RATE_LIMITED, SELLER_UNAVAILABLE, NOT_ELIGIBLE).
- [ ] `ContactAttemptRepository` and `ContactAttemptService.record` (`REQUIRES_NEW`, counter `contact.attempts{channel,outcome}`).
- [ ] `ContactListingPort` (defined in communication, implemented in the listing module): live, owner id, negotiable, price, real estate, without reading listing tables from communication.
- [ ] `ContactGuard.require(...)` in the LLD order with `ERROR_ACCOUNT_NOT_ACTIVE`, `ERROR_LISTING_NOT_AVAILABLE`, `ERROR_OWN_LISTING`, `ERROR_SELLER_UNAVAILABLE`, `ERROR_BLOCKED`, `WARNING_RATE_LIMIT`; records the outcome of the first failing check; Redis failure allows with a warning; a `newThread` variant applies `CHAT_NEW_THREADS_PER_DAY`. The call-reachability check is not wired (calls on hold, G7).
- [ ] `ContactEligibilityService.capabilities(callerId, listing)` per D.4. `Capabilities` gains `offer` (always `COMING_SOON` until US-017) and a `contact` block `{threadId, negotiationId}`: `threadId` filled when the caller already has a thread, `negotiationId` null until US-017. Reasons `UNAVAILABLE`, `NOT_NEGOTIABLE`, `IDENTITY_REQUIRED` added; `DISABLED_BY_SELLER` is **not** implemented (G6; see Cleanup).
- [ ] `valuex.calls.enabled=false` in `ValuexProperties` and the yml files.
- [ ] `ContactCapabilityPort` in the listing module, implemented by `ContactEligibilityService`, composed by `PublicListingService`. `ERROR_LISTING_NOT_AVAILABLE` becomes a shared constant.
- [ ] `ContactAttemptRetentionJob` (daily, deletes rows older than `CONTACT_ATTEMPT_RETENTION_DAYS`).

### Backend - chat (US-013)
- [ ] `MediaPurpose.CHAT_IMAGE` (private, owner = sender, signed links only); allow it in `MediaAssetService` authorisation and exclude it from listing-photo processing; a sanitising step through `ImageVariantProcessor` (1600 px JPEG, no EXIF), original deleted after the copy (G12).
- [ ] Entities and repositories `ChatThread`, `ChatMessage` (`communication/domain`, `infrastructure/persistence`); locked read of the thread (`FOR UPDATE`); keyset queries by `seq`.
- [ ] `ChatService.openThread(callerId, listingId)`: guard, find or insert with the listing snapshot and a `LISTING_CONTEXT` system message at `seq = 1` (`ON CONFLICT DO NOTHING` then re-select); 201 new, 200 existing.
- [ ] `ChatService.send(...)` in the LLD E.5 order: per-user rate limit, lock, participant check (404), `canSend` (`ERROR_BLOCKED`, `ERROR_SELLER_UNAVAILABLE`, `ERROR_THREAD_READ_ONLY`), validation (`ERROR_EMPTY_MESSAGE`, `ERROR_MESSAGE_TOO_LONG` by code points, image rules), idempotency, screening, `seq` assignment, thread update, `ChatMessageCreatedEvent` after commit.
- [ ] `MessageScreeningService` with `communication/blocked-terms-en.txt` and `-hi.txt` resources (normalisation: lower-case, accent folding, small leetspeak map), flag rules (`CONTACT_INFO`, `EXTERNAL_LINK`, `OFF_PLATFORM_PAYMENT`, `REPEATED`), Redis counter and the auto SYSTEM report at `CHAT_AUTO_REPORT_FLAGS`; D13 block, override and `ERROR_POLICY_AGREEMENT_OUTDATED`; overrides rate limited by `CHAT_POLICY_OVERRIDES_PER_DAY`; the agreement version constant `policy-override-v1`. The starter word lists are placeholders for Trust & Safety (G13).
- [ ] `markDelivered` and `markRead` (clamped, forward-only cursors, unread recompute), history (`beforeSeq`, `afterSeq`, `limit`), thread list by `role` with thumbnails (`ListingPhotoLinkPort`) and `available` (`ListingEligibilityFilter.liveAmong`), `GET /chats/unread-count`, signed image links.
- [ ] `ChatController` with the eight endpoints of E.4 (all authenticated; non-participant gets 404) and DTOs.
- [ ] `ChatMessageListener` (AFTER_COMMIT, async): in-app `CHAT_MESSAGE` notification through `NotificationDispatcher`, dedupe key `chat:{threadId}:{recipientId}:{bucket}` per `CHAT_NOTIFY_COALESCE_MINUTES`, title "New message from {displayName}", body "Open JustQlic to read it"; failures logged and never reach the sender. No realtime or push call yet (G10).
- [ ] Block handling: listener for `UserBlockedEvent` and `UserUnblockedEvent` so `canSend` reflects the block (read-only for both); history stays visible.
- [ ] Safety integration: `ReportTargetResolver` for THREAD and MESSAGE (reporting a chat from the thread menu); the real `CommunicationHoldPort` stays a no-op (US-016).
- [ ] `ListingEngagement.chats()` returns the thread count of the listing.
- [ ] Metrics `chat.messages.sent{type}`, `chat.messages.refused{reason}`, `chat.messages.flagged{reason}`, `chat.messages.overridden`, `chat.send.latency`; no user content in logs or labels.

### Mobile (`valuex-mobile`)
- [ ] `Capabilities` parses `offer` and `contact`; `CapabilityReason` gains `unavailable`, `notNegotiable`, `identityRequired`; unknown values map to `other`.
- [ ] `ListingActions`: Make Offer control added ahead of Add to Cart and Buy Now (disabled "Coming soon"); Chat opens the thread (calls `POST /chats`, then `/chats/:threadId`) with a double-tap guard; "Open chat" label when `contact.threadId` is set; `IDENTITY_REQUIRED` goes to the existing Aadhaar entry; reasons spoken. Layout and large-text behaviour unchanged.
- [ ] `features/chat/`: `data/chat_repository.dart`, `domain/` (`ChatThread`, `ChatMessage`, `MessageStatus`, `ChatFlag`), providers `chat_list_controller`, `chat_thread_controller`, `chat_unread_provider` (Riverpod, generated, as in `saved_listings`).
- [ ] `chat_list_screen.dart` (design source: Messages screenshot): "Messages" title, client-side search by counterpart name and listing title, All, Buying, Selling chips, rows with a rounded-square gradient initial avatar, name, relative time, listing title, preview, unread chip and Buying or Selling tag; no online dot; pull to refresh; empty and error states.
- [ ] `chat_thread_screen.dart` (design source: thread screenshot) and widgets `message_bubble` (white received, gradient sent, time inside, small Sent, Delivered, Read status on own), `system_card` (listing context; offer and call cards are rendered as a neutral fallback until Parts I, F, G), `composer` (rounded field with attach icon inside, counter, image attach with 1600 px client resize, gradient Send that looks disabled while empty), header (back, circular avatar, name, listing title as tappable subtitle, Call and Video buttons disabled with "Coming soon" while calls are off), `safety_banner` (info pill with the plan's safety wording, dismissible, remembered); sending states (optimistic bubble, "Sending", Retry with the same `clientMessageId`, offline queue while the thread is open); scroll to first unread and a "New messages" chip.
- [ ] Polling: every 15 s while the chat list or thread is visible, `afterSeq` on the open thread, delivered and read posted through REST (G10).
- [ ] Blocked-message sheet and agreement dialog exactly per E.7 (highlighted ranges, **Edit message** / **Deliver message**, **I agree and deliver** / **Cancel**); the agreement version constant matches the server.
- [ ] Error mapping (`contact_error_messages.dart`, chat error mapping): `ERROR_BLOCKED` and `ERROR_THREAD_READ_ONLY` switch the thread to read-only with a banner; `ERROR_MESSAGE_TOO_LONG` prevented by the counter and mapped; the standard 401 shows "Please login to contact seller"; rate-limit messages.
- [ ] Thread overflow menu reuses `UserSafetyMenu` (block, report) and adds report of the thread.
- [ ] Routes `/chats` and `/chats/:threadId` (`RouteNames.chats`, `RouteNames.chatThread(id)`, signed-in guard); `BottomNavItem.chats` opens the list instead of `showComingSoon`; the hard-coded `chatsHasUnread: true` on Home and Search is replaced by `chat_unread_provider`.
- [ ] Accessibility and contrast: spoken label per bubble (sender, text, time, status), 48 dp targets, no overflow at 320 px and 200 percent text, long Hindi words wrap; the gradient sent bubble and its time text pass the token contrast test.
- [ ] English and Hindi strings (`app_en.arb`, `app_hi.arb`, regenerate l10n); Hindi marked for the combined native review (G9).

### Documents (at the end)
- [ ] LLD Parts D and E as-built notes and changelog row (split migrations, no-realtime delivery, `offer` `COMING_SOON`, any deviations); LLD 1.7 migration numbers; `user-stories.md` and `Sprint-plan.md` status; `Manual Testing Guides/US-069-US-013-Testing-Guide.md`.
- [ ] Cleanup marker: note `DISABLED_BY_SELLER` as "to be removed later if unused" in the LLD and the mobile enum comment.

## 5. Test Plan

| Level | Cases | Covers |
|---|---|---|
| Unit | `ContactEligibilityServiceTest`: every D.4 row (own listing, inactive seller, block either way gives `UNAVAILABLE`, real estate, not negotiable, no Aadhaar, calls off, offer coming soon); chat `available` for an eligible buyer; `contact.threadId` set for an existing thread | AC1, AC3, edge cases |
| Unit | `ContactGuardTest`: check order, each code and status, rate limits (pair per hour, new thread per day), outcome recorded for refusal and for ALLOWED, Redis failure allows | AC2, edge cases, spam |
| Unit | `ContactAttemptServiceTest`, retention job, `CommunicationSettingTest` for new keys | rules |
| Unit | `ChatServiceTest`: openThread (new, existing, race), send validation (length by code points incl. Devanagari and emoji, empty, image rules), idempotent resend, `seq` assignment, `canSend` for each reason, delivered and read cursors (clamping, forward only), unread reset | AC4 to AC8 |
| Unit | `MessageScreeningServiceTest`: blocked terms with spacing and leetspeak, phone formats, UPI, URL, off-platform payment, repeated text; D13 flow (blocked not stored or delivered; valid agreement delivers, flags, reports, rate limits; wrong version 409; agreement on a clean message changes nothing; text never logged); auto-report counter | spam edge case, D13 |
| Unit | `ChatMessageListenerTest` (coalescing key, failure isolated), block listener, `ReportTargetResolver` THREAD and MESSAGE, `ListingEngagement.chats()` | AC5, AC6 |
| Integration (Testcontainers, runs in CI; Docker is unavailable locally) | concurrent sends get consecutive `seq`; duplicate `clientMessageId` returns one row; participant isolation (third user gets 404); block makes the thread read-only; `afterSeq` returns exactly the missed messages; deleted listing keeps the thread readable; admin-removed listing is read-only; image with GPS metadata delivered only as a sanitised copy, undecodable image refused; V33 and V34 constraints | AC7, AC8, edge cases |
| Controller | every status code of E.8, envelope shape, pagination bounds, 401 for signed-out, additive `offer` and `contact` on `GET /listings/{id}/public` | API |
| Mobile | repository parsing; controller reducers (insert by `seq`, dedupe, status upgrade); composer states and counter; optimistic send, retry with the same id; blocked-message sheet and agreement dialog (Edit, Deliver, Agree, Cancel); polling; read-only banner; chat list filters, client-side search and empty and error states; header Call and Video disabled while calls are off; action bar for each capability combination; error mapping in English and Hindi; 320 px and 200 percent text; accessibility labels | AC1 to AC8 |

Target above 90 percent line coverage on new and changed code in both repos.

## 6. Validation Checklist

- [ ] AC1 to AC8 each have a passing test.
- [ ] Guard order is exactly: caller active, listing live, not owner, seller active, not blocked, rate limits.
- [ ] A block and a suspended seller are indistinguishable on the details page (`UNAVAILABLE`); the guard answers `ERROR_BLOCKED` only on a contact attempt, never naming who blocked whom.
- [ ] Every refusal and every allowed attempt writes one `contact_attempts` row, also when the request rolls back.
- [ ] Call and Video stay disabled `COMING_SOON` while `valuex.calls.enabled` is false; Make Offer is `COMING_SOON`.
- [ ] Tapping Chat opens a thread with the listing context card first; a second tap reuses the thread.
- [ ] Messages are stored, ordered by `seq`, paginated, and shown with timestamps after the app restarts.
- [ ] Seller gets an in-app notification (coalesced); no message text in the notification, logs or metrics.
- [ ] Message over 2000 characters, empty message and image over 5 MB or not an image are refused with the right codes.
- [ ] Restricted-term message is not stored or delivered; Edit and Deliver message paths work; the agreement is required; override is flagged and reported; daily override limit enforced.
- [ ] Contact details, links and off-platform payment words are flagged but delivered with the safety tip; auto-report triggers at the threshold.
- [ ] Network interruption: retry with the same `clientMessageId` never duplicates.
- [ ] Blocking makes the thread read-only for both with history visible; deleted or sold listing keeps the chat open; Admin-removed listing makes it read-only.
- [ ] Chat images are re-encoded and carry no EXIF; links expire.
- [ ] Rate limits and chat limits are read from the Admin settings; a changed value applies without a restart.
- [ ] Chats tab and its unread dot are live; placeholders removed.
- [ ] Older app versions ignore the new `offer` and `contact` fields.
- [ ] Checkstyle, SonarQube (backend), `dart format` and `flutter analyze --fatal-infos` clean; coverage above 90 percent.

## 7. Open Gaps / Questions

### Decided (user answers, 2026-11-16)

| ID | Decision |
|---|---|
| G1 | US-069 and US-013 are planned and built as one story (11 SP). The master-switch idea is dropped. |
| G2 | Agreed: the guard ships with every check; the new-thread variant is used by chat now, call reachability when calls are built. |
| G3 | Agreed: migrations split (V33 contact, V34 chat). |
| G4 | Agreed in principle; updated by G1: `contact.threadId` and the engagement chat count are filled now, `negotiationId` stays null until US-017. |
| G5 | Agreed: small `ContactAttemptRetentionJob` in this story. |
| G6 | `DISABLED_BY_SELLER` is ignored for now; marked for cleanup later if it stays unused. |
| G7 | Agreed: follow D15 for call reachability when calls are built. |
| G8 | Agreed: standard 401, app shows "Please login to contact seller". |
| G9 | All Hindi copy is reviewed together at a later stage. |
| G10 | Agreed: chat runs on REST plus 15 s polling while a chat screen is visible (LLD A.7 fallback) and an in-app notification through `NotificationDispatcher`. `ChatMessageCreatedEvent` is published so US-130 and US-131 add realtime, typing and push later. The typing indicator and push are out of this story; "seller receives notification" is met in-app only until US-131. |
| G11 | Agreed: add one small exception mapped to 422 with an optional `details` object (for the term ranges); the LLD as-built note records it. |
| G12 | Confirmed: **1600 px**, JPEG quality about 80, configurable as `media.chat-image-px` (default 1600), through `ImageVariantProcessor` with a chat-specific `VariantSpec`. No new stored variant type; the sanitised copy replaces the original. The mobile client resizes to the same value before upload. 1200 px remains a config-only fallback. |
| G13 | Confirmed: a small starter blocked-term list ships in the resource files, marked for Trust & Safety review before production, on the same review track as the D13 agreement wording (O7). |
| G14 | Agreed: `system_card` renders a neutral fallback for `OFFER_EVENT` and `CALL_SUMMARY` until Parts I, F and G add them. |
| G15 | Agreed: the retention columns exist but nothing sets them here; US-016 adds closure and purge. |

**Status: Approved** (2026-11-17)

## 8. As built (2026-11-17)

Both stories were built together on `feature/US-069-US-013-contact-and-chat` in `valuex-backend` and `valuex-mobile`. The deviations from the LLD are listed in the LLD sections D.11 and E.11 (10 and 13 rows). The ones that change behaviour:

- Chat runs on REST and 15 second polling with an in-app notification; there is no realtime, typing indicator or push until US-130 and US-131 (decision G10).
- `canSend` is computed on every read, so there is no block listener. A seller sees a thread only once `last_seq > 1`.
- Make an Offer is `COMING_SOON` until US-017. Call and Video are `COMING_SOON` while `valuex.calls.enabled` is false.
- Migrations are `V33__contact_attempts.sql` and `V34__chat.sql`; `chat_threads` has the extra column `last_message_sender_id` and `chat_messages` the unique index `uq_chat_messages_media`.
- `contact.threadId` is hidden when the seller is unavailable or a block exists, so a block cannot be told from a suspended seller.
- A restricted-term refusal is a 422 (`UnprocessableException`) with `details.terms` (for example `4-8,12-17`) and `details.agreementVersion`.
- The production deployment needs the `<prefix>-chat-media` bucket; `docker-compose.yml` and the iPhone launcher create it locally.

Open items for others: Trust & Safety must review the blocked-term lists and the D13 agreement wording before production; Hindi copy is reviewed together later (G9); `DISABLED_BY_SELLER` stays unused and is a clean-up candidate (G6).

Results: backend 2,554 tests green, checkstyle clean, new-code coverage 94 percent, SonarQube quality gate on new code passed (the old `JwtTokenProvider` S2143 false positive is the only open item); mobile 1,830 tests green apart from the two pre-existing Google pixel-contrast tests, `dart format` and `flutter analyze --fatal-infos` clean, chat code coverage about 95 percent.
