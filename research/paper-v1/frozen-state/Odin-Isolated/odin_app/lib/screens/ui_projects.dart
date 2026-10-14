import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_state.dart';
import '../theme.dart';
import '../widgets.dart';

/// Phase-6 GENERIC, DB-driven project list (web + mobile). Content defines the COUNT (map over whatever
/// the anchor mirror returns); TYPE defines the UI (each card's controls + icons come from the `ui` spec).
/// Nothing hardcoded — identical contract to the desktop, read from /anchor/v1/mirror/ui_projects.
class UiProjectsScreen extends StatefulWidget {
  final void Function(String pid) onOpenProject;
  const UiProjectsScreen({super.key, required this.onOpenProject});
  @override
  State<UiProjectsScreen> createState() => _UiProjectsScreenState();
}

class _UiProjectsScreenState extends State<UiProjectsScreen> {
  List<Map<String, dynamic>> _cards = [];
  bool _loading = true;
  String? _err;

  static const Map<String, String> _icon = {'streaming-voice': '🎙️', 'notification': '🔔'};

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _err = null;
    });
    try {
      _cards = await context.read<AppState>().api.uiProjects();
    } catch (e) {
      _err = '$e';
    }
    if (mounted) setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Row(children: [
            const Expanded(child: SectionTitle('Projects')),
            IconButton(onPressed: _load, icon: const Icon(Icons.refresh)),
          ]),
          if (_loading) const Padding(padding: EdgeInsets.all(30), child: Center(child: CircularProgressIndicator(color: Odin.brand))),
          if (_err != null) Text(_err!, style: const TextStyle(color: Odin.danger, fontSize: 12)),
          ..._cards.map(_card),
        ],
      ),
    );
  }

  Widget _card(Map<String, dynamic> c) {
    final ui = (c['ui'] ?? const {}) as Map;
    final counts = (c['counts'] ?? const {}) as Map;
    final controls = (ui['controls'] ?? const []) as List;
    final icons = (ui['icons'] ?? const []) as List;
    final config = (c['config'] ?? const {}) as Map;
    final pid = c['id']?.toString() ?? '';
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(
        color: Odin.panelSolid,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Odin.stroke),
      ),
      child: InkWell(
        onTap: () => widget.onOpenProject(pid),
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(
                child: Text(c['name']?.toString() ?? '',
                    style: const TextStyle(fontWeight: FontWeight.bold, color: Odin.txt),
                    overflow: TextOverflow.ellipsis),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 2),
                decoration: BoxDecoration(color: Odin.bg2, borderRadius: BorderRadius.circular(20)),
                child: Text('${ui['chip'] ?? ''}', style: const TextStyle(fontSize: 11, color: Odin.txtFaint)),
              ),
            ]),
            const SizedBox(height: 4),
            Text(
              '${c['category'] ?? ''}${icons.isNotEmpty ? '  ${icons.map((i) => _icon[i] ?? '•').join(' ')}' : ''}',
              style: const TextStyle(fontSize: 12, color: Odin.txtFaint),
            ),
            Text(
              'agents ${counts['agents'] ?? 0} · connectors ${counts['connectors'] ?? 0} · files ${counts['files'] ?? 0}',
              style: const TextStyle(fontSize: 12, color: Odin.txtFaint),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 6,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                for (final ctrl in controls) _control(ctrl.toString(), pid, c, config),
                if (controls.isEmpty) const Text('on-demand', style: TextStyle(fontSize: 12, color: Odin.txtFaint)),
              ],
            ),
          ]),
        ),
      ),
    );
  }

  Widget _control(String ctrl, String pid, Map c, Map config) {
    if (ctrl == 'play' || ctrl == 'run-once') {
      return ElevatedButton.icon(
        onPressed: () => widget.onOpenProject(pid),
        icon: const Icon(Icons.play_arrow, size: 16),
        label: Text(ctrl == 'run-once' ? 'Run once' : 'Run'),
        style: ElevatedButton.styleFrom(
          backgroundColor: Odin.ok,
          foregroundColor: Odin.bg,
          visualDensity: VisualDensity.compact,
        ),
      );
    }
    if (ctrl == 'export') {
      return OutlinedButton.icon(
        onPressed: () => widget.onOpenProject(pid),
        icon: const Icon(Icons.download, size: 16),
        label: const Text('Export'),
        style: OutlinedButton.styleFrom(foregroundColor: Odin.brand, visualDensity: VisualDensity.compact),
      );
    }
    if (ctrl == 'cadence') {
      return Text('cadence: ${config['cadence'] ?? c['cadence'] ?? '—'}', style: const TextStyle(fontSize: 12, color: Odin.txtFaint));
    }
    if (ctrl == 'period') {
      return Text('period: ${config['period'] ?? '—'}', style: const TextStyle(fontSize: 12, color: Odin.txtFaint));
    }
    if (ctrl == 'timeout') {
      return Text('timeout: ${config['timeout'] ?? 300}s', style: const TextStyle(fontSize: 12, color: Odin.txtFaint));
    }
    return const SizedBox.shrink();
  }
}
