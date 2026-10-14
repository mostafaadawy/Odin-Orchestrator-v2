// NATIVE mobile live-meeting experience (iOS/Android). Web/desktop embed the served asset in an iframe;
// mobile can't reach the local brain directly, so here we transcribe ON-DEVICE (speech_to_text) — big mic,
// live voice sensitivity, live chunks — then send the chunk TEXTS to build the report through the anchor
// (it posts into the project chat, which syncs back). Same shape, same content, native widgets.
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:speech_to_text/speech_to_text.dart';
import 'package:speech_to_text/speech_recognition_result.dart';
import '../theme.dart';

typedef BuildReport = Future<Map<String, dynamic>> Function(List<String> texts, String lang);

class MeetingSheet extends StatefulWidget {
  final String pid;
  final BuildReport buildReport;
  const MeetingSheet({super.key, required this.pid, required this.buildReport});
  @override
  State<MeetingSheet> createState() => _MeetingSheetState();
}

class _MeetingSheetState extends State<MeetingSheet> {
  final SpeechToText _stt = SpeechToText();
  bool _listening = false, _building = false, _done = false, _viaChat = false;
  double _level = 0; // 0..1 mic sensitivity
  final List<String> _chunks = [];
  String _partial = '';
  String _lang = 'en';
  String? _reportMd;

  @override
  void dispose() {
    _listening = false;
    try { _stt.stop(); _stt.cancel(); } catch (_) {}
    super.dispose();
  }

