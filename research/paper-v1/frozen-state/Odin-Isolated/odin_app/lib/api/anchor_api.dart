import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as http;

import '../config.dart';
import '../models/models.dart';
import '../services/sse.dart';

class ApiException implements Exception {
  final int status;
  final String message;
  ApiException(this.status, this.message);
  @override
  String toString() => 'ApiException($status): $message';
}

/// One client for the whole backend surface the desktop uses.
///  - NATIVE brain endpoints (/health, /projects, /roles, /activity, /operations, …)
///    on apiBaseUrl, authed with X-Odin-Token.
///  - /api/v1 ask on apiBaseUrl, authed with X-API-Key (odinApiKey).
///  - /anchor/v1 on anchorBaseUrl, authed with X-API-Key (anchorApiKey).
/// Only anchorBaseUrl changes for Phase 3.
class OdinApi {
  final EnvProfile env;
  OdinApi(this.env);

  // The logged-in session token (anchor manage session). Set by AppState after a successful anchor login;
  // sent on EVERY anchor call so the anchor can require a valid login for web/mobile (no anonymous access).
  String mngToken = '';
  String get _target => kIsWeb ? 'web' : 'mobile';

  // DELTA SYNC state (cursor-based): per-scope message cache + the highest seq we already have. Reads fetch
  // ONLY messages with seq > lastSeq and merge them in (dedup by id, sort by seq) — fast + gap-proof.
  final Map<String, List<Map<String, dynamic>>> _deltaCache = {};
  final Map<String, int> _lastSeq = {};

  int _maxSeqOf(List<Map<String, dynamic>> ms) {
    var m = 0;
    for (final x in ms) {
      final s = (x['seq'] is int) ? x['seq'] as int : int.tryParse('${x['seq']}') ?? 0;
      if (s > m) m = s;
    }
    return m;
  }

  /// The whole scope pool via CURSOR DELTA: first call full-pulls + caches; later calls fetch only seq>lastSeq
  /// and merge. Correct (merges by id, sorts by seq) and fast (tiny payload when little changed).
  Future<List<Map<String, dynamic>>> _anchorPoolDelta(String scope) async {
    final cached = _deltaCache[scope];
    final since = _lastSeq[scope] ?? 0;
    if (cached != null && since > 0) {
      final d = await _get(_anchor('/anchor/v1/pool/${Uri.encodeComponent(scope)}?since=$since'), _anchorKey());
      final m = d is Map ? Map<String, dynamic>.from(d) : <String, dynamic>{};
      final delta = ((m['messages'] ?? []) as List).map((x) => Map<String, dynamic>.from(x)).toList();
      if (delta.isNotEmpty) {
        final byId = {for (final x in cached) (x['id'] ?? '').toString(): x};
        for (final x in delta) byId[(x['id'] ?? '').toString()] = x;
        final merged = byId.values.toList()
          ..sort((a, b) => ((a['seq'] ?? 0) as int).compareTo((b['seq'] ?? 0) as int));
        _deltaCache[scope] = merged;
      }
      final mx = (m['max_seq'] is int) ? m['max_seq'] as int : since;
      _lastSeq[scope] = mx > since ? mx : since;
      // SELF-HEAL: if the server pool count differs from ours (a message was deleted/cleared), delta can't
      // see removals → do one authoritative full pull to re-sync exactly.
      final total = (m['total'] is int) ? m['total'] as int : -1;
      if (total >= 0 && (_deltaCache[scope]?.length ?? 0) != total) {
        final full = await _anchorPool(scope);
        _deltaCache[scope] = full;
        _lastSeq[scope] = _maxSeqOf(full);
        return List<Map<String, dynamic>>.from(full);
      }
      return List<Map<String, dynamic>>.from(_deltaCache[scope]!);
    }
    // first load (or no cursor yet) — full pull, then seed the cursor
    final full = await _anchorPool(scope);
    _deltaCache[scope] = full;
    _lastSeq[scope] = _maxSeqOf(full);
    return List<Map<String, dynamic>>.from(full);
  }

  Map<String, String> _native() => {
        'Content-Type': 'application/json',
        if (env.token.isNotEmpty) 'X-Odin-Token': env.token,
      };
  Map<String, String> _apiKey() => {
        'Content-Type': 'application/json',
        if (env.odinApiKey.isNotEmpty) 'X-API-Key': env.odinApiKey,
      };
  Map<String, String> _anchorKey() => {
        'Content-Type': 'application/json',
        if (env.anchorApiKey.isNotEmpty) 'X-API-Key': env.anchorApiKey,
        // identify this client so the anchor's Manage "allow/stop mobile|web" toggles can gate it
        'X-Odin-Client': kIsWeb ? 'web' : 'mobile',
        if (mngToken.isNotEmpty) 'X-Manage-Token': mngToken,
      };

  // ---- LOGIN through the anchor (production/anchor mode): ONE flow (email + password) + a random,
  // target-specific CODE shown on the desktop. Returns the session token on success. ----
  Future<void> anchorRequestCode() async {
    await _post(_anchor('/anchor/v1/manage/request-code'), _anchorKey(), {'target': _target});
  }

  Future<String> anchorLogin(String email, String password, String code, {bool remember = true, String? deviceId}) async {
    final d = await _post(_anchor('/anchor/v1/manage/login'), _anchorKey(), {
      'email': email, 'password': password, 'code': code, 'remember': remember,
      'target': _target, if (deviceId != null) 'device_id': deviceId,
    });
    final m = d is Map ? Map<String, dynamic>.from(d) : <String, dynamic>{};
    if (m['ok'] == true) return (m['token'] ?? '').toString();
    throw ApiException(401, (m['error'] ?? 'login failed').toString());
  }

