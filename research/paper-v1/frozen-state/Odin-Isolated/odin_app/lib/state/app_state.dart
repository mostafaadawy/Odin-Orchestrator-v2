import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../api/anchor_api.dart';
import '../config.dart';
import '../models/models.dart';
import '../services/notifications.dart';
import '../screens/bell.dart' show kBellTabs;

/// Single source of truth. Refresh is ON-DEMAND (click) — no background timers —
/// plus webhook-driven banner alerts when the anchor feed reveals new terminal states.
class AppState extends ChangeNotifier {
  AppConfig cfg;
  late OdinApi api;
  final Notifier notifier = Notifier();

  AppState(this.cfg) {
    api = OdinApi(cfg.active);
  }

  static Future<AppState> create() async {
    final cfg = await AppConfig.load();
    // PHASE-3 AUTO-SELECT: when the app is launched by phase3_up.sh it passes
    // --dart-define=ODIN_FORCE_ENV=production. We then SELECT the "Deployed (Phase 3)" profile
    // automatically (so testing hits the real IP), WITHOUT deleting or overwriting any profile the
    // user edited. If the user later switches manually, that choice is respected on the next launch.
    // Both phases run the app in ANCHOR mode — the ONLY difference is which anchor URL is selected:
    //   production → the VM domain profile ("Deployed (Phase 3)")
    //   phase2     → the LOCAL anchor profile ("Anchor (local — Phase 2)")
    // Selecting by anchor URL (localhost vs remote) makes this robust regardless of profile names/order.
    const forceEnv = String.fromEnvironment('ODIN_FORCE_ENV');
    int pick = -1;
    if (forceEnv == 'production') {
      pick = cfg.profiles.indexWhere((p) => p.mode == AccessMode.anchor &&
          !(p.anchorBaseUrl.contains('localhost') || p.anchorBaseUrl.contains('127.0.0.1')));
    } else if (forceEnv == 'phase2') {
      pick = cfg.profiles.indexWhere((p) => p.mode == AccessMode.anchor &&
          (p.anchorBaseUrl.contains('localhost') || p.anchorBaseUrl.contains('127.0.0.1')));
    }
    if (pick >= 0) {
      cfg.selected = pick;
      await cfg.save();
    }
    final s = AppState(cfg);
    await s.notifier.init();
    await s.bootAuth();
    return s;
  }

  // ---------- auth ----------
  bool authResolved = false;       // we've checked config + any saved session
  bool requireLogin = true;        // from /auth/config (web/mobile)
  bool loggedIn = false;
  bool pendingBiometric = false; // saved session exists; mobile must unlock with Face ID first
  String? authToken;
  String authedEmail = '';
  Map<String, dynamic> authConfig = {};
  String authError = '';
  static const _kTok = 'odin.authToken';

  void resumeAfterBiometric() {
    pendingBiometric = false;
    loggedIn = authToken != null && authToken!.isNotEmpty;
    notifyListeners();
  }

  Future<void> bootAuth() async {
    // ANCHOR mode (web/mobile, incl. Phase-2 anchor + Phase-3 production): login goes THROUGH THE ANCHOR —
    // one flow (saved email + password) + a random, target-specific CODE shown on the desktop. REQUIRE it
    // (never bypass). The anchor enforces the 7-day session server-side; here we just resume a valid token.
    if (cfg.active.apiBase.isEmpty && cfg.active.mode == AccessMode.anchor) {
      requireLogin = true;
      loggedIn = false;
      try {
        final p = await SharedPreferences.getInstance();
        final tok = p.getString(_kTok) ?? '';
        if (tok.isNotEmpty) {
          api.mngToken = tok;
          authToken = tok;
          final ok = await api.anchorSessionValid(); // false once the 7 days expire → asks to log in again
          if (ok) {
            loggedIn = true;
          } else {
            api.mngToken = '';
            authToken = null;
            await p.remove(_kTok);
          }
        }
      } catch (_) {}
      authResolved = true;
      notifyListeners();
      return;
    }
    try {
      authConfig = await api.authConfig();
      requireLogin = kIsWeb
          ? (authConfig['require_login_web'] != false)
          : (authConfig['require_login_mobile'] != false);
    } catch (_) {
      // FAIL CLOSED: if the auth policy can't be verified, REQUIRE login — never grant access on an error.
      // This machine can reach your terminal + Azure, so "locked when unsure" must beat "open when unsure".
      requireLogin = true;
    }
    if (requireLogin) {
      final p = await SharedPreferences.getInstance();
      final tok = p.getString(_kTok);
      if (tok != null && tok.isNotEmpty) {
        try {
          final me = await api.me(tok);
          if (me['ok'] == true) {
            authToken = tok;
            authedEmail = (me['email'] ?? '').toString();
            if (!kIsWeb && authConfig['faceid_first_access'] == true) {
              pendingBiometric = true; // require Face ID to resume on mobile
              loggedIn = false;
            } else {
              loggedIn = true;
            }
          }
        } catch (_) {}
      }
    } else {
      loggedIn = true;
    }
    authResolved = true;
    notifyListeners();
  }

