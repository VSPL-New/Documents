# US-129: Voice Search - Implementation Plan

## 1. Header

| Field | Value |
|---|---|
| Story | US-129 - Voice Search (a new story added to Sprint 3 on 2026-11-11) |
| Sprint | Sprint 3 - Discovery & Search |
| Story points | 5 (proposed). Rises to 8 if decision V1 becomes "strict offline with native bridges" (LLD 9.5). |
| Repos involved | valuex-mobile (about 90% of the work), valuex-backend (an optional `source` query parameter and metric tags). No `valuex-ai`, infra or database change. |
| Dependencies | US-011 (search screen, search API, `SearchCriteria`, results controller). US-011 is built on `feature/US-011-browse-search-listings` in both repos and is not merged yet (see gap G2). No other story depends on US-129. |
| Date | 2026-11-11 |
| Design source | [Sprint 3 LLD](../LLD/Sprint-3-Discovery-Search-LLD.md) Part I (I.1 to I.11) and section 9.5 (decisions V1 to V8); [tentative design by ChatGPT](../VoiceSearchTentativeDesignByChatGPT.md), adapted as explained in LLD I.3 |
| Branches (proposal) | `feature/US-129-voice-search` in `valuex-mobile` and in `valuex-backend`, cut from `main` once US-011 is merged (or from `feature/US-011-browse-search-listings` if work must start earlier, see G2) |
| Flyway number | None |
| Effort | About 8 working days: spike 1, mobile 4.5, backend 0.5, device QA and documents 2 |

## 2. Story Recap

**As a** buyer **I want to** search by speaking **so that** I can find items quickly without typing, in English or Hindi.

### Acceptance Criteria (user-stories.md US-129)

| ID | Behaviour |
|---|---|
| AC1 | Tapping the microphone in the search box (first time: after a short notice and the permission prompts) opens a listening panel that shows the words as they are spoken. |
| AC2 | When speech stops for about 3 seconds, or Stop is tapped, the tidied text is placed in the search box and the results appear without another tap, as for typed text. |
| AC3 | The text can be edited and searched again, or the microphone tapped again. |
| AC4 | Listening starts in the app language (English India or Hindi India); the other language can be chosen in the panel and is remembered. |
| AC5 | The category, filters and Real Estate intent that were chosen are kept. |
| AC6 | Denied permission: an explanation, and Open Settings when the phone will not ask again; typing still works. |
| AC7 | Speech recognition or the chosen language not available: a clear message; switching language or typing is offered. |
| AC8 | Nothing recognised: "Didn't catch that" with Try again; no search is made. |
| AC9 | Leaving the screen, going to the background or another app taking the microphone stops listening. |

**Edge cases:** noise or a wrong word, long speech, Hinglish, Hindi against English listings, spoken numbers, double tap, permission revoked while open, no internet and no on-device pack, screen reader, search service down after speaking.
**Validation rules:** the text is an ordinary search query (200 characters, same validation, ranking, rate limit and errors as US-011); only a short list of command phrases is removed; listening never starts without a tap and stops after about 3 s of silence or 20 s in total; audio is never recorded, stored or uploaded by ValueX; the text is not stored or logged; `source=VOICE` is sent for metrics, any other value than `TYPED` or `VOICE` is rejected.
**Errors:** in-app `VOICE_PERMISSION_DENIED`, `VOICE_PERMISSION_BLOCKED`, `VOICE_UNAVAILABLE`, `VOICE_LANGUAGE_UNAVAILABLE`, `VOICE_NO_SPEECH`, `VOICE_NETWORK_REQUIRED`, `VOICE_BUSY`; backend `ERROR_INVALID_FILTERS` for an unknown `source`.

## 3. Design Reference

LLD Part I: I.3 (tentative design versus ValueX), I.5 and I.6 (API and backend), I.7 (mobile: packages and platform setup I.7.1, structure I.7.2, controller and error mapping I.7.3, text tidying and the hand-off to search I.7.4, UI I.7.5, lifecycle I.7.6), I.8 (sequence), I.9 to I.11 (rules, privacy and tests), and section 9.5 (decisions V1 to V8).

