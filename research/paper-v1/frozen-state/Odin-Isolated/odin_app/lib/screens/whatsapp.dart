import 'dart:async';
import 'package:audioplayers/audioplayers.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../models/models.dart';
import '../state/app_state.dart';
import '../theme.dart';
import '../services/voice.dart';
import '../services/web_open_stub.dart' if (dart.library.html) '../services/web_open.dart' as webopen;
import 'meeting_sheet.dart';

/// WhatsApp-clone MODE: the whole app becomes a chat app. Left = a conversation list
/// (Company + every project's CTO chat, as "groups"). Open one → its pool rendered
/// WhatsApp-style (text talks to the CTO; image/camera/file/voice are group posts;
/// reply to any message). Same shared /scope pool as the normal dashboard + desktop.
class WhatsAppMode extends StatefulWidget {
  const WhatsAppMode({super.key});
  @override
  State<WhatsAppMode> createState() => _WhatsAppModeState();
}

class _WhatsAppModeState extends State<WhatsAppMode> {
  String? _scope; // selected conversation (wide layout)
  String _title = '';

  List<_Conv> _projectConvs(AppState s) {
    // SAME scope keys the desktop + orchestration use: company / project:<pid>
    final list = <_Conv>[_Conv('company', 'Company — Chief Engineer', '🏛️')];
    for (final p in s.projects) {
      list.add(_Conv('project:${p.id}', p.name, typeByKey(p.type)?.icon ?? '📁'));
    }
    return list;
  }

  List<_Conv> _chatConvs(AppState s) =>
      s.adhocChats.map((a) => _Conv(a['scope'] ?? '', a['title'] ?? 'Chat', '💬')).toList();

  Widget _sectionHeader(String label) => Padding(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 4),
        child: Text(label.toUpperCase(),
            style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: Odin.txtFaint, letterSpacing: .6)),
      );

  Widget _tile(BuildContext context, AppState s, bool wide, _Conv c) => ListTile(
        selected: wide && c.scope == _scope,
        selectedTileColor: const Color(0x146C8CFF),
        leading: CircleAvatar(backgroundColor: const Color(0x226C8CFF), child: Text(c.icon)),
        title: Text(c.title, maxLines: 1, overflow: TextOverflow.ellipsis),
        trailing: PopupMenuButton<String>(
          icon: const Icon(Icons.more_vert, size: 18, color: Odin.txtFaint),
          onSelected: (v) {
            if (v == 'open') _open(context, wide, c);
            if (v == 'clear') _clearChat(context, s, c);
          },
          itemBuilder: (_) => [
            const PopupMenuItem(value: 'open', child: Text('Open / continue')),
            const PopupMenuItem(value: 'clear', child: Text('Delete conversation')),
          ],
        ),
        onTap: () {
          if (wide) {
            setState(() { _scope = c.scope; _title = c.title; });
          } else {
            Navigator.of(context).push(MaterialPageRoute(
              builder: (_) => Scaffold(
                appBar: AppBar(title: Text(c.title)),
                body: Container(decoration: Odin.bgDecoration, child: Conversation(scope: c.scope, title: c.title)),
              ),
            ));
          }
        },
      );

  @override
  Widget build(BuildContext context) {
    final s = context.watch<AppState>();
    // NO internal list column. The ONE main sidebar (shell) drives selection (Company / a project / a chat)
    // via s.activeChatScope. Chat mode just renders that scope's conversation — same shared pool, no extra bar.
    return Conversation(
      key: ValueKey(s.activeChatScope),
      scope: s.activeChatScope,
      title: s.activeChatTitle,
    );
  }

  void _open(BuildContext ctx, bool wide, _Conv c) {
    if (wide) {
      setState(() { _scope = c.scope; _title = c.title; });
    } else {
      Navigator.of(ctx).push(MaterialPageRoute(builder: (_) => Scaffold(
        appBar: AppBar(title: Text(c.title)),
        body: Container(decoration: Odin.bgDecoration, child: Conversation(scope: c.scope, title: c.title)),
      )));
    }
  }

  Future<String?> _prompt(BuildContext ctx, String title, String label) {
    final ctrl = TextEditingController();
    return showDialog<String>(context: ctx, builder: (d) => AlertDialog(
      backgroundColor: Odin.panel,
      title: Text(title),
      content: TextField(controller: ctrl, autofocus: true, decoration: InputDecoration(labelText: label)),
      actions: [
        TextButton(onPressed: () => Navigator.pop(d), child: const Text('Cancel')),
        TextButton(onPressed: () => Navigator.pop(d, ctrl.text.trim()), child: const Text('Create')),
      ],
    ));
  }

  Future<void> _newChat(BuildContext ctx, AppState s) async {
    final name = await _prompt(ctx, 'New chat', 'Chat name');
    if (name == null || name.isEmpty) return;
    final scope = await s.newAdhocChat(name);   // creates a fresh chat thread (anchor-routed)
    if (!mounted) return;
    _open(ctx, MediaQuery.of(ctx).size.width >= 820, _Conv(scope, name, '💬'));
  }

  Future<void> _newProject(BuildContext ctx, AppState s) async {
    final name = await _prompt(ctx, 'New project', 'Project name');
    if (name == null || name.isEmpty) return;
    showDialog(context: ctx, barrierDismissible: false, builder: (_) => const Center(child: CircularProgressIndicator()));
    final err = await s.createProjectAnywhere(name);
    if (mounted) Navigator.of(ctx, rootNavigator: true).pop();
    if (err != null && mounted) {
      ScaffoldMessenger.of(ctx).showSnackBar(SnackBar(content: Text(err)));
    }
  }

  Future<void> _clearChat(BuildContext ctx, AppState s, _Conv c) async {
    final yes = await showDialog<bool>(context: ctx, builder: (d) => AlertDialog(
      backgroundColor: Odin.panel,
      title: const Text('Delete conversation'),
      content: Text('Delete all messages in "${c.title}"?'),
      actions: [
        TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Cancel')),
        TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Delete')),
      ],
    ));
    if (yes != true) return;
    await s.clearConversation(c.scope);
    if (mounted && c.scope == _scope) setState(() => _scope = null);
  }
}

