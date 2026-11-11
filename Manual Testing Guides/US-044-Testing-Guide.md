# US-044 — Multi-Language Support (English, Hindi): QA Testing Guide

**Sprint 14 · Localization & Compliance**

Manual test cases for choosing the app language. The app supports **English (default) and Hindi**. A language chosen on the Language screen (or on the language chip before sign-in) changes the whole app at once, is remembered on the device, and survives sign-out. Listings and messages written by users are never translated. The product name in all text is **JustQlic**.

> **What ships (mobile only):** `features/settings/` (language list, `LocaleController`, pending choice, Language screen, language chip and sheet); `core/storage` key `app_language`; route `/profile/language`; the Profile "Language" row; the chip on Onboarding, Create Account and Sign In; new English and Hindi strings; `ValueXApp` now sets the locale itself.
> **Not in this story:** the web app, the "Translate" toggle for listings and messages (deferred until the Item Details page and a translation provider exist), the `WARNING_PARTIAL_TRANSLATION` message (a key-parity test makes a missing string impossible instead), region-based language detection, server-side language preference, Hindi email and SMS (they stay English).
> **Behaviour change:** the app no longer follows the phone's language. A new install is always English, even on a phone set to Hindi, until the user picks Hindi.
> **Hindi wording is a draft** and needs native-speaker review by **Abhay** before release (release gate).

| Setting | Value |
|---|---|
| App | `valuex-mobile`, emulator or device (`flutter run --dart-define-from-file=config/dev_android.json`, or the iOS file) |
| Storage | `SharedPreferences` key `app_language` (`en` or `hi`); absent on a fresh install |
| Languages | English `en` (default), Hindi `hi`; the second line of each row is the language in its own script ("English", "हिन्दी") |

---

## Prerequisites

1. Backend and dependencies as in `US-001-Testing-Guide.md`; an `ACTIVE` account you can sign in with.
2. A fresh install (or "Clear storage" / uninstall) for the first-run cases. Set the phone's language to **Hindi** for TC-001.
3. For TC-021, an account with a listing in My Listings.

---

## Test cases

### First run and default

| ID | Acceptance criterion / edge case | Steps | Expected |
|---|---|---|---|
| TC-001 | A new install uses English | Phone language set to Hindi; install fresh; open the app | Splash and onboarding are in **English** ("Skip", "Next"). Nothing is saved yet |
| TC-002 | Region does not matter | Repeat with phone region India and language Hindi, and with another region | Always English |

### Language screen (Profile → Language)

| ID | Acceptance criterion / edge case | Steps | Expected |
|---|---|---|---|
| TC-003 | The list shows English and Hindi only | Sign in, open Profile, tap **Language** | Back button, globe icon, title "Language", subtitle "Choose your preferred language"; two rows: "English / English" (selected: light tint and a blue check) and "Hindi / हिन्दी"; a "Save Language Preference" button fixed at the bottom. No other languages |
| TC-004 | Choosing a row does not change the app yet | Tap the Hindi row | The Hindi row is marked; every text on the screen is still English |
| TC-005 | Save changes the whole UI | Tap **Save Language Preference** | The app goes back to Profile, now in Hindi (section titles, menu rows, buttons, bottom navigation). The Language row reads "भाषा" |
| TC-006 | The choice is remembered | Close the app completely and reopen it | The splash, onboarding or home screen opens in Hindi, with no English frame first |
| TC-007 | Going back without Save | Open Language, tap another row, tap Back | Nothing changed. Open Language again: the row marked is the language still in use |
| TC-008 | Save without a change | Open Language, tap Save | Goes back; nothing changes |
| TC-009 | Switch back to English | In Hindi, open Language (भाषा), choose English, Save | The app is in English again |
| TC-010 | Sign-out keeps the language | In Hindi, sign out and sign in again | Sign In and later screens are still in Hindi |
| TC-011 | Home address and other data are untouched | Change language, return to Home | Location, cart count and listings unchanged |

### Language chip before sign-in

| ID | Acceptance criterion / edge case | Steps | Expected |
|---|---|---|---|
| TC-012 | Chip on Onboarding | Fresh install, onboarding screen | A chip "English" with a globe at the top right, clear of the Skip button and the pictures |
| TC-013 | Chip on Create Account and Sign In | Skip onboarding; open Sign In from Create Account | Chip at the top right of Create Account (next to Back) and of Sign In (next to Back) |
| TC-014 | Choose Hindi from the chip | Tap the chip; the sheet "Choose your language" opens; choose Hindi; tap Save | The sheet closes; the screen is now in Hindi and the chip reads "हिन्दी" |
| TC-015 | Dismiss without Save | Open the sheet, choose a row, swipe the sheet down | Nothing changed |
| TC-016 | Typed text is kept | On Sign In type a mobile number, switch language with the chip | The number stays; the screen stays on Sign In |
| TC-017 | Same saved choice after sign-in | Choose Hindi from the chip, sign in, open Profile → भाषा | Hindi is marked as the current language |

