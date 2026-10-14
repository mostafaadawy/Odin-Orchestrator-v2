import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_state.dart';
import '../theme.dart';
import '../widgets.dart';

Future<void> showNewProject(BuildContext context, {required void Function(String pid) onCreated}) {
  return showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    backgroundColor: Odin.panelSolid,
    builder: (_) => _NewProjectSheet(onCreated: onCreated),
  );
}

class _NewProjectSheet extends StatefulWidget {
  final void Function(String pid) onCreated;
  const _NewProjectSheet({required this.onCreated});
  @override
  State<_NewProjectSheet> createState() => _NewProjectSheetState();
}

class _NewProjectSheetState extends State<_NewProjectSheet> {
  final _name = TextEditingController();
  final _identifier = TextEditingController();
  final _desc = TextEditingController();
  String _type = 'web';
  String _cadence = 'once';
  List<String> _team = []; // suggested team names (used for the unknown-agent confirmation gate)
  bool _busy = false;
  bool _suggesting = false;
  String? _err;
  String? _suggestion;

  Future<void> _suggest() async {
    final desc = _desc.text.trim();
    if (desc.isEmpty) {
      setState(() => _suggestion = 'Write a short description first.');
      return;
    }
    setState(() {
      _suggesting = true;
      _suggestion = null;
    });
    try {
      final d = await context.read<AppState>().api.intake([
        {'role': 'user', 'content': desc}
      ]);
      final spec = (d['spec'] is Map) ? Map<String, dynamic>.from(d['spec']) : <String, dynamic>{};
      final t = (spec['type'] ?? d['type'] ?? d['recommend'] ?? '').toString().toLowerCase();
      final team = (spec['team'] ?? d['team'] ?? []);
      if (team is List) _team = team.map((e) => e.toString()).toList();
      if (t.isNotEmpty && typeByKey(t) != null) _type = t;
      // recommended unique identifier (editable) — so a re-used prompt won't reuse an old folder
      final sid = (spec['identifier'] ?? '').toString();
      if (_identifier.text.trim().isEmpty && sid.isNotEmpty) _identifier.text = sid;
      _suggestion = 'Suggested: ${typeByKey(_type)?.label ?? _type}'
          '${team is List && team.isNotEmpty ? ' · team: ${team.join(", ")}' : ''}'
          '${_identifier.text.isNotEmpty ? ' · id: ${_identifier.text}' : ''}';
    } catch (e) {
      _suggestion = 'Could not get a suggestion ($e). Pick a type manually.';
    }
    if (mounted) setState(() => _suggesting = false);
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(left: 16, right: 16, top: 16, bottom: MediaQuery.of(context).viewInsets.bottom + 16),
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SectionTitle('New project', size: 16),
            const SizedBox(height: 12),
            TextField(
              controller: _name,
              decoration: const InputDecoration(labelText: 'Name', border: OutlineInputBorder(), isDense: true),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: _identifier,
              decoration: const InputDecoration(
                labelText: 'Identifier (recommended — editable, must be unique)',
                helperText: 'A unique id; a re-used prompt won\'t reuse an old project\'s folder.',
                border: OutlineInputBorder(), isDense: true),
            ),
            const SizedBox(height: 10),
            DropdownButtonFormField<String>(
              initialValue: _type,
              isExpanded: true,
              dropdownColor: Odin.panelSolid,
              decoration: const InputDecoration(labelText: 'Type', border: OutlineInputBorder(), isDense: true),
              items: [
                for (final t in kTypeMeta)
                  DropdownMenuItem(
                    value: t.key,
                    child: Text('${t.icon}  ${t.label}  ·  ${t.group}', overflow: TextOverflow.ellipsis),
                  ),
              ],
              onChanged: (v) => setState(() => _type = v ?? 'web'),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: _desc,
              minLines: 2,
              maxLines: 4,
              decoration: const InputDecoration(labelText: 'Description / brief', border: OutlineInputBorder()),
            ),
            const SizedBox(height: 6),
            Align(
              alignment: Alignment.centerLeft,
              child: TextButton.icon(
                onPressed: _suggesting ? null : _suggest,
                icon: _suggesting
                    ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2))
                    : const Icon(Icons.auto_awesome, size: 16),
                label: const Text('Let the CTO suggest the type & team'),
              ),
            ),
            if (_suggestion != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Text(_suggestion!, style: const TextStyle(fontSize: 12, color: Odin.brand2)),
              ),
            const SizedBox(height: 10),
            DropdownButtonFormField<String>(
              initialValue: _cadence,
              isExpanded: true,
              dropdownColor: Odin.panelSolid,
              decoration: const InputDecoration(labelText: 'Cadence', border: OutlineInputBorder(), isDense: true),
              items: const [
                DropdownMenuItem(value: 'once', child: Text('Once')),
                DropdownMenuItem(value: 'recurring', child: Text('Recurring (on-demand, many times)')),
                DropdownMenuItem(value: 'periodical', child: Text('Periodical (scheduled)')),
              ],
              onChanged: (v) => setState(() => _cadence = v ?? 'once'),
            ),
            if (_err != null) ...[
              const SizedBox(height: 10),
              Text(_err!, style: const TextStyle(fontSize: 12, color: Odin.danger)),
            ],
            const SizedBox(height: 14),
            Row(
              children: [
                FilledButton.icon(
                  onPressed: _busy ? null : _create,
                  style: FilledButton.styleFrom(backgroundColor: Odin.brand),
                  icon: _busy
                      ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                      : const Icon(Icons.add),
                  label: const Text('Create'),
                ),
                const SizedBox(width: 8),
                TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
              ],
            ),
          ],
        ),
      ),
    );
  }

  // A long-streaming project (e.g. a 1–2h Zoom meeting) can't be waited on as one block — it must be
  // processed in CHUNKS. Detect that from the brief and put a big, explicit dialog in front of the owner.
  bool get _isStreaming {
    final d = '${_name.text} ${_desc.text}'.toLowerCase();
    const keys = ['zoom', 'meeting', 'transcrib', 'listen to', 'live audio', 'stream', 'microphone',
      'record the call', 'call recording', 'two hour', '2 hour', 'chunk', 'long audio', 'real-time audio',
      'speech to text', 'voice notes for'];
    return keys.any((k) => d.contains(k));
  }

  Future<bool> _confirmChunking() async {
    if (!_isStreaming) return true;
    final ok = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (c) => AlertDialog(
        backgroundColor: Odin.panelSolid,
        title: const Text('🎙️  Long-streaming project — chunked processing',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
        content: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: const [
            Text('This project listens to long live audio (e.g. a 1–2 hour Zoom meeting). Waiting for the '
                'whole meeting is not practical, so Odin processes it in SMALL CHUNKS while it runs:',
                style: TextStyle(fontSize: 14, height: 1.5, fontWeight: FontWeight.w600)),
            SizedBox(height: 12),
            Text('•  Audio is captured in short serial segments and transcribed as it arrives.\n'
                '•  Each chunk is analyzed on its own during the meeting — never one giant transcript.\n'
                '•  At the end, all chunks are merged into ONE final smart report.\n'
                '•  Your microphone / meeting audio is never blocked — capture runs in parallel.',
                style: TextStyle(fontSize: 13, height: 1.7)),
            SizedBox(height: 12),
            Text('Long sessions use more CPU/RAM — keep the desktop running for the whole meeting.',
                style: TextStyle(fontSize: 12, color: Odin.txtFaint)),
          ]),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancel')),
          FilledButton(
            onPressed: () => Navigator.pop(c, true),
            style: FilledButton.styleFrom(backgroundColor: Odin.brand),
            child: const Text('I understand — create it'),
          ),
        ],
      ),
    );
    return ok == true;
  }

  Future<void> _create() async {
    if (_name.text.trim().isEmpty) {
      setState(() => _err = 'Name is required');
      return;
    }
    if (!await _confirmChunking()) return; // prominent chunking dialog for long-streaming projects
    // ALTERNATIVE-to-web (same target, mobile-native form): the web confirm SCREEN gates unknown
    // agents inline; on mobile we do the same gate as a MODAL DIALOG (better fit for a bottom-sheet
    // flow). Reason: keeps full parity — an invented agent (e.g. "Vapi") is never silently created —
    // while respecting mobile UX. RULE: do not discard the original behavior — if no team was suggested
    // (the owner skipped "let the CTO suggest"), we pass members=null and the backend infers the team
    // exactly as before.
    List<Map<String, dynamic>>? members;
    if (_team.isNotEmpty) {
      try {
        final v = await context.read<AppState>().validateAgents(_team);
        final unknown = ((v['unknown'] ?? []) as List).map((e) => e.toString()).toList();
        final catalog = ((v['catalog'] ?? []) as List).map((e) => e.toString()).toList();
        if (unknown.isNotEmpty) {
          final resolved = await _confirmUnknownAgents(unknown, catalog);
          if (resolved == null) return; // owner cancelled — create nothing
          members = [
            // keep the known suggested members…
            for (final m in _team.where((x) => !unknown.contains(x))) {'name': m, 'role': m},
            // …plus the owner's resolutions for the unknown ones
            ...resolved,
          ];
        }
      } catch (_) {/* validation offline → fall back to backend inference (non-blocking) */}
    }
    setState(() {
      _busy = true;
      _err = null;
    });
    try {
      final p = await context.read<AppState>().createProject(
            name: _name.text.trim(),
            identifier: _identifier.text.trim(),
            description: _desc.text.trim(),
            type: _type,
            cadence: _cadence,
            members: members,
          );
      if (mounted) {
        Navigator.pop(context);
        widget.onCreated(p.id);
      }
    } catch (e) {
      setState(() {
        _busy = false;
        _err = '$e';
      });
    }
  }

  /// Mobile equivalent of the web "new agent(s) not recognized" dialog. Returns the resolved member
  /// maps to ADD (create-with-rules or pick-existing); removed ones are simply omitted. Null = cancel.
  Future<List<Map<String, dynamic>>?> _confirmUnknownAgents(List<String> unknown, List<String> catalog) {
    // per-unknown working state: mode (create|pick|remove), role, rules, pick
    final state = {for (final n in unknown) n: {'mode': 'create', 'role': '', 'rules': '', 'pick': ''}};
    return showDialog<List<Map<String, dynamic>>>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setLocal) {
          Widget tile(String n) {
            final s = state[n]!;
            return Card(
              color: Odin.panelSolid,
              child: Padding(
                padding: const EdgeInsets.all(10),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('“$n”', style: const TextStyle(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 6),
                  Wrap(spacing: 6, children: [
                    for (final m in const ['create', 'pick', 'remove'])
                      ChoiceChip(
                        label: Text(m == 'create' ? 'Create new' : m == 'pick' ? 'Use existing' : 'Remove'),
                        selected: s['mode'] == m,
                        onSelected: (_) => setLocal(() => s['mode'] = m),
                      ),
                  ]),
                  if (s['mode'] == 'create') ...[
                    const SizedBox(height: 6),
                    TextField(decoration: const InputDecoration(labelText: 'Role', isDense: true, border: OutlineInputBorder()),
                        onChanged: (v) => s['role'] = v),
                    const SizedBox(height: 6),
                    TextField(decoration: const InputDecoration(labelText: 'Rules / scope (prevents hallucination)', isDense: true, border: OutlineInputBorder()),
                        minLines: 1, maxLines: 3, onChanged: (v) => s['rules'] = v),
                  ],
                  if (s['mode'] == 'pick')
                    DropdownButton<String>(
                      isExpanded: true,
                      dropdownColor: Odin.panelSolid,
                      value: (s['pick'] as String).isEmpty ? null : s['pick'] as String,
                      hint: const Text('pick an existing agent'),
                      items: [for (final c in catalog) DropdownMenuItem(value: c, child: Text(c))],
                      onChanged: (v) => setLocal(() => s['pick'] = v ?? ''),
                    ),
                ]),
              ),
            );
          }

          final valid = unknown.every((n) {
            final s = state[n]!;
            if (s['mode'] == 'create') return (s['role'] as String).trim().isNotEmpty;
            if (s['mode'] == 'pick') return (s['pick'] as String).isNotEmpty;
            return true; // remove
          });

          return AlertDialog(
            backgroundColor: Odin.panelSolid,
            title: const Text('New agent(s) not recognized', style: TextStyle(fontSize: 15)),
            content: SizedBox(
              width: double.maxFinite,
              child: SingleChildScrollView(
                child: Column(mainAxisSize: MainAxisSize.min, children: [
                  const Text('Nothing is created until you decide. Create it (with a role + rules), use an '
                      'existing agent if you mis-named it, or remove it.', style: TextStyle(fontSize: 12, color: Odin.txtDim)),
                  const SizedBox(height: 8),
                  for (final n in unknown) tile(n),
                ]),
              ),
            ),
            actions: [
              TextButton(onPressed: () => Navigator.pop(ctx, null), child: const Text('Cancel')),
              FilledButton(
                onPressed: valid
                    ? () {
                        final out = <Map<String, dynamic>>[];
                        for (final n in unknown) {
                          final s = state[n]!;
                          if (s['mode'] == 'remove') continue;
                          if (s['mode'] == 'pick') {
                            out.add({'name': s['pick'], 'role': s['pick']});
                          } else {
                            out.add({
                              'name': n,
                              'role': (s['role'] as String).trim().isEmpty ? n : s['role'],
                              'description': (s['rules'] as String).trim().isEmpty ? 'Custom agent: $n' : s['rules'],
                              'rules': (s['rules'] as String).trim().isEmpty ? [] : [s['rules']],
                            });
                          }
                        }
                        Navigator.pop(ctx, out);
                      }
                    : null,
                child: const Text('Confirm'),
              ),
            ],
          );
        },
      ),
    );
  }
}
