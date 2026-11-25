# US-069 + US-013 - Contact the Seller and Chat: QA Testing Guide

**Sprint 4 · Communication & Negotiation**

Manual test cases for contacting a seller from a listing (US-069) and chatting with them (US-013). The backend is checked
with `curl` and SQL; the app is checked on two phones (or one phone and a second account over `curl`).

> **What ships:** `POST /api/v1/chats`, `GET /api/v1/chats`, `GET /api/v1/chats/{id}`, `GET` and `POST
> /api/v1/chats/{id}/messages`, `POST /api/v1/chats/{id}/delivered` and `/read`, `GET /api/v1/chats/unread-count`;
> the `offer` and `contact` fields on `GET /api/v1/listings/{id}/public`; migrations `V33` (`contact_attempts`) and
> `V34` (`chat_threads`, `chat_messages`); the Admin settings listed below; the pictures purpose `CHAT_IMAGE`. In the
> app: the Chat button on the listing page, the Chats tab with its unread dot, the Messages list and the conversation
> screen.
> **Not in this story:** realtime delivery, the typing indicator and push notifications (US-130, US-131: the app polls
> every 15 seconds and the seller gets an in-app notification); Make an Offer (US-017: shown as "Coming soon"); Call and
> Video (on hold, shown as "Coming soon" and disabled in the conversation header); closing a conversation and deleting
> old history (US-016); an online dot; Admin screens for the settings (US-116) and for reports (US-057).

| Setting | Value |
|---|---|
| Backend base URL | `http://localhost:8080` |
| New settings (Admin-managed, `platform_settings`) | `CONTACT_ATTEMPTS_PER_PAIR_PER_HOUR` 10, `CALL_ATTEMPTS_PER_PAIR_PER_HOUR` 3, `CHAT_NEW_THREADS_PER_DAY` 20, `CONTACT_ATTEMPT_RETENTION_DAYS` 180, `CHAT_MESSAGE_MAX_CHARS` 2000, `CHAT_IMAGE_MAX_MB` 5, `CHAT_MESSAGES_PER_MIN` 30, `CHAT_POLICY_OVERRIDES_PER_DAY` 5, `CHAT_NOTIFY_COALESCE_MINUTES` 10, `CHAT_AUTO_REPORT_FLAGS` 3, `CHAT_PAGE_SIZE` 30 |
| Properties | `valuex.calls.enabled` (env `CALLS_ENABLED`, default false), `valuex.media.variant.chat-image-px` (default 1600) |
| Error codes | 403 `ERROR_ACCOUNT_NOT_ACTIVE`, `ERROR_BLOCKED`; 404 `ERROR_LISTING_NOT_AVAILABLE`, `CHAT_THREAD_NOT_FOUND`; 409 `ERROR_OWN_LISTING`, `ERROR_SELLER_UNAVAILABLE`, `ERROR_THREAD_READ_ONLY`, `ERROR_POLICY_AGREEMENT_OUTDATED`; 422 `ERROR_MESSAGE_TOO_LONG`, `ERROR_EMPTY_MESSAGE`, `WARNING_CONTENT_FLAGGED`, `ERROR_IMAGE_TOO_LARGE`, `ERROR_IMAGE_INVALID`; 429 `WARNING_RATE_LIMIT`, `RATE_LIMIT_EXCEEDED`; 400 `ERROR_INVALID_MESSAGE_TYPE` |
| Known gaps | The blocked-term lists are a starter set for Trust & Safety to review; all Hindi texts and the agreement wording need review; the bucket `<prefix>-chat-media` must exist in every environment |

---

## Prerequisites

1. Backend, PostgreSQL, Redis and object storage running (the `chat-media` bucket exists: `docker compose up` creates it); the app running against it.
2. Three `ACTIVE` accounts with display names: `$SELLER` (Asha K), `$BUYER` (Ravi S) and `$THIRD` (Eve). Note `SELLER_ID`, `BUYER_ID`.
3. A live listing `LISTING` owned by `$SELLER` (negotiable, with a price), and a second live listing `LISTING2`.
4. Variables:

