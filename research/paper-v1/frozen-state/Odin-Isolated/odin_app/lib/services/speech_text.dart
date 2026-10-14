/// Turns raw chat/markdown text into clean, speakable text so the voice engine
/// never reads symbols/code as nonsense (e.g. "# **Hi**  `x=1`" must NOT be read
/// as "hash star star Hi backtick x equals one"). Engine-independent — helps the
/// native voice today and any neural voice we add later. Arabic-safe.
class SpeechText {
  /// Normalize [raw] for text-to-speech. Returns a short, natural utterance.
  static String forSpeech(String raw) {
    if (raw.trim().isEmpty) return '';
    var t = raw;

    // Fenced code blocks -> a single spoken marker (don't read the code aloud).
    t = t.replaceAllMapped(RegExp(r'```[\s\S]*?```'), (_) => ' . code block . ');
    // Inline code `like this` -> keep the words, drop the backticks.
    t = t.replaceAll('`', ' ');

    // Markdown links [text](url) -> speak the text only.
    t = t.replaceAllMapped(RegExp(r'\[([^\]]+)\]\((?:[^)]*)\)'), (m) => m.group(1) ?? '');
    // Bare URLs -> "link" (don't read the raw address character by character).
    t = t.replaceAll(RegExp(r'https?://\S+'), ' link ');

    // Images ![alt](url) -> alt text.
    t = t.replaceAllMapped(RegExp(r'!\[([^\]]*)\]\([^)]*\)'), (m) => m.group(1) ?? '');

    // Headings / blockquotes / list bullets at line starts -> just a pause.
    t = t.replaceAll(RegExp(r'^\s{0,3}#{1,6}\s*', multiLine: true), '');
    t = t.replaceAll(RegExp(r'^\s{0,3}>\s?', multiLine: true), '');
    t = t.replaceAll(RegExp(r'^\s*[-*+]\s+', multiLine: true), ', ');
    t = t.replaceAll(RegExp(r'^\s*\d+\.\s+', multiLine: true), ', ');

    // Emphasis / table pipes / stray markup characters.
    t = t.replaceAll(RegExp(r'[*_~]'), '');
    t = t.replaceAll('|', ' ');
    t = t.replaceAll(RegExp(r'^\s*[-:]{3,}\s*$', multiLine: true), ' '); // table/hr rules

    // Strip emoji and pictographic symbols (they get read as long garbage).
    t = t.replaceAll(RegExp(
        r'[\u{1F000}-\u{1FAFF}\u{2600}-\u{27BF}\u{2190}-\u{21FF}\u{2B00}-\u{2BFF}\u{FE00}-\u{FE0F}]',
        unicode: true), ' ');

    // Lone technical symbols that TTS voices announce literally -> spaces.
    // (Keep sentence punctuation . , ? ! : ; and Arabic ، ؟ so prosody stays natural.)
    t = t.replaceAll(RegExp(r'[#^={}<>\\/\[\]()@%$&+]'), ' ');

    // Collapse whitespace and tidy repeated punctuation.
    t = t.replaceAll(RegExp(r'[ \t]+'), ' ');
    t = t.replaceAll(RegExp(r'\s*\n\s*'), '. ');
    t = t.replaceAll(RegExp(r'\.\s*\.(?:\s*\.)+'), '. ');
    t = t.replaceAllMapped(RegExp(r'\s+([.,?!:;،؟])'), (m) => m.group(1)!);
    t = t.trim();

    // Cap length so a huge reply doesn't lock the voice engine for minutes.
    const maxChars = 1500;
    if (t.length > maxChars) t = '${t.substring(0, maxChars)} …';
    return t;
  }

  /// Heuristic: does the text contain Arabic script? Used to pick the voice locale.
  static bool isArabic(String s) => RegExp(r'[؀-ۿ]').hasMatch(s);
}
