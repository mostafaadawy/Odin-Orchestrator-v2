import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'state/app_state.dart';
import 'theme.dart';
import 'screens/shell.dart';
import 'screens/login.dart';
import 'screens/mobile_shell.dart';
import 'services/cert_override.dart';

Future<void> main() async {
  // A build-time error must never leave a blank/white screen — show a readable
  // message instead (this app is used with assistive needs, so a hard crash is
  // especially costly). Uncaught async errors are also swallowed rather than
  // taking the whole app down.
  ErrorWidget.builder = (FlutterErrorDetails details) => Material(
        color: const Color(0xFF0A0C12),
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text(
              'Something hiccuped on this screen.\nPull to refresh or reopen the chat.',
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.white70, fontSize: 15),
            ),
          ),
        ),
      );

  runZonedGuarded(() async {
    WidgetsFlutterBinding.ensureInitialized();
    installOdinCertOverride(); // trust the VM's self-signed cert for the reverse proxy (mobile/desktop only)
    FlutterError.onError = (d) => FlutterError.presentError(d);
    final state = await AppState.create();
    runApp(OdinApp(state: state));
  }, (error, stack) {
    debugPrint('Uncaught: $error');
  });
}

class OdinApp extends StatelessWidget {
  final AppState state;
  const OdinApp({super.key, required this.state});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider.value(
      value: state,
      child: MaterialApp(
        title: 'Odin — Remote Anchor',
        debugShowCheckedModeBanner: false,
        theme: Odin.theme(),
        // v2: on the PHONE every text is a notch larger (readable captions); the user's own iOS text size still
        // applies on top. The web keeps its sizes.
        builder: (context, child) {
          if (kIsWeb) return child!;
          final mq = MediaQuery.of(context);
          return MediaQuery(
            data: mq.copyWith(textScaler: TextScaler.linear((mq.textScaler.scale(14) / 14 * 1.15).clamp(1.15, 1.6))),
            child: child!,
          );
        },
        home: const _Gate(),
      ),
    );
  }
}

class _Gate extends StatelessWidget {
  const _Gate();
  @override
  Widget build(BuildContext context) {
    final s = context.watch<AppState>();
    if (!s.authResolved) {
      return Container(
        decoration: Odin.bgDecoration,
        child: const Scaffold(
          backgroundColor: Colors.transparent,
          body: Center(child: CircularProgressIndicator(color: Odin.brand)),
        ),
      );
    }
    // v2: the phone gets its own phone-first shell (bottom tabs + stack navigation); the web keeps the sidebar.
    return s.gateOpen ? (kIsWeb ? const Shell() : const MobileShell()) : const LoginScreen();
  }
}
