import 'package:flutter_local_notifications/flutter_local_notifications.dart';

import 'notifications.dart';

// Android + iOS: real local notifications via flutter_local_notifications.
class _MobileNotifier implements Notifier {
  final FlutterLocalNotificationsPlugin _p = FlutterLocalNotificationsPlugin();
  bool _ready = false;

  @override
  Future<void> init() async {
    const android = AndroidInitializationSettings('@mipmap/ic_launcher');
    const ios = DarwinInitializationSettings();
    await _p.initialize(
      const InitializationSettings(android: android, iOS: ios),
    );
    _ready = true;
  }

  @override
  Future<void> show(String title, String body) async {
    if (!_ready) await init();
    const details = NotificationDetails(
      android: AndroidNotificationDetails(
        'anchor_updates',
        'Anchor updates',
        channelDescription: 'New finished or failed Anchor Connect requests',
        importance: Importance.high,
        priority: Priority.high,
      ),
      iOS: DarwinNotificationDetails(),
    );
    await _p.show(
      DateTime.now().millisecondsSinceEpoch ~/ 1000,
      title,
      body,
      details,
    );
  }
}

Notifier createNotifier() => _MobileNotifier();