  bool get gateOpen => !requireLogin || loggedIn;

  // ANCHOR login (web/mobile): ask the anchor to generate a fresh code (shown on the desktop badge).
  Future<String?> requestLoginCode() async {
    try { await api.anchorRequestCode(); return null; }
    catch (e) { return 'Could not reach the anchor to request a code'; }
  }

  // ANCHOR login: one flow — email + password + the desktop code. On success, save the 7-day session.
  Future<String?> loginViaAnchor(String email, String password, String code) async {
    try {
      final tok = await api.anchorLogin(email, password, code);
      if (tok.isEmpty) return 'Login failed';
      api.mngToken = tok;
      authToken = tok;
      authedEmail = email;
      loggedIn = true;
      final p = await SharedPreferences.getInstance();
      await p.setString(_kTok, tok);
      notifyListeners();
      return null;
    } catch (e) {
      return 'Login failed: check email, password and the code on your desktop';
    }
  }

  Future<String?> login(String email, String password) async {
    // In anchor mode the login must go through the anchor (this path is backend-only / direct mode).
    if (isAnchorMode) return 'Use the desktop code to sign in';
    try {
      final r = await api.login(email, password);
      if (r['twofa_required'] == true) return '2fa:${r['email']}';
      await _finishLogin(r);
      return null;
    } catch (e) {
      return 'Login failed: invalid email or password';
    }
  }

  Future<String?> submit2fa(String email, String code) async {
    try {
      await _finishLogin(await api.twofa(email, code));
      return null;
    } catch (_) {
      return 'Invalid 2FA code';
    }
  }

  Future<void> _finishLogin(Map<String, dynamic> r) async {
    authToken = (r['token'] ?? '').toString();
    authedEmail = (r['email'] ?? '').toString();
    loggedIn = authToken!.isNotEmpty;
    final p = await SharedPreferences.getInstance();
    await p.setString(_kTok, authToken ?? '');
    notifyListeners();
  }

  Future<void> logout() async {
    try {
      if (isAnchorMode) {
        await api.anchorLogout();
      } else if (authToken != null) {
        await api.logout(authToken!);
      }
    } catch (_) {}
    api.mngToken = '';
    authToken = null;
    loggedIn = false;
    pendingBiometric = false;
    final p = await SharedPreferences.getInstance();
    await p.remove(_kTok);
    notifyListeners();
  }

  Future<String?> changePassword(String oldPw, String newPw) async {
    try {
      await api.changePassword(authedEmail.isEmpty ? 'tech@odinmarkets.com' : authedEmail, oldPw, newPw);
      return null;
    } catch (e) {
      return 'Could not change password (check current password)';
    }
  }

  Future<void> setAuthFlag(String key, bool value) async {
    try {
      authConfig = await api.setAuthConfig({key: value});
      notifyListeners();
    } catch (_) {}
  }

  Future<void> forgot(String email) async {
    try {
      await api.forgot(email);
    } catch (_) {}
  }

  EnvProfile get env => cfg.active;
  AccessMode get mode => env.mode;
  bool get isAnchorMode => env.mode == AccessMode.anchor; // web/mobile go ONLY through the anchor

  /// "offline · last synced X ago" badge for production (anchor) mode. Empty when live/local so the
  /// UI only shows it when the desktop is actually closed and the mirror is stale (WhatsApp-style).
  bool get syncStale => (api.lastSync?['stale'] == true);
  String get syncLabel {
    final ls = api.lastSync;
    if (ls == null) return '';
    final age = (ls['age_seconds'] is int) ? ls['age_seconds'] as int : -1;
    if ((ls['updated'] ?? 0) == 0) return 'offline · no synced data yet';
    if (!syncStale) return 'live · synced just now';
    if (age < 3600) return 'offline · last synced ${(age / 60).floor()}m ago';
    if (age < 86400) return 'offline · last synced ${(age / 3600).floor()}h ago';
    return 'offline · last synced ${(age / 86400).floor()}d ago';
  }

