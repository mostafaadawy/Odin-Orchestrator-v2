import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_state.dart';
import '../theme.dart';

/// Audit / Observer — the "silence page". Renders on EVERY surface (desktop/web/mobile) from the single
/// /audit/mirror bundle (mirrored to the anchor by the poller). Shows structure/DB integrity issues, the
/// debounced self-healing status, and the violations log (scope-answer + structural), newest first.
class AuditScreen extends StatefulWidget {
  const AuditScreen({super.key});
  @override
  State<AuditScreen> createState() => _AuditScreenState();
}

class _AuditScreenState extends State<AuditScreen> {
  Map<String, dynamic> _data = {};
  bool _loading = true;
  String? _msg;
  Timer? _live;

  @override
  void initState() {
    super.initState();
    _load();
    _live = Timer.periodic(const Duration(seconds: 12), (_) => _load(silent: true));
  }

  @override
  void dispose() {
    _live?.cancel();
    super.dispose();
  }

  Future<void> _load({bool silent = false}) async {
    if (!silent) setState(() => _loading = true);
    try {
      final d = await context.read<AppState>().api.auditData();
      if (mounted) setState(() { _data = d; _loading = false; });
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _run() async {
    setState(() => _msg = 'running…');
    try {
      final r = await context.read<AppState>().api.auditRun();
      final ran = r['ran'] == true;
      setState(() => _msg = ran
          ? 'healed ${r['healed'] ?? 0} · flagged ${r['flagged'] ?? 0}'
          : (r['note']?.toString() ?? 'debounced (silence gap not reached)'));
    } catch (_) {
      setState(() => _msg = 'error');
    }
    _load(silent: true);
  }

  @override
  Widget build(BuildContext context) {
    final status = (_data['status'] as Map?) ?? {};
    final cfg = (_data['config'] as Map?) ?? (status['config'] as Map?) ?? {};
    final issues = (_data['issues'] as List?) ?? [];
    final log = (((_data['violations'] as Map?)?['log']) as List?) ?? (_data['violations'] as List?) ?? [];
    final open = status['open_issues'] ?? issues.length;
    final enabled = cfg['enabled'] == true;
    final gap = cfg['silence_minutes'] ?? 30;

    return Scaffold(
      backgroundColor: Odin.bg,
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: Odin.brand))
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  Row(children: [
                    const Text('🛰️  ', style: TextStyle(fontSize: 20)),
                    const Expanded(
                      child: Text('Audit / Observer',
                          style: TextStyle(color: Odin.txt, fontSize: 20, fontWeight: FontWeight.w700)),
                    ),
                    _pill('$open open', open == 0 ? Odin.brand : Odin.danger),
                  ]),
                  const SizedBox(height: 4),
                  const Text('Structure + DB integrity and scope-answer reasoning — debounced self-healing safety net.',
                      style: TextStyle(color: Odin.txtDim, fontSize: 12)),
                  const SizedBox(height: 14),

                  // status / silence config
                  _card(Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Row(children: [
                      Icon(enabled ? Icons.shield_moon : Icons.shield_outlined,
                          color: enabled ? Odin.brand : Odin.txtFaint, size: 18),
                      const SizedBox(width: 8),
                      Text(enabled ? 'Observer ON' : 'Observer off',
                          style: const TextStyle(color: Odin.txt, fontWeight: FontWeight.w600)),
                      const Spacer(),
                      Text('silence gap: $gap min', style: const TextStyle(color: Odin.txtDim, fontSize: 12)),
                    ]),
                    const SizedBox(height: 8),
                    Text(
                        'It acts only after $gap minutes of no new writes (a silence gap), so it never reacts to every '
                        'single change. Fixes are real (index / move / promote / flag), so the corrected state stays '
                        'even if the observer is removed.',
                        style: const TextStyle(color: Odin.txtFaint, fontSize: 11.5)),
                    const SizedBox(height: 10),
                    Row(children: [
                      OutlinedButton.icon(
                        onPressed: _run,
                        icon: const Icon(Icons.play_arrow, size: 16),
                        label: const Text('Run now'),
                        style: OutlinedButton.styleFrom(
                            foregroundColor: Odin.txt, side: const BorderSide(color: Odin.strokeStrong)),
                      ),
                      const SizedBox(width: 12),
                      if (_msg != null) Text(_msg!, style: const TextStyle(color: Odin.txtDim, fontSize: 12)),
                    ]),
                  ])),
                  const SizedBox(height: 14),

