# Low Level Design - Sprint 14: Localization & Compliance

**Document Version:** 0.1 (US-044 implemented in `valuex-mobile`)
**Product:** ValueX (user-facing name JustQlic)
**Sprint:** Sprint 14 - Localization & Compliance
**Stories Covered in this version:** US-044
**Stories still to be designed in this document:** US-097, US-098, US-099
**Repos:** valuex-mobile (US-044 web half is a follow-up story)

**Change Log:**

| Version | Date | Change |
|---|---|---|
| 0.1 | Nov 2026 | Added Part A, US-044 Multi-Language Support (English, Hindi), mobile only. |

**Reference Documents:**
- [US-044-Implementation-Plan.md](../US-Implementation-Plans/US-044-Implementation-Plan.md)
- [HLD Part 5 - Frontend Architecture](../HLD/05-Frontend-Architecture.md) - §20 Localization
- [LLD Sprint 1](Sprint-1-Identity-User-Management-LLD.md) - §8.3 Profile menu (Language row)
- [valuex-mobile/docs/Flutter-Design-System.md](../../valuex-mobile/docs/Flutter-Design-System.md)

---

# Part A - US-044 Multi-Language Support (English, Hindi)

## A.1 Scope

The app UI is shown in English (default) or Hindi. The choice is made on **Profile → Language** or, before sign-in, on a **language chip** on Onboarding, Create Account and Sign In. It is stored on the device only (no API, no database change, no server preference). Email and SMS stay English (HLD §20). User-written content (listings, messages) is never translated; the listing "Translate" toggle and the web app are follow-up stories.

## A.2 Behaviour

- **Default.** A new install uses English. The phone's language and region are not used (`MaterialApp.locale` is always set).
- **Language screen.** Two rows (English, Hindi), each with the language name in the current app language and in its own script. A tap only marks the row; **Save Language Preference** applies it and goes back. Going back without saving drops the choice.
- **Chip and sheet.** A chip (globe and the language's own name, 48 dp) opens a bottom sheet with the same rows and Save button. The Profile route is behind the sign-in guard, so the sheet is how a signed-out user chooses.
- **Whole UI, no restart.** Saving changes `MaterialApp.locale`. The router, navigation stack and form state are not rebuilt, so switching in the middle of a flow keeps the user's place and typed text.
- **Stays.** The choice is kept after sign-out (a device preference, not account data).
- **Missing strings.** A test keeps `app_en.arb` and `app_hi.arb` on the same keys and placeholders, so no string can be missing in Hindi; `WARNING_PARTIAL_TRANSLATION` is not shown.
- **Hindi format.** Latin digits (0-9) with Hindi month names; amounts keep the `en_IN` format ("₹1,234").

## A.3 Mobile design

| Piece | File | Notes |
|---|---|---|
| Storage key | `core/constants/storage_keys.dart` | `appLanguage = 'app_language'`, value `en` or `hi` |
| Preferences | `core/storage/preferences_service.dart` | `getAppLanguage()`, `setAppLanguage(code)` |
| Languages | `features/settings/domain/supported_languages.dart` | `supportedLanguages` (locale and native name), `defaultLocale`, `localeFromCode` (null, empty or unsupported gives English), `isSupportedLocale`, `languageFor`. Adding a language is one ARB file and one entry |
| Initial value | `savedLanguageCodeProvider` (`locale_controller.dart`) | Overridden in `main()` with the saved code, read before `runApp`, so a returning Hindi user never sees an English frame |
| Locale state | `LocaleController` (`@Riverpod(keepAlive: true)`, `Notifier<Locale>`) | `select(Locale)`: ignores unsupported languages; sets state first (the UI changes at once), then saves; a failed save is logged and the language still applies for the session |
| Pending choice | `PendingLanguage` (auto-dispose) | The row marked but not saved; starts as the current language; dropped when the screen or sheet closes |
| App | `app.dart` | `locale: ref.watch(localeControllerProvider)`; `localeResolutionCallback` never returns anything but `en` or `hi` |
| Route | `RouteNames.language = '/profile/language'` | Child of Profile; in `_signedInOnlyRoutes` and the `_profileSteps` guard map |
| Screen | `language_screen.dart` | `SquareBackButton`, globe icon, title (heading), subtitle, scrollable `LanguageOptionList`, fixed footer with `LanguageSaveBar`; safe-area aware |
| Shared widgets | `widgets/language_option_list.dart`, `language_save_bar.dart`, `language_chip.dart` | Rows are mutually exclusive buttons with a "selected" state and label "{name}, selected"; tinted row and check circle (icon and text, not colour alone); at least 48 dp |
| Profile row | `profile_screen.dart` | The Language row opens `RouteNames.language` (it was "coming soon") |
| Chip placement | Onboarding (top right, over the carousel), Create Account (next to Back), Sign In (next to Back, through `AuthFormScaffold.trailing`) | No existing control moved |

### A.3.1 Strings (both ARB files)

`languageTitle`, `languageSubtitle`, `languageSave`, `languageNameEnglish`, `languageNameHindi` (first line of each row, in the app language), `languageSelected({name})`, `languageChipLabel({name})`, `languageSheetTitle`. The second line of each row (English, हिन्दी) is a constant. Hindi wording is a draft for native-speaker review (release gate).

## A.4 Design-system notes (§6.1)

Built from the Figma Make "Language options" screenshot with JustQlic tokens. Where the screenshot differed from the design system the default decision A was applied: `SquareBackButton` (not a plain arrow), `BrandGradientButton` (not a solid blue button), Poppins/DM Sans styles, `brandSurfaceTint` for the selected row, `brandMutedText` for secondary text. These await the product owner's confirmation before they go in the design-system decision log.

## A.5 Tests

`test/features/settings/` (controller, languages, preferences, Language screen, chip, sheet, persistence, sign-out, 200 % Hindi, accessibility); `test/l10n/` (key and placeholder parity, no hard-coded strings); the Language route is in `all_screens_accessibility_test.dart` and `screen_headings_test.dart`. `AppHarness` treats a platform language set before launch as a saved choice, because the app itself ignores the phone language.

## A.6 Not in this story

Web language support; the listing "Translate" toggle; region detection; server-side language preference and Hindi email/SMS; RTL; any language other than English and Hindi.
