import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_state.dart';
import '../theme.dart';
import '../services/voice.dart';
import '../services/web_open_stub.dart' if (dart.library.html) '../services/web_open.dart' as webopen;
import 'meeting_sheet.dart';

class _Msg {
  final String role; // you | bot
  final String text;
  _Msg(this.role, this.text);
}

/// Project / company chat bound to the SHARED scope pool (same context the desktop,
/// agents and your other devices use). Streams the CTO's reply; persists server-side.
class ChatView extends StatefulWidget {
  final String scope;
  final String title;
  const ChatView({super.key, required this.scope, this.title = 'Chat'});
  @override
  State<ChatView> createState() => _ChatViewState();
}

class _ChatViewState extends State<ChatView> {
  final _ctrl = TextEditingController();
  final _scroll = ScrollController();
  final _voice = Voice();
  final _inputFocus = FocusNode();
  String _sttLocale = 'en_US'; // dictation language (English / Arabic)
  bool _dictating = false; // true only while a mic session should write to the box
  bool _sending = false; // re-entrancy guard so a message can't be sent twice
  // ▶ RUN NOW — trigger the project's AUTONOMOUS scheduled run (executes like the cron; does NOT stop to ask
  // approval like the interactive chat). Its output posts into THIS chat; we pull it in as it lands.
  Future<void> _runNow(String pid) async {
    if (_busy) return;
    final s = context.read<AppState>();
    setState(() {
      _msgs.add(_Msg('bot', '▶ Running the recurring task now — autonomous (it executes, no approval prompt). The result will appear here shortly.'));
      _busy = true;
    });
    _jump();
    try {
      await s.api.runNow(pid, cid: _cid ?? '');
    } catch (e) {
      if (mounted) setState(() => _msgs.add(_Msg('bot', 'Run failed: $e')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
    for (final sec in [3, 9, 16, 25]) {
      Future.delayed(Duration(seconds: sec), () { if (mounted) _reload(); });
    }
  }

  // Does THIS project own the live-meeting asset? (has a meeting/voice agent). Checks members + name +
  // description so it works whether or not the mirror carries members. Shown in BOTH chat + normal modes.
  bool _meetingCapable(AppState s, String? pid) {
    if (pid == null) return false;
    final matches = s.projects.where((p) => p.id == pid);
    if (matches.isEmpty) return false;
    final p = matches.first;
    const sig = ['meeting', 'voice', 'audio capture', 'transcription', 'streaming', 'live meeting', 'zoom'];
    final blob = ('${p.name} ${p.description} ${p.members.join(' ')}').toLowerCase();
    return sig.any((x) => blob.contains(x));
  }

  // Open the live-meeting: web embeds the served asset from the brain in a dialog; native mobile uses the
  // on-device MeetingSheet. Same button, both modes, both platforms.
  void _openMeeting(String? pid) {
    if (pid == null) return;
    if (!webopen.canOpenMonitor) {
      final s = context.read<AppState>();
      showModalBottomSheet(
        context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
        builder: (_) => MeetingSheet(pid: pid,
            buildReport: (texts, lang) => s.api.meetingReport(pid, texts, lang: lang)),
      ).then((_) { if (mounted) _reload(); });
      return;
    }
    final vt = webopen.registerMonitor(pid);
    showDialog(
      context: context, barrierDismissible: true,
      builder: (_) => Dialog(
        backgroundColor: Colors.transparent,
        insetPadding: const EdgeInsets.all(14),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(14),
          child: SizedBox(width: 840, height: 720, child: HtmlElementView(viewType: vt)),
        ),
      ),
    ).then((_) { if (mounted) _reload(); });
  }

  // Does THIS project own the reusable REPORTING asset (a reporting/SOC agent)? If so we surface the export
  // capability (PDF/DOCX/MD/PPTX) at the top of the chat — so the owner sees what they can do at a glance.
  bool _reportCapable(AppState s, String? pid) {
    if (pid == null) return false;
    final matches = s.projects.where((p) => p.id == pid);
    if (matches.isEmpty) return false;
    final p = matches.first;
    const sig = ['reporting', 'report', 'soc', 'security operations', 'redberry', 'documentation agent'];
    final blob = ('${p.name} ${p.description} ${p.members.join(' ')}').toLowerCase();
    return sig.any((x) => blob.contains(x));
  }

  // Open/download a styled report from the brain in the chosen format (Reporting agent capability).
  void _exportReport(String? pid, String fmt) {
    if (pid == null) return;
    final url = '${webopen.brainBase()}/project/report?pid=${Uri.encodeComponent(pid)}&fmt=$fmt';
    if (webopen.canOpenMonitor) {
      webopen.openReport(url);
    } else {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text('Report ($fmt): open on web/desktop, or see the latest report embedded in this chat.')));
    }
  }

