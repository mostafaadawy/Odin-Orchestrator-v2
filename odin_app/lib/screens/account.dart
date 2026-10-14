import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_state.dart';
import '../theme.dart';
import '../widgets.dart';

class AccountSection extends StatefulWidget {
  const AccountSection({super.key});
  @override
  State<AccountSection> createState() => _AccountSectionState();
}

class _AccountSectionState extends State<AccountSection> {
  final _old = TextEditingController();
  final _new = TextEditingController();
  String? _msg;
  bool _busy = false;

  Future<void> _change() async {
    setState(() {
      _busy = true;
      _msg = null;
    });
    final err = await context.read<AppState>().changePassword(_old.text, _new.text);
    setState(() {
      _busy = false;
      _msg = err ?? 'Password changed ✓';
      if (err == null) {
        _old.clear();
        _new.clear();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final s = context.watch<AppState>();
    final cfg = s.authConfig;
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Text('Account', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
              const Spacer(),
              if (s.loggedIn)
                TextButton.icon(
                  onPressed: () => s.logout(),
                  icon: const Icon(Icons.logout, size: 16, color: Odin.danger),
                  label: const Text('Sign out', style: TextStyle(color: Odin.danger)),
                ),
            ],
          ),
          Text('Signed in as ${s.authedEmail.isEmpty ? "tech@odinmarkets.com" : s.authedEmail}',
              style: const TextStyle(fontSize: 12, color: Odin.txtDim)),
          const SizedBox(height: 12),
          const Text('Change password', style: TextStyle(fontSize: 12, color: Odin.txtDim)),
          const SizedBox(height: 6),
          TextField(controller: _old, obscureText: true, decoration: const InputDecoration(labelText: 'Current password', border: OutlineInputBorder(), isDense: true)),
          const SizedBox(height: 8),
          TextField(controller: _new, obscureText: true, decoration: const InputDecoration(labelText: 'New password', border: OutlineInputBorder(), isDense: true)),
          const SizedBox(height: 8),
          Row(
            children: [
              FilledButton(
                onPressed: _busy ? null : _change,
                style: FilledButton.styleFrom(backgroundColor: Odin.brand),
                child: const Text('Update password'),
              ),
              const SizedBox(width: 10),
              if (_msg != null) Flexible(child: Text(_msg!, style: TextStyle(fontSize: 12, color: _msg!.contains('✓') ? Odin.ok : Odin.danger))),
            ],
          ),
          const Divider(height: 24),
          const Text('Security (defaults off — toggle to enable)', style: TextStyle(fontSize: 12, color: Odin.txtDim)),
          SwitchListTile(
            dense: true,
            contentPadding: EdgeInsets.zero,
            value: cfg['twofa_enabled'] == true,
            onChanged: (v) => s.setAuthFlag('twofa_enabled', v),
            title: const Text('Two-factor authentication (2FA)', style: TextStyle(fontSize: 13)),
            subtitle: const Text('Dev code: 000000', style: TextStyle(fontSize: 11, color: Odin.txtFaint)),
          ),
          SwitchListTile(
            dense: true,
            contentPadding: EdgeInsets.zero,
            value: cfg['verify_email_enabled'] == true,
            onChanged: (v) => s.setAuthFlag('verify_email_enabled', v),
            title: const Text('Require verified email', style: TextStyle(fontSize: 13)),
          ),
          SwitchListTile(
            dense: true,
            contentPadding: EdgeInsets.zero,
            value: cfg['faceid_first_access'] == true,
            onChanged: (v) => s.setAuthFlag('faceid_first_access', v),
            title: const Text('Face ID first access (mobile)', style: TextStyle(fontSize: 13)),
          ),
        ],
      ),
    );
  }
}
