import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../config.dart';
import '../state/app_state.dart';
import '../theme.dart';
import '../widgets.dart';
import 'account.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});
  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  String? _testOutput;
  bool _testing = false;

  @override
  Widget build(BuildContext context) {
    final s = context.watch<AppState>();
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const AccountSection(),
        const SizedBox(height: 16),
        const SectionTitle('Environment & access'),
        const SizedBox(height: 4),
        const Text('Each profile = a base URL set + auth. Phase 3 = pick "Deployed" and set the anchor URL.',
            style: TextStyle(fontSize: 12, color: Odin.txtFaint)),
        const SizedBox(height: 12),
        ...List.generate(s.cfg.profiles.length, (i) {
          final p = s.cfg.profiles[i];
          final selected = s.cfg.selected == i;
          return GlassCard(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
            onTap: () => s.selectProfile(i),
            child: Row(
              children: [
                Icon(selected ? Icons.radio_button_checked : Icons.radio_button_off,
                    color: selected ? Odin.brand : Odin.txtFaint, size: 20),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('${p.name}  ·  ${p.mode.name}', style: const TextStyle(fontWeight: FontWeight.w600)),
                      Text('brain: ${p.apiBaseUrl}\nanchor: ${p.anchorBaseUrl}',
                          style: const TextStyle(fontSize: 11, color: Odin.txtFaint)),
                    ],
                  ),
                ),
              ],
            ),
          );
        }),
        const SizedBox(height: 16),
        GlassCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Edit "${s.env.name}"', style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
              const SizedBox(height: 10),
              _EditProfile(env: s.env, onChanged: s.saveProfiles),
            ],
          ),
        ),
        const SizedBox(height: 16),
        FilledButton.icon(
          onPressed: _testing ? null : () => _test(s),
          style: FilledButton.styleFrom(backgroundColor: Odin.brand),
          icon: _testing
              ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
              : const Icon(Icons.wifi_tethering),
          label: const Text('Test connection to local machine'),
        ),
        if (_testOutput != null)
          Padding(
            padding: const EdgeInsets.only(top: 12),
            child: Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(color: const Color(0xFF11151D), borderRadius: BorderRadius.circular(8)),
              child: SelectableText(_testOutput!, style: const TextStyle(fontSize: 12, fontFamily: 'monospace')),
            ),
          ),
        const SizedBox(height: 24),
        const Text(
          'Auth: the brain token (X-Odin-Token) and the anchor key (X-API-Key) are sent with every '
          'request. On localhost they can be blank; for the deployed anchor set the keys from oth/.cred. '
          'Going to Phase 3 = pick "Deployed" and set the anchor URL — nothing else changes.',
          style: TextStyle(fontSize: 11, color: Odin.txtFaint),
        ),
      ],
    );
  }

  Future<void> _test(AppState s) async {
    setState(() {
      _testing = true;
      _testOutput = null;
    });
    final out = await s.testConnection();
    setState(() {
      _testing = false;
      _testOutput = out.entries.map((e) => '${e.key}: ${e.value}').join('\n');
    });
  }
}

class _EditProfile extends StatefulWidget {
  final EnvProfile env;
  final VoidCallback onChanged;
  const _EditProfile({required this.env, required this.onChanged});
  @override
  State<_EditProfile> createState() => _EditProfileState();
}

class _EditProfileState extends State<_EditProfile> {
  late TextEditingController _api, _anchor, _token, _odinKey, _anchorKey;

  @override
  void initState() {
    super.initState();
    _api = TextEditingController(text: widget.env.apiBaseUrl);
    _anchor = TextEditingController(text: widget.env.anchorBaseUrl);
    _token = TextEditingController(text: widget.env.token);
    _odinKey = TextEditingController(text: widget.env.odinApiKey);
    _anchorKey = TextEditingController(text: widget.env.anchorApiKey);
  }

  @override
  void didUpdateWidget(covariant _EditProfile old) {
    super.didUpdateWidget(old);
    if (old.env != widget.env) {
      _api.text = widget.env.apiBaseUrl;
      _anchor.text = widget.env.anchorBaseUrl;
      _token.text = widget.env.token;
      _odinKey.text = widget.env.odinApiKey;
      _anchorKey.text = widget.env.anchorApiKey;
    }
  }

  void _commit() {
    widget.env.apiBaseUrl = _api.text;
    widget.env.anchorBaseUrl = _anchor.text;
    widget.env.token = _token.text;
    widget.env.odinApiKey = _odinKey.text;
    widget.env.anchorApiKey = _anchorKey.text;
    widget.onChanged();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        _field('Brain base URL (/api/v1, /projects, /chat …)', _api),
        _field('Anchor base URL (/anchor/v1)', _anchor),
        _field('Brain token — X-Odin-Token', _token, obscure: true),
        _field('ODIN_API_KEY — X-API-Key for /api/v1', _odinKey, obscure: true),
        _field('ANCHOR_API_KEY — X-API-Key for /anchor/v1', _anchorKey, obscure: true),
        Row(
          children: [
            SegmentedButton<AccessMode>(
              segments: const [
                ButtonSegment(value: AccessMode.direct, label: Text('direct')),
                ButtonSegment(value: AccessMode.anchor, label: Text('anchor')),
              ],
              selected: {widget.env.mode},
              onSelectionChanged: (set) {
                setState(() => widget.env.mode = set.first);
                widget.onChanged();
              },
            ),
            const Spacer(),
            FilledButton.tonal(onPressed: _commit, child: const Text('Save')),
          ],
        ),
      ],
    );
  }

  Widget _field(String label, TextEditingController c, {bool obscure = false}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: TextField(
        controller: c,
        obscureText: obscure,
        onChanged: (_) => _commit(),
        decoration: InputDecoration(labelText: label, border: const OutlineInputBorder(), isDense: true),
      ),
    );
  }
}
