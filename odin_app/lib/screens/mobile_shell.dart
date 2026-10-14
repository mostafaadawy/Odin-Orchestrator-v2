import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_state.dart';
import '../theme.dart';
import '../widgets.dart';
import 'agent_detail.dart';
import 'anchor_screen.dart';
import 'approvals.dart';
import 'archived.dart';
import 'audit_screen.dart';
import 'bell.dart';
import 'dashboard.dart';
import 'docs.dart';
import 'new_project.dart';
import 'notifications_panel.dart';
import 'project_detail.dart';
import 'settings_screen.dart';
import 'shell.dart' show showPortsSheet, askChatName, confirmDeleteChat;
import 'ui_agents.dart';
import 'ui_projects.dart';
import 'v2_news.dart';
import 'whatsapp.dart';

/// v2 PHONE-FIRST shell (iOS/Android only — the web keeps the sidebar Shell).
/// Bottom tabs (Home · Projects · Chats · Approvals · More), each with its OWN navigation stack, so you can go
/// deeper (project → agent) and come back with the back button / swipe, and every tab keeps its place.
/// Every screen is the same screen the web/desktop uses — same data, same actions, same backend; only the
/// layout and navigation are phone-native.
class MobileShell extends StatefulWidget {
  const MobileShell({super.key});
  @override
  State<MobileShell> createState() => _MobileShellState();
}

class _MobileShellState extends State<MobileShell> {
  int _tab = 0;
  final _navs = List.generate(5, (_) => GlobalKey<NavigatorState>());
  Timer? _poll;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final s = context.read<AppState>();
      s.navToProject = (pid) => _openProject(pid, switchTab: true);
      s.refreshDashboard();
      s.refreshAnchor();
      s.refreshNotifs();
    });
    // same light change-detector as the web shell
    _poll = Timer.periodic(const Duration(seconds: 12), (_) async {
      final s = context.read<AppState>();
      s.refreshNotifs();
      if (await s.pollForChanges()) {
        s.refreshAnchor();
        s.refreshDashboard();
      }
    });
  }

  @override
  void dispose() {
    _poll?.cancel();
    super.dispose();
  }

  NavigatorState? get _nav => _navs[_tab].currentState;

  void _openProject(String pid, {bool switchTab = false}) {
    if (switchTab) setState(() => _tab = 1);
    WidgetsBinding.instance.addPostFrameCallback((_) => _navs[switchTab ? 1 : _tab].currentState?.push(_route(_ProjectPage(pid: pid))));
  }

  @override
  Widget build(BuildContext context) {
    final s = context.watch<AppState>();
    final roots = <Widget>[
      _HomeTab(onOpenProject: (pid) => _nav?.push(_route(_ProjectPage(pid: pid))),
          onOpenAgent: (pid, a) => _nav?.push(_route(_AgentPage(pid: pid, name: a)))),
      _ProjectsTab(onOpen: (pid) => _nav?.push(_route(_ProjectPage(pid: pid)))),
      _ChatsTab(onOpenChat: (scope, title) {
        s.openChat(scope, title);
        _nav?.push(_route(_Page(title: title, child: const WhatsAppMode())));
      }),
      const _Page(title: 'Approvals', root: true, child: ApprovalsScreen()),
      _MoreTab(push: (w) => _nav?.push(_route(w))),
    ];
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) async {
        if (didPop) return;
        if (_nav?.canPop() == true) {
          _nav?.pop();
        } else if (_tab != 0) {
          setState(() => _tab = 0);
        }
      },
      child: Container(
        decoration: Odin.bgDecoration,
        child: Scaffold(
          backgroundColor: Colors.transparent,
          body: IndexedStack(
            index: _tab,
            children: [
              for (var i = 0; i < 5; i++)
                Navigator(
                  key: _navs[i],
                  onGenerateRoute: (_) => _route(roots[i]),
                ),
            ],
          ),
          bottomNavigationBar: NavigationBarTheme(
            data: NavigationBarThemeData(
              backgroundColor: const Color(0xF20E1020),
              indicatorColor: Odin.brand.withOpacity(.22),
              labelTextStyle: WidgetStateProperty.all(const TextStyle(fontSize: 11, fontWeight: FontWeight.w600)),
            ),
            child: NavigationBar(
              height: 64,
              selectedIndex: _tab,
              onDestinationSelected: (i) {
                if (i == _tab) {
                  _nav?.popUntil((r) => r.isFirst); // tap the active tab again → back to its top
                } else {
                  setState(() => _tab = i);
                }
              },
              destinations: [
                const NavigationDestination(icon: Icon(Icons.home_outlined), selectedIcon: Icon(Icons.home), label: 'Home'),
                const NavigationDestination(icon: Icon(Icons.folder_outlined), selectedIcon: Icon(Icons.folder), label: 'Projects'),
                const NavigationDestination(icon: Icon(Icons.forum_outlined), selectedIcon: Icon(Icons.forum), label: 'Chats'),
                const NavigationDestination(icon: Icon(Icons.verified_outlined), selectedIcon: Icon(Icons.verified), label: 'Approvals'),
                NavigationDestination(
                  icon: Badge(isLabelVisible: s.unreadNotifs > 0, label: Text('${s.unreadNotifs}'), child: const Icon(Icons.grid_view_outlined)),
                  selectedIcon: const Icon(Icons.grid_view_rounded),
                  label: 'More',
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

PageRoute _route(Widget w) => MaterialPageRoute(builder: (_) => w);

/// A pushed page: phone app bar (back arrow when it is not a tab root) + the shared screen body.
class _Page extends StatelessWidget {
  final String title;
  final Widget child;
  final bool root;
  final List<Widget> actions;
  const _Page({required this.title, required this.child, this.root = false, this.actions = const []});
  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          backgroundColor: const Color(0xE608090F),
          surfaceTintColor: Colors.transparent,
          automaticallyImplyLeading: !root,
          titleSpacing: root ? 16 : 0,
          title: Text(title, maxLines: 1, overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700)),
          actions: [...actions, const _BellButton(), const SizedBox(width: 4)],
        ),
        body: SafeArea(top: false, bottom: false, child: child),
      );
}

class _BellButton extends StatelessWidget {
  const _BellButton();
  @override
  Widget build(BuildContext context) {
    final s = context.watch<AppState>();
    return IconButton(
      tooltip: 'Notifications',
      onPressed: () => showNotifications(context),
      icon: Badge(isLabelVisible: s.unreadNotifs > 0, label: Text('${s.unreadNotifs}'), child: const Icon(Icons.notifications_none)),
    );
  }
}

// ------------------------------------------------------------------ Home
class _HomeTab extends StatelessWidget {
  final void Function(String pid) onOpenProject;
  final void Function(String pid, String agent) onOpenAgent;
  const _HomeTab({required this.onOpenProject, required this.onOpenAgent});
  @override
  Widget build(BuildContext context) {
    final s = context.watch<AppState>();
    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: AppBar(
        backgroundColor: const Color(0xE608090F),
        surfaceTintColor: Colors.transparent,
        titleSpacing: 16,
        title: const Row(children: [
          Text('Odin', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800)),
          SizedBox(width: 8),
          V2Badge(),
        ]),
        actions: [
          IconButton(tooltip: 'Refresh', icon: const Icon(Icons.refresh), onPressed: () {
            s.refreshDashboard(); s.refreshAnchor(); s.refreshNotifs();
          }),
          const _BellButton(),
        ],
      ),
      body: Column(children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 4, 16, 6),
          child: Wrap(spacing: 14, runSpacing: 4, children: [
            StatusDot(state: s.health?.ok == true ? 'ok' : 'bad', label: s.health?.ok == true ? 'Connected' : 'Offline'),
            if (s.requireLogin)
              StatusDot(state: s.loggedIn ? 'ok' : 'warn', label: s.loggedIn ? 'Signed in · 7 days' : 'Sign-in needed'),
          ]),
        ),
        Expanded(child: DashboardScreen(onOpenProject: onOpenProject, onOpenAgent: onOpenAgent)),
      ]),
    );
  }
}