```bash
B="localhost:8080/api/v1"
HS="Authorization: Bearer $SELLER"
HB="Authorization: Bearer $BUYER"
HT="Authorization: Bearer $THIRD"
```

---

## A. The listing page offers the contact options (US-069 AC1, AC3)

| # | Steps | Expected |
|---|---|---|
| A1 | `curl -H "$HB" $B/listings/$LISTING/public` and read `data.capabilities` and `data.contact` | `chat` `{available:true}`; `call`, `video` `COMING_SOON`; `offer` `IDENTITY_REQUIRED` (buyer without Aadhaar) or `COMING_SOON` (verified); `cart`, `buyNow` `COMING_SOON`; `contact.threadId` null. |
| A2 | The same as `$SELLER` | Every option `OWN_LISTING`; `contact` ids null. |
| A3 | Set the listing's `negotiable` to false and read it as the buyer | `offer.reason` `NOT_NEGOTIABLE`; `chat` still available. |
| A4 | A Real Estate listing | `cart` and `buyNow` `NOT_APPLICABLE`; `chat` available. |
| A5 | Block the buyer (`PUT /users/$BUYER_ID/block` as the seller) and read the listing as the buyer | Every option `UNAVAILABLE` (the same reason as a suspended seller); no sign of a block. Then unblock. |
| A6 | `UPDATE users SET status='SUSPENDED' WHERE id='<SELLER_ID>'` | Reading the listing answers 403 `ERROR_SELLER_SUSPENDED` (existing). Restore the status. |
| A7 | In the app: open the listing as the buyer | Chat is enabled; Call, Video and Make an Offer are dimmed; Buy Now as before (Add to Cart is no longer on this page, US-019 follow-up). A screen reader says "Call, Coming soon". |
| A8 | The same at 320 px width and 200 percent text | No overflow; buttons stay tappable. |
| A9 | Set `CALLS_ENABLED=true`, restart, read the listing | `call` and `video` `available:true` (nothing opens them yet). Set it back to false. |

## B. Start a chat (US-069 AC2, edge cases)

| # | Steps | Expected |
|---|---|---|
| B1 | `curl -i -X POST -H "$HB" -H "Content-Type: application/json" -d '{"listingId":"'$LISTING'"}' $B/chats` | 201; `data.role` BUYER, `listing.title`/`price` snapshot, `counterpart.displayName` "Asha K", `lastSeq` 1, `canSend` true. `SELECT message_type FROM chat_messages WHERE seq=1` is `LISTING_CONTEXT`. |
| B2 | Repeat B1 (or tap Chat twice quickly in the app) | 200 with the same `threadId`; one thread row for this listing and buyer. |
| B3 | `SELECT outcome, count(*) FROM contact_attempts GROUP BY outcome` | `ALLOWED` rows for each attempt. |
| B4 | As the seller: `POST /chats` for their own listing | 409 `ERROR_OWN_LISTING`; a `NOT_ELIGIBLE` row is stored even though the request failed. |
| B5 | Open a chat for a sold, deleted or unknown listing | 404 `ERROR_LISTING_NOT_AVAILABLE`. |
| B6 | Set the buyer's status to `SIGNUP_PENDING` and open a chat | 403 `ERROR_ACCOUNT_NOT_ACTIVE`. Restore. |
| B7 | Suspend the seller and open a chat for a listing with no thread yet | 409 `ERROR_SELLER_UNAVAILABLE`; a `SELLER_UNAVAILABLE` row. Restore. |
| B8 | Block either way and open a chat | 403 `ERROR_BLOCKED` ("You cannot contact this seller"); a `BLOCKED` row. |
| B9 | Lower `CONTACT_ATTEMPTS_PER_PAIR_PER_HOUR` to 2 (`UPDATE platform_settings ...`), repeat B1 three times, wait for the setting cache, then restore | The third answers 429 `WARNING_RATE_LIMIT` ("Too many contact attempts. Try again later"); a `RATE_LIMITED` row. |
| B10 | Lower `CHAT_NEW_THREADS_PER_DAY` to 1 and open chats for two listings | The second answers 429 `WARNING_RATE_LIMIT`. Restore. |
| B11 | Request without a token | 401 (the app shows "Please login to contact seller"). |
| B12 | In the app, tap Chat on the listing | The conversation opens with the listing card first (title and price). Going back, the listing now says "Open chat". |
| B13 | In the app, each refusal above | A message in the app's words (blocked, unavailable, too many attempts, own listing, complete registration) and the listing page stays. |
| B14 | `contact_attempts` rows older than 180 days | Deleted by the daily job at 03:45 (or call `purge()` in a test). |

