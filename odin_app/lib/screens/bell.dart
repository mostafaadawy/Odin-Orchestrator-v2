import 'dart:math' as math;
import 'package:flutter/material.dart';

import '../theme.dart';

/// The notification tabs — SINGLE SOURCE OF TRUTH. The bell badge shows this count (kBellTabs.length),
/// so the circle always equals the number of internal tabs. Add a tab here + a case in _tabBody().
const List<String> kBellTabs = [
  '① Story', '② Caching', '③ Klaviyo', '④ Veeqo', '⑤ Anchor', '⑥ Changes', '⑦ Tests', '⑧ Links',
  '⑨ Live Meeting', '⑩ Deploy', '⑪ Security SOC',
];

/// Polished notification bell panel — mirrors the desktop's animated "New in Odin"
/// popup: invite stage → tabbed details (Story with an animated diagram, Caching,
/// Tests, Anchor), with pop/fade/pulse/flow animations.
Future<void> showBell(BuildContext context) {
  return showGeneralDialog(
    context: context,
    barrierDismissible: true,
    barrierLabel: 'bell',
    barrierColor: Colors.black.withValues(alpha: 0.45),
    transitionDuration: const Duration(milliseconds: 220),
    pageBuilder: (_, __, ___) => const SizedBox.shrink(),
    transitionBuilder: (ctx, anim, _, __) {
      final curved = CurvedAnimation(parent: anim, curve: Curves.easeOutBack);
      return Align(
        alignment: Alignment.topRight,
        child: Padding(
          padding: const EdgeInsets.only(top: 58, right: 12, left: 12, bottom: 12),
          child: FadeTransition(
            opacity: anim,
            child: ScaleTransition(
              alignment: Alignment.topRight,
              scale: Tween(begin: 0.92, end: 1.0).animate(curved),
              child: const _BellPanel(),
            ),
          ),
        ),
      );
    },
  );
}

class _BellPanel extends StatefulWidget {
  const _BellPanel();
  @override
  State<_BellPanel> createState() => _BellPanelState();
}

class _BellPanelState extends State<_BellPanel> {
  bool _details = false;
  int _tab = 0; // 0 story 1 caching 2 tests 3 anchor

  @override
  Widget build(BuildContext context) {
    final w = MediaQuery.of(context).size.width;
    final panelW = _details ? math.min(460.0, w - 24) : math.min(340.0, w - 24);
    return Material(
      color: Colors.transparent,
      child: Container(
        width: panelW,
        constraints: BoxConstraints(maxHeight: MediaQuery.of(context).size.height - 90),
        decoration: BoxDecoration(
          color: Odin.panelSolid,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Odin.strokeStrong),
          boxShadow: const [BoxShadow(color: Color(0x80000000), blurRadius: 60, offset: Offset(0, 24))],
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              padding: const EdgeInsets.fromLTRB(15, 13, 12, 13),
              decoration: const BoxDecoration(border: Border(bottom: BorderSide(color: Odin.stroke))),
              child: Row(
                children: [
                  const Expanded(child: Text('✨ New in Odin', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700))),
                  InkWell(
                    onTap: () => Navigator.pop(context),
                    child: const Icon(Icons.close, size: 18, color: Odin.txtDim),
                  ),
                ],
              ),
            ),
            Flexible(
              child: SingleChildScrollView(
                child: _details ? _detailsView() : _inviteView(),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _inviteView() {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const _Fade(child: _StoryDiagram(height: 120)),
          const SizedBox(height: 10),
          RichText(
            text: const TextSpan(
              style: TextStyle(fontSize: 13.5, color: Odin.txt, height: 1.55),
              children: [
                TextSpan(text: 'Two big updates: your agents now '),
                TextSpan(text: 'reuse proven work', style: TextStyle(color: Odin.brand2, fontWeight: FontWeight.w700)),
                TextSpan(text: ', and '),
                TextSpan(text: 'Anchor Connect', style: TextStyle(color: Odin.brand2, fontWeight: FontWeight.w700)),
                TextSpan(text: ' lets your remote app + third parties reach local projects securely.'),
              ],
            ),
          ),
          const SizedBox(height: 14),
          FilledButton(
            onPressed: () => setState(() => _details = true),
            style: FilledButton.styleFrom(backgroundColor: Odin.brand),
            child: const Text('See how it works →'),
          ),
        ],
      ),
    );
  }

