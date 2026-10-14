// Minimal smoke test so `flutter analyze` / `flutter test` stays clean.
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('sanity', () {
    expect(1 + 1, 2);
  });
}
