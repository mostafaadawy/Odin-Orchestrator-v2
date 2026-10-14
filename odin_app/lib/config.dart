import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

/// How the app reaches the backend.
///  - direct: the app is on the same network as the brain. Project list + chat use
///    /api/v1 synchronously; the anchor status page uses /anchor/v1 directly.
///  - anchor: the app is remote (Phase 3). It can ONLY reach the deployed anchor, so
///    "chat" becomes an async anchor request (POST /anchor/v1/requests) that the local
///    machine picks up, processes, and returns via webhook/poll. Same contract, just
///    a different base URL + port. This is why we keep the two URLs separate.
enum AccessMode { direct, anchor }

/// A named environment. Phase 2 (Local) and Phase 3 (Deployed anchor) are just two
/// profiles — the ONLY thing that changes going to Phase 3 is the anchor host/port
/// and the mode. Nothing in the screens changes.
class EnvProfile {
  String name;
  String apiBaseUrl; // the native brain: /health, /projects, /roles, /activity, /api/v1, …
  String anchorBaseUrl; // serves /anchor/v1 (queue + status). Local now, VM ip:port later.
  AccessMode mode;
  String token; // X-Odin-Token for the native brain endpoints (usually empty on localhost)
  String odinApiKey; // X-API-Key for /api/v1
  String anchorApiKey; // X-API-Key for /anchor/v1

  EnvProfile({
    required this.name,
    required this.apiBaseUrl,
    required this.anchorBaseUrl,
    this.mode = AccessMode.direct,
    this.token = '',
    this.odinApiKey = '',
    this.anchorApiKey = '',
  });

  String get apiBase => apiBaseUrl.trim().replaceAll(RegExp(r'/+$'), '');
  String get anchorBase => anchorBaseUrl.trim().replaceAll(RegExp(r'/+$'), '');

  Map<String, dynamic> toJson() => {
        'name': name,
        'apiBaseUrl': apiBaseUrl,
        'anchorBaseUrl': anchorBaseUrl,
        'mode': mode.name,
        'token': token,
        'odinApiKey': odinApiKey,
        'anchorApiKey': anchorApiKey,
      };

  factory EnvProfile.fromJson(Map<String, dynamic> j) => EnvProfile(
        name: (j['name'] ?? 'Profile').toString(),
        apiBaseUrl: (j['apiBaseUrl'] ?? 'http://localhost:8000').toString(),
        anchorBaseUrl: (j['anchorBaseUrl'] ?? 'http://localhost:8000').toString(),
        mode: (j['mode'] == 'anchor') ? AccessMode.anchor : AccessMode.direct,
        token: (j['token'] ?? '').toString(),
        odinApiKey: (j['odinApiKey'] ?? '').toString(),
        anchorApiKey: (j['anchorApiKey'] ?? '').toString(),
      );

  EnvProfile clone() => EnvProfile.fromJson(toJson());

  /// Sensible starting profiles. The user edits IP/port/keys in Settings.
  static List<EnvProfile> defaults() => [
        EnvProfile(
          name: 'Local (Phase 2)',
          apiBaseUrl: 'http://localhost:8000',
          anchorBaseUrl: 'http://localhost:8000',
          mode: AccessMode.direct,
        ),
        // PHASE 2 — TOTALLY MIMICS PHASE 3. Web/mobile go THROUGH the local anchor, never to the backend.
        // apiBase is EMPTY on purpose: there is NO direct path to the brain, so if the anchor is down the
        // app shows nothing (proof the data really flows through the anchor). This profile is byte-for-byte
        // identical to "Deployed (Phase 3)" EXCEPT the anchor URL (localhost now, VM domain later).
        EnvProfile(
          name: 'Anchor (local — Phase 2)',
          apiBaseUrl: '', // NO backend shortcut — everything goes through the anchor (mimics remote client)
          anchorBaseUrl: 'http://localhost:9100', // the REAL anchor, running locally (same code as the VM)
          mode: AccessMode.anchor,
          anchorApiKey: const String.fromEnvironment('ODIN_ANCHOR_KEY'), // F-14: --dart-define=ODIN_ANCHOR_KEY=… // same key as Phase 3 (auth parity)
        ),
        EnvProfile(
          name: 'Deployed (Phase 3)',
          apiBaseUrl: '', // remote/mobile CANNOT reach the local brain — everything goes through the anchor
          anchorBaseUrl: 'https://anchor.odinmarkets.com/odin-anchor', // reverse proxy on 443 (no open port)
          mode: AccessMode.anchor,
          anchorApiKey: const String.fromEnvironment('ODIN_ANCHOR_KEY'), // F-14: --dart-define=ODIN_ANCHOR_KEY=… // auth for the anchor mirror reads
        ),
      ];
}

/// Persists the list of profiles + which one is selected.
class AppConfig {
  List<EnvProfile> profiles;
  int selected;

  AppConfig({required this.profiles, this.selected = 0});

  EnvProfile get active =>
      profiles.isEmpty ? EnvProfile.defaults().first : profiles[selected.clamp(0, profiles.length - 1)];

  // v3: the Phase-2 profile is now PURE anchor (apiBase empty) so the app cannot silently read the backend.
  // Bumping the key discards any stale saved profile (e.g. the old "Anchor sim" with apiBase=localhost:8000
  // that let the app cheat) and loads the corrected defaults — the app then truly depends on the anchor.
  static const _kProfiles = 'odin.profiles.v3';
  static const _kSelected = 'odin.selected.v3';

  static Future<AppConfig> load() async {
    final p = await SharedPreferences.getInstance();
    final raw = p.getString(_kProfiles);
    List<EnvProfile> profiles;
    if (raw == null) {
      profiles = EnvProfile.defaults();
    } else {
      final list = (jsonDecode(raw) as List)
          .map((e) => EnvProfile.fromJson(Map<String, dynamic>.from(e)))
          .toList();
      profiles = list.isEmpty ? EnvProfile.defaults() : list;
    }
    return AppConfig(profiles: profiles, selected: p.getInt(_kSelected) ?? 0);
  }

  Future<void> save() async {
    final p = await SharedPreferences.getInstance();
    await p.setString(_kProfiles, jsonEncode(profiles.map((e) => e.toJson()).toList()));
    await p.setInt(_kSelected, selected);
  }
}