  Future<bool> anchorSessionValid() async {
    if (mngToken.isEmpty) return false;
    try {
      final d = await _get(_anchor('/anchor/v1/manage/me'), _anchorKey());
      return d is Map && d['ok'] == true;
    } catch (_) {
      return false;
    }
  }

  Future<void> anchorLogout() async {
    try { await _post(_anchor('/anchor/v1/manage/logout'), _anchorKey(), {}); } catch (_) {}
    mngToken = '';
  }

  // HARD GUARANTEE: web/mobile in anchor mode must NEVER touch the backend directly — every path goes through
  // the anchor. So a backend URL cannot even be built in anchor mode; any such call throws instead of leaking.
  // (The desktop Electron app is the ONLY client that talks to the backend directly — it is not this code.)
  Uri _api(String p) {
    if (_anchorRead) {
      throw ApiException(0, 'backend is not reachable from the app — this must go through the anchor');
    }
    return Uri.parse('${env.apiBase}$p');
  }
  Uri _anchor(String p) => Uri.parse('${env.anchorBase}$p');

  dynamic _decode(http.Response r) {
    if (r.statusCode < 200 || r.statusCode >= 300) {
      // NEVER surface a raw HTML error page (nginx/Django 404 etc.) into the UI — keep it short + clean.
      var msg = r.body.isEmpty ? (r.reasonPhrase ?? '') : r.body;
      if (msg.contains('<!DOCTYPE') || msg.contains('<html') || msg.contains('<head')) {
        msg = 'the anchor returned an error page (HTTP ${r.statusCode})';
      } else if (msg.length > 160) {
        msg = '${msg.substring(0, 160)}…';
      }
      throw ApiException(r.statusCode, msg);
    }
    if (r.body.isEmpty) return {};
    // if a 200 body is actually HTML (misrouted), don't try to JSON-parse it — fail cleanly
    if (r.body.trimLeft().startsWith('<')) {
      throw ApiException(r.statusCode, 'unexpected HTML response (misrouted request)');
    }
    return jsonDecode(r.body);
  }

  static const _timeout = Duration(seconds: 15);
  Future<dynamic> _get(Uri u, Map<String, String> h) async =>
      _decode(await http.get(u, headers: h).timeout(_timeout));
  Future<dynamic> _post(Uri u, Map<String, String> h, [dynamic body]) async =>
      _decode(await http.post(u, headers: h, body: body == null ? null : jsonEncode(body)).timeout(_timeout));

  // In production the brain is LOCAL and unreachable from web/mobile — we read the WhatsApp-style mirror
  // from the anchor instead (fast, synced by the Mac's poller). Detect that mode once.
  bool get _anchorRead => env.mode == AccessMode.anchor && env.apiBase.isEmpty;

  // GENERIC MIRROR READ — in anchor mode EVERY read comes from the anchor mirror (the poller pushes the
  // brain's raw JSON under a key). This is how flutter/web have ZERO direct-backend calls: no _api reads.
  Future<Map<String, dynamic>> _anchorMirror(String key) async {
    final d = await _get(_anchor('/anchor/v1/mirror/${Uri.encodeComponent(key)}'), _anchorKey());
    return d is Map ? Map<String, dynamic>.from(d) : <String, dynamic>{};
  }

  // Read a scope's MESSAGE POOL from the anchor mirror (anchor mode). The pool is keyed by the EXACT scope
  // the app/brain/desktop use ('company' or 'project:<id>'), so we pass it through unchanged → same pool.
  Future<List<Map<String, dynamic>>> _anchorPool(String scope, {int offset = 0, int limit = 200}) async {
    final d = await _get(
        _anchor('/anchor/v1/pool/${Uri.encodeComponent(scope)}?offset=$offset&limit=$limit'), _anchorKey());
    return ((d is Map ? d['messages'] : null) as List? ?? const [])
        .map((m) => Map<String, dynamic>.from(m))
        .toList();
  }

  // ---------------- native brain (or anchor mirror in production) ----------------
  Future<Health> health() async {
    if (_anchorRead) {
      final d = Map<String, dynamic>.from(await _get(_anchor('/health'), _anchorKey()));
      return Health.fromJson({'ok': d['ok'] ?? true, 'engine': 'anchor', 'voice_enabled': false});
    }
    return Health.fromJson(Map<String, dynamic>.from(await _get(_api('/health'), _native())));
  }

  /// Freshness of the last anchor-mirror read: {updated:int, age_seconds:int, stale:bool}.
  /// Powers the "offline · last synced X ago" badge when the desktop is closed. Null in direct mode.
  Map<String, dynamic>? lastSync;

  // ---- Notifications (live sync feed for recurring/periodical work) ----
  // Direct mode: brain /notifications. Anchor mode: the poller mirrors it under key 'notifications'.
  Future<Map<String, dynamic>> notifications({bool unread = false}) async {
    try {
      final d = _anchorRead
          ? await _anchorMirror('notifications')
          : await _get(_api('/notifications?unread=$unread&limit=100'), _native());
      final m = d is Map ? Map<String, dynamic>.from(d) : <String, dynamic>{};
      final items = ((m['items'] ?? []) as List).map((e) => Map<String, dynamic>.from(e)).toList();
      final unreadN = m['unread'] ?? items.where((n) => n['read'] != true).length;
      return {'items': items, 'unread': unreadN};
    } catch (_) {
      return {'items': [], 'unread': 0};
    }
  }

  Future<void> markNotifRead({String id = '', bool all = false}) async {
    if (_anchorRead) {
      // anchor mode (web/mobile away from desktop): queue a command the local machine runs on the brain
      try { await commandViaAnchor('mark_notif', {'id': id, 'all': all}); } catch (_) {}
      return;
    }
    try { await _post(_api('/notifications/read'), _native(), {'id': id, 'all': all}); } catch (_) {}
  }

