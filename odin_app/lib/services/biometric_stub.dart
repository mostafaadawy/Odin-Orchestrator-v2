import 'biometric.dart';

class _WebBiometric implements Biometric {
  @override
  Future<bool> available() async => false;
  @override
  Future<bool> authenticate(String reason) async => false;
}

Biometric createBiometric() => _WebBiometric();