  Widget _detailsView() {
    const labels = kBellTabs;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(10, 10, 10, 4),
          child: Wrap(
            spacing: 6,
            runSpacing: 6,
            children: List.generate(labels.length, (i) {
              final on = _tab == i;
              return InkWell(
                onTap: () => setState(() => _tab = i),
                borderRadius: BorderRadius.circular(9),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: on ? const Color(0x296C8CFF) : Colors.transparent,
                    borderRadius: BorderRadius.circular(9),
                    border: Border.all(color: on ? const Color(0x596C8CFF) : Odin.stroke),
                  ),
                  child: Text(labels[i], style: TextStyle(fontSize: 12, color: on ? Colors.white : Odin.txtDim)),
                ),
              );
            }),
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 6, 16, 18),
          child: _Fade(key: ValueKey(_tab), child: _tabBody()),
        ),
      ],
    );
  }

  Widget _tabBody() {
    switch (_tab) {
      case 1:
        return const _CachingTab();
      case 2:
        return const _KlaviyoTab();
      case 3:
        return const _VeeqoTab();
      case 4:
        return const _AnchorTab();
      case 5:
        return const _ChangesTab();
      case 6:
        return const _TestsTab();
      case 7:
        return const _LinksTab();
      case 8:
        return const _LiveMeetingTab();
      case 9:
        return const _DeployTab();
      case 10:
        return const _SocTab();
      default:
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: const [
            _StoryDiagram(height: 130),
            SizedBox(height: 8),
            Text(
              'When a job is split across agents, each used to see only its slice — details drifted and '
              'results clashed. Now every agent reads from one growing shared context (the CTO\'s plan + '
              'everyone\'s work) and appends back to it. Same picture for all → consistent results.',
              style: TextStyle(fontSize: 12.5, color: Odin.txtDim, height: 1.6),
            ),
          ],
        );
    }
  }
}

// ---- animated story diagram ----
class _StoryDiagram extends StatefulWidget {
  final double height;
  const _StoryDiagram({this.height = 130});
  @override
  State<_StoryDiagram> createState() => _StoryDiagramState();
}

class _StoryDiagramState extends State<_StoryDiagram> with SingleTickerProviderStateMixin {
  late final AnimationController _c =
      AnimationController(vsync: this, duration: const Duration(seconds: 3))..repeat();
  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _c,
      builder: (_, __) => CustomPaint(painter: _StoryPainter(_c.value), size: Size(double.infinity, widget.height)),
    );
  }
}

class _StoryPainter extends CustomPainter {
  final double t;
  _StoryPainter(this.t);
  @override
  void paint(Canvas canvas, Size size) {
    final cy = size.height * 0.5;
    final cx = size.width / 2;
    final ax1 = size.width * 0.14, ax2 = size.width * 0.86;
    // dashed flowing links
    final dash = Paint()
      ..color = Odin.strokeStrong
      ..strokeWidth = 2;
    _dashedLine(canvas, Offset(ax1 + 18, cy), Offset(cx - 30, cy), dash, t);
    _dashedLine(canvas, Offset(cx + 30, cy), Offset(ax2 - 18, cy), dash, t);
    // side agents
    for (final ax in [ax1, ax2]) {
      canvas.drawCircle(Offset(ax, cy), 16, Paint()..color = Odin.brand.withValues(alpha: 0.15));
      canvas.drawCircle(Offset(ax, cy), 16, Paint()..color = Odin.brand..style = PaintingStyle.stroke..strokeWidth = 1.3);
    }
    _text(canvas, 'A1', Offset(ax1, cy), Odin.txtDim);
    _text(canvas, 'A2', Offset(ax2, cy), Odin.txtDim);
    // pulsing central shared-context pool
    final pulse = 0.86 + 0.14 * (0.5 + 0.5 * math.sin(t * 2 * math.pi));
    final r = 27.0 * pulse;
    canvas.drawCircle(Offset(cx, cy), r, Paint()..color = Odin.brand2.withValues(alpha: 0.12));
    canvas.drawCircle(Offset(cx, cy), r, Paint()..color = Odin.brand2..style = PaintingStyle.stroke..strokeWidth = 1.5);
    _text(canvas, 'SHARED', Offset(cx, cy - 6), Odin.brand2, 9, true);
    _text(canvas, 'CONTEXT', Offset(cx, cy + 6), Odin.brand2, 9, true);
    // a token that stays identical (drifts gently across the top)
    final tx = cx + (size.width * 0.18) * math.sin(t * 2 * math.pi);
    final rect = Rect.fromCenter(center: Offset(tx, size.height * 0.16), width: 13, height: 13);
    canvas.drawRRect(RRect.fromRectAndRadius(rect, const Radius.circular(3)), Paint()..color = Odin.brand2);
    _text(canvas, 'one source of truth — no drift', Offset(cx, size.height - 8), Odin.txtFaint, 9);
  }

