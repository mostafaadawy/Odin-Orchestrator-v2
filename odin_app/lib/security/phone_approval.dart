// PC-4 — secure phone approvals through the Anchor. Mirrors server/phone_approvals.py exactly:
//  * this phone owns an Ed25519 key (seed kept in the OS secure store); only the PUBLIC key leaves, in a pairing
//    request the owner must TRUST on the desktop after comparing the fingerprint shown on both screens;
//  * a decision is SIGNED over a digest of the exact request the phone shows (computed HERE from what is shown),
//    then SEALED to the Mac's relay key (F-41 envelope, AAD bound to the approval id) — the Anchor sees ciphertext;
//  * fresh (timestamp) + one-time nonce, so a captured decision can never be replayed.
import 'dart:convert';
import 'dart:math';

import 'package:cryptography/cryptography.dart';

import 'key_relay.dart';

/// Where the phone keeps its private seed. The app uses the OS secure store; tests pass a memory store.
abstract class SeedStore {
  Future<String?> read(String key);
  Future<void> write(String key, String value);
}

class MemorySeedStore implements SeedStore {
  final Map<String, String> m = {};
  @override
  Future<String?> read(String key) async => m[key];
  @override
  Future<void> write(String key, String value) async => m[key] = value;
}

class PhoneApproval {
  static const envelopeName = 'APPROVAL';
  static const _seedKey = 'odin.phone.ed25519.seed';

  static Future<String> _h(Object? s) async =>
      _hex((await Sha256().hash(utf8.encode(s == null ? '' : s.toString()))).bytes);
  static String _hex(List<int> b) => b.map((x) => x.toRadixString(16).padLeft(2, '0')).join();

  /// The exact content the owner approves (same algorithm as phone_approvals.digest).
  static Future<String> digest(Map<String, dynamic> a) async {
    final files = <String>[];
    for (final f in (a['files'] is List ? a['files'] as List : const [])) {
      if (f is Map) files.add('${await _h(f['action'] ?? '')}:${await _h(f['path'] ?? '')}:${await _h(f['preview'] ?? '')}');
    }
    final cmds = <String>[];
    for (final c in (a['commands'] is List ? a['commands'] as List : const [])) {
      if (c is Map) cmds.add('${await _h(c['where'] ?? '')}:${await _h(c['cmd'] ?? '')}');
    }
    final parts = [
      'odin-approval', 'v1', '${a['id'] ?? ''}', await _h(a['pid'] ?? ''), await _h(a['kind'] ?? ''),
      await _h(a['title'] ?? ''), await _h(a['summary'] ?? ''), await _h(a['cwd'] ?? ''),
      await _h(files.join('\n')), await _h(cmds.join('\n')),
    ];
    return _hex((await Sha256().hash(utf8.encode(parts.join('|')))).bytes);
  }

  static List<int> sigMessage(String aid, String decision, String dg, String nonce, int ts, String deviceId, String note) =>
      utf8.encode('odin-approval-sig|v1|$aid|$decision|$dg|$nonce|$ts|$deviceId|$note');

  static List<int> pairMessage(String deviceId, String pubB64) => utf8.encode('odin-phone-pair|v1|$deviceId|$pubB64');

  static Future<String> fingerprint(List<int> pubRaw) async {
    final k = _hex((await Sha256().hash(pubRaw)).bytes).substring(0, 16);
    return [for (var i = 0; i < 16; i += 4) k.substring(i, i + 4)].join('-');
  }

  static Future<SimpleKeyPair> keyPair(SeedStore store) async {
    var seed = await store.read(_seedKey);
    if (seed == null || seed.isEmpty) {
      final r = Random.secure();
      seed = base64.encode(List<int>.generate(32, (_) => r.nextInt(256)));
      await store.write(_seedKey, seed);
    }
    return Ed25519().newKeyPairFromSeed(base64.decode(seed));
  }

  static Future<String> publicKeyB64(SeedStore store) async =>
      base64.encode((await (await keyPair(store)).extractPublicKey()).bytes);

  /// The pairing REQUEST (public key + proof of possession). Trust is granted on the desktop only.
  static Future<Map<String, dynamic>> pairingRequest(SeedStore store, String deviceId, String name) async {
    final kp = await keyPair(store);
    final pub = base64.encode((await kp.extractPublicKey()).bytes);
    final sig = await Ed25519().sign(pairMessage(deviceId, pub), keyPair: kp);
    return {'device_id': deviceId, 'name': name, 'pub': pub, 'proof': base64.encode(sig.bytes)};
  }

  static String newNonce() {
    final r = Random.secure();
    return _hex(List<int>.generate(12, (_) => r.nextInt(256)));
  }

  /// Sign the decision over the digest of [approval] (as shown) and seal it to the Mac relay key [relayPubB64].
  static Future<Map<String, dynamic>> signAndSeal({
    required SeedStore store,
    required String deviceId,
    required String relayPubB64,
    required Map<String, dynamic> approval,
    required bool approve,
    String note = '',
    int? ts,
    String? nonce,
  }) async {
    final aid = '${approval['id'] ?? ''}';
    final decision = approve ? 'approve' : 'reject';
    final dg = await digest(approval);
    final n = nonce ?? newNonce();
    final t = ts ?? DateTime.now().millisecondsSinceEpoch ~/ 1000;
    final kp = await keyPair(store);
    final sig = await Ed25519().sign(sigMessage(aid, decision, dg, n, t, deviceId, note), keyPair: kp);
    final inner = {'device_id': deviceId, 'decision': decision, 'digest': dg, 'nonce': n, 'ts': t, 'note': note,
                   'sig': base64.encode(sig.bytes)};
    return KeyRelay.seal(relayPubB64, jsonEncode(inner), aid, envelopeName);
  }
}
