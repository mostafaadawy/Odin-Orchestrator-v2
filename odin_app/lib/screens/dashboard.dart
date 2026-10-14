import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/models.dart';
import '../state/app_state.dart';
import '../theme.dart';
import '../widgets.dart';
import 'chat_screen.dart';
import 'new_project.dart';
import 'schedule_editor.dart';

class DashboardScreen extends StatelessWidget {
  final void Function(String pid) onOpenProject;
  final void Function(String pid, String agent) onOpenAgent;
  const DashboardScreen({super.key, required this.onOpenProject, required this.onOpenAgent});

  @override
  Widget build(BuildContext context) {
    final s = context.watch<AppState>();
    final wide = MediaQuery.of(context).size.width >= 1000;

    // OFFLINE (anchor mode, anchor unreachable): show a clear message + Retry — never stale data, never an
    // endless spinner. Refreshing once the anchor is back clears this and loads the synced data.
    if (s.offline) return _OfflineView(s: s);

    final left = GlassCard(
      padding: EdgeInsets.zero,
      child: const _ChatArea(),
    );

    final right = ListView(
      padding: EdgeInsets.zero,
      children: [
        _AgentRoster(s: s),               // FIRST: every created agent, from the central store, scrollable
        const SizedBox(height: 12),
        _RecurringCard(s: s, onOpenProject: onOpenProject),
        _StatusPanel(s: s),
        const SizedBox(height: 12),
        _LiveAgents(s: s, onOpenAgent: onOpenAgent),
        const SizedBox(height: 12),
        _CompanyAgents(s: s),
        const SizedBox(height: 12),
        _Connectors(s: s),
        const SizedBox(height: 12),
        _MonitorFeed(s: s),
        const SizedBox(height: 16),
        _ProjectsGrouped(s: s, onOpenProject: onOpenProject),
      ],
    );

    if (!wide) {
      return RefreshIndicator(
        onRefresh: s.refreshDashboard,
        child: ListView(
          padding: const EdgeInsets.all(14),
          children: [
            _AgentRoster(s: s),           // FIRST: every created agent, from the central store, scrollable
            const SizedBox(height: 12),
            _RecurringCard(s: s, onOpenProject: onOpenProject),
            _StatusPanel(s: s),
            const SizedBox(height: 12),
            _LiveAgents(s: s, onOpenAgent: onOpenAgent),
            const SizedBox(height: 12),
            _CompanyAgents(s: s),
            const SizedBox(height: 12),
            _Connectors(s: s),
            const SizedBox(height: 16),
            _ProjectsGrouped(s: s, onOpenProject: onOpenProject),
            const SizedBox(height: 16),
            SizedBox(height: 460, child: GlassCard(padding: EdgeInsets.zero, child: const _ChatArea())),
          ],
        ),
      );
    }

    return Padding(
      padding: const EdgeInsets.all(16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Expanded(flex: 5, child: left),
          const SizedBox(width: 12),
          Expanded(flex: 4, child: right),
        ],
      ),
    );
  }
}

// NORMAL-MODE chat area: a strip of PREVIOUS chats above the Company — Chief Engineer chat. Select one to
// open it here, delete one, or "+ New" to create one — all server-side (synced through the anchor, shared
// with web/mobile/desktop). Selecting swaps the chat below to that scope's SAME shared pool.
/// The Chief-Engineer / chat area. Which chat it shows is driven ENTIRELY by the left sidebar's
/// CHATS section (s.activeChatScope) — no horizontal chip strip. Select a chat in the sidebar → it
/// opens here; the SAME shared pool renders (WhatsApp-style).
class _ChatArea extends StatelessWidget {
  const _ChatArea();
  @override
  Widget build(BuildContext context) {
    final s = context.watch<AppState>();
    final scope = s.activeChatScope;
    final title = s.activeChatTitle;
    return ChatView(key: ValueKey(scope), scope: scope, title: title);
  }
}

class _OfflineView extends StatelessWidget {
  final AppState s;
  const _OfflineView({required this.s});
  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.cloud_off, size: 48, color: Odin.txtFaint),
            const SizedBox(height: 14),
            const Text('You are offline',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
            const SizedBox(height: 8),
            Text(s.offlineMsg,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 13, color: Odin.txtFaint)),
            const SizedBox(height: 18),
            FilledButton.icon(
              onPressed: s.loadingDash ? null : () => s.refreshDashboard(),
              icon: s.loadingDash
                  ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.refresh),
              label: Text(s.loadingDash ? 'Reconnecting…' : 'Try again'),
            ),
          ],
        ),
      ),
    );
  }
}