  void _dashedLine(Canvas c, Offset a, Offset b, Paint p, double t) {
    const dash = 4.0, gap = 4.0;
    final total = (b - a).distance;
    final dir = (b - a) / total;
    double d = -((t * (dash + gap) * 2) % (dash + gap));
    while (d < total) {
      final s = math.max(0.0, d);
      final e = math.min(total, d + dash);
      if (e > s) c.drawLine(a + dir * s, a + dir * e, p);
      d += dash + gap;
    }
  }

  void _text(Canvas c, String s, Offset center, Color color, [double size = 10, bool bold = false]) {
    final tp = TextPainter(
      text: TextSpan(text: s, style: TextStyle(color: color, fontSize: size, fontWeight: bold ? FontWeight.w700 : FontWeight.w600)),
      textDirection: TextDirection.ltr,
    )..layout();
    tp.paint(c, center - Offset(tp.width / 2, tp.height / 2));
  }

  @override
  bool shouldRepaint(covariant _StoryPainter old) => old.t != t;
}

// ---- animated pipeline diagram (lives inside the Anchor tab) ----
class _PipelineDiagram extends StatefulWidget {
  final double height;
  const _PipelineDiagram({this.height = 150});
  @override
  State<_PipelineDiagram> createState() => _PipelineDiagramState();
}

class _PipelineDiagramState extends State<_PipelineDiagram> with SingleTickerProviderStateMixin {
  late final AnimationController _c =
      AnimationController(vsync: this, duration: const Duration(milliseconds: 2600))..repeat();
  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _c,
      builder: (_, __) => CustomPaint(painter: _PipelinePainter(_c.value), size: Size(double.infinity, widget.height)),
    );
  }
}

class _PipelinePainter extends CustomPainter {
  final double t;
  _PipelinePainter(this.t);
  static const _nodes = ['TP', 'Anchor', 'Local', 'Agents', 'Klav/VQ'];
  @override
  void paint(Canvas canvas, Size size) {
    final n = _nodes.length;
    final nw = (size.width - 8) / n - 8;
    final boxW = nw.clamp(40.0, 64.0);
    final gap = (size.width - boxW * n) / (n - 1 + 0.0001);
    final rowY = size.height * 0.28;
    final centers = <double>[];
    for (var i = 0; i < n; i++) {
      centers.add(boxW / 2 + i * (boxW + gap));
    }
    // forward connectors + flowing dots
    final dash = Paint()
      ..color = Odin.strokeStrong
      ..strokeWidth = 1.6;
    for (var i = 0; i < n - 1; i++) {
      final a = Offset(centers[i] + boxW / 2, rowY);
      final b = Offset(centers[i + 1] - boxW / 2, rowY);
      _dashed(canvas, a, b, dash);
      final phase = (t + i * 0.18) % 1.0;
      final p = Offset.lerp(a, b, phase)!;
      canvas.drawCircle(p, 3.5, Paint()..color = Odin.brand2);
    }
    // nodes
    for (var i = 0; i < n; i++) {
      final pulse = i == 1 ? (0.6 + 0.4 * (0.5 + 0.5 * math.sin(t * 2 * math.pi))) : 1.0;
      final c = i == 1 ? Odin.brand2 : Odin.brand;
      final rect = Rect.fromCenter(center: Offset(centers[i], rowY), width: boxW, height: 26);
      canvas.drawRRect(RRect.fromRectAndRadius(rect, const Radius.circular(7)),
          Paint()..color = Odin.brand.withValues(alpha: 0.13));
      canvas.drawRRect(RRect.fromRectAndRadius(rect, const Radius.circular(7)),
          Paint()..color = c.withValues(alpha: pulse)..style = PaintingStyle.stroke..strokeWidth = 1.3);
      _text(canvas, _nodes[i], Offset(centers[i], rowY), Odin.txtDim, 8.5, true);
    }
    // return path (result → webhook) flowing right→left
    final ry = size.height * 0.56;
    _dashed(canvas, Offset(size.width - 6, ry), Offset(6, ry),
        Paint()..color = Odin.brand2.withValues(alpha: 0.5)..strokeWidth = 1.6);
    final rp = Offset.lerp(Offset(size.width - 6, ry), Offset(6, ry), t)!;
    canvas.drawCircle(rp, 3.5, Paint()..color = Odin.ok);
    // labels
    _text(canvas, 'result → POST /result → webhook → 2xx ack → finished', Offset(size.width / 2, size.height * 0.74), Odin.brand2, 8.5);
    _text(canvas, 'POST /requests · X-API-Key · project id · prompt · webhook_url', Offset(size.width / 2, size.height * 0.88), Odin.txtFaint, 8);
    _text(canvas, 'GET /poll → CTO→team → read-only GET', Offset(size.width / 2, size.height * 0.99), Odin.txtFaint, 8);
  }

