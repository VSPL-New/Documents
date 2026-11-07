# US-044: Multi-Language Support (English, Hindi) — Implementation Plan

## 1. Header

| Field | Value |
|---|---|
| Story ID | US-044 |
| Title | Multi-Language Support (English, Hindi) |
| Sprint | Sprint 14 — Localization & Compliance |
| Story Points | 5 proposed (`Sprint-plan.md` says 8 for mobile and web; web is split out, Open Gap 3). The pre-login language chip (Open Gap 9) may push it back toward 6 to 8; re-estimate when the plan is approved |
| Repos | `valuex-mobile` only. `valuex-web` has no source yet and moves to a follow-up story |
| Dependency | None |
| Branch (proposed) | `feature/US-044-multi-language-support` |

**Sprint 14 exit criterion for this story:** English (default) and Hindi supported; other Indian languages are post-MVP.

**Decisions (2026-11-07):** all open gaps are decided (section 7). In short: mobile only (web is a follow-up story) · UI localization only, no translate toggle (deferred) · English default, no region detection · no `WARNING_PARTIAL_TRANSLATION` in the UI (key-parity test instead) · Latin digits in Hindi · capped hardcoded-string audit · **language chip on the onboarding and sign-in screens as well as Profile → Language** · Hindi review is a release gate · language kept on the device only · the Language screen follows the Figma Make "Language options" screen, built in the JustQlic design system.

## 2. Story Recap

**As a** user **I want to** use the app in my preferred language **so that** I can understand content easily.

**Acceptance Criteria** (`Documents/user-stories.md`, US-044):
- In app settings, tapping "Language" shows the supported languages: English and Hindi (English is the default).
- Selecting a language changes the entire app UI to that language.
- Listings and messages stay in their original language.
- A translation option is offered for user-generated content.

**Edge Cases:** language not fully translated (missing strings) · user switches language mid-transaction · language detection based on region · RTL languages (future).

**Validation Rules:** exactly two languages (English default, Hindi) · a new install uses English until the user picks Hindi · UI text translated · user-generated content is not auto-translated · translation toggle available for listings.

**Error Scenarios:** `WARNING_PARTIAL_TRANSLATION` — "Some content not available in this language".

**Flutter notes (story):** `flutter_localizations` + `intl` with one ARB file per language · choice saved in `SharedPreferences` · locale held in Riverpod and applied without a full rebuild · only `app_en.arb` (template) and `app_hi.arb` for the MVP; adding a language later means one ARB file and one list entry.

## 3. Design Reference

There is **no Sprint 14 LLD** and no US-044 section in any LLD (Open Gap 1). The plan uses the story plus these sources:
- [HLD 05-Frontend-Architecture.md §20 Localization](../HLD/05-Frontend-Architecture.md): English default, Hindi only for MVP (decision 2026-11-06); ARB files with `flutter_localizations` and `intl`; no hardcoded strings; web format not yet decided; email and SMS stay English until a language preference is stored on the server.
- [Sprint-0-Foundation-Architecture-LLD.md §3.3](../LLD/Sprint-0-Foundation-Architecture-LLD.md): mobile layout with `core/storage/preferences_service.dart` and `l10n/app_en.arb`, `app_hi.arb`.
- [Sprint-1-Identity-User-Management-LLD.md §8.3](../LLD/Sprint-1-Identity-User-Management-LLD.md): the Profile menu has a "Language" row (Preferences, no badge) whose destination is US-044.
- [CODING_STANDARDS.md §3.3, §3.4, §3.5, §3.8, §3.9](../CODING_STANDARDS.md): Riverpod (generated providers), no hardcoded strings, 48 dp targets, GoRouter route names, localization and test rules.
- [US-115 plan](./US-115-Implementation-Plan.md): server text stays English; the app localizes from `eventType` and `params`; Hindi text needs native-speaker review before release.