### Key design decisions

- No new endpoint, table or Admin setting. The text goes into the existing search box and runs the existing `GET /api/v1/search/listings`; the optional `source` parameter only feeds metrics.
- Speech recognition is a separate port (`SpeechRecognizer`) with the `speech_to_text` plugin behind one adapter file, so the engine can change without touching search.
- Live words appear in the listening panel only. The search box is written once when recognition ends, so the 250 ms suggestion call and the 400 ms search debounce never fire per word.
- `SearchCriteria` gets no `source`; saved searches and deep links never carry it. `SearchResultsController.applyVoiceQuery` marks only the first-page request.
- The controller initialises the recogniser on the first tap, never when the screen opens, so no permission dialog appears before the buyer asks for voice.

### Verified Implementation Anchors (checked in the code on 2026-11-11)

| Area | Finding and consequence |
|---|---|
| Search screen | `lib/features/search/presentation/search_screen.dart`: `_field` builds the `TextField` with a clear (x) `IconButton` as `suffixIcon` shown only when the text is not empty; `_onChanged` calls `_controller.setQuery` and `_suggestions.onTextChanged`; `_onSubmitted` calls `_suggestions.onSubmitted()` then `_controller.submit()`; `_selectSuggestion` shows how to write the field and call `applyCriteria`. The 200 limit is `TextField.maxLength` with `buildCounter` returning null. The suffix becomes a `Row` with the new button. |
| Results controller | `SearchResultsController` (`providers/search_results_controller.dart`): `applyCriteria`, `load`, a request counter for stale responses; `_search` calls `SearchRepository.search(criteria, page:, nearCity:, nearState:)`. `SearchCriteria.maxQueryLength` is the 200 limit. |
| Repository | `SearchRepository.search` builds `queryParameters` from `criteria.toQueryParameters()` plus `page`, `size`, `includeFacets`, `nearCity`, `nearState`. A `SearchSource` argument is added here. |
| Test patterns | `test/features/search/search_screen_test.dart` uses `AppHarness(extraOverrides: [...])`, `FakeSearchRepository` (`search_fixtures.dart`) and `FakeLocationService`-style fakes; widget tests run with `--dart-define=SKIP_PIXEL_CONTRAST=true` because of one unrelated contrast failure. |
| Packages | `permission_handler ^11.3.1` is already in `pubspec.yaml` but not used in `lib`; `speech_to_text` is not present. Riverpod 3 with `riverpod_generator` (a generated `locale_controller.g.dart` exists). |
| iOS config | `ios/Runner/Info.plist` has location, camera and photo strings only (no microphone or speech). `ios/Podfile` has no `GCC_PREPROCESSOR_DEFINITIONS` permission macros. Deployment target 15.0. The build uses Swift Package Manager for most plugins (one plugin, `flutter_secure_storage`, still needs CocoaPods). |
| Android config | `AndroidManifest.xml` has `INTERNET` and `ACCESS_COARSE_LOCATION`; its `<queries>` has only `PROCESS_TEXT`. `minSdk` comes from Flutter. |
| Language | `LocaleController` (`features/settings/presentation/providers/locale_controller.dart`) holds the app locale (English or Hindi); `SharedPreferences` is already used for the saved language. |
| Backend controller | `SearchController.search` takes the query parameters listed in B.4 (last is `includeFacets`); `SearchRequest` is a record of raw strings; `SearchRequestValidator.invalidFilters()` throws `ERROR_INVALID_FILTERS`; `SearchSort.parse` returns an `Optional` and is the pattern for `SearchSource.parse`. |
| Backend metrics | `ListingSearchService` increments `search.requests.total` with the tag key `result` (in `finally`) and `search.results.empty.total` without tags; `search.latency` is untagged. A meter name must always use the same tag keys, so both counters are changed together. The log line holds only result count, page and latency. |
| Plugin facts not yet verified | Exact `speech_to_text` version and API (`SpeechListenOptions`, `onDevice`, error names, locale id format), whether on-device recognition can be requested and detected per language, and `permission_handler` behaviour with this project's iOS build. These come from step 4.1 and are not assumed here. |

