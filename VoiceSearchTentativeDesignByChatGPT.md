# Flutter voice search implementation architecture

For your Flutter application, I recommend implementing voice search using Flutter + native speech recognition + your existing search API.

The objective is to add voice search without changing your existing search backend or building a separate voice-search service.

Your architecture will look like this:

## Proposed architecture

Flutter application

Search screen · Microphone · Language selector

Voice Search Controller

Manages listening, transcription, errors and lifecycle

English

en-IN

Hindi

hi-IN

Native speech recognition

Android SpeechRecognizer / Apple Speech

Transcribed search query

Editable text in existing search field

Existing Search API

Reuse current query endpoint

Search results

## 1. Recommended Flutter libraries

I would start with the following packages.

| Package | Purpose | Priority |
| --- | --- | --- |
| `speech_to_text` | Native speech recognition | Required |
| `permission_handler` | Permission management | Recommended |
| `dio` or `http` | Existing API integration | Existing |
| `provider`, `riverpod` or `bloc` | State management | Existing |
| `flutter_localizations` | Language and localization support | Optional |

### Primary package: speech\_to\_text

GitHub - csdcorp/speech\_to\_text: A Flutter plugin that exposes device specific text to speech recognition capability.

speech\_to\_text

Flutter plugin for native speech recognition

