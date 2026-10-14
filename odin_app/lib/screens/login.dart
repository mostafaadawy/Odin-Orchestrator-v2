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

  // ---------------------------------------------------------------- v2 look (logic above is unchanged)
  InputDecoration _field(String label, IconData icon, {String? hint, Widget? suffix}) => InputDecoration(
        labelText: label,
        hintText: hint,
        prefixIcon: Icon(icon, size: 20, color: Odin.txtDim),
        suffixIcon: suffix,
        filled: true,
        fillColor: const Color(0x0FFFFFFF),
        labelStyle: const TextStyle(color: Odin.txtDim, fontSize: 13.5),
        floatingLabelStyle: const TextStyle(color: Odin.brand2),
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 15),
        enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: Odin.stroke)),
        focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: Odin.brand, width: 1.4)),
      );

  Widget _step(int n, String t, bool done, bool now) => Expanded(
        child: Column(children: [
          AnimatedContainer(
            duration: const Duration(milliseconds: 250),
            width: 28, height: 28,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: done || now ? const LinearGradient(colors: [Odin.brand, Odin.brand2]) : null,
              color: done || now ? null : const Color(0x14FFFFFF),
              border: Border.all(color: now ? Odin.brand2 : Odin.stroke),
            ),
            child: Center(child: done
                ? const Icon(Icons.check, size: 16, color: Color(0xFF0B0B16))
                : Text('$n', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: now ? const Color(0xFF0B0B16) : Odin.txtFaint))),
          ),
          const SizedBox(height: 6),
          Text(t, textAlign: TextAlign.center, style: TextStyle(fontSize: 10.5, color: now ? Odin.txt : Odin.txtFaint, height: 1.2)),
        ]),
      );

  @override
  Widget build(BuildContext context) {
    final s = context.watch<AppState>();
    final anchor = s.isAnchorMode;
    return Container(
      decoration: Odin.bgDecoration,
      child: Scaffold(
        backgroundColor: Colors.transparent,
        body: Stack(children: [
          // soft tech glow behind the card
          Positioned(top: -120, left: -80, child: _Glow(color: Odin.brand, size: 320)),
          Positioned(bottom: -140, right: -90, child: _Glow(color: Odin.brand2, size: 300)),
          SafeArea(
            child: Center(
              child: SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(22, 24, 22, 24),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 400),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                    // brand
                    Center(
                      child: Container(
                        width: 68, height: 68,
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(20),
                          gradient: const SweepGradient(colors: [Odin.brand, Odin.accent, Odin.brand2, Odin.brand]),
                          boxShadow: [BoxShadow(color: Odin.brand.withOpacity(.45), blurRadius: 30, spreadRadius: 1)],
                        ),
                        child: const Center(child: Text('Ω', style: TextStyle(fontSize: 34, fontWeight: FontWeight.w900, color: Color(0xFF0B0B16)))),
                      ),
                    ),
                    const SizedBox(height: 14),
                    Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                      const Text('Odin', style: TextStyle(fontSize: 26, fontWeight: FontWeight.w800, letterSpacing: .3)),
                      const SizedBox(width: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                        decoration: BoxDecoration(borderRadius: BorderRadius.circular(999), gradient: const LinearGradient(colors: [Odin.brand, Odin.brand2])),
                        child: const Text('v2', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w900, color: Color(0xFF0B0B16))),
                      ),
                    ]),
                    const SizedBox(height: 4),
                    Center(
                      child: Text(kIsWeb ? 'SECURE WEB ACCESS · VIA ANCHOR' : 'SECURE MOBILE ACCESS · VIA ANCHOR',
                          style: const TextStyle(fontSize: 10.5, letterSpacing: 2, color: Odin.brand2, fontFamily: 'monospace')),
                    ),
                    const SizedBox(height: 22),
                    GlassCard(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                        if (anchor) ...[
                          Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                            _step(1, 'Get a code', _codeSent, !_codeSent),
                            _step(2, 'Approve on\nyour Mac', false, _codeSent),
                            _step(3, 'Sign in', false, false),
                          ]),
                          const SizedBox(height: 18),
                        ],
                        if (s.pendingBiometric && _bioAvail) ...[
                          SizedBox(
                            height: 50,
                            child: FilledButton.icon(
                              onPressed: _faceId,
                              style: FilledButton.styleFrom(backgroundColor: Odin.brand, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
                              icon: const Icon(Icons.face_retouching_natural),
                              label: const Text('Unlock with Face ID', style: TextStyle(fontWeight: FontWeight.w700)),
                            ),
                          ),
                          const SizedBox(height: 12),
                          const Row(children: [
                            Expanded(child: Divider(color: Odin.stroke)),
                            Padding(padding: EdgeInsets.symmetric(horizontal: 10), child: Text('or', style: TextStyle(fontSize: 11, color: Odin.txtFaint))),
                            Expanded(child: Divider(color: Odin.stroke)),
                          ]),
                          const SizedBox(height: 12),
                        ],
                        TextField(controller: _email, keyboardType: TextInputType.emailAddress, autocorrect: false,
                            decoration: _field('Email', Icons.alternate_email)),
                        const SizedBox(height: 12),
                        TextField(controller: _pw, obscureText: true,
                            onSubmitted: (_) => anchor ? null : _login(),
                            decoration: _field('Password', Icons.lock_outline, hint: 'copy it from the Mac')),
                        if (anchor) ...[
                          const SizedBox(height: 12),
                          Row(children: [
                            Expanded(
                              child: TextField(
                                controller: _code,
                                keyboardType: TextInputType.number,
                                onSubmitted: (_) => _login(),
                                style: const TextStyle(letterSpacing: 6, fontWeight: FontWeight.w700, fontSize: 18, fontFamily: 'monospace'),
                                decoration: _field('One-time code', Icons.pin_outlined),
                              ),
                            ),
                            const SizedBox(width: 10),
                            SizedBox(
                              height: 52,
                              child: OutlinedButton.icon(
                                onPressed: _busy ? null : _getCode,
                                style: OutlinedButton.styleFrom(
                                  foregroundColor: Odin.brand2,
                                  side: const BorderSide(color: Odin.brand2),
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                                ),
                                icon: Icon(_codeSent ? Icons.refresh : Icons.send_to_mobile, size: 18),
                                label: Text(_codeSent ? 'Again' : 'Get code'),
                              ),
                            ),
                          ]),
                          const SizedBox(height: 10),
                          Container(
                            padding: const EdgeInsets.all(10),
                            decoration: BoxDecoration(
                              color: (_codeSent ? Odin.brand2 : Odin.brand).withOpacity(.08),
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(color: (_codeSent ? Odin.brand2 : Odin.brand).withOpacity(.3)),
                            ),
                            child: Row(children: [
                              Icon(_codeSent ? Icons.desktop_mac : Icons.info_outline, size: 18, color: _codeSent ? Odin.brand2 : Odin.brand),
                              const SizedBox(width: 10),
                              Expanded(
                                child: Text(
                                  _codeSent
                                      ? 'Code sent. On your Mac the 🔗 Anchor button is blinking — open it and copy the email, password and code here.'
                                      : 'Tap "Get code". Your Mac shows it on the blinking 🔗 Anchor button, with the email and password to copy.',
                                  style: const TextStyle(fontSize: 11.5, color: Odin.txtDim, height: 1.35),
                                ),
                              ),
                            ]),
                          ),
                        ],
                        if (_err != null) ...[
                          const SizedBox(height: 12),
                          Row(children: [
                            const Icon(Icons.error_outline, size: 16, color: Odin.danger),
                            const SizedBox(width: 6),
                            Expanded(child: Text(_err!, style: const TextStyle(fontSize: 12, color: Odin.danger))),
                          ]),
                        ],
                        const SizedBox(height: 16),
                        SizedBox(
                          height: 52,
                          child: DecoratedBox(
                            decoration: BoxDecoration(
                              borderRadius: BorderRadius.circular(14),
                              gradient: const LinearGradient(colors: [Odin.brand, Color(0xFF6E5BFF)]),
                              boxShadow: [BoxShadow(color: Odin.brand.withOpacity(.35), blurRadius: 18, offset: const Offset(0, 6))],
                            ),
                            child: TextButton(
                              onPressed: _busy ? null : _login,
                              style: TextButton.styleFrom(foregroundColor: Colors.white, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
                              child: _busy
                                  ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                                  : const Text('Sign in', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800, letterSpacing: .3)),
                            ),
                          ),
                        ),
                        TextButton(onPressed: _forgot, child: const Text('Forgot password?', style: TextStyle(color: Odin.txtDim))),
                      ]),
                    ),
                    const SizedBox(height: 16),
                    const Wrap(alignment: WrapAlignment.center, spacing: 14, runSpacing: 6, children: [
                      _Badge(Icons.verified_user_outlined, 'Approved on your Mac'),
                      _Badge(Icons.timer_outlined, '7-day session'),
                      _Badge(Icons.devices_outlined, 'Remembered device 30 days'),
                    ]),
                    if (!_bioAvail && !kIsWeb)
                      const Padding(
                        padding: EdgeInsets.only(top: 10),
                        child: Text('Face ID is not available on this device — the code sign-in above works everywhere.',
                            style: TextStyle(fontSize: 10.5, color: Odin.txtFaint), textAlign: TextAlign.center),
                      ),
                  ]),
                ),
              ),
            ),
          ),
        ]),
      ),
    );
  }
}

class _Glow extends StatelessWidget {
  final Color color;
  final double size;
  const _Glow({required this.color, required this.size});
  @override
  Widget build(BuildContext context) => IgnorePointer(
        child: Container(
          width: size, height: size,
          decoration: BoxDecoration(shape: BoxShape.circle, gradient: RadialGradient(colors: [color.withOpacity(.28), color.withOpacity(0)])),
        ),
      );
}

class _Badge extends StatelessWidget {
  final IconData icon;
  final String text;
  const _Badge(this.icon, this.text);
  @override
  Widget build(BuildContext context) => Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(icon, size: 14, color: Odin.txtFaint),
        const SizedBox(width: 5),
        Text(text, style: const TextStyle(fontSize: 11, color: Odin.txtFaint)),
      ]);
}
