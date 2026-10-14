// F-41 relay: the phone seals a key to the Mac; the widget never sends a plain key and never shows Approve.
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:odin_app/screens/approvals.dart';
import 'package:odin_app/security/key_relay.dart';

void main() {
  final item = {'id': 'k1', 'kind': 'key_request', 'key_name': 'KLAVIYO_KEY_X', 'desktop_only': true, 'relay': true};

  Future<Map<String, List<dynamic>>> pump(WidgetTester t, Map<String, dynamic>? relay, {bool remote = false}) async {
    final calls = <String, List<dynamic>>{'act': [], 'key': []};
    await t.pumpWidget(MaterialApp(home: Scaffold(body: SingleChildScrollView(child: ApprovalActions(
        item: item,
        relay: relay,
        remote: remote,
        onAct: (aid, ok) async { calls['act']!.add([aid, ok]); },
        onSealedKey: (aid, name, v) async { calls['key']!.add([aid, name, v]); return 'stored'; })))));
    return calls;
  }

  testWidgets('trusted Mac key: secure field + fingerprint, no Approve, value goes only to onSealedKey', (t) async {
    final calls = await pump(t, {'pub': 'AA', 'kid': '0123456789abcdef', 'pin': 'pinned'});
    expect(find.byKey(const ValueKey('key-field')), findsOneWidget);
    expect(find.textContaining('0123-4567-89ab-cdef'), findsOneWidget);
    expect(find.byKey(const ValueKey('approve')), findsNothing);
    await t.enterText(find.byKey(const ValueKey('key-field')), 'sk-test-123');
    await t.tap(find.byKey(const ValueKey('send-key')));
    await t.pumpAndSettle();
    expect(calls['key'], [['k1', 'KLAVIYO_KEY_X', 'sk-test-123']]);
    expect(calls['act'], isEmpty);
    expect(find.text('sk-test-123'), findsNothing);   // field cleared
  });

  testWidgets('changed fingerprint: no field, blocked message', (t) async {
    await pump(t, {'pub': 'AA', 'kid': 'ffff', 'pin': 'mismatch'});
    expect(find.byKey(const ValueKey('relay-mismatch')), findsOneWidget);
    expect(find.byType(TextField), findsNothing);
  });

  testWidgets('no relay: desktop-only (F-41 interim kept)', (t) async {
    await pump(t, null);
    expect(find.byKey(const ValueKey('desktop-only')), findsOneWidget);
    expect(find.byType(TextField), findsNothing);
  });

  testWidgets('anchor mode: no Reject call path (approvals are desktop-only there)', (t) async {
    await pump(t, null, remote: true);
    expect(find.byKey(const ValueKey('reject')), findsNothing);
  });

  test('seal: envelope has no plaintext, correct kid; cross-language vector when asked', () async {
    final pubFile = Platform.environment['F41_PUB_FILE'];
    final pub = pubFile != null
        ? (jsonDecode(File(pubFile).readAsStringSync()) as Map)['pub'].toString()
        : base64.encode(List<int>.generate(32, (i) => i + 9));
    const value = 'sk-xlang-SECRET-42';
    final env = await KeyRelay.seal(pub, value, 'f41-xlang', 'xlang_key');
    final s = jsonEncode(env);
    expect(s.contains(value), isFalse);
    expect(s.contains(base64.encode(utf8.encode(value))), isFalse);
    expect(env['kid'], await KeyRelay.kidOf(base64.decode(pub)));
    expect(env['alg'], KeyRelay.alg);
    expect(KeyRelay.checkPin(null, 'a'), 'new');
    expect(KeyRelay.checkPin('a', 'a'), 'pinned');
    expect(KeyRelay.checkPin('a', 'b'), 'mismatch');
    final out = Platform.environment['F41_OUT'];
    if (out != null) File(out).writeAsStringSync(s);
  });
}
