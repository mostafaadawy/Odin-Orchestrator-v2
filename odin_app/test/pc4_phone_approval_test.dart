// PC-4: secure phone approvals through the Anchor — same digest/signature as server/phone_approvals.py.
import 'dart:convert';
import 'dart:io';

import 'package:cryptography/cryptography.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:odin_app/screens/approvals.dart';
import 'package:odin_app/security/phone_approval.dart';

void main() {
  final vec = {
    'id': 'pc4-vec', 'pid': 'proj', 'kind': 'change', 'title': 'T ✓', 'summary': 'line1\nline2', 'cwd': '',
    'files': [{'action': 'edit', 'path': 'a/b.py', 'preview': 'x=1\n'}],
    'commands': [{'where': 'local', 'cmd': 'pytest -q'}],
  };

  test('digest equals the Python value for the same request (cross-language vector)', () async {
    expect(await PhoneApproval.digest(vec), '51ec9abbb5d5a9c5798a2106ab63e8b7428c311db7f6d0baa6be080347f60ea7');
  });

  test('any change to what is shown changes the digest', () async {
    final d0 = await PhoneApproval.digest(vec);
    final v2 = jsonDecode(jsonEncode(vec)) as Map<String, dynamic>;
    (v2['files'] as List)[0]['preview'] = 'rm -rf ~';
    expect(await PhoneApproval.digest(v2), isNot(d0));
  });

  test('fingerprint matches the Python grouping', () async {
    expect(await PhoneApproval.fingerprint(List<int>.generate(32, (i) => i)), '630d-cd29-66c4-3366');
  });

  test('pairing request: public key + valid proof; the seed never appears', () async {
    final st = MemorySeedStore();
    final req = await PhoneApproval.pairingRequest(st, 'phone-test1', 'Odin phone');
    final pub = SimplePublicKey(base64.decode(req['pub']), type: KeyPairType.ed25519);
    final ok = await Ed25519().verify(PhoneApproval.pairMessage('phone-test1', req['pub']),
        signature: Signature(base64.decode(req['proof']), publicKey: pub));
    expect(ok, isTrue);
    expect(jsonEncode(req).contains(st.m.values.first), isFalse);
  });

  test('signed + sealed decision: envelope carries no plaintext; cross-language check when asked', () async {
    final st = MemorySeedStore();
    final pubFile = Platform.environment['PC4_PUB_FILE'];
    final relayPub = pubFile != null
        ? (jsonDecode(File(pubFile).readAsStringSync()) as Map)['pub'].toString()
        : base64.encode(List<int>.generate(32, (i) => i + 9));
    final env = await PhoneApproval.signAndSeal(store: st, deviceId: 'phone-test1', relayPubB64: relayPub,
        approval: vec, approve: true);
    final txt = jsonEncode(env);
    for (final w in ['approve', 'phone-test1', 'digest', 'pytest']) {
      expect(txt.contains(w), isFalse);
    }
    final out = Platform.environment['PC4_OUT'];
    if (out != null) {
      File(out).writeAsStringSync(jsonEncode({'envelope': env, 'pub': await PhoneApproval.publicKeyB64(st),
          'device_id': 'phone-test1', 'approval': vec}));
    }
  });

  Future<List<bool>> pump(WidgetTester t, {required bool trusted}) async {
    final calls = <bool>[];
    await t.pumpWidget(MaterialApp(home: Scaffold(body: ApprovalActions(
        item: const {'id': 'a1', 'kind': 'change', 'title': 'x'},
        remote: true,
        phoneTrusted: trusted,
        onAct: (aid, ok) async => fail('the plain path must never be used in anchor mode'),
        onActE2E: (ok) async => calls.add(ok)))));
    return calls;
  }

  testWidgets('anchor mode, phone not trusted: no Approve, pair-first message', (t) async {
    await pump(t, trusted: false);
    expect(find.byKey(const ValueKey('pair-first')), findsOneWidget);
    expect(find.byKey(const ValueKey('approve')), findsNothing);
  });

  testWidgets('anchor mode, trusted phone: Approve/Reject go ONLY through the signed path', (t) async {
    final calls = await pump(t, trusted: true);
    await t.tap(find.byKey(const ValueKey('approve')));
    await t.tap(find.byKey(const ValueKey('reject')));
    await t.pump();
    expect(calls, [true, false]);
  });
}
