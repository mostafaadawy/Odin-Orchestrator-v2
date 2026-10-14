import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/models.dart';
import '../state/app_state.dart';
import '../theme.dart';
import '../widgets.dart';

class AgentDetail extends StatefulWidget {
  final String pid;
  final String name;
  const AgentDetail({super.key, required this.pid, required this.name});
  @override
  State<AgentDetail> createState() => _AgentDetailState();
}

class _AgentDetailState extends State<AgentDetail> {
  Project? _p;
  List<Operation> _ops = [];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  Future<void> _load() async {
    final s = context.read<AppState>();
    try {
      _p = await s.api.project(widget.pid);
    } catch (_) {}
    try {
      _ops = await s.api.operations(widget.pid);
    } catch (_) {}
    await s.refreshActivity();
    if (mounted) setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final s = context.watch<AppState>();
    final kind = _p?.avatarFor(widget.name) ?? widget.name;
    final key = '${widget.pid}:${widget.name}';
    final active = s.activeKeys.contains(key);
    final act = s.activeByKey[key];

    // match this member to a role in the catalog for its identity + dependencies
    Role? found;
    for (final r in s.roles) {
      if (r.name.toLowerCase() == widget.name.toLowerCase()) {
        found = r;
        break;
      }
    }
    final role = found; // final local → reliable null-promotion below
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        GlassCard(
          child: Column(
            children: [
              Avatar(kind: kind, size: 84, active: active),
              const SizedBox(height: 10),
              SectionTitle(widget.name, size: 20),
              Text('${Odin.avatarKey(kind).toUpperCase()} · role on this project',
                  style: const TextStyle(fontSize: 12, color: Odin.txtDim, letterSpacing: 1)),
              const SizedBox(height: 8),
              Pill(active ? '● working now' : 'idle', color: active ? Odin.ok : Odin.txtDim,
                  borderColor: (active ? Odin.ok : Odin.txtDim).withValues(alpha: 0.4)),
            ],
          ),
        ),
        if (role != null) ...[
          const SizedBox(height: 12),
          GlassCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(children: [
                  Text(role.icon, style: const TextStyle(fontSize: 16)),
                  const SizedBox(width: 8),
                  Expanded(child: Text('${role.name} — ${role.group == 'tech' ? 'technical' : 'operational'} role',
                      style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700))),
                  Pill(role.ready ? 'ready' : 'needs setup',
                      color: role.ready ? Odin.ok : Odin.warn,
                      borderColor: (role.ready ? Odin.ok : Odin.warn).withValues(alpha: 0.4)),
                ]),
                if (role.description.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Text(role.description, style: const TextStyle(fontSize: 12.5, color: Odin.txtDim, height: 1.5)),
                ],
                if (role.missing.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Text('⚠ Needs connecting: ${role.missing.join(", ")} — it still works, but warns until set.',
                      style: const TextStyle(fontSize: 11.5, color: Odin.warn, height: 1.4)),
                ],
              ],
            ),
          ),
        ],
        const SizedBox(height: 12),
        GlassCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Text('Activity', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
                  const Spacer(),
                  IconButton(onPressed: _load, icon: const Icon(Icons.refresh, size: 18)),
                ],
              ),
              const SizedBox(height: 6),
              if (active && act != null) ...[
                Text('🗣️ ${act.phase.isEmpty ? 'working' : act.phase}', style: const TextStyle(fontSize: 13, color: Odin.ok)),
                if (act.task.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: Text(act.task, style: const TextStyle(fontSize: 12, color: Odin.txtDim)),
                  ),
              ] else
                const Text('No live activity. The heartbeat animates only when the agent is really working.',
                    style: TextStyle(fontSize: 12, color: Odin.txtFaint)),
            ],
          ),
        ),
        const SizedBox(height: 12),
        GlassCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('History (project operations)', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
              const SizedBox(height: 6),
              if (_ops.isEmpty)
                const Text('No operations recorded yet.', style: TextStyle(fontSize: 12, color: Odin.txtFaint))
              else
                ..._ops.take(12).map((o) => Padding(
                      padding: const EdgeInsets.symmetric(vertical: 3),
                      child: Row(
                        children: [
                          Pill(o.status,
                              color: o.status == 'finished' ? Odin.ok : o.status == 'failed' ? Odin.danger : Odin.brand,
                              borderColor: Odin.strokeStrong),
                          const SizedBox(width: 8),
                          Expanded(child: Text(o.kind, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12, color: Odin.txtDim))),
                        ],
                      ),
                    )),
            ],
          ),
        ),
      ],
    );
  }
}