  // STANDALONE CHATS — server-side registry shared by web/mobile/desktop. In anchor mode it is read from the
  // anchor mirror (key 'chats'); creating/deleting go through the anchor as commands the Mac executes on the
  // brain. So new chats sync across every surface, and web/mobile never touch the backend.
  List<Map<String, dynamic>> chats = [];

  // WhatsApp-style CACHE of each scope's pool — so reopening a conversation shows the last messages INSTANTLY
  // (no blank wait, less data/tokens), then we sync fresh in the background and update. Kept in memory for the
  // session; the durable copy is the anchor mirror / brain pool.
  final Map<String, List<Map<String, dynamic>>> poolCache = {};

  // NORMAL-MODE chat selection — driven by the LEFT SIDEBAR "CHATS" section (parallel to PROJECTS), NOT a
  // horizontal strip. The dashboard chat area renders whichever chat scope is active here.
  String activeChatScope = 'company';
  String activeChatTitle = 'Company — Chief Engineer';
  void openChat(String scope, String title) {
    activeChatScope = scope;
    activeChatTitle = title;
    notifyListeners();
  }

  List<Map<String, String>> get adhocChats => chats
      .map((c) => {'scope': (c['scope'] ?? '').toString(), 'title': (c['title'] ?? 'Chat').toString()})
      .toList();

  Future<void> refreshChats() async {
    try {
      chats = await api.chats();
      notifyListeners();
    } catch (_) {}
  }

  Future<String> newAdhocChat(String name) async {
    if (isAnchorMode) {
      await api.commandViaAnchor('create_chat', {'title': name});
      await Future.delayed(const Duration(milliseconds: 900));
    } else {
      await api.createChatDirect(name);
    }
    await refreshChats();
    return chats.isNotEmpty ? (chats.first['scope'] ?? '').toString() : 'chat:new';
  }

  /// Rename a chat — through the ANCHOR on web/mobile (a queued command the Mac executes), never a direct
  /// backend call. Updates the active title immediately so the header reflects it.
  Future<void> renameChat(String scope, String title) async {
    final t = title.trim();
    if (t.isEmpty) return;
    try {
      if (isAnchorMode) {
        await api.commandViaAnchor('rename_chat', {'scope': scope, 'title': t});
        await Future.delayed(const Duration(milliseconds: 700));
      } else {
        await api.renameChatDirect(scope, t);
      }
    } catch (_) {}
    if (activeChatScope == scope) activeChatTitle = t;
    await refreshChats();
    notifyListeners();
  }

  /// Create a project — through the ANCHOR on web/mobile (a queued command the Mac executes), directly on
  /// desktop/local. Returns null on success or an error string.
  Future<String?> createProjectAnywhere(String name) async {
    try {
      if (isAnchorMode) {
        await api.commandViaAnchor('create_project', {'name': name});
        await Future.delayed(const Duration(seconds: 1));
        await refreshDashboard();
      } else {
        await api.createProject(name: name);
        await refreshDashboard();
      }
      return null;
    } catch (e) {
      return 'Could not create project: $e';
    }
  }

  /// Delete a conversation — through the anchor (web/mobile) or backend (desktop).
  Future<void> clearConversation(String scope) async {
    try {
      if (scope.startsWith('chat:')) {
        if (isAnchorMode) {
          await api.commandViaAnchor('delete_chat', {'scope': scope});
        } else {
          await api.deleteChatDirect(scope);
        }
      } else if (isAnchorMode) {
        await api.commandViaAnchor('clear_scope', {'scope': scope});
      }
      await refreshChats();
    } catch (_) {}
    notifyListeners();
  }

  // caches
  Health? health;
  List<Project> projects = [];
  List<Role> roles = [];
  List<CompanyAgent> companyAgents = [];
  List<Map<String, dynamic>> allAgentsRoster = []; // ORG-WIDE roster of ACTUAL agents (every project + company)
  List<Connector> connectors = [];
  List<Activity> activity = [];
  List<AnchorRequest> requests = [];
  Map<String, int> counts = {};
  Map<String, dynamic>? anchorCfg;
  Map<String, dynamic>? vm;

  bool loadingDash = false;
  bool loadingAnchor = false;
  String? dashError;
  String? anchorError;

  // OFFLINE STATE — in anchor mode the anchor is the ONLY door. If it's unreachable we are offline:
  // show a clear message, NO stale/backend data, and never an endless spinner. Cleared once the anchor
  // answers again (then we load + sync). This is the visible proof the app depends on the anchor.
  bool offline = false;
  String offlineMsg = 'Offline — the anchor is unavailable. Pull to refresh once it is back.';

