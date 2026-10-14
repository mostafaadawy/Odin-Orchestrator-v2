import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../security/key_relay.dart';
import '../security/phone_approval.dart';
import '../security/secure_seed_store.dart';

import '../state/app_state.dart';
import '../theme.dart';
import '../widgets.dart';

class ApprovalsScreen extends StatefulWidget {
  const ApprovalsScreen({super.key});
  @override
  State<ApprovalsScreen> createState() => _ApprovalsScreenState();
}

class _ApprovalsScreenState extends State<ApprovalsScreen> {
  List<Map<String, dynamic>> _items = [];
  Map<String, dynamic>? _relay;   // F-41: {pub, kid, pin}
  Map<String, dynamic>? _phone;   // PC-4: {device_id, fingerprint, status: none|pending|trusted|revoked}
  final SeedStore _seeds = SecureSeedStore();
  bool _loading = true;
  String? _err;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _err = null;
    });
    try {
      final api = context.read<AppState>().api;
      _items = await api.approvals();
      _relay = await _loadRelay(api);
      if (api.anchorMode) _phone = await _loadPhone(api);
    } catch (e) {
      _err = '$e';
    }
    if (mounted) setState(() => _loading = false);
  }

  /// F-41: fetch the Mac's public key, check its fingerprint, and pin it on first use.
  Future<Map<String, dynamic>?> _loadRelay(dynamic api) async {
    try {
      final r = Map<String, dynamic>.from(await api.relayPubKey());
      final pub = (r['pub'] ?? '').toString();
      if (pub.isEmpty) return null;
      final kid = await KeyRelay.kidOf(base64.decode(pub));
      final prefs = await SharedPreferences.getInstance();
      var pin = (r['kid']?.toString() == kid) ? KeyRelay.checkPin(prefs.getString('odin.relay.kid'), kid) : 'mismatch';
      if (pin == 'new') {
        await prefs.setString('odin.relay.kid', kid);
        pin = 'pinned';
      }
      return {'pub': pub, 'kid': kid, 'pin': pin};
    } catch (_) {
      return null;
    }
  }

  /// PC-4: this phone's id + fingerprint, and whether the Mac has it as TRUSTED (owner confirmed on the desktop).
  Future<Map<String, dynamic>?> _loadPhone(dynamic api) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      var id = prefs.getString('odin.phone.device_id') ?? '';
      if (id.isEmpty) {
        id = 'phone-${PhoneApproval.newNonce().substring(0, 12)}';
        await prefs.setString('odin.phone.device_id', id);
      }
      final fp = await PhoneApproval.fingerprint(base64.decode(await PhoneApproval.publicKeyB64(_seeds)));
      var status = 'none';
      for (final d in await api.phoneDevices()) {
        if (d['device_id']?.toString() == id && d['fingerprint']?.toString() == fp) status = d['status'].toString();
      }
      return {'device_id': id, 'fingerprint': fp, 'status': status};
    } catch (_) {
      return null;
    }
  }

  Future<void> _pair() async {
    final p = _phone;
    if (p == null) return;
    final api = context.read<AppState>().api;
    final req = await PhoneApproval.pairingRequest(_seeds, p['device_id'].toString(), 'Odin phone');
    final res = await api.pairPhone(req);
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(
        '$res — on your Mac open Settings ▸ Paired phones, check fingerprint ${p['fingerprint']} and press Trust.')));
    _load();
  }

  /// PC-4: sign the decision over what this screen shows, seal it to the Mac, send it through the Anchor.
  Future<void> _actE2E(Map<String, dynamic> item, bool approve) async {
    final r = _relay, p = _phone;
    final api = context.read<AppState>().api;
    String res;
    if (r == null || r['pin'] != 'pinned') {
      res = 'refused here: no trusted Mac key';
    } else if (p == null || p['status'] != 'trusted') {
      res = 'refused here: this phone is not trusted on the Mac yet';
    } else {
      final ok = await showDialog<bool>(context: context, builder: (c) => AlertDialog(
            title: Text(approve ? 'Approve this request?' : 'Reject this request?'),
            content: Text('${item['title'] ?? ''}\n${(item['files'] as List?)?.length ?? 0} file(s), '
                '${(item['commands'] as List?)?.length ?? 0} command(s).\nSigned by this phone (${p['fingerprint']}) '
                'and encrypted for your Mac (${KeyRelay.pretty(r['kid'].toString())}).'),
            actions: [
              TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancel')),
              FilledButton(onPressed: () => Navigator.pop(c, true), child: Text(approve ? 'Approve' : 'Reject')),
            ]));
      if (ok != true) return;
      final env = await PhoneApproval.signAndSeal(store: _seeds, deviceId: p['device_id'].toString(),
          relayPubB64: r['pub'].toString(), approval: item, approve: approve);
      res = await api.sendApprovalE2E(item['id'].toString(), env);
    }
    if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(res)));
    _load();
  }

  Future<String> _sealed(String aid, String name, String value) async {
    final r = _relay;
    if (r == null || r['pin'] != 'pinned') return 'refused: no trusted Mac key';
    final api = context.read<AppState>().api;
    final env = await KeyRelay.seal(r['pub'].toString(), value, aid, name);   // plain value never leaves
    final res = await api.sendSealedKey(aid, name, env);
    _load();
    return res;
  }

  Future<void> _act(String aid, bool approve) async {
    final s = context.read<AppState>();
    if (approve) {
      await s.api.approveChange(aid);
    } else {
      await s.api.rejectChange(aid);
    }
    _load();
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Row(
            children: [
              const Expanded(child: SectionTitle('Approval center')),
              IconButton(onPressed: _load, icon: const Icon(Icons.refresh)),
            ],
          ),
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 6),
            child: Text('Nothing touches your code, config, or the VM until you approve it here.',
                style: TextStyle(fontSize: 12, color: Odin.txtDim)),
          ),
          if (_phone != null) PhonePairCard(phone: _phone!, onPair: _pair),
          if (_loading) const Padding(padding: EdgeInsets.all(30), child: Center(child: CircularProgressIndicator(color: Odin.brand))),
          if (_err != null) Text(_err!, style: const TextStyle(color: Odin.danger, fontSize: 12)),
          if (!_loading && _items.isEmpty && _err == null) const EmptyHint('No pending approvals.'),
          ..._items.map((a) => GlassCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Pill(a['kind']?.toString() ?? a['type']?.toString() ?? 'change',
                            color: Odin.warn, borderColor: Odin.warn.withValues(alpha: 0.4)),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text('${a['project'] ?? ''} · ${a['summary'] ?? a['title'] ?? a['id'] ?? ''}',
                              style: const TextStyle(fontSize: 13)),
                        ),
                      ],
                    ),
                    if ((a['detail'] ?? a['description'] ?? '').toString().isNotEmpty) ...[
                      const SizedBox(height: 6),
                      Text((a['detail'] ?? a['description']).toString(),
                          style: const TextStyle(fontSize: 12, color: Odin.txtDim)),
                    ],
                    const SizedBox(height: 10),
                    ApprovalActions(item: a, onAct: _act, relay: _relay, onSealedKey: _sealed,
                        remote: context.read<AppState>().api.anchorMode,
                        phoneTrusted: _phone?['status'] == 'trusted',
                        onActE2E: (approve) => _actE2E(a, approve)),
                  ],
                ),
              )),
        ],
      ),
    );
  }
}


