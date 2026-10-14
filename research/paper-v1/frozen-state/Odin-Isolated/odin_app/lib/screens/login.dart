import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_state.dart';
import '../services/biometric.dart';
import '../theme.dart';
import '../widgets.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});
  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _email = TextEditingController(text: 'tech@odinmarkets.com');
  final _pw = TextEditingController(text: '');
  final _code = TextEditingController();
  final _biometric = Biometric();
  bool _busy = false;
  String? _err;
  bool _bioAvail = false;
  bool _codeSent = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      _bioAvail = await _biometric.available();
      if (mounted) setState(() {});
      final s = context.read<AppState>();
      if (s.pendingBiometric && _bioAvail) _faceId();
    });
  }

  Future<void> _faceId() async {
    final s = context.read<AppState>();
    final ok = await _biometric.authenticate('Unlock Odin with Face ID');
    if (ok) s.resumeAfterBiometric();
  }

  Future<void> _getCode() async {
    final s = context.read<AppState>();
    setState(() { _busy = true; _err = null; });
    final e = await s.requestLoginCode();
    setState(() { _busy = false; _codeSent = e == null; _err = e; });
  }

  Future<void> _login() async {
    setState(() {
      _busy = true;
      _err = null;
    });
    final s = context.read<AppState>();
    // ANCHOR mode (web/mobile): email + password + the code shown on the desktop.
    if (s.isAnchorMode) {
      final res = await s.loginViaAnchor(_email.text.trim(), _pw.text, _code.text.trim());
      if (res == null) return; // success → gate rebuilds
      setState(() { _busy = false; _err = res; });
      return;
    }
    final res = await s.login(_email.text.trim(), _pw.text);
    if (res == null) return; // success → gate rebuilds
    if (res.startsWith('2fa:')) {
      final email = res.substring(4);
      if (mounted) _ask2fa(email);
    } else {
      setState(() {
        _busy = false;
        _err = res;
      });
    }
  }

  Future<void> _ask2fa(String email) async {
    final code = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: Odin.panelSolid,
        title: const Text('Two-factor code'),
        content: TextField(controller: code, decoration: const InputDecoration(hintText: '6-digit code (dev: 000000)')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Verify')),
        ],
      ),
    );
    if (ok == true) {
      final r = await context.read<AppState>().submit2fa(email, code.text.trim());
      if (r != null) setState(() => _err = r);
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _forgot() async {
    await context.read<AppState>().forgot(_email.text.trim());
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('If that email exists, a reset link was sent. (Dev: change it in Settings → Account after login.)')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = context.watch<AppState>();
    return Container(
      decoration: Odin.bgDecoration,
      child: Scaffold(
        backgroundColor: Colors.transparent,
        body: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 380),
              child: GlassCard(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Center(
                      child: Container(
                        width: 56,
                        height: 56,
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(16),
                          gradient: const SweepGradient(colors: [Odin.brand, Odin.accent, Odin.brand2, Odin.brand]),
                        ),
                        child: const Center(child: Text('Ω', style: TextStyle(fontSize: 28, fontWeight: FontWeight.w900, color: Odin.bg))),
                      ),
                    ),
                    const SizedBox(height: 12),
                    const Center(child: SectionTitle('Odin — Remote Anchor')),
                    Center(child: Text(kIsWeb ? 'Web sign in' : 'Mobile sign in', style: const TextStyle(fontSize: 12, color: Odin.txtFaint))),
                    const SizedBox(height: 18),
                    if (s.pendingBiometric && _bioAvail) ...[
                      FilledButton.icon(
                        onPressed: _faceId,
                        style: FilledButton.styleFrom(backgroundColor: Odin.brand),
                        icon: const Icon(Icons.face_retouching_natural),
                        label: const Text('Unlock with Face ID'),
                      ),
                      const SizedBox(height: 10),
                      const Center(child: Text('or sign in with password', style: TextStyle(fontSize: 11, color: Odin.txtFaint))),
                      const SizedBox(height: 10),
                    ],
                    TextField(
                      controller: _email,
                      decoration: const InputDecoration(labelText: 'Email', border: OutlineInputBorder(), isDense: true),
                    ),
                    const SizedBox(height: 10),
                    TextField(
                      controller: _pw,
                      obscureText: true,
                      onSubmitted: (_) => s.isAnchorMode ? null : _login(),
                      decoration: const InputDecoration(labelText: 'Password', border: OutlineInputBorder(), isDense: true),
                    ),
                    if (s.isAnchorMode) ...[
                      const SizedBox(height: 10),
                      Row(children: [
                        Expanded(
                          child: TextField(
                            controller: _code,
                            keyboardType: TextInputType.number,
                            onSubmitted: (_) => _login(),
                            decoration: const InputDecoration(labelText: 'Code (from your desktop)', border: OutlineInputBorder(), isDense: true),
                          ),
                        ),
                        const SizedBox(width: 8),
                        OutlinedButton(onPressed: _busy ? null : _getCode, child: const Text('Get code')),
                      ]),
                      const SizedBox(height: 4),
                      Text(_codeSent
                          ? 'A code was generated — see the blinking "Connecting with Anchor" badge on your desktop.'
                          : 'Tap "Get code" — the code appears on your desktop\'s "Connecting with Anchor" badge.',
                          style: const TextStyle(fontSize: 10.5, color: Odin.txtFaint)),
                    ],
                    if (_err != null) ...[
                      const SizedBox(height: 10),
                      Text(_err!, style: const TextStyle(fontSize: 12, color: Odin.danger)),
                    ],
                    const SizedBox(height: 14),
                    FilledButton(
                      onPressed: _busy ? null : _login,
                      style: FilledButton.styleFrom(backgroundColor: Odin.brand),
                      child: _busy
                          ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                          : const Text('Sign in'),
                    ),
                    TextButton(onPressed: _forgot, child: const Text('Forgot password?')),
                    if (!_bioAvail && !kIsWeb)
                      const Text('Face ID unavailable on this device/simulator — use the password.',
                          style: TextStyle(fontSize: 10.5, color: Odin.txtFaint), textAlign: TextAlign.center),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