  Set<String> get activeKeys => activity.map((a) => a.key).toSet();
  Map<String, Activity> get activeByKey => {for (final a in activity) a.key: a};

  // the bell badge shows the REAL number of notification/documentation tabs (kBellTabs — single source of
  // truth), so it auto-updates whenever a tab is added. (Was hardcoded to 2; now tracks the actual tabs.)
  int get bellCount => kBellTabs.length + newEvents;

  String? banner;
  int newEvents = 0;

  // ---- Notifications (recurring/periodical live feed) ----
  List<Map<String, dynamic>> notifs = [];
  int unreadNotifs = 0;
  bool notifPulse = false; // set true briefly when a NEW unread arrives → the bell shakes
  Future<void> refreshNotifs() async {
    try {
      final d = await api.notifications();
      notifs = List<Map<String, dynamic>>.from(d['items'] ?? []);
      final u = (d['unread'] ?? 0) as int;
      notifPulse = u > unreadNotifs; // more unread than before → pulse the bell
      unreadNotifs = u;
      notifyListeners();
      if (notifPulse) {
        Future.delayed(const Duration(seconds: 3), () { notifPulse = false; notifyListeners(); });
      }
    } catch (_) {}
  }
  Future<void> markNotif(String id) async { await api.markNotifRead(id: id); await refreshNotifs(); }
  Future<void> markAllNotifs() async { await api.markNotifRead(all: true); await refreshNotifs(); }
  // set by the shell so any widget (e.g. the notifications panel) can redirect to a project.
  void Function(String pid)? navToProject;
  void openProjectById(String pid) { navToProject?.call(pid); }
  void clearBanner() {
    banner = null;
    notifyListeners();
  }

  void clearNewEvents() {
    newEvents = 0;
    notifyListeners();
  }

  final Set<String> _alerted = {};

  Future<void> selectProfile(int i) async {
    cfg.selected = i.clamp(0, cfg.profiles.length - 1);
    await cfg.save();
    api = OdinApi(cfg.active);
    _alerted.clear();
    notifyListeners();
  }

  Future<void> saveProfiles() async {
    await cfg.save();
    api = OdinApi(cfg.active);
    notifyListeners();
  }

  // Guarantee the "checking…" spinner is VISIBLE for a real moment. A closed port refuses the connection
  // instantly, so without this the retry would flip back to offline before the spinner ever paints — making
  // it look like it never tried. This holds the spinner so the user actually sees a genuine attempt.
  Future<void> _minSpin(DateTime startedAt) async {
    const floor = Duration(milliseconds: 800);
    final elapsed = DateTime.now().difference(startedAt);
    if (elapsed < floor) await Future.delayed(floor - elapsed);
  }

  // ---- dashboard load (click) ----
  Future<void> refreshDashboard() async {
    final spinAt = DateTime.now();
    loadingDash = true;
    dashError = null;
    notifyListeners();
    // ESSENTIALS first — render immediately so the UI is never blocked on slow calls.
    try {
      health = await api.health();
      offline = false;
    } catch (e) {
      health = null;
      // ANCHOR MODE: the anchor is the ONLY way to any data. If it's unreachable we are OFFLINE — clear all
      // data so nothing stale/backend shows, stop the spinner, and let the UI display the offline message.
      if (env.mode == AccessMode.anchor) {
        await _minSpin(spinAt); // let the user SEE the attempt before we say offline
        offline = true;
        projects = [];
        roles = [];
        companyAgents = [];
        connectors = [];
        activity = [];
        loadingDash = false;
        notifyListeners();
        return;
      }
      dashError = 'health @ ${env.apiBase}: $e';
    }
    // ROBUST AUTO-SWITCH: if we're on a LOCAL (direct) profile but the local brain is unreachable
    // (mobile/web in production can't see localhost), switch to the Deployed anchor profile ourselves so
    // the app just works — no manual "Use Production" needed, no dependence on the compile-time flag.
    if (health == null && env.mode == AccessMode.direct) {
      final i = cfg.profiles.indexWhere(
          (p) => p.mode == AccessMode.anchor && p.name.toLowerCase().contains('deployed'));
      if (i >= 0 && i != cfg.selected) {
        await selectProfile(i);
        try {
          health = await api.health();
        } catch (_) {}
      }
    }
    try {
      projects = await api.projects();
      offline = false;
    } catch (e) {
      if (env.mode == AccessMode.anchor) {
        await _minSpin(spinAt);
        offline = true;
        projects = [];
        loadingDash = false;
        notifyListeners();
        return;
      }
      dashError = 'projects: $e';
    }
    loadingDash = false;
    notifyListeners(); // dashboard paints now with projects

    // ENRICH in the background — each updates the UI as it arrives; the slow Azure VM
    // probe runs on its own and never blocks the rest.
    _bg(() async => chats = await api.chats());
    _bg(() async => roles = await api.roles());
    _bg(() async => companyAgents = await api.companyAgents());
    _bg(() async => allAgentsRoster = await api.allAgents());
    _bg(() async => connectors = await api.connectors());
    _bg(() async => activity = await api.activity());
    _bg(() async => vm = await api.connectTest());
  }