  Future<void> _start() async {
    if (_listening) return;
    final ok = await _stt.initialize(onError: (_) {}, onStatus: (s) {
      // speech_to_text ends a session after a pause; keep going until the user taps Stop (continuous)
      if (_listening && (s == 'done' || s == 'notListening')) _listenOnce();
    });
    if (!ok) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Microphone / speech recognition not available on this device.')));
      }
      return;
    }
    setState(() { _listening = true; _chunks.clear(); _partial = ''; _reportMd = null; _done = false; });
    _listenOnce();
  }

  void _listenOnce() {
    if (!_listening) return;
    _stt.listen(
      onResult: (SpeechRecognitionResult r) {
        setState(() => _partial = r.recognizedWords);
        if (r.finalResult && r.recognizedWords.trim().isNotEmpty) {
          setState(() { _chunks.add(r.recognizedWords.trim()); _partial = ''; });
        }
      },
      onSoundLevelChange: (l) => setState(() => _level = ((l + 50) / 55).clamp(0.0, 1.0)),
      listenOptions: SpeechListenOptions(partialResults: true, cancelOnError: false,
          listenFor: const Duration(seconds: 30), pauseFor: const Duration(seconds: 4)),
    );
  }

  Future<void> _stop() async {
    _listening = false;
    try { await _stt.stop(); } catch (_) {}
    if (_partial.trim().isNotEmpty) { _chunks.add(_partial.trim()); _partial = ''; }
    if (_chunks.isEmpty) {
      setState(() { _done = true; _reportMd = 'No speech was captured. Tap “New meeting” and speak into the mic.'; });
      return;
    }
    setState(() => _building = true);
    try {
      final d = await widget.buildReport(_chunks, '');
      _viaChat = d['viaChat'] == true;
      _reportMd = d['markdown']?.toString();
      final l = d['lang']?.toString() ?? '';
      if (l.isNotEmpty) _lang = l;
    } catch (e) {
      _reportMd = 'Could not build the report: $e';
    }
    if (mounted) setState(() { _building = false; _done = true; });
  }

  void _newMeeting() => setState(() { _done = false; _chunks.clear(); _partial = ''; _reportMd = null; _level = 0; });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(18, 14, 18, 22),
      decoration: const BoxDecoration(color: Odin.panel,
          borderRadius: BorderRadius.vertical(top: Radius.circular(18))),
      child: SafeArea(top: false, child: _done ? _reportView() : _listenView()),
    );
  }

  Widget _listenView() {
    return Column(mainAxisSize: MainAxisSize.min, children: [
      Row(children: [
        const Text('🎙️  Live meeting', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16, color: Odin.txt)),
        const Spacer(),
        IconButton(onPressed: () => Navigator.of(context).pop(), icon: const Icon(Icons.close, color: Odin.txtFaint)),
      ]),
      const SizedBox(height: 6),
      // BIG mic that scales with the voice level
      AnimatedScale(
        scale: 1.0 + (_listening ? _level * 0.5 : 0),
        duration: const Duration(milliseconds: 90),
        child: Container(width: 120, height: 120, alignment: Alignment.center,
          decoration: BoxDecoration(shape: BoxShape.circle,
            color: _listening ? Odin.ok.withValues(alpha: 0.14) : Colors.white10,
            boxShadow: _listening ? [BoxShadow(color: Odin.ok.withValues(alpha: 0.35 * _level), blurRadius: 28, spreadRadius: 6 * _level)] : []),
          child: Icon(Icons.mic, size: 58, color: _listening ? Odin.ok : Odin.txtFaint)),
      ),
      const SizedBox(height: 12),
      // sensitivity bar
      ClipRRect(borderRadius: BorderRadius.circular(8),
        child: LinearProgressIndicator(value: _listening ? _level : 0, minHeight: 10,
          backgroundColor: Colors.white10, color: Odin.brand)),
      const SizedBox(height: 6),
      Text(_listening ? 'listening…  chunks ${_chunks.length}' : 'idle',
          style: const TextStyle(color: Odin.txtFaint, fontSize: 12.5)),
      if (_partial.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 4),
          child: Text('“$_partial”', maxLines: 2, overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: Odin.txtFaint, fontSize: 12, fontStyle: FontStyle.italic))),
      const SizedBox(height: 10),
      // live chunk list
      if (_chunks.isNotEmpty)
        ConstrainedBox(constraints: const BoxConstraints(maxHeight: 150),
          child: ListView(shrinkWrap: true, reverse: true, children: [
            for (int i = _chunks.length - 1; i >= 0; i--)
              Container(margin: const EdgeInsets.only(bottom: 6), padding: const EdgeInsets.all(9),
                decoration: BoxDecoration(color: Colors.white10, borderRadius: BorderRadius.circular(9)),
                child: Row(children: [
                  Container(padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                    decoration: BoxDecoration(color: Odin.ok, borderRadius: BorderRadius.circular(5)),
                    child: Text('${i + 1}', style: const TextStyle(color: Colors.black, fontSize: 10, fontWeight: FontWeight.w800))),
                  const SizedBox(width: 8),
                  Expanded(child: Text(_chunks[i], maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: Odin.txt, fontSize: 12.5))),
                ])),
          ])),
      const SizedBox(height: 12),
      if (_building)
        const Padding(padding: EdgeInsets.all(8),
          child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
            SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)),
            SizedBox(width: 10), Text('Building the report…', style: TextStyle(color: Odin.txtFaint)),
          ]))
      else
        Row(children: [
          if (!_listening)
            Expanded(child: FilledButton.icon(onPressed: _start,
                icon: const Icon(Icons.play_arrow), label: const Text('Start listening')))
          else
            Expanded(child: FilledButton.icon(
                style: FilledButton.styleFrom(backgroundColor: Odin.danger),
                onPressed: _stop, icon: const Icon(Icons.stop), label: const Text('Stop & finish'))),
        ]),
    ]);
  }

  Widget _reportView() {
    return Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        const Text('🎙️  Meeting report', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16, color: Odin.txt)),
        const Spacer(),
        IconButton(onPressed: () => Navigator.of(context).pop(), icon: const Icon(Icons.close, color: Odin.txtFaint)),
      ]),
      const SizedBox(height: 6),
      // INLINE report (parity with web/desktop) when we have the markdown; else a chat hint.
      if (_reportMd != null && _reportMd!.trim().isNotEmpty)
        Flexible(child: SingleChildScrollView(child: Directionality(
          textDirection: _lang == 'ar' ? TextDirection.rtl : TextDirection.ltr,
          child: Text(_reportMd!, style: const TextStyle(color: Odin.txt, fontSize: 13, height: 1.4)))))
      else
        Container(padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(color: Odin.ok.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(10)),
          child: const Text('✅ Report generated and posted to this project\'s chat — open the chat to read it, '
              'and export it as Word/Markdown in Arabic or English from desktop or web.',
              style: TextStyle(color: Odin.txt, fontSize: 13))),
      if (_reportMd != null && _reportMd!.trim().isNotEmpty)
        const Padding(padding: EdgeInsets.only(top: 6),
          child: Text('Also saved to the project chat. Export Word/MD (AR/EN) from desktop or web.',
              style: TextStyle(color: Odin.txtFaint, fontSize: 11))),
      const SizedBox(height: 12),
      Row(children: [
        OutlinedButton.icon(
          onPressed: () {
            final txt = _reportMd ?? _chunks.join('\n\n');
            Clipboard.setData(ClipboardData(text: txt));
            ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Copied to clipboard')));
          },
          icon: const Icon(Icons.copy, size: 18), label: const Text('Copy')),
        const SizedBox(width: 8),
        OutlinedButton.icon(onPressed: _newMeeting, icon: const Icon(Icons.refresh, size: 18), label: const Text('New')),
        const Spacer(),
        // clear, primary CLOSE — so the report is easy to dismiss (no confusion with 'New')
        FilledButton.icon(
          onPressed: () => Navigator.of(context).pop(),
          icon: const Icon(Icons.close, size: 18), label: const Text('Close')),
      ]),
    ]);
  }
}