  // ---- AUDIT / Observer (the "silence page") — one bundle, works on every surface (mirror in production) ----
  Future<Map<String, dynamic>> auditData() async {
    if (_anchorRead) {
      final d = await _get(_anchor('/anchor/v1/mirror/audit'), _anchorKey());
      return d is Map ? Map<String, dynamic>.from(d) : {};
    }
    final d = await _get(_api('/audit/mirror'), _native());
    return d is Map ? Map<String, dynamic>.from(d) : {};
  }

  Future<Map<String, dynamic>> auditRun() async {
    if (_anchorRead) return {'ran': false, 'note': 'run the observer from the desktop app'};
    final d = await _post(_api('/audit/run?force=true'), _native());
    return d is Map ? Map<String, dynamic>.from(d) : {};
  }

  Future<void> auditConfig(bool enabled, int silence) async {
    if (_anchorRead) return;
    try { await _post(_api('/audit/config?enabled=$enabled&silence_minutes=$silence'), _native()); } catch (_) {}
  }

  Future<List<Project>> projects() async {
    // production: GET /anchor/v1/projects (mirror). dev: GET /projects (local brain).
    final d = _anchorRead
        ? await _get(_anchor('/anchor/v1/projects'), _anchorKey())
        : await _get(_api('/projects'), _native());
    if (_anchorRead && d is Map) {
      lastSync = {
        'updated': d['updated'] ?? 0,
        'age_seconds': d['age_seconds'] ?? -1,
        'stale': d['stale'] == true,
      };
    }
    return ((d['projects'] ?? []) as List).map((e) => Project.fromJson(Map<String, dynamic>.from(e))).toList();
  }

  /// POST /projects — create a new project. Returns the created project.
  Future<Project> createProject({
    required String name,
    String identifier = '',
    String description = '',
    String type = '',
    String cadence = 'once',
    bool autoApprove = true,
    List<Map<String, dynamic>>? members, // ALTERNATIVE-to-web: when the owner confirms the team on
    // mobile, we pass an explicit members list (same payload the web confirm screen sends). When null
    // (the default), the backend infers the team from the description — the original mobile behavior,
    // kept so nothing is discarded.
  }) async {
    final body = <String, dynamic>{
      'name': name,
      'identifier': identifier,
      'description': description,
      'type': type,
      'mode': 'build',
      'cadence': cadence,
      'autoApprove': autoApprove,
    };
    if (members != null) body['members'] = members;
    final d = await _post(_api('/projects'), _native(), body);
    return Project.fromJson(Map<String, dynamic>.from(d));
  }

  /// Split proposed member names into known catalogue roles vs unknown (need owner confirmation).
  /// Mirrors the web create-flow gate so an invented agent (e.g. "Vapi") is never silently created.
  Future<Map<String, dynamic>> validateAgents(List<String> names) async {
    final d = await _post(_api('/agents/validate'), _native(), {'names': names});
    return Map<String, dynamic>.from(d);
  }

  /// Capability-gap options for the CTO dialog: ranked existing agents + a smart new-agent suggestion.
  Future<Map<String, dynamic>> capability(String pid, String task) async {
    final d = await _post(_api('/projects/$pid/capability'), _native(), {'task': task});
    return Map<String, dynamic>.from(d);
  }

  /// Add (or re-allow) an agent on a project — used when the owner creates a custom agent from the
  /// capability dialog. force=true on the backend clears any prior removal.
  Future<void> addAgent(String pid, Map<String, dynamic> body) async {
    await _post(_api('/projects/$pid/agents'), _native(), body);
  }

  /// Remove a member from a project's team (persistent exclusion — the CTO won't re-add it unless the
  /// owner adds it back with force). Parity with the web "✕ remove from team" action.
  Future<void> removeAgent(String pid, String name) async =>
      http.delete(_api('/projects/$pid/agents/${Uri.encodeComponent(name)}'), headers: _native());

  Future<String> suggestIdentifier(String name) async {
    try {
      final d = await _get(_api('/projects/suggest-id?name=${Uri.encodeQueryComponent(name)}'), _native());
      return (d['identifier'] ?? '').toString();
    } catch (_) {
      return '';
    }
  }

  Future<Project> project(String pid) async =>
      Project.fromJson(Map<String, dynamic>.from(await _get(_api('/projects/$pid'), _native())));

  Future<List<Role>> roles() async {
    final d = _anchorRead ? await _anchorMirror('roles') : await _get(_api('/roles'), _native());
    return ((d['roles'] ?? []) as List).map((e) => Role.fromJson(Map<String, dynamic>.from(e))).toList();
  }

  Future<List<CompanyAgent>> companyAgents() async {
    final d = _anchorRead ? await _anchorMirror('company_agents') : await _get(_api('/company/agents'), _native());
    return ((d['agents'] ?? []) as List).map((e) => CompanyAgent.fromJson(Map<String, dynamic>.from(e))).toList();
  }

  /// Org-wide roster of ACTUAL agents (every project's agents + company agents), so a newly-created
  /// agent shows on the main page — not only inside its project. Anchor mode → mirror; desktop → brain.
  Future<List<Map<String, dynamic>>> allAgents() async {
    final d = _anchorRead ? await _anchorMirror('all_agents') : await _get(_api('/agents/all'), _native());
    return ((d['agents'] ?? []) as List).map((e) => Map<String, dynamic>.from(e)).toList();
  }

  Future<List<Connector>> connectors() async {
    final d = _anchorRead ? await _anchorMirror('connectors') : await _get(_api('/connectors'), _native());
    return ((d['connectors'] ?? []) as List).map((e) => Connector.fromJson(Map<String, dynamic>.from(e))).toList();
  }