  List<_Msg> _msgs = [];
  String? _cid;
  bool _busy = false, _loading = true, _speak = false, _err = false, _syncing = false, _runActive = false;
  int _limit = 200; // LAZY LOADING: render only the most recent N; "Load earlier" reveals more (long pools stay fast/cheap)

  Timer? _live; // LIVE SYNC: re-read the open scope pool every few seconds so a message written on ANY
                // device (desktop/web/mobile) appears here — WhatsApp-style — matching the desktop ChatPanel.

  @override
  void initState() {
    super.initState();
    _init();
    _live = Timer.periodic(const Duration(seconds: 5), (_) async {
      if (!mounted) return;
      if (!_busy) _reload();
      if (widget.scope.startsWith('project:')) {
        try {
          final st = await context.read<AppState>().api.runStatus(widget.scope.substring(8));
          final active = st['running'] == true;
          if (mounted && active != _runActive) setState(() => _runActive = active);
        } catch (_) {}
      }
    });
  }

  @override
  void didUpdateWidget(covariant ChatView old) {
    super.didUpdateWidget(old);
    // Scope changed under the same State (e.g. embedded view reused) → reset and load the new scope.
    if (old.scope != widget.scope) {
      _cid = null;
      _msgs = [];
      _loading = true;
      _init();
    }
  }

  Future<void> _init() async {
    final s = context.read<AppState>();
    try {
      _cid = await s.api.ensureScopeChat(widget.scope);
      await _reload();
    } catch (_) {
      _err = true;
    }
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _reload() async {
    final s = context.read<AppState>();
    if (_cid == null) return;
    // INSTANT: show the cached pool first (WhatsApp-style — no blank wait, less data), then sync fresh.
    final cached = s.poolCache[widget.scope];
    if (cached != null && cached.isNotEmpty && _msgs.isEmpty) {
      _msgs = cached
          .map((m) => _Msg(m['role'] == 'user' ? 'you' : 'bot', (m['content'] ?? '').toString()))
          .toList();
      if (mounted) setState(() {});
    }
    if (mounted) setState(() => _syncing = true);
    try {
      final raw = await s.api.scopeMessages(widget.scope, _cid!);
      // never wipe a shown conversation with an empty/stale read (mirror may be a beat behind)
      if (!(raw.isEmpty && _msgs.isNotEmpty)) {
        _msgs = raw.map((m) => _Msg(m['role'] == 'user' ? 'you' : 'bot', m['content'] ?? '')).toList();
        s.poolCache[widget.scope] =
            raw.map((m) => <String, dynamic>{'role': m['role'], 'content': m['content']}).toList();
      }
    } catch (_) {}
    if (mounted) setState(() => _syncing = false);
    _jump();
  }

  Future<void> _showSummary() async {
    final s = context.read<AppState>();
    String summary = 'Summarizing…';
    try {
      summary = await s.api.scopeSummary(widget.scope);
    } catch (_) {
      summary = 'Could not summarize right now.';
    }
    if (!mounted) return;
    showDialog(
      context: context,
      builder: (c) => AlertDialog(
        backgroundColor: Odin.panel,
        title: const Text('Chat summary'),
        content: SingleChildScrollView(child: Text(summary, style: const TextStyle(fontSize: 13))),
        actions: [TextButton(onPressed: () => Navigator.pop(c), child: const Text('Close'))],
      ),
    );
  }

  Future<void> _renameChat() async {
    if (_cid == null) return;
    final ctrl = TextEditingController(text: widget.title);
    final title = await showDialog<String>(
      context: context,
      builder: (c) => AlertDialog(
        backgroundColor: Odin.panel,
        title: const Text('Rename chat'),
        content: TextField(controller: ctrl, decoration: const InputDecoration(labelText: 'New title')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.pop(c, ctrl.text.trim()), child: const Text('Save')),
        ],
      ),
    );
    if (title == null || title.isEmpty) return;
    try {
      await context.read<AppState>().api.renameScopeChat(widget.scope, _cid!, title);
    } catch (_) {}
  }

