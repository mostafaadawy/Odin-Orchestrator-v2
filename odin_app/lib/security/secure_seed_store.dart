// PC-4: the phone's Ed25519 seed lives in the OS secure store (iOS Keychain / Android Keystore), never in
// shared preferences and never sent anywhere.
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'phone_approval.dart';

class SecureSeedStore implements SeedStore {
  static const _s = FlutterSecureStorage();
  @override
  Future<String?> read(String key) => _s.read(key: key);
  @override
  Future<void> write(String key, String value) => _s.write(key: key, value: value);
}
