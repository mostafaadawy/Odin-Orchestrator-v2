import 'biometric_stub.dart' if (dart.library.io) 'biometric_mobile.dart';

abstract class Biometric {
  Future<bool> available();
  Future<bool> authenticate(String reason);
  factory Biometric() => createBiometric();
}
