"""Step F (F-41 relay) source edits — idempotent. Run from the copy root."""
import re, pathlib
def edit(p, old, new, count=1):
    s = pathlib.Path(p).read_text()
    if new in s: print('skip', p); return
    assert s.count(old) == count, (p, old[:60], s.count(old))
    pathlib.Path(p).write_text(s.replace(old, new)); print('ok', p)

# --- brain: secret_store gains the encrypted entry point + channel
edit('server/secret_store.py', 'def provide_key(aid: str, value: str, name: str = "", service: str = "") -> dict:',
     'def provide_key(aid: str, value: str, name: str = "", service: str = "", channel: str = "secure-field") -> dict:')
edit('server/secret_store.py', '''    approvals.decide(aid, True, f"key {name} provided by the owner in the app (value stored by the app, not shown)",
                     by="owner", channel="secure-field")''',
     '''    _how = "on the phone through the encrypted relay" if channel == "phone" else "in the app"
    approvals.decide(aid, True, f"key {name} provided by the owner {_how} (value stored by the app, not shown)",
                     by="owner", channel=channel)''')
edit('server/secret_store.py', 'KEY_REQ_RE = re.compile(', '''def provide_key_e2e(aid: str, envelope: dict, name: str = "") -> dict:
    """F-41: the phone's sealed envelope (relayed by the Anchor as ciphertext) is opened HERE, on the Mac, and
    the value goes down the same path as the desktop field. Errors never contain the value."""
    import approvals, key_relay
    a = approvals.get(aid)
    if not a or a.get("kind") != "key_request" or a.get("status") != "pending":
        return {"ok": False, "error": "no open key request with this id"}
    name = (name or a.get("key_name") or "").strip().upper()
    if not NAME_RE.match(name):
        return {"ok": False, "error": "the key name must be UPPER_SNAKE_CASE, e.g. KLAVIYO_KEY_BRAND2"}
    try:
        value = key_relay.open_envelope(envelope, aid, name)
    except key_relay.RelayError as e:
        return {"ok": False, "error": f"encrypted key refused: {e}"}
    return provide_key(aid, value, name=name, channel="phone")


KEY_REQ_RE = re.compile(''')

# --- brain routes
edit('server/api_v2.py', '''    def approvals_list(pid: str = "", all: int = 0):
        import approvals
        rows = approvals.list_for(pid or None) if all else approvals.list_pending(pid or None)''',
     '''    def approvals_list(pid: str = "", all: int = 0, kind: str = ""):
        import approvals
        rows = approvals.list_for(pid or None) if all else approvals.list_pending(pid or None)
        if kind:   # F-41: the poller mirrors ONLY key requests to the Anchor (?kind=key_request)
            rows = [x for x in rows if x.get("kind") == kind]''')
edit('server/api_v2.py', '''                x["desktop_only"] = True
                x["detail"] = "Enter this key on the desktop. The phone never sends keys."''',
     '''                x["desktop_only"] = True   # kept for phones without the relay (F-41 interim behaviour)
                x["relay"] = True          # F-41: phones with the relay may seal the key to the Mac
                x["detail"] = ("Enter this key on the desktop, or on the phone through the end-to-end encrypted "
                               "relay. The phone never sends a key in plain text.")''')
edit('server/api_v2.py', '''    @r.post("/approvals/{aid}/approve")''', '''    @r.get("/secrets/relay-pubkey")
    def secrets_relay_pubkey():
        """F-41: the Mac's PUBLIC relay key + fingerprint (mirrored to the Anchor). Never the private key."""
        import key_relay
        return key_relay.public_info()

    @r.post("/secrets/project-key-e2e")
    def secrets_project_key_e2e(body: dict | None = None):
        """F-41: a SEALED key from the phone (via the Anchor). Plain values are refused on this path."""
        import secret_store
        b = body or {}
        if "value" in b:
            return {"ok": False, "error": "plain values are not accepted on the relay path"}
        env = b.get("envelope")
        return secret_store.provide_key_e2e(str(b.get("aid", "")), env if isinstance(env, dict) else {},
                                            name=str(b.get("name", "")))

    @r.post("/approvals/{aid}/approve")''')

# --- poller: relay the sealed envelope; mirror the public key
edit('server/local_poller_http.py', '''    return "unknown command"''', '''    if kind == "key_e2e":
        # F-41: the phone sealed a key to this Mac's public key; the Anchor only carried ciphertext. Opened on
        # the brain. The reply never contains the value.
        env = payload.get("envelope") if isinstance(payload.get("envelope"), dict) else {}
        try:
            r = _brain_post("/secrets/project-key-e2e", {"aid": payload.get("aid", ""),
                                                        "name": payload.get("name", ""), "envelope": env})
            return f"key {r.get('name', '')} stored on the Mac (encrypted relay)" if r.get("ok") \\
                else f"key_e2e refused: {r.get('error', '')}"
        except Exception as e:
            return f"key_e2e error: {type(e).__name__}"
    return "unknown command"''')
edit('server/local_poller_http.py', '''                          ("ui_connectors", "/ui/connectors")):''',
     '''                          ("ui_connectors", "/ui/connectors"),
                          ("relay_pubkey", "/secrets/relay-pubkey"),   # F-41: phone seals keys to this
                          ("key_requests", "/approvals?kind=key_request")):   # F-41: only key requests''')