## C. Send and receive (US-013 AC4 to AC8)

| # | Steps | Expected |
|---|---|---|
| C1 | Buyer: `curl -X POST -H "$HB" -H "Content-Type: application/json" -d '{"clientMessageId":"<uuid>","type":"TEXT","body":"Is the box included?"}' $B/chats/$THREAD/messages` | 201; `seq` 2, `status` SENT, `fromMe` true. |
| C2 | Repeat C1 with the same `clientMessageId` | 200 with the same message id; one row. |
| C3 | Seller: `GET /chats?role=SELLING` | The thread appears with `unreadCount` 1, `lastMessage.preview` "Is the box included?", `fromMe` false. Before C1 the thread was not in the seller's list. |
| C4 | Seller: `GET /chats/unread-count` | `chatsUnread` 1. |
| C5 | `SELECT title, body FROM notifications WHERE user_id='<SELLER_ID>' AND event_type='CHAT_MESSAGE'` | One row: "New message from Ravi S" / "Open JustQlic to read it"; **no message text**. Send three more messages quickly: still one row inside the 10 minute window. |
| C6 | Seller replies; buyer `GET /chats/$THREAD/messages` | Ascending `seq`; the buyer's own message shows `status` DELIVERED or READ after the seller's cursors move. |
| C7 | `POST /chats/$THREAD/delivered {"upToSeq":3}` then `/read {"upToSeq":3}` as the seller | 204; `GET /chats/unread-count` drops; the buyer sees READ on messages up to 3. |
| C8 | `/read {"upToSeq":1000}` and then `/read {"upToSeq":1}` | The cursor stops at the last message and never moves back; unread counts stay right. |
| C9 | `GET /chats/$THREAD/messages?afterSeq=3`, `?beforeSeq=3&limit=2`, `?limit=2` | Exactly the later messages; the two before 3; the latest two with `hasMore` true. |
| C10 | A third user: `GET /chats/$THREAD`, `/messages`, `POST /messages`, `/read` | All 404 `CHAT_THREAD_NOT_FOUND`; their own list is empty. |
| C11 | Two phones, both send at the same moment (or run ten parallel `curl` sends) | Distinct consecutive `seq`; no gaps; `last_seq` equals the count. |
| C12 | Restart the app and open the conversation | All messages come back with times; the order is by `seq`. |
| C13 | In the app on both phones: send from A | B sees it within about 15 seconds on the open conversation and in the list; the Chats tab dot lights on B. Opening it clears the dot. |
| C14 | In the app: airplane mode, send, then back online | The bubble shows "Not sent. Tap to retry" (or is sent automatically after the next successful refresh); Retry sends it once, not twice. Delete removes it. |
| C15 | In the app: scroll up while a message arrives | A "New messages" chip appears; tapping it jumps to the newest. |
| C16 | In the app: the list search | Typing a name or a listing title filters the loaded conversations; typing words from a message finds nothing; Buying and Selling chips filter; pull to refresh works. |
| C17 | The thread screen at 320 px width and 200 percent text, and in Hindi | No overflow; every control reachable; long Hindi words wrap. |

## D. Message rules (validation and error scenarios)