  // Phase-6 GENERIC UI contract — type-driven cards + agent roster. Anchor mode reads the mirror the poller
  // pushes ('ui_projects' / 'ui_agents'); dev mode hits the brain's /ui/* directly. Same shape either way.
  Future<List<Map<String, dynamic>>> uiProjects() async {
    final d = _anchorRead ? await _anchorMirror('ui_projects') : await _get(_api('/ui/projects'), _native());
    return ((d['cards'] ?? []) as List).map((e) => Map<String, dynamic>.from(e)).toList();
  }

  Future<List<Map<String, dynamic>>> uiAgents() async {
    final d = _anchorRead ? await _anchorMirror('ui_agents') : await _get(_api('/ui/agents'), _native());
    return ((d['agents'] ?? []) as List).map((e) => Map<String, dynamic>.from(e)).toList();
  }

  /// Single project card. Anchor mode has no per-project mirror key, so derive it from the mirrored list;
  /// dev/direct mode hits /ui/project/{pid}. Same card shape either way.
  Future<Map<String, dynamic>?> uiProject(String pid) async {
    if (_anchorRead) {
      for (final c in await uiProjects()) {
        if (c['id']?.toString() == pid) return c;
      }
      return null;
    }
    final d = await _get(_api('/ui/project/$pid'), _native());
    return d.isEmpty || d['error'] != null ? null : Map<String, dynamic>.from(d);
  }

  /// Full type/feature catalog so a client can render controls/icons for types it has never seen (fully
  /// generic). Anchor mode → mirror 'ui_types'; dev → GET /ui/types.
  Future<Map<String, dynamic>> uiTypes() async {
    final d = _anchorRead ? await _anchorMirror('ui_types') : await _get(_api('/ui/types'), _native());
    return Map<String, dynamic>.from(d);
  }

  /// Generic connectors for the connection badges — array-mapped from odin_core_iso (not a hardcoded badge).
  Future<List<Map<String, dynamic>>> uiConnectors() async {
    final d = _anchorRead ? await _anchorMirror('ui_connectors') : await _get(_api('/ui/connectors'), _native());
    return ((d['connectors'] ?? []) as List).map((e) => Map<String, dynamic>.from(e)).toList();
  }

  /// HubSpot CRM account overview (connection + real counts). Anchor mode → the anchor mirror ('hubspot',
  /// pushed by the Mac poller); desktop/direct → GET /hubspot/overview. Never throws (badge degrades gracefully).
  Future<Map<String, dynamic>> hubspotOverview() async {
    try {
      final d = _anchorRead ? await _anchorMirror('hubspot') : await _get(_api('/hubspot/overview'), _native());
      return d is Map ? Map<String, dynamic>.from(d) : <String, dynamic>{'connected': false};
    } catch (_) {
      return <String, dynamic>{'connected': false};
    }
  }

  /// Standalone chats registry (server-side). Anchor mode → the anchor mirror; desktop/direct → the brain.
  Future<List<Map<String, dynamic>>> chats() async {
    final d = _anchorRead ? await _anchorMirror('chats') : await _get(_api('/chats'), _native());
    return ((d['chats'] ?? []) as List).map((e) => Map<String, dynamic>.from(e)).toList();
  }

  Future<void> createChatDirect(String title) async {
    await _post(_api('/chats'), _native(), {'title': title});
  }

  Future<void> deleteChatDirect(String scope) async {
    await http.delete(_api('/chats/${Uri.encodeComponent(scope)}'), headers: _native());
  }

  Future<void> renameChatDirect(String scope, String title) async {
    await _post(_api('/chats/rename?scope=${Uri.encodeComponent(scope)}'), _native(), {'title': title});
  }

  Future<List<Activity>> activity([String? pid]) async {
    final d = _anchorRead
        ? await _anchorMirror('activity')
        : await _get(_api('/activity${pid != null ? '?pid=$pid' : ''}'), _native());
    return ((d['active'] ?? []) as List).map((e) => Activity.fromJson(Map<String, dynamic>.from(e))).toList();
  }

  Future<List<String>> agents(String pid) async {
    final d = await _get(_api('/projects/$pid/agents'), _native());
    return ((d['agents'] ?? []) as List).map((e) => e is String ? e : (e as Map)['name'].toString()).toList();
  }

  Future<Map<String, dynamic>> plan(String pid) async =>
      Map<String, dynamic>.from(await _get(_api('/projects/$pid/plan'), _native()));

  Future<List<String>> rules(String pid) async {
    final d = await _get(_api('/projects/$pid/rules'), _native());
    return ((d['rules'] ?? []) as List).map((e) => e is String ? e : (e as Map)['rule'].toString()).toList();
  }

  /// Rules WITH their ids (so the UI can edit/delete a specific one). Additive — `rules()` is unchanged.
  Future<List<Map<String, dynamic>>> rulesDetailed(String pid) async {
    final d = await _get(_api('/projects/$pid/rules'), _native());
    return ((d['rules'] ?? []) as List)
        .map((e) => e is Map ? Map<String, dynamic>.from(e) : {'id': '', 'rule': e.toString()})
        .toList();
  }

  Future<Map<String, dynamic>> stats(String pid) async =>
      Map<String, dynamic>.from(await _get(_api('/projects/$pid/stats'), _native()));

  Future<List<Map<String, dynamic>>> schedules([String? pid]) async {
    final d = await _get(_api('/schedules${pid != null ? '?pid=$pid' : ''}'), _native());
    return ((d['tasks'] ?? []) as List).map((e) => Map<String, dynamic>.from(e)).toList();
  }