# --- phone: pubspec, API, approvals screen
edit('odin_app/pubspec.yaml', '  http: ^1.2.0\n', '  http: ^1.2.0\n  cryptography: ^2.7.0   # F-41: X25519 + HKDF + AES-GCM for the encrypted key relay\n')
edit('odin_app/lib/api/anchor_api.dart', '''  Future<List<Map<String, dynamic>>> approvals([String? pid]) async {
    final d = await _get(''', '''  /// True when the app talks to the Mac only through the Anchor (web/mobile away from the desktop).
  bool get anchorMode => _anchorRead;

  /// F-41: the Mac's PUBLIC relay key {alg, pub, kid}. Anchor mode -> mirror; direct -> brain.
  Future<Map<String, dynamic>> relayPubKey() async {
    if (_anchorRead) return _anchorMirror('relay_pubkey');
    return Map<String, dynamic>.from(await _get(_api('/secrets/relay-pubkey'), _native()));
  }

  /// F-41: send a SEALED key (envelope from KeyRelay.seal). There is no method that sends a plain key.
  Future<String> sendSealedKey(String aid, String name, Map<String, dynamic> envelope) async {
    if (_anchorRead) {
      await commandViaAnchor('key_e2e', {'aid': aid, 'name': name, 'envelope': envelope});
      return 'sent';
    }
    final r = await _post(_api('/secrets/project-key-e2e'), _native(), {'aid': aid, 'name': name, 'envelope': envelope});
    return (r is Map && r['ok'] == true) ? 'stored' : 'refused: ${r is Map ? r['error'] : r}';
  }

  Future<List<Map<String, dynamic>>> approvals([String? pid]) async {
    if (_anchorRead) {   // F-41: only KEY REQUESTS are mirrored; other approvals stay on the desktop
      final m = await _anchorMirror('key_requests');
      return ((m['approvals'] ?? []) as List).map((e) => Map<String, dynamic>.from(e))
          .where((a) => pid == null || a['pid']?.toString() == pid).toList();
    }
    final d = await _get(''')

A = 'odin_app/lib/screens/approvals.dart'
edit(A, "import 'package:flutter/material.dart';\nimport 'package:provider/provider.dart';\n",
     "import 'dart:convert';\n\nimport 'package:flutter/material.dart';\nimport 'package:provider/provider.dart';\nimport 'package:shared_preferences/shared_preferences.dart';\n\nimport '../security/key_relay.dart';\n")
edit(A, '''  List<Map<String, dynamic>> _items = [];
  bool _loading = true;''', '''  List<Map<String, dynamic>> _items = [];
  Map<String, dynamic>? _relay;   // F-41: {pub, kid, pin}
  bool _loading = true;''')
edit(A, '''      _items = await context.read<AppState>().api.approvals();
    } catch (e) {
      _err = '$e';
    }''', '''      final api = context.read<AppState>().api;
      _items = await api.approvals();
      _relay = await _loadRelay(api);
    } catch (e) {
      _err = '$e';
    }''')
edit(A, '''  Future<void> _act(String aid, bool approve) async {''', '''  /// F-41: fetch the Mac's public key, check its fingerprint, and pin it on first use.
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

  Future<String> _sealed(String aid, String name, String value) async {
    final r = _relay;
    if (r == null || r['pin'] != 'pinned') return 'refused: no trusted Mac key';
    final env = await KeyRelay.seal(r['pub'].toString(), value, aid, name);   // plain value never leaves
    final res = await context.read<AppState>().api.sendSealedKey(aid, name, env);
    _load();
    return res;
  }

  Future<void> _act(String aid, bool approve) async {''')
edit(A, '''                    ApprovalActions(item: a, onAct: _act),''',
     '''                    ApprovalActions(item: a, onAct: _act, relay: _relay, onSealedKey: _sealed,
                        remote: context.read<AppState>().api.anchorMode),''')
edit(A, '''/// F-41 interim (owner 2026-10-11): a KEY REQUEST is never answered on the phone. Until the end-to-end
/// encrypted relay exists, the phone shows "enter this key on the desktop" and has NO field and NO Approve —
/// so a key can never leave the phone in plain text. Reject (sends no key) stays available.
class ApprovalActions extends StatelessWidget {
  const ApprovalActions({super.key, required this.item, required this.onAct});
  final Map<String, dynamic> item;
  final Future<void> Function(String aid, bool approve) onAct;''', '''/// F-41 (owner 2026-10-11): a KEY REQUEST is never answered with Approve and never sends a plain key.
/// With a trusted (pinned) Mac key the phone shows a secure field whose value is SEALED to the Mac
/// (KeyRelay.seal) before it leaves; the Anchor only relays ciphertext. Without one — or if the Mac key's
/// fingerprint changed — the phone shows "enter this key on the desktop". Reject (sends no key) stays.
class ApprovalActions extends StatelessWidget {
  const ApprovalActions(
      {super.key, required this.item, required this.onAct, this.relay, this.onSealedKey, this.remote = false});
  final Map<String, dynamic> item;
  final Future<void> Function(String aid, bool approve) onAct;
  final Map<String, dynamic>? relay;   // {pub, kid, pin: pinned|mismatch}
  final Future<String> Function(String aid, String name, String value)? onSealedKey;
  final bool remote;                   // Anchor mode: approve/reject are desktop-only (owner decision pending)''')
edit(A, '''      final name = (item['key_name'] ?? '').toString();
      return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('Enter this key on the desktop${name.isNotEmpty ? ' ($name)' : ''}. '
            'For your safety, the phone never sends keys.',
            key: const ValueKey('desktop-only'),
            style: const TextStyle(fontSize: 13, color: Odin.warn)),
        const SizedBox(height: 8),
        reject,
      ]);''', '''      final name = (item['key_name'] ?? '').toString();
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
      ]);''')
s = pathlib.Path(A).read_text()
if 'class KeyRelayField' not in s:
    s += """

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
"""
    pathlib.Path(A).write_text(s); print('ok KeyRelayField')
