# US-129: Voice Search - Implementation Plan

## 1. Header

| Field | Value |
|---|---|
| Story | US-129 - Voice Search (a new story added to Sprint 3 on 2026-11-11) |
| Sprint | Sprint 3 - Discovery & Search |
| Story points | 5 (proposed); V1 strict-offline alternative was not selected. |
| Repos involved | valuex-mobile (about 90% of the work), valuex-backend (an optional `source` query parameter and metric tags). No `valuex-ai`, infra or database change. |
| Dependencies | US-011 (search screen, search API, `SearchCriteria`, results controller); user confirmed US-011 is merged. No other story depends on US-129. |
| Date | 2026-11-11 |
| Design source | [Sprint 3 LLD](../LLD/Sprint-3-Discovery-Search-LLD.md) Part I (I.1 to I.11) and section 9.5 (decisions V1 to V8); [tentative design by ChatGPT](../VoiceSearchTentativeDesignByChatGPT.md), adapted as explained in LLD I.3 |
| Branches (proposal) | `feature/US-129-voice-search` in `valuex-mobile` and `valuex-backend`, cut from `main` containing the merged US-011 changes |
| Flyway number | None |
| Effort | Implementation completed to the extent validated in the status below; the device spike/device QA were skipped at the user's direction and remain pending |

**Execution note (2026-11-12):** The user explicitly approved this plan and directed implementation to proceed without the physical-device spike. No real-device capability is inferred from simulator or unit-test results. Device-, OS- and locale-dependent validation remains pending; Hindi native-speaker and legal/privacy reviews remain release gates.

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
| Packages | `permission_handler` is used for permission status/settings; Riverpod 3 with `riverpod_generator`. Implementation uses `speech_to_text ^7.3.0` and direct `speech_to_text_platform_interface ^2.5.0`; pub resolves speech_to_text 7.5.0. |
| iOS config | `ios/Runner/Info.plist` has location, camera and photo strings only (no microphone or speech). `ios/Podfile` has no `GCC_PREPROCESSOR_DEFINITIONS` permission macros. Deployment target 15.0. The build uses Swift Package Manager for most plugins (one plugin, `flutter_secure_storage`, still needs CocoaPods). |
| Android config | `AndroidManifest.xml` has `INTERNET` and `ACCESS_COARSE_LOCATION`; its `<queries>` has only `PROCESS_TEXT`. `minSdk` comes from Flutter. |
| Language | `LocaleController` (`features/settings/presentation/providers/locale_controller.dart`) holds the app locale (English or Hindi); `SharedPreferences` is already used for the saved language. |
| Backend controller | `SearchController.search` takes the query parameters listed in B.4 (last is `includeFacets`); `SearchRequest` is a record of raw strings; `SearchRequestValidator.invalidFilters()` throws `ERROR_INVALID_FILTERS`; `SearchSort.parse` returns an `Optional` and is the pattern for `SearchSource.parse`. |
| Backend metrics | `ListingSearchService` increments `search.requests.total` with the tag key `result` (in `finally`) and `search.results.empty.total` without tags; `search.latency` is untagged. A meter name must always use the same tag keys, so both counters are changed together. The log line holds only result count, page and latency. |
| Plugin facts | The adapter uses partial results, 3-second pause, 20-second maximum, locale ids `en_IN`/`hi_IN`, `hasOnDeviceSupport(localeId:)` and plugin error mapping; unit tests exercise the mapping and locale selection. A physical-device spike was skipped at the user's direction. Actual device locale support, on-device availability, permission prompts and OS error behavior remain pending, not verified by these implementation details. |

## 4. Implementation Steps

### 4.1 Branches and device validation

- [x] Confirm `main` contains merged US-011; create `feature/US-129-voice-search` from `main` in mobile and backend repositories.
- [x] User decision recorded: proceed without the physical-device spike. Do not claim real-device or strict-offline validation.
- [ ] Physical-device spike and device availability matrix: pending by user direction; record results in the testing guide before release.

