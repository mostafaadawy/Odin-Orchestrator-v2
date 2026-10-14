import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/models.dart';
import '../state/app_state.dart';
import '../theme.dart';
import '../widgets.dart';
import 'chat_screen.dart';
import 'schedule_editor.dart';

class ProjectDetail extends StatefulWidget {
  final String pid;
  final void Function(String agent) onOpenAgent;
  const ProjectDetail({super.key, required this.pid, required this.onOpenAgent});
  @override
  State<ProjectDetail> createState() => _ProjectDetailState();
}

class _ProjectDetailState extends State<ProjectDetail> {
  Project? _p;
  List<String> _rules = [];
  List<Map<String, dynamic>> _ruleItems = []; // rules with ids (for delete)
  List<Map<String, dynamic>> _schedules = [];
  List<Operation> _ops = [];
  Map<String, dynamic>? _plan;
  bool _loading = false;
  bool _running = false; // ▶ Run-now in flight
  String? _err;

  Future<void> _runNow() async {
    setState(() => _running = true);
    try {
      final msg = await context.read<AppState>().api.runNow(widget.pid);
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Run failed: $e')));
    } finally {
      if (mounted) setState(() => _running = false);
    }
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  Future<void> _load() async {
    final s = context.read<AppState>();
    // seed instantly from the already-loaded dashboard list so the page is NEVER blank
    for (final p in s.projects) {
      if (p.id == widget.pid) {
        _p = p;
        break;
      }
    }
    setState(() {
      _loading = true;
      _err = null;
    });
    try {
      _p = await s.api.project(widget.pid); // enrich with full detail
    } catch (e) {
      _err = '$e'; // keep the seeded project; just note the detail fetch failed
    }
    Future<void> safe(Future<void> Function() f) async {
      try {
        await f();
      } catch (_) {}
    }

    await Future.wait([
      safe(() async => _rules = await s.api.rules(widget.pid)),
      safe(() async => _ruleItems = await s.api.rulesDetailed(widget.pid)),
      safe(() async => _schedules = await s.api.schedules(widget.pid)),
      safe(() async => _ops = await s.api.operations(widget.pid)),
      safe(() async => _plan = await s.api.plan(widget.pid)),
      s.refreshActivity(),
    ]);
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _confirmRemoveMember(String pid, String name) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        backgroundColor: Odin.panel,
        title: const Text('Remove from team?'),
        content: Text('Remove $name from this project\'s team? You can add a member back anytime.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancel')),
          TextButton(
            onPressed: () => Navigator.pop(c, true),
            child: const Text('Remove', style: TextStyle(color: Odin.danger)),
          ),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await context.read<AppState>().api.removeAgent(pid, name);
    } catch (_) {}
    await _load();
  }

  Future<void> _editProject(Project p) async {
    final nameC = TextEditingController(text: p.name);
    final descC = TextEditingController(text: p.description);
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        backgroundColor: Odin.panel,
        title: const Text('Edit project'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(controller: nameC, decoration: const InputDecoration(labelText: 'Name')),
            const SizedBox(height: 10),
            TextField(controller: descC, minLines: 2, maxLines: 5,
                decoration: const InputDecoration(labelText: 'Description / brief')),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.pop(c, true), child: const Text('Save')),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await context.read<AppState>().api.updateProject(
          widget.pid, {'name': nameC.text.trim(), 'description': descC.text.trim()});
    } catch (_) {}
    await _load();
  }

  Future<void> _suggestAndAddMember(String pid) async {
    final descC = TextEditingController();
    final api = context.read<AppState>().api;
    final go = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        backgroundColor: Odin.panel,
        title: const Text('Add a member'),
        content: TextField(
          controller: descC,
          minLines: 1,
          maxLines: 3,
          decoration: const InputDecoration(labelText: 'Describe the role/skill you need (CTO will suggest one)'),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.pop(c, true), child: const Text('Suggest & add')),
        ],
      ),
    );
    if (go != true || descC.text.trim().isEmpty) return;
    try {
      final sug = await api.suggestAgent(pid, descC.text.trim());
      final name = (sug['suggestedName'] ?? sug['name'] ?? sug['agent'] ?? '').toString();
      final role = (sug['role'] ?? name).toString();
      // REVIEW/EDIT the AI recommendation (description + Resources & Dependencies + env) before creating.
      final nameC = TextEditingController(text: name);
      final roleC = TextEditingController(text: role);
      final descrC = TextEditingController(text: (sug['description'] ?? '').toString());
      final resC = TextEditingController(text: (sug['resources'] ?? '').toString());
      final env = (sug['env'] as List?) ?? [];
      final envC = TextEditingController(
          text: env.map((e) => '${e['key']}=${e['value'] ?? ''}').join('\n'));
      final create = await _memberEditDialog('Review new member', nameC, roleC, descrC, resC, envC, nameEditable: true);
      if (create == true && nameC.text.trim().isNotEmpty) {
        await api.addAgent(pid, {
          'name': nameC.text.trim(), 'role': roleC.text.trim(), 'force': true,
          'nature': (sug['nature'] ?? 'technical').toString(),
          'description': descrC.text.trim(), 'resources': resC.text,
          'env': _parseEnv(envC.text),
        });
        if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Added ${nameC.text.trim()}')));
      }
    } catch (_) {}
    await _load();
  }

  // Parse "KEY=VALUE" lines into [{key,value}] for the env field.
  List<Map<String, String>> _parseEnv(String text) {
    final out = <Map<String, String>>[];
    for (final ln in text.split('\n')) {
      final t = ln.trim();
      if (t.isEmpty || !t.contains('=')) continue;
      final i = t.indexOf('=');
      out.add({'key': t.substring(0, i).trim(), 'value': t.substring(i + 1).trim()});
    }
    return out;
  }

  // Shared editor dialog for a member's identity + Resources & Dependencies + env.
  Future<bool?> _memberEditDialog(String title, TextEditingController nameC, TextEditingController roleC,
      TextEditingController descrC, TextEditingController resC, TextEditingController envC,
      {bool nameEditable = false}) {
    return showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        backgroundColor: Odin.panel,
        title: Text(title),
        content: SizedBox(
          width: 460,
          child: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              TextField(controller: nameC, enabled: nameEditable, decoration: const InputDecoration(labelText: 'Name')),
              TextField(controller: roleC, decoration: const InputDecoration(labelText: 'Role')),
              TextField(controller: descrC, minLines: 1, maxLines: 2, decoration: const InputDecoration(labelText: 'Description')),
              const SizedBox(height: 6),
              TextField(controller: resC, minLines: 5, maxLines: 12,
                  style: const TextStyle(fontFamily: 'monospace', fontSize: 12),
                  decoration: const InputDecoration(labelText: 'Allowed Resources & Dependencies')),
              const SizedBox(height: 6),
              TextField(controller: envC, minLines: 1, maxLines: 6,
                  style: const TextStyle(fontFamily: 'monospace', fontSize: 12),
                  decoration: const InputDecoration(labelText: 'Env vars — one KEY=VALUE per line')),
            ]),
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.pop(c, true), child: const Text('Save')),
        ],
      ),
    );
  }

  // Edit an EXISTING member's resources/env from the dashboard.
  Future<void> _editMemberResources(String pid, String name) async {
    final api = context.read<AppState>().api;
    try {
      final a = await api.agent(pid, name);
      final nameC = TextEditingController(text: name);
      final roleC = TextEditingController(text: (a['role'] ?? '').toString());
      final descrC = TextEditingController(text: (a['description'] ?? '').toString());
      final resC = TextEditingController(text: (a['resources'] ?? '').toString());
      final env = (a['env'] as List?) ?? [];
      final envC = TextEditingController(text: env.map((e) => '${e['key']}=${e['value'] ?? ''}').join('\n'));
      final ok = await _memberEditDialog('Edit $name — resources & env', nameC, roleC, descrC, resC, envC);
      if (ok == true) {
        await api.updateAgent(pid, name, {
          'role': roleC.text.trim(), 'description': descrC.text.trim(),
          'resources': resC.text, 'env': _parseEnv(envC.text),
        });
        if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Updated $name')));
      }
    } catch (_) {}
    await _load();
  }

  // Long-press a member → choose to edit its resources/env or remove it from the team.
  Future<void> _memberActions(String pid, String name) async {
    final choice = await showModalBottomSheet<String>(
      context: context,
      backgroundColor: Odin.panel,
      builder: (c) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          ListTile(leading: const Icon(Icons.tune), title: Text('Edit $name — resources & env'),
              onTap: () => Navigator.pop(c, 'edit')),
          ListTile(leading: const Icon(Icons.person_remove), title: Text('Remove $name from team'),
              onTap: () => Navigator.pop(c, 'remove')),
        ]),
      ),
    );
    if (choice == 'edit') await _editMemberResources(pid, name);
    if (choice == 'remove') await _confirmRemoveMember(pid, name);
  }

  Future<void> _addMapping(String pid) async {
    final localC = TextEditingController();
    final cloudC = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        backgroundColor: Odin.panel,
        title: const Text('Add folder mapping'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(controller: localC, decoration: const InputDecoration(labelText: 'Local folder')),
            const SizedBox(height: 8),
            TextField(controller: cloudC, decoration: const InputDecoration(labelText: 'Cloud / VM folder')),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.pop(c, true), child: const Text('Add')),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await context.read<AppState>().api.addMapping(pid, {'local': localC.text.trim(), 'cloud': cloudC.text.trim()});
    } catch (_) {}
    await _load();
  }

  Future<void> _removeRule(String rid) async {
    if (rid.isEmpty) return;
    try {
      await context.read<AppState>().api.removeRule(widget.pid, rid);
    } catch (_) {}
    await _load();
  }

  Future<void> _scheduleAction(String tid, {required bool approve}) async {
    if (tid.isEmpty) return;
    final api = context.read<AppState>().api;
    try {
      if (approve) {
        await api.approveSchedule(tid);
      } else {
        await api.skipSchedule(tid);
      }
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(approve ? 'Scheduled run approved' : 'Next run skipped')),
        );
      }
    } catch (_) {}
    await _load();
  }

  @override
  Widget build(BuildContext context) {
    final s = context.watch<AppState>();
    final p = _p;
    if (p == null) {
      if (_loading) return const Center(child: CircularProgressIndicator(color: Odin.brand));
      return Center(child: Text(_err ?? 'Project not found', style: const TextStyle(color: Odin.txtFaint)));
    }
    final wide = MediaQuery.of(context).size.width >= 1000;
    final latestOp = _ops.isNotEmpty ? _ops.first : null;

    final infoChildren = <Widget>[
        GlassCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Text(typeByKey(p.type)?.icon ?? '📦', style: const TextStyle(fontSize: 20)),
                  const SizedBox(width: 8),
                  Expanded(child: SectionTitle(p.name)),
                  if (_schedules.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(right: 4),
                      child: FilledButton.icon(
                        onPressed: _running ? null : _runNow,
                        style: FilledButton.styleFrom(backgroundColor: Odin.ok, visualDensity: VisualDensity.compact),
                        icon: _running
                            ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                            : const Icon(Icons.play_arrow, size: 18),
                        label: const Text('Run', style: TextStyle(fontSize: 12)),
                      ),
                    ),
                  PopupMenuButton<String>(
                    icon: const Icon(Icons.more_vert, size: 20),
                    tooltip: 'Project actions',
                    onSelected: (v) {
                      if (v == 'edit') _editProject(p);
                      if (v == 'mapping') _addMapping(p.id);
                    },
                    itemBuilder: (c) => const [
                      PopupMenuItem(value: 'edit', child: Text('Edit project')),
                      PopupMenuItem(value: 'mapping', child: Text('Add folder mapping')),
                    ],
                  ),
                  IconButton(onPressed: _loading ? null : _load, icon: const Icon(Icons.refresh)),
                ],
              ),
              Text('id: ${p.id}',
                  style: const TextStyle(fontSize: 11, color: Odin.brand2)),
              Text('${typeByKey(p.type)?.label ?? p.type}${p.stack.isNotEmpty ? ' · ${p.stack}' : ''}',
                  style: const TextStyle(fontSize: 12, color: Odin.txtDim)),
              if (p.description.isNotEmpty) ...[
                const SizedBox(height: 8),
                Text(p.description, style: const TextStyle(fontSize: 13, color: Odin.txtDim)),
              ],
            ],
          ),
        ),
        const SizedBox(height: 12),
        GlassCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Expanded(child: Text('Team', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700))),
                  TextButton.icon(
                    onPressed: () => _suggestAndAddMember(p.id),
                    icon: const Icon(Icons.person_add_alt, size: 16),
                    label: const Text('Add', style: TextStyle(fontSize: 12)),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              Wrap(
                spacing: 14,
                runSpacing: 10,
                children: ['Project CTO', ...p.members].map((m) {
                  final active = s.activeKeys.contains('${p.id}:$m');
                  final isCto = m == 'Project CTO';
                  return InkWell(
                    onTap: () => widget.onOpenAgent(m),
                    // long-press: edit the member's resources/env, or remove from team (CTO is the manager).
                    onLongPress: isCto ? null : () => _memberActions(p.id, m),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Avatar(kind: isCto ? 'cto' : p.avatarFor(m), size: 48, active: active),
                        Text(m, style: const TextStyle(fontSize: 10, color: Odin.txtDim)),
                        if (active) const Text('working', style: TextStyle(fontSize: 9, color: Odin.ok)),
                      ],
                    ),
                  );
                }).toList(),
              ),
            ],
          ),
        ),
        if (latestOp != null) ...[
          const SizedBox(height: 12),
          _OperationCard(op: latestOp),
        ],
        if (_plan != null && (_plan!['steps'] is List) && (_plan!['steps'] as List).isNotEmpty) ...[
          const SizedBox(height: 12),
          GlassCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Plan', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
                const SizedBox(height: 8),
                ...(_plan!['steps'] as List).take(12).map((st) => Padding(
                      padding: const EdgeInsets.symmetric(vertical: 2),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('• ', style: TextStyle(color: Odin.brand2)),
                          Expanded(child: Text('${st is Map ? (st['title'] ?? st['step'] ?? st) : st}',
                              style: const TextStyle(fontSize: 12.5, color: Odin.txtDim))),
                        ],
                      ),
                    )),
              ],
            ),
          ),
        ],
        if (_ruleItems.isNotEmpty || _rules.isNotEmpty) ...[
          const SizedBox(height: 12),
          GlassCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Rules / standing instructions', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
                const SizedBox(height: 8),
                // use the detailed items (with ids) when available so each rule can be deleted; fall
                // back to the plain strings if the detailed fetch failed.
                ...(_ruleItems.isNotEmpty
                        ? _ruleItems
                        : _rules.map((r) => {'id': '', 'rule': r}).toList())
                    .map((r) => Padding(
                          padding: const EdgeInsets.symmetric(vertical: 2),
                          child: Row(
                            children: [
                              Expanded(
                                child: Text('• ${r['rule'] ?? ''}',
                                    style: const TextStyle(fontSize: 12.5, color: Odin.txtDim)),
                              ),
                              if ((r['id'] ?? '').toString().isNotEmpty)
                                InkWell(
                                  onTap: () => _removeRule(r['id'].toString()),
                                  child: const Padding(
                                    padding: EdgeInsets.all(4),
                                    child: Icon(Icons.close, size: 15, color: Odin.txtFaint),
                                  ),
                                ),
                            ],
                          ),
                        )),
              ],
            ),
          ),
        ],
        if (_schedules.isNotEmpty) ...[
          const SizedBox(height: 12),
          GlassCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Schedules', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
                const SizedBox(height: 8),
                ..._schedules.map((t) => Padding(
                      padding: const EdgeInsets.symmetric(vertical: 2),
                      child: Row(
                        children: [
                          Expanded(
                            child: Text('⏰ ${t['name'] ?? t['goal'] ?? t['id']} · ${t['cron'] ?? t['every'] ?? ''}',
                                style: const TextStyle(fontSize: 12, color: Odin.txtDim)),
                          ),
                          // edit the time(s) / cadence / timezone (multi-time, daily/weekly/monthly, Egypt default)
                          IconButton(
                            tooltip: 'Edit schedule (time · days · timezone)',
                            visualDensity: VisualDensity.compact,
                            icon: const Icon(Icons.edit_calendar, size: 17, color: Odin.brand),
                            onPressed: () async {
                              final saved = await showScheduleEditor(context, context.read<AppState>().api, t);
                              if (saved == true) _load();
                            },
                          ),
                          // web parity: approve a due run / skip the next one
                          TextButton(
                            onPressed: () => _scheduleAction(t['id']?.toString() ?? '', approve: true),
                            child: const Text('Approve', style: TextStyle(fontSize: 11, color: Odin.ok)),
                          ),
                          TextButton(
                            onPressed: () => _scheduleAction(t['id']?.toString() ?? '', approve: false),
                            child: const Text('Skip', style: TextStyle(fontSize: 11, color: Odin.warn)),
                          ),
                        ],
                      ),
                    )),
              ],
            ),
          ),
        ],
        _ControlsCard(pid: p.id, type: p.type, latestOp: latestOp, onChanged: _load),
    ];

    final chatBody = ChatView(key: ValueKey('project:${p.id}'), scope: 'project:${p.id}', title: 'Project CTO — ${p.name}');

    if (!wide) {
      return ListView(
        padding: const EdgeInsets.all(14),
        children: [
          ...infoChildren,
          const SizedBox(height: 12),
          SizedBox(height: 460, child: GlassCard(padding: EdgeInsets.zero, child: chatBody)),
        ],
      );
    }
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Expanded(flex: 5, child: GlassCard(padding: EdgeInsets.zero, child: chatBody)),
          const SizedBox(width: 12),
          Expanded(flex: 4, child: ListView(padding: EdgeInsets.zero, children: infoChildren)),
        ],
      ),
    );
  }
}