class _Conv {
  final String scope;
  final String title;
  final String icon;
  _Conv(this.scope, this.title, this.icon);
}

/// One WhatsApp-style conversation over a scope pool: text → CTO (streamed),
/// image/camera/file/voice → group posts, reply to any message, audio + transcript.
class Conversation extends StatefulWidget {
  final String scope;
  final String title;
  const Conversation({super.key, required this.scope, this.title = 'Chat'});
  @override
  State<Conversation> createState() => _ConversationState();
}

class _ConversationState extends State<Conversation> {
  final _ctrl = TextEditingController();
  final _scroll = ScrollController();
  final _player = AudioPlayer();
  final _voice = Voice();
  final _inputFocus = FocusNode();
  String _sttLocale = 'en_US'; // dictation language (English / Arabic)
  bool _dictating = false; // true only while a mic session should write to the box
  bool _sending = false; // re-entrancy guard so a message can't be sent twice
  // ▶ RUN NOW — trigger the project's AUTONOMOUS scheduled run (executes like the cron; it does NOT stop to
  // ask approval like the interactive chat). Its output posts into THIS chat; we pull it in as it lands.
  Future<void> _runNow(String pid) async {
    if (_busy) return;
    final s = context.read<AppState>();
    setState(() {
      _msgs.add({'role': 'assistant', 'content': '▶ Running the recurring task now — autonomous (it executes, no approval prompt). The result will appear here shortly.', 'kind': 'text', 'sender': 'CTO'});
      _busy = true;
    });
    _jump();
    try {
      await s.api.runNow(pid, cid: _cid ?? '');
    } catch (e) {
      _snack('Run failed: $e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
    for (final sec in [3, 9, 16, 25]) {
      Future.delayed(Duration(seconds: sec), () { if (mounted) _reload(); });
    }
  }
  // Does THIS project own the live-meeting asset? True when it has an agent whose name/role matches the
  // meeting/voice-streaming signature (e.g. the Live Meeting & Voice Streaming Agent, or Audio Capture /
  // Transcription). Local check on the members the app already has — no network, works in anchor mode.
  bool _meetingCapable(AppState s) {
    if (!widget.scope.startsWith('project:')) return false;
    final pid = widget.scope.substring(8);
    final matches = s.projects.where((p) => p.id == pid);
    if (matches.isEmpty) return false;
    final p = matches.first;
    const sig = ['meeting', 'voice', 'audio capture', 'transcription', 'streaming', 'live meeting', 'zoom'];
    final blob = ('${p.name} ${p.description} ${p.members.join(' ')}').toLowerCase();
    return sig.any((x) => blob.contains(x));
  }

  // Does this project own the reusable REPORTING asset (reporting/SOC agent)? → show export capability.
  bool _reportCapable(AppState s) {
    if (!widget.scope.startsWith('project:')) return false;
    final pid = widget.scope.substring(8);
    final matches = s.projects.where((p) => p.id == pid);
    if (matches.isEmpty) return false;
    final p = matches.first;
    final recurring = p.periodicEnabled || p.periodicLabel.isNotEmpty;
    const sig = ['reporting', 'report', 'soc', 'security operations', 'redberry', 'documentation agent'];
    final blob = ('${p.name} ${p.description} ${p.members.join(' ')}').toLowerCase();
    return recurring || sig.any((x) => blob.contains(x));
  }

  // Export a styled report from the brain (Reporting agent capability): PDF/DOCX/MD/PPTX.
  void _exportReport(String pid, String fmt) {
    final url = '${webopen.brainBase()}/soc/report?pid=${Uri.encodeComponent(pid)}&fmt=$fmt';
    if (webopen.canOpenMonitor) {
      webopen.openReport(url);
    } else {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text('Report ($fmt): open on web/desktop, or see the latest report embedded in this chat.')));
    }
  }