## 4. Implementation Steps

### 4.1 Branches and device spike (about 1 day, before any production code)
- [ ] Confirm gap G1 (decisions V1 to V8) with the product owner, and G2 (branch base).
- [ ] Cut `feature/US-129-voice-search` in `valuex-mobile` and `valuex-backend`; run both baselines (backend `mvn verify` with JDK 21 and the Colima settings from the README, mobile `dart format`, `flutter analyze`, `flutter test --dart-define=SKIP_PIXEL_CONTRAST=true`).
- [ ] Throwaway spike app or branch on real devices (one iPhone, two Android phones, one of them without Google speech services): add `speech_to_text`, list locales, record the `en_IN` and `hi_IN` ids, trigger every error (denied, blocked, no speech, no network, busy, no service), note the exact error names and the shape of the final result on Android, and try `onDevice` for both languages in airplane mode. Note whether on-device support can be queried; this fixes V1.
- [ ] Check `permission_handler` on iOS with this project's SPM and CocoaPods mix: apply `PERMISSION_MICROPHONE=1` and `PERMISSION_SPEECH_RECOGNIZER=1` and confirm the statuses (denied, permanently denied, restricted) are reported.
- [ ] Write the findings into section 8 of this plan; update the error table in LLD I.7.3 if names differ. Decision gate: if on-device cannot be requested and the product owner needs strict offline, stop and re-plan as 8 SP (V1 option B).

### 4.2 Backend (about 0.5 day)
- [ ] `search/domain/SearchSource` enum (`TYPED`, `VOICE`) with `parse(String)` returning `Optional` (blank gives `TYPED`), following `SearchSort`.
- [ ] `SearchRequest`: add trailing `String source`. Update every constructor call (`grep "new SearchRequest("` in main and test code).
- [ ] `SearchController.search`: add `@RequestParam(required = false) String source`, pass it to `SearchRequest`, add it to the OpenAPI parameter notes.
- [ ] `SearchRequestValidator.validate`: reject an unknown non-blank `source` with `invalidFilters()`.
- [ ] `ListingSearchService`: compute the source tag once at the start (lenient: `VOICE` or `TYPED`), add it to `search.requests.total` and `search.results.empty.total`; leave `search.latency` untagged. Confirm the log line is unchanged and holds no text or `source`.
- [ ] Backend README search section: document `source` and the two metric tags.
- [ ] Checkstyle clean; no Flyway migration.

### 4.3 Mobile: domain and data (`lib/features/voice_search/{domain,data}`)
- [ ] Add `speech_to_text` to `pubspec.yaml` (version from the spike); `flutter pub get`.
- [ ] `domain/voice_error.dart`, `voice_language.dart` (`en_IN`, `hi_IN`; default from the app locale), `speech_event.dart`, `speech_recognizer.dart` (the port).
- [ ] `domain/voice_query_normalizer.dart`: the pure function of LLD I.7.4 (control characters, trim, collapse spaces, trailing punctuation, one leading and one trailing phrase from the fixed lists only when words remain, 200-character cut on a character boundary using `SearchCriteria.maxQueryLength`).
- [ ] `data/speech_to_text_recognizer.dart`: the only file importing the plugin. Initialise lazily; read `locales()` once per session; locale resolution (English: `en_IN`, `en_US`, `en_GB`, any `en_*`; Hindi: `hi_IN` only); `listen` with partial results, `pauseFor` 3 s, `listenFor` 20 s, short-query mode, and `onDevice` according to V1; map plugin errors and statuses to `SpeechEvent`; finish with the last partial when no final result arrives; cancel and stop.
- [ ] `data/voice_preferences.dart`: `voice_search_language` and the notice flag (`voice_search_notice_shown` with the notice version), over the existing `SharedPreferences` provider.
- [ ] Search feature: `search/domain/search_source.dart` (`typed`, `voice`); `SearchRepository.search(..., {SearchSource source = SearchSource.typed})` adds `'source': 'VOICE'` only for voice.
- [ ] `SearchResultsController.applyVoiceQuery(text)`: `applyCriteria(criteria.copyWith(query: text))` with the next first-page request marked voice; `setQuery`, filter changes, `loadMore` and `refresh` use typed. The marker is consumed when the request starts.