/// F-41 (owner 2026-10-11): a KEY REQUEST is never answered with Approve and never sends a plain key.
/// With a trusted (pinned) Mac key the phone shows a secure field whose value is SEALED to the Mac
/// (KeyRelay.seal) before it leaves; the Anchor only relays ciphertext. Without one — or if the Mac key's
/// fingerprint changed — the phone shows "enter this key on the desktop". Reject (sends no key) stays.
class ApprovalActions extends StatelessWidget {
  const ApprovalActions(
      {super.key, required this.item, required this.onAct, this.relay, this.onSealedKey, this.remote = false,
      this.phoneTrusted = false, this.onActE2E});
  final Map<String, dynamic> item;
  final Future<void> Function(String aid, bool approve) onAct;
  final Map<String, dynamic>? relay;   // {pub, kid, pin: pinned|mismatch}
  final Future<String> Function(String aid, String name, String value)? onSealedKey;
  final bool remote;                   // Anchor mode: decisions go signed + sealed (PC-4), never plain
  final bool phoneTrusted;             // PC-4: this phone is paired AND trusted on the Mac
  final Future<void> Function(bool approve)? onActE2E;

  static bool isKeyRequest(Map<String, dynamic> a) =>
      a['kind']?.toString() == 'key_request' || a['desktop_only'] == true;

