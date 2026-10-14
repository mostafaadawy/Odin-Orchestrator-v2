// F-41 — end-to-end encrypted key relay (phone -> Anchor -> Mac). Mirrors server/key_relay.py exactly:
// ephemeral X25519 -> HKDF-SHA256 (salt = epk || macPub, info "odin-key-relay-v1") -> AES-256-GCM,
// AAD = "odin-key-relay|v1|<approval id>|<KEY_NAME>". The Anchor only ever sees the sealed envelope.
// The phone PINS the Mac's key fingerprint on first use; a changed fingerprint blocks sending.
import 'dart:convert';

import 'package:cryptography/cryptography.dart';

class KeyRelay {
  static const alg = 'X25519-HKDF-SHA256-AES256GCM-v1';
  static const _info = 'odin-key-relay-v1';

  static Future<String> kidOf(List<int> pub) async =>
      (await Sha256().hash(pub)).bytes.take(8).map((b) => b.toRadixString(16).padLeft(2, '0')).join();

  static List<int> aad(String aid, String name) =>
      utf8.encode('odin-key-relay|v1|$aid|${name.trim().toUpperCase()}');

  /// Seal [value] to the Mac public key [pubB64]. Returns the envelope map (no plaintext inside).
  static Future<Map<String, dynamic>> seal(String pubB64, String value, String aid, String name) async {
    final pub = base64.decode(pubB64);
    if (pub.length != 32) throw ArgumentError('bad Mac public key');
    final x = X25519();
    final eph = await x.newKeyPair();
    final epk = (await eph.extractPublicKey()).bytes;
    final shared = await x.sharedSecretKey(
        keyPair: eph, remotePublicKey: SimplePublicKey(pub, type: KeyPairType.x25519));
    final k = await Hkdf(hmac: Hmac.sha256(), outputLength: 32)
        .deriveKey(secretKey: shared, nonce: [...epk, ...pub], info: utf8.encode(_info));
    final aes = AesGcm.with256bits();
    final nonce = aes.newNonce();
    final box = await aes.encrypt(utf8.encode(value), secretKey: k, nonce: nonce, aad: aad(aid, name));
    return {
      'v': 1,
      'alg': alg,
      'kid': await kidOf(pub),
      'epk': base64.encode(epk),
      'nonce': base64.encode(nonce),
      'ct': base64.encode([...box.cipherText, ...box.mac.bytes]),
    };
  }

  /// Trust-on-first-use pin. Returns 'pinned' (matches), 'new' (first sight, now pinned) or 'mismatch'.
  static String checkPin(String? pinned, String kid) {
    if (pinned == null || pinned.isEmpty) return 'new';
    return pinned == kid ? 'pinned' : 'mismatch';
  }

  /// Human-checkable fingerprint, e.g. "3f2a-91c0-77de-0b14" (compare with the desktop).
  static String pretty(String kid) =>
      [for (var i = 0; i < kid.length; i += 4) kid.substring(i, (i + 4).clamp(0, kid.length))].join('-');
}
