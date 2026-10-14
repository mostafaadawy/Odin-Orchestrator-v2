import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/models.dart';
import '../state/app_state.dart';
import '../theme.dart';
import '../widgets.dart';

class AnchorScreen extends StatelessWidget {
  const AnchorScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final s = context.watch<AppState>();
    final order = ['queued', 'sent_to_local', 'processing', 'ack_pending', 'finished', 'failed', 'cancelled'];
    final keys = [...order.where(s.counts.containsKey), ...s.counts.keys.where((k) => !order.contains(k))];

    return RefreshIndicator(
      onRefresh: s.refreshAnchor,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Row(
            children: [
              const Expanded(child: SectionTitle('🔌 Anchor Connect — pending & past tasks')),
              FilledButton.tonalIcon(
                onPressed: () => _send(context, s),
                icon: const Icon(Icons.add, size: 18),
                label: const Text('Send request'),
              ),
              IconButton(onPressed: s.refreshAnchor, icon: const Icon(Icons.refresh)),
            ],
          ),
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 6),
            child: Text(
              'Third parties & your remote apps reach local projects through the Anchor. A request is '
              'FINISHED only after the local machine processed it AND the webhook was acknowledged. '
              'Refreshes on click — and auto-refreshes when a background event lands.',
              style: TextStyle(fontSize: 12, color: Odin.txtDim),
            ),
          ),
          if (s.loadingAnchor && s.counts.isEmpty) const LinearProgressIndicator(minHeight: 2, color: Odin.brand),
          if (s.anchorError != null && s.requests.isEmpty)
            GlassCard(
              child: Column(
                children: [
                  const Icon(Icons.cloud_off, color: Odin.danger, size: 36),
                  const SizedBox(height: 8),
                  const Text('Could not reach the anchor'),
                  const SizedBox(height: 4),
                  Text(s.anchorError!, textAlign: TextAlign.center, style: const TextStyle(fontSize: 11, color: Odin.txtFaint)),
                  const SizedBox(height: 8),
                  OdinButton('Retry', icon: Icons.refresh, onPressed: s.refreshAnchor),
                ],
              ),
            ),
          if (keys.isNotEmpty) ...[
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: keys.map((k) => _CountChip(label: k, value: s.counts[k] ?? 0)).toList(),
            ),
          ],
          if (s.anchorCfg != null) ...[
            const SizedBox(height: 12),
            GlassCard(
              padding: const EdgeInsets.all(14),
              child: Wrap(
                spacing: 16,
                runSpacing: 8,
                children: [
                  Text('retry count: ${s.anchorCfg!['retry_count']}', style: const TextStyle(fontSize: 12)),
                  Text('retry interval: ${s.anchorCfg!['retry_interval_sec']}s', style: const TextStyle(fontSize: 12)),
                  Text('poll limit: ${s.anchorCfg!['poll_limit']}', style: const TextStyle(fontSize: 12)),
                ],
              ),
            ),
          ],
          const SizedBox(height: 12),
          GlassCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: const [
                Text('Lifecycle — a request is FINISHED only after the local machine returned a result AND the webhook was acknowledged.',
                    style: TextStyle(fontSize: 12, color: Odin.txtDim, height: 1.5)),
                SizedBox(height: 10),
                _LifecycleStep('queued', 'Accepted by the anchor and waiting in the smart queue.'),
                _LifecycleStep('sent_to_local', 'Handed to your machine on its next poll (never handed out twice).'),
                _LifecycleStep('processing', 'The CTO assigned the agent — the team is working on it.'),
                _LifecycleStep('response_received', 'Result produced locally; the anchor is delivering the webhook.'),
                _LifecycleStep('ack_pending', 'Webhook delivered but not yet 2xx-acked → will retry on its interval.'),
                _LifecycleStep('finished', 'Local result returned AND webhook acknowledged. Done.'),
                _LifecycleStep('failed', 'Retries exhausted — the record is kept (never silently deleted).'),
                _LifecycleStep('cancelled', 'Stopped by an admin action.'),
              ],
            ),
          ),
          const SizedBox(height: 12),
          GlassCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Requests', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
                const SizedBox(height: 6),
                if (s.requests.isEmpty)
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: 12),
                    child: Text('None yet.', style: TextStyle(fontSize: 12, color: Odin.txtFaint)),
                  )
                else
                  ...s.requests.map((r) => _RequestRow(r: r)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  void _send(BuildContext context, AppState s) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Odin.panelSolid,
      builder: (_) => _SendSheet(s: s),
    );
  }
}

class _CountChip extends StatelessWidget {
  final String label;
  final int value;
  const _CountChip({required this.label, required this.value});
  @override
  Widget build(BuildContext context) {
    final c = Odin.anchorStatusColor(label);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: c.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: c.withValues(alpha: 0.4)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text('$value', style: TextStyle(fontWeight: FontWeight.bold, color: c, fontSize: 18)),
          Text(label, style: const TextStyle(fontSize: 10, color: Odin.txtDim)),
        ],
      ),
    );
  }
}