// ------------------------------------------------------------------ Projects
class _ProjectsTab extends StatelessWidget {
  final void Function(String pid) onOpen;
  const _ProjectsTab({required this.onOpen});
  @override
  Widget build(BuildContext context) {
    final s = context.watch<AppState>();
    return _Page(
      title: 'Projects',
      root: true,
      actions: [
        IconButton(tooltip: 'All projects (cards)', icon: const Icon(Icons.dashboard_customize_outlined),
            onPressed: () => Navigator.of(context).push(_route(_Page(title: 'All projects', child: UiProjectsScreen(onOpenProject: onOpen))))),
      ],
      child: Stack(children: [
        RefreshIndicator(
          color: Odin.brand,
          onRefresh: () => s.refreshDashboard(),
          child: ListView.separated(
            physics: const AlwaysScrollableScrollPhysics(parent: BouncingScrollPhysics()),
            padding: const EdgeInsets.fromLTRB(14, 8, 14, 96),
            itemCount: s.projects.isEmpty ? 1 : s.projects.length,
            separatorBuilder: (_, __) => const SizedBox(height: 8),
            itemBuilder: (_, i) {
              if (s.projects.isEmpty) {
                return const Padding(padding: EdgeInsets.all(30), child: Center(child: Text('No projects yet', style: TextStyle(color: Odin.txtFaint))));
              }
              final p = s.projects[i];
              final t = typeByKey(p.type);
              return Material(
                color: const Color(0x0DFFFFFF),
                borderRadius: BorderRadius.circular(14),
                child: InkWell(
                  borderRadius: BorderRadius.circular(14),
                  onTap: () => onOpen(p.id),
                  child: Padding(
                    padding: const EdgeInsets.all(14),
                    child: Row(children: [
                      Container(
                        width: 40, height: 40,
                        decoration: BoxDecoration(borderRadius: BorderRadius.circular(12), color: Odin.brand.withOpacity(.16)),
                        child: Center(child: Text(t?.icon ?? '📁', style: const TextStyle(fontSize: 19))),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Text(p.name, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
                          const SizedBox(height: 2),
                          Text(p.description.isNotEmpty ? p.description : (t?.label ?? p.type),
                              maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12, color: Odin.txtDim)),
                        ]),
                      ),
                      const Icon(Icons.chevron_right, color: Odin.txtFaint),
                    ]),
                  ),
                ),
              );
            },
          ),
        ),
        Positioned(
          right: 16, bottom: 16,
          child: FloatingActionButton.extended(
            backgroundColor: Odin.brand,
            foregroundColor: const Color(0xFF0B0B16),
            onPressed: () => showNewProject(context, onCreated: onOpen),
            icon: const Icon(Icons.add),
            label: const Text('New project', style: TextStyle(fontWeight: FontWeight.w700)),
          ),
        ),
      ]),
    );
  }
}

