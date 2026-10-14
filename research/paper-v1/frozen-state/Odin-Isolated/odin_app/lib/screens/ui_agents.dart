import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_state.dart';
import '../theme.dart';
import '../widgets.dart';

/// Phase-6 GENERIC agent roster (web + mobile). Content defines the COUNT (map over whatever the anchor
/// returns), TYPE defines the grouping/chip (from the agent-type def, resolved server-side into `ui`).
/// Identical contract to the desktop AgentsGrid — read from /anchor/v1/mirror/ui_agents.
class UiAgentsScreen extends StatefulWidget {
  const UiAgentsScreen({super.key});
  @override
  State<UiAgentsScreen> createState() => _UiAgentsScreenState();
}

class _UiAgentsScreenState extends State<UiAgentsScreen> {
  List<Map<String, dynamic>> _agents = [];
  bool _loading = true;
  String? _err;

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
      _agents = await context.read<AppState>().api.uiAgents();
    } catch (e) {
      _err = '$e';
    }
    if (mounted) setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    final groups = <String, List<Map<String, dynamic>>>{};
    for (final a in _agents) {
      (groups[(a['type'] ?? 'technical').toString()] ??= []).add(a);
    }
    final types = groups.keys.toList()..sort();
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Row(children: [
            const Expanded(child: SectionTitle('Agents')),
            IconButton(onPressed: _load, icon: const Icon(Icons.refresh)),
          ]),
          if (_loading) const Padding(padding: EdgeInsets.all(30), child: Center(child: CircularProgressIndicator(color: Odin.brand))),
          if (_err != null) Text(_err!, style: const TextStyle(color: Odin.danger, fontSize: 12)),
          for (final t in types) ..._group(t, groups[t]!),
        ],
      ),
    );
  }

  List<Widget> _group(String type, List<Map<String, dynamic>> items) {
    final chip = (items.first['ui'] is Map ? items.first['ui']['chip'] : null) ?? type;
    return [
      Padding(
        padding: const EdgeInsets.only(top: 6, bottom: 6),
        child: Text('${chip.toString().toUpperCase()} · ${items.length}',
            style: const TextStyle(fontSize: 12, letterSpacing: 1, color: Odin.txtFaint)),
      ),
      ...items.map(_card),
    ];
  }

  Widget _card(Map<String, dynamic> a) {
    final group = a['group']?.toString();
    final role = a['role']?.toString();
    final projects = a['projects'] ?? 0;
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: Odin.panelSolid,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Odin.stroke),
      ),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(
              child: Text(a['name']?.toString() ?? '',
                  style: const TextStyle(fontWeight: FontWeight.bold, color: Odin.txt),
                  overflow: TextOverflow.ellipsis),
            ),
            if (group != null && group.isNotEmpty)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 2),
                decoration: BoxDecoration(color: Odin.bg2, borderRadius: BorderRadius.circular(20)),
                child: Text(group, style: const TextStyle(fontSize: 11, color: Odin.txtFaint)),
              ),
          ]),
          if (role != null && role.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 3),
              child: Text(role, style: const TextStyle(fontSize: 12, color: Odin.txtFaint)),
            ),
          Text('used by $projects project${projects == 1 ? '' : 's'}',
              style: const TextStyle(fontSize: 12, color: Odin.txtFaint)),
          if (((a['ui']?['controls']) ?? const []).isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Wrap(spacing: 6, children: [
                for (final ctrl in (a['ui']['controls'] as List))
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                    decoration: BoxDecoration(color: Odin.bg2, borderRadius: BorderRadius.circular(20)),
                    child: Text(ctrl == 'voice' ? '🎙️ Voice' : ctrl == 'export' ? '⬇ Export' : '$ctrl',
                        style: const TextStyle(fontSize: 11, color: Odin.brand)),
                  ),
              ]),
            ),
        ]),
      ),
    );
  }
}