### 4.2 Backend (about 0.5 day)
- [x] `search/domain/SearchSource` enum (`TYPED`, `VOICE`) with `parse(String)` returning `Optional` (blank gives `TYPED`), following `SearchSort`.
- [x] `SearchRequest`: add trailing `String source`; keep the typed-call compatibility constructor.
- [x] `SearchController.search`: add optional `source`, pass it to `SearchRequest`, and document it in the API parameter notes.
- [x] `SearchRequestValidator.validate`: reject an unknown non-blank `source` with `invalidFilters()`.
- [x] `ListingSearchService`: compute a lenient source metric value once, tag both request and empty-result counters; leave latency untagged and the content-free log line unchanged.
- [x] Backend README search section documents `source` and the metric tags.
- [x] `mvn verify` and Checkstyle pass with JDK 21; no Flyway migration. 1,865 backend tests ran, 0 failures/errors, 176 environment/integration tests skipped.

### 4.3 Mobile: domain and data (`lib/features/voice_search/{domain,data}`)
- [x] Add `speech_to_text ^7.3.0` and `speech_to_text_platform_interface ^2.5.0`; resolve dependencies.
- [x] Add voice domain types, locale handling and query normalizer per LLD I.7.4.
- [x] Add the speech plugin adapter with partials, 3-second pause, 20-second maximum, locale resolution, on-device capability query/fallback and error mapping.
- [x] Add language and first-use notice preferences using the existing SharedPreferences provider.
- [x] Add `SearchSource`; repository adds `source=VOICE` only for explicit voice requests.
- [x] `SearchResultsController.applyVoiceQuery` keeps category, intent and filters and consumes the voice marker on the first-page request; subsequent edits/filter/page/refresh are typed.

### 4.4 Mobile: presentation (`lib/features/voice_search/presentation`)
- [x] Add the Riverpod voice controller, generated provider, session guards, permissions/settings actions and lifecycle cancellation. `paused` cancels; `inactive` cancels only while listening/finishing so OS permission UI does not cancel initial authorization.
- [x] Add the microphone button, first-use notice and listening/error panel with live text, language choice, Stop/Cancel and recovery actions.
- [x] Integrate the sheet and one-time recognized-text handoff into Search; typed edits and later requests stay typed, and the text field's normal `onChanged` path is not invoked for partial speech. Sheet/provider disposal owns cancellation; Search does not redundantly cancel after the modal returns.
- [x] Announce listening/final text accessibly; application logging contains no transcript.

### 4.5 Platform configuration
- [x] Add iOS microphone and speech usage descriptions and the permission macros to the CocoaPods build settings.
- [x] `pod install`; iOS simulator debug build succeeds (this does not validate microphone recognition).
- [x] Add Android `RECORD_AUDIO` and the `RecognitionService` `<queries>` entry.
- [ ] Android debug build: not run because no Android SDK is installed/configured in this macOS environment.

### 4.6 Strings and Hindi
- [x] Add voice strings in English and Hindi ARB files and generate localization code. Hindi remains draft pending native-speaker review (G5).
- [x] Localization parity and no-hardcoded-strings tests pass in the mobile suite.

### 4.7 Documentation and quality
- [x] Add the manual testing guide with the device matrix and pending release validations.
- [x] Reconcile LLD Part I/I.12, Sprint-plan status, HLD 05 and HLD 07 §6.
- [x] `dart format lib test`, `flutter analyze`, full mobile tests and coverage above 90% for new/changed non-generated mobile files; backend `mvn verify` with Checkstyle passes under JDK 21.
- [ ] Sonar scan: unavailable in this macOS environment (no local scanner/token); run on the Windows machine before merge and report findings.
- [x] iOS simulator debug build succeeds; recognition is not verified without real devices.
- [ ] Ask before any commit, push or pull request.

## 5. Test Plan

Targets: above 90% line coverage for new code. Each test is mapped to the acceptance criteria and edge cases.

### 5.1 Backend (AC: metrics and validation only)
- [x] `SearchRequestValidatorTest`: missing, supported, blank and invalid `source` cases.
- [x] `SearchSourceTest`: parse cases.
- [x] `SearchControllerTest`: `source` binding and invalid-value envelope.
- [x] `ListingSearchServiceTest`: source tags for request/empty counters and content-free logs; backend suite passes.
- [x] Dashboard impact check not required for this development phase per G10.