class _ProjectPage extends StatelessWidget {
  final String pid;
  const _ProjectPage({required this.pid});
  @override
  Widget build(BuildContext context) {
    final s = context.watch<AppState>();
    var name = 'Project';
    for (final p in s.projects) {
      if (p.id == pid) name = p.name;
    }
    return _Page(
      title: name,
      child: ProjectDetail(
        key: ValueKey('project:$pid'),
        pid: pid,
        onOpenAgent: (a) => Navigator.of(context).push(_route(_AgentPage(pid: pid, name: a))),
      ),
    );
  }
}

class _AgentPage extends StatelessWidget {
  final String pid, name;
  const _AgentPage({required this.pid, required this.name});
  @override
  Widget build(BuildContext context) =>
      _Page(title: name, child: AgentDetail(key: ValueKey('agent:$pid:$name'), pid: pid, name: name));
}

// ------------------------------------------------------------------ Chats (the WhatsApp-style pool)
class _ChatsTab extends StatelessWidget {
  final void Function(String scope, String title) onOpenChat;
  const _ChatsTab({required this.onOpenChat});
  @override
  Widget build(BuildContext context) {
    final s = context.watch<AppState>();
    Widget row(String icon, String title, String sub, VoidCallback onTap, {VoidCallback? onLong}) => ListTile(
          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 2),
          leading: CircleAvatar(radius: 22, backgroundColor: Odin.brand.withOpacity(.16), child: Text(icon, style: const TextStyle(fontSize: 18))),
          title: Text(title, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w600)),
          subtitle: Text(sub, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12, color: Odin.txtFaint)),
          trailing: const Icon(Icons.chevron_right, color: Odin.txtFaint),
          onTap: onTap,
          onLongPress: onLong,
        );
    Widget header(String t) => Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 4),
          child: Text(t, style: const TextStyle(fontSize: 11, letterSpacing: 1, color: Odin.txtFaint, fontWeight: FontWeight.w700)),
        );
    return _Page(
      title: 'Chats',
      root: true,
      actions: [
        IconButton(
          tooltip: 'New chat',
          icon: const Icon(Icons.add_comment_outlined),
          onPressed: () async {
            final name = await askChatName(context, '');
            if (name == null || name.isEmpty) return;
            final scope = await s.newAdhocChat(name);
            if (scope.isNotEmpty) onOpenChat(scope, name);
          },
        ),
      ],
      child: RefreshIndicator(
        color: Odin.brand,
        onRefresh: () async { await s.refreshChats(); await s.refreshDashboard(); },
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(parent: BouncingScrollPhysics()),
          padding: const EdgeInsets.only(bottom: 24),
          children: [
            row('🏛️', 'Company — Chief Engineer', 'company-wide view of every project', () => onOpenChat('company', 'Company — Chief Engineer')),
            header('PROJECTS'),
            for (final p in s.projects)
              row(typeByKey(p.type)?.icon ?? '📁', p.name, 'project chat · CTO + team', () => onOpenChat('project:${p.id}', p.name)),
            header('CHATS'),
            for (final c in s.adhocChats)
              row('💬', c['title'] ?? 'Chat', 'long-press to rename or delete', () => onOpenChat(c['scope'] ?? '', c['title'] ?? 'Chat'),
                  onLong: () => _chatMenu(context, s, c)),
            if (s.adhocChats.isEmpty)
              const Padding(padding: EdgeInsets.all(16), child: Text('No chats yet — tap ＋ above', style: TextStyle(color: Odin.txtFaint, fontSize: 12.5))),
          ],
        ),
      ),
    );
  }

  void _chatMenu(BuildContext context, AppState s, Map c) {
    showModalBottomSheet(
      context: context,
      backgroundColor: Odin.bg2,
      builder: (ctx) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          ListTile(leading: const Icon(Icons.edit_outlined), title: const Text('Rename'), onTap: () async {
            Navigator.pop(ctx);
            final name = await askChatName(context, c['title'] ?? '');
            if (name != null && name.isNotEmpty) await s.renameChat(c['scope'] ?? '', name);
          }),
          ListTile(leading: const Icon(Icons.delete_outline, color: Odin.danger), title: const Text('Delete', style: TextStyle(color: Odin.danger)), onTap: () async {
            Navigator.pop(ctx);
            if (await confirmDeleteChat(context, c['title'] ?? 'this chat')) await s.clearConversation(c['scope'] ?? '');
          }),
        ]),
      ),
    );
  }
}