                  // open issues
                  const Text('OPEN ISSUES', style: TextStyle(color: Odin.txtFaint, fontSize: 11, letterSpacing: 1)),
                  const SizedBox(height: 6),
                  if (issues.isEmpty)
                    _card(const Row(children: [
                      Icon(Icons.check_circle, color: Odin.brand, size: 18),
                      SizedBox(width: 8),
                      Text('No open issues — structure, DB and JSON-as-DB all clean.',
                          style: TextStyle(color: Odin.txt, fontSize: 13)),
                    ]))
                  else
                    ...issues.map((it) => _issueRow(Map<String, dynamic>.from(it as Map))),
                  const SizedBox(height: 16),

                  // violations log — the silence page history
                  const Text('VIOLATIONS LOG (newest first)',
                      style: TextStyle(color: Odin.txtFaint, fontSize: 11, letterSpacing: 1)),
                  const SizedBox(height: 6),
                  if (log.isEmpty)
                    _card(const Text('No violations recorded.', style: TextStyle(color: Odin.txtDim, fontSize: 13)))
                  else
                    ...log.reversed.take(60).map((e) => _logRow(Map<String, dynamic>.from(e as Map))),
                  const SizedBox(height: 40),
                ],
              ),
            ),
    );
  }

  Widget _pill(String s, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(
            color: c.withOpacity(0.14), borderRadius: BorderRadius.circular(20), border: Border.all(color: c.withOpacity(0.4))),
        child: Text(s, style: TextStyle(color: c, fontSize: 12, fontWeight: FontWeight.w600)),
      );

  Widget _card(Widget child) => Container(
        width: double.infinity,
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
            color: Odin.panelSolid, borderRadius: BorderRadius.circular(12), border: Border.all(color: Odin.stroke)),
        child: child,
      );

  Widget _issueRow(Map<String, dynamic> it) {
    final type = (it['type'] ?? '').toString();
    final where = (it['path'] ?? it['name'] ?? it['reason'] ?? (it['paths']?.toString()) ?? '').toString();
    return _card(Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
      _pill(type, Odin.danger),
      const SizedBox(width: 10),
      Expanded(child: Text(where, style: const TextStyle(color: Odin.txt, fontSize: 12.5))),
    ]));
  }

  Widget _logRow(Map<String, dynamic> e) {
    final type = (e['type'] ?? '').toString();
    final proj = (e['project'] ?? '').toString();
    final reason = (e['reason'] ?? e['probe'] ?? '').toString();
    final fix = (e['fix'] ?? '').toString();
    final ts = (e['ts'] ?? '').toString().replaceFirst('T', ' ');
    final scope = type == 'scope-answer';
    return _card(Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        _pill(type.isEmpty ? 'issue' : type, scope ? const Color(0xFFE0A21B) : Odin.txtDim),
        if (proj.isNotEmpty) ...[
          const SizedBox(width: 8),
          Flexible(child: Text(proj, style: const TextStyle(color: Odin.txtDim, fontSize: 11), overflow: TextOverflow.ellipsis)),
        ],
        const Spacer(),
        Text(ts.length > 19 ? ts.substring(0, 19) : ts, style: const TextStyle(color: Odin.txtFaint, fontSize: 10.5)),
      ]),
      if (reason.isNotEmpty) ...[
        const SizedBox(height: 6),
        Text(reason, style: const TextStyle(color: Odin.txt, fontSize: 12.5)),
      ],
      if (fix.isNotEmpty) ...[
        const SizedBox(height: 4),
        Text('→ $fix', style: const TextStyle(color: Odin.txtFaint, fontSize: 11.5)),
      ],
    ]));
  }
}