**What already exists in the code (checked 2026-11-07):**
- `lib/l10n/app_en.arb` and `app_hi.arb` (581 keys each), `l10n.yaml` (template `app_en.arb`), generated `app_localizations*.dart`; `AppLocalizations.supportedLocales = [en, hi]`.
- `lib/app.dart` (`ValueXApp`) sets `localizationsDelegates` and `supportedLocales` but **no `locale`**, so the app follows the device language today. A phone set to Hindi already shows Hindi, which breaks "a new install uses English" (see decisions).
- `PreferencesService` (`getString` / `setString`) and `StorageKeys` (no language key yet).
- Profile menu: `profile_screen.dart` already has `item(Icons.language, l10n.profileLanguage)` with no `onTap`, so it shows "coming soon".
- `LogoutAction` clears only `homeLocation` and the registration flow, so the language will survive sign-out without changes there.
- Tests: `test/l10n/localization_test.dart`, `test/accessibility_test.dart` (English and Hindi at 1x and 2x text) already loop over `AppLocalizations.supportedLocales`.
- **Not present:** a `LanguageScreen` (the story says it is "already scaffolded"; it is not), a locale provider, a language route, a translation service or endpoint.

**Key design decisions (proposed; none contradict the story):**
1. **Explicit default.** `MaterialApp.locale` is always set: the saved choice, otherwise `Locale('en')`. Device language is not used (resolves the "language detection based on region" edge case in favour of the validation rule "a new install uses English"; Open Gap 5).
2. **Locale state.** One Riverpod `Notifier<Locale>` in `features/settings/` (new, small feature) with `Locale('en')` as the default; `select(Locale)` ignores unsupported codes, updates state first, then saves the language code through `PreferencesService` under a new `StorageKeys.appLanguage`. `ValueXApp` watches it, so changing language rebuilds `MaterialApp` only; the `GoRouter` instance, navigation stack and in-progress form state are untouched (covers the mid-transaction edge case).
3. **No flash of English.** The saved code is read before `runApp` (in `main.dart`) and passed to the provider as its initial value, so a returning Hindi user never sees an English frame.
4. **Local only.** The choice is stored on the device (story). It is not sent to the server and is kept after logout (it is a device preference, not account data). Email and SMS stay English (HLD §20).
5. **Language screen.** `LanguageScreen` under the Profile route (`RouteNames.language = '/profile/language'`) lists the languages from one constant (`supportedLanguages`: code, native name). Adding a language later is one ARB file plus one list entry.
   **Layout (from the Figma Make screenshot, 2026-11-07; only English and Hindi are shown, the other languages in the screenshot are ignored):**
   - Back arrow at the top left; header with a globe icon in brand blue, the title "Language" and the subtitle "Choose your preferred language"; a light divider under the header.
   - Page background `brandBackground`; one white rounded card holding the rows, separated by hairline dividers.
   - Each row has two lines: the language name in the current app language (bold, small: "English", "Hindi") and the language written in its own script (larger, muted: "English", "हिन्दी"), so a user who lands in the wrong language can still find their own. The selected row has a light blue tint and a filled blue circle with a white check at the right, and also a screen-reader "selected" state (not colour alone).
   - A fixed footer with a full-width primary button "Save Language Preference" that stays visible while the list scrolls.
   - **Choosing a row only marks it; the language changes when Save is tapped** (not on tap). Save applies and stores the language, then goes back. Going back without saving discards the pending choice. Saving with no change just goes back.
   **Design (decided 2026-11-07):** the screen is built from this design as inspiration, using only JustQlic design-system tokens and shared widgets (`AppColors`, `AppTextStyles`, `AppSpacing`, `SoftCard`, `SquareBackButton`, `BrandGradientButton` or `SingleToneButton`, 48 dp rows). Per `valuex-mobile/docs/Flutter-Design-System.md` §6.1, anything that differs from the design system is reported to the product owner as a conflict report and not applied until approved (default: the design-system token). **Likely conflicts to report** (the screenshot is the only source so far): plain back arrow vs `SquareBackButton`; solid blue Save button vs the brand gradient button; header font and weights; the selected-row tint and check circle vs existing selection styles; muted native-name grey vs `brandMutedText` contrast. The Figma Make file itself has not been read (Open Gap 12); the screenshot covers the main layout.