  void _dashed(Canvas c, Offset a, Offset b, Paint p) {
    const dash = 4.0, gap = 4.0;
    final total = (b - a).distance;
    if (total <= 0) return;
    final dir = (b - a) / total;
    double d = 0;
    while (d < total) {
      final s = d, e = math.min(total, d + dash);
      c.drawLine(a + dir * s, a + dir * e, p);
      d += dash + gap;
    }
  }

  void _text(Canvas c, String s, Offset center, Color color, double size, [bool bold = false]) {
    final tp = TextPainter(
      text: TextSpan(text: s, style: TextStyle(color: color, fontSize: size, fontWeight: bold ? FontWeight.w700 : FontWeight.w500)),
      textDirection: TextDirection.ltr,
      textAlign: TextAlign.center,
    )..layout(maxWidth: 360);
    tp.paint(c, center - Offset(tp.width / 2, tp.height / 2));
  }

  @override
  bool shouldRepaint(covariant _PipelinePainter old) => old.t != t;
}

// ---- content tabs ----
class _CachingTab extends StatelessWidget {
  const _CachingTab();
  @override
  Widget build(BuildContext context) {
    const steps = [
      ['📥', 'A task arrives for a role (e.g. DevOps).'],
      ['🔎', "The agent fetches its pool folder + reads each module's metadata."],
      ['🧠', 'It DECIDES: does a proven module match? If yes — configure & reuse.'],
      ['⚡', 'Reused, not rebuilt → faster, and already battle-tested.'],
    ];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: const EdgeInsets.all(9),
          decoration: BoxDecoration(
            color: const Color(0x08FFFFFF),
            border: Border.all(color: Odin.stroke),
            borderRadius: BorderRadius.circular(8),
          ),
          child: const Text('cached_modules/DevOps/cloud_deploy.sh + .meta.json',
              style: TextStyle(fontSize: 11, color: Odin.brand2, fontFamily: 'monospace')),
        ),
        const SizedBox(height: 10),
        for (var k = 0; k < steps.length; k++)
          _Stagger(
            delayMs: 120 * k,
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                SizedBox(width: 22, child: Text(steps[k][0], style: const TextStyle(fontSize: 15))),
                const SizedBox(width: 8),
                Expanded(child: Text(steps[k][1], style: const TextStyle(fontSize: 12.5, color: Odin.txtDim, height: 1.45))),
              ]),
            ),
          ),
        const SizedBox(height: 10),
        const Text(
          'The library only grows from work that actually succeeded — never filler. Each script carries '
          'safe defaults (keeps ports 80/443 open, never syncs secrets, never reboots unless asked).',
          style: TextStyle(fontSize: 11.5, color: Odin.txtFaint, height: 1.5),
        ),
      ],
    );
  }
}