  Future<void> _send() async {
    if (_sending) return; // guard: never fire the same send twice
    final text = _ctrl.text.trim();
    if (text.isEmpty || _busy || _cid == null) return;
    _sending = true;
    try {
      _dictating = false; // stop dictation from repopulating the box (guard, no await → can't hang the send)
      if (_voice.listening) _voice.stopListening();
      _ctrl.clear();
      setState(() {});
      await _stream(text);
    } finally {
      _sending = false;
    }
  }

  Future<void> _stream(String text) async {
    if (_busy || _cid == null) return;
    final s = context.read<AppState>();
    setState(() {
      _msgs.add(_Msg('you', text));
      _busy = true;
    });
    _jump();
    try {
      // ANCHOR MODE (web/mobile): the chat goes through the anchor queue — the engine runs on the Mac and the
      // reply comes back. NO backend connection. (Direct/streaming path below is desktop/local only.)
      if (s.isAnchorMode) {
        _msgs.add(_Msg('bot', '(sending…)'));
        final idx = _msgs.length - 1;
        try {
          final reply = await s.api.chatViaAnchor(widget.scope, text,
              onStatus: (st) { if (mounted) setState(() => _msgs[idx] = _Msg('bot', '($st…)')); });
          if (mounted) setState(() => _msgs[idx] = _Msg('bot', reply));
        } catch (e) {
          if (mounted) setState(() => _msgs[idx] = _Msg('bot', '(offline — could not reach the anchor)'));
        }
        _jump();
      } else {
      var acc = '';
      _msgs.add(_Msg('bot', ''));
      final idx = _msgs.length - 1;
      try {
        await for (final tok in s.api.streamScope(widget.scope, text, _cid!)) {
          acc += tok;
          if (mounted) setState(() => _msgs[idx] = _Msg('bot', acc));
          _jump();
        }
        await _reload();
      } catch (_) {
        await s.api.scopeSend(widget.scope, text, _cid!);
        await _reload();
      }
      }
      if (_speak && _msgs.isNotEmpty && _msgs.last.role == 'bot') _voice.speak(_msgs.last.text);
      await _maybeCapabilityGap(text);
    } catch (e) {
      setState(() => _msgs.add(_Msg('bot', '⚠️ $e')));
    } finally {
      setState(() => _busy = false);
      _jump();
    }
  }

  /// If the CTO flagged a capability gap (its persisted reply contains the marker), open the same
  /// 3-way dialog as web/desktop. Mobile-native form of the identical target. Shared pool preserved:
  /// the resolution is sent into the SAME project scope every agent reads.
  Future<void> _maybeCapabilityGap(String task) async {
    if (task.contains('⟦resolve⟧') || !widget.scope.startsWith('project:')) return;
    final last = _msgs.isNotEmpty ? _msgs.last.text : '';
    if (!last.contains("No current agent's rules fully cover this")) return;
    final pid = widget.scope.split(':')[1];
    Map<String, dynamic> opts;
    try {
      opts = await context.read<AppState>().api.capability(pid, task);
    } catch (_) {
      return;
    }
    if (!mounted) return;
    await _capabilityDialog(pid, task, opts);
  }