### 5.2 Mobile unit
- [x] `voice_query_normalizer_test` (AC2): English/Hindi phrases, punctuation, mixed case, digits, Unicode boundary, controls and empty inputs.
- [x] `speech_to_text_recognizer_test` (AC6 to AC8): error mapping, locale resolution, partial fallback and on-device capability fallback.
- [x] `voice_search_controller_test` (AC1 to AC9): lifecycle, retry, permissions, sessions, language switch, stale events and notice decline.
- [x] `voice_preferences_test`: language and notice preference persistence/version key.
- [x] `search_results_controller_test`: voice marker, preserved criteria, typed follow-on requests and stale-response handling.
- [x] `search_repository_test`: `source=VOICE` only when requested; criteria serialization remains unchanged.

### 5.3 Mobile widget and screen
- [x] Button: label and 48 dp tap target; Search screen integration test verifies the mic is present and opens the voice flow.
- [x] Notice Continue/Not now behavior and notice preference covered in widget/controller tests.
- [x] Panel starting/listening/errors/recovery/language switch and scrollability covered; real-device reduce-motion and accessibility verification remains part of the manual matrix.
- [x] Search screen integration: one `VOICE` call, no suggestion call on voice completion, and subsequent edit sends `TYPED`; controller/repository tests verify category/filter/intent preservation and the first-page marker.
- [x] English/Hindi panel at 200% text, localization parity and no-hardcoded-strings tests pass. Physical device matrix remains pending (5.4).

### 5.4 Real devices (manual, LLD I.11; recorded in the testing guide)
- [ ] Android and iPhone: English and Hindi recognition; permission denied and blocked; airplane mode with and without an on-device pack; weak network; a phone without speech services; background noise and accents; Hindi and Hinglish phrases and spoken numbers; editing before and after searching; call or app-switch interruption; TalkBack and VoiceOver; Real Estate and filter combinations.

## 6. Validation Checklist

- Automation validates the application-level behavior below. OS permission dialogs, installed speech packs, actual on-device recognition, interruptions and device accessibility remain pending in section 5.4 and the manual testing guide.
- [x] AC1: first-use notice behavior and panel live words are covered; platform permission prompts remain device-pending.
- [x] AC2: normalized text is applied once; the Search screen sends one voice query without another tap.
- [x] AC3: text remains editable and follow-up typed search is covered.
- [x] AC4: app-language default, locale resolution, switching and persistence are covered in tests.
- [x] AC5: category, filters and Real Estate intent are preserved in controller tests.
- [x] AC6: denied/blocked recovery paths and typed fallback are covered with fakes; Open Settings behavior needs device confirmation.
- [x] AC7: service/language/network recovery messages and actions are covered with fakes; actual OS service errors remain device-pending.
- [x] AC8: no recognized text yields no completed query and offers retry.
- [x] AC9: background cancellation and stale-event rejection are covered; physical call/app interruptions remain pending.
- [ ] Edge cases: long speech cut at 200, double tap, permission revoked while open, Hindi against English listings returns a normal empty state, Hinglish tested and not promised, spoken numbers searched as words, screen reader announcements, search service down keeps the text.
- [x] Validation rules: no audio/transcript persistence or application logging; `source` is metrics-only and validated; criteria/saved searches do not carry it.
- [x] Suggestion/search calls are not made per partial word; the integration test verifies a single voice request.
- [x] Both localization sets, 48 dp button, English/Hindi panel at 200% text and no-hardcoded-strings tests pass; device-level accessibility remains pending.
- [x] Backend metrics carry `source`, no migration, Maven verification and Checkstyle pass; Sonar is unavailable here and remains pending on Windows.
- [x] Testing guide, LLD "As built", HLD notes and Sprint-plan status are updated; US-129 story scope remains unchanged.

## 7. Open Gaps / Questions