  @override
  Widget build(BuildContext context) {
    final aid = item['id'].toString();
    final reject = OutlinedButton.icon(
      key: const ValueKey('reject'),
      style: OutlinedButton.styleFrom(foregroundColor: Odin.danger),
      onPressed: () => onAct(aid, false),
      icon: const Icon(Icons.close, size: 16),
      label: const Text('Reject'),
    );
    if (isKeyRequest(item)) {
      final name = (item['key_name'] ?? '').toString();
      final r = relay;
      final trusted = r != null && onSealedKey != null && r['pin'] == 'pinned' && name.isNotEmpty;
      return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        if (trusted)
          KeyRelayField(aid: aid, name: name, kid: r['kid'].toString(), onSend: onSealedKey!)
        else if (r != null && r['pin'] == 'mismatch')
          const Text("Your Mac's key fingerprint changed. Keys are blocked on this phone until you check "
              'the fingerprint on the desktop and re-pair.',
              key: ValueKey('relay-mismatch'), style: TextStyle(fontSize: 13, color: Odin.danger))
        else
          Text('Enter this key on the desktop${name.isNotEmpty ? ' ($name)' : ''}. '
              'For your safety, the phone never sends keys in plain text.',
              key: const ValueKey('desktop-only'),
              style: const TextStyle(fontSize: 13, color: Odin.warn)),
        const SizedBox(height: 8),
        if (!remote) reject,
      ]);
    }
    if (remote && (!phoneTrusted || onActE2E == null)) {
      return const Text('Pair this phone and trust it on your Mac (Settings ▸ Paired phones) to approve from here.',
          key: ValueKey('pair-first'), style: TextStyle(fontSize: 13, color: Odin.warn));
    }
    if (remote) {
      return Row(children: [
        FilledButton.icon(
          key: const ValueKey('approve'),
          style: FilledButton.styleFrom(backgroundColor: Odin.ok),
          onPressed: () => onActE2E!(true),
          icon: const Icon(Icons.verified_user, size: 16),
          label: const Text('Approve (signed)'),
        ),
        const SizedBox(width: 8),
        OutlinedButton.icon(
          key: const ValueKey('reject'),
          style: OutlinedButton.styleFrom(foregroundColor: Odin.danger),
          onPressed: () => onActE2E!(false),
          icon: const Icon(Icons.close, size: 16),
          label: const Text('Reject (signed)'),
        ),
      ]);
    }
    return Row(children: [
      FilledButton.icon(
        key: const ValueKey('approve'),
        style: FilledButton.styleFrom(backgroundColor: Odin.ok),
        onPressed: () => onAct(aid, true),
        icon: const Icon(Icons.check, size: 16),
        label: const Text('Approve'),
      ),
      const SizedBox(width: 8),
      reject,
    ]);
  }
}


/// F-41: the phone's secure key field. The value is handed ONLY to [onSend], which seals it to the Mac.
class KeyRelayField extends StatefulWidget {
  const KeyRelayField({super.key, required this.aid, required this.name, required this.kid, required this.onSend});
  final String aid, name, kid;
  final Future<String> Function(String aid, String name, String value) onSend;
  @override
  State<KeyRelayField> createState() => _KeyRelayFieldState();
}

class _KeyRelayFieldState extends State<KeyRelayField> {
  final _c = TextEditingController();
  String _msg = '';
  bool _busy = false;

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final v = _c.text.trim();
    if (v.isEmpty || _busy) return;
    setState(() => _busy = true);
    String res;
    try {
      res = await widget.onSend(widget.aid, widget.name, v);
    } catch (e) {
      res = 'error';
    }
    _c.clear();
    if (mounted) setState(() { _busy = false; _msg = res; });
  }

  @override
  Widget build(BuildContext context) {
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text('Encrypted for your Mac — fingerprint ${KeyRelay.pretty(widget.kid)}. The Anchor only relays ciphertext.',
          key: const ValueKey('relay-fp'), style: const TextStyle(fontSize: 12, color: Odin.txtDim)),
      const SizedBox(height: 6),
      TextField(
        key: const ValueKey('key-field'),
        controller: _c,
        obscureText: true,
        autocorrect: false,
        enableSuggestions: false,
        decoration: InputDecoration(labelText: widget.name, isDense: true),
      ),
      const SizedBox(height: 6),
      FilledButton.icon(
        key: const ValueKey('send-key'),
        onPressed: _busy ? null : _send,
        icon: const Icon(Icons.lock, size: 16),
        label: const Text('Send encrypted'),
      ),
      if (_msg.isNotEmpty) Text(_msg, key: const ValueKey('send-result'), style: const TextStyle(fontSize: 12)),
    ]);
  }
}


/// PC-4: this phone's pairing state. Pairing sends only the PUBLIC key; the owner trusts it on the desktop after
/// comparing this fingerprint with the one the desktop shows.
class PhonePairCard extends StatelessWidget {
  const PhonePairCard({super.key, required this.phone, required this.onPair});
  final Map<String, dynamic> phone;
  final Future<void> Function() onPair;
  @override
  Widget build(BuildContext context) {
    final st = phone['status']?.toString() ?? 'none';
    final fp = phone['fingerprint']?.toString() ?? '';
    final txt = {
      'trusted': 'This phone is trusted by your Mac ($fp). Decisions are signed here and encrypted for the Mac.',
      'pending': 'Waiting for you to trust this phone on the Mac: Settings ▸ Paired phones ▸ fingerprint $fp ▸ Trust.',
      'revoked': 'This phone was revoked on the Mac. Pair again and trust it on the desktop to approve from here.',
    }[st] ?? 'Pair this phone to approve requests from here. Fingerprint: $fp';
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(children: [
        Icon(st == 'trusted' ? Icons.verified_user : Icons.phonelink_lock, size: 18,
            color: st == 'trusted' ? Odin.ok : Odin.warn),
        const SizedBox(width: 8),
        Expanded(child: Text(txt, key: const ValueKey('phone-pair-state'), style: const TextStyle(fontSize: 12))),
        if (st != 'trusted' && st != 'pending')
          TextButton(key: const ValueKey('pair-phone'), onPressed: onPair, child: const Text('Pair')),
      ]),
    );
  }
}
