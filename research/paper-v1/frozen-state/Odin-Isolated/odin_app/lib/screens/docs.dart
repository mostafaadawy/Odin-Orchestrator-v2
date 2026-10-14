import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../config.dart';
import '../state/app_state.dart';
import '../theme.dart';
import '../widgets.dart';
import 'shell.dart' show showPortsSheet;

/// HELP & TESTING GUIDE — the single searchable place that explains environments, production support,
/// how to switch, the current status, what each phase shell does, how to test, and what to expect on
/// the simulator vs a real phone. Open it from the sidebar (📄 Docs) and use the search box.
class DocsScreen extends StatefulWidget {
  const DocsScreen({super.key});
  @override
  State<DocsScreen> createState() => _DocsScreenState();
}

class _DocsScreenState extends State<DocsScreen> {
  String _q = '';

  @override
  Widget build(BuildContext context) {
    final s = context.watch<AppState>();
    final env = s.env;
    final isProd = env.mode == AccessMode.anchor;

    final cards = <_Doc>[
      _Doc('🌍', '1 · Supported environments', [
        'Development — everything runs LOCALLY on your Mac (localhost). Default.',
        'Production — the Anchor and the Web run ONLINE via anchor.odinmarkets.com. Your desktop brain always stays local and is reached only THROUGH the anchor.',
        'Both are the SAME app and features — only the URLs/ports differ.',
      ]),
      _Doc('🛰️', '2 · Production support (what is online)', [
        'Anchor (online): https://anchor.odinmarkets.com/odin-anchor — via the nginx reverse proxy on 443 (no open port), the 3rd-party entry + queue.',
        'Web (online): https://anchor.odinmarkets.com/odin-web — the deployed Flutter web, open from any browser anywhere.',
        'Desktop brain: stays LOCAL on your Mac. Remote web/mobile reach it only via the anchor (async: request → fast ack → local desktop → webhook/poll result).',
        'Only 80/443/22 are open (22 locked to your IP). The apps bind to localhost on the VM; nothing touches your other Azure sites.',
      ]),
      _Doc('🔀', '3 · How to switch Development ↔ Production', [
        'Mobile/Web: tap the 🗺 (network) icon in the top bar, or the environment chip → choose "Use Development" or "Use Production".',
        'Desktop: top bar → "🗺 Ports & Env" button → pick the environment → Apply & reload.',
        'Switching is the ONLY change needed to go live — no code edits.',
      ]),
      _Doc(isProd ? '🟢' : '🔵', '4 · Current active environment (LIVE)', [
        'Active profile: ${env.name}',
        'Mode: ${env.mode.name}  (${isProd ? "PRODUCTION — talking to the online anchor" : "DEVELOPMENT — everything local"})',
        'Anchor URL in use: ${env.anchorBase.isEmpty ? "(none)" : env.anchorBase}',
        'API base in use: ${env.apiBase.isEmpty ? "(remote — via anchor only)" : env.apiBase}',
        'Connection: ${s.health?.ok == true ? "connected ✓" : "offline / not reachable"}',
      ]),
      _Doc('🖥️', '5 · The phases at a glance + Phase 2 shell (LOCAL · DEVELOPMENT)', [
        'Phase 1 = the original local proof (single machine, app talks to the local backend directly). Phase 2 = the same, PLUS the anchor running locally so web/mobile go through it (mimics production). Phase 3 = anchor + web ONLINE.',
        'Config per phase: Phase 2 uses DEVELOPMENT config (local); Phase 3 uses PRODUCTION config (online domain). Phase 2 is unchanged and always stays on development.',
        'Command: ./phase2_up.sh  — asks "with the anchor?" and brings up locally: brain :8000, anchor :9100, request page :9104/anchor_sim.html, webhook :9300, Flutter web :8080, desktop, iOS simulator.',
        'Use this to test the whole flow end-to-end on your Mac before anything goes online.',
      ]),
      _Doc('☁️', '6 · What the Phase 3 shell provides (ONLINE / PRODUCTION)', [
        'Command: ./phase3_up.sh  — a standalone script (works without the loop/agent).',
        'DEPLOYS FROM COPIES: keeps deploy_anchor/ + deploy_web/ copies of the successful folders and deploys by OVERWRITING the VM folders from those copies. Your original folders are never edited.',
        'CHANGE-DETECTION: compares originals vs copies. First run deploys even with no diff; later runs SKIP when nothing changed, and ASK you before deploying when a change is found.',
        'LEVERAGES existing infra — never recreates the reverse proxy, the SSL (valid Let\'s Encrypt, never self-signed), the domain, or the Postgres DB (created only if missing, never recreated).',
        'Postgres: the anchor runs on Postgres via its own isolated venv; connectivity is verified through the REAL app path (a submitted request lands as a row in the DB).',
        'Auto-selects Production and opens ONLY the main players: request page, online anchor, online web, desktop, mobile simulator. Brain + poller run in the background (no windows).',
      ]),
      _Doc('🔁', '6b · The loop (anchor_loop.sh) + resilience', [
        'anchor_loop.sh is the control loop: you type phase2 / phase3 / stop / done, and it also gives the agent (Claude / Cowork) a CLI bridge to drive + analyze runs with you, on your Mac terminal.',
        'The SAME tools work locally in Phase 2 with the local env (localhost) — identical behavior, just different URLs.',
        'This guide is synchronized across desktop, mobile, and web — you see the same helper everywhere.',
      ]),
      _Doc('🛡️', '6c · Lessons baked into phase3 (won\'t recur)', [
        'WHOLE-FOLDER overwrite from the copy, so every anchor dependency ships (no missing-module crash).',
        'The anchor\'s isolated venv (with psycopg2) is PRESERVED across deploys; the service runs on the venv python.',
        'The web is built with --base-href /odin-web/ so its assets load under the subpath (no stuck loading).',
        'Each privileged step is its own SSH call so sudo authenticates; reset-failed clears any start-limit before start.',
        'DB verified through the app (request → row), never just "service exists". Valid SSL/domain/proxy reused; other Azure sites untouched.',
      ]),
      _Doc('🧪', '7 · How to use Phase 3 for testing', [
        'After I confirm readiness, type "phase3" in the loop. The shell opens everything for you.',
        'Your only job: send a message from the app/simulator → confirm the 3rd-party page receives it → send a reply from the 3rd party → confirm the simulator receives it, all over the REAL IP.',
        'Watch the CD-flow on :9104 (Production) and the per-project webhook response blocks.',
        'If a request seems slow, that is expected — production is asynchronous (queued through the anchor).',
      ]),
      _Doc('📱', '8 · Simulator vs real-device testing', [
        'Simulator FIRST: I can read the live mobile logs while it runs, so we fix any issue against real logs before your phone.',
        'On the simulator you should see: the Odin icon + name, the login screen, then (after first login) the Face ID unlock on return.',
        'When set to Production, the app talks to https://anchor.odinmarkets.com/odin-anchor — confirm the top-bar shows PRODUCTION so you never test against the wrong environment.',
        'Real phone comes AFTER the simulator passes — then I depend on your description (no direct logs), so we lock it down on the simulator first.',
      ]),
      _Doc('⚠️', 'Avoid the #1 mistake', [
        'Before judging any result, check the top-bar environment badge. If it says Development you are hitting localhost; if it says Production you are hitting the online anchor. Testing prod behaviour while on dev (or vice-versa) gives misleading results.',
      ]),
      _Doc('🔐', '9 · Login & sessions (web + mobile + manage)', [
        'ONE login everywhere: your saved email + saved password + a random CODE shown on the DESKTOP. Web, mobile and the anchor Manage page all sign in the same way.',
        'The code is DIFFERENT and RANDOM for each target and each attempt — tap "Get code" in the app, then read the code from the desktop\'s blinking "Connecting with Anchor" badge (it shows which of web / mobile / manage needs to connect).',
        'The session lasts 7 DAYS, then it auto-logs-out and asks you to sign in again. No anonymous access: without a valid login the anchor returns 401 for web/mobile reads and command submits.',
        'LOGOUT is a clear button in the top bar — visible in normal mode AND chat mode, on both web and mobile. Log out any time to end the session early.',
        'Mobile Face ID is OPTIONAL: if the device supports it, it can unlock; if not, the email+password+code login always works (never blocked).',
        'Only the DESKTOP can approve a login (it shows the code) — so only you, at your machine, can let a web/mobile client in.',
      ]),
      _Doc('📲', '10 · Install the app on a real iPhone (no App Store)', [
        '1) Connect the iPhone by cable, unlock it, tap Trust. Open Xcode once so it "Prepares" the device (first time can take minutes) — then flutter can see it.',
        '2) Open odin_app/ios/Runner.xcworkspace (the WORKSPACE, not the .xcodeproj). Runner target → Signing & Capabilities → Automatically manage signing → Team → Add your Apple ID (free) and pick your Personal Team. Bundle id is a neutral personal one (com.mostafaadawy.mobileapp).',
        '3) Install a RELEASE build (debug apps cannot launch from the home screen on iOS 14+): flutter run --release -d <iphone-id> --dart-define=ODIN_FORCE_ENV=production --dart-define=ODIN_ANCHOR=https://anchor.odinmarkets.com/odin-anchor',
        '4) On the phone: Settings → General → VPN & Device Management → your Apple ID → Trust. Then open the app from the home screen.',
        'Free Apple ID = the app runs for 7 days, then re-run step 3 to renew. It talks only to the online anchor, so it works over any internet from a separate device.',
      ]),
    ];

    final q = _q.trim().toLowerCase();
    final shown = q.isEmpty
        ? cards
        : cards.where((c) => (c.title + c.lines.join(' ')).toLowerCase().contains(q)).toList();

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const SectionTitle('Help & Testing Guide'),
        const SizedBox(height: 4),
        const Text('Everything about environments, switching, the phase shells, and how to test. Searchable.',
            style: TextStyle(fontSize: 12, color: Odin.txtFaint)),
        const SizedBox(height: 12),
        // LIVE status banner — always shows which environment you are in right now.
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          decoration: BoxDecoration(
            color: (isProd ? Odin.ok : Odin.brand).withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: (isProd ? Odin.ok : Odin.brand).withValues(alpha: 0.5)),
          ),
          child: Row(
            children: [
              Icon(isProd ? Icons.cloud_done : Icons.developer_mode,
                  size: 18, color: isProd ? Odin.ok : Odin.brand),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Active now: ${isProd ? "PRODUCTION (online anchor)" : "DEVELOPMENT (local)"} · ${env.name}',
                  style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
                ),
              ),
              TextButton(onPressed: () => showPortsSheet(context, s), child: const Text('Switch')),
            ],
          ),
        ),
        const SizedBox(height: 12),
        TextField(
          onChanged: (v) => setState(() => _q = v),
          decoration: const InputDecoration(
            isDense: true,
            prefixIcon: Icon(Icons.search, size: 18),
            hintText: 'Search the guide (e.g. "switch", "phase 3", "simulator", "face id")…',
            border: OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 14),
        ...shown.map((c) => Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: _DocCard(icon: c.icon, title: c.title, bullets: c.lines),
            )),
        if (shown.isEmpty)
          const Padding(
            padding: EdgeInsets.all(20),
            child: Text('No section matches that search.', style: TextStyle(color: Odin.txtFaint)),
          ),
      ],
    );
  }
}

class _Doc {
  final String icon;
  final String title;
  final List<String> lines;
  _Doc(this.icon, this.title, this.lines);
}

class _DocCard extends StatelessWidget {
  final String icon;
  final String title;
  final List<String> bullets;
  const _DocCard({required this.icon, required this.title, required this.bullets});
  @override
  Widget build(BuildContext context) {
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(icon, style: const TextStyle(fontSize: 18)),
              const SizedBox(width: 8),
              Expanded(child: Text(title, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700))),
            ],
          ),
          const SizedBox(height: 8),
          ...bullets.map((b) => Padding(
                padding: const EdgeInsets.symmetric(vertical: 3),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('• ', style: TextStyle(color: Odin.brand2)),
                    Expanded(
                      child: SelectableText(b,
                          style: const TextStyle(fontSize: 12.5, color: Odin.txtDim, height: 1.5)),
                    ),
                  ],
                ),
              )),
        ],
      ),
    );
  }
}