### 4.4 Mobile: presentation (`lib/features/voice_search/presentation`)
- [ ] `providers/voice_search_controller.dart` with `@riverpod` (generated file committed, `dart run build_runner build --delete-conflicting-outputs`): phases `idle`, `starting`, `listening`, `finishing`, `done`, `failed`; session counter; `start`, `stop`, `cancel`, `switchLanguage`; permission flow (plugin first, then `permission_handler` for denied versus blocked; Open Settings through `openAppSettings`); `WidgetsBindingObserver` cancelling on `paused` and `inactive`; `ref.onDispose` cancels; a `speechRecognizerProvider` and a `voicePreferencesProvider` to override in tests.
- [ ] `widgets/voice_search_button.dart` (48 dp, `Icons.mic_none_rounded`, tooltip and semantic label), `voice_notice_sheet.dart` (first use; Not now returns without starting), `voice_listening_sheet.dart` (title as live region, pulsing circle respecting reduce-motion, live words, language chips, Stop, Cancel, error actions: Try again, Open Settings, switch language, Type instead).
- [ ] `search_screen.dart`: suffix `Row` with clear and the microphone; open the sheet; on `done(text)` write the field once, call `_suggestions.onSubmitted()`, unfocus, call `applyVoiceQuery`; for Type instead focus the field; a dismissed sheet cancels. Nothing is added to `_onChanged`.
- [ ] Announce "Listening" and the recognised text with `SemanticsService.announce`; no transcript in any log (`logger` writes phase and error names only).

### 4.5 Platform configuration
- [ ] `ios/Runner/Info.plist`: `NSMicrophoneUsageDescription` and `NSSpeechRecognitionUsageDescription` (English; same style as the existing strings).
- [ ] `ios/Podfile`: the permission macros confirmed in 4.1; `pod install` and an iOS simulator debug build.
- [ ] `android/app/src/main/AndroidManifest.xml`: `RECORD_AUDIO` and the `RecognitionService` `<queries>` entry; an Android debug build compiles.

### 4.6 Strings and Hindi
- [ ] New `voice*` keys in `app_en.arb` and `app_hi.arb` (button, panel title, hints, language chips, notice text, the seven error messages with their action labels, announcements); `flutter gen-l10n`. Hindi texts are drafts for native-speaker review (gap G5).
- [ ] `test/l10n` tests (same keys in both files, Hindi differs from English) and `no_hardcoded_strings_test` pass.

### 4.7 Documentation and quality
- [ ] `Documents/Manual Testing Guides/US-129-Testing-Guide.md` with the device matrix of LLD I.11.
- [ ] LLD Part I "As built" note for every deviation (I.12, same style as B.12), `Sprint-plan.md` status, and the HLD 05 and HLD 07 §6 notes listed in LLD section 8.
- [ ] `dart format lib test`, `flutter analyze`, full mobile tests with coverage above 90% for the new voice files; backend `mvn verify` with Checkstyle; SonarQube only where a server is available (none today, say so in the report).
- [ ] iOS simulator build for the UI states that do not need a microphone; the recognition itself is checked only on the real devices of 4.1.
- [ ] Ask before any commit, push or pull request.

## 5. Test Plan

Targets: above 90% line coverage for new code. Each test is mapped to the acceptance criteria and edge cases.