class _TestsTab extends StatelessWidget {
  const _TestsTab();
  @override
  Widget build(BuildContext context) {
    const rows = [
      ['1', 'Anchor Phase 1', 'python3 server/e2e_anchor_all.py — prints 50 flows (28/22), 26 orders'],
      ['2', 'Topology', 'python3 server/e2e_phase2.py — app ⇄ remote anchor ⇄ local'],
      ['3', 'Third party', 'third_party_sim.html or server/third_party.py'],
      ['4', 'Webhook + ack', 'python3 server/webhook_receiver.py --port 9300'],
    ];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Nothing is trusted without proof. These end-to-end tests verify the work and are built to be '
          'un-gameable (a massaged green is treated as a failure).',
          style: TextStyle(fontSize: 12.5, color: Odin.txtDim, height: 1.55),
        ),
        const SizedBox(height: 10),
        for (var k = 0; k < rows.length; k++)
          _Stagger(
            delayMs: 110 * k,
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 5),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                SizedBox(width: 18, child: Text(rows[k][0], style: const TextStyle(fontSize: 13, color: Odin.brand2))),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(rows[k][1], style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700)),
                    SelectableText(rows[k][2], style: const TextStyle(fontSize: 11, color: Odin.txtDim, fontFamily: 'monospace', height: 1.4)),
                  ]),
                ),
              ]),
            ),
          ),
      ],
    );
  }
}

class _DocRow extends StatelessWidget {
  final String label;
  final String value;
  const _DocRow(this.label, this.value);
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: RichText(
        text: TextSpan(
          style: const TextStyle(fontSize: 12.5, color: Odin.txtDim, height: 1.55),
          children: [
            TextSpan(text: '$label: ', style: const TextStyle(color: Odin.txt, fontWeight: FontWeight.w700)),
            TextSpan(text: value),
          ],
        ),
      ),
    );
  }
}

class _KlaviyoTab extends StatelessWidget {
  const _KlaviyoTab();
  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: const [
        Text('✉️ Klaviyo — Email', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700)),
        SizedBox(height: 6),
        _DocRow('What', 'email/SMS marketing automation — you build "flows" (automated journeys) and campaigns.'),
        _DocRow('Connect', 'oth/.cred → KLAVIYO_API_KEY=pk_… , KLAVIYO_BASE_URL=https://a.klaviyo.com/api , KLAVIYO_API_REVISION=2025-01-15. Header: Authorization: Klaviyo-API-Key <key> + revision.'),
        _DocRow('Make the project', 'New project → type "Email specialist" → the Email agent attaches. Identifier: email-klaviyo.'),
        _DocRow('Agent can', 'hit any Klaviyo endpoint via call(); read-only flows_summary() counts flows by status.'),
        _DocRow('Live numbers', '50 flows total — 28 live / 22 draft.'),
        _DocRow('File', 'server/integrations/klaviyo.py'),
      ],
    );
  }
}

class _VeeqoTab extends StatelessWidget {
  const _VeeqoTab();
  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: const [
        Text('📦 Veeqo — Shipping / Fulfillment', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700)),
        SizedBox(height: 6),
        _DocRow('What', 'inventory + shipping/fulfillment platform — orders, shipments, carriers.'),
        _DocRow('Connect', 'oth/.cred → VEEQO_API_KEY=Vqt/… . Base https://api.veeqo.com . Header: x-api-key.'),
        _DocRow('Make the project', 'New project → type "Fulfillment Provider" → the Shipping agent attaches. Identifier: shipping-veeqo.'),
        _DocRow('Agent can', 'orders, shipments, create_shipment, carriers, current_user; read-only orders_summary(since).'),
        _DocRow('Live number', '26 orders this week.'),
        _DocRow('File', 'server/integrations/veeqo.py'),
      ],
    );
  }
}