class _OperationCard extends StatelessWidget {
  final Operation op;
  const _OperationCard({required this.op});
  @override
  Widget build(BuildContext context) {
    Color c = op.status == 'finished' ? Odin.ok : op.status == 'failed' ? Odin.danger : op.status == 'blocked' ? Odin.warn : Odin.brand;
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Text('Latest operation', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
              const Spacer(),
              Pill(op.status, color: c, borderColor: c.withValues(alpha: 0.4)),
            ],
          ),
          const SizedBox(height: 6),
          Text('${op.kind}', style: const TextStyle(fontSize: 12, color: Odin.txtDim)),
          if (op.question.isNotEmpty) ...[
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: Odin.warn.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: Odin.warn.withValues(alpha: 0.4)),
              ),
              child: Text('⛔ Needs you: ${op.question}', style: const TextStyle(fontSize: 12, color: Odin.warn)),
            ),
          ],
          if (op.log.isNotEmpty) ...[
            const SizedBox(height: 8),
            Container(
              width: double.infinity,
              constraints: const BoxConstraints(maxHeight: 160),
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(color: const Color(0xFF0A0C14), borderRadius: BorderRadius.circular(10)),
              child: SingleChildScrollView(
                child: Text(op.log.take(40).join('\n'),
                    style: const TextStyle(fontSize: 11, color: Odin.txtDim, fontFamily: 'monospace')),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _ControlsCard extends StatefulWidget {
  final String pid;
  final String type;
  final Operation? latestOp;
  final Future<void> Function() onChanged;
  const _ControlsCard({required this.pid, required this.type, required this.latestOp, required this.onChanged});
  @override
  State<_ControlsCard> createState() => _ControlsCardState();
}

class _ControlsCardState extends State<_ControlsCard> {
  bool _running = false;
  bool _busy = false;
  String? _msg;

  Future<void> _refreshStatus() async {
    try {
      final st = await context.read<AppState>().api.runStatus(widget.pid);
      if (mounted) setState(() => _running = st['running'] == true);
    } catch (_) {}
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _refreshStatus());
  }

  Future<void> _do(Future<void> Function() f, String ok) async {
    setState(() {
      _busy = true;
      _msg = null;
    });
    try {
      await f();
      _msg = ok;
    } catch (e) {
      _msg = '⚠️ $e';
    }
    await _refreshStatus();
    await widget.onChanged();
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _runTeam() async {
    final ctrl = TextEditingController();
    final goal = await showDialog<String>(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: Odin.panelSolid,
        title: const Text('Run the team'),
        content: TextField(controller: ctrl, minLines: 2, maxLines: 4, decoration: const InputDecoration(hintText: 'Goal for the CTO → team…')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(context, ctrl.text.trim()), child: const Text('Start')),
        ],
      ),
    );
    if (goal != null && goal.isNotEmpty) {
      await _do(() => context.read<AppState>().api.startRun(widget.pid, goal), 'Team run started');
    }
  }

  Future<void> _provide() async {
    final op = widget.latestOp!;
    final ctrl = TextEditingController();
    final ans = await showDialog<String>(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: Odin.panelSolid,
        title: const Text('Provide the missing info'),
        content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(op.question, style: const TextStyle(fontSize: 12, color: Odin.txtDim)),
          const SizedBox(height: 8),
          TextField(controller: ctrl, decoration: const InputDecoration(hintText: 'Your answer')),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(context, ctrl.text.trim()), child: const Text('Send')),
        ],
      ),
    );
    if (ans != null && ans.isNotEmpty) {
      await _do(() => context.read<AppState>().api.provideOperation(op.id, {'answer': ans}), 'Sent — resuming');
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = context.read<AppState>();
    final isDeploy = widget.type == 'deployment';
    final op = widget.latestOp;
    final blocked = op != null && op.question.isNotEmpty;
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Text('Operations', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
              const Spacer(),
              if (_running) Pill('● running', color: Odin.ok, borderColor: Odin.ok.withValues(alpha: 0.4)),
            ],
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              if (!_running)
                OdinButton('Run team', icon: Icons.play_arrow, primary: true, onPressed: _busy ? null : _runTeam)
              else
                OdinButton('Stop', icon: Icons.stop, onPressed: _busy ? null : () => _do(() => s.api.stopRun(widget.pid), 'Stopped')),
              OdinButton('Sync', icon: Icons.sync, onPressed: _busy ? null : () => _do(() => s.api.syncRun(widget.pid).then((_) {}), 'Sync started')),
              if (isDeploy)
                OdinButton('Deploy', icon: Icons.rocket_launch, onPressed: _busy ? null : () => _do(() => s.api.deployRun(widget.pid).then((_) {}), 'Deploy started')),
              if (isDeploy)
                OdinButton('Request deploy', icon: Icons.fact_check, onPressed: _busy ? null : () => _do(() => s.api.requestDeploy(widget.pid).then((_) {}), 'Deploy requested')),
            ],
          ),
          if (blocked) ...[
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: Odin.warn.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: Odin.warn.withValues(alpha: 0.4)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('⛔ Needs you: ${op.question}', style: const TextStyle(fontSize: 12, color: Odin.warn)),
                  const SizedBox(height: 8),
                  Row(children: [
                    OdinButton('Provide answer', icon: Icons.reply, primary: true, onPressed: _busy ? null : _provide),
                    const SizedBox(width: 8),
                    OdinButton('Stop operation', icon: Icons.cancel, onPressed: _busy ? null : () => _do(() => s.api.stopOperation(op.id), 'Stopped')),
                  ]),
                ],
              ),
            ),
          ],
          if (_msg != null) Padding(padding: const EdgeInsets.only(top: 8), child: Text(_msg!, style: const TextStyle(fontSize: 12, color: Odin.txtDim))),
        ],
      ),
    );
  }
}