  Future<void> _capabilityDialog(String pid, String task, Map<String, dynamic> opts) async {
    final recommended = ((opts['recommended'] ?? []) as List).map((e) => Map<String, dynamic>.from(e)).toList();
    final editable = ((opts['editable'] ?? []) as List).map((e) => Map<String, dynamic>.from(e)).toList();
    final sug = Map<String, dynamic>.from(opts['suggestion'] ?? {});
    final overlap = sug['overlaps'] is Map ? Map<String, dynamic>.from(sug['overlaps']) : null;
    String mode = recommended.isNotEmpty ? 'existing' : 'create';
    String pick = recommended.isNotEmpty ? (recommended.first['name'] ?? '').toString() : '';
    String editPick = '';
    final nameC = TextEditingController(text: (sug['name'] ?? '').toString());
    final roleC = TextEditingController(text: (sug['role'] ?? '').toString());
    final rulesC = TextEditingController(text: (sug['rules'] ?? '').toString());
    final editRulesC = TextEditingController();

    final choice = await showDialog<Map<String, String>>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setLocal) => AlertDialog(
          backgroundColor: Odin.panelSolid,
          title: const Text('Agent can\'t do this per its rules', style: TextStyle(fontSize: 15)),
          content: SizedBox(
            width: double.maxFinite,
            child: SingleChildScrollView(
              child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('Please specify what you need for: "${task.length > 100 ? '${task.substring(0, 100)}…' : task}"',
                    style: const TextStyle(fontSize: 12, color: Odin.txtDim)),
                const SizedBox(height: 8),
                Wrap(spacing: 6, children: [
                  for (final m in const [['self', 'I\'ll do it (CTO)'], ['existing', 'Embed existing'], ['expand', 'Expand a role'], ['create', 'Create new']])
                    ChoiceChip(label: Text(m[1]), selected: mode == m[0], onSelected: (_) => setLocal(() => mode = m[0])),
                ]),
                if (mode == 'existing') ...[
                  const SizedBox(height: 8),
                  DropdownButton<String>(
                    isExpanded: true, value: pick.isEmpty ? null : pick, dropdownColor: Odin.panelSolid,
                    items: [for (final r in recommended) DropdownMenuItem(value: (r['name'] ?? '').toString(), child: Text('${r['name']} — ${r['role']}'))],
                    onChanged: (v) => setLocal(() => pick = v ?? ''),
                  ),
                ],
                if (mode == 'expand') ...[
                  const SizedBox(height: 8),
                  const Text('Expand which member\'s role?', style: TextStyle(fontSize: 12, color: Odin.txtDim)),
                  DropdownButton<String>(
                    isExpanded: true, value: editPick.isEmpty ? null : editPick, dropdownColor: Odin.panelSolid,
                    items: [for (final r in editable) DropdownMenuItem(value: (r['name'] ?? '').toString(), child: Text('${r['name']} — ${r['role']}'))],
                    onChanged: (v) => setLocal(() {
                      editPick = v ?? '';
                      final m = editable.firstWhere((x) => x['name'] == editPick, orElse: () => {});
                      editRulesC.text = (m['rules'] ?? '').toString();
                    }),
                  ),
                  const SizedBox(height: 6),
                  TextField(controller: editRulesC, minLines: 2, maxLines: 4,
                      decoration: const InputDecoration(labelText: 'Edit its role/rules to also cover this task', isDense: true, border: OutlineInputBorder())),
                ],
                if (mode == 'create') ...[
                  const SizedBox(height: 8),
                  if (overlap != null)
                    Text('⚠ ${overlap['note'] ?? ''}', style: const TextStyle(fontSize: 11, color: Odin.warn)),
                  TextField(controller: nameC, decoration: const InputDecoration(labelText: 'Name', isDense: true, border: OutlineInputBorder())),
                  const SizedBox(height: 6),
                  TextField(controller: roleC, decoration: const InputDecoration(labelText: 'Role', isDense: true, border: OutlineInputBorder())),
                  const SizedBox(height: 6),
                  TextField(controller: rulesC, minLines: 1, maxLines: 3, decoration: const InputDecoration(labelText: 'Rules / scope', isDense: true, border: OutlineInputBorder())),
                ],
              ]),
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
            FilledButton(
              onPressed: () => Navigator.pop(ctx, {
                'mode': mode, 'pick': pick, 'name': nameC.text.trim(), 'role': roleC.text.trim(), 'rules': rulesC.text.trim(),
                'editPick': editPick, 'editRules': editRulesC.text.trim(),
              }),
              child: const Text('Proceed'),
            ),
          ],
        ),
      ),
    );
    if (choice == null || !mounted) return;
    String msg;
    if (choice['mode'] == 'existing') {
      if ((choice['pick'] ?? '').isEmpty) return;
      msg = '⟦resolve⟧ Delegate this to ${choice['pick']} (they have the full shared pool): $task';
    } else if (choice['mode'] == 'create') {
      if ((choice['name'] ?? '').isEmpty || (choice['role'] ?? '').isEmpty) return;
      try {
        await context.read<AppState>().api.addAgent(pid, {
          'name': choice['name'], 'role': choice['role'],
          'description': choice['rules'], 'restrictions': (choice['rules'] ?? '').isEmpty ? [] : [choice['rules']],
        });
      } catch (_) {}
      msg = '⟦resolve⟧ Delegate this to ${choice['name']} (full shared context): $task';
    } else if (choice['mode'] == 'expand') {
      // CHOICE 3 — widen an existing member's role so it can take this task (no duplicate agent)
      if ((choice['editPick'] ?? '').isEmpty || (choice['editRules'] ?? '').isEmpty) return;
      try {
        await context.read<AppState>().api.updateAgent(pid, choice['editPick']!, {
          'description': choice['editRules'],
          'restrictions': (choice['editRules'] ?? '').isEmpty ? [] : [choice['editRules']],
        });
      } catch (_) {}
      msg = '⟦resolve⟧ Delegate this to ${choice['editPick']} (role expanded; full shared pool): $task';
    } else {
      msg = '⟦resolve⟧ Handle this yourself, CTO (you have the full shared context): $task';
    }
    await _stream(msg);
  }

  Future<void> _mic() async {
    if (_voice.listening) {
      _dictating = false;
      await _voice.stopListening();
      setState(() {});
      return;
    }
    _dictating = true;
    _ctrl.clear(); // fresh session — never echo the previous transcript
    final ok = await _voice.startListening(
      (t) {
        if (!_dictating) return; // ignore any late result after send/stop
        setState(() {
          _ctrl.text = t;
          _ctrl.selection = TextSelection.collapsed(offset: t.length);
        });
      },
      localeId: _sttLocale,
    );
    if (!ok && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Microphone/speech not available')));
    }
    setState(() {});
  }

  void _jump() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.animateTo(_scroll.position.maxScrollExtent, duration: const Duration(milliseconds: 200), curve: Curves.easeOut);
      }
    });
  }

  @override
  void dispose() {
    _live?.cancel();
    _voice.stopSpeaking();
    _inputFocus.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final s = context.read<AppState>();
    final _pid = widget.scope.startsWith('project:') ? widget.scope.substring(8) : null;
    final _recurring = _pid != null && s.projects.any((p) => p.id == _pid && (p.periodicEnabled || p.periodicLabel.isNotEmpty));
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(14, 12, 6, 4),
          child: Row(
            children: [
              Expanded(child: Text(widget.title, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w700))),
              if (_recurring)
                IconButton(
                  tooltip: 'Run now — recurring task (runs in this chat)',
                  visualDensity: VisualDensity.compact,
                  icon: _busy
                      ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Odin.ok))
                      : const Icon(Icons.play_circle_fill, size: 22, color: Odin.ok),
                  onPressed: _busy ? null : () => _runNow(_pid!),
                ),
              // 📄 REPORT EXPORT — shown for recurring/SOC/reporting projects. One-tap styled exports
              // (PDF/DOCX/MD/PPTX) — the Reporting agent's capability, surfaced at the top of the chat.
              if (_recurring || _reportCapable(s, _pid))
                PopupMenuButton<String>(
                  tooltip: 'Export report (PDF · DOCX · MD · PPTX)',
                  icon: const Icon(Icons.picture_as_pdf, size: 20, color: Odin.brand),
                  onSelected: (f) => _exportReport(_pid, f),
                  itemBuilder: (_) => const [
                    PopupMenuItem(value: 'pdf', child: Text('📄  Export PDF')),
                    PopupMenuItem(value: 'docx', child: Text('📝  Export Word (.docx)')),
                    PopupMenuItem(value: 'md', child: Text('🔖  Export Markdown')),
                    PopupMenuItem(value: 'pptx', child: Text('📊  Export PowerPoint (.pptx)')),
                  ],
                ),
              // 🎙 LIVE MEETING — shown when the project owns the asset (Zoom/meeting). Opens the dialog
              // (web: served asset from the brain; mobile: native sheet). Present in this NORMAL mode too.
              if (_meetingCapable(s, _pid))
                IconButton(
                  tooltip: 'Live meeting — voice streaming → smart report (MD/Word · AR/EN)',
                  visualDensity: VisualDensity.compact,
                  icon: const Icon(Icons.record_voice_over, size: 21, color: Odin.brand),
                  onPressed: () => _openMeeting(_pid),
                ),
              IconButton(
                tooltip: 'Voice replies',
                visualDensity: VisualDensity.compact,
                icon: Icon(_speak ? Icons.volume_up : Icons.volume_off, size: 20, color: _speak ? Odin.ok : Odin.txtFaint),
                onPressed: () async {
                  final on = !_speak;
                  setState(() => _speak = on);
                  if (on) {
                    await _voice.speak('Voice on'); // short confirm (also unlocks web audio within the tap)
                  } else {
                    _voice.stopSpeaking();
                  }
                },
              ),
              IconButton(
                tooltip: 'Reload',
                visualDensity: VisualDensity.compact,
                icon: const Icon(Icons.refresh, size: 18),
                onPressed: _loading ? null : _reload,
              ),
              // web parity: summarize this chat scope, or rename the chat
              PopupMenuButton<String>(
                tooltip: 'More',
                icon: const Icon(Icons.more_vert, size: 18),
                onSelected: (v) {
                  if (v == 'summary') _showSummary();
                  if (v == 'rename') _renameChat();
                },
                itemBuilder: (c) => const [
                  PopupMenuItem(value: 'summary', child: Text('Summarize this chat')),
                  PopupMenuItem(value: 'rename', child: Text('Rename chat')),
                ],
              ),
            ],
          ),
        ),
        // ⏳/✅ BIG RUN-STATE BANNER — unmistakable: still working, or the CTO's final answer is ready.
        if (widget.scope.startsWith('project:'))
          Builder(builder: (_) {
            final working = _busy || _runActive;
            if (working) {
              return Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 14),
                color: const Color(0x33F5A623),
                child: const Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                  SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2.4, color: Color(0xFFF5A623))),
                  SizedBox(width: 12),
                  Flexible(child: Text('⏳  WORKING — the CTO is on it. New messages appear below.',
                      style: TextStyle(fontSize: 14, fontWeight: FontWeight.w800, color: Color(0xFFF5A623)))),
                ]),
              );
            }
            if (_msgs.isNotEmpty) {
              return Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 14),
                color: const Color(0x2600C853),
                child: const Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                  Icon(Icons.check_circle, size: 20, color: Odin.ok),
                  SizedBox(width: 10),
                  Flexible(child: Text("✅  FINISHED — the CTO's final answer is below. Nothing more until you ask again.",
                      textAlign: TextAlign.center, style: TextStyle(fontSize: 14, fontWeight: FontWeight.w800, color: Odin.ok))),
                ]),
              );
            }
            return const SizedBox.shrink();
          }),
        if (_syncing && !_loading && _msgs.isNotEmpty)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(vertical: 3),
            color: const Color(0x14FFFFFF),
            child: const Row(mainAxisAlignment: MainAxisAlignment.center, children: [
              SizedBox(width: 11, height: 11, child: CircularProgressIndicator(strokeWidth: 1.6, color: Odin.brand)),
              SizedBox(width: 8),
              Text('Syncing…', style: TextStyle(fontSize: 11, color: Odin.txtFaint)),
            ]),
          ),
        Expanded(
          child: _loading
              ? const Center(child: CircularProgressIndicator(color: Odin.brand))
              : _err
                  ? const Center(child: Padding(padding: EdgeInsets.all(20), child: Text('Could not reach the chat pool. Check the brain connection in Settings.', textAlign: TextAlign.center, style: TextStyle(color: Odin.txtFaint))))
                  : _msgs.isEmpty
                      ? Center(
                          child: _syncing
                              ? const Column(mainAxisSize: MainAxisSize.min, children: [
                                  SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2, color: Odin.brand)),
                                  SizedBox(height: 10),
                                  Text('Syncing your messages…', style: TextStyle(color: Odin.txtFaint)),
                                ])
                              : Text(widget.scope == 'company' ? 'Talk to the Chief Engineer' : 'Ask the Project CTO', style: const TextStyle(color: Odin.txtFaint)))
                      : Builder(builder: (_) {
                          final start = _msgs.length > _limit ? _msgs.length - _limit : 0;
                          final hasEarlier = start > 0;
                          return ListView.builder(
                            controller: _scroll,
                            keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
                            padding: const EdgeInsets.all(12),
                            itemCount: (_msgs.length - start) + (hasEarlier ? 1 : 0),
                            itemBuilder: (_, i) {
                              if (hasEarlier && i == 0) {
                                return Center(
                                  child: TextButton.icon(
                                    onPressed: () => setState(() => _limit += 200),
                                    icon: const Icon(Icons.history, size: 16),
                                    label: Text('Load earlier ($start more)', style: const TextStyle(fontSize: 12)),
                                  ),
                                );
                              }
                              return _Bubble(msg: _msgs[start + i - (hasEarlier ? 1 : 0)]);
                            },
                          );
                        }),
        ),
        if (_busy) const LinearProgressIndicator(minHeight: 2, color: Odin.brand),
        Padding(
          padding: const EdgeInsets.all(8),
          child: Row(
            children: [
              IconButton(tooltip: 'Dictate', onPressed: _mic, icon: Icon(_voice.listening ? Icons.mic : Icons.mic_none, color: _voice.listening ? Odin.danger : Odin.txtDim)),
              InkWell(
                onTap: () => setState(() => _sttLocale = _sttLocale.startsWith('ar') ? 'en_US' : 'ar_SA'),
                borderRadius: BorderRadius.circular(6),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 8),
                  child: Text(_sttLocale.startsWith('ar') ? 'ع' : 'EN',
                      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: Odin.txtDim)),
                ),
              ),
              Expanded(
                child: TextField(
                  controller: _ctrl,
                  focusNode: _inputFocus,
                  minLines: 1,
                  maxLines: 4,
                  onTapOutside: (_) => _inputFocus.unfocus(),
                  onSubmitted: (_) => _send(),
                  decoration: const InputDecoration(hintText: 'Type a message…', border: OutlineInputBorder(), isDense: true),
                ),
              ),
              IconButton(
                tooltip: 'Hide keyboard',
                visualDensity: VisualDensity.compact,
                onPressed: () => _inputFocus.unfocus(),
                icon: const Icon(Icons.keyboard_hide_outlined, size: 20, color: Odin.txtFaint),
              ),
              const SizedBox(width: 4),
              FilledButton(
                onPressed: _busy ? null : _send,
                style: FilledButton.styleFrom(backgroundColor: Odin.brand),
                child: _busy
                    ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Icon(Icons.send, size: 18),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _Bubble extends StatelessWidget {
  final _Msg msg;
  const _Bubble({required this.msg});
  @override
  Widget build(BuildContext context) {
    final you = msg.role == 'you';
    return Align(
      alignment: you ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.all(12),
        constraints: const BoxConstraints(maxWidth: 620),
        decoration: BoxDecoration(
          color: you ? const Color(0x386C8CFF) : const Color(0x0AFFFFFF),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: you ? const Color(0x4D6C8CFF) : Odin.stroke),
        ),
        child: SelectableText(msg.text, style: const TextStyle(fontSize: 14, height: 1.5)),
      ),
    );
  }
}