class _AnchorTab extends StatelessWidget {
  const _AnchorTab();
  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: const [
        _PipelineDiagram(height: 150),
        SizedBox(height: 8),
        Text('⚓ Anchor Connect', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700)),
        SizedBox(height: 6),
        _DocRow('Why', 'your machine has a dynamic IP behind NAT — unreachable. The anchor (on the VM) is the stable, authenticated front door; your machine only calls out to it.'),
        _DocRow('Flow', 'third party → POST /anchor/v1/requests → queue → your machine GET /poll → CTO→team → read-only Klaviyo/Veeqo → POST /result → anchor POSTs your webhook_url → 2xx ack → finished.'),
        _DocRow('Passed in the request', 'X-API-Key (ANCHOR_API_KEY), project (identifier), prompt, webhook_url.'),
        _DocRow('Endpoints', 'POST /requests · GET /requests/{id} · POST /requests/{id}/ack · GET /poll · POST /requests/{id}/result · admin/counts|requests|config.'),
        _DocRow('Lifecycle', 'queued → sent_to_local → processing → response_received → webhook_sent → acknowledged → finished (+ ack_pending / failed / cancelled).'),
        _DocRow('Ports', '9100 = anchor stand-in · 9300 = webhook receiver (callback /cb, viewer /).'),
        _DocRow('Production', 'point the anchor URL at the VM, TLS on 443, rotate keys, sign webhooks — only the base URL changes.'),
      ],
    );
  }
}

class _ChangesTab extends StatelessWidget {
  const _ChangesTab();
  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: const [
        Text('🔧 What changed', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700)),
        SizedBox(height: 6),
        _DocRow('Desktop', 'bell gained the ④ Anchor doc; Anchor Connect page; grouped project types; agent/role roster; operations + block→ask→continue.'),
        _DocRow('Backend', 'anchor_queue, anchor, anchor_remote, local_poller_http, klaviyo, veeqo, external_api (/api/v1), auth, webhook_receiver, gen_test_keys.'),
        _DocRow('Web + Mobile (odin_app)', 'full mirror — dashboard, project, agent, anchor, approvals, archived, docs, settings/account; login + Face ID + 2FA; shared /scope chat; voice; streaming; new project.'),
        _DocRow('How connected', 'app→brain (/api/v1,/projects,/scope,/auth) on LAN · app→anchor (/anchor/v1) when remote · third party→anchor · poller→anchor.'),
        _DocRow('Full docs', 'docs/ODIN_PHASES_TECH_DOC.pdf · docs/odin_pipeline.html · ANCHOR_CONTRACT.md'),
      ],
    );
  }
}

class _LinksTab extends StatelessWidget {
  const _LinksTab();
  Widget _grp(String title, List<String> items) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700, color: Odin.brand2)),
            const SizedBox(height: 4),
            ...items.map((s) => Padding(
                  padding: const EdgeInsets.symmetric(vertical: 1.5),
                  child: SelectableText('• $s',
                      style: const TextStyle(fontSize: 11.5, color: Odin.txtDim, fontFamily: 'monospace', height: 1.4)),
                )),
          ],
        ),
      );

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('🔗 Important files & links', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700)),
        const SizedBox(height: 2),
        const Text('Paths under ~/Desktop/AiAgentWorkSpace. Open from Finder or the link cards in chat.',
            style: TextStyle(fontSize: 11, color: Odin.txtFaint)),
        const SizedBox(height: 10),
        _grp('Paper & article (previous)', const [
          'Resulted Papers and Documents/odin_paper.pdf  (.docx, .tex)',
          'Resulted Papers and Documents/engineering_journey.pdf  (.docx, .md)',
          'Resulted Papers and Documents/venue_submission_guide.pdf  (.docx)',
          'Resulted Papers and Documents/Social Media/linkedin_post.docx',
          'Resulted Papers and Documents/Social Media/instagram_post.docx',
        ]),
        _grp('Current docs', const [
          'Odin-Orchestrator/docs/ODIN_PHASES_TECH_DOC.pdf  (.md)',
          'Odin-Orchestrator/docs/odin_pipeline.html',
          'Odin-Orchestrator/ANCHOR_CONTRACT.md',
          'Odin-Orchestrator/README_ANCHOR_AND_INTEGRATIONS.md',
        ]),
        _grp('Key code', const [
          'server/anchor_queue.py · anchor.py · anchor_remote.py',
          'server/local_poller_http.py · webhook_receiver.py · auth.py',
          'server/integrations/klaviyo.py · veeqo.py',
          'server/e2e_anchor_all.py · e2e_phase2.py · third_party.py',
          'odin_app/lib  (Flutter web + mobile)  ·  desktop/src/views.jsx',
          'third_party_sim.html · phase2_up.sh',
        ]),
      ],
    );
  }
}