// ------------------------------------------------------------------ More
class _MoreTab extends StatelessWidget {
  final void Function(Widget) push;
  const _MoreTab({required this.push});
  @override
  Widget build(BuildContext context) {
    final s = context.watch<AppState>();
    Widget tile(IconData i, String t, String sub, VoidCallback onTap, {Color? color}) => ListTile(
          leading: Container(
            width: 38, height: 38,
            decoration: BoxDecoration(borderRadius: BorderRadius.circular(11), color: (color ?? Odin.brand).withOpacity(.16)),
            child: Icon(i, size: 20, color: color ?? Odin.brand),
          ),
          title: Text(t, style: const TextStyle(fontWeight: FontWeight.w600)),
          subtitle: Text(sub, style: const TextStyle(fontSize: 12, color: Odin.txtFaint)),
          trailing: const Icon(Icons.chevron_right, color: Odin.txtFaint),
          onTap: onTap,
        );
    Widget header(String t) => Padding(
          padding: const EdgeInsets.fromLTRB(16, 18, 16, 4),
          child: Text(t, style: const TextStyle(fontSize: 11, letterSpacing: 1, color: Odin.txtFaint, fontWeight: FontWeight.w700)),
        );
    return _Page(
      title: 'More',
      root: true,
      child: ListView(
        physics: const BouncingScrollPhysics(),
        padding: const EdgeInsets.only(bottom: 24),
        children: [
          header('WORK'),
          tile(Icons.groups_outlined, 'Agents', 'every agent, grouped by type', () => push(const _Page(title: 'Agents', child: UiAgentsScreen()))),
          tile(Icons.notifications_none, 'Notifications', '${s.unreadNotifs} unread', () => showNotifications(context), color: Odin.warn),
          tile(Icons.inventory_2_outlined, 'Archived projects', 'view and restore', () => push(_Page(title: 'Archived', child: ArchivedScreen(onOpenProject: (pid) => push(_ProjectPage(pid: pid)))))),
          header('SYSTEM'),
          tile(Icons.hub_outlined, 'Anchor Connect', 'queue, webhooks, statuses', () => push(const _Page(title: 'Anchor Connect', child: AnchorScreen())), color: Odin.brand2),
          tile(Icons.radar_outlined, 'Audit / Observer', 'structure integrity', () => push(const _Page(title: 'Audit', child: AuditScreen())), color: Odin.brand2),
          tile(Icons.lan_outlined, 'Ports & environment', 'development / production map', () => showPortsSheet(context, s), color: Odin.brand2),
          header('HELP'),
          tile(Icons.auto_awesome_outlined, "What's new in v2", 'Jev, phone approvals, security, paper', () => showWhatsNew(context), color: Odin.accent),
          tile(Icons.menu_book_outlined, 'Guide', 'how-to and updates', () => showBell(context), color: Odin.accent),
          tile(Icons.description_outlined, 'Documentation', 'the full docs', () => push(const _Page(title: 'Documentation', child: DocsScreen())), color: Odin.accent),
          header('ACCOUNT'),
          tile(Icons.settings_outlined, 'Settings', 'connection, environment, preferences', () => push(const _Page(title: 'Settings', child: SettingsScreen())), color: Odin.txtDim),
          if (s.requireLogin && s.loggedIn)
            tile(Icons.logout, 'Log out', 'ends the 7-day session', () => s.logout(), color: Odin.danger),
          const SizedBox(height: 10),
          const Center(child: Text('Odin v2 · phone', style: TextStyle(fontSize: 11, color: Odin.txtFaint))),
        ],
      ),
    );
  }
}