class _StatusPanel extends StatelessWidget {
  final AppState s;
  const _StatusPanel({required this.s});
  @override
  Widget build(BuildContext context) {
    final h = s.health;
    final live = s.activeKeys.length;
    final vmOk = (s.vm?['ok'] == true);
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SectionTitle('System status'),
                    Text('Company CTO · live across all projects',
                        style: TextStyle(fontSize: 12, color: Odin.txtFaint)),
                  ],
                ),
              ),
              Kpi('${s.projects.length}', 'PROJECTS'),
              const SizedBox(width: 16),
              Kpi('$live', 'AGENTS LIVE', color: live > 0 ? Odin.ok : Odin.txt),
            ],
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 18,
            runSpacing: 10,
            children: [
              StatusDot(state: h?.ok == true ? 'ok' : 'bad', label: 'API ${h?.ok == true ? 'ready' : 'offline'}'),
              StatusDot(state: h?.isClaude == true ? 'ok' : 'warn', label: h?.engine ?? 'engine'),
              StatusDot(state: h?.voiceEnabled == true ? 'ok' : 'warn', label: h?.voiceEnabled == true ? 'Voice ready' : 'Voice off'),
              StatusDot(state: vmOk ? 'ok' : 'warn', label: 'Azure VM ${vmOk ? 'connected' : 'checking…'}'),
              Pill('model: ${h?.isClaude == true ? 'Claude Code' : (h?.ollamaModel ?? '—')}'),
            ],
          ),
          if (s.dashError != null) ...[
            const SizedBox(height: 10),
            Text(s.dashError!, style: const TextStyle(fontSize: 11, color: Odin.danger)),
          ],
        ],
      ),
    );
  }
}