### 5.1 Backend (AC: metrics and validation only)
- [ ] `SearchRequestValidatorTest`: no `source`, `TYPED`, `VOICE`, lower case, blank, unknown value gives `ERROR_INVALID_FILTERS`.
- [ ] `SearchSourceTest`: `parse` cases.
- [ ] `SearchControllerTest`: `source` binding; unknown value gives 400 with the code; the envelope is unchanged.
- [ ] `ListingSearchServiceTest`: `search.requests.total` carries `source` for success, empty, rejected and rate-limited outcomes; `search.results.empty.total{source}`; the same results for `VOICE` and `TYPED`; no `source` or text in the log output.
- [ ] A check that no existing test or dashboard query depends on the untagged meters.

### 5.2 Mobile unit
- [ ] `voice_query_normalizer_test` (AC2): every phrase in English and Hindi, a command word alone stays, punctuation including `।`, mixed case, digits and currency words unchanged, 200-character cut at an emoji boundary, control characters, empty and whitespace-only input.
- [ ] `speech_to_text_recognizer_test` with the plugin faked at its platform interface (AC6 to AC8): error-name mapping table, locale resolution (`en_IN`, only `en_US`, only `en_GB`, Hindi absent), final text missing so the last partial is used, `onDevice` request according to V1.
- [ ] `voice_search_controller_test` with `FakeSpeechRecognizer` and `fake_async` (AC1 to AC9): happy path with partials, stop, `ended` without a final, every `VoiceError`, denied versus blocked, double tap, switch language while listening, stale events from an older session, late error after `done`, dispose and `paused` while listening, notice declined.
- [ ] `voice_preferences_test`: language and notice flag persistence; the notice version key.
- [ ] `search_results_controller_test` additions (AC2, AC5): `applyVoiceQuery` keeps category, intent and filters; only the first-page request is voice; edit, filter change, `loadMore` and `refresh` are typed; a stale response is still ignored.
- [ ] `search_repository_test` addition: `source=VOICE` appears only when asked; `SearchCriteria.toQueryParameters` is unchanged (so saved searches never contain it).

### 5.3 Mobile widget and screen
- [ ] Button: label, 48 dp, beside the clear button; tapping starts the flow (AC1).
- [ ] Notice shown once; Not now starts nothing; Continue proceeds.
- [ ] Panel states: starting, listening with live words, each error with its action (Try again, Open Settings, switch language, Type instead), language chips and the remembered choice, dismiss cancels, reduce-motion (AC1, AC4, AC6 to AC9).
- [ ] Search screen integration (AC2, AC3, AC5): `done` writes the field once and makes exactly one search call with `source=VOICE`; no suggestion call during partials; editing afterwards searches as typed; nothing is searched for an empty or noise-only result; a Real Estate category still shows the Buy, Rent or Lease chooser; a failing search keeps the spoken text and shows Retry.
- [ ] Hindi and English at 200% text on a small screen without overflow; the accessibility guidelines (tap target, labels, contrast) and headings tests; `no_hardcoded_strings_test`; localization key parity tests.

### 5.4 Real devices (manual, LLD I.11; recorded in the testing guide)
- [ ] Android and iPhone: English and Hindi recognition; permission denied and blocked; airplane mode with and without an on-device pack; weak network; a phone without speech services; background noise and accents; Hindi and Hinglish phrases and spoken numbers; editing before and after searching; call or app-switch interruption; TalkBack and VoiceOver; Real Estate and filter combinations.

## 6. Validation Checklist

