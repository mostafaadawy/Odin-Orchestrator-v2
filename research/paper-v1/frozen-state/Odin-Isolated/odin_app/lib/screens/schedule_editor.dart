import 'package:flutter/material.dart';
import '../api/anchor_api.dart';
import '../theme.dart';

const _tzs = [
  'Africa/Cairo', 'Europe/London', 'America/New_York', 'America/Los_Angeles', 'Europe/Berlin',
  'Asia/Dubai', 'Asia/Riyadh', 'Asia/Kolkata', 'Asia/Singapore', 'Australia/Sydney', 'UTC',
];
const _wd = [['Mon', 0], ['Tue', 1], ['Wed', 2], ['Thu', 3], ['Fri', 4], ['Sat', 5], ['Sun', 6]];

/// Edit a recurring task's schedule: change time(s), add MULTIPLE times, daily/weekly/monthly, timezone
/// (default Egypt). Saves via /schedules/{id}/update. Works on web + mobile.
Future<bool?> showScheduleEditor(BuildContext context, OdinApi api, Map<String, dynamic> task) {
  return showDialog<bool>(
    context: context,
    builder: (_) => _ScheduleEditorDialog(api: api, task: task),
  );
}

class _ScheduleEditorDialog extends StatefulWidget {
  final OdinApi api;
  final Map<String, dynamic> task;
  const _ScheduleEditorDialog({required this.api, required this.task});
  @override
  State<_ScheduleEditorDialog> createState() => _ScheduleEditorDialogState();
}

class _ScheduleEditorDialogState extends State<_ScheduleEditorDialog> {
  late String _cadence;
  late List<String> _times;
  late String _tz;
  late Set<int> _weekdays;
  late String _monthdays;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    final s = (widget.task['schedule'] as Map?) ?? {};
    _weekdays = ((s['weekdays'] as List?)?.map((e) => e as int).toSet()) ?? <int>{};
    final md = (s['monthdays'] as List?)?.map((e) => e.toString()).join(',');
    _monthdays = (md != null && md.isNotEmpty) ? md : '1';
    _cadence = _weekdays.isNotEmpty ? 'weekly' : (s['monthdays'] != null && (s['monthdays'] as List).isNotEmpty ? 'monthly' : 'daily');
    final t = (s['times'] as List?)?.map((e) => e.toString()).toList();
    _times = (t != null && t.isNotEmpty) ? t : [s['hhmm']?.toString() ?? '09:00'];
    _tz = s['tz']?.toString() ?? 'Africa/Cairo';
  }

  Future<void> _pickTime(int i) async {
    final parts = _times[i].split(':');
    final res = await showTimePicker(
      context: context,
      initialTime: TimeOfDay(hour: int.tryParse(parts[0]) ?? 9, minute: int.tryParse(parts.length > 1 ? parts[1] : '0') ?? 0),
    );
    if (res != null) {
      setState(() => _times[i] = '${res.hour.toString().padLeft(2, '0')}:${res.minute.toString().padLeft(2, '0')}');
    }
  }

  Future<void> _save() async {
    setState(() => _busy = true);
    final sched = <String, dynamic>{'kind': 'calendar', 'times': _times.where((t) => t.isNotEmpty).toList(), 'tz': _tz};
    if (_cadence == 'weekly') sched['weekdays'] = _weekdays.isNotEmpty ? _weekdays.toList() : [0, 1, 2, 3, 4, 5, 6];
    if (_cadence == 'monthly') {
      sched['monthdays'] = _monthdays.split(',').map((x) => int.tryParse(x.trim()) ?? 0).where((x) => x >= 1 && x <= 31).toList();
    }
    await widget.api.updateSchedule(widget.task['id']?.toString() ?? '', {'schedule': sched});
    if (mounted) Navigator.pop(context, true);
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: Odin.panelSolid,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 440),
        child: Padding(
          padding: const EdgeInsets.all(18),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('⏰ Edit schedule — ${widget.task['title'] ?? ''}',
                  style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700)),
              const SizedBox(height: 14),
              Row(children: [
                const Text('Repeat', style: TextStyle(fontSize: 12, color: Odin.txtDim)),
                const SizedBox(width: 10),
                ...['daily', 'weekly', 'monthly'].map((c) => Padding(
                      padding: const EdgeInsets.only(right: 6),
                      child: ChoiceChip(
                        label: Text(c, style: const TextStyle(fontSize: 11)),
                        selected: _cadence == c,
                        onSelected: (_) => setState(() => _cadence = c),
                      ),
                    )),
              ]),
              const SizedBox(height: 10),
              if (_cadence == 'weekly')
                Wrap(spacing: 5, children: _wd.map((d) {
                  final on = _weekdays.contains(d[1] as int);
                  return FilterChip(
                    label: Text(d[0] as String, style: const TextStyle(fontSize: 10.5)),
                    selected: on,
                    onSelected: (_) => setState(() => on ? _weekdays.remove(d[1]) : _weekdays.add(d[1] as int)),
                  );
                }).toList()),
              if (_cadence == 'monthly')
                Row(children: [
                  const Text('Day(s) of month  ', style: TextStyle(fontSize: 12, color: Odin.txtDim)),
                  SizedBox(width: 100, child: TextFormField(
                    initialValue: _monthdays,
                    style: const TextStyle(fontSize: 12),
                    decoration: const InputDecoration(hintText: '1,15', isDense: true),
                    onChanged: (v) => _monthdays = v,
                  )),
                ]),
              const SizedBox(height: 12),
              const Text('Time(s)', style: TextStyle(fontSize: 12, color: Odin.txtDim)),
              const SizedBox(height: 6),
              Wrap(spacing: 8, runSpacing: 6, children: [
                ..._times.asMap().entries.map((e) => Chip(
                      label: Text(e.value, style: const TextStyle(fontSize: 12)),
                      onDeleted: _times.length > 1 ? () => setState(() => _times.removeAt(e.key)) : null,
                      deleteIcon: const Icon(Icons.close, size: 15),
                      avatar: InkWell(onTap: () => _pickTime(e.key), child: const Icon(Icons.edit, size: 14)),
                    )),
                ActionChip(
                  label: const Text('＋ time', style: TextStyle(fontSize: 12)),
                  onPressed: () => setState(() => _times.add('12:00')),
                ),
              ]),
              const SizedBox(height: 12),
              Row(children: [
                const Text('Timezone  ', style: TextStyle(fontSize: 12, color: Odin.txtDim)),
                Expanded(child: DropdownButton<String>(
                  value: _tz,
                  isExpanded: true,
                  style: const TextStyle(fontSize: 12, color: Odin.txt),
                  dropdownColor: Odin.panelSolid,
                  items: _tzs.map((z) => DropdownMenuItem(value: z,
                      child: Text(z == 'Africa/Cairo' ? '$z (Egypt · default)' : z, style: const TextStyle(fontSize: 12)))).toList(),
                  onChanged: (v) => setState(() => _tz = v ?? 'Africa/Cairo'),
                )),
              ]),
              const SizedBox(height: 16),
              Row(mainAxisAlignment: MainAxisAlignment.end, children: [
                TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
                const SizedBox(width: 8),
                FilledButton(
                  onPressed: _busy ? null : _save,
                  style: FilledButton.styleFrom(backgroundColor: Odin.brand),
                  child: Text(_busy ? 'Saving…' : 'Save schedule'),
                ),
              ]),
            ],
          ),
        ),
      ),
    );
  }
}