class _LiveAgents extends StatelessWidget {
  final AppState s;
  final void Function(String, String) onOpenAgent;
  const _LiveAgents({required this.s, required this.onOpenAgent});
  @override
  Widget build(BuildContext context) {
    final working = s.activity;
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('Live agents', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
              Pill(working.isEmpty ? 'all idle' : '${working.length} working now',
                  color: working.isEmpty ? Odin.txtDim : Odin.ok),
            ],
          ),
          for (final a in working) ...[
            const SizedBox(height: 8),
            InkWell(
              onTap: () => onOpenAgent(a.pid, a.agent),
              child: Row(
                children: [
                  Avatar(kind: a.agent, name: a.agent, active: true, size: 36),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('🗣️ ${a.phase.isEmpty ? a.agent : a.phase}', style: const TextStyle(fontSize: 12.5)),
                        if (a.task.isNotEmpty)
                          Text(a.task, maxLines: 1, overflow: TextOverflow.ellipsis,
                              style: const TextStyle(fontSize: 10.5, color: Odin.txtFaint)),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _AgentRoster extends StatelessWidget {
  final AppState s;
  const _AgentRoster({required this.s});
  @override
  Widget build(BuildContext context) {
    // THE single roster: every ACTUAL agent (all projects + company), deduped by name, grouped by nature,
    // scrollable when tall. No duplicate list anywhere else.
    final uniq = _agentsByNature(s.allAgentsRoster);
    final groups = [
      ['operational', '📋 Operational'],
      ['technical', '🛠 Technical'],
    ];
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Agent roster — all agents (${uniq.length})', style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
          const SizedBox(height: 2),
          const Text('Every agent across all projects + company, grouped by nature (not only active). HubSpot is operational; security agents appear under their category.',
              style: TextStyle(fontSize: 11, color: Odin.txtFaint)),
          const SizedBox(height: 6),
          if (uniq.isEmpty)
            const Text('No agents yet.', style: TextStyle(fontSize: 11, color: Odin.txtFaint))
          else
            ConstrainedBox(
              constraints: const BoxConstraints(maxHeight: 320),
              child: Scrollbar(
                child: SingleChildScrollView(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      for (final g in groups) ...[
                        Builder(builder: (_) {
                          final rs = uniq.where((a) => ((a['nature'] ?? 'technical').toString()) == g[0]).toList();
                          if (rs.isEmpty) return const SizedBox.shrink();
                          return Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const SizedBox(height: 8),
                              Text('${g[1]} · ${rs.length}', style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w700, color: Odin.txtFaint, letterSpacing: 0.4)),
                              const SizedBox(height: 5),
                              Wrap(spacing: 8, runSpacing: 8, children: rs.map(_agentChip).toList()),
                            ],
                          );
                        }),
                      ],
                    ],
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _agentChip(Map<String, dynamic> a) {
    return Pill(
      (a['name'] ?? '').toString(),
      leading: Avatar(kind: (a['avatar'] ?? 'generic').toString(), name: (a['name'] ?? '').toString(), size: 16),
      color: Odin.txtDim,
    );
  }
}

class _CompanyAgents extends StatefulWidget {
  final AppState s;
  const _CompanyAgents({required this.s});
  @override
  State<_CompanyAgents> createState() => _CompanyAgentsState();
}

class _CompanyAgentsState extends State<_CompanyAgents> {
  final _name = TextEditingController();
  final _role = TextEditingController();

  Future<void> _add() async {
    if (_name.text.trim().isEmpty) return;
    await widget.s.api.addCompanyAgent({
      'name': _name.text.trim(),
      'role': _role.text.trim().isEmpty ? _name.text.trim() : _role.text.trim(),
      'avatar': 'generic',
      'description': _role.text.trim(),
    });
    _name.clear();
    _role.clear();
    await widget.s.refreshDashboard();
  }

  @override
  Widget build(BuildContext context) {
    final s = widget.s;
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Company agents (native to every project)', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          if (s.companyAgents.isEmpty)
            const Text('None yet.', style: TextStyle(fontSize: 12, color: Odin.txtFaint))
          else
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: s.companyAgents
                  .map((a) => Pill(a.name,
                      leading: Avatar(kind: a.avatar, name: a.name, size: 22),
                      onRemove: () => _remove(a.name)))
                  .toList(),
            ),
          const SizedBox(height: 8),
          Row(children: [
            Expanded(child: TextField(controller: _name, decoration: const InputDecoration(hintText: 'name', isDense: true, border: OutlineInputBorder()))),
            const SizedBox(width: 6),
            Expanded(child: TextField(controller: _role, decoration: const InputDecoration(hintText: 'role', isDense: true, border: OutlineInputBorder()))),
            const SizedBox(width: 6),
            IconButton(onPressed: _add, icon: const Icon(Icons.add_circle, color: Odin.brand)),
          ]),
        ],
      ),
    );
  }

  Future<void> _remove(String name) async {
    await widget.s.api.removeCompanyAgent(name);
    await widget.s.refreshDashboard();
  }
}

/// Dedupe the org-wide agent roster by name (an agent can appear in several projects) so the roster shows
/// each real agent once, keeping its nature/avatar/role for category grouping.
List<Map<String, dynamic>> _agentsByNature(List roster) {
  final byName = <String, Map<String, dynamic>>{};
  for (final a in roster) {
    if (a is! Map) continue;
    final m = Map<String, dynamic>.from(a);
    final k = (m['name'] ?? '').toString().toLowerCase();
    if (k.isEmpty) continue;
    byName.putIfAbsent(k, () => m);
  }
  return byName.values.toList();
}

class _Connectors extends StatefulWidget {
  final AppState s;
  const _Connectors({required this.s});
  @override
  State<_Connectors> createState() => _ConnectorsState();
}

class _ConnectorsState extends State<_Connectors> {
  final _name = TextEditingController();
  final _type = TextEditingController();
  final _key = TextEditingController();

  Future<void> _add() async {
    if (_name.text.trim().isEmpty) return;
    await widget.s.api.addConnector({'name': _name.text.trim(), 'type': _type.text.trim(), 'apiKey': _key.text.trim()});
    _name.clear();
    _type.clear();
    _key.clear();
    await widget.s.refreshDashboard();
  }

