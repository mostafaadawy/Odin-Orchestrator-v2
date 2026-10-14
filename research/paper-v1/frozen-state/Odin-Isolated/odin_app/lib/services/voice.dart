import 'package:flutter/foundation.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:speech_to_text/speech_to_text.dart';

import 'speech_text.dart';
import 'speech_web_stub.dart' if (dart.library.html) 'speech_web.dart' as webtts;

/// Voice via the device/OS engine — works on web (Web Speech API), iOS and Android
/// with no models to ship. Every call is fully defensive: engines are created
/// LAZILY on first use (so merely opening a chat never touches native code), and
/// any platform that lacks support no-ops instead of crashing.
///
/// TTS: text is run through [SpeechText.forSpeech] first so markdown/code/symbols
/// are never read as nonsense, and the voice locale follows the script (Arabic vs
/// English). STT: the recognition locale is resolved against the installed
/// locales (English / Arabic) because reliable automatic spoken-language detection
/// is not available on-device; the format differs across web (en-US) and iOS
/// (en_US), so we look it up rather than hard-code it.
///
/// This is intentionally a thin, swappable layer: a neural on-device engine
/// (kokoro-js on web / sherpa_onnx on mobile) can later replace the TTS backend
/// here without touching any screen code.
class Voice {
  FlutterTts? _ttsInst;
  SpeechToText? _sttInst;
  bool _sttReady = false;
  List<LocaleName> _locales = const [];
  bool listening = false;

  FlutterTts get _tts => _ttsInst ??= FlutterTts();

  /// Speak [text]. Cleans markdown/symbols first and picks an Arabic or English
  /// voice from the script (or an explicit [lang]). Never throws.
  Future<void> speak(String text, {String? lang}) async {
    String clean;
    try {
      clean = SpeechText.forSpeech(text);
    } catch (_) {
      clean = text.trim(); // never let text-cleaning break anything
    }
    if (clean.isEmpty) return;
    final arabic = lang == null ? SpeechText.isArabic(clean) : lang.toLowerCase().startsWith('ar');

    // WEB: use the browser's Web Speech API directly (flutter_tts web stalls).
    if (kIsWeb) {
      webtts.webSpeak(clean, arabic: arabic);
      return;
    }

    // MOBILE (iOS/Android): the simple, original calls — no audio-session juggling
    // (that crashed the iOS simulator during playback).
    final tts = _tts;
    try { await tts.setLanguage(arabic ? 'ar-SA' : 'en-US'); } catch (_) {}
    // Faster than before — Arabic was dragging; English a touch quicker too.
    try { await tts.setSpeechRate(arabic ? 0.58 : 0.54); } catch (_) {}
    try { await tts.stop(); } catch (_) {}
    try { await tts.speak(clean); } catch (_) {}
  }

  Future<void> stopSpeaking() async {
    if (kIsWeb) {
      webtts.webStopSpeak();
      return;
    }
    try {
      await _ttsInst?.stop();
    } catch (_) {}
  }

  Future<bool> _ensureStt() async {
    if (_sttReady && _sttInst != null) return true;
    try {
      _sttInst ??= SpeechToText();
      _sttReady = await _sttInst!.initialize(onError: (_) {}, onStatus: (_) {});
      if (_sttReady) {
        try {
          _locales = await _sttInst!.locales();
        } catch (_) {
          _locales = const [];
        }
      }
    } catch (_) {
      _sttReady = false;
    }
    return _sttReady;
  }

  /// Resolve a usable localeId for the requested language across platforms.
  /// [want] may be 'en', 'ar', 'en_US', 'ar_SA', etc. Returns the installed
  /// locale that matches the language, else a sensible BCP-47 default.
  String _resolveLocale(String want) {
    final lang = want.toLowerCase().split(RegExp(r'[_-]')).first; // 'en' / 'ar'
    for (final l in _locales) {
      final id = l.localeId.toLowerCase();
      if (id.startsWith(lang)) return l.localeId; // exact platform format
    }
    return lang == 'ar' ? 'ar-SA' : 'en-US';
  }

  /// Start dictation. [onText] receives partial + final transcripts. [localeId]
  /// selects the recognition language ('en'/'ar' or a full id). The phone/browser
  /// native engine (SFSpeechRecognizer / Web Speech API) does the recognition.
  /// A FRESH session is started each time (fixes the "returns the previous
  /// message" bug caused by a stale recognizer buffer). Never throws.
  Future<bool> startListening(void Function(String) onText,
      {VoidCallback? onDone, String localeId = 'en'}) async {
    if (listening) {
      await stopListening();
    }
    if (!await _ensureStt()) return false;
    listening = true;
    try {
      await _sttInst!.listen(
        onResult: (r) => onText(r.recognizedWords),
        listenFor: const Duration(seconds: 30),
        pauseFor: const Duration(seconds: 4),
        localeId: _resolveLocale(localeId),
        listenOptions: SpeechListenOptions(partialResults: true, cancelOnError: true),
      );
    } catch (_) {
      listening = false;
      return false;
    }
    return true;
  }

  Future<void> stopListening({VoidCallback? onDone}) async {
    try {
      await _sttInst?.stop();
    } catch (_) {}
    listening = false;
    onDone?.call();
  }

  /// Cancel discards any pending final result (used on send so a late transcript
  /// can't repopulate a box we just cleared).
  Future<void> cancel() async {
    try {
      await _sttInst?.cancel();
    } catch (_) {}
    listening = false;
  }

  /// On-screen diagnostic for the web speaker (voices loaded / speaking state).
  String ttsDiag() => kIsWeb ? webtts.webTtsDiag() : 'native';

  bool get available => true; // TTS is essentially always available; STT is checked at listen time
}
