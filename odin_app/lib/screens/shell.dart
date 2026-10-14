import 'dart:async';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../api/anchor_api.dart';
import '../config.dart';
import '../state/app_state.dart';
import '../theme.dart';
import '../widgets.dart';
import 'dashboard.dart';
import 'project_detail.dart';
import 'agent_detail.dart';
import 'anchor_screen.dart';
import 'settings_screen.dart';
import 'audit_screen.dart';
import 'new_project.dart';
import 'docs.dart';
import 'archived.dart';
import 'ui_projects.dart';
import 'ui_agents.dart';
import 'approvals.dart';
import 'bell.dart';
import 'notifications_panel.dart';
import 'whatsapp.dart';
import 'v2_news.dart';

class Route {
  final String name; // dashboard | project | agent | anchor | settings
  final String? pid;
  final String? agent;
  const Route(this.name, {this.pid, this.agent});
}

class Shell extends StatefulWidget {
  const Shell({super.key});
  @override
  State<Shell> createState() => _ShellState();
}

class _ShellState extends State<Shell> {
  Route _route = const Route('dashboard');
  final _scaffold = GlobalKey<ScaffoldState>();
  Timer? _poll;
  bool _chat = false; // WhatsApp-clone mode (same pool, different representation)

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final s = context.read<AppState>();
      s.navToProject = (pid) => _go(Route('project', pid: pid)); // notifications panel → open project
      s.refreshDashboard();
      s.refreshAnchor();
      s.refreshNotifs();
    });
    // light change-detector: only when something actually changed do we do a full
    // refresh (which fires the banner + notification). This is the "auto-refresh
    // when a background event lands" — not constant heavy polling.
    _poll = Timer.periodic(const Duration(seconds: 12), (_) async {
      final s = context.read<AppState>();
      s.refreshNotifs(); // keep the live bell current → it shakes when a scheduled project starts/finishes
      if (await s.pollForChanges()) {
        s.refreshAnchor();
        if (_route.name == 'dashboard') s.refreshDashboard();
      }
    });
  }

  @override
  void dispose() {
    _poll?.cancel();
    super.dispose();
  }

  void _go(Route r) {
    setState(() => _route = r);
    _scaffold.currentState?.closeDrawer();
    final s = context.read<AppState>();
    if (r.name == 'dashboard') s.refreshDashboard();
    if (r.name == 'anchor') s.refreshAnchor();
  }

  String _title(AppState s) {
    switch (_route.name) {
      case 'project':
        for (final p in s.projects) {
          if (p.id == _route.pid) return p.name;
        }
        return 'Project';
      case 'agent':
        return _route.agent ?? 'Agent';
      case 'anchor':
        return 'Anchor Connect';
      case 'settings':
        return 'Settings';
      case 'docs':
        return 'Documentation';
      case 'archived':
        return 'Archived';
      case 'projects':
        return 'Projects';
      case 'agents':
        return 'Agents';
      case 'approvals':
        return 'Approval center';
      case 'audit':
        return 'Audit / Observer';
      default:
        return 'Company';
    }
  }

  Widget _content() {
    if (_chat) return const WhatsAppMode(); // radio ON → the whole app is WhatsApp, same pool
    switch (_route.name) {
      case 'project':
        // KEY by pid so switching projects REBUILDS State (fetches the new project + its chat) instead of
        // reusing the previous project's stale State — the "only the title changed, chat didn't load" bug.
        return ProjectDetail(key: ValueKey('project:${_route.pid}'), pid: _route.pid!, onOpenAgent: (a) => _go(Route('agent', pid: _route.pid, agent: a)));
      case 'agent':
        return AgentDetail(key: ValueKey('agent:${_route.pid}:${_route.agent}'), pid: _route.pid!, name: _route.agent!);
      case 'anchor':
        return const AnchorScreen();
      case 'settings':
        return const SettingsScreen();
      case 'docs':
        return const DocsScreen();
      case 'archived':
        return ArchivedScreen(onOpenProject: (pid) => _go(Route('project', pid: pid)));
      case 'projects':
        return UiProjectsScreen(onOpenProject: (pid) => _go(Route('project', pid: pid)));
      case 'agents':
        return const UiAgentsScreen();
      case 'approvals':
        return const ApprovalsScreen();
      case 'audit':
        return const AuditScreen();
      default:
        return DashboardScreen(
          onOpenProject: (pid) => _go(Route('project', pid: pid)),
          onOpenAgent: (pid, a) => _go(Route('agent', pid: pid, agent: a)),
        );
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = context.watch<AppState>();
    final wide = MediaQuery.of(context).size.width >= 900;
    final sidebar = _Sidebar(route: _route, onGo: _go, s: s, chat: _chat);

    return Container(
      decoration: Odin.bgDecoration,
      child: Scaffold(
        key: _scaffold,
        backgroundColor: Colors.transparent,
        drawer: wide ? null : Drawer(backgroundColor: Odin.bg2, width: 264, child: sidebar),
        body: SafeArea(
          child: Row(
            children: [
              // ONE main sidebar EVERYWHERE (normal AND chat mode) — Company, PROJECTS(+New), CHATS(+chat).
              // No secondary columns. In chat mode the conversation area (WhatsAppMode) reads the sidebar's
              // active scope. Narrow screens reach the same sidebar via the drawer.
              if (wide) SizedBox(width: 264, child: sidebar),
              Expanded(
                child: Column(
                  children: [
                    _TopBar(
                      title: _chat ? s.activeChatTitle : _title(s),
                      route: _route,
                      wide: wide,
                      onMenu: () => _scaffold.currentState?.openDrawer(),
                      onHome: () => _go(const Route('dashboard')),
                      onRefresh: () {
                        s.refreshDashboard();
                        s.refreshAnchor();
                        s.refreshNotifs();
                      },
                      onBell: () {
                        s.clearNewEvents();
                        showBell(context);
                      },
                      chat: _chat,
                      onChat: (v) => setState(() => _chat = v),
                    ),
                    if (s.banner != null) _BannerBar(text: s.banner!, onClose: s.clearBanner),
                    Expanded(child: _content()),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Sidebar extends StatelessWidget {
  final Route route;
  final void Function(Route) onGo;
  final AppState s;
  final bool chat; // chat (WhatsApp) mode → selecting a project/chat opens it in the conversation area
  const _Sidebar({required this.route, required this.onGo, required this.s, this.chat = false});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        border: Border(right: BorderSide(color: Odin.stroke)),
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [Color(0xE60F1320), Color(0xE60A0C12)],
        ),
      ),
      padding: const EdgeInsets.fromLTRB(14, 16, 14, 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Container(
                width: 38,
                height: 38,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(11),
                  gradient: const SweepGradient(colors: [Odin.brand, Odin.accent, Odin.brand2, Odin.brand]),
                ),
                child: const Center(
                  child: Text('Ω', style: TextStyle(fontWeight: FontWeight.w900, color: Odin.bg, fontSize: 18)),
                ),
              ),
              const SizedBox(width: 10),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Row(children: [Text('Odin', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700)), SizedBox(width: 6), V2Badge()]),
                  Text(kIsWeb ? 'Remote Anchor · Web' : 'Remote Anchor · Mobile',
                      style: const TextStyle(fontSize: 10.5, color: Odin.brand2)),
                  Text(s.health?.isClaude == true ? 'Claude engine' : 'engine',
                      style: const TextStyle(fontSize: 10, color: Odin.txtFaint)),
                ],
              ),
            ],
          ),
          const SizedBox(height: 16),
          _NavBtn('🏛️', 'Company', route.name == 'dashboard' && s.activeChatScope == 'company', () {
            s.openChat('company', 'Company — Chief Engineer');
            onGo(const Route('dashboard'));
          }),
          Padding(
            padding: const EdgeInsets.fromLTRB(11, 10, 4, 4),
            child: Row(
              children: [
                const Text('PROJECTS', style: TextStyle(fontSize: 10.5, color: Odin.txtFaint, letterSpacing: 1)),
                const Spacer(),
                InkWell(
                  onTap: () => showNewProject(context, onCreated: (pid) => onGo(Route('project', pid: pid))),
                  child: const Padding(
                    padding: EdgeInsets.all(2),
                    child: Text('＋ New', style: TextStyle(fontSize: 11, color: Odin.brand)),
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            child: ListView(
              padding: EdgeInsets.zero,
              children: [
                for (final p in s.projects)
                  _NavBtn(
                      (typeByKey(p.type)?.icon ?? '📁'),
                      p.name,
                      chat
                          ? s.activeChatScope == 'project:${p.id}'
                          : route.name == 'project' && route.pid == p.id,
                      () {
                    if (chat) {
                      s.openChat('project:${p.id}', p.name);
                    } else {
                      onGo(Route('project', pid: p.id));
                    }
                  }),
                if (s.projects.isEmpty)
                  const Padding(
                    padding: EdgeInsets.all(11),
                    child: Text('No projects yet', style: TextStyle(fontSize: 12, color: Odin.txtFaint)),
                  ),
                // CHATS — its OWN section under a separator, parallel to PROJECTS (NOT a horizontal strip).
                // Standalone chats live here; selecting one opens it in the Chief-Engineer chat area.
                Padding(
                  padding: const EdgeInsets.fromLTRB(11, 16, 4, 4),
                  child: Row(
                    children: [
                      const Text('CHATS', style: TextStyle(fontSize: 10.5, color: Odin.txtFaint, letterSpacing: 1)),
                      const Spacer(),
                      InkWell(
                        onTap: () async {
                          // ASK for the name first (no silent "New chat").
                          final name = await _askChatName(context, '');
                          if (name == null || name.isEmpty) return;
                          final scope = await s.newAdhocChat(name);
                          if (scope.isNotEmpty) {
                            s.openChat(scope, name);
                            onGo(const Route('dashboard'));
                          }
                        },
                        child: const Padding(
                          padding: EdgeInsets.all(2),
                          child: Text('＋ New', style: TextStyle(fontSize: 11, color: Odin.brand)),
                        ),
                      ),
                    ],
                  ),
                ),
                for (final c in s.adhocChats)
                  _ChatRow(
                    title: c['title'] ?? 'Chat',
                    active: (chat ? s.activeChatScope == c['scope'] : route.name == 'dashboard' && s.activeChatScope == c['scope']),
                    onOpen: () {
                      s.openChat(c['scope'] ?? '', c['title'] ?? 'Chat');
                      onGo(const Route('dashboard'));
                    },
                    onRename: () async {
                      final name = await _askChatName(context, c['title'] ?? '');
                      if (name != null && name.isNotEmpty) await s.renameChat(c['scope'] ?? '', name);
                    },
                    onDelete: () async {
                      final yes = await _confirmDelete(context, c['title'] ?? 'this chat');
                      if (yes) await s.clearConversation(c['scope'] ?? '');
                    },
                  ),
                if (s.adhocChats.isEmpty)
                  const Padding(
                    padding: EdgeInsets.all(11),
                    child: Text('No chats yet — tap ＋ chat', style: TextStyle(fontSize: 12, color: Odin.txtFaint)),
                  ),
              ],
            ),
          ),
          _NavBtn('🗂', 'Projects', route.name == 'projects', () => onGo(const Route('projects'))),
          _NavBtn('👥', 'Agents', route.name == 'agents', () => onGo(const Route('agents'))),
          _NavBtn('🔌', 'Anchor Connect', route.name == 'anchor', () => onGo(const Route('anchor'))),
          _NavBtn('✅', 'Approvals', route.name == 'approvals', () => onGo(const Route('approvals'))),
          _NavBtn('🛰️', 'Audit', route.name == 'audit', () => onGo(const Route('audit'))),
          _NavBtn('🗄', 'Archived', route.name == 'archived', () => onGo(const Route('archived'))),
          _NavBtn('📄', 'Docs', route.name == 'docs', () => onGo(const Route('docs'))),
          _NavBtn('✨', "What's new in v2", false, () => showWhatsNew(context)),
          _NavBtn('⚙️', 'Settings', route.name == 'settings', () => onGo(const Route('settings'))),
          const SizedBox(height: 8),
          StatusDot(state: s.health?.ok == true ? 'ok' : 'bad', label: s.health?.ok == true ? 'Connected' : 'Offline'),
          const SizedBox(height: 6),
          StatusDot(
              state: s.health?.voiceEnabled == true ? 'ok' : 'warn',
              label: s.health?.voiceEnabled == true ? 'Voice ready' : 'Voice off'),
          // 4th status circle — LOGIN/connection (7-day session). Shows when a login is required.
          if (s.requireLogin) ...[
            const SizedBox(height: 6),
            StatusDot(state: s.loggedIn ? 'ok' : 'warn',
                label: s.loggedIn ? 'Signed in · 7-day session' : 'Login required — connect'),
          ],
        ],
      ),
    );
  }
}

class _NavBtn extends StatelessWidget {
  final String icon;
  final String label;
  final bool active;
  final VoidCallback onTap;
  const _NavBtn(this.icon, this.label, this.active, this.onTap);
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Material(
        color: active ? const Color(0x296C8CFF) : Colors.transparent,
        borderRadius: BorderRadius.circular(11),
        child: InkWell(
          borderRadius: BorderRadius.circular(11),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 9),
            child: Row(
              children: [
                Text(icon, style: const TextStyle(fontSize: 14)),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(label,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(fontSize: 13.5, color: active ? Colors.white : Odin.txtDim)),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Ask for a chat name (create OR rename) — everywhere, so no chat is silently named "New chat".
Future<String?> _askChatName(BuildContext context, String initial) async {
  final ctrl = TextEditingController(text: initial);
  final v = await showDialog<String>(
    context: context,
    builder: (d) => AlertDialog(
      backgroundColor: Odin.panelSolid,
      title: Text(initial.isEmpty ? 'New chat' : 'Rename chat'),
      content: TextField(
        controller: ctrl,
        autofocus: true,
        decoration: const InputDecoration(labelText: 'Chat name'),
        onSubmitted: (t) => Navigator.pop(d, t.trim()),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(d), child: const Text('Cancel')),
        FilledButton(onPressed: () => Navigator.pop(d, ctrl.text.trim()), child: Text(initial.isEmpty ? 'Create' : 'Save')),
      ],
    ),
  );
  return v;
}

Future<bool> _confirmDelete(BuildContext context, String title) async {
  final v = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      backgroundColor: Odin.panelSolid,
      title: const Text('Delete chat'),
      content: Text('Delete "$title"? This removes it everywhere.'),
      actions: [
        TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Cancel')),
        TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Delete', style: TextStyle(color: Odin.danger))),
      ],
    ),
  );
  return v == true;
}

/// A chat entry in the sidebar's CHATS section — tap to open, ⋮ menu to Rename / Delete (every surface,
/// mobile included). Same look as a nav button, plus the actions.
class _ChatRow extends StatelessWidget {
  final String title;
  final bool active;
  final VoidCallback onOpen;
  final Future<void> Function() onRename;
  final Future<void> Function() onDelete;
  const _ChatRow({required this.title, required this.active, required this.onOpen, required this.onRename, required this.onDelete});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Material(
        color: active ? const Color(0x296C8CFF) : Colors.transparent,
        borderRadius: BorderRadius.circular(11),
        child: InkWell(
          borderRadius: BorderRadius.circular(11),
          onTap: onOpen,
          onLongPress: () => onRename(),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(11, 4, 4, 4),
            child: Row(
              children: [
                const Text('💬', style: TextStyle(fontSize: 14)),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(fontSize: 13.5, color: active ? Colors.white : Odin.txtDim)),
                ),
                PopupMenuButton<String>(
                  tooltip: 'Rename / delete',
                  icon: const Icon(Icons.more_vert, size: 16, color: Odin.txtFaint),
                  padding: EdgeInsets.zero,
                  onSelected: (v) { if (v == 'rename') onRename(); if (v == 'delete') onDelete(); },
                  itemBuilder: (_) => const [
                    PopupMenuItem(value: 'rename', child: Text('Rename')),
                    PopupMenuItem(value: 'delete', child: Text('Delete')),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _TopBar extends StatelessWidget {
  final String title;
  final Route route;
  final bool wide;
  final VoidCallback onMenu, onHome, onRefresh, onBell;
  final bool chat;
  final void Function(bool) onChat;
  const _TopBar({
    required this.title,
    required this.route,
    required this.wide,
    required this.onMenu,
    required this.onHome,
    required this.onRefresh,
    required this.onBell,
    required this.chat,
    required this.onChat,
  });

  @override
  Widget build(BuildContext context) {
    final s = context.watch<AppState>();
    return Container(
      padding: EdgeInsets.symmetric(horizontal: wide ? 16 : 6, vertical: 8),
      decoration: const BoxDecoration(border: Border(bottom: BorderSide(color: Odin.stroke))),
      child: Row(
        children: [
          if (!wide)
            IconButton(
              icon: const Icon(Icons.menu),
              onPressed: onMenu,
              visualDensity: VisualDensity.compact,
              constraints: const BoxConstraints(minWidth: 38, minHeight: 38),
            ),
          Expanded(
            child: InkWell(
              onTap: onHome,
              child: Text(chat ? title : (route.name == 'dashboard' ? 'Company' : title),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                      color: (chat || route.name != 'dashboard') ? Odin.txt : Odin.txtDim,
                      fontWeight: (chat || route.name != 'dashboard') ? FontWeight.w700 : FontWeight.normal,
                      fontSize: 14)),
            ),
          ),
          const SizedBox(width: 6),
          // MODE SWITCH — a FIRST-CLASS control that is ALWAYS visible, on wide AND mobile, in BOTH modes.
          // It must NEVER be buried in the ⋮ dropdown: you have to be able to flip normal ↔ Conversations
          // (WhatsApp) from anywhere. Highlighted when Conversations mode is active.
          IconButton(
            tooltip: chat ? 'Back to dashboard' : 'Conversations view',
            icon: Icon(Icons.forum_outlined, color: chat ? Odin.brand2 : Odin.txtFaint),
            onPressed: () => onChat(!chat),
            visualDensity: VisualDensity.compact,
            constraints: const BoxConstraints(minWidth: 38, minHeight: 38),
          ),
          // WIDE (web/tablet): show every action inline. NARROW (mobile): collapse the secondary actions
          // into a ⋮ dropdown (below) — fixes the RenderFlex top-bar overflow; notifications stay visible.
          if (wide) ...[
          // PORTS & ENVIRONMENT — tap to see the full ports/links map and flip Development <-> Production.
          IconButton(
            tooltip: 'Ports & environment map — flip Development / Production',
            icon: const Icon(Icons.lan_outlined),
            onPressed: () => showPortsSheet(context, s),
            visualDensity: VisualDensity.compact,
            constraints: const BoxConstraints(minWidth: 38, minHeight: 38),
          ),
          if (wide)
            InkWell(onTap: () => showPortsSheet(context, s), child: _EnvChip(env: s.env, compact: !wide)),
          // HubSpot connection badge — BESIDE the Azure/Env chip (web + mobile parity with desktop).
          _HubSpotChip(api: s.api),
          // (the mode switch is now the always-visible control above — not duplicated here)
          IconButton(
            tooltip: 'Refresh',
            icon: const Icon(Icons.refresh),
            onPressed: onRefresh,
            visualDensity: VisualDensity.compact,
            constraints: const BoxConstraints(minWidth: 38, minHeight: 38),
          ),
          // LOGOUT — always visible (normal + chat mode) once logged in via the anchor. Ends the 7-day session.
          if (s.requireLogin && s.loggedIn)
            IconButton(
              tooltip: 'Log out',
              icon: const Icon(Icons.logout),
              onPressed: () async {
                await context.read<AppState>().logout();
              },
              visualDensity: VisualDensity.compact,
              constraints: const BoxConstraints(minWidth: 38, minHeight: 38),
            ),
          ] else
            // NARROW (mobile): the secondary actions live in a ⋮ dropdown so the bar never overflows.
            PopupMenuButton<String>(
              tooltip: 'More',
              icon: const Icon(Icons.more_vert),
              onSelected: (v) async {
                switch (v) {
                  case 'ports': showPortsSheet(context, s); break;
                  case 'refresh': onRefresh(); break;
                  case 'guide': onBell(); break;
                  case 'logout': await context.read<AppState>().logout(); break;
                }
              },
              itemBuilder: (_) => [
                PopupMenuItem<String>(value: 'ports', child: ListTile(dense: true, leading: const Icon(Icons.lan_outlined), title: const Text('Ports & environment'))),
                PopupMenuItem<String>(value: 'chat', child: ListTile(dense: true, leading: const Icon(Icons.forum_outlined), title: Text(chat ? 'Back to dashboard' : 'Conversations'))),
                PopupMenuItem<String>(value: 'refresh', child: ListTile(dense: true, leading: const Icon(Icons.refresh), title: const Text('Refresh'))),
                PopupMenuItem<String>(value: 'guide', child: ListTile(dense: true, leading: const Icon(Icons.menu_book_outlined), title: const Text('Guide'))),
                if (s.requireLogin && s.loggedIn)
                  PopupMenuItem<String>(value: 'logout', child: ListTile(dense: true, leading: const Icon(Icons.logout), title: const Text('Log out'))),
              ],
            ),
          // 🔔 REAL NOTIFICATIONS — live feed for recurring/periodical work. Shakes when a new one arrives.
          Stack(
            clipBehavior: Clip.none,
            children: [
              NotifShakeBell(
                pulse: s.notifPulse,
                onTap: () { showNotifications(context); },
              ),
              if (s.unreadNotifs > 0)
                Positioned(
                  right: 2, top: 2,
                  child: Container(
                    padding: const EdgeInsets.all(3),
                    decoration: const BoxDecoration(color: Odin.danger, shape: BoxShape.circle),
                    constraints: const BoxConstraints(minWidth: 15, minHeight: 15),
                    child: Text('${s.unreadNotifs}',
                        textAlign: TextAlign.center, style: const TextStyle(fontSize: 9, color: Colors.white, fontWeight: FontWeight.w700)),
                  ),
                ),
            ],
          ),
          // 📖 GUIDE — on mobile it lives in the ⋮ dropdown above; on wide it's an inline bell.
          if (wide) Stack(
            clipBehavior: Clip.none,
            children: [
              IconButton(
                tooltip: 'Guide — what\'s new & how-to',
                icon: const Icon(Icons.menu_book_outlined),
                onPressed: onBell,
                visualDensity: VisualDensity.compact,
                constraints: const BoxConstraints(minWidth: 38, minHeight: 38),
              ),
              if (kBellTabs.isNotEmpty)
                Positioned(
                  right: 2, top: 2,
                  child: Container(
                    padding: const EdgeInsets.all(3),
                    decoration: const BoxDecoration(color: Odin.brand, shape: BoxShape.circle),
                    constraints: const BoxConstraints(minWidth: 15, minHeight: 15),
                    child: Text('${kBellTabs.length}',
                        textAlign: TextAlign.center, style: const TextStyle(fontSize: 9, color: Colors.white)),
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

/// PORTS & ENVIRONMENT MAP — one place to SEE every port/link and FLIP Development <-> Production.
/// In production only the ANCHOR and the WEB are online (Azure VM); the desktop brain stays local and
/// is reached only through the anchor. Flipping selects the matching EnvProfile and re-points the app.
void showPortsSheet(BuildContext context, AppState s) {
  final profiles = s.cfg.profiles;
  // find the "local" and "deployed" profiles by name (defaults order: 0 Local, 1 Anchor sim, 2 Deployed)
  int idxLocal = profiles.indexWhere((p) => p.mode == AccessMode.direct);
  int idxProd = profiles.indexWhere((p) => p.name.toLowerCase().contains('deployed'));
  if (idxLocal < 0) idxLocal = 0;
  if (idxProd < 0) idxProd = profiles.length - 1;
  final active = s.cfg.selected;

  List<List<String>> devRows = [
    ['brain (desktop AI + API)', 'http://localhost:8000', 'local'],
    ['anchor (3rd-party entry / queue)', 'http://localhost:9100', 'local'],
    ['3rd-party test page (sim)', 'http://localhost:9104/anchor_sim.html', 'local'],
    ['webhook receiver (results)', 'http://localhost:9300', 'local'],
    ['WEB app (Flutter)', 'http://localhost:8080', 'local'],
  ];
  List<List<String>> prodRows = [
    ['brain (desktop AI + API)', 'http://localhost:8000', 'stays LOCAL — via anchor only'],
    ['anchor (reverse proxy)', 'https://anchor.odinmarkets.com/odin-anchor', 'ONLINE · 443'],
    ['WEB app (reverse proxy)', 'https://anchor.odinmarkets.com/odin-web', 'ONLINE · 443'],
    ['webhook (via anchor)', 'https://anchor.odinmarkets.com/odin-anchor', 'ONLINE · 443'],
  ];

  Widget table(String title, List<List<String>> rows) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.only(top: 10, bottom: 4),
            child: Text(title, style: const TextStyle(fontSize: 12, color: Odin.txtDim, fontWeight: FontWeight.w700)),
          ),
          ...rows.map((r) => Padding(
                padding: const EdgeInsets.symmetric(vertical: 3),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SizedBox(width: 150, child: Text(r[0], style: const TextStyle(fontSize: 11.5))),
                    Expanded(
                      child: Text(r[1],
                          style: TextStyle(
                              fontSize: 11.5, fontFamily: 'monospace', color: Odin.brand2)),
                    ),
                    Text(r[2],
                        style: TextStyle(
                            fontSize: 10.5,
                            color: r[2].contains('ONLINE') ? Odin.ok : Odin.txtFaint)),
                  ],
                ),
              )),
        ],
      );

  showModalBottomSheet(
    context: context,
    backgroundColor: Odin.bg2,
    isScrollControlled: true,
    shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(16))),
    builder: (ctx) => Padding(
      padding: EdgeInsets.fromLTRB(18, 16, 18, 16 + MediaQuery.of(ctx).viewInsets.bottom),
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text('🗺  Ports & Environment', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
            const SizedBox(height: 4),
            Text('Active: ${s.env.name} · ${s.env.mode.name}   (anchor: ${s.env.anchorBase})',
                style: const TextStyle(fontSize: 11.5, color: Odin.brand2)),
            table('Development — everything LOCAL', devRows),
            table('Production — only ANCHOR + WEB online (Azure VM)', prodRows),
            const SizedBox(height: 14),
            Row(
              children: [
                Expanded(
                  child: ElevatedButton(
                    onPressed: () async {
                      await s.selectProfile(idxLocal);
                      await s.refreshDashboard();
                      if (ctx.mounted) Navigator.pop(ctx);
                    },
                    style: ElevatedButton.styleFrom(
                        backgroundColor: active == idxLocal ? Odin.brand : const Color(0xFF222A3F)),
                    child: const Text('Use Development (local)'),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: ElevatedButton(
                    onPressed: () async {
                      await s.selectProfile(idxProd);
                      await s.refreshDashboard();
                      if (ctx.mounted) Navigator.pop(ctx);
                    },
                    style: ElevatedButton.styleFrom(
                        backgroundColor: active == idxProd ? Odin.ok : const Color(0xFF222A3F)),
                    child: const Text('Use Production (online)'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            const Text(
              'Production points the app at the online anchor (https://anchor.odinmarkets.com/odin-anchor via the 443 reverse proxy — no open ports). The desktop brain stays local — reached only through the anchor.',
              style: TextStyle(fontSize: 11, color: Odin.txtFaint),
            ),
          ],
        ),
      ),
    ),
  );
}

// HubSpot CRM connection badge — top bar, beside the Azure/Env chip. Green dot = connected. Tap → the
// real account overview (contacts/companies/deals/this-month). Reads the anchor mirror on web/mobile.
class _HubSpotChip extends StatefulWidget {
  final OdinApi api;
  const _HubSpotChip({required this.api});
  @override
  State<_HubSpotChip> createState() => _HubSpotChipState();
}

class _HubSpotChipState extends State<_HubSpotChip> {
  Map<String, dynamic>? ov;
  Timer? _t;
  @override
  void initState() {
    super.initState();
    _load();
    _t = Timer.periodic(const Duration(seconds: 60), (_) => _load());
  }

  @override
  void dispose() {
    _t?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    final d = await widget.api.hubspotOverview();
    if (mounted) setState(() => ov = d);
  }

  void _show() {
    final o = ov ?? <String, dynamic>{};
    final connected = o['connected'] == true;
    final c = (o['counts'] is Map) ? Map<String, dynamic>.from(o['counts']) : <String, dynamic>{};
    String f(String k) {
      final v = c[k];
      return v == null ? '—' : (v is Map ? 'scope needed' : '$v');
    }

    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('🧡 HubSpot CRM — Account Overview'),
        content: connected
            ? Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('Connected · portal ${o['connection'] is Map ? o['connection']['portal_id'] ?? '' : ''}'),
                const SizedBox(height: 6),
                Text('Contacts: ${f('contacts')}'),
                Text('Companies: ${f('companies')}'),
                Text('Deals: ${f('deals')}'),
                Text('Contacts this month: ${f('contacts_this_month')}'),
              ])
            : Text('Not connected${o['error'] != null ? ': ${o['error']}' : ' — check HUBSPOT_SECRET_KEY'}'),
        actions: [TextButton(onPressed: () => Navigator.pop(context), child: const Text('Close'))],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final connected = ov?['connected'] == true;
    final color = ov == null
        ? const Color(0xFFC9A227)
        : (connected ? const Color(0xFF39D98A) : const Color(0xFFFF6B81));
    return InkWell(
      onTap: _show,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 6),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Container(width: 8, height: 8, decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
          const SizedBox(width: 5),
          const Text('HubSpot', style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600)),
        ]),
      ),
    );
  }
}

class _EnvChip extends StatelessWidget {
  final EnvProfile env;
  final bool compact;
  const _EnvChip({required this.env, this.compact = false});
  @override
  Widget build(BuildContext context) {
    final anchor = env.mode == AccessMode.anchor;
    final c = anchor ? Odin.warn : Odin.ok;
    final label = compact ? env.mode.name : '${env.name} · ${env.mode.name}';
    return ConstrainedBox(
      constraints: BoxConstraints(maxWidth: compact ? 90 : 220),
      child: Pill(label, color: c, borderColor: c.withValues(alpha: 0.5)),
    );
  }
}

class _BannerBar extends StatelessWidget {
  final String text;
  final VoidCallback onClose;
  const _BannerBar({required this.text, required this.onClose});
  @override
  Widget build(BuildContext context) {
    return Material(
      color: const Color(0xFF1B2230),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        child: Row(
          children: [
            const Icon(Icons.notifications_active, size: 18, color: Odin.warn),
            const SizedBox(width: 8),
            Expanded(child: Text(text, style: const TextStyle(fontSize: 13))),
            IconButton(icon: const Icon(Icons.close, size: 16), onPressed: onClose),
          ],
        ),
      ),
    );
  }
}


// v2: public wrappers so the phone-first shell (mobile_shell.dart) reuses the exact same dialogs.
Future<String?> askChatName(BuildContext context, String initial) => _askChatName(context, initial);
Future<bool> confirmDeleteChat(BuildContext context, String title) => _confirmDelete(context, title);