| # | Gap or question | Recommendation / decision | Remaining action |
|---|---|---|---|
| G1 | Product decisions V1-V8: offline policy, auto-search, language handling, backend scope, text tidying, privacy, Hindi matching and settings. | **Resolved:** user accepted all LLD recommendations. V1 is on-device when supported, otherwise the phone's speech service may use its servers; no strict-offline native bridges. | None for approval; actual device capabilities remain pending by user direction (G3/G4). |
| G2 | US-011 is a prerequisite and shares the search screen/results flow. | **Resolved:** user confirmed US-011 has been merged; both story branches were cut from local `main`, verified against `origin/main`. | None. |
| G3 | `speech_to_text` and `permission_handler` behavior varies by device/OS and was not physically verified. | **Resolved for implementation sequencing:** user explicitly directed proceeding without the device spike. Code uses the inspected plugin API and unit tests cover locale/error mappings. | Physical device/permission/on-device validation remains pending; do not claim hardware validation. |
| G4 | Required device coverage: iPhone with Hindi, Android with Google speech services, and Android without them. | User accepted arranging devices or a device lab. | Confirm device availability for steps 4.1 and 5.4. |
| G5 | Hindi strings and the Hindi command-word list are drafts. | User accepted native-speaker review. | Obtain review before release. |
| G6 | First-use notice wording and privacy/store disclosures need review; iOS permission messages are English-only unless localized `InfoPlist.strings` are added. | User accepted legal/privacy review. | Complete review and localization decision before release. |
| G7 | Devanagari queries do not match English-only listing text; there is no transliteration or synonym layer. | **Resolved as an accepted limitation:** retain current behavior and measure voice zero-result rates after launch. | Consider a follow-up only if post-launch evidence warrants it. |
| G8 | Spoken price or condition (for example, "under 20000") is not parsed. | **Resolved as out of scope:** keep V5 behavior; any parser needs a separate design/story. | None for US-129. |
| G9 | No Figma frames exist for Search's voice panel. | User accepted following existing Home/Search styles and confirming the panel in visual review. | Include the visual confirmation in UI review; no Figma dependency. |
| G10 | `source` changes the search metric tag shape. | **Resolved for this development phase:** user reports no impact. | No dashboard/alert check is required for this implementation. |
| G11 | Sonar scan availability. | User reports Sonar scan is available on a local Windows machine; the current execution environment is macOS and has no `sonar-scanner` or `SONAR_TOKEN`. | Sonar scan cannot be run from this environment; run on the Windows machine before merge and report findings. |

## 8. Spike Findings and Unverified Device Behavior

**Product decisions:** V1-V8 confirmed by the user on 2026-11-12; recommendations accepted. The strict-offline alternative was not selected.

**Physical-device spike:** Skipped at the user's explicit direction. Device availability remains pending; no claim is made for recognition behavior on a physical device.

**Implementation API inspection (not a device spike):** Added `speech_to_text ^7.3.0` and direct `speech_to_text_platform_interface ^2.5.0`; resolved speech_to_text is 7.5.0. The installed interface exposes `hasOnDeviceSupport(localeId:)`. The adapter asks this per selected locale and requests on-device recognition when supported; if querying the capability throws, it falls back to the phone speech service. Unit tests use an injected `SpeechToText.withMethodChannel()` instance to avoid singleton initialization leaking between tests. Adapter tests cover supported/unsupported locale resolution and mapped error names; they do not prove OS behavior or locale packs are available.

**Remaining device findings:** Exact available locale ids, whether each platform actually honors on-device recognition, permission prompt/status behavior, error names emitted by real OS services, audio interruption/release behavior and final-result behavior remain to be recorded in the testing guide on the iPhone/Android matrix before release.

**iPhone test correction (2026-11-12):** The buyer reported language unavailable for both English and Hindi. Locale selection previously compared only underscore identifiers. Selection now compares identifiers case-insensitively with hyphen/underscore equivalence and passes the original platform identifier to recognition. Six regression cases cover Apple-style English/Hindi identifiers; physical recognition must be retested on the updated build.

**Validation results (2026-11-12):** Mobile `dart format lib test` completed with no changes; `flutter analyze` reported no issues; the full mobile suite passed (1,407 tests). Changed/new non-generated mobile production files have 92%–100% line coverage (generated Riverpod code is 80%). Backend `mvn verify` passed under JDK 21, including Checkstyle; 1,865 tests ran with 0 failures/errors and 176 integration tests skipped by environment. The iOS simulator debug build passed. Android debug build was not run because no Android SDK is installed/configured. SonarQube was not run because this macOS environment has no scanner/token; the user's Windows scan remains pending.

---

**Status:** Approved (2026-11-12). Implementation is on story branches. The user approved proceeding without the physical-device spike; device validation, SonarQube (Windows environment), Hindi native-speaker review and legal/privacy review remain pending. No commit, push or PR has been made.