  Future<List<Operation>> operations([String? pid]) async {
    final d = await _get(_api('/operations${pid != null ? '?pid=$pid' : ''}'), _native());
    return ((d['operations'] ?? []) as List).map((e) => Operation.fromJson(Map<String, dynamic>.from(e))).toList();
  }

  Future<Map<String, dynamic>> connectTest() async {
    if (_anchorRead) return {}; // remote app: no direct-infra probe — everything is via the anchor
    return Map<String, dynamic>.from(await _get(_api('/infra/connect-test'), _native()));
  }

  // ---- archived ----
  Future<List<Project>> archivedProjects() async {
    final d = await _get(_api('/projects/archived'), _native());
    return ((d['projects'] ?? []) as List).map((e) => Project.fromJson(Map<String, dynamic>.from(e))).toList();
  }

  Future<void> archiveProject(String pid) async => _post(_api('/projects/$pid/archive'), _native(), {});
  Future<void> unarchiveProject(String pid) async => _post(_api('/projects/$pid/unarchive'), _native(), {});

  // ---- WEB PARITY (additive only): these hit the exact same backend endpoints the web app already
  // uses, so nothing on the server or web changes — Flutter just gains the same capabilities.
  Future<void> updateProject(String pid, Map<String, dynamic> b) async =>
      _post(_api('/projects/$pid/update'), _native(), b);
  Future<void> addMapping(String pid, Map<String, dynamic> b) async =>
      _post(_api('/projects/$pid/mappings'), _native(), b);
  Future<void> updateRule(String pid, String rid, String rule) async =>
      _post(_api('/projects/$pid/rules/$rid'), _native(), {'rule': rule});
  Future<void> removeRule(String pid, String rid) async =>
      http.delete(_api('/projects/$pid/rules/$rid'), headers: _native());
  Future<Map<String, dynamic>> suggestAgent(String pid, String description) async =>
      Map<String, dynamic>.from(
          await _post(_api('/projects/$pid/agents/suggest'), _native(), {'description': description}));
  Future<void> updateAgent(String pid, String name, Map<String, dynamic> b) async =>
      _post(_api('/projects/$pid/agents/${Uri.encodeComponent(name)}/update'), _native(), b);
  Future<Map<String, dynamic>> agent(String pid, String name) async =>
      Map<String, dynamic>.from(
          await _get(_api('/projects/$pid/agents/${Uri.encodeComponent(name)}'), _native()));
  Future<void> renameScopeChat(String scope, String cid, String title) async => _post(
      _api('/scope/chat/rename?scope=${Uri.encodeQueryComponent(scope)}&cid=$cid'), _native(), {'title': title});
  Future<String> scopeSummary(String scope) async {
    final d = await _get(_api('/scope/summary?scope=${Uri.encodeQueryComponent(scope)}'), _native());
    return (d is Map && d['summary'] != null) ? d['summary'].toString() : d.toString();
  }
  Future<void> updateSchedule(String tid, Map<String, dynamic> b) async =>
      _post(_api('/schedules/$tid/update'), _native(), b);
  Future<void> approveSchedule(String tid) async => _post(_api('/schedules/$tid/approve'), _native(), {});
  Future<void> skipSchedule(String tid) async => _post(_api('/schedules/$tid/skip'), _native(), {});
  Future<void> deleteProject(String pid) async {
    await http.delete(_api('/projects/$pid'), headers: _native());
  }

  // ---- company agents / connectors (add + remove) ----
  Future<void> addCompanyAgent(Map<String, dynamic> b) async => _post(_api('/company/agents'), _native(), b);
  Future<void> removeCompanyAgent(String name) async =>
      http.delete(_api('/company/agents/${Uri.encodeComponent(name)}'), headers: _native());
  Future<void> addConnector(Map<String, dynamic> b) async => _post(_api('/connectors'), _native(), b);
  Future<void> removeConnector(String cid) async => http.delete(_api('/connectors/$cid'), headers: _native());

  // ---- approvals ----
  Future<List<Map<String, dynamic>>> approvals([String? pid]) async {
    final d = await _get(_api('/approvals${pid != null ? '?pid=$pid' : ''}'), _native());
    return ((d['approvals'] ?? []) as List).map((e) => Map<String, dynamic>.from(e)).toList();
  }

  Future<int> approvalsCount([String? pid]) async {
    final d = await _get(_api('/approvals/count${pid != null ? '?pid=$pid' : ''}'), _native());
    return (d['pending'] is int) ? d['pending'] : int.tryParse('${d['pending']}') ?? 0;
  }

  Future<void> approveChange(String aid, {String note = ''}) async =>
      _post(_api('/approvals/$aid/approve'), _native(), {'note': note});
  Future<void> rejectChange(String aid, {String note = ''}) async =>
      _post(_api('/approvals/$aid/reject'), _native(), {'note': note});

  // ---- team run / deploy / sync ----
  Future<Map<String, dynamic>> startRun(String pid, String goal) async =>
      Map<String, dynamic>.from(await _post(_api('/projects/$pid/orchestrate/start'), _native(), {'goal': goal}));
  Future<Map<String, dynamic>> runStatus(String pid) async =>
      Map<String, dynamic>.from(await _get(_api('/projects/$pid/orchestrate/status'), _native()));
  Future<void> stopRun(String pid) async => _post(_api('/projects/$pid/orchestrate/stop'), _native(), {});
  Future<Map<String, dynamic>> syncRun(String pid) async =>
      Map<String, dynamic>.from(await _post(_api('/projects/$pid/sync/run'), _native(), {}));
  Future<Map<String, dynamic>> deployRun(String pid) async =>
      Map<String, dynamic>.from(await _post(_api('/projects/$pid/deploy/run'), _native(), {}));
  Future<Map<String, dynamic>> requestDeploy(String pid) async =>
      Map<String, dynamic>.from(await _post(_api('/projects/$pid/deploy/request'), _native(), {}));