  @override
  Widget build(BuildContext context) {
    final s = widget.s;
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Connectors / integrations', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          if (s.connectors.isEmpty)
            const Text('None yet.', style: TextStyle(fontSize: 12, color: Odin.txtFaint))
          else
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: s.connectors
                  .map((c) => Pill('${c.name} · ${c.status}',
                      leading: Container(width: 9, height: 9, decoration: BoxDecoration(color: c.connected ? Odin.ok : Odin.warn, shape: BoxShape.circle)),
                      onRemove: () => _remove(c.id)))
                  .toList(),
            ),
          const SizedBox(height: 8),
          Row(children: [
            Expanded(child: TextField(controller: _name, decoration: const InputDecoration(hintText: 'name', isDense: true, border: OutlineInputBorder()))),
            const SizedBox(width: 6),
            Expanded(child: TextField(controller: _type, decoration: const InputDecoration(hintText: 'type', isDense: true, border: OutlineInputBorder()))),
            const SizedBox(width: 6),
            IconButton(onPressed: _add, icon: const Icon(Icons.add_circle, color: Odin.brand)),
          ]),
          const SizedBox(height: 6),
          TextField(controller: _key, obscureText: true, decoration: const InputDecoration(hintText: 'API key (optional)', isDense: true, border: OutlineInputBorder())),
        ],
      ),
    );
  }

  Future<void> _remove(String cid) async {
    await widget.s.api.removeConnector(cid);
    await widget.s.refreshDashboard();
  }
}

class _MonitorFeed extends StatefulWidget {
  final AppState s;
  const _MonitorFeed({required this.s});
  @override
  State<_MonitorFeed> createState() => _MonitorFeedState();
}

class _MonitorFeedState extends State<_MonitorFeed> {
  List<Map<String, dynamic>> _items = [];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  Future<void> _load() async {
    try {
      _items = await widget.s.api.scopeChildren('company');
      if (mounted) setState(() {});
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            const Text('Company monitor — across all projects', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
            const Spacer(),
            IconButton(onPressed: _load, icon: const Icon(Icons.refresh, size: 16)),
          ]),
          if (_items.isEmpty)
            const Text('No recent activity.', style: TextStyle(fontSize: 12, color: Odin.txtFaint))
          else
            ..._items.take(8).map((c) => Padding(
                  padding: const EdgeInsets.symmetric(vertical: 2),
                  child: Text('• ${c['scope'] ?? c['title'] ?? ''}: ${c['last'] ?? c['summary'] ?? ''}',
                      maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 11.5, color: Odin.txtDim)),
                )),
        ],
      ),
    );
  }
}

class _ProjectsGrouped extends StatelessWidget {
  final AppState s;
  final void Function(String) onOpenProject;
  const _ProjectsGrouped({required this.s, required this.onOpenProject});
  @override
  Widget build(BuildContext context) {
    if (s.projects.isEmpty) {
      return GlassCard(
        child: Column(
          children: [
            const EmptyHint('No projects yet.'),
            OdinButton('New project', icon: Icons.add, primary: true,
                onPressed: () => showNewProject(context, onCreated: onOpenProject)),
          ],
        ),
      );
    }
    final groups = <String, List<Project>>{};
    for (final p in s.projects) {
      (groups[p.type.isEmpty ? 'web' : p.type] ??= []).add(p);
    }
    final orderedKeys = [
      ...kTypeMeta.map((t) => t.key).where(groups.containsKey),
      ...groups.keys.where((k) => typeByKey(k) == null),
    ];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const SectionTitle('Projects'),
            const Spacer(),
            OdinButton('New', icon: Icons.add, onPressed: () => showNewProject(context, onCreated: onOpenProject)),
          ],
        ),
        for (final k in orderedKeys) ...[
          const SizedBox(height: 10),
          Row(
            children: [
              Text(typeByKey(k)?.icon ?? '📦', style: const TextStyle(fontSize: 14)),
              const SizedBox(width: 7),
              Flexible(child: Text(typeByKey(k)?.label ?? k,
                  maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700, color: Odin.txtDim))),
              const SizedBox(width: 6),
              Text('· ${groups[k]!.length}', style: const TextStyle(fontSize: 12, color: Odin.txtFaint)),
              const SizedBox(width: 8),
              const Expanded(child: Divider(color: Odin.stroke)),
            ],
          ),
          const SizedBox(height: 8),
          ...groups[k]!.map((p) => Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: _ProjectCard(s: s, p: p, onOpen: () => onOpenProject(p.id)),
              )),
        ],
      ],
    );
  }
}

