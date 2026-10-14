import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_state.dart';
import '../theme.dart';

/// 🔔 A bell icon that SHAKES briefly when [pulse] is true (a new notification arrived).
class NotifShakeBell extends StatefulWidget {
  final bool pulse;
  final VoidCallback onTap;
  const NotifShakeBell({super.key, required this.pulse, required this.onTap});
  @override
  State<NotifShakeBell> createState() => NotifShakeBellState();
}

class NotifShakeBellState extends State<NotifShakeBell> with SingleTickerProviderStateMixin {
  late final AnimationController _c =
      AnimationController(vsync: this, duration: const Duration(milliseconds: 600));
  @override
  void didUpdateWidget(covariant NotifShakeBell old) {
    super.didUpdateWidget(old);
    if (widget.pulse && !old.pulse) _c.repeat();
    if (!widget.pulse && old.pulse) { _c.stop(); _c.reset(); }
  }
  @override
  void dispose() { _c.dispose(); super.dispose(); }
  @override
  Widget build(BuildContext context) {
    return IconButton(
      tooltip: 'Notifications — recurring & scheduled work',
      visualDensity: VisualDensity.compact,
      constraints: const BoxConstraints(minWidth: 38, minHeight: 38),
      onPressed: widget.onTap,
      icon: AnimatedBuilder(
        animation: _c,
        builder: (_, child) {
          final a = widget.pulse ? math.sin(_c.value * math.pi * 6) * 0.28 : 0.0;
          return Transform.rotate(angle: a, child: child);
        },
        child: Icon(Icons.notifications_active_outlined,
            color: widget.pulse ? Odin.danger : null),
      ),
    );
  }
}

/// Show the live notifications panel (read · mark read · mark all · tap to redirect to the project).
Future<void> showNotifications(BuildContext context) {
  context.read<AppState>().refreshNotifs();
  return showGeneralDialog(
    context: context,
    barrierDismissible: true,
    barrierLabel: 'notifications',
    barrierColor: Colors.black.withValues(alpha: 0.45),
    transitionDuration: const Duration(milliseconds: 200),
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
              child: const _NotifPanel(),
            ),
          ),
        ),
      );
    },
  );
}

class _NotifPanel extends StatelessWidget {
  const _NotifPanel();
  @override
  Widget build(BuildContext context) {
    final w = MediaQuery.of(context).size.width;
    return Material(
      color: Colors.transparent,
      child: Consumer<AppState>(
        builder: (context, s, _) {
          final items = s.notifs;
          return Container(
            width: math.min(400.0, w - 24),
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
                  padding: const EdgeInsets.fromLTRB(15, 12, 8, 12),
                  decoration: const BoxDecoration(border: Border(bottom: BorderSide(color: Odin.stroke))),
                  child: Row(
                    children: [
                      const Icon(Icons.notifications_active_outlined, size: 18, color: Odin.brand),
                      const SizedBox(width: 8),
                      const Expanded(child: Text('Notifications', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700))),
                      if (s.unreadNotifs > 0)
                        TextButton(
                          onPressed: () => s.markAllNotifs(),
                          child: const Text('Mark all read', style: TextStyle(fontSize: 12)),
                        ),
                      InkWell(onTap: () => Navigator.pop(context), child: const Icon(Icons.close, size: 18, color: Odin.txtDim)),
                    ],
                  ),
                ),
                Flexible(
                  child: items.isEmpty
                      ? const Padding(
                          padding: EdgeInsets.all(28),
                          child: Text('No notifications yet.\nScheduled & recurring projects will report here when they run.',
                              textAlign: TextAlign.center, style: TextStyle(fontSize: 12.5, color: Odin.txtDim, height: 1.5)))
                      : ListView.separated(
                          shrinkWrap: true,
                          padding: const EdgeInsets.symmetric(vertical: 4),
                          itemCount: items.length,
                          separatorBuilder: (_, __) => const Divider(height: 1, color: Odin.stroke),
                          itemBuilder: (_, i) => _tile(context, s, items[i]),
                        ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _tile(BuildContext context, AppState s, Map<String, dynamic> n) {
    final read = n['read'] == true;
    final sev = (n['severity'] ?? 'info').toString();
    final color = sev == 'critical' ? Odin.danger : (sev == 'attention' ? Odin.warn : Odin.brand);
    return InkWell(
      onTap: () async {
        if (!read) await s.markNotif(n['id']?.toString() ?? '');
        final pid = (n['pid'] ?? '').toString();
        if (pid.isNotEmpty) {
          if (context.mounted) Navigator.pop(context);
          s.openProjectById(pid); // redirect to the project
        }
      },
      child: Container(
        color: read ? Colors.transparent : color.withValues(alpha: 0.06),
        padding: const EdgeInsets.fromLTRB(14, 10, 12, 10),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(width: 8, height: 8, margin: const EdgeInsets.only(top: 5, right: 9),
                decoration: BoxDecoration(color: read ? Odin.stroke : color, shape: BoxShape.circle)),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('${n['icon'] ?? '🔔'}  ${n['title'] ?? ''}',
                      style: TextStyle(fontSize: 13, fontWeight: read ? FontWeight.w500 : FontWeight.w700)),
                  if ((n['body'] ?? '').toString().isNotEmpty)
                    Padding(padding: const EdgeInsets.only(top: 2),
                        child: Text(n['body'].toString(), style: const TextStyle(fontSize: 11.5, color: Odin.txtDim, height: 1.4))),
                  if ((n['project'] ?? '').toString().isNotEmpty)
                    Padding(padding: const EdgeInsets.only(top: 3),
                        child: Text('${n['project']}  ·  tap to open', style: const TextStyle(fontSize: 10.5, color: Odin.txtFaint))),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