| # | Steps | Expected |
|---|---|---|
| D1 | Send `{"type":"TEXT","body":"   "}` | 422 `ERROR_EMPTY_MESSAGE`; nothing stored. |
| D2 | Send 2000 characters, then 2001 | 201, then 422 `ERROR_MESSAGE_TOO_LONG` ("Message exceeds 2000 characters"). 2000 Hindi characters or emoji are accepted (counted as characters). |
| D3 | `"type":"LISTING_CONTEXT"` or `"VIDEO"` | 400 `ERROR_INVALID_MESSAGE_TYPE`. |
| D4 | Missing `clientMessageId` | 400 validation error. |
| D5 | In the app type past the limit | The field stops at the limit; the counter shows near 2000 and turns red at the limit. |
| D6 | `CHAT_MESSAGES_PER_MIN` to 5, send six messages | The sixth answers 429 `RATE_LIMIT_EXCEEDED`. Restore. |
| D7 | Send a message with control characters or markup | Stored as plain text; markup is shown as text, never interpreted. |

## E. Restricted terms and "Deliver message" (decision D13)

| # | Steps | Expected |
|---|---|---|
| E1 | Send `"you shit"` | 422 `WARNING_CONTENT_FLAGGED` with the full alert text; `details.terms` `4-8`, `details.agreementVersion` `policy-override-v1`; **nothing stored, nothing delivered, no notification**. |
| E2 | In the app send the same | The alert sheet shows the text with "shit" highlighted, the words "We detected restricted terms ... resubmit.", and **Edit message** and **Deliver message**. Edit puts the text back in the field. |
| E3 | In the app tap Deliver message, then Cancel | The agreement dialog ("I am confident that I'm not violating JustQlic policies. ...") appears; Cancel returns to the alert; nothing is sent. |
| E4 | Tap Deliver message, then **I agree and deliver** | The message is delivered to the seller. `SELECT flagged, flag_reasons, policy_override_at, policy_agreement_version FROM chat_messages ...` is true, `BLOCKED_TERM_OVERRIDE`, a time, `policy-override-v1`; `communication_reports` has a new row `source='SYSTEM'`, `target_type='MESSAGE'`, `reason='INAPPROPRIATE_CONTENT'`, no reporter, `status` OPEN. |
| E5 | `curl` the same text with `"policyAgreement":{"accepted":true,"version":"policy-override-v1"}` | 201 with `flags` `["BLOCKED_TERM_OVERRIDE"]`. With `"version":"old"` | 409 `ERROR_POLICY_AGREEMENT_OUTDATED`. With `accepted:false` | 422 again. |
| E6 | A clean message that carries an agreement | Delivered as an ordinary message: no flag, no report. |
| E7 | `CHAT_POLICY_OVERRIDES_PER_DAY` to 1, override twice | The second answers 429 `RATE_LIMIT_EXCEEDED`; in the app "You've used all your overrides for today". Restore. |
| E8 | Variants: `"sh1t"`, `"s h i t"`, `"SHIT!"`, a Hindi term in Roman script and in Devanagari | All blocked. `"shitake"`, `"classic"`, `"Can I pay via UPI?"` are **not** blocked. |
| E9 | Check the application log after E1 and E4 | The text of the message appears nowhere. |
| E10 | Send a message with a phone number, an email, a UPI id, a link | Delivered with `flags` (`CONTACT_INFO`, `EXTERNAL_LINK`); the other person sees "For your safety, keep chats and payments on JustQlic." |
| E11 | Send `"pay by gpay to 9876543210"` | Flagged `OFF_PLATFORM_PAYMENT`. |
| E12 | Send the same text three times in a minute | The third is flagged `REPEATED`. |
| E13 | `CHAT_AUTO_REPORT_FLAGS` to 2 and send two flagged messages | One `SYSTEM` report (`SHARING_CONTACT_DETAILS` for contact details, otherwise `SPAM`) on the second only. Restore. |

## F. Pictures

