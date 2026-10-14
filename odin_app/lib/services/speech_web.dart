// WEB text-to-speech via the browser's own Web Speech API — the SAME path that
// works in the standalone tester. We bypass flutter_tts on web because its web
// layer stalls (speak future never resolves → no audio). Mobile still uses
// flutter_tts. This file is only imported on web (conditional import).
import 'dart:html' as html;

bool get ttsSupported => html.window.speechSynthesis != null;

void webSpeak(String text, {required bool arabic}) {
  final synth = html.window.speechSynthesis;
  if (synth == null) return;
  try {
    synth.cancel(); // clear anything queued/stuck
    final u = html.SpeechSynthesisUtterance(text);
    final voices = synth.getVoices();
    final lang = arabic ? 'ar' : 'en';
    html.SpeechSynthesisVoice? match;
    for (final v in voices) {
      final vl = (v.lang ?? '').toLowerCase();
      if (vl.startsWith(lang)) { match = v; break; }
    }
    if (match != null) u.voice = match;
    u.lang = match?.lang ?? (arabic ? 'ar-SA' : 'en-US');
    u.volume = 1;
    u.rate = arabic ? 1.15 : 1.08; // faster — Arabic was too slow, English a touch quicker
    u.pitch = 1;
    synth.speak(u);
  } catch (_) {}
}

void webStopSpeak() {
  try {
    html.window.speechSynthesis?.cancel();
  } catch (_) {}
}

String webTtsDiag() {
  final s = html.window.speechSynthesis;
  if (s == null) return 'web: NO speechSynthesis';
  final v = s.getVoices();
  final en = v.where((x) => (x.lang ?? '').toLowerCase().startsWith('en')).length;
  final ar = v.where((x) => (x.lang ?? '').toLowerCase().startsWith('ar')).length;
  return 'web voices=${v.length} en=$en ar=$ar speaking=${s.speaking}';
}