- [ ] AC1: first use shows the notice and the permission prompts; the panel shows live words.
- [ ] AC2: the tidied text lands in the field once and results appear without another tap; leading and trailing command phrases are removed only when words remain.
- [ ] AC3: the text is editable; a new tap on the microphone speaks again.
- [ ] AC4: the default language follows the app language; switching is remembered; English prefers `en_IN`.
- [ ] AC5: category, filters and Real Estate intent are kept.
- [ ] AC6: denied and blocked permission messages; Open Settings works; typing still works.
- [ ] AC7: no speech service, language unavailable and no-network cases show the right message and a way forward.
- [ ] AC8: no recognised text means no search and a Try again action.
- [ ] AC9: leaving the screen, backgrounding, dismissing the panel and a competing microphone user all stop listening; no result is applied afterwards.
- [ ] Edge cases: long speech cut at 200, double tap, permission revoked while open, Hindi against English listings returns a normal empty state, Hinglish tested and not promised, spoken numbers searched as words, screen reader announcements, search service down keeps the text.
- [ ] Validation rules: the text is never stored or logged; audio never leaves the app for ValueX; the first-use notice names the phone's speech service; `source` accepted only as `TYPED` or `VOICE`; `SearchCriteria` and saved searches carry no `source`.
- [ ] Suggestion and search calls are not made per partial word.
- [ ] Both languages complete; 48 dp targets; 200% text; no hard-coded strings.
- [ ] Backend metrics show `source`; no migration; Checkstyle, tests and coverage pass; SonarQube result or its absence reported.
- [ ] Testing guide and LLD "As built" written; the sprint plan and story text match what was built.

## 7. Open Gaps / Questions

| # | Gap or question | Recommendation | Needed before |
|---|---|---|---|
| G1 | Product decisions V1 to V8 (LLD 9.5): offline policy, auto-search, language handling, backend scope, text tidying, privacy, Hindi matching and settings. | Accept the recommendations. V1 matters most: strict offline raises the story to 8 SP and needs native Kotlin and Swift bridges. | Step 4.1 |
| G2 | US-011 (including auto-complete and the single-screen categories) is not merged, and the voice work edits `search_screen.dart` and `SearchResultsController`, which US-011 owns. The US-011 mobile changes after the first commit are still uncommitted. | Commit and merge US-011 first and cut `feature/US-129-voice-search` from `main`; otherwise branch from `feature/US-011-browse-search-listings` and rebase after the merge. | Step 4.1 |
| G3 | `speech_to_text` and `permission_handler` behaviour in this project (versions, error names, on-device support, iOS macros with the SPM and CocoaPods mix) is not verified; the tentative design's claims came from a web answer and documentation, not from a device. | The 4.1 spike decides; the findings update this plan and LLD I.7.3. | Step 4.3 |
| G4 | Devices: at least one iPhone with Hindi enabled, one Android with Google speech services and one without. The Android emulator usually has no speech service and the iOS simulator has no Hindi model. | Provide the devices or a device lab. | Steps 4.1 and 5.4 |
| G5 | Hindi strings and the Hindi command-word list are drafts. | A native speaker reviews them (as for US-115). | Before release |
| G6 | Legal: wording of the first-use notice; Privacy Policy and app store privacy answers must mention the phone's speech services; iOS permission texts are English only unless localised `InfoPlist.strings` are added. | Legal review; decide on localised permission texts. | Before release |
| G7 | Hindi (Devanagari) queries match only Devanagari listing text; there is no transliteration or synonym layer. | Ship, measure `search.results.empty.total{source=VOICE}` and the Hindi share, then decide on a follow-up story. | After launch |
| G8 | Spoken price or condition ("under 20000") is not parsed. | Out of scope (V5); a follow-up story can add client rules or use `valuex-ai`. | After launch |
| G9 | No Figma frames exist for Search; the panel follows the design system and the existing Home and Search styles. | Product or design to confirm the panel visually in review. | Step 4.4 |
| G10 | Metric tag change: `search.requests.total` gets a `source` tag; any existing dashboard or alert on the untagged meter must be checked. | Check the dashboards with Infra before merge. | Step 4.2 |
| G11 | SonarQube is not available locally; the new code is covered by tests only. | Same limitation as US-011; report it. | End of build |

## 8. Spike Findings (to be filled in step 4.1)

_Not started. Record here: plugin version and API, locale ids, exact error names, on-device support per language and OS, `permission_handler` iOS result, behaviour without a final result, and the V1 outcome._

---

**Status:** Draft (2026-11-11). Created with the user story and the LLD Part I on the same day. Not approved: waiting for the user's review, and for G1 and G2 above. No code has been written.
