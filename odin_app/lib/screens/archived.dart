import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/models.dart';
import '../state/app_state.dart';
import '../theme.dart';
import '../widgets.dart';

class ArchivedScreen extends StatefulWidget {
  final void Function(String pid) onOpenProject;
  const ArchivedScreen({super.key, required this.onOpenProject});
  @override
  State<ArchivedScreen> createState() => _ArchivedScreenState();
}

class _ArchivedScreenState extends State<ArchivedScreen> {
  List<Project> _list = [];
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
      _list = await context.read<AppState>().api.archivedProjects();
    } catch (e) {
      _err = '$e';
    }
    if (mounted) setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    final s = context.read<AppState>();
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Row(
            children: [
              const Expanded(child: SectionTitle('Archived projects')),
              IconButton(onPressed: _load, icon: const Icon(Icons.refresh)),
            ],
          ),
          if (_loading) const Padding(padding: EdgeInsets.all(30), child: Center(child: CircularProgressIndicator(color: Odin.brand))),
          if (_err != null) Text(_err!, style: const TextStyle(color: Odin.danger, fontSize: 12)),
          if (!_loading && _list.isEmpty && _err == null) const EmptyHint('No archived projects.'),
          ..._list.map((p) => GlassCard(
                child: Row(
                  children: [
                    Text(typeByKey(p.type)?.icon ?? '📦', style: const TextStyle(fontSize: 18)),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(p.name, style: const TextStyle(fontWeight: FontWeight.w600)),
                          Text(typeByKey(p.type)?.label ?? p.type, style: const TextStyle(fontSize: 11, color: Odin.txtFaint)),
                        ],
                      ),
                    ),
                    TextButton(
                      onPressed: () async {
                        await s.api.unarchiveProject(p.id);
                        await s.refreshDashboard();
                        _load();
                      },
                      child: const Text('Unarchive'),
                    ),
                    IconButton(
                      tooltip: 'Delete',
                      icon: const Icon(Icons.delete_outline, color: Odin.danger, size: 20),
                      onPressed: () async {
                        final ok = await showDialog<bool>(
                          context: context,
                          builder: (_) => AlertDialog(
                            backgroundColor: Odin.panelSolid,
                            title: Text('Delete "${p.name}"?'),
                            content: const Text('Removes the project + its chats (files on disk are kept).'),
                            actions: [
                              TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
                              FilledButton(
                                  style: FilledButton.styleFrom(backgroundColor: Odin.danger),
                                  onPressed: () => Navigator.pop(context, true),
                                  child: const Text('Delete')),
                            ],
                          ),
                        );
                        if (ok == true) {
                          await s.api.deleteProject(p.id);
                          await s.refreshDashboard();
                          _load();
                        }
                      },
                    ),
                  ],
                ),
              )),
        ],
      ),
    );
  }
}
