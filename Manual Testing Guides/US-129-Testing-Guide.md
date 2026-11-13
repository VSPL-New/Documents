# US-129 — Voice Search: Manual Testing Guide

**Sprint 3 · Discovery & Search**

Use this guide to validate spoken English or Hindi search on the existing Search screen. Voice recognition is
provided by the phone's speech service. ValueX must never record, retain, log or upload audio, and the transcript
must be sent only as the ordinary search query. The physical-device spike was skipped at the user's direction; all
device- and speech-service-dependent cases below remain **pending** until completed on the listed devices.

## Status and release gates

| Validation | Status |
|---|---|
| Mobile/backend source implementation and automated tests | Implemented; automated results are recorded with the delivery |
| iOS simulator debug build | Passed on the available iOS simulator; speech hardware behavior is not validated |
| Android debug build | Pending; Android SDK is not installed/configured in this macOS environment |
| Real-device speech, permissions, offline packs and interruptions | Pending; no test devices were available during implementation |
| Hindi language/command wording | Draft; native Hindi-speaker review required before release |
| Notice, permission wording, privacy policy and app-store disclosures | Legal/privacy review required before release |
| Hindi-to-English listing matching | Accepted limitation: no transliteration or synonym expansion |

## Prerequisites

1. A checkout of the `feature/US-129-voice-search` branches in `valuex-mobile` and `valuex-backend`, including
   merged US-011.
2. Flutter/Dart, Xcode and CocoaPods for iOS; Android SDK and an Android device/emulator with speech services for
   Android. Use a signed-in buyer account for Search.
3. A reachable backend with published test listings in goods and Real Estate categories. Include both English and
   Devanagari listing text, a category with facets, and a Real Estate leaf requiring Buy/Rent/Lease.
4. Fresh-install state for first-use cases (clear app data or remove the SharedPreferences keys
   `voice_search_notice_shown_v1` and `voice_search_language`). Use a second run to confirm the notice is not shown
   again.
5. To observe network behavior, use the platform proxy/dev tools and backend metrics. Do not retain speech audio or
   copy transcripts into logs, crash reports, analytics, or screenshots shared outside the test team.

## Automated test subset

From `valuex-mobile`:

```bash
dart format lib test
flutter analyze
flutter test --coverage --dart-define=SKIP_PIXEL_CONTRAST=true
```

Focused tests include `test/features/voice_search/`, `test/features/search/search_repository_test.dart`,
`test/features/search/search_results_controller_test.dart`, and `test/features/search/search_screen_test.dart`.
From `valuex-backend`, run `mvn verify`; focused tests are `SearchSourceTest`,
`SearchRequestValidatorTest`, `SearchControllerTest`, and `ListingSearchServiceTest`.

## Manual test cases