  // Open the live-meeting asset in an IN-APP dialog (not a browser). Web embeds the served page via an
  // iframe platform-view; native mobile shows a hint (the asset runs on the brain, reachable on web/desktop).
  void _openMeeting(String pid) {
    if (!webopen.canOpenMonitor) {
      // NATIVE mobile: on-device transcription + report via the anchor (see meeting_sheet.dart)
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
      context: context,
      barrierDismissible: true,
      builder: (_) => Dialog(
        backgroundColor: Colors.transparent,
        insetPadding: const EdgeInsets.all(14),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(14),
          child: SizedBox(
            width: 840, height: 720,
            child: HtmlElementView(viewType: vt),
          ),
        ),
      ),
    ).then((_) { if (mounted) _reload(); });
  }

  List<Map<String, dynamic>> _msgs = [];
  String? _cid;
  bool _busy = false, _loading = true, _err = false, _speak = false, _syncing = false;
  int _limit = 200; // LAZY LOADING: render only the most recent N; "Load earlier" reveals more (long pools stay fast/cheap)
  Map<String, dynamic>? _replyTo;
  final Set<String> _selected = {}; // selected message ids (WhatsApp-style multi-select)
  bool _selectMode = false;

  String _line(Map<String, dynamic> m) {
    final who = (m['sender'] ?? m['role'] ?? '').toString();
    final body = (m['content'] ?? '').toString();
    final att = m['attachment'] is Map ? '[${(m['attachment'] as Map)['name']}]' : '';
    return '$who: ${body.isEmpty ? att : body}${att.isNotEmpty && body.isNotEmpty ? ' $att' : ''}';
  }

  void _toggleSel(String id) {
    setState(() {
      if (_selected.contains(id)) {
        _selected.remove(id);
      } else {
        _selected.add(id);
      }
      _selectMode = _selected.isNotEmpty;
    });
  }

  List<Map<String, dynamic>> get _selMsgs => _msgs.where((m) => _selected.contains(m['id'])).toList();

  Future<void> _copy(List<Map<String, dynamic>> msgs) async {
    await Clipboard.setData(ClipboardData(text: msgs.map(_line).join('\n')));
    _snack('Copied ${msgs.length} message(s)');
    setState(() {
      _selected.clear();
      _selectMode = false;
    });
  }

  Future<void> _deleteSelected() async {
    final s = context.read<AppState>();
    final toDel = _selMsgs;
    for (final m in toDel) {
      try {
        await s.api.deleteScopeMessage(widget.scope, (m['cid'] ?? _cid ?? '').toString(), (m['id'] ?? '').toString());
      } catch (_) {}
    }
    setState(() {
      _selected.clear();
      _selectMode = false;
    });
    await _reload();
    _snack('Deleted ${toDel.length} message(s)');
  }

  Future<void> _forwardSelected() async {
    final s = context.read<AppState>();
    final convs = <Map<String, String>>[
      {'scope': 'company', 'title': 'Company'},
      for (final p in s.projects) {'scope': 'project:${p.id}', 'title': p.name},
    ];
    final target = await showDialog<String>(
      context: context,
      builder: (_) => SimpleDialog(
        backgroundColor: Odin.panelSolid,
        title: const Text('Forward to…'),
        children: convs
            .map((c) => SimpleDialogOption(onPressed: () => Navigator.pop(context, c['scope']), child: Text(c['title']!)))
            .toList(),
      ),
    );
    if (target == null) return;
    final tcid = await s.api.ensureScopeChat(target);
    for (final m in _selMsgs) {
      await s.api.postScopeMessage(target, tcid, {
        'role': 'user',
        'content': (m['content'] ?? '').toString(),
        'sender': '$_sender (forwarded)',
        'kind': (m['kind'] ?? 'text').toString(),
        if (m['attachment'] is Map) 'attachment': m['attachment'],
      });
    }
    _snack('Forwarded ${_selMsgs.length} to $target');
    setState(() {
      _selected.clear();
      _selectMode = false;
    });
  }

  String get _sender {
    final s = context.read<AppState>();
    final email = s.authedEmail.isEmpty ? 'You' : s.authedEmail.split('@').first;
    return '$email · via Conversations'; // tag so it's recognizable in the normal view too
  }

  Timer? _live; // LIVE SYNC: poll the open scope pool so messages from any device appear WhatsApp-style.

  @override
  void initState() {
    super.initState();
    _init();
    _live = Timer.periodic(const Duration(seconds: 5), (_) { if (mounted && !_busy) _reload(); });
  }

  @override
  void didUpdateWidget(covariant Conversation old) {
    super.didUpdateWidget(old);
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
    // INSTANT: show the cached pool first (WhatsApp-style — no blank wait), then sync fresh in the background.
    final cached = s.poolCache[widget.scope];
    if (cached != null && cached.isNotEmpty && _msgs.isEmpty) {
      _msgs = List<Map<String, dynamic>>.from(cached);
      if (mounted) setState(() {});
      _jump();
    }
    if (mounted) setState(() => _syncing = true);
    try {
      final fresh = await s.api.scopeAllMessages(widget.scope);
      // NEVER wipe a shown conversation with an empty/stale read (mirror may be a beat behind).
      if (!(fresh.isEmpty && _msgs.isNotEmpty)) {
        _msgs = fresh;
        s.poolCache[widget.scope] = List<Map<String, dynamic>>.from(fresh);
      }
    } catch (_) {}
    if (mounted) setState(() => _syncing = false);
    _jump();
  }

  Future<void> _sendText() async {
    if (_sending) return; // guard: never fire the same send twice
    final text = _ctrl.text.trim();
    if (text.isEmpty || _busy || _cid == null) return;
    _sending = true;
    _dictating = false; // guard prevents refill; no await → the mic can never hang the send
    if (_voice.listening) _voice.stopListening();
    final s = context.read<AppState>();
    final reply = _replyTo?['id']?.toString();
    setState(() {
      _busy = true;
      _ctrl.clear();
      _replyTo = null;
    });
    // Same pool. A reply = a group post (tagged, no AI). A plain message talks to the CTO/team
    // (streamed) and persists — exactly the normal chat, shown here.
    try {
      if (reply != null) {
        await s.api.postScopeMessage(widget.scope, _cid!,
            {'role': 'user', 'content': text, 'sender': _sender, 'kind': 'text', 'reply_to': reply});
        await _reload();
      } else {
        _msgs.add({'role': 'user', 'content': text, 'sender': _sender, 'kind': 'text'});
        setState(() {});
        _jump();
        _msgs.add({'role': 'assistant', 'content': '…', 'kind': 'text', 'sender': 'CTO'});
        final idx = _msgs.length - 1;
        if (s.isAnchorMode) {
          // ANCHOR MODE (web/mobile): send THROUGH the anchor (engine on the Mac). Show the reply in place;
          // do NOT _reload() here (the mirror may not have synced yet, which was wiping the conversation).
          try {
            final rep = await s.api.chatViaAnchor(widget.scope, text);
            if (mounted) setState(() => _msgs[idx]['content'] = rep.isEmpty ? '(no reply)' : rep);
            if (_speak && rep.isNotEmpty) _voice.speak(rep);
          } catch (_) {
            if (mounted) setState(() => _msgs[idx]['content'] = '(offline — could not reach the anchor)');
          }
          _jump();
        } else {
          var acc = '';
          try {
            await for (final tok in s.api.streamScope(widget.scope, text, _cid!)) {
              acc += tok;
              if (mounted) setState(() => _msgs[idx]['content'] = acc);
              _jump();
            }
            if (_speak && acc.isNotEmpty) _voice.speak(acc);
            await _reload();
          } catch (_) {
            await s.api.scopeSend(widget.scope, text, _cid!);
            await _reload();
          }
        }
      }
    } catch (e) {
      _snack('Send failed: $e');
    } finally {
      _sending = false;
      if (mounted) setState(() => _busy = false);
      _jump();
    }
  }

  Future<void> _attachBytes(List<int> bytes, String name) async {
    final s = context.read<AppState>();
    final reply = _replyTo?['id']?.toString();
    setState(() {
      _busy = true;
      _replyTo = null;
    });
    try {
      final desc = await s.api.uploadScopeFile(widget.scope, bytes, name);
      await s.api.postScopeMessage(widget.scope, _cid!, {
        'role': 'user',
        'content': (desc['transcript'] ?? '').toString(),
        'sender': _sender,
        'kind': (desc['kind'] ?? 'file').toString(),
        'attachment': desc,
        if (reply != null) 'reply_to': reply,
      });
      await _reload();
    } catch (e) {
      _snack('Attach failed: $e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _pickImage(ImageSource src) async {
    try {
      final x = await ImagePicker().pickImage(source: src, imageQuality: 82);
      if (x == null) return;
      await _attachBytes(await x.readAsBytes(), x.name);
    } catch (e) {
      _snack('Camera/photos unavailable: $e');
    }
  }

  Future<void> _pickFile() async {
    try {
      final r = await FilePicker.platform.pickFiles(withData: true);
      if (r == null || r.files.isEmpty || r.files.first.bytes == null) return;
      await _attachBytes(r.files.first.bytes!, r.files.first.name);
    } catch (e) {
      _snack('File picker unavailable: $e');
    }
  }

  // MIC = dictation (speech-to-text) via the DEVICE's native engine — SFSpeechRecognizer
  // on iOS, Web Speech API in the browser. Recognized words go straight into the input;
  // nothing is sent to the backend/anchor (that path is blocked by design and was the
  // source of the "backend is not reachable" error). A fresh session each time avoids
  // echoing the previous transcript.
  Future<void> _micDictate() async {
    if (_voice.listening) {
      _dictating = false;
      await _voice.stopListening();
      setState(() {});
      return;
    }
    _dictating = true;
    _ctrl.clear();
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
    if (!ok) _snack('Microphone/speech not available on this device');
    setState(() {});
  }

  void _snack(String m) {
    if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));
  }

  void _attachSheet() {
    showModalBottomSheet(
      context: context,
      backgroundColor: Odin.panelSolid,
      builder: (_) => SafeArea(
        child: Wrap(children: [
          ListTile(leading: const Icon(Icons.photo_camera, color: Odin.brand), title: const Text('Camera'), onTap: () {
            Navigator.pop(context);
            _pickImage(ImageSource.camera);
          }),
          ListTile(leading: const Icon(Icons.photo, color: Odin.brand), title: const Text('Photo / gallery'), onTap: () {
            Navigator.pop(context);
            _pickImage(ImageSource.gallery);
          }),
          ListTile(leading: const Icon(Icons.attach_file, color: Odin.brand), title: const Text('File · doc · zip'), onTap: () {
            Navigator.pop(context);
            _pickFile();
          }),
        ]),
      ),
    );
  }

  void _jump() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.animateTo(_scroll.position.maxScrollExtent, duration: const Duration(milliseconds: 200), curve: Curves.easeOut);
      }
    });
  }

  Map<String, dynamic>? _byId(String? id) {
    if (id == null) return null;
    for (final m in _msgs) {
      if (m['id'] == id) return m;
    }
    return null;
  }

  @override
  void dispose() {
    _live?.cancel();
    _player.dispose();
    _voice.stopSpeaking();
    _inputFocus.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final s = context.read<AppState>();
    return Column(
      children: [
        // action bar: select-mode toolbar (copy/forward/delete/reply) OR copy-all/export + reload
        Padding(
          padding: const EdgeInsets.fromLTRB(8, 6, 8, 0),
          child: _selectMode
              ? Row(children: [
                  IconButton(visualDensity: VisualDensity.compact, icon: const Icon(Icons.close), onPressed: () => setState(() { _selected.clear(); _selectMode = false; })),
                  Text('${_selected.length} selected', style: const TextStyle(fontSize: 13)),
                  const Spacer(),
                  if (_selected.length == 1)
                    IconButton(tooltip: 'Reply', visualDensity: VisualDensity.compact, icon: const Icon(Icons.reply), onPressed: () => setState(() { _replyTo = _selMsgs.first; _selected.clear(); _selectMode = false; })),
                  IconButton(tooltip: 'Copy', visualDensity: VisualDensity.compact, icon: const Icon(Icons.copy), onPressed: () => _copy(_selMsgs)),
                  IconButton(tooltip: 'Forward', visualDensity: VisualDensity.compact, icon: const Icon(Icons.forward), onPressed: _forwardSelected),
                  IconButton(tooltip: 'Delete', visualDensity: VisualDensity.compact, icon: const Icon(Icons.delete_outline, color: Odin.danger), onPressed: _deleteSelected),
                ])
              : Row(children: [
                  const Icon(Icons.forum_outlined, size: 16, color: Odin.brand2),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(widget.title,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14)),
                  ),
                  if (_syncing)
                    const Padding(
                      padding: EdgeInsets.only(right: 6),
                      child: SizedBox(width: 13, height: 13, child: CircularProgressIndicator(strokeWidth: 1.6, color: Odin.brand)),
                    ),
                  if (widget.scope.startsWith('project:') &&
                      s.projects.any((p) => p.id == widget.scope.substring(8) && (p.periodicEnabled || p.periodicLabel.isNotEmpty)))
                    IconButton(
                      tooltip: 'Run now — recurring task (runs in this chat)',
                      visualDensity: VisualDensity.compact,
                      icon: _busy
                          ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Odin.ok))
                          : const Icon(Icons.play_circle_fill, size: 22, color: Odin.ok),
                      onPressed: _busy ? null : () => _runNow(widget.scope.substring(8)),
                    ),
                  // 📄 REPORT EXPORT — recurring/SOC/reporting projects get one-tap styled exports at the top.
                  if (widget.scope.startsWith('project:') && _reportCapable(s))
                    PopupMenuButton<String>(
                      tooltip: 'Export report (PDF · DOCX · MD · PPTX)',
                      icon: const Icon(Icons.picture_as_pdf, size: 20, color: Odin.brand),
                      onSelected: (f) => _exportReport(widget.scope.substring(8), f),
                      itemBuilder: (_) => const [
                        PopupMenuItem(value: 'pdf', child: Text('📄  Export PDF')),
                        PopupMenuItem(value: 'docx', child: Text('📝  Export Word (.docx)')),
                        PopupMenuItem(value: 'md', child: Text('🔖  Export Markdown')),
                        PopupMenuItem(value: 'pptx', child: Text('📊  Export PowerPoint (.pptx)')),
                      ],
                    ),
                  // 🎙 LIVE MEETING — shown only when the project owns the asset (has the Live Meeting &
                  // Voice Streaming Agent). Opens an in-app dialog (not a browser): mic + sensitivity +
                  // live chunks, then stop → report → export (MD/Word · AR/EN).
                  if (_meetingCapable(s))
                    IconButton(
                      tooltip: 'Live meeting — voice streaming → smart report (MD/Word · AR/EN)',
                      visualDensity: VisualDensity.compact,
                      icon: const Icon(Icons.record_voice_over, size: 21, color: Odin.brand),
                      onPressed: () => _openMeeting(widget.scope.substring(8)),
                    ),
                  IconButton(
                    tooltip: _speak ? 'Voice replies: on' : 'Voice replies: off',
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
                  TextButton.icon(onPressed: _msgs.isEmpty ? null : () => _copy(_msgs), icon: const Icon(Icons.copy_all, size: 16), label: const Text('Copy all')),
                  IconButton(tooltip: 'Reload', visualDensity: VisualDensity.compact, icon: const Icon(Icons.refresh, size: 18), onPressed: _reload),
                ]),
        ),
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
                  ? const Center(child: Padding(padding: EdgeInsets.all(20), child: Text('Could not reach the chat pool.', textAlign: TextAlign.center, style: TextStyle(color: Odin.txtFaint))))
                  : _msgs.isEmpty
                      ? Center(
                          child: _syncing
                              ? const Column(mainAxisSize: MainAxisSize.min, children: [
                                  SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2, color: Odin.brand)),
                                  SizedBox(height: 10),
                                  Text('Syncing your messages…', style: TextStyle(color: Odin.txtFaint)),
                                ])
                              : const Text('Say hi — text talks to the CTO; attach a photo, file or voice note', style: TextStyle(color: Odin.txtFaint), textAlign: TextAlign.center))
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
                              final msg = _msgs[start + i - (hasEarlier ? 1 : 0)];
                              final id = (msg['id'] ?? '').toString();
                              return _Bubble(
                                msg: msg,
                                replied: _byId(msg['reply_to']?.toString()),
                                fileUrl: s.api.fileUrl,
                                selected: _selected.contains(id),
                                onTap: _selectMode ? () => _toggleSel(id) : null,
                                onLongPress: () => _toggleSel(id),
                                onPlay: (url) => _player.play(UrlSource(url)),
                              );
                            },
                          );
                        }),
        ),
        if (_busy) const LinearProgressIndicator(minHeight: 2, color: Odin.brand),
        if (_replyTo != null)
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            color: const Color(0x141A73E8),
            child: Row(children: [
              const Icon(Icons.reply, size: 16, color: Odin.brand2),
              const SizedBox(width: 8),
              Expanded(child: Text('Replying to ${_replyTo!['sender'] ?? _replyTo!['role']}: ${(_replyTo!['content'] ?? _replyTo!['kind'] ?? '').toString()}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12, color: Odin.txtDim))),
              InkWell(onTap: () => setState(() => _replyTo = null), child: const Icon(Icons.close, size: 16, color: Odin.txtFaint)),
            ]),
          ),
        Padding(
          padding: const EdgeInsets.all(8),
          child: Row(
            children: [
              IconButton(tooltip: 'Attach', onPressed: _attachSheet, icon: const Icon(Icons.add_circle_outline, color: Odin.txtDim)),
              IconButton(tooltip: 'Dictate', onPressed: _micDictate, icon: Icon(_voice.listening ? Icons.mic : Icons.mic_none, color: _voice.listening ? Odin.danger : Odin.txtDim)),
              InkWell(
                onTap: () => setState(() => _sttLocale = _sttLocale.startsWith('ar') ? 'en_US' : 'ar_SA'),
                borderRadius: BorderRadius.circular(6),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 8),
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
                  onSubmitted: (_) => _sendText(),
                  decoration: const InputDecoration(hintText: 'Message…', border: OutlineInputBorder(), isDense: true),
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
                onPressed: _busy ? null : _sendText,
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
  final Map<String, dynamic> msg;
  final Map<String, dynamic>? replied;
  final String Function(String) fileUrl;
  final bool selected;
  final VoidCallback? onTap;
  final VoidCallback onLongPress;
  final void Function(String url) onPlay;
  const _Bubble({required this.msg, required this.replied, required this.fileUrl, required this.selected, required this.onTap, required this.onLongPress, required this.onPlay});

  @override
  Widget build(BuildContext context) {
    final you = (msg['role'] ?? '') == 'user';
    final sender = (msg['sender'] ?? (you ? 'You' : 'CTO')).toString();
    final kind = (msg['kind'] ?? 'text').toString();
    final content = (msg['content'] ?? '').toString();
    final att = msg['attachment'] is Map ? Map<String, dynamic>.from(msg['attachment']) : null;

    final children = <Widget>[
      Text(sender, style: TextStyle(fontSize: 10.5, color: you ? Odin.brand2 : Odin.accent, fontWeight: FontWeight.w700)),
    ];
    if (replied != null) {
      children.add(Container(
        margin: const EdgeInsets.only(top: 4),
        padding: const EdgeInsets.all(6),
        decoration: BoxDecoration(color: const Color(0x14FFFFFF), borderRadius: BorderRadius.circular(6), border: const Border(left: BorderSide(color: Odin.brand2, width: 2))),
        child: Text('↩ ${replied!['sender'] ?? replied!['role']}: ${(replied!['content'] ?? replied!['kind'] ?? '').toString()}',
            maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 11, color: Odin.txtFaint)),
      ));
    }
    if (kind == 'image' && att != null) {
      children.add(Padding(
        padding: const EdgeInsets.only(top: 6),
        child: ClipRRect(borderRadius: BorderRadius.circular(8), child: Image.network(fileUrl(att['url']?.toString() ?? ''), errorBuilder: (_, __, ___) => const Text('[image]'))),
      ));
    } else if (kind == 'audio' && att != null) {
      children.add(Padding(
        padding: const EdgeInsets.only(top: 6),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          InkWell(onTap: () => onPlay(fileUrl(att['url']?.toString() ?? '')), child: const Icon(Icons.play_circle, color: Odin.brand, size: 30)),
          const SizedBox(width: 8),
          const Text('voice note', style: TextStyle(fontSize: 12, color: Odin.txtDim)),
        ]),
      ));
      if (content.isNotEmpty) {
        children.add(Padding(padding: const EdgeInsets.only(top: 4), child: Text('“$content”', style: const TextStyle(fontSize: 12.5, color: Odin.txt, fontStyle: FontStyle.italic))));
      }
    } else if ((kind == 'file' || kind == 'zip') && att != null) {
      children.add(Padding(
        padding: const EdgeInsets.only(top: 6),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(kind == 'zip' ? Icons.folder_zip : Icons.insert_drive_file, color: Odin.brand, size: 22),
          const SizedBox(width: 8),
          Flexible(child: Text(att['name']?.toString() ?? 'file', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12.5))),
        ]),
      ));
    }
    if (content.isNotEmpty && kind == 'text') {
      children.add(Padding(padding: const EdgeInsets.only(top: 2), child: SelectableText(content, style: const TextStyle(fontSize: 14, height: 1.5))));
    }

    return Align(
      alignment: you ? Alignment.centerRight : Alignment.centerLeft,
      child: GestureDetector(
        onTap: onTap,
        onLongPress: onLongPress,
        child: Container(
          margin: const EdgeInsets.symmetric(vertical: 4),
          padding: const EdgeInsets.all(10),
          constraints: const BoxConstraints(maxWidth: 560),
          decoration: BoxDecoration(
            color: selected ? const Color(0x553B82F6) : (you ? const Color(0x386C8CFF) : const Color(0x0AFFFFFF)),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: selected ? Odin.brand2 : (you ? const Color(0x4D6C8CFF) : Odin.stroke), width: selected ? 1.5 : 1),
          ),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: children),
        ),
      ),
    );
  }
}
