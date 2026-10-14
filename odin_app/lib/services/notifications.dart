// Public notifications facade with a conditional import: the mobile implementation
// uses flutter_local_notifications; the web implementation is a no-op (web builds
// can't import the plugin). The UI layer also shows an in-app banner regardless.
import 'notifications_stub.dart'
    if (dart.library.io) 'notifications_mobile.dart';

abstract class Notifier {
  Future<void> init();
  Future<void> show(String title, String body);

  factory Notifier() => createNotifier();
}