// ⑨ LIVE MEETING — tutorial for the Global Voice Streaming asset.
class _LiveMeetingTab extends StatelessWidget {
  const _LiveMeetingTab();
  @override
  Widget build(BuildContext context) {
    const steps = [
      ['🗣️', 'Open a meeting/voice project (e.g. the Zoom agent). In the chat header — normal AND chat mode — tap the speaking‑head icon (next to ▶). It is NOT the dictation mic.'],
      ['🎙️', 'A popup dialog opens (web/desktop) or a native sheet (mobile). Grant mic permission, then Start listening. You see a big mic, live sensitivity, voice‑activity, noise level, language, and chunks saving 1,2,3…'],
      ['⏸️', 'Pause/Resume anytime. Each chunk is transcribed live, its language detected, and low‑confidence chunks are marked for review.'],
      ['🧠', 'Stop → the chunks are refined (fillers/duplicates/noise removed, technical terms & names kept), and a smart 13‑section report is built in the meeting’s language.'],
      ['📄', 'The report shows in the dialog AND is embedded into the project chat as Markdown. Tap Close when done.'],
      ['⬇️', 'Export: Markdown or Word (.docx), Arabic or English — or “All 4” as one zip. DOCX is clean, colorful and structured.'],
    ];
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const Text('🗣️ Live Meeting — voice → smart report', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700)),
      const SizedBox(height: 2),
      const Text('A reusable app asset owned by the Live Meeting & Voice Streaming Agent. Works on web, desktop and mobile.',
          style: TextStyle(fontSize: 11, color: Odin.txtFaint)),
      const SizedBox(height: 10),
      for (var k = 0; k < steps.length; k++)
        _Stagger(delayMs: 110 * k, child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 4),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            SizedBox(width: 22, child: Text(steps[k][0], style: const TextStyle(fontSize: 15))),
            const SizedBox(width: 8),
            Expanded(child: Text(steps[k][1], style: const TextStyle(fontSize: 12.5, color: Odin.txtDim, height: 1.45))),
          ]),
        )),
      const SizedBox(height: 8),
      const _DocRow('📚 Docs', 'assets/global_voice_streaming_asset.md · docs/WHATS_NEW.md'),
    ]);
  }
}

// ⑩ DEPLOY — tutorial for the DevOps production deployment.
class _DeployTab extends StatelessWidget {
  const _DeployTab();
  @override
  Widget build(BuildContext context) {
    const steps = [
      ['📦', 'The deployment project (e.g. “Organics Production Deploy (2VM)”) is created through the real intake flow — DevOps‑only, no other agents.'],
      ['🔒', 'Source‑of‑truth folders (organics‑backend / organics‑frontend) are read‑only. The working copy + a .git baseline live under ~/Desktop/misc/Odin/.'],
      ['🚩', 'A persistent first‑time flag: the first corrected deploy ships everything; later deploys diff the .git baseline and ship ONLY changed files.'],
      ['⚙️', 'Deploy from the project: preview the exact rsync + commands + reboot, respecting the exclusion lists (.env, node_modules, dist, .next, migrations, …).'],
      ['🗄️', 'Database: the reset runs only the first time; every later deploy ASKS before any DB reset. Nothing destructive runs without your approval.'],
      ['✅', 'After reboot: health checks (domain, backend, frontend, nginx, systemd) confirm the update is really live on the Azure VM.'],
    ];
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const Text('🚀 Deploy — DevOps to the Azure VM', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700)),
      const SizedBox(height: 2),
      const Text('Corrected, repeatable production deployment. Source = local machine → destination = Azure VM.',
          style: TextStyle(fontSize: 11, color: Odin.txtFaint)),
      const SizedBox(height: 10),
      for (var k = 0; k < steps.length; k++)
        _Stagger(delayMs: 110 * k, child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 4),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            SizedBox(width: 22, child: Text(steps[k][0], style: const TextStyle(fontSize: 15))),
            const SizedBox(width: 8),
            Expanded(child: Text(steps[k][1], style: const TextStyle(fontSize: 12.5, color: Odin.txtDim, height: 1.45))),
          ]),
        )),
      const SizedBox(height: 8),
      const _DocRow('📚 Docs', 'docs/WHATS_NEW.md · infra/deploy.config.sh'),
    ]);
  }
}

