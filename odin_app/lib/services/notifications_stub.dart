import 'notifications.dart';

// Web (and any platform without dart:io): no OS notifications. The in-app banner
// in the UI covers the user-visible part, so this is intentionally a no-op.
class _WebNotifier implements Notifier {
  @override
  Future<void> init() async {}
  @override
  Future<void> show(String title, String body) async {}
}

Notifier createNotifier() => _WebNotifier();
