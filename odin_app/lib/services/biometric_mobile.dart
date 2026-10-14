import 'package:local_auth/local_auth.dart';

import 'biometric.dart';

class _MobileBiometric implements Biometric {
  final LocalAuthentication _a = LocalAuthentication();

  @override
  Future<bool> available() async {
    try {
      return (await _a.canCheckBiometrics) || (await _a.isDeviceSupported());
    } catch (_) {
      return false;
    }
  }

  @override
  Future<bool> authenticate(String reason) async {
    try {
      return await _a.authenticate(
        localizedReason: reason,
        options: const AuthenticationOptions(biometricOnly: false, stickyAuth: true),
      );
    } catch (_) {
      return false;
    }
  }
}

Biometric createBiometric() => _MobileBiometric();