// ⑪ SECURITY SOC — the always-on multi-agent security company (educational + how it works).
class _SocTab extends StatelessWidget {
  const _SocTab();
  @override
  Widget build(BuildContext context) {
    const agents = [
      ['🧭', 'CTO Orchestrator — governs each run, correlates everyone into a root cause, raises approvals (approves nothing itself).'],
      ['🗺️', 'Asset & Attack‑Surface — living inventory of every cloud/VM/stack (Azure now; extensible to AWS/GoDaddy/Hostinger/Cloudflare) + reverse‑search targeting.'],
      ['🧠', 'Threat‑Hunting Architect — pulls current advisories (OSV.dev) for OUR versions, triages by reachability, keeps the playbooks current.'],
      ['🔎', 'Operations Investigator — read‑only checks of the present state: services, ports/NSG/ufw, website, SSH, persistence, miner hunt, abuse, DB, deps.'],
      ['🕵️', 'Behavioral Analytics (UEBA) — catches stealthy/AI‑era abuse by behaviour (same‑IP‑many‑accounts, low‑and‑slow) and excludes YOUR dynamic IP.'],
      ['🔮', 'Prediction & Prevention — predicts the NEXT weakness and hardens before exploitation.'],
      ['🛟', 'Recovery & Resilience — encrypted dated backups (key on your desktop only) + smart date‑aware recovery.'],
      ['📝', 'Reporting — branded report: plain‑language first, then technical. PDF/DOCX/MD/PPTX.'],
    ];
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const Text('🛡️ RedBerry Continuous SOC', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700)),
      const SizedBox(height: 2),
      const Text('An always‑on, monitor‑and‑report‑only security company of 8 non‑overlapping agents. '
          'Runs daily 11 PM (New York, DST‑aware, with catch‑up) and on demand. It changes nothing on its own — '
          'only decisions that recover or modify a working service need your approval.',
          style: TextStyle(fontSize: 11, color: Odin.txtFaint, height: 1.5)),
      const SizedBox(height: 10),
      const Text('Who does what (ask any agent “what is your role?”):',
          style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Odin.txt)),
      const SizedBox(height: 6),
      for (var k = 0; k < agents.length; k++)
        _Stagger(delayMs: 80 * k, child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 3),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            SizedBox(width: 22, child: Text(agents[k][0], style: const TextStyle(fontSize: 15))),
            const SizedBox(width: 8),
            Expanded(child: Text(agents[k][1], style: const TextStyle(fontSize: 12.5, color: Odin.txtDim, height: 1.45))),
          ]),
        )),
      const SizedBox(height: 8),
      const Text('Methodology: white‑scope wide sweep → narrow to evidence (NIST 800‑61 · SANS PICERL · '
          'threat‑hunting funnel · MITRE ATT&CK). Reports & backups live in the RedBerry‑Continuous‑SOC project folder.',
          style: TextStyle(fontSize: 11.5, color: Odin.txtDim, height: 1.5)),
      const SizedBox(height: 8),
      const _DocRow('📚 Learn', 'docs/SOC_SECURITY_ROLES.md · docs/SOC_REDBERRY.md'),
      const _DocRow('🔗 API', '/soc/status · /soc/run · /soc/report?fmt=pdf · /soc/inventory · /soc/behavior · /soc/recovery'),
    ]);
  }
}

// ---- tiny animation helpers ----
class _Fade extends StatelessWidget {
  final Widget child;
  const _Fade({super.key, required this.child});
  @override
  Widget build(BuildContext context) {
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0, end: 1),
      duration: const Duration(milliseconds: 320),
      builder: (_, v, c) => Opacity(opacity: v, child: Transform.translate(offset: Offset(0, (1 - v) * 6), child: c)),
      child: child,
    );
  }
}

class _Stagger extends StatelessWidget {
  final int delayMs;
  final Widget child;
  const _Stagger({required this.delayMs, required this.child});
  @override
  Widget build(BuildContext context) {
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0, end: 1),
      duration: Duration(milliseconds: 350 + delayMs),
      curve: Curves.easeOut,
      builder: (_, v, c) => Opacity(opacity: v.clamp(0, 1), child: Transform.translate(offset: Offset((1 - v) * 8, 0), child: c)),
      child: child,
    );
  }
}