  // ---- operations (stop / provide answers) ----
  Future<void> stopOperation(String oid) async => _post(_api('/operations/$oid/stop'), _native(), {});
  Future<void> provideOperation(String oid, Map<String, dynamic> answers) async =>
      _post(_api('/operations/$oid/provide'), _native(), {'answers': answers});

  // ---- conversational intake ----
  Future<Map<String, dynamic>> intake(List<Map<String, String>> history) async =>
      Map<String, dynamic>.from(await _post(_api('/projects/intake'), _native(), {'history': history}));

  // ---- monitor feed ----
  Future<List<Map<String, dynamic>>> scopeChildren(String scope) async {
    final d = await _get(_api('/scope/children?scope=${Uri.encodeComponent(scope)}'), _native());
    return ((d['children'] ?? []) as List).map((e) => Map<String, dynamic>.from(e)).toList();
  }

  /// Company / main chat → POST /chat {text,lang} -> {reply}. Native, synchronous.
  Future<String> companyChat(String text, {String lang = 'en'}) async {
    final d = await _post(_api('/chat'), _native(), {'text': text, 'lang': lang});
    return (d['reply'] ?? d['answer'] ?? '').toString();
  }

  // ---------------- shared scope chat (the SAME pool the desktop + agents use) ----------------
  /// Returns an existing chat id for the scope, or creates one. scope='company' for the
  /// main chat; scope=<pid> for a project (the team run writes into this same pool).
  Future<String> ensureScopeChat(String scope) async {
    if (_anchorRead) return 'anchor'; // anchor mode: no backend session; the pool is read from the anchor mirror
    final d = await _get(_api('/scope/chats?scope=${Uri.encodeComponent(scope)}'), _native());
    final chats = (d['chats'] ?? []) as List;
    if (chats.isNotEmpty) return (chats.first as Map)['id'].toString();
    final created = await _post(_api('/scope/chats?scope=${Uri.encodeComponent(scope)}'), _native(), {'title': 'App chat'});
    return (created['id'] ?? '').toString();
  }

  /// Persisted messages for a scope chat: [{role, content}] (role: user|assistant).
  Future<List<Map<String, String>>> scopeMessages(String scope, String cid) async {
    if (_anchorRead) {
      final pool = await _anchorPoolDelta(scope);
      return pool
          .map((m) => {'role': (m['role'] ?? 'assistant').toString(), 'content': (m['content'] ?? '').toString()})
          .toList();
    }
    final d = await _get(_api('/scope/chat?scope=${Uri.encodeComponent(scope)}&cid=$cid'), _native());
    final msgs = (d['messages'] ?? []) as List;
    return msgs
        .map((m) => {'role': (m['role'] ?? 'assistant').toString(), 'content': (m['content'] ?? '').toString()})
        .toList();
  }

  /// FULL messages for the WhatsApp-style group view: id, role, sender, kind, content,
  /// attachment {id,name,url,kind,size,transcript?}, reply_to, ts.
  Future<List<Map<String, dynamic>>> scopeMessagesRich(String scope, String cid) async {
    if (_anchorRead) return _anchorPoolDelta(scope);
    final d = await _get(_api('/scope/chat?scope=${Uri.encodeComponent(scope)}&cid=$cid'), _native());
    return ((d['messages'] ?? []) as List).map((m) => Map<String, dynamic>.from(m)).toList();
  }

  /// The WHOLE pool for a scope — every message across all its chats merged in time order
  /// (each carries its own cid). The single-source-of-truth view for Conversations.
  Future<List<Map<String, dynamic>>> scopeAllMessages(String scope) async {
    if (_anchorRead) return _anchorPoolDelta(scope);
    final d = await _get(_api('/scope/messages?scope=${Uri.encodeComponent(scope)}'), _native());
    return ((d['messages'] ?? []) as List).map((m) => Map<String, dynamic>.from(m)).toList();
  }

  Future<void> deleteScopeMessage(String scope, String cid, String mid) async {
    if (_anchorRead) {
      // production: route the delete through the anchor command queue so it propagates to every device.
      await commandViaAnchor('delete_message', {'scope': scope, 'cid': cid, 'mid': mid});
      return;
    }
    await http.delete(_api('/scope/message?scope=${Uri.encodeComponent(scope)}&cid=$cid&mid=$mid'), headers: _native());
  }

  /// Upload an attachment (multipart) → descriptor {id,name,url,kind,size,transcript?}.
  Future<Map<String, dynamic>> uploadScopeFile(String scope, List<int> bytes, String filename) async {
    final req = http.MultipartRequest('POST', _api('/scope/upload?scope=${Uri.encodeComponent(scope)}'));
    if (env.token.isNotEmpty) req.headers['X-Odin-Token'] = env.token;
    req.files.add(http.MultipartFile.fromBytes('file', bytes, filename: filename));
    req.fields['scope'] = scope;
    final streamed = await req.send();
    final body = await streamed.stream.bytesToString();
    if (streamed.statusCode < 200 || streamed.statusCode >= 300) {
      throw ApiException(streamed.statusCode, body);
    }
    return Map<String, dynamic>.from(jsonDecode(body));
  }