  void _bg(Future<void> Function() f) {
    f().then((_) => notifyListeners()).catchError((_) {});
  }

  Future<void> refreshActivity() async {
    try {
      activity = await api.activity();
      notifyListeners();
    } catch (_) {}
  }

  // ---- anchor load (click) ----
  Future<void> refreshAnchor() async {
    loadingAnchor = true;
    anchorError = null;
    notifyListeners();
    try {
      final r = await Future.wait([api.anchorCounts(), api.anchorRequests(), api.anchorConfig()]);
      counts = r[0] as Map<String, int>;
      requests = r[1] as List<AnchorRequest>;
      anchorCfg = r[2] as Map<String, dynamic>;
      _detect(requests);
    } catch (e) {
      anchorError = '$e';
    } finally {
      loadingAnchor = false;
      notifyListeners();
    }
  }

  void _detect(List<AnchorRequest> reqs) {
    if (_alerted.isEmpty) {
      for (final r in reqs) {
        if (r.isTerminal) _alerted.add(r.id);
      }
      return;
    }
    for (final r in reqs.where((r) => r.isTerminal && !_alerted.contains(r.id))) {
      _alerted.add(r.id);
      newEvents++;
      banner = 'Request ${r.id} → ${r.status.toUpperCase()} (project ${r.project})';
      notifier.show('Anchor: ${r.status}', banner!);
    }
  }

  Future<String> ask(String identifier, String prompt, {void Function(String)? onStatus}) async {
    if (mode == AccessMode.direct) {
      onStatus?.call('asking');
      return api.askDirect(identifier, prompt);
    }
    final r = await api.askViaAnchor(identifier, prompt, onStatus: onStatus);
    if (r.status == 'failed') return '(request failed: ${r.error})';
    final res = r.result;
    return res is String ? res : res?.toString() ?? '(no result)';
  }

  Future<String> companyChat(String text) => api.companyChat(text);

  Future<Project> createProject({
    required String name,
    String identifier = '',
    String description = '',
    String type = '',
    String cadence = 'once',
    List<Map<String, dynamic>>? members, // optional confirmed team (mobile parity with web)
  }) async {
    final p = await api.createProject(name: name, identifier: identifier, description: description, type: type, cadence: cadence, members: members);
    await refreshDashboard();
    return p;
  }

  /// Validate proposed agent names against the catalogue (known vs unknown) — mobile parity gate.
  Future<Map<String, dynamic>> validateAgents(List<String> names) => api.validateAgents(names);

  Future<Map<String, dynamic>> sendRequest(String project, String prompt, {String webhookUrl = ''}) =>
      api.sendRequest(project: project, prompt: prompt, webhookUrl: webhookUrl);

  /// Light change-detector for "auto refresh when something happens" without heavy
  /// polling: compares a fingerprint of anchor counts + live-agent count. Returns true
  /// if something changed since last check (caller then refreshes the open view).
  String _fingerprint = '';
  Future<bool> pollForChanges() async {
    try {
      final c = await api.anchorCounts();
      final act = await api.activity();
      final fp = '${c.toString()}|${act.length}';
      final changed = _fingerprint.isNotEmpty && fp != _fingerprint;
      _fingerprint = fp;
      if (changed) {
        counts = c;
        activity = act;
        notifyListeners();
      }
      return changed;
    } catch (_) {
      return false;
    }
  }

  Future<Map<String, dynamic>> testConnection() async {
    final out = <String, dynamic>{};
    try {
      final h = await api.health();
      out['brain'] = 'ok · ${h.engine}';
    } catch (e) {
      out['brain_error'] = '$e';
    }
    try {
      out['anchor_counts'] = await api.anchorCounts();
    } catch (e) {
      out['anchor_error'] = '$e';
    }
    return out;
  }
}