[Package documentation](<https://pub.dev/packages/speech_to_text?utm_source=chatgpt.com>)

This package provides:

- Native Android and iOS speech recognition.
- Listening callbacks.
- Partial and final transcription.
- Recognition status callbacks.
- Language selection through locale IDs.
- Error callbacks.
- Listening timeout configuration.

Important architecture decision: `speech_to_text` uses the operating system's speech recognition services. It does not guarantee fully offline recognition on every device.

If strict offline functionality is a requirement, you must separately verify on-device recognition support and consider a dedicated offline speech engine.

## 2. Platform configuration

### A. Add dependencies

Run:

bash

```bash
flutter pub add speech_to_text
flutter pub add dio
flutter pub add permission_handler
```

If your project already uses Dio or another networking library, reuse it instead of adding another dependency.

### B. Android configuration

Open:

`android/app/src/main/AndroidManifest.xml`

Add these permissions before the application element:

xml

```xml
<uses-permission
    android:name="android.permission.RECORD_AUDIO"/>

<uses-permission
    android:name="android.permission.INTERNET"/>

<queries>
    <intent>
        <action
            android:name="android.speech.RecognitionService"/>
    </intent>
</queries>
```

The queries declaration is important for Android 11 and later when discovering speech recognition services.

Dart API docs

+1

### C. iOS configuration

Open:

`ios/Runner/Info.plist`

Add:

xml

```xml
<key>NSMicrophoneUsageDescription</key>
<string>Microphone access is required
to search using your voice.</string>

<key>NSSpeechRecognitionUsageDescription</key>
<string>Speech recognition converts
your voice into search text.</string>
```

These permissions are required for the Apple Speech framework integration.

Dart API docs

+1

## 3. Implement speech recognition service

I recommend separating speech recognition from your search API.

Create this project structure:

text

```text
lib/
 ├── features/
 │    └── voice_search/
 │         ├── services/
 │         │    └── speech_service.dart
 │         ├── controllers/
 │         │    └── voice_search_controller.dart
 │         ├── widgets/
 │         │    └── voice_search_button.dart
 │         └── screens/
 │              └── search_screen.dart
 │
 ├── services/
 │    └── search_api_service.dart
 │
 └── main.dart
```

### speech\_service.dart

This service handles microphone recognition and language selection.

dart

```dart

import 'package:speech_to_text/speech_to_text.dart'
    as stt;

class SpeechService {
  final stt.SpeechToText _speech =
      stt.SpeechToText();

  bool get isListening => _speech.isListening;

  Future<bool> initialize({
    required Function(String) onStatus,
    required Function(String) onError,
  }) async {
    return await _speech.initialize(
      onStatus: onStatus,
      onError: (error) => onError(error.errorMsg),
      debugLogging: false,
    );
  }

  Future<List<stt.LocaleName>> getLanguages() async {
    return await _speech.locales();
  }

  Future<void> startListening({
    required String languageCode,
    required Function(String, bool) onResult,
  }) async {
    await _speech.listen(
      localeId: languageCode,
      listenFor: const Duration(seconds: 30),
      pauseFor: const Duration(seconds: 3),
      onResult: (result) {
        onResult(
          result.recognizedWords,
          result.finalResult,
        );
      },
    );
  }

  Future<void> stopListening() async {
    await _speech.stop();
  }

  Future<void> cancelListening() async {
    await _speech.cancel();
  }
}
```

Language configuration

Use these locale identifiers as starting candidates:

| Language | Locale ID |
| --- | --- |
| English (India) | `en_IN` |
| English (US) | `en_US` |
| Hindi (India) | `hi_IN` |

Do not assume that all three are available on every device. Query the installed locales and let the user choose an available one. The plugin documents this locale discovery mechanism.

Dart API docs

## 4. Implement voice search controller

The controller connects speech recognition with your search screen.

It should manage:

- Listening state.
- Recognized text.
- Selected language.
- Recognition errors.
- Search submission.

Example using Flutter's built-in `ChangeNotifier`:

dart

```dart

import 'package:flutter/material.dart';
import '../services/speech_service.dart';

class VoiceSearchController extends ChangeNotifier {
  final SpeechService _speechService = SpeechService();

  String recognizedText = '';
  String selectedLanguage = 'en_IN';

  bool isListening = false;
  bool isAvailable = false;
  String? errorMessage;

  Future<void> initialize() async {
    isAvailable = await _speechService.initialize(
      onStatus: (status) {
        isListening = status == 'listening';
        notifyListeners();
      },
      onError: (error) {
        errorMessage = error;
        isListening = false;
        notifyListeners();
      },
    );

    if (!isAvailable) {
      errorMessage = 'Speech recognition unavailable';
    }

    notifyListeners();
  }

  Future<void> startVoiceSearch() async {
    errorMessage = null;
    recognizedText = '';

    if (!isAvailable) {
      await initialize();
    }

    if (!isAvailable) return;

    await _speechService.startListening(
      languageCode: selectedLanguage,
      onResult: (text, isFinal) {
        recognizedText = text;
        notifyListeners();
      },
    );

    notifyListeners();
  }

  Future<void> stopVoiceSearch() async {
    await _speechService.stopListening();
  }

  void changeLanguage(String language) {
    selectedLanguage = language;
    notifyListeners();
  }

  @override
  void dispose() {
    _speechService.cancelListening();
    super.dispose();
  }
}
```

Note: This is a basic controller implementation. In production, also guard against repeated initialization, overlapping listening sessions, and widget disposal during asynchronous operations.

## 5. Integrate with your existing search API

You do not need a separate voice-search endpoint.

The voice transcription should be passed to the same API that currently accepts typed search queries.

### Example API request

Assume your existing API looks like this:

http

```http
POST /api/search
Content-Type: application/json
Authorization: Bearer <token>
```

Request body:

json

```json
{
  "query": "Find mobile phones under 20000",
  "source": "voice",
  "language": "en-IN"
}
```

For Hindi:

json

```json
{
  "query": "बीस हजार रुपये के अंदर मोबाइल फोन दिखाओ",
  "source": "voice",
  "language": "hi-IN"
}
```

### search\_api\_service.dart

dart

```dart

import 'package:dio/dio.dart';

class SearchApiService {
  final Dio _dio = Dio(
    BaseOptions(
      baseUrl: 'https://your-api-domain.com',
      connectTimeout: const Duration(seconds: 15),
      receiveTimeout: const Duration(seconds: 15),
    ),
  );

  Future<dynamic> search({
    required String query,
    required String language,
  }) async {
    if (query.trim().isEmpty) {
      throw Exception('Search query cannot be empty');
    }

    final response = await _dio.post(
      '/api/search',
      data: {
        'query': query.trim(),
        'source': 'voice',
        'language': language,
      },
    );

    return response.data;
  }
}
```

Replace the example URL, endpoint, authentication and request structure with your existing API contract.

## 6. Build the voice search UI

The UI should feel similar to a normal search box, with a microphone button and an animated listening state.

\[Flutter\] 검색창(SearchBar) 위젯 활용 예시 :: 뇌님의 관심사

La recherche vocale, une opportunité pour les e-commerce

Smart Voice Recognition App :: Behance

### search\_screen.dart

Here is a basic working UI example connecting the controller, transcription and API.

dart

```dart

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../controllers/voice_search_controller.dart';
import '../../../services/search_api_service.dart';

class SearchScreen extends StatefulWidget {
  const SearchScreen({super.key});

  @override
  State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen> {
  final TextEditingController searchController =
      TextEditingController();

  final SearchApiService api = SearchApiService();

  bool isSearching = false;

  @override
  void initState() {
    super.initState();

    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<VoiceSearchController>().initialize();
    });
  }

  Future<void> performSearch(String query) async {
    if (query.trim().isEmpty) return;

    setState(() => isSearching = true);

    try {
      final controller =
          context.read<VoiceSearchController>();

      final results = await api.search(
        query: query,
        language: controller.selectedLanguage,
      );

      debugPrint('Search results: $results');

      if (!mounted) return;

      // Replace with your existing results navigation
      // or results state update.
    } catch (e) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Search failed: $e')),
      );
    } finally {
      if (mounted) {
        setState(() => isSearching = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<VoiceSearchController>(
      builder: (context, voice, child) {
        // Keep the input synchronized with transcription.
        if (voice.recognizedText !=
            searchController.text) {
          searchController.value = TextEditingValue(
            text: voice.recognizedText,
            selection: TextSelection.collapsed(
              offset: voice.recognizedText.length,
            ),
          );
        }

        return Scaffold(
          appBar: AppBar(
            title: const Text('Voice Search'),
          ),
          body: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                Row(
                  children: [
                    const Text('Language: '),
                    DropdownButton<String>(
                      value: voice.selectedLanguage,
                      items: const [
                        DropdownMenuItem(
                          value: 'en_IN',
                          child: Text('English'),
                        ),
                        DropdownMenuItem(
                          value: 'hi_IN',
                          child: Text('Hindi'),
                        ),
                      ],
                      onChanged: (value) {
                        if (value != null) {
                          voice.changeLanguage(value);
                        }
                      },
                    ),
                  ],
                ),

                const SizedBox(height: 20),

                TextField(
                  controller: searchController,
                  decoration: InputDecoration(
                    hintText: 'Search or speak...',
                    border: const OutlineInputBorder(),
                    suffixIcon: IconButton(
                      icon: const Icon(Icons.search),
                      onPressed: isSearching
                          ? null
                          : () => performSearch(
                              searchController.text),
                    ),
                  ),
                  onSubmitted: performSearch,
                ),

                const SizedBox(height: 30),

                IconButton(
                  iconSize: 64,
                  onPressed: voice.isListening
                      ? voice.stopVoiceSearch
                      : voice.startVoiceSearch,
                  icon: Icon(
                    voice.isListening
                        ? Icons.stop_circle
                        : Icons.mic,
                    color: voice.isListening
                        ? Colors.red
                        : Colors.blue,
                  ),
                ),

                Text(
                  voice.isListening
                      ? 'Listening... Speak now'
                      : 'Tap microphone to speak',
                ),

                const SizedBox(height: 20),

                if (voice.recognizedText.isNotEmpty)
                  Text(
                    voice.recognizedText,
                    style: const TextStyle(fontSize: 18),
                  ),

                if (voice.errorMessage != null)
                  Text(
                    voice.errorMessage!,
                    style: const TextStyle(color: Colors.red),
                  ),

                const SizedBox(height: 20),

                ElevatedButton(
                  onPressed: voice.recognizedText.isEmpty ||
                          isSearching
                      ? null
                      : () => performSearch(
                          voice.recognizedText),
                  child: Text(
                    isSearching ? 'Searching...' : 'Search',
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  @override
  void dispose() {
    searchController.dispose();
    super.dispose();
  }
}
```

Add the provider at your application root:

dart

```dart
ChangeNotifierProvider(
  create: (_) => VoiceSearchController(),
  child: const MyApp(),
)
```

Add `provider` if it is not already part of your project:

bash

```bash
flutter pub add provider
```

This example keeps the search button separate from transcription so that users can correct recognition mistakes before searching.

## 7. Important: How to achieve genuinely offline speech recognition

This is the most important technical consideration in your requirements.

Native speech recognition does not automatically mean offline speech recognition.

There are differences between the platforms:

Android

Device-dependent

Android provides an on-device speech recognizer starting at API 31.

You can check availability using:

java

```java
SpeechRecognizer.isOnDeviceRecognitionAvailable(context)
```

If available, Android supports creating a recognizer specifically for on-device processing.

Android Developers

The standard `speech_to_text` plugin does not expose a general guarantee that it will select this recognizer. A native Android integration through a Flutter MethodChannel may be needed.

iOS

Device-dependent

Apple provides `SFSpeechRecognizer` and exposes `supportsOnDeviceRecognition`.

When supported, a recognition request can require on-device processing through `requiresOnDeviceRecognition`.

Apple Developer Documentation

+1

The Flutter plugin's standard interface does not expose all these native controls, so strict offline operation may require a small Swift MethodChannel implementation.

### My recommendation

You have two implementation choices:

| Approach | Complexity | Offline control |
| --- | --- | --- |
| `speech_to_text` plugin | Low | Not guaranteed |
| Native Android + Swift integration | Medium | Explicit on-device requirement |
| Dedicated offline speech engine | High | Can provide more control over models |

For your requirements, I would choose:

- Flutter for the UI and application logic.
- Native Android SpeechRecognizer with on-device mode where available.
- Apple Speech framework with on-device mode where supported.
- Flutter MethodChannel to communicate with the native implementations.
- Existing search API for retrieving results.

For devices where offline recognition or the selected language is unavailable, show a clear message rather than silently sending audio to a cloud service.

## 8. English and Hindi language handling

I recommend initially offering a manual language selector.

Voice search language

✓ English  हिन्दी

Selected recognition locale

# en\_IN

Example: Find products under 5000 rupees

Consider these requirements:

1. English speech should produce English transcription.
2. Hindi speech should produce Devanagari transcription where supported.
3. Search backend should accept Unicode text.
4. API should receive the selected language code.
5. Search results should work regardless of whether the query is typed or spoken.

One additional consideration: users may speak Hinglish, for example, "Mujhe five thousand ke under phone chahiye."

A fixed Hindi or English recognizer may not transcribe mixed-language speech reliably. Treat Hinglish as a separate test case before promising support.

## 9. Error handling and edge cases

For production, cover these scenarios:

| Scenario | Expected application behaviour |
| --- | --- |
| Microphone permission denied | Explain how to enable permission |
| Speech service unavailable | Offer typed search |
| No speech detected | Show retry option |
| Background noise | Allow user to retry |
| Recognition timeout | Preserve available transcription |
| Network unavailable | Continue transcription if offline engine is available; otherwise explain limitation |
| Empty transcription | Do not call search API |
| Wrong transcription | Allow editing |
| Language unavailable | Offer another installed language |
| API failure | Show retry without restarting voice recognition |

Also ensure microphone sessions are stopped when the user navigates away, the app enters the background, or another audio feature takes control.

## 10. Development plan

I would split implementation into five phases.

## Implementation roadmap

1. Phase 1 – Flutter integration
   Foundation- Add speech recognition package.
   - Configure Android and iOS permissions.
   - Test microphone access.
   - Retrieve supported language locales.
   Estimated: 1 day
2. Phase 2 – Speech recognition
   - Implement speech service.
   - Add English and Hindi recognition.
   - Handle partial and final transcription.
   - Build listening and stopping controls.
   Estimated: 1–2 days
3. Phase 3 – Search API integration
   - Connect recognized text to existing search API.
   - Pass language and source metadata.
   - Display results.
   - Support editing before submission.
   Estimated: 1 day
4. Phase 4 – Offline implementation
   - Implement Android on-device recognition.
   - Implement iOS on-device recognition.
   - Verify English and Hindi model availability.
   - Handle unsupported devices.
   Estimated: 2–4 days
5. Phase 5 – QA and release
   - Test different Android and iOS devices.
   - Test different accents and background noise.
   - Test permissions and offline scenarios.
   - Optimize UI and error handling.
   Estimated: 1–2 days

Estimated total

# 6–10 days

Approximate development effort for one experienced Flutter developer, assuming existing API documentation and no major native integration blockers.

## 11. Testing checklist

Before release, test on actual devices, not just emulators.

- [ ]Android: English recognition.
- [ ]Android: Hindi recognition.
- [ ]iOS: English recognition.
- [ ]iOS: Hindi recognition.
- [ ]On-device recognition with internet disabled.
- [ ]Recognition with weak internet connectivity.
- [ ]Device without an installed language model.
- [ ]Microphone permission denied.
- [ ]Background noise and different accents.
- [ ]Hindi and Hinglish queries.
- [ ]Existing API integration.
- [ ]Editing recognized text before search.

## 12. Final technical recommendation

Here is the architecture I would approve for your project:

| Layer | Recommended technology |
| --- | --- |
| UI | Flutter |
| Speech recognition interface | Dart service |
| Android recognition | Native Android SpeechRecognizer |
| iOS recognition | Apple Speech framework |
| Platform communication | Flutter MethodChannel |
| State management | Existing solution / Provider |
| API integration | Existing Dio or HTTP client |
| Search engine | Existing backend |
| Language support | English (`en-IN`), Hindi (`hi-IN`) |

One architectural decision I would make before starting development: Do not couple speech recognition with search API execution. Keep them as two independent services. This allows you to replace the speech engine later without modifying your search functionality.

## 13. One final clarification about offline requirements

1. What exactly do you mean by offline?

Strictly offline Strictly offline – speech recognition must never use cloud services

Prefer offline, cloud fallback allowed with user consent

Native recognition, internet connectivity is acceptable

2. When should the search API be called?

Automatically search after speech ends Automatically search after speech ends

Show transcription and wait for Search button

3. How should English and Hindi work?

English and Hindi separately Separate English and Hindi selection

Automatically detect English or Hindi

English, Hindi and Hinglish in the same sentence

 Finalize technical architecture

These decisions will determine whether the standard Flutter plugin is sufficient or whether we should build the native Android and iOS recognition bridges from the beginning.