  /// Post a message (no AI turn) into the shared pool — media, replies, group posts.
  Future<Map<String, dynamic>> postScopeMessage(String scope, String cid, Map<String, dynamic> body) async {
    if (_anchorRead) {
      // production: web/mobile cannot touch the backend directly — route the rich post (reply / media /
      // voice / forward) through the anchor command queue so it reaches the brain pool and mirrors back to
      // every device. Rename 'kind' → 'msg_kind' so it doesn't collide with the command's own 'kind'.
      final args = <String, dynamic>{'scope': scope, 'cid': cid};
      body.forEach((k, v) {
        if (v == null) return;
        args[k == 'kind' ? 'msg_kind' : k] = v;
      });
      await commandViaAnchor('post_message', args);
      return <String, dynamic>{};
    }
    final d = await _post(_api('/scope/message?scope=${Uri.encodeComponent(scope)}&cid=$cid'), _native(), body);
    return Map<String, dynamic>.from(d);
  }

  /// Absolute URL for a stored attachment (Image.network / audio source). In anchor mode media is served
  /// THROUGH the anchor (never the backend) — files posted via the anchor already come back as absolute
  /// anchor URLs, so this only ever prefixes in direct (desktop) mode where apiBase is set.
  String fileUrl(String path) => path.startsWith('http') ? path : '${env.apiBase}$path';

  /// Live token stream for a scope turn (SSE). DIRECT mode (desktop) only — in anchor mode web/mobile must
  /// go through the anchor queue (chatViaAnchor), so we HARD-REFUSE a direct SSE to the backend here too.
  Stream<String> streamScope(String scope, String text, String cid, {String lang = 'en'}) {
    if (_anchorRead) {
      throw ApiException(0, 'streaming is not reachable from the app — chat must go through the anchor');
    }
    final url = '${env.apiBase}/scope/stream?scope=${Uri.encodeComponent(scope)}'
        '&text=${Uri.encodeComponent(text)}&lang=$lang&cid=$cid';
    return sseTokens(url, _native(), tokenQuery: env.token);
  }

  /// Send a message into the shared scope pool. In ANCHOR mode this goes THROUGH THE ANCHOR queue (see
  /// chatViaAnchor below); in direct mode (desktop only) it uses the local streaming endpoint.
  Future<void> scopeSend(String scope, String text, String cid, {String lang = 'en'}) async {
    if (_anchorRead) { await chatViaAnchor(scope, text); return; }
    final url = _api('/scope/stream?scope=${Uri.encodeComponent(scope)}'
        '&text=${Uri.encodeComponent(text)}&lang=$lang&cid=$cid');
    final h = Map<String, String>.from(_native())..['Accept'] = 'text/event-stream';
    final r = await http.get(url, headers: h);
    if (r.statusCode < 200 || r.statusCode >= 300) {
      throw ApiException(r.statusCode, r.body.isEmpty ? (r.reasonPhrase ?? '') : r.body);
    }
  }

  // ---------------- auth ----------------
  Future<Map<String, dynamic>> authConfig() async =>
      Map<String, dynamic>.from(await _get(_api('/auth/config'), _native()));

  Future<Map<String, dynamic>> setAuthConfig(Map<String, dynamic> flags) async =>
      Map<String, dynamic>.from(await _post(_api('/auth/config'), _native(), flags));

  Future<Map<String, dynamic>> login(String email, String password) async =>
      Map<String, dynamic>.from(await _post(_api('/auth/login'), _native(), {'email': email, 'password': password}));

  Future<Map<String, dynamic>> twofa(String email, String code) async =>
      Map<String, dynamic>.from(await _post(_api('/auth/2fa'), _native(), {'email': email, 'code': code}));

  Future<Map<String, dynamic>> me(String token) async {
    final h = Map<String, String>.from(_native())..['X-Auth-Token'] = token;
    return Map<String, dynamic>.from(await _get(_api('/auth/me'), h));
  }

  Future<void> logout(String token) async => _post(_api('/auth/logout'), _native(), {'token': token});

  Future<Map<String, dynamic>> changePassword(String email, String oldPw, String newPw) async =>
      Map<String, dynamic>.from(await _post(_api('/auth/change-password'), _native(), {'email': email, 'old': oldPw, 'new': newPw}));

  Future<Map<String, dynamic>> forgot(String email) async =>
      Map<String, dynamic>.from(await _post(_api('/auth/forgot'), _native(), {'email': email}));

  // ---------------- /api/v1 (synchronous ask) ----------------
  Future<String> askDirect(String identifier, String prompt, {String lang = 'en'}) async {
    final d = await _post(_api('/api/v1/p/$identifier/ask'), _apiKey(), {'prompt': prompt, 'lang': lang});
    return (d['answer'] ?? '').toString();
  }

  // ---------------- anchor ----------------
  Future<Map<String, int>> anchorCounts() async {
    final d = await _get(_anchor('/anchor/v1/admin/counts'), _anchorKey());
    final c = Map<String, dynamic>.from(d['counts'] ?? {});
    return c.map((k, v) => MapEntry(k, v is int ? v : int.tryParse('$v') ?? 0));
  }

  Future<List<AnchorRequest>> anchorRequests({String status = ''}) async {
    final p = status.isEmpty ? '/anchor/v1/admin/requests' : '/anchor/v1/admin/requests?status=$status';
    final d = await _get(_anchor(p), _anchorKey());
    return ((d['requests'] ?? []) as List).map((e) => AnchorRequest.fromJson(Map<String, dynamic>.from(e))).toList();
  }

  Future<Map<String, dynamic>> anchorConfig() async =>
      Map<String, dynamic>.from(await _get(_anchor('/anchor/v1/admin/config'), _anchorKey()));

  Future<Map<String, dynamic>> sendRequest({
    required String project,
    required String prompt,
    String webhookUrl = '',
    String sender = 'odin_app',
  }) async =>
      Map<String, dynamic>.from(await _post(_anchor('/anchor/v1/requests'), _anchorKey(),
          {'project': project, 'prompt': prompt, 'webhook_url': webhookUrl, 'sender': sender}));