class _RequestRow extends StatelessWidget {
  final AnchorRequest r;
  const _RequestRow({required this.r});
  @override
  Widget build(BuildContext context) {
    final c = Odin.anchorStatusColor(r.status);
    return InkWell(
      onTap: () => showDialog(
        context: context,
        builder: (_) => AlertDialog(
          backgroundColor: Odin.panelSolid,
          title: Text(r.id, style: const TextStyle(fontSize: 15)),
          content: SingleChildScrollView(
            child: SelectableText(
              'project: ${r.project}\nstatus: ${r.status}\nacked: ${r.acked}\n'
              'webhook attempts: ${r.webhookAttempts}\nerror: ${r.error}\n\nresult:\n${r.result}',
              style: const TextStyle(fontSize: 12),
            ),
          ),
          actions: [TextButton(onPressed: () => Navigator.pop(context), child: const Text('Close'))],
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Row(
          children: [
            Container(
              width: 104,
              padding: const EdgeInsets.symmetric(vertical: 3),
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: c.withValues(alpha: 0.16),
                borderRadius: BorderRadius.circular(999),
                border: Border.all(color: Odin.strokeStrong),
              ),
              child: Text(r.status, style: TextStyle(fontSize: 10.5, color: c)),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('${r.id.length > 16 ? r.id.substring(0, 16) : r.id}  →  ${r.project}',
                      style: const TextStyle(fontSize: 12, fontFamily: 'monospace', color: Odin.txtDim)),
                  Text('webhook ×${r.webhookAttempts}${r.acked ? ' · ✓ack' : ''}${r.error.isNotEmpty ? ' · ${r.error}' : ''}',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(fontSize: 10.5, color: r.error.isNotEmpty ? Odin.danger : Odin.txtFaint)),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SendSheet extends StatefulWidget {
  final AppState s;
  const _SendSheet({required this.s});
  @override
  State<_SendSheet> createState() => _SendSheetState();
}

class _SendSheetState extends State<_SendSheet> {
  String? _project;
  final _prompt = TextEditingController();
  String? _result;
  bool _busy = false;

  @override
  Widget build(BuildContext context) {
    final s = widget.s;
    return Padding(
      padding: EdgeInsets.only(left: 16, right: 16, top: 16, bottom: MediaQuery.of(context).viewInsets.bottom + 16),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SectionTitle('Send an external request', size: 16),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            initialValue: _project,
            isExpanded: true,
            dropdownColor: Odin.panelSolid,
            decoration: const InputDecoration(labelText: 'Target project', border: OutlineInputBorder()),
            items: s.projects.map((p) => DropdownMenuItem(value: p.id, child: Text(p.name, overflow: TextOverflow.ellipsis))).toList(),
            onChanged: (v) => setState(() => _project = v),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _prompt,
            minLines: 2,
            maxLines: 4,
            decoration: const InputDecoration(labelText: 'Prompt', border: OutlineInputBorder()),
          ),
          const SizedBox(height: 12),
          if (_result != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: SelectableText(_result!, style: const TextStyle(fontSize: 12, color: Odin.ok)),
            ),
          Row(
            children: [
              FilledButton.icon(
                onPressed: _busy || _project == null ? null : _submit,
                style: FilledButton.styleFrom(backgroundColor: Odin.brand),
                icon: _busy
                    ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Icon(Icons.send, size: 18),
                label: const Text('Submit'),
              ),
              const SizedBox(width: 8),
              TextButton(onPressed: () => Navigator.pop(context), child: const Text('Close')),
            ],
          ),
        ],
      ),
    );
  }

  Future<void> _submit() async {
    setState(() {
      _busy = true;
      _result = null;
    });
    try {
      final r = await widget.s.sendRequest(_project!, _prompt.text.trim());
      _result = 'Queued: ${r['request_id']} (${r['status']})';
      await widget.s.refreshAnchor();
    } catch (e) {
      _result = '⚠️ $e';
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }
}

class _LifecycleStep extends StatelessWidget {
  final String status;
  final String desc;
  const _LifecycleStep(this.status, this.desc);
  @override
  Widget build(BuildContext context) {
    final c = Odin.anchorStatusColor(status);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 104,
            padding: const EdgeInsets.symmetric(vertical: 2),
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: c.withValues(alpha: 0.16),
              borderRadius: BorderRadius.circular(999),
              border: Border.all(color: Odin.strokeStrong),
            ),
            child: Text(status, style: TextStyle(fontSize: 10.5, color: c)),
          ),
          const SizedBox(width: 10),
          Expanded(child: Text(desc, style: const TextStyle(fontSize: 11.5, color: Odin.txtDim, height: 1.4))),
        ],
      ),
    );
  }
}