### Mid-transaction, content and edge cases

| ID | Acceptance criterion / edge case | Steps | Expected |
|---|---|---|---|
| TC-018 | Switch mid-transaction | Start a listing (Sell → item details), type a title; from Profile → Language switch to Hindi and Save; go back to the form | The form is where you left it with the typed text. Labels are in Hindi |
| TC-019 | Whole app is translated | In Hindi visit Home, Categories, Sell, My Listings, Notifications, Account Security, sign-in and sign-up | Every label, button, error, snackbar and dialog is Hindi (apart from names, listing text, numbers and the product name JustQlic) |
| TC-020 | Listings and messages stay as written | Open a listing and a notification the seller wrote in English while the app is in Hindi | The seller's own text is unchanged; no translate option is shown |
| TC-021 | System messages follow the language | Trigger a listing notification (see `US-115-Testing-Guide.md`) while in Hindi | The notification title and body are Hindi |
| TC-022 | Dates and money | In Hindi open Notifications, Account Security (devices), Profile details | Dates use Hindi month names with normal digits (0–9); amounts read like "₹1,234" |
| TC-023 | Missing or invalid saved value | (Developer) set `app_language` to `fr` or empty in storage and start the app | The app opens in English |
| TC-024 | Language cannot be opened when signed out | Open `/profile/language` with no session (deep link) | Sent to the sign-in flow, not the Language screen |
| TC-025 | Save fails | (Developer) make storage write fail | The language still changes for this session; it is just not remembered after restart; no error is shown |
| TC-026 | RTL | Not supported and not required | n/a |

### Accessibility and layout

| ID | Acceptance criterion / edge case | Steps | Expected |
|---|---|---|---|
| TC-027 | Large text | Phone text size at maximum; open Language and the chip sheet in English and Hindi | No clipped text; the list scrolls; "Save Language Preference" stays visible at the bottom |
| TC-028 | Small phone | Repeat on a narrow screen (320 px wide) | Same |
| TC-029 | Screen reader | TalkBack / VoiceOver: open Language | Title is read as a heading; each row is a button; the chosen row is read as "…, selected" (Hindi: "…, चयनित"); the chip reads "Language, English" |
| TC-030 | Not colour alone | Look at the chosen row | A blue check mark is shown as well as the tint |
| TC-031 | Tap targets | Rows, chip, Back and Save | Each at least 48×48 |

---

## Automated tests

```bash
cd valuex-mobile
dart format lib test && flutter analyze
flutter test test/features/settings test/l10n                       # this story
flutter test test/screen_headings_test.dart test/all_screens_accessibility_test.dart
flutter test --coverage --dart-define=SKIP_PIXEL_CONTRAST=true && tool/check_coverage.sh coverage/lcov.info 85
```

| Test file | Covers |
|---|---|
| `test/features/settings/locale_controller_test.dart` | supported languages, fallback to English, saving and reading the choice, ignoring unsupported languages, failed save, pending choice |
| `test/features/settings/language_test.dart` | new install in English on a Hindi phone, saved Hindi on first frame, Language screen (list, marked row, Save, back without Save, no change), signed-out access, chip on the three screens and the sheet, typed text kept, sign-out keeps language, 200 % text in Hindi, tap target and label guidelines, Hindi dates and money |
| `test/l10n/localization_test.dart` | same keys in `app_en.arb` and `app_hi.arb`, every placeholder used, no empty values |
| `test/l10n/no_hardcoded_strings_test.dart` | no widget shows a literal English string |

Known unrelated failure: `item_details_live_test.dart` "the page passes the tap target and label guidelines" (text contrast of the condition chips) fails locally on `main` too (CI skips pixel contrast with `SKIP_PIXEL_CONTRAST=true`) and is not part of this story.

## Design notes for review

The screen follows the Figma Make "Language options" screenshot, using JustQlic tokens. Differences from the screenshot that follow the design system (`Flutter-Design-System.md` §6.1, default decision A, awaiting the product owner's confirmation): the square Back button instead of a plain arrow; the brand-gradient Save button instead of a solid blue one; Poppins/DM Sans text styles; the selected-row tint `brandSurfaceTint` and check circle in `brandPrimary`; secondary text in `brandMutedText`.