  Future<AnchorRequest> requestStatus(String id) async =>
      AnchorRequest.fromJson(Map<String, dynamic>.from(await _get(_anchor('/anchor/v1/requests/$id'), _anchorKey())));

  /// CHAT via the anchor — a scope message becomes an async ask (engine runs on the Mac; result returns).
  /// Returns the assistant reply text. Works for any scope (company or a project) — the anchor accepts it
  /// because sender='chat'. This is how web/mobile chat WITHOUT ever touching the backend directly.
  Future<String> chatViaAnchor(String scope, String text,
      {void Function(String status)? onStatus,
      Duration interval = const Duration(seconds: 2),
      Duration timeout = const Duration(minutes: 8)}) async {
    final created = Map<String, dynamic>.from(await _post(_anchor('/anchor/v1/requests'), _anchorKey(),
        {'project': scope, 'prompt': text, 'sender': 'chat'}));
    final id = (created['request_id'] ?? '').toString();
    if (id.isEmpty) throw ApiException(0, 'anchor returned no request_id: $created');
    onStatus?.call((created['status'] ?? 'queued').toString());
    final deadline = DateTime.now().add(timeout);
    String last = '';
    while (DateTime.now().isBefore(deadline)) {
      await Future.delayed(interval);
      final r = await requestStatus(id);
      if (r.status != last) { last = r.status; onStatus?.call(r.status); }
      if (r.isTerminal) {
        final res = r.result;
        return res is String ? res : (res?.toString() ?? '(no reply)');
      }
    }
    throw ApiException(0, 'timed out waiting for chat $id');
  }

  /// COMMAND through the anchor — a write action (create_project, clear_scope, …) becomes a queued command
  /// the local machine executes on the backend, then syncs. Web/mobile NEVER touch the backend directly.
  Future<void> commandViaAnchor(String kind, Map<String, dynamic> args,
      {Duration timeout = const Duration(minutes: 3)}) async {
    final created = Map<String, dynamic>.from(await _post(_anchor('/anchor/v1/requests'), _anchorKey(),
        {'project': '__command__', 'sender': 'command', 'prompt': kind,
         'payload': {'kind': kind, ...args}}));
    final id = (created['request_id'] ?? '').toString();
    if (id.isEmpty) throw ApiException(0, 'anchor returned no request_id: $created');
    final deadline = DateTime.now().add(timeout);
    while (DateTime.now().isBefore(deadline)) {
      await Future.delayed(const Duration(seconds: 2));
      try {
        final r = await requestStatus(id);
        if (r.isTerminal) return;
      } catch (_) {}
    }
  }

  /// ▶ RUN NOW — fire a project's recurring/scheduled task on demand. Anchor mode (web/mobile) queues a
  /// command the local machine runs; desktop/direct posts to the brain. Never touches the backend directly.
  Future<String> runNow(String pid, {String prompt = '', String cid = ''}) async {
    if (_anchorRead) {
      await commandViaAnchor('run_now', {'pid': pid, 'prompt': prompt, 'cid': cid});
      return 'Running now…';
    }
    final d = await _post(_api('/projects/${Uri.encodeComponent(pid)}/run-now'), _native(), {'prompt': prompt, 'cid': cid});
    return (d is Map && d['message'] != null) ? d['message'].toString() : 'Running now…';
  }

  /// 🎙 MOBILE live-meeting: the phone transcribed on-device; send the chunk TEXTS to build the report.
  /// Anchor mode (mobile) queues a command the local machine runs on the brain (the report then posts into
  /// the project chat and syncs back); direct mode posts and returns the markdown to show inline.
  Future<Map<String, dynamic>> meetingReport(String pid, List<String> texts, {String lang = ''}) async {
    if (_anchorRead) {
      await commandViaAnchor('meeting_report', {'pid': pid, 'texts': texts, 'lang': lang});
      // the poller builds the report and posts it into the project chat; poll the mirror so we can
      // show it INLINE in the dialog too (parity with web/desktop), not only in the chat.
      String md = '';
      for (int i = 0; i < 8 && md.isEmpty; i++) {
        await Future.delayed(const Duration(seconds: 2));
        try {
          final msgs = await scopeAllMessages('project:$pid');
          for (final m in msgs.reversed) {
            final sender = (m['sender'] ?? '').toString();
            final content = (m['content'] ?? '').toString();
            if (sender.contains('Live Meeting') && content.trim().isNotEmpty) { md = content; break; }
          }
        } catch (_) {}
      }
      return {'viaChat': true, 'markdown': md, 'lang': lang, 'chunks': texts.length};
    }
    final d = await _post(_api('/meeting/finish_text?pid=${Uri.encodeComponent(pid)}'), _native(),
        {'texts': texts, 'lang': lang});
    return (d is Map) ? Map<String, dynamic>.from(d) : {'chunks': texts.length};
  }

  /// Async ask via the anchor (anchor mode / Phase 3): submit then poll to terminal.
  Future<AnchorRequest> askViaAnchor(
    String project,
    String prompt, {
    void Function(String status)? onStatus,
    Duration interval = const Duration(seconds: 3),
    Duration timeout = const Duration(minutes: 8),
  }) async {
    final created = await sendRequest(project: project, prompt: prompt);
    final id = (created['request_id'] ?? '').toString();
    if (id.isEmpty) throw ApiException(0, 'anchor returned no request_id: $created');
    onStatus?.call((created['status'] ?? 'queued').toString());
    final deadline = DateTime.now().add(timeout);
    String last = '';
    while (DateTime.now().isBefore(deadline)) {
      await Future.delayed(interval);
      final r = await requestStatus(id);
      if (r.status != last) {
        last = r.status;
        onStatus?.call(r.status);
      }
      if (r.isTerminal) return r;
    }
    throw ApiException(0, 'timed out waiting for request $id');
  }
}