| ID | AC / edge case | Steps | Expected |
|---|---|---|---|
| TC-001 | AC1, AC4 — first use and default English | Set app language to English, clear voice preferences, open Search, tap the microphone | First-use notice explains the phone speech service and that JustQlic does not record/keep voice. Not now returns to Search without prompting/listening. Continue leads to OS permission prompt(s), then the listening panel; English India is selected when available. |
| TC-002 | AC1 — live partial words | While listening, say a short English query and pause before finishing | Partial words appear in the panel only. Search field, suggestions and results do not update per partial. |
| TC-003 | AC2 — auto-search | Finish speaking and remain silent for about 3 seconds | The panel closes; tidied query is written once into the existing field; one first-page search starts without another tap. The ordinary result/loading/error UI is used. |
| TC-004 | AC2 — Stop | Speak a query and tap Stop before the silence timeout | Recognition finishes, the last partial/final text is placed in the field and the single search starts. |
| TC-005 | AC2 — command tidying | Say “Show me Samsung phones, please” and (separately) “मुझे सैमसंग फोन चाहिए” | Only the permitted leading/trailing command phrases and trailing punctuation are removed; the resulting queries are `Samsung phones` and `सैमसंग फोन`. |
| TC-006 | AC3 — edit and search again | After a voice search, edit a word and submit; then tap the microphone and speak a different query | Edited searches use the normal typed flow; microphone opens a new recognition session. |
| TC-007 | AC4 — remembered Hindi | Change the app language to Hindi; tap the mic; switch to English in the panel; close and reopen voice search | First voice session defaults to Hindi; the later choice is remembered across panel sessions and app restarts. |
| TC-008 | AC5 — category, filters and intent | Choose an L3 category, apply price/condition/facet filters and a location; use a Real Estate category with Buy/Rent/Lease selected; speak a query | The same category, filter values and Real Estate intent are included in the search; only the query changes. The Real Estate intent chooser still appears when no intent has been selected. |
| TC-009 | AC6 — denied permission | Deny microphone/speech permission, tap the mic again | A clear permission explanation and Try again are shown; the text field remains usable. |
| TC-010 | AC6 — blocked permission | Deny permission until the OS will not ask again, then tap the mic | The blocked-permission explanation includes Open Settings. Settings opens the app settings; after enabling permission, retry succeeds. |
| TC-011 | AC7 — recognition unavailable | Use a device without a speech service or disable/remove its speech service | A clear unavailable message and Type instead action are shown; typing still searches normally. |
| TC-012 | AC7 — language unavailable | Select Hindi where `hi_IN` is unavailable | The language-specific message offers switching to English. Typing remains available. |
| TC-013 | AC7 — network needed | With no network and no usable on-device language pack, request recognition | A network-required message appears with a path to switch language or type; no ValueX audio request is made. |
| TC-014 | AC8 — silence/noise | Start listening and say nothing, or produce only noise | “Didn't catch that” and Try again appear; no search request is sent and no empty query is applied. |
| TC-015 | AC9 — route/background interruption | Start speaking, then leave Search, background the app, answer a call, or switch to another app | The session stops/cancels, the microphone is released, and late partial/final events do not change the search field or results. |
| TC-016 | Privacy — inspect network and logs | Speak a unique test phrase while capturing app/backend requests and logs | No audio/media upload, transcript log, analytics property, saved-search field or crash-report value exists. The first-page search has `source=VOICE`; later edit, refresh, filter and pagination requests omit it. |
| TC-017 | Backend validation and metrics | Call search with missing/blank source, `TYPED`, `VOICE`, lowercase `voice`, and an unknown value | Missing/blank and the two exact enum values are accepted; unknown/lowercase values return the usual `ERROR_INVALID_FILTERS` envelope. Request/empty counters have consistent `source` tags; latency remains untagged; logs do not include source or query. |
| TC-018 | Long query, punctuation and numbers | Speak a query longer than 200 characters, include an emoji, punctuation, prices and spoken numbers | Normalization truncates at 200 Unicode characters without splitting a surrogate pair; punctuation is tidied; numbers/currency words remain words and do not become filters. |
| TC-019 | Hindi/Hinglish matching | Search Devanagari against English-only listings, then try Hindi/Hinglish phrases | Devanagari query behaves like a normal search and can return an ordinary empty state. Hinglish recognition is exploratory only; it is not a product guarantee. |
| TC-020 | Accessibility/display | Enable TalkBack/VoiceOver; use 200% text and a small display; enable system reduce motion | Microphone is labelled and at least 48 dp; listening/live text is announced; all actions are reachable and labelled; content scrolls without clipping; motion is reduced when requested. |
| TC-021 | Competing microphone and double tap | Start another microphone user/phone call; double tap the mic rapidly | Busy/unavailable recovery is clear; only one ValueX voice session is active. |
| TC-022 | Search service failure | Speak a valid phrase while the search service is unavailable | Spoken text remains editable and the standard Retry/error behavior is shown; no second search is automatically sent. |

## Device matrix (pending)

Complete and record OS version, device model, speech service/version, available locale ids and results:

| Device | Language/network scenarios | Permission/lifecycle/accessibility scenarios | Status |
|---|---|---|---|
| iPhone with Apple Speech | `en_IN`, `hi_IN`, airplane mode with/without on-device pack, weak network | denied/blocked/revoked, call/app switch, VoiceOver, Real Estate/filters | Pending |
| Android with Google speech services | `en_IN`, `hi_IN`, airplane mode with/without pack, weak network | denied/blocked/revoked, call/app switch, TalkBack, Real Estate/filters | Pending |
| Android without Google speech services | both locale availability and no-service recovery | denied/blocked, Type instead and typed search | Pending |

Record whether on-device capability is reported per locale, exact OS error names, final/partial-result behavior,
permission status behavior, and whether recognition requires network. No production release should claim strict
offline recognition; the phone speech service may use its own servers.