6. **Language chip before sign-in (Open Gap 9, decided B).** A small shared widget `LanguageChip` (the current language's native name plus a globe icon, 48 dp tap area) is shown on the onboarding screen, the Create Account screen and the Sign In (mobile) screen. It opens a bottom sheet with the same option list and the same Save button as the Language screen (one shared `LanguageOptionList` widget; Open Gap 15 asks to confirm the sheet also needs Save), because the Profile route is behind the sign-in guard. The other auth screens simply follow the chosen language; they get no chip. The choice made here is the same saved choice used by Profile → Language.
7. **User-generated content is never auto-translated** and the translate toggle is **deferred** (Open Gap 4). Listing titles, descriptions and messages render as stored.

## 4. Implementation Steps

No database, backend, AI-service or web change is needed.

### Design (first, before the Language screen code)
- [ ] Start from the screenshot layout in section 3 (decision 5) and, if Figma access is available, read the Figma Make "Language options" screen (link: <https://www.figma.com/make/tzrpUwfrR0SYeyKkv1p0co/Mobile-App-UI-Design?p=f&t=nKSVfTOM02Es0IgQ-0>) to confirm measurements. Follow `Flutter-Design-System.md` §6 (use the `nova-figma-to-code` skill when reading Figma), map the elements to existing tokens and widgets, and record the layout here.
- [ ] Run the §6.1 conflict check (colours, fonts, radii, spacing, control heights, back button, selection style). Send one conflict report to the product owner; wait for per-item decisions (A, B or C); do not code conflicting elements until approved. Non-conflicting layout can start.
- [ ] Add the decisions to the design-system decision log (§11) and list the conflicts and decisions in the PR description.

### Mobile — storage and state (`valuex-mobile`)
- [ ] Create branch `feature/US-044-multi-language-support` from `main` (design system §6 step 7).
- [ ] `core/constants/storage_keys.dart`: add `appLanguage = 'app_language'`.
- [ ] `core/storage/preferences_service.dart`: add `getAppLanguage()` / `setAppLanguage(String)` on top of `getString` / `setString` (keeps the key in one place).
- [ ] `features/settings/domain/supported_languages.dart`: `SupportedLanguage(code, nativeName)` and the list `[en: English, hi: हिन्दी]`; `defaultLocale = Locale('en')`; a helper `localeFromCode(String?)` that returns the default for `null`, empty or unsupported codes (a corrupted or removed language falls back to English).
- [ ] `features/settings/presentation/providers/locale_controller.dart`: generated Riverpod `Notifier<Locale>` (`@riverpod`, run `build_runner`); `select(Locale)` as in design decision 2; if saving fails, the UI keeps the new language for the session and the error is logged, not shown.
- [ ] `main.dart`: read the saved code before `runApp` and override the controller's initial value (decision 3). Keep the existing start-up order for the other services.
- [ ] `lib/app.dart`: `locale: ref.watch(localeControllerProvider)`; keep `supportedLocales` and the delegates; add a `localeResolutionCallback` that never returns anything but `en` or `hi` (so a stray value cannot select an unsupported locale).
- [ ] `core/utils/date_utils.dart` and `core/utils/formatters.dart`: confirm `DateFormat` and `NumberFormat` use the app locale (they use the default `Intl` locale today). Either set `Intl.defaultLocale` when the locale changes or pass the locale from the caller. Digit style in Hindi (decided): Latin digits 0–9 with Hindi month names; add a test that Hindi amounts and dates show Latin digits and Hindi month names.

### Mobile — Language screen, language chip and Profile menu
- [ ] `core/routing/route_names.dart`: add `language = '/profile/language'`; `core/routing/app_router.dart`: register it as a child of the Profile route (name `language`); `core/routing/route_guard.dart`: add it to the same `_profileSteps` map as `accountSecurity`.
- [ ] `features/settings/presentation/providers/pending_language_provider.dart`: small auto-disposed Riverpod provider holding the row chosen but not yet saved (starts as the current language); dropped when the screen or sheet closes, so going back discards it.
- [ ] `features/settings/presentation/widgets/language_option_list.dart`: the shared card of rows (from `supportedLanguages`), two lines per row (name in the app language from ARB plus native name constant), minimum 48 dp, one `Semantics` button each with "selected" state, tinted row and check circle for the chosen one (icon plus text, not colour alone). Tapping a row updates the pending choice only.
- [ ] `features/settings/presentation/widgets/language_save_bar.dart`: the fixed footer button "Save Language Preference"; on tap calls `localeController.select(pending)` then closes (screen: go back; sheet: dismiss). No loading or error state (state is synchronous).
- [ ] `features/settings/presentation/language_screen.dart`: page background `brandBackground`, back button, header (globe icon, title as `Semantics(header: true)`, subtitle), the option list in a scrollable area and the save bar in a fixed footer (safe-area padding; list scrolls at 200 % text).
- [ ] `features/settings/presentation/widgets/language_chip.dart` and `language_sheet.dart`: the chip (globe icon plus native name of the current language) and the bottom sheet that shows `LanguageOptionList` and the save bar; the sheet closes after Save. Add the chip to `onboarding_screen.dart`, `create_account_screen.dart` and `sign_in_mobile_screen.dart` without moving their existing controls; check no overlap at 200 % text in both languages.
- [ ] `profile_screen.dart`: give the Language row `onTap: () => context.push(RouteNames.language)`; show the current language's native name as the row's trailing text if the menu row widget supports it (otherwise leave as is; the check mark on the Language screen is the indicator).

### Mobile — strings (`app_en.arb` template, `app_hi.arb`)
- [ ] Add keys for the Language screen and chip: `languageTitle` ("Language"), `languageSubtitle` ("Choose your preferred language"), `languageSave` ("Save Language Preference"), `languageNameEnglish` ("English") and `languageNameHindi` ("Hindi", the name shown on the first line of each row in the app language), `languageSelected` (screen-reader text, "{name}, selected"), `languageChipLabel` (screen-reader text, "Language, {name}"), `languageSheetTitle`. The second line of each row (English, हिन्दी) is a constant shown the same in every language, not an ARB key.
- [ ] `WARNING_PARTIAL_TRANSLATION` is **not** shown in the UI (decided); no ARB key is added for it. The key-parity test below is the guard.
- [ ] Hindi wording for the new keys goes in `app_hi.arb` and is reviewed by **Abhay** (native-speaker review): a release gate (as in US-115). Set the review date before the end of Sprint 14.
- [ ] Run `flutter gen-l10n` (or `flutter pub get`) and commit the regenerated `app_localizations*.dart` as the repo already does.
- [ ] Audit for hardcoded user-facing strings in `lib/` (widgets, snackbars, semantics labels, tooltips, validators, error mapping) and move any found to the ARB files. **Cap (decided):** fix them in this story unless the audit finds more than about 20 strings or more than 3 screens; the rest are listed in the PR and become a follow-up story. The lint-style test below stops new ones.

### Deferred (not in this story)
- Translate toggle for listings and messages (Open Gap 4): needs the Item Details page (US-012/US-114) and a translation provider and privacy decision. In this story, listing and message text render as stored (already true) and nothing is auto-translated.
- Web (`valuex-web`) language support (Open Gap 3): its own story once the web stack and translation file format are chosen.
- Server-side language preference and localized email and SMS (Open Gap 11).

### Documentation
- [ ] `Documents/Manual Testing Guides/US-044-Testing-Guide.md` after implementation.
- [ ] Add a US-044 part to a new Sprint 14 LLD after the build (Open Gap 1), with the design in section 3.
- [ ] Correct the US-044 story: remove "LanguageScreen already scaffolded", remove the region-detection edge case, state that the translate toggle is deferred and `WARNING_PARTIAL_TRANSLATION` is not shown, and add the pre-login language chip. Add the Language screen entry to the design-system decision log.

## 5. Test Plan

Target above 90 % coverage for new code (`flutter test --coverage`).

Unit tests (`test/features/settings/`)
- [ ] `localeFromCode`: `en` → en, `hi` → hi, `null`, empty, `fr`, `ta`, `HI`/`hi-IN` (decide normalisation) → default en. (Validation: exactly two languages.)
- [ ] `PendingLanguage` provider: starts as the current language; choosing a row changes only the pending value; it is dropped when the screen or sheet closes (no change to the saved language).
- [ ] `LocaleController`: initial value is English with nothing saved; initial value is Hindi when saved; `select(hi)` updates state and writes `app_language = hi`; `select(Locale('fr'))` is ignored; a failing write keeps the new state.
- [ ] `PreferencesService.getAppLanguage/setAppLanguage` round trip (`SharedPreferences.setMockInitialValues`).

Widget tests
- [ ] **New install uses English:** with no saved value and the platform locale set to Hindi (`localeTestValue`), `ValueXApp` shows English. *(Fails today; proves the default.)*
- [ ] **Saved Hindi is used on start:** the first frame is Hindi.
- [ ] **Language screen:** shows exactly English and हिन्दी (two lines each); the current one is marked (tint, check, "selected" state); tapping the other row marks it but the UI language does **not** change yet; **Save** switches the screen text and the Profile page text and goes back; going back without Save changes nothing; Save with no change just goes back; the saved choice survives disposing and recreating the app (persisted); the Save button stays visible when the list scrolls and at 2x text.
- [ ] **Language chip (before sign-in):** shown on onboarding, Create Account and Sign In; opens the sheet with the same two options and Save; Save in Hindi changes the screen at once and the choice is the one Profile → Language shows after sign-in; dismissing the sheet without Save changes nothing; the chip does not overlap other controls at 2x text in English and Hindi.
- [ ] **Hindi numbers and dates:** amounts and dates use Latin digits and Hindi month names.
- [ ] **Mid-transaction:** on a form with typed text (for example the listing details form or address form), switch language from the Language screen and go back: the typed text, the step and the navigation stack are unchanged.
- [ ] **Profile menu:** the Language row opens the Language screen (no longer "coming soon").
- [ ] **Sign out keeps the language;** sign-in screens then appear in the saved language.
- [ ] **Listings and messages stay as written:** a listing and a message with English and Hindi text render unchanged in both UI languages.
- [ ] Notifications: the US-115 messages follow the selected language (existing tests keep passing).

Localization tests (extend `test/l10n/localization_test.dart`)
- [ ] `app_en.arb` and `app_hi.arb` have identical key sets and the same placeholders and plural forms (this is the guard for the "missing strings" edge case; the Hindi file must never lack a key).
- [ ] No empty values; Hindi values differ from English except for allowed identical strings (brand name, numbers, abbreviations) kept in an explicit allow-list.
- [ ] Existing "JustQlic" brand-name test covers the new keys.
- [ ] Lint-style test (or script run in CI) that no `Text('...')` literal with letters is left in `lib/features` and `lib/core` widgets (allow-list for non-user text), so new hardcoded strings fail the build.

Accessibility tests
- [ ] Add `LanguageScreen` and the language sheet to `test/accessibility_test.dart` and `test/all_screens_accessibility_test.dart` (English and Hindi, 1x and 2x text, tap targets, labelled guidelines), and `LanguageScreen` to `test/screen_headings_test.dart`; add a row to `test/core/theme/contrast_test.dart` for any new colour pair (design system §6 step 6).
- [ ] Screen reader announces the selected language and the change.
- [ ] Screenshots on the Android emulator and iOS simulator, for the product owner's review (design system §6).

Regression
- [ ] `flutter analyze` clean, `dart format` clean, full `flutter test` green (the 986-test baseline from US-115 plus new ones).

## 6. Validation Checklist

- [ ] Profile → Language lists English and Hindi only (two lines each, chosen row marked), a fixed "Save Language Preference" button applies the choice, and the screen matches the approved design (Figma Make screenshot, JustQlic tokens, conflict decisions logged).
- [ ] The language chip on onboarding, Create Account and Sign In works and shares the saved choice.
- [ ] Choosing a language changes the whole UI (every screen in the app today, including snackbars, errors, validators and dialogs) with no restart.
- [ ] A fresh install is English even on a Hindi phone; Hindi is used only after the user picks it.
- [ ] The choice survives app restart and sign-out.
- [ ] Switching language in the middle of a flow keeps the user's input and place.
- [ ] Listings and messages are shown in their original language; nothing is auto-translated; the translate toggle is not built (deferred, decided).
- [ ] Missing-string guard: the key-parity test passes; `WARNING_PARTIAL_TRANSLATION` is not shown (decided).
- [ ] Hindi text fits at 200 % text size and large fonts; no overflow on small phones.
- [ ] Dates, times and currency follow the selected language consistently, with Latin digits and Hindi month names.
- [ ] RTL: not supported and not required; no layout hardcodes `left`/`right` in the new screen (use start/end) so it stays possible later.
- [ ] Adding a third language needs only one ARB file and one list entry (checked by reading the code, not built).
- [ ] No sensitive data stored in the language preference or logged.
- [ ] Hindi wording reviewed by a native speaker before release (release gate).
- [ ] Checkstyle is not applicable; `flutter analyze`, tests and coverage pass before push; new code above 90 % coverage.

## 7. Open Gaps / Questions

All gaps were decided by the product owner on 2026-11-07.

1. **No Sprint 14 LLD.** *Decided (A):* section 3 is the design; a short "Part A: US-044" is added to a new Sprint 14 LLD after the build.
2. **Story note "LanguageScreen already scaffolded".** *Decided:* the screen is built from scratch. It takes the Figma Make "Language options" screen as inspiration (screenshot received 2026-11-07, layout in section 3, decision 5), designed within the JustQlic design system ("Design" steps). **Design source:** the screenshot (only English and Hindi are built); the Figma Make file link is also on record: <https://www.figma.com/make/tzrpUwfrR0SYeyKkv1p0co/Mobile-App-UI-Design?p=f&t=nKSVfTOM02Es0IgQ-0>, to be read at implementation start if Figma access is available.
3. **Web scope.** *Decided (A):* mobile only; web moves to a follow-up story once the web stack and translation file format are chosen. SP reduced to about 5 (see header).
4. **Translating user-generated content.** *Decided (A):* the translate toggle is deferred to a follow-up story (needs the Item Details page and a provider and privacy decision). This story only guarantees no auto-translation.
5. **Region detection.** *Decided (A):* none. English default until the user picks Hindi. This changes today's behaviour on phones set to Hindi.
6. **`WARNING_PARTIAL_TRANSLATION`.** *Decided (A):* not shown in the UI; the ARB key-parity test is the guard.
7. **Number and date style in Hindi.** *Decided (A):* Latin digits, Hindi month names.
8. **Hardcoded-string audit.** *Decided (A):* fix in this story, capped at about 20 strings or 3 screens; the rest become a follow-up; a lint-style test blocks new ones.
9. **Language choice before sign-in.** *Decided (B):* a language chip on the onboarding, Create Account and Sign In screens, opening a bottom sheet with the shared option list. Raises scope (section 3, decision 6; header SP note). **Confirmed (2026-11-07):** onboarding, Create Account and Sign In are the right three screens. **To check in Figma:** the chip's look; if the Make file has none, it follows the design system's outlined/tinted control style, subject to the §6.1 protocol.
10. **Hindi wording.** *Decided (A):* drafts now, native-speaker review is a release gate; the owner and date are to be named before the end of Sprint 14. The reviewer is **Abhay** (named 2026-11-07); the review date is still to be set before the end of Sprint 14.
11. **Server-side preference.** *Decided (A):* out of scope; device only; email and SMS stay English.

**New items from the decisions:**
12. **Figma access.** The Figma tools were not available in the planning session. The design source for now is the screenshot of the Language options screen (2026-11-07), with the Make link on record (gap 2). Exact measurements, fonts and the chip's look still need the Figma file; confirm at implementation start.
13. **Story corrections.** `user-stories.md` US-044 needs the edits listed under Documentation (region detection removed, toggle deferred, warning not shown, chip added, scaffold note removed). Not done yet; to be applied with the plan's approval.
14. **Sprint plan.** If web and the toggle are split out, `Sprint-plan.md` needs two new backlog stories (web language support; listing translation) and US-044's repo and SP updated. Not done yet.
15. **Save step (from the design).** *Decided (2026-11-07, plan approved with the proposal):* follow the design (choose, then Save); the pre-login chip sheet uses the same Save button. "Save" is added to the story's acceptance wording (see Documentation).
16. **Language names on each row.** *Decided (2026-11-07, plan approved with the proposal):* the first line is an ARB string in the app language (two new keys); the second line is a constant native name.

**Status:** Approved — approved by the user on 2026-11-07. Open Gaps 13 and 14 (story and sprint-plan edits) and the exact Figma measurements (Gap 12) are carried into implementation as listed tasks.