| # | Steps | Expected |
|---|---|---|
| F1 | In the app: attach, pick a photo (camera or gallery) | The bubble shows the picture while sending; the seller sees it. |
| F2 | `curl` flow: `POST /media/uploads {"purpose":"CHAT_IMAGE","ownerType":"USER","ownerId":"<BUYER_ID>","fileName":"a.jpg","contentType":"image/jpeg","sizeBytes":...}`, `PUT` the bytes to `uploadUrl`, `POST /media/{id}/complete`, then send `{"type":"IMAGE","mediaId":"..."}` | 201 `type` IMAGE with `image.url` (a signed link that expires in 10 minutes). |
| F3 | Upload a JPEG that has GPS EXIF data and download the delivered picture | The delivered copy is a JPEG with no EXIF or location data and a longest side of at most 1600 px; the original object is gone from the bucket. |
| F4 | Send a picture over `CHAT_IMAGE_MAX_MB` (5) | 422 `ERROR_IMAGE_TOO_LARGE` ("Image exceeds 5 MB"). |
| F5 | Upload a text file renamed `.jpg`; use someone else's media id; use a `LISTING_IMAGE` id; reuse a media id in a second message | 422 `ERROR_IMAGE_INVALID` each time. |
| F6 | Deny the camera or photo permission in the phone settings | "Allow access to your camera or photos in Settings to share a picture". |
| F7 | Switch off the network after the upload, before the send, then retry | The picture is not uploaded again; it is sent once. |

## G. Blocks, closed listings and reports

| # | Steps | Expected |
|---|---|---|
| G1 | The seller blocks the buyer while a thread exists | Both sides: `GET /chats/{id}` `canSend` false, `readOnlyReason` BLOCKED; sending answers 403 `ERROR_BLOCKED`; the history is still readable; the app shows "You can't send messages in this conversation." and no composer. |
| G2 | Unblock | Sending works again. |
| G3 | Mark the listing SOLD, then delete it (`deleted_at`) | The thread stays readable and writable; `listing.available` false. |
| G4 | Set the listing's status to `REMOVED_BY_ADMIN` or `REJECTED` | `readOnlyReason` LISTING_REMOVED; sending answers 409 `ERROR_THREAD_READ_ONLY`. |
| G5 | Suspend the other person | `readOnlyReason` ACCOUNT_UNAVAILABLE; sending answers 409 `ERROR_SELLER_UNAVAILABLE`. |
| G6 | `POST /reports {"targetType":"THREAD","targetId":"<thread>","reason":"SPAM"}` as a participant | 201; a stranger gets 404 `REPORT_TARGET_NOT_FOUND`. |
| G7 | `POST /reports {"targetType":"MESSAGE","targetId":"<the other person's message>","reason":"HARASSMENT"}` | 201; reporting your own message, a system card or a stranger's thread answers 404. |
| G8 | In the app: the conversation menu | Block user, Report user and Report conversation work (the existing confirmation and report sheet). |

## H. Acceptance criteria and edge cases tally

| Criterion | Cases |
|---|---|
| US-069 AC1 options on the listing | A1 to A9 |
| US-069 AC2 Chat opens with the listing context | B1, B12 |
| US-069 AC3 Call and Video coming soon | A1, A7, A9 |
| US-069 seller unavailable, account not active, blocked, many attempts | A5, A6, B6 to B10 |
| US-013 AC4 chat opens | B12, C1 |
| US-013 AC5 seller notified | C5 |
| US-013 AC6 reply notified and visible | C6, C13 |
| US-013 AC7 messages stored | C12 |
| US-013 AC8 history with timestamps | C9, C12 |
| Spam and inappropriate messages | E1 to E13 |
| Listing deleted after the chat started | G3, G4 |
| Network interruption | C2, C14, F7 |
| User blocks the seller | G1 |
| Message length, image size | D2, F4 |

## I. Automated tests

```bash
# backend (unit and integration; the integration tests need Docker)
cd valuex-backend
mvn clean verify
# Docker Desktop with Engine 29 and a non-UTC machine time zone may need:
#   JAVA_TOOL_OPTIONS="-Dapi.version=1.44 -Duser.timezone=UTC"
mvn test -Dtest='Chat*Test,Contact*Test,MessageScreeningServiceTest,RestrictedTermMatcherTest,ChatImageServiceTest'

# mobile
cd valuex-mobile
dart format lib test && flutter analyze --fatal-infos
flutter test test/features/chat test/features/listing_view test/core/routing --dart-define=SKIP_PIXEL_CONTRAST=true
```