class _ProjectCard extends StatelessWidget {
  final AppState s;
  final Project p;
  final VoidCallback onOpen;
  const _ProjectCard({required this.s, required this.p, required this.onOpen});
  @override
  Widget build(BuildContext context) {
    final liveMembers = ['Project CTO', ...p.members].where((m) => s.activeKeys.contains('${p.id}:$m')).toList();
    return GlassCard(
      onTap: onOpen,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(typeByKey(p.type)?.icon ?? '📦', style: const TextStyle(fontSize: 16)),
              const SizedBox(width: 7),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(p.name, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
                Text('id: ${p.id}', style: const TextStyle(fontSize: 10, color: Odin.brand2)),
              ])),
              if (p.periodicEnabled) Pill('⏰ ${p.periodicLabel}', color: Odin.brand2, borderColor: Odin.brand2.withValues(alpha: 0.4)),
              if (liveMembers.isNotEmpty) ...[
                const SizedBox(width: 6),
                Pill('● ${liveMembers.length} live', color: Odin.ok, borderColor: Odin.ok.withValues(alpha: 0.4)),
              ],
            ],
          ),
          Padding(
            padding: const EdgeInsets.only(top: 4, bottom: 12),
            child: Text('${typeByKey(p.type)?.label ?? (p.type.isEmpty ? 'Web application' : p.type)}${p.stack.isNotEmpty ? ' · ${p.stack}' : ''}',
                maxLines: 2, overflow: TextOverflow.ellipsis, softWrap: true,
                style: const TextStyle(fontSize: 12, color: Odin.txtDim)),
          ),
          TeamGrid(
            members: ['Project CTO', ...p.members],
            kindOf: (m) => m == 'Project CTO' ? 'cto' : p.avatarFor(m),
            isActive: (m) => s.activeKeys.contains('${p.id}:$m'),
            iconSize: 42,
          ),
        ],
      ),
    );
  }
}

// 🔁 RECURRING & SCHEDULED — a card you notice on open: every periodical/recurring project, its cadence,
// and a pulsing dot when there's new activity (unread notifications). Tap a row to open the project.
class _RecurringCard extends StatelessWidget {
  final AppState s;
  final void Function(String pid) onOpenProject;
  const _RecurringCard({required this.s, required this.onOpenProject});
  @override
  Widget build(BuildContext context) {
    final rec = s.projects.where((p) => p.periodicEnabled || p.periodicLabel.isNotEmpty).toList();
    if (rec.isEmpty) return const SizedBox.shrink();
    final hasNew = s.unreadNotifs > 0;
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: GlassCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              const Text('🔁 Recurring & scheduled', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
              const SizedBox(width: 8),
              if (hasNew)
                _PulseDot(),
              const Spacer(),
              Text('${rec.length}', style: const TextStyle(fontSize: 12, color: Odin.txtFaint)),
            ]),
            const SizedBox(height: 8),
            ...rec.map((p) => Padding(
                  padding: const EdgeInsets.symmetric(vertical: 4, horizontal: 2),
                  child: Row(children: [
                    const Icon(Icons.schedule, size: 15, color: Odin.brand),
                    const SizedBox(width: 8),
                    Expanded(child: InkWell(
                      onTap: () => onOpenProject(p.id),
                      child: Text(p.name, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12.5)))),
                    Text(p.periodicLabel.isNotEmpty ? p.periodicLabel : 'scheduled',
                        style: const TextStyle(fontSize: 11, color: Odin.txtDim)),
                    // edit the schedule (time · days · timezone) directly from the card
                    IconButton(
                      tooltip: 'Edit schedule',
                      visualDensity: VisualDensity.compact,
                      constraints: const BoxConstraints(minWidth: 30, minHeight: 30),
                      icon: const Icon(Icons.edit_calendar, size: 16, color: Odin.brand),
                      onPressed: () async {
                        final api = context.read<AppState>().api;
                        final tasks = await api.schedules(p.id);
                        if (tasks.isEmpty) {
                          if (context.mounted) onOpenProject(p.id);
                          return;
                        }
                        if (context.mounted) await showScheduleEditor(context, api, tasks.first);
                      },
                    ),
                    InkWell(onTap: () => onOpenProject(p.id),
                        child: const Icon(Icons.chevron_right, size: 16, color: Odin.txtFaint)),
                  ]),
                )),
          ],
        ),
      ),
    );
  }
}

class _PulseDot extends StatefulWidget {
  @override
  State<_PulseDot> createState() => _PulseDotState();
}

class _PulseDotState extends State<_PulseDot> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(vsync: this, duration: const Duration(milliseconds: 900))..repeat(reverse: true);
  @override
  void dispose() { _c.dispose(); super.dispose(); }
  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: Tween(begin: 0.35, end: 1.0).animate(_c),
      child: Container(width: 8, height: 8, decoration: const BoxDecoration(color: Odin.danger, shape: BoxShape.circle)),
    );
  }
}
