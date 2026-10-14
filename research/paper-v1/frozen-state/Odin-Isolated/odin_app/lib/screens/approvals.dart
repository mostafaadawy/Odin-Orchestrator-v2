import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_state.dart';
import '../theme.dart';
import '../widgets.dart';

class ApprovalsScreen extends StatefulWidget {
  const ApprovalsScreen({super.key});
  @override
  State<ApprovalsScreen> createState() => _ApprovalsScreenState();
}

class _ApprovalsScreenState extends State<ApprovalsScreen> {
  List<Map<String, dynamic>> _items = [];
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
      _items = await context.read<AppState>().api.approvals();
    } catch (e) {
      _err = '$e';
    }
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _act(String aid, bool approve) async {
    final s = context.read<AppState>();
    if (approve) {
      await s.api.approveChange(aid);
    } else {
      await s.api.rejectChange(aid);
    }
    _load();
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Row(
            children: [
              const Expanded(child: SectionTitle('Approval center')),
              IconButton(onPressed: _load, icon: const Icon(Icons.refresh)),
            ],
          ),
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 6),
            child: Text('Nothing touches your code, config, or the VM until you approve it here.',
                style: TextStyle(fontSize: 12, color: Odin.txtDim)),
          ),
          if (_loading) const Padding(padding: EdgeInsets.all(30), child: Center(child: CircularProgressIndicator(color: Odin.brand))),
          if (_err != null) Text(_err!, style: const TextStyle(color: Odin.danger, fontSize: 12)),
          if (!_loading && _items.isEmpty && _err == null) const EmptyHint('No pending approvals.'),
          ..._items.map((a) => GlassCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Pill(a['kind']?.toString() ?? a['type']?.toString() ?? 'change',
                            color: Odin.warn, borderColor: Odin.warn.withValues(alpha: 0.4)),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text('${a['project'] ?? ''} · ${a['summary'] ?? a['title'] ?? a['id'] ?? ''}',
                              style: const TextStyle(fontSize: 13)),
                        ),
                      ],
                    ),
                    if ((a['detail'] ?? a['description'] ?? '').toString().isNotEmpty) ...[
                      const SizedBox(height: 6),
                      Text((a['detail'] ?? a['description']).toString(),
                          style: const TextStyle(fontSize: 12, color: Odin.txtDim)),
                    ],
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        FilledButton.icon(
                          style: FilledButton.styleFrom(backgroundColor: Odin.ok),
                          onPressed: () => _act(a['id'].toString(), true),
                          icon: const Icon(Icons.check, size: 16),
                          label: const Text('Approve'),
                        ),
                        const SizedBox(width: 8),
                        OutlinedButton.icon(
                          style: OutlinedButton.styleFrom(foregroundColor: Odin.danger),
                          onPressed: () => _act(a['id'].toString(), false),
                          icon: const Icon(Icons.close, size: 16),
                          label: const Text('Reject'),
                        ),
                      ],
                    ),
                  ],
                ),
              )),
        ],
      ),
    );
  }
}
